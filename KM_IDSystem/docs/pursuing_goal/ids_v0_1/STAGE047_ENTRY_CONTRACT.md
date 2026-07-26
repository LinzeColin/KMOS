# STAGE-047 Phase 1 Entry Contract

## Identity

- Stage: `STAGE-047 · 解析器输出合同`
- Task: `IDS-V0_1-STAGE047-P1`
- Acceptance: `ACC-STAGE-047`
- Local code: `D08-S003`
- Domain: `D08 · 解析器路由`
- Entrance: `IDS 系统运营入口`
- Contract: `ids.parser_output.v0_1.stage047.p1`
- State: `PHASE1_ENGINEERING_CONTRACT_PARSER_OUTPUT_RUNTIME_DISABLED`
- Next gate: `IDS-STAGE047-P2-GATE`

## Goal

把 Stage045 文件类型身份与 Stage046 解析路线结果收敛成一个精确、可测试、可回滚的
parser output 工程合同。每个未来输出必须包含 `text`、`tables`、`pages`、
`sections`、`confidence`、`errors`，并保留 detection、route、source、parser
family/version 的完整引用链。

Phase 1 只交付静态合同和 fail-closed checker。它不打开业务文件，不重新检测类型或
评估 route，不选择、分派或执行 parser，不创建 runtime output，不运行 fallback、
差异评估或提示注入扫描，也不写 manifest、evidence ledger、audit、index、report、
database 或任何生产状态。

## Source And Predecessor Binding

唯一批准成员
`IDS_v0_1_Final_Chinese_Revised/stages/STAGE-047_解析器输出合同.md`
的 SHA-256 是
`e1d5bdb219b6f16ca7fec4e4455e7acba1ecbae9803a7c13721b75895671d2f4`。
批准归档、roadmap、instructions 与执行索引均按精确哈希绑定。

唯一前序是已提交并复审的 Stage046 commit
`c7d66380cfab7cf00ccbb9af34ef43a7f44a7bde`，root tree 为
`455b675a23243a8978b332e07e4a4cadcc532038`，`KM_IDSystem` tree 为
`98d21d245ccee585795cbc6e6180a8fcafda7f75`。Stage045 detection、Stage046
Phase1–4、整阶段复审与 raw-data 边界都从该 immutable snapshot 读取并重新哈希。

## Entry Preconditions

- Stage046 四个 Phase 与独立复审已完成，六项复审发现全部关闭。
- Stage045 继续拥有文件类型与 detection identity；Stage047 不重新 sniff。
- Stage046 继续拥有 route result；Stage047 不把候选路线当成 dispatch 授权。
- 输出身份只证明 canonical projection 完整性，不证明外部来源、真实性或质量通过。
- parser version 必须明确且不能使用 placeholder，才能形成未来候选 output。
- Stage048、049、050 分别保留 fallback、差异评估与提示注入 runtime ownership。
- 原始元数据根保持 path-only 禁区，本轮完全不触碰。

## Phase 1 Deliverables

1. 本入口合同。
2. `STAGE047_PHASE1_PARSER_OUTPUT_SCOPE_BOUNDARY.md`。
3. `parser_output/stage047_parser_output_contract.json`。
4. `scripts/check_parser_output.py`。
5. `tests/test_stage047_parser_output.py`。
6. 最小 batch、roadmap、event、handoff 与双平面治理路由。

## Stop Boundary

`Phase 2 must run separately`。本轮只在静态合同、checker、测试和治理证据通过后停止。

- `NO_PHASE2`
- `NO_SOURCE_FILE_OPEN`
- `NO_FILE_TYPE_REDETECTION`
- `NO_ROUTE_EVALUATION`
- `NO_PARSER_DISPATCH`
- `NO_PARSER_EXECUTION`
- `NO_PARSER_OUTPUT_RUNTIME`
- `NO_FALLBACK_EXECUTION`
- `NO_DIFFERENTIAL_EVALUATION`
- `NO_PROMPT_INJECTION_SCAN_OR_MARKER_RUNTIME`
- `NO_QUALITY_GATE_EXECUTION`
- `NO_EVIDENCE_PROMOTION`
- `NO_JOB_OR_STATE_MUTATION`
- `NO_MANIFEST_AUDIT_DATABASE_INDEX_REPORT_OR_RUNTIME_WRITE`
- `NO_RAW_METADATA_ACCESS`
- `NO_FAKE_IDS_BUSINESS_DATA`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`

`push_allowed=false`。下一任务只能是未来独立 run 中的
`IDS-V0_1-STAGE047-P2`。

## Rollback

只回滚 Stage047 Phase 1 合同、checker、tests、文档和治理投影，返回已复审的
Stage046 snapshot。不得清理或改变 source、manifest、evidence ledger、audit、index、
report、database、GitHub 或 app 状态。
