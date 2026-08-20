# STAGE-072 · Embedding 模型版本整阶段机械复审

## 本次边界

- 任务：`IDS-V0_1-STAGE072-REVIEW`
- 验收：`ACC-STAGE-072`
- 当前门：`IDS-STAGE072-REVIEW-GATE`
- 通过后下一门：`IDS-STAGE073-P1-GATE`
- 唯一合同上下文：冻结 `STAGE-072_Embedding模型版本.md`、Stage072 P1--P4 合同及 P2/P3/P4 纯内存控制报告。

本复审只读重放既有合同和固定控制引用，不读取、打开、保留、复制或写入任何真实资料、原始元数据、来源正文、摘要正文、文本块、物理路径、真实 URI、provider、模型、维度、时间、金额、Token、预算、队列、缓存、重试、审计或业务结论。来源文档及业务线白箱人工复核继续是唯一权威；本复审不建立第二权威事实源。

## 机械复审对象

| 阶段 | 复审的固定形状 |
| --- | --- |
| P1 | 6 字段模型版本、2 跳策略继承、12/10/7 队列/缓存/重试、8 字段成本、18 字段审计、9 类失败关闭。 |
| P2 | 5 条固定非业务控制请求；5 条 10 字段策略、14 字段队列、10 字段缓存、7 字段重试、6 字段模型版本、8 字段成本和 18 字段审计投影。 |
| P3 | 5 条 35 字段显式处置，0 条静默丢弃，4 条业务线白箱人工处理，90 次审计字段检查，3 个未来调用候选。 |
| P4 | 5 条策略、5 条审计样例、5 条零值成本、5 条失败、5 条未外发控制引用、7 键查询、4 条中文反馈和回到 P3 的控制回退。 |

## 必须保持的结论

1. 默认 `denied` 阻断未授权外发；data source/document 到 chunk 的策略只能自动继承，document 只能收紧。
2. `summary_only` 不得升级为文本块引用；`full_text_allowed` 仍只保留未来授权前的控制引用；预算不足必须暂停外部 API 候选。
3. 3 个未来调用候选仍需完整 18 字段审计投影和业务线白箱人工处理；控制投影、零值成本和中文反馈不能成为真实模型、审计、成本、Token 或业务事实。
4. P4 只能以纯内存控制方式回到 `PASS_PHASE3_EMBEDDING_MODEL_VERSION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED`；不能触及真实资料、持久状态、GitHub、OVH 或生产。

## 本地运行时边界

复审模块没有启动真实资料访问、解析、切块、摘要、模型版本记录、成本估算、预算查询、队列、缓存、失败重试、provider 或模型选择、外部 API、模型 Token、审计写入或查询、数据库、Agent、OVH、生产、批次复审、上传或推送。它只在内存中调用 P2/P3/P4 既有控制构建函数，并以失败关闭方式输出 Review 结论。

## 回滚

只撤回本 Review 说明、机械复审模块、聚焦用例、machine run、事件、机器事实、治理路线和机器生成中文视图，恢复到 `PHASE4_EMBEDDING_MODEL_VERSION_METADATA_ONLY_DELIVERY_RUNTIME_DISABLED`。保留 Stage072 P1--P4、Stage071 Review 及更早证据、冻结任务包、真实资料、manifest、evidence ledger、audit log、事实库、数据库、索引、GitHub、OVH 和应用状态。

## 验收证据

执行结果写入 `KM_IDSystem/machine/runs/2026-08-20-stage072-review-local.json`。本地聚焦用例 `10/10`、Stage072 P1--Review `49/49`、Stage060--069 `473/473`、Stage070 `47/47` 与 Stage071 `53/53` 均通过；覆盖固定形状、单一权威/策略审计/回退边界、零运行时/Stage073 关闭，以及 P1/P2/P3/P4 任一输入异常时停留在 `IDS-STAGE072-REVIEW-GATE`。
