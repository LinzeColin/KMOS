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

本仓库正从 LinzeColin/CodexProject 分批迁入项目。
KMFA 与 KMIDS 仍在 CodexProject 中（codex 正在开发），将在其静默后迁入。
**在它们迁入之前，不要在本仓库为它们创建占位目录或桩代码。**
