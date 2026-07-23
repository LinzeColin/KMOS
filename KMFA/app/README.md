# KMFA App（DT6，D2=A：KMIDS 同栈）

后端骨架（PROD.0001）：根路径 `/` 是 canonical 公共 App Shell，`/ui` 与 `/ui/` 单跳 `308` 回 `/`；
`/healthz` 是不含内部细节的公共浅健康。既有 `/api*`、`/ops/openapi.json`、`/ops/docs` 与
`/ops/healthz` 属于私有运维面；既有经营仪表盘兼容入口为 `/ops/app`。生产由路径级 Cloudflare
Access 加源站 JWT 校验双重保护。公共壳异常时把 `KMFA_PUBLIC_SHELL_ENABLED=0` 并重部署，可仅关闭
增强 JavaScript、保留根路径六项稳定静态入口；该回滚不动数据，也不放松 `/api*`、`/ops*` 守卫。
`KMFA_PUBLIC_INDEXING_ENABLED` 独立控制搜索索引且生产默认 `0`：hold 模式仍可直接访问主页，但
`robots.txt` 全拒绝、`sitemap.xml` 为空且根响应带 `noindex`。隐私与爬虫 canary 全绿后置 `1`
只会放行 canonical 根页；所有其他路由仍统一 `noindex, nofollow, noarchive`。除哈希资产和
`robots.txt` / `sitemap.xml` 控制文件外，这些非公开响应均为 `private, no-store`。

`KMFA_WALKING_SKELETON_ENABLED` 是 S03/P3.4 的独立早期骨架 Flag，生产默认 `0`。显式置 `1`
后，根页可创建一个无需账号的服务器工作区、保存项目名称与 0–100% 进度、上传一个任意类型且不超过
8 MiB 的文件、用一次显示的高熵恢复码换取一小时短时会话，并以 attachment-only 下载校验
SHA-256。恢复码与会话 capability 在服务端只存 hash；S05 的版本化 structured-store adapter 默认
继续读取 `/var/lib/kmfa/state/walking-skeleton/walking_skeleton.sqlite3`，也可在显式
`postgresql-primary` 模式连接共享 PostgreSQL。文件字节默认继续写
`kmfa-app-state` 的私有对象区；P5.2 也可显式切到私有 S3-compatible adapter。无论新写 backend
为何，v1.5 filesystem 对象始终保留 read path。P5.3 上传还接受 `Idempotency-Key`，浏览器按
workspace + 文件名/type/size/content hash 生成稳定值，服务端只持久化其 SHA-256；对象、DB 与
outbox 的部分成功会续跑或显式隔离，不以删除原始对象补偿。Flag 置 `0` 会关闭骨架创建、恢复、读写和下载入口但
不删除任一存储；显式会话撤销仍可用，避免回滚期间把浏览器凭据留在服务端。

S04/P4.1-P4.4 起，新 workspace ID 使用 128-bit CSPRNG，workspace secret 与一小时 access token 均使用
256-bit CSPRNG。`POST /public-api/walking-skeleton/v1/sessions` 用 workspace ID + secret 交换短时
session；未知 ID、错误 secret 与格式错误统一返回 `workspace_not_found`，服务端只以 SHA-256 verifier
配合 constant-time compare 验证。S03 的 96-bit legacy workspace ID 继续可验证，既有恢复资产不迁移、
不重写、不删除。用户可复制恢复码或下载/导入严格四字段、4 KiB 上限的 `.kmfa-recovery` 文件；
恢复材料只经 POST 正文传输且服务端不保存明文。工作区内可原子轮换恢复 secret，轮换后旧码、旧文件
与旧 ID+secret 交换立即失效，同时撤销该工作区全部旧 session 并原子签发替代 session。

浏览器 API 不再返回 access token 明文，而是使用 host-only 的
`__Secure-kmfa_session` Cookie：`Secure`、`HttpOnly`、`SameSite=Strict`、API-scoped Path 和一小时
Max-Age；现存 S03/P4.1 bearer 在自身到期前继续兼容读写，冲突的 bearer+Cookie fail closed。用户可调用
`DELETE /public-api/walking-skeleton/v1/sessions/current` 立即撤销服务端 session 并清除 Cookie。
仅携带 session Cookie 的写操作还必须带匹配 scheme/host 的同源 `Origin`，防止同站兄弟域代发请求。
全局边界拒绝 URL path/query/Referer 内含原始、percent-encoded 或重复编码 capability；Walking
Skeleton 的字段校验错误只返回固定错误码，不回显提交值。进程日志会脱敏恢复码、session、device
Cookie、Bearer 和异常；生产 Uvicorn raw access log 已关闭。CSP `connect-src 'self'`、`no-referrer`、
`private, no-store` 与无第三方分析/错误 SDK 的依赖边界共同阻止遥测外送。最终镜像 Gate 会扫描
URL、Referer、日志、审计事件、错误、缓存、状态文件与截图，并验证轮换/显式撤销后的旧 session
重放失败。

