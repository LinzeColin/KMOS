FROM python:3.12-slim-bookworm
WORKDIR /opt/kmfa/KMOS/KMFA/app/backend
# build context = 仓根（compose）。先装依赖（缓存友好）再烧代码。
COPY KMFA/app/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# 自包含：不再依赖运行时卷挂载（Coolify 的 ./ 挂载只含 compose）——代码烧进镜像。
COPY . /opt/kmfa/KMOS
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
