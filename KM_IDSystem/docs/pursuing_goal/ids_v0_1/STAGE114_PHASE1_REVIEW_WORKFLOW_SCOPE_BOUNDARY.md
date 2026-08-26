# Stage114 · 复核工作流 Phase 1 范围、输入输出与控制边界

## 目标与入口

- 任务：`IDS-V0_1-STAGE114-P1`
- 入口门禁：`IDS-STAGE114-P1-GATE`
- 后续门禁：`IDS-STAGE114-P2-GATE`
- 冻结输入：Stage114 任务包与 Stage113 复核队列 Schema Review 控制工件。

本 Phase 固定人工复核工作流的未来控制形状：低 OCR 置信度、资料冲突、解析失败和证据风险均保留进入待复核的控制路由；待复核、已确认、已拒绝、需补资料和已归档均为固定状态标签。合同不承载真实队列项、真实状态、真实复核结果、真实证据可信等级、真实报告质量分或业务结论。

## P1 固定工作流控制合同

- 输入与输出只包含 future-control reference：复核队列项、触发类型、状态前后、转换请求、转换原因、actor、time、review result、old value、new value、证据绑定、证据可信等级与报告质量／状态影响。
- 四类触发 `low_ocr_confidence`、`source_conflict`、`parsing_failure`、`evidence_risk` 必须各自能够指向未来 `pending_review` 路由；本 Phase 不评估任何真实 OCR、冲突、解析或证据风险。
- 状态集固定为 `pending_review`、`confirmed`、`rejected`、`needs_more_material`、`archived`。`submit_for_review`、`confirm`、`reject`、`request_more_material`、`archive` 仅为未来动作控制标签；具体允许的状态转移、归档时机、重新复核及例外处理继续由业务线白箱人工复核授权。
- 每次未来转换必须保留 `from_status`、`to_status`、`actor`、`time`、`reason`、`old_value`、`new_value`、`review_result` 与审计控制引用。复核结果只能指向未来 evidence trust level、报告质量分和报告状态影响控制，不能形成事实、等级、分数或最终结论。
- 外部增强保留外部来源身份，不能成为内部项目证据、替代证据绑定、关闭 evidence gap 或绕过人工复核。

## 单一权威与运行时边界

- 冻结 Stage114 任务包与 Stage113 Review 控制工件构成本 Phase 的唯一工程控制上下文；来源文档、真实证据账本、已交付报告、既有审计日志与业务线白箱人工复核继续承担业务事实权威。
- 本 Phase 产物是范围说明、静态合同、聚焦用例、治理投影和本地回执。真实资料、OCR、冲突、解析、证据风险、复核队列、复核工作流、复核 UI、复核审计、证据可信等级、报告质量分、报告状态、数据库、人工确认、模型 Token、Agent、OVH、生产和正式上传保持后续授权范围。
- 本 run 不创建队列、工作流实例、状态转换、审计、schema migration、数据库或持久化记录；运行计数保持零。

## 验收、停止与回滚

- 聚焦用例必须验证四类未来入队路由、五个固定状态、五个工作流动作标签、actor/time/reason/old/new 审计控制、复核结果对证据可信等级与报告质量／状态控制的未来引用、外部增强来源分离、业务线白箱门禁和零运行时边界。
- 缺失 Stage113 Review 控制、任一触发、任一状态、任一动作标签、审计必填引用、证据可信等级或报告影响控制，或者发现实际工作流、人工确认、审计写入、数据库写入、第二权威、模型、Agent、OVH、生产或提前进入 P2 时，合同以失败状态关闭并停留在 `IDS-STAGE114-P1-GATE`。
- 回滚只撤回本 P1 的范围说明、静态合同、聚焦用例、machine run、治理投影、中文视图与交接，恢复 Stage113 Review 的本地零运行时状态；来源文档、真实证据账本、已交付报告、既有审计日志、数据库、GitHub、OVH 与应用状态保持既有边界。
