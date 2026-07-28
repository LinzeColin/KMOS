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
# 退出时把机器码送到 **stdout**。log() 只写本技能自己的 dws-archive.log，
# 而 run_skill.sh 抓的是 stdout——所以过去归档失败在台账里只留下一个 rc=4，
# 失败码提取器什么也看不到（线上实测报回 UNKNOWN）。
# 码的形状必须是 UPPER_SNAKE：公开端点只放行这种，别的形状会被整条丢弃。
# 三个位置参数写死：码、说明、退出码。别用 shift+$*——那样退出码会被拼进说明里。
die(){ log "$2"; echo "{\"status\": \"$1\"} $2"; exit "${3:-1}"; }
mkdir -p "$WORKDIR" /var/log/kmfa

if [ ! -f "$KEY" ]; then
  die DEPLOY_KEY_MISSING "缺部署密钥 $KEY —— 无法取私有配置/回传，跳过（不空跑假装成功）" 3
fi
export GIT_SSH_COMMAND="ssh -i $KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o BatchMode=yes"

# 1) 从私有库取群清单配置（稀疏，只取配置与归档区）
rm -rf "$PDB_DIR"
git clone --quiet --filter=blob:none --no-checkout "$PDB_REPO" "$PDB_DIR" || \
  die PRIVATE_DB_CLONE_FAILED "私有库克隆失败" 1
cd "$PDB_DIR" || exit 1
git sparse-checkout init --cone >/dev/null 2>&1
git sparse-checkout set "$CONF_AREA" "$AREA" >/dev/null 2>&1
git checkout --quiet 2>/dev/null

CONF_SRC="$PDB_DIR/$CONF_AREA/target_groups.yaml"
if [ ! -f "$CONF_SRC" ]; then
  # 实测（2026-07-27 公开健康端点）：本技能连续 8 次 rc=4，全卡在这里。
  # 更正一处早先的判断：生成群清单的 bootstrap **是有排程的**（crontab 周日 10:30），
  # 但它没登记进健康面，所以「它到底跑没跑、成没成」长期无人可见（本次一并补登记）。
  # 真正的问题是节奏：归档每天跑、自举每周才跑一次，配置一旦缺失就要空转到下个周日。
  # Owner 明令「不登录、不做这类操作」，故缺配置时就地自举，不等下一个周日、也不等人。
  log "私有库缺 $CONF_AREA/target_groups.yaml —— 就地自举群清单"
  BOOT="$(dirname "$0")/bootstrap_groups_cloud.sh"
  if [ -x "$BOOT" ] || [ -f "$BOOT" ]; then
    # 自举的输出必须**同时进 stdout**，不能只写 dws-archive.log。
    # 2026-07-28 实测代价：自举在这里失败了，但它的日志只落在本技能私有的
    # dws-archive.log 里，而 run_skill.sh 抓的是 stdout ——于是私有库取证尾巴里
    # 一个字都看不到，公开端点只剩一个下游的 NO_TARGET_GROUPS。
    # 容器 exec 又是 404（Coolify 实测），等于**完全没有诊断通道**：
    # 只能改一版、部署、等下一轮，再猜一次。这正是「一个月」的那个循环。
    # tee 一份到日志、一份到 stdout，取证尾巴就能直接回答"自举为什么没列出群"。
    BOOT_OUT="$(bash "$BOOT" 2>&1)"; BOOT_RC=$?
    printf '%s\n' "$BOOT_OUT" >> "$LOG"
    printf '%s\n' "$BOOT_OUT" | tail -20
    log "自举返回码 $BOOT_RC（继续尝试重取配置）"
    git -C "$PDB_DIR" fetch --quiet origin main 2>/dev/null || true
    git -C "$PDB_DIR" checkout --quiet origin/main -- "$CONF_AREA" 2>/dev/null || true
  else
    log "找不到自举脚本 $BOOT"
  fi
