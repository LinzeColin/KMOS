# -*- coding: utf-8 -*-
"""判据对了没用，字段得真送到判据手上。

2026-07-28 线上抓到的：#273 给去重守卫加了 `duplicate_guard_blocked_on`，
让「今天已确认送达、本轮正确没重发」判绿。判据函数本身是对的，
`run_attendance` 却只把回执整个塞进嵌套的 `dispatch_receipt`，
**没把这个字段抬到顶层**——而 `result_exit_code` 只读顶层。
于是线上取到的永远是 None，照旧判 5、照旧假红。

当时的单元测试之所以全绿，是因为它**喂了一个自己造的字典**，
字段是我手放进去的，真调用方从来不放。测了判据、没测接线——
跟这条线反复栽的「绿的但没干活」是同一个形状，只是这次栽在自己的修复上。

所以这里锚的不是判据，是**接线**：从守卫写回执，一路到退出码。
"""
from __future__ import annotations

import inspect

from KMFA.tools.dingtalk_attendance import run_attendance as RA


def test_the_field_is_lifted_to_the_top_level():
    """**每一个**带着派发回执返回的路径，都要把这个键抬到顶层。

    留在 `dispatch_receipt` 嵌套里等于没接——退出码那边看不见。
    这里按语法树定位，不靠「离某个字符串多少个字符」——那种写法在同一个字符串
    出现五次时会锚错地方（第一次写这条测试就锚在了 906 行那个提前返回上）。
    """
    import ast

    tree = ast.parse(inspect.getsource(RA))
    checked = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Dict):
            continue
        keys = {k.value for k in node.value.keys if isinstance(k, ast.Constant)}
        # 只有「真做了派发」的返回才可能带守卫状态；提前返回的那几条产生不了它。
        if "dispatch_receipt" not in keys:
            continue
        checked += 1
        assert "duplicate_guard_blocked_on" in keys, \
            f"这条返回带了派发回执却没把守卫成因抬到顶层：键={sorted(keys)}"
    assert checked >= 1, "一条带派发回执的返回都没找到——前提变了，重新审这条测试"


def test_the_exit_code_reads_the_same_key_the_result_writes():
    """写的键和读的键必须是同一个——这条防的正是「两边各写各的」。"""
    src = inspect.getsource(RA)
    written = '"duplicate_guard_blocked_on": dispatch_receipt.get(' in src
    read = 'result.get("duplicate_guard_blocked_on")' in src
    assert written and read, f"写={written} 读={read}——有一边没接上"


def test_a_guard_receipt_flows_end_to_end_to_a_green_exit_code():
    """把守卫真写出来的那种回执，按真调用方的组装方式喂进退出码。

    不自己造字典——造字典正是上次漏掉接线的原因。
    """
    from KMFA.tools.dingtalk_attendance import notification_targets as NT

    receipt = NT._targets_receipt(
        status="NOT_SENT_DUPLICATE_GUARD",
        output_status={"run_id": "r2", "run_type": "evening", "work_date": "2026-07-28"},
        target_results=[],
        failure_reason="an earlier send or send attempt already exists",
    )
    receipt["duplicate_guard_blocked_on"] = "SENT"      # 守卫源码里就是这么写的

    # 按 send_latest_report_only 的组装方式还原 result
    result = {
        "status": receipt["notification_status"],
        "notification_status": receipt["notification_status"],
        "duplicate_guard_blocked_on": receipt.get("duplicate_guard_blocked_on"),
        "dispatch_receipt": receipt,
    }
    assert RA.result_exit_code(result) == 0, "端到端仍然判红——接线没通"


def test_the_same_flow_stays_red_when_the_earlier_attempt_was_unconfirmed():
    """接线通了也不能一律判绿：先前只是「开始发」的，仍然要红。"""
    from KMFA.tools.dingtalk_attendance import notification_targets as NT

    receipt = NT._targets_receipt(
        status="NOT_SENT_DUPLICATE_GUARD",
        output_status={"run_id": "r2", "run_type": "evening", "work_date": "2026-07-28"},
        target_results=[],
        failure_reason="an earlier send or send attempt already exists",
    )
    receipt["duplicate_guard_blocked_on"] = "SEND_STARTED"
    result = {
        "status": receipt["notification_status"],
        "notification_status": receipt["notification_status"],
        "duplicate_guard_blocked_on": receipt.get("duplicate_guard_blocked_on"),
        "dispatch_receipt": receipt,
    }
    assert RA.result_exit_code(result) != 0
