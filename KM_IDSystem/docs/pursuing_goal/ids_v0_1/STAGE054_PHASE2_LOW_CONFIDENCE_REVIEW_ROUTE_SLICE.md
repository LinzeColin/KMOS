# STAGE-054 Phase 2：低置信度复核路由受控切片

## 当前结论

本步骤完成 `IDS-V0_1-STAGE054-P2` 的纯内存低置信度复核路由切片。它只接收 P1 固定的
九字段 reference-only 控制记录，在进程内形成十字段候选复核请求、三种受控路由状态和中文反馈。
控制记录只包含固定来源与页引用、语言、置信度、状态、失败分类、证据资格、路由与缓存策略标记；
不含 OCR 文本、图片、页面内容、真实路径、业务正文、人工意见或原始异常。

该切片不创建持久队列、实际人工任务或复核结果。候选复核请求仅是函数返回的固定非业务控制结构，
明确不是实际请求、人工分派、人工意见、审计记录或第二权威事实源。

## P2 最小实现

- 输入固定为 P1 的九字段：`source_identity_ref`、`source_page_ref`、`language_profile`、
  `confidence_level`、`output_status`、`failure_reason`、`evidence_eligibility`、
  `review_route`、`cache_policy_ref`。
- 只接受四条固定非业务控制记录：英文低置信、中英文混合、显式失败和中文简体高置信候选。
  它们不是文件、图片、页面、真实 OCR 输出、真实失败记录或业务样本。
- 低置信、中英文混合和失败控制记录在内存中分别形成十字段候选复核请求，并保留原有
  `source_page_ref`；不重写 Stage053 的按页输出或来源页引用所有权。
- 十字段候选请求为 P1 已声明的九字段加 `feedback_code`；候选事实等级固定为 `CANDIDATE`，
  质量状态固定为 `UNASSESSED`。
- 中文简体高置信候选不形成复核请求，也不因此进入高可信证据层；P2 不执行质量门或证据提升。
- 缓存策略固定为 `IN_MEMORY_REBUILDABLE_NOT_PERSISTED`，不创建缓存、路径、保留策略或清理动作；
  Stage056 仍拥有缓存保留与清理。

## 可解释状态

| 控制记录 | P2 路由状态 | 候选复核请求 | 中文反馈 |
| --- | --- | --- | --- |
| 英文 `LOW` | `LOW_CONFIDENCE_REVIEW_REQUIRED` | 仅内存候选 | 英文低置信控制页已形成候选复核请求，未创建人工任务。 |
| 中英文混合 | `MIXED_LANGUAGE_REVIEW_REQUIRED` | 仅内存候选 | 中英文混合控制页已形成候选复核请求，未创建人工任务。 |
| 显式失败页 | `FAILED_PAGE_REVIEW_REQUIRED` | 仅内存候选 | 失败控制页已形成候选复核请求，未创建人工任务。 |
| 中文简体 `HIGH` | 无 | 不创建 | 当前控制页无需复核路由，仍未进行质量评估或高可信证据提升。 |

所有四种控制结果的 `high_trust_direct_entry_allowed` 都是 `false`。P2 只验证复核路由形状和
状态隔离，不代表实际 OCR、识别准确率、人工复核、业务结论或生产能力。

## 运行与数据边界

此切片只返回函数内存值，不写入队列、缓存、数据库、manifest、evidence ledger、audit、report、
job 或状态。它不执行文件检测、真实路由、PDF 栅格化、图片处理、语言检测、OCR 引擎选择或调用、
质量门、证据提升、Agent、模型调用、OVH 部署或生产激活。

Stage051 继续拥有 OCR 队列基线，Stage052 继续拥有语言边界，Stage053 继续拥有按页 OCR 输出与
来源页引用，Stage055 继续拥有 OCR 引擎映射与调度，Stage056 继续拥有缓存保留与清理。P2 只拥有
低置信度复核路由的控制适配器，不改写这些阶段的合同或结果。

## 回滚与后续门

回滚只撤回本 P2 说明、切片合同、纯内存适配器、聚焦用例、machine run、事件、事实投影、治理状态
和生成的中文视图，恢复到 `PHASE1_LOW_CONFIDENCE_REVIEW_ROUTE_BOUNDARY_RUNTIME_DISABLED`。不得改变
真实资料、原始元数据、manifest、evidence ledger、audit、报告、GitHub、OVH 或应用状态。

本步骤通过后的唯一后续门为 `IDS-STAGE054-P3-GATE`，且必须由独立 run 进入。
