# Stage101 · RAG 可复现整阶段机械复审

## 目标与入口

- 任务：`IDS-V0_1-STAGE101-REVIEW`
- 入口门禁：`IDS-STAGE101-REVIEW-GATE`
- 后续门禁：`IDS-STAGE102-P1-GATE`
- 冻结输入：Stage101 任务包、Stage101 P1--P4 控制工件，以及 Stage100 Review 已验收控制工件。

本 Review 只机械重放既有控制合同和控制报告，确认八元可复现记录键、来源类型分离、提示注入防护、模型输出权限、业务线白箱人工确认、失败关闭和 P4→P3 回退保持一致。复审结论只描述冻结控制工件，不建立第二权威事实源，也不改写为业务事实。

## 固定复审形状

| 前序阶段 | 固定复审内容 |
| --- | --- |
| P1 | `15/4/5/5/3/22/4`：15 个回答与可复现控制引用、4 类底层来源类型、5 个回答结构段、5 类输出、3 类高风险输出、22 类失败关闭、4 条中文反馈 |
| P2 | `6×23/4/45/270`：6 条控制请求、23 个输入字段、4 组投影、每条 45 个字段、270 个控制检查点 |
| P3 | `6×32=192/5/6/16`：6 条场景、每条 32 个字段、192 个检查点、5 个控制视图、6 条人工处理要求、16 类失败关闭 |
| P4 | `6/6/6/6/6/2`、`17/12/14/17/12/12`、456 个交付检查点、4 条中文反馈、16 类失败关闭 |

八元记录键固定为 query、index_version、prompt_version、model_provider、model_version、temperature、retrieval_context 与 selected_evidence 的控制引用。回答样例和可复现日志只保存该固定形状，不处理真实查询、提示词、检索结果或回答。

## 权威与运行时边界

- 来源文档与业务线白箱人工复核继续承担唯一业务事实权威；内部依据不足始终保留为 `evidence_gap`，外部公开参考和模型推理组成的 `external_augmentation_opinion` 仅为展示标签。
- 检索文档始终是 evidence，IDS 规则保持优先级；不可信文档指令保持拒绝状态。
- 高风险工程建议、合同承诺和生产写回保持业务线白箱人工处理，人工确认未记录，最终结论未发布。
- 本 Review 只在内存中生成控制报告。真实资料、原始元数据、fixture、查询、检索、提示词、模型、模型 Token、Agent、OVH、生产、持久化、正式全局上传和推送均不属于本阶段执行范围。

## 失败关闭与停止条件

- P1、P2、P3 或 P4 的合同、固定形状、八元记录键、来源类型、提示注入、白箱人工处理、回退前置或零运行时边界出现漂移时，复审报告保持失败关闭并停在 `IDS-STAGE101-REVIEW-GATE`。
- 读取或写入任何业务来源、原始元数据、manifest、检索结果、提示词正文、回答、真实证据账本、审计日志、报告、数据库或物理索引时停止。
- 出现实际模型 Token、Agent、OVH、生产、持久化、GitHub 上传或 Stage102 启动信号时停止。

## 验收与回滚

- 聚焦验证命令：`python3 -B -m unittest -q KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.test_stage101_rag_reproducibility_stage_review`
- 验收证据由复审合同、纯内存模块、聚焦用例、机器回执、治理事件和中文机器平面共同构成；它们只证明冻结控制工件和零运行时边界。
- 回滚仅撤回本 Review 的说明、静态合同、纯内存复审模块、聚焦用例、回执、治理投影与中文机器平面，返回 P4 的 `PASS_RAG_REPRODUCIBILITY_DELIVERY_EVIDENCE_RUNTIME_DISABLED`。Stage101 P1--P4、Stage100 Review、冻结任务包、受保护资料、`main`、release、OVH 与应用状态保持原状。

Stage102 只开放 `IDS-STAGE102-P1-GATE`，并由下一次独立 run 处理。
