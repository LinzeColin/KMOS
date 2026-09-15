#!/bin/bash
# 上线前自检。只读、不发送任何消息、不改任何文件。
# 全部 PASS 才可以去设 cron；任何一条 FAIL 就停下来报告，不要自己修。
set -uo pipefail
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${KMFA_BRIEF_VENV:-$HOME/.local/share/kmfa-attendance-brief/venv}"
ENVF="$SKILL/private_runtime/kmfa_brief.env"
fail=0
ok(){ echo "  PASS  $1"; }
no(){ echo "  FAIL  $1"; fail=1; }
# 只有 ok / no 两个报告函数。曾经写成 bad(...)，shell 报 command not found，
# 失败分支静默失效、fail 永远是 0，自检照样说「全部通过」—— 假绿。
bad(){ echo "  FAIL  (内部错误：请用 no 而不是 bad) $1"; fail=1; }

echo "考勤简报上线自检"
echo "----------------------------------------"

[ -f "$ENVF" ] && ok "配置文件存在" || no "缺 $ENVF（跑 scripts/setup_attendance_brief.sh 后按模板填）"
[ -x "$VENV/bin/python" ] && ok "venv 存在" || no "缺 venv（跑 scripts/setup_attendance_brief.sh）"

if [ -x "$VENV/bin/python" ]; then
  "$VENV/bin/python" -c "import Vision,numpy,PIL" 2>/dev/null \
    && ok "OCR 依赖就绪（系统 Vision + numpy + pillow）" || no "依赖缺失（重跑 setup）"
fi

if [ -f "$ENVF" ]; then
  set -a; . "$ENVF"; set +a
  # 默认值跟 config.py 保持一致。env 文件里刻意不写这一项 ——
  # 写了会在 cron 包装脚本 source 时盖掉外面设的替身，让试跑静默变成真发。
  DWS="${KMFA_BRIEF_DWS:-$HOME/.local/bin/dws}"; DWS="${DWS/#\~/$HOME}"
  [ -x "$DWS" ] && ok "dws 命令在 $DWS" || no "dws 找不到：$DWS"
  if [ -x "$DWS" ]; then
    if "$DWS" auth status -f json 2>/dev/null | grep -q '"authenticated": true'; then
      ok "钉钉授权有效"
    else
      no "钉钉授权失效 —— 需要人工重新授权，不要自动重试"
    fi
  fi
  for v in KMFA_BRIEF_GROUP_ID KMFA_BRIEF_NOTIFY_USER KMFA_BRIEF_ARCHIVE_ROOT; do
    [ -n "${!v:-}" ] && ok "$v 已配置" || no "$v 为空"
  done
  R="${KMFA_BRIEF_ARCHIVE_ROOT:-}"
  if [ -n "$R" ]; then
    # 不能只用 [ -d ]。实测 2026-09-07 共享盘瞬断时，/Volumes/share 作为挂载点目录
    # 仍然存在，-d 照样为真，而任何读写都报 EPERM / ENOTCONN(Errno 57)。
    # 判据必须跟运行期的 smb_ready 一致：写进去、读回来、对得上。
    if P="$R/.kmfa_check_probe" && mkdir -p "$R" 2>/dev/null \
       && printf 'ok' > "$P" 2>/dev/null && [ "$(cat "$P" 2>/dev/null)" = "ok" ]; then
      rm -f "$P" 2>/dev/null; ok "SMB 归档目录可读写（写进去读得回来）"
    else
      rm -f "$P" 2>/dev/null; no "SMB 挂了或写不进：$R（瞬断时目录还在，只有读写才认得出来）"
    fi
  fi
fi

# 调度核对：调度器按本机墙钟触发，截止线是北京时间，本机（悉尼）有夏令时而北京没有，
# 所以一年里两地差 2 或 3 小时。做法是每天触发两个钟点，让脚本自己挑等于北京 17:15 的那次。
# 这里不告诉人该填几点，直接核对装上去的那份配置对不对。
# 考勤线固定两条，不多不少：一条出报（三个钟点写在同一条 rrule 里），一条看门狗。
# 认名字不认 id —— create_automation 不接受自定义 id，中文名生成不出 slug。
AUTO1="$HOME/.codex/automations/automation/automation.toml"        # 出报
AUTO2="$HOME/.codex/automations/automation-2/automation.toml"      # 看门狗
chk_auto() {   # $1=toml $2=名字关键词 $3=该调的脚本 $4=说明
  [ -f "$1" ] || { no "$4 的 automation 不见了：$1"; return; }
  grep -q "$2" "$1" || { no "$4 的 automation 名字对不上（应含「$2」）"; return; }
  grep -q 'status = "ACTIVE"' "$1" || { no "$4 的 automation 不是 ACTIVE"; return; }
  grep -q 'BYDAY=MO,TU,WE,TH,FR' "$1" || { no "$4 的 automation 缺工作日限制"; return; }
  grep -q "$3" "$1" || { no "$4 的 automation 调的不是 $3"; return; }
  ok "$4 的 automation 在且启用，调 $3"
}
chk_auto "$AUTO1" '考勤异常简报 每工作日发送' 'kmfa_brief_cron.sh'     "出报"
chk_auto "$AUTO2" '看门狗'                     'kmfa_brief_watchdog.sh' "看门狗"

