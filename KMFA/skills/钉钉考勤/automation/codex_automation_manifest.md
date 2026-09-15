# Codex Automation 登记

考勤异常简报的调度由 **Codex automation** 承担。本机那份
`~/.codex/automations/<id>/automation.toml` 不进 Git，本文件是它的可移植镜像。

**必须用 Codex 自己的 `create_automation` 建（在 Codex 里说一句话让它建），不要手写 toml**
—— 手写的文件不会注册进 app，界面里看不到，也不会触发。Codex 工具说明原话：
「Never write raw automation directives by hand」。

**已知限制：id 指定不了。** `create_automation` 不接受自定义 id，也不能改写；
中文名字生成不出 slug，所以 id 就是 `automation` / `automation-2`。
认名字，别认 id —— 名字是对的，而且跟 `每日资金卡片（付款请示群）`、
`商务投标简报 每日发送（商务部报价群）` 同一个风格。

## 两条，不多不少

| 项 | 出报 | 看门狗 |
| --- | --- | --- |
| id | `automation` | `automation-2` |
| 名称 | 考勤异常简报 每工作日发送（生产管理群） | 考勤看门狗 + 出勤累计（生产管理群） |
| rrule | `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=19,20,21;BYMINUTE=15` | 同前缀，`BYHOUR=10;BYMINUTE=50` |
| 本机时间 | 每工作日 19:15 / 20:15 / 21:15 | 每工作日 10:50 |
| 调的命令 | `scripts/kmfa_brief_cron.sh` | `scripts/kmfa_brief_watchdog.sh`<br>`scripts/kmfa_monthly_cron.sh` |

其余字段两条相同：`status=ACTIVE`、`model=scnet-deepseek-v4-flash-0731`（张霖泽指定，别改）、
`reasoning_effort=max`、`execution_environment=local`、
`cwds=["/Users/linzezhang/Documents/Codex"]`、
`project_id=b4e5abb7-70bb-463b-a484-d4ef000d8601`（与 kmfa-daily-funds、kmbid-daily 同一个）。
出报那条的 `prompt` = 本目录 `kmfa_attendance_brief.prompt.md` 逐字原文。

**这条线永远只有两条 automation。** 2026-09-15 之前是「主 19:15 + 备位 20:15」两条都出报、
没有看门狗；现在三个钟点收进同一条 rrule（跟 `kmfa-daily-funds` 的 `BYHOUR=14,15` 一个写法），
腾出来的那条改成看门狗 —— **automation 总数没变，槽位从 2 个变 3 个，还多了停摆检测。**
每加一条 automation 都要多一份治理成本，能靠 rrule 多写一个钟点解决的，就不要新建。

**为什么每条不止一个钟点。** 本机是 Australia/Sydney 有夏令时，北京没有。
`2026-10-04` 悉尼转夏令时那天，本机 19:15 从北京 17:15 变成 16:15 —— 早于出报时刻，
会被「未到出报时刻」闸挡掉：

| | 本机 19:15 | 20:15 | 21:15 | 窗口内趟数 |
| --- | --- | --- | --- | --- |
| AEST（现在） | 北京 17:15 | 18:15 | 19:15 | 3 |
| AEDT（10-04 起） | 16:15 ✗ | 17:15 | 18:15 | 2 |

判据写成不变式「窗口内 ≥ 2 趟」，不是「有一个等于 19:15」——
后者在换季当天照样绿，而那时已经退回单趟了。自检和看门狗都按这个不变式判。

**DB 里还有一条 `kmfa-attendance-brief`（旧名「工作日北京 16:05」）没有目录、从没跑过，
2026-09-15 已置 PAUSED。** 它不是这条线在用的。自检里有一条守卫：
DB 里除了 `automation` / `automation-2`，不许再有 ACTIVE 的考勤 automation。

## 考勤累计：越线通知 + 周一月报（2026-09-15 起）

跑在 `automation-2` 的第二条命令 `scripts/kmfa_monthly_cron.sh` 上 —— **不新建 automation**。
工作日上午（本机 10:50 = 北京 08:50），看上一个自然日，发生产管理群。

| 报文 | 什么时候发 | 幂等 |
| --- | --- | --- |
| 出勤越线通知 | 有人的本月出勤跨过门槛，且这个人本月还没报过 | 首报制，台账记 uid |
| 月报 | 北京周一，报上一个自然日所属那个月 | 每月每天最多一条 |

都不满足就什么都不发（`SKIP_NO_CROSSING` / `SKIP_NOT_MONDAY`），照抄付款线「没付款就不说话」。

