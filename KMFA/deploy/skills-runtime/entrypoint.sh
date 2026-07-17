#!/usr/bin/env bash
# 容器入口：校验 secrets 权限 → 装载 crontab → 前台 cron。
# 带参数时透传执行（调试/验收用，如 docker run <img> sh -c '…'），不进 cron。
set -euo pipefail

# 业务锚不变量：容器挂钟必须是北京时间（+0800，中国无夏令时，全年零漂移）。
# 任何运行时 TZ 覆盖（曾见 docker-compose environment 误设 Australia/Sydney）都会让
# cron 按错时区评估排程、让技能打错报表日期——此处快速失败，杜绝 #100/#108 锚定被静默回退。
TZ_OFFSET="$(date +%z)"
if [ "$TZ_OFFSET" != "+0800" ]; then
  echo "拒绝启动：容器挂钟偏移 $TZ_OFFSET（TZ=${TZ:-未设}），业务锚要求 +0800（Asia/Shanghai）。" >&2
  echo "  多半是 docker-compose 的 environment.TZ 覆盖了镜像 Asia/Shanghai——改回 Asia/Shanghai。" >&2
  exit 1
fi

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
