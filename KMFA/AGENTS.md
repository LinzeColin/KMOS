# KMFA Agent Contract

本项目继承仓库根 `AGENTS.md`。任何 agent 接手前先读本文件、`HANDOFF.md` 和 `machine/facts/status.json`。

## 当前真相与 namespace

- GitHub canonical upstream：`LinzeColin/KMOS` 的 `main`，项目目录 `KMFA/`；中间 phase 在隔离 worktree 本地提交，只有整个 Stage 完成、复审并修复后才上传。
- 当前公开软件交付合同：Owner 授权的 v1.5.2 Taskpack，SHA-256 `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`。当前 phase/Task 只从 `HANDOFF.md` 与该 task graph 读取。
- 产品/runtime 版本：以 `KMFA/VERSION` 为唯一 writer，当前为 `0.1.4-one-time-github-main-upload`；不得由 taskpack 版本推断。
- 版本、事实域 writer、生产身份与冲突规则：`machine/runs/AUTHORITY_REGISTER.md`。本文件只定义执行边界，不另存进度或业务事实。
- `machine/facts/status.json`、`plan.json`、`roadmap.json` 描述旧业务状态域：有效进度 `4/18`、任务 `S05-P3-T1`、`Q4 / D / NO_GO / 3-9-2-1`。它们不是 v1.5.2 delivery DAG 的 writer。
- Owner blocker：`BLK-001` 仍对正式财务结论 fail closed。未取得 8 份 PDF 加 1 份电子表格的真实字段确认前，不得把旧业务 S05-S18 宣称为完成；这不阻止不接触真实数据的 v1.5.2 公共软件阶段按 Task/AC 推进。

## 执行规则

- 每个 run 最多解决一个 Phase；开始时先验证 `git root`、branch、remote、HEAD、status。
- 代码、skill、配置或 automation prompt 改动须先跑目标验证；通过后可在隔离 worktree 本地提交。v1.5.2 中间 phase 禁止 push；只有整个 Stage 完成、复审、问题修复后才整体上传 GitHub。
- 旧 `LinzeColin/CodexProject` 与 `/Users/linzezhang/CodexProject` 只作历史取证，不是 KMFA 提交入口。
- 不创建 branch、PR、issue 或额外 worktree，除非用户在当前线程明确改变规则。
- 七个人类文档由 `machine/canonical_facts.yaml`（v1.5.2 产品合同）、`acceptance_contract.yaml` / `task_graph.yaml` / `traceability.csv`（`05` 的验收追踪）与 `machine/facts/`（旧业务状态）经 `machine/tools/render_human.py` 单向渲染；不得直接手写 `文档/`，也不得复制 taskpack `human/*` 形成第二人类平面。

## 数据与安全

- `~/Downloads/KMFA_MetaData` 若存在则是用户原始财务数据，只读；2026-07-17 清理交接盘点时该路径不存在，恢复状态见 `HANDOFF.md`。
- 公开 GitHub 只保存代码、schema、validator、脱敏 fixture、hash/index、状态和治理证据。
- 不提交员工/考勤/群聊/财务明文、DWS 包、工作簿、PDF、SQLite、raw JSON/JSONL/GZ、完整账号、token、key、webhook、cookie 或 session。
- 真实运行/开发现场的 GitHub 接管入口是 PRIVATE `LinzeColin/KMFA-Private-Runtime` 的 `cleanup-handoff-20260717` Release；OneDrive 仅为冗余副本。凭证、token、cookie、session 和 `.env*` 不进入任何 GitHub 仓库或 Release，恢复后重新认证。
- 金额使用整数分或 `Decimal`；任何 0.01 元差异必须失败或进入差异队列。
- 数据缺失、过期、血缘不完整或人工确认未完成时 fail closed，不生成正式可信经营结论。

## 业务动作边界

除非用户在当前线程明确授权，不执行 live DWS、钉钉发送、正式报告发布、付款、报税、开票、薪资、银行、客户联络、合同或生产操作。
