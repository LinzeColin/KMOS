# STAGE-071 Phase 1：Embedding 成本治理器的范围、输入输出与边界确认

## 当前结论

本步骤只定义 IDS-V0_1-STAGE071-P1 的静态工程合同。它复用已复审的 Stage070
Embedding 队列、缓存、失败重试、成本与审计字段，以及 Stage069 的外部 API 策略继承：
默认 external_api_policy=denied，策略只可为 denied、summary_only 或
full_text_allowed，并由 data source/document 自动继承到 chunk；owner 不需要、也不得逐条
标记 chunk。本合同不建立第二权威事实源，来源文档和业务线白箱人工复核仍是唯一权威。

## P1 允许的静态定义

- 16 个仅引用的未来成本治理输入字段，不含来源正文、摘要正文、文本块、真实路径、URI、Token
  或金额；
- 16 个未来成本治理字段，覆盖本批次估算、月预算和单任务上限的三重关闭检查；
- 复用 Stage070 的 8 个成本/模型版本字段和 18 个未来外部 API 审计字段；
- 三档策略的关闭流程：denied 不形成外发载荷、队列、缓存、重试或成本治理任务；
  summary_only 只保留未来已授权摘要引用；full_text_allowed 也只能在未来已授权、三重预算
  检查、审计字段和业务线白箱人工复核完成后使用文本块；
- 14 类失败关闭、中文企业反馈和从 Stage071 P1 回到 Stage070 Review 的可逆边界。

上述字段只是不含业务内容的 schema 标签，不是预算配置、金额、Token、成本估算、队列、缓存、
审计记录或业务事实。任一批次估算、月预算或单任务上限未知、不足或超限时必须关闭；未来 provider
调用前必须具备策略授权、全部三重预算检查、模型/版本字段、审计字段和业务线白箱人工复核。

## 本步骤明确不做

- 不读取、打开、解析、总结、复制、外发或写入真实资料、原始元数据、授权 fixture、摘要、文本块、
  chunk、manifest、evidence ledger、audit log 或已交付报告；
- 不创建或执行成本估算、预算查找、单任务上限判断、队列、缓存、失败重试、模型版本记录、审计记录、
  provider/模型选择、外部 API、模型 Token、索引、数据库、持久状态或 Agent；
- 不进入 Stage071 P2/P3/P4、整阶段复审、批次复审、OVH、生产、GitHub 上传或推送。

## 验证与回滚

聚焦测试只验证静态合同、冻结任务包、Stage070 已复审边界、路线图、历史上传锁和机器事实投影是否
一致。回滚只撤回本 P1 的范围说明、静态合同、聚焦测试、本地 run、事件、治理投影和生成中文视图，
恢复到 STAGE070_REVIEWED_LOCAL_EMBEDDING_QUEUE_CACHE_RUNTIME_DISABLED；不影响 Stage070
复审证据、真实资料、manifest、evidence ledger、audit log、数据库、GitHub、OVH 或应用状态。

下一步仅可在新的独立 run 进入 IDS-STAGE071-P2-GATE。
