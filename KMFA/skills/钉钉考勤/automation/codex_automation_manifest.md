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

## 两条，缺一不可

| 项 | 主 | 备位 |
| --- | --- | --- |
| id | `automation` | `automation-2` |
| 名称 | 考勤异常简报 每工作日发送（生产管理群） | 考勤异常简报 每工作日发送 备位（生产管理群） |
| rrule | `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=19,20;BYMINUTE=15` | 同左，`BYHOUR=20,21` |
| 本机时间 | 每工作日 19:15、20:15 | 每工作日 20:15、21:15 |

**为什么每条两个钟点（2026-09-15 起）。** 本机是 Australia/Sydney 有夏令时，北京没有。
`2026-10-04` 悉尼转夏令时那天，本机 19:15 从北京 17:15 变成 16:15 —— 早于出报时刻，
会被「未到出报时刻」闸挡掉，主槽从此**天天空跑**，实际只剩备位一趟。
四个钟点铺开之后，换季前后都至少有两趟落在北京 17:15–21:15：

| | 本机 19:15 | 20:15 | 20:15 | 21:15 | 窗口内趟数 |
| --- | --- | --- | --- | --- | --- |
| AEST（现在） | 北京 17:15 | 18:15 | 18:15 | 19:15 | 4 |
| AEDT（10-04 起） | 16:15 ✗ | 17:15 | 17:15 | 18:15 | 3 |

判据写成不变式「窗口内 ≥ 2 趟」，不是「有一个等于 19:15」——
后者在换季当天照样绿，而那时已经退回单趟了。自检和看门狗都按这个不变式判。

其余字段两条完全相同：`status=ACTIVE`、`model=scnet-deepseek-v4-flash-0731`、`reasoning_effort=max`、
`execution_environment=local`、`cwds=["/Users/linzezhang/Documents/Codex"]`、
`project_id=b4e5abb7-70bb-463b-a484-d4ef000d8601`（与 kmfa-daily-funds、kmbid-daily 同一个）、
`prompt` = 本目录的 `kmfa_attendance_brief.prompt.md` 逐字原文。
两条都只执行 `scripts/kmfa_brief_cron.sh` 一条命令。

## 第三条腿：launchd 兜底触发器（不依赖 Codex，也不依赖任何 GUI 应用）

    ~/Library/LaunchAgents/com.kmfa.attendance-brief.plist   本机 19:20 / 20:20 / 21:20
    ~/Library/LaunchAgents/com.kmfa.keep-awake.plist         caffeinate -s，插电不休眠

装/卸：`scripts/install_launchd_trigger.sh` / `--uninstall`。

为什么要有它：Codex automation 只有在 **Codex 桌面端开着**的时候才会触发
（实测缺失全部集中在下午与夜里，与休眠无关，是宿主 app 不在）。而本机
`pmset -c sleep` 是 **1 分钟** —— 一直靠 Claude.app / ChatGPT.app 的 Electron
`NoIdleSleepAssertion` 顶着，那两个应用一关，一分钟后机器就睡，所有定时任务一起停。
「无人值守」到这里隐含了一个没人保证的前提：某个 GUI 应用一直开着。

launchd 是 macOS 自己的调度器：开机自启、不依赖任何应用、机器睡过了钟点会在唤醒后
补跑一次。它比 Codex 那一枪晚 5 分钟，所以正常日子只会拿到 `SKIP_ALREADY_SENT`；
Codex 没触发的那天，它就是唯一发得出简报的那个。
`caffeinate -s` 只在插电时生效，电池上照常省电。

**它必须走排程分支。** 包装脚本原来靠「离计划钟点多远」猜是不是人点的 Run，
远就给 `--force`。机器睡过钟点、launchd 醒来补跑时离钟点同样很远 ——
按旧推断会拿到 `--force`，绕开周末闸和出报时刻闸，把简报发进北京时间的深夜。
所以改成触发者显式声明：`KMFA_BRIEF_TRIGGER=launchd`。自检里有一条专门守这个分支。

## 发送窗口有上沿了（2026-09-15 起）

下沿一直有（`SKIP_BEFORE_PUBLISH`），上沿以前没有。多了 launchd 这条补跑路径之后，
「今天没发」和「半夜发出去」就成了两种完全不同的错误：前者第二天早上看门狗会说，
后者撤不回来。窗口 = 北京 17:15 起 `KMFA_BRIEF_WINDOW_HOURS`（默认 4）小时，
过了打 `SKIP_AFTER_WINDOW` 退 0 不发。人手动 `--force` 不受这条限制。

