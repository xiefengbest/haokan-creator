"""检查 GitHub 上是否有新版本。发布进行中只提示，不替换正在运行的程序。"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

CHECK_INTERVAL_SECONDS = 60 * 60


def sync_repo(repo: Path, cache_path: Path, *, allow_apply: bool, now: float | None = None, runner=None) -> str:
    """返回 current、updated、pending、skipped。updated 表示已经拉取，调用方应重新执行命令。"""
    if os.environ.get("HAOKAN_CREATOR_SKIP_UPDATE") == "1":
        return "skipped"
    if not (repo / ".git").is_dir():
        return "skipped"
    moment = time.time() if now is None else now
    cached = _read_cache(cache_path)
    run = runner or _git_run
    fresh = cached is not None and moment - cached.get("checked_at", 0) < CHECK_INTERVAL_SECONDS
    if fresh and cached.get("state") == "current":
        return "current"
    if fresh and cached.get("state") == "pending":
        return _apply_pending(repo, cache_path, allow_apply=allow_apply, now=moment, runner=run)
    if _git(repo, "fetch", "origin", "main", runner=run) != 0:
        return "skipped"
    local = _git_text(repo, "rev-parse", "HEAD", runner=run)
    remote = _git_text(repo, "rev-parse", "origin/main", runner=run)
    if not local or not remote:
        return "skipped"
    if local == remote:
        _write_cache(cache_path, {"checked_at": moment, "state": "current"})
        return "current"
    _write_cache(cache_path, {"checked_at": moment, "state": "pending"})
    return _apply_pending(repo, cache_path, allow_apply=allow_apply, now=moment, runner=run)


def _apply_pending(repo: Path, cache_path: Path, *, allow_apply: bool, now: float, runner) -> str:
    if not allow_apply:
        return "pending"
    status = runner(["git", "-C", str(repo), "status", "--porcelain"], text=True, capture_output=True, timeout=20)
    if status.returncode != 0 or (status.stdout or "").strip():
        return "pending"
    if _git(repo, "pull", "--ff-only", runner=runner) != 0:
        return "pending"
    from creator_publish.venv_install import install_repo_into_venv

    code, _detail = install_repo_into_venv(repo, runner=runner)
    if code != 0:
        return "pending"
    _write_cache(cache_path, {"checked_at": now, "state": "current"})
    return "updated"


def _git_run(cmd: list[str], **kwargs):
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    kwargs.setdefault("text", True)
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("timeout", 20)
    kwargs["env"] = env
    return subprocess.run(cmd, **kwargs)


def _git(repo: Path, *args: str, runner) -> int:
    result = runner(["git", "-C", str(repo), *args], text=True, capture_output=True, timeout=20)
    return result.returncode


def _git_text(repo: Path, *args: str, runner) -> str:
    result = runner(["git", "-C", str(repo), *args], text=True, capture_output=True, timeout=20)
    if result.returncode != 0:
        return ""
    return (result.stdout or "").strip()


def _read_cache(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _write_cache(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
