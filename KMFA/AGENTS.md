# KMFA Agent Contract

本项目继承仓库根 `AGENTS.md`。任何 agent 接手前先读本文件、`HANDOFF.md` 和 `machine/facts/status.json`。

## 0. Owner 硬覆写（最高优先级，压过 sealed taskpack）

**冲突裁决顺序：Owner 在会话中的直接指令 > 本节 > v1.5.2 sealed taskpack > 其余一切文档。**
sealed 合同只在 Owner 没有另行指令的题目上有效；**下列条目 Owner 已直接指令，任何 agent 不得以「合同这么写」为由回退。**

- **O-1 根路径归属与已删除页面（2026-08-10 Owner 最终指令）**
  `/` = **KMFA 经营驾驶舱**（`app/frontend/src/App.jsx` 与 `index.html` 的驾驶舱兜底，标题 `KMFA｜经营驾驶舱`）。
  v1.5.2 里「`/` 是完整匿名 App Shell」**已被 Owner 覆写作废**；此前放在 **`/workspace`** 的匿名页面亦已被 Owner 明令删除。`/workspace`、`/workspace/` 及其任意子路径必须为 `404`，不得作为兼容入口、跳转页或备用壳复活。
  - 禁止新增或恢复 `PublicAppShell.jsx`、`public-shell.css`、`workspace_shell_fragment.html` 或任何 `/workspace` 页面路由。现有 walking-skeleton / anti-abuse API 不构成恢复该页面的授权。
  - 门禁：`app/backend/tests/test_root_is_the_app_not_a_brochure.py`。**它红了要改代码，不许改它来"修复"**；确需变更须 Owner 在会话中明说。
  - Owner 原话：「这根本不是我的东西 你不要搞这些恶心人的东西来恶心我」「主页还是没有恢复 我看到这个主页就恶心」「删除你之前添加的那个workspace页，不允许任何恢复」。
- **O-2 永不新建 repo。** 禁 `gh repo create`。一切私有数据进唯一私有库 `LinzeColin/Private-Database` 的 `Private-KMDatabase/` 分区；体量问题用 sparse / blobless clone 解决，不用开新仓。
- **O-3 测试期禁发钉钉群。** 未经 Owner 当场授权，投递收件人只能是**张霖泽本人**（个人通道）。安全态 = `KMFA_DELIVERY_ENABLED=0` **且** Coolify 内无群机器人凭据；一键恢复见 `.github/workflows/coolify-ops.yml` 的 `testing-safe-mode`。
- **O-4 本机零占用。** 禁 launchd / 本机定时任务 / 本机大缓存。定时与增量同步只能跑在云端容器（Coolify / GitHub Actions）。
- **O-5 原始数据只读。** `~/Downloads/KMFA_MetaData` 永不写、永不删。可删的只有"云端已存在的本地可重建副本"，且删前先证明云端已有。
- **O-6 真实金额与真实公司名不进公开仓。** KMOS 是 PUBLIC；真额只进 `Private-Database`。
- **O-7 文件入库唯一正路** = `skills/上游归档` **在容器内**跑（`scripts/run_cloud_archive.sh`）。不走钉钉云盘，不靠本机。
- **O-8 不得叫 Owner 登录、看页面、点确认、粘贴任何东西。** 一切验收由 agent 自验并留证据到 `stage_artifacts/`。
- **O-9 业务基线按纵向切片治理。** 九条基线 × 六阶段的健康与耦合规则见 `machine/facts/business_baselines.json`，门禁 `tools/check_baseline_slices.py`：上游 blocked/not_built 时，下游 计算/校验/输出/投递 不得标 `healthy`。

## 当前真相与 namespace

