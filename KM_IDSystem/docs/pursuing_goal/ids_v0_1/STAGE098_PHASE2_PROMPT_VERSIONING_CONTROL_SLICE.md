# Stage098 Phase 2 · Prompt 版本化受控最小切片

## 本轮目标

将冻结 Stage098 P1 的 Prompt 版本化合同投影为可执行的纯内存控制切片。切片以固定、非业务、`reference-only` 标签表达回答合同、查询／索引／版本记录形状、来源类型、外部增强展示、提示注入防护和输出权限门禁。

## 唯一权威与前序

- 冻结 Stage098 任务包是本 P2 范围和验收的唯一来源；Stage098 P1 静态合同与 Stage097 Review 已复审回答合同提供控制边界。
- 来源文档、真实证据账本与业务线白箱人工复核继续承担业务事实权威。本切片不建立第二权威事实源。
- 输入与输出使用 `:control:stage098-p2:` 前缀的 `reference-only` 标签，不包含正文、路径、业务事实、真实查询、真实提示词、真实模型配置、真实 evidence、真实回答或业务结论。

## 固定控制输入与投影

1. 输入固定为 6 条非业务、`reference-only` 控制请求，每条 23 个字段。场景覆盖内部依据与外部增强、无内部依据、检索文档提示注入拒绝、高风险工程建议、合同承诺和生产写回。
2. 每条请求以控制引用记录 `query_ref`、`index_version_ref`、`prompt_version_ref`、`model_provider_ref`、`model_version_ref`、`temperature_ref`、`retrieval_context_ref` 与 `selected_evidence_ref`。这些字段是未来记录形状，不触发查询、检索、版本选择、提示词执行、模型调用或 evidence 选择。
3. 输出固定为 4 组纯内存控制投影：Prompt 版本化与回答合同绑定、版本与所选 evidence 记录、来源类型与外部增强展示、提示注入与输出权限。每条请求固定 41 个投影字段，共 246 个控制检查点。
4. 外部公开参考与模型推理在展示层共同形成 `external_augmentation_display_ref`；底层保持 `external_public_reference` 与 `model_reasoning` 两个来源类型，并与 `internal_evidence`、`evidence_gap` 保持分离。展示层聚合不改变底层来源类型。
5. 检索文档保持 evidence 身份，IDS 规则保持优先级。提示注入控制状态保持拒绝或人工复核前置。高风险工程建议、合同承诺和生产写回保持业务线白箱人工确认，最终结论保持未发布。

## 失败关闭与运行边界

- 输入只接受模块自身生成的六条固定控制请求。字段形状、场景或控制标签改变时返回 `CONTROL_INPUT_MISMATCH`，并产生零条投影。
- 来源类型分配规则、真实版本治理、真实查询、检索、提示词、模型、引用、证据选择、人工确认与业务结论继续等待业务线白箱 owner 的后续授权。
- 真实资料、原始元数据、fixture、manifest、检索、证据账本、回答、报告、数据库、模型 Token、Agent、OVH、生产、正式上传和推送保持后续授权范围。

## 验收、回退与下一门

本 P2 验收固定控制形状、查询／索引／版本／所选 evidence 记录形状、来源类型分离、外部增强展示映射、提示注入防护、三类高风险输出人工确认、失败关闭、全零运行计数、机器事实投影和中文生成视图的一致性。回退只撤回本 P2 的说明、纯内存控制切片、合同、聚焦用例、machine run、机器事实投影、治理路线、生成中文视图与本交接，恢复到 `PHASE1_PROMPT_VERSIONING_RUNTIME_DISABLED`。Stage098 P1、Stage097 Review、冻结任务包、真实资料、manifest、检索、evidence ledger、audit log、回答、报告、数据库、GitHub、OVH 和应用状态保持原状。下一步仅可在新的独立 run 进入 `IDS-STAGE098-P3-GATE`。
