# Stage059 Phase 2 · 事实抽取最小可运行控制切片

## 当前门

- 任务：`IDS-V0_1-STAGE059-P2`
- 验收：`ACC-STAGE-059`
- 前置：冻结 Stage059 任务包、Stage059 P1 静态合同与 Stage058 已复审工件。
- 后继：`IDS-STAGE059-P3-GATE`，只能由新的独立 run 进入。

## 本切片做什么

本切片只接受两条固定、非业务、reference-only 控制记录。每条记录严格使用 P1
定义的 12 个输入字段；记录中只允许控制引用，不含表格、表头、单元格、公式、正文、
真实路径、物理工作簿或实际业务值。

在内存中，切片会：

1. 严格核验生产 XLSX 控制引用和质量检验 CSV 控制引用是否符合 P1 的字段形状。
2. 投影 3 条 P1 定义的 25 字段 typed fact 控制候选，分别覆盖
   `PRODUCTION_FACT`、`QUALITY_FACT` 与 `INSPECTION_FACT`。
3. 为每条候选保留来源文档、工作表、表头行、行范围、列范围、Schema profile、字段候选和
   evidence 的控制引用；`typed_value` 始终为空，候选不是业务事实、来源绑定或证据记录。
4. 明确 RAG 摘要继续归 Stage060；本切片不生成摘要、不以摘要替代事实，也不形成数值统计。

## 白箱边界

- `fact_id`、字段名、单位、日期、设备、材料和质量结果均为 `*:control:*` 形式的控制引用，
  不是已识别的真实字段或业务值。
- 输入形状、引用、格式、Schema profile、字段候选或记录类型不匹配时返回 `REJECTED`；不返回
  候选、来源引用或内容。
- 本切片不打开、检测或解析 XLSX/CSV；不读取真实生产记录、质检记录、授权 fixture、来源正文或
  物理路径；不连接数据库，不写事实、RAG、manifest、evidence ledger、audit、报告或持久状态。
- 真实 Schema 推断、真实字段识别、真实事实抽取、typed value、数据质量、真实来源/证据绑定分别仍受
  Stage058、Stage059 后续受控步骤、Stage061 与 Stage062 的冻结门约束。
- Agent、模型调用、模型 Token、本地服务、OVH、生产、上传和推送保持关闭。

## 运行与验证

```bash
python3 -B -m unittest -q KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.test_stage059_fact_extraction_slice
```

该命令只运行固定控制记录的纯内存逻辑。它不是 XLSX/CSV 真实解析、真实字段识别、真实事实提取、
来源或证据验证、数据质量验证、数值统计、RAG 写入或生产验收的证据。

## 回滚

只回滚本 P2 说明、切片模块、切片合同、聚焦用例、machine run、事件、事实投影、治理路线和生成中文
视图，回到 `PHASE1_FACT_EXTRACTION_BASELINE_CONTRACT_RUNTIME_DISABLED`。不得改动原始资料、manifest、
evidence ledger、audit log、已交付报告、数据库、GitHub、OVH 或应用状态。
