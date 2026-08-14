# STAGE-067 Phase 3：切块质量回归受控专项场景

## 当前范围

本步骤只执行 `IDS-V0_1-STAGE067-P3` 的纯内存、非业务、reference-only 专项场景验证。它重放
Phase 2 的四条固定切块质量回归控制记录，并把冻结任务包的专项表面映射为六类显式业务线白箱人工处置：长文档、
跨页表格、施工步骤、参数表、引用页码与来源反查，以及重复 chunk 的 embedding/index 写入边界。

所有场景只保留 `document_ref`、`page_ref`、`section_ref`、`parser_output_ref`、`table_context_ref`
和 `source_fragment_ref` 的 `:control:` 引用形状。它们不读取、打开、解析、切分、计算、检测、分类或创建任何真实
资料、页面、chunk、hash、质量结果、重复项、来源绑定、索引或业务结论。

## 场景处置

| 控制类别 | 显式处置 | 自动切块、去重或写入 | 人工处理 |
| --- | --- | --- | --- |
| 长文档 | `LONG_DOCUMENT_CHUNK_QUALITY_CONTROL_REQUIRES_HUMAN_BOUNDARY_REVIEW` | 否 | 是 |
| 跨页表格 | `CROSS_PAGE_TABLE_CHUNK_QUALITY_CONTROL_REQUIRES_HUMAN_HANDLING` | 否 | 是 |
| 施工步骤 | `ENGINEERING_PROCEDURE_CHUNK_QUALITY_CONTROL_REQUIRES_HUMAN_BOUNDARY_REVIEW` | 否 | 是 |
| 参数表 | `PARAMETER_TABLE_CHUNK_QUALITY_CONTROL_REQUIRES_HUMAN_BOUNDARY_REVIEW` | 否 | 是 |
| 引用页码与来源反查 | `CITATION_PAGE_CHUNK_QUALITY_CONTROL_REQUIRES_HUMAN_SOURCE_CONFIRMATION` | 否 | 是 |
| 重复 chunk 写入边界 | `DUPLICATE_CHUNK_QUALITY_CONTROL_REQUIRES_LATER_IDENTITY_AND_HUMAN_REVIEW` | 否 | 是 |

“重复 chunk 不重复 embedding/index”在本阶段只核验控制模块没有发起 embedding 或索引写入。它不检测真实
重复项、不验证真实 `chunk_id`、`chunk_hash` 或版本，也不形成真实去重效果。报告到原文位置的能力也只核验六维
控制引用形状，真实页码、章节、表格和来源反查仍须由业务线白箱人工确认。

## 单一权威与停止条件

来源文档和业务线人工复核始终是唯一权威。P2 控制记录、P3 场景标签、模型文本和本步骤的验证结果均不能成为
第二权威事实源或业务决策依据。工程步骤、验收条款和参数表三类受保护语义面保持原子，不因控制场景被切断。

本阶段不读取真实资料、授权 fixture、正文、物理路径、实际页码、章节、表格、parser 输出或来源片段；不执行
真实 parser、章节检测、切块、身份/版本/hash 生成、语义分类、覆盖率、质量、质量降级、来源追溯、embedding、
索引、数据库、Agent、模型、OVH、生产、Phase4、整阶段复审、批次复审、上传或推送。

## 回滚与后续门

回滚只允许撤回本 P3 的说明、合同、纯内存模块、用例、machine run、事件、机器事实投影、路线和生成中文视图，
恢复到 `PHASE2_CHUNK_QUALITY_REGRESSION_CONTROL_SLICE_RUNTIME_DISABLED`。不得改变冻结任务包、P1/P2 工件、真实
资料、`00_ORIGINAL_RAW_DATA`、manifest、evidence ledger、audit log、事实库、数据库、索引、GitHub、OVH 或应用状态。

完成本阶段本地验证后，唯一后续门为 `IDS-STAGE067-P4-GATE`，且必须由新的独立 run 进入。
