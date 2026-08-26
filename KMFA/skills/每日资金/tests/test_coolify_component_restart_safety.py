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
    assert 'service.get("environment_id") != environment_id' in step
    assert 'service.get("destination_id") != destination_id' in step
    assert 'service.get("destination_type") != destination_type' in step
    assert "contains_daily_funds_component(compose)" in step
    assert "if len(matching_services) != 1" in step
    assert 'component.get("name") == "daily-funds"' in step
    assert "if len(matching_components) != 1" in step
    assert '"$BASE/api/v1/services/$service_uuid/applications/$component_uuid/restart"' in step
    assert "app_compose" not in step
