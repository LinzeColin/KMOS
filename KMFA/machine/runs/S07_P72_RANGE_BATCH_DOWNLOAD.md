# S07 / P7.2 / T-S07-02 — Range 与批量 ZIP 下载 receipt

状态：**LOCAL PHASE PASS — 未做 S07 整体复审、未上传、未部署、未灰度**

Taskpack SHA-256：
`31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`

Parent commit：
`bd30da81a1b23328c41995b55a5a716b8a43d6d6`

Requirement / acceptance / test：
`R-DL-002 / AC-DL-002 / TEST-DL-002`

## 1. 范围与结论

本 receipt 只关闭 `S07 / P7.2 / T-S07-02`。默认关闭的
`KMFA_RANGE_BATCH_DOWNLOAD_ENABLED` 在 P7.1 已授权的精确下载链上增加单区间
HTTP Range、稳定 SHA-256 ETag、并行区间请求，以及最多 500 个已授权对象的可验证流式 ZIP。
Range 与批量 selector 都保留在同源 POST 的 JSON 正文和请求头中；对象 ID 不进入 URL，也不会
成为长期 capability。

批量实现选择 Task 合同允许的 `batch stream`：服务器先生成不含私有存储位置的 canonical
`manifest.json`，再按选择顺序逐个物化、复核并流出 `ZIP_STORED` entry。服务器从不生成第二份
归档文件，也不在单进程内存保存整个归档；仅保存最多 501 项的中央目录元数据。每项位于唯一的
`files/NNNN/<safe-name>`，因此重名不会覆盖；绝对路径、反斜杠、空段、`.`、`..`、控制字符和
超长名称均不能形成可穿越路径。

本 phase 不实现 P7.3 的显式高成本 export job，也不实现 P7.4 download ownership matrix 或
S08 published snapshot。没有 schema 迁移，没有删除、覆盖或改写 v1.5 恢复资产、项目、进度、
原件、派生物、备份、session/verifier、数据库、对象或卷。

任务包原始 `observation_window` 文本按 Owner 后续明确合同执行为即时确定性回放：本轮没有真实
时间 Soak、观察期、等待窗口、后台空转、重复审批、形式化 Gate、无限重试或全量测试前置。

## 2. 已实现合同

- P7.2 Flag 只有显式 true 值才启用，并要求 P7.1 精确下载 Flag 同时可用。关闭 P7.2 后完整的
  P7.1 单文件下载仍可用，已有资产与 schema `6` 状态不变。
- 单文件端点在物化对象前只接受一个 `bytes=<start>-<end>`、开放尾部或 suffix Range。畸形或
  multi-range 返回 `400 invalid_range_header`；不可满足范围返回 `416` 和
  `Content-Range: bytes */<size>`。响应使用记录中的 SHA-256 强 ETag，支持 `If-Range`；
  不同区间可并行请求并按最终 SHA-256 验证重组结果。
- 批量端点 `POST .../artifact/downloads/batch` 只接受 1–500 个不重复
  `original|derivative + opaque asset_id`。服务器先做一次 workspace 授权，再在该 workspace
  registry 内解析全部对象；跨 workspace、缺失、重复或安全状态不允许的选择 fail closed。
- 批量原始字节预算为 `512 MiB`，归档固定 ZIP32、无压缩、固定最早 DOS 时间和 canonical JSON，
  因而相同选择的有界重试得到逐字节相同归档。响应公开 file count、source bytes、归档格式、
  manifest path/hash 与精确 `Content-Length`。
- 流式 writer 每次最多读取/产出 `64 KiB`，每次只物化一个对象，同时重新计算 size、CRC32 与
  SHA-256。中途对象缺失、存储不可用或完整性不一致时连接只留下不可打开的截断 ZIP，不会返回
  一个伪造为成功的有效归档；客户端至多重试一次。
- ASGI 取消会显式关闭同步 generator；当前临时物化对象在 `finally` 中删除。单文件
  `FileResponse` 也在发送完成或客户端断线后清理临时对象。
- 前端固定按 `4 MiB` Range 分片下载精确对象，当前分片只允许一次网络重试，并以稳定 ETag、
  Content-Range、来源元数据和最终 SHA-256 验证后保存。批量下载支持选择、显式取消和一次有界
  重试；4xx 与用户取消不重试。浏览器只保留下载所需 Blob，不再为整包 hash 创建第二份
  `arrayBuffer`；逐项真实性由响应中的 manifest SHA-256 与 manifest 内 entry SHA-256 提供。
