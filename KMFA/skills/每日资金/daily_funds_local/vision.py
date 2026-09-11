"""用 DeepSeek Vision 把余额表截图读成结构化数字。

三代版式的表头和行结构完全不同，所以按版式分派三套提示词——用一套通用提示词
会在版式 A 上读错列（A 的列名是「收款小计/付款小计/本日余额」，B/C 是
「今日收款/今日支出/今日余额」）。

模型只被要求输出 JSON。读出来的数字随后必须过 gate.check()：硬门不过就丢弃，
所以这里不需要信任模型，只需要它给出可被验伪的答案。
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from typing import Optional

from .crop import focus
from .gate import DayFacts, GateError, to_fen

API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-v4-flash-vision-exp"

_COMMON_TAIL = """
规则：
- 只输出 JSON，不要任何解释、不要 markdown 代码围栏。
- 金额保留两位小数的字符串原样输出，去掉千分位逗号。
- 单元格是「–」「-」或空白时输出 "0"。
- 日期输出 YYYY-MM-DD。表里只写了月日时，年份用 2026。
"""

PROMPT_BC = """这是一张「2026年资金账户明细表」截图。列依次是：
公司 / 内容 / 账户名 / 昨日余额 / 今日收款 / 今日支出 / 今日余额。

只读这四样，其他行一律忽略：
1. 左上角那个日期单元格（形如「09月03日」）。
2. 橙色底的「所有银行存款合计」行的四个数。
3. 橙色底的「所有汇票合计」行的四个数。
4. 最底部粉色底的「合计」行的四个数。

输出：
{"report_date":"","bank":{"open":"","in":"","out":"","close":""},
 "bill":{"open":"","in":"","out":"","close":""},
 "total":{"open":"","in":"","out":"","close":""}}
""" + _COMMON_TAIL

PROMPT_A = """这是一张「资金账户明细表」截图（旧版式）。列依次是：
昨日余额 / 收款小计 / 付款小计 / 本日余额。注意列名与新版不同。

只读这五样，其他行一律忽略：
1. 顶部「报告日期：」后面的日期。
2. 底部黄色「总计」区块里「银行存款」行的四个数。
3. 同一区块里「电子承兑汇票」行的四个数。
4. 同一区块里「库存现金」行的四个数。
5. 同一区块里「总计」行的四个数。

注意：「总计」区块下面还有几行（工会户、个人、岚丹等）不在总计之内，不要读。

输出：
{"report_date":"","bank":{"open":"","in":"","out":"","close":""},
 "bill":{"open":"","in":"","out":"","close":""},
 "cash":{"open":"","in":"","out":"","close":""},
 "total":{"open":"","in":"","out":"","close":""}}
""" + _COMMON_TAIL

PROMPTS = {"A": PROMPT_A, "B": PROMPT_BC, "C": PROMPT_BC}

# 「现存票据」逐张台账。读出来的东西由 bills.check_rows 的三道校验位 + 跨源核对验伪，
# 所以这里同样不需要信任模型。实测模型爱把各行加起来冒充「合计」（07-06 那张输出的合计与图上
# 印的差两位数字，却与它自己读的各行自洽），所以提示词里专门禁止。
PROMPT_BILLS = """这是一张「现存票据」表截图：电子承兑汇票逐张台账。列依次是：
序号 / 收到票据日期 / 汇票出票日 / 汇票到期日 / 距离到期日 / 收款银行 / 票据类别 / 出票行（承兑行）/ 票据号 / 票据金额 / 客户名。
最底部一行是「合计」。

逐行读出每一张票的这四样，其余列一律忽略：
- seq：序号
- due：汇票到期日
- days：距离到期日（整数）
- amount：票据金额
再读出最底部「合计」那一格的金额。

输出：
{"rows":[{"seq":1,"due":"2026-09-24","days":17,"amount":"12345.67"}],"total":"123456.78"}

规则：
- 只输出 JSON，不要任何解释、不要 markdown 代码围栏。
- 每一张票都要输出，不要跳行、不要合并行、不要编造；行数必须等于表里的票据张数。
- 「合计」必须照图上那一格印的数字逐位抄写。绝对不要把各行金额加起来代替它——
  它是用来核对你读的每一行对不对的，自己算出来就失去了核对的意义。
