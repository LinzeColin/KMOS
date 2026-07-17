# KMFA HANDOFF

更新时间：2026-07-17（Australia/Sydney）

## 接管入口

- 唯一 GitHub 源码：`git@github.com:LinzeColin/KMOS.git`，branch `main`，项目目录 `KMFA/`。
- 推荐稳定 checkout：`/Users/linzezhang/Documents/Codex/KMOS`；其他机器可放在任意路径，脚本应从 `git rev-parse --show-toplevel` 发现仓库根。
- 旧 `/Users/linzezhang/CodexProject` 是事故隔离中的历史 checkout，push URL 已禁用；不要解锁、不要从其他旧 clone 绕过。
- 迁移前 736 行 handoff 保存在 `machine/legacy/HANDOFF_PRE_KMOS_20260717.md`，仅供历史取证，不是当前执行合同。

## 当前项目状态

- 机器事实源：`machine/facts/`；人类入口：`文档/`。
- 当前有效进度：`4/18`；当前业务任务 `S05-P3-T1`。
- 当前状态：`Q4 / D / NO_GO / 3-9-2-1`，源优先级链未接通，`lineage_complete=false`。
- Owner blocker `BLK-001`：8 份 PDF 加 1 份电子表格约 273 行字段尚未逐条确认。未解决前，不得把结构校验解释为业务完成。

## Repo 内 portable skills

1. `daily_routine_check_skill/`：钉钉工作检查，OneDrive `DWS_Outputs.zip` 只读输入。
2. `fund-weekly-analysis-skill/`：资金与税费周报，真实证据、OCR 复核和 no-simulation 门禁。
3. `kmfa-dingtalk-attendance-skill/`：考勤晨晚提醒与官方报表 final reconciliation。
4. `mgmt-monthly-report-skill/`：七输入槽位到 Excel/PDF 的月报流程。
5. `dingtalk-dws-archive-skill/`：DWS 全文件归档 public-safe 源码、模板和验证器。

## 私有恢复点

清理前快照位于 OneDrive：

```text
/Users/linzezhang/Library/CloudStorage/OneDrive-Personal/KMFA/cleanup_handoff_20260717/
├── dws_archive_project/
└── private_runtime/
    ├── daily_routine_check/
    ├── dingtalk_attendance/
    └── fund_weekly_analysis/
```

该目录包含真实运行状态，禁止提交 Git。DWS SQLite 已在源端和备份端执行 `PRAGMA quick_check`；最终文件数、hash 和验证结果以本次 GitHub 提交的 `machine/runs/20260717_cleanup_handoff.json` 为准。

考勤自然 automation 使用 immutable runtime：

```text
$HOME/Library/Application Support/Codex/KMFA/attendance-production/current
```

仓库状态只作诊断，不得替代 immutable release fingerprint 门禁。

## 清理保护清单

在远端 parity、OneDrive 快照校验和本机 automation cwd 更新全部完成前，不得删除：

- 推荐稳定 checkout `/Users/linzezhang/Documents/Codex/KMOS`；
- 上述 OneDrive `cleanup_handoff_20260717/`；
- OneDrive `DWS_Outputs.zip`、`DWS_Archive/` 与既有 `KMFA/` 私有目录；
- attendance immutable runtime；
- `~/.codex/automations/`、`~/.codex/skills/`、DWS 认证 profile 与自动化 memory/state；
- `~/Downloads/KMFA_MetaData`。

旧 checkout 可否删除必须以本 handoff 的最新 run result 为准；本文件本身不授权删除。

## 验证与停止条件

最小接管验证：

```bash
git status --short --branch
git fetch origin main
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
python3 KMFA/machine/tools/check_dual_plane_ci.py --root . --projects KMFA --require-projects
python3 KMFA/daily_routine_check_skill/tools/validate_skill_package.py
python3 KMFA/fund-weekly-analysis-skill/tools/validate_taskpack.py
python3 KMFA/kmfa-dingtalk-attendance-skill/tools/validate_skill_package.py
python3 KMFA/mgmt-monthly-report-skill/tools/validate_skill_package.py
python3 KMFA/dingtalk-dws-archive-skill/tools/validate_skill_package.py
```

遇到 secret/private 命中、远端非预期提交、非 `main`、SQLite 损坏、OneDrive 快照不完整或 automation 指向已删除路径时立即停止，不得伪造接管完成。
