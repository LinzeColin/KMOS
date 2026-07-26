# STAGE-045 Phase 1 Entry Contract

## Identity

- Stage: `STAGE-045 · 文件类型检测`
- Task: `IDS-V0_1-STAGE045-P1`
- Acceptance: `ACC-STAGE-045`
- Local code: `D08-S001`
- Domain: `D08 · 解析器路由`
- Entrance: `IDS 系统运营入口`
- Contract: `ids.file_type_detection.v0_1.p1`
- State: `PHASE1_ENGINEERING_CONTRACT_DETECTION_RUNTIME_DISABLED`
- Next gate: `IDS-STAGE045-P2-GATE`

## Goal

为扩展名、MIME 与文件签名建立可执行、可测试、可回滚的文件类型检测合同，
且永不盲目信任文件名。合同定义检测输入、类型与置信度、parser 候选路由、
`text` / `tables` / `pages` / `sections` / `confidence` / `errors` 输出骨架、
显式 fallback，以及把源文档文本标为 `UNTRUSTED_EVIDENCE_TEXT` 的安全边界。

Phase 1 只交付静态合同和失败关闭 checker。它不打开源文件，不观察扩展名、
MIME 或签名，不检查容器内容，不执行类型分类、parser route、parser、fallback
或提示注入扫描，也不创建 job、写 manifest、evidence、audit、database、index
或任何运行输出。

## Source And Predecessor Binding

唯一批准成员
`IDS_v0_1_Final_Chinese_Revised/stages/STAGE-045_文件类型检测.md`
的 SHA-256 为
`4eac237a7f63d764cf71789d4949a5168cbe8fe24e1fe7eb816baabe04bb4d27`。
机器合同同时绑定批准归档、路线图、使用说明、执行索引、Stage044 reviewed-local
commit/root tree/KM_IDSystem tree，以及 Stage013、Stage027、Stage037 和 Stage044
的直接权威证据。本轮未读取 IDS 业务文件或原始元数据内容。

## Entry Preconditions

- Stage044 已在 commit `97044d0b6475ebf41b4f79311164a392979305a0`
  关闭为 `completed_reviewed_local`，真实清理与删除仍禁用。
- Stage013 的 extension/MIME 只读指纹结果是 advisory 上游，不能代替文件签名。
- Stage027 要求 extracted file 经 hash、manifest、dedup 后才可到 parser 边界；
  Stage045 不绕过该顺序。
- Stage037 仍拥有 `PARSE` job 与全部状态迁移；Stage045 不创建或改变 job。
- `STAGE-046..050` 分别拥有详细 route、output、fallback、评估与提示注入标记
  实现；本 Phase 只定义兼容边界，不提前实现后续 Stage。
- 原始元数据根目录仍只是 path-only 禁区，完全未触碰。

## Phase 1 Deliverables

1. 本入口合同。
2. `STAGE045_PHASE1_FILE_TYPE_DETECTION_SCOPE_BOUNDARY.md`。
3. `file_type_detection/stage045_file_type_detection_contract.json`。
4. `scripts/check_file_type_detection.py`。
5. `tests/test_stage045_file_type_detection.py`。
6. 最小 batch、roadmap、event、handoff 与双平面治理路由。

## Stop Boundary

`Phase 2 must run separately`。本轮在静态合同和治理门通过后停止。

- `NO_PHASE2`
- `NO_SOURCE_FILE_OPEN`
- `NO_FILE_SCAN_OR_HASH`
- `NO_FILE_TYPE_RUNTIME`
- `NO_MIME_OR_SIGNATURE_INSPECTION`
- `NO_CONTAINER_INSPECTION`
- `NO_PARSER_ROUTE_EXECUTION`
- `NO_PARSER_EXECUTION`
- `NO_FALLBACK_EXECUTION`
- `NO_PROMPT_INJECTION_SCAN_OR_MARKER_RUNTIME`
- `NO_EVIDENCE_PROMOTION`
- `NO_JOB_OR_STATE_MUTATION`
- `NO_MANIFEST_AUDIT_DATABASE_INDEX_OR_RUNTIME_WRITE`
- `NO_RAW_METADATA_ACCESS`
- `NO_FAKE_IDS_BUSINESS_DATA`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`

`push_allowed=false`。下一任务只能是未来单独 run 中的
`IDS-V0_1-STAGE045-P2`。

## Rollback

只回滚 Stage045 Phase 1 产物和本轮治理投影。保留 Stage044 reviewed-local 与
全部早期证据，不打开、扫描、hash、解析、移动、覆盖或删除任何源文件；不清理
manifest、evidence ledger、audit log、report、index、database、运行输出、
GitHub 状态或 app 入口。
