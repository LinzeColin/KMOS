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

OUT=/tmp/dws_convs.json
dws chat list-all-conversations --format json > "$OUT" 2>>"$LOG" || { log "列会话失败(dws 未登录?)"; exit 4; }

python3 - "$OUT" > /tmp/target_groups.yaml <<'PY'
import json, sys
raw = open(sys.argv[1], encoding="utf-8").read()
try:
    d = json.loads(raw)
except Exception:
    print("# 解析失败"); sys.exit(1)
items = d if isinstance(d, list) else (d.get("data") or d.get("conversations") or d.get("items") or [])
groups = [x for x in items if str(x.get("conversationType", x.get("type", ""))) in ("2", "group", "GROUP")]
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
print("groups:")
for g in groups:
    cid = g.get("conversationId") or g.get("openConversationId") or g.get("id")
    name = str(g.get("title") or g.get("name") or "").replace('"', "'")
    if not cid: continue
    print(f'  - id: "{cid}"')
    print(f'    name: "{name}"')
    print('    mode: "auto"')
print(f"# 共 {len(groups)} 个群")
PY

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
text = open(sys.argv[1], encoding="utf-8").read()
groups, current = [], None
for line in text.splitlines():
    m = re.match(r'\s*-\s*id:\s*"([^"]+)"', line)
    if m:
        current = {"id": m.group(1), "name": ""}
        groups.append(current)
        continue
    m = re.match(r'\s*name:\s*"([^"]*)"', line)
    if m and current is not None:
        current["name"] = m.group(1)
print(json.dumps({"schema_version": "kmfa.dws.candidate_groups.v1",
                  "群数": len(groups), "群": groups}, ensure_ascii=False, indent=2))
PYJ
log "候选群清单已落共享卷（$(python3 -c "import json;print(json.load(open('/var/log/kmfa/dws/candidate_groups.json'))['群数'])" 2>/dev/null || echo '?') 个）"

rm -rf "$PDB_DIR" /tmp/target_groups.yaml "$OUT"
