#!/usr/bin/env bash
# 健康检查：cron 存活、总台账活跃、项目成本运行态新鲜且结构有效。
set -uo pipefail
pgrep -x cron >/dev/null || { echo "cron 未运行"; exit 1; }
LEDGER=/var/log/kmfa/ledger.jsonl
if [ -s "$LEDGER" ]; then
  LAST_EPOCH="$(date -d "$(tail -1 "$LEDGER" | sed -E 's/.*"ts":"([^"]+)".*/\1/')" +%s 2>/dev/null || echo 0)"
  NOW="$(date +%s)"
  if [ "$LAST_EPOCH" -gt 0 ] && [ $((NOW - LAST_EPOCH)) -gt $((48*3600)) ]; then
    echo "台账超过 48h 无记录"; exit 1
  fi
fi
PROJECT_COST_DIR=/var/log/kmfa/project_cost
START_FILE=$PROJECT_COST_DIR/.container_started_at
RUNTIME=$PROJECT_COST_DIR/recent_completed.json
NOW="$(date +%s)"
STARTED="$(cat "$START_FILE" 2>/dev/null || echo 0)"
if [ "$STARTED" -gt 0 ] && [ $((NOW - STARTED)) -lt 1800 ]; then
  # Cold refresh parses the full private source set. Give it 30 minutes before
  # requiring a new runtime so the health check cannot restart it mid-run.
  exit 0
fi
[ -s "$RUNTIME" ] || { echo "项目成本运行态缺失"; exit 1; }
RUNTIME_MTIME="$(stat -c %Y "$RUNTIME" 2>/dev/null || echo 0)"
[ "$RUNTIME_MTIME" -gt 0 ] || { echo "项目成本运行态时间不可读"; exit 1; }
[ $((NOW - RUNTIME_MTIME)) -le $((36*3600)) ] || {
  echo "项目成本运行态超过 36h 未成功刷新"; exit 1;
}
python3 - "$RUNTIME" "$LEDGER" <<'PY' || exit 1
import json
import re
import sys
from datetime import datetime
from pathlib import Path

runtime = Path(sys.argv[1])
payload = json.loads(runtime.read_text(encoding="utf-8"))
if payload.get("schema_version") != "kmfa.project_cost.current.v4":
    raise SystemExit("项目成本运行态 schema 不受支持")
if payload.get("计算状态") not in ("PASS", "PASS_WITH_OPEN_REVIEWS"):
    raise SystemExit("项目成本运行态不是可服务状态")
binding = payload.get("封印工作簿") or {}
if not binding.get("文件名") or not binding.get("SHA256"):
    raise SystemExit("项目成本运行态缺封印工作簿绑定")
source = payload.get("封印来源") or {}
private_input_digest = str(source.get("私有输入清单SHA256") or "")
if (
    source.get("源码摘要算法") != "kmfa.project_cost.subject_tree.v1"
    or re.fullmatch(r"[0-9a-f]{64}", str(source.get("源码SHA256") or "")) is None
    or re.fullmatch(r"[0-9a-f]{64}", private_input_digest) is None
    or source.get("输入清单类型") != "PRIVATE_MANIFEST_SHA256"
    or source.get("输入清单SHA256") != private_input_digest
    or re.fullmatch(
        r"[0-9a-f]{64}",
        str(source.get("选中来源绑定SHA256") or ""),
    )
    is None
):
    raise SystemExit("项目成本运行态缺源码或输入清单封印绑定")
latest = None
ledger = Path(sys.argv[2])
if ledger.is_file():
    for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("skill") == "project-cost-refresh":
            latest = row
if latest and int(latest.get("rc") or 0) != 0:
    ts = str(latest.get("ts") or "").replace("Z", "+00:00")
    try:
        failed_at = datetime.fromisoformat(ts).timestamp()
    except ValueError:
        failed_at = runtime.stat().st_mtime + 1
    if failed_at >= runtime.stat().st_mtime:
        raise SystemExit("项目成本最近一次刷新失败")
PY
exit 0
