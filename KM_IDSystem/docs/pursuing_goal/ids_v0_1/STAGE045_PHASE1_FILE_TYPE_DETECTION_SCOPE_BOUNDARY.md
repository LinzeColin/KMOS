# STAGE-045 Phase 1 File-Type Detection Scope Boundary

## Decision

`IDS-V0_1-STAGE045-P1` 只定义文件类型检测及其与 parser pipeline 的静态工程
合同。状态为 `PHASE1_ENGINEERING_CONTRACT_DETECTION_RUNTIME_DISABLED`，
`execution_ready=false`，`parser_dispatch_allowed=false`。

本阶段遵守 fail-closed：缺失、冲突、未知、不可读、无法验证或只有文件名证据，
均不得自动选择并执行 parser。静态 checker PASS 只说明合同一致，不能描述为
“文件已识别”“文档已解析”“证据已入库”或“生产可用”。

## Source And Prior Authority

- 唯一 taskpack member、批准归档、路线图、使用说明和执行索引均按精确 SHA-256
  绑定。
- Stage044 reviewed-local commit、root tree 与 `KM_IDSystem` tree 是本阶段前序事实。
- Stage013 只提供 extension/MIME 指纹元数据；它明确保留 MIME unknown/conflict，
  所以不得被当成可靠类型真相。
- Stage027 要求 safe extracted file 依次经过 hash、manifest、dedup、parser；类型
  检测不能让 extraction staging 直接进入 index、database 或 evidence。
- Stage037 拥有 `PARSE` job、11-state 状态机、attempt、lease、fencing 与 audit。
- Stage044 保护原始资料、manifest、evidence、audit、report、index 与成功输出；
  Stage045 不改变任何清理资格。
- Stage046–050 拥有详细 route、output、fallback、parser evaluation 与提示注入
  标记实现。本阶段只定义对接骨架，不提前实现这些 Stage。

## Input Contract

未来检测输入必须是 bounded reference-only metadata，并精确包含：

- `detection_request_id`；
- `source_fingerprint_ref` 与 `source_identity_ref`；
- `extension_signal`、`mime_signal`、`signature_signal`；
- `detector_contract_version` 与 `requested_at`。

三个 signal 必须分别保留 value、observation provenance、detector/version 和状态，
不能用调用方自报值冒充观察事实。控制合同不得包含 raw body、文件片段、密码、
secret 或无界日志。Phase 1 不创建输入记录，也不读取源文件产生 signal。

真实原始元数据根保持硬阻断。即使路径存在，也不得读取、列出、打开、hash、
扫描、复制、移动、覆盖、删除或修改其内容。

## Signal Trust And Conflict Rules

信号优先级是：

1. `FILE_SIGNATURE`
2. `MIME_OBSERVATION`
3. `FILENAME_EXTENSION`

该顺序不等于“签名一票通过”。文件签名是主要证据，但仍须做格式级验证；MIME
只有在观察 provenance 完整时才可作为 advisory evidence；扩展名永远只是
`ADVISORY_ONLY`。只有扩展名时置信度最高为 `LOW`，且不得产生可执行 route。

DOCX 与 XLSX 都可能具有 ZIP magic。仅识别 ZIP 签名不足以区分 OOXML；未来
DOCX 必须验证 `[Content_Types].xml` 与 `word/`，XLSX 必须验证
`[Content_Types].xml` 与 `xl/`。缺失或冲突时进入 review/unsupported，而不是
根据 `.docx` / `.xlsx` 文件名猜测。

CSV/TXT 通常没有唯一 magic。未来只允许 bounded、versioned heuristic 产生低
或中等置信候选，必须保留编码、分隔符、结构和错误证据；不得把“可解码”直接
当成 CSV/TXT 已确认。Phase 1 不执行任何 heuristic。

信号冲突统一为 `REVIEW_REQUIRED`；缺失信号失败关闭。不得调用远端服务识别类型，
不得把 raw signature bytes 写入治理、manifest、evidence 或日志。

## Detection And Confidence Contract

Phase 1 固化候选类型：`PDF`、`DOCX`、`XLSX`、`CSV`、`TXT`、`PNG`、
`JPEG`、`TIFF`、`UNKNOWN`、`CORRUPT_OR_UNREADABLE`。

检测状态只有：

- `TYPE_CONFIRMED`
- `TYPE_PROVISIONAL`
- `TYPE_CONFLICT_REVIEW_REQUIRED`
- `TYPE_UNKNOWN_REVIEW_REQUIRED`
- `TYPE_UNSUPPORTED`
- `TYPE_INPUT_BLOCKED`

