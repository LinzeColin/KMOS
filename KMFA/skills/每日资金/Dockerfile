# Keep the daily-funds base identical to the App image.  Coolify builds both
# services from the same constrained host, so a different rolling ``slim`` tag
# would make Docker retain a second Debian base solely for this isolated slice.
# The explicit bookworm base already contains the timezone and CA bundle that
# the worker needs at runtime.
FROM python:3.12-slim-bookworm AS dws-installer

WORKDIR /opt/daily-funds
COPY KMFA/skills/每日资金/install_dws.sh KMFA/skills/每日资金/dws.sha256.lock /opt/daily-funds/

# curl is a build-only dependency for the pinned DWS release.  Do not retain
# it in the worker image: all runtime HTTP clients are Python stdlib/boto3.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && chmod 0755 /opt/daily-funds/install_dws.sh \
    && /opt/daily-funds/install_dws.sh

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    OMP_THREAD_LIMIT=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      cron git openssh-client \
      tesseract-ocr tesseract-ocr-chi-sim poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/daily-funds
COPY KMFA/skills/每日资金/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Pin DWS separately from the shared skills runtime.  This service owns an
# isolated profile/keyring and never mounts the shared DWS volumes.  Only the
# verified executable crosses the build-stage boundary; the downloader and
# temporary release archive never reach the production layer.
COPY --from=dws-installer /usr/local/bin/dws /usr/local/bin/dws

COPY KMFA/skills/每日资金 /opt/daily-funds
ARG SOURCE_COMMIT
# This file is an image-layer fact, not a runtime environment value.  The
# worker hashes it before writing any app-readable projection so neither a
# source SHA nor a container identity can escape through the status UI.
RUN python3 -c "from pathlib import Path; import os; value = os.environ.get('SOURCE_COMMIT', '').strip(); valid = len(value) == 40 and all(ch in '0123456789abcdef' for ch in value); Path('/opt/daily-funds/daily_funds/.kmfa-source-commit').write_text((value if valid else 'UNKNOWN') + chr(10), encoding='ascii')" \
    && chmod 0444 /opt/daily-funds/daily_funds/.kmfa-source-commit
RUN chmod 0755 /opt/daily-funds/entrypoint.sh /opt/daily-funds/healthcheck.sh /opt/daily-funds/scripts/run_daily_funds.py /opt/daily-funds/scripts/run_cron_job.sh /opt/daily-funds/scripts/run_history_probe_broker.py /opt/daily-funds/scripts/run_recovery_broker.py

ENTRYPOINT ["/opt/daily-funds/entrypoint.sh"]
