# STAGE-072 Phase 3：Embedding 模型版本专项验证

## 当前结论

IDS-V0_1-STAGE072-P3 仅重放 P2 的五条固定、非业务、reference-only 控制记录，验证策略继承后的外发边界、预算暂停和审计前置。它验证的是未来外发候选的控制条件，而不是实际外发：所有 data source、document、chunk、provider、model、model_version、dimension、created_at、Token 与审计字段均是不透明的 :control: 引用或零值。

来源文档和业务线白箱人工复核继续是唯一权威。本步骤不建立第二权威事实源，场景报告、模型版本控制投影或审计投影不能替代来源文档、形成业务事实或自动业务建议。

## P3 专项验证范围

- denied 形成无外发引用的显式阻断结果，并阻断队列、缓存、失败重试和模型版本运行时记录；
- summary_only 只保留未来授权摘要引用；来源允许全文但 document 收紧为摘要时，仍不得升级为文本块引用；
- full_text_allowed 只保留未来授权文本块引用；它仍未创建文本载荷、队列、模型版本或外部调用；
- 预算不足时，外部 API 候选在队列、缓存和重试三个控制面同时暂停；
- 五条控制场景均要求完整 18 字段审计控制投影。三个未来外部调用候选均先具备 policy reason、provider/model 引用、token_count=0、chunk_id、队列引用和预算状态。

## 本步骤明确不做

- 不读取、打开、复制、解析、总结、保留、外发、删除、修改或写入真实资料、原始元数据、fixture、摘要、文本块、chunk、manifest、evidence ledger、audit log 或已交付报告；
- 不选择 provider 或模型，不读取凭据，不记录真实模型版本、维度、创建时间、外发状态、Token、成本或预算；不执行成本估算、预算查找、队列、缓存、失败重试、审计、索引、数据库、持久化、外部 API、模型、Agent、OVH 或生产；
- 不进入 P4、整阶段复审、批次复审、GitHub 上传、推送或部署。

## 验证、停止与回滚

聚焦测试重放 P2 固定输入，并验证五类场景次序、策略边界、预算暂停、审计字段完整性、审计前置和零运行时标志。P2 形状损坏、策略或场景错序、审计缺失、预算未暂停、候选无审计或任何运行时标志为真，均失败关闭且不进入 P4。

回滚只撤回本 P3 范围说明、场景合同、场景模块、聚焦测试、本地 run、事件、机器事实、治理路线和生成中文视图，恢复到 PHASE2_EMBEDDING_MODEL_VERSION_CONTROL_SLICE_RUNTIME_DISABLED；不会改变 P1/P2、Stage071 Review、冻结任务包、真实资料、manifest、evidence ledger、audit log、数据库、GitHub、OVH 或应用状态。

下一步仅可在新的独立 run 进入 IDS-STAGE072-P4-GATE。
