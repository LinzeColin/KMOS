# STAGE-074 Phase 1：本地 Embedding 兜底的范围、输入输出与边界确认

## 当前结论

本步骤只定义 IDS-V0_1-STAGE074-P1 的静态本地 Embedding 兜底工程合同。它只引用冻结
Stage074 任务包、已完成的 Stage073 Review，以及 Stage069--073 已提交的策略继承、队列、
成本治理、模型版本与审计控制合同。默认 external_api_policy=denied；策略只能是 denied、
summary_only 或 full_text_allowed，并由 data source/document 自动继承到 chunk。owner 不需要、
也不得逐条标记 chunk。来源文档与业务线白箱人工复核仍是唯一权威，本合同不建立第二权威事实源。

## P1 允许的静态定义

- 定义未来本地 Embedding 兜底路线：它只表示商业化时可进一步实施的本地路径，不选择
  provider 或模型，不读取来源正文，也不启动本地 Embedding、索引或持久化；
- 固定默认 denied、三档外部 API 策略、data source/document 到 chunk 的自动继承，以及
  owner 不逐条标记 chunk 的边界；
- 固定未来 Embedding 队列、缓存、失败重试、成本治理、模型版本和 18 字段外部 API 审计
  形状；所有字段只作为 schema 标签，不含真实资料、provider、模型、时间、Token、金额或
  外发事实值；
- 固定 denied、summary_only、full_text_allowed 的未来操作边界、失败关闭、克制的中文企业
  反馈，以及从 Stage074 P1 回到 Stage073 Review 的可逆范围。

## 本步骤明确不做

- 不读取、打开、解析、总结、复制、外发或写入真实资料、原始元数据、授权 fixture、摘要、
  文本块、chunk、manifest、evidence ledger、audit log 或已交付报告；
- 不选择或下载本地 provider/模型，不创建或执行本地 Embedding、Embedding 队列、缓存、失败
  重试、成本估算、预算查找、模型版本记录、审计记录、provider/模型选择、外部 API、模型
  Token、索引、数据库、持久状态或 Agent；
- 不进入 Stage074 P2/P3/P4、整阶段复审、批次复审、OVH、生产、GitHub 上传或推送。

## 验证与回滚

聚焦测试只验证冻结任务包、Stage073 Review、前序控制合同、未来本地兜底路线、三档外部策略、
队列/成本/模型/审计形状、失败关闭和机器事实投影是否一致；它不执行 Embedding 或外部 API
行为，也不产生日志。回滚只撤回本 P1 的范围说明、静态合同、聚焦测试、本地 run、事件、治理
投影和生成中文视图，恢复到 LOCAL_STAGE073_REVIEWED_EMBEDDING_AUDIT_TEST_RUNTIME_DISABLED；
不影响 Stage073 Review 证据、真实资料、manifest、evidence ledger、audit log、数据库、
GitHub、OVH 或应用状态。

下一步仅可在新的独立 run 进入 IDS-STAGE074-P2-GATE。
