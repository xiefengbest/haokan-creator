#!/usr/bin/env bash
# 解析国内 CDN 安装包地址（读 manifest.json，避免固定文件名被缓存）
# 可被 install.sh source；install-from-cdn.sh 内联相同逻辑以便首装可用。
set -euo pipefail

cdn_dist_base() {
  echo "${HAOKAN_CREATOR_CDN_DIST:-https://hk-h5-cdn.levect.com/html/xiefeng/creator/dist}"
}

cdn_manifest_url() {
  echo "$(cdn_dist_base)/manifest.json"
}

# 输出 tarball 的完整 URL；可用环境变量 HAOKAN_CREATOR_DIST_URL 覆盖
cdn_resolve_tarball_url() {
  if [[ -n "${HAOKAN_CREATOR_DIST_URL:-}" ]]; then
    echo "$HAOKAN_CREATOR_DIST_URL"
    return 0
  fi
  if ! command -v curl >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
    echo "需要 curl 与 python3 以读取 CDN manifest" >&2
    return 1
  fi
  local manifest
  manifest="$(curl -fsSL "$(cdn_manifest_url)")" || return 1
  CDN_MANIFEST_JSON="$manifest" python3 - <<'PY'
import json, os, sys
base = os.environ.get("HAOKAN_CREATOR_CDN_DIST", "https://hk-h5-cdn.levect.com/html/xiefeng/creator/dist").rstrip("/")
raw = os.environ.get("CDN_MANIFEST_JSON", "")
m = json.loads(raw)
url = m.get("tarballUrl") or ""
if not url:
    name = m.get("tarball") or ""
    if not name:
        sys.exit("manifest 缺少 tarball")
    url = f"{base}/{name}"
print(url)
PY
}

cdn_manifest_label() {
  if ! command -v curl >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
    return 0
  fi
  local manifest
  manifest="$(curl -fsSL "$(cdn_manifest_url)" 2>/dev/null)" || return 0
  CDN_MANIFEST_JSON="$manifest" python3 - <<'PY'
import json, os
m = json.loads(os.environ.get("CDN_MANIFEST_JSON", "{}"))
commit = m.get("commit") or "?"
ver = m.get("version") or ""
label = commit if not ver else f"{ver} ({commit})"
print(label)
PY
}
