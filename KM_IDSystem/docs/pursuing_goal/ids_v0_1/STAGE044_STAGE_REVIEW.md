# STAGE-044 Whole-Stage Independent Review

- Task: `IDS-V0_1-STAGE044-REVIEW`
- Acceptance: `ACC-STAGE-044`
- Result: `PASS_REVIEWED_LOCAL_DELETE_DISABLED`
- Review gate: `IDS-STAGE044-REVIEW-GATE`
- Next gate: `IDS-STAGE045-P1-GATE`（仅允许后续独立 run）
- Phase 4 commit: `5da8fdf64cab35545e717900e71ccbbb5dacb11c`
- Phase 4 `KM_IDSystem` tree: `4df0d01406b2021ef0c4968373b9649733a5f857`
- Finding count: 6（Critical 1 / Important 5 / Minor 0）

## Review Scope And Evidence

本轮独立复核 Stage 044 Phase 1–4 的任务包原文、来源哈希、Phase 4 commit/tree
ancestry、工程契约、reference-only candidate decision slice、十四个隔离场景、交付
合同、治理路由和禁止项。原文目标是清理由失败任务产生的残留临时半成品，不得清理
事实源或审计证据。

复核重新运行四阶段 checker 与测试，并用反例直接验证：可恢复状态、伪造 root/
manifest/evidence identity、任意 tracked input ref、creator/job 不一致、非规范路径、
深层契约篡改和中文状态过度宣称。所有检查保持 `delete_allowed=false`；没有扫描、
遍历、探测、移动、覆盖、删除、数据库、audit write、生产激活或持久运行时动作。

## Findings And Repairs

### STAGE044-REVIEW-F1 — Critical — repaired

`PAUSED` 与 `RETRY_WAIT` 原先会进入清理候选，但二者是可恢复非终态，仍由
resume/retry owner 管理，与“失败任务残留”来源边界冲突。候选态已收窄为
`FAILED`、`DEAD_LETTERED`、`CANCELLED`；`PAUSED` 与 `RETRY_WAIT` 永久走
`CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN`。

### STAGE044-REVIEW-F2 — Important — repaired

原 `_contract_fast_valid` 只校验契约子集，可能绕过 source、path、identity 与深层
字段完整性。现在快速入口复用完整 `evaluate_contract`，并以整个 runtime contract
的 canonical SHA-256 绑定全部嵌套字段；任一篡改都返回
`CLEANUP_CONTRACT_INVALID`。

### STAGE044-REVIEW-F3 — Important — repaired

候选 provenance 原先只做格式或“任意 Git-tracked ref”检查，未把 creator、root、
manifest、writer/resource evidence 与候选内容绑定。现在要求 creator 等于 job，
input refs 精确等于五个批准上游引用，root/manifest/writer/resource refs 均按 canonical
payload 派生；伪造值失败关闭。

### STAGE044-REVIEW-F4 — Important — repaired

`PurePosixPath` 规范化会静默接受 `./` 与重复 `/`，使一个路径存在多种词法身份。
现在要求原始字符串严格等于 canonical POSIX 表示，并拒绝空、`.`、`..` segment。

### STAGE044-REVIEW-F5 — Important — repaired

human status 原先只检查 action key 集，`label_zh` 可被改为“文件已自动删除”仍通过。
现在完整精确绑定 action、中文 label 与 severity，禁止产生超出事实的状态投影。

### STAGE044-REVIEW-F6 — Important — repaired

Phase 4 后缺少 Stage 044 的 durable whole-stage review 路由。已新增独立 review
checker/test/event/machine run，batch 与 roadmap 收口到
`stage044_completed_reviewed_local`，下一 gate 仅为后续独立
`IDS-V0_1-STAGE045-P1`；本轮没有执行 Stage 045。

## Rebound Evidence Chain

Phase 1 contract/checker/boundary 的修复哈希已精确回绑到 Phase 2；Phase 2
contract/checker/test/evidence 的修复哈希作为 reviewed forward-compatible digest
加入 Phase 3；Phase 3 checker 的新 digest 再绑定到 Phase 4。历史 Phase 1–4 commit
仍保留作原始交付证据，本 review commit 只记录修复后的 staged snapshot。

## Layered Validation

- Review TDD RED：`10` 项测试产生 `18` 个预期失败；最终 focused review suite
  `10/10` 通过（`159.695s`）。
- Stage 041–044 聚合最终 `268/268` 通过（`1189.358s`）。前序失败依次暴露历史
  Stage 041–043 current-route 兼容、Stage 044 P4→Review 迁移证据和一次已撤回的
  hash-chain 破坏；均保留在 machine run 中，没有静默忽略。
- IDS v0.1 全量 discovery 首轮 `1010/1014`，仅失败于 Stage 038/039 历史路由
  白名单；精确加入 `IDS-STAGE044-REVIEW -> IDS-STAGE045-P1-GATE` 后最终
  `1014/1014` 通过（`1665.517s`）。
- 最终 Stage005 `168/168` 通过（`34.019s`），七个 Stage038–044 review checker
  全部通过；`215` 条事件无解析、重复标识或语义错误，owner render 幂等且
  KM_IDSystem project dual-plane PASS。

## Fail-Closed Stop Conditions

- `NO_STAGE045_THIS_RUN`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`
- `NO_RAW_METADATA_ACCESS`
- `NO_CLEANUP_OR_DELETE_RUNTIME`
- Stage 045 必须在后续独立 run 从 `IDS-STAGE045-P1-GATE` 开始。
- Stage 041–050 未全部完成、独立十阶段复审和 batch upload gate 未通过前，禁止 push、
  merge 或 app reinstall。
