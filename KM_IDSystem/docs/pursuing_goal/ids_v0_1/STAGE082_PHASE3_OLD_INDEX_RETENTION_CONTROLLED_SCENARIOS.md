# Stage082 Phase 3 · 旧索引保留策略受控场景重放

## 目标与停止条件

本阶段只将 Stage082 P2 已冻结的五条非业务控制引用在进程内重放为六个可验证场景：索引构建失败、影子冒烟失败、原子切换失败、回滚窗口未设值时的保留上一活动版本、后台构建期间检索隔离，以及 Operations／报告快照中的索引版本可见性。它不建立第二权威事实源，也不创建、读取、构建、查询、切换、回滚或清理真实索引。

完成本阶段的停止条件是：P3 合同、模块、聚焦测试、治理回归和机器事实均证明所有真实运行计数为零、全部运行闭锁字段为 `false`，并把路线推进到 `IDS-STAGE082-P4-GATE`。到达该门禁即停止，不进入 P4。

## 唯一事实边界

业务、索引和来源事实仍由既有源文档及其已登记机器事实承担权威。本阶段的控制场景、视图投影和中文反馈只是可复跑的验证工件，不能替代来源文档、业务线白箱审批、Operations 记录或报告快照。

允许的输入只有 P2 的以下五条固定 `:control:stage082-p2:` 引用：

- `fulltext_smoke_passed_retention_unconfigured_switch_candidate`
- `vector_background_build_incomplete_preserves_active`
- `hybrid_shadow_smoke_failure_blocks_switch`
- `fulltext_atomic_switch_failure_preserves_active`
- `hybrid_retained_previous_rollback_window_unconfigured`

禁止输入业务内容、真实文件路径、URL、原始元数据、数据库连接、OVH 运行参数或任何模型／Agent 参数。

## 六个控制场景

| 场景 | P2 控制引用 | 验证结论 |
| --- | --- | --- |
| 候选构建未完成 | `vector_background_build_incomplete_preserves_active` | 阻止切换，旧活动版本继续服务。 |
| 影子冒烟失败 | `hybrid_shadow_smoke_failure_blocks_switch` | 阻止切换，活动指针不变。 |
| 原子切换失败 | `fulltext_atomic_switch_failure_preserves_active` | 结果保持原活动版本，回滚与清理仍因未设值策略关闭。 |
| 回滚窗口未设值 | `hybrid_retained_previous_rollback_window_unconfigured` | 仅投影保留的上一活动版本，未实际回滚或清理。 |
| 后台构建检索隔离 | `vector_background_build_incomplete_preserves_active` | 仅核验控制投影；未执行并发检索。 |
| Operations／报告版本可见性 | `fulltext_smoke_passed_retention_unconfigured_switch_candidate` | 仅建立不透明控制引用，未写入 Operations 或报告。 |

## 白箱与恢复边界

所有场景都要求业务线白箱人工处理；自动业务写入、自动活动指针切换、自动回滚、自动旧索引清理和自动建议均为禁止。切换失败、构建未完成和冒烟失败时，旧活动版本必须在控制投影中连续服务。回滚目标只能是最低数量保留的上一活动版本；额外保留数量、回滚窗口、清理时点或业务线白箱批准未设值时，回滚与清理均保持关闭。

若 P2 输出结构不完整、不是固定输入、出现任一运行闭锁字段为 `true`、引用不再是不透明控制标签，或六个场景任一不满足预期，P3 必须输出失败结果并保留 P2 结果为最近可恢复点。恢复只允许撤回 P3 本阶段工件与治理事实，不能修改 P1/P2、Stage081 复核证据、任务包、来源文档或业务事实。

## 验证范围

本阶段通过下列本地只读／纯内存验证：

- P1/P2/P3 聚焦单元测试；
- Stage060–082 白箱回归；
- Stage005 治理回归与批次复核；
- 从机器事实渲染的中文文档一致性检查；
- `git diff --check`、任务包不变性、主树／开发树工作区审计。

上述验证不等于 OVH 部署、业务线审批、真实索引切换、真实并发检索、Operations 写入、报告发布或生产运行验收。
