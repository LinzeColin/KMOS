# KMOS Agent Contract

KM 系列商用线仓库，中文优先；代码、API、库名、模型名和错误可保留英文。

## 永久规则

- 本仓库是**商用线**。代码与数据默认专有，不得以任何开源许可对外发布。
- 治理框架来自共享仓库 LinzeColin/Governance。
  **禁止**在本仓库内复制、分叉或重建治理框架。
  **禁止**用 git submodule 引入它 —— 通过 CI checkout 或 pip 安装消费。
- 跨 KM 项目的数据交换必须经过 KMDatabase 声明的 schema，
  **禁止**直接引用其他项目的内部路径。

## 迁移状态

本仓库从 `LinzeColin/CodexProject` 拆分而来。

- `KMFA/` 已在 2026-07-17 迁入并成为 KMFA 的唯一 GitHub 源码归属。
- `KMIDS/` 的迁移状态以仓库根 `README.md` 为准。
- 旧 `CodexProject` checkout 仅是历史/私有运行态来源，不得再作为 KMFA 的提交或推送入口。

处理 KMFA 前先读 `KMFA/HANDOFF.md`；真实员工、财务、群聊、考勤、SQLite、压缩包和凭据不得进入本公开仓库。
