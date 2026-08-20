# STAGE-075 Phase 1：外部 API 覆盖授权审计的范围、输入输出与边界确认

## 当前结论

本步骤只定义 `IDS-V0_1-STAGE075-P1` 的静态外部 API 覆盖授权审计工程合同。唯一合同上下文是冻结
Stage075 任务包、已完成的 Stage074 Review、Stage074 P1 静态合同及其已提交的策略继承、队列、成本、
模型版本与审计控制形状。默认 `external_api_policy=denied`；策略只能是 `denied`、`summary_only` 或
`full_text_allowed`，并由 data source/document 自动继承到 chunk。owner 不需要、也不得逐条标记 chunk。
来源文档与业务线白箱人工复核仍是唯一权威，本合同不建立第二权威事实源。

## P1 允许的静态定义

- 定义未来外部 API 覆盖授权审计路线：默认 `denied`、三档策略、data source/document 到 chunk 的自动继承、
  document 只能收紧及未知策略失败关闭；不读取来源正文、不创建请求或持久记录；
- 定义未来 Embedding 队列、缓存、失败重试、成本治理、模型版本和外部 API 审计字段形状；所有字段仅为 schema
  标签，不含真实资料、provider、model、时间、Token、金额或外发事实值；
- 定义 owner 将来强制放宽外发策略时必须在策略生效前具备 `actor`、`reason`、`old_value`、`new_value` 四字段
  审计合同；该合同只表达未来前置条件，当前不创建审计日志、不改变任何策略或资料；
- 定义 `denied`、`summary_only`、`full_text_allowed` 的未来操作边界、失败关闭、克制的中文企业反馈，以及从
  Stage075 P1 回到 Stage074 Review 的可逆范围。

## 本步骤明确不做

- 不读取、打开、解析、总结、复制、外发或写入真实资料、原始元数据、授权 fixture、摘要、文本块、chunk、
  manifest、evidence ledger、audit log 或已交付报告；
- 不选择或下载 provider/模型，不创建或执行 Embedding、Embedding 队列、缓存、失败重试、成本估算、预算查找、
  模型版本记录、审计记录、外部 API、模型 Token、索引、数据库、持久状态或 Agent；
- 不进入 Stage075 P2/P3/P4、整阶段复审、批次复审、OVH、生产、GitHub 上传或推送。

## 验证与回滚

聚焦测试只验证冻结任务包、Stage074 Review、前序控制合同、默认策略、自动继承、未来队列/成本/模型/审计形状、
owner 强制允许时的四字段审计前置、失败关闭和机器事实投影是否一致；它不执行外部 API 行为，也不产生日志。
回滚只撤回本 P1 的范围说明、静态合同、聚焦测试、本地 run、事件、治理投影和生成中文视图，恢复到
`LOCAL_STAGE074_REVIEWED_LOCAL_EMBEDDING_FALLBACK_RUNTIME_DISABLED`；不影响 Stage074 Review 证据、真实资料、
manifest、evidence ledger、audit log、数据库、GitHub、OVH 或应用状态。

下一步仅可在新的独立 run 进入 `IDS-STAGE075-P2-GATE`。
