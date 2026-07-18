# STAGE-044 Phase 1 Entry Contract

## Identity

- Stage: `STAGE-044 · 半成品输出清理`
- Task: `IDS-V0_1-STAGE044-P1`
- Acceptance: `ACC-STAGE-044`
- Local code: `D07-S008`
- Domain: `D07 · 任务编排与机器控制`
- Entrance: `IDS 系统运营入口`
- Contract: `ids.half_product_cleanup.v0_1.p1`
- State: `PHASE1_ENGINEERING_CONTRACT_DELETE_DISABLED`
- Next gate: `IDS-STAGE044-P2-GATE`

## Goal

为失败、中断或安全暂停 attempt 留下的半成品定义可执行、可测试、可回滚的
清理合同。只有已证明由该 attempt 创建、位于批准 staging/cache root、可重建、
无保留或持有、无持久证据引用且 writer 已静默的临时产物，才可成为未来清理
候选。事实源、原始资料、数据库、manifest、evidence、audit、report、active
index、有效重试 checkpoint、owner-held artifact 与成功任务输出永不成为候选。

Phase 1 只固化静态工程合同和失败关闭 checker；不扫描目录、不解析候选、不
获取生产锁、不遍历文件系统、不移动、覆盖或删除任何文件，也不写 audit 或
运行输出。

## Source And Predecessor Binding

唯一批准成员
`IDS_v0_1_Final_Chinese_Revised/stages/STAGE-044_半成品输出清理.md`
的 SHA-256 为
`e7e98eb5497aa33124b944dfc1d00e15588a672c0f9accc4cda4a66fe1f72a53`。
机器合同同时绑定批准归档、路线图、使用说明、Stage043 已提交复审
commit/tree，以及 Stage029、Stage037–043 的精确清理和控制合同。本轮未读取
IDS 业务源或原始元数据内容。

## Entry Preconditions

- Stage043 仅以 `completed_reviewed_local` 关闭，绑定 commit
  `e7835134550e2776f0949870fcaf7d7b9a54bd01`。
- Stage037 仍是唯一任务状态、attempt、cleanup manifest 与半成品安全规则真源。
- Stage038–043 分别继续拥有 worker、retry/dead letter、resource pause、
  lock/fencing、lifecycle 与 crash recovery；Stage044 不重建这些运行时。
- 候选必须绑定批准 root 的 canonical identity、root-relative path 和
  `st_dev` / `st_ino` / `file_type` immutable lstat identity。
- 原始元数据根目录仍只是路径边界，完全未触碰。

## Phase 1 Deliverables

1. 本入口合同。
2. `STAGE044_PHASE1_HALF_PRODUCT_CLEANUP_SCOPE_BOUNDARY.md`。
3. `half_product_cleanup/stage044_half_product_cleanup_contract.json`。
4. `scripts/check_half_product_cleanup.py`。
5. `tests/test_stage044_half_product_cleanup.py`。
6. 最小批次锁、路线、事件、交接和双平面路由。

## Stop Boundary

`Phase 2 must run separately`。本轮在静态、失败关闭合同通过后停止。

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

`push_allowed=false`。下一任务只能是单独 run 中的
`IDS-V0_1-STAGE044-P2`。

## Rollback

只回滚 Stage044 Phase 1 产物和本轮治理投影。保留 Stage043 复审历史、早期
stage 证据、原始资料、source/runtime database、manifest、evidence ledger、
audit log、report snapshot、delivered report、checkpoint、active index、运行
输出、GitHub 状态和 app 入口。回滚本身不得扫描、移动、覆盖或删除任何运行
路径。
