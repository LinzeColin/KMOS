<!-- 机器平面根说明。英文随意，Owner 不看这里。 -->

# machine/ —— 机器平面与运行证据导航

人类平面 `../文档/` 的每个字段必须能回到 `canonical_facts.yaml`、`acceptance_contract.yaml`、`task_graph.yaml`、`traceability.csv`（v1.5.2 交付合同）或 `facts/`（旧业务状态）。产品版本、Git/制品/部署身份与 writer 边界另有明确 namespace，见 `runs/AUTHORITY_REGISTER.md`；本 README 只导航，不是事实源。

## 目录

| 目录 | 装什么 | 现状 |
|---|---|---|
| `canonical_facts.yaml` | v1.5.2 delivery 产品合同的 sealed Canonical Facts | P2.1 已按任务包原字节落入；唯一 writer 为 `WR-TASKPACK-PUBLISHER` |
| `acceptance_contract.yaml` | 49 个主 Acceptance 及确定性 Oracle | P2.3 已按任务包原字节落入；字段完整率由 focused gate 校验 |
| `task_graph.yaml` | 14 Stage / 56 Task 的 sealed DAG 输入 | P2.3 作为引用闭环所需输入按原字节落入；循环与完整包门禁留给 P2.4 |
| `traceability.csv` | 49 条 Requirement→AC→Oracle→Task→Test→Artifact→Owner 精确投影 | P2.3 已按任务包原字节落入；断链必须为 0 |
| `facts/` | 14 个既有业务状态事实（status/features/flows/plan/acceptance/ops/blockers/changelog...） | 已填充；描述旧业务状态域，不代表 v1.5.2 delivery 进度 |
| `runs/` | compact public-safe receipts；完整日志与制品外置 | 已含清理交接、P0.1-P0.4、S00 Stage Review、P1.1-P1.4、S01 Stage Review、S02/P2.1-P2.3 记录 |
| `tools/` | 既有双平面门、P2.3 focused trace gate 与渲染器 | 已装；完整 taskpack validator/CI 留给 P2.4 |
| `legacy/` | v0.1.4 遗留记录指针（就地引用，未搬动，见其 README） | 指针 |

## 当前门禁（`tools/`）

```bash
cd KMFA
python3 machine/tools/check_traceability.py     # P2.3：AC 字段与端到端引用闭环
python3 machine/tools/render_human.py        # 从 Canonical Facts + 14 个旧 facts 重渲染七文件
python3 machine/tools/check_doc_budget.py    # 体积门 + 中文门 + 纯净门
python3 machine/tools/check_blocker_stop.py  # 阻塞重审门
```

仓库级入口是 `python3 KMFA/machine/tools/check_dual_plane_ci.py --root . --projects KMFA --require-projects`。它校验精确七文件、Canonical 逐值投影、重渲染零漂移，并通过 renderer fail closed 复用 P2.3 trace gate，再执行文档预算与 blocker 门；P2.4 仍须安装完整 taskpack validator 与显式 CI 接入。结构通过不代表旧业务数据已解除 `BLK-001`，也不代表 v1.5.2 Stage 已通过。

## Authority boundary

- `facts/*` 是旧业务状态域的 writer；`文档/*` 只能由 renderer 生成。
- `canonical_facts.yaml`、`acceptance_contract.yaml`、`task_graph.yaml` 与 `traceability.csv` 是 v1.5.2 delivery namespace；它们与任务包 sealed bytes 一致，不得把 receipt、旧 facts 或手写文档变成第二 writer。
- v1.5.2 的产品合同、AC、Task DAG、Traceability 与 release policy 来自已授权 sealed taskpack，不写进旧业务 facts 伪装同一进度。
- `runs/*` 只保存 compact evidence/authority mapping，不得反向成为产品或业务事实 writer。
- 当前 delivery phase 看 `../HANDOFF.md`；产品版本看 `../VERSION`；published source 看 GitHub `main`；生产制品看 deployment manifest。
- S02/P2.2 已把 Canonical Facts 与旧业务事实按职责单向投影到恰好七文件；P2.3 又把 AC/Task DAG/Traceability 精确投影到 `05`。taskpack `human/*` 仅是 reference，不复制到仓库。派生规则见 `runs/S02_P21_CANONICAL_FACTS.md`，验证见 `runs/S02_P22_HUMAN_PLANE.md` 与 `runs/S02_P23_TRACEABILITY.md`。
