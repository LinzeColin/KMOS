# STAGE-054 Phase 1：低置信度复核路由范围、输入输出与边界确认

## 当前结论

本步骤只定义 `IDS-V0_1-STAGE054-P1` 的低置信度复核路由静态工程合同。它以冻结的
Stage054 任务包和 Stage053 已完成整阶段复审工件为唯一合同上下文，定义未来复核输入、
未来复核请求字段、默认中文简体与英文、低置信/中英文混合/失败页的隔离状态、缓存边界和
中文反馈；没有读取资料、创建人工复核任务、写入队列、保存 OCR 文本或选择/调用 OCR 引擎。

合同中的字段名只描述未来受控复核路由的结构，不是业务资料、来源正文、真实路径、页面、
图片、OCR 文本、失败详情、人工意见或运行结果。它不建立第二权威事实源。

## 职责交界

| 事项 | 唯一职责阶段 | 本步骤处置 |
| --- | --- | --- |
| OCR 队列基线 | Stage051 | 只引用已复审的 reference-only 输入与按页结构，不重建或运行队列 |
| 中英文 OCR 语言边界 | Stage052 | 只继承中文简体、英文和中英文混合档案，不执行语言检测 |
| 按页 OCR 输出与置信度记录 | Stage053 | 只引用已复审的字段与 metadata-only 状态，不重新运行 OCR 或写输出 |
| 低置信度复核路由 | Stage054 | 定义未来人工复核路由合同，不创建任务、队列、意见或结果 |
| OCR 引擎映射与调度 | Stage055 | 不选择、配置或调用 OCR 引擎 |
| OCR 缓存保留与清理 | Stage056 | 只声明可重建缓存边界，不写入、保留或清理缓存 |

## 输入、路由输出、语言与置信度合同

未来路由输入只引用 Stage053 已定义的非内容字段：`source_identity_ref`、`source_page_ref`、
`language_profile`、`confidence_level`、`output_status`、`failure_reason`、
`evidence_eligibility`、`review_route`、`cache_policy_ref`。这些字段不得携带来源正文、
真实路径、页面内容、图片二进制、OCR 文本、人工意见或原始异常。

未来复核请求固定为十个引用字段：`source_identity_ref`、`source_page_ref`、
`language_profile`、`confidence_level`、`output_status`、`failure_reason`、
`evidence_eligibility`、`review_route`、`cache_policy_ref`、`feedback_code`。本步骤不创建、
保存、返回或持久化任何请求实例。

- 默认语言为中文简体与英文，允许的语言档案仍只有中文简体、英文和中英文混合；不运行语言检测。
- 置信度只引用 `HIGH`、`MEDIUM`、`LOW`、`UNKNOWN` 四个已有状态，不设数值阈值、不评估准确率。
- `LOW`、`UNKNOWN`、中英文混合或失败页只能进入未来受控复核路由，不能直接进入高可信证据层。
- 未来路由状态只有 `LOW_CONFIDENCE_REVIEW_REQUIRED`、`MIXED_LANGUAGE_REVIEW_REQUIRED`、
  `FAILED_PAGE_REVIEW_REQUIRED`；它们只是静态枚举，不代表任务已创建、已分派或已完成。

缓存仅保留为可重建派生产物的引用边界。本步骤不指定存储位置、不创建或写入缓存、不做缓存
清理；缓存保留与清理细则仍归 Stage056。审计、manifest、evidence ledger、report、数据库和
持久状态均不写入。

中文反馈只说明复核合同状态、默认语言、低置信隔离、人工复核任务未创建和缓存未创建；不承诺
OCR 自动化、人工复核已完成、生产可用或部署完成。

## 质量、回滚与停止条件

未来复核请求初始事实等级保持 `CANDIDATE`，质量状态保持 `UNASSESSED`。本步骤不执行质量门、
不提升证据，也不把任何未来路由视为人工复核完成或可用业务证据。

回滚只允许移除本步骤的范围说明、静态合同、聚焦用例、machine run、治理投影和生成的中文视图，
并恢复到 `STAGE053_REVIEWED_LOCAL_PER_PAGE_OCR_OUTPUT_RUNTIME_DISABLED`。真实资料、既有证据、
运行状态、GitHub、OVH 与应用状态不在回滚范围内。

一旦需要真实资料访问、文件检测、页面渲染、图片处理、语言检测、OCR 引擎选择或调用、实际按页
输出/图片引用/失败记录、人工复核任务或结果、队列/缓存/审计写入、质量门、证据提升、持久写入、
Agent、模型、OVH、生产服务、Phase2、整阶段复审、批次复审、上传或推送，立即停止本步骤。

## 后续门

本步骤通过后的唯一后续门为 `IDS-STAGE054-P2-GATE`，且必须由独立 run 进入。
