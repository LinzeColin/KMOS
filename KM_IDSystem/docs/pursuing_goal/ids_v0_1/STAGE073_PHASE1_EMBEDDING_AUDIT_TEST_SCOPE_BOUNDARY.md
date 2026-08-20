# STAGE-073 Phase 1：Embedding 审计测试的范围、输入输出与边界确认

## 当前结论

本步骤只定义 `IDS-V0_1-STAGE073-P1` 的静态审计测试工程合同。它只引用冻结
Stage073 任务包、已完成的 Stage072 Review、Stage072 P1 模型版本合同、Stage071 P1
审计字段合同和既有上传锁：默认 `external_api_policy=denied`，策略只可为
`denied`、`summary_only` 或 `full_text_allowed`，并由 data source/document 自动继承到
chunk；owner 不需要、也不得逐条标记 chunk。来源文档与业务线白箱人工复核仍是唯一权威，
本合同不建立第二权威事实源。

## P1 允许的静态定义

- 定义三档策略的未来审计测试预期：`denied` 阻断外发和队列；`summary_only` 仅允许未来
  已授权摘要引用；`full_text_allowed` 只可在未来授权、预算、完整审计字段与业务线白箱人工
  复核完成后处理文本块；
- 固定 data source/document 到 chunk 的策略继承、12 字段未来 Embedding 队列、8 字段
  成本/模型控制、6 字段模型版本和 18 字段外部 API 审计合同；所有字段仅为 schema 标签，
  不含真实资料、provider、模型、时间、Token、金额或外发事实值；
- 固定 7 类失败关闭、克制的中文企业反馈，以及从 Stage073 P1 回到 Stage072 Review 的
  可逆边界；P3 的实际专项验证与任何审计记录创建均明确延后。

## 本步骤明确不做

- 不读取、打开、解析、总结、复制、外发或写入真实资料、原始元数据、授权 fixture、摘要、
  文本块、chunk、manifest、evidence ledger、audit log 或已交付报告；
- 不创建或执行 Embedding 队列、缓存、失败重试、成本估算、预算查找、模型版本记录、审计
  记录、provider/模型选择、外部 API、模型 Token、索引、数据库、持久状态或 Agent；
- 不进入 Stage073 P2/P3/P4、整阶段复审、批次复审、OVH、生产、GitHub 上传或推送。

## 验证与回滚

聚焦测试只验证冻结任务包、前序 Review/控制合同、三档策略、18 字段审计形状、失败关闭
和机器事实投影是否一致；它不执行外部 API 行为，也不产生日志。回滚只撤回本 P1 的范围
说明、静态合同、聚焦测试、本地 run、事件、治理投影和生成中文视图，恢复到
`LOCAL_STAGE072_REVIEWED_EMBEDDING_MODEL_VERSION_RUNTIME_DISABLED`；不影响 Stage072
证据、真实资料、manifest、evidence ledger、audit log、数据库、GitHub、OVH 或应用状态。

下一步仅可在新的独立 run 进入 `IDS-STAGE073-P2-GATE`。
