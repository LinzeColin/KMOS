# KMFA HANDOFF

## v1.5.2 公开软件交付线（2026-07-22）

- 当前唯一执行基线：用户提供的 `KMFA_Product_Design_Taskpack_v1.5.2.zip`，SHA-256 `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`；产品/runtime 版本仍为 `0.1.4-one-time-github-main-upload`，两者禁止混用。
- 最近完成的唯一执行单元：`S00 / P0.4 / T-S00-04`。`AC-GOV-004` 已复验通过；20 项输入/权限/环境/配额均闭合为 `Ready 7 / Default 6 / Deferred-not-blocking 7`，14 项默认决策、8 个 Stage entry、普通场景 `6/6 CONTINUE`、Stop 场景 `4/4 FAIL_CLOSED` 与 `12/12` 协议字段见 `machine/runs/PREAUTHORIZED_INPUTS_CHECKLIST.md`。本 run 未启动 S00 Stage Review 或 S01。
- 当前状态：`P0.1 + P0.2 + P0.3 + P0.4 DONE`，但 **S00/G0 尚未通过**，必须整体复审、修复 findings 后才能上传。P0.1/P0.3 身份字段 `5/5`、唯一 production claim `1`、歧义 `0`；当前生产唯一链仍为 source `68306e850fa66ffe6b53622915ca81ff8ba98bf8`、image `sha256:adfc849b24e2efc471706c718377c97df07b41b4ce921f972e0cf598b0e25841`、Coolify deployment `boh5fsnxe82umwcpqzooam1p`、completed `2026-07-22T11:39:29.000000Z`；GitHub deploy/query runs 分别为 `29916233128` / `29916590384`。`STOP-S00-001` 已解决。
- Owner 提供的 `fb31e8e... / sha256:0b09ca... / qcq1q8m... / 2026-07-20T21:50:47Z` 已由 query run `29916243207` 原样复核，作为上一部署的回滚/溯源记录保留。收口前发现 `main` 已前进并自动产生新部署，因此没有把旧 tuple 冒充当前身份。
- v1.5 恢复 bundle `1ee7fb111` 仍是不可变兜底，SHA-256 `2d0b516f...` 且 verify PASS；另发现并核验历史仓公开 recovery ref 已前进至 `268acce792`，仍为 PARTIAL 且 S24 路径为 0。受保护 full-sweep 的 1060 路径已互斥分类为 `Adopt 239 / Redo 750 / Discard 71 / Conflict 0 / 未分类 0`；`Redo` 只表示按当前 v1.5.2 Task/AC 重做所需行为，不重建旧文件。未 replay、merge、force-push 或复制私有元数据。
- 旧业务 `machine/facts` 的 S05/A0/Q4/BLK-001 与当前 v1.5.2 delivery DAG 已分属不同 namespace：前者继续约束正式财务结论，后者决定本轮公开软件开发；14 个既有 facts 未在 P0.3 改写，七文件仍只由 renderer 生成。
- P0.4 保留了当前真实缺口：现有 App SQLite `/var/lib/kmfa/state` 未在 Coolify 挂耐久卷，生产关系数据库与 S3-compatible object adapter 均未实现；它们是 S05 entry 的 `Deferred-not-blocking`，不得提前冒充持久化完成。Cloudflare repo-managed mutation 通道、最终配额、完整浏览器/安全/观测能力也分别绑定 S03/S06/S10-S13 entry，普通缺参不得反复询问或暂停。
- 未完成：S00 Stage Review、复审问题修复与 S00 整体 GitHub upload；禁止跳级、phase 级上传或提前进入 S01。
- 下一步：下一个新 run 严格只执行整个 `S00 Stage Review`，重跑 P0.1-P0.4 的身份、恢复、权威、预授权与 G0 Gate，并修复所有复审 findings；全部通过后才整体上传 GitHub。不得在同一 run 顺带启动 S01。

下列既有交接主体更新时间：2026-07-17（Australia/Sydney）

## 接管入口

- 唯一 GitHub 源码：`git@github.com:LinzeColin/KMOS.git`，branch `main`，项目目录 `KMFA/`。
- 推荐稳定 checkout：`/Users/linzezhang/Documents/Codex/KMOS`；其他机器可放在任意路径，脚本应从 `git rev-parse --show-toplevel` 发现仓库根。
- 旧 `/Users/linzezhang/CodexProject` 是事故隔离中的历史 checkout，push URL 已禁用；不要解锁、不要从其他旧 clone 绕过。
- 迁移前 736 行 handoff 保存在 `machine/legacy/HANDOFF_PRE_KMOS_20260717.md`，仅供历史取证，不是当前执行合同。

