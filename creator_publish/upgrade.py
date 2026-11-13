"""更新：优先 GitHub，不通再走国内 CDN。"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

GITHUB_REPO = "https://github.com/xiefengbest/haokan-creator.git"


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def upgrade_via_github(repo: Path) -> tuple[bool, str, str]:
    """
    返回 (成功, 详情, 来源 github|无)。
    有 .git 时 pull；无 .git 时浅克隆替换源码（保留 .venv）。
    """
    if (repo / ".git").is_dir():
        pull = subprocess.run(
            ["git", "-C", str(repo), "pull", "--ff-only"],
            text=True,
            capture_output=True,
            timeout=120,
            env=_git_env(),
        )
        if pull.returncode != 0:
            detail = (pull.stderr or pull.stdout or "git pull 失败").strip()
            return False, detail, "github"
        from creator_publish.venv_install import install_repo_into_venv

        code, detail = install_repo_into_venv(repo)
        if code != 0:
            return False, detail or "依赖安装失败", "github"
        git_out = (pull.stdout or "").strip()
        return True, git_out or "已更新", "github"

    if not shutil.which("git"):
        return False, "未安装 git", ""

    parent = repo.parent
    stash = parent / ".haokan-creator-git-upgrade"
    if stash.exists():
        shutil.rmtree(stash, ignore_errors=True)
    clone = subprocess.run(
        ["git", "clone", "--depth", "1", "-b", "main", GITHUB_REPO, str(stash)],
        text=True,
        capture_output=True,
        timeout=180,
        env=_git_env(),
    )
    if clone.returncode != 0:
        shutil.rmtree(stash, ignore_errors=True)
        detail = (clone.stderr or clone.stdout or "git clone 失败").strip()
        return False, detail, "github"

    venv = repo / ".venv"
    venv_stash = parent / ".haokan-creator-venv-stash"
    if venv_stash.exists():
        shutil.rmtree(venv_stash, ignore_errors=True)
    if venv.is_dir():
        shutil.move(str(venv), str(venv_stash))

    shutil.rmtree(repo, ignore_errors=True)
    shutil.move(str(stash), str(repo))

    if venv_stash.is_dir():
        shutil.move(str(venv_stash), str(venv))

    from creator_publish.venv_install import install_repo_into_venv

    code, detail = install_repo_into_venv(repo)
    if code != 0:
        return False, detail or "依赖安装失败", "github"
    return True, "已从 GitHub 克隆最新 main", "github"


def upgrade_via_cdn(repo: Path) -> tuple[bool, str]:
    script = repo / "scripts" / "install-from-cdn.sh"
    if not script.is_file():
        return False, "找不到 install-from-cdn.sh，请执行安装页上的 curl 命令"
    proc = subprocess.run(["bash", str(script)], text=True, capture_output=True, timeout=600)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "CDN 更新失败").strip()
        return False, detail
    return True, "已从国内 CDN 更新"
