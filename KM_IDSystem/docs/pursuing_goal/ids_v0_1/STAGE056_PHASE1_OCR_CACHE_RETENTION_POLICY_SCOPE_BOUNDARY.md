# STAGE-056 Phase 1：OCR 缓存保留策略范围、输入输出与边界确认

## 当前结论

本步骤只定义 `IDS-V0_1-STAGE056-P1` 的静态缓存保留与清理工程合同。唯一合同上下文是冻结
Stage056 任务包和 Stage055 已完成整阶段复审工件。合同登记未来 OCR 临时图片、中间文本和失败
产物的引用字段、保留类别、清理资格、磁盘保护前置条件，以及与既有语言、置信度和复核路由的
交界；它没有创建、读取、保留、扫描、写入或清理任何物理缓存、文件、目录、样本、页面、图片、
文本或失败内容。

字段、类别和策略名仅描述未来受控实现的结构，不是缓存条目、真实路径、存储容量、保留时长、
清理记录、业务资料、OCR 文本、来源正文、失败详情或运行结果。因此本步骤不建立第二权威事实源。

## 职责交界

| 事项 | 唯一职责阶段 | 本步骤处置 |
| --- | --- | --- |
| OCR 队列基线 | Stage051 | 只继承 reference-only 队列边界，不创建或运行队列 |
| 中英文 OCR 合同 | Stage052 | 继承中文简体、英文和中英文混合档案，不检测语言 |
| 按页 OCR 输出与置信度字段 | Stage053 | 只继承字段形状，不创建按页输出、图片引用或 OCR 文本 |
| 低置信度复核路由 | Stage054 | 只继承既有受控复核状态，不创建复核任务、队列、意见或结果 |
| OCR 回归语料 | Stage055 | 只引用已复审的固定 control 合同和零运行时边界 |
| OCR 缓存保留与清理策略 | Stage056 | 定义未来缓存类别、保留/清理资格与保护边界，不执行物理操作 |

## 缓存、输入输出、语言与置信度合同

未来缓存输入固定为十一个非内容字段：`cache_entry_ref`、`source_identity_ref`、
`source_page_ref`、`artifact_class`、`language_profile`、`confidence_level`、`cache_state`、
`retention_class`、`cleanup_eligibility`、`evidence_eligibility`、`review_route`。未来缓存策略输出
固定为十个非内容字段：`cache_entry_ref`、`artifact_class`、`retention_class`、
`cleanup_eligibility`、`rebuildability`、`source_identity_ref`、`source_page_ref`、
`language_profile`、`confidence_level`、`review_route`。字段名不授权保存任何路径、图片、文本、失败内容或清理动作。

缓存类别仅登记三个不可打开、不可枚举的标量类别：`TEMPORARY_PAGE_IMAGE`、
`INTERMEDIATE_OCR_TEXT`、`FAILURE_ARTIFACT`。当前缓存条目数为零。

- 临时图片和中间文本仅定义为未来可重建临时类别；若未来实施，必须同时具备经批准的保留边界和容量限制。
- 失败产物仅定义为未来需要复核的类别，不允许自动清理。
- 未来可清理范围仅限已明确标识的临时图片和中间文本；原始资料、manifest、evidence ledger、audit log 和已交付报告绝不属于清理范围。
- 当前不指定物理路径、数值保留窗口、容量阈值或清理目标；不扫描磁盘、不评估容量、不创建缓存、不写入缓存且不执行清理。
- 默认语言仍为中文简体与英文，允许中英文混合；`LOW`、`UNKNOWN`、中英文混合或失败页不能因缓存策略直接进入高可信证据层，仍只引用 Stage054 的受控复核状态。

中文反馈只说明合同已定义、临时范围、未执行磁盘保护和低置信隔离；不承诺缓存可用、自动清理、
容量充足、OCR 自动化、识别准确率、质量门、生产可用或部署完成。

## 质量、回滚与停止条件

未来缓存策略条目的初始事实等级保持 `CANDIDATE`，质量状态保持 `UNASSESSED`。本步骤不执行
质量门、不提升证据、不运行 OCR 或回归，也不把策略字段表述为真实缓存容量、实际保留时长或已经完成的清理。

回滚只允许移除本步骤的范围说明、静态合同、聚焦用例、machine run、治理投影和生成中文视图，
恢复到 `STAGE055_REVIEWED_LOCAL_OCR_REGRESSION_CORPUS_RUNTIME_DISABLED`。真实资料、既有证据、
物理缓存、运行状态、GitHub、OVH 与应用状态不在回滚范围内。

一旦需要真实资料、授权 fixture、物理缓存路径、磁盘扫描、容量测量、缓存创建/写入/保留/清理、
删除/移动/覆盖文件、OCR 引擎、语言检测、队列、按页输出、复核记录、质量门、持久写入、Agent、模型、
OVH、生产服务、Phase2、整阶段复审、批次复审、上传或推送，立即停止本步骤。

## 后续门

本步骤通过后的唯一后续门为 `IDS-STAGE056-P2-GATE`，且必须由独立 run 进入。
