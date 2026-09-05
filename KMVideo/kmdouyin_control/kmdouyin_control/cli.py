#!/usr/bin/env python3
"""KMDouyin 的日运行、交接、发布观测与生产门控制器。"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from . import SCHEMA_VERSION

ROLE_KEYS = ("t00", "t10", "t20", "t30", "t40")
ROLE_NAMES = {
    "t00": "T00",
    "t10": "T10",
    "t20": "T20",
    "t30": "T30",
    "t40": "T40",
}
ROLE_WORK_KINDS = {
    "t10": "market_research",
    "t20": "content_strategy",
    "t30": "internal_production",
    "t40": "performance_review",
}
OBJECTIVES = {
    "market_research",
    "content_strategy",
    "internal_production",
    "release_preparation",
    "performance_review",
}
DIRECTIONS = {
    "G1_客户价值获客",
    "G2_技术信任教育",
    "G3_能力品牌信任",
    "G4_报价方案教育",
}
READY_GATES = {"ready", "approved", "closed", "release_qc_ready", "internal_qc_ready"}
INTERNAL_STRATEGY_GATES = (
    "scope",
    "script_evidence",
    "source_assets",
    "voice",
    "bgm",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} 必须是非空文本")
    return value.strip()


def ensure_empty_dir(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.exists() and any(path.iterdir()):
        raise ValueError(f"输出目录已经有内容，拒绝覆盖: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"无法读取 YAML: {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML 解析失败: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"YAML 顶层必须是对象: {path}")
    return data


def write_yaml(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(dict(value), allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for value in values:
            handle.write(json.dumps(dict(value), ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSONL 解析失败: {path}:{line_number}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"JSONL 行必须是对象: {path}:{line_number}")
        records.append(row)
    return records


def workspace_ref(workspace: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path.resolve())


def is_pending(value: object) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return not text or text in {"pending", "待业务确认", "待工程业务审核", "待自动采集", "draft"}


def is_ready_gate(value: object) -> bool:
    return isinstance(value, str) and value.strip() in READY_GATES


def parse_published_at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def run_sort_key(run: Mapping[str, Any]) -> tuple[str, str]:
    return (str(run.get("run_date") or ""), str(run.get("run_id") or ""))


def role_runtime_summary(role_data: object) -> dict[str, Any]:
    """保留运行状态与引用，项目正文继续留在角色/项目真源。"""
    if not isinstance(role_data, dict):
        return {}
    result: dict[str, Any] = {}
    scalar_fields = (
        "status",
        "research_id",
        "project_id",
        "task_id",
        "batch_id",
        "variant_id",
        "render_id",
        "release_id",
        "review_id",
        "observation_state",
        "brief_state",
        "qc_state",
        "error_code",
        "block_reason",
        "next_receiver",
        "recommended_next_action",
        "acceptance_condition",
        "single_changed_atom",
        "evidence_boundary",
    )
    for field in scalar_fields:
        value = role_data.get(field)
        if isinstance(value, (str, int, float, bool)) and str(value).strip():
            result[field] = value
    for field in ("input_refs", "output_refs", "fact_pack_refs", "asset_reference_refs", "metric_source_refs"):
        value = role_data.get(field)
        if isinstance(value, list):
            result[field] = [str(item) for item in value if str(item).strip()]
    output_ref = role_data.get("output_ref")
    if isinstance(output_ref, str) and output_ref.strip():
        result["output_ref"] = output_ref
    return result


def load_runs(run_root: Path, workspace: Path) -> list[dict[str, Any]]:
    if not run_root.is_dir():
        raise ValueError(f"运行目录不存在: {run_root}")
    runs: list[dict[str, Any]] = []
    for path in sorted(run_root.glob("RUN-*.yaml")):
        value = load_yaml(path)
        run_id = required_text(value.get("run_id"), f"{path} run_id")
        runs.append(
            {
                "run_id": run_id,
                "run_date": str(value.get("run_date") or ""),
                "run_state": str(value.get("run_state") or ""),
                "primary_objective": str(value.get("primary_objective") or ""),
                "primary_direction": str(value.get("primary_direction") or ""),
                "path": workspace_ref(workspace, path),
                "next_transition": value.get("next_transition") if isinstance(value.get("next_transition"), dict) else {},
                "roles": {
                    role: role_runtime_summary(value.get(role))
                    for role in ROLE_KEYS
                },
            }
        )
    return sorted(runs, key=run_sort_key)


def release_observation(review_path: Path, workspace: Path) -> dict[str, Any]:
    review = load_yaml(review_path)
    release_id = required_text(review.get("release_id"), f"{review_path} release_id")
    account = review.get("account_binding") if isinstance(review.get("account_binding"), dict) else {}
    receipt = review.get("release_receipt") if isinstance(review.get("release_receipt"), dict) else {}
    metrics_24h = review.get("metrics_24h") if isinstance(review.get("metrics_24h"), dict) else {}
    metrics_7d = review.get("metrics_7d") if isinstance(review.get("metrics_7d"), dict) else {}
    decision = review.get("decision") if isinstance(review.get("decision"), dict) else {}
    published_at = parse_published_at(receipt.get("published_at"))
    has_receipt = bool(str(receipt.get("work_url_or_receipt_ref") or "").strip() or str(receipt.get("work_id") or "").strip())
    has_24h = bool(str(metrics_24h.get("captured_at") or "").strip())
    has_7d = bool(str(metrics_7d.get("captured_at") or "").strip())

    if has_7d:
        state = "metrics_7d_ready"
        receiver = "T00"
        action = "将同组样本送入 T10/T20，按可比性规则决定下一批。"
        runnable = True
    elif has_24h:
        state = "waiting_7d_window"
        receiver = "T40"
        action = "在 7d 窗口到达后采集同一作品的 7d 平台与业务数据。"
        runnable = published_at is not None and datetime.now(timezone.utc) >= published_at + timedelta(days=7)
    elif published_at is not None and has_receipt:
        state = "waiting_24h_window"
        receiver = "T40"
        action = "在 24h 窗口到达后采集同一作品的平台数据。"
        runnable = datetime.now(timezone.utc) >= published_at + timedelta(hours=24)
    elif has_receipt:
        state = "waiting_actual_published_at"
        receiver = "T40"
        action = "从公开作品页、授权只读页面或只读导出补入实际发布时间与时区。"
        runnable = False
    else:
        state = "waiting_platform_receipt"
        receiver = "T40"
        action = "取得作品链接、作品 ID 或平台/后台回执；现有 Owner 发布声明继续保留。"
        runnable = False

    due_24h = (published_at + timedelta(hours=24)).isoformat().replace("+00:00", "Z") if published_at else ""
    due_7d = (published_at + timedelta(days=7)).isoformat().replace("+00:00", "Z") if published_at else ""
    return {
        "schema_version": SCHEMA_VERSION,
        "work_item_id": f"WI-RELEASE-{release_id}",
        "kind": "release_observation",
        "release_id": release_id,
        "review_id": str(review.get("review_id") or ""),
        "project_id": str(review.get("project_id") or ""),
        "task_id": str(review.get("task_id") or ""),
        "variant_id": str(review.get("variant_id") or ""),
        "account_ref": str(account.get("account_subject_ref") or ""),
        "review_ref": workspace_ref(workspace, review_path),
        "state": state,
        "next_receiver": receiver,
        "next_action": action,
        "runnable": runnable,
        "published_at": receipt.get("published_at") or "",
        "due_24h": due_24h,
        "due_7d": due_7d,
        "platform_receipt_present": has_receipt,
        "metrics_24h_present": has_24h,
        "metrics_7d_present": has_7d,
        "comparison_status": str(decision.get("status") or ""),
        "error_codes": list((account.get("public_profile_discovery") or {}).get("error_codes") or []),
    }


def task_gate(task_path: Path, workspace: Path) -> dict[str, Any]:
    task = load_yaml(task_path)
    gate = task.get("production_gate") if isinstance(task.get("production_gate"), dict) else {}
    required_gate_names = (
        "fact_pack",
        "public_scope",
        "claim_approval",
        "market_data",
        "source_assets",
        "audio_rights",
    )
    missing = [{"field": field, "state": str(gate.get(field) or "pending")} for field in required_gate_names if not is_ready_gate(gate.get(field))]
    ready_for_openchatcut = bool(gate.get("ready_for_openchatcut")) and not missing
    ready_for_render = bool(gate.get("ready_for_render")) and not missing
    if ready_for_render:
        state = "ready_for_t30_render"
        next_receiver = "T30"
        action = "按 task_id、精确素材引用、批准范围和单变量定义创建内部渲染包。"
        runnable = True
    elif ready_for_openchatcut:
        state = "ready_for_t30_plan"
        next_receiver = "T30"
        action = "生成 OpenChatCut/本地 A/B/C 候选规划，保持内部审阅范围。"
        runnable = True
    else:
        state = "production_gate_waiting"
        next_receiver = "T20"
        action = "补齐下列精确事实/许可引用后生成 brief_ready 任务卡。"
        runnable = False
    return {
        "schema_version": SCHEMA_VERSION,
        "work_item_id": f"WI-TASK-{required_text(task.get('task_id'), f'{task_path} task_id')}",
        "kind": "production_gate",
        "task_id": task.get("task_id"),
        "project_id": task.get("project_id") or "",
        "task_ref": workspace_ref(workspace, task_path),
        "task_status": task.get("status") or "",
        "state": state,
        "next_receiver": next_receiver,
        "next_action": action,
        "runnable": runnable,
        "missing_gates": missing,
        "ready_for_openchatcut": ready_for_openchatcut,
        "ready_for_render": ready_for_render,
        "research_id": str((task.get("market_research") or {}).get("research_id") or ""),
        "primary_direction": str(task.get("primary_direction") or ""),
    }


def resolve_workspace_ref(workspace: Path, reference: object) -> Path | None:
    if not isinstance(reference, str) or not reference.strip():
        return None
    candidate = Path(reference.strip())
    path = candidate if candidate.is_absolute() else workspace / candidate
    path = path.expanduser().resolve()
    try:
        path.relative_to(workspace.resolve())
    except ValueError:
        return None
    return path


def reference_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def internal_strategy_production_work_item(
    latest_run: Mapping[str, Any] | None, workspace: Path
) -> dict[str, Any] | None:
    """只把通过内部策略门的 T20 产物路由给 T30。"""
    if not latest_run:
        return None
    roles = latest_run.get("roles")
    if not isinstance(roles, dict):
        return None
    t20 = roles.get("t20")
    if not isinstance(t20, dict) or str(t20.get("status") or "") not in {"ready", "partial", "blocked"}:
        return None

    run_id = str(latest_run.get("run_id") or "")
    run_ref = str(latest_run.get("path") or "")
    task_id = str(t20.get("task_id") or "")
    project_id = str(t20.get("project_id") or "")
    output_refs = reference_list(t20.get("output_refs"))
    output_refs.extend(reference_list(t20.get("output_ref")))
    strategy_ref = next((ref for ref in output_refs if ref.lower().endswith((".yaml", ".yml"))), "")
    missing: list[dict[str, str]] = []
    card: dict[str, Any] = {}
    if not strategy_ref:
        missing.append({"field": "strategy_card", "reason": "T20 尚未登记 YAML 策略卡引用"})
    else:
        strategy_path = resolve_workspace_ref(workspace, strategy_ref)
        if strategy_path is None or not strategy_path.is_file():
            missing.append({"field": "strategy_card", "reason": f"策略卡不可读取: {strategy_ref}"})
        else:
            try:
                card = load_yaml(strategy_path)
            except ValueError as exc:
                missing.append({"field": "strategy_card", "reason": str(exc)})

    if card:
        expected_fields = {
            "run_id": run_id,
            "project_id": project_id,
            "task_id": task_id,
        }
        for field, expected in expected_fields.items():
            actual = str(card.get(field) or "")
            if not expected or actual != expected:
                missing.append({"field": field, "reason": f"应为 {expected or '非空'}，实际为 {actual or '空'}"})
        if not str(card.get("strategy_id") or "").strip():
            missing.append({"field": "strategy_id", "reason": "缺少策略卡唯一标识"})
        if str(card.get("status") or "") != "internal_review_ready":
            missing.append({"field": "status", "reason": "策略卡状态必须为 internal_review_ready"})
        if str(card.get("delivery_scope") or "") != "internal_review_only":
            missing.append({"field": "delivery_scope", "reason": "策略卡仅可路由 internal_review_only"})
        gates = card.get("production_gates")
        if not isinstance(gates, dict):
            gates = {}
        for gate_name in INTERNAL_STRATEGY_GATES:
            gate = gates.get(gate_name)
            if not isinstance(gate, dict):
                missing.append({"field": gate_name, "reason": "缺少生产门"})
                continue
            if not is_ready_gate(gate.get("state")):
                missing.append({"field": gate_name, "reason": f"状态为 {gate.get('state') or '空'}"})
            if not reference_list(gate.get("refs")):
                missing.append({"field": gate_name, "reason": "缺少精确引用"})
    if str(t20.get("status") or "") != "ready":
        missing.append({"field": "t20_status", "reason": f"运行单状态为 {t20.get('status') or '空'}"})

    ready = not missing
    return {
        "schema_version": SCHEMA_VERSION,
        "work_item_id": f"WI-T30-PRODUCTION-{task_id or run_id}",
        "kind": "internal_production",
        "state": "ready_to_route" if ready else "production_gate_waiting",
        "next_receiver": "T30" if ready else "T20",
        "next_action": (
            "按内部策略卡创建可审阅候选成片与 QC 回执；保持 internal_review_only，禁止发布。"
            if ready
            else "补齐策略卡中列出的精确内部生产门；完成后由 T00 重投影。"
        ),
        "runnable": ready,
        "source_run_id": run_id,
        "project_id": project_id,
        "task_id": task_id,
        "strategy_ref": strategy_ref,
        "input_refs": [ref for ref in (run_ref, strategy_ref) if ref],
        "missing_gates": missing,
        "single_changed_atom": str(t20.get("single_changed_atom") or ""),
        "evidence_boundary": str(t20.get("evidence_boundary") or ""),
    }


def active_run_work_item(latest_run: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """活动运行单优先于任何新路由，避免同一日重复派工。"""
    if not latest_run:
        return None
    roles = latest_run.get("roles")
    if not isinstance(roles, dict):
        return None
    for role in ROLE_KEYS[1:]:
        role_data = roles.get(role)
        if not isinstance(role_data, dict) or str(role_data.get("status") or "") != "in_progress":
            continue
        run_id = str(latest_run.get("run_id") or "")
        inputs = [str(ref) for ref in role_data.get("input_refs") or [] if str(ref).strip()]
        run_ref = str(latest_run.get("path") or "")
        if run_ref:
            inputs.insert(0, run_ref)
        acceptance = str(role_data.get("acceptance_condition") or "指定产物")
        return {
            "schema_version": SCHEMA_VERSION,
            "work_item_id": f"WI-RUN-{run_id}-{ROLE_NAMES[role]}",
            "kind": ROLE_WORK_KINDS[role],
            "state": "in_progress",
            "next_receiver": ROLE_NAMES[role],
            "next_action": f"等待 {ROLE_NAMES[role]} 完成：{acceptance}",
            "runnable": False,
            "active_run_id": run_id,
            "input_refs": inputs,
            "single_changed_atom": str(role_data.get("single_changed_atom") or ""),
            "evidence_boundary": str(role_data.get("evidence_boundary") or ""),
        }
    return None


def research_work_item(latest_run: Mapping[str, Any] | None, workspace: Path) -> dict[str, Any]:
    input_refs: list[str] = []
    latest_run_id = ""
    t10_status = ""
    if latest_run:
        path = str(latest_run.get("path") or "")
        if path:
            input_refs.append(path)
        latest_run_id = str(latest_run.get("run_id") or "")
        roles = latest_run.get("roles")
        if isinstance(roles, dict):
            t10 = roles.get("t10")
            if isinstance(t10, dict):
                t10_status = str(t10.get("status") or "")
    if t10_status == "in_progress":
        return {
            "schema_version": SCHEMA_VERSION,
            "work_item_id": "WI-T10-MARKET-REFRESH-NEXT",
            "kind": "market_research",
            "state": "in_progress",
            "next_receiver": "T10",
            "next_action": "等待当前 T10 运行单产出指定市场快照；T00 读取完成状态后再路由下一角色。",
            "runnable": False,
            "active_run_id": latest_run_id,
            "input_refs": input_refs,
            "evidence_boundary": "公开样本只形成假设；自有账号、客户、报价和工程事实保持各自真源。",
        }
    if t10_status == "ready":
        return {
            "schema_version": SCHEMA_VERSION,
            "work_item_id": "WI-T10-MARKET-REFRESH-NEXT",
            "kind": "market_research",
            "state": "research_ready",
            "next_receiver": "T00",
            "next_action": "读取当前 T10 市场快照，并路由一条只使用该事实范围的 T20 策略工作。",
            "runnable": False,
            "active_run_id": latest_run_id,
            "input_refs": input_refs,
            "evidence_boundary": "公开样本只形成假设；自有账号、客户、报价和工程事实保持各自真源。",
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "work_item_id": "WI-T10-MARKET-REFRESH-NEXT",
        "kind": "market_research",
        "state": "ready_to_route",
        "next_receiver": "T10",
        "next_action": "以当前账号身份、公开可访问样本和一手工程资料生成新鲜市场快照；输出一个可证伪的 G2/G1 选题假设。",
        "runnable": True,
        "input_refs": input_refs,
        "evidence_boundary": "公开样本只形成假设；自有账号、客户、报价和工程事实保持各自真源。",
    }


def strategy_work_item(latest_run: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not latest_run:
        return None
    roles = latest_run.get("roles")
    if not isinstance(roles, dict):
        return None
    t10 = roles.get("t10")
    if not isinstance(t10, dict) or str(t10.get("status") or "") != "ready":
        return None
    research_id = str(t10.get("research_id") or "")
    output_ref = str(t10.get("output_ref") or "")
    if not research_id or not output_ref:
        return None
    run_id = str(latest_run.get("run_id") or "")
    run_ref = str(latest_run.get("path") or "")
    return {
        "schema_version": SCHEMA_VERSION,
        "work_item_id": f"WI-T20-STRATEGY-{research_id}",
        "kind": "content_strategy",
        "state": "ready_to_route",
        "next_receiver": "T20",
        "next_action": "在研究允许的事实边界内形成 G2 内部审阅策略卡；确定可制作范围、脚本/镜头候选和精确生产门，不扩展为客户、价格、工程结果或公开发布主张。",
        "runnable": True,
        "source_run_id": run_id,
        "input_refs": [ref for ref in (run_ref, output_ref) if ref],
        "single_changed_atom": str(t10.get("single_changed_atom") or ""),
        "evidence_boundary": str(t10.get("evidence_boundary") or ""),
    }


def derive_projection(
    workspace: Path,
    run_root: Path,
    release_root: Path,
    task_cards: Sequence[Path],
) -> dict[str, Any]:
    runs = load_runs(run_root, workspace)
    latest_run = runs[-1] if runs else None
    releases = [release_observation(path, workspace) for path in sorted(release_root.glob("REV-*.yaml"))]
    tasks = [task_gate(path, workspace) for path in task_cards]
    active_item = active_run_work_item(latest_run)
    role_work_items: list[dict[str, Any]]
    if active_item:
        role_work_items = [active_item]
    else:
        production = internal_strategy_production_work_item(latest_run, workspace)
        strategy = strategy_work_item(latest_run)
        role_work_items = [production or strategy or research_work_item(latest_run, workspace)]
    work_items = [*role_work_items, *tasks, *releases]
    work_items.sort(key=lambda item: (item["state"] != "in_progress", not bool(item["runnable"]), item["kind"], item["work_item_id"]))
    runnable = [item for item in work_items if item["runnable"]]
    active = [item for item in work_items if item["state"] == "in_progress"]
    current = active[0] if active else (runnable[0] if runnable else None)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_utc(),
        "workspace": str(workspace),
        "source_refs": {
            "run_root": workspace_ref(workspace, run_root),
            "release_root": workspace_ref(workspace, release_root),
            "task_cards": [workspace_ref(workspace, path) for path in task_cards],
        },
        "run_summary": {
            "total": len(runs),
            "latest_run_id": latest_run.get("run_id") if latest_run else "",
            "latest_run_state": latest_run.get("run_state") if latest_run else "",
            "runs": runs,
        },
        "release_summary": {
            "total": len(releases),
            "items": releases,
        },
        "task_summary": {
            "total": len(tasks),
            "items": tasks,
        },
        "work_items": work_items,
        "active_work_items": active,
        "current_executable": current,
    }


def render_status_md(projection: Mapping[str, Any]) -> str:
    current = projection.get("current_executable")
    lines = [
        "# KMDouyin｜日运行状态",
        "",
        "本页由运行单、项目任务卡和作品级回执派生；原始事实仍以各自真源为准。",
        "",
        "## 当前可执行工作",
        "",
    ]
    active = projection.get("active_work_items")
    if isinstance(active, list) and active:
        for item in active:
            lines.extend(
                [
                    f"- 正在执行：`{item.get('work_item_id', '')}` → `{item.get('next_receiver', '')}`",
                    f"- 当前动作：{item.get('next_action', '')}",
                ]
            )
    elif isinstance(current, dict):
        lines.extend(
            [
                f"- 工作项：`{current.get('work_item_id', '')}`",
                f"- 接收角色：`{current.get('next_receiver', '')}`",
                f"- 动作：{current.get('next_action', '')}",
            ]
        )
    else:
        lines.append("- 当前所有工作项均等待精确事实、批准或平台证据。")
    lines.extend(["", "## 工作队列", "", "| 工作项 | 状态 | 接收角色 | 可执行 |", "| --- | --- | --- | --- |"])
    for item in projection["work_items"]:
        lines.append(
            f"| `{item['work_item_id']}` | `{item['state']}` | `{item['next_receiver']}` | {'是' if item['runnable'] else '等待事实'} |"
        )
    lines.extend(
        [
            "",
            "## 原则",
            "",
            "- 一个工作项只引用既有真源，不复制客户、素材、审批或指标正文。",
            "- 公开样本支持选题假设；平台和业务指标必须绑定实际采集来源与时间。",
            "- T30 只接收通过生产门的任务卡；发布动作继续由 Owner/授权发布者执行。",
            "",
        ]
    )
    return "\n".join(lines)


def legacy_events(runs: Sequence[Mapping[str, Any]], existing: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    known_ids = {str(row.get("event_id") or "") for row in existing}
    events = list(existing)
    for run in runs:
        event_id = f"legacy-run:{run['run_id']}"
        if event_id in known_ids:
            continue
        events.append(
            {
                "event_id": event_id,
                "event_type": "run_registered",
                "occurred_at": now_utc(),
                "run_id": run["run_id"],
                "run_state": run["run_state"],
                "source_ref": run["path"],
                "actor": "T00",
                "boundary": "由既有 RUN 迁入运行总线索引；不复制原始事实。",
            }
        )
    return events


def cmd_project(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    run_root = Path(args.run_root).expanduser().resolve()
    release_root = Path(args.release_root).expanduser().resolve()
    task_cards = [Path(value).expanduser().resolve() for value in args.task_card]
    out_dir = ensure_empty_dir(Path(args.out_dir))
    projection = derive_projection(workspace, run_root, release_root, task_cards)
    events = legacy_events(projection["run_summary"]["runs"], read_jsonl(Path(args.event_log).expanduser().resolve() if args.event_log else None))
    events.append(
        {
            "event_id": f"projection:{projection['generated_at']}",
            "event_type": "control_plane_projected",
            "occurred_at": projection["generated_at"],
            "actor": "T00",
            "run_id": projection["run_summary"]["latest_run_id"],
            "current_executable_id": (projection.get("current_executable") or {}).get("work_item_id", ""),
        }
    )
    state = {
        key: projection[key]
        for key in (
            "schema_version",
            "generated_at",
            "workspace",
            "source_refs",
            "run_summary",
            "active_work_items",
            "current_executable",
        )
    }
    write_yaml(out_dir / "运行总线当前态.yaml", state)
    write_jsonl(out_dir / "工作项队列.jsonl", projection["work_items"])
    write_jsonl(out_dir / "发布观测索引.jsonl", projection["release_summary"]["items"])
    write_jsonl(out_dir / "运行事件.jsonl", events)
    (out_dir / "日运行状态.md").write_text(render_status_md(projection), encoding="utf-8")
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "created_at": projection["generated_at"],
        "operation": "project",
        "outputs": [
            "运行总线当前态.yaml",
            "工作项队列.jsonl",
            "发布观测索引.jsonl",
            "运行事件.jsonl",
            "日运行状态.md",
        ],
        "source_run_count": projection["run_summary"]["total"],
        "source_release_count": projection["release_summary"]["total"],
        "source_task_count": projection["task_summary"]["total"],
        "current_executable": projection.get("current_executable"),
        "formal_delivery": "调用方使用 rsync -a --inplace 迁入 KMDouyin 控制面，并读取目标文件确认。",
    }
    write_yaml(out_dir / "P0运行回执.yaml", receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


def new_run_document(args: argparse.Namespace) -> dict[str, Any]:
    run_id = required_text(args.run_id, "run_id")
    objective = required_text(args.objective, "objective")
    direction = required_text(args.direction, "direction")
    role = required_text(args.to_role, "to_role").lower()
    if objective not in OBJECTIVES:
        raise ValueError(f"objective 必须是: {', '.join(sorted(OBJECTIVES))}")
    if direction not in DIRECTIONS:
        raise ValueError(f"direction 必须是: {', '.join(sorted(DIRECTIONS))}")
    if role not in ROLE_KEYS or role == "t00":
        raise ValueError("to_role 必须是 t10、t20、t30 或 t40")
    roles: dict[str, Any] = {key: {"status": "not_scheduled"} for key in ROLE_KEYS}
    roles["t00"] = {
        "status": "in_progress",
        "decision_refs": list(args.decision_ref),
        "acceptance_condition": required_text(args.acceptance_condition, "acceptance_condition"),
    }
    target: dict[str, Any] = {
        "status": "in_progress",
        "input_refs": list(args.input_ref),
        "single_changed_atom": required_text(args.single_changed_atom, "single_changed_atom"),
        "evidence_boundary": required_text(args.evidence_boundary, "evidence_boundary"),
        "acceptance_condition": required_text(args.acceptance_condition, "acceptance_condition"),
        "recommended_next_action": required_text(args.next_action, "next_action"),
        "next_receiver": "T00",
    }
    if role == "t10":
        target.update({"research_id": args.research_id or "", "output_ref": args.output_ref or ""})
    elif role == "t20":
        target.update({"project_id": args.project_id or "", "task_id": args.task_id or "", "output_refs": [args.output_ref] if args.output_ref else []})
    elif role == "t30":
        target.update(
            {
                "project_id": args.project_id or "",
                "task_id": args.task_id or "",
                "batch_id": args.batch_id or "",
                "variant_id": args.variant_id or "",
                "output_refs": [args.output_ref] if args.output_ref else [],
            }
        )
    else:
        target.update(
            {
                "project_id": args.project_id or "",
                "task_id": args.task_id or "",
                "release_id": args.release_id or "",
                "review_id": args.review_id or "",
                "output_ref": args.output_ref or "",
            }
        )
    roles[role] = target
    return {
        "schema_version": 1,
        "run_id": run_id,
        "run_date": args.run_date or datetime.now().date().isoformat(),
        "owner": "T00",
        "run_state": f"{role}_in_progress",
        "primary_objective": objective,
        "primary_direction": direction,
        "resource_boundary": required_text(args.resource_boundary, "resource_boundary"),
        **roles,
        "next_transition": {
            "required_state": f"{role}_ready_or_precisely_blocked",
            "required_refs": [args.output_ref] if args.output_ref else [],
            "receiving_role": "T00",
            "next_action": required_text(args.next_action, "next_action"),
        },
    }


def cmd_new_run(args: argparse.Namespace) -> int:
    out_dir = ensure_empty_dir(Path(args.out_dir))
    document = new_run_document(args)
    run_path = out_dir / f"{document['run_id']}.yaml"
    write_yaml(run_path, document)
    created_at = now_utc()
    handoff = {
        "schema_version": SCHEMA_VERSION,
        "handoff_id": f"HANDOFF-{document['run_id']}-{args.to_role.upper()}",
        "created_at": created_at,
        "run_id": document["run_id"],
        "from_role": "T00",
        "to_role": args.to_role.upper(),
        "state": "in_progress",
        "input_refs": list(args.input_ref),
        "output_refs": [args.output_ref] if args.output_ref else [],
        "single_changed_atom": args.single_changed_atom,
        "evidence_boundary": args.evidence_boundary,
        "acceptance_condition": args.acceptance_condition,
        "next_action": args.next_action,
    }
    write_json(out_dir / "交接包.json", handoff)
    event = {
        "event_id": f"run_created:{document['run_id']}:{created_at}",
        "event_type": "run_created",
        "occurred_at": created_at,
        "run_id": document["run_id"],
        "role": "T00",
        "status": document["run_state"],
        "input_refs": list(args.input_ref),
        "next_receiver": args.to_role.upper(),
    }
    write_jsonl(out_dir / "运行事件增量.jsonl", [event])
    events = [*read_jsonl(Path(args.event_log).expanduser().resolve() if args.event_log else None), event]
    write_jsonl(out_dir / "运行事件.jsonl", events)
    print(json.dumps({"run": str(run_path), "handoff": handoff, "event": event}, ensure_ascii=False, indent=2))
    return 0


def update_role_document(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    source_path = Path(args.run_file).expanduser().resolve()
    document = load_yaml(source_path)
    role = required_text(args.role, "role").lower()
    if role not in ROLE_KEYS:
        raise ValueError("role 必须是 t00、t10、t20、t30 或 t40")
    role_data = document.get(role)
    if not isinstance(role_data, dict):
        role_data = {}
        document[role] = role_data
    role_data["status"] = required_text(args.status, "status")
    if args.input_ref:
        role_data["input_refs"] = list(args.input_ref)
    if args.output_ref:
        if "output_refs" in role_data:
            role_data["output_refs"] = list(args.output_ref)
        else:
            role_data["output_ref"] = args.output_ref[-1]
    if args.error_code:
        role_data["error_code"] = args.error_code
    if args.block_reason:
        role_data["block_reason"] = args.block_reason
    if args.next_action:
        role_data["recommended_next_action"] = args.next_action
    if args.acceptance_condition:
        role_data["acceptance_condition"] = args.acceptance_condition
    if args.single_changed_atom:
        role_data["single_changed_atom"] = args.single_changed_atom
    if args.evidence_boundary:
        role_data["evidence_boundary"] = args.evidence_boundary
    if args.run_state:
        document["run_state"] = args.run_state
    document["next_transition"] = {
        "required_state": args.required_state or "",
        "required_refs": list(args.required_ref),
        "receiving_role": args.next_receiver or "T00",
        "next_action": args.next_action or "",
    }
    event = {
        "event_id": f"handoff:{document.get('run_id', '')}:{role}:{now_utc()}",
        "event_type": "role_status_updated",
        "occurred_at": now_utc(),
        "run_id": document.get("run_id", ""),
        "role": ROLE_NAMES[role],
        "status": role_data["status"],
        "output_refs": list(args.output_ref),
        "error_code": args.error_code or "",
        "next_receiver": args.next_receiver or "T00",
    }
    return document, event


def cmd_handoff(args: argparse.Namespace) -> int:
    out_dir = ensure_empty_dir(Path(args.out_dir))
    document, event = update_role_document(args)
    write_yaml(out_dir / f"{document['run_id']}.yaml", document)
    write_jsonl(out_dir / "运行事件增量.jsonl", [event])
    events = [*read_jsonl(Path(args.event_log).expanduser().resolve() if args.event_log else None), event]
    write_jsonl(out_dir / "运行事件.jsonl", events)
    write_json(out_dir / "交接结果.json", {"run_id": document["run_id"], "event": event})
    print(json.dumps({"run_id": document["run_id"], "event": event}, ensure_ascii=False, indent=2))
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    task_path = Path(args.task_card).expanduser().resolve()
    out_dir = ensure_empty_dir(Path(args.out_dir))
    result = task_gate(task_path, workspace)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "created_at": now_utc(),
        "operation": "production_preflight",
        **result,
        "result": "ready" if result["runnable"] else "waiting_exact_gate_refs",
    }
    write_yaml(out_dir / "生产门结果.yaml", receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if result["runnable"] else 3


def cmd_observe_release(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    review_path = Path(args.review).expanduser().resolve()
    out_dir = ensure_empty_dir(Path(args.out_dir))
    observation = release_observation(review_path, workspace)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "created_at": now_utc(),
        "operation": "release_observation",
        **observation,
    }
    write_yaml(out_dir / "发布观测结果.yaml", receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


def load_component_candidates(path: Path, workspace: Path) -> list[dict[str, Any]]:
    document = load_yaml(path)
    rows = document.get("components")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"组件候选清单必须包含非空 components 列表: {path}")
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"组件候选第 {index} 条必须是对象")
        component_id = required_text(row.get("component_id"), f"组件候选第 {index} 条 component_id")
        if component_id in seen:
            raise ValueError(f"组件候选 ID 重复: {component_id}")
        seen.add(component_id)
        source_ref = required_text(row.get("source_ref"), f"组件候选 {component_id} source_ref")
        candidates.append(
            {
                "schema_version": SCHEMA_VERSION,
                "component_id": component_id,
                "name": required_text(row.get("name"), f"组件候选 {component_id} name"),
                "component_type": required_text(row.get("component_type"), f"组件候选 {component_id} component_type"),
                "project_id": str(row.get("project_id") or ""),
                "render_id": str(row.get("render_id") or ""),
                "source_ref": source_ref,
                "evidence_ref": str(row.get("evidence_ref") or workspace_ref(workspace, path)),
                "status": "candidate_review_required",
                "reuse_scope": "internal_review_only",
                "approval_ref": "",
                "promotion_gate": "T30 绑定目标任务、适用场景、权利/审批范围与一次复用结果后，T00 才能提升为受控模板。",
                "claim_boundary": str(row.get("claim_boundary") or ""),
                "created_at": now_utc(),
            }
        )
    return candidates


def cmd_catalog_components(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    candidate_path = Path(args.candidate_file).expanduser().resolve()
    out_dir = ensure_empty_dir(Path(args.out_dir))
    existing = read_jsonl(Path(args.catalog).expanduser().resolve() if args.catalog else None)
    candidates = load_component_candidates(candidate_path, workspace)
    existing_ids = {str(row.get("component_id") or "") for row in existing}
    duplicate_ids = sorted({row["component_id"] for row in candidates if row["component_id"] in existing_ids})
    if duplicate_ids:
        raise ValueError(f"组件候选已登记，拒绝重复写入: {', '.join(duplicate_ids)}")
    catalog = [*existing, *candidates]
    write_jsonl(out_dir / "组件候选登记.jsonl", catalog)
    lines = [
        "# KMDouyin｜共享表达组件候选",
        "",
        "本登记只保存组件身份、来源和提升门；源文件仍位于项目交付包。",
        "",
        "| 组件 | 类型 | 当前状态 | 复用范围 | 来源 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in catalog:
        lines.append(
            f"| `{row.get('component_id', '')}` | `{row.get('component_type', '')}` | `{row.get('status', '')}` | `{row.get('reuse_scope', '')}` | `{row.get('source_ref', '')}` |"
        )
    lines.append("")
    (out_dir / "组件候选状态.md").write_text("\n".join(lines), encoding="utf-8")
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "created_at": now_utc(),
        "operation": "catalog_components",
        "candidate_source": workspace_ref(workspace, candidate_path),
        "catalog_count": len(catalog),
        "new_candidate_count": len(candidates),
        "promotion_boundary": "所有本轮组件保持 candidate_review_required / internal_review_only。",
    }
    write_yaml(out_dir / "组件候选回执.yaml", receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


def add_common_out_dir(command: argparse.ArgumentParser) -> None:
    command.add_argument("--out-dir", required=True, help="新的本机暂存输出目录")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    project = commands.add_parser("project", help="把既有运行与事实引用投影为日控制面")
    project.add_argument("--workspace", required=True)
    project.add_argument("--run-root", required=True)
    project.add_argument("--release-root", required=True)
    project.add_argument("--task-card", action="append", required=True)
    project.add_argument("--event-log", help="既有运行事件账；仅在本机读取后带入新暂存包")
    add_common_out_dir(project)
    project.set_defaults(func=cmd_project)

    new_run = commands.add_parser("new-run", help="创建一个角色已绑定的日运行单与交接包")
    new_run.add_argument("--run-id", required=True)
    new_run.add_argument("--event-log", help="既有运行事件账；读取后带入新的完整暂存账")
    new_run.add_argument("--run-date")
    new_run.add_argument("--objective", required=True)
    new_run.add_argument("--direction", required=True)
    new_run.add_argument("--resource-boundary", required=True)
    new_run.add_argument("--to-role", required=True)
    new_run.add_argument("--input-ref", action="append", default=[])
    new_run.add_argument("--decision-ref", action="append", default=[])
    new_run.add_argument("--output-ref")
    new_run.add_argument("--single-changed-atom", required=True)
    new_run.add_argument("--evidence-boundary", required=True)
    new_run.add_argument("--acceptance-condition", required=True)
    new_run.add_argument("--next-action", required=True)
    new_run.add_argument("--research-id")
    new_run.add_argument("--project-id")
    new_run.add_argument("--task-id")
    new_run.add_argument("--batch-id")
    new_run.add_argument("--variant-id")
    new_run.add_argument("--release-id")
    new_run.add_argument("--review-id")
    add_common_out_dir(new_run)
    new_run.set_defaults(func=cmd_new_run)

    handoff = commands.add_parser("handoff", help="把一个角色的结果或精确阻塞写入新的运行单副本")
    handoff.add_argument("--run-file", required=True)
    handoff.add_argument("--event-log", help="既有运行事件账；读取后带入新的完整暂存账")
    handoff.add_argument("--role", required=True)
    handoff.add_argument("--status", required=True)
    handoff.add_argument("--run-state")
    handoff.add_argument("--input-ref", action="append", default=[])
    handoff.add_argument("--output-ref", action="append", default=[])
    handoff.add_argument("--error-code")
    handoff.add_argument("--block-reason")
    handoff.add_argument("--single-changed-atom")
    handoff.add_argument("--evidence-boundary")
    handoff.add_argument("--acceptance-condition")
    handoff.add_argument("--required-state")
    handoff.add_argument("--required-ref", action="append", default=[])
    handoff.add_argument("--next-receiver")
    handoff.add_argument("--next-action")
    add_common_out_dir(handoff)
    handoff.set_defaults(func=cmd_handoff)

    preflight = commands.add_parser("preflight", help="生成商业任务卡的生产门结果")
    preflight.add_argument("--workspace", required=True)
    preflight.add_argument("--task-card", required=True)
    add_common_out_dir(preflight)
    preflight.set_defaults(func=cmd_preflight)

    observe = commands.add_parser("observe-release", help="生成作品级回执的 24h/7d 观测状态")
    observe.add_argument("--workspace", required=True)
    observe.add_argument("--review", required=True)
    add_common_out_dir(observe)
    observe.set_defaults(func=cmd_observe_release)

    components = commands.add_parser("catalog-components", help="登记共享表达组件候选，不提升公开或商业使用资格")
    components.add_argument("--workspace", required=True)
    components.add_argument("--candidate-file", required=True)
    components.add_argument("--catalog", help="既有组件候选登记 JSONL；读取后写入新的完整暂存包")
    add_common_out_dir(components)
    components.set_defaults(func=cmd_catalog_components)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except ValueError as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
