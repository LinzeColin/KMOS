# Stage075 Phase 4 · 外部 API 覆盖授权审计交付证据、回滚与中文反馈

## 范围

本阶段只从 P3 的五条固定、非业务、reference-only 控制场景和 P2 的纯内存控制
投影派生 metadata-only 交付证据：五条策略样例、五条十九字段审计投影、五条零值
成本估算、五条失败处理、五条未外发原因、八键查询说明、一条 owner 强制允许外发
四字段前置样例、回到 P3 的策略回滚说明和四条中文反馈。该交付证据不建立第二权威
事实源。

## 已交付的受控证据

- `denied` 场景的外发、队列、缓存和重试均保持阻断；
- `summary_only` 只保留摘要引用类别，document 收紧不得升级为文本块；
- `full_text_allowed` 仍只是未来文本块引用，必须先满足审计前置和业务线白箱人工复核；
- 预算不足时外部 API 候选、队列、缓存和重试均保持暂停；
- 每条样例均重建十九字段审计投影；provider、model、model_version、chunk_id、owner
  授权与 owner 强制允许外发引用均只是控制标签，Token 与成本均为零值投影；
- owner 强制允许外发仍只保留 `actor`、`reason`、`old_value`、`new_value` 四字段前置，
  不等于已应用策略或已创建真实审计记录。

## 查询、回滚与中文反馈

查询只支持当前 Python 进程中的控制交付报告，可按 scenario、策略、队列状态、预算
状态、策略引用、审计引用和 owner 强制允许外发审计引用筛选；没有持久审计日志、真实
外发历史或真实记录查询。回滚只撤回本 P4 的说明、合同、纯内存模块、测试、machine
run、事件、机器事实、治理路线和生成中文视图，恢复到 P3；不影响真实资料、manifest、
evidence ledger、audit log、数据库、GitHub、OVH 或生产。

## 零运行时边界

不读取、保留、创建、外发或查询真实资料、摘要、文本块、provider、模型、Token、成本、
预算、队列、缓存、重试或审计记录；不读取凭据、不调用外部 API 或模型、不消耗模型
Token、不写入数据库、不启动 Agent、不部署 OVH、不进入 Stage075 Review、不上传或推送。

下一步只可在新的独立 run 进入 `IDS-STAGE075-REVIEW-GATE`。
