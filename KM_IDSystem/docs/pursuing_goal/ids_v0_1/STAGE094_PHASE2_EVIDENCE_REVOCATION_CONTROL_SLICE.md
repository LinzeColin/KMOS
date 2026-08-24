# Stage094 Phase 2 · 证据撤回受控最小切片

## 本轮目标

只将冻结 Stage094 P1 的证据撤回合同投影为可执行的纯内存控制切片。切片固定 Evidence Ledger、检索证据捕获、风险评分、可信等级、撤回、降级、恢复、知识库投毒防护和报告影响的 future control reference，并保持 evidence 与 document、chunk、fact、query、answer、report 的关联形状；它不读取、创建、写入或修改任何真实资料、真实证据账本、报告、数据库或持久化状态。

## 唯一权威与前序

- 冻结 Stage094 任务包是本 P2 范围和验收的唯一来源。
- Stage094 P1 静态合同与 Stage093 Review 已复审可信等级工件只提供控制边界和既有 A/B/C/D/E 标签，不替代来源文档、真实证据账本或业务线白箱人工复核的业务事实权威。
- 本切片不建立第二权威事实源。全部输入和输出均使用 :control:stage094-p2: 前缀的 reference-only 标签，不包含正文、路径、业务事实、实际风险分值、实际等级、撤回理由或报告状态。

## 固定控制输入与投影

1. 输入固定为 6 条非业务、reference-only 控制请求，每条 29 个字段，场景覆盖资料不足、低可信、冲突、过期、撤回和疑似投毒。
2. 输出固定为 11 组纯内存控制投影：schema binding、evidence relation、检索证据捕获、风险引用、可信等级引用、撤回控制、投毒防护、关键结论绑定、降级、报告影响和 future integration。
3. 每条请求固定 105 个投影字段，共 630 个控制检查点；所有记录仅存在于函数返回值中，不创建 evidence、evidence gap、document、chunk、fact、query、answer、report、风险、等级、撤回、恢复、投毒、审计、缓存、队列或数据库记录。
4. 关键结论未来仍须关联至少一个 evidence_id_ref 或 evidence_gap_ref。撤回、降级、恢复、风险评分和可信等级引用都不能替代该关联。
5. 低可信、冲突、过期和撤回场景保持降级候选；疑似投毒场景保持隔离候选；报告状态影响和恢复均保留 future reference，业务使用继续要求业务线白箱人工复核。

## 失败关闭与运行边界

- 输入只接受模块自身生成的六条固定控制请求。任何额外字段、缺失字段、场景替换或控制标签变更都返回 CONTROL_INPUT_MISMATCH，并产出零条投影。
- 风险公式、阈值、等级分配、撤回规则、降级条件、恢复条件、投毒处置和业务判定继续等待业务线白箱 owner 的后续授权。
- 真实资料、原始元数据、fixture、manifest、检索、证据账本、回答、报告、数据库、模型 Token、Agent、OVH、生产、正式上传和推送保持后续授权范围。

## 验收、回退与下一门

本 P2 只验收固定控制形状、关联完整性、六类降级／隔离控制状态、失败关闭、全零运行计数、机器事实投影和中文生成视图的一致性。回退只撤回本 P2 的说明、纯内存控制切片、合同、聚焦用例、machine run、机器事实投影、治理路线、生成中文视图与本交接，恢复到 PHASE1_EVIDENCE_REVOCATION_CONTRACT_RUNTIME_DISABLED。Stage094 P1、Stage093 Review、冻结任务包、真实资料、manifest、检索、evidence ledger、audit log、报告、数据库、GitHub、OVH 和应用状态保持原状。下一步仅可在新的独立 run 进入 IDS-STAGE094-P3-GATE。
