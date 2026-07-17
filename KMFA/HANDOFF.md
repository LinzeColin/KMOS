# KMFA HANDOFF

更新时间：2026-07-17（Australia/Sydney）

## 接管入口

- 唯一 GitHub 源码：`git@github.com:LinzeColin/KMOS.git`，branch `main`，项目目录 `KMFA/`。
- 推荐稳定 checkout：`/Users/linzezhang/Documents/Codex/KMOS`；其他机器可放在任意路径，脚本应从 `git rev-parse --show-toplevel` 发现仓库根。
- 旧 `/Users/linzezhang/CodexProject` 是事故隔离中的历史 checkout，push URL 已禁用；不要解锁、不要从其他旧 clone 绕过。
- 迁移前 736 行 handoff 保存在 `machine/legacy/HANDOFF_PRE_KMOS_20260717.md`，仅供历史取证，不是当前执行合同。

## 当前项目状态（2026-07-17 深夜刷新：打通线执行态）

- 机器事实源：`machine/facts/`；人类入口：`文档/`（渲染产物，勿手写）。
- **打通线（DT1-DT9）**：canonical roadmap 见 `docs/governance/roadmap.yaml`；DT1 收官、DT4 吸收、DT5 主体实弹运转、DT8 门禁引擎试点、DT9 前置与基座齐备、DT6 App 可部署。
- **真实数据**：53 原始文件入 `KMOS/KMDatabase/data`（内容寻址）；私有派生层十表 204,697 行（`KMFA/tools/` 全链零重建可复现，实证过）。
- **对账**：《一致性证明与差异分析报告》第 1/2 号已交付（`stage_artifacts/DT5_DATA0019_report_no*`）；断言表 `metadata/quality/assertions.jsonl` 20 条（closed 12）；回款轴 7/11 月 0 分差、开票轴集团口径差 3 分、五账套凭证 0 不平；声明式门禁 `tools/gate_runner.py` 三门全绿。
- 旧口径提示：`4/18 / S05-P3-T1 / Q4 / D / NO_GO` 为 v1.5 业务线（S 系）状态，受 BLK-001 门控，与 DT 线并行存在；当前数据质量按 Q3（机器候选结构化）执行。
- Owner blocker `BLK-001`：8 份 PDF + 1 份电子表格约 273 行字段尚未逐条确认——**A 级报告的唯一人门**。未解决前，不得把结构校验解释为业务完成。
- **云端**：skills 运行基座与 App 部署件在 `KMFA/deploy/skills-runtime/` 与 `KMFA/app/`；等 Oracle ARM 实例 + `dws auth login --device` 一次 + Codex 应用停用 6 条旧排程（路线 B 已拍板）。实例日 runbook 见 deploy README。

## Repo 内 portable skills

1. `skills/每日工作检查/`（id `daily_routine_check_skill`）：钉钉工作检查，OneDrive `DWS_Outputs.zip` 只读输入。
2. `skills/资金周报/`（id `fund-weekly-analysis-skill`）：资金与税费周报，真实证据、OCR 复核和 no-simulation 门禁。
3. `skills/钉钉考勤/`（id `kmfa-dingtalk-attendance-skill`）：考勤晨晚提醒与官方报表 final reconciliation。
4. `skills/经营月报/`（id `mgmt-monthly-report-skill`）：七输入槽位到 Excel/PDF 的月报流程。
5. `skills/上游归档/`（id `dingtalk-dws-archive-skill`）：DWS 全文件归档 public-safe 源码、模板和验证器。

## 私有恢复点

agent 的私有恢复入口也在 GitHub：

```text
PRIVATE repo: LinzeColin/KMFA-Private-Runtime
Release:      cleanup-handoff-20260717
Manifest:     manifests/release_manifest.json
```

Release 包含 3 个经 SHA-256 校验的资产：旧 KMFA 开发/运行现场、DWS 全文件归档项目、6 张 Codex automation 的本机状态与旧 DWS skill 备份。PRIVATE 仓库的 `HANDOFF.md` 是恢复合同；任何 agent 都必须先确认仓库仍为 PRIVATE，再按 manifest 校验 size/hash。凭证、token、cookie、browser session、Keychain 导出和 `.env*` 明确不上传，恢复后重新认证。

