# KMOS

KM 系列的商用线仓库。从 LinzeColin/CodexProject 拆分而来，各项目保留完整提交历史。

## 项目

| 项目 | 状态 | 说明 |
|---|---|---|
| whkmSalary | ✅ 已迁入 | 薪酬 |
| KMFA | ✅ 已迁入 | 经营分析、考勤、日常检查、资金周报、月报与 DWS 归档 public-safe 源码 |
| KMIDS | ✅ 已迁入 | 实际目录 `KM_IDSystem/`；工业数据系统与 public-safe 搜标 Skill |
| KMVideo | ✅ 已建立 | 钉钉授权素材归档与视频生成流程源码；原始素材位于 Private-Database 的 `Private-KMDatabase/KMVideo/` |
| KMDatabase | ✅ 数据契约层 | KM 系列共享 schema 与存取 SDK；真实经营数据已移入私有仓 `Private-Database/Private-KMDatabase`，本仓不再存数据 |

## KMDatabase 的职责

KMFA / KMIDS / whkmSalary 三者共享的**数据契约层**。

拆分前它们同处一个 monorepo，可以直接互相引用路径。拆分后若无共享层，
跨项目引用会退化成跨仓库引用（脆弱、难以版本化）。KMDatabase 承担：

- `schema/` —— 三个项目共用的数据结构定义（单一事实源）
- `machine/tools/private_db_client.py` —— 免 clone 存取 `Private-Database` 的 SDK（`ingest/get/list/verify`）
- `data/` —— **不再存真实数据**：全部经营原始数据在私有仓 `Private-Database/Private-KMDatabase`；本地仅留 `WHERE_IS_THE_DATA.md` 路牌

**约定**：任何跨 KM 项目的数据交换，必须经过 KMDatabase 声明的 schema，
不得直接引用对方内部路径。

## 📦 数据落地政策（长期有效 · 自运行分仓治理）

**本仓只存代码与治理，长期/业务/运行时数据不入本仓。** 开发中产生的任何需长期存储的数据
（原始经营数据、导出件、数据库、内容寻址对象、含 PII 的记录等）一律写入私有仓
`LinzeColin/Private-Database` 的 `Private-KMDatabase/` 区，**不要提交进本仓**：
用 `KMDatabase/machine/tools/private_db_client.py` 免 clone 读写（`ingest/get/list/verify`），
Private-Database 禁止 `git clone`；派生/临时/可再生产物走 `.gitignore`。
**一次分清、长期自运行，不再需要人工反复迁移。**（`AGENTS.md` 已将本条列为永久规则。）

## 治理

治理框架不在本仓库内，来自共享仓库 [LinzeColin/Governance](https://github.com/LinzeColin/Governance)。
**不要在此复制或分叉治理框架。**

## 许可

专有，保留所有权利。见 LICENSE。
