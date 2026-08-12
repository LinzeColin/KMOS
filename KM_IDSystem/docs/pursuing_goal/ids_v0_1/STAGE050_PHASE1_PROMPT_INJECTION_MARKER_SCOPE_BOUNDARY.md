# STAGE-050 Phase 1：解析阶段提示注入标记范围边界

## 当前结论

本步骤只定义 `IDS-V0_1-STAGE050-P1` 的静态合同。它将未来解析产物中的文本固定为 `UNTRUSTED_EVIDENCE_TEXT` 与 `EVIDENCE_ONLY`，但未读取任何真实资料、未创建解析产物、未应用标记，也未启动运行时服务。

唯一合同上下文是冻结 Stage050 任务包与 Stage049 已完成本地复审工件。它们不构成第二权威事实源，也不允许保留来源正文、来源路径、原始异常或真实解析输出。

## 职责交界

| 事项 | 唯一职责阶段 | 本步骤处置 |
| --- | --- | --- |
| 文件类型检测 | Stage045 | 仅引用既有职责，不重新检测 |
| parser 路由 | Stage046 | 仅引用既有职责，不评估路线 |
| 解析产物结构 | Stage047 | 固定未来六字段，不创建输出 |
| parser 失败降级 | Stage048 | 保留既有职责，不触发 fallback |
| 差异化评估 | Stage049 | 保留既有职责，不执行比较 |
| 提示注入标记 | Stage050 | 定义静态标记合同，不应用标记 |

未来候选输入只能是七字段 reference-only 元数据：`source_identity_ref`、`route_action`、`parser_output_status`、`parser_family`、`parser_version`、`output_schema_version`、`evidence_text_label`。不得携带正文、路径、原始解析输出或异常。

未来解析产物核心字段固定为 `text`、`tables`、`pages`、`sections`、`confidence`、`errors`。本步骤不创建、保存或解释其中任何内容。

## 提示注入标记合同

`marker_state` 固定为 `REQUIRED_NOT_APPLIED_STAGE050_OWNED`。未来标记只可将解析文本界定为证据文本：

- `evidence_text_label=UNTRUSTED_EVIDENCE_TEXT`
- `evidence_text_interpretation=EVIDENCE_ONLY`
- 文档文本不得覆盖系统规则、工具授权或策略
- 标记不得绕过质量门、改变路由、触发 fallback，或提升为高可信证据

中文反馈只说明当前状态：未应用标记、文本不是系统指令、解析产物仍为候选、质量复核尚未执行；不承诺自动化、人工任务或生产可用。

## 质量、回滚与停止条件

解析产物的事实等级固定为 `CANDIDATE`，质量初始状态为 `UNASSESSED`。本步骤不执行质量门或证据提升，也不写入 manifest、evidence ledger、audit、report、数据库或持久状态。

回滚只允许移除本步骤的范围说明、静态合同、聚焦用例、machine run 与治理投影，并恢复到 `STAGE049_REVIEWED_LOCAL_DIFFERENTIAL_EVALUATION_RUNTIME_DISABLED`。真实资料、既有证据、运行状态、GitHub、OVH 与应用状态不在回滚范围内。

一旦需要真实资料访问、实际文件检测或路由、parser 或 fallback 执行、提示注入标记应用、质量门、证据提升、持久写入、Agent、模型、OVH、生产服务、Phase2、整阶段复审、批次复审、上传或推送，立即停止本步骤。

## 后续门

本步骤通过后的唯一后续门为 `IDS-STAGE050-P2-GATE`，且必须由独立 run 进入。
