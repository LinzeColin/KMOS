# Stage090 Phase 1 · 从检索捕获证据范围、输入输出与边界确认

## 本轮目标

只将冻结的 Stage090「从检索捕获证据」任务包与已复审的 Stage089 证据账本 Schema 控制工件投影为一份静态工程合同。合同只固定未来检索证据捕获的请求、账本捕获和关联引用形状；不读取、生成、写入或持久化真实检索、证据、资料、回答、报告、账本、数据库或业务结论。

## 唯一权威与输入

- 冻结 Stage090 任务包是本阶段范围和验收的唯一来源。
- Stage089 Review 与其已复审 P1--P4 证据账本控制工件只作为前序控制证据；Stage090 不重定义、不替代或扩充其业务含义。
- 不建立第二权威事实源；来源文档、真实证据账本与业务线白箱人工复核仍是唯一业务权威。
- 不读取、打开、解析、复制、移动或修改真实资料、原始元数据、manifest、检索结果、evidence ledger、audit log、回答、报告、数据库或物理索引。

## 静态输入输出合同

1. 检索证据捕获请求只固定 retrieval trace、query、answer、report、document、chunk、fact、source type、source version 与请求状态的未来不透明引用；字段值不保存真实检索内容、正文、路径、业务事实或报告内容。
2. 未来证据账本捕获只固定 evidence capture、evidence id、evidence gap、可信等级、风险、撤回、知识库投毒防护、关键结论与捕获状态的控制引用；它不创建或更新任何真实 evidence ledger。
3. 未来关联只固定 evidence 与 document、chunk、fact、query、answer、report 的引用形状；它不查询、生成或持久化任何对象。
4. 每条关键结论未来必须关联至少一个 evidence_id 或 evidence_gap；两者均缺失时失败关闭，不能由系统输出、风险、可信等级、撤回状态或报告状态替代。
5. A/B/C/D/E 可信等级只复用冻结任务包与 Stage089 前序控制的静态标签：A 为高可信候选、B 为较高可信候选、C 为受限可信候选、D 为低可信、E 为不可作为结论依据。所有等级仍须业务线白箱人工复核。
6. 低可信、冲突、过期、撤回或疑似投毒证据的降级、隔离、恢复、报告状态影响与任何实际检索捕获只属于后续授权 Phase 的工程前置；本 Phase 不创建运行模块、连接、持久化或实际结论。

## 本阶段不做

- 不实现或启动真实检索、检索证据捕获、evidence ledger、数据库 schema 或连接、风险评分、可信等级变更、撤回处理、投毒检测、隔离、恢复、报告状态更新或审计写入。
- 不读取真实资料、检索结果、回答或报告，不执行批量导入，不选择 provider 或模型，不消耗模型 Token，不调用外部 API，不执行 Agent。
- 不创建持久化 evidence、document、chunk、fact、query、answer、report、风险、撤回、投毒、证据缺口、审计、缓存、队列、Operations 或已交付报告。
- 不启动 Stage090 P2、P3、P4、整阶段复审、Stage091、OVH、生产、上传或推送。

## 验收与停止

本阶段只验收静态合同、聚焦用例、机器事实投影、中文生成视图与可撤回范围的一致性。任何真实资料、检索、回答、报告、证据账本或数据库访问，任何持久化、风险计算、撤回／投毒运行、模型调用、Agent、OVH、生产或超出 Stage090 P1 的修改都会停止本阶段。

## 回退与下一门

只撤回本 P1 的范围说明、静态合同、聚焦用例、机器事实投影、治理路线、生成中文视图和本地回执，恢复到 `PASS_REVIEWED_EVIDENCE_LEDGER_RUNTIME_DISABLED`。不影响 Stage089 Review、冻结任务包、真实资料、manifest、检索、evidence ledger、audit log、回答、报告、数据库、索引、GitHub、OVH 或应用状态。下一步仅可在新的独立 run 进入 `IDS-STAGE090-P2-GATE`。
