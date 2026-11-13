#!/usr/bin/env bash
# 从国内 CDN 安装 Haokan Creator（不访问 GitHub）。也可：curl -fsSL <本脚本 CDN 地址> | bash
set -euo pipefail

ROOT="${HAOKAN_CREATOR_HOME:-$HOME/.haokan-creator}"
SRC="$ROOT/repo"
CDN_DIST_DEFAULT="https://hk-h5-cdn.levect.com/html/xiefeng/creator/dist"

_load_cdn_dist() {
  local here=""
  if [[ -n "${BASH_SOURCE[0]:-}" ]]; then
    here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  fi
  if [[ -n "$here" && -f "$here/cdn-dist.sh" ]]; then
    # shellcheck source=cdn-dist.sh
    source "$here/cdn-dist.sh"
    return 0
  fi
  local helper
  helper="$(mktemp)"
  curl -fsSL "${HAOKAN_CREATOR_CDN_DIST:-$CDN_DIST_DEFAULT}/cdn-dist.sh" -o "$helper"
  # shellcheck source=/dev/null
  source "$helper"
  rm -f "$helper"
}

if ! command -v curl >/dev/null 2>&1; then
  echo "需要先安装 curl" >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "需要先安装 Python 3" >&2
  exit 1
fi
_check_py() {
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null || {
    echo "需要 Python 3.9 或更新版本（当前：$(python3 --version 2>&1)）" >&2
    exit 1
  }
}
_check_py
if ! command -v tar >/dev/null 2>&1; then
  echo "需要先安装 tar" >&2
  exit 1
fi

_load_cdn_dist

DIST_URL="$(cdn_resolve_tarball_url)" || {
  echo "无法读取 CDN manifest（$(cdn_manifest_url)）" >&2
  exit 1
}
LABEL="$(cdn_manifest_label 2>/dev/null || true)"

mkdir -p "$ROOT"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "正在从国内 CDN 下载安装包${LABEL:+（版本 ${LABEL}）}…"
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
