# Stage088 Phase 2 · 检索结果有效性门禁纯内存受控切片

## 本轮目标

本 Phase 只把冻结 Stage088 要求投影为六条固定、非业务、`reference-only` 的纯内存控制请求，以及相应的 query、六类 metadata filter、活动索引版本、candidate、score、selected、retrieval trace、结果有效性门禁和未来运行路线控制投影。它只验证字段形状、引用链与失败关闭，不产生业务查询、过滤、分数、排序、Top-K 选择、结果有效性结论、证据账本记录或持久化记录。

## 唯一权威与输入

- 冻结 Stage088 任务包是本 Phase 范围和验收的唯一来源。
- Stage087 Review/P1--P4 已复审检索轨迹控制工件，以及 Stage088 P1 静态合同，只作为前序控制边界；本 Phase 不重定义、不替代或扩充业务事实。
- 六条输入是模块内固定的不透明控制标签，不读取、打开、解析、复制、移动或修改真实资料、原始元数据、manifest、evidence ledger、audit log、报告、数据库或物理索引。
- 不建立第二权威事实源；来源文档、evidence ledger 与业务线白箱人工复核仍是唯一业务权威。

## 固定控制投影

1. 六个固定场景分别覆盖文档类型、年份、项目、设备、资料状态和证据等级；每条都同时声明 query、六个过滤维度、keyword／vector retrieval baseline、活动索引版本和 evidence ledger 不透明引用。
2. keyword baseline 与 vector baseline 都只作为未来能力的控制字段。不得只依赖 vector similarity，也不得仅因系统有输出而接受结果；本 Phase 不执行关键词或向量查询。
3. candidate、score 与 selected 只保留文档、控制引用、过滤、关键词／向量／混合 score、排序解释和活动索引版本的引用形状；没有数值、文档正文、chunk 正文或真实 rank。
4. retrieval trace 必须沿用 query、filter、candidate set、selected set、关键词／向量 baseline、metadata filter、hybrid score、ranking policy、score explanation、活动索引版本和 evidence ledger 引用。
5. 每条结果有效性门禁投影必须沿用 query、filter、candidate、selected、请求 Top-K、关键词／向量 baseline、hybrid score、ranking policy、score explanation、活动索引版本、retrieval trace 和 evidence ledger 引用；它只能产生“未评估、待业务线白箱人工复核”的控制状态，不能自动确认资料正确、结果有效、业务建议或最终决策。
6. PostgreSQL full-text／BM25、pgvector、元数据过滤、混合排序、retrieval trace writer 和结果有效性门禁运行只登记为 `future-only` 路线，全部保持 `NOT_EXECUTED`。
7. 任何非固定输入，包括 `vector` query kind，均返回 `CONTROL_INPUT_MISMATCH`，且不生成 candidate、selected、trace 或有效性门禁投影。

## 本阶段不做

- 不实现、启动或连接 PostgreSQL、FTS、BM25、pgvector、embedding、数据库 schema、物理索引、关键词检索、向量检索、元数据过滤、混合排序、Top-K 选择、检索轨迹、结果有效性判定或 evidence ledger 读写。
- 不读取真实资料，不执行批量导入，不选择 provider 或模型，不消耗模型 Token，不调用外部 API，不执行 Agent。
- 不创建持久化 query、filter、candidate、selected、score、向量、检索轨迹、有效性测试报告、审计记录、缓存、队列、Operations、报告快照或已交付报告。
- 不进入 Stage088 P3、P4、整阶段复审、Stage089、OVH、生产、上传或推送。

## 验收、回退与下一门

本 Phase 只验收固定控制输入、字段和计数合同、六类过滤覆盖、关键词与向量基线声明、活动索引版本／trace／evidence ledger／结果有效性门禁引用链、`vector-only` 与仅凭系统输出的失败关闭、全零运行时边界及中文生成视图的一致性。任何真实资料访问、数据库或模型运行、业务查询、过滤、评分、排序、有效性判定、持久化、模型调用、Agent、OVH、生产、上传或超出 Stage088 P2 的修改都会停止本 Phase。

回退时只撤回 P2 的范围说明、纯内存合同、控制模块、聚焦用例、机器事实投影、生成中文视图和本地回执，恢复到 `PASS_RETRIEVAL_RESULT_VALIDITY_GATE_CONTRACT_RUNTIME_DISABLED`；不影响 Stage087 Review、Stage088 P1、冻结任务包、真实资料、manifest、evidence ledger、audit log、报告、数据库、索引、GitHub、OVH 或应用状态。下一步仅可在新的独立 run 进入 `IDS-STAGE088-P3-GATE`。