- 批量端点复用 P4.4 已有 `export` 并发/速率预算，不新增后台队列、无界 worker 或新的策略层。
  Local/Coolify Compose 与 `.env.example` 均默认
  `KMFA_RANGE_BATCH_DOWNLOAD_ENABLED=0`。

## 3. AC-DL-002 确定性证据

最终本地 runtime image：
`sha256:3dfe4a4d678a1f445a569b38747079f7fe2e1de6f765c91e0c2f149d48a63ab5`

所有输入均为 synthetic fixture；恢复码、session capability、scanner secret、storage key 和
私有对象正文未写入 evidence。

| 验收项 | 最终观测 | 结果 |
|---|---:|---|
| 完整/开放尾部/suffix/If-Range | 精确状态、区间与长度均匹配 | **PASS** |
| 并行 Range | `2` 个并行区间；重组 SHA-256 一致 | **PASS** |
| 模拟断线续传 | Chromium 注入 `1` 次 connection reset；当前分片一次重试后 `2` chunks 完成 | **PASS** |
| 50 文件批量 | `32` originals + `18` derivatives；逐项大小/hash 一致 | **PASS** |
| 500 文件边界 | `500/500` 可打开；`501` 明确拒绝 | **PASS** |
| 重名/Unicode/特殊字符 | 唯一路径，无覆盖 | **PASS** |
| zip-slip 负向 | missing/overwritten/traversal=`0/0/0` | **PASS** |
| manifest | canonical JSON、逐项来源/size/SHA-256；header hash 一致 | **PASS** |
| 资源边界 | server whole-archive buffered=`false`；max chunk=`64 KiB`；archive temp=`0` | **PASS** |
| 取消 | async stream 与模拟 ASGI 客户端断线均即时删除当前临时对象 | **PASS** |
| 失败与有界重试 | 首次物化失败后一次 retry 成功；归档 retry byte-identical | **PASS** |
| 重启 / rollback / re-enable | 资产保持；P7.1 单文件保持；重新启用恢复相同 ZIP | **PASS** |
| 浏览器批量下载 | `1` 项真实 ZIP，manifest 与 payload hash 已打开复核 | **PASS** |
| 隐私 | capability/shared-secret log 命中 `0` | **PASS** |

最终 exact-image ZIP：

```text
archive SHA-256  60fe8fdb20ff19c19b61324e30c4600ac232a37b0d06a5ec2a7eac054ff90487
manifest SHA-256 4640481d076feddfb6d746046e958b9db0cf229771b90a172d63deaf64893fdf
```

Ignored local evidence：

```text
KMFA/.codex_private_runtime/s07-p72-e2e-reviewed/summary.json
  sha256 f7f2e919089f4925543088ad47088b5ea1ecd7b171ff5f696778f6f1f05680c6
KMFA/.codex_private_runtime/s07-p72-e2e-reviewed/http-trace.json
  sha256 3d73d2a3fe1aafe88b080f5848a1dee5dfd07f9fdbb0a618b8ac3eec6d2e1d86
KMFA/.codex_private_runtime/s07-p72-e2e-reviewed/zip-manifest.json
  sha256 cd473bfad879c142a0d85306f25b9e27a5e8f9784e32d1c8c041b6732d02087c
KMFA/.codex_private_runtime/s07-p72-e2e-reviewed/zip-hashes.json
  sha256 5c3ad7f3751589afba6afc7e6926bdc9d00b38e52a80495e244df131bb09bab5
KMFA/.codex_private_runtime/s07-p72-e2e-reviewed/range-batch-ui.png
  sha256 366f9718b0e65b8c9c3fbe4be3c3569b1f1adfd49f6d87d281a32f1095323d85
```

## 4. Phase review findings

