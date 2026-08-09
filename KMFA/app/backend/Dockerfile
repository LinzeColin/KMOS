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
# Coolify may provide the checked-out source commit only at build time.  Keep
# a strictly validated copy in the immutable image layer instead of an
# environment variable or a shared volume; the application will expose only
# a one-way fingerprint comparison and never the raw SHA.
ARG SOURCE_COMMIT
RUN python3 -c "from pathlib import Path; import os; value = os.environ.get('SOURCE_COMMIT', '').strip(); valid = len(value) == 40 and all(ch in '0123456789abcdef' for ch in value); Path('/opt/kmfa/KMOS/KMFA/app/backend/app/.kmfa-source-commit').write_text((value if valid else 'UNKNOWN') + chr(10), encoding='ascii')" \
    && chmod 0444 /opt/kmfa/KMOS/KMFA/app/backend/app/.kmfa-source-commit
# Raw request-target access logs are disabled: a caller can control query
# strings before application middleware runs. The app keeps structured,
# capability-redacted audit events instead. Port 8000 is internal-only behind
# the deployment proxy, whose forwarded scheme is required by the exact-origin
# session mutation boundary.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--proxy-headers", "--forwarded-allow-ips", "*"]
