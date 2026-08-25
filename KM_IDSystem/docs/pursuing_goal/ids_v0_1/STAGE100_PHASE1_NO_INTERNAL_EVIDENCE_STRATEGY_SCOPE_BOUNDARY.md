# Stage100 Phase 1 · 无内部依据策略范围、输入输出与边界确认

## 本轮目标

将冻结的 Stage100「无内部依据策略」任务包与已复审的 Stage099 内部依据与外部增强分离控制工件投影为静态工程合同。合同固定 RAG 回答结构、prompt 版本、内部依据、外部增强、evidence_gap、无内部依据策略、来源类型、模型输出权限和业务线白箱人工确认门禁。

## 唯一权威与输入

- 冻结 Stage100 任务包是本阶段范围、验收和停止条件的唯一来源。
- Stage099 Review 与其 P1--P4 控制工件是前序控制证据；Stage100 继承检索文档 evidence 身份、IDS 规则优先级、来源类型分离、输出权限、人工白箱处理和 P4 回退边界，不重写任何前序业务规则、证据状态或结论。
- 来源文档、真实证据账本与业务线白箱人工复核继续承担业务事实权威；本合同不建立第二权威事实源。
- 本轮不读取、打开、解析、复制、移动或修改真实资料、原始元数据、manifest、检索结果、提示词正文、回答、报告、evidence ledger、audit log、数据库或物理索引。

## 静态输入输出合同

1. 本 P1 固定 rag_answer_structure_ref、prompt_version_ref、internal_evidence_ref、external_augmentation_ref、evidence_gap_ref、no_internal_evidence_policy_ref、source_type_ref、model_output_permission_ref 与 human_confirmation_gate_ref 九个未来控制引用。字段只保存控制名称，不保存资料内容、路径、提示词正文、模型输出、业务事实或业务结论。
2. 内部依据不足时必须保留 evidence_gap，并声明“内部依据不足”这一未来答案状态。evidence_gap 不得伪装为内部经验，不能重分类为内部依据；外部公开参考与模型推理形成的外部增强也不能消除、替代或伪装该缺口。
3. 底层来源类型固定为 internal_evidence、external_public_reference、model_reasoning 与 evidence_gap。external_augmentation_opinion 仅允许作为未来展示层组合名称：它可组合外部公开参考与模型推理，但保持底层来源类型，不能成为内部依据。
4. 检索文档永远只是 evidence，不能成为系统指令或覆盖 IDS 规则。高风险工程建议、合同承诺与生产写回保持独立的模型输出分类；业务线白箱人工确认是进入未来最终结论前的必要门禁。
5. 本合同明确失败状态、停止条件、未来审计引用需求和回退路径；当前不创建实际审计日志、持久化记录、外部增强展示、回答或业务结论。

## 本阶段不做

- 不创建或执行实际 prompt，不选择或调用 provider 或 model，不生成 RAG 回答、引用、来源类型绑定或模型输出分类。
- 不实现 UI 展示、外部增强合并、检索、query/index/selected evidence 记录、人工确认流、回答发布、合同承诺或生产写回。
- 不读取真实资料、检索结果、回答、报告或证据账本；不消耗模型 Token，不调用外部 API，不执行 Agent。
- 不创建持久化 prompt、model、query、document、chunk、fact、evidence、answer、report、审计、缓存、队列、Operations 或已交付报告。
- 不启动 Stage100 P2、P3、P4、整阶段复审、OVH、生产或正式全局上传。

## 验收与停止

本阶段只验收静态合同、聚焦用例、机器事实投影、中文生成视图与可回滚范围的一致性。真实资料、提示词正文、回答、检索、模型调用、模型 Token、Agent、数据库、持久化、OVH、生产或超出 Stage100 P1 的修改触发本阶段停止条件。

## 回退与下一门

只撤回本 P1 的范围说明、静态合同、聚焦用例、机器事实投影、治理路线、生成中文视图和本地回执，恢复到 PASS_REVIEWED_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_RUNTIME_DISABLED。Stage099 Review、冻结任务包、真实资料、manifest、检索、evidence ledger、audit log、回答、报告、数据库、索引、GitHub、OVH 与应用状态保持原状。下一步仅可在新的独立 run 进入 IDS-STAGE100-P2-GATE。
