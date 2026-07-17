# KMFA App（DT6，D2=A：KMIDS 同栈）

后端骨架（PROD.0001）：FastAPI 只读吃机器面——`/healthz`、`/api/状态`（页眉三元组：质量/报告/GO）、
`/api/数据管线`、`/api/断言`、`/api/技能`。私有派生层明细不经本服务暴露。

本地跑：`cd KMFA/app/backend && uvicorn app.main:app --reload`
测试：`python -m pytest KMFA/app/backend/tests`
前端（React/Vite/ECharts）与 docker-compose 集成随 PROD.0002/0003；
上线走 Cloudflare Tunnel + Access（PROD.0020/0021，等实例）。
