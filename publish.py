#!/usr/bin/env python3
"""创作者后台批量发布静态壁纸。"""

from __future__ import annotations

import sys


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, OSError):
        pass
    try:
        from creator_publish.pipeline import run
    except ImportError as exc:
        raise SystemExit(
            "缺少依赖。请在本目录执行：\n"
            "python3 -m venv .venv && .venv/bin/pip install -r requirements.txt\n"
            f"({exc})"
        ) from exc
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
