# STAGE-043 Phase 2 Worker Crash Recovery Decision Slice

## Identity

- Task: `IDS-V0_1-STAGE043-P2`
- Acceptance: `ACC-STAGE-043`
- Policy: `ids.worker_crash_recovery_policy.v0_1.stage043.p2`
- Mode: `ISOLATED_NON_PRODUCTION_REFERENCE_ONLY_CRASH_RECOVERY_DECISION_SLICE`
- Next gate: `IDS-STAGE043-P3-GATE`

## Controlled Evidence

本步骤只在进程内对 Git-tracked 控制引用进行确定性候选判断。它不探测、
终止或重启进程，不修改任务、队列、重试、锁、租约、栅栏、检查点、输出或
数据库。默认控制请求使用 `control:stage043:` 命名空间，不是 IDS 业务任务。

候选仅有四条受控路径：

1. `CHECKPOINT_RESUME`：只有崩溃证据、状态版本、持久状态、检查点完整性、
   幂等身份、owner 复核、资源门、丢失 worker 栅栏和全新准入/领取/锁周期
   全部有效时，才输出 `CHECKPOINT_RESUME_CANDIDATE`。它仍须先候选
   `RUNNING -> RETRY_WAIT`，再由上游所有者重新准入，不允许原地继续。
2. `STAGE039_RETRY`：只有 Stage039 policy、预算、重放安全、错误引用、资源门
   和 backoff 全部有效时，才输出 Stage039-owned retry 候选。
3. `SAFE_FAILURE`：只有 `RUNNING -> FAILED` 合法边、永久错误和审计证据完整时，
   才输出安全失败候选。
4. `RESOURCE_PAUSE`：移动硬盘离线、磁盘不足或 API 预算不足时，输出
   `RUNNING -> RETRY_WAIT -> PAUSED` 候选；资源恢复不等于自动恢复或 owner 授权。

规范 recovery request key 只绑定 job、attempt、worker generation、observed
state version 和 crash incident。精确重放返回同一决定；同 key 不同 payload
返回 `RECOVERY_REQUEST_CONFLICT` 并要求人工复核。终态、缺失/陈旧/冲突证据、
活动 claim/lock、未栅栏 worker、无持久状态或非规范 key 一律失败关闭。

所有结果都只记录 input refs、空 output refs、安全 error ref、checkpoint/quarantine
摘要和 audit ref；不回显 raw payload。局部输出只能保留隔离引用，Stage044 仍是
清理执行唯一所有者，任何删除均未授权。

整阶段复审进一步将 lease owner 精确绑定到 worker instance，并将 checkpoint /
quarantine digest 绑定到规范 recovery request key；崩溃时间、资源门/压力信号与
Stage039 retry/permanent error allowlist 也必须内部一致。任一不一致请求只返回人工
复核，不产生候选转换。

## Proposed Parameters

五个值全部为 `PROPOSED`，注册为 planned，并继续绑定
`TASK-OPME-B-001` 的生产校准任务。本步骤不 sleep、poll、wait、schedule 或校准。

| Parameter | Value | Source and derivation |
|---|---:|---|
| `crash_detection_interval` | 1 s | reviewed Stage042 lifecycle tick，亦等于 Stage041 acquisition timeout |
| `heartbeat_stale_window` | 30 s | reviewed Stage041 lease duration，即三个 renewal intervals |
| `lease_expiry_grace` | 5 s | reviewed Stage041 expiry grace |
| `recovery_retry_backoff` | 30 s | reviewed Stage039 second/maximum retry backoff ceiling |
| `checkpoint_validation_timeout` | 30 s | reviewed Stage042 checkpoint wait，亦等于 Stage041 lease duration |

任一参数、来源、请求、时间关系、状态、引用或上游哈希无效时，回滚策略为
`NO_AUTOMATIC_CRASH_RECOVERY` 并要求人工复核。

## Explicit Non-Actions

- no crash injection, process probe, termination, restart or recovery;
- no job-state, queue, worker, retry, lock, lease or fencing mutation;
- no checkpoint continuation, output mutation, cleanup or delete;
- no database, schema, persistent state, registry state or runtime output write;
- no raw metadata, IDS business source, fake business data or external API access;
- no production activation, Stage 3, whole-stage review, GitHub action or app reinstall.

## Validation

- TDD RED: 16 focused tests produced 19 expected failures because Phase 2 artifacts,
  checker, registries and governance route were absent.
- Final GREEN: checker `18/18` contract and `15/15` decision checks; focused
  `16/16`; Stage005 `161/161`; Stage041-043 aggregate `156/156` in `644.177s`;
  full IDS v0.1 discovery `895/895` in `1065.039s`; all five historical
  stage-review checkers; `207` events with zero parse, duplicate or semantic
  errors; idempotent rendering and project-scoped dual-plane PASS.
- Validation repairs were bounded to nine glossary registrations, the explicit
  historical Stage042 `11/11/76` registry-count checkpoint, Stage041/042 current
  handoff compatibility, and P2-to-P3 forward-route allowlists. No historical
  review conclusion, runtime contract, process action or safety boundary changed.
- Pre-commit self-review repaired one Important fail-closed gap: every control
  identity now uses the same safe-reference grammar, and invalid requests cannot
  project untrusted error, checkpoint or quarantine references into results.

## Phase 3 Gate

Phase 3 must run separately. It may validate duplicate requests, stale evidence,
resource pauses, crash ownership, lock conflicts and protected cleanup boundaries;
it must not reinterpret this reference-only decision slice as process recovery.

Stop markers:

- `NO_PHASE3_THIS_RUN`
- `NO_ACTUAL_CRASH_RECOVERY`
- `NO_PROCESS_TERMINATION_OR_RESTART`
- `NO_STATE_OR_PERSISTENT_WRITE`
- `NO_CLEANUP_DELETE`
- `NO_RAW_METADATA_ACCESS`
- `NO_FAKE_IDS_BUSINESS_DATA`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`

`push_allowed=false`; the only next task is `IDS-V0_1-STAGE043-P3`.
