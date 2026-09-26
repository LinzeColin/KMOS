"""招标公告限价抽取器（仅 Python 3 标准库，离线可跑）。

主入口：
    抽限价(原文: str) -> list[dict]
每个 dict：
    标段     str|None   标段/包号，统一成阿拉伯数字字符串（"1"、"2"、"A"）；无标段为 None
    限价元   float|None 统一成"元"；"详见招标文件"类为 None
    含税     True/False/None   原文说明含税/不含税；未说明为 None
    类型     "最高限价" | "预算(代限价)" | "单价限价" | "详见文件"
    单位     "元" 或 "元/吨" 等（单价时）
    依据     命中的关键词
    片段     原文中该金额附近的文字（便于人工核对）
    存疑     list[str]  例如 ["无单位,按元计"]

规则：公告里只要出现"最高限价/控制价/拦标价"等，就只返回这类；
一个都没有时，才用"预算金额/采购预算"代替，类型标"预算(代限价)"。
通用函数 抽金额(原文, 关键词表) 也给 C2 用来抽中标价。
"""
from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------- 关键词
限价词 = ["最高投标限价", "最高限价", "招标控制价", "投标控制价", "采购控制价", "控制价", "拦标价", "最高报价", "最高投标价", "限价", "上限价", "封顶价"]
预算词 = ["采购预算金额", "项目预算金额", "采购预算", "预算金额", "项目预算", "预算价", "预算", "估算金额", "估算价"]
单价词 = ["单价最高限价", "最高单价", "综合单价", "单价限价", "单价"]
# 干扰金额：出现在它们后面的金额一律不是限价
干扰词 = ["投标保证金", "履约保证金", "保证金", "注册资本", "注册资金", "业绩", "合同金额", "服务费", "代理费", "文件售价", "标书费", "售价", "资产总额", "净资产", "营业收入", "中标价", "中标金额", "成交金额", "投标报价", "报价", "罚款", "违约金", "赔偿", "工程款", "保险"]
详见式 = r"(?:详见|见)(?:招标|采购|谈判|磋商|询价|比选|竞争性)?(?:文件|附件|公告附件|清单)|另行(?:公布|通知|发布)|开标(?:前|时)(?:公布|宣读)|不(?:予)?公开|暂不公布|以.{0,6}为准"

标段名 = r"(?:标段|标包|包件|分包|子包|包号|批次|包|标)"
_中数 = "一二三四五六七八九十"
_罗马式 = r"(?:VIII|VII|VI|IV|IX|III|II|I|V|X)"
标段式 = re.compile(
    r"(?:第\s*([%s\d]{1,3}|%s|[A-Za-z])\s*%s)"  # 第一标段 / 第1包
    r"|(?:(?<![%s\dA-Za-z])([%s\d]{1,3}|%s|[A-Za-z])\s*(?:号)?%s(?![件]?[的内外]))"  # 一标段 / 1包 / A包 / II标段
    r"|(?:%s\s*[:：]?\s*(0?\d{1,2}|[%s]{1,3}|%s(?![A-Za-z])|[A-Za-z](?![A-Za-z]))(?![\d\.万元]))"  # 标段一 / 包1 / 包号：01
    % (_中数, _罗马式, 标段名, _中数, _中数, _罗马式, 标段名, 标段名, _中数, _罗马式)
)
_罗马 = {"Ⅰ": "1", "Ⅱ": "2", "Ⅲ": "3", "Ⅳ": "4", "Ⅴ": "5", "Ⅵ": "6", "Ⅶ": "7", "Ⅷ": "8", "Ⅸ": "9", "Ⅹ": "10"}

# ---------------------------------------------------------------- 数字
_大写数 = {"零": 0, "〇": 0, "○": 0, "壹": 1, "一": 1, "贰": 2, "貳": 2, "二": 2, "两": 2, "叁": 3, "參": 3, "三": 3, "肆": 4, "四": 4,
          "伍": 5, "五": 5, "陆": 6, "陸": 6, "六": 6, "柒": 7, "七": 7, "捌": 8, "八": 8, "玖": 9, "九": 9}
