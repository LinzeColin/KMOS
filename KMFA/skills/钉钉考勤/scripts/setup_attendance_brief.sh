#!/bin/bash
# 一次性安装：建 venv、装依赖。之后只需要跑 run_attendance_brief.py。
# 依赖只有三个纯 wheel 包，不需要 brew、不需要 Xcode、不联网调任何模型。
set -euo pipefail
VENV="${KMFA_BRIEF_VENV:-$HOME/.local/share/kmfa-attendance-brief/venv}"
mkdir -p "$(dirname "$VENV")"
[ -d "$VENV" ] || /usr/bin/python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --disable-pip-version-check --only-binary=:all: \
  "pyobjc-framework-Vision==10.3.2" "numpy" "pillow"
"$VENV/bin/python" -c "import Vision, numpy, PIL; print('依赖就绪')"
echo "venv: $VENV"
echo
echo "下一步：复制 templates/kmfa_brief.env.example 到 private_runtime/kmfa_brief.env 并填真值"
