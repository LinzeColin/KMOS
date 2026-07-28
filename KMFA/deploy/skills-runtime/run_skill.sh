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
# 考勤私有运行时目录：**必须在这里钉死，不能只靠 compose 的 environment**。
# 2026-07-27 线上抓到的活例子：compose 里设了它，entrypoint 触发的自举与冷启动重试
# 都能读到持久卷、跑绿；而 **cron 触发的定时运行不继承容器 ENV**，退回镜像层默认路径，
# 于是同一个技能「手动跑绿、到点跑红」。表现像是随机失败，其实是两条路径读了不同目录。
# 这也是下面 OCR 那条注释里同一个坑，只是这次踩在考勤上。
export KMFA_ATTENDANCE_RUNTIME_DIR="${KMFA_ATTENDANCE_RUNTIME_DIR:-/var/log/kmfa/attendance-runtime}"
# SKL.0005：cron 环境不继承容器 ENV，这里显式钉死 OCR 引擎替换（swift Vision → Python 链）
export KMFA_FUND_VISION_OCR_COMMAND="${KMFA_FUND_VISION_OCR_COMMAND:-python3 $ROOT/KMFA/skills/资金周报/tools/ocr_with_python.py}"

cd "$ROOT"
export PYTHONPATH="$ROOT"

