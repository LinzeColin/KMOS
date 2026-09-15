#!/bin/bash
# 装两条 LaunchAgent，让「无人值守」不再以「某个 GUI 应用一直开着」为前提。
#
#   com.kmfa.attendance-brief   本机 19:20 / 20:20 / 21:20 各一枪，跑的就是
#                               Codex automation 调的同一个脚本。它比 Codex 那边
#                               晚 5 分钟，所以正常日子它只会拿到 SKIP_ALREADY_SENT；
#                               Codex 桌面端没开、排程漏触发的那天，它就是唯一发得出
#                               简报的那个。launchd 是 macOS 自己的调度器：开机自启、
#                               不依赖任何应用、机器睡过了钟点会在唤醒后补跑一次。
#   com.kmfa.keep-awake         caffeinate -s，插电时不让机器空闲休眠。
#                               本机 AC 上 pmset sleep=1（一分钟），以前全靠
#                               Claude.app / ChatGPT.app 的 Electron 断言顶着 ——
#                               应用一关，一分钟后机器就睡，所有定时任务一起停。
#                               -s 只在插电时生效，电池上照常省电。
#
# 卸载：scripts/install_launchd_trigger.sh --uninstall
set -uo pipefail
if [ -z "${HOME:-}" ]; then echo "HOME 未设置，装不了" >&2; exit 2; fi
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LA="$HOME/Library/LaunchAgents"
LOGD="$HOME/Library/Logs"
BRIEF="com.kmfa.attendance-brief"
AWAKE="com.kmfa.keep-awake"
DOMAIN="gui/$(id -u)"

unload() {   # 老的先退干净，再装新的；两种写法都试，新旧 macOS 都吃得下
  launchctl bootout "$DOMAIN/$1" 2>/dev/null
  launchctl unload -w "$LA/$1.plist" 2>/dev/null
  return 0
}
load() {
  launchctl bootstrap "$DOMAIN" "$LA/$1.plist" 2>/dev/null \
    || launchctl load -w "$LA/$1.plist" 2>/dev/null
  launchctl list "$1" >/dev/null 2>&1
}

if [ "${1:-}" = "--uninstall" ]; then
  for l in "$BRIEF" "$AWAKE"; do unload "$l"; rm -f "$LA/$l.plist"; echo "已卸载 $l"; done
  exit 0
fi

[ -x "$SKILL/scripts/kmfa_brief_cron.sh" ] || {
  echo "入口脚本不在或不可执行：$SKILL/scripts/kmfa_brief_cron.sh" >&2; exit 2; }
mkdir -p "$LA" "$LOGD"

cat > "$LA/$BRIEF.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$BRIEF</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$SKILL/scripts/kmfa_brief_cron.sh</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key><string>$HOME</string>
    <key>PATH</key><string>$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>LANG</key><string>zh_CN.UTF-8</string>
    <key>KMFA_BRIEF_TRIGGER</key><string>launchd</string>
  </dict>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Hour</key><integer>19</integer><key>Minute</key><integer>20</integer></dict>
    <dict><key>Hour</key><integer>20</integer><key>Minute</key><integer>20</integer></dict>
    <dict><key>Hour</key><integer>21</integer><key>Minute</key><integer>20</integer></dict>
  </array>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$LOGD/$BRIEF.log</string>
  <key>StandardErrorPath</key><string>$LOGD/$BRIEF.log</string>
</dict>
</plist>
PLIST

cat > "$LA/$AWAKE.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$AWAKE</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/caffeinate</string>
    <string>-s</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardErrorPath</key><string>$LOGD/$AWAKE.log</string>
</dict>
</plist>
PLIST

rc=0
for l in "$BRIEF" "$AWAKE"; do
  unload "$l"
  if load "$l"; then echo "已加载 $l"; else echo "加载失败 $l" >&2; rc=1; fi
done
echo
echo "下次触发："
launchctl print "$DOMAIN/$BRIEF" 2>/dev/null | grep -iE 'next fire|runs = ' | head -3
pgrep -x caffeinate >/dev/null && echo "caffeinate 在跑" || { echo "caffeinate 没起来" >&2; rc=1; }
exit $rc
