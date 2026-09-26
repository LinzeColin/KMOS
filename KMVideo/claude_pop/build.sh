#!/usr/bin/env bash
# 一键出片：字体 → 依赖 → 水彩底板 → 配乐 → 逐帧渲染 → 合成 MP4。可重复执行，已有的中间物会跳过（帧可断点续跑）。
# 用法：KMVideo/claude_pop/build.sh [输出.mp4]      环境变量：CHROME_PATH（Chromium 路径）、WORKERS（并行页数，默认 3）
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; BASE="$HERE/../../ClaudeAnimationBase"; OUT="${1:-$HERE/out/KM_claude_pop.mp4}"
mkdir -p "$HERE/out" "$HERE/assets/plates"
# 1 字体
while read -r f sum url; do
  [[ -z "$f" || "$f" == \#* ]] && continue
  dst="$HERE/fonts/$f"
  if [[ ! -s "$dst" ]]; then
    if [[ "$url" == *.zip#* ]]; then tmp=$(mktemp -d); curl -sSL -o "$tmp/z.zip" "${url%%#*}"; unzip -q -o "$tmp/z.zip" -d "$tmp"; cp "$(find "$tmp" -name "${url##*#}" | head -1)" "$dst"; rm -rf "$tmp";
    else curl -sSL -o "$dst" "$url"; fi
  fi
  echo "$sum  $dst" | sha256sum -c --quiet
done < "$HERE/fonts/SOURCES.txt"
# 2 依赖
[[ -d "$BASE/node_modules" ]] || (cd "$BASE" && npm ci)
cd "$BASE"
R=(node render.mjs --soft-gl --page="$HERE/index.html")
# 3 水彩底板（真水彩填充，只画一次）
for n in gray gold blue night; do
  [[ -s "$HERE/assets/plates/$n.jpg" ]] && continue
  "${R[@]}" --loop="plate_$n" --stills=0 --out="$HERE/out/plate_$n"
  ffmpeg -v error -y -i "$HERE/out/plate_$n/t0_00.png" -q:v 2 "$HERE/assets/plates/$n.jpg"
done
# 4 配乐（原创合成，-14 LUFS）
python3 "$HERE/music.py" "$HERE/out/bgm.wav"
# 5 逐帧（并行、可续跑）
"${R[@]}" --frames --workers="${WORKERS:-3}" --frames-dir="$HERE/out/frames"
# 6 合成
ffmpeg -y -v error -framerate 24 -i "$HERE/out/frames/f%05d.jpg" -i "$HERE/out/bgm.wav" -map 0:v -map 1:a \
  -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -profile:v high -level 4.1 -r 24 \
  -c:a aac -b:a 192k -ar 44100 -shortest -movflags +faststart "$OUT"
echo "wrote $OUT"
