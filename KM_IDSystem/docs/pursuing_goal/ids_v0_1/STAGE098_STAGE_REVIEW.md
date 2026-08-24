# Stage098 Prompt 版本化整阶段机械复审

本复审只机械确认 Stage098 P1--P4 的冻结 Prompt 版本化控制工件：未来版本化配置引用、回答与来源边界、Prompt 版本化控制切片、提示注入防护、异常场景、交付证据、模型输出权限、失败关闭、业务线白箱人工处理和 P4→P3 回退保持一致。

来源文档、真实证据账本和业务线白箱人工复核继续承担业务事实权威。复审不建立第二权威事实源，复审结果是控制报告，不承载真实资料、提示词、回答、业务事实、证据内容或业务结论。

## 固定复审形状

| 层级 | 固定形状 | 复审重点 |
| --- | --- | --- |
| P1 | 5/3/16 | 五个未来 Prompt／模型配置引用、三类高风险输出和十六类失败关闭 |
| P2 | 6×23 输入、4 组投影、每条 41、合计 246 | 查询、索引、Prompt、模型 provider／版本、temperature、检索上下文、所选 evidence、来源类型、提示注入和输出权限的 reference-only 控制投影 |
| P3 | 6×31=186、5 个控制视图、6 条人工处理、15 类失败关闭 | 外部增强来源类型、evidence_gap、检索文档提示注入与三类高风险输出 |
| P4 | 6/6/6/6/6/2、17/12/14/15/12/12、444、4 条中文反馈、16 类失败关闭 | 回答样例、负向结果、版本记录、可复现日志、模型输出权限和 P4→P3 回退 |

检索文档保持 evidence 身份并保持 IDS 规则优先；无内部依据保持 evidence_gap；外部增强保留内部依据、外部公开参考、模型推理与依据缺口的来源类型分离；高风险工程建议、合同承诺和生产写回保持业务线白箱人工确认，最终结论保持未发布。

## 失败关闭与运行边界

任一 P1--P4 合同、控制报告、固定形状、控制引用、单一权威、来源类型、提示注入防护、输出权限、业务线白箱边界、失败关闭、P4→P3 回退或零运行时边界发生漂移，复审结果保持 FAIL_REVIEWED_PROMPT_VERSIONING_RUNTIME_DISABLED，下一门禁保持 IDS-STAGE098-REVIEW-GATE。

本复审只处理本地控制工件。真实资料、原始元数据、manifest、检索结果、真实提示词、真实回答、证据账本、审计日志、报告、数据库、物理索引、实际查询、检索、提示词、模型、模型 Token、人工确认、回答发布、生产写回、prompt 回滚、模型配置回退、Agent、OVH、生产和正式全局上传保持后续授权边界。

## 验证与回滚

聚焦验证命令：

    python3 -B -m unittest -q KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.test_stage098_prompt_versioning_stage_review

复审通过只开放 IDS-STAGE099-P1-GATE，Stage099 保持未启动。本阶段回滚只撤回本说明、Review 合同、纯内存模块、聚焦用例、local receipt、治理投影和生成中文视图，恢复到 PASS_PROMPT_VERSIONING_DELIVERY_EVIDENCE_RUNTIME_DISABLED。Stage098 P1--P4、Stage097 Review、冻结任务包、受保护资料、真实证据账本、GitHub main/release、OVH 与应用状态保持原状。