# 考勤线只许有这两条。多出来的（改名遗留、手滑建的、DB 里的僵尸）会重复跑、
# 重复发、互相盖运行记录，而且让人看不清到底哪条在管事。
ZOMB=$(sqlite3 "$HOME/.codex/sqlite/codex-dev.db" \
       "select id from automations where status='ACTIVE' and (name like '%考勤%' or id like '%attendance%') and id not in ('automation','automation-2');" 2>/dev/null)
[ -z "$ZOMB" ] && ok "没有多余的考勤 automation（DB 里只有这两条是 ACTIVE）" \
                || no "DB 里还有多余且 ACTIVE 的考勤 automation：$(echo $ZOMB) —— 会重复跑"

# 断言的是**不变式**，不是某个具体钟点：把出报那条 rrule 的全部 BYHOUR 换算成北京时间，
# 落在发送窗口 [17:15, 17:15+4h] 里的必须 >= 2 个。
#
# 为什么不比「有没有一个恰好等于 19:15」：那是把当前这一季的答案写死当规矩。
# 2026-10-04 悉尼一转夏令时，本机 19:15 就从北京 17:15 变成 16:15，
# 被「未到出报时刻」闸挡掉，主槽从此天天空跑，只剩备位一趟。
# 那时候旧写法照样绿 —— 它只要求「有一个等于」，而那一个换成了备位。
# >= 2 才是「第一趟出岔子还有第二趟」这句话本身。
PUBLISH_H=17; PUBLISH_M=15        # 出报时刻（北京），同时也是人员表截止线
WINDOW_H="${KMFA_BRIEF_WINDOW_HOURS:-4}"
SLOT_REPORT=$(/usr/bin/python3 "$(cd "$(dirname "$0")" && pwd)/slot_window.py" \
              "$AUTO1" "$PUBLISH_H" "$PUBLISH_M" "$WINDOW_H" 2>/dev/null)
SLOT_N="${SLOT_REPORT%%|*}"; SLOT_REST="${SLOT_REPORT#*|}"
SLOT_ALL="${SLOT_REST%%|*}"; SLOT_VALID="${SLOT_REST#*|}"
case "${SLOT_N:-x}" in
  ''|*[!0-9]*) no "触发钟点算不出来（slot_window.py 没有输出）" ;;
  *) if [ "$SLOT_N" -ge 2 ]; then
       ok "触发钟点 $SLOT_ALL —— 窗口内有 $SLOT_N 趟（北京 $SLOT_VALID），双趟成立"
     elif [ "$SLOT_N" -eq 1 ]; then
       no "触发钟点 $SLOT_ALL —— 只剩北京 $SLOT_VALID 一趟，第一趟出岔子就没有兜底"
     else
       no "触发钟点 $SLOT_ALL —— 没有一趟落在发送窗口内，简报永远发不出去"
     fi ;;
esac

# 线上 automation 的 prompt / 模型必须跟仓库里这份 mirror 一致。
# 改仓库里的 automation/kmfa_attendance_brief.prompt.md **不会**更新线上那两条 ——
# 它只是可移植镜像。2026-09-09 实测：改了标记名之后线上还是旧版，
# agent 会因为「表里没有这个标记」而每天误报 ESCALATE。
# 模型也一起核：Codex 每次改 automation 都会把当前会话的模型盖上去，
# 所以这里断言的是**张霖泽指定的那个模型**，不是我猜的。改模型请改下面两个变量，
# 别改代码里的默认值 —— 让守卫跟着人的决定走，而不是反过来。
PROMPT_SRC="$(cd "$(dirname "$0")/.." && pwd)/automation/kmfa_attendance_brief.prompt.md"
WANT_MODEL="${KMFA_BRIEF_MODEL:-scnet-deepseek-v4-flash-0731}"   # 张霖泽 2026-09-09 指定
WANT_EFFORT="${KMFA_BRIEF_EFFORT:-max}"
for A in "$AUTO1"; do
  [ -f "$A" ] || continue
  id=$(basename "$(dirname "$A")")
  # 必须用带 tomllib 的解释器（3.11+）。第一版写成「没有就 sys.exit(0) 跳过」，
  # 而系统 python 正好是 3.9 —— 整条检查静默失效、照样报 PASS。假绿。
  # 现在找不到合适的解释器就直接 FAIL，不许悄悄跳过。
  PY311=""
  for c in python3.13 python3.12 python3.11 /opt/homebrew/bin/python3; do
    command -v "$c" >/dev/null 2>&1 && "$c" -c "import tomllib" 2>/dev/null && { PY311="$c"; break; }
  done
  if [ -z "$PY311" ]; then
    no "找不到带 tomllib 的 python（3.11+），无法核对线上 automation 与仓库是否一致"
    continue
  fi
  "$PY311" - "$A" "$PROMPT_SRC" "$id" "$WANT_MODEL" "$WANT_EFFORT" <<'PY' || fail=1
