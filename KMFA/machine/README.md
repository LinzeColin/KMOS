<!-- 机器平面根说明。英文随意，Owner 不看这里。 -->

# machine/ —— 机器平面与运行证据导航

人类平面 `../文档/` 的每个业务字段都必须能在 `facts/` 找到出处。v1.5.2 delivery 的授权 taskpack、产品版本、Git/制品/部署身份与 writer 边界另有明确 namespace，见 `runs/AUTHORITY_REGISTER.md`；本 README 只导航，不是事实源。

## 目录

| 目录 | 装什么 | 现状 |
|---|---|---|
| `facts/` | 14 个既有业务状态事实（status/features/flows/plan/acceptance/ops/blockers/changelog...） | 已填充；描述旧业务状态域，不代表 v1.5.2 delivery 进度 |
| `runs/` | compact public-safe receipts；完整日志与制品外置 | 已含清理交接、P0.1-P0.4、S00 Stage Review、P1.1 Customer PR/FAQ 及 P1.2 PRD/OKR 记录 |
| `tools/` | 三道门 + 渲染器 | 已装 |
| `legacy/` | v0.1.4 遗留记录指针（就地引用，未搬动，见其 README） | 指针 |

## 三道门（`tools/`）

```bash
cd KMFA
python3 machine/tools/render_human.py        # 从 14 个既有 facts 重渲染七文件
python3 machine/tools/check_doc_budget.py    # 体积门 + 中文门 + 纯净门
python3 machine/tools/check_blocker_stop.py  # 阻塞重审门
```

仓库级入口是 `python3 KMFA/machine/tools/check_dual_plane_ci.py --root . --projects KMFA --require-projects`。它重渲染后比较七文件并执行文档预算与 blocker 门；结构通过不代表旧业务数据已解除 `BLK-001`，也不代表 v1.5.2 Stage 已通过。

## Authority boundary

- `facts/*` 是旧业务状态域的 writer；`文档/*` 只能由 renderer 生成。
- v1.5.2 的产品合同、AC、Task DAG 与 release policy 来自已授权 sealed taskpack，不写进旧业务 facts 伪装同一进度。
- `runs/*` 只保存 compact evidence/authority mapping，不得反向成为产品或业务事实 writer。
- 当前 delivery phase 看 `../HANDOFF.md`；产品版本看 `../VERSION`；published source 看 GitHub `main`；生产制品看 deployment manifest。
- S02 会按其 Task/AC 建立 v1.5.2 canonical facts；在那之前不得提前迁移或覆盖现有 14 个业务 facts。
