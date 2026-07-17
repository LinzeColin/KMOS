#!/usr/bin/env bash
# 容器入口：校验 secrets 权限 → 装载 crontab → 前台 cron。
# 带参数时透传执行（调试/验收用，如 docker run <img> sh -c '…'），不进 cron。
set -euo pipefail

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

SECRETS=/opt/kmfa/secrets/skills.env
if [ -f "$SECRETS" ]; then
  PERM="$(stat -c '%a' "$SECRETS" 2>/dev/null || stat -f '%Lp' "$SECRETS")"
  if [ "$PERM" != "600" ] && [ "$PERM" != "400" ]; then
    echo "拒绝启动：$SECRETS 权限为 $PERM，要求 600/400" >&2
    exit 1
  fi
else
  echo "警告：$SECRETS 不存在——全部技能将以 NOTIFIER_CONFIG_MISSING 空跑" >&2
fi

mkdir -p /var/log/kmfa
crontab /opt/runtime/crontab.txt 2>/dev/null || cp /opt/runtime/crontab.txt /etc/cron.d/kmfa-skills
touch /var/log/kmfa/cron.log /var/log/kmfa/ledger.jsonl
echo "$(date -Is) entrypoint: cron 启动（TZ=$TZ，KMFA_DELIVERY_ENABLED=${KMFA_DELIVERY_ENABLED:-0}）" >> /var/log/kmfa/cron.log
exec cron -f
