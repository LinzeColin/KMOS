# S07 / P7.1 / T-S07-01 — 单文件下载 receipt

状态：**LOCAL PHASE PASS — 未做 S07 整体复审、未上传、未部署、未灰度**

Taskpack SHA-256：
`31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`

Parent commit：
`dedc4690f092e7e54f3b157501ce0ad2990173cc`

Requirement / acceptance / test：
`R-DL-001 / AC-DL-001 / TEST-DL-001`

## 1. 范围与结论

本 receipt 只关闭 `S07 / P7.1 / T-S07-01`。默认关闭的
`KMFA_SINGLE_FILE_DOWNLOAD_ENABLED` 为已授权匿名 workspace 返回有界的原件版本与派生物
索引，并接受 JSON body 中的 opaque `kind + asset_id` 精确选择一个对象。对象 ID 不进入下载
URL，不是长期 capability；无 session、错误 workspace 或跨 workspace asset 均 fail closed。

每个响应固定 `Content-Disposition: attachment`、`nosniff`、`private, no-store`，同时返回并
由浏览器复核 Content-Type、记录媒体类型、字节数、SHA-256、asset kind/id、源版本，以及上传
operation 或 processor/version。Unicode、空格、`# + []` 等特殊文件名通过 RFC 5987 保留。
HTML、PDF 等主动格式即使可下载也不内联执行。历史原件版本、当前派生物和已作为 workspace 文件
进入同一 artifact version registry 的报告均走同一私有对象读取与完整性校验链。

本 phase 不接入旧 `/api/报告中心`，避免把历史私有报告暴露给匿名 workspace；未来生成的报告
必须先进入 workspace-scoped object/version metadata，不能从旧全局目录旁路。Range、批量 ZIP、
显式导出 Job 与 published snapshot 分别属于 P7.2、P7.3 和 S08，本轮保持关闭。没有 schema
迁移，也没有改写或删除 v1.5 恢复资产、原件、派生物、备份、session/verifier 或任何卷。

## 2. 已实现合同

- `StructuredRepository.downloadable_assets()` 只在已授权 workspace 内联合读取 active
  `artifact_versions` 与 registry-validated `artifact_derivatives`；storage key/backend 不进入
  公共 payload。
- 新端点 `POST /workspaces/{workspace_id}/artifact/downloads` 只接受
  `original|derivative` 与 opaque ID。原件继续执行持久化 security assessment；派生物要求 clean
  source 和已登记 processor。找不到的对象固定返回 `artifact_download_not_found`。
- 兼容端点 `POST .../artifact/download` 保留“最新原件 + application/octet-stream +
  attachment-only”，供 P7.1 Flag 快速回滚；关闭新 Flag 不删除索引、版本或对象。
- workspace UI 逐项显示文件名、原件版本或派生来源、媒体类型、大小与 SHA-256。保存前浏览器
  比较响应 kind/id、记录媒体类型、Content-Type、size、source、processor/upload operation 和
  完整字节 SHA-256；任一不一致立即停止保存。
- 新下载端点与旧下载端点共用 P4.4 `export` 资源预算；没有落入普通 mutation 预算，也没有新增
  无界 retry、队列或后台任务。
- Local/Coolify Compose 与 `.env.example` 均默认
  `KMFA_SINGLE_FILE_DOWNLOAD_ENABLED=0`。CI 只运行核心链路与高风险故障的固定 Fixture Oracle，
  不使用真实时间 soak、观察期、等待窗口或全量测试作为前置。

## 3. AC-DL-001 确定性证据

最终本地 runtime image：
`sha256:7a6073f94f206a168c17ff875bbe0ccc47eb0fafd372d84d62366c2075f1ca20`

所有输入均为 synthetic fixture；恢复码、session capability、scanner secret、workspace ID、
object key、私有报告正文和凭据未写入 evidence。

| 验收项 | 最终观测 | 结果 |
|---|---:|---|
| 精确原件版本 | `2/2`，含非最新 v1 | **PASS** |
| 派生物 | `1/1`，processor/source version 一致 | **PASS** |
| 已存储报告文件 | PDF `1/1`，准确 `application/pdf` | **PASS** |
| 字节与元数据 | mismatch `0` | **PASS** |
| Unicode/特殊文件名 | API + Chromium 均保留 | **PASS** |
| 高风险边界 | inline response `0`；全部 attachment + nosniff | **PASS** |
| 权限 | IDOR/无 session 成功下载 `0` | **PASS** |
| 完整性故障注入 | 对象篡改 `1/1` 返回 `503`，未返回替代字节 | **PASS** |
| selector 泄露 | asset ID 出现在 URL `0` | **PASS** |
| 重启 | 原件、派生物、索引与下载保持 | **PASS** |
| Flag rollback / re-enable | 资产保持；旧最新下载可用；重新启用恢复精确下载 | **PASS** |
| 浏览器 | 3 项可见，真实下载与 metadata/hash 二次校验，error `0` | **PASS** |
| 隐私 | capability/shared-secret log 命中 `0` | **PASS** |

Ignored local evidence：

