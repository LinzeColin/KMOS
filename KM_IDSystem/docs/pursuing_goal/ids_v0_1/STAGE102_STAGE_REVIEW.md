# Stage102 · 文档内提示注入防护整阶段机械复审

## 目标与入口

- 任务：`IDS-V0_1-STAGE102-REVIEW`
- 入口门禁：`IDS-STAGE102-REVIEW-GATE`
- 后续门禁：`IDS-STAGE103-P1-GATE`
- 冻结输入：Stage102 任务包、Stage102 P1--P4 控制工件，以及 Stage101 Review 已验收 RAG 可复现控制工件。

本 Review 只机械复审既有的静态合同和纯内存控制报告，确认文档 evidence 边界、IDS 规则优先级、来源类型分离、输出权限、业务线白箱人工处理、失败关闭和 P4→P3 回退保持一致。复审报告只描述冻结控制工件，不建立第二权威事实源；来源文档与业务线白箱人工复核继续承担业务事实权威。

## 固定复审形状

| 前序阶段 | 固定复审内容 |
| --- | --- |
| P1 | `17/7/4/5/25/4`：17 个控制引用、7 类不可信文档指令类别、4 类底层来源类型、5 类输出权限、25 类失败关闭、4 条中文反馈 |
| P2 | `7×28/4/50/350`：7 条固定控制请求、28 个输入字段、4 组投影、每条 50 个字段、350 个控制检查点 |
| P3 | `7×34=238/5/7/27`：7 条场景、每条 34 个字段、238 个检查点、5 个控制视图、7 条业务线白箱处理要求、27 类失败关闭 |
| P4 | `7/7/7/7/7/2`、`17/12/14/17/12/12`、528 个交付检查点、4 条中文反馈、16 类失败关闭 |

P4 的回答样例与可复现日志只保留 query、index_version、prompt_version、model_version、selected_evidence、document_evidence、document_instruction_candidate 与 IDS rule 的八元控制引用。它们不读取真实查询、文档正文、提示词、检索结果、回答或日志。

## 权威与运行时边界

- 文档 evidence 与文档内潜在指令保持不可信、不可执行的控制引用；IDS 规则保持优先级。
- 内部依据不足保持 `evidence_gap`；`external_augmentation_opinion` 只作为展示标签并保留外部公开参考与模型推理的底层来源类型。
- 高风险工程建议、合同承诺和生产写回保持业务线白箱人工处理，人工确认未记录，最终结论未发布。
- 本 Review 只在内存中构造控制报告。真实资料、原始元数据、fixture、查询、检索、提示词、模型、模型 Token、Agent、OVH、生产、持久化、正式全局上传和推送不属于本阶段执行范围。

## 失败关闭与停止条件

- P1、P2、P3 或 P4 的身份、固定形状、控制引用、文档内提示注入边界、来源语义、输出权限、白箱人工处理、回退前置或零运行时边界发生漂移时，Review 报告保持失败关闭并停在 `IDS-STAGE102-REVIEW-GATE`。
- 对业务来源、原始元数据、manifest、文档正文、检索结果、提示词正文、回答、证据账本、审计日志、报告、数据库或物理索引的访问或写入会终止本阶段。
- 出现实际模型 Token、Agent、OVH、生产、持久化、GitHub 上传或 Stage103 启动信号时，Review 保持失败关闭。

## 验收与回滚

- 聚焦验证命令：`python3 -B -m unittest -q KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.test_stage102_document_prompt_injection_defense_stage_review`
- 验收证据由 Review 合同、纯内存模块、聚焦用例、机器回执、治理事件和中文机器平面共同构成；它们只证明冻结控制工件和零运行时边界。
- 回滚仅撤回本 Review 的说明、静态合同、纯内存复审模块、聚焦用例、回执、治理投影与中文机器平面，返回 P4 的 `PASS_DOCUMENT_PROMPT_INJECTION_DEFENSE_DELIVERY_EVIDENCE_RUNTIME_DISABLED`。Stage102 P1--P4、Stage101 Review、冻结任务包、受保护资料、`main`、release、OVH 与应用状态保持原状。

Stage103 只开放 `IDS-STAGE103-P1-GATE`，并由下一次独立 run 处理。
