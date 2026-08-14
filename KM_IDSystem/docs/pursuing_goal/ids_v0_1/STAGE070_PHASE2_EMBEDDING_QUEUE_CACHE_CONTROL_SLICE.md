# STAGE-070 Phase 2：Embedding 队列、缓存与审计控制切片

## 目标与范围

本切片仅实现冻结 `STAGE-070` Phase 2 的最小、本地、纯内存控制接线：复用 Stage069 的三档外部 API 策略继承，在五条固定、非业务、reference-only `:control:` 记录上投影未来 Embedding 队列、缓存、失败重试、成本/模型版本与审计字段。

真实来源文档仍是唯一权威；控制记录、策略解析和未来调用候选均不能成为业务事实或决策依据。业务线策略例外必须经过白箱人工复核。

## 执行合同

- 输入固定为五条 17 字段控制引用，拒绝额外字段、调换顺序或篡改内容。
- 策略从 data source 经 document 自动继承到 chunk；未知值、无效值或 document 放宽来源策略均失败关闭为 `denied`。
- 队列、缓存、重试分别保持 P1 的 `12/10/7` 字段形状；成本/模型版本和审计分别保持 `8/18` 字段形状。
- `denied` 关闭队列、缓存、重试；预算不足仅投影暂停；其余控制候选为 eligible but not persisted / not scheduled。
- provider、model、model_version、chunk_ref 和审计引用都只是固定控制标签；Token 与成本均为零值投影。

## 禁止路径与停止条件

本切片不读取或保留来源正文、摘要正文、chunk 文本、物理路径或真实 URI；不创建真实队列、缓存、重试、成本、模型版本或审计记录；不读取凭据，不选择 provider/模型，不初始化客户端，不调用外部 API，不消耗模型 Token，不写索引、数据库或持久状态，不运行 Agent，不部署 OVH，不启用生产，也不上传或推送。

若输入非固定控制形状、策略缺失/无效、document 放宽来源策略、策略拒绝、预算不足或未来审计前置字段无法满足，则保持关闭并停在 `IDS-STAGE070-P3-GATE` 前。P3 不属于本 run。

## 可恢复与回滚

撤回仅限本说明、P2 切片模块、P2 合同、聚焦测试、machine run、事件、机器事实、路线和生成中文投影，返回 `PHASE1_EMBEDDING_QUEUE_AND_CACHE_CONTRACT_RUNTIME_DISABLED`。不修改 P1、Stage069 及更早证据、冻结任务包、真实资料、manifest、evidence ledger、audit log、数据库、GitHub、OVH 或应用状态。
