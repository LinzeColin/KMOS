# Stage113 · 复核队列 Schema Phase 2 受控最小切片

## 本轮目标

Stage113 P2 以 P1 静态复核队列 Schema 合同与 Stage112 Review 控制工件为前序，形成可机械执行、可测试、可回滚的纯内存控制切片。切片投影复核 Schema、入队工作流、固定状态、复核审计、证据风险与报告状态未来写回，以及可理解的中文复核原因。

## 固定控制输入

- 固定五条非业务、`reference-only` 控制请求：低 OCR、资料冲突、解析失败、证据风险与外部增强白箱边界。
- 每条请求固定 32 个输入字段：`control_scenario`、`binding_mode`、固定状态控制值与 P1 的 29 个未来控制引用。
- 五条请求机械覆盖 `pending_review`、`confirmed`、`rejected`、`needs_more_material` 与 `archived` 五个固定状态；四类入队触发继续通过不透明控制标签承接。
- 每条关键结论严格二选一关联 `evidence_id_ref` 或 `evidence_gap_ref`。所有输入都是控制标签，不包含真实来源、OCR、冲突、解析、证据、报告、actor、时间、旧值、新值或业务判断。

## 纯内存投影

每条请求机械投影四组控制记录，共 101 个字段、五条共 505 个检查点：

1. 复核队列 Schema、入队工作流、四类触发、固定状态与来源／证据绑定形状。
2. actor、time、reason、old_value、new_value、复核结果、重新复核、归档与业务线白箱确认审计形状。
3. 证据风险、证据可信等级、报告质量与报告状态未来写回形状。
4. 面向人类的中文复核原因、外部增强来源分离与业务线白箱门禁形状。

“写回复核队列、证据风险和报告状态”在本切片中表示未来字段、状态和审计控制标签已经被机械投影。真实队列、schema migration、UI 渲染、审计写入、证据可信等级、报告质量、报告状态、数据库和人工确认继续由后续业务线白箱授权工作处理。

## 阶段边界

- P3 才专项验证低质量 OCR、冲突资料、撤回资料与外部增强替代内部证据等异常场景，并验证 actor、time、reason、old/new value 和影响控制。
- P4 才交付复核队列样例、复核审计日志和 UI 流程说明的 metadata-only 控制证据。
- Stage113 Review 才机械复审 P1 至 P4 的冻结控制工件。
- 本 run 止于 `IDS-STAGE113-P3-GATE`。

## 停止与回滚

输入漂移返回 `CONTROL_INPUT_MISMATCH`，并保持零投影、零持久化、零运行时。回滚只撤回本 P2 的范围说明、纯内存模块、合同、聚焦用例、machine run、治理投影、生成中文视图、变更日志和交接，恢复到 P1 的 `PASS_REVIEW_QUEUE_SCHEMA_CONTRACT_RUNTIME_DISABLED`；P1、Stage112 Review、冻结任务包、来源资料、真实证据账本、已交付报告、既有审计日志、数据库、GitHub、OVH 与应用状态保持原有边界。
