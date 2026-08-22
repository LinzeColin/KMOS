# Stage084 Phase 2 · 向量检索基线纯内存控制切片

## 本轮目标

只以冻结的 `STAGE-084_向量检索基线.md`、Stage084 P1 静态合同和已复审的 Stage083 关键词检索基线控制工件为合同上下文，在内存中处理五条固定、非业务、`reference-only` 控制请求。切片仅投影关键词／向量基线、五类 metadata filter、候选、混合评分、选择结果、检索轨迹、模型／版本／维度／相似度度量和证据账本引用的未来形状；不把任何控制标签升级为真实查询、embedding、检索结果、轨迹或业务事实。

## 唯一权威与控制输入

- 冻结 Stage084 任务包定义本 Phase 的范围与验收；Stage084 P1 和 Stage083 Review 的已审核工件只提供前序合同证据。
- 不建立第二权威事实源。业务资料、原始元数据、manifest、证据账本、审计日志、报告、数据库和物理索引均不读取、不写入、不复制或解析。
- 五条固定控制请求分别覆盖文档类型、年份、项目、设备和证据等级过滤；每条恰有 19 个不透明字段：`control_scenario`、11 个 query／向量合同字段、6 个 filter 字段和 `evidence_ledger_ref`。
- `query_kind` 只能是 `keyword` 或 `hybrid`；关键词基线与向量检索基线都必须被声明，`vector-only` 输入失败关闭。

## 纯内存投影

1. 每条固定请求仅产生一条 query、filter、candidate、hybrid score、selected result、retrieval trace 和 future integration 控制投影；总计每请求 58 个投影字段、五请求 290 个字段检查点。
2. candidate 和 trace 均绑定活动索引版本、向量模型版本与相似度度量；selected result 和 trace 均绑定同一 `evidence_ledger_ref`。这些都只是引用形状，不读取证据账本。
3. future PostgreSQL FTS／BM25、pgvector、metadata filter、hybrid ranking 和 retrieval trace 只保留为 `future-only` 路由引用，状态固定为未执行。
4. 非固定输入、缺失模型／版本／维度／相似度度量、缺失活动索引版本、过滤维度、排序解释、证据账本或轨迹引用，以及任何 `vector-only` 路由均进入失败关闭；不产生候选、选择、轨迹或持久化记录。

## 本阶段不做

- 不创建或连接 PostgreSQL，不执行 FTS/BM25、pgvector、schema migration、物理索引、embedding、关键词／向量查询、metadata filter、混合排序、Top-K、trace 或证据账本读写。
- 不读取真实资料、原始元数据、manifest、报告或审计日志；不产生数据库、缓存、队列、检索参数、查询、向量、候选、分数、选择、trace、Operations 或交付报告的持久化状态。
- 不选择或调用 provider／模型，不消耗模型 Token，不执行 Agent、OVH、生产、上传、推送、Stage084 P3／P4 或整阶段 Review。

## 验收、回退与下一门

本 Phase 只验收固定输入、控制投影字段、失败关闭、Stage084 P1 继承、历史白箱兼容、机器事实和生成中文视图的一致性。若出现真实资料访问、数据库／索引／embedding／检索／排序／轨迹／证据账本运行、持久化、模型 Token、Agent、OVH、生产、上传或超出本 P2 的修改，即停止本 Phase。

回退仅撤回本 P2 的范围说明、控制合同、纯内存模块、聚焦测试、机器事实投影、治理路线、生成中文视图和本地回执，恢复到 `PASS_VECTOR_RETRIEVAL_BASELINE_CONTRACT_RUNTIME_DISABLED`；保留 Stage084 P1、Stage083 Review、冻结任务包、真实资料、数据库、索引、GitHub、OVH 与应用状态。下一步仅可在新的独立 run 进入 `IDS-STAGE084-P3-GATE`，仍只使用既有唯一开发 worktree。
