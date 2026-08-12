# STAGE-052 Phase 1：中英文 OCR 合同范围、输入输出与边界确认

## 当前结论

本步骤只定义 `IDS-V0_1-STAGE052-P1` 的中英文 OCR 静态工程合同。它以已完成的 Stage051 OCR 队列基线复审为前置边界，声明默认中文简体与英文、混合中英文页面的语言档案、按页输出引用、置信度隔离、缓存和后续复核路由；没有打开任何资料、没有创建队列、没有选择或调用 OCR 引擎。

唯一合同上下文是冻结的 Stage052 任务包与 Stage051 已复审合同/控制证据。它们只证明受控工程边界，不构成第二权威事实源，也不允许保留来源正文、路径、图像、页面或 OCR 文本。

## 职责交界

| 事项 | 唯一职责阶段 | 本步骤处置 |
| --- | --- | --- |
| OCR 队列基线 | Stage051 | 只引用已复审的 reference-only 输入和按页结构，不重建或运行队列 |
| 中英文 OCR 合同 | Stage052 | 定义默认语言、混合语言档案和语言边界 |
| 按页 OCR 输出细则 | Stage053 | 不创建、保存或解释实际按页 OCR 输出 |
| 低置信度复核路由 | Stage054 | 只声明后续受控复核路由，不创建实际复核任务 |
| OCR 引擎映射与调度 | Stage055 | 不选择、配置或调用 OCR 引擎 |
| OCR 缓存保留策略 | Stage056 | 只保留可重建缓存边界，不指定落盘位置或清理策略 |

未来候选输入继续固定为 Stage051 的七字段 reference-only 元数据：`source_identity_ref`、`input_kind_hint`、`parser_output_status`、`source_page_count_ref`、`language_profile`、`ocr_request_reason`、`cache_policy_ref`。`language_profile` 只能声明中文简体、英文或中英文混合；它不是文件内容、页面读取、语言检测或识别结果。

## 语言、按页输出与置信度合同

默认语言只声明为中文简体与英文。允许的未来语言档案是 `SIMPLIFIED_CHINESE`、`ENGLISH` 和 `SIMPLIFIED_CHINESE_AND_ENGLISH`；不选择 OCR 引擎、不写引擎映射、不运行混合语言处理，也不定义数值置信度阈值。

未来按页输出继续引用 Stage051 的八字段结构：`source_identity_ref`、`source_page_ref`、`ocr_text`、`language_profile`、`confidence_level`、`evidence_eligibility`、`cache_ref`、`review_route`。本步骤不创建、保存、解释或回显任何字段内容。中英文混合页和低置信页都不能直接进入高可信证据层，后续只能经 Stage054 的受控复核路由处理。

缓存只可在后续作为可重建的派生临时产物受控管理。本步骤不创建缓存、不指定落盘位置、不写缓存、不清理缓存；缓存保留与清理细则仍归 Stage056。

中文反馈只说明合同状态、默认语言、混合语言边界、低置信度隔离和缓存未创建；不承诺 OCR 自动化、人工复核已创建、生产可用或部署完成。

## 质量、回滚与停止条件

未来 OCR 页面初始事实等级保持 `CANDIDATE`，质量状态保持 `UNASSESSED`。本步骤不执行质量门、不提升证据、不写入 manifest、evidence ledger、audit、report、数据库或持久状态。

回滚只允许移除本步骤的范围说明、静态合同、聚焦用例、machine run、治理投影和生成的中文视图，并恢复到 `STAGE051_REVIEWED_LOCAL_OCR_QUEUE_RUNTIME_DISABLED`。真实资料、既有 evidence、运行状态、GitHub、OVH 与应用状态不在回滚范围内。

一旦需要真实资料访问、文件检测、页面渲染、图片处理、语言检测、OCR 引擎选择或调用、队列/缓存/复核记录创建、质量门、证据提升、持久写入、Agent、模型、OVH、生产服务、Phase2、整阶段复审、批次复审、上传或推送，立即停止本步骤。

## 后续门

本步骤通过后的唯一后续门为 `IDS-STAGE052-P2-GATE`，且必须由独立 run 进入。
