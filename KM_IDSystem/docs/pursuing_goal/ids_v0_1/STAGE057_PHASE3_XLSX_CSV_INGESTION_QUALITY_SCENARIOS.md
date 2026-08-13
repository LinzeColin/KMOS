# Stage057 Phase 3 · XLSX/CSV 接入合同专项验证与异常场景

## 当前门

- 任务：`IDS-V0_1-STAGE057-P3`
- 验收：`ACC-STAGE-057`
- 前置：冻结 Stage057 任务包、Stage057 P1/P2 合同与 Stage056 已复审工件。
- 后继：`IDS-STAGE057-P4-GATE`，只能由新的独立 run 进入。

## 本专项做什么

本专项只重放 P2 两条固定、非业务、reference-only 控制记录形成的候选，覆盖六类冻结任务包异常类别：空表、合并单元格、单位混乱、日期格式不一、异常值和重复行。类别只是控制元数据，不是实际表格、工作表、单元格、公式、行、数值、日期或业务事实。

每个场景都保留一个 P2 事实候选的来源文档、工作表、行范围、列范围和证据引用，用于验证**控制引用形状**可追溯；这不证明真实源文件、真实行列或真实证据记录已被读取、验证或创建。

## 白箱处置

- 空表显式关闭并要求人工处理。
- 合并单元格、单位混乱、日期格式不一和重复行全部要求人工处理；不解合并、不单位/日期规范化、不去重。
- 异常值只证明未验证数值必须阻断统计结论与模型确定性数值结论；不评估异常值、不计算统计量、不生成 typed value。
- 六类均有显式处置，静默丢弃为零；RAG 仍不能替代结构化事实或数值权威。

## 运行与验证

```bash
python3 -B -m unittest -q KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.test_stage057_xlsx_csv_ingestion_quality_scenarios
```

该命令只重放固定控制引用，不能作为真实 XLSX/CSV 解析、真实数据质量验证、真实来源可追溯、事实库、统计结果或生产验收的证据。

## 边界与回滚

本专项不读取、打开、检测、解析或评估真实 XLSX/CSV、生产记录、质检记录、fixture、工作表、单元格、公式、来源正文或物理路径；不连接数据库、不写事实、RAG、manifest、evidence ledger、audit、报告或持久状态。Agent、模型调用、模型 Token、本地服务、OVH、生产、上传和推送保持关闭。

只回滚本 P3 说明、场景合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理路线和生成中文视图，回到 `PHASE2_XLSX_CSV_INGESTION_CONTROL_SLICE_RUNTIME_DISABLED`。不得改动原始资料、manifest、evidence ledger、audit log、已交付报告、数据库、GitHub、OVH 或应用状态。
