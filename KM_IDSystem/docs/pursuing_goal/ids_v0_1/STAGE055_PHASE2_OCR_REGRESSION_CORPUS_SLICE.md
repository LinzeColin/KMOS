# STAGE-055 Phase 2：OCR 回归语料受控切片

## 当前结论

本步骤完成 `IDS-V0_1-STAGE055-P2` 的纯内存 OCR 回归语料受控切片。它只接收 P1
定义的十字段 reference-only 控制记录，为五个冻结类别形成内存队列状态、十一字段逐页
结构、置信度记录、来源页引用和中文可解释状态。五条记录均为固定的非业务标记，不含样本、
业务资料、来源正文、真实路径、页面、图片、表格单元或 OCR 文本。

切片返回的 `ocr_text` 与 `page_image_ref` 均为符号标记，失败原因也是控制分类；它们不是
真实 OCR 输出、真实图片引用或实际失败记录。函数返回的内存队列记录、逐页结构与置信度
记录不持久化，因此不建立第二权威事实源。

## P2 最小实现

- 只接受扫描件、模糊件、表格件、混合中英文和低质量件五条固定 control 记录。输入完整
  保持 P1 的十字段：`source_identity_ref`、`source_page_ref`、`input_class`、
  `language_profile`、`confidence_level`、`output_status`、`failure_reason`、
  `evidence_eligibility`、`review_route`、`cache_policy_ref`。
- 在进程内建立 `QUEUED → PROCESSING → COMPLETED` 的控制队列状态，并为每条记录返回
  Stage053 已定义的十一字段按页结构。`source_page_ref` 原样保留，符号化图片引用只由该
  来源页标记派生。
- 扫描件和表格件保持 `CANDIDATE` / `UNASSESSED`；表格件不执行表格结构提取。
- 模糊控制页以 `LOW` 置信度记录为未排队的 Stage054 受控复核状态；混合中英文控制页也
  明确记录为未排队复核状态；低质量控制页保持显式失败。三者均不能直接进入高可信证据层。
- 缓存固定为 `IN_MEMORY_REBUILDABLE_NOT_PERSISTED`，不创建缓存、路径、保留策略或清理
  动作；缓存保留与清理仍归 Stage056。

## 可解释状态

| 控制类别 | P2 状态 | 来源页引用 | 中文反馈 |
| --- | --- | --- | --- |
| 扫描件 | `OCR_SCANNED_DOCUMENT_CANDIDATE_RETAINED` | 原样保留 | 已形成候选逐页结构，未执行 OCR 或质量评估。 |
| 模糊件 | `OCR_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED` | 原样保留 | 以低置信状态保留，未创建复核任务。 |
| 表格件 | `OCR_TABLE_DOCUMENT_CANDIDATE_UNASSESSED` | 原样保留 | 未执行表格结构提取或质量评估。 |
| 中英文混合 | `OCR_MIXED_ZH_EN_REVIEW_REQUIRED_NOT_QUEUED` | 原样保留 | 已记录为受控复核状态，未创建复核任务。 |
| 低质量件 | `OCR_PAGE_FAILED_EXPLICIT` | 原样保留 | 已记录为显式失败，未创建真实失败记录或复核任务。 |

所有控制结果的 `high_trust_direct_entry_allowed` 都是 `false`。默认语言合同仍为中文简体
与英文；本步骤不检测语言、不设数值阈值、不评估置信度或识别准确率。

## 运行与职责边界

Stage051 继续拥有 OCR 队列基线，Stage052 继续拥有语言边界，Stage053 继续拥有按页输出
字段，Stage054 继续拥有低置信复核路由，Stage055 只拥有回归语料 control 适配器与未来
引擎映射合同，Stage056 继续拥有缓存保留和清理。P2 不改写前序阶段的合同或结果。

本步骤只返回函数内存值，不写入队列、缓存、数据库、manifest、evidence ledger、audit、
report、job 或状态。它不读取文件、页面或图片，不执行文件检测、真实路由、parser、PDF
栅格化、图像处理、表格提取、语言检测、OCR 引擎选择或调用、回归、质量门、证据提升、
Agent、模型调用、OVH 部署或生产激活。

## 回滚与后续门

回滚只撤回本 P2 说明、切片合同、纯内存适配器、聚焦用例、machine run、事件、事实投影、
治理状态和生成的中文视图，恢复到 `PHASE1_OCR_REGRESSION_CORPUS_BOUNDARY_RUNTIME_DISABLED`。
不得改变真实资料、原始元数据、manifest、evidence ledger、audit、报告、GitHub、OVH 或应用
状态。

本步骤通过后的唯一后续门为 `IDS-STAGE055-P3-GATE`，且必须由独立 run 进入。
