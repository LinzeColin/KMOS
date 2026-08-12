# STAGE-051 Phase 2：OCR 队列最小可运行切片

## 当前结论

本步骤完成 IDS-V0_1-STAGE051-P2 的纯内存 OCR 队列控制切片。它只接收 P1 定义的七字段引用输入和四个固定、非业务的页面控制记录，创建一个进程内队列记录和逐页结构输出。它不读取 PDF、图片、页面、原始元数据或业务正文，不选择或调用 OCR 引擎。

执行模式为 ISOLATED_NON_PRODUCTION_IN_MEMORY_OCR_QUEUE_SLICE。该切片可以被直接调用和测试，但不代表真实 OCR、持久队列、缓存、人工复核、OVH 或生产服务已经启用。

## P2 最小实现

- OCR 输入继续固定为 P1 的七字段 reference-only 元数据，并只允许 control source identity。
- 四个控制页覆盖中文简体高置信、英文低置信、中英混合和显式失败页；它们不是业务资料或 OCR 引擎结果。
- 每页返回 P1 定义的八字段：source_identity_ref、source_page_ref、ocr_text、language_profile、confidence_level、evidence_eligibility、cache_ref、review_route。
- source_page_ref 由控制 source identity 与页号在内存中派生；不记录真实路径、页图像或来源正文。
- 低置信页、中英混合页和失败页各自进入可解释状态，均不允许直接进入高可信证据层，也不写入实际人工复核队列。后续实际复核仍归 Stage054。
- 缓存只记录 IN_MEMORY_REBUILDABLE_NOT_PERSISTED 策略；没有创建缓存文件、指定落盘位置或执行清理。

## 明确状态

| 页面类型 | 状态 | 中文反馈 | 高可信证据 |
| --- | --- | --- | --- |
| 中文简体或英文高置信控制页 | OCR_PAGE_CANDIDATE_RETAINED | 当前控制页已形成候选逐页输出，尚未进行质量评估。 | 不允许 |
| 低置信控制页 | OCR_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED | 低置信控制页需要后续复核，当前未创建复核任务。 | 不允许 |
| 中英混合控制页 | OCR_MIXED_ZH_EN_REVIEW_REQUIRED_NOT_QUEUED | 中英混合控制页已记录，当前未创建复核任务。 | 不允许 |
| 失败控制页 | OCR_PAGE_FAILED_EXPLICIT | 控制页识别失败已明确记录，未丢弃或创建高可信证据。 | 不允许 |

## 运行与数据边界

该切片只创建可调用函数返回值，不写数据库、manifest、evidence ledger、audit、index、report、job、state 或任何磁盘缓存。它不执行文件检测、真实路由、parser、fallback、OCR 引擎调用、图像处理、质量门、证据提升、智能体、模型调用、OVH 部署或生产激活。

固定控制文本只用于验证逐页输出结构和中文状态，不是业务样本、真实 OCR 输出或第二权威事实源。所有真实资料访问、实际 OCR 引擎配置、真实队列、真实图片处理、质量阈值、实际人工复核和缓存保留期仍分别由后续受控阶段处理。

## 回滚与后续门

回滚只撤回本 P2 说明、切片合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理状态和生成中文视图，恢复到 PHASE1_OCR_QUEUE_BOUNDARY_RUNTIME_DISABLED。不得改变真实资料、原始元数据、manifest、evidence ledger、audit、报告、GitHub、OVH 或应用状态。

本步骤通过后的唯一后续门为 IDS-STAGE051-P3-GATE，且必须由独立 run 进入。
