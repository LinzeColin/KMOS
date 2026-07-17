FROM python:3.12-slim-bookworm
WORKDIR /opt/kmfa/KMOS/KMFA/app/backend
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# 仓库以卷挂载（compose），镜像不含业务数据
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