fi
# 驾驶舱勾选优先：候选清单 + 人工勾选 → 已确认清单。
# 这一步存在的理由是 Owner 明确「需要前端控制器筛选目标群」——归档是增量的，
# 全量拉所有群既慢又会把无关群的文件拖进来。没有勾选就不猜，宁可停。
SEL=/var/log/kmfa/dws/selected_groups.json
CAND=/var/log/kmfa/dws/candidate_groups.json
# 没有勾选时**退回全量候选**，而不是停下来等人勾。
#
# 为什么改（2026-07-28）：原设计「没有勾选就不猜，宁可停」在纸面上是对的，但它假设了
# 有人会去驾驶舱勾。Owner 的硬性工作方式里写死了「不登录、不看页面、不点确认」——
# 这个前提永远不成立，于是「宁可停」在实际运行中等价于**永久停**：
# 归档从上线起一个文件都没取回来过，而 Owner 要的正是「用 dws 上游归档自动整理文件」。
# 两害相权：多归档几个无关群，代价是磁盘和一次增量扫描；一个群都不归档，代价是这条链白建。
# 勾选一旦出现仍然优先（人的意图永远压过兜底），兜底只在无勾选时生效，且在日志里写明。
if [ -s "$CAND" ] && [ ! -s "$SEL" ]; then
  log "驾驶舱无勾选——按全量候选自动生成目标群清单（兜底；有勾选时以勾选为准）"
  python3 - "$CAND" "$CONF_SRC" <<'PYA' && log "已按全量候选生成目标群清单"
import json, sys, os
cand = json.load(open(sys.argv[1], encoding="utf-8"))
picked = cand.get("群", [])
if not picked:
    print("候选为空——不生成清单", file=sys.stderr); raise SystemExit(1)
out = sys.argv[2]
base = out.replace("target_groups.yaml", "target_groups.candidate.yaml")
head = open(base, encoding="utf-8").read().split("groups:")[0] if os.path.exists(base) else ""
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as fh:
    fh.write(head or "# 由全量候选兜底生成（驾驶舱未勾选）\n")
    fh.write("groups:\n")
    for g in picked:
        fh.write(f'  - id: "{g["id"]}"\n    name: "{g["name"]}"\n    mode: "auto"\n')
    fh.write(f"# 兜底：全量候选 {len(picked)} 个群（驾驶舱未勾选）\n")
PYA
fi
if [ -s "$SEL" ] && [ -s "$CAND" ]; then
  python3 - "$CAND" "$SEL" "$CONF_SRC" <<'PYS' && log "已按驾驶舱勾选生成目标群清单"
import json, sys, os, re
cand = json.load(open(sys.argv[1], encoding="utf-8"))
sel = set(json.load(open(sys.argv[2], encoding="utf-8")).get("已选群", []))
picked = [g for g in cand.get("群", []) if g["id"] in sel]
if not picked:
    print("勾选为空——不生成清单", file=sys.stderr); raise SystemExit(1)
out = sys.argv[3]
base = out.replace("target_groups.yaml", "target_groups.candidate.yaml")
head = open(base, encoding="utf-8").read().split("groups:")[0] if os.path.exists(base) else ""
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as fh:
    fh.write(head or "# 由驾驶舱勾选生成\n")
    fh.write("groups:\n")
    for g in picked:
        fh.write(f'  - id: "{g["id"]}"\n    name: "{g["name"]}"\n    mode: "auto"\n')
    fh.write(f"# 驾驶舱勾选 {len(picked)} / 候选 {len(cand.get('群', []))}\n")
PYS
fi

if [ ! -f "$CONF_SRC" ]; then
  # 走到这里只剩一种成因了：连**候选**都没有（自举列不出群 → 见 NO_GROUPS_LISTED）。
  # 「勾选为空」不再是成因——无勾选已由上面的全量候选兜底接住。
  die NO_TARGET_GROUPS "无目标群清单：连候选都没有，多半是容器内 dws 未登录（自举会报 NO_GROUPS_LISTED）" 4
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
[ "$RC" -eq 0 ] || echo "{\"status\": \"ARCHIVE_RUN_FAILED\"} archive_dingtalk_all_files.py rc=$RC"

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
