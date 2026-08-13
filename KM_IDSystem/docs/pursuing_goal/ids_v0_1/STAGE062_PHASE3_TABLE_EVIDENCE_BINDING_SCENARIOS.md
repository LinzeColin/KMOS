# Stage062 Phase 3 · 表格证据绑定受控异常场景

状态：`phase3_completed_local`  
任务：`IDS-V0_1-STAGE062-P3`  
下一门：`IDS-STAGE062-P4-GATE`

## 本阶段的可验证结论

本阶段机械重放 Phase 2 的两条固定、非业务、`reference-only` 控制请求和两条未绑定候选，并对下列六类受控异常类别给出显式处置：空表、合并单元格、单位混乱、日期格式不一、异常值、重复行。

- 六个场景均保留 `evidence_id`、`document_id`、`sheet`、`row`、`column`、`source_uri` 的控制引用形状。
- 六个场景均要求业务线人工白箱处理，静默丢弃数量为零。
- 异常值和任何未验证数值都不能形成统计结论或模型确定性数值结论。
- “可追溯”在本阶段只指控制引用形状被机械保留；没有打开真实文件、验证真实行列，也没有创建来源位置绑定或证据记录。

## 不在本阶段的范围

本阶段不读取、复制、解析、统计或写入真实 XLSX/CSV、业务资料、原始元数据或授权夹；不推断 Schema/字段、不抽取结构化事实、不创建数据库、持久化、事实库、证据记录或第二权威源；不运行 Agent、模型或模型 Token；不启动本地服务、OVH、生产运行、GitHub 上传或推送。

## 场景处置

| 控制类别 | 显式处置 | 自动修正/绑定 | 人工处理 |
| --- | --- | --- | --- |
| 空表 | `EMPTY_TABLE_REFERENCE_REQUIRES_HUMAN_HANDLING` | 否 | 是 |
| 合并单元格 | `MERGED_CELL_REFERENCE_REQUIRES_HUMAN_HANDLING` | 否 | 是 |
| 单位混乱 | `UNVERIFIED_UNIT_REFERENCE_REQUIRES_HUMAN_HANDLING` | 否 | 是 |
| 日期格式不一 | `UNVERIFIED_DATE_REFERENCE_REQUIRES_HUMAN_HANDLING` | 否 | 是 |
| 异常值 | `UNVERIFIED_NUMERIC_REFERENCE_BLOCKS_STATISTICAL_CONCLUSION` | 否 | 是 |
| 重复行 | `DUPLICATE_ROW_REFERENCE_REQUIRES_HUMAN_HANDLING` | 否 | 是 |

## 恢复与回滚

若本控制切片需要撤回，只撤回本 P3 的说明、合同、纯内存模块、用例、machine run、事件、机器事实投影、路线和生成中文视图，恢复到 `PHASE2_TABLE_EVIDENCE_BINDING_CONTROL_SLICE_RUNTIME_DISABLED`。不得改变冻结任务包、真实资料、P1/P2 工件、manifest、evidence ledger、audit log、事实库、数据库、GitHub、OVH 或应用状态。

## P4 交接条件

P4 之前仍需明确的、经授权的业务线白箱输入和人工责任边界。若真实来源、行列位置、字段、单位、日期、质量结果或证据无法确认，应保留本 P3 的人工处置结论，不得自动推进、写入或将控制标签表述为真实业务结论。
