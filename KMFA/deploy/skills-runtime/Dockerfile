# KMFA skills 云端运行容器（Oracle A1 arm64 / 本地 amd64 通用）
FROM python:3.12-slim-bookworm

ENV TZ=Australia/Sydney \
    PYTHONUNBUFFERED=1 \
    DWS_BIN=/usr/local/bin/dws

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      cron curl ca-certificates git tzdata flock procps \
 && rm -rf /var/lib/apt/lists/* \
 && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 技能公共 Python 依赖（各技能自带 requirements 时在此汇总固定）
RUN pip install --no-cache-dir openpyxl pyyaml requests

COPY install_dws.sh dws.sha256.lock* /opt/runtime/
RUN chmod +x /opt/runtime/install_dws.sh && /opt/runtime/install_dws.sh

COPY entrypoint.sh run_skill.sh healthcheck.sh test_send.sh crontab.txt /opt/runtime/
RUN chmod +x /opt/runtime/*.sh

WORKDIR /opt/kmfa/KMOS
HEALTHCHECK --interval=5m --timeout=20s --start-period=1m \
  CMD /opt/runtime/healthcheck.sh || exit 1
ENTRYPOINT ["/opt/runtime/entrypoint.sh"]
