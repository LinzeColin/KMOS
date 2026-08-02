FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

RUN apt-get update \
    && apt-get install -y --no-install-recommends cron curl ca-certificates git openssh-client tzdata procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/daily-funds
COPY KMFA/skills/每日资金/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Pin DWS separately from the shared skills runtime.  This service owns an
# isolated profile/keyring and never mounts the shared DWS volumes.
COPY KMFA/skills/每日资金/install_dws.sh KMFA/skills/每日资金/dws.sha256.lock /opt/daily-funds/
RUN chmod 0755 /opt/daily-funds/install_dws.sh && /opt/daily-funds/install_dws.sh

COPY KMFA/skills/每日资金 /opt/daily-funds
RUN chmod 0755 /opt/daily-funds/entrypoint.sh /opt/daily-funds/healthcheck.sh /opt/daily-funds/scripts/run_daily_funds.py /opt/daily-funds/scripts/run_cron_job.sh

ENTRYPOINT ["/opt/daily-funds/entrypoint.sh"]
