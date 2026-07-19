# STAGE-044 Phase 2 Half-Product Cleanup Candidate Decision Slice

## Identity

- Task: `IDS-V0_1-STAGE044-P2`
- Acceptance: `ACC-STAGE-044`
- Policy: `ids.half_product_cleanup_policy.v0_1.stage044.p2`
- Mode: `ISOLATED_NON_PRODUCTION_REFERENCE_ONLY_CLEANUP_CANDIDATE_DECISION_SLICE`
- Next gate: `IDS-STAGE044-P3-GATE`

## Controlled Evidence

本步骤只在进程内对 Git-tracked 控制引用和有界 metadata 做确定性判断。它不
扫描目录、不探测真实候选、不访问候选路径、不获取生产锁、不执行 `openat`、
`unlinkat`、移动、覆盖或删除，也不写候选记录、audit、数据库或运行输出。

只有 `TEMP_STAGING_OUTPUT` 与 `INCOMPLETE_DERIVATIVE_OUTPUT` 两类，并且任务处于
`PAUSED`、`RETRY_WAIT`、`FAILED`、`DEAD_LETTERED` 或 `CANCELLED` 时，才可能
返回 `CLEANUP_CANDIDATE_REVIEW_REQUIRED`。它只是待复核候选，不是清理授权。

候选仍须同时证明：attempt ownership、批准 root identity、root-relative path、
可重建性、manifest、无 retention/legal/owner hold、无 durable reference、稳定
`st_dev`/`st_ino`/`file_type`、writer quiescence、资源门、受管 exclusive namespace
lock 与 canonical containment。缺失、冲突、未知或不新鲜的证据全部失败关闭。

十四类受保护资料继续永不进入候选，包括 raw/source/database、manifest、
evidence、audit、report、index、有效 checkpoint、held artifact 和成功输出。
移动硬盘离线、磁盘不足或 API 预算不足只返回资源阻断；资源恢复不等于自动恢复
或 owner 授权。

规范请求 ID 绑定完整 reference-only payload。完全相同 replay 返回同一结果；
同 ID 不同 payload 返回 `CLEANUP_REQUEST_CONFLICT`。结果只包含有界 refs、中文
状态和 `delete_allowed=false`，不回显不可信 payload。

## Proposed Parameters

五个值全部为 `PROPOSED`，注册为 planned，并绑定 `TASK-OPME-B-001` 的生产校准
任务。本步骤不 sleep、poll、schedule、scan、lock、stat、open 或 delete。

| Parameter | Value | Source and derivation |
|---|---:|---|
| `cleanup_scan_interval` | 300 s | 复用 Stage042 已评审候选扫描间隔；本步骤不实际扫描 |
| `cleanup_candidate_retention` | 600 s | 两个 scan interval，且继续受 Stage034 keep-until/hold 合同约束 |
| `cleanup_lock_lease` | 30 s | 复用 Stage041 lease；本步骤不获取或续约锁 |
| `writer_quiescence_window` | 60 s | Stage042 stability window，也是两个 Stage041 lease |
| `cleanup_attempt_timeout` | 30 s | 一个 Stage041 lease / Stage043 checkpoint validation timeout；本步骤不等待 |

这些值只是隔离控制边界，不是生产校准结果。任何参数、来源、关系或证据无效时，
回滚为 `NO_AUTOMATIC_HALF_PRODUCT_CLEANUP`。

## Explicit Non-Actions

- no cleanup scan, filesystem probe, traversal, stat, open, rename or delete;
- no production lock, lease, fencing or writer-quiescence probe;
- no job state, terminal result, manifest, checkpoint or output mutation;
- no candidate/audit/database/schema/persistent/runtime-output write;
- no raw metadata, IDS business source, fake business data or external API access;
- no production activation, Phase 3, whole-stage review, GitHub action or app reinstall.

## Phase 3 Gate

Phase 3 must run separately. It may validate duplicate requests, active/unknown writer,
stale identity, resource pressure, lock conflict and protected-artifact scenarios using
reference-only control metadata. It must not scan or delete real files and must not turn
this candidate decision into cleanup execution evidence.

Stop markers:

- `NO_PHASE3_THIS_RUN`
- `NO_REAL_CLEANUP_SCAN`
- `NO_FILESYSTEM_TRAVERSAL`
- `NO_PRODUCTION_LOCK`
- `NO_DELETE_MOVE_OR_OVERWRITE`
- `NO_PERSISTENCE_OR_AUDIT_WRITE`
- `NO_RAW_METADATA_ACCESS`
- `NO_FAKE_IDS_BUSINESS_DATA`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`

`push_allowed=false`; the only next task is `IDS-V0_1-STAGE044-P3`.
