# Stage061 Phase 2 · 结构化数据质量最小可运行控制切片

## 当前门

- 任务：IDS-V0_1-STAGE061-P2
- 验收：ACC-STAGE-061
- 前置：冻结 Stage061 任务包、Stage061 P1 静态合同与 Batch051-060 本地复审工件。
- 后继：IDS-STAGE061-P3-GATE，只能由新的独立 run 进入。

## 本切片做什么

本切片只接受两条固定、非业务、reference-only 结构化数据质量控制记录。每条记录严格使用 P1
定义的 16 个输入字段；记录中只允许 `:control:` 形式的引用，不含表格、工作表、表头、单元格、
公式、正文、真实路径、业务事实或数值。

在内存中，切片会：

1. 严格核验生产 XLSX 控制引用和质量检验 CSV 控制引用是否符合 P1 的输入字段形状。
2. 对每条记录投影字段完整性、单位一致性、日期合法性、主键重复和异常值五类、共十条 P1
   定义的 18 字段质量结果控制候选。
3. 为每条候选保留字段、主键、事实集、来源文档、工作簿、工作表、表头行、行列范围和 evidence
   的控制引用；候选不是实际质量结果、实际事实、来源绑定或证据记录。
4. 所有候选均为 `UNASSESSED`，必须人工确认；未验证数值不能形成异常值、统计或确定性质量结论。

这实现冻结任务包 Phase 2 中结构化数据质量测试的最小受控分支。真实 Schema 推断、字段识别、
事实抽取、表格摘要与 evidence 绑定仍分别归 Stage058、Stage059、Stage060 和 Stage062；本切片
不改写其合同或创建第二权威事实源。

## 白箱边界

- source、workbook、worksheet、header-row、row-range、column-range、fact、field、primary-key、
  quality-profile 和 evidence 均为 `:control:` 形式的控制引用，不是已识别的真实字段、真实行列、
  业务值或真实来源位置。
- 输入形状、引用、文件类型、记录类型或记录顺序不匹配时返回 `REJECTED`；不返回候选、来源引用或
  内容。
- 本切片不打开、检测或解析 XLSX/CSV；不读取真实生产记录、质检记录、授权 fixture、来源正文或
  物理路径；不连接数据库，不写质量结果、事实、manifest、evidence ledger、audit、报告或持久状态。
- 控制候选不能成为第二权威事实源、事实库、数值统计依据或高可信证据；RAG 摘要不能替代结构化事实。
- Agent、模型调用、模型 Token、本地服务、OVH、生产、上传和推送保持关闭。

## 运行与验证

~~~text
python3 -B -m unittest -q KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.test_stage061_structured_data_quality_slice
~~~

该命令只运行固定控制记录的纯内存逻辑。它不是 XLSX/CSV 真实解析、真实字段识别、真实事实提取、
真实质量验证、来源或证据验证、数值统计、质量结果写入或生产验收的证据。

## 回滚

只回滚本 P2 说明、切片模块、切片合同、聚焦用例、machine run、事件、事实投影、治理路线和生成
中文视图，回到 `PHASE1_STRUCTURED_DATA_QUALITY_CONTRACT_RUNTIME_DISABLED`。不得改动原始资料、
manifest、evidence ledger、audit log、已交付报告、数据库、GitHub、OVH 或应用状态。