OneDrive 同时保留冗余副本，但不是 agent 通信或唯一恢复入口：

```text
/Users/linzezhang/Library/CloudStorage/OneDrive-Personal/KMFA/cleanup_handoff_20260717/
├── dws_archive_project/
└── private_runtime/
    ├── daily_routine_check/
    ├── dingtalk_attendance/
    └── fund_weekly_analysis/
```

该目录包含真实运行状态；DWS SQLite 已在源端和备份端执行 `PRAGMA quick_check`。OneDrive 位置、文件数和校验结果已同步写入 public KMOS 与 private runtime repo，不能只依赖本机路径沟通。

旧脏工作区未直接合并到当前主线；其完整 KMFA 覆盖层已私有保存并通过 checksum 零差异验证：

```text
cleanup_handoff_20260717/legacy_worktrees/CodexProject_KMFA_overlay/
cleanup_handoff_20260717/legacy_worktrees/CodexProject-KMFA-S19_overlay/
```

考勤自然 automation 使用 immutable runtime：

```text
$HOME/Library/Application Support/Codex/KMFA/attendance-production/current
```

仓库状态只作诊断，不得替代 immutable release fingerprint 门禁。

## 本机接管结果

- 首轮公开接管提交：`64a4d7083be08ed6ef9169e585306464c2d06ec5`，已推送至 `origin/main`。
- Codex 已登记稳定项目 `/Users/linzezhang/Documents/Codex/KMOS`；6 张既有 automation 均已原位迁移到该项目，未创建重复任务。
- `kmfa` 10:35、`kmfa-3` 20:05、`kmfa-4` 13:35/19:05、`kmfa-dws` 每日 11:00、DWS auth 每 4 小时 20 分的计划保持不变；`kmfa-5` 已恢复技能合同规定的周一和周六 11:00。
- attendance immutable release 已原子切换至 fingerprint `eeb36084adcd39507597f5df6b273de4e8f1b18212234e2226eb3edb9d71255a`，source commit 为上述首轮接管提交；晨晚 live prompt 均通过只读一致性校验。
- 6 个本机 skill 名称均指向稳定 KMOS checkout；历史独立 DWS skill 已私有备份后由兼容别名接管。
- 未运行 live DWS、未发送钉钉消息；真实业务数据只进入 PRIVATE GitHub Release，public KMOS 无原始业务数据。

## 清理保护清单

public/private GitHub、OneDrive 冗余快照和本机 automation cwd 已完成校验。大清理时仍不得删除或改为 public：

- 推荐稳定 checkout `/Users/linzezhang/Documents/Codex/KMOS`；
- 上述 OneDrive `cleanup_handoff_20260717/`；
- OneDrive `DWS_Outputs.zip`、`DWS_Archive/` 与既有 `KMFA/` 私有目录；
- attendance immutable runtime；
- `~/.codex/automations/`、`~/.codex/skills/`、DWS 认证 profile 与自动化 memory/state；
- PRIVATE `LinzeColin/KMFA-Private-Runtime` 及 Release `cleanup-handoff-20260717`；
- `~/Downloads/KMFA_MetaData` 若后续重新出现则先只读核对；本次盘点该路径不存在。

旧 checkout 的 KMFA 内容已有私有覆盖层恢复点；删除旧 checkout 前仍应再次确认上述保护项存在且稳定 checkout 与 `origin/main` parity。本文不授权删除保护项。

## 验证与停止条件

最小接管验证：

```bash
git status --short --branch
git fetch origin main
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
python3 KMFA/machine/tools/check_dual_plane_ci.py --root . --projects KMFA --require-projects
python3 KMFA/skills/每日工作检查/tools/validate_skill_package.py
python3 KMFA/skills/资金周报/tools/validate_taskpack.py
python3 KMFA/skills/钉钉考勤/tools/validate_skill_package.py
python3 KMFA/skills/经营月报/tools/validate_skill_package.py
python3 KMFA/skills/上游归档/tools/validate_skill_package.py
```

遇到 secret/private 命中、远端非预期提交、非 `main`、SQLite 损坏、OneDrive 快照不完整或 automation 指向已删除路径时立即停止，不得伪造接管完成。
