# Stage112 · 报告导出审计 Phase 2 受控最小切片

## 本轮目标

Stage112 P2 以 P1 静态报告导出审计合同与 Stage111 Review 控制工件为前序，形成可机械执行、可测试、可回滚的纯内存控制切片。切片投影报告证据绑定、章节输出、五项生成快照、报告快照、影响分析、质量评分、报告导出审计身份／状态／保留控制，以及外部增强来源分离与业务线白箱确认门禁。

## 固定控制输入

- 固定五条非业务、reference-only 控制请求：报告导出审计身份、资料撤回、证据降级、索引版本变化与外部增强白箱确认。
- 每条请求固定 34 个输入字段：`control_scenario`、`binding_mode` 与 P1 的 32 个未来控制引用。
- 每条关键结论保持 `evidence_id_ref` 或 `evidence_gap_ref` 严格二选一，并保留 `evidence_grade_ref`、`citation_source_ref`、`citation_page_ref` 与 `human_confirmation_item_ref`。
- 所有输入都是不透明控制标签；模块不包含业务事实、业务判断、真实 actor、时间、report_id、快照、审计记录或可写入运行时参数。

## 纯内存投影

每条请求机械投影四组控制记录，共 100 个字段、五条共 500 个检查点：

1. 报告导出审计身份（actor、time、report_id、evidence_snapshot）、报告证据绑定、章节输出、导出目的地／格式和 PDF 引用来源／页码形状。
2. data/index/evidence/model/generated_at 五项生成快照与报告快照形状。
3. 报告影响、质量评分、导出审计标签、审计状态／失败原因／保留、重新生成与撤回形状。
4. 外部增强来源语义与业务线白箱人工确认门禁。

“写入报告”和“记录报告导出审计”在本切片中表示未来字段与状态标签已经被机械投影。真实报告、PDF、快照、影响结果、质量分数、审计记录、数据库记录和人工确认继续由后续业务线白箱授权工作处理。

## 阶段边界

- P3 才专项验证关键结论 `evidence_id/evidence_gap`、资料撤回、证据降级、索引版本变化和外部增强来源边界。
- P4 才交付报告样例、报告快照、质量评分、影响分析、模板限制与重新生成／撤回说明的 metadata-only 交付控制证据。
- Stage112 Review 才机械复审 P1 至 P4 的冻结控制工件。
- 本 run 止于 `IDS-STAGE112-P3-GATE`。

## 停止与回滚

输入漂移返回 `CONTROL_INPUT_MISMATCH`，并保持零投影、零持久化、零运行时。回滚只撤回本 P2 的范围说明、纯内存模块、合同、聚焦用例、machine run、治理投影、生成中文视图、变更日志和交接，恢复到 P1 的 `PASS_REPORT_EXPORT_AUDIT_CONTRACT_RUNTIME_DISABLED`；P1、Stage111 Review、冻结任务包、来源资料、真实证据账本、已交付报告、既有审计日志、数据库、GitHub、OVH 与应用状态保持原有边界。
