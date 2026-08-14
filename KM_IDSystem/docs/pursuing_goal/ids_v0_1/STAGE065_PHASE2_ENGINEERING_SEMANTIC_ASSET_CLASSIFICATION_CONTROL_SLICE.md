# STAGE-065 Phase 2：工程语义资产分类最小控制切片

## 当前结论

本步骤只执行 `IDS-V0_1-STAGE065-P2` 的纯内存、非业务、reference-only 控制切片。它严格复用
Phase 1 的十二字段输入和十六字段输出形状，以七条固定控制请求分别覆盖
`procedure`、`risk`、`acceptance`、`material`、`equipment`、`case` 和 `bid_response` 标签；输出只保留
不透明控制引用和低可信人工复核标记，不读取、打开、解析、切分、计算、分类或创建任何真实资料、chunk、
hash、分类记录、来源绑定、覆盖率、质量结果、索引或业务结论。

## 最小可运行边界

切片只接受一个包含七条固定控制请求的内存对象。每条请求必须完全匹配 Phase 1 的十二个引用字段并维持既定
顺序；新增字段、重排、未知标签或篡改任何控制引用都会被拒绝。标签只由固定控制请求标识投影，不能解释为
对真实文档或工程内容的分类。

输出固定十六字段，保留 `document_ref`、`page_ref`、`section_ref`、`parser_output_ref`、
`table_context_ref` 和 `source_fragment_ref` 六维控制引用；`chunk_id`、`chunk_hash` 和 `version` 都是
`:control:` 标签，未生成真实身份、版本或 hash。工程步骤、验收条款和参数表三类受保护语义面仍保持原子，
不被分类规则覆盖或切断。

## 低可信与人工处理

七条控制记录均标记为低可信并要求业务线白箱人工复核。这只是固定控制标签，既不是低质量 chunk 检测，也
不是覆盖率计算、质量回归或质量降级机制；这些职责分别留在 Stage066、Stage067 和 Stage068。来源文档和
业务线人工复核始终是权威，控制标签、模型文本或本切片不得成为第二权威事实源或业务决策依据。

## 禁止动作与回滚

不得读取真实资料、授权 fixture、正文、物理路径、实际页码、章节、表格、parser 输出或来源片段；不得执行
真实 parser、章节检测、切块、身份/版本/hash 生成、语义分类、覆盖率、质量、来源追溯、embedding、索引、
数据库、Agent、模型、OVH、生产、Phase3、整阶段复审、批次复审、上传或推送。

回滚只允许移除本 P2 范围说明、纯内存模块、控制合同、聚焦用例、machine run、事件、机器事实投影、治理
路线和生成中文视图，回到 `PHASE1_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_CONTRACT_RUNTIME_DISABLED`。
真实资料、manifest、evidence ledger、audit log、已交付报告、事实库、数据库、索引、GitHub、OVH 与应用
状态不在回滚范围内。

## 后续门

本步骤通过后的唯一后续门为 `IDS-STAGE065-P3-GATE`，且必须由新的独立 run 进入。
