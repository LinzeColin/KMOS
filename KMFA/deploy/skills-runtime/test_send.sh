#!/usr/bin/env bash
# 「张霖泽」测试投递（Owner 2026-07-17 授权的测试收发对象）。
# 默认 dry-run：只解析收件人并打印将要发送的内容；置 KMFA_TEST_SEND_CONFIRM=1 才真实发送。
set -euo pipefail

RECIPIENT="${1:-张霖泽}"
TITLE="${2:-KMFA 云端基座连通性测试}"
TEXT="${3:-这是一条来自云端 KMFA skills 基座的测试消息（可忽略）。}"

echo "① 解析收件人：$RECIPIENT"
SEARCH_JSON="$(dws contact user search --query "$RECIPIENT" --format json)"
echo "$SEARCH_JSON"
echo "$SEARCH_JSON" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("success") is True, "contact search 失败"'

if [ "${KMFA_TEST_SEND_CONFIRM:-0}" != "1" ]; then
  echo "② dry-run（未发送）。真实发送请置 KMFA_TEST_SEND_CONFIRM=1 后重跑。"
  echo "   将发送：title=$TITLE text=$TEXT → $RECIPIENT"
  exit 0
fi

echo "② 真实发送 → $RECIPIENT"
OPEN_ID="$(echo "$SEARCH_JSON" | python3 -c 'import json,sys
d=json.load(sys.stdin)
rows=d.get("result") or d.get("items") or []
rows=rows if isinstance(rows,list) else [rows]
assert rows, "查无此人"
r=rows[0]
print(r.get("openDingtalkId") or r.get("open_dingtalk_id") or r.get("userId") or r.get("userid"))')"
dws chat message send --open-dingtalk-id "$OPEN_ID" --title "$TITLE" --text "$TEXT" --format json
