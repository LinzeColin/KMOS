# Stage074 Phase 4 · 本地 Embedding 兜底合同交付证据、回滚与中文反馈

## 范围

本阶段只从 P3 的五条固定、非业务、reference-only 控制场景和 P2 的纯内存控制投影
派生 metadata-only 交付证据：五条外部 API 策略样例、五条十八字段审计投影、五条
零值成本估算、五条失败处理、五条未外发原因、七键查询说明、回到 P3 的策略回滚说明
和四条中文反馈。该交付证据不建立第二权威事实源。

## 已交付的受控证据

- denied 场景的外发、队列、缓存和重试均保持阻断；
- summary_only 只保留摘要引用类别，document 收紧不得升级为文本块；
- full_text_allowed 仍只是未来文本块引用，必须先满足审计前置和业务线白箱人工复核；
- 预算不足时外部 API 候选、队列、缓存和重试均保持暂停；
- 每条样例均重建十八字段审计投影；provider、model、model_version、chunk_id 与控制时间
  字段均只是控制引用，Token 与成本均为零值投影。

## 查询、回滚与中文反馈

查询只支持当前 Python 进程中的控制交付报告，可按 scenario_id、策略、队列/缓存/
重试引用、预算状态和审计引用筛选；没有持久审计日志、真实外发历史或真实记录查询。
回滚只撤回本 P4 的说明、合同、纯内存模块、测试、machine run、事件、机器事实、治理
路线和生成中文视图，恢复到 P3；不影响真实资料、manifest、evidence ledger、audit
log、数据库、GitHub、OVH 或生产。

## 零运行时边界

不读取、保留、创建、外发或查询真实资料、摘要、文本块、provider、模型、Token、成本、
预算、队列、缓存、重试或审计记录；不读取凭据、不调用外部 API 或模型、不消耗模型
Token、不写入数据库、不启动 Agent、不部署 OVH、不进入 Stage074 Review、不上传或推送。

下一步只可在新的独立 run 进入 IDS-STAGE074-REVIEW-GATE。
