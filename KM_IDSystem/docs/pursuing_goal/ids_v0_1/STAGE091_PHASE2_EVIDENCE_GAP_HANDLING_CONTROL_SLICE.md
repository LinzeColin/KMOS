# Stage091 Phase 2 · 证据缺口处理受控最小切片

## 本轮目标

只把冻结 Stage091 P2 投影为可测试、可回退的纯内存证据缺口处理控制切片。切片只接受六条固定、非业务、reference-only 控制输入，绑定 Stage091 P1 的 evidence gap 形状与已复审 Stage090 检索证据捕获控制链；它不创建或读取真实证据、资料、账本、回答、报告、数据库或审计记录。

## 唯一权威与输入

- 冻结 Stage091 任务包、Stage091 P1 静态合同与已复审 Stage090 从检索捕获证据控制工件构成本 P2 的唯一合同上下文。
- P2 只绑定前序控制引用，不重定义、不替代或扩充来源文档、真实证据账本和业务线白箱人工复核的业务事实权威。
- 六条输入是模块内建的控制标签；不包含业务资料、来源正文、真实路径、真实检索、真实证据、真实风险值或实际报告内容。
- 本阶段不建立第二权威事实源。来源文档、真实 evidence ledger 与业务线白箱人工复核继续承担业务事实权威。
- 本阶段不读取、打开、解析、复制、移动或修改真实资料、原始元数据、manifest、检索结果、evidence ledger、audit log、回答、报告、数据库或物理索引。

## 最小切片

1. 六条固定控制请求各含 27 个字段；每条只投影 Stage091 P1 的 evidence gap、关键结论、document、chunk、fact、query、answer、report、风险、撤回、投毒与报告状态未来引用。
2. evidence gap 与 document、chunk、fact、query、answer、report 保持 P1 固定的 7 字段关联；资料不足场景允许关键结论只关联 `evidence_gap_ref`，其余场景同时携带 reference-only `evidence_id_ref` 与 `evidence_gap_ref`。
3. 切片分别投影 evidence gap schema 绑定、evidence gap 关联、检索证据捕获绑定、风险、撤回、投毒防护、关键结论绑定、降级、报告状态影响与未来运行路线，共 10 组控制投影。所有对象只在函数返回值中存在。
4. A 等级仍只进入待业务线白箱人工复核；低可信、冲突、过期和撤回场景固定为降级候选，疑似投毒场景固定为隔离候选，资料不足场景固定为待补证据候选。它们均不能自动采纳、升级、写入或形成业务决策。
5. 风险、撤回、知识库投毒防护与报告状态影响只保留控制引用和未来路由；本阶段不计算真实风险，不捕获真实证据，不执行撤回、隔离、恢复或报告状态更新。

## 本阶段不做

- 不创建或迁移数据库 schema，不连接数据库，不创建真实 evidence gap、evidence ledger、document、chunk、fact、query、answer、report、风险、撤回、投毒或审计记录。
- 不读取真实资料或 fixture，不执行真实检索、检索证据捕获、证据缺口识别或关闭、风险评分、可信等级变更、撤回影响、投毒检测、隔离、恢复或报告状态更新。
- 不选择或调用 provider／模型，不消耗模型 Token，不执行 Agent、外部 API、OVH、生产、上传或推送。
- 不启动 Stage091 P3、P4、Review 或 Stage092。

## 验收与停止

验收只覆盖固定控制输入、精确投影形状、Stage091 P1／Stage090 Review 前序绑定、资料不足 evidence gap、低可信／冲突／过期／撤回降级、疑似投毒隔离候选、关键结论 evidence_id 或 evidence_gap 绑定、业务线白箱人工复核与零运行时边界。任何真实资料或 evidence ledger 访问、数据库 schema 或连接、持久化、实际检索／缺口／风险／撤回／投毒处理、模型、Agent、OVH、生产或超出 P2 的修改都会停止本阶段。

## 回退与下一门

回退只撤回本 P2 的范围说明、纯内存控制切片、聚焦用例、机器事实投影、治理路线、生成中文视图和本地回执，恢复到 `PHASE1_EVIDENCE_GAP_HANDLING_CONTRACT_RUNTIME_DISABLED`。不影响 Stage091 P1、Stage090 Review、冻结任务包、真实资料、manifest、检索、evidence ledger、audit log、回答、报告、数据库、索引、GitHub、OVH 或应用状态。下一步仅可在新的独立 run 进入 `IDS-STAGE091-P3-GATE`。
