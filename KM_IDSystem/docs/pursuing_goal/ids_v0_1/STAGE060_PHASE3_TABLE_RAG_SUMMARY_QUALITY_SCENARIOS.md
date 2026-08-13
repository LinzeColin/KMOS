# Stage060 Phase 3 · 表格到 RAG 摘要专项验证与异常场景

## 当前门

- 任务：`IDS-V0_1-STAGE060-P3`
- 验收：`ACC-STAGE-060`
- 前置：冻结 Stage060 任务包、Stage060 P1/P2 合同与 Stage059 已完成整阶段复审工件。
- 后继：`IDS-STAGE060-P4-GATE`，只能由新的独立 run 进入。

## 本切片做什么

本切片只重放 Stage060 P2 的两条固定、非业务、reference-only 表格摘要控制输入和两条
中文 RAG 摘要控制候选。空表、合并单元格、单位混乱、日期格式不一、异常值和重复行都只是
固定控制类别标签，不是表格、表头、单元格、行、列、公式、数值、日期、摘要正文或业务记录。

在内存中，切片会：

1. 严格核验 P2 的 `2` 条输入、`2` 条十字段中文 RAG 摘要控制候选、`2` 个事实引用、
   空摘要正文与每个候选的 `6` 项来源位置控制引用形状。
2. 对冻结任务包指定的六类异常分别给出显式处置；任何场景都不静默丢弃，且全部要求人工处理。
3. 为每个场景重放来源文档、工作簿、工作表、行范围、列范围和 evidence 的控制引用形状。
4. 阻断未验证数值的统计结论和模型确定性数值结论；摘要不能替代结构化事实或成为数值证据。

## 白箱边界

- 控制候选与所有来源位置均使用 `*:control:*` 引用；这些引用仅验证结构形状，
  不代表真实原始文件、工作表、行列位置或证据记录已被读取或验证。
- 不解合并单元格，不规范化单位或日期，不评估真实异常值或重复行，不生成摘要正文、真实
  structured fact、数值统计、RAG 摘要、来源绑定或 evidence record。
- 本切片不打开、检测或解析 XLSX/CSV；不读取真实生产记录、质检记录、授权 fixture、
  来源正文或物理路径；不连接数据库，也不写 RAG、事实、manifest、evidence ledger、audit、
  报告或持久状态。
- Agent、模型调用、模型 Token、本地服务、OVH、生产、上传和推送保持关闭。

## 运行与验证

```bash
python3 -B -m unittest -q KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.test_stage060_table_rag_summary_quality_scenarios
```

该命令仅重放固定控制引用和 P2 纯内存候选。它不是实际异常表格验证、真实来源可追溯验证、
摘要正文生成、事实抽取、数值统计、RAG 写入或生产验收的证据。

## 回滚

只回滚本 P3 说明、场景合同、纯内存模块、聚焦用例、machine run、事件、事实投影、
治理路线和生成中文视图，回到 `PHASE2_TABLE_RAG_SUMMARY_CONTROL_SLICE_RUNTIME_DISABLED`。
不得改动原始资料、manifest、evidence ledger、audit log、已交付报告、数据库、GitHub、
OVH 或应用状态。
