# Stage102 P1 · 文档内提示注入防护范围、输入输出与边界确认

## 本 phase 的目标

依据冻结 `STAGE-102_文档内提示注入防护.md` 与已复审的 Stage101 RAG 可复现控制工件，固定文档内潜在指令的控制引用、IDS 规则优先级、来源语义、输出权限和业务线白箱人工确认门禁。本 phase 的交付物是可审计、可测试、可回滚的静态工程合同。

## 单一权威与输入边界

- 冻结 Stage102 任务包与 Stage101 Review 控制工件构成唯一控制上下文。
- 来源文档、真实证据账本与业务线白箱人工复核继续承担业务事实权威。
- 本合同不建立第二权威事实源，也不替代来源文档、真实证据、审计记录或业务线判断。
- 本 phase 不读取、列举、提取、分类或处理业务资料、原始元数据、fixture、manifest、检索结果、文档正文、Prompt 正文、回答、报告、数据库、物理索引或审计日志。

## 文档指令的未来控制形状

未来处理每条文档 evidence 时必须保留 `rag_answer_structure_ref`、`document_evidence_ref`、`document_instruction_candidate_ref`、`ids_rule_ref`、`prompt_version_ref`、`injection_defense_policy_ref`、查询、索引、selected evidence、来源类型、输出权限、人工确认和审计边界共 `17` 个控制引用。

- 文档 evidence 和文档内潜在指令均保持不可信、不可执行的控制引用。
- IDS 规则、Prompt 版本、输出权限和业务线白箱人工确认门禁保持控制面优先级。
- 文档文本不能成为系统指令、工具或外部动作授权、Prompt 或模型配置覆盖，也不能绕过输出权限、人工确认、发布或生产写回。
- P1 只定义未来类别和边界；不读取、识别、分类或压制任何真实文档内指令。

## 来源语义与输出权限

- `internal_evidence`、`external_public_reference`、`model_reasoning` 与 `evidence_gap` 保持独立底层来源类型。
- `external_augmentation_opinion` 仅是未来展示层组合标签，保留外部公开参考和模型推理的底层来源类型。
- 内部依据不足时保留 `evidence_gap`；外部增强意见不替代内部依据，也不关闭 `evidence_gap`。
- 文档 evidence 不改变 `safe_summary`、`draft_recommendation`、`high_risk_engineering_advice`、`contractual_commitment` 与 `production_writeback` 的未来权限语义。高风险工程建议、合同承诺和生产写回均保持业务线白箱人工确认前置，最终结论保持未发布。

## 本 phase 之外的运行时事项

真实文档读取、潜在指令识别或处理、查询、索引读取或切换、检索、Prompt 正文、provider 或模型选择和调用、模型 Token、来源类型绑定、外部增强展示、引用生成、输出分类、人工确认、回答发布、生产写回、数据库连接、审计、持久化、Agent、OVH、生产和正式上传均属于后续授权范围。

## 验收与停止条件

- 静态合同完整覆盖任务包 P1 的回答结构、Prompt 版本、内部依据、外部增强、无内部依据策略、模型输出权限、文档 evidence 边界、七类未来越权类别和人工确认门禁。
- 聚焦白箱用例验证合同身份、单一权威、17 个控制引用、文档指令边界、来源语义、输出权限、失败关闭、回退与零运行时边界。
- 本 run 止于 `IDS-STAGE102-P2-GATE`；P2 仍保持未启动。
- 任何真实资料或运行时动作、任何不可回滚 schema 变更、任何跨 Stage 改动或测试原因不明的失败都会停止该 phase。

## 回滚

回滚仅撤回本 P1 的范围说明、静态合同、聚焦用例、机器事实投影、治理路线、生成中文视图与本地回执，返回 Stage101 Review 的本地零运行时状态。冻结任务包、Stage101 P1--P4/Review、真实资料、manifest、证据账本、审计日志、报告、数据库、索引、GitHub、OVH 与应用状态保持原状。
