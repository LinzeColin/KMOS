# -*- coding: utf-8 -*-
"""失败码提取的边界测试。

这个模块的价值全在**它出的东西能不能公开**。考勤日志里有员工姓名和打卡明细，
生产成本日志里有客户名和金额；只要有一条能拼进公开端点，就是一次数据泄露。
所以测试的重点不是"能不能提取到码"，而是"能不能构造出不该出现的东西"。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from KMFA.tools.skill_failure_code import UNKNOWN, extract, is_public_safe, tail


def test_picks_the_notification_status_that_decided_the_exit_code():
    """rc=5 就是 notification_status 判出来的，那就得报出是哪一个。"""
    log = """2026-07-27T10:35:01 attendance-morning: 开始
{"status": "COMPLETED", "notification_status": "NOT_SENT_DWS_AUTH_REQUIRED"}
2026-07-27T10:36:02 attendance-morning: 结束 rc=5"""
    assert extract(log) == "NOT_SENT_DWS_AUTH_REQUIRED"


def test_takes_the_last_status_not_the_first():
    """一次运行会写很多次状态，只有最后落定的那个决定退出码。"""
    log = '{"notification_status": "NOT_SENT"}\n{"notification_status": "NOT_SENT_DWS_UNAVAILABLE"}'
    assert extract(log) == "NOT_SENT_DWS_UNAVAILABLE"


def test_falls_back_to_the_exception_class_when_there_is_no_status():
    log = "Traceback (most recent call last):\n  File \"x.py\", line 3\nurllib.error.HTTPError: 403 禁止访问"
    assert extract(log) == "HTTPError"


def test_a_plain_colon_line_is_not_mistaken_for_an_exception():
    """`说明: xxx` 这种行到处都是，不能当异常类名报出去。"""
    assert extract("Note: 归档完成\nSummary: 一切正常") == UNKNOWN


def test_success_words_do_not_occupy_the_failure_slot():
    assert extract('{"status": "COMPLETED"}\n{"collection_status": "OK"}') == UNKNOWN


def test_nothing_useful_says_unknown_instead_of_guessing():
    assert extract("") == UNKNOWN
    assert extract("张霖泽 09:12 打卡正常\n客户 武汉某某 金额 40960322.77") == UNKNOWN


# ——— 公开安全性：这些是真正在防的东西 ———

def test_chinese_can_never_become_a_public_code():
    """日志里的中文包含姓名和客户名——必须构造不出来，而不是被过滤掉。"""
    log = '{"notification_status": "投递失败张霖泽未读"}'
    assert extract(log) == UNKNOWN
    assert not is_public_safe("投递失败")


def test_amounts_and_paths_can_never_become_a_public_code():
    for hostile in ("40960322.77", "/var/log/kmfa/attendance-morning/2026.log",
                    "ghp_AAAABBBBCCCCDDDDEEEEFFFFGGGGHHHH", "a b c", "", "X", "12345"):
        assert not is_public_safe(hostile), hostile


def test_every_extracted_code_is_public_safe_by_construction():
    """提取器的输出**永远**能过公开校验——这是 app 侧敢直接发的前提。"""
    samples = [
        '{"notification_status": "NOT_SENT_OWNER_DISABLED"}',
        "ValueError: 客户名 武汉开明 缺失",
        "张霖泽 打卡 09:12",
        "",
        '{"status": "DWS_AUTH_REQUIRED"} 金额 ¥40,960,322.77',
    ]
    for text in samples:
        assert is_public_safe(extract(text)), text


# ——— 私有取证尾巴 ———

def test_tail_keeps_business_detail_but_never_credentials():
    """尾巴进私有库，业务信息可以留；凭据进了私有库也是事故。"""
    log = "\n".join([
        "张霖泽 09:12 打卡正常",
        "token=ghp_AAAABBBBCCCCDDDDEEEEFFFFGGGGHHHH 调用失败",
        "sig=0123456789abcdef0123456789abcdef",
    ])
    out = tail(log)
    assert "张霖泽" in out, "私有库要的就是这些细节"
    assert "ghp_AAAABBBB" not in out and "0123456789abcdef0123456789abcdef" not in out


def test_tail_is_bounded_so_one_runaway_log_cannot_blow_up_the_ledger():
    out = tail("\n".join(f"line {i} " + "x" * 900 for i in range(500)), lines=40)
    assert len(out.splitlines()) == 40
    assert all(len(line) <= 400 for line in out.splitlines())