_小位 = {"拾": 10, "十": 10, "佰": 100, "百": 100, "仟": 1000, "千": 1000}
_大位 = {"万": 10 ** 4, "萬": 10 ** 4, "亿": 10 ** 8, "億": 10 ** 8}
_大写字 = "".join(_大写数) + "".join(_小位) + "".join(_大位)
大写式 = re.compile(r"[%s]{2,}(?:元|圆)(?:[%s]角)?(?:[%s]分)?(?:整|正)?" % (_大写字, "".join(_大写数), "".join(_大写数)))
# 阿拉伯数字：1,234,567.89 / 1234567.89 / 120.5，后接可选单位
数字式 = re.compile(r"(?<![\d.,A-Za-z_])(?:RMB|CNY)?\s*[¥￥]?\s*(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(亿元|万元|千元|百万元|元|万|亿)?(\s*/\s*[一-龥a-zA-Z²³]{1,4})?")


def 中文数(s: str) -> int:
    """'壹佰贰拾万' → 1200000；'十二' → 12。"""
    总, 节, 位数 = 0, 0, 0
    for ch in s:
        if ch in _大写数:
            位数 = _大写数[ch]
        elif ch in _小位:
            节 += (位数 or 1) * _小位[ch]
            位数 = 0
        elif ch in _大位:
            节 += 位数
            总 = (总 + 节) * _大位[ch] if _大位[ch] > 10 ** 4 else 总 + 节 * _大位[ch]
            节, 位数 = 0, 0
    return 总 + 节 + 位数


def 大写转数(s: str) -> float:
    s = s.rstrip("整正")
    m = re.match(r"(.*?)(?:元|圆)(?:(.)角)?(?:(.)分)?$", s)
    if not m:
        return float(中文数(s))
    值 = float(中文数(m.group(1)))
    if m.group(2):
        值 += _大写数.get(m.group(2), 0) / 10
    if m.group(3):
        值 += _大写数.get(m.group(3), 0) / 100
    return 值


def 规整(文本: str) -> str:
    """全角转半角、统一符号，保留原有长度无关性（后续用规整后的文本定位）。"""
    t = unicodedata.normalize("NFKC", 文本)
    t = t.replace("，", ",").replace("：", ":").replace("（", "(").replace("）", ")")
    # 千分位里的中文逗号已转半角；去掉数字内部空格 "1 200 000"
    t = re.sub(r"(?<=\d) (?=\d{3}\b)", "", t)
    return t


_单位倍数 = {"元": 1, "千元": 1e3, "万元": 1e4, "万": 1e4, "百万元": 1e6, "亿元": 1e8, "亿": 1e8}


