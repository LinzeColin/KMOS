# Stage083 Phase 2 · 关键词检索基线控制切片边界

## 目标

在不读取任何 IDS 业务资料、不访问保护目录、不建立第二权威事实源的前提下，实现一个固定输入、纯内存、`reference-only` 的关键词检索基线控制切片。切片只投影任务包要求的关键词基线、五类元数据过滤、候选、混合评分、选择结果、检索轨迹与证据账本引用；它不连接 PostgreSQL、不建立 FTS 或 pgvector 索引，也不执行真实查询、过滤、排序、轨迹或持久化。

## 唯一依据与范围

- 冻结任务包：`STAGE-083_关键词检索基线.md`。
- 已完成前置：Stage083 P1 静态关键词检索基线合同，以及 Stage082 Review/P1--P4 已审核旧索引保留策略控制工件。
- 五条固定控制请求分别对应文档类型、年份、项目、设备与证据等级过滤维度；所有 query、filter、candidate、score、index、trace 与 ledger 值均为不透明控制标签。
- 不新增业务规则、真实查询文本、实际 Top-K 数量、文档范围、索引版本、评分、检索结果、证据账本或业务结论的权威事实。

## 固定控制输入与投影

输入严格固定为五条 `:control:stage083-p2:` 控制请求，每条包含 P1 固定的七个 query 字段、六个过滤字段和一个证据账本引用。关键词基线对所有请求均为必需条件，`vector` 不能单独作为 query kind；`hybrid` 请求也必须保留关键词分数引用。每条请求只在内存中投影：

1. query 与 metadata filter 控制字段；
2. 一个 candidate 与其活动索引版本引用；
3. 一个 keyword/vector/hybrid score 控制投影及排序解释；
4. 一个 selected result 与候选、评分解释、证据账本引用；
5. 一个 retrieval trace 与 query、filter、候选集、选择集、活动索引版本和证据账本引用；
6. future PostgreSQL FTS／BM25、pgvector、过滤、混合排序与轨迹路由的未执行集成投影。

上述投影不表示数据库表、物理索引、真实候选、真实评分、Top-K 选择、证据账本访问、日志或审计记录。

## 失败关闭与业务线白箱

只接受完全匹配的固定控制输入。任一 query、Top-K 声明、过滤维度、活动索引版本、候选关联、评分解释、证据账本引用或轨迹引用缺失，或出现 vector-only query kind 时，均返回关闭结果，不输出控制投影。未来真实检索配置、参数、资料范围、证据等级映射和结果采用仍须业务线白箱人工复核。

## 严格禁止

不得读取、写入、查询、过滤、排序、追踪、复制、移动、删除或解析真实资料、原始元数据、fixture、manifest、证据账本、审计日志、数据库、索引、Operations 或报告；不得连接 PostgreSQL、执行 FTS／BM25／pgvector、写入 trace、选择模型、消耗 Token、执行 Agent、部署 OVH、启动生产、上传 GitHub 或 push。P3、P4、整阶段复审和 Stage084 均不在本 run 范围内。

## 验收与回退

P2 仅在静态合同可解析、五条固定输入与各类控制投影字段完全匹配、五类过滤维度均被覆盖、关键词基线和 vector-only 拒绝保持、候选/选择/轨迹/证据引用关联一致、全部运行时边界为 false 时完成。回退只撤回本 P2 的范围说明、控制合同、纯内存切片、测试和机器事实投影，恢复到 `STAGE083_P1_LOCAL_CONTRACT_RUNTIME_DISABLED`；不得触及真实资料、持久状态、OVH 或 GitHub。下一步只能在新的独立 run 中进入 `IDS-STAGE083-P3-GATE`。
