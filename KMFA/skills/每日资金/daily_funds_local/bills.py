"""「现存票据」→ 卡片上的「14 天内到期承兑」。

资金账户明细表里电子汇票只有分公司合计，没有到期日；到期信息只在杨婷每周一
发到付款请示群的「现存票据」逐张台账里。这是唯一的源。

表自己带三道校验位，读错任何一处当场崩，所以读图不需要被信任：
1. 序号连续——漏行、重行过不去。
2. 逐张求和 == 表内合计——金额读错一位过不去。
3. 「距离到期日」列是财务按 DAYS360（每月当 30 天）算的，全表共用同一个基准日。
   反推出一个基准日让每一行都对上；到期日读错一行就对不上。
   实测 09-07 表 28/28 与 DAYS360 吻合，与自然日 16/28 不符——所以卡片上的天数
   必须按到期日自己算自然日，不能用这一列。

外加跨源一道：表内合计 ≈ 基准日前 CROSS_LOOKBACK_DAYS 天内某一天的电子汇票
（资金账户明细表），容差 1 元。**这一道必须是硬门**：实测模型会自己把读出来的
各行加起来当「合计」输出，而不是去读图上印的那一格——那样逐张求和永远自洽，
单行读错就溜过去了。5 月到 7 月的回放里，差额全是「错一两个数字」的形状，只有拿另一张独立的表来比才抓得住。

卡片上的数按报表日逐日滚动：已到期剔除，窗口 0 ≤ 到期日−报表日 ≤ 14，
不等下一张表。表超过 MAX_LIST_AGE_DAYS 没换新就不给数，由调用方首报告警。
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence, Tuple

from .gate import GateError, to_fen

LABELS = ("现存票据", "票据明细", "承兑明细")  # 与 KMFA 日常检查 PAY_MON_EXISTING_BILLS 同一组词
WINDOW_DAYS = 14
MAX_LIST_AGE_DAYS = 10      # 周一发表，到下周四是 10 天；周五起算断供
REF_SEARCH_DAYS = 7         # 基准日在发表日往前一周内找
CROSS_LOOKBACK_DAYS = 4     # 表反映发表前最后一个工作日的收盘；跨周末最多往前 3 天，留 1 天余量
CROSS_TOLERANCE_FEN = 100   # 1 元。两张表各自按显示值求和，实测最大残差 0.20 元
_MEDIA = re.compile(r"mediaId=@([A-Za-z0-9_\-]+)")


def _amount(raw) -> int:
    """票据金额单元格带「¥」和空格，先剥掉再按整数分解析。"""
    return to_fen(re.sub(r"[¥￥\s]", "", str(raw if raw is not None else "")))


def _date(raw) -> dt.date:
    m = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", str(raw or ""))
    if not m:
        raise ValueError("日期读不出: %r" % (raw,))
    return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _last_day_of_february(d: dt.date) -> bool:
    return d.month == 2 and (d + dt.timedelta(days=1)).month == 3


def days360(a: dt.date, b: dt.date) -> int:
    """Excel DAYS360(start, end, FALSE)（美国法），财务表「距离到期日」的口径。

    起始日是月末（31 日，或二月最后一天）按 30 日算；结束日是 31 日且起始日已按 30 日算时，结束日也按 30 日算。
    Excel 的实际实现不对结束日套用「二月月末」规则：
    DAYS360(2011-02-28, 2011-03-31) = 30，DAYS360(2011-01-30, 2011-02-28) = 28。
    """
    ad = 30 if (a.day == 31 or _last_day_of_february(a)) else a.day
    bd = 30 if (b.day == 31 and ad >= 30) else b.day
    return (b.year - a.year) * 360 + (b.month - a.month) * 30 + (bd - ad)


@dataclass
class ListCheck:
    ok: bool
    bills: List[Tuple[str, int]]          # (到期日 ISO, 金额分)
    total_fen: int
    ref_date: Optional[str]
    reasons: List[str] = field(default_factory=list)


def parse_read(data: dict):
    """把 Vision 返回的原始 JSON 解成行。解不出的行记下来，由闸门判失败。"""
    rows, errors = [], []
    for raw in data.get("rows") or []:
        try:
            days_txt = str(raw.get("days", "")).strip()
            rows.append({"seq": int(str(raw.get("seq")).strip()),
                         "due": _date(raw.get("due")),
                         "days": int(days_txt) if re.fullmatch(r"-?\d+", days_txt) else None,
                         "amount_fen": _amount(raw.get("amount"))})
        except (ValueError, TypeError, AttributeError, GateError):
            errors.append(str(raw)[:80])
    try:
        total = _amount(data.get("total"))
    except GateError:
        total, errors = -1, errors + ["TOTAL:%r" % (data.get("total"),)]
    return rows, total, errors


def fit_reference(rows: Sequence[dict], posted: dt.date) -> Optional[dt.date]:
    for k in range(REF_SEARCH_DAYS + 1):
        r0 = posted - dt.timedelta(days=k)
        if rows and all(r["days"] is not None and days360(r0, r["due"]) == r["days"] for r in rows):
            return r0
    return None


def check_rows(rows: Sequence[dict], total_fen: int, posted: dt.date,
               parse_errors: Sequence[str] = ()) -> ListCheck:
    reasons = ["ROW_PARSE:%s" % e for e in parse_errors]
    if not rows:
        reasons.append("EMPTY")
    seqs = [r["seq"] for r in rows]
    if seqs != list(range(1, len(rows) + 1)):
        reasons.append("SEQ:%s" % seqs[:40])
    if any(r["amount_fen"] <= 0 for r in rows):
        reasons.append("NONPOSITIVE_AMOUNT")
    s = sum(r["amount_fen"] for r in rows)
    if s != total_fen:
        reasons.append("SUM:%d!=%d" % (s, total_fen))
    if any(r["days"] is None for r in rows):
        reasons.append("DAYS_MISSING")
    ref = fit_reference(rows, posted)
    if rows and ref is None:
        reasons.append("DAYS360_NO_COMMON_REF")
    return ListCheck(ok=not reasons, bills=[(r["due"].isoformat(), r["amount_fen"]) for r in rows],
                     total_fen=total_fen, ref_date=ref.isoformat() if ref else None, reasons=reasons)


def same_reading(a: ListCheck, b: ListCheck) -> bool:
    """两次独立读出来逐行一致。只核总额挡不住「两行金额读串位、互相抵消」：
    合计、资金表都对得上，但到期日和金额的对应关系错了，14 天窗口就算错。"""
    return (a.ok and b.ok and a.bills == b.bills and a.total_fen == b.total_fen
            and a.ref_date == b.ref_date)


def cross_window(ref_date: str) -> Tuple[str, str]:
    d = dt.date.fromisoformat(ref_date)
    return (d - dt.timedelta(days=CROSS_LOOKBACK_DAYS)).isoformat(), ref_date


def cross_match(total_fen: int, balances: Sequence[Tuple[str, int]]) -> Optional[str]:
    """balances = 窗口内的 [(报表日, 汇票分)]。返回对上的最晚那天；一天都对不上返回 None。"""
    for day, bill in sorted(balances, reverse=True):
        if abs(bill - total_fen) <= CROSS_TOLERANCE_FEN:
            return day
    return None


def due_within(bills: Sequence[Tuple[str, int]], report_date: str, window: int = WINDOW_DAYS) -> int:
    d0 = dt.date.fromisoformat(report_date)
    return sum(a for due, a in bills if 0 <= (dt.date.fromisoformat(due) - d0).days <= window)


def pick(lists: Sequence[dict], report_date: str) -> Optional[dict]:
    """报表日能用的最新一张。不拿未来的表算过去：它对上的资金表日期不晚于报表日，
    发表日期不晚于报表日次日（周一中午发的表，对的是周日的报表）。"""
    limit = (dt.date.fromisoformat(report_date) + dt.timedelta(days=1)).isoformat()
    ok = [x for x in lists if x["as_of"] <= report_date and x["posted_at"][:10] <= limit]
    return max(ok, key=lambda x: x["posted_at"]) if ok else None


def card_fields(lists: Sequence[dict], report_date: str, bill_fen: int):
    """返回 (payload 片段, 状态, 用到的表)。状态：ok / none / stale / inconsistent。"""
    chosen = pick(lists, report_date)
    if chosen is None:
        return {}, "none", None
    age = (dt.date.fromisoformat(report_date) - dt.date.fromisoformat(chosen["posted_at"][:10])).days
    if age > MAX_LIST_AGE_DAYS:
        return {}, "stale", chosen
    fen = due_within(chosen["bills"], report_date)
    if fen > bill_fen:
        return {}, "inconsistent", chosen
    return {"bill_due14": fen, "bill_due14_src": chosen["posted_at"][:10]}, "ok", chosen


def find_list_messages(run: Callable[[list], dict], group_id: str, since: str, start: str,
                       max_pages: int = 10) -> List[dict]:
    """从 start 往前翻群消息到 since，挑出带「现存票据」类标签且带图的消息。

    不按发送人、不按星期几过滤：实测 06-04（周四）、07-21（周二）发的都是真表且与资金表对上。
    来源是否可信由闸门决定——DAYS360 基准日必须落在发表前一周内、合计必须对上独立的资金表、
    两次读法必须逐行一致。能全部通过的，就是当期那张表，与是谁转发的无关。
    """
    seen, t = {}, start
    for _ in range(max_pages):
        body = run(["chat", "message", "list", "--group", group_id, "--time", t,
                    "--direction", "older", "--limit", "100"])
        msgs = (body.get("result") or {}).get("messages") or []
        fresh = [m for m in msgs if m.get("openMessageId") not in seen]
        for m in fresh:
            seen[m["openMessageId"]] = m
        if not fresh:
            break
        oldest = min(m.get("createTime", "") for m in msgs)
        if oldest < since:
            break
        t = oldest
    out = []
    for m in seen.values():
        content = m.get("content") or ""
        hit = _MEDIA.search(content)
        if m.get("createTime", "") >= since and hit and any(k in content for k in LABELS):
            out.append({"media": hit.group(1), "posted_at": m.get("createTime", ""),
                        "sender": m.get("sender", "")})
    return sorted(out, key=lambda x: x["posted_at"])
