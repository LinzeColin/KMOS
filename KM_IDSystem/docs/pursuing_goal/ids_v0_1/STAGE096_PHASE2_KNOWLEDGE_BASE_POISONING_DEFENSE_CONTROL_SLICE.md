# Stage096 Phase 2 · 知识库投毒防护受控最小切片

## 本轮目标

只将冻结 Stage096 P1 的知识库投毒防护静态合同投影为可执行的纯内存控制切片。切片固定证据 schema、检索证据捕获、风险评分、可信等级、撤回和投毒防护的未来关联，覆盖 evidence 与 document、chunk、fact、query、answer、report 的关联形状，并以 `reference-only` 标签表达六类后续验证场景。

## 唯一权威与前序

- 冻结 Stage096 任务包是本 P2 范围和验收的唯一来源。
- Stage096 P1 静态合同与 Stage095 Review 已复审证据回归控制工件提供控制边界和既有 A/B/C/D/E 标签；来源文档、真实证据账本与业务线白箱人工复核继续承担业务事实权威。
- 本切片不建立第二权威事实源。输入与输出都使用 `:control:stage096-p2:` 前缀的 `reference-only` 标签，不包含正文、路径、业务事实、实际风险分值、实际等级、撤回理由或报告状态。

## 固定控制输入与投影

1. 输入固定为 6 条非业务、`reference-only` 控制请求，每条 21 个字段。场景依次覆盖内部资料不足、低 OCR、旧版本、冲突、撤回与疑似恶意资料。
2. 输入完整保留 Stage096 P1 的 8 个知识库投毒防护控制引用，并补充 evidence 与 document、chunk、fact、query、answer、report 的关联及静态捕获、风险、降级、报告影响和白箱复核状态。
3. 输出固定为 6 组纯内存控制投影：schema binding、evidence relation、检索证据捕获、风险与可信等级、撤回与投毒防护、关键结论与报告影响。每条请求固定 58 个投影字段，共 348 个控制检查点。
4. 关键结论未来保持至少一个 `evidence_id_ref` 或 `evidence_gap_ref` 关联。内部资料不足场景使用 `evidence_gap_ref`；其他控制场景使用 `evidence_id_ref`。风险、可信等级、撤回、降级、投毒防护和报告影响引用不能替代该关联。
5. 低 OCR、旧版本、冲突和撤回资料保持降级候选；疑似恶意资料保持隔离候选；报告影响保留后续人工复核引用，业务使用继续要求业务线白箱人工复核。

## 失败关闭与运行边界

- 输入只接受模块自身生成的六条固定控制请求。额外字段、缺失字段、场景替换或标签变化会返回 `CONTROL_INPUT_MISMATCH`，并生成零条投影。
- 风险公式、阈值、等级分配、撤回规则、降级条件、恢复条件、投毒处置和业务判定继续等待业务线白箱 owner 的后续授权。
- 真实资料、原始元数据、fixture、manifest、检索、证据账本、回答、报告、数据库、模型 Token、Agent、OVH、生产、正式上传和推送保持后续授权范围。

## 验收、回退与下一门

本 P2 验收固定控制形状、关联完整性、六类降级或隔离控制状态、失败关闭、全零运行计数、机器事实投影和中文生成视图的一致性。回退只撤回本 P2 的说明、纯内存控制切片、合同、聚焦用例、machine run、机器事实投影、治理路线、生成中文视图与本交接，恢复到 `PHASE1_KNOWLEDGE_BASE_POISONING_DEFENSE_CONTRACT_RUNTIME_DISABLED`。Stage096 P1、Stage095 Review、冻结任务包、真实资料、manifest、检索、evidence ledger、audit log、报告、数据库、GitHub、OVH 和应用状态保持原状。下一步仅可在新的独立 run 进入 `IDS-STAGE096-P3-GATE`。
