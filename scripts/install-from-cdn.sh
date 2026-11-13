#!/usr/bin/env bash
# 从国内 CDN 安装 Haokan Creator（不访问 GitHub）。也可：curl -fsSL <本脚本 CDN 地址> | bash
set -euo pipefail

ROOT="${HAOKAN_CREATOR_HOME:-$HOME/.haokan-creator}"
SRC="$ROOT/repo"
DIST_URL="${HAOKAN_CREATOR_DIST_URL:-https://hk-h5-cdn.levect.com/html/xiefeng/creator/dist/haokan-creator.tar.gz}"

if ! command -v curl >/dev/null 2>&1; then
  echo "需要先安装 curl" >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "需要先安装 Python 3" >&2
  exit 1
fi
if ! command -v tar >/dev/null 2>&1; then
  echo "需要先安装 tar" >&2
  exit 1
fi

mkdir -p "$ROOT"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "正在从国内 CDN 下载安装包…"
if ! curl -fsSL "$DIST_URL" | tar -xzf - -C "$tmp"; then
  echo "下载失败。若公司网络限制，请联系谢峰获取离线包。" >&2
  exit 1
fi
if [[ ! -d "$tmp/haokan-creator" ]]; then
  echo "安装包格式异常，请联系维护者。" >&2
  exit 1
fi

rm -rf "$SRC"
mv "$tmp/haokan-creator" "$SRC"
trap - EXIT
rm -rf "$tmp"

export HAOKAN_CREATOR_SKIP_GIT=1
exec bash "$SRC/install.sh"
