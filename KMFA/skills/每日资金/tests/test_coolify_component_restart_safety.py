"""Safety contract for the exact daily-funds component restart action."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_component_restart_binds_exact_component_inside_the_same_runtime() -> None:
    workflow = (ROOT.parents[2] / ".github" / "workflows" / "coolify-ops.yml").read_text(encoding="utf-8")
    start = workflow.index("精确重启每日资金组件")
    end = workflow.index("受控强制重建每日资金恢复目标", start)
    step = workflow[start:end]

    assert "inputs.mode == 'daily-funds-recovery-component-restart'" in step
    assert 'app.get("name") != "kmfa-kmos-p1"' in step
    assert 'app.get("build_pack") != "dockercompose"' in step
    assert "def runtime_key(record: dict):" in step
    assert 'for key in ("environment_id", "destination_id", "destination_type"):' in step
    assert "target_runtime = runtime_key(app)" in step
    assert "runtime_key(service) != target_runtime" in step
    assert "contains_daily_funds_component(compose)" in step
    assert "if len(matching_services) != 1" in step
    assert 'component.get("name") == "daily-funds"' in step
    assert "if len(matching_components) != 1" in step
    assert '"$BASE/api/v1/services/$service_uuid/applications/$component_uuid/restart"' in step
    assert "app_compose" not in step


def test_runtime_topology_is_read_only_and_values_free() -> None:
    workflow = (ROOT.parents[2] / ".github" / "workflows" / "coolify-ops.yml").read_text(encoding="utf-8")
    start = workflow.index("只读分类每日资金运行拓扑")
    end = workflow.index("受控强制重建每日资金恢复目标", start)
    step = workflow[start:end]

    assert "inputs.mode == 'daily-funds-runtime-topology'" in step
    assert 'GITHUB_REF:-}" = "refs/heads/main"' in step
    assert '"$BASE/api/v1/applications/$APP"' in step
    assert '"$BASE/api/v1/services"' in step
    assert '"$BASE/api/v1/applications"' in step
    assert "daily_funds_runtime_topology_target=VERIFIED" in step
    assert "daily_funds_runtime_topology_service_component" in step
    assert "daily_funds_runtime_topology_application_component" in step
    assert "daily_funds_runtime_topology={topology}" in step
    assert "-X POST" not in step
    assert "-X PATCH" not in step
    assert "-X DELETE" not in step


def test_worker_log_probe_is_read_only_and_values_free() -> None:
    workflow = (ROOT.parents[2] / ".github" / "workflows" / "coolify-ops.yml").read_text(encoding="utf-8")
    start = workflow.index("只读汇总每日资金 worker 运行回执")
    end = workflow.index("受控强制重建每日资金恢复目标", start)
    step = workflow[start:end]

    assert "daily-funds-worker-logs" in workflow
    assert "inputs.mode == 'daily-funds-worker-logs'" in step
    assert 'GITHUB_REF:-}" = "refs/heads/main"' in step
    assert "daily_funds_worker_logs=MAIN_REF_REQUIRED" in step
    assert "daily_funds_worker_logs=APP_REQUIRED" in step
    assert "daily_funds_worker_logs=APP_INVALID" in step
    assert '"$BASE/api/v1/applications/$APP/logs?lines=200&service=daily-funds"' in step
    assert "summarize_coolify_logs.py" in step
    assert "daily-funds-worker-logs.out" in step
    assert "trap 'rm -f" in step
    assert "cat " not in step
    assert "json.dumps" not in step
    assert "-X POST" not in step
    assert "-X PATCH" not in step
    assert "-X DELETE" not in step


def test_app_log_probe_is_read_only_and_values_free() -> None:
    workflow = (ROOT.parents[2] / ".github" / "workflows" / "coolify-ops.yml").read_text(encoding="utf-8")
    start = workflow.index("只读汇总 KMFA app 运行状态")
    end = workflow.index("受控强制重建每日资金恢复目标", start)
    step = workflow[start:end]

    assert "daily-funds-app-logs" in workflow
    assert "inputs.mode == 'daily-funds-app-logs'" in step
    assert 'GITHUB_REF:-}" = "refs/heads/main"' in step
    assert "daily_funds_app_logs=MAIN_REF_REQUIRED" in step
    assert "daily_funds_app_logs=APP_REQUIRED" in step
    assert "daily_funds_app_logs=APP_INVALID" in step
    assert '"$BASE/api/v1/applications/$APP/logs?lines=200&service=app"' in step
    assert "summarize_coolify_logs.py" in step
    assert "daily-funds-app-logs.out" in step
    assert "trap 'rm -f" in step
    assert "cat " not in step
    assert "json.dumps" not in step
    assert "-X POST" not in step
    assert "-X PATCH" not in step
    assert "-X DELETE" not in step


def test_public_routing_audit_is_values_free_and_service_specific() -> None:
    workflow = (ROOT.parents[2] / ".github" / "workflows" / "coolify-ops.yml").read_text(encoding="utf-8")
    start = workflow.index("只读核对 KMFA app 服务域名接线")
    end = workflow.index("受控强制重建每日资金恢复目标", start)
    step = workflow[start:end]

    assert "daily-funds-public-routing-audit" in workflow
    assert "inputs.mode == 'daily-funds-public-routing-audit'" in step
    assert 'GITHUB_REF:-}" = "refs/heads/main"' in step
    assert '"$BASE/api/v1/applications/$APP"' in step
    assert 'EXPECTED_DOMAIN = "kmfa.linzezhang.com"' in step
    assert "daily_funds_public_routing_target=" in step
    assert "daily_funds_public_routing_app_service_marker=" in step
    assert "daily_funds_public_routing_expected_domain=" in step
    assert "print(raw)" not in step
    assert "print(payload)" not in step
    assert "-X POST" not in step
    assert "-X PATCH" not in step
    assert "-X DELETE" not in step
