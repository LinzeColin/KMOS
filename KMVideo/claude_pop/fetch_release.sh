#!/usr/bin/env bash
# 从 GitHub Release 取回本片的全部产物，逐个校验 sha256，并摆到 build.sh 期望的位置。
# 用法：KMVideo/claude_pop/fetch_release.sh [video|build|all]
#   video：只要成片（母版/平台版/分享版/封面 → out/）
#   build：接着改片所需的一切（逐帧图 → out/frames、字体 → fonts/、水彩底板 → assets/plates/、
#          配乐与分轨 → out/、ClaudeAnimationBase/node_modules）。之后改字幕/配乐只需重跑 build.sh，
#          只有被删掉的帧会重渲。
#   all（默认）：两者都要，外加审片对比图（out/release/review_sheets.zip）和源码快照。
# 可断点续传；已下载且校验通过的文件不会重下。Mac / Linux 通用（需要 curl、unzip、tar）。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; BASE="$HERE/../../ClaudeAnimationBase"
TAG="${TAG:-KMVideo-claude-pop-v1}"; URL="https://github.com/LinzeColin/KMOS/releases/download/$TAG"
WHAT="${1:-all}"; DL="$HERE/out/release"; mkdir -p "$DL"
sha() { if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1; }
curl -fsSL --retry 4 -o "$DL/SHA256SUMS.txt" "$URL/SHA256SUMS.txt"
get() {  # 下载单个附件并校验
  local f="$1" want; want="$(awk -v f="$f" '$2==f{print $1}' "$DL/SHA256SUMS.txt")"
  [[ -n "$want" ]] || { echo "SHA256SUMS.txt 里没有 $f" >&2; exit 1; }
  if [[ -s "$DL/$f" && "$(sha "$DL/$f")" == "$want" ]]; then echo "已有 $f"; return; fi
  echo "下载 $f"; curl -fL --retry 4 -C - -o "$DL/$f" "$URL/$f" || curl -fL --retry 4 -o "$DL/$f" "$URL/$f"
  [[ "$(sha "$DL/$f")" == "$want" ]] || { echo "校验失败：$f（删掉 $DL/$f 重跑）" >&2; exit 1; }
}
if [[ "$WHAT" == video || "$WHAT" == all ]]; then
  for f in KM_claude_pop.mp4 KM_claude_pop_web.mp4 KM_claude_pop_share.mp4 KM_claude_pop_cover.jpg; do get "$f"; cp "$DL/$f" "$HERE/out/$f"; done
fi
if [[ "$WHAT" == build || "$WHAT" == all ]]; then
  for f in frames.zip build_env.zip bgm.wav stems.zip node_modules.tar.gz; do get "$f"; done
  unzip -q -o "$DL/frames.zip" -d "$HERE/out"             # → out/frames/f00000.jpg … f01103.jpg
  unzip -q -o "$DL/build_env.zip" -d "$HERE"               # → fonts/*、assets/plates/*.jpg
  unzip -q -o "$DL/stems.zip" -d "$HERE/out"               # → out/stems/*.wav
  cp "$DL/bgm.wav" "$HERE/out/bgm.wav"
  [[ -d "$BASE/node_modules" ]] || tar -xzf "$DL/node_modules.tar.gz" -C "$BASE"
  n=$(ls "$HERE/out/frames" | grep -c '^f[0-9]*\.jpg$'); echo "逐帧图 $n 张（应为 1104）"
fi
if [[ "$WHAT" == all ]]; then get review_sheets.zip; get source_snapshot.zip; fi
echo "完成。成片在 $HERE/out/；想重新出片：CHROME_PATH=<Chrome 路径> GL= $HERE/build.sh"
