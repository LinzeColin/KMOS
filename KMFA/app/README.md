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
SHA-256。恢复码与会话 capability 在服务端只存 hash；SQLite 结构化状态和私有文件字节分别写入
`/var/lib/kmfa/state/walking-skeleton` 下的数据库与对象目录，由 `kmfa-app-state` named volume 跨容器
重启保留。Flag 置 `0` 会关闭骨架创建、恢复、读写和下载入口但不删除卷内状态；显式会话撤销仍可用，
避免回滚期间把浏览器凭据留在服务端。

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

早期 adapter 还设置有限的 lifetime resource ceiling：最多 10,000 个 workspace、每 workspace 8 个
活动 session、每 workspace 10,000/全局 250,000 条业务审计、全局 512 MiB artifact 字节，并在写入前
保留 128 MiB 文件系统余量；原有单文件 8 MiB、单 workspace 一个 artifact 上限不变。达到上限只拒绝
新昂贵动作，不删除既有项目或文件。这些是灰度安全预算，不是生产采用率、容量或“永久保存”证明；
S05 必须用真实耐久数据库/对象存储与备份恢复重新定容。

这只是可替换的 Walking Skeleton，不是 GA 或“永久保存”证明：耐久数据库服务、S3-compatible
对象存储、备份恢复、恶意文件扫描、多文件和明确删除仍由 S05–S07 完成。
禁止把单节点 named volume 或本阶段重启测试宣传为跨节点、备份或长期 RPO/RTO 已通过。

本地跑：`cd KMFA/app/backend && uvicorn app.main:app --reload`（未设置
`KMFA_PRIVATE_OPS_REQUIRE_ACCESS` 时仅用于本机开发，私有面守卫关闭）。
测试：`python -m pytest KMFA/app/backend/tests`
前端（React/Vite/ECharts）与 docker-compose 集成随 PROD.0002/0003；
生产 compose 强制 `KMFA_PRIVATE_OPS_REQUIRE_ACCESS=1`；team domain 或 Audience tags 缺失时私有面
fail-closed。上线与回滚顺序见 `deploy/coolify/README.md`；Tunnel 仅为 fallback。
