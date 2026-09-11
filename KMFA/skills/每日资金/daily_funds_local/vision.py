"""用 DeepSeek Vision 把余额表截图读成结构化数字。

三代版式的表头和行结构完全不同，所以按版式分派三套提示词——用一套通用提示词
会在版式 A 上读错列（A 的列名是「收款小计/付款小计/本日余额」，B/C 是
「今日收款/今日支出/今日余额」）。

模型只被要求输出 JSON。读出来的数字随后必须过 gate.check()：硬门不过就丢弃，
所以这里不需要信任模型，只需要它给出可被验伪的答案。
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import os
import re
import time
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


def _normalize_date(raw: str, message_date: Optional[str] = None) -> str:
    """表上多半只写「09月09日」。年份从消息日期推，不写死：一月初发的「12月31日」是上一年的。"""
    raw = (raw or "").strip()
    m = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", raw)
    if m:
        return "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3)))
    m = re.search(r"(\d{1,2})[-/月](\d{1,2})", raw)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        ref = dt.date.fromisoformat(message_date) if message_date else dt.date.today()
        year = ref.year - 1 if month > ref.month + 1 else ref.year
        return "%d-%02d-%02d" % (year, month, day)
    return raw


def read_card(image_path: str, layout: str, *, model: Optional[str] = None,
              retries: int = 1, message_date: Optional[str] = None) -> DayFacts:
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
            return _to_facts(data, layout, message_date)
        except (VisionError, GateError, KeyError, ValueError) as exc:
            last = exc
    raise VisionError("Vision 解析失败: %s" % last)


def _to_facts(data: dict, layout: str, message_date: Optional[str] = None) -> DayFacts:
    def grp(name: str):
        g = data.get(name) or {}
        return (to_fen(g.get("open")), to_fen(g.get("in")),
                to_fen(g.get("out")), to_fen(g.get("close")))

    bank = grp("bank")
    bill = grp("bill")
    total = grp("total")
    cash = grp("cash") if layout == "A" else (0, 0, 0, 0)

    return DayFacts(
        report_date=_normalize_date(data.get("report_date", ""), message_date),
        layout=layout,
        bank_open=bank[0], bank_in=bank[1], bank_out=bank[2], bank_close=bank[3],
        bill_open=bill[0], bill_in=bill[1], bill_out=bill[2], bill_close=bill[3],
        total_open=total[0], total_in=total[1], total_out=total[2], total_close=total[3],
        cash_open=cash[0], cash_in=cash[1], cash_out=cash[2], cash_close=cash[3],
    )


# 长表（实测 40 行以上、图高近 2000 像素）整张送进去每行分到的像素太少，
# 「距离到期日」和到期日会被读错，而且同一字形会反复读错，重试救不了。
# 超过这个高度就改成分段读：每段都带表头，段与段之间留重叠，按序号拼回去。
TALL_BILL_IMAGE_PX = 1500

PROMPT_BILLS_PART = """这是「现存票据」表截图的一段：最上面一行是表头，下面是从整张表里截出来的连续若干行。
列依次是：序号 / 收到票据日期 / 汇票出票日 / 汇票到期日 / 距离到期日 / 收款银行 / 票据类别 / 出票行（承兑行）/ 票据号 / 票据金额 / 客户名。

只输出这一段里**完整可见**的票据行（被截断、看不全的行不要输出），每行读这四样：
- seq：序号
- due：汇票到期日
- days：距离到期日（整数）
- amount：票据金额
如果这一段里有最底部的「合计」行，把那一格印的数字逐位抄进 total；没有就输出空字符串。
绝对不要自己把各行加起来代替合计。

输出：
{"rows":[{"seq":17,"due":"2026-09-24","days":78,"amount":"12345.67"}],"total":""}

