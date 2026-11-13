#!/usr/bin/env bash
# 安装 Haokan Creator，并把技能说明接到本机代理。
set -euo pipefail

# 部分机器的文件策略会拦截 venv 内删除 .pyc；不生成字节码可减少触发。
export PYTHONDONTWRITEBYTECODE=1

REPO="https://github.com/xiefengbest/haokan-creator.git"
ROOT="${HAOKAN_CREATOR_HOME:-$HOME/.haokan-creator}"
SRC="$ROOT/repo"

if ! command -v git >/dev/null 2>&1; then
  echo "需要先安装 git" >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "需要先安装 Python 3" >&2
  exit 1
fi

mkdir -p "$ROOT"
if [[ ! -d "$SRC/.git" ]]; then
  git clone "$REPO" "$SRC"
else
  git -C "$SRC" pull --ff-only
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

install_editable() {
  local py
  py="$(venv_python)"
  export PYTHONDONTWRITEBYTECODE=1

  if [[ -x "$SRC/.venv/bin/pip" ]]; then
    if "$SRC/.venv/bin/pip" install -e "$SRC"; then
      return 0
    fi
    echo "pip 安装失败，尝试备用方式…" >&2
  fi

  if command -v uv >/dev/null 2>&1; then
    uv pip install -e "$SRC" --python "$py"
    return 0
  fi

  if [[ ! -x "$SRC/.venv/bin/pip" ]]; then
    if ! command -v curl >/dev/null 2>&1; then
      echo "需要 curl 或本机已安装 uv，以便在无 pip 的 venv 里装依赖" >&2
      return 1
    fi
    curl -fsSL https://bootstrap.pypa.io/get-pip.py | "$py" -
    PYTHONDONTWRITEBYTECODE=1 "$SRC/.venv/bin/pip" install -e "$SRC"
    return 0
  fi

  echo "依赖安装失败。若本机策略拦截 venv 内删除 .pyc，可先安装 uv 后重跑本脚本。" >&2
  return 1
}

create_venv
install_editable

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

if [[ -f "$SRC/scripts/git-hooks/pre-commit" ]]; then
  mkdir -p "$SRC/.git/hooks"
  cp "$SRC/scripts/git-hooks/pre-commit" "$SRC/.git/hooks/pre-commit"
  chmod +x "$SRC/.git/hooks/pre-commit"
fi

echo "Haokan Creator 已安装到 $SRC"
echo "重新打开终端和代理后，执行：creator auth status"
