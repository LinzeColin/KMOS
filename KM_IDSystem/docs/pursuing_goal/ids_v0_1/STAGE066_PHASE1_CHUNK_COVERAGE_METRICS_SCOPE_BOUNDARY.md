# STAGE-066 Phase 1：Chunk 覆盖率指标范围、口径与边界确认

## 当前结论

本步骤只定义 `IDS-V0_1-STAGE066-P1` 的静态 Chunk 覆盖率指标合同。唯一合同上下文是冻结
Stage066 任务包、Stage065 已完成本地整阶段机械复审工件和 Batch061-070 上传锁。合同只登记未来每份
文档的解析覆盖率、Chunk 覆盖率和未覆盖页面的受控引用、分母口径、保护语义面、失败关闭、中文反馈和
回滚边界；没有读取、打开、解析、切分、计算、分类、生成、写入或删除任何业务资料、原始元数据、文档、
页面、章节、表格、parser 输出、来源片段、chunk、身份、哈希、版本、覆盖率、未覆盖页面、索引或业务结论。

`document_ref`、`page_ref`、`section_ref`、`parser_output_ref`、`table_context_ref`、`source_fragment_ref`、
`declared_document_page_set_ref` 和 `parser_page_set_ref` 均为不透明受控引用，当前不得填入正文、物理路径、
URL、页码值、章节名称、表格内容、来源片段或任何实际计数。`parse_coverage_ratio`、
`chunk_coverage_ratio` 与 `uncovered_page_refs` 仅是未来输出字段；本步骤没有实际比率、未覆盖页或质量结论。

## 职责交界

| 事项 | 唯一职责阶段 | 本步骤处置 |
| --- | --- | --- |
| 章节感知切块边界 | Stage063 | 只复用已复审引用边界，不重新检测或切分 |
| chunk 身份、哈希与版本 | Stage064 | 只引用已复审身份与版本字段，不生成或计算 |
| 工程语义资产目录 | Stage065 | 只引用已复审目录边界，不重新分类 |
| Chunk 覆盖率指标合同 | Stage066 | 只定义未来解析覆盖率、Chunk 覆盖率和未覆盖页口径 |
| 切块质量回归 | Stage067 | 不运行质量验证或回归 |
| 质量降级与人工复核 | Stage068 | 只声明未来人工处理入口，不产生质量或业务结论 |

## 指标、保护面与追溯边界

未来解析覆盖率的公式标签为 `parsed_page_reference_count / declared_document_page_reference_count`；未来
Chunk 覆盖率的公式标签为 `chunk_covered_page_reference_count / parsed_page_reference_count`。这两项只是
冻结的未来口径，并未求值。分母未知、为零、引用缺失或 document/page/parser 追溯无法确认时，未来流程
必须关闭，不能输出覆盖率或未覆盖页集合。

工程步骤、验收条款和参数表是三类保护语义面：不得因覆盖率口径被任意切断、合并或覆盖。未来记录必须
保留 document、page、section、parser output、表格上下文和来源片段六维引用，当前追溯绑定数为零。
长文档、跨页参数表、覆盖率分母、未覆盖页面、语义边界或来源追溯无法确认时，必须转业务线白箱人工处理。

来源文档与经授权的业务线人工复核始终保持权威；覆盖率字段、控制标签、模型输出或本合同不得替代来源
形成事实、决策结论或第二权威事实源。

## 失败、中文反馈与回滚

缺少章节感知切块、身份/版本、工程语义资产目录、document/page/section/parser output、表格上下文、来源
片段或页面集合引用，分母未知，遇到保护语义面，或未获授权执行覆盖率计算时，未来流程必须关闭并转人工
处理；当前没有任何实际失败、输入、覆盖率、未覆盖页、来源定位或处置记录。不得自动写入事实库、证据
账本、数据库、索引、报告、生产状态或业务线结论。

回滚只允许移除本步骤的范围说明、静态合同、聚焦用例、machine run、事件、机器事实投影、治理路线和
生成中文视图，恢复到 `STAGE065_REVIEWED_LOCAL_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_RUNTIME_DISABLED`。
真实资料、manifest、evidence ledger、audit log、已交付报告、事实库、数据库、索引、GitHub、OVH 与应用
状态不在回滚范围内。

一旦需要真实资料、授权 fixture、实际 parser 输出、实际切块、实际身份/版本、实际覆盖率、未覆盖页面、
质量回归、质量降级、索引、embedding、Agent、模型、OVH、生产、Phase2、整阶段复审、批次复审、上传或
推送，立即停止本步骤。

## 后续门

本步骤通过后的唯一后续门为 `IDS-STAGE066-P2-GATE`，且必须由新的独立 run 进入。
