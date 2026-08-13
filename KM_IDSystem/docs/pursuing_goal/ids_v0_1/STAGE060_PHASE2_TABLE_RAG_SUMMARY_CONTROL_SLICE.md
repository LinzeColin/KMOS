# Stage060 Phase 2 · 表格到 RAG 摘要最小可运行控制切片

## 当前门

- 任务：IDS-V0_1-STAGE060-P2
- 验收：ACC-STAGE-060
- 前置：冻结 Stage060 任务包、Stage060 P1 静态合同与 Stage059 已完成整阶段复审工件。
- 后继：IDS-STAGE060-P3-GATE，只能由新的独立 run 进入。

## 本切片做什么

本切片只接受两条固定、非业务、reference-only 表格摘要控制记录。每条记录严格使用 P1
定义的 13 个输入字段；记录中只允许控制引用，不含表格、工作表、表头、单元格、公式、正文、
真实路径、物理工作簿、实际事实值或摘要正文。

在内存中，切片会：

1. 严格核验生产 XLSX 控制引用和质量检验 CSV 控制引用是否符合 P1 的输入字段形状。
2. 投影两条 P1 定义的 10 字段中文 RAG 摘要控制候选，并保持每条候选与一个结构化事实引用分离。
3. 为每条候选保留来源文档、工作簿、工作表、行范围、列范围和 evidence 的控制引用；候选不是
   业务摘要、业务事实、来源绑定或证据记录。
4. 明确数值统计只能依赖未来带来源位置和证据绑定的结构化事实；候选没有摘要正文，不能替代事实
   或形成数值统计结论。

这实现冻结任务包 Phase 2 所允许的“表格摘要”最小受控分支；真实 Schema 推断、真实字段识别和
真实事实抽取不在本切片范围内，仍由 Stage058、Stage059 及后续已授权输入门负责。

## 白箱边界

- fact、summary、source、workbook、worksheet、row、column、schema 和 evidence 均为
  :control: 形式的控制引用，不是已识别的真实字段、真实行列、业务值或真实来源位置。
- 输入形状、引用、事实类别、摘要资格或记录顺序不匹配时返回 REJECTED；不返回候选、来源引用或
  内容。
- 本切片不打开、检测或解析 XLSX/CSV；不读取真实生产记录、质检记录、授权 fixture、来源正文或
  物理路径；不连接数据库，不写 RAG、事实、manifest、evidence ledger、audit、报告或持久状态。
- 候选只表达未来摘要接口与引用链，不能成为第二权威事实源、事实库、数值统计依据或高可信证据。
- Agent、模型调用、模型 Token、本地服务、OVH、生产、上传和推送保持关闭。

## 运行与验证

~~~text
python3 -B -m unittest -q KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.test_stage060_table_rag_summary_slice
~~~

该命令只运行固定控制记录的纯内存逻辑。它不是 XLSX/CSV 真实解析、真实字段识别、真实事实提取、
来源或证据验证、数据质量验证、摘要生成、数值统计、RAG 写入或生产验收的证据。

## 回滚

只回滚本 P2 说明、切片模块、切片合同、聚焦用例、machine run、事件、事实投影、治理路线和生成
中文视图，回到 PHASE1_TABLE_RAG_SUMMARY_CONTRACT_RUNTIME_DISABLED。不得改动原始资料、manifest、
evidence ledger、audit log、已交付报告、数据库、GitHub、OVH 或应用状态。
