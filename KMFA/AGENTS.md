# KMFA Agent Contract

本项目继承仓库根 `AGENTS.md`。任何 agent 接手前先读本文件、`HANDOFF.md` 和 `machine/facts/status.json`。

## 当前真相

- GitHub：`LinzeColin/KMOS`，项目目录 `KMFA/`，只在 `main` 工作。
- 版本：`0.1.4`。
- 当前有效进度：`4/18`；结构校验通过不等于真实数据通过。
- 当前任务：`S05-P3-T1`，人工确认后将 Q4 字段升级为 Q5 计算基准。
- 业务状态：`Q4 / D / NO_GO / 3-9-2-1`，`lineage_complete=false`。
- Owner blocker：`BLK-001`。未取得 8 份 PDF 加 1 份电子表格的真实字段确认前，不得继续把 S05-S18 宣称为完成。

## 执行规则

- 每个 run 最多解决一个 Phase；开始时先验证 `git root`、branch、remote、HEAD、status。
- 代码、skill、配置或 automation prompt 改动须先跑目标验证；通过后才可提交并推送 `origin/main`。
- 旧 `LinzeColin/CodexProject` 与 `/Users/linzezhang/CodexProject` 只作历史取证，不是 KMFA 提交入口。
- 不创建 branch、PR、issue 或额外 worktree，除非用户在当前线程明确改变规则。
- 七个人类文档由 `machine/facts/` 渲染；不得直接手写 `文档/`。

## 数据与安全

- `~/Downloads/KMFA_MetaData` 若存在则是用户原始财务数据，只读；2026-07-17 清理交接盘点时该路径不存在，恢复状态见 `HANDOFF.md`。
- 公开 GitHub 只保存代码、schema、validator、脱敏 fixture、hash/index、状态和治理证据。
- 不提交员工/考勤/群聊/财务明文、DWS 包、工作簿、PDF、SQLite、raw JSON/JSONL/GZ、完整账号、token、key、webhook、cookie 或 session。
- 真实运行/开发现场的 GitHub 接管入口是 PRIVATE `LinzeColin/KMFA-Private-Runtime` 的 `cleanup-handoff-20260717` Release；OneDrive 仅为冗余副本。凭证、token、cookie、session 和 `.env*` 不进入任何 GitHub 仓库或 Release，恢复后重新认证。
- 金额使用整数分或 `Decimal`；任何 0.01 元差异必须失败或进入差异队列。
- 数据缺失、过期、血缘不完整或人工确认未完成时 fail closed，不生成正式可信经营结论。

## 业务动作边界

除非用户在当前线程明确授权，不执行 live DWS、钉钉发送、正式报告发布、付款、报税、开票、薪资、银行、客户联络、合同或生产操作。
