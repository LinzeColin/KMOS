# STAGE-061 Phase 1：结构化数据质量测试范围、输入输出与边界确认

## 当前结论

本步骤只定义 IDS-V0_1-STAGE061-P1 的静态结构化数据质量测试合同。唯一合同上下文是冻结
Stage061 任务包与 Batch051-060 已完成本地复审工件；Stage057 的 XLSX/CSV 接入、Stage058 的
Schema 推断、Stage059 的事实抽取、Stage060 的 RAG 摘要与 Stage062 的证据绑定继续保持各自
唯一职责。本步骤只登记未来质量检查可引用的输入、结果字段、质量维度、数值边界、人工处理、
失败关闭和回滚边界；没有读取、打开、解析、推断、验证、写入、复制、移动或删除任何真实表格、
工作表、表头、单元格、公式、事实、来源路径或业务资料。

字段名、枚举和计数仅描述未来受控实施的接口，不是工作表内容、列名、字段映射、主键、typed
value、数值、日期、单位、设备、材料、质量结果、真实事实、统计结论或数据质量结果。因此本
步骤不建立第二权威事实源。

## 职责交界

| 事项 | 唯一职责阶段 | 本步骤处置 |
| --- | --- | --- |
| XLSX/CSV 接入合同 | Stage057 | 只引用已复审的输入边界，不读取或重写输入 |
| 表格 Schema 推断 | Stage058 | 只引用已复审的 Schema profile 与字段候选边界，不重新推断 |
| 结构化事实抽取 | Stage059 | 只引用 future typed fact 与来源定位合同，不创建或修改事实 |
| 表格到 RAG 摘要 | Stage060 | 只保留摘要非数值权威边界，不生成摘要 |
| 结构化数据质量测试 | Stage061 | 只定义未来字段完整性、单位一致性、日期合法性、主键重复和异常值复核合同，不验证真实数据 |
| 表格证据绑定 | Stage062 | 只定义未来引用字段，不创建 evidence、document、sheet、row 或 column 绑定 |

## 输入、结果输出与数值边界

未来质量检查输入固定为十六个非内容引用字段：quality_request_ref、source_identity_ref、
source_document_ref、file_format、workbook_ref、worksheet_ref、header_row_ref、row_range_ref、
column_range_ref、schema_profile_ref、fact_set_ref、field_candidate_ref、primary_key_ref、
record_type、evidence_ref 与 quality_profile_ref。仅允许 XLSX、CSV、生产记录和质检记录的
future reference；输入不保存来源正文、物理路径、工作表、表头、单元格、公式或真实事实值。

未来质量结果固定为十八个引用或界面接口字段，覆盖五类质量维度：FIELD_COMPLETENESS、
UNIT_CONSISTENCY、DATE_VALIDITY、PRIMARY_KEY_DUPLICATION 与 OUTLIER_REVIEW。质量状态只可
表达 future candidate、未评估、拒绝或人工处理需要；本步骤没有创建质量结果、质量配置、主键、
事实、异常值或统计。

数值统计未来只能基于带来源文档、工作表、表头行、行列范围与证据引用的结构化事实。模型不得
根据文本猜测数值、单位、日期、质量结果、主键、异常值或统计结论；RAG 摘要不得替代结构化
事实、成为数值统计依据或产生另一权威事实源。

## 失败、中文反馈与回滚

缺少质量配置、Schema profile、字段候选、主键、来源位置或证据引用，或字段完整性、单位、
日期、重复状态、异常基线或数值无法确认时，未来流程必须停止并交由人工处理；当前没有实际
失败或质量结果。不能自动写入业务事实、质量结果、证据账本、数据库或生产状态。

中文反馈只说明静态合同已定义、未来质量结果必须可追溯以及待人工处理边界，不承诺自动质量
验证、统计准确率、数据库可用、OVH 可用或生产可用。

回滚仅允许移除本步骤的范围说明、静态合同、聚焦用例、machine run、事件、机器事实投影和
生成中文视图，恢复到 Batch051-060 本地复审完成状态。真实资料、manifest、evidence ledger、
audit log、已交付报告、事实库、数据库、运行状态、GitHub、OVH 与应用状态不在回滚范围内。

一旦需要真实 XLSX/CSV、生产记录、质检表、fixture、文件检测、解析器、表格解析、实际字段
识别、实际事实抽取、typed value、质量验证、异常检测、数值统计、来源位置或证据写入、持久化、
数据库、Agent、模型、OVH、生产、Phase2、整阶段复审、批次复审、上传或推送，立即停止本步骤。

## 后续门

本步骤通过后的唯一后续门为 IDS-STAGE061-P2-GATE，且必须由新的独立 run 进入。
