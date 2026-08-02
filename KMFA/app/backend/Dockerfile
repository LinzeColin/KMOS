# 前端 ``dist`` 是本提交的一部分；CI 会先以锁定依赖重建它，并拒绝任何
# 未提交的差异。生产镜像只复制该受检产物，不在小磁盘 Coolify 主机临时展开
# Node 依赖树，避免无关的构建缓存挤占每日资金运行空间。
FROM python:3.12-slim-bookworm
WORKDIR /opt/kmfa/KMOS/KMFA/app/backend
# build context = 仓根（compose）。先装依赖（缓存友好）再烧代码。
COPY KMFA/app/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# 自包含：不再依赖运行时卷挂载（Coolify 的 ./ 挂载只含 compose）。
# App 只依赖 KMFA 与跨项目契约层 KMDatabase；禁止把其他产品线烧入镜像，
# 否则小磁盘 Coolify 宿主会在无缓存构建时耗尽空间。
COPY KMDatabase /opt/kmfa/KMOS/KMDatabase
COPY KMFA /opt/kmfa/KMOS/KMFA
# 显式重复制受 CI 校验的静态产物，防止日后 ``COPY KMFA`` 范围变化时静默遗漏。
COPY KMFA/app/frontend/dist /opt/kmfa/KMOS/KMFA/app/frontend/dist
# Raw request-target access logs are disabled: a caller can control query
# strings before application middleware runs. The app keeps structured,
# capability-redacted audit events instead. Port 8000 is internal-only behind
# the deployment proxy, whose forwarded scheme is required by the exact-origin
# session mutation boundary.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--proxy-headers", "--forwarded-allow-ips", "*"]
