# STAGE-055 Phase 3：OCR 回归语料专项场景

## 当前结论

本步骤完成 `IDS-V0_1-STAGE055-P3` 的受控专项场景验证。它只重放 P2 已冻结的五条
非业务 control 记录：扫描 PDF、模糊图片、表格图片、中英文混合和低质量。五个名称只是
任务包类别标签，不是文件、页面、图片、表格、样本或 OCR 结果；报告仅保留类别、来源页
引用、状态、语言档案、置信度等级与处置，不保留 OCR 文本、符号化输出、图片引用、失败
原因或任何业务内容。

当前冻结合同没有授权 fixture 或真实样本访问，因此本步骤证明的是 P2 控制切片的五类场景
覆盖、显式处置、来源页引用保留和零静默丢弃，**不证明真实 OCR、识别准确率、真实人工复核
或缓存容量**。

## 五类受控专项场景

| 控制类别 | P2 重放状态 | P3 处置 | 高可信证据 |
| --- | --- | --- | --- |
| 扫描 PDF | `OCR_SCANNED_DOCUMENT_CANDIDATE_RETAINED` | 候选保留，质量未评估 | 禁止直入 |
| 模糊图片 | `OCR_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED` | 降级证据，声明既有 Stage054 复核路由但未排队 | 禁止直入 |
| 表格图片 | `OCR_TABLE_DOCUMENT_CANDIDATE_UNASSESSED` | 候选保留，表格结构未提取 | 禁止直入 |
| 中英文混合 | `OCR_MIXED_ZH_EN_REVIEW_REQUIRED_NOT_QUEUED` | 降级证据，声明既有 Stage054 复核路由但未排队 | 禁止直入 |
| 低质量 | `OCR_PAGE_FAILED_EXPLICIT` | 显式失败，不提升证据 | 禁止直入 |

五类 control 全部有显式处置，静默丢弃为 `0`。低置信和混合中英文页均保持降级、未排队
的复核状态；低质量页保持显式失败。没有创建实际人工任务、复核队列或复核结果。

## 缓存与资源边界

缓存仍为 `IN_MEMORY_REBUILDABLE_NOT_PERSISTED`：本步骤没有创建缓存、缓存路径或临时产物，
因此临时产物数为 `0`，清理结论为 `NO_TEMPORARY_ARTIFACT_CREATED`。这只说明该 control
模块没有创建可归属的缓存路径或临时产物，不把它表述为本机内置盘用量的实测；它更不构成真实
OCR 缓存的容量证明。缓存保留、容量评估和任何清理执行仍由 Stage056 负责。

本步骤不读取 fixture、PDF、图片或页面，不执行文件检测、栅格化、图像处理、表格提取、
语言检测、置信度计算、OCR 引擎选择或调用、真实回归或准确率评估。它也不写入持久队列、
输出、缓存、审计、数据库、manifest、evidence ledger 或 report；没有 Agent、模型调用、
模型 Token、OVH、生产、上传或推送动作。

## 回滚与后续门

回滚只撤回本 P3 说明、专项场景合同、纯内存重放模块、聚焦用例、machine run、事件、事实
投影、治理状态和生成的中文视图，恢复到
`PHASE2_OCR_REGRESSION_CORPUS_CONTROL_SLICE_ENGINE_DISABLED`。真实资料、原始元数据、
既有 P1/P2 证据、运行状态、GitHub、OVH 与应用状态不在回滚范围内。

本步骤通过后的唯一后续门为 `IDS-STAGE055-P4-GATE`，且必须由独立 run 进入。
