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

- **2026-07-25：本地 `objects/`（53 文件 / 120M）与 `manifest.jsonl` 已从当前版本移除。** 迁移前已核对 53/53 全部存在于 Private-Database，移除安全。
- Private-Database 的 `Private-KMDatabase/` 是**跨仓访问的权威入口**，含全部 53 对象 + KMFA 后续上传（当前 56 个）。
- **仍未做的事（Owner 另行决策）**：`manifest.jsonl` 与 objects 含真人姓名与客户名（余永昕、新疆宜化 等），本次只删当前版本，**git 历史里的旧提交仍含这些财务对象**。彻底清除需一次 KMOS 历史重写（或把 KMOS 切为 Private），属破坏性操作，尚未执行。
- KMFA 约 12 个一次性入库提取器（`invoice_lines_extract.py` 等）历史上读本目录，随数据移除一并成为历史工具；权威消费链 `facts_from_staging.py` 早已经 SDK 从 Private 读，不受影响，均未接入 CI。
- **后续 agent 结论**：要数据走 SDK 读 Private-Database；本地已无数据副本，不要尝试恢复。
