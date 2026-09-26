#!/usr/bin/env bash
# 一键出片：字体 → 依赖 → 水彩底板 → 配乐 → 逐帧渲染 → 合成 MP4。可重复执行，已有的中间物会跳过（帧可断点续跑）。
# 用法：KMVideo/claude_pop/build.sh [输出目录]   默认 out/。产出：KM_claude_pop.mp4（母版）/_web.mp4（12Mbps）/_share.mp4（≤30MB）/_cover.jpg
# 环境变量：CHROME_PATH（Chromium 路径）、WORKERS（并行页数，默认 3）、
#           GL（传给 render.mjs 的显卡参数；默认 --soft-gl 软件渲染，有显卡的 Mac/Windows 设 GL= 空串走 Metal/D3D，快很多）
# 捷径：先跑 ./fetch_release.sh 把 Release 里的逐帧图、底板、字体摆好，这里就会跳过渲染，只剩配乐+编码（几分钟）。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; BASE="$HERE/../../ClaudeAnimationBase"; OUT="${1:-$HERE/out}"; FR="$HERE/out/frames"
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
R=(node render.mjs ${GL---soft-gl} --page="$HERE/index.html")
# 3 水彩底板（真水彩填充，只画一次）
for n in gray gold blue night; do
  [[ -s "$HERE/assets/plates/$n.jpg" ]] && continue
  "${R[@]}" --loop="plate_$n" --stills=0 --out="$HERE/out/plate_$n"
  ffmpeg -v error -y -i "$HERE/out/plate_$n/t0_00.png" -q:v 2 "$HERE/assets/plates/$n.jpg"
done
# 4 配乐（原创合成，-14 LUFS）
python3 "$HERE/music.py" "$HERE/out/bgm.wav"
# 5 逐帧（并行、可续跑）
"${R[@]}" --frames --workers="${WORKERS:-3}" --frames-dir="$FR"
# 6 合成：母版（crf17）→ 平台版（12Mbps 上限）→ 分享版（两遍编码压到 ~28MB，能直接发聊天软件）→ 封面（片尾卡）
mkdir -p "$OUT"; V=(-framerate 24 -i "$FR/f%05d.jpg" -i "$HERE/out/bgm.wav" -map 0:v -map 1:a); X=(-pix_fmt yuv420p -profile:v high -level 4.1 -r 24 -g 48 -shortest -movflags +faststart)
ffmpeg -y -v error "${V[@]}" -c:v libx264 -preset slow -crf 17 "${X[@]}" -c:a aac -b:a 192k -ar 44100 "$OUT/KM_claude_pop.mp4"
ffmpeg -y -v error "${V[@]}" -c:v libx264 -preset slow -crf 20 -maxrate 12M -bufsize 24M "${X[@]}" -c:a aac -b:a 192k -ar 44100 "$OUT/KM_claude_pop_web.mp4"
PL="$(mktemp -d)/pass"
ffmpeg -y -v error -framerate 24 -i "$FR/f%05d.jpg" -c:v libx264 -preset slower -b:v 4900k -pass 1 -passlogfile "$PL" -pix_fmt yuv420p -r 24 -g 48 -an -f mp4 /dev/null
ffmpeg -y -v error "${V[@]}" -c:v libx264 -preset slower -b:v 4900k -maxrate 7M -bufsize 10M -pass 2 -passlogfile "$PL" "${X[@]}" -c:a aac -b:a 160k "$OUT/KM_claude_pop_share.mp4"
rm -rf "$(dirname "$PL")"
ffmpeg -y -v error -ss 43.6 -i "$OUT/KM_claude_pop.mp4" -frames:v 1 -q:v 2 "$OUT/KM_claude_pop_cover.jpg"
ls -la "$OUT"/KM_claude_pop*
"$HERE/verify.sh" "$OUT/KM_claude_pop.mp4"