- GitHub canonical upstream：`LinzeColin/KMOS` 的 `main`，项目目录 `KMFA/`；中间 phase 在隔离 worktree 本地提交，只有整个 Stage 完成、复审并修复后才上传。
- 当前公开软件交付合同：Owner 授权的 v1.5.2 Taskpack，SHA-256 `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`。当前 phase/Task 只从 `HANDOFF.md` 与该 task graph 读取。
- 产品/runtime 版本：以 `KMFA/VERSION` 为唯一 writer，当前为 `0.1.4-one-time-github-main-upload`；不得由 taskpack 版本推断。
- 版本、事实域 writer、生产身份与冲突规则：`machine/runs/AUTHORITY_REGISTER.md`。本文件只定义执行边界，不另存进度或业务事实。
- `machine/facts/status.json`、`plan.json`、`roadmap.json` 描述旧业务状态域：有效进度 `4/18`、任务 `S05-P3-T1`、`Q4 / D / NO_GO / 3-9-2-1`。它们不是 v1.5.2 delivery DAG 的 writer。
- Owner blocker：`BLK-001` 仍对正式财务结论 fail closed。未取得 8 份 PDF 加 1 份电子表格的真实字段确认前，不得把旧业务 S05-S18 宣称为完成；这不阻止不接触真实数据的 v1.5.2 公共软件阶段按 Task/AC 推进。

## 执行规则

- **进 KMFA 先读 `tools/INDEX.md`，不要列目录。** 2026-08-19 实测，四个大目录全列 ≈ **64370 tokens**：
  `tools` 16546 ／ `tests` 9041 ／ `metadata/quality` 28371 ／ `stage_artifacts` 10412。
  索引 ≈3092 tokens 覆盖全部四个，**省 95%**。
  其中 1033 个文件是已完成阶段的冻结校验器与配套测试，你几乎永远不需要逐个看；
  产物目录只增不减，要找就按精确名 grep。
  索引由 `tools/build_tools_index.py` 生成、CI 校验是否过期，可以信。

- 每个 run 最多解决一个 Phase；开始时先验证 `git root`、branch、remote、HEAD、status。
- 代码、skill、配置或 automation prompt 改动须先跑目标验证；通过后可在隔离 worktree 本地提交。v1.5.2 中间 phase 禁止 push；只有整个 Stage 完成、复审、问题修复后才整体上传 GitHub。
- 旧 `LinzeColin/CodexProject` 与 `/Users/linzezhang/CodexProject` 只作历史取证，不是 KMFA 提交入口。
- 不创建 branch、PR、issue 或额外 worktree，除非用户在当前线程明确改变规则。
- 七个人类文档由 `machine/canonical_facts.yaml`（v1.5.2 产品合同）、`acceptance_contract.yaml` / `task_graph.yaml` / `release_policy.yaml` / `traceability.csv`（`05` 的验收追踪与晋级门）与 `machine/facts/`（旧业务状态）经 `machine/tools/render_human.py` 单向渲染；不得直接手写 `文档/`，也不得复制 taskpack `human/*` 形成第二人类平面。

## 数据与安全

- `~/Downloads/KMFA_MetaData` 若存在则是用户原始财务数据，只读；2026-07-17 清理交接盘点时该路径不存在，恢复状态见 `HANDOFF.md`。
- 公开 GitHub 只保存代码、schema、validator、脱敏 fixture、hash/index、状态和治理证据。
- 不提交员工/考勤/群聊/财务明文、DWS 包、工作簿、PDF、SQLite、raw JSON/JSONL/GZ、完整账号、token、key、webhook、cookie 或 session。
- 真实运行/开发现场的 GitHub 接管入口是 PRIVATE `LinzeColin/KMFA-Private-Runtime` 的 `cleanup-handoff-20260717` Release；OneDrive 仅为冗余副本。凭证、token、cookie、session 和 `.env*` 不进入任何 GitHub 仓库或 Release，恢复后重新认证。
- 金额使用整数分或 `Decimal`；任何 0.01 元差异必须失败或进入差异队列。
- 数据缺失、过期、血缘不完整或人工确认未完成时 fail closed，不生成正式可信经营结论。

## 业务动作边界

除非用户在当前线程明确授权，不执行 live DWS、钉钉发送、正式报告发布、付款、报税、开票、薪资、银行、客户联络、合同或生产操作。
