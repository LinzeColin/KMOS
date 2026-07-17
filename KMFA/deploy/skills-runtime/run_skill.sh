#!/usr/bin/env bash
# 统一技能运行包装：flock 防重入 → 注入 secrets → 运行 → 台账 append → 失败告警。
# 用法：run_skill.sh <skill-name>
set -uo pipefail

SKILL="${1:?用法: run_skill.sh <skill-name>}"
ROOT=/opt/kmfa/KMOS
LOG_DIR=/var/log/kmfa/$SKILL
LEDGER=/var/log/kmfa/ledger.jsonl
LOCK=/tmp/kmfa-$SKILL.lock
TS="$(date +%Y%m%d_%H%M%S)"
LOG="$LOG_DIR/$TS.log"
mkdir -p "$LOG_DIR"

# secrets 注入（600 校验在 entrypoint 已做）
[ -f /opt/kmfa/secrets/skills.env ] && set -a && . /opt/kmfa/secrets/skills.env && set +a

# 双跑纪律：未开启投递时强制 dry-run 语义（各技能读该变量；考勤守卫另有 ALLOW_DWS_COMMANDS）
export KMFA_DELIVERY_ENABLED="${KMFA_DELIVERY_ENABLED:-0}"
# 投递旗标：双跑纪律的机械化——未开闸一律 --dry-run
DELIVERY_FLAG=$([ "$KMFA_DELIVERY_ENABLED" = "1" ] && echo --send || echo --dry-run)
# SKL.0005：cron 环境不继承容器 ENV，这里显式钉死 OCR 引擎替换（swift Vision → Python 链）
export KMFA_FUND_VISION_OCR_COMMAND="${KMFA_FUND_VISION_OCR_COMMAND:-python3 $ROOT/KMFA/skills/资金周报/tools/ocr_with_python.py}"

cd "$ROOT"
export PYTHONPATH="$ROOT"

case "$SKILL" in
  attendance-morning)  CMD=(python3 KMFA/tools/dingtalk_attendance/run_attendance.py --run-type morning) ;;
  attendance-evening)  CMD=(python3 KMFA/tools/dingtalk_attendance/run_attendance.py --run-type evening) ;;
  work-check-morning)  CMD=(python3 -m KMFA.tools.daily_routine_check.main --input-zip "${KMFA_DAILY_INPUT_ZIP:-/opt/kmfa/data/DWS_Outputs.zip}" --trigger-window morning_1135 $DELIVERY_FLAG) ;;   # SKL.0004 已演练（真实输入 dry-run 通过，通知对象原生=张霖泽）
  work-check-evening)  CMD=(python3 -m KMFA.tools.daily_routine_check.main --input-zip "${KMFA_DAILY_INPUT_ZIP:-/opt/kmfa/data/DWS_Outputs.zip}" --trigger-window evening_1705 $DELIVERY_FLAG) ;;
  fund-weekly)         CMD=(python3 KMFA/skills/资金周报/tools/validate_taskpack.py) ;;       # SKL.0005 OCR 替换后接业务入口
  mgmt-monthly)        CMD=(python3 KMFA/skills/经营月报/tools/validate_skill_package.py) ;;   # SKL.0004 演练时替换为业务入口
  upstream-archive)    CMD=(python3 KMFA/skills/上游归档/tools/validate_skill_package.py) ;;  # dws drive 命令面核对后接业务入口
  daily-backup)        CMD=(bash -c 'cd /opt/kmfa/KMOS && git -C . pull --ff-only -q || true') ;;         # DATA 线入仓机制就绪后改为真备份
  *) echo "未知技能: $SKILL" >&2; exit 2 ;;
esac

(
  flock -n 9 || { echo "$(date -Is) $SKILL: 上一轮仍在运行，跳过" >> "$LOG"; exit 0; }
  echo "$(date -Is) $SKILL: 开始 ${CMD[*]}" >> "$LOG"
  "${CMD[@]}" >> "$LOG" 2>&1
  RC=$?
  echo "$(date -Is) $SKILL: 结束 rc=$RC" >> "$LOG"
  printf '{"ts":"%s","skill":"%s","rc":%d,"log":"%s","delivery_enabled":"%s"}\n' \
    "$(date -Is)" "$SKILL" "$RC" "$LOG" "$KMFA_DELIVERY_ENABLED" >> "$LEDGER"
  if [ "$RC" -ne 0 ] && [ -n "${KMFA_ALERT_WEBHOOK_TOKEN:-}" ]; then
    dws chat message send-by-webhook --token "$KMFA_ALERT_WEBHOOK_TOKEN" \
      --title "KMFA 云端技能失败告警" \
      --text "技能 $SKILL 运行失败（rc=$RC），日志 $LOG" --format json >> "$LOG" 2>&1 || true
  fi
  exit $RC
) 9>"$LOCK"
