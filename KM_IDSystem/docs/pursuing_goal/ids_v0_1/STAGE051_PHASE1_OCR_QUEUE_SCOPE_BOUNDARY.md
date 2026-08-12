# STAGE-051 Phase 1：OCR 队列范围、输入输出与边界确认

## 当前结论

本步骤只定义 IDS-V0_1-STAGE051-P1 的静态 OCR 队列合同。它为未来扫描 PDF、图片与低文本覆盖 PDF 固定引用输入、按页输出、默认语言、置信度、缓存和复核路由边界；没有打开任何资料、没有创建队列、没有选择或调用 OCR 引擎。

唯一合同上下文是冻结 Stage051 任务包与已完成的 Stage041--050 批次复审工件。它们只证明既有控制边界，不构成第二权威事实源，也不允许保留来源正文、路径、图像、页面或 OCR 文本。

## 职责交界

| 事项 | 唯一职责阶段 | 本步骤处置 |
| --- | --- | --- |
| 文件类型检测 | Stage045 | 仅使用未来 reference-only 输入，不重新检测 |
| 解析器路由 | Stage046 | 不评估或改写真实路由 |
| 解析产物封套 | Stage047 | 仅引用既有封套，不创建解析产物 |
| 解析失败降级 | Stage048 | 不触发 fallback |
| 差异化解析器评估 | Stage049 | 不比较候选或正文 |
| 提示注入标记 | Stage050 | 不应用运行时标记 |
| OCR 队列基线 | Stage051 | 定义本静态队列、逐页输出与隔离合同 |
| 中英文 OCR 细则 | Stage052 | 保留后续语言细则与引擎映射职责 |
| 按页 OCR 输出细则 | Stage053 | 保留后续实际输出细则职责 |
| 低置信度复核路由 | Stage054 | 保留后续实际复核路由职责 |
| OCR 缓存保留策略 | Stage056 | 保留后续缓存期限与清理细则职责 |

未来候选输入固定为七字段 reference-only 元数据：source_identity_ref、input_kind_hint、parser_output_status、source_page_count_ref、language_profile、ocr_request_reason、cache_policy_ref。其中 input_kind_hint 只能声明 SCANNED_PDF、IMAGE 或 LOW_TEXT_COVERAGE_PDF；它不是文件检测、页面读取或真实路由结果。

## 按页输出、语言与置信度合同

未来每页 OCR 输出固定为八字段结构：source_identity_ref、source_page_ref、ocr_text、language_profile、confidence_level、evidence_eligibility、cache_ref、review_route。本步骤不创建、保存、解释或回显其中任何字段内容。

默认语言只声明为中文简体与英文；不选择 OCR 引擎、不写引擎配置、不定义数值置信度阈值。低置信度页面固定为 NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY，不能直接进入高可信证据层；后续只能经 Stage054 的受控复核路由处理。

缓存只可在后续作为可重建的派生临时产物受控管理。本步骤不创建缓存、不指定落盘位置、不写缓存、不清理缓存；缓存保留与清理细则仍归 Stage056。

中文反馈只说明合同状态、默认语言、低置信度隔离和缓存未创建；不承诺 OCR 自动化、人工复核已创建、生产可用或部署完成。

## 质量、回滚与停止条件

未来 OCR 页面初始事实等级固定为 CANDIDATE，质量状态固定为 UNASSESSED。本步骤不执行质量门、不提升证据、不写入 manifest、evidence ledger、audit、report、数据库或持久状态。

回滚只允许移除本步骤的范围说明、静态合同、聚焦用例、machine run、治理投影和生成的中文视图，并恢复到 BATCH041_050_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED。真实资料、既有 evidence、运行状态、GitHub、OVH 与应用状态不在回滚范围内。

一旦需要真实资料访问、文件检测、页面渲染、图片处理、OCR 引擎选择或调用、队列/缓存/复核记录创建、质量门、证据提升、持久写入、Agent、模型、OVH、生产服务、Phase2、整阶段复审、批次复审、上传或推送，立即停止本步骤。

## 后续门

本步骤通过后的唯一后续门为 IDS-STAGE051-P2-GATE，且必须由独立 run 进入。
