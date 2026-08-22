# Stage086 Phase 3 · 混合排序受控场景验证

## 本轮目标

本阶段只在进程内重放 Stage086 P2 已冻结的六条固定、非业务、`reference-only` 控制投影，形成八个可验证场景：关键词基线、材料牌号、设备型号、标准号、语义相似、六维过滤组合、Top-K／排序解释／结果有效性，以及旧索引服务期间的版本轨迹。材料牌号、设备型号、标准号和语义相似都只表示场景类别；查询、候选、选择、资料质量、新鲜度、业务模块、分数、过滤、模型、版本、维度、相似度度量、活动索引版本、轨迹和证据账本均为不透明控制标签。

完成条件是：P3 合同、纯内存场景模块、聚焦测试、精确历史白箱后继、机器事实和中文视图一致证明所有实际运行计数为零、所有运行闭锁字段为 `false`，并把路线推进到 `IDS-STAGE086-P4-GATE`。到达该门即停止，不进入 P4。

## 唯一权威与控制输入

- 冻结 Stage086 任务包、Stage085 Review／P1--P4 已审核元数据过滤控制工件，以及 Stage086 P1/P2 是唯一合同上下文；真实资料、原始元数据、manifest、证据账本、审计记录、数据库、索引和业务结论继续由既有来源承担权威。
- 控制场景、中文反馈和本地报告只重放不透明控制引用，不能替代来源文档、业务线白箱审批、真实 trace 或业务事实，也不建立第二权威事实源。
- 允许输入仅为 P2 的六条固定引用：`keyword_document_type_filter_reference_only`、`keyword_year_filter_reference_only`、`hybrid_project_filter_reference_only`、`hybrid_equipment_filter_reference_only`、`hybrid_metadata_status_filter_reference_only` 与 `hybrid_evidence_level_filter_reference_only`。
- 禁止输入业务正文、真实材料牌号、真实设备型号、真实标准号、真实文件路径、URL、数据库连接、OVH 运行参数或任何模型／Agent 参数。

## 八个控制场景

| 场景 | P2 控制引用 | 控制结论 |
| --- | --- | --- |
| 关键词基线 | `keyword_document_type_filter_reference_only` | 关键词与向量基线都已声明，不能退化为只依赖向量相似度。 |
| 材料牌号 | `keyword_year_filter_reference_only` | 仅验证材料牌号场景类别的关键词控制路径；未读取真实牌号。 |
| 设备型号 | `hybrid_equipment_filter_reference_only` | 仅验证设备型号场景类别的混合控制路径；未匹配真实型号。 |
| 标准号 | `hybrid_project_filter_reference_only` | 仅验证标准号场景类别的混合控制路径；未读取真实标准。 |
| 语义相似 | `hybrid_evidence_level_filter_reference_only` | 仅验证已声明向量合同和关键词基线并存；未计算 embedding 或语义分数。 |
| 六维过滤组合 | 六条 P2 控制引用 | 仅确认文档类型、年份、项目、设备、资料状态和证据等级的控制标签齐备；未执行过滤。 |
| Top-K、排序解释与有效性 | `hybrid_metadata_status_filter_reference_only` | 仅确认请求、候选、五类评分输入、评分解释、选择、资料状态、向量合同和证据引用形状一致；未排序或选择。 |
| 旧索引服务版本轨迹 | `keyword_year_filter_reference_only` | 仅确认独立活动索引版本记录与 candidate、selected、trace 同链，且模型版本与相似度度量一致；未读取旧索引或写 trace。 |

## 白箱、失败关闭与恢复边界

所有场景均需业务线白箱人工处理；自动业务推荐、自动结果采纳、自动索引切换、自动参数写入和自动发布均禁止。P2 输出结构不完整、非固定输入、任一运行闭锁字段为 `true`、引用不再是控制标签、六维过滤或资料状态引用不完整、独立活动索引版本链不完整、五类评分输入引用缺失，或任一场景不满足预期时，P3 必须失败关闭并保留 P2 为最近可恢复点。

回滚只允许撤回 P3 的范围说明、合同、场景模块、聚焦测试、精确治理后继、机器事实、回执、生成中文视图与本交接；不得修改 P1/P2、Stage085 Review、冻结任务包、来源文档、证据账本、审计记录、数据库、索引、GitHub、OVH 或应用状态。

## 验证范围

本阶段通过 P3 聚焦单元测试及 P1/P2/P3 关联白箱、Stage060--086 历史白箱回归、Stage005 治理回归、两个既有批次复核、机器事实生成的中文文档一致性检查、`git diff --check` 与主树／唯一开发 worktree 审计完成本地验证。

上述验证不等于 PostgreSQL、FTS、BM25、pgvector、真实过滤、Top-K、排序、旧索引服务、业务线审批、OVH 部署、生产运行或发布验收。
