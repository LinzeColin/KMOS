"""KMFA 钉钉考勤 skill runtime package."""

from KMFA.tools.dingtalk_attendance.identity import SKILL_ID

AUTOMATION_NAME = "每日早晚钉钉考勤检查"
TIMEZONE = "Asia/Shanghai"
ONEDRIVE_ROOT = "/Users/linzezhang/OneDrive/dingtalk_attendance"
# 收件人标识必须是 dws 可反查的真实 userId。
# 2026-07-20 主机实测更正：旧值 "1iv-1t2oesv2yd" 反查 `dws contact user get --ids` 返回
# 全 null 的 orgEmployeeModel（解析不出人）。此前投递之所以仍能送达 Owner，靠的是
# notification_targets._resolve_user() 在拿不到 openDingTalkId 时按 label「张霖泽」做**姓名搜索兜底**——
# 而姓名兜底取 records[0]，**一旦组织内重名就可能命中他人**。故改为真实 userId，
# 使解析确定化、不再依赖姓名搜索。
ZHANG_LINZE_USER_ID = "01256723246324629191"
