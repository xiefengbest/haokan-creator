"""Haokan Creator 命令行。"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

from creator_publish import __version__
from creator_publish.config import REPO_ROOT, data_home


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, OSError):
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    profile_name = None
    if len(argv) >= 2 and argv[0] == "--profile":
        profile_name = argv[1]
        argv = argv[2:]
    if not argv or argv[0] in {"-h", "--help", "help"}:
        print(_overview())
        return 0
    group = argv[0]
    rest = argv[1:]
    publishing = group == "work" and rest[:1] == ["+publish"] and "--dry-run" not in rest
    pending = False
    if group != "update" and not publishing:
        state = _sync(allow_apply=True)
        if state == "updated":
            _restart()
        pending = state == "pending"
    try:
        if group == "profile":
            code = _profile(rest)
        elif group == "auth":
            code = _auth(rest, profile_name)
        elif group == "update":
            code = _update(rest)
        elif group == "work":
            code = _work(rest, profile_name)
        elif group in {"album", "me"}:
            code = _later(group)
        else:
            print(_overview())
            return 2
        if publishing and _sync(allow_apply=False) == "pending":
            pending = True
        if pending:
            _notice()
        return code
    except SystemExit as exc:
        code = exc.code
        if code in (None, 0):
            return 0
        if isinstance(code, int):
            return code
        return _fail(str(code))


def _sync(allow_apply: bool) -> str:
    from creator_publish.update_check import sync_repo

    return sync_repo(REPO_ROOT, data_home() / "update-check.json", allow_apply=allow_apply)


def _restart() -> None:
    os.environ["HAOKAN_CREATOR_SKIP_UPDATE"] = "1"
    print("已自动更新到最新版本。", file=sys.stderr)
    argv0 = sys.argv[0]
    if os.access(argv0, os.X_OK):
        os.execv(argv0, sys.argv)
    os.execv(sys.executable, [sys.executable, *sys.argv])


def _notice() -> None:
    print("有新版本。当前操作已完成，执行 creator update 即可更新。", file=sys.stderr)


def _profile(argv: list[str]) -> int:
    from creator_publish.profiles import add_profile, list_profiles, remove_profile, use_profile

    parser = argparse.ArgumentParser(prog="creator profile")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("list", help="查看本机已保存的创作者账号")
    add = sub.add_parser("add", help="添加一个创作者账号")
    add.add_argument("--name", required=True, help="显示名，用创作者名字")
    add.add_argument("--phone", required=True, help="登录手机号")
    add.add_argument("--region", choices=("cn", "xjp"), default="cn")
    add.add_argument("--password-stdin", action="store_true", help="从标准输入读密码")
    use = sub.add_parser("use", help="切换默认账号")
    use.add_argument("name")
    remove = sub.add_parser("remove", help="只从这台电脑删除账号")
    remove.add_argument("name")
    args = parser.parse_args(argv)
    if args.action == "list":
        return _ok({"profiles": list_profiles()})
    if args.action == "add":
        password = sys.stdin.read().strip() if args.password_stdin else ""
        if not args.password_stdin:
            return _fail("请用 --password-stdin 从标准输入提供密码，避免密码出现在命令历史里。")
        add_profile(args.name, args.phone, password, args.region)
        return _ok({"name": args.name, "region": args.region})
    if args.action == "use":
        use_profile(args.name)
        return _ok({"active": args.name})
    remove_profile(args.name)
    return _ok({"removed": args.name})


def _auth(argv: list[str], profile_name: str | None) -> int:
    parser = argparse.ArgumentParser(prog="creator auth")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status", help="检查当前账号能否登录")
    args = parser.parse_args(argv)
    if args.action != "status":
        return _fail("只能执行 creator auth status")
    from creator_publish.api import ApiError, CreatorClient
    from creator_publish.config import load_settings
    from creator_publish.profiles import apply_profile, mask_phone

    item = apply_profile(profile_name)
    settings = load_settings(require_account=True)
    client = CreatorClient(settings)
    try:
        session = client.login()
    except ApiError as exc:
        return _fail(str(exc))
    return _ok(
        {
            "version": __version__,
            "name": item["name"],
            "region": item.get("region") or "cn",
            "phone": mask_phone(item.get("phone") or ""),
            "userName": session.user_name,
        }
    )


def _update(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="creator update")
    parser.parse_args(argv)
    repo = REPO_ROOT
    if not (repo / ".git").is_dir():
        return _fail("这不是从 GitHub 安装的副本，无法更新。")
    pull = subprocess.run(["git", "-C", str(repo), "pull", "--ff-only"], text=True, capture_output=True)
    if pull.returncode != 0:
        detail = (pull.stderr or pull.stdout or "git pull 失败").strip()
        return _fail(detail)
    pip = repo / ".venv" / "bin" / "pip"
    if pip.is_file():
        installed = subprocess.run([str(pip), "install", "-e", str(repo)], text=True, capture_output=True)
        if installed.returncode != 0:
            detail = (installed.stderr or installed.stdout or "依赖安装失败").strip()
            return _fail(detail)
    return _ok({"version": __version__, "message": "已更新。请重新打开代理后再使用。", "git": pull.stdout.strip()})


def _work(argv: list[str], profile_name: str | None) -> int:
    if not argv or argv[0] in {"-h", "--help"}:
        print("creator work +publish --dir <文件夹> --album-id <合辑ID> [--start-date 2026-07-13] [--dry-run]")
        return 0
    action = argv[0]
    if action != "+publish":
        return _later("work " + action)
    parser = argparse.ArgumentParser(prog="creator work +publish")
    parser.add_argument("--dir", required=True, type=Path, help="图片文件夹")
    parser.add_argument("--album-id", required=True, help="合辑 ID")
    parser.add_argument("--start-date", help="从这一天起一天一张")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不上传")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--square-from", choices=("portrait", "landscape"))
    args = parser.parse_args(argv[1:])
    if not args.dir.exists():
        return _fail(f"找不到文件夹：{args.dir}")
    if not args.dry_run:
        from creator_publish.profiles import apply_profile

        apply_profile(profile_name)
    from creator_publish.pipeline import run

    forwarded = ["--inbox", str(args.dir), "--album-id", args.album_id]
    if args.start_date:
        forwarded += ["--start-date", args.start_date]
    if args.limit:
        forwarded += ["--limit", str(args.limit)]
    if args.square_from:
        forwarded += ["--square-from", args.square_from]
    if not args.dry_run:
        forwarded.append("--publish")
    return run(forwarded)


def _later(group: str) -> int:
    return _fail(f"{group} 还没有开放。不要自己请求创作者接口。")


def _ok(data: dict) -> int:
    print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
    return 0


def _fail(message: str) -> int:
    print(json.dumps({"ok": False, "error": {"message": message}}, ensure_ascii=False), file=sys.stderr)
    return 1


def _overview() -> str:
    return f"""Haokan Creator {__version__}

安装：
  git clone https://github.com/xiefengbest/haokan-creator.git ~/.haokan-creator/repo && bash ~/.haokan-creator/repo/install.sh

账号：
  creator profile list
  printf '%s' '密码' | creator profile add --name 创作者名 --phone +8613800138000 --password-stdin
  creator profile use 创作者名
  creator --profile 创作者名 auth status

发布：
  creator work +publish --dir <文件夹> --album-id <合辑ID> --dry-run
  creator work +publish --dir <文件夹> --album-id <合辑ID> --start-date 2026-07-13

更新：
  creator update
"""
