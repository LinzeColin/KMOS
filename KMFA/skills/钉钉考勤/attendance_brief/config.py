"""配置：全部来自环境变量，仓库里只放键名，真值留在机器上。"""
import os
from pathlib import Path

def _req(key: str) -> str:
    v = os.environ.get(key, "").strip()
    if not v:
        raise SystemExit(f"缺少环境变量 {key}，请先配置 private_runtime/kmfa_brief.env")
    return v

class Config:
    def __init__(self) -> None:
        self.slot = os.environ.get("KMFA_RUN_SLOT", "evening").strip().lower()
        # 数据源
        self.group_id = _req("KMFA_BRIEF_GROUP_ID")            # 生产管理群
        # 发布人姓名是员工个人信息，不进仓库 —— 跟群 id 一样只留键名，真值在机器上。
        self.publishers = [s for s in _req("KMFA_BRIEF_PUBLISHERS").split(",") if s.strip()]
        # 落点：全部在 SMB
        self.archive_root = Path(_req("KMFA_BRIEF_ARCHIVE_ROOT"))
        self.runtime_root = Path(_req("KMFA_BRIEF_RUNTIME_ROOT"))
        # 发送目标
        self.notify_user = _req("KMFA_BRIEF_NOTIFY_USER")      # 张霖泽 userId
        self.notify_group = os.environ.get("KMFA_BRIEF_NOTIFY_GROUP", "").strip()
        self.send_enabled = os.environ.get("KMFA_BRIEF_SEND", "0") == "1"
        # 只有调度器（kmfa_brief_cron.sh）会置这一位。手工在终端里跑脚本时它是空的，
        # 于是只出报不发送 —— 排查、改参数、试新逻辑都不可能误发进真实工作群。
        # 要手工发真的，显式加 --send。
        self.scheduled = os.environ.get("KMFA_BRIEF_SCHEDULED", "0") == "1"
        # 限时
        self.wall_clock_limit = int(os.environ.get("KMFA_BRIEF_TIMEOUT", "330"))
        # 出报前先归档一遍自己这个群，让下游读到的钉钉原件是完整的。
        # 只跑生产管理群一个群 —— 全公司全量是 KMFile / KMMedia 各自每日任务的职责，
        # 不是考勤简报该扛的（实测全量单轮 20 分钟以上）。
        self.group_title = os.environ.get("KMFA_BRIEF_GROUP_TITLE", "生产管理群").strip()
        # 两个归档并发跑的合计墙钟预算（秒）。防止把简报拖到下班，不是范围闸。
        # 600 秒是跟资金线取齐的经验值，**还没有一次干净的单群实测**——
        # 2026-09-07 那次测量撞上共享盘掉线，182 秒全在报错，不算数。
        # 拿到第一次干净的单群耗时后回来修正这个默认值。
        self.archive_budget = int(os.environ.get("KMFA_BRIEF_ARCHIVE_BUDGET", "600"))
        # 出报时刻（北京）。这也是人员表的截止线 —— 两者是同一个时刻：
        # 简报什么时候发，人员表就得在那之前到，晚于它就是迟发。
        # 它同时是「两个触发钟点里挑哪一个」的判据 —— 本机有夏令时而北京没有，
        # 一年里只有一个钟点等于北京 17:15，另一个必然早一小时，靠这道闸挡掉。
        self.publish_hour = int(os.environ.get("KMFA_BRIEF_PUBLISH_HOUR", "17"))
        self.publish_minute = int(os.environ.get("KMFA_BRIEF_PUBLISH_MINUTE", "15"))
        # 截止线默认就等于出报时刻。留 override 只是为了「万一哪天要分开」，
        # 正常情况不要动它 —— 分开了会让「迟发」和「什么时候能看到简报」对不上。
        self.deadline = os.environ.get(
            "KMFA_BRIEF_DEADLINE",
            f"{self.publish_hour:02d}:{self.publish_minute:02d}").strip()
        self.dws = os.path.expanduser(os.environ.get("KMFA_BRIEF_DWS", "~/.local/bin/dws"))

    def month_dir(self, day: str) -> Path:
        return self.archive_root / day.replace("-", "")[:6]