case "$SKILL" in
  # 测试期只发张霖泽本人（Owner:不许发群，除非授权）。授权后在 Coolify 置 KMFA_NOTIFICATION_TARGETS=group。
  attendance-morning)  CMD=(python3 KMFA/tools/dingtalk_attendance/run_attendance.py --run-type morning --notification-targets "${KMFA_NOTIFICATION_TARGETS:-personal}") ;;
  attendance-evening)  CMD=(python3 KMFA/tools/dingtalk_attendance/run_attendance.py --run-type evening --notification-targets "${KMFA_NOTIFICATION_TARGETS:-personal}") ;;
  # 日常检查：输入**必须真找得到**才跑。原来写死默认值 /opt/kmfa/data/DWS_Outputs.zip，
  # 而全仓没有任何东西会去生成它——没有 Dockerfile COPY、没有 compose 挂载、没有下载步骤，
  # 那个路径只出现在这一行的默认值里。于是线上连绿 9 次，实际零条规则被评
  # （2026-07-28 本机用历史数据压测抓获）。写死一个不存在的路径，等于把「源没配」
  # 伪装成「源配好了只是没数」。这里改成和上面 fund-weekly 同一种写法：find 不到就明说源缺失。
  # 注：reader 是刻意 zip-only（stream_members_no_copy_no_extract，从不解压），
  # 而上游归档落地的是目录树——两头格式还没搭上桥，这条在权限通了之后要一起接。
  work-check-morning|work-check-evening)
                       WINDOW=$([ "$SKILL" = work-check-morning ] && echo morning_1135 || echo evening_1705)
                       CMD=(bash -c '
                         Z="${KMFA_DAILY_INPUT_ZIP:-}"; \
                         [ -n "$Z" ] || Z=$(find /var/lib/kmfa/dws-archive -maxdepth 3 -type f -name "DWS_Outputs*.zip" 2>/dev/null | sort | tail -1); \
                         if [ -z "$Z" ] || [ ! -f "$Z" ]; then \
                           echo "{\"status\": \"ZIP_INPUT_MISSING\"} 日常检查的输入 zip 不在——上游归档还没把聊天记录落成 zip；未检查任何规则"; \
                           exit 2; \
                         fi; \
                         python3 -m KMFA.tools.daily_routine_check.main \
                           --input-zip "$Z" --trigger-window '"$WINDOW"' '"$DELIVERY_FLAG"'') ;;
  # 资金周报：接真业务入口。原先跑 validate_taskpack.py——那是校验器，它永远绿，
  # 而周报一次都没真出过。绿得没有意义比红更糟：红至少会被查，假绿谁也不会去查。
  # 真入口自带分型退出码（2=源缺失 / 5=源不可读 / 6=私有模板缺失）且打印 status，
  # 正好被 skill_failure_code.py 抓成失败码——失败也说得清是哪一种。
  # 输入用 find 而不是写死路径：归档产物的目录层级由 dws 决定，写死会在改版时静默变空。
  fund-weekly)         CMD=(bash -c '
                         IN=$(find /var/lib/kmfa/dws-archive -maxdepth 4 -type d -name "*付款请示*" 2>/dev/null | head -1); \
                         if [ -z "$IN" ]; then \
                           echo "{\"status\": \"SOURCE_MISSING\"} 付款请示群的归档目录不在——上游归档还没把文件拉下来"; \
                           exit 2; \
                         fi; \
                         python3 KMFA/skills/资金周报/tools/run_fund_weekly_analysis.py \
                           --input-dir "$IN" --repo-root . --timezone Asia/Shanghai') ;;
  # 经营月报：**这个技能的业务入口还没实现**。
  # scripts/mgmt_monthly_report.py 只有 register 子命令，它自己的 help 就写着
  # "this command does not copy raw data"——那是治理登记器，不是出报告的东西。
  # 原先跑 validate_skill_package.py 同样是校验器。把它接到 register 上只是换件衣服的假绿，
  # 所以这里如实退非零：没实现就说没实现，不拿一个绿灯冒充「月报在跑」。
  mgmt-monthly)        CMD=(bash -c '
                         echo "{\"status\": \"NOT_BUILT\"} 经营月报没有业务入口——"; \
                         echo "KMFA/skills/经营月报/ 下只有 register（治理登记）与校验器，没有出报告的实现。"; \
                         echo "接校验器会让它显示成功，那是假绿；这里如实报未建成。"; \
                         exit 8') ;;
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
                         python3 KMFA/tools/data_source_matrix.py \
                           --data-root "$D/Private-KMDatabase/KMFA_MetaData" \
                           --out /var/log/kmfa/project_cost/data_source_matrix.json \
                           --csv-out /var/log/kmfa/project_cost/data_source_matrix.csv; \
                         python3 KMFA/tools/project_cost/build_project_margin.py \
                           --data-root "$D/Private-KMDatabase/KMFA_MetaData" \
                           --account-map KMFA/machine/facts/project_cost_account_map.json \
                           --out /var/log/kmfa/project_cost/project_margin.json; \
                         rm -rf "$D"') ;;
  # 真业务入口:云端 dws 归档(钉钉→容器→GitHub 私有库)。原先只跑校验器→从未真归档。
  upstream-archive)    CMD=(bash KMFA/skills/上游归档/scripts/run_cloud_archive.sh) ;;
  # 考勤投递目标自举：解析出「谁收、钉钉 userid 是多少」并落持久卷。
  # 这是「考勤修一个月没修好」的那把钥匙——派发要读 notification_targets_resolved.json，
  # 而它的默认路径在镜像层里、每次部署被重置，于是容器里它永远不存在，
  # 派发一路走到 NOTIFIER_CONFIG_MISSING → rc=5。rc=5 有十来种成因，所以过去查不动。
  # **只探 personal**：探测会真发消息，测试期 Owner 明令禁群。
  attendance-bootstrap-targets) CMD=(python3 KMFA/tools/dingtalk_attendance/notification_probe.py \
                         --all-targets --target-filter personal) ;;
  # 群清单自举:用容器内已认证 dws 列群生成候选配置进私有库(Owner 无需提供群 ID)
  dws-bootstrap-groups) CMD=(bash KMFA/skills/上游归档/scripts/bootstrap_groups_cloud.sh) ;;  # dws drive 命令面核对后接业务入口
  daily-backup)        CMD=(python3 KMFA/tools/app_state_backup.py backup --state-dir /var/lib/kmfa/state) ;;  # App 状态面异地备份→GitHub 私有库（一致快照+sha256+manifest）。设 KMFA_BACKUP_GH_TOKEN 后异地生效；未设则降级写 /var/log/kmfa/backups 并告警。往返自测见 DT6_APP_STATE_BACKUP
  dws-keepalive)       CMD=(bash -c 'set -e; \
                         D=/var/log/kmfa/dws-keepalive; mkdir -p "$D"; \
                         A="--profile-config $D/expected_profile.json --ledger-path $D/memory.md --state-path $D/state.json"; \
                         [ -f "$D/expected_profile.json" ] || A="$A --bootstrap-current-profile"; \
                         python3 KMFA/tools/automation/dws_auth_keepalive.py $A') ;;  # 认证保活：替代已停用的 Codex 排程 dws-auth-keepalive-2；无交互刷新 access-token；profile/state/ledger 落 kmfa-logs 卷（容器重建不丢），首跑自举 profile；失败经 run_skill 告警面上报
  # 三道检查逐条跑完再一起判，**不是** set -e 一路串下来。
  # 实测（2026-07-27）：lineage stale 发现陈旧资产时按设计返回 1，那是一条「发现」；
  # 而 set -e 把这条发现当成中断，双平面门禁于是几周没被跑到过，还一直显示"自检失败"。
  # 一条发现不该掐死后面的检查——自检的职责是把问题找全，不是遇到第一个就撒手。
  self-audit)          CMD=(bash -c 'set -e; \
                         rm -rf /tmp/kmfa-audit && mkdir -p /tmp/kmfa-audit; \
                         tar -C /opt/kmfa/KMOS --exclude=./.git --exclude=./KMDatabase/data/objects \
                             --exclude=./KMFA/app/frontend/node_modules --exclude=./KMFA/.codex_private_runtime \
                             -cf - . | tar -C /tmp/kmfa-audit -xf -; \
                         cd /tmp/kmfa-audit; \
                         set +e; BAD=0; \
                         for CHK in "KMFA/tools/evidence_check.py" "KMFA/tools/lineage_graph.py stale" \
                                    "KMDatabase/machine/tools/check_dual_plane_ci.py --root . --require-projects"; do \
                           python3 $CHK; R=$?; \
                           [ $R -eq 0 ] || { echo "自检不过：$CHK → rc=$R"; BAD=1; }; \
                         done; \
                         rm -rf /tmp/kmfa-audit; exit $BAD') ;;  # DT8 健康周检：tar 影子里跑（仓库挂载只读且双平面门原地重渲染——容器演练抓获；worktree .git 为指针文件故不用克隆），私有库类门禁另跑
  *) echo "未知技能: $SKILL" >&2; exit 2 ;;
