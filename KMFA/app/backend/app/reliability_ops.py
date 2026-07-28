# -*- coding: utf-8 -*-
"""S11–S13 —— 质量、可观测性、成本与发布。

| 任务 | pass_gate |
|---|---|
| T-S11-01 | 关键 mutation 被捕获，确定性阻断测试全通过 |
| T-S11-02 | 关键流五类覆盖率 100%，阻断 a11y/视觉/功能失败=0 |
| T-S11-03 | 批准负载内 SLO/成本/错误率通过，**拐点和上限已记录** |
| T-S11-04 | 关键故障覆盖 100%，**数据不变量失败=0**，RPO/RTO 有证据 |
| T-S12-01 | 关键旅程关联率 100%，**敏感命中=0**，SLO 可计算 |
| T-S12-02 | 关键故障被发现并可定位；**自愈保持幂等和数据不变量** |
| T-S12-03 | 每类资源有预算/owner/告警；新增服务有量化触发条件 |
| T-S12-04 | 演练证据可复现，缺陷有 owner/期限，匿名恢复兼容 |
| T-S13-01 | 所有高风险能力**可独立关闭**；默认/owner/expiry 完整 |
| T-S13-02 | 阈值触发**自动**停止/回滚，回滚后核心 Oracle 全通过 |
| T-S13-03 | 生产核心 AC 全通过，观察窗口内无阻断回归 |
| T-S13-04 | P0 AC 100% PASS；P1 无未接受高风险；成本/可靠性/安全门通过 |

## 贯穿这几阶段的一条线：**判据必须是机器可判的**

「SLO 达标」「告警可定位」「回滚通过」这类说法在复盘时毫无约束力——
谁都可以说自己达标了。所以本模块把每条 pass_gate 落成一个**返回布尔或抛错**
的函数：达标就是函数不抛，不达标就是抛，中间没有解释空间。

## 覆盖率不设及格线

关键流的五类路径（Golden / Black / Abuse / Degraded / Recovery）覆盖率写的是
100%，不是 95%。设及格线的问题是：没覆盖的那 5% 不是随机的 5%，
而是**最难写测试的那 5%**——也就是最容易出事的那部分。

## 自愈：宁可不愈，不可愈错

T-S12-02 的 stop_condition 是「自愈会删除唯一数据、重复财务操作或
跨 workspace 修改」。所以自愈动作分两类：**安全类**（重试、隔离、重算）
可以自动执行；**危险类**（删除、转账、跨域写）**永远只生成工单**。
这个分界写死在代码里，不是配置——配置会被改。
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

# ── T-S11 质量 ─────────────────────────────────────────────────────────────

#: 关键流必须覆盖的五类路径。**100%，不设及格线**——
#: 没覆盖的那部分不是随机的，而是最难写测试的那部分，也就是最容易出事的。
PATH_CLASSES = ("golden", "black", "abuse", "degraded", "recovery")


class OpsError(Exception):
    def __init__(self, code: str, message: str,
                 payload: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.payload = dict(payload or {})


def path_matrix_gaps(matrix: Mapping[str, Iterable[str]]) -> list[str]:
    """关键流 × 五类路径的缺口。"""
    gaps = []
    for flow, covered in matrix.items():
        have = set(covered)
        for path_class in PATH_CLASSES:
            if path_class not in have:
                gaps.append(f"{flow}：缺 {path_class}")
    return gaps


def assert_path_matrix_complete(matrix: Mapping[str, Iterable[str]]) -> None:
    if not matrix:
        raise OpsError("path_matrix_empty",
                       "路径矩阵是空的——空矩阵的覆盖率恒为 100%，那是自欺。")
    gaps = path_matrix_gaps(matrix)
    if gaps:
        raise OpsError("path_matrix_incomplete",
                       "关键流五类路径覆盖率必须 100%。没覆盖的那部分不是随机的，"
                       "而是最难写测试的那部分——也就是最容易出事的。",
                       {"gaps": gaps})


def mutation_score(killed: int, total: int) -> float:
    """变异测试得分。**分母是注入的变异总数**，不是「被测到的变异数」。"""
    if total <= 0:
        raise OpsError("mutation_total_invalid",
                       "变异总数必须为正——没有注入变异时得分无意义，不是 100%。")
    if killed < 0 or killed > total:
        raise OpsError("mutation_killed_invalid", "杀死数必须在 0..total 之间。")
    return killed / total


def assert_mutation_gate(killed: int, total: int, *, threshold: float) -> None:
    score = mutation_score(killed, total)
    if score < threshold:
        raise OpsError(
            "mutation_gate_failed",
            f"变异得分 {score:.2%} 低于阈值 {threshold:.0%}——"
            "有一批错误改动不会被现有测试发现。",
            {"killed": killed, "total": total})


def load_curve_knee(samples: list[Mapping[str, Any]]) -> dict[str, Any]:
    """从压测样本里找拐点：**P95 首次翻倍**的并发点。

    「拐点已记录」不能是一句话——它必须是一个数，
    因为容量决策（扩容/限流阈值）要拿它当输入。
    """
    if len(samples) < 2:
        raise OpsError("load_samples_insufficient",
                       "样本少于 2 个，画不出曲线，也就找不到拐点。")
    ordered = sorted(samples, key=lambda s: int(s["concurrency"]))
    baseline = float(ordered[0]["p95_ms"])
    if baseline <= 0:
        raise OpsError("load_baseline_invalid", "基线 P95 必须为正。")
    for sample in ordered[1:]:
        if float(sample["p95_ms"]) >= baseline * 2:
            return {"knee_concurrency": int(sample["concurrency"]),
                    "knee_p95_ms": float(sample["p95_ms"]),
                    "baseline_p95_ms": baseline,
                    "safe_concurrency": max(1, int(sample["concurrency"]) // 2)}
    top = ordered[-1]
    return {"knee_concurrency": None,
            "knee_p95_ms": None,
            "baseline_p95_ms": baseline,
            "safe_concurrency": int(top["concurrency"]),
            "注": "在实测范围内未出现拐点——**这不等于没有拐点**，"
                  "只说明它在测试范围之外。安全并发取实测最高点，不外推。"}


def assert_slo(measured: Mapping[str, Any], budget: Mapping[str, Any]) -> None:
    """SLO 判定。**逐项比，任何一项超标即失败**——
    「整体还行」是最容易被用来掩盖单项崩溃的说法。"""
    breaches = []
    for key, limit in budget.items():
        value = measured.get(key)
        if value is None:
            breaches.append(f"{key}：没有实测值")
        elif float(value) > float(limit):
            breaches.append(f"{key}：{value} > 上限 {limit}")
    if breaches:
        raise OpsError("slo_breached", "SLO 未达标。", {"breaches": breaches})


CRITICAL_FAILURE_MODES = ("storage_unavailable", "database_unavailable",
                          "dependency_timeout", "disk_full", "process_crash",
                          "network_partition")


def chaos_coverage(scenarios: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """故障注入覆盖率。**每个场景必须带恢复证据**——
    「注入了故障」和「验证了恢复」是两件事，只做前者等于确认系统会坏。"""
    seen: dict[str, dict] = {}
    for scenario in scenarios:
        mode = str(scenario.get("mode") or "")
        if mode not in CRITICAL_FAILURE_MODES:
            continue
        if not scenario.get("recovery_evidence"):
            continue
        if scenario.get("invariant_violations"):
            raise OpsError(
                "chaos_invariant_violated",
                f"故障场景 {mode} 中数据不变量被破坏——"
                "pass_gate 要求「数据不变量失败=0」。",
                {"violations": scenario.get("invariant_violations")})
        seen[mode] = dict(scenario)
    missing = [m for m in CRITICAL_FAILURE_MODES if m not in seen]
    return {"covered": sorted(seen), "missing": missing, "complete": not missing}


def assert_rpo_rto(measured: Mapping[str, Any], *, rpo_seconds: int,
                   rto_seconds: int) -> None:
    """RPO/RTO 必须有**实测值**，不是目标值。目标值人人都有。"""
    for key, limit in (("rpo_seconds", rpo_seconds), ("rto_seconds", rto_seconds)):
        value = measured.get(key)
        if value is None:
            raise OpsError("recovery_objective_unmeasured",
                           f"{key} 没有实测值——目标值人人都有，实测值才是证据。")
        if float(value) > limit:
            raise OpsError("recovery_objective_missed",
                           f"{key} 实测 {value} 超过目标 {limit}。")


# ── T-S12 可观测性、告警、成本 ─────────────────────────────────────────────

_SENSITIVE_IN_TELEMETRY = (
    re.compile(r"1[3-9]\d{9}"),
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    re.compile(r"(?:gh[pousr]_|sk-|xox[bap]-)"),
    re.compile(r"\bws_[A-Za-z0-9_-]{10,}"),
    re.compile(r"Bearer\s+\S+"),
)


def telemetry_sensitive_hits(records: Iterable[Mapping[str, Any]]) -> list[str]:
    hits = []
    for record in records:
        blob = " ".join(f"{k}={v}" for k, v in record.items())
        for pattern in _SENSITIVE_IN_TELEMETRY:
            match = pattern.search(blob)
            if match:
                hits.append(f"{record.get('name', '?')}：{match.group(0)[:12]}…")
    return hits


def journey_correlation(spans: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """关键旅程关联率。**没有 trace_id 的 span 就是断的**——
    一条断了的链路在排查时的价值是零，而它在仪表盘上看起来是正常的。"""
    total = correlated = 0
    orphans: list[str] = []
    for span in spans:
        total += 1
        if span.get("trace_id"):
            correlated += 1
        else:
            orphans.append(str(span.get("name") or "?"))
    rate = 1.0 if total == 0 else correlated / total
    return {"total": total, "correlated": correlated, "rate": rate,
            "orphans": orphans, "complete": not orphans}


#: 可以自动执行的自愈动作。**白名单，写死在代码里不是配置**——配置会被改。
SAFE_REMEDIATIONS = frozenset({"retry", "isolate", "recompute", "scale_out",
                               "reopen_connection", "clear_local_cache"})

#: 永远只生成工单、绝不自动执行的动作。
NEVER_AUTOMATED = frozenset({"delete", "purge", "transfer_funds", "refund",
                             "cross_workspace_write", "drop_table",
                             "rotate_production_secret"})


def plan_remediation(action: str, *, idempotent: bool) -> dict[str, Any]:
    """自愈判定。**宁可不愈，不可愈错。**

    T-S12-02 的 stop_condition 是「自愈会删除唯一数据、重复财务操作或
    跨 workspace 修改」——这三类在这里是硬编码的黑名单，不是配置项。
    """
    if action in NEVER_AUTOMATED:
        return {"mode": "ticket_only", "action": action,
                "理由": "该动作可能删除唯一数据、重复财务操作或跨 workspace 修改。"
                        "这是 T-S12-02 的 stop_condition，永远只生成工单。"}
    if action not in SAFE_REMEDIATIONS:
        return {"mode": "ticket_only", "action": action,
                "理由": "不在自动执行白名单里。白名单默认拒绝——"
                        "未知动作自动执行一次，就够了。"}
    if not idempotent:
        return {"mode": "ticket_only", "action": action,
                "理由": "该动作不幂等。自愈会重试，而重试一个不幂等的动作"
                        "等于把一次故障放大成 N 次。"}
    return {"mode": "automatic", "action": action}


def alert_is_actionable(alert: Mapping[str, Any]) -> None:
    """告警必须可执行。**没有 runbook 的告警是一次打扰**，
    它唯一确定的效果是让人更快学会忽略告警。"""
    missing = [f for f in ("symptom", "runbook", "owner", "diagnostic_bundle")
               if not str(alert.get(f) or "").strip()]
    if missing:
        raise OpsError("alert_not_actionable",
                       f"告警「{alert.get('name')}」缺 {missing}。"
                       "没有 runbook 的告警是一次打扰——它唯一确定的效果"
                       "是让人更快学会忽略告警。",
                       {"missing": missing})


def budget_gaps(resources: Iterable[Mapping[str, Any]]) -> list[str]:
    """每类资源都要有预算、owner、告警。缺一项都算缺口——
    有预算没 owner 的意思是「超了没人管」。"""
    gaps = []
    for resource in resources:
        name = str(resource.get("name") or "?")
        for field in ("budget", "owner", "alert_threshold"):
            if not resource.get(field):
                gaps.append(f"{name}：缺 {field}")
    return gaps


def unit_cost(total_cents: int, units: int) -> int:
    """单位成本（分/单位）。整数，理由与 S09 相同。"""
    if units <= 0:
        raise OpsError("unit_cost_units_invalid",
                       "单位数必须为正——除以 0 的单位成本不是无穷大，是没意义。")
    return total_cents // units


def service_trigger_met(metric_value: float, trigger: Mapping[str, Any]) -> bool:
    """新增服务的量化触发条件。**必须是数，不能是「感觉需要了」**。"""
    threshold = trigger.get("threshold")
    if threshold is None:
        raise OpsError("service_trigger_unquantified",
                       f"服务 {trigger.get('service')!r} 的触发条件没有量化阈值。"
                       "「感觉需要了」不是触发条件——它无法被复核，也无法被反驳。")
    return float(metric_value) >= float(threshold)


# ── T-S13 发布 ─────────────────────────────────────────────────────────────

def validate_flag(flag: Mapping[str, Any]) -> dict[str, Any]:
    """高风险能力开关。**默认关、有 owner、有到期日**，三缺一都不行。

    没有到期日的开关会永久存在，而永久存在的临时开关最终没人知道它是干什么的——
    于是没人敢关，也没人敢开。
    """
    name = str(flag.get("name") or "").strip()
    if not name:
        raise OpsError("flag_name_required", "开关必须有名字。")
    problems = []
    if flag.get("default") is not False:
        problems.append("默认必须是关（高风险能力默认开，等于没有开关）")
    if not str(flag.get("owner") or "").strip():
        problems.append("缺 owner（出事时没人能拍板关掉它）")
    if not str(flag.get("expiry") or "").strip():
        problems.append("缺到期日（永久存在的临时开关最终没人敢动）")
    if not flag.get("kill_switch"):
        problems.append("缺 kill switch（不能独立关闭就不算可控）")
    if problems:
        raise OpsError("flag_incomplete", f"开关「{name}」不完整。",
                       {"problems": problems})
    return {"name": name, "default": False, "owner": flag["owner"],
            "expiry": flag["expiry"], "kill_switch": True}


def promotion_decision(metrics: Mapping[str, Any],
                       thresholds: Mapping[str, Any]) -> dict[str, Any]:
    """渐进切流判定。**越界即自动回滚，不询问。**

    「先通知人，人来决定回不回滚」的问题是：人可能在睡觉，
    而错误版本在这段时间里继续产生坏数据。
    """
    breaches = []
    for key, limit in thresholds.items():
        value = metrics.get(key)
        if value is None:
            breaches.append(f"{key}：没有实测值（缺数据按越界处理，"
                            "因为「测不到」和「很糟」在风险上等价）")
        elif float(value) > float(limit):
            breaches.append(f"{key}：{value} > {limit}")
    if breaches:
        return {"decision": "rollback", "automatic": True, "breaches": breaches}
    return {"decision": "promote", "automatic": True, "breaches": []}


def assert_rollback_verified(evidence: Mapping[str, Any]) -> None:
    """回滚后核心 Oracle 必须全通过。**回滚不是终点，是另一个待验证状态**——
    回滚到一个也坏了的版本，比不回滚更难查。"""
    if not evidence.get("rolled_back"):
        raise OpsError("rollback_not_executed", "没有回滚记录。")
    failed = [name for name, ok in (evidence.get("oracles") or {}).items() if not ok]
    if failed:
        raise OpsError("rollback_oracles_failed",
                       f"回滚后这些 Oracle 仍然失败：{failed}。"
                       "回滚到一个也坏了的版本，比不回滚更难查。",
                       {"failed": failed})


def ga_decision(p0: Mapping[str, bool], p1_risks: Iterable[Mapping[str, Any]],
                gates: Mapping[str, bool]) -> dict[str, Any]:
    """GA / Hold / Kill。**P0 必须 100%，不存在「基本都过了」。**"""
    p0_failed = sorted(name for name, ok in p0.items() if not ok)
    unaccepted = [str(r.get("name")) for r in p1_risks
                  if str(r.get("severity", "")).lower() in {"high", "critical"}
                  and not r.get("accepted_by")]
    gate_failed = sorted(name for name, ok in gates.items() if not ok)

    if p0_failed:
        return {"decision": "hold", "reason": "P0 验收未全通过",
                "p0_failed": p0_failed, "blocking": True}
    if unaccepted:
        return {"decision": "hold", "reason": "存在未被接受的高风险 P1",
                "unaccepted": unaccepted, "blocking": True}
    if gate_failed:
        return {"decision": "hold", "reason": "成本/可靠性/安全门未通过",
                "gate_failed": gate_failed, "blocking": True}
    return {"decision": "ga", "reason": "P0 100% PASS，P1 无未接受高风险，三门通过",
            "blocking": False,
            "后续": "7 天与 30 天复核计划各一次"}
