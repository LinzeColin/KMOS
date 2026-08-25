# Stage101 P4 · RAG 可复现交付证据、回滚与中文反馈

## 本轮目标

只从 Stage101 P3 已验收的六条固定、非业务、reference-only 场景派生 P4 交付证据：RAG 回答样例、负向测试结果、prompt/version 记录、完整可复现元组日志、模型输出权限边界，以及 prompt 回滚和模型配置回退说明。

## 唯一控制上下文

- 冻结 Stage101 任务包、Stage101 P1/P2/P3 控制工件和 Stage100 Review 已复审无内部依据策略工件共同限定本 P4；来源文档与业务线白箱人工复核继续承担唯一业务事实权威。
- 所有样例、记录、日志和回退说明只使用 `:control:stage101-p2:` 或 `:control:stage101-p4:` 控制引用与 `CONTROL_` 状态。它们不包含真实查询、提示词、provider、模型配置、证据、回答、日志正文或业务结论。
- 受控交付证据不能替代来源文档、业务线白箱人工确认或正式运行审计；本轮不建立第二权威事实源。

## 固定交付证据

1. 六条 P3 场景各派生一条受控 RAG 回答样例、负向测试结果、prompt/version 记录、可复现日志和模型输出权限边界记录。
2. 回答样例和可复现日志持续携带 query、index_version、prompt_version、model_provider、model_version、temperature、retrieval_context 与 selected_evidence 的八元可复现记录键引用。
3. 负向测试结果固定覆盖提示注入拒绝、无内部依据不伪装为内部经验，以及三类高风险输出不自动进入最终结论。
4. prompt/version 记录保留 provider、模型版本、temperature、检索上下文、未来模型推理候选与实际模型调用分离；实际提示词或模型配置访问保持未执行。
5. 两条回退说明分别定义 prompt 回滚与模型配置回退的未来控制目标；业务线白箱批准、版本化依据和可验证回退目标是未来执行前置条件。
6. 输出权限记录保持业务线白箱人工处理必经、人工确认未记录、最终结论未发布；高风险工程建议、合同承诺和生产写回保持人工确认门禁。

## 失败关闭与运行边界

- P3 输出形状、完整可复现元组、控制引用、零运行边界、提示注入语义、来源类型分离、高风险权限或交付记录形状不匹配时，P4 返回失败结果并留在 `IDS-STAGE101-P4-GATE`；不生成交付记录或持久化内容。
- 真实资料、原始元数据、fixture、检索、提示词、回答、真实日志、证据账本、报告、数据库、模型、模型 Token、Agent、OVH、生产、正式上传与推送保持后续授权范围。
- 真实 RAG 执行、prompt 或模型配置访问、输出分类、人工确认、回答发布、日志写入、prompt 回滚和模型配置回退均不在本 P4 执行。

## 验收、回滚与下一门

本 P4 验收六组受控交付记录、负向语义、完整可复现元组、输出权限、两条回退说明、失败关闭、全零运行计数、机器事实投影和中文生成视图的一致性。回滚只撤回本文件、P4 纯内存交付模块、合同、聚焦用例、machine run、机器事实投影、治理路线、生成中文视图与本交接，恢复到 `PASS_RAG_REPRODUCIBILITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED`。Stage101 P1/P2/P3、Stage100 Review、冻结任务包、真实资料、manifest、检索、evidence ledger、audit log、回答、报告、数据库、GitHub、OVH 和应用状态保持原状。下一步仅可在新的独立 run 进入 `IDS-STAGE101-REVIEW-GATE`。
