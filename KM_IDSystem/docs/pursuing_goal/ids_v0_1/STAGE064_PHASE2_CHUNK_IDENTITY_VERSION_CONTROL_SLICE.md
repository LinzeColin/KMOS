# Stage064 Phase 2 · Chunk 身份与版本最小可运行控制切片

## 当前目标

在 Stage064 P1 的十字段仅引用输入和十四字段未来身份/版本输出合同上，提供一个只在内存中运行的、固定且非业务的身份与版本控制切片。它只机械验证受控引用、三类受保护工程语义面、六维追溯引用和待人工复核状态能够被投影；不读取、打开、解析、切分、计算或保留真实文档、页面、章节、表格、来源片段、parser 输出或 chunk。

## 固定控制范围

- 输入严格为三条固定 `:control:` 身份/版本请求，分别对应 `ENGINEERING_PROCEDURE_STEP`、`ACCEPTANCE_CLAUSE` 和 `PARAMETER_TABLE`。
- 三条请求均只使用不透明控制引用。`document_ref`、`page_ref`、`section_ref`、`parser_output_ref`、`table_context_ref`、`source_fragment_ref`、`chunk_identity_ref` 和 `chunk_version_ref` 不含真实路径、URL、正文、页码内容、章节文本、表格内容、parser 输出或真实身份。
- 每条请求只投影一个十四字段身份/版本控制记录。记录中的 `chunk_id`、`chunk_hash`、`document_id`、`page`、`section` 和 `version` 都是控制字段标签，不是实际生成、绑定、计算或持久化的身份、哈希、文档、页码、章节或版本。
- 固定映射只保留 Stage063 已有的受保护语义面标签，不执行 Stage065 的真实语义资产分类；覆盖率、质量回归和质量降级仍分别由 Stage066、Stage067 和 Stage068 负责。

## 可执行边界

- 允许：纯内存输入字段验证、固定控制记录投影、十四字段形状断言、受保护表面一对一原子记录、六维控制追溯引用、中文反馈，以及拒绝未知、重排或篡改的控制输入。
- 不允许：真实资料或 parser 输出读取、章节检测、文本切分、实际 `chunk_id` 生成、实际 `chunk_hash` 计算、实际 `document_id` 绑定、版本生成、真实语义分类、覆盖率计算、质量回归、质量降级、跨页参数表处理、来源追溯绑定、重复检测、embedding、索引、数据库、持久化、Agent、模型调用、模型 Token、服务、OVH、生产、上传或推送。
- 来源文档与业务线白箱人工复核持续保持唯一权威；控制记录不能成为业务事实、决策结论、索引记录或第二权威事实源。

## 验收与回滚

- 聚焦用例必须证明三条固定控制请求能投影为三条十四字段控制记录，六维追溯引用保持控制形状，三类受保护表面不被任意拆分，所有记录均要求人工复核，并拒绝异常输入。
- 回滚只撤回本 P2 说明、切片合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理路线和生成中文视图，回到 `PHASE1_CHUNK_IDENTITY_AND_VERSION_CONTRACT_RUNTIME_DISABLED`。
- 不触及真实资料、`00_ORIGINAL_RAW_DATA`、manifest、evidence ledger、audit log、已交付报告、事实库、索引、数据库、GitHub、OVH 或应用状态。

## 下一门

本切片完成后，下一步仅允许在新的独立 run 进入 `IDS-STAGE064-P3-GATE`。P2 不进入 P3、整阶段复审、批次复审、OVH、生产或上传。
