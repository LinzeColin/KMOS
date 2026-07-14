# KMOS

KM 系列的商用线仓库。从 LinzeColin/CodexProject 拆分而来，各项目保留完整提交历史。

## 项目

| 项目 | 状态 | 说明 |
|---|---|---|
| whkmSalary | ✅ 已迁入 | 薪酬 |
| KMFA | ⏳ 待迁入 | codex 正在开发，等其静默后迁入 |
| KMIDS | ⏳ 待迁入 | 原 KM_IDSystem；codex 正在开发 |
| KMDatabase | 🆕 新建骨架 | KM 系列共享数据与元数据层 |

## KMDatabase 的职责

KMFA / KMIDS / whkmSalary 三者共享的**数据契约层**。

拆分前它们同处一个 monorepo，可以直接互相引用路径。拆分后若无共享层，
跨项目引用会退化成跨仓库引用（脆弱、难以版本化）。KMDatabase 承担：

- `schema/` —— 三个项目共用的数据结构定义（单一事实源）
- `data/` —— 实际数据（已 gitignore，不入库）

**约定**：任何跨 KM 项目的数据交换，必须经过 KMDatabase 声明的 schema，
不得直接引用对方内部路径。

## 治理

治理框架不在本仓库内，来自共享仓库 [LinzeColin/Governance](https://github.com/LinzeColin/Governance)。
**不要在此复制或分叉治理框架。**

## 许可

专有，保留所有权利。见 LICENSE。
