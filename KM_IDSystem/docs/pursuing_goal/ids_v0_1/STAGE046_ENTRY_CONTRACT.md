# STAGE-046 Phase 1 Entry Contract

## Identity

- Stage: `STAGE-046 · 解析器路由合同`
- Task: `IDS-V0_1-STAGE046-P1`
- Acceptance: `ACC-STAGE-046`
- Local code: `D08-S002`
- Domain: `D08 · 解析器路由`
- Entrance: `IDS 系统运营入口`
- Contract: `ids.parser_routing.v0_1.stage046.p1`
- State: `PHASE1_ENGINEERING_CONTRACT_PARSER_DISPATCH_DISABLED`
- Next gate: `IDS-STAGE046-P2-GATE`

## Goal

把 Stage045 已治理的文件类型检测结果转换成明确、可测试、可回滚的解析器候选
路由合同。合同覆盖 PDF、DOCX、XLSX、CSV、TXT、PNG、JPEG、TIFF 六个 route
family；未知、损坏、冲突、低置信或输入阻断必须显式复核、unsupported 或 blocked。

Phase 1 只交付静态工程合同和失败关闭 checker。它不重新检测文件类型，不读取
业务文件，不加载运行时 parser registry，不选择、分派或执行 parser，不执行
fallback，也不创建 parser output、job、manifest、evidence、audit、index、report、
database 或任何运行输出。

## Source And Predecessor Binding

唯一批准成员
`IDS_v0_1_Final_Chinese_Revised/stages/STAGE-046_解析器路由合同.md`
的 SHA-256 是
`955cdf40f365c05853a87269eb02aa46e5922807e0bb0c48d9b99cfca9bc1d39`。
合同同时绑定批准归档、roadmap、instructions、执行索引，以及已提交 Stage045
review commit/root tree/KM_IDSystem tree。Stage045 上游文件均从 commit
`76027b8dc89e325c212d492d7f5df88357ea7112` 读取并重新计算哈希，避免后续
Handoff 前向路由维护改变历史前序事实。

## Entry Preconditions

- Stage045 已完成四个 Phase 与独立复审，七项发现全部关闭。
- Stage045 是文件类型、检测状态与置信度的唯一上游权威；Stage046 不重新 sniff。
- `TYPE_CONFIRMED/HIGH` 只产生未执行 route candidate；其余状态失败关闭或复核。
- Stage037 仍拥有 `PARSE` job 与状态机；本 Phase 不创建或改变 job。
- Stage047、048、050 分别拥有详细 output、fallback 和提示注入实现。
- 原始元数据根保持 path-only 禁区，本轮完全不触碰。

## Phase 1 Deliverables

1. 本入口合同。
2. `STAGE046_PHASE1_PARSER_ROUTING_SCOPE_BOUNDARY.md`。
3. `parser_routing/stage046_parser_routing_contract.json`。
4. `scripts/check_parser_routing.py`。
5. `tests/test_stage046_parser_routing.py`。
6. 最小 batch、roadmap、event、handoff 与双平面治理路由。

## Stop Boundary

`Phase 2 must run separately`。本轮在静态合同和治理门通过后停止。

- `NO_PHASE2`
- `NO_SOURCE_FILE_OPEN`
- `NO_FILE_TYPE_REDETECTION`
- `NO_PARSER_REGISTRY_RUNTIME_LOAD`
- `NO_PARSER_ROUTE_EXECUTION`
- `NO_PARSER_DISPATCH`
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
`IDS-V0_1-STAGE046-P2`。

## Rollback

只回滚 Stage046 Phase 1 合同、checker、tests、文档和治理投影，返回已复审的
Stage045 snapshot。不得打开、扫描、解析、移动、覆盖或删除 source，也不得修改
manifest、evidence ledger、audit log、index、report、database、GitHub 或 app。
