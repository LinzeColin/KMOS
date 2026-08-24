# Stage092 Phase 2 · 证据风险评分受控最小切片

## 本轮目标

只把冻结 Stage092 P2 投影为可测试、可回退的纯内存证据风险评分控制切片。切片只接受六条固定、非业务、`reference-only` 控制输入，绑定 Stage092 P1 的静态风险合同与已复审 Stage091 证据缺口处理控制链；它不创建或读取真实证据、资料、账本、回答、报告、数据库或审计记录。

## 唯一权威与输入

- 冻结 Stage092 任务包、Stage092 P1 静态合同与已复审 Stage091 证据缺口处理控制工件构成本 P2 的唯一合同上下文。
- P2 只绑定前序控制引用，不重定义、不替代或扩充来源文档、真实证据账本和业务线白箱人工复核的业务事实权威。
- 六条输入是模块内建的控制标签；不包含业务资料、来源正文、真实路径、真实检索、真实证据、真实风险值或实际报告内容。
- 本阶段不建立第二权威事实源。来源文档、真实 evidence ledger 与业务线白箱人工复核继续承担业务事实权威。
- 冻结任务包未定义风险权重、阈值和业务判定公式。本切片只验证固定控制路由，风险分值、等级变更和自动处置继续等待业务线白箱 owner 的后续授权规则。

## 最小切片

1. 六条固定控制请求各含 `27` 个字段；每条只投影 Stage092 P1 的 risk score、evidence ledger、evidence/evidence gap、关键结论、document、chunk、fact、query、answer、report、来源、OCR、版本、复核、冲突、可信等级、撤回和投毒防护未来引用。
2. evidence risk 与 document、chunk、fact、query、answer、report 保持 P1 固定的 `10` 字段关联；资料不足场景允许关键结论只关联 `evidence_gap_ref`，其余场景同时携带 `reference-only` 的 `evidence_id_ref` 与 `evidence_gap_ref`。
3. 切片分别投影风险 schema 绑定、风险关联、检索证据捕获绑定、五类风险输入、风险评分路由、撤回、投毒防护、关键结论绑定、降级、报告状态影响与未来运行路线，共 `11` 组控制投影。所有对象只在函数返回值中存在。
4. A/B/C/D/E 仍只进入待业务线白箱人工复核；低可信、冲突、过期和撤回场景固定为降级候选，疑似投毒场景固定为隔离候选，资料不足场景固定为待补证据候选。它们均不能自动采纳、升级、写入或形成业务决策。
5. 风险评分、撤回、知识库投毒防护与报告状态影响只保留控制引用和未来路由；本阶段不计算真实风险，不捕获真实证据，不执行撤回、隔离、恢复或报告状态更新。

## 本阶段不做

- 不创建或迁移数据库 schema，不连接数据库，不创建真实 evidence、evidence gap、evidence ledger、document、chunk、fact、query、answer、report、风险、可信等级、撤回、投毒或审计记录。
- 不读取真实资料或 fixture，不执行真实检索、检索证据捕获、来源、OCR、版本、复核或冲突评估、风险评分、可信等级变更、撤回影响、投毒检测、隔离、恢复或报告状态更新。
- 不选择或调用 provider／模型，不消耗模型 Token，不执行 Agent、外部 API、OVH、生产、上传或推送。
- 不启动 Stage092 P3、P4、Review 或 Stage093。

## 验收与停止

验收只覆盖固定控制输入、精确投影形状、Stage092 P1／Stage091 Review 前序绑定、五类风险输入引用、资料不足 evidence gap、低可信／冲突／过期／撤回降级、疑似投毒隔离候选、关键结论 evidence_id 或 evidence_gap 绑定、业务线白箱人工复核与零运行时边界。任何真实资料或 evidence ledger 访问、数据库 schema 或连接、持久化、实际检索／风险／撤回／投毒处理、模型、Agent、OVH、生产或超出 P2 的修改都会停止本阶段。

## 回退与下一门

回退只撤回本 P2 的范围说明、纯内存控制切片、聚焦用例、机器事实投影、治理路线、生成中文视图和本地回执，恢复到 `PHASE1_EVIDENCE_RISK_SCORING_CONTRACT_RUNTIME_DISABLED`。不影响 Stage092 P1、Stage091 Review、冻结任务包、真实资料、manifest、检索、evidence ledger、audit log、回答、报告、数据库、索引、GitHub、OVH 或应用状态。下一步仅可在新的独立 run 进入 `IDS-STAGE092-P3-GATE`。