esac

(
  flock -n 9 || { echo "$(date -Is) $SKILL: 上一轮仍在运行，跳过" >> "$LOG"; exit 0; }
  echo "$(date -Is) $SKILL: 开始 ${CMD[*]}" >> "$LOG"
  "${CMD[@]}" >> "$LOG" 2>&1
  RC=$?
  echo "$(date -Is) $SKILL: 结束 rc=$RC" >> "$LOG"
  # 失败码：rc 只说「投递没成功」，而那对应十来种完全不同的原因。没有它就只能改一版等一天。
  # 提取器是白名单构造的（见 skill_failure_code.py），出来的东西天然可公开。
  CODE=""
  if [ "$RC" -ne 0 ]; then
    CODE="$(timeout 30 python3 "$ROOT/KMFA/tools/skill_failure_code.py" "$LOG" 2>/dev/null || echo UNKNOWN)"
  fi
  LINE="$(printf '{"ts":"%s","skill":"%s","rc":%d,"code":"%s","log":"%s","delivery_enabled":"%s"}' \
    "$(date -Is)" "$SKILL" "$RC" "$CODE" "$LOG" "$KMFA_DELIVERY_ENABLED")"
  # 共享卷这份被公开端点读，**故意不带日志尾巴**——考勤日志里有员工姓名和打卡明细。
  echo "$LINE" >> "$LEDGER"
  # 回传私有库：容器卷里的台账没人验得到（Coolify 的 logs 返回空、exec 返回 404，
  # /api/排程健康 在 Access 后面）。回传后验证就是一条 gh api，不必登录也不必进容器。
  # 私有库这份**带**日志尾巴——取证细节只该落在私有侧。失败只记日志，绝不改退出码。
  if [ "$RC" -ne 0 ]; then
    TAIL="$(timeout 30 python3 "$ROOT/KMFA/tools/skill_failure_code.py" "$LOG" --tail 2>/dev/null || true)"
    LINE_FULL="$(SKILL_LINE="$LINE" SKILL_TAIL="$TAIL" python3 -c 'import json,os,sys
d = json.loads(os.environ["SKILL_LINE"])
t = os.environ.get("SKILL_TAIL", "")
if t:
    d["tail"] = t
sys.stdout.write(json.dumps(d, ensure_ascii=False))' 2>/dev/null || printf '%s' "$LINE")"
  else
    LINE_FULL="$LINE"
  fi
  printf '%s' "$LINE_FULL" | timeout 60 python3 "$ROOT/KMFA/tools/skill_ledger_uplink.py" >> "$LOG" 2>&1 || true
  if [ "$RC" -ne 0 ] && [ -n "${KMFA_ALERT_WEBHOOK_TOKEN:-}" ]; then
    dws chat message send-by-webhook --token "$KMFA_ALERT_WEBHOOK_TOKEN" \
      --title "KMFA 云端技能失败告警" \
      --text "技能 $SKILL 运行失败（rc=$RC），日志 $LOG" --format json >> "$LOG" 2>&1 || true
  fi
  exit $RC
) 9>"$LOCK"
