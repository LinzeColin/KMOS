# Stage106 P3 · 外部增强意见章节专项异常场景

## 目标与入口

- 任务：`IDS-V0_1-STAGE106-P3`
- 入口门禁：`IDS-STAGE106-P3-GATE`
- 下一门禁：`IDS-STAGE106-P4-GATE`
- 依据：冻结 `STAGE-106_外部增强意见章节.md`、Stage106 P1/P2 控制工件与已复审的 Stage105 报告证据绑定控制工件。

本阶段只机械重放 P2 的五条固定、非业务、`reference-only` 控制投影。来源文档、真实证据账本与业务线白箱人工复核继续承担业务事实权威；本阶段不建立第二权威事实源。

## 固定验证范围

P2 控制形状保持为：5 条控制请求、每条 30 个输入字段、承接 P1 的 27 个控制引用并加入 `evidence_grade_ref`、4 组投影、每条 74 个投影字段、共 370 个前序控制检查点。P3 固定形成：

- 5 条场景，每条 34 个字段，共 170 个场景检查点；
- 5 个控制视图与 5 条业务线白箱处理记录；
- 2 条场景表达未来白箱人工确认要求，人工确认与最终结论均未记录；
- 15 类失败关闭状态。

五条场景覆盖冻结任务包的 P3 验证项：

| 场景 | 验证的控制结论 |
| --- | --- |
| `critical_conclusion_evidence_id_binding_integrity_control` | 关键结论保留 `evidence_id`，并且与 `evidence_gap` 严格二选一。 |
| `critical_conclusion_evidence_gap_binding_integrity_control` | 关键结论保留 `evidence_gap`，并且不能伪装为已有内部证据。 |
| `external_augmentation_retains_external_source_type_control` | `external_public_reference` 与 `model_reasoning` 保留底层来源语义，不能写成内部项目依据。 |
| `human_confirmation_gate_keeps_final_conclusion_unpublished_control` | 业务线白箱确认保持未来门禁，最终结论未发布。 |
| `withdrawal_downgrade_and_index_change_impact_report_status_control` | 资料撤回、证据降级与索引版本变化保持报告状态影响控制，等待业务线白箱复核。 |

## 控制边界

场景模块只处理 P2 生成的控制标签。它不读取真实资料、原始元数据、外部参考、报告、PDF、证据账本、审计日志、数据库或物理索引；不生成、展示、导出、保存、更新、发布、重新生成或撤回报告；不调用模型、Agent、外部 API、OVH 或生产服务。

资料撤回、证据降级和索引版本变化只表达未来报告状态影响控制，不读取、更新、发布、重新生成或撤回真实报告。外部增强只保留未来来源语义，不能替代 `evidence_id`、`evidence_gap` 或业务线白箱人工确认。

## 失败关闭与回退

P2 控制形状、零运行时边界、不透明引用、关键结论绑定、外部来源分离、报告状态自动更新或白箱确认门禁发生漂移时，P3 返回失败报告：不产生场景、控制视图或业务记录，所有运行时计数保持零，运行时标志保持 false。

回退只撤回本 P3 的范围说明、纯内存场景模块、合同、聚焦用例、machine run、机器事实投影、治理路线、事件、生成中文视图与交接，返回 `PASS_IN_MEMORY_EXTERNAL_AUGMENTATION_OPINION_CONTROL_SLICE_RUNTIME_DISABLED`。Stage106 P1/P2、Stage105 Review、冻结任务包、来源文档、真实证据账本、已交付报告、数据库、GitHub、OVH 与应用状态保持原状。

## P4 前置条件

P3 本地验收完成后停在 `IDS-STAGE106-P4-GATE`。P4 只可从本阶段固定控制场景派生 metadata-only 交付证据、报告模板限制、重新生成/撤回说明和中文反馈，继续保持单一权威事实源、业务线白箱人工复核与全零运行时边界。
