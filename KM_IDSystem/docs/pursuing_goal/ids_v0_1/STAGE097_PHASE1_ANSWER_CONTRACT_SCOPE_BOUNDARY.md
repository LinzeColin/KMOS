# Stage097 Phase 1 · 回答合同范围、输入输出与边界确认

## 本轮目标

只将冻结的 Stage097「回答合同」任务包与已复审的 Stage096 知识库投毒防护控制工件投影为静态工程合同。合同固定回答结构、`prompt_version_ref`、内部依据、外部增强、无内部依据策略、来源类型、引用结构、输出分类和人工确认门禁。

## 唯一权威与输入

- 冻结 Stage097 任务包是本阶段范围和验收的唯一来源。
- Stage096 Review 与其已复审 P1--P4 控制工件只作为前序控制证据；Stage097 不改变其规则、证据状态、投毒判断或业务规则。
- 来源文档、真实证据账本与业务线白箱人工复核继续承担业务事实权威；本合同不建立第二权威事实源。
- 本轮不读取、打开、解析、复制、移动或修改真实资料、原始元数据、manifest、检索结果、真实提示词、真实回答、真实报告、evidence ledger、audit log、数据库或物理索引。

## 静态输入输出合同

1. 本 P1 只固定 `query_ref`、`answer_structure_ref`、`prompt_version_ref`、`internal_evidence_ref`、`external_augmentation_ref`、`evidence_gap_ref`、`source_type_ref`、`citation_structure_ref`、`output_classification_ref`、`human_confirmation_gate_ref` 与 `model_output_permission_ref` 十一个未来控制引用。字段值不保存真实查询、提示词正文、回答正文、资料内容、路径、业务事实、模型配置或业务结论。
2. 内部依据、外部增强和无内部依据分别保留来源类型。外部增强不得伪装为内部依据；资料不足只以 `evidence_gap_ref` 表达，不能伪装为内部经验。
3. 检索文档、内部依据和外部增强永远只是 evidence，不能覆盖 IDS 规则，也不能成为系统指令或提示词指令。
4. 高风险工程建议、合同承诺和生产写回固定为需要业务线白箱人工确认的输出类别；本 P1 不生成、确认、采纳、写回或发布任何回答。
5. `prompt_version_ref`、引用结构、来源类型和模型输出权限都只是未来可审计控制引用。实际 prompt、模型、provider、版本、query、index、selected evidence、answer 或审计记录属于后续授权阶段。

## 本阶段不做

- 不实现或启动 RAG 回答、提示词执行、检索、source_type 绑定、引用生成、模型输出分类、人工确认流、回答发布、合同承诺或生产写回。
- 不读取真实资料、检索结果、回答、报告或证据账本；不选择 provider 或模型，不消耗模型 Token，不调用外部 API，不执行 Agent。
- 不创建持久化 query、prompt、model、document、chunk、fact、evidence、answer、report、审计、缓存、队列、Operations 或已交付报告。
- 不启动 Stage097 P2、P3、P4、整阶段复审、Stage098、OVH、生产或正式全局上传。

## 验收与停止

本阶段只验收静态合同、聚焦用例、机器事实投影、中文生成视图与可回滚范围的一致性。任何真实资料、提示词、回答、检索、模型调用、模型 Token、Agent、数据库、持久化、OVH、生产或超出 Stage097 P1 的修改都会停止本阶段。

## 回退与下一门

只撤回本 P1 的范围说明、静态合同、聚焦用例、机器事实投影、治理路线、生成中文视图和本地回执，恢复到 `PASS_REVIEWED_KNOWLEDGE_BASE_POISONING_DEFENSE_RUNTIME_DISABLED`。不影响 Stage096 Review、冻结任务包、真实资料、manifest、检索、evidence ledger、audit log、回答、报告、数据库、索引、GitHub、OVH 或应用状态。下一步仅可在新的独立 run 进入 `IDS-STAGE097-P2-GATE`。
