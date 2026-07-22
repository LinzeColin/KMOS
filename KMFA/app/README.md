# KMFA App（DT6，D2=A：KMIDS 同栈）

后端骨架（PROD.0001）：根路径 `/` 是 canonical 公共 App Shell，`/ui` 与 `/ui/` 单跳 `308` 回 `/`；
`/healthz` 是不含内部细节的公共浅健康。既有 `/api*`、`/ops/openapi.json`、`/ops/docs` 与
`/ops/healthz` 属于私有运维面；既有经营仪表盘兼容入口为 `/ops/app`。生产由路径级 Cloudflare
Access 加源站 JWT 校验双重保护。公共壳异常时把 `KMFA_PUBLIC_SHELL_ENABLED=0` 并重部署，可仅关闭
增强 JavaScript、保留根路径六项稳定静态入口；该回滚不动数据，也不放松 `/api*`、`/ops*` 守卫。

本地跑：`cd KMFA/app/backend && uvicorn app.main:app --reload`（未设置
`KMFA_PRIVATE_OPS_REQUIRE_ACCESS` 时仅用于本机开发，私有面守卫关闭）。
测试：`python -m pytest KMFA/app/backend/tests`
前端（React/Vite/ECharts）与 docker-compose 集成随 PROD.0002/0003；
生产 compose 强制 `KMFA_PRIVATE_OPS_REQUIRE_ACCESS=1`；team domain 或 Audience tags 缺失时私有面
fail-closed。上线与回滚顺序见 `deploy/coolify/README.md`；Tunnel 仅为 fallback。
