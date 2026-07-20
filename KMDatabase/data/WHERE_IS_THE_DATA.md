# 📍 数据在哪：已迁往 Private-Database

> **给所有正在开发和后续新 agent 的路牌。** 2026-07-19 起，经营原始数据的**权威落地处**是
> **私有仓 `LinzeColin/Private-Database` 的 `Private-KMDatabase/` 区**，不再是本地目录。

## 读数据 / 写数据（免 clone，永不整仓下载）

用本仓 `KMDatabase/machine/tools/private_db_client.py`（底层 GitHub API，零 clone、不落本地）：

```bash
T=KMDatabase/machine/tools/private_db_client.py

# 上传（KMFA 前端上传 → 跨仓入库：算 sha256 + 入 objects + 追加 manifest）
python3 $T ingest Private-KMDatabase ./新数据.xlsx --domain 财务

# 下载单个对象（按需，不下整仓）
python3 $T get  Private-KMDatabase objects/23/235a...zip ./out.zip

# 查 / 删 / 全量对账
python3 $T list   Private-KMDatabase
python3 $T verify Private-KMDatabase
```

域：`财务 / WPS钉钉红圈 / 绩效 / 预算 / 对账基准 / 其他`。协议见 `Private-Database/PROTOCOL.md`。

## 规则

- **新数据一律用 SDK 写入 Private-Database，不要再往本地 `data/objects/` 落。**
- Private-Database 是 **PRIVATE** 仓；**禁止 `git clone` 它**（预计 500GB+，会损伤本地机器）。只按需下载单文件。
- KMFA 的权威消费链（`KMFA/tools/facts_from_staging.py`）**已改为经 SDK 从 Private-Database 读**，不再依赖本目录。

## 本地这份 `objects/` 现状（给后续 agent）

- Private-Database 的 `Private-KMDatabase/` 是**跨仓访问的权威入口**，含全部 53 对象 + KMFA 后续上传（当前 56 个）。
- 本目录现存的 `objects/`（53 文件 / 120M）与 `manifest.jsonl` 仍在，原因有二，**都不该由「仓库拆分」线程删**：
  1. `manifest.jsonl` 含真人姓名与客户名（余永昕、新疆宜化 等），其清除属 **KMFA 线程**负责的「公网财务数据清除」——那是一次 KMOS 历史重写，会把整个 `KMDatabase/data` 一并清掉。
  2. KMFA 另有约 8 个一次性入库提取器（`invoice_lines_extract.py` 等）历史上读本目录；是否随清除退役由 KMFA 决定。
- **后续 agent 结论**：要数据走 SDK 读 Private-Database；本地这份是 KMFA 待清对象，不要依赖、也不要替 KMFA 删。
