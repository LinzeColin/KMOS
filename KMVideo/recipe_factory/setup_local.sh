#!/usr/bin/env bash
# KMDY-RF 本机环境检查与依赖安装。在 KMDY-RF 根目录运行：bash KMVideo/recipe_factory/setup_local.sh
# 只装项目依赖（npm / pip --user），不改系统设置；缺的系统组件打印安装命令。
cd "$(dirname "$0")/../.." || exit 1
ok=1
need() { command -v "$1" >/dev/null 2>&1 && echo "✓ $1 $($1 $2 2>&1 | head -1)" || { echo "✗ 缺 $1：$3"; ok=0; }; }
need node --version "brew install node（需 18+，云端用 22）"
need python3 --version "brew install python"
need ffmpeg -version "brew install ffmpeg"
python3 - <<'P' || python3 -m pip install --user numpy scipy pyyaml pillow playwright
import numpy, scipy, yaml; print("✓ numpy", numpy.__version__, "scipy", scipy.__version__)
P
if [ -z "$CHROME_PATH" ]; then
  for c in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" /usr/bin/google-chrome /usr/bin/chromium; do
    [ -x "$c" ] && export CHROME_PATH="$c" && break
  done
fi
[ -n "$CHROME_PATH" ] && echo "✓ Chrome $CHROME_PATH" || { echo "✗ 缺 Chrome：装 Google Chrome，或 export CHROME_PATH=<路径>"; ok=0; }
for d in KMBearAnimationBase ClaudeAnimationBase; do
  [ -d "$d/node_modules" ] && echo "✓ $d 依赖已装" || (cd "$d" && npm install --no-audit --no-fund >/dev/null && echo "✓ $d npm install 完成")
done
(cd KMVideo/recipe_factory && python3 factory.py status | tail -3)
[ $ok = 1 ] && echo "环境就绪。下一步读 KMVideo/recipe_factory/LOCAL_SETUP.md §3 填 workspace.yaml" || echo "按上面 ✗ 补齐后重跑本脚本"
