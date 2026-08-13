# Stage063 Phase 3 · 章节感知切块受控专项场景

状态：`phase3_completed_local`  
任务：`IDS-V0_1-STAGE063-P3`  
下一门：`IDS-STAGE063-P4-GATE`

## 本阶段的可验证结论

本阶段只重放 Phase 2 的三条固定、非业务、`reference-only` 章节感知切块控制候选，并针对冻结任务包列出的专项表面输出六类显式人工处置：长文档、跨页参数表、施工步骤、参数表、引用页码，以及重复 chunk 的 embedding/index 写入边界。

- 六个场景仅保留 `document_ref`、`page_ref`、`section_ref`、`parser_output_ref`、`table_context_ref` 与 `source_fragment_ref` 的 `:control:` 引用形状。
- 六个场景均要求业务线白箱人工复核，静默丢弃数量为零；控制标签不构成真实长文档质量、真实跨页表格关系、真实施工步骤、真实参数表、真实页码、真实来源反查或真实 chunk 质量结论。
- “重复 chunk 不重复 embedding/index”在本阶段仅核验控制模块没有发起 embedding 或索引写入。没有计算 chunk 身份、版本或哈希，没有检测真实重复项，故不能把该控制边界表述为真实去重效果。
- “可从报告反查原文”在本阶段仅核验六维控制引用形状被保留；没有读取原文、验证真实页码或创建来源追溯绑定。

## 不在本阶段的范围

本阶段不读取、复制、打开、解析、检测、切分或写入真实业务资料、原始元数据、授权 fixture、文档、页面、章节、表格、来源片段或 parser 输出；不执行真实章节检测、chunk 身份/版本/哈希、语义资产分类、覆盖率、质量回归、质量降级、来源追溯绑定、embedding、索引、数据库或持久化；不运行 Agent、模型或模型 Token；不启动本地服务、OVH、生产运行、GitHub 上传或推送。

## 场景处置

| 控制类别 | 显式处置 | 自动切块/去重/写入 | 人工处理 |
| --- | --- | --- | --- |
| 长文档 | `LONG_DOCUMENT_REFERENCE_REQUIRES_HUMAN_BOUNDARY_REVIEW` | 否 | 是 |
| 跨页参数表 | `CROSS_PAGE_PARAMETER_TABLE_REFERENCE_REQUIRES_HUMAN_HANDLING` | 否 | 是 |
| 施工步骤 | `ENGINEERING_PROCEDURE_STEP_REFERENCE_REQUIRES_HUMAN_BOUNDARY_REVIEW` | 否 | 是 |
| 参数表 | `PARAMETER_TABLE_REFERENCE_REQUIRES_HUMAN_BOUNDARY_REVIEW` | 否 | 是 |
| 引用页码与来源反查 | `PAGE_REFERENCE_CONTROL_REQUIRES_HUMAN_SOURCE_CONFIRMATION` | 否 | 是 |
| 重复 chunk 写入边界 | `DUPLICATE_CHUNK_REFERENCE_REQUIRES_LATER_IDENTITY_AND_HUMAN_REVIEW` | 否 | 是 |

## 恢复与回滚

若本控制场景需要撤回，只撤回本 P3 的说明、合同、纯内存模块、用例、machine run、事件、机器事实投影、路线和生成中文视图，恢复到 `PHASE2_CHAPTER_AWARE_CHUNKING_CONTROL_SLICE_RUNTIME_DISABLED`。不得改变冻结任务包、P1/P2 工件、真实资料、`00_ORIGINAL_RAW_DATA`、manifest、evidence ledger、audit log、事实库、数据库、索引、GitHub、OVH 或应用状态。

## P4 交接条件

P4 之前仍需保持本 P3 的边界：后续交付只能依据经授权且可白箱复核的输入，且必须单独记录 JSONL 样例、覆盖率报告、低质量清单、策略边界及重新生成/版本回滚说明。若真实章节边界、跨页关系、来源位置或重复判断无法确认，必须保留人工处置，不得以本控制标签自动推进或写入。
