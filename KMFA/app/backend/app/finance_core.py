# -*- coding: utf-8 -*-
"""S09 —— 财务核心：血缘、金额不变量、幂等重跑、经营分析。

| 任务 | 验收 | pass_gate |
|---|---|---|
| T-S09-01 | AC-FIN-002 | 关键结果 100% 可追溯，**来源链断点=0** |
| T-S09-02 | AC-FIN-001 | 所有精确测试通过，**权威浮点字段=0** |
| T-S09-03 | AC-FIN-003 | **静默覆盖=0，重复结果=0**，冲突均可解释 |
| T-S09-04 | AC-FIN-004 | Golden Path 100%，Black Path 数据不丢，报告 hash/数值/来源一致 |

## 金额：整数分，全程不出现 float

`0.1 + 0.2 != 0.3` 在报表上的表现不是"差一点点"，是**对不平**——
而对不平会被当成业务问题去查，查上半天才发现是二进制浮点。

所以本模块的金额一律是 `int`（最小货币单位，人民币即"分"）。
不是 `Decimal` 而是 `int`：`Decimal` 仍然可以被误乘一个 float 而降级，
`int` 不会。要小数的地方在**展示层**才转，且只转一次。

`T-S09-02` 的 pass_gate 是「权威浮点字段=0」，本仓已有
`tools/check_no_float_money.py` 做 AST 级静态检查，本模块与它同向。

## 舍入：银行家舍入，且**只在最后一步**

中间步骤舍入会累积误差：10 次 `round(x/3)` 和 `round(10*x/3)` 不等。
所以内部保留全精度整数（分），只在产出对外数字时舍入一次。

用 `ROUND_HALF_EVEN`（银行家舍入）而不是 `ROUND_HALF_UP`：
后者在大量数据上系统性偏高，而"每一笔都合规、总数却偏了"最难解释。

## 血缘：断点 = 0 意味着**推断值不能冒充事实**

stop_condition 写得很清楚：「原始来源缺失且系统准备把推断值标为事实」即停止。
所以每个结果都带 `provenance`，其中 `kind` 只有三种：
`measured`（来自原始凭证）、`derived`（由其它带来源的值算出）、
`estimated`（推断）。**`estimated` 的结果不允许进入权威口径**——
它可以显示，但必须带标记，且不参与需要 `measured` 的断言。
"""
from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any, Iterable, Mapping

#: 来源种类。**顺序即可信度**，后面的不得冒充前面的。
PROVENANCE_KINDS = ("measured", "derived", "estimated")

#: 需要 measured 血缘才允许出现的口径。这些数字会被拿去做决策，
#: 而推断值做决策的问题不是"可能不准"，是"没人知道它不准"。
AUTHORITATIVE_METRICS = frozenset({
    "revenue_cents", "cost_cents", "gross_margin_cents", "cash_in_cents",
    "cash_out_cents", "receivable_cents", "payable_cents",
})

_IDENT = re.compile(r"^[a-z][a-z0-9_]{0,63}$")  # 单字符字段名合法——2 字符起是写正则时的意外，不是约束


