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
重启保留。Flag 置 `0` 会关闭全部骨架写入/恢复/下载入口但不删除卷内状态。

这只是可替换的 Walking Skeleton，不是 GA 或“永久保存”证明：耐久数据库服务、S3-compatible
对象存储、备份恢复、恢复文件/轮换撤销、扫描、反滥用、多文件和明确删除仍由 S04–S07 完成。
禁止把单节点 named volume 或本阶段重启测试宣传为跨节点、备份或长期 RPO/RTO 已通过。

本地跑：`cd KMFA/app/backend && uvicorn app.main:app --reload`（未设置
`KMFA_PRIVATE_OPS_REQUIRE_ACCESS` 时仅用于本机开发，私有面守卫关闭）。
测试：`python -m pytest KMFA/app/backend/tests`
前端（React/Vite/ECharts）与 docker-compose 集成随 PROD.0002/0003；
生产 compose 强制 `KMFA_PRIVATE_OPS_REQUIRE_ACCESS=1`；team domain 或 Audience tags 缺失时私有面
fail-closed。上线与回滚顺序见 `deploy/coolify/README.md`；Tunnel 仅为 fallback。
