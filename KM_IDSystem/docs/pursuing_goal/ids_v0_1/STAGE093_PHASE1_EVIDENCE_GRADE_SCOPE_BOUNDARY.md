# Stage093 Phase 1 · 证据可信等级 A/B/C/D/E 范围、输入输出与边界确认

## 本轮目标

只将冻结的 Stage093「证据可信等级 A/B/C/D/E」任务包与已复审的 Stage092 证据风险评分控制工件投影为静态工程合同。合同固定 A/B/C/D/E、关键结论 `evidence_id_ref`/`evidence_gap_ref` 约束，以及 evidence ledger、风险、撤回和知识库投毒防护的未来控制边界；不读取、推断、分配或变更真实证据等级。

## 唯一权威与输入

- 冻结 Stage093 任务包是本阶段范围和验收的唯一来源。
- Stage092 Review 与其已复审 P1--P4 控制工件只作为前序控制证据；Stage093 不重定义、不替代或扩充其业务含义。
- 来源文档、真实证据账本与业务线白箱人工复核继续承担业务事实权威；本合同不建立第二权威事实源。
- 本轮不读取、打开、解析、复制、移动或修改真实资料、原始元数据、manifest、检索结果、evidence ledger、audit log、回答、报告、数据库或物理索引。

## 静态输入输出合同

1. 证据可信等级只固定 `evidence_grade_ref`、`evidence_id_ref`、`evidence_gap_ref`、关键结论、document、chunk、fact、query、answer、report、五类风险输入、风险、撤回、知识库投毒防护与等级分配状态的未来不透明引用；字段值不保存真实资料、正文、路径、业务事实或等级结果。
2. A/B/C/D/E 可信等级只固定为未来控制标签：A 为高可信候选、B 为较高可信候选、C 为受限可信候选、D 为低可信、E 为不可作为结论依据。任何等级、风险或结论都须经过业务线白箱人工复核。
3. 每条关键结论未来必须关联至少一个 `evidence_id_ref` 或 `evidence_gap_ref`。可信等级、风险评分、撤回状态或投毒状态不能替代该关联；资料不足继续由 `evidence_gap_ref` 表达。
4. 低可信、冲突、过期或撤回资料未来必须保持降级候选；疑似投毒或未复核资料不得自动采纳；低等级不得伪装为高可信结论。
5. 冻结任务包没有给出可信等级分配公式、阈值或业务判定规则。本 P1 将它们固定为后续业务线白箱 owner 的前置输入，不自行编造等级算法、阈值、结论或自动处置规则。
6. 未来关联只固定可信等级与 evidence、evidence gap、document、chunk、fact、query、answer、report、关键结论的引用形状；它不查询、生成或持久化任何对象。

## 本阶段不做

- 不实现或启动真实证据等级分配、来源判断、OCR 评估、版本比较、复核判断、冲突裁决、风险计算、证据撤回、知识库投毒防护、隔离、恢复、报告状态更新或审计写入。
- 不读取真实资料、检索结果、回答或报告，不执行批量导入，不选择 provider 或模型，不消耗模型 Token，不调用外部 API，不执行 Agent。
- 不创建持久化 evidence、evidence gap、document、chunk、fact、query、answer、report、风险、可信等级、撤回、投毒、审计、缓存、队列、Operations 或已交付报告。
- 不启动 Stage093 P2、P3、P4、整阶段复审、Stage094、OVH、生产或正式全局上传。

## 验收与停止

本阶段只验收静态合同、聚焦用例、机器事实投影、中文生成视图与可撤回范围的一致性。任何真实资料、证据账本、等级分配或阈值访问，任何持久化、模型调用、Agent、OVH、生产或超出 Stage093 P1 的修改都会停止本阶段。

## 回退与下一门

只撤回本 P1 的范围说明、静态合同、聚焦用例、机器事实投影、治理路线、生成中文视图和本地回执，恢复到 `PASS_REVIEWED_EVIDENCE_RISK_SCORING_RUNTIME_DISABLED`。不影响 Stage092 Review、冻结任务包、真实资料、manifest、检索、evidence ledger、audit log、回答、报告、数据库、索引、GitHub、OVH 或应用状态。下一步仅可在新的独立 run 进入 `IDS-STAGE093-P2-GATE`。
