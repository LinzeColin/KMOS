#!/usr/bin/env bash
# 造 KMFA.app（TSK.KMFA.PROD.0015，复用 KMIDS app_bundle 模式）。
# 与 KMIDS 的差别：启动器用 shell 而非编译 C——KMFA 没有 C 源，
# 引入 clang 依赖只会让「双击可用」多一个可能坏掉的环节。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${KMFA_REPO_DIR:-$(cd "$HERE/../../.." && pwd)}"
APP_NAME="${KMFA_APP_NAME:-KMFA.app}"
APP_DIR="$HERE/$APP_NAME"
EXEC_NAME="KMFALauncher"

rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"

# 把仓路径烧进启动器：.app 被拷到 Downloads/Applications 后仍要找得到仓
sed "s#__REPO_DIR__#${REPO_DIR}#g" "$HERE/launcher.sh" > "$APP_DIR/Contents/MacOS/$EXEC_NAME"
chmod +x "$APP_DIR/Contents/MacOS/$EXEC_NAME"

cat > "$APP_DIR/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>KMFA</string>
  <key>CFBundleDisplayName</key><string>KMFA 经营分析</string>
  <key>CFBundleIdentifier</key><string>com.linzecolin.kmfa.app</string>
  <key>CFBundleVersion</key><string>0.1.4</string>
  <key>CFBundleShortVersionString</key><string>0.1.4</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>$EXEC_NAME</string>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <key>LSUIElement</key><true/>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

# 记录构建绑定，供验收器与 parity 比对
cat > "$APP_DIR/Contents/Resources/build_manifest.json" <<MANIFEST
{
  "app_name": "$APP_NAME",
  "bundle_id": "com.linzecolin.kmfa.app",
  "executable": "$EXEC_NAME",
  "repo_dir": "$REPO_DIR",
  "entry_kind": "start_service_and_open_app",
  "legacy_entry_kind": "open_static_html",
  "task_id": "TSK.KMFA.PROD.0015"
}
MANIFEST

echo "$APP_DIR"
