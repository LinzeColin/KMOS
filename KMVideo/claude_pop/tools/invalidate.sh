#!/usr/bin/env bash
# 改了某段动画后，删掉这段时间内的旧帧，让 build.sh 只重渲这一段（其余帧照用）。
# 用法：tools/invalidate.sh 起始秒 结束秒      例：tools/invalidate.sh 20.5 24   （帧号 = round(秒 × 24)）
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; A="${1:?起始秒}"; B="${2:?结束秒}"
python3 - "$HERE/out/frames" "$A" "$B" <<'PY'
import os, sys
d, a, b = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]); n = 0
for i in range(round(a * 24), min(round(b * 24), 1103) + 1):
    p = f'{d}/f{i:05d}.jpg'
    if os.path.exists(p): os.remove(p); n += 1
print(f'删除 {n} 帧（{a}s–{b}s）；现在跑 build.sh 会只补这 {n} 帧')
PY
