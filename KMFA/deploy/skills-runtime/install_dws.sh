#!/usr/bin/env bash
# 安装固化版本的 dws（DingTalk Workspace CLI，官方开源）。
# 版本固化：改 DWS_VERSION 必须走 PR；首次安装把实测 SHA-256 写入 dws.sha256.lock，
# 之后的安装若哈希不匹配立即失败（防上游资产被替换）。
set -euo pipefail

DWS_VERSION="${DWS_VERSION:-v1.0.52}"
REPO="DingTalk-Real-AI/dingtalk-workspace-cli"
INSTALL_DIR="${DWS_INSTALL_DIR:-/usr/local/bin}"
LOCK_FILE="$(cd "$(dirname "$0")" && pwd)/dws.sha256.lock"

case "$(uname -s)-$(uname -m)" in
  Linux-aarch64|Linux-arm64) ASSET_ARCH="linux-arm64" ;;
  Linux-x86_64)              ASSET_ARCH="linux-amd64" ;;
  Darwin-arm64)              ASSET_ARCH="darwin-arm64" ;;
  Darwin-x86_64)             ASSET_ARCH="darwin-amd64" ;;
  *) echo "不支持的平台: $(uname -s)-$(uname -m)" >&2; exit 1 ;;
esac

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# 资产命名以 release 页为准；两种常见命名都尝试。
BASE="https://github.com/${REPO}/releases/download/${DWS_VERSION}"
for NAME in "dws-${ASSET_ARCH}" "dws_${DWS_VERSION#v}_${ASSET_ARCH}.tar.gz" "dws-${DWS_VERSION}-${ASSET_ARCH}.tar.gz"; do
  if curl -fsSL -o "$TMP_DIR/$NAME" "$BASE/$NAME" 2>/dev/null; then
    ASSET="$NAME"
    break
  fi
done
[ -n "${ASSET:-}" ] || { echo "下载失败：请到 https://github.com/${REPO}/releases/tag/${DWS_VERSION} 核对资产名" >&2; exit 1; }

ACTUAL_SHA="$(shasum -a 256 "$TMP_DIR/$ASSET" 2>/dev/null | awk '{print $1}')" || ACTUAL_SHA="$(sha256sum "$TMP_DIR/$ASSET" | awk '{print $1}')"
LOCK_KEY="${DWS_VERSION} ${ASSET}"
if [ -f "$LOCK_FILE" ] && grep -q "^${LOCK_KEY} " "$LOCK_FILE"; then
  EXPECTED_SHA="$(grep "^${LOCK_KEY} " "$LOCK_FILE" | awk '{print $3}')"
  if [ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]; then
    echo "SHA-256 不匹配！期望 $EXPECTED_SHA 实测 $ACTUAL_SHA —— 中止安装" >&2
    exit 1
  fi
else
  echo "${LOCK_KEY} ${ACTUAL_SHA}" >> "$LOCK_FILE"
  echo "首次安装：已记录 SHA-256 ${ACTUAL_SHA} → $(basename "$LOCK_FILE")（请随 PR 入仓固化）"
fi

case "$ASSET" in
  *.tar.gz) tar -xzf "$TMP_DIR/$ASSET" -C "$TMP_DIR"; BIN="$(find "$TMP_DIR" -type f -name dws | head -1)" ;;
  *)        BIN="$TMP_DIR/$ASSET" ;;
esac
[ -n "$BIN" ] || { echo "压缩包内未找到 dws 可执行文件" >&2; exit 1; }
install -m 755 "$BIN" "$INSTALL_DIR/dws"
echo "dws ${DWS_VERSION} 已安装到 ${INSTALL_DIR}/dws"
"$INSTALL_DIR/dws" --version || true
