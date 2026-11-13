#!/usr/bin/env bash
# 安装前检查 Python >= 3.9
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "需要先安装 Python 3" >&2
  exit 1
fi
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
  echo "需要 Python 3.9 或更新版本（当前：$(python3 --version 2>&1)）" >&2
  exit 1
fi
