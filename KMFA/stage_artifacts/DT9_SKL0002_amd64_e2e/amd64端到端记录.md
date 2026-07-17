# 部署件 amd64（OVH 目标架构）端到端实证记录（2026-07-18）

Owner 2026-07-18 拍板：不等下批数据，用现有数据在**真实上云目标架构**上证明"准确/能用/跑通全流程"；上云目标由 Oracle A1（arm64）改为 **OVH VPS（amd64/x86_64）**。本记录是 amd64 目标架构上的真构建 + 容器内真跑证据，并附本次暴露的一个真 bug 及其修复与防回归守卫。

本机 Apple Silicon + Docker 29.6.1 buildx（`linux/amd64` 经 qemu 跨架构构建/运行）。镜像 tag `kmfa-skills:amd64-wt`，构建上下文 = `KMFA/deploy/skills-runtime/`（worktree `kmfa/ovh-amd64-e2e-proof`）。

## 一、真构建（amd64）——全绿

- 基镜像 `python:3.12-slim-bookworm` 多架构清单，amd64 变体拉取正常。
- Python 依赖**全部解析到 x86_64 轮子**并安装成功：`numpy-2.5.1…manylinux…x86_64`、`onnxruntime-1.27.0…x86_64`、`opencv_python-5.0.0.93…x86_64`、`rapidocr-onnxruntime-1.4.4`、`pillow/pytesseract/openpyxl/pyyaml/requests` 等（onnxruntime 曾是 arm 外唯一存疑点，x86_64 轮子齐备）。
- **`install_dws.sh` 在 amd64 下自证**：下载 `dws-linux-amd64.tar.gz` → SHA-256 命中锁文件 `b7dfd9a4…`（不匹配即非零中止）→ 安装 → `dws version v1.0.52 (4e59f9a, 2026-07-15)` 真跑输出。即 amd64 dws 二进制"下载 + 校验 + 可执行"三合一通过。
- 镜像导出成功：`kmfa-skills:amd64-wt`（manifest list `sha256:1cd3278b…`）。

## 二、容器内运行时（amd64 = x86_64）——全绿

| 项 | 命令 | 实测 |
|---|---|---|
| 目标架构 | `uname -m` / `python -c platform.machine()` | `x86_64` / `x86_64` |
| dws 可执行 | `dws --version` | `dws version v1.0.52 (4e59f9a)` |
| 对账归一自检 | `recon_common.py --selftest` | `全部通过` |
| 材料三层匹配自检 | `material_matcher.py --selftest` | `全部通过` |
| 断言证据自检 | `evidence_check.py --selftest` | `全部通过` |
| **技能端到端** | `run_skill.sh self-audit`（只读挂真仓 → tar 影子 → 三门） | **rc=0**：证据链 30/30 零悬空、血缘 FRESH、双平面 4 项目全绿 |

self-audit 台账：`{"skill":"self-audit","rc":0,"ts":"2026-07-18T05:28:56+08:00",…}`——时间戳 **+08:00**，即技能日志/报表日期按北京时间（见下节 TZ 修复）。只读挂载 + tar 影子路径同时复证了旧「双平面门只读原地重渲染崩」雷在 amd64 下仍被绕开。

## 三、本次暴露并修复的真 bug：运行时 TZ 被悉尼覆盖

- **现象**：`Dockerfile` 已锚 `TZ=Asia/Shanghai`（#100）、`crontab.txt` 明写"钟面 = 容器 TZ Asia/Shanghai"（#108），但 `docker-compose.yml` 的 `environment.TZ` 仍是历史遗留 `Australia/Sydney`（本目录 2026-07-17 `../DT9_SKL0002_deploy_precheck/预检记录.md` 第 18 行即录得容器时区为悉尼）。compose 的 `environment` 在**运行时覆盖**镜像 ENV。
- **影响**：glibc `localtime()` 认 `TZ` 环境变量 → vixie-cron 按悉尼评估排程（晨报 10:35 变悉尼时刻 → ≈北京 07:35-08:35）、技能内 `datetime.now()`/`date` 全走悉尼 → 抵消 #100/#108 的北京业务锚。arm64 预检未抓到：预检走 `run_skill.sh` 直调、未观测 cron 的挂钟触发时刻。
- **修复**：① `docker-compose.yml` → `TZ: Asia/Shanghai`（与 Dockerfile 一致，附注释禁止再覆盖）；② `entrypoint.sh` 加**快速失败守卫**——启动即校验 `date +%z`，非 `+0800` 立即拒启并指明病因，杜绝此类回归静默发生。
- **守卫正反实测（amd64 容器）**：
  - 正向（默认）：`date +%z` = `+0800`，放行。
  - 负向（`-e TZ=Australia/Sydney`）：守卫打印"拒绝启动：容器挂钟偏移 +1000（TZ=Australia/Sydney），业务锚要求 +0800…"，容器 **exit 1**。

## 四、诚实边界（本次未跑 = 结构性等 dws 设备码 / 真实输入，非缺陷）

- `attendance-morning/evening`、`test_send.sh`、`upstream-archive` 的**真实投递/抓取**需 `dws auth login --device`（Owner 手机确认一次）——即"云端三件套②"，是实例日边界，非本地可自证。本次已证 dws 二进制在 amd64 可执行、契约测试收件人 = 张霖泽的解析入口就绪。
- `work-check-morning/evening` 需真实 `DWS_Outputs.zip`（钉钉导出；SKL.0004 曾以真实输入 dry-run 演练通过，见 DT 演练档）；仓内无样例输入，本次不重跑。
- 结论：**凡不依赖 dws 在线态 / 外部输入的环节，已在 amd64 目标架构容器内端到端跑通并全绿**；其余环节在实例日 dws 设备码到位后即接续（runbook 见 `../../deploy/skills-runtime/OWNER三件套.md`）。

## 结论

OVH（amd64）目标架构上，**构建 / 依赖 / dws 二进制 / 时区正确性 / 对账正确性 / 技能端到端**六面均实测通过，并顺带修掉一个会静默漂移排程时刻的 TZ 覆盖 bug + 加了防回归守卫。实例日无已知构建 / 架构风险。预检镜像本机随后清理，实例日按 `bootstrap.sh` 在原生 amd64 上重新构建（无需 qemu）。
