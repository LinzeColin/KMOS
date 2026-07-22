#!/usr/bin/env bash
# KMFA.app 的真入口（TSK.KMFA.PROD.0015）。
#
# 从「打开一个静态 HTML」升级为「起服务 + 开 App」：
#   起 docker 容器（已在跑就复用）→ 等 /healthz 就绪 → 用默认浏览器打开根路径
#
# 保留旧入口的干跑契约：KMFA_APP_LAUNCH_DRY_RUN=1 时只打印将要做什么并退出 0，
# 供 check_v013_s00_app_entry.py 那类验收器无副作用地检查绑定关系。
set -euo pipefail

PORT="${KMFA_APP_PORT:-8000}"
IMAGE="${KMFA_APP_IMAGE:-kmfa-app:local}"
CONTAINER="${KMFA_APP_CONTAINER:-kmfa-app-local}"
URL="http://127.0.0.1:${PORT}/"
REPO="${KMFA_REPO_DIR:-__REPO_DIR__}"
LOG="${KMFA_APP_ENTRY_LOG:-$HOME/Library/Logs/KMFA-app-entry.log}"

log() { mkdir -p "$(dirname "$LOG")"; echo "$(date -Iseconds) $*" >> "$LOG"; }

if [ "${KMFA_APP_LAUNCH_DRY_RUN:-0}" = "1" ]; then
  echo "KMFA_APP_LAUNCH: 起服务+开 App（非打开静态 HTML）"
  echo "KMFA_APP_LAUNCH_REPO: ${REPO}"
  echo "KMFA_APP_LAUNCH_IMAGE: ${IMAGE}"
  echo "KMFA_APP_LAUNCH_CONTAINER: ${CONTAINER}"
  echo "KMFA_APP_LAUNCH_URL: ${URL}"
  exit 0
fi

fail() {
  log "FAILED: $*"
  /usr/bin/osascript -e "display alert \"KMFA 启动失败\" message \"$1\n\n日志：$LOG\" as critical" >/dev/null 2>&1 || true
  exit 1
}

command -v docker >/dev/null 2>&1 || fail "未找到 docker。请先启动 Docker Desktop。"
docker info >/dev/null 2>&1 || fail "Docker 未运行。请先启动 Docker Desktop。"
[ -d "$REPO/KMFA" ] || fail "仓库目录不存在：$REPO"

log "launch: repo=$REPO image=$IMAGE container=$CONTAINER url=$URL"

# 已在跑就复用，不重复起（双击第二次不该炸）
if [ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null || echo false)" != "true" ]; then
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    log "build: $IMAGE"
    docker build -q -f "$REPO/KMFA/app/backend/Dockerfile" -t "$IMAGE" "$REPO" >>"$LOG" 2>&1 \
      || fail "镜像构建失败，详见日志。"
  fi
  docker run -d --name "$CONTAINER" -p "127.0.0.1:${PORT}:8000" \
    -v "$HOME/Library/Application Support/KMFA/state:/var/lib/kmfa/state" \
    "$IMAGE" >>"$LOG" 2>&1 || fail "容器启动失败，详见日志。"
fi

# 等真就绪再开浏览器——否则用户看到的是一个连接被拒的页面
for _ in $(seq 1 60); do
  curl -sf "http://127.0.0.1:${PORT}/healthz" >/dev/null 2>&1 && break
  sleep 1
done
curl -sf "http://127.0.0.1:${PORT}/healthz" >/dev/null 2>&1 || fail "服务 60 秒内未就绪。"

log "ready: opening $URL"
open "$URL"
