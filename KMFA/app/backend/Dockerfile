# 阶段一：前端在镜像里现建——「任意提交，镜像内前端必是当次源码的产物」。
# 曾拿仓里旧 dist 打镜像而不自知（e2e 工作流为此在 runner 上先 npm build 兜底）；
# 把构建挪进 Dockerfile 后，Coolify / CI / 本地 docker build 三条路走同一保证，兜底可退役。
# 仓里提交的 dist 从此只服务本机 .app 双击场景，镜像不再依赖它。
FROM node:20-alpine AS frontend
WORKDIR /fe
COPY KMFA/app/frontend/package.json KMFA/app/frontend/package-lock.json ./
RUN npm ci
COPY KMFA/app/frontend/ .
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /opt/kmfa/KMOS/KMFA/app/backend
# build context = 仓根（compose）。先装依赖（缓存友好）再烧代码。
COPY KMFA/app/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# 自包含：不再依赖运行时卷挂载（Coolify 的 ./ 挂载只含 compose）——代码烧进镜像。
COPY . /opt/kmfa/KMOS
# 现建的 dist 最后落位，覆盖仓里那份——顺序在 COPY . 之后，不许倒。
COPY --from=frontend /fe/dist /opt/kmfa/KMOS/KMFA/app/frontend/dist
# Raw request-target access logs are disabled: a caller can control query
# strings before application middleware runs. The app keeps structured,
# capability-redacted audit events instead. Port 8000 is internal-only behind
# the deployment proxy, whose forwarded scheme is required by the exact-origin
# session mutation boundary.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--proxy-headers", "--forwarded-allow-ips", "*"]
