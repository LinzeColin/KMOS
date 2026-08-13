# Stage057 Phase 2 · XLSX/CSV 接入最小可运行切片

## 当前门

- 任务：`IDS-V0_1-STAGE057-P2`
- 验收：`ACC-STAGE-057`
- 前置：冻结 Stage057 任务包、Stage057 P1 静态合同与 Stage056 已复审工件。
- 后继：`IDS-STAGE057-P3-GATE`，只能由新的独立 run 进入。

## 本切片做什么

本切片只接受两条固定、非业务、reference-only 控制记录。每条记录严格使用 P1 的 12 个输入字段；其 `schema_profile_ref` 只选择本模块内已经声明的字段标识，不含表头、单元格值、公式、正文、真实路径或真实工作簿内容。

在内存中，切片会：

1. 选择生产记录 XLSX 控制 profile 或质量检验 CSV 控制 profile。
2. 识别 P1 已定义的字段语义，形成 2 个 schema 候选与 10 个字段候选。
3. 为每个字段候选投影 P1 的 19 字段事实形状；`typed_value`、单位、日期、设备、材料和质量结果均保持空值，候选不构成业务事实。
4. 为每条控制记录形成一个 metadata-only RAG 摘要候选。摘要候选只引用事实候选，不能替代事实层，也不能作为数值统计依据。

## 白箱边界

- 来源文档、工作表、行范围、列范围和证据引用会原样保留在候选中；它们是控制引用，不是物理路径、内容读取或已建立的证据记录。
- 数值字段只有 `measurement_value` 的字段类型候选；没有数值、没有事实存储、没有统计计算，也不允许模型根据文本猜测数值。
- 输入形状、引用、格式或 profile 不匹配时，结果为 `REJECTED`，不会返回候选或来源引用。
- 本切片不打开、检测或解析 XLSX/CSV，不读取真实生产记录、质检记录或授权 fixture，不连接数据库，不写事实、RAG、manifest、evidence ledger、audit、报告或持久状态。
- Agent、模型调用、模型 Token、本地服务、OVH、生产、上传和推送保持关闭。

## 运行与验证

```bash
python3 -B -m unittest -q KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.test_stage057_xlsx_csv_ingestion_slice
```

该命令只运行固定控制记录的纯内存逻辑。它不是 XLSX/CSV 真实解析、真实 schema 推断、真实事实提取、数据质量验证或生产验收的证据。

## 回滚

只回滚本 P2 说明、切片模块、切片合同、聚焦用例、machine run、事件、事实投影、治理路线和生成中文视图，回到 `PHASE1_XLSX_CSV_INGESTION_CONTRACT_RUNTIME_DISABLED`。不得改动原始资料、manifest、evidence ledger、audit log、已交付报告、数据库、GitHub、OVH 或应用状态。
