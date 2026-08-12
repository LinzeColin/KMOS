# STAGE-050 Phase 2：提示注入标记最小切片

## 本轮结论

`IDS-V0_1-STAGE050-P2` 实现 `ISOLATED_NON_PRODUCTION_IN_MEMORY_PROMPT_INJECTION_MARKER_SLICE`。它只接受固定的非业务 control 文本和七字段 reference-only 候选元数据，记录 control parser 版本与解析置信度，并将指令样 control 文本标记为 `UNTRUSTED_EVIDENCE_TEXT/EVIDENCE_ONLY`。

它不是实际文件签名识别、parser 路由、fallback、差异化评估或生产扫描器。它不会读取来源正文、文件路径、文件字节或原始异常，也不会创建实际解析产物。

## 输入与标记

入口 `mark_controlled_instruction_text_as_evidence` 位于 `prompt_injection_marker/stage050_prompt_injection_marker_slice.py`。输入严格只有：

1. `parse_product_reference`：P1 固定的七字段 reference-only 元数据；
2. `parser_confidence`：`HIGH`、`MEDIUM`、`LOW` 或 `UNKNOWN`；
3. `instruction_text_control.control_text`：两个固定的非业务 control 文本之一。

control 文本只在内存中用于受控分类，不被返回、保存或作为业务来源。指令样 control 返回 `CONTROL_INSTRUCTION_TEXT_MARKED_EVIDENCE_ONLY`；普通证据 control 返回 `CONTROL_EVIDENCE_TEXT_RETAINED_EVIDENCE_ONLY`；非合同输入返回 `CONTROL_PROMPT_MARKER_INPUT_REJECTED`，且不回显输入。

每个可接受 control 都记录 parser 版本与置信度。它们是 control-fixture 元数据，不是 Stage046 实际 parser 配置，也不创建配置写入。

## 证据、质量与上游边界

所有结果固定为 `UNTRUSTED_EVIDENCE_TEXT/EVIDENCE_ONLY`。文档文本不能成为系统指令、工具授权或策略覆盖；标记不能改变路线、触发 fallback、绕过质量门或提升为高可信证据。

解析产物仍为 `CANDIDATE`，质量初始状态仍为 `UNASSESSED`。P2 不执行质量门、证据提升、人工复核队列、manifest、evidence ledger、audit、report、数据库或持久写入。Stage045--Stage049 的既有职责不被调用或改写。

## 明确未执行

- 未打开、扫描、识别或读取任何文件，未评估真实路线；
- 未选择、分派或执行 parser，未创建解析产物或执行 fallback、差异评估；
- 未应用运行时标记，未启动 Agent、模型调用、本地服务、OVH 或生产运行；
- 未进入 P3、整阶段复审、批次复审、GitHub 上传或推送。

## 回滚与下一门

回滚只撤销本 P2 切片、合同、聚焦测试和治理投影，恢复到 `PHASE1_PROMPT_INJECTION_MARKER_BOUNDARY_RUNTIME_DISABLED`；不改变真实资料、manifest、evidence ledger、audit log、已交付报告、持久运行状态、GitHub、OVH 或应用状态。

下一步只能在新的独立 run 进入 `IDS-STAGE050-P3-GATE`。
