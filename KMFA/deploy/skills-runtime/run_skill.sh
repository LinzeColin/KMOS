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
  # 测试期只发张霖泽本人（Owner:不许发群，除非授权）。授权后在 Coolify 置 KMFA_NOTIFICATION_TARGETS=group。
  attendance-morning)  CMD=(python3 KMFA/tools/dingtalk_attendance/run_attendance.py --run-type morning --notification-targets "${KMFA_NOTIFICATION_TARGETS:-personal}") ;;
  attendance-evening)  CMD=(python3 KMFA/tools/dingtalk_attendance/run_attendance.py --run-type evening --notification-targets "${KMFA_NOTIFICATION_TARGETS:-personal}") ;;
  work-check-morning)  CMD=(python3 -m KMFA.tools.daily_routine_check.main --input-zip "${KMFA_DAILY_INPUT_ZIP:-/opt/kmfa/data/DWS_Outputs.zip}" --trigger-window morning_1135 $DELIVERY_FLAG) ;;   # SKL.0004 已演练（真实输入 dry-run 通过，通知对象原生=张霖泽）
  work-check-evening)  CMD=(python3 -m KMFA.tools.daily_routine_check.main --input-zip "${KMFA_DAILY_INPUT_ZIP:-/opt/kmfa/data/DWS_Outputs.zip}" --trigger-window evening_1705 $DELIVERY_FLAG) ;;
  fund-weekly)         CMD=(python3 KMFA/skills/资金周报/tools/validate_taskpack.py) ;;       # SKL.0005 OCR 替换后接业务入口
  mgmt-monthly)        CMD=(python3 KMFA/skills/经营月报/tools/validate_skill_package.py) ;;   # SKL.0004 演练时替换为业务入口
  # 最近完工项目成本：稀疏克隆私有库取真源 → 算 → 写共享卷；App 只读不算。
  # Owner 2026-07-27：「我根本没有看到项目成本，我说了我要最近完工的项目成本」——
  # 数要出现在驾驶舱页面上，所以产物是 App 直接读的 JSON，不是导出的文件。
  project-cost-refresh) CMD=(bash -c '\
                         set -e; K=/opt/kmfa/secrets/kmfa_backup_deploy_key; \
                         [ -f "$K" ] || { echo "缺部署密钥，无法取私有源"; exit 3; }; \
                         export GIT_SSH_COMMAND="ssh -i $K -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o BatchMode=yes"; \
                         D=/tmp/kmfa-pdb-cost; rm -rf "$D"; \
                         git clone --quiet --filter=blob:none --no-checkout git@github.com:LinzeColin/Private-Database.git "$D"; \
                         git -C "$D" sparse-checkout init --cone; \
                         git -C "$D" sparse-checkout set Private-KMDatabase/KMFA_MetaData; \
                         git -C "$D" checkout --quiet; \
                         mkdir -p /var/log/kmfa/project_cost; \
                         python3 KMFA/tools/project_cost/build_recent_completed.py \
                           --data-root "$D/Private-KMDatabase/KMFA_MetaData" \
                           --account-map KMFA/machine/facts/project_cost_account_map.json \
                           --out /var/log/kmfa/project_cost/recent_completed.json; \
                         python3 KMFA/tools/project_cost/build_customer_margin.py \
                           --data-root "$D/Private-KMDatabase/KMFA_MetaData" \
                           --out /var/log/kmfa/project_cost/customer_margin.json; \
                         rm -rf "$D"') ;;
  # 真业务入口:云端 dws 归档(钉钉→容器→GitHub 私有库)。原先只跑校验器→从未真归档。
  upstream-archive)    CMD=(bash KMFA/skills/上游归档/scripts/run_cloud_archive.sh) ;;
  # 群清单自举:用容器内已认证 dws 列群生成候选配置进私有库(Owner 无需提供群 ID)
  dws-bootstrap-groups) CMD=(bash KMFA/skills/上游归档/scripts/bootstrap_groups_cloud.sh) ;;  # dws drive 命令面核对后接业务入口
  daily-backup)        CMD=(python3 KMFA/tools/app_state_backup.py backup --state-dir /var/lib/kmfa/state) ;;  # App 状态面异地备份→GitHub 私有库（一致快照+sha256+manifest）。设 KMFA_BACKUP_GH_TOKEN 后异地生效；未设则降级写 /var/log/kmfa/backups 并告警。往返自测见 DT6_APP_STATE_BACKUP
  dws-keepalive)       CMD=(bash -c 'set -e; \
                         D=/var/log/kmfa/dws-keepalive; mkdir -p "$D"; \
                         A="--profile-config $D/expected_profile.json --ledger-path $D/memory.md --state-path $D/state.json"; \
                         [ -f "$D/expected_profile.json" ] || A="$A --bootstrap-current-profile"; \
                         python3 KMFA/tools/automation/dws_auth_keepalive.py $A') ;;  # 认证保活：替代已停用的 Codex 排程 dws-auth-keepalive-2；无交互刷新 access-token；profile/state/ledger 落 kmfa-logs 卷（容器重建不丢），首跑自举 profile；失败经 run_skill 告警面上报
  self-audit)          CMD=(bash -c 'set -e; \
                         rm -rf /tmp/kmfa-audit && mkdir -p /tmp/kmfa-audit; \
                         tar -C /opt/kmfa/KMOS --exclude=./.git --exclude=./KMDatabase/data/objects \
                             --exclude=./KMFA/app/frontend/node_modules --exclude=./KMFA/.codex_private_runtime \
                             -cf - . | tar -C /tmp/kmfa-audit -xf -; \
                         cd /tmp/kmfa-audit; \
                         python3 KMFA/tools/evidence_check.py; \
                         python3 KMFA/tools/lineage_graph.py stale; \
                         python3 KMDatabase/machine/tools/check_dual_plane_ci.py --root . --require-projects; \
                         rm -rf /tmp/kmfa-audit') ;;  # DT8 健康周检：tar 影子里跑（仓库挂载只读且双平面门原地重渲染——容器演练抓获；worktree .git 为指针文件故不用克隆），私有库类门禁另跑
  *) echo "未知技能: $SKILL" >&2; exit 2 ;;
