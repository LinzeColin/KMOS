# STAGE-044 Phase 1 Half-Product Cleanup Scope Boundary

## Decision

`IDS-V0_1-STAGE044-P1` 只定义半成品清理的工程合同。它不是清理器、不是目录
扫描器，也不证明任何真实文件已符合删除条件。合同状态为
`PHASE1_ENGINEERING_CONTRACT_DELETE_DISABLED`，`execution_ready=false`，
`delete_allowed=false`。

本阶段遵守 fail-closed：缺失、过期、冲突、不可验证或由调用方自报的关键证据
一律阻断，不把“不知道”解释为“可删除”。

## Source And Prior Authority

- 唯一 taskpack member 已按精确路径与 SHA-256 绑定。
- Stage043 reviewed-local commit/tree 是进入 Stage044 的前序事实。
- Stage029 只提供早期 archive staging allowlist 证据；它不授权本阶段删除。
- Stage037 的 11-state / 4-terminal 模型、attempt-owned manifest、清理安全规则
  仍是权威语义。
- Stage038 拥有 queue/worker，Stage039 拥有 retry/dead letter，Stage040 拥有
  resource pause，Stage041 拥有 lock/lease/fencing，Stage042 拥有 automatic
  lifecycle，Stage043 拥有 worker crash recovery。
- Stage044 只拥有半成品清理；Phase 1 不启动该运行时。

## State And Attempt Boundary

Phase 1 不新增 job state，不把 cleanup status、resource reason 或 human label
伪装成 state。活动执行态 `CLAIMED`、`RUNNING`、`PAUSE_REQUESTED` 永远阻断
清理；`CREATED`、`QUEUED` 也没有足够 attempt 终止证据。`PAUSED` 与
`RETRY_WAIT` 都是可恢复的非终态，必须保留给 resume/retry owner；`SUCCEEDED`
输出受保护。只有 `FAILED`、`DEAD_LETTERED`、`CANCELLED` 中由失败或取消任务
产生的 attempt-owned 半成品可进入后续候选判断，而且 job state 只是必要条件，
不是充分条件。

清理不得重开或改变任何 terminal job 结果。重试、dead letter、resume、crash
recovery 和新 job lineage 仍由既有 owner 合同处理。

## Cleanup Candidate Contract

未来候选必须是 reference-only control metadata，并精确绑定：

- `cleanup_request_id`, `job_id`, `attempt_id`, `creator_job_id`；
- `approved_root_id` 与 canonical approved-root identity；
- root-relative path；
- artifact class 与 `rebuildable=true`；
- retention policy、legal hold、owner hold；
- `cleanup_manifest_ref` 与 durable-reference status；
- immutable lstat identity：`st_dev`, `st_ino`, `file_type`；
- writer-quiescence evidence 与 resource-gate evidence。

候选只允许两类：

1. `TEMP_STAGING_OUTPUT`
2. `INCOMPLETE_DERIVATIVE_OUTPUT`

候选记录不得承载 raw body、source content、secret 或无界日志。Phase 1 不创建
候选记录，也不读取目录来发现候选。

## Protected Artifact Contract

以下类别永不进入清理 allowlist：

- original raw data 与 source file；
- source/runtime database；
- fact source、manifest、evidence ledger、audit log；
- report snapshot 与 delivered report；
- active index；
- retry 所需的 validated checkpoint；
- legal/owner held artifact；
- succeeded job output。

任何 durable evidence 引用、未知 ownership、未知 rebuildability、缺失 manifest、
retention/legal/owner hold 或成功输出引用均执行 `BLOCK_CLEANUP`。没有 override。

## Resource Pause Boundary

`EXTERNAL_DRIVE_OFFLINE`、`DISK_SPACE_INSUFFICIENT` 或
`EXTERNAL_API_BUDGET_INSUFFICIENT` 任一信号存在时必须阻断清理。后续阶段也
必须取得新鲜 owner observation 并证明全部 resource gates pass；不得因旧状态
或计时器自动恢复。本 Phase 不探测 drive、disk 或 API。

## Namespace Lock And Writer Quiescence

在任何验证前，未来实现必须通过 Stage041 owner 获取 exclusive cleanup
namespace lock；key 精确由 `approved_root_id` 与 candidate parent directory
组成，不使用 project-wide global lock。

