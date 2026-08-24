# Stage098 Phase 1 · Prompt 版本化范围、输入输出与边界确认

## 本轮目标

将冻结的 Stage098「Prompt 版本化」任务包与已复审的 Stage097 回答合同控制工件投影为静态工程合同。本合同只固定未来 `prompt_version`、`model_provider`、`model_version`、`temperature` 与 `retrieval_context` 的控制引用，以及回答结构、来源类型和输出权限的继承边界。

## 唯一权威与输入

- 冻结 Stage098 任务包是本阶段范围和验收的唯一来源。
- Stage097 Review 与其 P1--P4 控制工件是前序控制证据；Stage098 继承其回答结构、资料身份、来源类型和业务线白箱门禁，不改变其业务规则、证据状态或结论。
- 来源文档、真实证据账本与业务线白箱人工复核继续承担业务事实权威；本合同不建立第二权威事实源。
- 本轮不读取、打开、解析、复制、移动或修改真实资料、原始元数据、manifest、检索结果、提示词正文、回答、报告、evidence ledger、audit log、数据库或物理索引。

## 静态输入输出合同

1. 本 P1 只固定 `prompt_version_ref`、`model_provider_ref`、`model_version_ref`、`temperature_ref` 与 `retrieval_context_ref` 五个未来控制引用。字段值不保存提示词正文、供应商、模型、温度、检索上下文、资料内容、路径、业务事实或业务结论。
2. `prompt_version_ref` 只标识未来可审计的版本引用；provider、model 与 temperature 只保留未来配置引用。实际配置、实际模型选择与实际检索上下文保持后续授权范围。
3. RAG 回答结构、内部依据、外部增强、无内部依据策略、来源类型分离和引用结构继承 Stage097 回答合同。检索文档永远只是 evidence，IDS 规则保持优先级，资料不足保持 `evidence_gap`，外部增强保持底层来源类型。
4. 高风险工程建议、合同承诺与生产写回继续要求业务线白箱人工确认。本 P1 不生成、分类、确认、采纳、发布或写回任何回答。
5. 本合同明确失败状态、停止条件、未来审计引用需求和回退路径；当前不创建实际审计日志或持久化记录。

## 本阶段不做

- 不创建或执行实际 prompt，不选择或调用 provider／model，不配置 temperature，不绑定 retrieval_context。
- 不实现或启动 RAG 回答、检索、source_type 绑定、引用生成、模型输出分类、人工确认流、回答发布、合同承诺或生产写回。
- 不读取真实资料、检索结果、回答、报告或证据账本；不消耗模型 Token，不调用外部 API，不执行 Agent。
- 不创建持久化 prompt、model、query、document、chunk、fact、evidence、answer、report、审计、缓存、队列、Operations 或已交付报告。
- 不启动 Stage098 P2、P3、P4、整阶段复审、Stage099、OVH、生产或正式全局上传。

## 验收与停止

本阶段只验收静态合同、聚焦用例、机器事实投影、中文生成视图与可回滚范围的一致性。真实资料、提示词正文、回答、检索、模型调用、模型 Token、Agent、数据库、持久化、OVH、生产或超出 Stage098 P1 的修改触发本阶段停止条件。

## 回退与下一门

只撤回本 P1 的范围说明、静态合同、聚焦用例、机器事实投影、治理路线、生成中文视图和本地回执，恢复到 `PASS_REVIEWED_ANSWER_CONTRACT_RUNTIME_DISABLED`。Stage097 Review、冻结任务包、真实资料、manifest、检索、evidence ledger、audit log、回答、报告、数据库、索引、GitHub、OVH 与应用状态保持原状。下一步仅可在新的独立 run 进入 `IDS-STAGE098-P2-GATE`。
