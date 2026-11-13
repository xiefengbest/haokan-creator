#!/usr/bin/env python3
"""检查公开仓库里有没有密钥、口令、后台配置或真实手机号。失败时只报告位置，不打印内容。"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PHONE = "13800138000"
FORBIDDEN_NAMES = {
    ".env",
    ".env.local",
    "profiles.json",
    "service.json",
    "credentials.json",
    "id_rsa",
    "id_ed25519",
}
FORBIDDEN_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
SENSITIVE_ASSIGNMENT = re.compile(
    r"(?m)^[ \t]*(?:export[ \t]+)?CREATOR_"
    r"(?:SIGN_KEY|PASSWORD|STS_URL|COMPANY_ID|CLIENT_TYPE|API_VERSION|"
    r"CN_API|CN_OSS_RES|CN_BUCKET|CN_ENDPOINT|"
    r"XJP_API|XJP_OSS_RES|XJP_BUCKET|XJP_ENDPOINT|"
    r"PHONE|NAME|ALBUM_ID)"
    r"=[^\s#]"
)
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
CLOUD_KEY = re.compile(
    r"AKIA[0-9A-Z]{16}|LTAI[A-Za-z0-9]{12,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
)
PHONE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
HISTORY_PATTERNS = (
    r"CREATOR_(SIGN_KEY|PASSWORD|STS_URL|COMPANY_ID|CLIENT_TYPE|API_VERSION|CN_API|CN_OSS_RES|CN_BUCKET|CN_ENDPOINT|XJP_API|XJP_OSS_RES|XJP_BUCKET|XJP_ENDPOINT|PHONE|NAME|ALBUM_ID)=[^[:space:]#]",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"AKIA[0-9A-Z]{16}",
    r"LTAI[A-Za-z0-9]{12,}",
    r"ghp_[A-Za-z0-9]{20,}",
    r"github_pat_[A-Za-z0-9_]{20,}",
    r"1[3-9][0-9]{9}",
)


def scan_text(label: str, text: str) -> list[str]:
    problems = []
    if SENSITIVE_ASSIGNMENT.search(text):
        problems.append(f"{label}: 敏感配置写了具体值")
    if PRIVATE_KEY.search(text):
        problems.append(f"{label}: 含有私钥")
    if CLOUD_KEY.search(text):
        problems.append(f"{label}: 含有云账号或访问令牌")
    phones = {item for item in PHONE.findall(text) if item != SAMPLE_PHONE}
    if phones:
        problems.append(f"{label}: 含有示例以外的手机号")
    return problems


def forbidden_path(path: str) -> bool:
    name = Path(path).name
    if name in FORBIDDEN_NAMES or name.startswith(".env.") and name != ".env.example":
        return True
    return Path(path).suffix.lower() in FORBIDDEN_SUFFIXES


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in {0, 1}:
        raise SystemExit(result.stderr.strip() or "git 命令失败")
    return result.stdout


def collect() -> list[str]:
    problems = []
    tracked = [line for line in git_output("ls-files", "-z").split("\0") if line]
    for path in tracked:
        if forbidden_path(path):
            problems.append(f"{path}: 这个文件不能进入公开仓库")
            continue
        file_path = ROOT / path
        if not file_path.is_file():
            continue
        data = file_path.read_bytes()
        if b"\0" in data[:8000]:
            continue
        problems.extend(scan_text(path, data.decode("utf-8", "replace")))

    commits = [line for line in git_output("rev-list", "--all").splitlines() if line]
    for commit in commits:
        for path in git_output("ls-tree", "-r", "--name-only", commit).splitlines():
            if forbidden_path(path):
                problems.append(f"{commit[:12]}:{path}: 历史里有不能公开的文件")
        shown = git_output("grep", "-I", "-n", "-E", "|".join(HISTORY_PATTERNS), commit)
        for line in shown.splitlines():
            parts = line.split(":", 2)
            if len(parts) < 3:
                continue
            label = f"{parts[0][:12]}:{parts[1]}"
            problems.extend(scan_text(label, parts[2]))
    return sorted(set(problems))


def main() -> int:
    problems = collect()
    if problems:
        print("公开仓库检查未通过。下面只标出位置，没有打印具体内容。", file=sys.stderr)
        for item in problems:
            print(item, file=sys.stderr)
        return 1
    print("公开仓库检查通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
