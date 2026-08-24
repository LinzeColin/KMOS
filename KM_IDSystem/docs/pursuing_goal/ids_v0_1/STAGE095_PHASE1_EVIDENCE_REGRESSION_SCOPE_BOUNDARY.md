# Stage095 Phase 1 · 证据回归测试范围、输入输出与边界确认

## 本轮目标

只将冻结的 Stage095「证据回归测试」任务包与已复审的 Stage094 证据撤回控制工件投影为静态工程合同。合同固定 Evidence Ledger、证据缺口、风险评分、可信等级、撤回和知识库投毒防护的未来控制定义，确认关键结论未来必须关联至少一个 evidence_id_ref 或 evidence_gap_ref，并继承 A/B/C/D/E 证据等级标签。

## 唯一权威与输入

- 冻结 Stage095 任务包是本阶段范围和验收的唯一来源。
- Stage094 Review 与其已复审 P1--P4 控制工件只作为前序控制证据；Stage095 保持其已有控制定义，不扩充业务事实、证据状态或业务规则。
- 来源文档、真实证据账本与业务线白箱人工复核继续承担业务事实权威；本合同不建立第二权威事实源。
- 本轮不读取、打开、解析、复制、移动或修改真实资料、原始元数据、manifest、检索结果、evidence ledger、audit log、回答、报告、数据库或物理索引。

## 静态输入输出合同

1. Evidence Ledger、证据缺口、风险评分、可信等级、撤回和知识库投毒防护均仅固定为未来控制定义与不透明引用；字段值不保存真实资料、正文、路径、业务事实、风险分值、等级、撤回理由或报告状态。
2. 未来证据回归控制形状只关联 evidence_ledger_ref、evidence_id_ref、evidence_gap_ref、关键结论、document、chunk、fact、query、answer、report、风险、可信等级、撤回与投毒防护引用；它不查询、生成或持久化任何对象。
3. 每条关键结论未来必须关联至少一个 evidence_id_ref 或 evidence_gap_ref。风险评分、可信等级、撤回或回归结果不能替代该关联；资料不足继续由 evidence_gap_ref 表达。
4. A/B/C/D/E 作为 Stage094 已复审的未来等级标签保持不变。等级分配规则、阈值、撤回规则、风险公式和业务判定规则等待业务线白箱 owner 的后续确认。
5. 证据回归测试在本 P1 只定义未来控制输入、预期失败关闭与回滚边界；实际检索、证据关联、风险评分、等级分配、撤回、投毒防护和报告状态影响属于后续授权阶段。

## 本阶段不做

- 不实现或启动真实 Evidence Ledger 读写、检索证据捕获、风险计算、可信等级分配或变更、撤回、降级、恢复、冲突裁决、投毒防护、隔离、报告状态更新或审计写入。
- 不读取真实资料、检索结果、回答或报告，不执行批量导入，不选择 provider 或模型，不消耗模型 Token，不调用外部 API，不执行 Agent。
- 不创建持久化 evidence、evidence gap、document、chunk、fact、query、answer、report、风险、可信等级、撤回、恢复、投毒、审计、缓存、队列、Operations 或已交付报告。
- 不启动 Stage095 P2、P3、P4、整阶段复审、Stage096、OVH、生产或正式全局上传。

## 验收与停止

本阶段只验收静态合同、聚焦用例、机器事实投影、中文生成视图与可撤回范围的一致性。任何真实资料、证据账本、检索、风险、可信等级、撤回、报告、数据库、持久化、模型调用、Agent、OVH、生产或超出 Stage095 P1 的修改都会停止本阶段。

## 回退与下一门

只撤回本 P1 的范围说明、静态合同、聚焦用例、机器事实投影、治理路线、生成中文视图和本地回执，恢复到 PASS_REVIEWED_EVIDENCE_REVOCATION_RUNTIME_DISABLED。不影响 Stage094 Review、冻结任务包、真实资料、manifest、检索、evidence ledger、audit log、回答、报告、数据库、索引、GitHub、OVH 或应用状态。下一步仅可在新的独立 run 进入 IDS-STAGE095-P2-GATE。
