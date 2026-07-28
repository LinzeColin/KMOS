# -*- coding: utf-8 -*-
"""今天已经确认发成功过，再跑一次不算失败。

2026-07-28 全量压测当场抓到的：boot sweep 在 19:30 重跑 attendance-evening，
而 17:32 那一轮**已经确认送达张霖泽**。去重守卫正确地拦住了第二次发送，
但这条被记成 `NOT_SENT_DUPLICATE_GUARD` → FAILED → rc=5 → 台账一个 ❌。

守卫干对了事却被记成失败，就是**假红**。假红比不报还糟：
红灯天天亮、次次都不是真问题，最后一定被人当噪音关掉，
真出事那次也就跟着一起被忽略了。而这个假红还是我自己的 boot sweep 造出来的
——「所有技能主动压测」这条要求，不能靠把好路径染红来满足。

但也**不能一刀切成绿**：拦住的那次「先前尝试」有两种，要修的地方完全不同：
  · 先前是确认 SENT ——当天的契约已经达成，不重发是对的，绿。
  · 先前只是 SEND_STARTED / SENT_UNVERIFIED ——我们其实**不知道**它到底出去没有，
    现在又拒绝重试，那正是 Owner 该看见的状态，必须留红。
把这两种并成一档，就退回到 #270 之前「rc=0 只代表进程没崩」的老毛病。
"""
from __future__ import annotations

from KMFA.tools.dingtalk_attendance.run_attendance import result_exit_code

GUARD = "NOT_SENT_DUPLICATE_GUARD"


def _result(notification_status: str, *, blocked_on: str | None = None, status: str = "COMPLETED"):
    payload = {"status": status, "notification_status": notification_status}
    if blocked_on is not None:
        payload["duplicate_guard_blocked_on"] = blocked_on
    return payload


def test_guard_on_a_confirmed_send_is_green():
    """17:32 确认发出去了，19:30 压测重跑被拦——当天契约已达成。"""
    assert result_exit_code(_result(GUARD, blocked_on="SENT")) == 0, \
        "确认送达过还判红，就是 boot sweep 自己造的假红"


def test_guard_on_an_unconfirmed_attempt_stays_red():
    """先前那次只是「开始发」，没有送达凭据——现在还拒绝重试，必须让人看见。"""
    rc = result_exit_code(_result(GUARD, blocked_on="SEND_STARTED"))
    assert rc != 0, "拿不准发没发出去还报绿，就是 #270 修掉的那个老毛病复发"


def test_guard_on_an_unverified_send_stays_red():
    """SENT_UNVERIFIED 是「命令没报错但没凭据」，同样不算达成。"""
    assert result_exit_code(_result(GUARD, blocked_on="SENT_UNVERIFIED")) != 0


def test_guard_without_provenance_stays_red():
    """不知道拦的是哪一种时，按红处理——判据缺失不许往绿的方向倒。"""
    assert result_exit_code(_result(GUARD)) != 0, \
        "先前状态未知就报绿，等于默认一切都好"


def test_the_two_guard_outcomes_do_not_share_one_code():
    """两种成因的退出码要分得开，否则又回到「一个码对十来种原因」。"""
    green = result_exit_code(_result(GUARD, blocked_on="SENT"))
    red = result_exit_code(_result(GUARD, blocked_on="SEND_STARTED"))
    assert green != red


def test_a_real_failure_is_still_red():
    """修假红不能把真红一起弄绿。"""
    assert result_exit_code(_result("FAILED")) != 0
    assert result_exit_code(_result("NOTIFIER_CONFIG_MISSING")) != 0
    assert result_exit_code(_result("SENT_UNVERIFIED")) == 8, "8 是「发了但没凭据」的专属码"


def test_the_guard_receipt_records_what_it_blocked_on():
    """守卫回执必须写明拦的是哪一种——不然上面那套判据无源可依。"""
    import inspect

    from KMFA.tools.dingtalk_attendance import notification_targets as nt

    src = inspect.getsource(nt)
    assert "duplicate_guard_blocked_on" in src, \
        "回执没记先前那次的状态，退出码就只能瞎猜"
