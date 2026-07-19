#!/usr/bin/env bash
# KMFA 实例日一键引导（Ubuntu 22.04+，amd64/arm64 通用——OVH 标准 VPS 为 amd64；幂等可重跑）。
# 用法（实例上）：
#   curl -fsSL https://raw.githubusercontent.com/LinzeColin/KMOS/main/KMFA/deploy/skills-runtime/bootstrap.sh | bash
# 完成：装 docker → HTTPS 克隆/更新仓库 → 起 skills 栈 + App 栈 → 健康自检。
# 之后只剩人工两步：`docker compose exec skills dws auth login --device`（手机确认）→ 测试发送。
set -euo pipefail

REPO_URL="https://github.com/LinzeColin/KMOS.git"
BASE=/opt/kmfa
REPO_DIR="$BASE/KMOS"

echo "== ① docker/compose/git =="
if ! command -v docker >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq docker.io docker-compose-v2 git
  sudo usermod -aG docker "$USER" || true
  echo "   docker 已装（本 shell 用 sudo 继续；下次登录后免 sudo）"
fi
DOCKER="docker"; docker info >/dev/null 2>&1 || DOCKER="sudo docker"

echo "== ② 仓库 =="
sudo mkdir -p "$BASE" && sudo chown "$USER" "$BASE"
if [ -d "$REPO_DIR/.git" ]; then
  git -C "$REPO_DIR" pull --ff-only
else
  git clone --filter=blob:none "$REPO_URL" "$REPO_DIR"
fi

echo "== ③ secrets 骨架（若缺） =="
sudo install -d -m 700 -o "$USER" "$BASE/secrets"
[ -f "$BASE/secrets/skills.env" ] || install -m 600 /dev/null "$BASE/secrets/skills.env"

echo "== ④ skills 栈 =="
(cd "$REPO_DIR/KMFA/deploy/skills-runtime" && $DOCKER compose up -d --build)

echo "== ⑤ App 栈 =="
(cd "$REPO_DIR/KMFA/app" && $DOCKER compose up -d --build)

echo "== ⑥ 健康自检 =="
for i in $(seq 1 30); do
  curl -sf http://127.0.0.1:8000/healthz >/dev/null 2>&1 && break
  $DOCKER ps >/dev/null; i=$i  # 占位防空转告警
done
curl -s http://127.0.0.1:8000/healthz && echo
$DOCKER ps --format '  {{.Names}}\t{{.Status}}'

cat <<'NEXT'
== 完成。剩余人工两步 ==
  1) dws 设备码（钉钉手机点确认）：
     cd /opt/kmfa/KMOS/KMFA/deploy/skills-runtime
     docker compose exec skills dws auth login --device
     docker compose exec skills dws pat browser-policy --enabled=false --format json --yes
  2) 测试发送（默认 dry-run；确认后加 KMFA_TEST_SEND_CONFIRM=1）：
     docker compose exec skills /opt/runtime/test_send.sh "张霖泽"
上线段（等双跑 3 天后）：KMFA/deploy/cloudflared/README.md
NEXT
