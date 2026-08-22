# Stage087 Phase 1 · 检索轨迹范围、输入输出与边界确认

## 本轮目标

只将冻结的 Stage087 检索轨迹任务包与已复审的 Stage086 混合排序控制工件投影为一份静态工程合同。合同定义未来关键词检索、向量检索、元数据过滤、混合排序和检索轨迹之间的控制关系，以及 query、filter、candidate chunks、selected chunks、score 与 active_index_version 的记录形状；不创建 PostgreSQL、FTS、BM25、pgvector、embedding、数据库连接、物理索引、查询、过滤、排序、轨迹或持久化记录。

## 唯一权威与输入

- 冻结 Stage087 任务包是本阶段范围和验收的唯一来源。
- Stage086 Review 及其 P1--P4 已复审混合排序控制工件只作为前序控制证据；Stage087 不重定义、不替代或扩充其业务含义。
- 不建立第二权威事实源；来源文档、evidence ledger 与业务线白箱人工复核仍是唯一业务权威。
- 不读取、打开、解析、复制、移动或修改真实资料、原始元数据、manifest、evidence ledger、audit log、报告、数据库或物理索引。

## 静态输入输出合同

1. keyword retrieval baseline、vector retrieval baseline、metadata filter 与 hybrid ranking 仅以不透明控制引用表示；未来结果不得只依赖 vector similarity。
2. query 只记录不透明 query、语言、类型、请求 Top-K、关键词／向量基线与 active_index_version 引用；不保存或查询真实 query 正文。
3. filter 只固定文档类型、年份、项目、设备、资料状态与证据等级六类未来过滤引用及状态；任一过滤引用缺失时，不生成 candidate chunks 或 selected chunks。
4. candidate chunks 与 selected chunks 只固定 chunk、文档、过滤、关键词／向量／混合 score、排序解释与活动索引版本的控制引用；两者不得跨 active_index_version、过滤合同或 score explanation 混用。
5. retrieval trace 必须关联 query、filter、candidate chunk set、selected chunk set、score explanation、关键词／向量基线、metadata filter、active_index_version 与 evidence ledger 引用；它只描述未来审计形状，不读取 evidence ledger 或写入审计记录。
6. PostgreSQL full-text／BM25、pgvector、过滤器、混合排序与 trace writer 只属于后续授权 Phase 的工程前置；本 Phase 不创建 schema、索引、连接、模型选择、embedding、查询、过滤、排序、Top-K 或 trace 写入。

## 本阶段不做

- 不实现或启动 PostgreSQL、FTS、BM25、pgvector、embedding、数据库 schema 或连接、物理索引、关键词查询、向量检索、元数据过滤、混合排序、Top-K、检索轨迹或 evidence ledger 读取／写入。
- 不读取真实资料，不执行批量导入，不选择 provider 或模型，不消耗模型 Token，不调用外部 API，不执行 Agent。
- 不创建持久化 query、filter、candidate chunks、selected chunks、score、向量、检索轨迹、审计记录、缓存、队列、Operations、报告快照或已交付报告。
- 不启动 Stage087 P2、P3、P4、整阶段复审、OVH、生产、上传或推送。

## 验收与停止

本阶段只验收静态合同、聚焦用例、机器事实投影、中文生成视图与可撤回范围的一致性。任何真实资料访问、数据库 schema 或连接、索引构建、embedding、关键词或向量查询、过滤、排序、检索轨迹读写、evidence ledger 访问、持久化、模型调用、Agent、OVH、生产或超出 Stage087 P1 的修改都会停止本阶段。

## 回退与下一门

只撤回本 P1 的范围说明、静态合同、聚焦用例、机器事实投影、治理路线、生成中文视图和本地回执，恢复到 `PASS_REVIEWED_HYBRID_RANKING_RUNTIME_DISABLED`。不影响 Stage086 Review、冻结任务包、真实资料、manifest、evidence ledger、audit log、报告、数据库、索引、GitHub、OVH 或应用状态。下一步仅可在新的独立 run 进入 `IDS-STAGE087-P2-GATE`。
