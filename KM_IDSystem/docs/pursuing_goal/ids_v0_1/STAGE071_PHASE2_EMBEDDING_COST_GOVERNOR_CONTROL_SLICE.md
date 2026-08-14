# STAGE-071 Phase 2：Embedding 成本治理器控制切片

## 目标与范围

本切片只实现冻结 STAGE-071 Phase 2 的最小、本地、纯内存控制接线：在七条固定、
非业务、reference-only control 记录上复用 data source/document 到 chunk 的策略继承，
投影未来 Embedding 队列、缓存、失败重试、三重预算关闭、成本/模型版本和审计字段。

来源文档仍是唯一权威；控制记录、预算状态、策略解析、成本字段和未来调用候选均不能成为
业务事实或决策依据。业务线策略例外必须经过白箱人工复核。

## 执行合同

- 输入固定为七条 16 字段控制引用，拒绝额外字段、调换顺序或篡改内容。
- 策略从 data source 经 document 自动继承到 chunk；默认 denied，未知或无效策略以及
  document 放宽来源策略均失败关闭。
- denied 禁止 chunk 外发、成本治理、队列、缓存和重试；summary_only 只保留未来已授权
  摘要引用，full_text_allowed 也只保留未来授权文本块引用。
- 本批次、自然月和单任务三重预算门必须全部是固定的可用控制状态才可投影 eligible；
  三种不足/超限场景均投影 paused，且不持久化或调度。
- queue/cache/retry 继续保持 12/10/7 字段形状，成本治理保持 16 字段，审计保持 18 字段。
  provider、model、model_version、token、chunk 和 policy reason 都是 control 标签或零值投影。

## 禁止路径与停止条件

本切片不读取或保留来源正文、摘要正文、chunk 文本、物理路径或真实 URI；不创建真实队列、
缓存、重试、成本、模型版本或审计记录；不读取凭据，不选择 provider/模型，不初始化客户端，
不调用外部 API，不消耗模型 Token，不写索引、数据库或持久状态，不运行 Agent，不部署 OVH，
不启用生产，也不上传或推送。

若输入不是固定控制形状、策略缺失/无效、document 放宽来源策略、策略拒绝、任一预算门未通过
或未来审计前置字段无法满足，则保持关闭并停在 IDS-STAGE071-P3-GATE 前。P3 不属于本 run。

## 可恢复与回滚

撤回仅限本说明、P2 切片模块、P2 合同、聚焦测试、machine run、事件、机器事实、路线和生成
中文投影，返回 PHASE1_EMBEDDING_COST_GOVERNOR_CONTRACT_RUNTIME_DISABLED。不修改 P1、
Stage070 及更早证据、冻结任务包、真实资料、manifest、evidence ledger、audit log、数据库、
GitHub、OVH 或应用状态。
