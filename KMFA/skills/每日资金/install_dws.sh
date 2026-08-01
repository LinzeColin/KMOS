#!/bin/sh
set -eu

DWS_VERSION="${DWS_VERSION:-v1.0.52}"
ASSET="dws-linux-amd64.tar.gz"
EXPECTED="$(awk -v version="$DWS_VERSION" -v asset="$ASSET" '$1==version && $2==asset {print $3}' /opt/daily-funds/dws.sha256.lock)"
[ -n "$EXPECTED" ] || { echo "DWS_LOCK_MISSING" >&2; exit 1; }
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
curl -fsSL -o "$tmp/$ASSET" "https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/releases/download/$DWS_VERSION/$ASSET"
echo "$EXPECTED  $tmp/$ASSET" | sha256sum -c -
tar -xzf "$tmp/$ASSET" -C "$tmp"
binary="$(find "$tmp" -type f -name dws | head -1)"
[ -n "$binary" ] || { echo "DWS_BINARY_MISSING" >&2; exit 1; }
install -m 0755 "$binary" /usr/local/bin/dws
/usr/local/bin/dws --version >/dev/null
