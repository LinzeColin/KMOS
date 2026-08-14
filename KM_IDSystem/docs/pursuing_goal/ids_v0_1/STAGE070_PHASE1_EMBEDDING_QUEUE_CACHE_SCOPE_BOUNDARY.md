# STAGE-070 Phase 1：Embedding 队列、缓存与失败重试的范围、输入输出和边界确认

## 当前结论

本步骤只定义 `IDS-V0_1-STAGE070-P1` 的静态工程合同。它继承已完成的 Stage069 外部 API
策略合同：默认 `external_api_policy=denied`，策略只可为 `denied`、`summary_only` 或
`full_text_allowed`，并由 data source/document 自动继承到 chunk；owner 不需要、也不得逐条标记
chunk。本合同不建立第二权威事实源，来源文档和业务线白箱人工复核仍是唯一权威。

## P1 允许的静态定义

- 17 个仅引用的未来队列/缓存/重试输入字段，不含来源正文、摘要正文、文本块、真实路径或 URI；
- 12 个未来 Embedding 队列字段、10 个未来缓存字段、7 个未来失败重试字段；
- 8 个未来成本与模型版本字段，以及 18 个未来外部 API 审计字段；
- 三档策略的关闭流程：`denied` 不形成外发载荷、队列、缓存或重试；`summary_only` 仅保留未来已授权摘要引用；`full_text_allowed` 也只能在未来已授权、预算和审计门完成后使用文本块；
- 12 类失败关闭、中文企业反馈和从 Stage070 P1 回到 Stage069 Review 的可逆边界。

上述字段只是不含业务内容的 schema 标签，不是队列、缓存、重试、成本、模型版本、审计记录或
业务事实。预算未知或不足必须关闭；未来 provider 调用前必须具备业务线白箱人工复核、授权、预算和
审计字段。

## 本步骤明确不做

- 不读取、打开、解析、总结、复制、外发或写入真实资料、原始元数据、授权 fixture、摘要、文本块、chunk、manifest、evidence ledger、audit log 或已交付报告；
- 不创建或执行队列、缓存、失败重试、成本计算、模型版本记录、审计记录、provider/模型选择、外部 API、模型 Token、索引、数据库、持久状态或 Agent；
- 不进入 Stage070 P2/P3/P4、整阶段复审、批次复审、OVH、生产、GitHub 上传或推送。

## 验证与回滚

聚焦测试只验证静态合同、冻结任务包、Stage069 已复审边界、路线图、上传锁和机器事实投影是否一致。
回滚只撤回本 P1 的范围说明、静态合同、聚焦测试、本地 run、事件、治理投影和生成中文视图，恢复到
`STAGE069_REVIEWED_LOCAL_EXTERNAL_API_POLICY_RUNTIME_DISABLED`；不影响 Stage069 复审证据、真实资料、
manifest、evidence ledger、audit log、数据库、GitHub、OVH 或应用状态。

下一步仅可在新的独立 run 进入 `IDS-STAGE070-P2-GATE`。