**门槛不写死数字。** 判的是跨过去这个动作：`昨天累计 <= 门槛 且 今天累计 > 门槛`。
半天班（钉钉记 0.5 天）、补录、数据跳一格都不会失灵；门槛换数、或按当月天数浮动，
只改 `KMFA_BRIEF_ATTEND_THRESHOLD`，代码一个字不动。
越线判定看的是「还没报过的人」，不是「昨天那一天跨的人」——
这条 automation 只在工作日跑，周六跨线的人没有哪一趟会正好看到周六。

**只看生产部全口径**（`KMFA_BRIEF_DEPT_ROOT`，含车工/焊工/钳工/调度/车间/司机/
各项目组等 11 个下级，29 人）。只查生产部本级会漏掉一多半。

## 两条硬闸，两条线都挂

**① 报文里不许出现「加班」「工时」「小时」**（`runtime.BANNED`）。
说时长等于书面记录公司自己的用工强度，压力给到公司而不是员工；
这条线要的是「谁该补卡、谁该调休」。闸在**投递之前**，不在写文案的人的自觉上。

**② 干跑在调用图上就够不着投递。**
2026-09-15 栽过一次：`run_attendance_monthly.py` 里 `--dry-run` 只被拿去跳过台账，
投递那段照跑，一次「干跑验证」把八月的两条报文真发进了生产管理群（已 `recall` 撤回）。
现在由 `publisher()` 选落点：干跑拿到的是 `_print_only`，它的调用图里没有 dws；
全文件只有 `_deliver` 一处会调 `chat message send`。自检里有一条 AST 守卫查这个，
并且用「故意注入缺陷」的负控验过它抓得到。

## 钉钉会吃掉空行

2026-09-15 把群里 09-14 那条日报的原文拉回来看，源文件里 4 处空行一处都没剩：
`"…要处理 3 条  \n考勤异常 3 人  \n · 林维…"` —— 段与段之间没有任何间隔，
十几行连成一片。`report.dingtalk()` 现在把空行换成一行全角空格（U+3000）：
渲染出来是空白，但它不是空行，吃不掉。自检里有一条守卫断言输出里没有 `\n\n`。

## 跑的是机外部署位，不是仓库工作树

    ~/.codex/skills/KMFA-Attendance-Brief/
      attendance_brief/   scripts/   templates/   automation/
      private_runtime/kmfa_brief.env      ← 真值只有这一份，600

两条 automation 里写死的就是这个路径下的 `scripts/kmfa_brief_cron.sh`。
跟 `KMFile-Archive` / `KMMedia-Archive` 同一个惯例。
本仓 `KMFA/skills/钉钉考勤/` 是**源**，不是运行位；改完源要
`rsync -a` 同步到部署位才生效（`private_runtime/` 不同步）。

**为什么不在仓库里直接跑。** 2026-09-10 06:44，本仓主工作树被一次
`git reset --hard` + `git clean -fd` 清过：简报的 17 个未跟踪文件整目录消失，
7 个已跟踪文件回退到旧版，两条 automation 指向的 `kmfa_brief_cron.sh` 随之不存在。
当天 17:15 的出报本来会直接失败，而且**失败告警本身也在被删的文件里**，
所以是静默失败 —— 群里没简报，手机上也没有任何提示。
主工作树的规矩是「永远停 main、永远干净、只 pull 不写」（提交钩子会拦下在主树的 commit），
生产代码放在那里迟早还会被清一次。搬到 `~/.codex/skills/` 之后，
`clean` 和 `reset --hard` 都够不着它。

**万一部署位也没了怎么恢复。** SMB 上有整包备份：

    /Volumes/share/03_资料库/MetaData/KMFA_MetaData/KMFA/skill_backup/钉钉考勤/

2026-09-10 那次就是靠它逐文件 md5 还原的（备份快照 05:29，清空 06:44，正好赶上）。

## 模型

`scnet-deepseek-v4-flash-0731` / `reasoning_effort=max` —— **模型由张霖泽指定**，
2026-09-09 定。Codex 每次改 automation 都会把当前会话的模型盖上去，
所以 `scripts/kmfa_brief_check.sh` 里有一条断言盯着它；要换模型改那里的
`WANT_MODEL` / `WANT_EFFORT`（或用 `KMFA_BRIEF_MODEL` / `KMFA_BRIEF_EFFORT` 覆盖），
别去改代码默认值。

automation 的活很轻：执行一条命令、读退出码、按标记表对号入座、抄回四行。
判读规则全在 prompt 的标记表里，不需要模型自己推理。

## 为什么要两条：夏令时免疫

本机是悉尼、有夏令时；北京没有。两地差 2 小时（AEST）或 3 小时（AEDT，10 月初—次年 4 月初）。
**只配一个钟点，10 月 4 日夏令时一开就整体漂 1 小时，而且是静默漂。**

| 期间 | 本机 19:15 | 本机 20:15 |
| --- | --- | --- |
| AEST（4 月—10 月初） | **北京 17:15 → 出报** | 北京 18:15 → 已发过，退 0 |
| AEDT（10 月初—次年 4 月） | 北京 16:15 → 已过截止线但主条先跑，正常出报 | **北京 17:15 → 已发过，退 0** |

