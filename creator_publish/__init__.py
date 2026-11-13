"""创作者后台命令行。"""

from __future__ import annotations

import re
from pathlib import Path


def _version_from_pyproject() -> str:
    root = Path(__file__).resolve().parents[1]
    path = root / "pyproject.toml"
    if not path.is_file():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    if not match:
        raise RuntimeError("pyproject.toml 缺少 version")
    return match.group(1)


def _resolve_version() -> str:
    try:
        from importlib.metadata import version

        return version("haokan-creator")
    except Exception:
        pass
    try:
        return _version_from_pyproject()
    except (FileNotFoundError, OSError, RuntimeError):
        return "0.0.0"


__version__ = _resolve_version()
