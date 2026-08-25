# Stage101 P1 · RAG 可复现范围、输入输出与边界确认

## 本 phase 的目标

依据冻结 `STAGE-101_RAG可复现.md` 与已复审的 Stage100 无内部依据策略控制工件，固定未来 RAG 回答可复现所需的控制引用、来源语义、输出权限和人工确认门禁。本 phase 的交付物是可审计、可测试、可回滚的静态工程合同。

## 单一权威与输入边界

- 冻结 Stage101 任务包与 Stage100 Review 控制工件构成唯一控制上下文。
- 来源文档、真实证据账本与业务线白箱人工复核继续承担业务事实权威。
- 本合同不建立第二权威事实源，也不替代来源文档、真实证据、审计记录或业务线判断。
- 本 phase 不读取或列举业务资料、原始元数据、fixture、manifest、检索结果、Prompt 正文、回答、报告、数据库、物理索引或审计日志。

## 未来回答的可复现记录形状

每条未来 RAG 回答必须保留以下控制引用：

1. `rag_answer_structure_ref`
2. `query_ref`
3. `index_version_ref`
4. `prompt_version_ref`
5. `model_provider_ref`
6. `model_version_ref`
7. `temperature_ref`
8. `retrieval_context_ref`
9. `selected_evidence_ref`
10. `internal_evidence_ref`
11. `external_augmentation_ref`
12. `evidence_gap_ref`
13. `source_type_ref`
14. `model_output_permission_ref`
15. `human_confirmation_gate_ref`

未来重放需要同时保留查询、索引、Prompt、模型、温度、检索上下文和所选依据引用，并保留底层来源类型、内部依据不足声明、输出权限和人工确认门禁。当前不创建记录、不执行重放、不生成答案。

## 来源语义与输出权限

- 内部依据、外部公开参考、模型推理和 `evidence_gap` 保持独立的底层来源类型。
- `external_augmentation_opinion` 仅为未来展示层组合标签，保留外部公开参考和模型推理的底层来源类型。
- 内部依据不足时保留 `evidence_gap`；外部增强意见不替代内部依据，也不关闭 `evidence_gap`。
- 检索文档永远只是 evidence，文档内指令不能覆盖 IDS 规则或成为系统指令。
- `safe_summary`、`draft_recommendation`、`high_risk_engineering_advice`、`contractual_commitment` 与 `production_writeback` 仅定义未来分类语义。高风险工程建议、合同承诺和生产写回均保持业务线白箱人工确认前置，最终结论保持未发布。

## 本 phase 之外的运行时事项

真实查询、索引读取或切换、检索、Prompt 正文、provider 或模型选择和调用、模型 Token、来源类型绑定、外部增强展示、引用生成、输出分类、人工确认、回答发布、生产写回、数据库连接、审计、持久化、Agent、OVH、生产和正式上传均属于后续授权范围。

## 验收与停止条件

- 静态合同完整覆盖任务包 P1 的回答结构、Prompt 版本、内部依据、外部增强、无内部依据策略、模型输出权限、检索文档 evidence 边界和人工确认门禁。
- 聚焦白箱用例验证合同身份、单一权威、可复现记录形状、来源语义、输出权限、失败关闭、回退与零运行时边界。
- 本 run 止于 `IDS-STAGE101-P2-GATE`；P2 仍保持未启动。
- 任何真实资料或运行时动作、任何不可回滚 schema 变更、任何跨 Stage 改动或测试原因不明的失败都会停止该 phase。

## 回滚

回滚仅撤回本 P1 的范围说明、静态合同、聚焦用例、机器事实投影、治理路线、生成中文视图与本地回执，返回 Stage100 Review 的本地零运行时状态。冻结任务包、Stage100 P1--P4、真实资料、manifest、证据账本、审计日志、报告、数据库、索引、GitHub、OVH 与应用状态保持原状。
