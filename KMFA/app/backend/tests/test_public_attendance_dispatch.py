# -*- coding: utf-8 -*-
"""考勤投递回执的公开端点。

Owner 2026-07-28：「考勤我没有收到」。

台账里考勤 `rc=0`，看着是绿的——但绿只代表**进程正常退出**，不代表**消息发出去了**。
真相在容器里的 `*.dispatch.json` 回执里，而 Coolify 的 `exec` 实测 404、`logs` 空、
`/api/*` 在 Access 后面而 Owner 不登录。这个端点就是把那份证据搬到能读到的地方。

最要紧的一条是**公开边界**：回执里同时躺着 `management_report`／`hr_report`／
`notification_template_text`——那是全员考勤正文。端点用白名单，不是黑名单；
测试必须真的去断言那几个字段不在响应里，否则将来回执加字段就会默认泄露。
"""
import json

from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)
URL = "/public-api/考勤投递"

SENT = {
    "notification_status": "SENT",
    "channel": "multi_target",
    "run_id": "R-20260728-0801",
    "run_type": "morning",
    "work_date": "2026-07-28",
    "target_results": [
        {"label": "张霖泽", "status": "SENT", "channel": "dws_open_dingtalk_id_chat",
         "user_id": "机密员工标识"},
    ],
    "management_report": "全员考勤明细：张三迟到 12 分钟……",
    "hr_report": "HR 口径全员明细……",
    "notification_template_text": "【开明考勤提醒】今日未打卡：张三、李四",
}

NOT_SENT = {
    "notification_status": "NOTIFIER_CONFIG_MISSING",
    "channel": "multi_target",
    "run_type": "evening",
    "work_date": "2026-07-27",
    "failure_reason": "missing targets resolved file: /var/log/.../notification_targets_resolved.json",
    "target_results": [],
    "management_report": "全员考勤明细……",
    "hr_report": "……",
    "notification_template_text": "……",
}


def _archive(tmp_path, monkeypatch, *receipts):
    month = tmp_path / "202607"
    month.mkdir(parents=True, exist_ok=True)
    for index, payload in enumerate(receipts):
        name = (f"dingtalk_attendance_{payload.get('run_type','x')}_20260728_"
                f"{index:03d}.dispatch.json")
        (month / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(main, "ATTENDANCE_ARCHIVE_ROOT", tmp_path)
    return tmp_path


def test_lives_on_the_anonymous_surface():
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert URL in paths and URL.startswith("/public-api/")


def test_missing_archive_says_so_instead_of_an_empty_list(tmp_path, monkeypatch):
    """空列表和读不到长得一样，意思完全相反。"""
    monkeypatch.setattr(main, "ATTENDANCE_ARCHIVE_ROOT", tmp_path / "nope")
    body = client.get(URL).json()
    assert body["可读"] is False
    assert body["原因"]
    assert body["投递"] == []


def test_a_sent_receipt_reads_as_actually_sent(tmp_path, monkeypatch):
    _archive(tmp_path, monkeypatch, SENT)
    body = client.get(URL).json()
    assert body["可读"] is True
    assert body["最近一次是否真的发出"] is True
    row = body["投递"][0]
    assert row["notification_status"] == "SENT"
    assert row["目标"][0]["对象"] == "张霖泽" and row["目标"][0]["成功"] is True


def test_a_green_run_that_sent_nothing_is_not_reported_as_sent(tmp_path, monkeypatch):
    """这就是「考勤我没有收到」的形状：进程 rc=0，回执却是 CONFIG_MISSING。"""
    _archive(tmp_path, monkeypatch, NOT_SENT)
    body = client.get(URL).json()
    assert body["最近一次是否真的发出"] is False
    row = body["投递"][0]
    assert row["notification_status"] == "NOTIFIER_CONFIG_MISSING"
    assert row["failure_reason"], "没发就必须说为什么没发"
    assert row["目标"] == []


def test_report_bodies_never_reach_the_public_surface(tmp_path, monkeypatch):
    """白名单不是黑名单——回执里的考勤正文一个字都不能出去。"""
    _archive(tmp_path, monkeypatch, SENT, NOT_SENT)
    text = client.get(URL).text
    for leaked in ("全员考勤明细", "张三", "李四", "HR 口径", "机密员工标识",
                   "management_report", "hr_report", "notification_template_text"):
        assert leaked not in text, f"公开面泄露了 {leaked!r}"


def test_unknown_future_fields_do_not_leak_by_default(tmp_path, monkeypatch):
    """将来回执加字段，默认必须是不出——这正是用白名单的理由。"""
    payload = dict(SENT, 新增字段="将来某个人加的敏感东西")
    _archive(tmp_path, monkeypatch, payload)
    assert "将来某个人加的敏感东西" not in client.get(URL).text


def test_a_corrupt_receipt_is_named_not_swallowed(tmp_path, monkeypatch):
    month = tmp_path / "202607"
    month.mkdir(parents=True)
    (month / "broken.dispatch.json").write_text("{ 不是 JSON", encoding="utf-8")
    monkeypatch.setattr(main, "ATTENDANCE_ARCHIVE_ROOT", tmp_path)
    row = client.get(URL).json()["投递"][0]
    assert row["可读"] is False and row["原因"]


def test_is_not_indexable_and_not_cached(tmp_path, monkeypatch):
    _archive(tmp_path, monkeypatch, SENT)
    headers = client.get(URL).headers
    assert "noindex" in headers.get("x-robots-tag", "")
    assert headers.get("cache-control") == "no-store"