## 当前项目状态（2026-07-17 深夜刷新：打通线执行态）

- 机器事实源：`machine/facts/`；人类入口：`文档/`（渲染产物，勿手写）。
- **打通线（DT1-DT9）**：canonical roadmap 见 `docs/governance/roadmap.yaml`；DT1 收官、DT4 吸收、DT5 主体实弹运转、DT8 门禁引擎试点、DT9 前置与基座齐备、DT6 App 可部署。
- **真实数据**：53 原始文件入 `KMOS/KMDatabase/data`（内容寻址）；私有派生层十一表 215,109 行（`KMFA/tools/` 全链零重建可复现，实证过；板表族首件税负率明细已入 `_staging.tax_composition`）。
- **证据档导航**：`stage_artifacts/索引.md`（打通线 76 档一表可查，断言表 `evidence_ref` 直跳）。
- **下批数据**：需求单已定稿 `docs/governance/下批数据需求单.md`（12 项，具体到导出选项；拉齐任一项即可机械复跑对应断言）。
- **对账**：《一致性证明与差异分析报告》第 1-7 号已交付（`stage_artifacts/DT5_DATA0019_report_no*`）；断言表 `metadata/quality/assertions.jsonl` 30 条（closed 族 19，证据链 30/30 零悬空）；**八切面零候选**（回款/开票/凭证/费用/税费/借款/材料/个人借支——每项闭案或挂单一数据依赖）——回款 7/11 月 0 分差、开票集团口径差 3 分、五账套凭证 0 不平、费用轴两大账套全窗口收口（湖北开明 2025-01..10 全解释含 07..10 段 8/8 根码 0 分差、武汉开明 01..10 十根码差额逐分归因零残留）、税费轴 36/39 格 0 分差、借款轴流量级闭合（窗口内新贷 0 分差+存量反推期初自洽，期初系统性缺失具名）、材料轴 117/190 凭证匹配（映射表 `metadata/quality/material_subject_map.json` 定稿）；对账基础设施 `tools/recon_common.py`（凭证号/科目双写法归一）；声明式门禁 `tools/gate_runner.py` 三门全绿。
- 旧口径提示：`4/18 / S05-P3-T1 / Q4 / D / NO_GO` 为 v1.5 业务线（S 系）状态，受 BLK-001 门控，与 DT 线并行存在；当前数据质量按 Q3（机器候选结构化）执行。
- Owner blocker `BLK-001`：8 份 PDF + 1 份电子表格约 273 行字段尚未逐条确认——**A 级报告的唯一人门**。未解决前，不得把结构校验解释为业务完成。
- **云端**：skills 运行基座与 App 部署件在 `KMFA/deploy/skills-runtime/` 与 `KMFA/app/`；等 Oracle ARM 实例 + `dws auth login --device` 一次 + Codex 应用停用 6 条旧排程（路线 B 已拍板）。实例日 runbook 见 deploy README。

## Repo 内 Skills（9 个，统一位于 `KMFA/skills/`）

1. `skills/每日工作检查/`（id `daily_routine_check_skill`）：钉钉工作检查，OneDrive `DWS_Outputs.zip` 只读输入。
2. `skills/资金周报/`（id `fund-weekly-analysis-skill`）：资金与税费周报，真实证据、OCR 复核和 no-simulation 门禁。
3. `skills/钉钉考勤/`（id `kmfa-dingtalk-attendance-skill`）：考勤晨晚提醒与官方报表 final reconciliation。
4. `skills/经营月报/`（id `mgmt-monthly-report-skill`）：七输入槽位到 Excel/PDF 的月报流程。
5. `skills/上游归档/`（id `dingtalk-dws-archive-skill`）：DWS 全文件归档 public-safe 源码、模板和验证器。
6. `skills/工资发放标准/`（id `gongzi-fafang-biaozhun`）：工资发放表模板复用与金额分校验。
7. `skills/红圈主合同/`（id `hongquan-main-contract-dws`）：红圈主合同导出、下载与归档。
8. `skills/信息费更新/`（id `info-fee-update`）：信息费申请表与历史明细更新。
9. `skills/项目成本表/`（id `project-cost-table-skill`）：项目成本输入门禁、双口径计算与工作簿生成。

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
python3 KMFA/skills/项目成本表/scripts/validate_skill_package.py
```

遇到 secret/private 命中、远端非预期提交、非 `main`、SQLite 损坏、OneDrive 快照不完整或 automation 指向已删除路径时立即停止，不得伪造接管完成。
