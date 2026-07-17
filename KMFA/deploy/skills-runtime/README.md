# KMFA Skills 云端运行基座（Oracle）

> **Owner 看这里** → 上云前只差你三件事，全部步骤见 [OWNER三件套.md](OWNER三件套.md)（实例/设备码/停排程，约 15 分钟）。
>
> 任务：`TSK.KMFA.SKL.0002`（含 `SKL.0008` dws 采用决定）｜建立：2026-07-17
> 目标：在产 skill 全部在 Oracle 云端运行——定时走容器内 cron，按需将来走 KMFA App 触发（DT6 之后）。
> 本目录全部为代码与模板，**不含任何凭据**；凭据只存在云主机 `/opt/kmfa/secrets/`（600 权限）。

## 架构（对齐任务包 09 第七节）

```
Mac 采集端（保留）                     Oracle 运行端（本基座）
 红圈浏览器导出（周六）  ┐
 OneDrive/Downloads 落地 ├→ KMOS/KMDatabase/data →(git pull)→ 容器内 cron 逐技能运行
 采集自动化（hash 入仓） ┘        │
                                  ├ 凭据：/opt/kmfa/secrets/skills.env（600，不入仓）
                                  ├ 日志与运行台账：/opt/kmfa/logs/、ledger.jsonl
                                  └ 失败告警：钉钉 webhook（配置后自动启用）
```

## dws 依赖的采用决定（SKL.0008，2026-07-17 落定）

- **采用官方 CLI**：[DingTalk-Real-AI/dingtalk-workspace-cli](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli)（钉钉官方开源、Go、macOS/Linux amd64/arm64），**固化版本 v1.0.52**（2026-07-15 稳定版），由 `install_dws.sh` 安装并记录 SHA-256。
- **无人值守认证**：`dws auth login --device`（设备码流，官方支持 Docker/SSH/CI 场景；一次性，需 Owner 在钉钉上确认），或自建应用模式 `--client-id/--client-secret`；跨机迁移可用 `dws auth export/import`。
- **守卫前置**（考勤代码 `dws_auth_guard.py` 的 READY 条件）：
  1. `dws pat browser-policy --enabled=false --format json --yes`（生成 `~/.dws/pat_policy.json`，`default.openBrowser=false`）
  2. 运行环境注入 `KMFA_DINGTALK_ATTENDANCE_ALLOW_DWS_COMMANDS=1`
- 备选方案（仅当官方 CLI 在 arm64 上不可用时启用）：Python 直连钉钉开放 API 的兼容 shim——调用面已锁定（chat message send / send-by-webhook / contact user search|get / attendance report 系列），暂不实现。

## 本机预检结论（2026-07-17，实例日风险已消除）

镜像与运行栈已在本机 `arm64`（与 Oracle A1 同架构）Docker **真构建 + 容器内真跑**验收：`dws v1.0.52` 可执行、SKL.0005 OCR 双引擎自检 PASS、crontab 8 条装载、健康检查 `healthy`、compose 校验通过。四颗构建期地雷（`flock` 假包名、`dws` 资产名、锁文件首次信任、`libGL` 缺失）已排掉——详见 `KMFA/stage_artifacts/DT9_SKL0002_deploy_precheck/预检记录.md`。实例日按下节步骤执行即可，无已知构建风险。

## 部署步骤（实例就绪后执行；下列 0-3 步可用同目录 `bootstrap.sh` 一键完成）

