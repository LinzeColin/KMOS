# STAGE-047 Phase 1 Parser Output Scope Boundary

## Decision

`IDS-V0_1-STAGE047-P1` 只定义 parser output 的静态 envelope、六个核心字段、嵌套对象、
lineage、失败状态、质量门和下游 ownership。状态为
`PHASE1_ENGINEERING_CONTRACT_PARSER_OUTPUT_RUNTIME_DISABLED`，
`execution_ready=false`，`parser_execution_allowed=false`。

checker PASS 只说明 schema、来源、前序、边界和禁止项一致；不能描述为“已解析文件”、
“已生成 parser output”“fallback 已运行”“质量已通过”“证据已入库”或“生产可用”。

## Approved Source And Snapshot Authority

- taskpack 唯一 Stage047 成员、批准归档、roadmap、instructions 和执行索引按精确
  SHA-256 绑定。
- Stage046 review commit `c7d66380...` 及其 root/KMIDS tree 是唯一前序。
- Stage045 delivery、Stage046 Phase1–4 合同、Stage046 review 文档/checker/run 与
  raw-data boundary 都从该 commit 读取，拒绝可变 working tree 伪装成前序证据。
- Stage046 review 必须保持 `completed_reviewed_local`、零 open finding，且本 commit
  必须是当前 HEAD 的祖先。

## Input Boundary

未来 Stage047 input 是 reference-only wrapper，不包含 source body/path。wrapper 必须
携带 Stage046 route result、source identity、请求的 output schema 与严格 UTC 时间。

- detection authority：Stage045；route authority：Stage046。
- route result 必须匹配 `ids.stage046.parser_routing_result.v1`。
- `route_result_id` 按 canonical JSON 计算
  `route-result:sha256:<64-lower-hex>`；它只证明完整性，不是外部 provenance、授权或质量
  证明。
- source、detection、routing、route、parser family/version 必须形成一致 lineage。
- blocked/review/unsupported route 不得伪装成 parser output input。
- placeholder parser version 不能形成候选 output。
- 路径、URI、原始异常、secret、无界文本和 raw metadata 均不允许进入 wrapper。

本 Phase 不创建或持久化 input wrapper。

## Exact Output Envelope

未来 output envelope 必须精确包含：

1. `output_id`
2. `output_schema_version`
3. `route_result_id`
4. `routing_request_id`
5. `detection_result_id`
6. `source_identity_ref`
7. `parser_family`
8. `parser_version`
9. `status`
10. `text`
11. `tables`
12. `pages`
13. `sections`
14. `confidence`
15. `errors`
16. `content_security`
17. `quality_gate`
18. `produced_at`

unknown top-level 字段失败关闭。`output_id` 是 exact output projection 的 canonical
SHA-256，格式为 `parser-output:sha256:<64-lower-hex>`；它不证明 provenance、事实正确、
质量通过或下游授权。

允许的状态只有：

- `OUTPUT_CANDIDATE_NOT_VALIDATED`
- `OUTPUT_PARTIAL_REVIEW_REQUIRED`
- `OUTPUT_FAILED_EXPLICIT`

不存在可绕过质量门的 `SUCCEEDED` 或 `HIGH_TRUST` 状态。

## Six Core Fields

### `text`

`STRING_OR_NULL`，来源固定为 source-derived，并标记
`UNTRUSTED_EVIDENCE_TEXT`。它不能被解释为 system/tool/policy/control 指令。`null`
只允许在存在非文本结构或显式 safe error 时出现。

### `tables`

有序数组，每项必须使用 `ids.parser_output.table.v0_1`，包含 `table_id`、页面/章节引用、
二维 cells、confidence 与 errors。table IDs 唯一；cells 是不可信标量文本或 null；公式
不得执行。

### `pages`

有序数组，每项必须使用 `ids.parser_output.page.v0_1`，包含唯一 `page_id`、正整数
`page_number`、text、table refs、confidence 与 errors。页号唯一且递增。

### `sections`

有序数组，每项必须使用 `ids.parser_output.section.v0_1`，包含唯一 `section_id`、title、
正整数 level、page refs、text、table refs、confidence 与 errors；层级不得成环。

### `confidence`

只允许 `HIGH`、`MEDIUM`、`LOW`、`UNKNOWN`。Phase1 不编造 numeric threshold；未测量
必须是 `UNKNOWN`，且 `UNKNOWN`/`LOW` 不能自动提升证据。

### `errors`

有序 safe error 数组，每项精确包含 `code`、`severity`、`retryable`、`message_key`。
禁止原始 exception、stack、path、URI、secret 或业务内容回显；失败必须显式，不得空数组
静默成功。

## Lineage, Completeness And Failure Rules

- route/detection/source identity chain 必须完整且一致。
- 所有 page/section/table 内部引用必须解析；重复 ID 与 orphan ref 均拒绝。
- candidate 至少包含 non-empty text/tables/pages/sections 之一。
- 全空且无 error 的 candidate 失败关闭。
- partial/failed 必须携带 safe error；failed output 的内容必须为空。
- invalid identity、lineage、shape、confidence 或 error 返回显式 reject，不创建下游引用。
- silent success、silent drop 与 silent parser switch 全部禁止。

## Quality And Evidence Boundary

parser content 的初始 fact level 固定为 `CANDIDATE`，quality gate 初始为
`UNASSESSED`。Phase1 允许的 gate state 只有 `UNASSESSED`、`REVIEW_REQUIRED`、
`BLOCKED`，不能声明 PASS。

没有质量证据时必须 `BLOCK_DOWNSTREAM_PROMOTION`。parser output 不能直接写高可信
evidence、manifest、evidence ledger、audit、index、report 或 database，也不能修改
原始资料或已交付输出。

## Downstream Ownership

- Stage048：fallback runtime、attempt/version/error/stop reason；禁止 silent drop/switch。
- Stage049：差异化解析比较；候选输出保持分离，比较不能重写 source output 或自我提升。
- Stage050：提示注入扫描/标记；Phase1 marker state 仅是
  `REQUIRED_NOT_APPLIED`，没有执行扫描或标记。
- Stage037：`PARSE` job/state；Stage046：route；Stage047：output schema。

本 Phase 不抢占这些 runtime ownership。

## Phase 2 Gate

只有来源、Stage046 immutable snapshot、detection/route lineage、18-field envelope、六字段
shape、嵌套 schema、empty/partial/failure 规则、质量/证据门、Stage048/049/050 ownership
和所有 runtime false truth flags 同时通过，才把下一 gate 路由到
`IDS-STAGE047-P2-GATE`。

`Phase 2 must run separately`。Phase1 不授权 Phase2，不安装依赖，不生成 `.venv`、
`node_modules`、`data`、`reports` 或 `outputs`。

## Stop Conditions

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

若需要读取真实文件、执行 parser、创建 output、运行 fallback/差异评估/提示扫描、写持久
态、进入 Phase2、扩展其他 KM 项目、上传或重装，立即停止。

## Rollback

只撤销 Stage047 Phase1 文档、合同、checker、tests 和最小治理投影，返回 Stage046
reviewed-local snapshot。不得删除、移动、覆盖或修改 source、manifest、evidence、audit、
index、report、database、runtime、GitHub 或 app 状态。
