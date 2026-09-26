#!/usr/bin/env bash
# 取回本片的全部产物，逐个校验 sha256，并摆到 build.sh 期望的位置。
# 来源二选一：
#   SRC=<本地文件夹>  文件夹里放着交付包解出来的文件（KM_claude_pop_bundle.tar 解包后的内容，含 SHA256SUMS.txt）
#   （不设 SRC）      从 GitHub Release $TAG 下载（需要先有人把交付包传成 Release，见 HANDOFF.md §7）
# 用法：[SRC=…] KMVideo/claude_pop/fetch_release.sh [video|build|all]
#   video：只要成片（母版/平台版/分享版/封面 → out/）
#   build：接着改片所需的一切（逐帧图 → out/frames、字体 → fonts/、水彩底板 → assets/plates/、
#          配乐与分轨 → out/、ClaudeAnimationBase/node_modules）。之后改字幕/配乐只需重跑 build.sh，
#          只有被删掉的帧会重渲。
#   all（默认）：两者都要，外加审片对比图与源码快照（留在 out/release/）。
# 可重复执行；已存在且校验通过的文件不会重下。Mac / Linux 通用（需要 curl、unzip、tar、ffmpeg）。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; BASE="$HERE/../../ClaudeAnimationBase"
TAG="${TAG:-KMVideo-claude-pop-v1}"; URL="https://github.com/LinzeColin/KMOS/releases/download/$TAG"
WHAT="${1:-all}"; DL="$HERE/out/release"; mkdir -p "$DL"
sha() { if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1; }
fetch() { if [[ -n "${SRC:-}" ]]; then cp "$SRC/$1" "$DL/$1"; else curl -fL --retry 4 -o "$DL/$1" "$URL/$1"; fi; }
[[ -n "${SRC:-}" && "$(cd "$SRC" && pwd)" == "$DL" ]] || fetch SHA256SUMS.txt
has() { awk -v f="$1" '$2==f{found=1} END{exit !found}' "$DL/SHA256SUMS.txt"; }
get() {  # 取单个文件并校验
  local f="$1" want; want="$(awk -v f="$f" '$2==f{print $1}' "$DL/SHA256SUMS.txt")"
  [[ -n "$want" ]] || { echo "SHA256SUMS.txt 里没有 $f" >&2; exit 1; }
  if [[ -s "$DL/$f" && "$(sha "$DL/$f")" == "$want" ]]; then echo "已有 $f"; return; fi
  echo "取 $f"; fetch "$f"
  [[ "$(sha "$DL/$f")" == "$want" ]] || { echo "校验失败：$f（删掉 $DL/$f 重跑）" >&2; exit 1; }
}
if [[ "$WHAT" == video || "$WHAT" == all ]]; then
  for f in KM_claude_pop.mp4 KM_claude_pop_web.mp4 KM_claude_pop_share.mp4 KM_claude_pop_cover.jpg; do get "$f"; cp "$DL/$f" "$HERE/out/$f"; done
fi
if [[ "$WHAT" == build || "$WHAT" == all ]]; then
  for f in build_env.zip bgm.wav stems.zip node_modules.tar.gz; do get "$f"; done
  unzip -q -o "$DL/build_env.zip" -d "$HERE"               # → fonts/*、fonts/licenses/、assets/plates/*.jpg
  unzip -q -o "$DL/stems.zip" -d "$HERE/out"               # → out/stems/*.wav
  cp "$DL/bgm.wav" "$HERE/out/bgm.wav"
  [[ -d "$BASE/node_modules" ]] || tar -xzf "$DL/node_modules.tar.gz" -C "$BASE"
  mkdir -p "$HERE/out/frames"
  if has frames.zip; then                                  # 原始逐帧 JPG（体积大，交付包里可能没有）
    get frames.zip; unzip -q -o "$DL/frames.zip" -d "$HERE/out"
  elif [[ "$(ls "$HERE/out/frames" | grep -c '^f[0-9]*\.jpg$' || true)" != 1104 ]]; then
    # 母版是 crf17（肉眼无损），1104 帧都在里面，拆出来就能当逐帧图用
    get KM_claude_pop.mp4
    ffmpeg -v error -y -i "$DL/KM_claude_pop.mp4" -start_number 0 -q:v 2 "$HERE/out/frames/f%05d.jpg"
  fi
  n=$(ls "$HERE/out/frames" | grep -c '^f[0-9]*\.jpg$' || true); echo "逐帧图 $n 张（应为 1104）"
fi
if [[ "$WHAT" == all ]]; then get review_sheets.zip; get source_snapshot.zip; fi
echo "完成。成片在 $HERE/out/；想重新出片：CHROME_PATH=<Chrome 路径> GL= $HERE/build.sh"