挑哪一条由脚本自己判，不需要任何人在换季时改钟点。
两条同时存在也不会重复进群 —— 幂等是无条件的（见下）。

## 出报前先归档一遍自己这个群

闸全过了、今天确实要出报时，先并发跑一轮前置归档，让下游读到的钉钉原件是完整的：

```
python3 ~/.codex/skills/KMFile-Archive/scripts/kmfile_pipeline.py  scan --only-group 生产管理群 --since-manifest --no-private
python3 ~/.codex/skills/KMMedia-Archive/scripts/kmvideo_pipeline.py scan --only-group 生产管理群 --since-manifest --no-private
```

**只跑 `scan`，不跑 `all`。** scan 就是「把这个群的新原件抓下来归档进 SMB」，
考勤要的就是这个。all 后面那串 probe / thumbs / dedup / label / rename / registry / upload
是 KMFile、KMVideo 各自的编目流程，跟出一份考勤报无关，而且慢得离谱 ——
2026-09-07 实测 kmmedia 的 scan 只要 4 分 36 秒，接着 thumbs 一个阶段跑了 22 分钟还没完
（109 个媒体逐张 rsync 到 SMB 再 stat 回来）。编目交给它们各自 03:15 / 03:30 的每日任务。

**`--no-private` 只跳过「往私有资料库推」这一步。** pipeline 找的是
`$KMOS_ROOT/machine/tools/private_db_client.py`，这台机器上没有那个文件
（真件在 MetaDatabase/EEI 和 AgentDatabase 下），不加这个开关每轮必然 RuntimeError。
这条是归档线自己的老毛病，它的每日任务同样会挂，得它自己修。

以上都不缩小归档范围：群、类型、对象一个没少，少的只是下游编目步骤和一个推送目的地。

**只管自己那一个群。** KMFile / KMMedia 各自 03:15 / 03:30 的每日任务才是全公司
全群全类型的，那是它们的职责；考勤简报只是调用方，为了出一份考勤报去跑一轮
全公司归档既慢（实测全量单轮 20 分钟以上）也不是它该扛的。群名可用
`KMFA_BRIEF_GROUP_TITLE` 覆盖，默认「生产管理群」。

参数上的几个坑：

- `--since-manifest` 是日增量入口。**不带它会从 2025-01-01 全量回填**，回填不许进调度。
- `--refresh-groups` / `--include-new-groups` 不带 —— 有 `--only-group` 时 pipeline
  直接忽略（源码 `if args.refresh_groups and not args.only_group`）。
- `--window-days` 只有 kmfile 有，kmvideo 没有，传了会报错，所以两边都不传。
- 底层的 `archive_internal_files.py` / `archive_internal_media.py` 不用，
  它们的 `--allow-title` 是 required，参数形态完全不同。

**放在闸之后**，不是最前面：备位那条 automation 绝大多数日子命中
`SKIP_ALREADY_SENT`，放闸之前等于每天白跑一轮。

**失败不阻断。** 简报才是交付物，归档只是前置热身。结果只发过程标记
（`*_OK` / `*_LOCKED` / `*_FAILED` / `*_TIMEOUT`），不改退出码、不影响 ACTION。

### 并发与超时（实测定的规矩）

- **不走 `subprocess.PIPE`。** 只在最后 read() 时，输出超过管道缓冲（约 64KB）
  子进程就会阻塞在写上。改成直连临时文件，被超时打断也还能拿到尾巴。
- **超时用 SIGTERM 不用 SIGKILL。** pipeline 收到 TERM 会写完当前 manifest 窗口再退，
  直接 -9 会写坏 manifest。给 20 秒宽限，赖着不走才升级。
- **被锁挡住要单独认出来。** 实测两个 pipeline 被活锁挡住时退出码是 1（不是 0），
  但不能只看退出码 —— 日志里「另一个 pipeline 实例仍在运行」才是确证，
  记成 `*_LOCKED`，不要混进 `*_FAILED`，更不能记成完成。
- **陈旧锁不用自己收。** 上游 `acquire_workdir_lock` 已经用 `kill -0` 判活，
  只有 ProcessLookupError 才算残留、EPERM 当活着。实测造过 pid=999999 的死锁，
  pipeline 自己收掉并正常跑完。这里不重复做，免得误杀真实竞争。
- workdir 用 pipeline 默认值，跟每日全量任务共用同一份 manifest 与登记表，
  `--since-manifest` 的增量水位才连续。代价是撞上全量任务会被锁挡，属正常。

## 出报时刻 = 截止线 = 北京 17:15

