# STAGE-043 Phase 1 Worker Crash Recovery Scope Boundary

## State Authority

Stage043 不引入新状态，不允许把 worker 崩溃等同于任务已失败，也不允许
“原地继续”。所有候选必须使用 `ids.job_state.v1` 的现有边：

- 活跃态恢复先候选 `CLAIMED|RUNNING|PAUSE_REQUESTED -> RETRY_WAIT`；
- 后续候选只能按 `RETRY_WAIT -> QUEUED -> CLAIMED -> RUNNING`，且重试准入
  由 Stage039 所有；
- 永久非重试错误仅可在合法 guard 下候选 `RUNNING -> FAILED`；
- `SUCCEEDED`、`FAILED`、`DEAD_LETTERED`、`CANCELLED` 永不重开。

`RUNNING -> RUNNING`、`RUNNING -> QUEUED`、`CLAIMED -> QUEUED`、绕过 `RETRY_WAIT`
或盲目恢复内存态全部禁止。

## Worker And Failure Boundary

Phase 1 只区分四类事件：普通任务异常归 Stage039，有序关闭归 Stage042，
worker 进程丢失或代际更换归 Stage043，半成品删除归 Stage044。它不调用
进程探测、终止、重启、worker 运行时或生产队列。

崩溃判定必须绑定任务、attempt、worker instance/generation、当前状态版本、
最后心跳观测、租约归属/到期、锁键、fencing token、checkpoint/quarantine/error
引用和 audit 引用。缺失、过期、冲突或不可证明的证据一律进入人工复核。

## Recovery Candidate Decision

检查点续作候选必须同时满足：检查点完整性有效、幂等身份有效、owner
重新确认、资源门通过、丢失 worker 已被栅栏、状态版本当前，并经过全新
准入/领取/锁/租约/栅栏周期。否则只能生成 Stage039 重试候选、安全失败
候选或人工复核，不修改状态。

每个崩溃事件只有一个规范 recovery request key，绑定 job、attempt、worker
generation、observed state version 和 crash incident。精确重放返回原决策；同键
不同 payload 失败关闭。

## Resource Pause

外接盘离线、磁盘空间不足或 API 预算不足时，相关任务必须暂停而非
自动续作。已崩溃的活跃任务只能先进入 `RETRY_WAIT` 候选，再由 Stage040/042
规则候选 `RETRY_WAIT -> PAUSED`。资源恢复不等于 owner 授权，Phase 1 不自动
恢复。

## Lock, Fencing And Partial Output

丢失 worker 必须在新候选之前被可证明地栅栏。Stage041 仍是锁、租约、CAS
和 fencing token 所有者。Phase 1 不接管锁，不恢复丢失的内存锁状态。

局部输出只能隔离并保留引用；清理仅能产生 `TEMP_STAGING_OUTPUT` 或
`INCOMPLETE_DERIVATIVE_OUTPUT` 候选，Stage044 独立执行。`FACT_SOURCE`、
`MANIFEST`、`EVIDENCE_LEDGER`、`REPORT_SNAPSHOT`、`AUDIT_LOG` 永不允许删除。

## Deferred Parameters

Phase 1 不设置任何数值。`crash_detection_interval`、`heartbeat_stale_window`、
`lease_expiry_grace`、`recovery_retry_backoff`、`checkpoint_validation_timeout` 必须在单独
Phase 2 中给出来源、理由、单位、策略版本、验证证据与回滚。

## Phase 2 Gate

`Phase 2 must run separately`。它最多实现一个隔离非生产、引用型恢复决策切片，
不终止或重启进程，不修改任务或锁，不删除局部输出。

- `NO_PHASE2`
- `NO_CRASH_RECOVERY_RUNTIME`
- `NO_PROCESS_TERMINATION`
- `NO_STATE_MUTATION`
- `NO_CLEANUP_DELETE`
- `NO_RAW_METADATA_ACCESS`
- `NO_FAKE_IDS_BUSINESS_DATA`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`

下一门是 `IDS-STAGE043-P2-GATE`；`push_allowed=false`。