```text
KMFA/.codex_private_runtime/s07-p71-e2e-reviewed/summary.json
  sha256 abb9934d57b6cbaffcf2f86bf3df13c713821c1853760c8d980051d2b288f53a
KMFA/.codex_private_runtime/s07-p71-e2e-reviewed/http-trace.json
  sha256 ad85e7a842c7269beb1058ebf08967dac1759ff857e4e6fa62a5b1de369e2545
KMFA/.codex_private_runtime/s07-p71-e2e-reviewed/download-ui.png
  sha256 a3a073d6e18473f5f16a57bc4d75ecc1ccf511d611c7d48a2c394e1e9c62394e
```

## 4. Phase review findings

| Finding | 影响 | 最小修复 | 状态 |
|---|---|---|---|
| F-P71-001 旧端点只能下载最新原件 | 历史版本不可取回 | workspace-scoped bounded index + exact selector | **RESOLVED** |
| F-P71-002 所有下载都返回 octet-stream | 类型/来源不可验证 | 准确 Content-Type + recorded media/size/source headers | **RESOLVED** |
| F-P71-003 派生物只能内联预览 | 用户无法把派生结果作为文件取回 | registry-validated derivative attachment 下载 | **RESOLVED** |
| F-P71-004 若把 asset ID 放 URL 或跳过 workspace join | 可枚举或 IDOR | JSON body selector + authorize-before-resolve + 跨 workspace 404 | **RESOLVED** |
| F-P71-005 前端只比当前 SHA | 版本/UI/响应可能错配 | kind/id/type/size/source/hash 全量浏览器复核 | **RESOLVED** |
| F-P71-006 新 POST 初版落入 mutation budget | 下载资源预算语义错误 | 与旧下载共同分类为 bounded export | **RESOLVED** |
| F-P71-007 既有 P6.3 E2E helper 调用签名漂移，skip-browser 固定断言 6 | CI 会在 P7.1 前假失败 | 对齐 helper 参数并按 browser fixture 动态断言 4/6 | **RESOLVED** |
| F-P71-008 exact-image 初版把同 workspace 第 7 个下载寄希望于时间窗滑出 | 违反确定性验证约束 | 用独立 unlisted workspace 隔离权限负测，取消真实时间依赖 | **RESOLVED** |

Phase review open finding：`0`；waived/accepted risk：`0`。published snapshot、Range/ZIP 和 export
job 是后续明确 scope，不被本 receipt 冒充为已完成。

## 5. 验证

```text
P7.1 + walking/lineage/object/S3/abuse focused tests: 48 passed
P6.3 exact-image targeted regression (--skip-browser): PASS
Ruff E/F on changed Python:                            PASS
frontend production build:                            PASS (622 modules)
  existing private App bundle warning:                >500 kB, non-blocking
local + Coolify Compose render:                       PASS / PASS
final Docker frontend+backend image build:            PASS
TEST-DL-001 exact-image API + Chromium Oracle:         PASS
  originals / derivatives / stored report:            2 / 1 / 1
  byte-metadata mismatch / unauthorized / inline:     0 / 0 / 0
  integrity fault blocked / browser errors:            1 / 0
taskpack validator:                                   49 req / 49 AC / 56 tasks PASS
dual-plane check:                                     PASS (5 projects)
diff secret-shape scan / git diff --check:             0 / PASS
```

验证只用了固定合成 Fixture、即时对象篡改、容器重启与 Flag 切换。HTTP/浏览器 readiness 仅同步
进程和事件完成，不作为观察期或 soak 证据；没有连续运行 N 小时、后台空转、无限重试或全量测试
前置。

## 6. Rollback、停止条件与下一边界

整个 v1.5.2 Taskpack 完成前保持 `KMFA_SINGLE_FILE_DOWNLOAD_ENABLED=0`，不部署、不灰度。
快速回滚使用同一 schema `6` binary 把该 Flag 置 `0`；精确 selector fail closed，旧最新原件
attachment 下载继续可用。保留 DB、所有原件版本、lineage、processing runs、派生物、对象、
备份、卷、session/verifier 和 v1.5 recovery bundle。禁止 schema/binary downgrade、
`down -v`、删对象/版本/派生物/备份、撤 reader 凭据或用 recovery replay 覆盖 live state。

立即停止条件：跨 workspace 下载成功；无 session 可读取 unlisted asset；下载 URL 可枚举；
高风险格式内联；字节、大小、类型、checksum 或来源错配；完整性错误仍返回对象；日志/证据出现
capability/private bytes；或回滚要求删除既有状态。

2026-07-26 收口前重新 fetch：`origin/main` 仍为
`c00a90f5b9fab87c880a7046ad3255b27ab24a45`，当前本地 parent 相对远端为 `ahead 7 /
behind 0`；远端没有比本地 parent 更新的提交。本 phase 未 push、未创建 PR、未部署。

本地 Task 进度为 `29/56`；S07 为 `1/4` phases，S07 整体复审未开始；published Stage 仍为
`6/14`。下一次新 run 只可执行 `S07 / P7.2 / T-S07-02` 续传与批量 ZIP，不得提前进入 P7.3、
P7.4、S07 整体复审、上传 GitHub、部署或启用任何生产 Flag。
