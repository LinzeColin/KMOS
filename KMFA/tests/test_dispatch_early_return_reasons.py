"""派发早退必须说清原因（2026-07-20 主机实测：FAILED 却无 failure_reason）。"""
import json
from pathlib import Path

from KMFA.tools.dingtalk_attendance.notification_targets import dispatch_reports_to_targets


def _status(tmp_path, targets):
    resolved = tmp_path / "resolved.json"
    resolved.write_text(json.dumps({"targets": targets}, ensure_ascii=False), encoding="utf-8")
    out = {
        "dispatch_receipt": str(tmp_path / "receipt.json"),
        # stats 必须真过完整性 gate，否则先撞上更早的分支（那条本来就带 reason，行为正确），
        # 测不到本次要验的「零目标」路径
        "stats": {
            "realtime_reminder_run_type": "morning",
            "realtime_reminder_integrity_status": "PASS",
            "attendance_group_member_count": 3, "member_count": 3,
            "realtime_reminder_expected_count": 3, "realtime_reminder_coverage_count": 3,
            "realtime_reminder_query_failure_count": 0,
            "realtime_reminder_parse_failure_count": 0,
            "realtime_reminder_anomaly_count": 0,
            "realtime_reminder_anomaly_names": [],
        },
        "run_type": "morning", "work_date": "2026-07-20", "run_id": "T1",
    }
    return dispatch_reports_to_targets(output_status=out, targets_resolved_path=resolved)


def test_no_target_says_why(tmp_path):
    """零目标不得退化成裸 FAILED——排查的人只能看着 FAILED 猜。"""
    r = _status(tmp_path, [])
    assert r["notification_status"] == "NOT_SENT_NO_TARGET_SELECTED"
    assert "no target selected" in r["failure_reason"]
    assert "total=0" in r["failure_reason"] and "filter=all" in r["failure_reason"]
    assert r["notification_status"] != "FAILED"


def test_all_disabled_says_which(tmp_path):
    r = _status(tmp_path, [{"label": "张霖泽", "type": "personal", "enabled": False}])
    assert r["notification_status"] == "NOT_SENT_ALL_TARGETS_DISABLED"
    assert "张霖泽" in r["failure_reason"]


def test_every_early_return_carries_reason(tmp_path):
    """凡是"没发出去"的收据，都必须带非空 failure_reason。"""
    for targets in ([], [{"label": "A", "type": "personal", "enabled": False}]):
        r = _status(tmp_path, targets)
        assert r["notification_status"].startswith("NOT_SENT_")
        assert r.get("failure_reason"), f"{r['notification_status']} 缺 failure_reason"
        Path(r["dispatch_receipt"] if "dispatch_receipt" in r else tmp_path / "receipt.json")