def _标段规整(tok: str) -> str:
    tok = tok.strip()
    if tok in _罗马:
        return _罗马[tok]
    if re.fullmatch(_罗马式, tok):
        return str({"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}[tok])
    if tok.isdigit():
        return str(int(tok))
    if all(c in _大写数 or c in "十" for c in tok):
        return str(中文数(tok))
    return tok.upper()


def _找标段(t: str, pos: int, 回看: int = 120) -> str | None:
    起 = max(0, pos - 回看)
    最近 = None
    for m in 标段式.finditer(t, 起, pos):
        tok = m.group(1) or m.group(2) or m.group(3)
        if tok:
            最近 = _标段规整(tok)
    return 最近


_税式 = re.compile(r"不含税|不含增值税|未含税|税前|除税|含税|含增值税|含\d{1,2}%\s*(?:增值税|税)|含\d{1,2}%税率|包含.{0,6}税")


def _判税(t: str, 窗起: int, 起: int, 止: int) -> bool | None:
    """税口径：①关键词及其与金额之间（含关键词前 6 字）②金额后紧跟的括号或到下一个逗号为止 ③关键词前 15 字。"""
    def 判(m):
        return not re.match(r"不含|未含|税前|除税", m.group())

    前 = list(_税式.finditer(t, max(0, 窗起 - 6), 起))
    if 前:
        return 判(前[-1])
    后文 = t[止: 止 + 30]
    k = re.match(r"\s*(?:元|万元)?\s*\(([^)]{0,28})\)", 后文)
    后段 = k.group(0) if k else re.split(r"[,;。\n]", 后文, maxsplit=1)[0]
    m = _税式.search(后段)
    if m:
        return 判(m)
    前 = list(_税式.finditer(t, max(0, 窗起 - 15), 起))
    if 前:
        return 判(前[-1])
    # ④ 同一句剩余部分若不再出现别的金额，句内的"为含税价/含6%增值税"也算
    句 = re.split(r"[。\n]", t[止: 止 + 60], maxsplit=1)[0]
    if not re.search(r"\d[\d,.]*\s*(?:亿元|万元|元)|" + 大写式.pattern, 句):
        m = _税式.search(句)
        if m:
            return 判(m)
    return None


def _表头单位(t: str, 左: int, 右: int) -> float | None:
    段 = t[左:右]
    m = re.search(r"(?:单位\s*:?\s*|\(|\[)\s*(万元|元|亿元|千元)\s*[\)\]]?", 段)
    return _单位倍数[m.group(1)] if m else None


_分项起 = re.compile(r"其中|内含|包括|包含(?!税|增值税)|含(?!税|增值税|\d{1,2}%)")


def _是分项(t: str, 词止: int, 起: int) -> bool:
    """金额是否是限价的组成部分（暂列金、安全文明施工费、设备费…），而不是限价本身。
    ① 位于未闭合括号内，且括号内容以 其中/含/包括 开头；② 关键词与金额之间出现"其中"且其后没有标段标记。"""
    间 = t[词止:起]
    左 = 间.rfind("(")
    if 左 > 间.rfind(")") and _分项起.match(间[左 + 1:].lstrip()):
        return True
    k = 间.rfind("其中")
    if k >= 0 and not 标段式.search(间[k:]):
        return True
    return False


def _所有关键词(词表组: dict[str, list[str]]):
    项 = []
    for 类, 词表 in 词表组.items():
        for w in 词表:
            项.append((w, 类))
    项.sort(key=lambda x: -len(x[0]))  # 长词优先
    return re.compile("|".join(re.escape(w) for w, _ in 项)), {w: 类 for w, 类 in 项}


def _金额列表(t: str):
    """找出所有金额：(起, 止, 值元或None, 单位后缀, 是大写, 原单位)"""
    结果 = []
    for m in 大写式.finditer(t):
        结果.append([m.start(), m.end(), 大写转数(m.group()), "", True, "元"])
    for m in 数字式.finditer(t):
        数, 单位, 斜杠 = m.group(1), m.group(2), m.group(3)
        # 排除日期、电话、编号、百分比、年份
        尾 = t[m.end(): m.end() + 2]
        if 尾.startswith(("%", "％", "年", "月", "日", "天", "个", "人", "号", "-", "吨", "台", "套", "米", "㎡", "项", "次", "家", "名", "小时", "期", "标", "包", "批", "条", "份", "章", "节", "款")) and not 单位:
            continue
        if re.match(r"[.\-/]\d", 尾) and not 单位:  # 2025.10.08 / 2025-10 这类日期续接
            continue
        前 = t[max(0, m.start() - 1): m.start()]
        if 前 in ("-", "/", ".", "第") or (前.isalpha() and 前.isascii()):
            continue
        原 = 数.replace(",", "")
        if not 单位 and not 斜杠 and "," not in 数 and "." not in 数 and len(原) >= 11:
            continue  # 很可能是电话/编号
        值 = float(原)
        if not 单位 and re.search(r"RMB|CNY|[¥￥]", m.group(0)):
            单位 = "元"  # 货币符号本身就说明是元
        结果.append([m.start(), m.end(), 值, (斜杠 or "").replace(" ", ""), False, 单位 or ""])
    结果.sort(key=lambda x: x[0])
    return 结果


def 抽金额(原文: str, 目标: dict[str, list[str]], 窗口: int = 60) -> list[dict]:
    """通用金额抽取。目标 = {"类型名": [关键词...]}；干扰词会自动加入以挡住误配。

    每个金额归属于它前方最近的关键词（窗口内、不跨句号/换行）。
    """
    t = 规整(原文)
    组 = dict(目标)
    组["_干扰"] = [w for w in 干扰词 if not any(w in ws for ws in 目标.values())]
    词式, 词类 = _所有关键词(组)
    词位 = [(m.start(), m.end(), 词类[m.group()], m.group()) for m in 词式.finditer(t)]
    金额 = _金额列表(t)
    输出: list[dict] = []
    已用大写 = []

    for 起, 止, 值, 斜杠, 是大写, 单位 in 金额:
        # 最近的前置关键词
        前词 = None
        for w in reversed(词位):
            if w[1] <= 起:
                if 起 - w[1] <= 窗口 and not re.search(r"[。\n]", t[w[1]:起]):
                    前词 = w
                break
        if not 前词 or 前词[2] == "_干扰":
            continue
        if _是分项(t, 前词[1], 起):
            continue
        # 前词与金额之间若夹着另一个金额且中间有标点分隔，仍允许（多标段 "限价:一标段100万;二标段80万"）
        存疑 = []
        if not 是大写:
            倍 = _单位倍数.get(单位) if 单位 else _表头单位(t, 前词[0], 起 + 1) or _表头单位(t, 前词[1], 前词[1] + 12)
            if 倍 is None:
                后 = t[止: 止 + 3]
                if 后.startswith("元"):
                    倍 = 1
                else:
                    倍 = 1
                    存疑.append("无单位,按元计")
            值元 = round(值 * 倍, 2)
        else:
            值元 = round(值, 2)
        类型 = 前词[2]
        单位名 = "元"
        if 斜杠:
            类型 = "单价限价" if 类型 in ("最高限价", "单价限价") else 类型
            单位名 = "元" + 斜杠 if not 单位 or 单位 == "元" else 单位 + 斜杠
        输出.append({
            "标段": _找标段(t, 起),
            "限价元": 值元,
            "含税": _判税(t, 前词[0], 起, 止),
            "类型": 类型,
            "单位": 单位名,
            "依据": 前词[3],
            "片段": t[max(0, 前词[0] - 10): min(len(t), 止 + 15)],
            "存疑": 存疑,
            "_pos": 起,
            "_大写": 是大写,
        })
        if 是大写:
            已用大写.append(len(输出) - 1)

    # 详见文件：关键词后紧跟"详见招标文件"之类
    for w in 词位:
        if w[2] in ("_干扰",):
            continue
        后 = t[w[1]: w[1] + 25]
        if re.match(r"\s*(?:为|是|:)?\s*(?:将)?(?:在|于)?\s*(?:" + 详见式 + ")", 后):
            输出.append({"标段": _找标段(t, w[0]), "限价元": None, "含税": None, "类型": "详见文件", "单位": "", "依据": w[3],
                       "片段": t[max(0, w[0] - 10): w[1] + 25], "存疑": [], "_pos": w[0], "_大写": False, "_源类": w[2]})

    输出 += _表格(t, 目标)
    return _去重(输出)


def _表格(t: str, 目标: dict[str, list[str]]) -> list[dict]:
    """识别 `| a | b |` 行格式的表格（网页文本.py 输出）。"""
    行们 = t.split("\n")
    结果 = []
    偏移 = 0
    位置 = []
    for 行 in 行们:
        位置.append(偏移)
        偏移 += len(行) + 1
    i = 0
    while i < len(行们):
        行 = 行们[i].strip()
        if not (行.startswith("|") and 行.endswith("|")):
            i += 1
            continue
        头 = [c.strip() for c in 行.strip("|").split("|")]
        列, 类 = None, None
        for 类名, 词表 in 目标.items():
            for j, c in enumerate(头):
                if any(w in c for w in 词表) and not any(g in c for g in ("保证金",)):
                    列, 类 = j, 类名
                    break
            if 列 is not None:
                break
        if 列 is None:
            i += 1
            continue
        头单位 = re.search(r"(万元|亿元|千元|元)", 头[列])
        倍 = _单位倍数[头单位.group(1)] if 头单位 else None
        头税 = None
        if re.search(r"不含税|不含增值税", 头[列]):
            头税 = False
        elif re.search(r"含税|含增值税", 头[列]):
            头税 = True
        段列 = next((j for j, c in enumerate(头) if re.search(r"标段|包号|标包|分包|包件|包名|序号|批次", c)), None)
        j = i + 1
        while j < len(行们) and 行们[j].strip().startswith("|"):
            格 = [c.strip() for c in 行们[j].strip().strip("|").split("|")]
            if len(格) == len(头) and 列 < len(格):
                c = 规整(格[列])
                m = 大写式.search(c)
                if m:
                    值 = 大写转数(m.group())
                else:
                    n = re.search(r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(亿元|万元|千元|元|万)?", c)
                    值 = None
                    if n:
                        值 = float(n.group(1).replace(",", "")) * (_单位倍数[n.group(2)] if n.group(2) else (倍 or 1))
                段 = None
                if 段列 is not None:
                    s = _找标段(格[段列] + " ", len(格[段列]) + 1) if 标段式.search(格[段列]) else None
                    if s is None and re.fullmatch(r"0?\d{1,2}|[A-Z]", 格[段列].strip()):
                        s = _标段规整(格[段列].strip())
                    段 = s
                if 值 is not None:
                    结果.append({"标段": 段, "限价元": round(值, 2), "含税": 头税 if 头税 is not None else _判税(t, 位置[j], 位置[j], 位置[j] + len(行们[j])),
                               "类型": 类, "单位": "元", "依据": "表格:" + 头[列], "片段": 行们[j][:200],
                               "存疑": [] if (头单位 or (n and n.group(2)) or m) else ["表格无单位,按元计"], "_pos": 位置[j], "_大写": bool(m)})
                elif re.search(详见式, c):
                    结果.append({"标段": 段, "限价元": None, "含税": None, "类型": "详见文件", "单位": "", "依据": "表格:" + 头[列],
                               "片段": 行们[j][:200], "存疑": [], "_pos": 位置[j], "_大写": False, "_源类": 类})
            j += 1
        i = j
    return 结果


def _去重(项: list[dict]) -> list[dict]:
    """同一标段、同值、同税口径只留一条；大写与阿拉伯并写（值相同、相距近）合并。"""
    项 = sorted(项, key=lambda x: x["_pos"])
    留 = []
    for x in 项:
        重复 = False
        for y in 留:
            if x["类型"] == "详见文件" and y["类型"] == "详见文件" and x["标段"] == y["标段"]:
                重复 = True
                break
            if x["类型"] == y["类型"] and x["限价元"] is not None and y["限价元"] is not None and abs(x["限价元"] - y["限价元"]) < 0.005:
                同段 = x["标段"] == y["标段"] or x["标段"] is None or y["标段"] is None
                同税 = x["含税"] == y["含税"] or x["含税"] is None or y["含税"] is None
                if 同段 and 同税:
                    y["标段"] = y["标段"] or x["标段"]
                    y["含税"] = y["含税"] if y["含税"] is not None else x["含税"]
                    重复 = True
                    break
        if not 重复:
            留.append(x)
    return 留


def 抽限价(原文: str) -> list[dict]:
    """返回公告的限价列表（见模块说明）。"""
    全部 = 抽金额(原文, {"最高限价": 限价词, "预算(代限价)": 预算词, "单价限价": 单价词})
    # 某标段已有真实金额，就不再保留它的"详见文件"
    有值段 = {x["标段"] for x in 全部 if x["限价元"] is not None and x["类型"] != "预算(代限价)"}
    限价 = [x for x in 全部 if x["类型"] in ("最高限价", "单价限价") or (x["类型"] == "详见文件" and x.get("_源类") in ("最高限价", "单价限价"))]
    限价 = [x for x in 限价 if not (x["类型"] == "详见文件" and x["标段"] in 有值段)]
    if not any(x["限价元"] is not None for x in 限价):
        预算 = [x for x in 全部 if x["类型"] == "预算(代限价)"]
        if 预算:
            限价 = [x for x in 限价 if x["类型"] == "详见文件"] + 预算
        # 只有预算的"详见文件"也返回
        if not 限价:
            限价 = [dict(x, 类型="详见文件") for x in 全部 if x["类型"] == "详见文件"]
    # 若同时有总价限价，单价限价也保留（题目要求区分单价与总价）
    for x in 限价:
        x.pop("_pos", None)
        x.pop("_大写", None)
        x.pop("_源类", None)
    return 限价


if __name__ == "__main__":
    import json
    import sys

    文本 = sys.stdin.read()
    print(json.dumps(抽限价(文本), ensure_ascii=False, indent=1))
