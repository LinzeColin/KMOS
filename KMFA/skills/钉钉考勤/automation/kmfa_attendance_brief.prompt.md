<!-- automation-run-mode:v1:start -->
## 运行触发方式（最高优先级）

- 计划运行和用户点击的手动 `Run` 同等有效；不得因当前日期、当前时刻、距计划时刻的间隔或是否错过计划而拒绝执行。
- 每次启动只处理当前这一批任务，不补跑历史批次，不等待下一个计划时刻。
- 完成后正常收敛；最终消息首行必须且只能有一个 `ACTION: NONE|ACT|STOP|ESCALATE`，并给出简短结果摘要。
<!-- automation-run-mode:v1:end -->

默认中文。本任务只做一件事：执行下面这一条命令，把它的输出照抄回来。

    /Users/linzezhang/.codex/skills/KMFA-Attendance-Brief/scripts/kmfa_brief_cron.sh

规矩（照做，不要发挥）：
- 不读脚本、不改脚本、不改任何文件、不装任何东西、不自己去调钉钉、不自己写简报。
- 不加参数、不设环境变量、不改日期。业务判定全在脚本里，你判不了也不需要判。
- 脚本自己会分辨是排程触发还是人点的 Run，你不用管。

**判读只认 stderr 里的固定标记，不要看中文措辞。** 中文随时会改，标记不会。
每行形如 `TOKEN | 中文说明`。按最后出现的结论性标记判：

| 标记 | 含义 | 你写什么 |
| --- | --- | --- |
| `SEND_COMPLETED` | 简报已发进生产管理群 | `ACTION: ACT` |
| `SKIP_ALREADY_SENT` | 今天这份已经发过 | `ACTION: NONE` |
| `SKIP_WEEKEND` | 周末，不发 | `ACTION: NONE` |
| `SKIP_NON_WORKDAY` | 节假日/调休，不发 | `ACTION: NONE` |
| `SKIP_BEFORE_PUBLISH` | 还没到出报时刻北京 17:15，等本日下一个触发点 | `ACTION: NONE` |
| `SKIP_AFTER_WINDOW` | 已过发送窗口（北京 17:15 起 4 小时），今天不补发 | `ACTION: NONE` |
| `LOCK_HELD` | 上一轮还在跑 | `ACTION: NONE` |
| `NOT_SENT_DRY_RUN` / `NOT_SENT_MANUAL` | 刻意不发 | `ACTION: NONE` |
| `SMB_UNAVAILABLE` | 共享盘掉了 | `ACTION: ESCALATE` |
| `DINGTALK_UNAVAILABLE` | 连不上钉钉网关（阵发），本轮拒发 | `ACTION: ESCALATE` |
| `SEND_FAILED` | 报出来了但发不进群 | `ACTION: ESCALATE` |
| `ABORTED_TIMEOUT` | 超时中止 | `ACTION: ESCALATE` |
| `RUN_FAILED` | 脚本异常 | `ACTION: ESCALATE` |
| `CONFIG_MISSING` / `VENV_MISSING` / `NO_TARGET` | 没装好 | `ACTION: ESCALATE` |

**过程标记不参与判读**，看到了不要当故障：
`RUN_START`、`LOCK_ACQUIRED`、`LOCK_STALE_RECLAIMED`、`ALARM_SENT`/`ALARM_FAILED`，
以及出报前那轮前置归档的 `KMFILE_START`/`KMFILE_OK`/`KMFILE_LOCKED`/`KMFILE_FAILED`/`KMFILE_TIMEOUT`
和 `KMMEDIA_START`/`KMMEDIA_OK`/`KMMEDIA_LOCKED`/`KMMEDIA_FAILED`/`KMMEDIA_TIMEOUT`。
（`_LOCKED` = 撞上另一轮归档的锁，本轮跳过，属正常。）
还有一个 `ARCHIVE_ABORTED` —— 归档整段被兜住了（子进程 SIGKILL 都收不走那类），同样只是过程标记，简报照出。
**归档失败或超时不影响 ACTION** —— 简报才是交付物，归档只是前置热身，
它挂了简报照出。只有上表里的结论性标记才决定 ACTION。

- 一个结论性标记都没出现 → `ACTION: ESCALATE`，并贴 stderr 最后 20 行原文。
- ESCALATE 时不要自己诊断、不要重试、不要改脚本。脚本已经自己私聊告警过张霖泽了。

最终报告只要这四行，不要多写：
ACTION: <NONE|ACT|ESCALATE>
标记：<结论性标记>
退出码：<n>
结果：<该标记那一行的中文部分>