| Finding | 影响 | 最小修复 | 状态 |
|---|---|---|---|
| F-P72-001 基线只有框架隐式 Range，批量端点不存在 | 合同不可见且 AC 无法闭合 | 显式 Flag/Range 校验/ETag 与 authorized batch stream | **RESOLVED** |
| F-P72-002 初版假设 manifest 小于单个 64 KiB chunk | 500 项 metadata 可超过 writer chunk 边界 | manifest 同样按 64 KiB 分块 | **RESOLVED** |
| F-P72-003 50 项 Fixture 初版触发真实速率时间窗 | 验收会依赖等待 | 仅在 Fixture 中推进 Fake Clock bucket | **RESOLVED** |
| F-P72-004 临时 S3 物化对象需覆盖断线取消 | 客户端断线可能遗留临时文件 | generator close + FileResponse finally；故障注入验证 | **RESOLVED** |
| F-P72-005 批量浏览器初版再次读取整个 Blob 做 archive hash | 产生无收益的第二份客户端内存副本 | 移除整包 arrayBuffer；保留 manifest/entry hash 合同 | **RESOLVED** |
| F-P72-006 同名和不可信 legacy 名称可能覆盖或穿越 | ZIP 提取风险 | ordinal 独立目录 + strict path validator + fallback 名称 | **RESOLVED** |

Phase review open finding：`0`；waived/accepted risk：`0`。显式 export job 的 durable 状态、成本与
取消语义属于 P7.3，不被本 receipt 冒充为已完成。

## 5. 验证

```text
pre-change baseline:
  exact POST Range bytes=4-7:                         206（框架隐式能力）
  batch endpoint:                                    404
  explicit P7.2 status/Flag contract:                 absent
P7.1/P7.2 + abuse/walking/public-entry focused tests: 54 passed
Ruff on changed Python:                               PASS
frontend production build:                           PASS (622 modules)
  existing private App bundle warning:               >500 kB, non-blocking
host dist vs final exact-image dist:                  byte-identical
final Docker frontend+backend image build:            PASS
TEST-DL-002 exact-image API + Chromium Oracle:        PASS
  parallel Range / reconstructed hash:               2 / match
  batch / missing / overwritten / traversal:         3 / 0 / 0 / 0
  injected disconnect / bounded retry / browser err: 1 / true / 0
  server whole archive buffered / archive temp:      false / 0
  restart / rollback / re-enable:                     true / true / true
taskpack repository projection:                      PASS
  req / AC / stages / phases / tasks / receipts:     49 / 49 / 14 / 56 / 56 / 40
  errors / warnings:                                 0 / 0
dual-plane check / sealed source hashes:              PASS / unchanged
added-line secret/private-path shape scan:            0
git diff --check:                                     PASS
```

验证只使用固定合成 Fixture、Fake Clock、模拟 connection reset、模拟 ASGI disconnect、即时对象
物化失败、容器重启和 Flag 切换。HTTP/浏览器 readiness 只同步进程与事件完成，不是观察期或
Soak 证据。

## 6. Rollback、停止条件与下一边界

整个 v1.5.2 Taskpack 完成前保持 `KMFA_RANGE_BATCH_DOWNLOAD_ENABLED=0`，不部署、不灰度。
快速回滚使用同一 schema `6` binary 仅把该 Flag 置 `0`；Range 请求和批量端点 fail closed，
P7.1 全量精确单文件下载继续可用。若批量容量未来需要扩大，先维持 500 项/512 MiB 限制，再由
P7.3 显式异步 job 承接；不能以扩大单进程内存换容量。

保留 DB、所有原件版本、lineage、processing runs、派生物、对象、备份、卷、session/verifier
和 v1.5 recovery bundle。禁止 schema/binary downgrade、`down -v`、删对象/版本/派生物/备份、
撤 reader 凭据或用 recovery replay 覆盖 live state。

立即停止条件：跨 workspace 或无 session 下载成功；Range 重组 hash 不一致；ETag 在续传中
漂移仍保存；ZIP 丢失、覆盖、穿越或 manifest/hash 不一致；服务端需要把整个归档放入单进程
内存；取消后临时对象残留；无界 retry/worker；日志或 evidence 出现 capability/private bytes；
或回滚要求删除既有状态。

2026-07-26 收口前重新 fetch：`origin/main` 为
`c00a90f5b9fab87c880a7046ad3255b27ab24a45`，当前本地 parent 相对远端为 `ahead 8 /
behind 0`；远端没有比本地 parent 更新的提交。本 phase 未 push、未创建 PR、未部署。

本地 Task 进度为 `30/56`；S07 为 `2/4` phases，S07 整体复审未开始；published Stage 仍为
`6/14`。下一次新 run 只可执行 `S07 / P7.3 / T-S07-03` 显式导出 Job，不得提前进入 P7.4、
S07 整体复审、上传 GitHub、部署或启用任何生产 Flag。
