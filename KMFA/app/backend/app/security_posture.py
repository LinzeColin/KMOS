# -*- coding: utf-8 -*-
"""S10 —— 安全态势：威胁模型、供应链、负向验证、AI 范围。

| 任务 | 验收 | pass_gate |
|---|---|---|
| T-S10-01 | AC-ARCH-001 | 所有高风险威胁有**预防、检测、响应和验收 Oracle** |
| T-S10-02 | AC-SEC-002 | **Critical/High 阻断=0**，SBOM 完整，逾期补丁=0 |
| T-S10-03 | AC-SEC-001 | **canary 命中=0，越权读写=0** |
| T-S10-04 | AC-AI-001 | AI scope 与代码一致；适用时双流水线均通过 |

## 威胁模型：每条威胁必须四件齐全

只写"风险：数据泄露"没有任何用——它不能被验证，也不能被反驳。
本模块要求每条高风险威胁都带四样：

  · **预防**（怎么让它发生不了）
  · **检测**（发生了怎么知道）
  · **响应**（知道了怎么办）
  · **Oracle**（拿什么证明前三条是真的）

第四条是关键。没有 Oracle 的威胁条目是**一段声明**，
而声明在事故复盘里唯一的作用是证明我们当初想到过。

## canary：不依赖谁记得检查什么

在私有面里埋固定标记串，在所有公开面（页面、API、搜索、缓存、对象、
sitemap、日志）里搜它。命中即泄露——**这个判据不需要任何人判断**，
也不会因为换了个人来做而变松。

## AI scope：先回答"有没有"，再谈"合不合规"

T-S10-04 的措辞是「**仅在真实模型能力存在时**建立双流水线」。
所以第一步是判定本仓到底有没有模型能力，并且这个判定要**可复核**——
扫代码里的模型调用面，而不是问人。

判定为"没有"时，双流水线不是被跳过，是**不适用**；
而这两者的区别必须留痕，否则后来的人看到"没有 eval"会以为是漏了。
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

#: 威胁必备的四件套。缺任何一件，该条威胁不算被处置。
THREAT_CONTROLS = ("prevent", "detect", "respond", "oracle")

#: 风险等级。high 及以上必须四件齐全。
RISK_LEVELS = ("low", "medium", "high", "critical")
RISK_REQUIRING_FULL_CONTROLS = frozenset({"high", "critical"})

#: 阻断级漏洞等级——出现即不得发布。
BLOCKING_SEVERITIES = frozenset({"critical", "high"})

#: 补丁时限（天）。逾期数必须为 0。
PATCH_SLA_DAYS = {"critical": 7, "high": 14, "medium": 30, "low": 90}

#: 模型能力的代码特征。**扫代码而不是问人**——
#: 问人得到的是记忆，扫代码得到的是事实。
_AI_CALL_SIGNS = (
    re.compile(r"\banthropic\b", re.I),
    re.compile(r"\bopenai\b", re.I),
    re.compile(r"\bclaude-[a-z0-9-]+\b", re.I),
    re.compile(r"\bgpt-[0-9]"),
    re.compile(r"\bmessages\.create\b"),
    re.compile(r"\bchat\.completions\b"),
    re.compile(r"\btransformers\b"),
    re.compile(r"\btorch\b"),
)


class SecurityError(Exception):
    def __init__(self, code: str, message: str,
                 payload: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.payload = dict(payload or {})


# ── T-S10-01 威胁模型 ──────────────────────────────────────────────────────

def validate_threat(threat: Mapping[str, Any]) -> dict[str, Any]:
    """校验一条威胁条目。**高风险必须四件齐全。**

    只写「风险：数据泄露」不能被验证也不能被反驳；
    没有 Oracle 的条目是一段声明，而声明在事故复盘里唯一的作用
    是证明我们当初想到过。
    """
    name = str(threat.get("name") or "").strip()
    if not name:
        raise SecurityError("threat_name_required", "威胁必须有名字。")
    level = str(threat.get("risk") or "").lower()
    if level not in RISK_LEVELS:
        raise SecurityError("threat_risk_invalid",
                            f"风险等级须为 {RISK_LEVELS}，收到 {level!r}。")
    if level in RISK_REQUIRING_FULL_CONTROLS:
        missing = [c for c in THREAT_CONTROLS if not str(threat.get(c) or "").strip()]
        if missing:
            raise SecurityError(
                "threat_controls_incomplete",
                f"高风险威胁「{name}」缺少 {missing}。"
                "四件套缺一件就不算处置——尤其 oracle：没有它，"
                "前三条是否为真无从验证。",
                {"missing": missing})
    return {"name": name, "risk": level,
            **{c: str(threat.get(c) or "") for c in THREAT_CONTROLS}}


def threat_coverage(threats: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """全表覆盖率。**高风险覆盖率必须是 100%**，不设及格线。"""
    total = high = covered = 0
    gaps: list[str] = []
    for threat in threats:
        total += 1
        if str(threat.get("risk", "")).lower() in RISK_REQUIRING_FULL_CONTROLS:
            high += 1
            try:
                validate_threat(threat)
                covered += 1
            except SecurityError as error:
                gaps.append(f"{threat.get('name')}：{error.payload.get('missing')}")
    return {"total": total, "high_risk": high, "high_risk_covered": covered,
            "gaps": gaps, "complete": not gaps}


# ── T-S10-02 供应链 ────────────────────────────────────────────────────────

def blocking_findings(findings: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """筛出阻断级发现。**已接受的例外必须带到期日**——

    没有到期日的例外会永久存在，而「永久接受的高危」和「没发现」
    在后果上没有区别，只是多了一份让人安心的记录。
    """
    blockers: list[dict[str, Any]] = []
    for item in findings:
        severity = str(item.get("severity") or "").lower()
        if severity not in BLOCKING_SEVERITIES:
            continue
        accepted = item.get("accepted_until")
        if not accepted:
            blockers.append(dict(item))
        elif not str(accepted).strip():
            blockers.append(dict(item))
    return blockers


def overdue_patches(items: Iterable[Mapping[str, Any]],
                    *, today_ordinal: int) -> list[dict[str, Any]]:
    """逾期补丁。时间用**序数天**传进来，不在这里读时钟——
    读时钟的函数无法测「明天会不会逾期」。"""
    overdue = []
    for item in items:
        severity = str(item.get("severity") or "").lower()
        sla = PATCH_SLA_DAYS.get(severity)
        if sla is None:
            continue
        discovered = item.get("discovered_ordinal")
        if not isinstance(discovered, int):
            raise SecurityError("patch_missing_discovery_date",
                                f"{item.get('id')} 没有发现日期，无法判断是否逾期。")
        if item.get("fixed"):
            continue
        if today_ordinal - discovered > sla:
            overdue.append({**dict(item), "overdue_days":
                            today_ordinal - discovered - sla})
    return overdue


def validate_sbom(sbom: Mapping[str, Any]) -> dict[str, Any]:
    """SBOM 完整性。**每个组件都要有名字、版本和来源**——

    少了版本的 SBOM 无法回答「我们受不受这个 CVE 影响」，
    而那正是 SBOM 存在的唯一理由。
    """
    components = sbom.get("components")
    if not isinstance(components, list) or not components:
        raise SecurityError("sbom_empty", "SBOM 没有组件——空 SBOM 不是 SBOM。")
    incomplete = [
        c.get("name", "?") for c in components
        if not (c.get("name") and c.get("version") and c.get("source"))
    ]
    if incomplete:
        raise SecurityError(
            "sbom_incomplete",
            "有组件缺名字/版本/来源。少了版本的 SBOM 无法回答"
            "「我们受不受这个 CVE 影响」——而那是 SBOM 存在的唯一理由。",
            {"incomplete": incomplete})
    return {"component_count": len(components), "complete": True}


def artifact_signature_required(artifact: Mapping[str, Any]) -> None:
    """制品必须有签名与摘要。**摘要不能替代签名**：
    摘要证明"没被改过"，签名证明"是我们发的"——
    攻击者能同时替换制品和它的摘要，但替换不了签名。"""
    if not artifact.get("sha256"):
        raise SecurityError("artifact_digest_missing", "制品缺摘要。")
    if not artifact.get("signature"):
        raise SecurityError(
            "artifact_signature_missing",
            "制品缺签名。摘要证明「没被改过」，签名证明「是我们发的」——"
            "攻击者能同时替换制品和它的摘要，但替换不了签名。")


# ── T-S10-03 负向验证 ──────────────────────────────────────────────────────

def canary_hits(surfaces: Mapping[str, str], canaries: Iterable[str]) -> list[str]:
    """在所有公开面里搜 canary。**命中即泄露，判据不需要任何人判断**，
    也不会因为换了个人来做而变松。"""
    hits: list[str] = []
    for surface, content in surfaces.items():
        for canary in canaries:
            if canary and canary in (content or ""):
                hits.append(f"{surface}：命中 {canary}")
    return hits


def assert_no_leak(surfaces: Mapping[str, str], canaries: Iterable[str]) -> None:
    hits = canary_hits(surfaces, canaries)
    if hits:
        raise SecurityError(
            "canary_leaked",
            "私有 canary 出现在公开面上——这是 T-S10-03 的 stop_condition，"
            "发布必须停下并撤销。",
            {"hits": hits})


REQUIRED_LEAK_SURFACES = ("page", "api", "search", "cache", "object",
                          "sitemap", "log", "error")


def assert_surfaces_covered(surfaces: Mapping[str, str]) -> None:
    """**扫的面不全，等于没扫。** 少扫一个面的表现和一切正常完全一样。"""
    missing = [name for name in REQUIRED_LEAK_SURFACES if name not in surfaces]
    if missing:
        raise SecurityError(
            "leak_scan_incomplete",
            f"这些公开面没有被扫到：{missing}。少扫一个面的表现和一切正常完全一样。",
            {"missing": missing})


# ── T-S10-04 AI 范围 ───────────────────────────────────────────────────────

#: 扫描器自身与它的测试。**必须排除，否则它永远会找到自己**——
#: 这些文件里写着 `anthropic` / `torch` / `openai` 这些**字面量**，
#: 因为它们就是判据本身。不排除的话，任何仓库扫出来都「有模型能力」，
#: 而一个恒为真的检测器等于没有检测器。
_SELF_EXCLUDED = ("security_posture.py", "test_s10_s13_posture_and_release.py")


def detect_model_capability(sources: Mapping[str, str]) -> dict[str, Any]:
    """扫代码判定有没有真实模型能力。**扫代码而不是问人**——
    问人得到的是记忆，扫代码得到的是事实。

    排除扫描器自身：它的正则字面量里就写着那些关键词，
    不排除的话检测结果恒为真。这是本函数第一版真踩到的——
    对本仓后端一扫，结论是「有模型能力」，而实际一处调用都没有。
    """
    evidence: list[str] = []
    for path, text in sources.items():
        if any(path.endswith(name) for name in _SELF_EXCLUDED):
            continue
        for pattern in _AI_CALL_SIGNS:
            match = pattern.search(text or "")
            if match:
                evidence.append(f"{path}：{match.group(0)}")
    return {"has_model_capability": bool(evidence), "evidence": sorted(set(evidence))}


def ai_scope_decision(detection: Mapping[str, Any],
                      declared: Mapping[str, Any]) -> dict[str, Any]:
    """AI scope 与代码必须一致。

    判定为「没有」时，双流水线是**不适用**而不是被跳过——
    两者的区别必须留痕，否则后来的人看到「没有 eval」会以为是漏了。
    """
    detected = bool(detection.get("has_model_capability"))
    claimed = bool(declared.get("in_scope"))
    if detected != claimed:
        raise SecurityError(
            "ai_scope_mismatch",
            f"声明 AI scope={claimed}，但代码扫描结果是 {detected}。"
            "声明与代码不一致时，以代码为准并停下来对齐——"
            "不一致本身就说明有人改了东西而没改声明。",
            {"evidence": detection.get("evidence")})
    if not detected:
        return {
            "in_scope": False,
            "dual_pipeline": "not_applicable",
            "理由": "本仓不含模型调用面（已扫描全部源文件，无 anthropic/openai/"
                    "transformers/torch 等调用）。双流水线**不适用**，"
                    "不是被跳过——这两者的区别必须留痕，"
                    "否则后来的人看到「没有 eval」会以为是漏了。",
            "evidence": detection.get("evidence", []),
        }
    return {"in_scope": True, "dual_pipeline": "required",
            "必须交付": ["eval 套件", "red-team 报告", "System Card",
                        "阶段 Gate", "线上监控"],
            "evidence": detection.get("evidence", [])}
