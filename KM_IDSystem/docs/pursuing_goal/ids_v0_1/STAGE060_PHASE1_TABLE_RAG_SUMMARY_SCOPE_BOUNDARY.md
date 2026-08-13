# STAGE-060 Phase 1：表格到 RAG 摘要范围、输入输出与边界确认

## 当前结论

本步骤只定义 `IDS-V0_1-STAGE060-P1` 的静态表格到 RAG 摘要合同。唯一合同上下文是冻结
Stage060 任务包与 Stage059 已完成整阶段复审工件；Stage057 的 XLSX/CSV 接入、Stage058 的
Schema 推断、Stage059 的事实抽取基线、Stage061 的结构化数据质量测试和 Stage062 的证据绑定
保持各自唯一职责。本步骤只登记未来表格摘要可引用的结构化事实、来源位置、摘要范围、中文输出
接口、数值边界、失败关闭和回滚边界；它没有读取、打开、解析、推断、写入、复制、移动或删除
任何真实表格、工作表、单元格、公式、事实、来源路径或业务资料。

字段名、枚举和计数仅描述未来受控实施的接口，不是工作表内容、列名、字段映射、typed value、
数值、日期、单位、设备、材料、质量结果、真实事实、摘要正文或统计结论。因此本步骤不建立第
二权威事实源。

## 职责交界

| 事项 | 唯一职责阶段 | 本步骤处置 |
| --- | --- | --- |
| XLSX/CSV 接入合同 | Stage057 | 仅引用已复审的接入边界，不读取或重写输入 |
| 表格 Schema 推断 | Stage058 | 仅引用已复审的 Schema profile 与字段候选边界，不重新推断 |
| 结构化事实抽取 | Stage059 | 仅引用已复审的 future typed fact 与来源定位合同，不创建或修改事实 |
| 表格到 RAG 摘要 | Stage060 | 只定义未来摘要输入、输出、非权威数值边界和失败关闭，不生成摘要 |
| 结构化数据质量测试 | Stage061 | 不验证真实空表、单位、日期、异常或重复行 |
| 表格证据绑定 | Stage062 | 只定义未来引用字段，不创建 evidence、document、sheet、row 或 column 绑定 |

## 输入、摘要输出与数值边界

未来摘要输入固定为十三个非内容引用字段：`summary_scope_ref`、`fact_set_ref`、`fact_id_ref`、
`fact_type`、`source_identity_ref`、`source_document_ref`、`workbook_ref`、`worksheet_ref`、
`row_range_ref`、`column_range_ref`、`schema_profile_ref`、`evidence_ref` 和
`rag_summary_eligibility`。仅允许 XLSX、CSV、生产记录和质检记录的 future reference；输入不
保存来源正文、物理路径、工作表、表头、单元格、公式或真实事实值。

未来摘要输出固定为十个引用或界面接口字段：`rag_summary_id`、`summary_scope_ref`、
`fact_set_ref`、`fact_reference_list`、`source_location_ref_list`、`summary_language`、
`summary_state`、`numeric_claim_state`、`human_review_state` 和 `evidence_ref`。`summary_language`
默认 `zh-CN`；摘要正文、事实值、数值、单位、日期、设备、材料和质量结果在本步骤均未生成。

结构化事实层仍是未来数值统计的唯一派生输入，且每条事实必须具备来源文档、工作表、表头行、
行列范围和证据引用。RAG 摘要只能提供未来的上下文导航，不能替代结构化事实、成为数值统计
依据、改变事实类型或将未验证数值、单位、日期、质量结果写成确定结论；模型不得直接根据文本
猜测这些内容。

## 失败、中文反馈与回滚

缺少事实引用、摘要范围、来源位置、证据引用，或事实类型、单位、日期、质量结果、摘要资格或
数值无法确认时，未来流程必须停止并交由人工处理；当前没有实际失败记录。不能自动写入摘要、
业务事实、证据账本、数据库或生产状态。

中文反馈只说明静态合同已定义、未来摘要必须引用结构化事实以及待人工处理边界，不承诺自动摘要、
检索质量、数值准确率、数据库可用、OVH 可用或生产可用。

回滚仅允许移除本步骤的范围说明、静态合同、聚焦用例、machine run、事件、机器事实投影和生成
中文视图，恢复到 `STAGE059_REVIEWED_LOCAL_FACT_EXTRACTION_RUNTIME_DISABLED`。真实资料、
manifest、evidence ledger、audit log、已交付报告、事实库、数据库、运行状态、GitHub、OVH 与
应用状态不在回滚范围内。

一旦需要真实 XLSX/CSV、生产记录、质检表、fixture、文件检测、解析器、表格解析、实际字段识别、
实际事实抽取、typed value、RAG 摘要正文、数值统计、质量验证、来源位置或证据写入、持久化、
数据库、Agent、模型、OVH、生产、Phase2、整阶段复审、批次复审、上传或推送，立即停止本步骤。

## 后续门

本步骤通过后的唯一后续门为 `IDS-STAGE060-P2-GATE`，且必须由新的独立 run 进入。
