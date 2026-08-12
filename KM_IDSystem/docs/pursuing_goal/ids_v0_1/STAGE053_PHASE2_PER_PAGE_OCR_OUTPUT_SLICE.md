# STAGE-053 Phase 2：按页 OCR 输出受控切片

## 当前结论

本步骤完成 `IDS-V0_1-STAGE053-P2` 的纯内存按页 OCR 输出受控切片。它只接收 P1 已冻结的七字段 reference-only 输入和四个固定、非业务的控制页标记，在进程内派生 P1 约定的十一字段逐页结构、来源页引用、图片引用标记、置信度、失败原因与可解释状态。

该切片不读取 PDF、图片、页面、原始元数据或业务正文；不选择、配置或调用 OCR 引擎。输出中的 `ocr_text`、`page_image_ref` 和 `failure_reason` 仅可能是固定控制标记或受控分类，明确不是 OCR 识别文本、真实图片引用、来源正文、原始异常或第二权威事实源。

## P2 最小实现

- 输入保持 P1 的七字段 reference-only 合同，且只接受 Stage053 P2 的固定控制来源标识。
- 四个控制页覆盖中文简体候选、英文低置信、中英文混合和显式失败；它们不是文件、图像、页面或真实 OCR 结果。
- 每页返回 P1 声明的十一字段：`source_identity_ref`、`source_page_ref`、`page_image_ref`、`ocr_text`、`language_profile`、`confidence_level`、`failure_reason`、`output_status`、`evidence_eligibility`、`cache_ref`、`review_route`。
- `source_page_ref` 与 `page_image_ref` 只由控制来源标识、页号和固定控制标记在内存中派生；绝不记录真实路径、页图像、图片二进制或来源正文。
- 低置信页、中英文混合页和失败页均有独立、可解释的中文状态；均不能直接进入高可信证据层，且不创建实际人工复核任务。
- 缓存策略固定为 `IN_MEMORY_REBUILDABLE_NOT_PERSISTED`；不创建缓存文件、不分配落盘位置、不执行保留或清理。

## 明确状态

| 控制页类型 | 输出状态 | 中文反馈 | 高可信证据 |
| --- | --- | --- | --- |
| 中文简体控制页 | `OCR_PAGE_CANDIDATE_RETAINED` | 当前控制页已形成候选逐页结构，尚未进行质量评估。 | 不允许 |
| 英文低置信控制页 | `OCR_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED` | 英文低置信控制页需要后续复核，当前未创建复核任务。 | 不允许 |
| 中英文混合控制页 | `OCR_MIXED_ZH_EN_REVIEW_REQUIRED_NOT_QUEUED` | 中英文混合控制页已记录，当前未创建复核任务。 | 不允许 |
| 显式失败控制页 | `OCR_PAGE_FAILED_EXPLICIT` | 控制页失败状态已明确记录，未丢弃或创建高可信证据。 | 不允许 |

失败控制页只使用 P1 允许的 `OCR_EXECUTION_NOT_STARTED` 受控分类，表示控制切片没有执行 OCR 引擎；它不是实际执行失败、原始异常或实际失败记录。

## 运行与数据边界

此切片只返回函数内存值，不写数据库、manifest、evidence ledger、audit、index、report、job、state 或缓存。它不执行文件检测、真实路由、parser、PDF 栅格化、图片处理、语言检测、OCR 引擎调用、质量门、证据提升、智能体、模型调用、OVH 部署或生产激活。

固定控制标记只用于验证按页结构、来源页/图片引用形状与中文状态，不是业务样本、真实 OCR 输出、真实图片引用、来源内容或人工复核记录。实际低置信复核继续归 `STAGE-054`，OCR 引擎映射归 `STAGE-055`，缓存保留与清理归 `STAGE-056`。

## 回滚与后续门

回滚只撤回本 P2 说明、合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理状态和生成中文视图，恢复到 `PHASE1_PER_PAGE_OCR_OUTPUT_BOUNDARY_RUNTIME_DISABLED`。不得改变真实资料、原始元数据、manifest、evidence ledger、audit、报告、GitHub、OVH 或应用状态。

本步骤通过后的唯一后续门为 `IDS-STAGE053-P3-GATE`，且必须由独立 run 进入。
