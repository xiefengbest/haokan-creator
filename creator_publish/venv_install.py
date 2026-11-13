"""把当前仓库装进 ~/.haokan-creator/repo/.venv。默认非 editable，避免 egg-info 临时文件被文件代理拦截。"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def install_repo_into_venv(repo: Path, *, runner=None) -> tuple[int, str]:
    run = runner or subprocess.run
    py = repo / ".venv" / "bin" / "python"
    pip = repo / ".venv" / "bin" / "pip"
    if not py.is_file():
        return 0, ""
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    uv = shutil.which("uv")
    if uv:
        completed = run(
            [uv, "pip", "install", str(repo), "--python", str(py)],
            text=True,
            capture_output=True,
            timeout=300,
            env=env,
        )
    elif pip.is_file():
        completed = run(
            [str(pip), "install", str(repo)],
            text=True,
            capture_output=True,
            timeout=300,
            env=env,
        )
    else:
        return 1, "虚拟环境里找不到 pip，请先重新执行 install.sh"
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "依赖安装失败").strip()
        return completed.returncode, detail
    return 0, ""
