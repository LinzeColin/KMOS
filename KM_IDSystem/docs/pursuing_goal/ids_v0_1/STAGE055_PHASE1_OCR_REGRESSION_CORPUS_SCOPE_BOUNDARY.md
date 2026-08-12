# STAGE-055 Phase 1：OCR 回归语料范围、输入输出与边界确认

## 当前结论

本步骤只定义 `IDS-V0_1-STAGE055-P1` 的 OCR 回归语料静态工程合同。它以冻结的
Stage055 任务包和 Stage054 已完成整阶段复审工件为唯一合同上下文，定义未来回归语料的
引用输入、预期按页输出字段、中文简体与英文语言档案、置信度隔离、缓存和复核路由边界。
本步骤没有读取、创建、保存、复制或评估任何资料、样本、页面、图片、表格、OCR 文本或
回归结果。

合同中的类别和字段名只描述未来受控回归语料的结构；它们不是语料样本、业务资料、来源正文、
真实路径、页面、图片、OCR 文本、引擎配置、失败详情或运行结果。因此本步骤不建立第二权威
事实源。

## 职责交界

| 事项 | 唯一职责阶段 | 本步骤处置 |
| --- | --- | --- |
| OCR 队列基线 | Stage051 | 只引用已复审的 reference-only 结构，不创建或运行队列 |
| 中英文 OCR 语言边界 | Stage052 | 继承中文简体、英文和中英文混合档案，不检测语言 |
| 按页 OCR 输出与置信度字段 | Stage053 | 只复用字段形状，不创建按页输出、图片引用或 OCR 文本 |
| 低置信度复核路由 | Stage054 | 只引用既有受控复核状态，不创建复核任务、队列、意见或结果 |
| OCR 回归语料与引擎映射合同 | Stage055 | 定义五类语料登记、未来引擎映射字段和质量隔离，不选择、配置或调用引擎 |
| OCR 缓存保留与清理 | Stage056 | 只声明可重建缓存引用边界，不写入、保留或清理缓存 |

## 回归语料、输入输出、语言与置信度合同

冻结任务包要求未来覆盖扫描件、模糊件、表格件、混合中英文文件和低质量件。本步骤只登记
五个不含内容的类别：`SCANNED_DOCUMENT_CONTROL`、`BLURRED_DOCUMENT_CONTROL`、
`TABLE_DOCUMENT_CONTROL`、`MIXED_ZH_EN_DOCUMENT_CONTROL`、
`LOW_QUALITY_DOCUMENT_CONTROL`。类别不是文件、样本、页面、图片、表格单元、OCR 输出或
识别准确率结论；当前样本数为零，所有类别均为待授权的 reference-only 候选。

未来语料输入固定为十个非内容字段：`source_identity_ref`、`source_page_ref`、
`input_class`、`language_profile`、`confidence_level`、`output_status`、
`failure_reason`、`evidence_eligibility`、`review_route`、`cache_policy_ref`。未来按页
输出继承 Stage053 的十一字段形状：`source_identity_ref`、`source_page_ref`、
`page_image_ref`、`ocr_text`、`language_profile`、`confidence_level`、
`failure_reason`、`output_status`、`evidence_eligibility`、`cache_ref`、`review_route`。
字段名不授权保存其中任何内容。

- 默认语言为中文简体与英文，允许中文简体、英文和中英文混合三个语言档案；不运行语言检测。
- 置信度只声明 `HIGH`、`MEDIUM`、`LOW`、`UNKNOWN` 四个已有状态；不设置数值阈值、不评估准确率。
- `LOW`、`UNKNOWN`、中英文混合或失败页不能直接进入高可信证据层，只能保留在 Stage054 已定义的未来受控复核状态。
- Stage055 只定义未来引擎映射字段（语言档案、输入类别、能力引用、选择理由和回退引用）；不选择、配置、调用或比较任何 OCR 引擎。

缓存仅保留为可重建派生产物的引用边界。本步骤不指定存储位置、不创建或写入缓存、不评估容量、
不保留或清理临时产物；缓存保留和清理细则仍归 Stage056。审计、manifest、evidence ledger、
report、数据库和持久状态均不写入。

中文反馈只说明语料合同、默认语言、低置信隔离、引擎尚未选择和缓存尚未创建；不承诺样本可用、
OCR 自动化、识别准确率、质量门、生产可用或部署完成。

## 质量、回滚与停止条件

未来回归条目初始事实等级保持 `CANDIDATE`，质量状态保持 `UNASSESSED`。本步骤不执行质量门、
不提升证据、不比较引擎，也不把任何类别视为已经建立、已经运行或可以作为业务证据。

回滚只允许移除本步骤的范围说明、静态合同、聚焦用例、machine run、治理投影和生成的中文视图，
并恢复到 `STAGE054_REVIEWED_LOCAL_LOW_CONFIDENCE_REVIEW_ROUTE_RUNTIME_DISABLED`。真实资料、
既有证据、运行状态、GitHub、OVH 与应用状态不在回滚范围内。

一旦需要真实资料、授权 fixture、样本文件、页面、图片、表格、OCR 文本、语言检测、OCR 引擎
选择或调用、引擎比较、队列、按页输出、缓存、复核记录、质量门、证据提升、持久写入、Agent、
模型、OVH、生产服务、Phase2、整阶段复审、批次复审、上传或推送，立即停止本步骤。

## 后续门

本步骤通过后的唯一后续门为 `IDS-STAGE055-P2-GATE`，且必须由独立 run 进入。
