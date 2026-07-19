# Owner 上云 · 你只剩 1 步（dws 设备码）

> 打通线 goal 子条件②「本地不运行的技能全部依赖云端运行」——**运行层面已达成**：skills 技能栈已在 OVH 云端跑起来、主机侧验证通过（dry-run）。真正往钉钉投递，只差你 dws 授权一次。
> 治理：Coolify（唯一部署面板）+ Cloudflare + OVH VPS；push main → 自动部署（Golden Path），你无需碰 Coolify 面板。

## ✅ 已完成（不用你管）

- OVH Singapore VPS-1（amd64 / Ubuntu 24.04 / 2vCore / 3.7GB+2G swap）+ Docker + Coolify 就绪。
- KMOS 经 **Golden Path 自动上云**：每次 push main → Coolify API 自动重部署（无需你碰面板）。
- **skills 云端运行 + 主机核验全绿**（#119 自包含镜像）：容器 `Up healthy`、完整仓烧进镜像、`date +%z=+0800`、`KMFA_DELIVERY_ENABLED=0`（dry-run 不投递）、`self-audit rc=0`（证据链 30/30、血缘 FRESH、双平面 5 项目、台账 +08:00）。
- 6 条旧 Codex 排程你已停用、契约同步 DISABLED（#112）。
- ~~连 Coolify GitHub App~~ **已免除**（KMOS 公开仓 + API 触发，不需要）。
- ~~一条 DNS~~ skills 无入站、无需域名；App 面板（P2）上线时才需一条 Cloudflare 记录。

## 👤 你只剩这一步：dws 设备码登录（钉钉手机点一次）

skills 现在是"空跑不投递"（dry-run）。要让它真的往钉钉发（考勤晨晚报 / 工作检查 / 资金周报等），需要你的钉钉授权一次：

- 基建线在 OVH 的 skills 容器里跑 `dws auth login --device`；
- **你钉钉手机弹一次确认 → 点同意**即可；
- 之后无人值守：云端 **每 4 小时自动跑 dws 保活**（`dws-keepalive`，无交互刷新 access-token；profile/state 落持久卷，容器重建不丢），保活失败会经告警面上报。
  > ⚠️ **认证有效期**：钉钉 **refresh 令牌本身约一个月到期**（本次至 **2026-08-18**）。保活只能在 refresh 有效期内自动续 access-token；refresh 到期那次需你**再点一次设备码**。届时保活会失败并告警，我会提醒你，不会静默断掉。
  > （历史教训：旧 Codex 排程 `dws-auth-keepalive-2` 停用后，云端一度**没有**任何保活——已于本次补上。）

## 做完 dws 之后（我来，不用你管）

给**张霖泽**发一条测试核收发 → 全技能 dry-run 双跑 ≥3 天 → 无异常切 `KMFA_DELIVERY_ENABLED=1` 正式投递。P2 再按容量上 App 面板 `kmfa.linzezhang.com`。

> 另有一件**不挡任何事**的挂你名下：BLK-001（273 行字段逐条确认）——只挡 A 级报告，不急。
