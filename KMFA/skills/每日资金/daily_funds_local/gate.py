"""两级闸门——本方案敢用 Vision OCR 的全部依据。

**硬门**（不过就丢弃该天）：表内部必须自洽。
    银行存款 + 电子汇票 (+ 库存现金，仅版式 A) ≈ 总计
读错任何一位，这个等式当场崩，所以 OCR 不需要被信任，它必须自证。

「≈」不是放水。源表的小计行是对**显示值**（已四舍五入）求和，所以合计与
分项之和天然会差几分——实测 0.02 / 0.10 / 0.20 / 0.21 元。要求分毫不差会
因为 2 分钱扔掉一整天的真数据。而卡片显示到万元后两位 = 100 元分辨率，
1 元容差比显示精度还低两个数量级；真正的单字误读实测是 600 元起跳。

**软门**分两个互不替代的信号，混成一个会把两类完全不同的问题报成同一件事：

``flow_ok``  昨日余额 + 今日收款 − 今日支出 == 今日余额（一天之内）
    不过 → ``source_imbalance``：**源表自己的 SUM 有问题**。实测 2026-04-27
    那天「合计」行漏了一家公司（差额恰好等于它当天的收入减支出），余额列对、
    收支列错。这是财务的 Excel 公式 bug，不是 OCR 错，丢弃它就是丢真数据。

``chain_ok``  本日的昨日余额 ≈ 前一有效日的今日余额（跨天，带量级门槛）
    不过 → ``chain_suspect``：这一天的读数可疑，值得重读。

    门槛不能设成零。实测 09-02 的表上白纸黑字印的昨日余额，与 09-01 的收盘
    差几块钱——**这个差额是源表自己的**：财务改了前一天
    的数但没有重述。手工表里这很常见，20 天里观察到 8 次，最大一千多元。

    但同一道校验抓到了模型把整列一致读错 600,000 的那次：四列自洽、硬门放行，
    只有跨日链能发现。所以它必须保留，只是要按量级区分——单个数字读错至少
    改变一个数量级，和几十上千的人工微调不在一个尺度上。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import List, Optional

CASH_LAYOUT = "A"  # 只有版式 A 有「库存现金」这一类

# 分项之和与合计的容差。源表小计是对显示值求和，天然有几分残差。
# 实测残差 ≤0.21 元，最小的真误读是 600 元——中间有三个数量级的安全带。
COMPOSITION_TOLERANCE_FEN = 100   # 1.00 元


class GateError(ValueError):
    pass


def to_fen(value) -> int:
    """金额一律整数分。'–'/'-'/空 当 0。绝不用 float。"""
    if value is None:
        return 0
    if isinstance(value, int) and not isinstance(value, bool):
        return value  # 调用方已折算成分
    text = str(value).strip().replace(",", "").replace("，", "")
    text = text.replace("–", "").replace("—", "").replace("−", "-")
    if text in {"", "-", "0.00-"}:
        return 0
    try:
        return int((Decimal(text) * 100).to_integral_value())
    except (InvalidOperation, ValueError):
        raise GateError("金额无法解析: %r" % (value,))


@dataclass
class DayFacts:
    """一天从图里读出来的事实。金额全部是整数分。"""
    report_date: str          # 图内日期 YYYY-MM-DD（不是消息日期）
    layout: str
    bank_open: int
    bank_in: int
    bank_out: int
    bank_close: int
    bill_open: int
    bill_in: int
    bill_out: int
    bill_close: int
    total_open: int
    total_in: int
    total_out: int
    total_close: int
    # 仅版式 A 有「库存现金」，其余版式恒为 0
    cash_open: int = 0
    cash_in: int = 0
    cash_out: int = 0
    cash_close: int = 0


@dataclass
class GateResult:
    passed_hard: bool
    flow_ok: bool
    chain_ok: bool
    reasons: List[str] = field(default_factory=list)

    @property
    def passed_soft(self) -> bool:
        return self.flow_ok and self.chain_ok

    @property
    def source_imbalance(self) -> bool:
        """源表自己的 SUM 对不平（04-27 那类）。余额可信，只是流水不闭合。"""
        return self.passed_hard and not self.flow_ok

    @property
    def chain_suspect(self) -> bool:
        """跨日差额**超过量级门槛**——这一天的读数可疑，值得重读。

        门槛内的小差额是源表人工微调（实测最大一千多元），不算问题；
        门槛外的才是读错（实测抓到过 600,000）。详见模块头。
        """
        return self.passed_hard and not self.chain_ok


# 跨日差额低于此值当作源表人工微调，不判可疑。
# 实测依据：20 天里 8 次微调，最大一千多元；而单字误读最小也是千位级起跳。
CHAIN_TOLERANCE_FEN = 200_000   # 2,000.00 元


def check(facts: DayFacts, prev_close: Optional[int] = None,
          prev_date: Optional[str] = None) -> GateResult:
    """prev_close 是**上一有效日的 银行+汇票**（与 storable_total 同口径），
    不是表上的「总计」——版式 A 的总计含库存现金，混用会误报。

    prev_date 给了才做跨日链校验，且只在两日相隔 ≤4 天时做：
    序列有断档（周末、缺采、硬门丢弃）时链条本来就接不上，
    那是缺数据，不是数据错。
    """
    reasons: List[str] = []

    # ---- 硬门 ----
    hard = True
    for name in ("bank_close", "bill_close", "total_close"):
        if getattr(facts, name) < 0:
            reasons.append("HARD_NEGATIVE:%s" % name)
            hard = False

    # 非退化：组成校验在零点是尺度不变的——全零读数天然满足 0+0==0，会一路过关。
    # 实测 2026-03-27 就这么进了库：模型把收盘列整列读空，硬门放行，
    # 走势图上凭空多出一个 0 的谷底。
    # 单条子线为 0 是可能的（某公司可以不持汇票），但一个多公司集团的**合计**
    # 为 0 不是可信读数，那是「模型什么都没读到」的样子。所以只卡合计。
    for name in ("total_open", "total_close"):
        if getattr(facts, name) <= 0:
            reasons.append("HARD_DEGENERATE:%s" % name)
            hard = False

    # 四列全查，不只查「今日余额」。
    # 实测：只查收盘列时，「昨日余额」列里的单字误读（十万位的 6 读成 0）
    # 会溜过硬门，然后以软门失败的形式冒出来——那会把 OCR 错
    # 误报成「源表对不平」，正好是最容易误导人的一种错。
    has_cash = facts.layout == CASH_LAYOUT
    for col, bank, bill, cash, total in (
        ("OPEN", facts.bank_open, facts.bill_open, facts.cash_open, facts.total_open),
        ("IN", facts.bank_in, facts.bill_in, facts.cash_in, facts.total_in),
        ("OUT", facts.bank_out, facts.bill_out, facts.cash_out, facts.total_out),
        ("CLOSE", facts.bank_close, facts.bill_close, facts.cash_close, facts.total_close),
    ):
        composed = bank + bill + (cash if has_cash else 0)
        drift = composed - total
        if abs(drift) > COMPOSITION_TOLERANCE_FEN:
            reasons.append("HARD_COMPOSITION_%s:%d!=%d" % (col, composed, total))
            hard = False
        elif drift:
            reasons.append("INFO_ROUNDING_%s:%d" % (col, drift))

    if len(facts.report_date) != 10 or facts.report_date[4] != "-":
        reasons.append("HARD_BAD_DATE:%s" % facts.report_date)
        hard = False

    # ---- 软门 · 流水闭合 ----
    flow_ok = True
    for tag, o, i, x, c in (
        ("BANK", facts.bank_open, facts.bank_in, facts.bank_out, facts.bank_close),
        ("BILL", facts.bill_open, facts.bill_in, facts.bill_out, facts.bill_close),
        ("TOTAL", facts.total_open, facts.total_in, facts.total_out, facts.total_close),
    ):
        drift = o + i - x - c
        if abs(drift) > COMPOSITION_TOLERANCE_FEN:
            reasons.append("SOFT_FLOW_%s:%d" % (tag, drift))
            flow_ok = False
        elif drift:
            reasons.append("INFO_ROUNDING_FLOW_%s:%d" % (tag, drift))

    # ---- 软门 · 跨日链 ----
    chain_ok = True
    if prev_close is not None and _contiguous(prev_date, facts.report_date):
        opening = facts.bank_open + facts.bill_open   # 与 prev_close 同口径，不含库存现金
        delta = opening - prev_close
        if abs(delta) > CHAIN_TOLERANCE_FEN:
            reasons.append("SOFT_CHAIN_BREAK:%d" % delta)
            chain_ok = False
        elif delta:
            # 记下来但不判可疑——源表人工微调，不是读错
            reasons.append("INFO_CHAIN_ADJUST:%d" % delta)

    return GateResult(passed_hard=hard, flow_ok=flow_ok, chain_ok=chain_ok,
                      reasons=reasons)


def _contiguous(prev_date: Optional[str], report_date: str, max_gap: int = 4) -> bool:
    """两日足够近才值得对链条。跨周末最多 3 天，留 4 天余量。"""
    if not prev_date:
        return False
    from datetime import date
    try:
        a = date.fromisoformat(prev_date)
        b = date.fromisoformat(report_date)
    except ValueError:
        return False
    return 0 < (b - a).days <= max_gap


def storable_total(facts: DayFacts) -> int:
    """入库口径：银行存款 + 电子汇票。库存现金按用户决定统一忽略。"""
    return facts.bank_close + facts.bill_close
