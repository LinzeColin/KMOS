# KMDatabase/data —— 数据已移出本公开仓

> 🔴 **2026-07-25 更新：本地 `objects/` 与 `manifest.jsonl` 已从本公开仓移除（Phase B 完成）。**
> 全部 53 个经营数据对象的**唯一权威落地处**是私有仓
> `LinzeColin/Private-Database` 的 `Private-KMDatabase/` 区（迁移已核对：53/53 一致，另含 KMFA 后续上传共 56 个）。
> 本目录现在只剩这两份**路牌文档**，不再存任何真实数据。

> 说明：manifest 与 objects 含真人姓名、客户名与财务明细，本仓为**公开仓**，故已移除。
> 移除只针对当前版本；git 历史里的旧提交仍含这些对象，历史清除（重写/切私有）由 Owner 另行决策。

## 读数据 / 写数据（免 clone，永不整仓下载）

用本仓 `KMDatabase/machine/tools/private_db_client.py`（底层 GitHub API，零 clone、不落本地）：

```bash
T=KMDatabase/machine/tools/private_db_client.py
python3 $T ingest Private-KMDatabase ./新数据.xlsx --domain 财务   # 域：财务/WPS钉钉红圈/绩效/预算/对账基准/其他
python3 $T get    Private-KMDatabase objects/23/235a...zip ./out.zip  # 按需下载单个对象
python3 $T list   Private-KMDatabase
python3 $T verify Private-KMDatabase                                  # 全量对账
```

协议见 `Private-Database/PROTOCOL.md`。Private-Database 是 **PRIVATE** 仓，**禁止 `git clone`**（预计 500GB+），只按需下载单文件。

## 红线（迁移后仍然有效）

- **新数据一律用 SDK 写进 Private-Database，不要再往本地落 `objects/`。**
- **凭据类永不入仓**：`.env/.pem/.key/token/secret/cookie` 与密钥模式一律拒绝。
- **单文件 >95MB 拒绝**：GitHub 100MB 硬限；需要时先配 Git LFS。

## 历史记录（D11，已废止的本地落地方案）

Owner 2026-07-17 决策 D11 曾把原始数据以内容寻址方式落在本地 `objects/` + `manifest.jsonl`；
2026-07-19 起数据权威改为私有仓 `Private-KMDatabase`，本地这份降级为 KMFA 待清对象，
2026-07-25 正式移除。KMFA 权威消费链 `facts_from_staging.py` 早已改经 SDK 从私有仓读，不依赖本目录；
另有约 12 个一次性入库提取器（`invoice_lines_extract.py` 等）历史上读本目录，现随数据移除一并成为历史工具，未接入任何 CI。
