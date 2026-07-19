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

# 收件人 id 解析必须在 dry-run 之前——2026-07-20 主机实测踩过：旧版只在真发分支解析，
# 且只看 result/items 顶层、找不到就 print(None)，于是 dry-run 全绿、真发才炸
# （dws 收到空 receiverUid → 「单聊时 receiverUid 不能为空」）。现改为递归全树找 id + 空即中止。
USER_ID="$(echo "$SEARCH_JSON" | python3 -c '
import json, sys
KEYS = ("userId", "userid", "user_id", "openDingtalkId", "open_dingtalk_id", "unionId")
found = []
def walk(node):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in KEYS and isinstance(v, str) and v.strip():
                found.append((KEYS.index(k), v.strip()))
            else:
                walk(v)
    elif isinstance(node, list):
        for item in node:
            walk(item)
walk(json.load(sys.stdin))
if not found:
    sys.exit("contact search 返回里找不到 userId/openDingtalkId —— 请核对收件人是否在通讯录")
found.sort()          # KEYS 顺序即优先级：userId 优先（单聊 --user 实测可送达）
print(found[0][1])
')"
[ -n "$USER_ID" ] || { echo "收件人 id 解析为空——中止，不向 dws 传空值" >&2; exit 1; }
echo "   解析到收件人 id：$USER_ID"

if [ "${KMFA_TEST_SEND_CONFIRM:-0}" != "1" ]; then
  echo "② dry-run（未发送）。真实发送请置 KMFA_TEST_SEND_CONFIRM=1 后重跑。"
  echo "   将发送：title=$TITLE text=$TEXT → $RECIPIENT（id=$USER_ID）"
  exit 0
fi

echo "② 真实发送 → $RECIPIENT（id=$USER_ID）"
# 单聊用 --user <userId>：2026-07-20 主机实测可送达；旧 --open-dingtalk-id 传空即报 receiverUid 不能为空
dws chat message send --user "$USER_ID" --title "$TITLE" --text "$TEXT" --format json
