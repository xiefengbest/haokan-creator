"""创作者后台命令行。"""

from __future__ import annotations

import re
from pathlib import Path


def _version_from_pyproject() -> str:
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    if not match:
        raise RuntimeError("pyproject.toml 缺少 version")
    return match.group(1)


__version__ = _version_from_pyproject()
