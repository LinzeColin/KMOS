# KMFA HANDOFF

## v1.5.2 公开软件交付线（2026-07-23）

- 当前唯一执行基线：用户提供的 `KMFA_Product_Design_Taskpack_v1.5.2.zip`，SHA-256 `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`；产品/runtime 版本仍为 `0.1.4-one-time-github-main-upload`，两者禁止混用。
- 最近完成的唯一执行单元：**S02 / P2.4 / T-S02-04**。新增只读 `machine/tools/validate_taskpack.py`、临时夹具负向套件、`machine/VALIDATION_REPORT.md` 并显式接入 `.github/workflows/dual-plane.yml`；正向仓库投影以 `49 Requirements / 49 AC / 14 Stages / 56 Phases / 56 Tasks / 49 trace rows`、0 errors/warnings PASS，缺 AC、闭合循环、第八治理文件、`EVIDENCE/` 四类变异 `4/4` 非零且错误可读，四个 sealed source hash 全程不变。fresh 官方 taskpack validator、P2.3 focused gate、五项目双平面与 workflow 解析均 PASS。见 `machine/runs/S02_P24_VALIDATOR.md`。这只完成 P2.4；未做 S02 全 Stage Review、GitHub CI、上传或部署。
- P2.3 的 sealed `acceptance_contract.yaml`、`task_graph.yaml`、`traceability.csv` 继续与任务包原字节一致（SHA-256 分别为 `1f07bd14…bc1`、`a9753e7c…306`、`ca369627…727`）；focused gate 保持 49 需求↔49 唯一主 AC、AC 必填字段 `735/735`、断链 `0`，`05_执行与验收.md` 继续机械投影 AC/Oracle/Task/Test/Artifact/Owner。见 `machine/runs/S02_P23_TRACEABILITY.md`。
- P2.2 的七文件渲染继续有效：14 决策、49 需求、49 指标及 49 个 Task/Owner seed 全覆盖；无 `human/` 副本、无第八权威文档。连续两次渲染哈希一致；受控手改 `00` 与临时第八文件均被精确拒绝并恢复/移除；术语排序漂移和 shared-checker 跨项目误约束均已修复，见 `machine/runs/S02_P22_HUMAN_PLANE.md`。
- P2.1 的 sealed `machine/canonical_facts.yaml` 继续保持任务包原字节，SHA-256 `5ae070cb4105e83eec0c05b3771759e550a67f1241708810f0b4430300198552`；唯一 writer 仍为 `WR-TASKPACK-PUBLISHER`，P2.2 只读渲染。
- 上一个完整 Stage 是 **S01 全 Stage Review**。P1.1–P1.4、四个 sealed Task Test 与问题/用户/价值/非目标/指标/观察期/经济判据/范围八项 Stage Gate 已整体重放；发现 `F-S01-001`：旧 10-path filter 会让纯 S01 治理上传误触生产 rebuild，现以 5 个 S01 精确路径修复并同步预授权，`total=1 / resolved=1 / open=0`。见 `machine/runs/S01_STAGE_REVIEW.md`；结论为 `S01 PASS / G1 pending S02`，不是 runtime/GA PASS。
- P1.1 的 12 FAQ/12 反证、P1.2 的 5 类用户/JTBD、10 步匿名旅程、P0 `12/12` + P1 `7/7`、`4 Objectives / 12 KRs`，以及 P1.3 的重大能力 `8/8`、低/基/高情景、敏感性、机会成本和 Kill 继续作为 P1.4 的冻结输入。工程总量沿用 task-level `58.5–106 engineer-days`，运行成本只作可重算公式；真实采用率、收益、账户账单、流量、容量与单点 ROI 均未伪造。2026-07-23 已只读刷新官方 R2 pricing/limits，实施和预算 Gate 仍须按当日账户与官方资料重取。
- 整个 S00 已完成复审、修复并上传：P0.1-P0.4、`AC-GOV-001/002/004`、S00 Stage Gate 与 `G0 Authority` 整体复验，4 个 findings 全部修复、open finding `0`，见 `machine/runs/S00_STAGE_REVIEW.md`；发布后的 `main` 为 `6a9f2163d00adc000e965bf6bffbc0ed59283d7a`。S01 中间 phase 只作本地 commit，不上传 GitHub。
- S01 发布已闭合：远端 `main=283a24080bce6590e902c77bb1fea20b19b990a7`，Dual-Plane run `29931423572` PASS，且该 SHA 没有 deploy run。published main 必须从 GitHub ref 实时读取，deployment source 必须从 Coolify manifest 实时读取，二者不得混用。
- 最新只读查询 run `29931489638` 证明生产唯一链仍为 deployment source `68306e850fa66ffe6b53622915ca81ff8ba98bf8`、image `sha256:adfc849b24e2efc471706c718377c97df07b41b4ce921f972e0cf598b0e25841`、Coolify deployment `boh5fsnxe82umwcpqzooam1p`、completed `2026-07-22T11:39:29.000000Z`；最新 deploy run 仍为 `29916233128`，S01 治理上传未触发新部署。
- Owner 提供的 `fb31e8e... / sha256:0b09ca... / qcq1q8m... / 2026-07-20T21:50:47Z` 已由 query run `29916243207` 原样复核，作为上一部署的回滚/溯源记录保留。收口前发现 `main` 已前进并自动产生新部署，因此没有把旧 tuple 冒充当前身份。
- v1.5 恢复 bundle `1ee7fb111` 仍是不可变兜底，SHA-256 `2d0b516f...` 且 verify PASS；另发现并核验历史仓公开 recovery ref 已前进至 `268acce792`，仍为 PARTIAL 且 S24 路径为 0。受保护 full-sweep 的 1060 路径已互斥分类为 `Adopt 239 / Redo 750 / Discard 71 / Conflict 0 / 未分类 0`；`Redo` 只表示按当前 v1.5.2 Task/AC 重做所需行为，不重建旧文件。未 replay、merge、force-push 或复制私有元数据。
- 旧业务 `machine/facts` 的 S05/A0/Q4/BLK-001 与 v1.5.2 delivery Canonical Facts 分属不同 namespace：前者继续约束正式财务结论，后者由 sealed taskpack 的 `WR-TASKPACK-PUBLISHER` 唯一写入；14 个旧 facts 未改写，七文件只由 `WR-RENDER-HUMAN` 全量生成。旧运维快照中的 Access/私有入口步骤已明确标为历史取证，不得当作 v1.5.2 发布指令。
- P0.4/S00 继续保留真实失败基线：现有 App SQLite `/var/lib/kmfa/state` 未挂耐久卷，生产关系数据库、S3-compatible object adapter 与 backup/restore 均未实现，所以当前有限 RPO/RTO 不可证明，按 `unbounded/not recoverable` 处理。Taskpack 的 5 项 S00 unknown 已 `5/5` 绑定现状、默认动作、owner 与后续硬 Gate；这不会被伪报为 durable PASS。
- 当前总进度：Task `12/56`，已完成 Stage `2/14`，S02 为 `4/4` phase、但尚未完成 Stage Review。2026-07-23 已有 fresh anonymous probes 对 `/`、`/ui`、`/ui/`、`/healthz` 全部返回 Cloudflare Access `302`；匿名完整使用、耐久 DB/object、任意文件安全上传下载、canary/rollback 等产品能力均尚未完成，不因 P2.4 structural PASS 提前宣称上线达标。
- 当前上传风险：`.github/workflows/deploy.yml` 的精确 `paths-ignore` 尚未覆盖 S02 candidate delta；现在上传可能误触生产 rebuild。下一个新 run 只能执行 **S02 whole-Stage Review**：整体重放 P2.1-P2.4/G1、复审最终 diff、解决全部 finding，补齐且负测精确治理路径后再一次性上传并核验 GitHub CI/no-deploy；该 run 不得启动 S03/P3.1，也不得提前把 `G1` 判 PASS。

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
