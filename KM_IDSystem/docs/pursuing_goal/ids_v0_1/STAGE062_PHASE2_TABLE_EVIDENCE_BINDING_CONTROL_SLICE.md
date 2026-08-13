# Stage062 Phase 2 · 表格证据绑定最小可运行控制切片

## 当前目标

在 Stage062 P1 的十九字段引用式输入和十七字段未来绑定输出合同上，提供一个只在内存中运行的、固定且非业务的控制切片。它只验证引用字段形状、XLSX/CSV 类型标签、生产/质检记录类别、六维可追溯引用和数值关闭状态能被机械投影；不读取、解析、推断、抽取、绑定或写入真实表格、事实、证据或来源。

## 固定控制范围

- 输入严格为两条固定的 reference-only 控制请求：一条 `PRODUCTION_RECORD`/`XLSX`，一条 `QUALITY_INSPECTION_RECORD`/`CSV`。
- 两条请求均只使用 `:control:` 引用标识。`evidence_id`、`document_id`、`sheet`、`row`、`column` 和 `source_uri` 保留为不透明引用形状，不含真实路径、URL、来源正文、工作表、表头、单元格、公式或业务数值。
- 输出严格为两条 `UNBOUND_REFERENCE_ONLY` 候选。候选不是事实、证据记录、来源位置绑定、数据库记录或第二权威事实源。
- Stage057、Stage058、Stage059、Stage060、Stage061 的接入、Schema、事实、摘要与质量职责保持不变；本切片只连接已声明的引用字段。

## 可执行边界

- 允许：纯内存输入字段验证、固定控制候选投影、候选形状断言、中文反馈和拒绝未知/重排/篡改控制输入。
- 不允许：真实 XLSX/CSV 读取、文件检测、Schema 推断、字段识别、事实抽取、typed value、表格摘要正文、质量评估、数值统计、真实来源/证据绑定、数据库、持久化、Agent、模型调用、模型 Token、服务、OVH、生产、上传或推送。
- 候选始终要求人工确认；未验证的来源和数值始终阻断统计或确定性结论。

## 验收与回滚

- 聚焦测试必须证明两条固定控制请求能投影为两条十七字段候选，六维引用保持为控制形状，并拒绝异常输入。
- 回滚只撤回本 P2 说明、切片合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理路线和生成中文视图，回到 `PHASE1_TABLE_EVIDENCE_BINDING_CONTRACT_RUNTIME_DISABLED`。
- 不触及真实资料、`00_ORIGINAL_RAW_DATA`、manifest、evidence ledger、audit log、已交付报告、事实库、数据库、GitHub、OVH 或应用状态。

## 下一门

本切片完成后，下一步仅允许在新的独立 run 进入 `IDS-STAGE062-P3-GATE`。P2 不进入 P3、整阶段复审、批次复审、OVH、生产或上传。
