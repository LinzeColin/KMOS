# KMDatabase/data —— 原始数据增量仓（D11）

> 🔴 **2026-07-19 更新：数据已迁往私有仓 `Private-Database/Private-KMDatabase`。**
> **新数据不要再往本地 `objects/` 落**——用 `machine/tools/private_db_client.py ingest`（免 clone 写入 Private-Database）。
> 详见同目录 `WHERE_IS_THE_DATA.md`。以下 D11 旧说明（本地内容寻址）为历史记录，本地 `objects/` 待 Phase B 协调移除。

> 授权：Owner 2026-07-17 决策 D11（打通任务包 09 三节 v2）：原始数据直接入本目录，不新建仓库。
> ⚠️ 推送前置：本仓当前为**公开仓**。首批真实业务数据推送前需 Owner 对「公开可见」再确认一次，
> 或先把 KMOS 切为 Private（仓库 Settings 一个开关，结构零改动——09 三节第 5 条预留的正是这条路）。

## 布局

```
data/
├── objects/<sha256 前 2 位>/<sha256>_<原文件名>   # 内容寻址：同名不同内容共存，永不覆盖
├── manifest.jsonl                                # append-only 账本（原名/批次/域/sha256/大小/来源）
└── README.md
```

## Owner 用法（丢文件）

把新批次文件（压缩包/Excel/PDF 均可）放到任意本地目录，然后：

```bash
python3 KMDatabase/machine/tools/ingest_data.py add <目录或文件> --domain 财务   # 域：财务/WPS钉钉红圈/绩效/预算/对账基准/其他
python3 KMDatabase/machine/tools/ingest_data.py verify                          # 随时全量核对
```

重复运行无副作用（同内容幂等跳过）；同名新版本自动共存为新对象。

## 红线（工具强制）

- **凭据类永不入仓**：`.env/.pem/.key/token/secret/cookie` 等文件名直接拒绝；文本文件内容命中密钥模式（私钥头/AKIA/ghp_/sk-/JWT）拒绝。
- **单文件 >95MB 拒绝**：GitHub 100MB 硬限制；需要时先配置 Git LFS（`git lfs track 'KMDatabase/data/objects/**'`）再入仓。
- 本目录只进「数据」，不进 `_protected/` 的私密运行时、身份文件、部署密钥。