2026-09-09 起两者合并成同一个时刻（此前截止线是 16:00，出报是 17:15，分开的）：
**简报什么时候发，人员表就得在那之前到，晚于它就是迟发。**

- `KMFA_BRIEF_PUBLISH_HOUR` / `KMFA_BRIEF_PUBLISH_MINUTE` = 17 / 15
- `KMFA_BRIEF_DEADLINE` 默认就等于上面两个拼出来的 `17:15`，正常不要单独设。
  分开会让「迟发」和「什么时候能看到简报」对不上，解释不清。

这个时刻同时是**挑钟点的判据**（`SKIP_BEFORE_PUBLISH`）：本机有夏令时而北京没有，
两个触发钟点里只有一个等于北京 17:15，另一个必然早一小时，靠这道闸挡掉。

**台账只存事实，不存判断。** `人员表按时台账.json` 每天只记「发布时间」，
按时与否在读的时候按当前截止线现算。把判断存死的话，改一次截止线全部历史就错了，
而且错得看不出来 —— 2026-09-09 这次改动实测：同一份 41 天台账，
按 16:00 算 2 天按时，按 17:15 算 27 天按时。

## 只在周一到周五

台账实测 38 个工作日 38 天都有人员表，周末一张都没有。周末触发只会平白追着发布人要表。
`BYDAY` 之外脚本里另有一道周末闸。法定节假日和调休算不出来，改用硬证据：
工作日没有人员表时先查全公司当天打卡，一个人都没打就判非工作日，不出报、不记账、不点名。

## 幂等是无条件的

发成功后在 SMB 落 `已发送/YYYY-MM-DD.txt`。**一个业务日只进群一次，谁触发的都一样**
—— 排程、备位那条、Codex 界面上的手动 `Run`、连点两下，都只发一份。
`--force` 只放行周末和截止线两道闸，**不放行已发标记**。

## 手动触发

在 Codex 里点任意一条的 `Run`。脚本按「离计划钟点多远」分辨：
±15 分钟内算排程触发，按规矩来；其它时刻算人按的，自动带 `--force`，周末和截止线都不拦。

## 判读只认固定标记

脚本 stderr 每行形如 `TOKEN | 中文说明`。**调度侧一律认 TOKEN，中文只给人看** ——
文案随时会改，改了不该影响判读。

结论性标记：`SEND_COMPLETED`（发成功）、`SKIP_ALREADY_SENT`、`SKIP_WEEKEND`、
`SKIP_NON_WORKDAY`、`SKIP_BEFORE_PUBLISH`、`LOCK_HELD`、`NOT_SENT_DRY_RUN`、
`NOT_SENT_MANUAL`、`SMB_UNAVAILABLE`、`SEND_FAILED`、`ABORTED_TIMEOUT`、`RUN_FAILED`、
`CONFIG_MISSING`、`VENV_MISSING`、`NO_TARGET`。
过程标记：`RUN_START`、`LOCK_ACQUIRED`、`LOCK_STALE_RECLAIMED`、`ALARM_SENT`/`ALARM_FAILED`。
一个结论性标记都没出现 = 异常，按 ESCALATE 处理。对应动作见 `kmfa_attendance_brief.prompt.md` 的表。

## 出事会私聊张霖泽

`ACTION: ESCALATE` 只写在 Codex 桌面 app 的任务消息里，手机上看不见 —— 挂三天没人知道。
所以脚本自己走钉钉私聊告警，四种情况会发：
`SMB_UNAVAILABLE`、`SEND_FAILED`、`ABORTED_TIMEOUT`、`RUN_FAILED`。
简报本身只发群，私聊这条通道只用来报故障。

## 运行日志

SMB 上 `attendance_brief_runtime/logs/kmfa_brief_run.log`，每行带时间戳和标记，
超过 2MB 自动砍掉前半。出事直接贴最后 30 行。

## 换机重建

1. 按 `scripts/setup_attendance_brief.sh` 建 venv。
2. 照 `templates/kmfa_brief.env.example` 填 `private_runtime/kmfa_brief.env`（真值不进 Git）。
3. 在 Codex 里让它 `create_automation` 建两条，字段照上表，prompt 用
   `automation/kmfa_attendance_brief.prompt.md` 原文。
   **钟点按新机器时区重算**：新机时区等于北京时，两条就是 17:15 和 18:15；
   若新机没有夏令时，一条即可（把 `KMFA_BRIEF_SLOT_HOUR2` 设成与 `KMFA_BRIEF_SLOT_HOUR` 相同）。
4. 跑 `bash scripts/kmfa_brief_check.sh`，全 PASS 才算装好。

## 纪律

- `prompt` 里不许放业务判定。判定全在脚本里，automation 只负责按点执行、把标记抄回来。
- 私有运行态、钉钉原始载荷、简报正文、凭据、解析出来的 DWS id 一律不进 Git。
