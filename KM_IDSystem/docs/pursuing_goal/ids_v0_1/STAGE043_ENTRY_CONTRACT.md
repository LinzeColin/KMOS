# STAGE-043 Phase 1 Entry Contract

## Identity

- Stage: `STAGE-043 · Worker 崩溃恢复`
- Task: `IDS-V0_1-STAGE043-P1`
- Acceptance: `ACC-STAGE-043`
- Local code: `D07-S007`
- Domain: `D07 · 任务编排与机器控制`
- Entrance: `IDS 系统运营入口`
- Contract: `ids.worker_crash_recovery.v0_1.p1`
- State: `PHASE1_ENGINEERING_CONTRACT_RUNTIME_DISABLED`
- Next gate: `IDS-STAGE043-P2-GATE`

## Goal

定义 worker 进程丢失后任务状态不丢失、可受控继续或安全失败的可执行、
可测试、可回滚工程合同。Phase 1 只评估引用型恢复候选，不终止或重启
进程，不修改任务状态、队列、锁、检查点或输出，不写数据库或持久态。

## Source And Predecessor Binding

唯一批准成员
`IDS_v0_1_Final_Chinese_Revised/stages/STAGE-043_Worker崩溃恢复.md`
的 SHA-256 为
`e1d5169cbc30515930a7224743b860d9b577ccfbf9e0f913ec254d2ea060317b`。
机器合同同时绑定批准归档、路线图、使用说明、Stage042 已提交的复审
commit/tree 以及 Stage037–042 的精确跟踪合同。本轮未读取 IDS 业务源或
原始元数据内容。

## Entry Preconditions

- Stage042 只以 `completed_reviewed_local` 关闭，绑定 commit
  `ba248f66ce993a726cb12547ae1c772ab1228bfa`。
- Stage037 仍是唯一任务状态和迁移真源；Stage043 不新增状态或快捷迁移。
- Stage038 拥有队列和 worker 传输；Stage039 拥有重试与死信。
- Stage040 拥有压力观测与资源暂停；Stage041 拥有锁、租约与栅栏。
- Stage042 拥有自动生命周期；Stage044 才能执行半成品清理。
- 原始元数据根目录仍只是路径边界，完全未触碰。

## Phase 1 Deliverables

1. 本入口合同。
2. `STAGE043_PHASE1_WORKER_CRASH_RECOVERY_SCOPE_BOUNDARY.md`。
3. `worker_crash_recovery/stage043_worker_crash_recovery_contract.json`。
4. `scripts/check_worker_crash_recovery.py`。
5. `tests/test_stage043_worker_crash_recovery.py`。
6. 最小批次锁、路线、事件、交接和双平面路由。

## Stop Boundary

`Phase 2 must run separately`。本轮在静态、失败关闭合同通过后停止。

- `NO_PHASE2`
- `NO_CRASH_RECOVERY_RUNTIME`
- `NO_PROCESS_TERMINATION`
- `NO_WORKER_RESTART`
- `NO_STATE_MUTATION`
- `NO_QUEUE_OR_RETRY_RUNTIME`
- `NO_PRODUCTION_LOCK_RUNTIME`
- `NO_CLEANUP_DELETE`
- `NO_DATABASE_OR_SCHEMA_CHANGE`
- `NO_PERSISTENT_OR_RUNTIME_OUTPUT`
- `NO_RAW_METADATA_ACCESS`
- `NO_FAKE_IDS_BUSINESS_DATA`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`

`push_allowed=false`。下一任务只能是单独 run 中的
`IDS-V0_1-STAGE043-P2`。

## Rollback

只回滚 Stage043 Phase 1 产物和本轮治理投影。保留 Stage042 复审历史、早期
stages、原始数据、manifest、evidence ledger、audit log、report snapshot、
数据库、运行输出、GitHub 状态和 app 入口。
