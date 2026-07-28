#!/usr/bin/env bash
# 用容器内已认证的 dws 列出会话 → 生成 target_groups.yaml 候选 → 推私有库。
# 这样 Owner 不需要提供任何群 ID（他明确表示不做这类操作）。
set -uo pipefail
PDB_DIR=/tmp/kmfa-pdb-bootstrap
PDB_REPO="git@github.com:LinzeColin/Private-Database.git"
CONF_AREA="Private-KMDatabase/dws-config"
KEY=/opt/kmfa/secrets/kmfa_backup_deploy_key
LOG=/var/log/kmfa/dws-archive.log
mkdir -p /var/log/kmfa
log(){ echo "$(date -Iseconds 2>/dev/null || date) [bootstrap] $*" >> "$LOG"; }

command -v dws >/dev/null || { log "容器内无 dws"; exit 2; }
[ -f "$KEY" ] || { log "缺部署密钥"; exit 3; }
export GIT_SSH_COMMAND="ssh -i $KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o BatchMode=yes"

# 列群：用 `chat group list-all`，**不是** `chat list-all-conversations`。
#
# 为什么换（2026-07-28 心跳实测抓获，这是归档一周零文件的根因）：
#   旧实现调 list-all-conversations，然后按 `conversationType in (2/group/GROUP)` 过滤群。
#   但 dws 文档白纸黑字写着这条命令「返回结果包含单聊和群聊，**不区分会话类型**」——
#   返回项里压根没有 conversationType 这个字段，于是过滤器恒为空集：
#   自举每次都"成功"（rc=0）并推上一份 `# 共 0 个群` 的候选清单，
#   而下游 upstream-archive 每天 exit 4 NO_TARGET_GROUPS。
#   健康面上看到的是「自举绿、归档红」，于是一周都在查归档——查错了地方。
#   另外那条命令还有硬上限：分页已失效（hasMore 恒 false），最多只能拿 100 条会话。
# `chat group list-all` 直接只返回群，limit 上限 200，且 cursor 分页是真能翻的。
OUT=/tmp/dws_groups.json
CURSOR=""
: > "$OUT"
for _ in $(seq 1 20); do          # 20 页 × 200 = 4000 群，够用且防呆死循环
  PAGE=/tmp/dws_groups_page.json
  if [ -z "$CURSOR" ]; then
    dws chat group list-all --limit 200 --format json > "$PAGE" 2>>"$LOG" \
      || { log "列群失败(dws 未登录?)"; exit 4; }
  else
    dws chat group list-all --limit 200 --cursor "$CURSOR" --format json > "$PAGE" 2>>"$LOG" \
      || { log "列群翻页失败(cursor=$CURSOR)"; break; }
  fi
  cat "$PAGE" >> "$OUT"; echo >> "$OUT"
  CURSOR="$(python3 - "$PAGE" <<'PYC'
import json, sys
try:
    d = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    raise SystemExit(0)
while isinstance(d, dict) and not any(k in d for k in ("hasMore", "has_more")):
    nxt = d.get("data") or d.get("result")
    if not isinstance(nxt, dict):
        raise SystemExit(0)
    d = nxt
if isinstance(d, dict) and (d.get("hasMore") or d.get("has_more")):
    print(d.get("nextCursor") or d.get("next_cursor") or "")
PYC
)"
  [ -n "$CURSOR" ] || break
done
rm -f /tmp/dws_groups_page.json

python3 - "$OUT" > /tmp/target_groups.yaml <<'PY'
import json, sys

# 每页一个 JSON 文档，逐页解析后合并去重（同一个群可能跨页重复出现）。
def items_of(doc):
    if isinstance(doc, list):
        return doc
    if not isinstance(doc, dict):
        return []
    for key in ("groups", "list", "data", "items", "result", "conversations"):
        val = doc.get(key)
        if isinstance(val, list):
            return val
        if isinstance(val, dict):                 # data 再包一层的情况
            inner = items_of(val)
            if inner:
                return inner
    return []

raw = open(sys.argv[1], encoding="utf-8").read()
items, dec = [], json.JSONDecoder()
idx = 0
while idx < len(raw):
    while idx < len(raw) and raw[idx].isspace():
        idx += 1
    if idx >= len(raw):
        break
    try:
        doc, idx = dec.raw_decode(raw, idx)
    except ValueError:
        break
    items.extend(items_of(doc))

groups, seen = [], set()
for g in items:
    if not isinstance(g, dict):
        continue
    cid = g.get("openConversationId") or g.get("conversationId") or g.get("chatId") or g.get("id")
    if not cid or cid in seen:
        continue
    seen.add(cid)
    groups.append({"id": cid,
                   "name": str(g.get("title") or g.get("name") or g.get("groupName") or "").replace('"', "'")})
