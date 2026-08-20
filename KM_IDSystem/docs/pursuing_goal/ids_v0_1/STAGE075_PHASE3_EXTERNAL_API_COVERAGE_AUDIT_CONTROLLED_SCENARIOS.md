# STAGE-075 Phase 3：外部 API 覆盖授权审计专项验证与异常场景

## 当前结论

`IDS-V0_1-STAGE075-P3` 只重放 P2 的五条固定、非业务、`:control:` 外部 API 覆盖授权审计控制投影，验证默认 `denied`、`summary_only`、`full_text_allowed`、document 收紧、预算不足暂停、十九字段审计前置和 owner 强制允许外发的四字段前置。它验证的是未来外部 API 候选的控制条件，不是实际外发、模型调用或审计写入；所有引用均为不透明 `:control:` 标签，Token 与成本固定为零。

来源文档与业务线白箱人工复核继续是唯一权威。P3 场景报告、队列/缓存/重试、成本、模型版本、覆盖审计或 owner 例外前置控制投影均不能成为业务事实、替代来源文档或生成自动业务建议。

## P3 专项验证范围

- `denied` 产生无外发引用的显式阻断，并同步阻断队列、缓存和失败重试；
- `summary_only` 只保留未来授权摘要引用；source 允许全文但 document 收紧时，仍不得升级为文本块引用；
- `full_text_allowed` 只保留未来授权文本块引用；它不创建正文载荷、队列、模型版本、索引或外部调用；
- 预算不足时，外部 API 候选在队列、缓存和重试三个控制面同时暂停；
- 五条场景均要求完整十九字段审计控制投影，共进行九十五次字段检查。三个未来调用候选均在授权、预算、policy reason、provider/model 引用、`token_count=0`、不透明 `chunk_id` 引用和业务线白箱人工复核前置下停留为候选；owner 强制允许外发仍独立受 `actor`、`reason`、`old_value`、`new_value` 四字段前置约束，未创建策略变更。

## 本步骤明确不做

- 不读取、打开、复制、解析、总结、保留、外发、删除、修改或写入真实资料、原始元数据、fixture、摘要、文本块、chunk、manifest、evidence ledger、audit log 或已交付报告；
- 不选择或下载 provider/模型，不读取凭据，不执行 Embedding、索引、成本估算、预算查询、队列、缓存、失败重试、审计写入或查询、数据库、持久化、外部 API、模型、Agent、OVH 或生产；
- 不进入 P4、整阶段复审、批次复审、GitHub 上传、推送或部署。

## 验证、停止与回滚

聚焦测试重放 P2 固定输入，并验证五类场景次序、策略外发边界、预算暂停、十九字段审计完整性、owner 四字段前置和零运行时标志。P2 形状损坏、场景或策略错序、审计或 owner 前置缺失、预算未暂停、未来调用候选缺少审计前置或任何运行时标志为真，均失败关闭且不进入 P4。

回滚只撤回本 P3 范围说明、场景合同、场景模块、聚焦测试、本地 run、事件、机器事实、治理路线和生成中文视图，恢复到 `PHASE2_EXTERNAL_API_COVERAGE_AUDIT_CONTROL_SLICE_RUNTIME_DISABLED`；不会改变 P1/P2、Stage074 Review、冻结任务包、真实资料、manifest、evidence ledger、audit log、数据库、GitHub、OVH 或应用状态。

下一步仅可在新的独立 run 进入 `IDS-STAGE075-P4-GATE`。
