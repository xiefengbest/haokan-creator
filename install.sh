#!/usr/bin/env bash
# 安装 Haokan Creator，并把技能说明接到本机代理。
set -euo pipefail

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

python3 -m venv "$SRC/.venv"
"$SRC/.venv/bin/pip" install -U pip
"$SRC/.venv/bin/pip" install -e "$SRC"

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

echo "Haokan Creator 已安装到 $SRC"
echo "重新打开终端和代理后，执行：creator auth status"
