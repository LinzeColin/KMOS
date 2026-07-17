# Owner 上云清单——你本人只剩这些（一页纸）

> 打通线 goal 子条件②「本地不运行的技能全部依赖云端运行」。
> 治理原则（你 2026-07-18 定）：统一治理、降复杂度、不加第四件——**Coolify**（唯一部署面板）+ **Cloudflare**（域名/TLS）+ **OVH VPS**（主机）。
> 运行栈已在本机容器全量实证（arm64 + **amd64 目标架构端到端**六面全绿，见 `stage_artifacts/DT9_SKL0002_*`）；amd64 = OVH 同架构。云端部署件见 `KMFA/deploy/coolify/`。

## 基建线（operate 线）已/将做（不用你管）

- ✅ OVH Singapore VPS-1（amd64、Ubuntu 24.04、2vCore/3.7GB + 2G swap）已采购 + 接管 + 基线。
- ✅ **Docker 已就绪**（29.6.2，amd64）；Coolify 待就位。
- 连好下方 GitHub App 后，operate 线在 Coolify 建 project、登记 `KMFA/deploy/coolify/docker-compose.yml`、过容量 Gate、发 "P1-GO" → 我起 skills（dry-run），后按容量上 app。

## 👤 只有你本人能做的（都是点一下的小事）

### ① 点连 Coolify 的 GitHub App（一次，约 1 分钟）——现在就能做
在 Coolify 里授权连接你的 GitHub（`LinzeColin/KMOS`）；连好 operate 线才能登记资源。不依赖其它，随时可做。

### ② dws 设备码登录（钉钉手机点一次）——P1-GO 起容器后
skills 容器起来后，在 **Coolify → skills → Terminal** 我会跑：
```
dws auth login --device      # 你钉钉手机弹一次确认 → 点同意
```
之后无人值守（PAT 策略 + 保活由基座处理）。

### ③ Codex 应用停用 6 条旧排程（6 次点击）——现在就能做
这 6 条工作目录已删、每天空跑失败；**直接停用**，云端一刀接管：

| id | 名称 |
|---|---|
| `kmfa` | 每日钉钉考勤检查｜晨报 |
| `kmfa-3` | 每日钉钉考勤检查｜晚报 |
| `kmfa-4` | 钉钉工作检查 |
| `kmfa-5` | 资金周报自动化 |
| `kmfa-dws` | 上游每日钉钉 DWS 归档 |
| `dws-auth-keepalive-2` | DWS 认证保活 |

停完回一句「停了」，我把契约 `KMFA/metadata/automation/codex_app_schedules.contract.toml` 同步 DISABLED（PR 进仓）。

## 一条 DNS（你或基建线，1 分钟；上 App 面板时才需要）

Cloudflare 加一条**代理（橙云）**记录 `kmfa` → OVH 公网 IP（或按 Coolify 提示的 CNAME）。App 经 Coolify Traefik 出网，主机零额外开放端口。skills 栈纯出站、不需要这条。

## 做完之后（我来，不用你管）

测试发送给**张霖泽**核收发 → 全技能 `KMFA_DELIVERY_ENABLED=0` dry-run 双跑 ≥3 天 → 无异常切 `=1` 正式投递 → 起 App 面板 `kmfa.linzezhang.com`。详细分批步骤：`KMFA/deploy/coolify/README.md`。

> 另有一件**不挡上云**的挂你名下：BLK-001（273 行字段逐条确认）——只挡 A 级报告，不急。
