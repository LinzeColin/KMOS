# STAGE-046 Phase 1 Parser Routing Scope Boundary

## Decision

`IDS-V0_1-STAGE046-P1` 只定义 Stage045 detection result 到 parser route candidate
的静态工程合同。状态为
`PHASE1_ENGINEERING_CONTRACT_PARSER_DISPATCH_DISABLED`，
`execution_ready=false`，`parser_dispatch_allowed=false`。

静态 checker PASS 只说明 route schema、来源、前序和禁止项一致；不能描述为
“已选择解析器”“已解析文档”“fallback 已执行”“证据已入库”或“生产可用”。

## Approved Source And Snapshot Authority

- taskpack 唯一 Stage046 成员、批准归档、roadmap、instructions 和执行索引按精确
  SHA-256 绑定。
- Stage045 review commit `76027b8d...`、root tree 与 `KM_IDSystem` tree 是唯一前序。
- Stage045 type contract、delivery、review doc/checker/run、Stage037 state index 和
  raw-data boundary 从前序 commit 读取，不依赖可变 working tree 文本。
- Stage045 继续拥有文件类型检测；Stage046 只能消费受治理 detection result。

## Input Contract

未来 routing request 只接受 reference-only Stage045 detection result，必须包含：

- `routing_request_id` 与 `detection_request_id`；
- `source_fingerprint_ref` 与 `source_identity_ref`；
- `detected_type`、`detection_state`、`detection_confidence`；
- `detection_evidence_ref` 与 `detector_contract_version`；
- `parser_registry_version` 与严格 UTC `requested_at`。

调用方不能直接指定 parser，Stage046 不能重新读取文件、扩展名、MIME、signature
或 container 来推翻 Stage045。请求不得包含 source body/path、secret、无界文本或
原始异常。Phase1 不创建 routing request 记录。

## Eligibility And Fail-Closed Rules

- 只有 `TYPE_CONFIRMED/HIGH` 可形成 `ROUTE_CANDIDATE_READY_NOT_EXECUTED`。
- `TYPE_PROVISIONAL/MEDIUM|LOW` 必须 `ROUTE_REVIEW_REQUIRED`。
- conflict 与 unknown state 必须人工复核。
- `TYPE_UNSUPPORTED` 返回 `ROUTE_UNSUPPORTED`。
- `TYPE_INPUT_BLOCKED`、`UNKNOWN`、`CORRUPT_OR_UNREADABLE` 返回 blocked/review，
  永不进入 generic parser。
- caller override、unknown route 和 generic fallback 全部禁止。

route candidate 不是 dispatch 授权。即使类型与 route family 匹配，parser
implementation/version 缺失也必须返回
`ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE`。

## Static Route Registry

Phase1 固化六个 route family，覆盖八类已治理类型：

| Route | 类型 | Family |
|---|---|---|
| `ROUTE_PDF` | PDF | `PDF_PARSER` |
| `ROUTE_OOXML_WORD` | DOCX | `OOXML_WORD_PARSER` |
| `ROUTE_OOXML_WORKBOOK` | XLSX | `OOXML_WORKBOOK_PARSER` |
| `ROUTE_DELIMITED_TEXT` | CSV | `DELIMITED_TEXT_PARSER` |
| `ROUTE_PLAIN_TEXT` | TXT | `PLAIN_TEXT_PARSER` |
| `ROUTE_IMAGE` | PNG/JPEG/TIFF | `IMAGE_PARSER` |

registry 中 parser implementations 与 assigned versions 都为空。这是真实未实现状态，
不是缺省 parser 或生产配置。Phase2 才能在独立 run 中实现最小可运行切片。

## Output, Fallback And Prompt Boundaries

- Stage047 拥有详细 output 合同；至少保留 `text`、`tables`、`pages`、`sections`、
  `confidence`、`errors`，且全部内容字段是 untrusted candidate。
- Stage048 拥有 fallback；attempt/version/error/stop reason 必须可追溯，禁止 silent
  drop 和 silent parser switch。
- Stage050 拥有提示注入扫描/标记；source-derived text 必须在进入下游模型前标为
  `UNTRUSTED_EVIDENCE_TEXT`，不能成为系统指令或工具授权。

本 Phase 不创建 output，不执行 fallback，不读取文本，也不应用 runtime marker。

## Quality, Job And Side-Effect Boundary

route decision 的 fact level 只能是 `CANDIDATE`。质量证据缺失统一
`BLOCK_DOWNSTREAM_PROMOTION`；parser 结果不能绕过质量门写入高可信 evidence。

Stage037 仍拥有 `PARSE` job、queue、claim、attempt、state 与 terminal history。
Phase1 不创建 job，不准入 queue，不获取 lock，不转换状态，也不启动 backend、
worker、外部 API 或生产 runtime。

本阶段也不打开、stat、hash、sniff、解码、解压、遍历业务文件；不写 manifest、
evidence、audit、index、report、database、cache 或派生产物。

## Phase 2 Gate

只有来源与 Stage045 snapshot、reference-only input、route eligibility、六类 route、
八类格式、Stage047/048/050 ownership、质量/状态边界和所有 false truth flags 同时
通过，才把下一 gate 路由到 `IDS-STAGE046-P2-GATE`。

`Phase 2 must run separately`。Phase1 不授权 Phase2，不安装依赖，不生成
`.venv`、`node_modules`、`data`、`reports` 或 `outputs`。

## Stop Conditions

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

若需要读取真实文件、加载 runtime registry、选择或执行 parser、运行 fallback、写
持久态、进入 Phase2、扩展到其他 KM 项目、上传或重装，立即停止。

## Rollback

只撤销 Stage046 Phase1 文档、合同、checker、tests 和最小治理投影。保留 Stage045
reviewed-local 与全部历史证据；rollback 不得影响 source、manifest、evidence、audit、
index、report、database、runtime、GitHub 或 app 状态。
