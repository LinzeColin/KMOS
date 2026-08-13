# STAGE-059 Phase 1：事实抽取基线范围、输入输出与边界确认

## 当前结论

本步骤只定义 `IDS-V0_1-STAGE059-P1` 的静态事实抽取基线合同。唯一合同上下文是冻结
Stage059 任务包与 Stage058 已完成整阶段复审工件；Stage057 的 XLSX/CSV 接入合同和 Stage058
的 Schema 推断合同保持各自唯一职责，本步骤不复制、替换或扩展其业务事实。合同只登记未来从
受控 Schema profile 抽取生产、质量和检验事实所需的抽象引用、typed-value 字段、来源位置、
证据边界和停止条件；它没有读取、打开、解析、推断、写入、复制、移动或删除任何真实表格、
工作表、单元格、公式、数据库、来源路径或业务资料。

字段名、枚举和计数仅描述未来受控实施的接口，不是工作表内容、列名、字段映射、typed value、
数值、日期、单位、设备、材料、质量结果、来源正文或统计结论。因此本步骤不建立第二权威事实源。

## 职责交界

| 事项 | 唯一职责阶段 | 本步骤处置 |
| --- | --- | --- |
| XLSX/CSV 接入合同 | Stage057 | 仅引用已复审的接入边界，不读取或重写输入 |
| 表格 Schema 推断 | Stage058 | 仅引用已复审的 Schema profile 与字段候选边界，不重新推断 |
| 结构化事实抽取 | Stage059 | 只定义未来生产、质量、检验事实的输入、输出与失败关闭，不抽取或写入事实 |
| 表格到 RAG 摘要 | Stage060 | 不生成摘要；摘要不能替代事实或成为数值权威 |
| 结构化数据质量测试 | Stage061 | 不验证真实空表、单位、日期、异常或重复行 |
| 表格证据绑定 | Stage062 | 只定义未来引用字段，不创建 evidence、document、sheet、row 或 column 绑定 |

## 输入、事实输出与数值边界

未来事实抽取输入固定为十二个非内容引用字段：`source_identity_ref`、`source_document_ref`、
`file_format`、`workbook_ref`、`worksheet_ref`、`header_row_ref`、`row_range_ref`、
`column_range_ref`、`schema_profile_ref`、`field_candidate_ref`、`record_type` 和 `evidence_ref`。
仅允许 XLSX、CSV、生产记录和质检记录；输入不保存来源正文、物理路径、工作表、表头、单元格
或公式内容。

未来 typed fact 输出固定为 25 个引用或字段接口，明确 `PRODUCTION_FACT`、`QUALITY_FACT` 和
`INSPECTION_FACT` 三类事实。`typed_value`、字段名、单位、日期、设备、材料和质量结果在本步骤
只是字段定义，不是已抽取或已确认的值；没有创建事实、typed value、统计、数据库、RAG 摘要、
evidence 或持久状态。

数值统计未来只能基于带来源文档、工作表、表头行、行列范围与证据引用的结构化事实。模型不得
根据文本猜测数值、单位、日期、质量结果、事实类型或统计结论；RAG 摘要不得替代结构化事实、
成为数值统计依据或产生另一权威事实源。

## 失败、中文反馈与回滚

缺少 Schema profile、字段候选、来源位置或证据引用，或字段类型、单位、日期、质量结果、事实
类型或数值无法确认时，未来流程必须停止并交由人工处理；当前没有实际失败记录。不能自动写入
业务事实、证据账本、数据库或生产状态。

中文反馈只说明静态合同已定义、未来事实必须可追溯以及待人工处理边界，不承诺自动抽取、统计
准确率、数据库可用、OVH 可用或生产可用。

回滚仅允许移除本步骤的范围说明、静态合同、聚焦用例、machine run、事件、机器事实投影和生成
中文视图，恢复到 `STAGE058_REVIEWED_LOCAL_TABLE_SCHEMA_INFERENCE_RUNTIME_DISABLED`。真实资料、
manifest、evidence ledger、audit log、已交付报告、数据库、运行状态、GitHub、OVH 与应用状态
不在回滚范围内。

一旦需要真实 XLSX/CSV、生产记录、质检表、fixture、文件检测、解析器、表格解析、实际字段识别、
实际事实抽取、typed value、RAG 摘要、数值统计、质量验证、来源位置或证据写入、持久化、数据库、
Agent、模型、OVH、生产、Phase2、整阶段复审、批次复审、上传或推送，立即停止本步骤。

## 后续门

本步骤通过后的唯一后续门为 `IDS-STAGE059-P2-GATE`，且必须由新的独立 run 进入。
