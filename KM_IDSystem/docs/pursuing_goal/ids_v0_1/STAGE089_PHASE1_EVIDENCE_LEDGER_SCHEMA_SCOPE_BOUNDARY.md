# Stage089 Phase 1 · 证据账本 Schema 范围、输入输出与边界确认

## 本轮目标

只将冻结的 Stage089 证据账本 Schema 任务包与已复审的 Stage088 检索结果有效性门禁控制工件投影为一份静态工程合同。合同固定未来 evidence_id、document_id、chunk_id、fact_id、report_id、source_type、evidence_grade、证据缺口、风险评分、撤回、知识库投毒防护与关键结论绑定的控制形状；不创建、读取、写入或迁移真实证据账本、资料、数据库、索引、审计记录、报告或业务结论。

## 唯一权威与输入

- 冻结 Stage089 任务包是本阶段范围和验收的唯一来源。
- Stage088 Review 及其已复审 P1--P4 检索结果有效性门禁控制工件只作为前序控制证据；Stage089 不重定义、不替代或扩充其业务含义。
- 不建立第二权威事实源；来源文档、真实 evidence ledger 与业务线白箱人工复核仍是唯一业务权威。
- 不读取、打开、解析、复制、移动或修改真实资料、原始元数据、manifest、evidence ledger、audit log、报告、数据库或物理索引。

## 静态输入输出合同

1. evidence record 只固定 evidence_id、document_id、chunk_id、fact_id、report_id、source_type、evidence_grade、来源版本、检索轨迹与状态的未来控制引用；字段值均为不透明标签，不保存真实证据正文、资料路径、业务事实或报告内容。
2. evidence relation 只固定 evidence 与 document、chunk、fact、query、answer、report 的未来关联形状；它不查询、生成或持久化任何对象。
3. 可信等级固定为 A/B/C/D/E：A 为高可信候选、B 为较高可信候选、C 为受限可信候选、D 为低可信、E 为不可作为结论依据。所有等级仍须业务线白箱人工复核，D/E 不得单独支撑关键结论，也不得自动升格。
4. evidence gap 只记录关键结论、缺失维度、原因与阻断状态的未来引用。每条关键结论必须关联至少一个 evidence_id 或 evidence_gap；两者均缺失时失败关闭，不能被系统输出、风险分数或报告状态替代。
5. 风险评分只固定可信等级、冲突、时效、OCR 质量、撤回与风险状态的未来引用；不计算真实分数、不评价真实资料，也不自动降低或接受任何业务结论。
6. 撤回合同只固定证据、原因、受影响 fact/report、撤回状态与恢复状态的未来引用。未来撤回、低可信、冲突或过期证据必须降级，撤回影响不得被静默忽略。
7. 知识库投毒防护只固定来源溯源、冲突、异常、隔离、人工复核与防护状态的未来引用。可疑或未复核证据不得自动进入关键结论、报告或业务决策。
8. 证据 schema、检索证据捕获、风险评分、撤回影响、投毒防护、数据库迁移、报告状态更新和恢复只属于后续授权 Phase 的工程前置；本 Phase 不创建 schema、连接、运行模块、持久化或实际结论。

## 本阶段不做

- 不实现或启动真实 evidence ledger、数据库 schema 或连接、检索证据捕获、风险评分、撤回处理、投毒检测、隔离、恢复、报告状态更新或审计写入。
- 不读取真实资料，不执行批量导入，不选择 provider 或模型，不消耗模型 Token，不调用外部 API，不执行 Agent。
- 不创建持久化 evidence、document、chunk、fact、query、answer、report、风险评分、撤回记录、投毒记录、证据缺口、审计记录、缓存、队列、Operations 或已交付报告。
- 不启动 Stage089 P2、P3、P4、整阶段复审、Stage090、OVH、生产、上传或推送。

## 验收与停止

本阶段只验收静态合同、聚焦用例、机器事实投影、中文生成视图与可撤回范围的一致性。任何真实资料访问、证据账本访问、数据库 schema 或连接、持久化、风险计算、撤回／投毒运行、报告写入、模型调用、Agent、OVH、生产或超出 Stage089 P1 的修改都会停止本阶段。

## 回退与下一门

只撤回本 P1 的范围说明、静态合同、聚焦用例、机器事实投影、治理路线、生成中文视图和本地回执，恢复到 `PASS_REVIEWED_RETRIEVAL_RESULT_VALIDITY_RUNTIME_DISABLED`。不影响 Stage088 Review、冻结任务包、真实资料、manifest、evidence ledger、audit log、报告、数据库、索引、GitHub、OVH 或应用状态。下一步仅可在新的独立 run 进入 `IDS-STAGE089-P2-GATE`。
