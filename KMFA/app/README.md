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

S04/P4.1-P4.3 起，新 workspace ID 使用 128-bit CSPRNG，workspace secret 与一小时 access token 均使用
256-bit CSPRNG。`POST /public-api/walking-skeleton/v1/sessions` 用 workspace ID + secret 交换短时
session；未知 ID、错误 secret 与格式错误统一返回 `workspace_not_found`，服务端只以 SHA-256 verifier
配合 constant-time compare 验证。S03 的 96-bit legacy workspace ID 继续可验证，既有恢复资产不迁移、
不重写、不删除。用户可复制恢复码或下载/导入严格四字段、4 KiB 上限的 `.kmfa-recovery` 文件；
恢复材料只经 POST 正文传输且服务端不保存明文。工作区内可原子轮换恢复 secret，轮换后旧码、旧文件
与旧 ID+secret 交换立即失效，同时撤销该工作区全部旧 session 并原子签发替代 session。

浏览器 API 不再返回 access token 明文，而是使用 host-only 的
`__Secure-kmfa_session` Cookie：`Secure`、`HttpOnly`、`SameSite=Strict`、API-scoped Path 和一小时
Max-Age；现存 S03/P4.1 bearer 仍只读兼容，冲突的 bearer+Cookie fail closed。用户可调用
`DELETE /public-api/walking-skeleton/v1/sessions/current` 立即撤销服务端 session 并清除 Cookie。
携带 session Cookie 的写操作还必须带匹配 scheme/host 的同源 `Origin`，防止同站兄弟域代发请求。
全局边界拒绝 URL/Referer 内含原始或 percent-encoded capability，进程日志会脱敏恢复码、session、
Bearer 和异常；生产 Uvicorn raw access log 已关闭。CSP `connect-src 'self'`、`no-referrer`、
`private, no-store` 与无第三方分析/错误 SDK 的依赖边界共同阻止遥测外送。最终镜像 Gate 会扫描
URL、Referer、日志、审计事件、错误、缓存、状态文件与截图，并验证轮换/显式撤销后的旧 session
重放失败。

这只是可替换的 Walking Skeleton，不是 GA 或“永久保存”证明：耐久数据库服务、S3-compatible
对象存储、备份恢复、恶意文件扫描、反滥用、多文件和明确删除仍由 S04–S07 完成。
禁止把单节点 named volume 或本阶段重启测试宣传为跨节点、备份或长期 RPO/RTO 已通过。

本地跑：`cd KMFA/app/backend && uvicorn app.main:app --reload`（未设置
`KMFA_PRIVATE_OPS_REQUIRE_ACCESS` 时仅用于本机开发，私有面守卫关闭）。
测试：`python -m pytest KMFA/app/backend/tests`
前端（React/Vite/ECharts）与 docker-compose 集成随 PROD.0002/0003；
生产 compose 强制 `KMFA_PRIVATE_OPS_REQUIRE_ACCESS=1`；team domain 或 Audience tags 缺失时私有面
fail-closed。上线与回滚顺序见 `deploy/coolify/README.md`；Tunnel 仅为 fallback。
