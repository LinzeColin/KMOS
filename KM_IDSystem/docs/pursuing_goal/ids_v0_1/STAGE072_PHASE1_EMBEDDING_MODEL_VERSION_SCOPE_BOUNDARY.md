# STAGE-072 Phase 1：Embedding 模型版本的范围、输入输出与边界确认

## 当前结论

本步骤只定义 `IDS-V0_1-STAGE072-P1` 的静态工程合同。它只引用已完成的
Stage071 Review 与 Stage071 P1 成本治理合同：默认 `external_api_policy=denied`，策略只可为 `denied`、`summary_only` 或
`full_text_allowed`，并由 data source/document 自动继承到 chunk；owner 不需要、也不得逐条
标记 chunk。来源文档与业务线白箱人工复核仍是唯一权威，本合同不建立第二权威事实源。

## P1 允许的静态定义

- 六个未来模型版本记录字段：`provider_ref`、`model_ref`、`model_version`、
  `dimension`、`created_at`、`sent_to_external_api`；它们只是 schema 标签，
  不含 provider、模型、维度、时间或外发事实值；
- 复用 Stage071 的三档外部 API 策略、未来队列/缓存/重试、成本治理和审计前置；
- `denied` 不形成外发、队列、缓存、重试、模型版本或审计记录；
  `summary_only` 只保留未来已授权摘要引用；`full_text_allowed` 也只能在未来已授权、
  全部预算门、审计字段和业务线白箱人工复核完成后使用文本块；
- 九类失败关闭、克制的中文企业反馈，以及从 Stage072 P1 回到 Stage071 Review 的可逆边界。

## 本步骤明确不做

- 不读取、打开、解析、总结、复制、外发或写入真实资料、原始元数据、授权 fixture、摘要、文本块、
  chunk、manifest、evidence ledger、audit log 或已交付报告；
- 不创建或执行模型版本记录、维度记录、外发状态、成本估算、预算查找、队列、缓存、失败重试、
  审计记录、provider/模型选择、外部 API、模型 Token、索引、数据库、持久状态或 Agent；
- 不进入 Stage072 P2/P3/P4、整阶段复审、批次复审、OVH、生产、GitHub 上传或推送。

## 验证与回滚

聚焦测试只验证冻结任务包、Stage071 Review、Stage071 P1 合同、静态模型版本字段、策略流程、
失败关闭和机器事实投影是否一致。回滚只撤回本 P1 的范围说明、静态合同、聚焦测试、本地 run、
事件、治理投影和生成中文视图，恢复到
`LOCAL_STAGE071_REVIEWED_EMBEDDING_COST_GOVERNOR_RUNTIME_DISABLED`；不影响 Stage071
证据、真实资料、manifest、evidence ledger、audit log、数据库、GitHub、OVH 或应用状态。

下一步仅可在新的独立 run 进入 `IDS-STAGE072-P2-GATE`。
