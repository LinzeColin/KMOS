# Stage061 Phase 3 · 结构化数据质量测试受控异常场景

## 本轮目标

本工件只重放 Stage061 P2 的两条固定、非业务、reference-only 质量控制输入与十条 `UNASSESSED` 质量候选，逐一覆盖冻结任务包规定的空表、合并单元格、单位混乱、日期格式不一、异常值和重复行六类异常场景。

每个场景都返回明确的人工处理处置；来源文档、工作簿、工作表、表头行、行列范围和 evidence 仅保留 `:control:` 引用形状。它们不代表真实文件、真实位置、真实表格质量、真实事实或已验证证据。

## 受控场景与处置

| 场景 | 控制处置 | 人工处理 |
| --- | --- | --- |
| 空表 | `REJECTED_EMPTY_TABLE_REQUIRES_HUMAN_HANDLING` | 必须 |
| 合并单元格 | `UNRECOGNIZED_STRUCTURE_REQUIRES_HUMAN_HANDLING` | 必须 |
| 单位混乱 | `UNVERIFIED_UNIT_REQUIRES_HUMAN_HANDLING` | 必须 |
| 日期格式不一 | `UNVERIFIED_DATE_REQUIRES_HUMAN_HANDLING` | 必须 |
| 异常值 | `UNVERIFIED_NUMERIC_CANDIDATE_BLOCKS_STATISTICAL_CONCLUSION` | 必须 |
| 重复行 | `DUPLICATE_PRIMARY_KEY_CANDIDATE_REQUIRES_HUMAN_HANDLING` | 必须 |

未验证数值始终关闭统计结论和模型确定性结论；控制引用不能替代结构化事实，也不能成为第二权威事实源。

## 可执行边界

- 实现：`structured_table_facts/stage061_structured_data_quality_scenarios.py`
- 合同：`structured_table_facts/stage061_structured_data_quality_scenarios_contract.json`
- 聚焦用例：`tests/test_stage061_structured_data_quality_scenarios.py`
- 本地运行记录：`KM_IDSystem/machine/runs/2026-08-14-stage061-p3-local.json`

本轮不读取、打开、检测、解析、评估、生成或写入真实 XLSX/CSV、生产记录、质检记录、fixture、工作表、表头、单元格、公式、来源正文、物理路径、事实库或数据库；不执行真实字段完整性、单位一致性、日期合法性、主键重复、异常值、质量门、统计、来源/证据绑定、持久化、Agent、模型调用、模型 Token、OVH、生产、上传或推送。

## 验收与回滚

本阶段的本地证据只证明：P2 固定控制候选可被重放，六类任务包异常均有显式人工处置，控制来源位置引用形状未丢失，且未验证数值不能成为统计或模型确定性结论。

本地验证通过：P3 聚焦用例 `13/13`；与 P2 切片、P1 合同、Batch051-060、Batch041-050 和 Stage060 Review 的聚焦兼容用例合计 `55/55`；两个批次检查器均返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`；Stage005 治理回归为 `valid=true`；中文事实投影已重渲染 `7` 个文件。

回滚只撤回本 P3 说明、场景合同、纯内存模块、聚焦用例、machine run、事件、机器事实投影、治理路线和生成中文视图，恢复到 `PHASE2_STRUCTURED_DATA_QUALITY_CONTROL_SLICE_RUNTIME_DISABLED`。P1/P2、冻结任务包、真实资料、fixture、事实库、数据库、GitHub、OVH 和应用状态均不改变。

下一步唯一允许项是在新的独立 run 进入 `IDS-STAGE061-P4-GATE`；本轮不进入 P4、整阶段复审、OVH、生产或上传。