置信度只有 `HIGH`、`MEDIUM`、`LOW`、`UNKNOWN`。这些是 Phase 1 schema 值，
不是已观测分布或生产阈值。`UNKNOWN`、conflict 与 corrupt/unreadable 都必须
显式失败或人工复核，不能静默跳过；文件名不能覆盖 MIME/签名冲突。

## Parser Route Boundary

Stage045 只给出类型到 route family 的候选映射：PDF、OOXML Word、OOXML
Workbook、delimited text、plain text、image 或 unsupported。候选结果还必须
包含 detection request、类型、状态、置信度和 signal provenance。

详细 parser route 合同与执行属于 Stage046。Phase 1 不 dispatch parser，不创建
queue/job，不调用 parser，也不直接写 index、evidence 或 database。无法确认的
类型只能进入 `ROUTE_REVIEW_REQUIRED`、`ROUTE_UNSUPPORTED` 或
`ROUTE_BLOCKED`，不得静默选择通用 parser。

## Parser Output Boundary

未来 parser output envelope 至少保留：

- `text`
- `tables`
- `pages`
- `sections`
- `confidence`
- `errors`

详细字段、cardinality 与 compatibility 由 Stage047 负责。任何空输出都不能静默
记为成功；错误必须 bounded、结构化、可追溯，parser 版本与 provenance 必须
存在。`text`、table cell、page text 与 section text 全部是 source-derived
untrusted evidence，不是高可信事实。

Parser 只产生 derivative candidate。它不得绕过质量门禁，把输出直接提升为
高可信 evidence、写入 evidence ledger、audit、manifest、index、report 或
database。质量证据缺失统一为 `BLOCK_DOWNSTREAM_PROMOTION`。

## Fallback Boundary

Stage048 拥有 fallback chain 实现。未来每次 parser 尝试、版本、输入 refs、错误、
置信度和停止原因都必须保留 provenance；低置信、unknown、unsupported、corrupt
或所有 parser 失败都要明确反馈。禁止 silent drop，禁止 silent parser switch，
禁止空结果伪装成功。

Phase 1 不执行 fallback，不提供生产 parser 优先级或阈值，也不声称任何格式已
成功解析。

## Prompt Injection Boundary

所有从文件正文、表格、页、section、metadata 或 OCR 候选中得到的类似指令文本，
都必须标为 `UNTRUSTED_EVIDENCE_TEXT`。它不得被解释为：

- `SYSTEM_INSTRUCTION`
- `TOOL_INSTRUCTION`
- `POLICY`
- `CONTROL_COMMAND`

源文本不能覆盖 IDS 系统规则，不能授权工具或改变安全门禁。进入任何下游模型前
必须有安全标记；实际提示注入识别与标记实现属于 Stage050。本 Phase 不读取文本、
不扫描提示词，也不应用 runtime marker。

## Job, State And Side-Effect Boundary

类型检测与 parser pipeline 的 orchestration job type 是 Stage037 的 `PARSE`。
Phase 1 不创建 job、不写 queue、不获取 claim/lock、不转换 state、不改变 terminal
history，也不运行 worker/retry/backpressure/lifecycle/crash/cleanup 能力。

本阶段也不：

- 打开、stat、hash、sniff、解码、解压或遍历任何业务文件；
- 执行 MIME、signature、container、CSV/TXT heuristic 或图像检测；
- 创建 parser output、manifest、document、chunk、index、report 或 runtime data；
- 连接 database、迁移 schema、写 evidence ledger 或 audit；
- 启动 backend、frontend、worker、外部 API 或生产 runtime。

## Phase 2 Gate

只有 source/predecessor/upstream hash、bounded input、三信号信任顺序、OOXML
容器规则、unknown/conflict/corrupt 失败关闭、route/output/fallback/prompt
边界、质量门禁和所有 no-runtime truth flags 同时通过，才把下一 gate 路由为
`IDS-STAGE045-P2-GATE`。

`Phase 2 must run separately`。Phase 1 不授权 Phase 2，不安装依赖，不生成
`.venv`、`node_modules`、`data`、`reports` 或 `outputs`。

## Stop Conditions

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

原始元数据边界保持 path-only，完全未触碰。若需要读取真实文件、检查真实 MIME
或签名、执行 parser/fallback、写持久态、进入 Phase 2、扩大到其他 KM 项目、
上传或重装应用，立即停止。

## Rollback

只撤销 Stage045 Phase 1 文档、合同、checker、tests 和最小治理投影。保留
Stage044 reviewed-local 与全部早期证据。rollback 不得打开、扫描、hash、解析、
移动、覆盖或删除 source/staging/runtime 路径，也不得更改 original、manifest、
evidence、audit、report、index、database 或 app/GitHub 状态。
