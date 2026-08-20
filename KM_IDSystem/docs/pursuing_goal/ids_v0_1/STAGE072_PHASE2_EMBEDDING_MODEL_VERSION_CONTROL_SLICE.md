# STAGE-072 Phase 2：Embedding 模型版本纯内存控制切片

## 当前结论

`IDS-V0_1-STAGE072-P2` 只把冻结任务包和 P1 已冻结的字段、策略继承、队列、缓存、成本与审计边界，机械投影为五条固定、非业务、`reference-only` 的内存控制请求。它不读取任何 data source、document、chunk、摘要或正文；所有 `provider_ref`、`model_ref`、`model_version`、`dimension`、`created_at`、`chunk_id` 都是不透明的 `:control:` 标签，不是业务事实或真实运行时记录。

来源文档和业务线白箱人工复核仍是唯一权威。本切片不建立第二权威事实源，也不能替代来源文档、形成自动业务建议或允许策略例外。

## P2 实现的最小控制范围

- 机械解析 `data source → document → chunk` 的三档外部 API 策略：默认 `denied`；document 只能收紧，不能放宽；chunk 不接受人工逐条赋值；
- 内存投影五条未来 Embedding 队列、缓存、失败重试、零值成本和六字段模型版本控制记录；它们不会被持久化、调度或执行；
- 每条控制审计投影固定保留受控 `provider_ref`、`model_ref`、`token_count=0`、`chunk_id` 和 `policy_inheritance_reason`，并在未来 provider 调用前要求审计、预算和业务线白箱人工复核；
- `denied` 阻断外发及运行时队列/缓存/模型版本记录；未授权 chunk 不会外发；`summary_only` 只保留未来授权摘要引用；`full_text_allowed` 也只保留未来授权文本块引用。切片永远不创建外发载荷，也不调用外部 API。

## 本步骤明确不做

- 不读取、打开、复制、解析、总结、保留、外发、删除、修改或写入真实资料、原始元数据、fixture、摘要、文本块、chunk、manifest、evidence ledger、audit log 或已交付报告；
- 不选择 provider 或模型，不读取凭据，不记录真实模型版本、维度、创建时间、外发状态、Token、成本或预算；不执行成本估算、预算查找、队列、缓存、失败重试、审计、索引、数据库、持久化、外部 API、模型、Agent、OVH 或生产；
- 不进入 P3/P4、整阶段复审、批次复审、GitHub 上传、推送或部署。

## 验证与回滚

聚焦测试只验证固定输入的完全匹配、策略继承和失败关闭、队列/缓存/模型版本/审计控制形状、中文反馈及零运行时标志。回滚只撤回本 P2 范围说明、控制合同、纯内存模块、聚焦测试、本地 run、事件、机器事实、治理路线和生成中文视图，恢复到 `PHASE1_EMBEDDING_MODEL_VERSION_CONTRACT_RUNTIME_DISABLED`；不会改变 P1、Stage071 Review、冻结任务包、真实资料、manifest、evidence ledger、audit log、数据库、GitHub、OVH 或应用状态。

下一步仅可在新的独立 run 进入 `IDS-STAGE072-P3-GATE`。