P4.4 不用账号替代安全边界。生产 compose 固定
`KMFA_ABUSE_POLICY_MODE=enforced`；未知值会让全部受保护操作 fail closed，公共根页和 Walking Skeleton
状态仍可浏览。策略 `p44-v1` 对 identity、recovery、mutation、upload、export、read 分别建立
10 秒与 1 小时窗口，并同时检查 edge IP、`__Host-kmfa_device`、workspace 与全局四层 HMAC tag；
控制面不保存原始 IP、device、workspace ID、文件名或 capability。IP 桶比 device 桶宽，避免共享
NAT 误伤；更换 device/IP 仍无法绕过 workspace 与 global 桶。upload/export 另有全局并发 lease，
从请求进入一直持有到最后一个 ASGI response body；超时 lease 会自动回收。

actor 层超限时返回一次性、90 秒、actor+workspace+operation 绑定的 SHA-256 work challenge；公共前端
在内存中自动求解并只通过 `X-KMFA-Challenge-Proof` 重试一次，不进入 URL、日志或持久证据。proof
不能重放或跨 actor/operation 使用，也永远不能绕过 global/concurrency budget。global 或并发用尽
直接 `429 risk_capacity_limited`，公共浏览不关闭。拒绝只写入独立
`abuse-control/abuse_control.sqlite3` 的固定维度聚合/分桶窗口，容量首次触发每五分钟至多写一条
结构化告警；私有 `/ops/abuse-control/status` 可读取无原始标识的指标。紧急回滚只能把 mode 切到
`emergency-expensive-only`，让低成本 read/mutation 恢复、继续限制 identity/recovery/upload/export；
不存在生产 `off` 模式。

S04 开始签发的 22 字符 workspace ID 不被 S03/P4.1 之前的 reader 接受。首次创建 S04 workspace
之后，Walking Skeleton 开启状态下不得把运行镜像降到 P4.1 之前；快速回滚应保留当前 S04 reader 与
named volume，只关闭 `KMFA_WALKING_SKELETON_ENABLED` 或切换紧急策略，再前滚修复。任何 ordinary
revert 都必须继续包含 P4.1 双 ID reader；禁止用删卷、改 verifier 或重放恢复包代替兼容回滚。

adapter 还设置有限的 lifetime resource ceiling：最多 10,000 个 workspace、每 workspace 8 个
活动 session、每 workspace 10,000/全局 250,000 条业务审计、全局 512 MiB artifact 字节，并在写入前
保留 128 MiB 文件系统余量；原有单文件 8 MiB、单 workspace 一个 artifact 上限不变。达到上限只拒绝
新昂贵动作，不删除既有项目或文件。这些是灰度安全预算，不是生产采用率、容量或“永久保存”证明；
P5.2 对象层沿用这些早期 API 限额，S05/P5.4 仍必须用备份恢复重新定容并测量 RPO/RTO。

S05/P5.1 把 schema 升到 v2：`projects`、`project_metrics`（progress/score）、
`financial_records`、`artifact_versions`、`workspace_tasks` 与 append-only audit 均由有序、
checksum-locked、expand-only migration 建立，并由 repository/service transaction 边界写入。
`legacy-sqlite` 仍是未配置时的默认 reader；`postgresql-primary` 只有完整
`KMFA_STRUCTURED_DATABASE_URL` 时才启用，未知 mode、缺 DSN 或连接失败均返回固定 503，不回显 DSN。
旧 v1.5 SQLite 可用
`python -m app.legacy_sqlite_import --source /只读路径/walking_skeleton.sqlite3`
幂等导入 PostgreSQL；DSN 只从环境读取，源文件只读且冲突会让整个事务回滚。快速回滚可恢复
`legacy-sqlite`，不得删、改或覆盖源 SQLite/PG volume；migration 采用 forward-fix，不做 destructive
downgrade。

