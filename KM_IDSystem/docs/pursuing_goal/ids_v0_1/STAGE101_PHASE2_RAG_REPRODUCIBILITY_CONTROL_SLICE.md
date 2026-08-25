# Stage101 P2 · RAG 可复现受控最小切片

## 本轮目标

将冻结 Stage101 P1 的 RAG 可复现静态合同投影为可执行的纯内存控制切片。切片使用固定、非业务、`reference-only` 标签表达回答结构、查询、索引、Prompt、模型提供方、模型版本、温度、检索上下文、所选依据、来源类型、外部增强展示、提示注入防护和输出权限门禁。

## 单一权威与前序

- 冻结 Stage101 任务包、Stage101 P1 静态合同与 Stage100 Review 已复审无内部依据策略控制工件构成本 P2 的唯一控制上下文。
- 来源文档、真实证据账本与业务线白箱人工复核继续承担业务事实权威；本切片只投影控制标签，不建立第二权威事实源。
- 输入与输出使用 `:control:stage101-p2:` 前缀的 `reference-only` 标签，不承载正文、路径、业务事实、真实查询、真实 Prompt、真实模型配置、真实 evidence、真实回答或业务结论。

## 固定控制输入与投影

1. 输入固定为 6 条非业务、`reference-only` 控制请求，每条 23 个字段。场景覆盖安全摘要、带 evidence_gap 的草案建议、检索文档提示注入拒绝、高风险工程建议、合同承诺和生产写回。
2. 每条请求保留 `query_ref`、`index_version_ref`、`prompt_version_ref`、`model_provider_ref`、`model_version_ref`、`temperature_ref`、`retrieval_context_ref` 与 `selected_evidence_ref` 八个未来可复现记录键引用。它们只定义未来记录形状，不触发查询、检索、版本选择、Prompt 执行、模型调用或 evidence 选择。
3. 输出固定为 4 组纯内存控制投影：可复现记录绑定、可复现记录、来源语义与外部增强展示、提示注入与输出权限。每条请求固定 45 个投影字段，共 270 个控制检查点。
4. `external_augmentation_opinion` 仅是展示层组合标签，由 `external_public_reference` 与 `model_reasoning` 组成；`internal_evidence`、`external_public_reference`、`model_reasoning` 与 `evidence_gap` 保持四类底层来源类型。外部增强不替代内部依据，也不关闭 `evidence_gap`。
5. 检索文档保持 evidence 身份，IDS 规则保持优先级。高风险工程建议、合同承诺和生产写回保留业务线白箱人工确认门禁，最终结论保持未发布。

## 运行边界

- 控制输入由模块自身生成，字段形状、场景或控制标签变化时产生 `CONTROL_INPUT_MISMATCH` 并返回零条投影。
- 真实资料、原始元数据、fixture、manifest、查询、检索、证据账本、Prompt、回答、报告、数据库、模型 Token、Agent、OVH、生产与正式上传保留在后续授权阶段。
- 本切片保持纯内存状态，运行计数、运行标志和持久化记录均维持零值或关闭值。

## 验收、回退与下一门

本 P2 验收固定控制形状、八类未来可复现记录键引用、来源类型分离、外部增强展示、提示注入防护、五类输出分类、三类高风险输出人工确认、输入不匹配处理、机器事实投影和中文生成视图的一致性。回退只撤回本 P2 的说明、纯内存控制切片、合同、聚焦用例、机器事实投影、治理路线、生成中文视图与本地回执，恢复到 `PHASE1_RAG_REPRODUCIBILITY_CONTRACT_RUNTIME_DISABLED`。Stage101 P1、Stage100 Review、冻结任务包、真实资料、manifest、检索、evidence ledger、audit log、回答、报告、数据库、GitHub、OVH 与应用状态保持原状。下一步仅可在新的独立 run 进入 `IDS-STAGE101-P3-GATE`。
