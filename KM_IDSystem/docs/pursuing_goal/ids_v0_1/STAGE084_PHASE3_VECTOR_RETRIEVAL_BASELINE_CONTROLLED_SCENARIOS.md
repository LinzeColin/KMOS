# Stage084 Phase 3 · 向量检索基线受控场景验证

## 目标与停止条件

本阶段只在进程内重放 Stage084 P2 已冻结的五条非业务、reference-only 控制投影，形成八个可验证场景：关键词基线、材料牌号、设备型号、标准号、语义相似、五维过滤组合、Top-K／排序解释／结果有效性，以及旧索引服务期间的版本轨迹。材料牌号、设备型号、标准号和语义相似均只表示场景类别；向量模型、版本、维度与相似度度量均为不透明控制标签，不携带、读取、匹配或计算任何业务值。

完成条件是：P3 合同、模块、聚焦测试、治理回归和机器事实一致证明所有实际运行计数为零、全部运行闭锁字段为 false，并把路线推进到 IDS-STAGE084-P4-GATE。到达该门禁即停止，不进入 P4。

## 唯一事实边界

业务资料、原始元数据、真实索引、真实检索结果、embedding、证据账本和审计记录仍由既有来源承担权威。本阶段的控制场景与中文反馈只是不透明控制标签的可复跑验证工件，不能替代来源文档、业务线白箱审批、真实 trace 或业务结论。

允许输入仅为 P2 的下列固定控制引用：

- vector_document_type_filter_reference_only
- vector_year_filter_reference_only
- hybrid_project_filter_reference_only
- hybrid_equipment_filter_reference_only
- hybrid_evidence_level_filter_reference_only

禁止输入业务正文、真实材料牌号、真实设备型号、真实标准号、真实文件路径、URL、数据库连接、OVH 运行参数或任何模型／Agent 参数。

## 八个控制场景

| 场景 | P2 控制引用 | 验证结论 |
| --- | --- | --- |
| 关键词基线 | vector_document_type_filter_reference_only | 关键词基线与向量基线均已声明，不能退化为只依赖向量相似度。 |
| 材料牌号 | vector_year_filter_reference_only | 仅验证材料牌号场景类别的控制路径；未读取真实牌号。 |
| 设备型号 | hybrid_equipment_filter_reference_only | 仅验证设备型号场景类别的混合控制路径；未匹配真实型号。 |
| 标准号 | hybrid_project_filter_reference_only | 仅验证标准号场景类别的混合控制路径；未读取真实标准。 |
| 语义相似 | hybrid_evidence_level_filter_reference_only | 仅验证已声明向量合同和关键词基线并存；未计算 embedding 或语义分数。 |
| 五维过滤组合 | 五条 P2 控制引用 | 仅确认五个过滤维度的控制标签齐备；未执行过滤。 |
| Top-K、排序解释与有效性 | hybrid_evidence_level_filter_reference_only | 仅确认请求、候选、评分解释、选择、向量合同和证据引用的形状一致；未排序或选择。 |
| 旧索引服务版本轨迹 | vector_year_filter_reference_only | 仅确认候选、选择和轨迹引用同一活动索引版本、模型版本与相似度度量；未读取旧索引或写 trace。 |

## 白箱、失败关闭与恢复边界

所有场景均需业务线白箱人工处理；自动业务推荐、自动结果采纳、自动索引切换、自动参数写入和自动发布均禁止。若 P2 输出结构不完整、不是固定输入、出现任一运行闭锁字段为 true、引用不再是控制标签、向量合同链不完整，或八个场景任一不满足预期，P3 必须失败关闭并保留 P2 为最近可恢复点。

恢复只允许撤回 P3 的范围说明、合同、场景模块、聚焦测试、治理事实、回执、生成中文视图与本交接；不能修改 P1/P2、Stage083 Review、冻结任务包、来源文档、证据账本、审计记录、数据库、索引、GitHub、OVH 或应用状态。

## 验证范围

本阶段通过下列本地纯内存或只读验证：

- P3 聚焦单元测试与 P1/P2/P3 关联白箱；
- Stage060--084 历史白箱回归；
- Stage005 治理回归与既有批次复核；
- 由机器事实生成的中文文档一致性检查；
- git diff --check 与主树／唯一开发 worktree 审计。

上述验证不等于 PostgreSQL、FTS、BM25、pgvector、真实过滤、Top-K、排序、旧索引服务、业务线审批、OVH 部署、生产运行或发布验收。
