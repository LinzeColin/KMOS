#!/usr/bin/env bash
# 云端 DWS 上游归档（跑在 OVH 容器里，本机零参与）。
#
# 为什么存在：Owner 2026-07-26——「不允许本机 launch，确保本机无内存存储缓存占用，全部上云」
# 且「走不了钉钉云盘，你需要用 dws 上游归档自动整理文件」。
# 原 cron 的 upstream-archive 只跑 validate_skill_package.py（校验器），**从未真归档**，
# 所以一个文件都没取回来过——这里接上真业务入口。
#
# 链路：钉钉 --(dws，容器内已认证)--> 容器本地输出 --> GitHub 私有库 Private-Database
#       （Owner：GitHub 是唯一权威全量存储）
#
# 私有配置：群清单含真实群 ID，绝不进公开 KMOS；运行时从私有库取。
set -uo pipefail

ROOT=/opt/kmfa/KMOS
SKILL="$ROOT/KMFA/skills/上游归档"
WORKDIR=/var/lib/kmfa/dws-archive          # 容器内输出（挂 kmfa-app-state 卷则可持久）
PDB_DIR=/tmp/kmfa-pdb-archive
PDB_REPO="git@github.com:LinzeColin/Private-Database.git"
AREA="Private-KMDatabase/dws-archive"
CONF_AREA="Private-KMDatabase/dws-config"
KEY=/opt/kmfa/secrets/kmfa_backup_deploy_key
LOG=/var/log/kmfa/dws-archive.log

log(){ echo "$(date -Iseconds 2>/dev/null || date) $*" >> "$LOG"; }
mkdir -p "$WORKDIR" /var/log/kmfa

if [ ! -f "$KEY" ]; then
  log "缺部署密钥 $KEY —— 无法取私有配置/回传，跳过（不空跑假装成功）"; exit 3
fi
export GIT_SSH_COMMAND="ssh -i $KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o BatchMode=yes"

# 1) 从私有库取群清单配置（稀疏，只取配置与归档区）
rm -rf "$PDB_DIR"
git clone --quiet --filter=blob:none --no-checkout "$PDB_REPO" "$PDB_DIR" || { log "私有库克隆失败"; exit 1; }
cd "$PDB_DIR" || exit 1
git sparse-checkout init --cone >/dev/null 2>&1
git sparse-checkout set "$CONF_AREA" "$AREA" >/dev/null 2>&1
git checkout --quiet 2>/dev/null

CONF_SRC="$PDB_DIR/$CONF_AREA/target_groups.yaml"
if [ ! -f "$CONF_SRC" ]; then
  log "私有库缺 $CONF_AREA/target_groups.yaml —— 先跑 dws-list-groups 生成候选清单后再归档"
  exit 4
fi
mkdir -p "$SKILL/config"
install -m 600 "$CONF_SRC" "$SKILL/config/target_groups.yaml"
log "已载入群清单配置"

# 2) 真跑归档（容器内输出；不写宿主 OneDrive）
cd "$SKILL" || exit 1
export DWS_CODEX_CONTROLLED=1
/usr/bin/env python3 scripts/archive_dingtalk_all_files.py \
  --run-source "cloud_cron" --automation-name "云端钉钉DWS归档" "$@" >> "$LOG" 2>&1
RC=$?
log "归档退出码 rc=$RC"

# 3) 回传私有库（GitHub = 唯一权威全量存储）；无新增不产生空提交
if [ -d "$WORKDIR" ] && [ -n "$(ls -A "$WORKDIR" 2>/dev/null)" ]; then
  mkdir -p "$PDB_DIR/$AREA"
  rsync -a --exclude='.git' "$WORKDIR/" "$PDB_DIR/$AREA/" 2>/dev/null || cp -R "$WORKDIR/." "$PDB_DIR/$AREA/" 2>/dev/null
  cd "$PDB_DIR" || exit 1
  git add "$AREA" 2>/dev/null
  if git diff --cached --quiet; then
    log "无新增归档，不提交"
  else
    N=$(find "$PDB_DIR/$AREA" -type f 2>/dev/null | wc -l | tr -d ' ')
    git -c user.email=kmfa-archive@localhost -c user.name="KMFA DWS Archive" \
      commit -q -m "archive(dws): 云端归档同步（$N 文件）"
    git push -q origin HEAD && log "✓ 已回传私有库（$N 文件）" || log "✗ 回传失败，下轮重试"
  fi
fi
rm -rf "$PDB_DIR"
exit $RC
