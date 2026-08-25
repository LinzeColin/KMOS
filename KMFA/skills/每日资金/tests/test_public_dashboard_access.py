"""Contracts for the explicit Owner public-dashboard Access override."""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_funds.public_dashboard_access import (  # noqa: E402
    PUBLIC_DASHBOARD_BYPASS_POLICY_NAME,
    PUBLIC_DASHBOARD_ROOT_APPLICATION_NAME,
    PublicDashboardAccessError,
    capture_public_dashboard_application_id,
    public_dashboard_bypass_policy_payload,
    public_dashboard_bypass_policy_state,
    public_dashboard_root_application_count,
    public_dashboard_root_application_payload,
    public_origin_guard_entry_ids,
    public_origin_guard_state,
    select_public_dashboard_application_ids,
    main,
)


OPS_ID = "2d7ac813-4f60-4d2f-9c69-8d5294e4c7fe"
API_ID = "20b0c6f3-77f1-4591-8f4a-d643709b42cf"
ROOT_ID = "b2b3c4d5-1e2f-4a5b-8c9d-0e1f2a3b4c5d"
ROOT_WILDCARD_ID = "c2b3c4d5-1e2f-4a5b-8c9d-0e1f2a3b4c5d"
POLICY_ID = "a2b3c4d5-1e2f-4a5b-8c9d-0e1f2a3b4c5d"
PROBE_CONTROL_ID = "d2b3c4d5-1e2f-4a5b-8c9d-0e1f2a3b4c5d"
RECOVERY_CONTROL_ID = "e2b3c4d5-1e2f-4a5b-8c9d-0e1f2a3b4c5d"


def _apps(items: list[object]) -> dict[str, object]:
    return {"success": True, "result_info": {"total_pages": 1}, "result": items}


def _policy(items: list[object]) -> dict[str, object]:
    return {"success": True, "result_info": {"total_pages": 1}, "result": items}


def test_selects_only_exact_host_dashboard_access_applications() -> None:
    payload = _apps([
        {"id": OPS_ID, "type": "self_hosted", "domain": "kmfa.linzezhang.com/ops/*"},
        {"id": API_ID, "type": "self_hosted", "destinations": [{"type": "public", "uri": "kmfa.linzezhang.com/api/*"}]},
        {"id": POLICY_ID, "type": "self_hosted", "domain": "other.linzezhang.com/api/*"},
        {"id": ROOT_ID, "type": "self_hosted", "domain": "kmfa.linzezhang.com/"},
        {"id": ROOT_WILDCARD_ID, "type": "self_hosted", "domain": "kmfa.linzezhang.com/*"},
        {"id": PROBE_CONTROL_ID, "type": "self_hosted", "domain": "kmfa.linzezhang.com/ops/api/daily-funds/history-probe"},
        {"id": RECOVERY_CONTROL_ID, "type": "self_hosted", "destinations": [{"type": "public", "uri": "kmfa.linzezhang.com/ops/api/daily-funds/recovery/*"}]},
    ])

    assert select_public_dashboard_application_ids(payload) == tuple(
        sorted((OPS_ID, API_ID, ROOT_ID, ROOT_WILDCARD_ID))
    )


@pytest.mark.parametrize("payload", [
    _apps([]),
    _apps([{"id": OPS_ID, "type": "self_hosted", "domain": "kmfa.linzezhang.com/unrelated"}]),
    _apps([{"id": OPS_ID, "type": "self_hosted", "domain": "kmfa.linzezhang.com:8443/ops/*"}]),
    {"success": True, "result_info": {"total_pages": 2}, "result": []},
])
def test_selection_fails_closed_for_incomplete_or_non_target_provider_results(payload: object) -> None:
    with pytest.raises(PublicDashboardAccessError):
        select_public_dashboard_application_ids(payload)


def test_fixed_bypass_policy_is_idempotently_recognized() -> None:
    expected = {
        "name": PUBLIC_DASHBOARD_BYPASS_POLICY_NAME,
        "decision": "bypass",
        "include": [{"everyone": {}}],
    }
    assert public_dashboard_bypass_policy_payload() == expected
    assert public_dashboard_bypass_policy_state(_policy([])) == "MISSING"
    assert public_dashboard_bypass_policy_state(_policy([{**expected, "id": POLICY_ID}])) == "PRESENT"
    assert public_dashboard_bypass_policy_state(_policy([{**expected, "id": POLICY_ID, "exclude": [{"everyone": {}}]}])) == "INVALID"


def test_exact_host_root_application_can_be_created_without_touching_wildcard_hosts() -> None:
    payload = _apps([
        {"id": OPS_ID, "type": "self_hosted", "domain": "kmfa.linzezhang.com/ops/*"},
        {"id": POLICY_ID, "type": "self_hosted", "domain": "*.linzezhang.com/*"},
    ])
    assert public_dashboard_root_application_count(payload) == 0
    assert public_dashboard_root_application_payload() == {
        "name": PUBLIC_DASHBOARD_ROOT_APPLICATION_NAME,
        "domain": "kmfa.linzezhang.com",
        "type": "self_hosted",
        "app_launcher_visible": False,
    }

    exact_root = _apps([
        {"id": ROOT_ID, "type": "self_hosted", "domain": "kmfa.linzezhang.com"},
        {"id": ROOT_WILDCARD_ID, "type": "self_hosted", "domain": "kmfa.linzezhang.com/*"},
    ])
    assert public_dashboard_root_application_count(exact_root) == 2
    assert capture_public_dashboard_application_id({"success": True, "result": {"id": ROOT_ID}}) == ROOT_ID
    with pytest.raises(PublicDashboardAccessError):
        capture_public_dashboard_application_id({"success": True, "result": {"id": "not-an-id"}})


def test_origin_guard_requires_all_existing_representations_to_be_disabled() -> None:
    payload = [
        {"key": "KMFA_PRIVATE_OPS_REQUIRE_ACCESS", "value": "0", "uuid": "env-a"},
        {"key": "KMFA_PRIVATE_OPS_REQUIRE_ACCESS", "value": "0", "uuid": "env-b"},
        {"key": "KMFA_PUBLIC_SHELL_ENABLED", "value": "1", "uuid": "env-c"},
    ]
    assert public_origin_guard_state(payload) == "PRESENT"
    assert public_origin_guard_entry_ids(payload) == ("env-a", "env-b")
    payload[1]["value"] = "1"
    assert public_origin_guard_state(payload) == "INVALID"


def test_cli_writes_only_selected_application_ids_with_private_permissions(tmp_path: Path) -> None:
    source = tmp_path / "apps.json"
    target = tmp_path / "selected.txt"
    source.write_text(json.dumps(_apps([
        {"id": OPS_ID, "type": "self_hosted", "domain": "kmfa.linzezhang.com/ops/*"},
        {"id": POLICY_ID, "type": "self_hosted", "domain": "other.linzezhang.com/ops/*"},
    ])), encoding="utf-8")

    assert main(["select-apps", str(source), str(target)]) == 0
    assert target.read_text(encoding="utf-8") == f"{OPS_ID}\n"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_cli_writes_created_root_application_id_privately(tmp_path: Path) -> None:
    source = tmp_path / "created.json"
    target = tmp_path / "created.txt"
    source.write_text(json.dumps({"success": True, "result": {"id": ROOT_ID}}), encoding="utf-8")

    assert main(["capture-app-id", str(source), str(target)]) == 0
    assert target.read_text(encoding="utf-8") == f"{ROOT_ID}\n"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