## 硬墙钟在进程外（2026-09-15 起）

python 里那个 `Deadline` 是阶段之间的协作式检查，要求进程还在跑。共享盘挂起时
进程卡在 `open()` 里进 U 态（不可中断），`Deadline` 一次都轮不到，信号也送不进去。
2026-09-15 实测：一次正常的 `SKIP_BEFORE_PUBLISH` 在 `smb_ready` 里卡了 **3 分 44 秒**
才出来——盘是活的，只是慢；真挂起就是无限期，而且卡在第一个标记之前。
所以包装脚本改成后台跑 + 自己数秒，`KMFA_BRIEF_HARD_TIMEOUT`（默认 900 秒）到了就
`kill -9`、打 `ABORTED_TIMEOUT`、**由包装脚本自己**发钉钉私聊告警
（那个 python 已经卡死，它自己的告警代码执行不到）。

## 钉钉网关是阵发性不可用的，必须当异常不能当空集（2026-09-15 起）

`dws` 走 `mcp-gw.dingtalk.com`，会**成串**地失败：实测一个 20 次的窗口里 11 次
stdout 全空、退出码 1，而 JSON 里 `errorCode` / `errorMsg` 都是 `null`；
换个时间点又连着 24 次全成。跟人数、天数、`--timeout` 都无关，是网关抖动。

旧的 `Dws.json()` 只看 stdout 解不解得出 JSON，解不出就 `return None`，于是一次抖动会变成：

| 抖在哪 | 调用方看到 | 实际发出去的 |
| --- | --- | --- |
| `chat message list` | 群里今天没有人员表 | 公开点发布人的名，而他发了 |
| `attendance check result` | 所有人都没打卡 | 整片点名补卡，而他们打了卡 |
| 两个都抖 | 全公司无人打卡 = 非工作日 | 什么都不发，也不告警 |

三种都没有告警。现在 `Dws.json()` 只信**退出码**（失败时那两个 JSON 字段也是 null），
非 0 就退避重试 3 次（2s、4s），仍失败抛 `DwsUnavailable` →
标记 `DINGTALK_UNAVAILABLE` + 私聊告警 + **拒发**，不写已发送标记，
本工作日剩下的触发点会再试。

花名册同理：部门树爬到一半够不着，收上来就是半份，而半份的后果不是「少几个人」，
是这几个人被判「不在钉钉花名册」、名字印进简报去问综合部，并且**把缓存里好的那份盖掉**，
之后每天都错。现在缩水超过两成一律不落盘，宁可继续用旧的。

## 看门狗：kmfa-attendance-watchdog

| 项 | 值 |
| --- | --- |
| id | `kmfa-attendance-watchdog` |
| 名称 | 考勤异常简报看门狗（停摆检测） |
| rrule | `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=10;BYMINUTE=50` |
| 命令 | `~/.codex/skills/KMFA-Attendance-Brief/scripts/kmfa_brief_watchdog.sh` |

排在上午（实测上午槽位四天零缺失，缺的全在下午与夜里），看的是**上一个工作日**，
所以它跑的时候「该发而没发」已经是定论。用系统 `python3`（3.9）不用主线那个 venv ——
venv 烂掉恰恰是要被报出来的故障之一，看门狗不能跟它同生共死。只用标准库。

查九件事，任一命中就私聊张霖泽，**同一件事只报一次**（状态落共享盘
`.考勤看门狗状态.json`）：部署位脚本在不在 → env 读不读得到 → 共享盘在不在 →
钉钉登录过没过期 → 两条 automation 在不在且 ACTIVE → prompt 还指不指向部署位脚本 →
换算成北京时间的有效槽位数（0 = 永远发不出去，1 = 退回单趟）→ launchd 兜底装没装 →
插电会不会一分钟就睡且没有 caffeinate 顶着 → 26 小时没被触发 →
上一个工作日的运行日志里有没有留下结论性标记。

**判的是「有没有留下结论」，不是「有没有发」。** 法定节假日会正常留下
`SKIP_NON_WORKDAY`，那是结论不是故障；真正要抓的是那一天整片空白 ——
群里没简报、日志里没有一行、手机上没有告警。

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
