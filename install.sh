#!/usr/bin/env bash
# 安装 Haokan Creator，并把技能说明接到本机代理。
set -euo pipefail

# 部分机器的文件策略会拦截 venv 内删除 .pyc；不生成字节码可减少触发。
export PYTHONDONTWRITEBYTECODE=1

REPO="https://github.com/xiefengbest/haokan-creator.git"
ROOT="${HAOKAN_CREATOR_HOME:-$HOME/.haokan-creator}"
SRC="$ROOT/repo"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "需要先安装 Python 3" >&2
  exit 1
fi

fetch_from_cdn() {
  if ! command -v curl >/dev/null 2>&1 || ! command -v tar >/dev/null 2>&1; then
    echo "无法访问 GitHub 时需 curl 与 tar，或使用 scripts/install-from-cdn.sh" >&2
    return 1
  fi
  local dist_url label
  if [[ -f "$SCRIPT_DIR/scripts/cdn-dist.sh" ]]; then
    # shellcheck source=scripts/cdn-dist.sh
    source "$SCRIPT_DIR/scripts/cdn-dist.sh"
    dist_url="$(cdn_resolve_tarball_url)" || return 1
    label="$(cdn_manifest_label 2>/dev/null || true)"
  elif [[ -n "${HAOKAN_CREATOR_DIST_URL:-}" ]]; then
    dist_url="$HAOKAN_CREATOR_DIST_URL"
  else
    echo "缺少 scripts/cdn-dist.sh，请用 install-from-cdn.sh 更新" >&2
    return 1
  fi
  if [[ -n "$label" ]]; then
    echo "从 CDN 下载版本 ${label}…" >&2
  fi
  local tmp
  tmp="$(mktemp -d)"
  if ! curl -fsSL "$dist_url" | tar -xzf - -C "$tmp"; then
    rm -rf "$tmp"
    return 1
  fi
  if [[ ! -d "$tmp/haokan-creator" ]]; then
    rm -rf "$tmp"
    echo "CDN 安装包格式异常" >&2
    return 1
  fi
  rm -rf "$SRC"
  mkdir -p "$ROOT"
  mv "$tmp/haokan-creator" "$SRC"
  rm -rf "$tmp"
  return 0
}

sync_source() {
  mkdir -p "$ROOT"
  if [[ "${HAOKAN_CREATOR_USE_CDN:-}" == "1" ]]; then
    fetch_from_cdn || exit 1
    return
  fi
  if [[ -f "$SRC/pyproject.toml" && "${HAOKAN_CREATOR_SKIP_GIT:-}" == "1" ]]; then
    return
  fi
  if [[ -d "$SRC/.git" ]]; then
    git -C "$SRC" pull --ff-only
    return
  fi
  if [[ -f "$SRC/pyproject.toml" ]]; then
    return
  fi
  if command -v git >/dev/null 2>&1; then
    if git clone "$REPO" "$SRC" 2>/dev/null; then
      return
    fi
    echo "GitHub 不可用，改从国内 CDN 下载…" >&2
  fi
  if fetch_from_cdn; then
    return
  fi
  echo "安装失败：请确认能访问 GitHub，或执行：curl -fsSL https://hk-h5-cdn.levect.com/html/xiefeng/creator/dist/install-from-cdn.sh | bash" >&2
  exit 1
}

sync_source
if [[ ! -f "$SRC/install.sh" || ! -f "$SRC/pyproject.toml" ]]; then
  echo "安装目录不完整" >&2
  exit 1
fi

venv_python() {
  echo "$SRC/.venv/bin/python"
}

venv_ready() {
  [[ -x "$(venv_python)" ]]
}

create_venv() {
  if venv_ready; then
    return 0
  fi
  if [[ -d "$SRC/.venv" ]]; then
    rm -rf "$SRC/.venv" 2>/dev/null || true
  fi
  if python3 -m venv "$SRC/.venv" 2>/dev/null; then
    return 0
  fi
  echo "标准虚拟环境创建失败，改用不带 pip 的 venv（适用于拦截 .pyc 删除的机器）" >&2
  python3 -m venv --without-pip "$SRC/.venv"
}

# 不用 pip install -e：企业代理（如 WorkBuddy safe-delete）常拦截 egg-info 临时文件删除。
install_package() {
  local py
  py="$(venv_python)"
  export PYTHONDONTWRITEBYTECODE=1

  if command -v uv >/dev/null 2>&1; then
    if uv pip install "$SRC" --python "$py"; then
      return 0
    fi
    echo "uv 安装失败，尝试 pip…" >&2
  fi

  if [[ -x "$SRC/.venv/bin/pip" ]]; then
    if "$SRC/.venv/bin/pip" install "$SRC"; then
      return 0
    fi
    echo "pip 安装失败，尝试备用方式…" >&2
  fi

  if [[ ! -x "$SRC/.venv/bin/pip" ]]; then
    if ! command -v curl >/dev/null 2>&1; then
      echo "需要 curl 或本机已安装 uv，以便在无 pip 的 venv 里装依赖" >&2
      return 1
    fi
    curl -fsSL https://bootstrap.pypa.io/get-pip.py | "$py" -
    PYTHONDONTWRITEBYTECODE=1 "$SRC/.venv/bin/pip" install "$SRC"
    return 0
  fi

  echo "依赖安装失败。" >&2
  echo "若日志含 safe-delete、broker denied、egg-info：多为 WorkBuddy 等文件代理拦截。" >&2
  echo "请在本机「终端」执行同一安装命令（勿在沙箱内），或先安装 uv 后重跑： https://github.com/astral-sh/uv" >&2
  return 1
}

create_venv
install_package

mkdir -p "$HOME/.local/bin"
ln -sfn "$SRC/.venv/bin/creator" "$HOME/.local/bin/creator"

for agent in "$HOME/.cursor/skills" "$HOME/.agents/skills"; do
  mkdir -p "$agent"
  for skill in creator-shared creator-work creator-album creator-profile; do
    ln -sfn "$SRC/skills/$skill" "$agent/$skill"
  done
done

PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
for rc in "$HOME/.zshrc" "$HOME/.bashrc"; do
  if [[ -f "$rc" ]] && grep -Fq '.local/bin' "$rc"; then
    continue
  fi
  if [[ -f "$rc" || "$rc" == "$HOME/.zshrc" ]]; then
    touch "$rc"
    printf '\n%s\n' "$PATH_LINE" >> "$rc"
  fi
done

if [[ -d "$SRC/.git" && -f "$SRC/scripts/git-hooks/pre-commit" ]]; then
  mkdir -p "$SRC/.git/hooks"
  cp "$SRC/scripts/git-hooks/pre-commit" "$SRC/.git/hooks/pre-commit"
  chmod +x "$SRC/.git/hooks/pre-commit"
fi

echo "Haokan Creator 已安装到 $SRC"
echo "重新打开终端和代理后，执行：creator auth status"