S05/P5.2 加入 `KMFA_ARTIFACT_STORAGE_MODE=s3` 的私有对象 adapter。它只有在 endpoint、bucket、
region、prefix 与 bucket-scoped access key 全部存在时才启用；未知 mode、缺项、非本机 HTTP endpoint
或依赖故障均固定 503，不回显 endpoint 或凭据。对象 key 只含内部 workspace/artifact/version ID 和
SHA-256，不含用户文件名；每个 `artifact_version` 独占 key，并以 `If-None-Match: *` 条件写阻止覆盖。
数据库继续保存 backend、key、原名、reported media type、size、SHA-256、状态与 project/artifact
血缘；下载只经匿名 capability 校验后的同源 attachment response，永不返回 bucket URL 或 presigned
URL。对象 inventory 会深读原始字节计算 SHA-256，与 DB index 和对象 metadata 对账；missing、
checksum/metadata mismatch、orphan 和 duplicate index key 都进入固定 repair state，报告仅保留对象
key 的不可逆短 hash。

Cloudflare R2 当前官方 S3 兼容表不实现 bucket versioning API，所以 KMFA 不伪报 R2 native versioning；
provider-neutral 合同是上述 immutable application-version key。生产等价 Oracle 使用额外启用 native
versioning 的私有 MinIO bucket，验证多类型/大小、同名、重复内容、两 App 节点、对象服务保卷替换、
匿名读取 403、越 prefix 403、异常对账和切回 `legacy-filesystem` 后 S3 双读。可复现命令：

```bash
python KMFA/app/e2e/object_storage_flow.py \
  --image kmfa-app:e2e \
  --state-dir "$(mktemp -d /tmp/kmfa-p52-state.XXXXXX)" \
  --out-dir object-storage-e2e \
  --prefix kmfa-p52-local
```

本地 `docker-compose.yml` 的 `s3` profile 固定 MinIO/MC digest、私有 policy 与
`kmfa-object-data` named volume；启动前必须显式提供不同的 MinIO root 和 App S3 凭据，并固定
`KMFA_S3_BUCKET=kmfa-private-artifacts`、`KMFA_S3_PREFIX=kmfa/private/v1`。生产 R2 endpoint 必须
HTTPS，`KMFA_S3_ALLOW_INSECURE_LOCAL=1` 只接受 loopback/`object-store` fixture。

S05/P5.3 把 schema expand 到 v3：`consistency_operations` 保存 hashed idempotency 与
upload/process/index/export 的固定状态，`consistency_outbox` 使用 lease + retry，消费者必须以
`dedupe_key` 原子去重并回写稳定 receipt；append-only trace 和 `object_quarantine` 让未知结果能
续跑或隔离。真实 upload 已接入 staging → object verify → DB+outbox 原子提交 → converged 链；
process/index/export 的通用 adapter 合同已通过 synthetic Oracle，但业务处理器、搜索索引和导出器
仍由各自后续 Stage 接线，状态页不会伪报已运行。可执行 upload reconciliation：

```bash
python -m app.consistency_worker --limit 100 --isolate-after-attempts 5
```

同一候选镜像的 PostgreSQL + 私有 MinIO + 外部 synthetic effect sink 故障矩阵：

```bash
python KMFA/app/e2e/consistency_state_flow.py \
  --image kmfa-app:e2e \
  --state-dir "$(mktemp -d /tmp/kmfa-p53-state.XXXXXX)" \
  --out-dir consistency-state-e2e \
  --prefix kmfa-p53-local
```

快速回滚把 `KMFA_CONSISTENCY_STATE_MODE=paused`：只拒绝新上传，既有项目、恢复、读取、下载及
reconciliation 保持可用；恢复写入时重新置 `recoverable-v1`。v3 是 expand-only/forward-fix，
旧二进制不能通过降 schema 回滚；禁止 destructive downgrade、删 outbox/trace、删对象或删卷。

这仍不是 GA 或“永久保存”证明：P5.4 数据库/对象备份恢复、保留与明确删除，S06
恶意文件扫描与多文件/大文件上传仍未完成。P5.2 只证明对象层、私有策略、版本/checksum 与
inventory reconciliation；禁止把 MinIO named volume replacement 宣传为备份恢复或长期 RPO/RTO
已通过。快速回滚只把新写 mode 恢复 `legacy-filesystem`，保留 S3 配置供已写版本双读，并保留
`kmfa-app-state`、`kmfa-object-data` 与 PostgreSQL 数据；不得 `down -v`、删对象或移除 legacy reader。

本地跑：`cd KMFA/app/backend && uvicorn app.main:app --reload`（未设置
`KMFA_PRIVATE_OPS_REQUIRE_ACCESS` 时仅用于本机开发，私有面守卫关闭）。
测试：`python -m pytest KMFA/app/backend/tests`
前端（React/Vite/ECharts）与 docker-compose 集成随 PROD.0002/0003；
生产 compose 强制 `KMFA_PRIVATE_OPS_REQUIRE_ACCESS=1`；team domain 或 Audience tags 缺失时私有面
fail-closed。上线与回滚顺序见 `deploy/coolify/README.md`；Tunnel 仅为 fallback。