class FinanceError(Exception):
    def __init__(self, code: str, message: str,
                 payload: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.payload = dict(payload or {})


# ── T-S09-02 金额与舍入 ────────────────────────────────────────────────────

def to_cents(value: Any) -> int:
    """把输入转成整数分。**拒绝 float，不是转换 float。**

    转换会让 `0.1` 变成 `10` 而 `2.675` 变成 `267`（不是 268），
    而调用方不会知道自己刚刚丢了一分钱。拒绝则当场暴露。
    """
    if isinstance(value, bool):
        raise FinanceError("amount_is_bool", "布尔不是金额。")
    if isinstance(value, float):
        raise FinanceError(
            "amount_is_float",
            f"金额不接受 float（收到 {value!r}）。0.1+0.2 != 0.3 在报表上的表现"
            "不是「差一点点」而是**对不平**，而对不平会被当成业务问题查半天。"
            "请传整数分，或十进制字符串。")
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        cents = (value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
        return int(cents)
    if isinstance(value, str):
        text = value.strip().replace(",", "").replace("，", "")
        if not text:
            raise FinanceError("amount_empty", "金额为空。")
        try:
            return int((Decimal(text) * 100).quantize(
                Decimal("1"), rounding=ROUND_HALF_EVEN))
        except Exception as exc:
            raise FinanceError("amount_unparsable", f"无法解析金额 {value!r}。") from exc
    raise FinanceError("amount_type_unsupported", f"不支持的金额类型 {type(value)}。")


def format_cents(cents: int) -> str:
    """分 → 展示串。**只在这里转小数，且只转一次。**"""
    if not isinstance(cents, int) or isinstance(cents, bool):
        raise FinanceError("format_requires_int_cents", "展示层只接受整数分。")
    sign = "-" if cents < 0 else ""
    whole, remainder = divmod(abs(cents), 100)
    return f"{sign}{whole:,}.{remainder:02d}"


def allocate(total_cents: int, weights: list[int]) -> list[int]:
    """按权重分摊，**保证分摊结果之和恰好等于总额**。

    先按比例取整，再把余数一分一分地补给余数最大的几项（最大余数法）。
    朴素做法是各自 round 然后相加——那样几乎必然差几分，
    而"合计对不上明细"是财务报表里最招人质疑的一种错误。
    """
    if not isinstance(total_cents, int) or isinstance(total_cents, bool):
        raise FinanceError("allocate_requires_int", "分摊只接受整数分。")
    if not weights or any(w < 0 for w in weights):
        raise FinanceError("allocate_weights_invalid", "权重必须非负且非空。")
    total_weight = sum(weights)
    if total_weight == 0:
        raise FinanceError("allocate_weights_zero", "权重之和为 0，无法分摊。")

    sign = -1 if total_cents < 0 else 1
    amount = abs(total_cents)
    base = [amount * w // total_weight for w in weights]
    remainder = amount - sum(base)
    # 余数按「本该分到的小数部分」从大到小补，同分则按索引，保证确定性
    order = sorted(range(len(weights)),
                   key=lambda i: (-((amount * weights[i]) % total_weight), i))
    for index in order[:remainder]:
        base[index] += 1
    result = [sign * value for value in base]
    assert sum(result) == total_cents, "分摊之和与总额不符——这是本函数的全部意义"
    return result


def zero_diff(left_cents: int, right_cents: int) -> dict[str, Any]:
    """零差额不变量。**差额用整数比，不设容差。**

    设容差（"差 1 分算平"）等于把对账变成一句安慰：
    真正的错误常常就是一分钱起步，而容差恰好把它盖住。
    """
    for value in (left_cents, right_cents):
        if not isinstance(value, int) or isinstance(value, bool):
            raise FinanceError("zero_diff_requires_int", "对账只接受整数分。")
    delta = left_cents - right_cents
    return {"left_cents": left_cents, "right_cents": right_cents,
            "delta_cents": delta, "balanced": delta == 0}


# ── T-S09-01 血缘 ──────────────────────────────────────────────────────────

def provenance(kind: str, *, source_ref: str, field: str,
               inputs: Iterable[str] = ()) -> dict[str, Any]:
    if kind not in PROVENANCE_KINDS:
        raise FinanceError("provenance_kind_unknown",
                           f"来源种类只能是 {PROVENANCE_KINDS}。")
    if not source_ref:
        raise FinanceError("provenance_source_required",
                           "来源引用不能为空——没有来源的数字无法被追溯，"
                           "而无法追溯的数字在对账时只能靠猜。")
    if not _IDENT.fullmatch(field):
        raise FinanceError("provenance_field_invalid", f"字段名 {field!r} 不合规。")
    return {"kind": kind, "source_ref": source_ref, "field": field,
            "inputs": sorted(set(inputs))}


def assert_traceable(metric: str, record: Mapping[str, Any]) -> None:
    """权威口径必须有 measured 或 derived 血缘。

    **`estimated` 不得进入权威口径**——推断值做决策的问题不是「可能不准」，
    是「没人知道它不准」。这正是 T-S09-01 的 stop_condition。
    """
    trail = record.get("provenance")
    if not isinstance(trail, Mapping):
        raise FinanceError("lineage_missing",
                           f"{metric} 没有来源链——来源链断点 = 0 不成立。")
    if metric in AUTHORITATIVE_METRICS and trail.get("kind") == "estimated":
        raise FinanceError(
            "estimated_value_in_authoritative_metric",
            f"{metric} 是权威口径，但它的值是推断出来的。"
            "推断值可以显示、必须带标记，但不得冒充事实进入决策口径。",
            {"provenance": dict(trail)})


def lineage_breaks(records: Iterable[Mapping[str, Any]],
                   known_sources: set[str]) -> list[str]:
    """找出断点。**`derived` 的每个 input 都必须能找到**——
    找不到就说明链条中间断了，而断了的链条比没有链条更危险：
    它看起来是完整的。"""
    breaks: list[str] = []
    for record in records:
        metric = str(record.get("metric") or "?")
        trail = record.get("provenance")
        if not isinstance(trail, Mapping):
            breaks.append(f"{metric}：无来源")
            continue
        if trail.get("source_ref") not in known_sources:
            breaks.append(f"{metric}：来源 {trail.get('source_ref')!r} 不存在")
        if trail.get("kind") == "derived":
            if not trail.get("inputs"):
                breaks.append(f"{metric}：声明为 derived 却没有输入")
            for item in trail.get("inputs") or []:
                if item not in known_sources:
                    breaks.append(f"{metric}：输入 {item!r} 不存在")
    return breaks


# ── T-S09-03 幂等重跑与跨源决策 ────────────────────────────────────────────

def rerun_key(*, source: str, period: str, version: str) -> str:
    """同源重跑的幂等键。**含版本**：同一期间的第二版数据是新结果，
    不是重复——把它去重掉才是真正的数据丢失。"""
    for part in (source, period, version):
        if not part:
            raise FinanceError("rerun_key_incomplete", "重跑键三段都不能为空。")
    return hashlib.sha256(f"{source}\x00{period}\x00{version}".encode()).hexdigest()[:32]


def plan_rerun(existing: Mapping[str, Any] | None,
               incoming: Mapping[str, Any]) -> dict[str, Any]:
    """同源重跑策略：**造新版本，绝不覆盖旧版本。**

    覆盖的问题不是丢了旧值，是丢了「为什么变了」——
    对账时唯一有用的信息恰恰是两版之间的差异。
    """
    if existing is None:
        return {"action": "create", "supersedes": None}
    if existing.get("content_sha256") == incoming.get("content_sha256"):
        # 内容一模一样 ⇒ 真重复，不产生第二个结果（重复结果 = 0）
        return {"action": "noop", "reason": "内容与既有版本逐字节相同"}
    return {"action": "create_new_version", "supersedes": existing.get("version_id")}


def decide_cross_source(candidates: list[Mapping[str, Any]],
                        priority: list[str]) -> dict[str, Any]:
    """跨来源冲突。**按 Owner 定的源优先级裁决，且把落选的一并带出。**

    只返回赢家等于把冲突藏起来：看报表的人不知道另一个源说的是别的数，
    也就无从判断这次裁决对不对。
    """
    if not candidates:
        raise FinanceError("no_candidate", "没有候选值。")
    ranked = []
    for item in candidates:
        source = str(item.get("source") or "")
        if source not in priority:
            raise FinanceError(
                "source_not_in_priority",
                f"来源 {source!r} 不在已授权的优先级表里。"
                "跨源冲突不能靠临时判断——没有默认裁决规则时必须停下来问，"
                "而不是随手选一个。")
        ranked.append((priority.index(source), item))
    ranked.sort(key=lambda pair: (pair[0], str(pair[1].get("source"))))

    winner = ranked[0][1]
    losers = [item for _, item in ranked[1:]]
    disagreement = [
        {"source": item.get("source"), "value_cents": item.get("value_cents"),
         "delta_cents": int(item.get("value_cents", 0)) - int(winner.get("value_cents", 0))}
        for item in losers
        if item.get("value_cents") != winner.get("value_cents")
    ]
    return {
        "winner": dict(winner),
        "reason": f"源优先级：{winner.get('source')} 高于 "
                  f"{[i.get('source') for i in losers] or '（无其它候选）'}",
        "disagreement": disagreement,
        "unanimous": not disagreement,
    }


# ── T-S09-04 经营分析与报告 ────────────────────────────────────────────────

def analyse(*, revenue_cents: int, cost_cents: int,
            budget_cents: int | None = None) -> dict[str, Any]:
    """经营分析。**全程整数分，比率用「万分比整数」而不是浮点。**

    毛利率写成 `2537`（即 25.37%）而不是 `0.2537`：
    浮点比率在累加与比较时会带来和金额一样的问题，而它同样会进报表。
    """
    for value in (revenue_cents, cost_cents):
        if not isinstance(value, int) or isinstance(value, bool):
            raise FinanceError("analyse_requires_int", "分析只接受整数分。")
    gross = revenue_cents - cost_cents
    result: dict[str, Any] = {
        "revenue_cents": revenue_cents,
        "cost_cents": cost_cents,
        "gross_margin_cents": gross,
    }
    if revenue_cents > 0:
        # 万分比：先乘后除，绝不先除——先除会在整数除法里直接归零。
        result["gross_margin_bps"] = gross * 10_000 // revenue_cents
    else:
        # 收入为 0 时毛利率**没有定义**，给 None 而不是 0：
        # 给 0 会在图表上画出一条「毛利率 0%」的线，那是编造。
        result["gross_margin_bps"] = None
    if budget_cents is not None:
        if not isinstance(budget_cents, int) or isinstance(budget_cents, bool):
            raise FinanceError("analyse_requires_int", "预算只接受整数分。")
        result["budget_cents"] = budget_cents
        result["variance_cents"] = cost_cents - budget_cents
        result["over_budget"] = cost_cents > budget_cents
    return result


def report_digest(payload: Mapping[str, Any]) -> str:
    """报告摘要。`sort_keys` 保证同样的内容产出同样的 hash——
    否则「报告 hash 一致」这条验收无法自证。"""
    return hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")).hexdigest()


def black_path_preserve(partial: Mapping[str, Any],
                        failure: str) -> dict[str, Any]:
    """Black Path：出错时**数据不丢**。

    把已经算出来的部分连同失败原因一起返回，而不是抛掉重来。
    抛掉的代价不只是重算——用户已经填进去的东西也一起没了。
    """
    if not failure:
        raise FinanceError("black_path_needs_reason", "失败必须带原因。")
    return {"status": "partial", "failure": failure,
            "preserved": dict(partial),
            "提示": "已算出的部分保留在 preserved 里，修好原因后可继续，不必重填。"}