```bash
# 0) 前置：Ubuntu 22.04+ ARM（Oracle A1）。docker 未装则一行装齐：
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2 git && sudo usermod -aG docker "$USER"
# （usermod 后重新登录一次 shell 使组生效）
# 1) 拉仓（公开仓走 HTTPS，免密钥——alpha_oracle 私钥只用于登录实例，不是 GitHub deploy key）
sudo mkdir -p /opt/kmfa && sudo chown "$USER" /opt/kmfa && cd /opt/kmfa
git clone --filter=blob:none https://github.com/LinzeColin/KMOS.git
# 2) 凭据（600）：按 secrets.env.example 的键位写 /opt/kmfa/secrets/skills.env
install -m 700 -d /opt/kmfa/secrets && install -m 600 /dev/null /opt/kmfa/secrets/skills.env
# 3) 构建与启动
cd /opt/kmfa/KMOS/KMFA/deploy/skills-runtime
docker compose up -d --build
# 4) 一次性登录 dws（设备码，Owner 手机确认）
docker compose exec skills dws auth login --device
docker compose exec skills dws pat browser-policy --enabled=false --format json --yes
# 5) 测试投递（默认 dry-run；确认后加 KMFA_TEST_SEND_CONFIRM=1）
docker compose exec skills /opt/runtime/test_send.sh "张霖泽"
```

## 铁律（违反即停）

1. **双跑切换**：钉钉考勤先 dry-run 与现运行端并行比对 ≥3 天，一致后一刀切换发送权；**任一时刻只允许一个发送端存活**（防真实群双发）。切换前本容器内所有投递默认 `KMFA_DELIVERY_ENABLED=0`。
2. **凭据不入仓**：`/opt/kmfa/secrets/` 600 权限；本目录只有 `secrets.env.example`（仅键名）。
3. **可回收设计**（Owner 不开 PAYG，Always Free 闲置实例可能被 Oracle 回收）：本基座全部状态 = 仓库 + secrets 一个文件 + 数据卷日备份回 `KMOS/KMDatabase/data`——实例丢失后按「部署步骤」10 分钟内可原样重建，除 dws 重新登录外无其他手工步骤。
4. **时区**：容器 cron 钟面 = `Australia/Sydney`（与原 Codex 排程钟面一致；考勤代码内部对钉钉数据自会使用 Asia/Shanghai）。投产前时区口径需 Owner 确认一次。

## 排程表（crontab.txt，与原在产排程对表）

| 技能 | 原排程（悉尼钟面） | 说明 |
|---|---|---|
| 钉钉考勤 晨报 | 每日 10:35 | `run_skill.sh attendance-morning` |
| 钉钉考勤 晚报 | 每日 20:05 | `run_skill.sh attendance-evening` |
| 钉钉工作检查 | 每日 13:35 / 19:05 | `run_skill.sh work-check` |
| 每日工作检查（日检） | 每日 11:30 | `run_skill.sh daily-routine` |
| 资金周报 | 周一 / 周六 11:00 | `run_skill.sh fund-weekly`（先完成 SKL.0005 OCR 替换） |
| 经营月报 | 每月 1 日 09:00 + 按需 | `run_skill.sh mgmt-monthly` |
| 上游归档 | 每日 11:00 | `run_skill.sh upstream-archive`（v1.0.52 命令面核对后启用） |

> 初始状态：**全部技能以 dry-run 模式排程**（`KMFA_DELIVERY_ENABLED=0`），双跑验证通过并经 Owner 同意后逐技能置 1。

## 文件清单

| 文件 | 作用 |
|---|---|
| `install_dws.sh` | 固化版本安装 dws（arm64/amd64 自适应，SHA-256 记录于 `dws.sha256.lock`） |
| `Dockerfile` / `docker-compose.yml` | 运行容器：python3.12 + cron + dws |
| `crontab.txt` | 排程表（上表的机器形式） |
| `entrypoint.sh` | 校验 secrets 权限 → 装载 crontab → 前台 cron |
| `run_skill.sh` | 统一运行包装：flock 防重入、日志、台账 append、失败告警 |
| `healthcheck.sh` | 容器健康检查：cron 存活 + 台账新鲜度 |
| `test_send.sh` | 「张霖泽」测试投递（默认 dry-run） |
| `secrets.env.example` | 凭据键位清单（无值） |