import sys, pathlib, tomllib
a, src, i, want_model, want_effort = sys.argv[1:6]
d = tomllib.loads(pathlib.Path(a).read_text())
want = pathlib.Path(src).read_text().strip()
bad = []
if d.get("prompt", "").strip() != want:
    bad.append("prompt 与仓库 mirror 不一致（改 mirror 不会自动同步到线上，要去 Codex 里改）")
if d.get("model") != want_model:
    bad.append(f"model 是 {d.get('model')}，应为 {want_model}")
if d.get("reasoning_effort") != want_effort:
    bad.append(f"reasoning_effort 是 {d.get('reasoning_effort')}，应为 {want_effort}")
for b in bad:
    print(f"  FAIL  {i}: {b}")
sys.exit(1 if bad else 0)
PY
  [ "$fail" = "1" ] || ok "$id 的 prompt 与仓库一致，模型是 $WANT_MODEL / $WANT_EFFORT"
done

# 出事能不能通知到人
[ -n "${KMFA_BRIEF_NOTIFY_USER:-}" ] \
  && ok "故障告警有私聊对象（出事会直接发到手机，不是只写在 Codex 里）" \
  || no "没配 KMFA_BRIEF_NOTIFY_USER —— 挂了不会有人知道"

# 运行日志落点
LOGD="${KMFA_BRIEF_RUNTIME_ROOT:-}/logs"
if [ -n "${KMFA_BRIEF_RUNTIME_ROOT:-}" ] && mkdir -p "$LOGD" 2>/dev/null && [ -w "$LOGD" ]; then
  ok "运行日志可写：$LOGD/kmfa_brief_run.log"
else
  no "运行日志目录不可写：$LOGD"
fi


# 包装脚本两条分支都得真跑到最后一行。
# 2026-09-07 的事故就是这么漏掉的：所有测试都在离计划钟点很远的时刻做，走的全是
# --force 分支；排程那条分支 FORCE 为空，而 macOS bash 3.2 在 set -u 下展开空数组
# 会直接退出 —— 第一次真实触发当场崩在倒数第二行，run_attendance_brief.py 一次都没跑到。
#
# 探针必须真的走到 exec 那一行。第一版把 venv 指到不存在的路径，结果脚本在 venv 检查
# 就退出了，有 bug 的版本照样全绿 —— 假绿。现在改成：造一个 venv 桩，
# bin/python 只把收到的参数打印出来，于是能一路跑到底并看清实际传了什么。
W="$(cd "$(dirname "$0")" && pwd)/kmfa_brief_cron.sh"
STUB=$(mktemp -d); mkdir -p "$STUB/bin"
printf '#!/bin/bash\necho "STUB_ARGS:[$*]"\n' > "$STUB/bin/python"; chmod +x "$STUB/bin/python"
probe_branch() {   # $1=说明 $2=期望参数 其余=环境覆盖
  desc="$1"; want="$2"; shift 2
  out=$(env "$@" KMFA_BRIEF_VENV="$STUB" bash "$W" 2>&1)
  case "$out" in
    *"unbound variable"*|*"bad substitution"*|*"syntax error"*)
      no "包装脚本${desc}分支崩了：$(echo "$out" | head -1)"; return ;;
  esac
  got=$(echo "$out" | sed -n 's/.*STUB_ARGS:\[\(.*\)\].*/\1/p' | head -1)
  got=$(echo "$got" | sed 's#.*run_attendance_brief\.py##; s/^ *//')   # 只看脚本后面那截
  if [ "$out" = "${out#*STUB_ARGS:}" ]; then
    no "包装脚本${desc}分支没走到最后一行：$(echo "$out" | head -1)"
  elif [ "$got" = "$want" ]; then
    ok "包装脚本${desc}分支跑到底，传参 [$got]"
  else
    no "包装脚本${desc}分支传参不对：期望 [$want] 实得 [$got]"
  fi
}
NOWH=$(date +%H); NOWM=$(date +%M)
probe_branch "排程触发" "" "KMFA_BRIEF_SLOT_HOURS=$NOWH" "KMFA_BRIEF_SLOT_MIN=$NOWM"
probe_branch "手动 Run" "--force" "KMFA_BRIEF_SLOT_HOURS=00" "KMFA_BRIEF_SLOT_MIN=00"
rm -rf "$STUB"

echo "----------------------------------------"
if [ "$fail" -eq 0 ]; then
  echo "自检全部通过。Codex automation 已就位，不需要再动手设任何东西。"
else
  echo "有 FAIL 项。停下来把上面的 FAIL 原样报告给张霖泽，不要自行修改代码或配置。"
fi
exit "$fail"
