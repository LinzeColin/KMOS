# Stage097 Phase 3 · 回答合同专项验证与异常场景

## 本轮目标

只重放 Stage097 P2 的六条固定、非业务、`reference-only` 控制投影，形成 P3 的六条异常场景验证。验证检索文档中的提示词不能覆盖 IDS 规则、无内部依据不伪装为内部经验，以及高风险工程建议、合同承诺和生产写回不会自动进入最终结论。

## 唯一控制上下文

- 冻结 Stage097 任务包、Stage097 P1 静态回答合同、Stage097 P2 受控最小切片和 Stage096 Review 已复审工件共同限定本 P3；来源文档、真实证据账本和业务线白箱人工复核继续承担业务事实权威。
- P3 只读取本仓已追踪的 P1/P2/Review 控制工件。所有输入、场景、视图与人工处理记录均是 `:control:stage097-p2:` 前缀的控制引用或 `CONTROL_` 状态，不包含正文、路径、真实查询、真实提示词、真实模型配置、真实 evidence、真实回答或业务结论。
- 本轮不建立第二权威事实源；不把场景通过误作真实 RAG 回答、模型输出、业务判断、人工确认完成、合同承诺或生产写回。

## 固定专项验证

1. 六条 P2 控制请求按固定顺序重放：外部增强来源类型保持、无内部依据、检索文档提示注入、高风险工程建议、合同承诺、生产写回。
2. 每条场景固定 28 个字段，共 168 个场景字段检查点；同时复核 P2 的 4 组、每条 35 字段、共 210 个源控制字段。
3. 固定输出 5 个控制视图：回答合同绑定、版本与所选 evidence、来源类型与外部增强、提示注入、输出权限；每个视图只呈现控制引用与状态。
4. 六条场景各保留一条业务线白箱人工处理要求。人工处理仅为未来前置条件，当前 `business_line_whitebox_human_approval_recorded=false`，最终结论保持未发布。
5. 提示注入场景必须保持 `CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL` 和 `CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED`。无内部依据场景必须保留 `evidence_gap_ref`，且 `internal_evidence_ref` 为空。三类高风险输出必须保持 `CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION`。

## 失败关闭与运行边界

- P2 输出形状、固定控制引用、零运行时边界或任一专项语义不匹配时，P3 返回失败结果并留在 `IDS-STAGE097-P3-GATE`；不生成场景、视图、业务事实或持久化记录。
- 真实资料、原始元数据、fixture、manifest、检索、提示词、回答、evidence ledger、审计日志、报告、数据库、模型、模型 Token、Agent、OVH、生产、正式上传与推送均保持后续授权范围。
- 真实来源类型绑定、提示注入执行、输出分类、人工确认、回答发布、合同承诺和生产写回均不在本 P3 执行。

## 验收、回滚与下一门

本 P3 验收六条场景、28 字段场景形状、五个控制视图、六条人工处理要求、三类冻结异常语义、失败关闭、全零运行计数、机器事实投影和中文生成视图的一致性。回滚只撤回本 P3 的范围说明、纯内存场景模块、合同、聚焦用例、machine run、机器事实投影、治理路线、生成中文视图与本交接，恢复到 `PASS_ANSWER_CONTRACT_CONTROL_SLICE_RUNTIME_DISABLED`。Stage097 P1/P2、Stage096 Review、冻结任务包、真实资料、manifest、检索、evidence ledger、audit log、回答、报告、数据库、GitHub、OVH 和应用状态保持原状。下一步仅可在新的独立 run 进入 `IDS-STAGE097-P4-GATE`。
