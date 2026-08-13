# Stage062 Phase 4 · 表格证据绑定交付、回滚与中文反馈

状态：`phase4_completed_review_pending`  
任务：`IDS-V0_1-STAGE062-P4`  
下一门：`IDS-STAGE062-REVIEW-GATE`

## 本阶段的可验证结论

本阶段只从 Phase 3 的六类固定、非业务、`reference-only` 表格证据绑定控制场景派生下列 metadata-only 交付证据：

- 六个表格事实交付样例；
- 六个字段推断引用标签及其报告；
- 六条控制数据质量测试结果；
- 六条人工处理建议，其中合并单元格明确记录为无法识别的表格结构；
- 三条全局中文、业务线白箱确认提示；
- 返回 P3 control 状态的表格重解析和事实回滚说明。

样例仅保留 `table_evidence_binding_ref`、`binding_request_ref`、`fact_ref`、`evidence_id`、`document_id`、`sheet`、`row`、`column` 与 `source_uri` 的 `:control:` 引用形状。它们不包含真实 URL、物理路径、来源正文、工作表、单元格、字段值、数值或业务内容；不会建立第二权威事实源。

## 业务线白箱边界

- 来源文档始终是唯一权威；P4 交付不能替代真实结构化事实、来源位置、证据记录、字段映射、质量结果或数值结论。
- 六个场景均要求业务线人工处理，自动确认、自动修正、自动绑定、自动写入和静默丢弃均未发生。
- 未验证数值、RAG 摘要和模型文本都不得形成确定性统计或业务结论。
- 中文反馈只说明控制边界和待人工确认事项，不作自动化、准确率或生产可用性承诺。

## 本地验证

- Stage062 P4 聚焦用例通过 `13/13`。
- Stage062 P4/P3/P2/P1、Stage061 Review/P4/P3/P2/P1、Batch051-060、Batch041-050 与 Stage060 Review 阶段链路回归通过 `119/119`。
- 两个批次检查器均返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`；Stage005 治理回归为 `valid=true`；中文事实投影已重渲染 `7` 个文件。

## 不在本阶段的范围

本阶段不读取、列举、复制、解析、统计或写入真实 XLSX/CSV、业务资料、原始元数据或授权夹；不推断真实 Schema/字段，不抽取或持久化结构化事实，不创建数据库、证据记录、事实库或第二权威源；不运行 Agent、模型或模型 Token；不启动本地服务、OVH、生产运行、GitHub 上传或推送。

## 重解析与回滚

未来若获得真实输入授权，必须先由业务线 owner 明确来源、授权 fixture、输入范围、字段规则、行列定位、证据绑定、事实存储、回滚点和恢复责任。当前只允许重放 P3 的固定 control 报告。

若 P4 派生交付不一致，只撤回本 P4 的说明、合同、纯内存模块、用例、machine run、事件、机器事实投影、路线和生成中文视图，恢复到 `PHASE3_TABLE_EVIDENCE_BINDING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED`；保留 P1/P2/P3 证据，不改变冻结任务包、真实资料、manifest、evidence ledger、audit log、事实库、数据库、GitHub、OVH 或应用状态。

## Stage062 Review 交接条件

下一独立 run 仅可进入 `IDS-STAGE062-REVIEW-GATE`，机械复审 P1--P4 的本地合同、控制报告、回滚边界和治理投影。该复审不自动授权真实资料访问、外部服务、OVH、生产运行或上传；全局上传仍延后至完整冻结任务包完成 `ACC-STAGE-168`。
