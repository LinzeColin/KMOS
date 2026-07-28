# -*- coding: utf-8 -*-
"""「发出去了」必须有钉钉收下的凭据，退出码 0 不算。

2026-07-28 查明的事故：`_dws_result_to_status` 里 `SENT` 的**唯一判据**是
dws 命令退出码为 0——既不看钉钉有没有收下，也把成功时的返回体整个丢掉。
于是台账绿、回执写着 SENT，而 Owner 整整一个月一条都没收到。

Owner 原话：「考勤为什么不发啊 卧槽 你都浪费我一个月的时间了」。

退出码只说明**进程没崩**。这组测试钉死三档必须分得开：

  · `SENT`             —— 退出码 0 **且**返回体里有投递凭据
  · `SENT_UNVERIFIED`  —— 退出码 0 但没凭据：不是失败，**更不是成功**
  · `FAILED`           —— 命令报错

把中间那档并进任何一边，都是这次事故本身：并进 SENT 就继续骗人，
并进 FAILED 就分不出该查错误码还是该查 dws 返回体。
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from KMFA.tools.dingtalk_attendance import notifier_dws_personal_chat as N  # noqa: E402
from KMFA.tools.dingtalk_attendance import run_attendance as R  # noqa: E402

CHANNEL = "dws_open_dingtalk_id_chat"


def _ok(payload):
    return {"returncode": 0, "payload": payload}


def test_exit_zero_without_evidence_is_not_sent():
    """这就是那一个月的形状：命令成功，什么凭据都没有。"""
    got = N._dws_result_to_status(_ok({"ok": True}), channel=CHANNEL)
    assert got["status"] == "SENT_UNVERIFIED"
    assert got["failure_reason"]


def test_exit_zero_with_evidence_is_sent():
    got = N._dws_result_to_status(_ok({"result": {"messageId": "msg-123"}}), channel=CHANNEL)
    assert got["status"] == "SENT"
    assert got["trace_id"] == "msg-123"


@pytest.mark.parametrize("key", [
    "messageId", "message_id", "msgId", "processQueryKey", "taskId", "requestId", "traceId"])
def test_evidence_keys_are_recognised_under_any_common_name(key):
    """各接口命名不统一，按 key 名匹配而不是按固定路径取。"""
    got = N._dws_result_to_status(_ok({"data": {key: "X1"}}), channel=CHANNEL)
    assert got["status"] == "SENT" and got["trace_id"] == "X1"


def test_evidence_is_found_however_deep_it_is_nested():
    got = N._dws_result_to_status(
        _ok({"a": {"b": [{"c": {"msg_id": "deep"}}]}}), channel=CHANNEL)
    assert got["status"] == "SENT" and got["trace_id"] == "deep"


def test_an_empty_evidence_value_does_not_count():
    """键在但值是空的，等于没有——不能靠键名存在就判成功。"""
    for empty in ("", "   ", None):
        got = N._dws_result_to_status(_ok({"messageId": empty}), channel=CHANNEL)
        assert got["status"] == "SENT_UNVERIFIED"


def test_an_error_payload_is_still_failed():
    got = N._dws_result_to_status(
        {"returncode": 0, "payload": {"error": {"errcode": 88, "message": "无权限"}}},
        channel=CHANNEL)
    assert got["status"] == "FAILED"


def test_unverified_keeps_payload_keys_for_diagnosis():
    """留**键名**不留值：值可能含会话或员工标识。
    这是下次要补凭据键时唯一的线索——不留就只能再猜一轮。"""
    got = N._dws_result_to_status(_ok({"ok": True, "elapsed": 12}), channel=CHANNEL)
    assert set(got["payload_keys"]) == {"ok", "elapsed"}


def test_unverified_does_not_leak_payload_values():
    got = N._dws_result_to_status(
        _ok({"conversationId": "", "员工": "张三的敏感值"}), channel=CHANNEL)
    assert "张三的敏感值" not in str(got)


# ── 一路贯通：汇总 / 退出码 ─────────────────────────────────────────────
def test_summary_keeps_unverified_as_its_own_bucket():
    assert R._summarize_notification_status(["SENT", "SENT_UNVERIFIED"]) == "SENT_UNVERIFIED"
    assert R._summarize_notification_status(["SENT", "SENT"]) == "SENT"
    assert R._summarize_notification_status(["SENT_UNVERIFIED", "FAILED"]) == "FAILED"


def test_unverified_exits_nonzero_and_distinctly():
    """必须非零（否则继续绿着骗人），且必须区别于 5（明确失败）——
    5 去看错误码，8 去看 dws 返回了什么，混成一个码排查方向就没了。"""
    unverified = R.result_exit_code(
        {"status": "COMPLETED", "notification_status": "SENT_UNVERIFIED"})
    assert unverified == 8
    assert R.result_exit_code({"status": "COMPLETED", "notification_status": "FAILED"}) == 5
    assert R.result_exit_code({"status": "COMPLETED", "notification_status": "SENT"}) == 0
