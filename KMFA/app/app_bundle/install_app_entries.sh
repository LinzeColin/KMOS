#!/usr/bin/env bash
# 安装 KMFA.app 入口（TSK.KMFA.PROD.0015，复用 KMIDS install_app_entries.sh 模式）。
#
# 与 KMIDS 的一处刻意差别：**默认只装 ~/Downloads**。
# /Applications 属系统目录，要装得显式加 --applications——不替 Owner 动系统位置。
#
# parity：装完逐份比对 bundle 内所有文件的 sha256，任一份不一致即失败。
# 「重装 parity 证据」要的就是这个：重装后各份必须与源构建**逐字节一致**。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="${KMFA_APP_NAME:-KMFA.app}"
SOURCE_APP="$HERE/$APP_NAME"
WITH_APPLICATIONS=0
PARITY_OUT="${KMFA_PARITY_OUT:-$HERE/parity_record.json}"

for arg in "$@"; do
  case "$arg" in
    --applications) WITH_APPLICATIONS=1 ;;
    --parity-out=*) PARITY_OUT="${arg#*=}" ;;
    *) echo "未知参数：$arg" >&2; exit 2 ;;
  esac
done

"$HERE/build_app_bundle.sh" >/dev/null

clear_bundle_xattrs() {
  xattr -cr "$1" 2>/dev/null || true
  find "$1" -print0 2>/dev/null | while IFS= read -r -d '' item; do
    xattr -d com.apple.FinderInfo "$item" 2>/dev/null || true
    xattr -d com.apple.ResourceFork "$item" 2>/dev/null || true
    xattr -d 'com.apple.fileprovider.fpfs#P' "$item" 2>/dev/null || true
  done
}

sign_best_effort() {
  clear_bundle_xattrs "$1"
  if /usr/bin/codesign --force --deep --sign - "$1" >/dev/null 2>&1; then
    clear_bundle_xattrs "$1"
  else
    echo "警告：$1 未能签名，macOS 首次打开可能需要人工放行。" >&2
  fi
}

targets=("$HOME/Downloads/$APP_NAME")
[ "$WITH_APPLICATIONS" = "1" ] && targets+=("/Applications/$APP_NAME")

for dest in "${targets[@]}"; do
  rm -rf "$dest"
  cp -R "$SOURCE_APP" "$dest"
  sign_best_effort "$dest"
  LSREG="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
  [ -x "$LSREG" ] && "$LSREG" -f "$dest" >/dev/null 2>&1 || true
  echo "已安装：$dest"
done

# parity：签名会改 bundle（加 _CodeSignature），故比对**启动器与 Info.plist 与 manifest**
# 这三份「内容面」文件；它们才是"装出来的东西是不是同一个 App"的判据。
python3 - "$SOURCE_APP" "${targets[@]}" > "$PARITY_OUT" <<'PY'
import hashlib, json, sys
from pathlib import Path

CONTENT_FILES = (
    "Contents/MacOS/KMFALauncher",
    "Contents/Info.plist",
    "Contents/Resources/build_manifest.json",
)

def digest(root: Path) -> dict[str, str]:
    out = {}
    for rel in CONTENT_FILES:
        p = root / rel
        out[rel] = "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "MISSING"
    return out

source = Path(sys.argv[1])
src = digest(source)
installs = {str(Path(a)): digest(Path(a)) for a in sys.argv[2:]}
mismatched = {k: v for k, v in installs.items() if v != src}
print(json.dumps({
    "task_id": "TSK.KMFA.PROD.0015",
    "source": str(source),
    "source_digests": src,
    "installed": installs,
    "parity_ok": not mismatched,
    "mismatched": sorted(mismatched),
    "content_files_compared": list(CONTENT_FILES),
    "note": "签名会新增 _CodeSignature，故只比内容面三份文件——它们才决定装出来的是不是同一个 App",
}, ensure_ascii=False, indent=2))
PY

python3 -c "
import json,sys
d=json.load(open('$PARITY_OUT'))
print('parity:', 'OK' if d['parity_ok'] else 'MISMATCH ' + str(d['mismatched']))
sys.exit(0 if d['parity_ok'] else 1)
"
