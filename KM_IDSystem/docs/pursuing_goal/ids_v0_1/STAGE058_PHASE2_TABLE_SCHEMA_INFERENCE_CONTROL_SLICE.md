# Stage058 Phase 2 · 表格 Schema 推断最小可运行切片

## 当前门

- 任务：`IDS-V0_1-STAGE058-P2`
- 验收：`ACC-STAGE-058`
- 前置：冻结 Stage058 任务包、Stage058 P1 静态合同与 Stage057 已复审工件。
- 后继：`IDS-STAGE058-P3-GATE`，只能由新的独立 run 进入。

## 本切片做什么

本切片只接受两条固定、非业务、reference-only 控制记录。每条记录严格使用 P1 定义的十个输入字段，且不含表头、单元格、公式、正文、真实路径、物理工作簿或实际数据值。

在内存中，切片会：

1. 选择生产记录 XLSX 或质量检验 CSV 的控制 schema profile 组。
2. 投影 `11` 条 P1 定义的 `18` 字段 Schema profile 候选，覆盖日期、单位、设备、材料、工序、质量结果、事实类型和六类候选字段类型。
3. 为每个候选保留来源文档、工作表、表头行、行范围、列范围和证据引用的控制标识；它们不是物理路径、来源正文或已建立的证据记录。
4. 明确事实抽取仍归 Stage059、RAG 摘要仍归 Stage060；本切片不创建事实、RAG 摘要、数值统计或持久化状态。

## 白箱边界

- 候选列名均为 `column-handle:control:*` 控制标识，不是实际表头或真实字段映射。
- 输入形状、引用、格式或记录类型不匹配时返回 `REJECTED`，不返回候选、来源引用或任何数据内容。
- 不打开、检测或解析 XLSX/CSV；不读取真实生产记录、质检记录、授权 fixture、来源正文或物理路径；不连接数据库，不写事实、RAG、manifest、evidence ledger、audit、报告或持久状态。
- Agent、模型调用、模型 Token、本地服务、OVH、生产、上传和推送保持关闭。

## 运行与验证

```bash
python3 -B -m unittest -q KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.test_stage058_table_schema_inference_slice
```

该命令只运行固定控制记录的纯内存逻辑。它不是 XLSX/CSV 真实解析、真实列名识别、真实 Schema、事实抽取、RAG 写入、数值统计、数据质量验证或生产验收的证据。

## 回滚

只回滚本 P2 说明、切片模块、切片合同、聚焦用例、machine run、事件、事实投影、治理路线和生成中文视图，回到 `PHASE1_TABLE_SCHEMA_INFERENCE_CONTRACT_RUNTIME_DISABLED`。不得改动原始资料、manifest、evidence ledger、audit log、已交付报告、数据库、GitHub、OVH 或应用状态。