print("# 由云端 bootstrap 自动生成（含真实群 ID → 只进私有库，永不进公开 KMOS）")
print('output_root: "/var/lib/kmfa/dws-archive/output"')
print('cold_archive_root: "/var/lib/kmfa/dws-archive/cold"')
print('mirror_archive_path: "/var/lib/kmfa/dws-archive/DWS_Outputs.zip"')
print('output_layout: "group_directory_files_MM"')
print("per_group_zip_enabled: false")
print('mirror_mode: "whole_output_tree_zip"')
print("notion_backup_enabled: false")
print("codex_control:")
print('  automation_name: "云端钉钉DWS归档"')
print("  local_unattended_schedule_enabled: false")
print("scan:")
print('  mode: "codex_controlled_incremental_hot_cold"')
print("  page_size: 500")
print("  full_depth_no_time_or_page_truncation: true")
# 群条目的键名必须与归档器读的一致：canonical_name / open_conversation_id /
# group_type / scan_mode / enabled（见 templates/target_groups.example.yaml
# 与 archive_dingtalk_all_files.py 的 enabled_groups()/validate_config()）。
# 上一版这里写的是 id/name/mode——三个键**没有一个**是归档器认识的，
# 于是配置一送进去就 KeyError: 'canonical_name'（2026-07-28 线上实测 rc=1）。
# 它一直没被发现，是因为归档在更前面先被 NO_TARGET_GROUPS 挡住，从没读到过这份配置。
#
# canonical_name 取群标题：归档器靠它 `chat search` 反查群，再与
# open_conversation_id 交叉校验（resolve_group）。故**无标题的群直接跳过**——
# 没有标题就没法反查，留着只会在解析阶段炸掉整轮。
print("groups:")
kept = 0
for g in groups:
    if not g["name"]:
        continue
    kept += 1
    print(f'  - canonical_name: "{g["name"]}"')
    print(f'    aliases: ["{g["name"]}"]')
    print(f'    open_conversation_id: "{g["id"]}"')
    print('    group_type: "standing"')
    print('    scan_mode: "auto"')
    print("    enabled: true")
print(f"# 共 {kept} 个群（列出 {len(groups)}，跳过无标题 {len(groups) - kept}）")
sys.exit(0 if kept else 9)        # 零群不是成功——见下面 rc=9 的处理
PY
BOOT_RC=$?

# 零群必须响。上一版在这里返回 0，于是「列不出群」这件事在健康面上长得跟正常一模一样，
# 真正的症状被推给下游的 upstream_archive（rc=4），查了一周查在错的技能上。
# 机器码走 stdout：run_skill.sh 的失败码提取器抓的是 stdout，log() 只写本技能日志。
if [ "$BOOT_RC" -eq 9 ]; then
  log "列群返回 0 个群——dws 可能未登录或该账号确实不在任何群里；不推空清单，就地失败"
  echo '{"status": "NO_GROUPS_LISTED"} dws chat group list-all 返回 0 个群，拒绝推空候选清单'
  exit 5
fi

rm -rf "$PDB_DIR"
git clone --quiet --filter=blob:none --no-checkout "$PDB_REPO" "$PDB_DIR" || { log "克隆失败"; exit 1; }
cd "$PDB_DIR" || exit 1
git sparse-checkout init --cone >/dev/null 2>&1; git sparse-checkout set "$CONF_AREA" >/dev/null 2>&1; git checkout --quiet 2>/dev/null
mkdir -p "$CONF_AREA"
cp /tmp/target_groups.yaml "$CONF_AREA/target_groups.candidate.yaml"
git add "$CONF_AREA"
if git diff --cached --quiet; then log "候选清单无变化"; else
  git -c user.email=kmfa-archive@localhost -c user.name="KMFA DWS Bootstrap" commit -q -m "config(dws): 云端自举群清单候选"
  git push -q origin HEAD && log "✓ 候选群清单已推私有库" || log "✗ 推送失败"
fi
# 候选清单同时落共享卷：驾驶舱要靠它显示可勾选的群。
# Owner 2026-07-27：「dws 上游存档是增量存档，他也需要前端控制器筛选目标群」——
# 选哪些群归档必须由人勾，不能由 agent 猜。群 ID/群名是敏感信息，只进共享卷与私有库，
# 永不进公开仓。
mkdir -p /var/log/kmfa/dws
python3 - /tmp/target_groups.yaml > /var/log/kmfa/dws/candidate_groups.json <<'PYJ'
import json, re, sys
# 共享卷这份是**驾驶舱的契约**（{id, name}），刻意与 YAML 的键名解耦：
# 前端只关心"勾哪个群"，不该跟着归档器的 schema 走。
# 但解析的来源是上面那份 YAML，所以这里读的是 canonical_name / open_conversation_id。
text = open(sys.argv[1], encoding="utf-8").read()
groups, current = [], None
for line in text.splitlines():
    m = re.match(r'\s*-\s*canonical_name:\s*"([^"]*)"', line)
    if m:
        current = {"id": "", "name": m.group(1)}
        groups.append(current)
        continue
    m = re.match(r'\s*open_conversation_id:\s*"([^"]+)"', line)
    if m and current is not None:
        current["id"] = m.group(1)
groups = [g for g in groups if g["id"]]
print(json.dumps({"schema_version": "kmfa.dws.candidate_groups.v1",
                  "群数": len(groups), "群": groups}, ensure_ascii=False, indent=2))
PYJ
log "候选群清单已落共享卷（$(python3 -c "import json;print(json.load(open('/var/log/kmfa/dws/candidate_groups.json'))['群数'])" 2>/dev/null || echo '?') 个）"

rm -rf "$PDB_DIR" /tmp/target_groups.yaml "$OUT"
