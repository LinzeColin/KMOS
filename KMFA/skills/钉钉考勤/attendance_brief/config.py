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
        # 干净的单群实测（两个并发，取墙钟）：
        #   2026-09-08  KMMEDIA 22 秒 · KMFILE 72 秒
        #   2026-09-09  KMMEDIA 74 秒 · KMFILE 114 秒
        # 240 秒 ≈ 实测上限的两倍。原来的 600 是跟资金线取齐的猜测值，
        # 而调用方是**同步等**这笔预算的：归档一卡住，简报要等满 600 秒 + 收尾
        # 才开始跑，17:15 的简报能被拖到 17:26 之后。归档是热身，不是交付物，
        # 被砍断完全无害（它幂等，下一轮接着跑），简报迟到才是真损失。
        self.archive_budget = int(os.environ.get("KMFA_BRIEF_ARCHIVE_BUDGET", "240"))
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
        # 发送窗口的**上沿**：出报时刻往后几小时之内还算数，过了就今天不发了。
        # 下沿一直有（SKIP_BEFORE_PUBLISH），上沿以前没有 —— 只要有任何一条路
        # 能在深夜把脚本拉起来（机器睡着错过了钟点、launchd 醒来补跑、
        # 有人半夜点了 Run），简报就会在北京 23 点冒进生产管理群。
        # 老板 2026-09-10 定过这条：在非指定时间冒出消息，等于自动化失控。
        # 今天没发是可修的（看门狗第二天早上会说），半夜发出去是不可修的。
        self.window_hours = int(os.environ.get("KMFA_BRIEF_WINDOW_HOURS", "4"))
        # ——— 生产部周报（连续在岗 / 在岗待核实 / 打卡规范）———
        # 只看生产部全口径（含车工/焊工/钳工/调度/车间/司机/各项目组等下级）。
        # 老板 2026-09-15 定的：这条规则只对生产部的人。
        self.dept_root = os.environ.get("KMFA_BRIEF_DEPT_ROOT", "生产部").strip()
        # 连续在岗门槛：连续到岗满这么多天就进本周名单，休一天即归零。
        #
        # 为什么 24 天不会误伤办公室 / 行政 / 管理这些双休岗 —— 是算术，不是名单：
        # 每周只要休 1 天，连续到岗最长就是 12 天（上周休周一、这周休周日）。
        # 要满 24 天，必须连着三周一天没休。所以这条线天然筛掉所有正常休息的人，
        # 不需要维护任何岗位白名单 —— 入职、离职、调岗、转外派全都不用管。
        # 180 天全量实测佐证：双休岗最大连续 7–19 天，一线 24–87 天，交集 0 人。
        self.rest_threshold = int(os.environ.get("KMFA_BRIEF_REST_THRESHOLD", "24"))
        # 取数窗口。只判「够不够门槛」、不对外报天数，所以窗口比门槛长就够；
        # 32 天正好是 query-data 的单次跨度上限，于是永远只有一个分片、2 次调用。
        # 实测：32 天窗口与 180 天窗口算出的名单完全一致，而调用次数是 2 对 12 ——
        # 钉钉网关是阵发性失败，少一次调用就少一次暴露。
        self.weekly_window_days = int(os.environ.get("KMFA_BRIEF_WEEKLY_DAYS", "32"))
        # 在册却一次卡都没打，连续这么多天就点出来核实（走了请假流程的除外）。
        self.zero_punch_days = int(os.environ.get("KMFA_BRIEF_ZERO_PUNCH_DAYS", "10"))
        # 迟到 / 缺卡 / 补卡本月累计到这个次数才进打卡规范那一块。
        self.discipline_threshold = int(os.environ.get("KMFA_BRIEF_DISCIPLINE", "3"))
        # 人员表往回找几天。周报跑在周一，业务日是周日，那天没有人员表，
        # 必须能回溯到周五 —— 至少要 3，给 5 是留节假日的余量。
        self.roster_lookback = int(os.environ.get("KMFA_BRIEF_ROSTER_LOOKBACK", "5"))
        # 发送窗口（北京，分钟）。这条线排在上午，窗口给到 08:00–12:00。
        # 跟日报一样上下沿都有：Codex 会补跑错过的计划，没有上沿就会在半夜冒出来。
        self.weekly_window = (
            int(os.environ.get("KMFA_BRIEF_WEEKLY_FROM", "480")),      # 08:00
            int(os.environ.get("KMFA_BRIEF_WEEKLY_TO", "720")))        # 12:00
        self.dws = os.path.expanduser(os.environ.get("KMFA_BRIEF_DWS", "~/.local/bin/dws"))

    def month_dir(self, day: str) -> Path:
        return self.archive_root / day.replace("-", "")[:6]
