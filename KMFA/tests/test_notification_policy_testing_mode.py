# -*- coding: utf-8 -*-
"""测试期投递策略的守卫。

Owner 2026-07-26：「目前都还是测试阶段，不要发到群聊里了，除非我授权，测试发送人是张霖泽」。

这条一直只做了一半：开关关了、群机器人凭据也移除了，**但策略里的投递目标仍是 group**，
于是每次排程都先走群通道、每次都发不出去——公开健康端点实测考勤连续 rc=5（通知未送达）。
本测试钉住这半条，免得它再被改回去而没人发现。
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "metadata" / "dingtalk_attendance" / "notification_policy.yaml"


def _policy():
    return yaml.safe_load(POLICY.read_text(encoding="utf-8"))


def test_scheduled_target_is_personal_during_testing():
    assert _policy()["scheduled_delivery_target_filter"] == "personal", (
        "测试期排程投递目标必须是 personal。改回 group 前须 Owner 当场授权，"
        "并同时用 coolify-ops 的 sync-dingtalk 恢复群机器人凭据——"
        "只改这一行会让排程重新走一个没有凭据的通道，每次静默失败。"
    )


def test_group_robot_is_last_resort():
    prio = _policy()["channel_priority"]
    assert prio[0] != "dingtalk_group_robot", "测试期群机器人不得排在第一优先"
    assert prio[-1] == "dingtalk_group_robot", "群机器人应退到最后，作为授权后才启用的通道"


def test_personal_channel_is_first_and_recipient_is_owner():
    p = _policy()
    assert p["channel_priority"][0] == "dws_ding_personal"
    assert p["recipient_policy"]["zhang_linze_dingtalk_user_id"], "测试收件人必须具名配置"


def test_policy_records_why_it_is_personal():
    """把原因写在文件里，下一个人改之前先看见代价。"""
    raw = POLICY.read_text(encoding="utf-8")
    assert "测试阶段" in raw and "rc=5" in raw
