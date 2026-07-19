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

- **不要再往本地 `data/objects/` 落新数据**——一律用 SDK 写入 Private-Database。
- Private-Database 是 **PRIVATE** 仓；**禁止 `git clone` 它**（预计 500GB+，会损伤本地机器）。
- 本目录下现存的 `objects/` 是迁移前副本，已 1:1 同步到 Private-Database（53 对象校验一致）；
  待 KMFA 线程就位 SDK 后，由拆分线程协调移除本地副本（Phase B）。在此之前两处并存、不影响读取。
