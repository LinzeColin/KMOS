#!/usr/bin/env bash
set -euo pipefail

# KMDouyin 的每日控制面投影：本机暂存 → rsync --inplace → 目标读回。

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
PACKAGE_ROOT=$(cd "$SCRIPT_DIR/.." && pwd -P)
WORKSPACE=${KMD_WORKSPACE:-/Volumes/share/03_资料库/KMDouyin}
RUNTIME_ROOT=${KMD_RUNTIME_ROOT:-/Users/linzezhang/Movies/Hub/KMDouyinRuntime}
RUN_ROOT="$WORKSPACE/00_治理与登记/04_运行记录/内容增长循环"
RELEASE_ROOT="$WORKSPACE/03_复盘与洞察/发布后复盘"
TASK_CARD=${KMD_TASK_CARD:-$WORKSPACE/01_视频项目/06_真实表达实验/260826_齿形秩序/05_策略重设与重做/商业片任务卡_v3.yaml}
BUS_ROOT="$WORKSPACE/00_治理与登记/00_控制面/运行总线"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
STAGE_ROOT="$RUNTIME_ROOT/control-plane/daily/$STAMP"

if [ -e "$STAGE_ROOT" ]; then
  printf '运行暂存目录已存在：%s\n' "$STAGE_ROOT" >&2
  exit 2
fi

mkdir -p "$STAGE_ROOT"

EVENT_LOG_ARG=()
if [ -f "$BUS_ROOT/运行事件.jsonl" ]; then
  EVENT_LOG_ARG=(--event-log "$BUS_ROOT/运行事件.jsonl")
fi

PYTHONPATH="$PACKAGE_ROOT" python3 -m kmdouyin_control.cli project \
  --workspace "$WORKSPACE" \
  --run-root "$RUN_ROOT" \
  --release-root "$RELEASE_ROOT" \
  --task-card "$TASK_CARD" \
  "${EVENT_LOG_ARG[@]}" \
  --out-dir "$STAGE_ROOT/运行总线"

set +e
PYTHONPATH="$PACKAGE_ROOT" python3 -m kmdouyin_control.cli preflight \
  --workspace "$WORKSPACE" \
  --task-card "$TASK_CARD" \
  --out-dir "$STAGE_ROOT/生产门"
PREFLIGHT_CODE=$?
set -e
if [ "$PREFLIGHT_CODE" -ne 0 ] && [ "$PREFLIGHT_CODE" -ne 3 ]; then
  exit "$PREFLIGHT_CODE"
fi

PYTHONPATH="$PACKAGE_ROOT" python3 -m kmdouyin_control.cli observe-release \
  --workspace "$WORKSPACE" \
  --review "$RELEASE_ROOT/REV-260905-DOUYIN-TRANSMISSION-V3-R2-001.yaml" \
  --out-dir "$STAGE_ROOT/发布数据面"

rsync -a --inplace "$STAGE_ROOT/运行总线/" "$BUS_ROOT/"
rsync -a --inplace "$STAGE_ROOT/生产门/" "$BUS_ROOT/生产门/"
rsync -a --inplace "$STAGE_ROOT/发布数据面/" "$BUS_ROOT/发布数据面/"

cmp "$STAGE_ROOT/运行总线/运行总线当前态.yaml" "$BUS_ROOT/运行总线当前态.yaml"
cmp "$STAGE_ROOT/运行总线/工作项队列.jsonl" "$BUS_ROOT/工作项队列.jsonl"
cmp "$STAGE_ROOT/生产门/生产门结果.yaml" "$BUS_ROOT/生产门/生产门结果.yaml"
cmp "$STAGE_ROOT/发布数据面/发布观测结果.yaml" "$BUS_ROOT/发布数据面/发布观测结果.yaml"

printf '控制面已更新：%s\n' "$BUS_ROOT"
printf '当前状态：%s\n' "$BUS_ROOT/日运行状态.md"
printf '生产门退出码：%s\n' "$PREFLIGHT_CODE"