esac

(
  flock -n 9 || { echo "$(date -Is) $SKILL: 上一轮仍在运行，跳过" >> "$LOG"; exit 0; }
  echo "$(date -Is) $SKILL: 开始 ${CMD[*]}" >> "$LOG"
  "${CMD[@]}" >> "$LOG" 2>&1
  RC=$?
  echo "$(date -Is) $SKILL: 结束 rc=$RC" >> "$LOG"
  LINE="$(printf '{"ts":"%s","skill":"%s","rc":%d,"log":"%s","delivery_enabled":"%s"}' \
    "$(date -Is)" "$SKILL" "$RC" "$LOG" "$KMFA_DELIVERY_ENABLED")"
  echo "$LINE" >> "$LEDGER"
  # 回传私有库：容器卷里的台账没人验得到（Coolify 的 logs 返回空、exec 返回 404，
  # /api/排程健康 在 Access 后面）。回传后验证就是一条 gh api，不必登录也不必进容器。
  # 失败只记日志，绝不改变技能自身的退出码。
  echo "$LINE" | timeout 60 python3 "$ROOT/KMFA/tools/skill_ledger_uplink.py" >> "$LOG" 2>&1 || true
  if [ "$RC" -ne 0 ] && [ -n "${KMFA_ALERT_WEBHOOK_TOKEN:-}" ]; then
    dws chat message send-by-webhook --token "$KMFA_ALERT_WEBHOOK_TOKEN" \
      --title "KMFA 云端技能失败告警" \
      --text "技能 $SKILL 运行失败（rc=$RC），日志 $LOG" --format json >> "$LOG" 2>&1 || true
  fi
  exit $RC
) 9>"$LOCK"