- 金额去掉「¥」和千分位逗号，保留两位小数的字符串原样输出。
- 日期输出 YYYY-MM-DD。
"""


class VisionError(RuntimeError):
    pass


def _api_key() -> str:
    key = os.environ.get("DAILY_FUNDS_DEEPSEEK_KEY", "").strip()
    if not key:
        env = os.path.expanduser("~/.kmfa_daily_funds.env")
        if os.path.exists(env):
            for line in open(env, encoding="utf-8"):
                line = line.strip()
                if line.startswith("DAILY_FUNDS_DEEPSEEK_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not key:
        raise VisionError("缺少 DAILY_FUNDS_DEEPSEEK_KEY（环境变量或 ~/.kmfa_daily_funds.env）")
    return key


def _post(payload: dict, key: str, timeout: int = 90) -> dict:
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 绝不把 key 或响应体原样抛进日志
        raise VisionError("Vision HTTP %s" % exc.code)
    except Exception as exc:
        raise VisionError("Vision 请求失败: %s" % type(exc).__name__)


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise VisionError("Vision 返回里没有 JSON")
    return json.loads(text[start:end + 1])


def _normalize_date(raw: str, fallback_year: str = "2026") -> str:
    raw = (raw or "").strip()
    m = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", raw)
    if m:
        return "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3)))
    m = re.search(r"(\d{1,2})[-/月](\d{1,2})", raw)
    if m:
        return "%s-%02d-%02d" % (fallback_year, int(m.group(1)), int(m.group(2)))
    return raw


def read_card(image_path: str, layout: str, *, model: Optional[str] = None,
              retries: int = 1) -> DayFacts:
    key = _api_key()
    # 先裁成聚焦图：只留日期条 + 底部三行汇总，放大 2x。
    # 整张表的四十行账户明细会挤占分辨率，是确定性误读的根因（见 crop.py）。
    b64 = base64.b64encode(open(focus(image_path, layout), "rb").read()).decode("ascii")
    payload = {
        "model": model or os.environ.get("DAILY_FUNDS_VISION_MODEL") or DEFAULT_MODEL,
        "temperature": 0,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPTS[layout]},
                {"type": "image_url",
                 "image_url": {"url": "data:image/png;base64," + b64}},
            ],
        }],
    }

    last: Optional[Exception] = None
    for _ in range(retries + 1):
        try:
            body = _post(payload, key)
            text = body["choices"][0]["message"]["content"]
            data = _extract_json(text)
            return _to_facts(data, layout)
        except (VisionError, GateError, KeyError, ValueError) as exc:
            last = exc
    raise VisionError("Vision 解析失败: %s" % last)


def _to_facts(data: dict, layout: str) -> DayFacts:
    def grp(name: str):
        g = data.get(name) or {}
        return (to_fen(g.get("open")), to_fen(g.get("in")),
                to_fen(g.get("out")), to_fen(g.get("close")))

    bank = grp("bank")
    bill = grp("bill")
    total = grp("total")
    cash = grp("cash") if layout == "A" else (0, 0, 0, 0)

    return DayFacts(
        report_date=_normalize_date(data.get("report_date", "")),
        layout=layout,
        bank_open=bank[0], bank_in=bank[1], bank_out=bank[2], bank_close=bank[3],
        bill_open=bill[0], bill_in=bill[1], bill_out=bill[2], bill_close=bill[3],
        total_open=total[0], total_in=total[1], total_out=total[2], total_close=total[3],
        cash_open=cash[0], cash_in=cash[1], cash_out=cash[2], cash_close=cash[3],
    )


def read_bill_list(image_path: str, *, scale: int = 1, model: Optional[str] = None) -> dict:
    """读「现存票据」，返回模型给的原始 JSON（交给 bills.parse_read / check_rows）。"""
    key = _api_key()
    src = image_path
    if scale > 1:
        from PIL import Image
        im = Image.open(image_path).convert("RGB")
        im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
        src = image_path + ".x%d.png" % scale
        im.save(src)
    b64 = base64.b64encode(open(src, "rb").read()).decode("ascii")
    payload = {
        "model": model or os.environ.get("DAILY_FUNDS_VISION_MODEL") or DEFAULT_MODEL,
        "temperature": 0,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT_BILLS},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}},
        ]}],
    }
    # 三十行逐张输出比三行汇总慢得多，给足超时
    body = _post(payload, key, timeout=240)
    try:
        return _extract_json(body["choices"][0]["message"]["content"])
    except (KeyError, IndexError, ValueError) as exc:
        raise VisionError("票据表返回解析失败: %s" % type(exc).__name__)