规则：
- 只输出 JSON，不要任何解释、不要 markdown 代码围栏。
- 金额去掉「¥」和千分位逗号，保留两位小数的字符串原样输出。
- 日期输出 YYYY-MM-DD。
"""


def bill_read_plan(image_path: str) -> list:
    """每次读图用的 (放大倍数, 分几段)。短表只整张读（实测近 8 周全部一次过）。"""
    try:
        from PIL import Image
        height = Image.open(image_path).size[1]
    except Exception:
        height = 0
    if height > TALL_BILL_IMAGE_PX:
        return [(1, 1), (2, 2), (2, 1), (2, 3)]
    return [(1, 1), (2, 1)]


def _bill_chunks(image_path: str, parts: int, *, header_px: int = 40,
                 overlap_px: int = 90, scale: int = 2) -> list:
    from PIL import Image
    im = Image.open(image_path).convert("RGB")
    w, h = im.size
    step = (h - header_px) / parts
    head = im.crop((0, 0, w, header_px))
    out = []
    for i in range(parts):
        y0 = max(header_px, int(header_px + i * step) - (overlap_px if i else 0))
        y1 = min(h, int(header_px + (i + 1) * step) + (overlap_px if i < parts - 1 else 0))
        canvas = Image.new("RGB", (w, header_px + 6 + (y1 - y0)), "white")
        canvas.paste(head, (0, 0))
        canvas.paste(im.crop((0, y0, w, y1)), (0, header_px + 6))
        canvas = canvas.resize((canvas.width * scale, canvas.height * scale), Image.LANCZOS)
        path = "%s.part%d_of%d.png" % (image_path, i, parts)
        canvas.save(path)
        out.append(path)
    return out


VISION_CALL_TIMEOUT = 240


def _timeout_left(deadline: Optional[float]) -> int:
    """单次调用的超时取「剩余预算」和 240 秒里小的那个。预算见底就不再发起新调用。"""
    if deadline is None:
        return VISION_CALL_TIMEOUT
    left = deadline - time.monotonic()
    if left < 15:
        raise VisionError("BUDGET")
    return int(min(VISION_CALL_TIMEOUT, left))


def _ask(prompt: str, image_path: str, key: str, model: Optional[str],
         deadline: Optional[float] = None) -> dict:
    b64 = base64.b64encode(open(image_path, "rb").read()).decode("ascii")
    payload = {
        "model": model or os.environ.get("DAILY_FUNDS_VISION_MODEL") or DEFAULT_MODEL,
        "temperature": 0,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}},
        ]}],
    }
    # 三十行逐张输出比三行汇总慢得多，给足超时——但不能越过调用方的总预算
    body = _post(payload, key, timeout=_timeout_left(deadline))
    try:
        return _extract_json(body["choices"][0]["message"]["content"])
    except (KeyError, IndexError, ValueError) as exc:
        raise VisionError("票据表返回解析失败: %s" % type(exc).__name__)


def _row_key(row: dict) -> tuple:
    return (re.sub(r"\D", "", str(row.get("due", ""))), str(row.get("days", "")).strip(),
            re.sub(r"[^\d.]", "", str(row.get("amount", ""))))


def read_bill_list(image_path: str, *, scale: int = 1, parts: int = 1,
                   model: Optional[str] = None, deadline: Optional[float] = None) -> dict:
    """读「现存票据」，返回 {"rows": [...], "total": ...}（交给 bills.parse_read / check_rows）。"""
    key = _api_key()
    if parts > 1:
        merged: dict = {}
        total = ""
        conflicts = []
        for chunk in _bill_chunks(image_path, parts, scale=max(scale, 1)):
            data = _ask(PROMPT_BILLS_PART, chunk, key, model, deadline)
            for row in data.get("rows") or []:
                try:
                    seq = int(str(row.get("seq")).strip())
                except (TypeError, ValueError):
                    continue          # 序号读不出的行丢掉，序号连续性闸门会拦下
                if seq in merged and _row_key(merged[seq]) != _row_key(row):
                    conflicts.append(seq)
                merged.setdefault(seq, row)
            if str(data.get("total") or "").strip():
                total = data["total"]
        # 重叠区同一行两段读得不一样，说明至少一段读错了——不猜哪段对，整次作废重读
        if conflicts:
            raise VisionError("分段读的重叠行对不上: %s" % sorted(set(conflicts))[:6])
        return {"rows": [merged[k] for k in sorted(merged)], "total": total}
    src = image_path
    if scale > 1:
        from PIL import Image
        im = Image.open(image_path).convert("RGB")
        im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
        src = image_path + ".x%d.png" % scale
        im.save(src)
    return _ask(PROMPT_BILLS, src, key, model, deadline)