锁内必须证明所有 producer/cleanup lease 已不存在或被 fencing，且 creation、
rename、replacement、delete 都无法进入同一 namespace。锁保持到未来
`unlinkat` 完成。unmanaged namespace、advisory-only lock 或无法证明 writer
quiescence 一律 `BLOCK_CLEANUP`。Phase 1 不获取任何锁，也不探测 writer。

## Path And TOCTOU Safety

未来实现只能从受信任 approved root `dirfd` 出发，以 root-relative path 通过
`openat` + `O_NOFOLLOW` 遍历，并以同一 directory descriptor 相对调用
`unlinkat`。绝对路径、`..`、symlink target 或任一 symlink path component
均阻断。

在删除前最后一刻，仍在 exclusive namespace lock 内重新验证：

- canonical containment；
- owner job/attempt；
- artifact class、file type；
- `st_dev`、`st_ino`；
- cleanup manifest；
- retention/hold、durable refs 与 resource gates。

任何 TOCTOU change 或 identity mismatch 都执行 `BLOCK_CLEANUP`。这只是后续
协议；本 Phase 不 open root、不 traverse、不 stat、不 rename、不 move、不
overwrite、不调用 `unlinkat`，也不删除任何文件。

## Idempotency And Audit

未来 idempotency key 必须绑定 cleanup request、job/attempt、approved root、
relative path、`st_dev`、`st_ino` 与 manifest ref。完全相同 replay 返回原始
decision；同 key 不同 payload 失败关闭。每个未来清理结果必须有独立 append-only
audit，并且永远不能改变 terminal job result。

Phase 1 不写 idempotency registry 或 audit，不把合同验证结果描述为清理成功。

## Parameters

`cleanup_scan_interval`、`cleanup_candidate_retention`、`cleanup_lock_lease`、
`writer_quiescence_window`、`cleanup_attempt_timeout` 全部留待单独 Phase 2。
未来值必须带 value、unit、source、rationale、policy version、validation evidence
与 rollback；本轮不提供隐式默认值，不声称 production calibration。

## Human Status Projection

owner-facing 状态必须明确区分：候选待复核、活动或证据未知阻断、资源阻断、
受保护资料阻断，以及“合同就绪但删除仍禁用”。静态 checker PASS 不得显示为
“文件已清理”或“生产可用”。

## Phase 2 Gate

只有 source/predecessor/upstream hash、state/owner boundary、candidate/protected
class、resource pause、namespace lock、dirfd/nofollow/unlinkat protocol、
idempotency/audit 与所有 no-runtime truth flag 同时通过，才把下一 gate 路由为
`IDS-STAGE044-P2-GATE`。

`Phase 2 must run separately`。Phase 1 不授权 Phase 2，不安装依赖，不生成
`.venv`、`node_modules`、`data`、`reports` 或 `outputs`。

## Stop Conditions

- `NO_PHASE2`
- `NO_CLEANUP_SCAN`
- `NO_CANDIDATE_RUNTIME_EVALUATION`
- `NO_FILESYSTEM_TRAVERSAL`
- `NO_PRODUCTION_LOCK_ACQUISITION`
- `NO_DELETE`
- `NO_MOVE_OR_OVERWRITE`
- `NO_STATE_MUTATION`
- `NO_AUDIT_OR_RUNTIME_WRITE`
- `NO_DATABASE_OR_SCHEMA_CHANGE`
- `NO_RAW_METADATA_ACCESS`
- `NO_FAKE_IDS_BUSINESS_DATA`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`

原始元数据边界保持 path-only，完全未触碰。如果需要读取、列出、扫描、hash、
复制、移动、覆盖、删除或修改该目录内容，立即停止。若必须实际处理文件、获取
生产锁、写持久态、执行 cleanup、扩大到其他 KM 项目、进入 Phase 2 或上传，
也立即停止。

## Rollback

只撤销 Stage044 Phase 1 文档、合同、checker、tests 和最小治理投影。保留
Stage043 reviewed-local commit 及所有早期证据。rollback 不得扫描或操作任何
runtime/source path，也不得删除 staging、cache、database、manifest、evidence、
audit、report、checkpoint、index 或原始资料。
