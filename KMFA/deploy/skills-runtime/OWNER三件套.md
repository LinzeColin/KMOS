# Owner 三件套——上云前你要做的全部事情（一页纸）

> 打通线（goal 子条件②「本地不运行的技能全部依赖云端运行」）只剩这三件是你本人才能做的。
> 运行栈已在本机容器内全量实证：arm64（构建/OCR/cron/告警）+ **amd64 目标架构端到端**（构建/依赖/dws 二进制/时区/对账/self-audit 六面全绿，并修掉一个 TZ 覆盖 bug），见 `stage_artifacts/DT9_SKL0002_*`。部署链 amd64/arm64 通用，做完三件当天即可上生产。

## ① 开一台云端 VPS（约 10 分钟）——你正在配的 OVH 即可

1. **OVH VPS**（或任意 Ubuntu 22.04/24.04 云主机）：≥2 vCPU / 4GB，架构 amd64 或 arm64 都行——部署链两架构通用。
   > OVH 标准 VPS 是 **amd64**：dws 二进制、容器镜像、Python/OCR 依赖均已按 amd64 就绪并出证，无需 ARM。（Oracle Always-Free A1 arm64 仍可作备选。）
2. SSH 公钥粘贴这一个（本机已备好私钥）：`~/.ssh/alpha_oracle_ed25519.pub` 的内容（密钥名沿用旧名不影响，OVH 建实例时贴进「SSH Key」即可）。
3. 建好后把**公网 IP + 登录用户名**（OVH 默认多为 `ubuntu` / `debian`）发我一句。后面全部由我来——实例上一条命令引导到位：
   `curl -fsSL https://raw.githubusercontent.com/LinzeColin/KMOS/main/KMFA/deploy/skills-runtime/bootstrap.sh | bash`

## ② dws 设备码登录（手机点一次）

实例上容器起来后，我会跑 `dws auth login --device`——你的钉钉手机上会弹一次确认，**点同意即可**。之后无人值守（PAT 策略与保活由基座处理）。

## ③ Codex 应用停用 6 条旧排程（6 次点击）

路线 B 已拍板（2026-07-17）：这 6 条的工作目录指向已删除的路径，正在每天空跑失败；**不修，直接全部暂停/停用**，由云端一刀接管。

| id | 名称 | 节奏（悉尼钟面） |
|---|---|---|
| `kmfa` | KMFA｜每日钉钉考勤检查｜晨报 | 每日 10:35 |
| `kmfa-3` | KMFA｜每日钉钉考勤检查｜晚报 | 每日 20:05 |
| `kmfa-4` | KMFA｜钉钉工作检查 | 每日 13:35 / 19:05 |
| `kmfa-5` | KMFA｜资金周报自动化 | 周一/周六 11:00 |
| `kmfa-dws` | KMFA｜上游每日钉钉DWS归档 | 每日 11:00 |
| `dws-auth-keepalive-2` | DWS Auth Keepalive｜钉钉认证保活 | 每 4 小时 |

停完回一句「停了」，我把契约文件 `KMFA/metadata/automation/codex_app_schedules.contract.toml` 同步成 DISABLED（PR 进仓）。

## 三件做完之后自动发生什么（都不用你管）

1. 双栈 `docker compose up` → dws 登录（即②）→ 给**张霖泽**发一条测试消息核收发。
2. 全部技能 `--dry-run` 双跑 **≥3 天**（`KMFA_DELIVERY_ENABLED=0`，只记日志不投递）。
3. 双跑无异常 → 切 `KMFA_DELIVERY_ENABLED=1` 正式投递。
4. 上线 `kmfa.linzezhang.com`：到时你在 Cloudflare 面板建一次 Tunnel + Access（约 5 分钟，含贴一个 token）——步骤与部署件已备好：`KMFA/deploy/cloudflared/README.md`。

> 之外还有一件**不挡上云**的事挂在你名下：BLK-001（273 行字段逐条确认）——它只挡 A 级报告，不挡技能上云，不急。
