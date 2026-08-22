# Stage089 Phase 2 · 证据账本受控最小切片

## 本轮目标

只把冻结 Stage089 P2 投影为可测试、可回退的纯内存控制切片。切片接受六条固定、非业务、`reference-only` 控制输入，投影未来 evidence schema、evidence 与 document、chunk、fact、query、answer、report 的关联、evidence gap、检索证据捕获、风险、撤回、投毒防护、关键结论绑定、降级和未来运行路线。它不创建真实 evidence ledger、资料、数据库、报告或审计记录。

## 唯一权威与输入

- 冻结 Stage089 任务包、已完成的 Stage089 P1 静态合同和已复审的 Stage088 控制工件是本 P2 的唯一合同上下文。
- 六条输入是模块内建的控制标签；不包含业务资料、来源正文、真实路径、真实证据、真实风险值或实际报告内容。
- 不建立第二权威事实源。来源文档、真实 evidence ledger 与业务线白箱人工复核仍是唯一业务权威。
- 不读取、打开、解析、复制、移动或修改真实资料、原始元数据、manifest、evidence ledger、audit log、报告、数据库或物理索引。

## 最小切片

1. evidence schema 投影固定 `evidence_id`、`document_id`、`chunk_id`、`fact_id`、`report_id`、`source_type`、`evidence_grade`、来源版本、检索轨迹和状态的控制引用。
2. evidence relation 明确关联 document、chunk、fact、query、answer 与 report；所有关联只在函数返回值中存在，不持久化。
3. evidence gap、检索证据捕获、风险评分、撤回和知识库投毒防护均只保留未来控制引用；不计算真实风险、不捕获真实证据、不执行撤回、隔离或恢复。
4. 每条关键结论同时携带 `evidence_id` 与 `evidence_gap` 控制引用，确保未来任一关键结论至少关联二者之一；系统输出不能替代证据链。
5. A 等级仍只会进入“待业务线白箱人工复核”；低可信、冲突、过期和撤回场景固定为降级候选，疑似投毒场景固定为隔离候选，均不得自动采纳、升级、写入或形成业务决策。

## 本阶段不做

- 不创建或迁移数据库 schema，不连接数据库，不创建真实 evidence ledger、document、chunk、fact、query、answer、report、风险、撤回、投毒或审计记录。
- 不读取真实资料或 fixture，不执行检索证据捕获、风险评分、可信等级变更、撤回影响、投毒检测、隔离、恢复或报告状态更新。
- 不选择或调用 provider／模型，不消耗模型 Token，不执行 Agent、外部 API、OVH、生产、上传或推送。
- 不启动 Stage089 P3、P4、Review 或 Stage090。

## 验收与停止

验收只覆盖固定控制输入、精确投影形状、失败关闭、低可信／冲突／过期／撤回降级、疑似投毒隔离候选、业务线白箱人工复核与零运行时边界。任何真实资料或 evidence ledger 访问、数据库 schema 或连接、持久化、实际捕获／风险／撤回／投毒处理、模型、Agent、OVH、生产或超出 P2 的修改都会停止本阶段。

## 回退与下一门

回退只撤回本 P2 的范围说明、纯内存控制切片、聚焦用例、机器事实投影、治理路线、生成中文视图和本地回执，恢复到 `PASS_EVIDENCE_LEDGER_SCHEMA_CONTRACT_RUNTIME_DISABLED`。不影响 Stage089 P1、Stage088 Review、冻结任务包、真实资料、manifest、evidence ledger、audit log、报告、数据库、索引、GitHub、OVH 或应用状态。下一步仅可在新的独立 run 进入 `IDS-STAGE089-P3-GATE`。
