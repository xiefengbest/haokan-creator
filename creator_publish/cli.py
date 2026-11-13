"""Haokan Creator 命令行。"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

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
    writing = _online_write(group, rest)
    pending = False
    if group != "update" and not writing:
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
        elif group == "album":
            code = _album(rest, profile_name)
        elif group == "me":
            code = _me(rest, profile_name)
        elif group == "config":
            code = _config(rest)
        else:
            print(_overview())
            return 2
        if writing and _sync(allow_apply=False) == "pending":
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


def _online_write(group: str, rest: list[str]) -> bool:
    if "--yes" not in rest or "--dry-run" in rest:
        return False
    action = rest[:1]
    if group == "work" and action in (["+publish"], ["+update"], ["+delete"]):
        return True
    if group == "album" and action in (["+create"], ["+update"], ["+delete"]):
        return True
    return group == "me" and action == ["+update"]


def _config(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="creator config")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status", help="检查本机后台配置是否齐全")
    import_cmd = sub.add_parser("import", help="导入谢峰提供的 backend.env")
    import_cmd.add_argument("file", type=Path, help="配置文件路径")
    args = parser.parse_args(argv)
    from creator_publish.config_cmd import describe_status, import_backend, inspect_backend

    if args.action == "status":
        payload = inspect_backend()
        payload["message"] = describe_status(payload)
        return _ok(payload)
    target = import_backend(args.file.expanduser().resolve())
    return _ok({"backendEnv": str(target), "imported": True, "message": "后台配置已导入。请执行 creator auth status 确认能登录。"})


def _login(profile_name: str | None):
    from creator_publish.api import CreatorClient
    from creator_publish.config import load_settings
    from creator_publish.profiles import apply_profile

    item = apply_profile(profile_name)
    client = CreatorClient(load_settings(require_account=True))
    client.login()
    return item, client


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
    add.add_argument("--yes", action="store_true", help="用户确认后再保存")
    use = sub.add_parser("use", help="切换默认账号")
    use.add_argument("name")
    use.add_argument("--yes", action="store_true", help="用户确认后再切换")
    remove = sub.add_parser("remove", help="只从这台电脑删除账号")
    remove.add_argument("name")
    remove.add_argument("--yes", action="store_true", help="用户确认后再删除")
    args = parser.parse_args(argv)
    if args.action == "list":
        return _ok({"profiles": list_profiles()})
    if args.action == "add":
        from creator_publish.profiles import mask_phone

        if not args.yes:
            return _confirm(
                "新增本机账号",
                {"name": args.name, "phone": mask_phone(args.phone), "region": args.region},
                "将在这台电脑保存这个创作者号。不会修改线上资料。",
            )
        password = sys.stdin.read().strip() if args.password_stdin else ""
        if not args.password_stdin:
            return _fail("请用 --password-stdin 从标准输入提供密码，避免密码出现在命令历史里。")
        add_profile(args.name, args.phone, password, args.region)
        return _ok({"name": args.name, "region": args.region})
    if args.action == "use":
        if not args.yes:
            active = next((row["name"] for row in list_profiles() if row["active"]), "")
            return _confirm(
                "切换默认账号",
                {"from": active or "未设置", "to": args.name},
                "之后没指定账号的命令都会用这个创作者号。",
            )
        use_profile(args.name)
        return _ok({"active": args.name})
    if not args.yes:
        return _confirm(
            "删除本机账号",
            {"name": args.name},
            "只从这台电脑删除登录信息，不删除线上创作者。",
        )
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
        script = repo / "scripts" / "install-from-cdn.sh"
        if not script.is_file():
            return _fail("这是从国内 CDN 安装的副本。请重新执行安装页上的 curl 安装命令，或联系谢峰。")
        proc = subprocess.run(["bash", str(script)], text=True, capture_output=True)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "CDN 更新失败").strip()
            return _fail(detail)
        from creator_publish import _version_from_pyproject

        return _ok(
            {
                "version": _version_from_pyproject(),
                "message": "已从国内 CDN 更新。请重新打开代理后再使用。",
                "source": "cdn",
            }
        )
    pull = subprocess.run(["git", "-C", str(repo), "pull", "--ff-only"], text=True, capture_output=True)
    if pull.returncode != 0:
        detail = (pull.stderr or pull.stdout or "git pull 失败").strip()
        return _fail(detail)
    from creator_publish.venv_install import install_repo_into_venv

    code, detail = install_repo_into_venv(repo)
    if code != 0:
        return _fail(detail or "依赖安装失败")
    return _ok({"version": __version__, "message": "已更新。请重新打开代理后再使用。", "git": pull.stdout.strip()})


def _work(argv: list[str], profile_name: str | None) -> int:
    if not argv or argv[0] in {"-h", "--help"}:
        print("creator work +publish --dir <文件夹> --album-id <合辑ID> [--start-date 2026-07-13]")
        print("creator work +update --group-id <作品ID> [--content 描述] [--album-id <合辑ID>]")
        print("creator work +delete --group-id <作品ID>")
        print("先看基本信息和变动。用户确认后，在原命令末尾加上 --yes 再执行。")
        return 0
    action = argv[0]
    if action == "+publish":
        return _publish(argv[1:], profile_name)
    if action == "+update":
        return _update_work(argv[1:], profile_name)
    if action == "+delete":
        return _delete_work(argv[1:], profile_name)
    return _later("work " + action)


def _publish(argv: list[str], profile_name: str | None) -> int:
    parser = argparse.ArgumentParser(prog="creator work +publish")
    parser.add_argument("--dir", required=True, type=Path, help="图片文件夹")
    parser.add_argument("--album-id", required=True, help="合辑 ID")
    parser.add_argument("--start-date", help="从这一天起一天一张")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不上传")
    parser.add_argument("--yes", action="store_true", help="用户确认变动后再发布")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--square-from", choices=("portrait", "landscape"))
    args = parser.parse_args(argv)
    if not args.dir.exists():
        return _fail(f"找不到文件夹：{args.dir}")
    from creator_publish.profiles import apply_profile

    item = apply_profile(profile_name)
    from creator_publish.pipeline import run

    execute = args.yes and not args.dry_run
    forwarded = ["--inbox", str(args.dir), "--album-id", args.album_id]
    if args.start_date:
        forwarded += ["--start-date", args.start_date]
    if args.limit:
        forwarded += ["--limit", str(args.limit)]
    if args.square_from:
        forwarded += ["--square-from", args.square_from]
    if execute:
        forwarded.append("--publish")
        return run(forwarded)
    code = run(forwarded)
    if code != 0:
        print("有不能发布的作品，先处理后再确认。", file=sys.stderr)
        return code
    if args.dry_run:
        return 0
    change = "将把预览通过的作品新发布到这个合辑。已经发过的会跳过。"
    if args.start_date:
        change = f"从 {args.start_date} 起按序号一天一张。" + change
    else:
        change = "不填写上线日期，发布后立即可见。" + change
    return _confirm(
        "发布作品",
        {
            "creator": item["name"],
            "albumId": args.album_id,
            "dir": str(args.dir),
            "startDate": args.start_date or "立即发布",
        },
        change,
    )


def _album(argv: list[str], profile_name: str | None) -> int:
    if not argv or argv[0] in {"-h", "--help"}:
        print("creator album list")
        print("creator album +create --name 合辑名 --desc 简介 --frequency daily")
        print("creator album +update --album-id <ID> [--name 合辑名] [--desc 简介] [--frequency daily]")
        print("creator album +delete --album-id <ID>")
        print("先看基本信息和变动。用户确认后，在原命令末尾加上 --yes 再执行。")
        return 0
    action = argv[0]
    if action == "list":
        return _album_list(profile_name)
    if action == "+create":
        return _album_create(argv[1:], profile_name)
    if action == "+update":
        return _album_update(argv[1:], profile_name)
    if action == "+delete":
        return _album_delete(argv[1:], profile_name)
    return _later("album " + action)


def _album_list(profile_name: str | None) -> int:
    from creator_publish.api import ApiError
    from creator_publish.manage import album_row

    try:
        _, client = _login(profile_name)
        rows = [album_row(item) for item in client.list_albums()]
    except (ApiError, SystemExit) as exc:
        return _fail(str(exc))
    return _ok({"albums": rows})


def _album_create(argv: list[str], profile_name: str | None) -> int:
    from creator_publish.api import ApiError
    from creator_publish.manage import FREQUENCIES, limit_text, parse_frequency

    parser = argparse.ArgumentParser(prog="creator album +create")
    parser.add_argument("--name", required=True)
    parser.add_argument("--desc", required=True)
    parser.add_argument("--frequency", required=True, choices=tuple(FREQUENCIES))
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)
    try:
        rate = parse_frequency(args.frequency)
        assert rate is not None
        name = limit_text(args.name, "cn", "合辑名称")
        desc = limit_text(args.desc, "cn", "合辑简介")
    except SystemExit as exc:
        return _fail(str(exc))
    from creator_publish.profiles import apply_profile

    item = apply_profile(profile_name)
    label = FREQUENCIES[args.frequency][1]
    if not args.yes:
        return _confirm(
            "新建合辑",
            {"creator": item["name"], "name": name, "frequency": label},
            f"将新建一个订阅合辑，更新频率是{label}。",
        )
    try:
        _, client = _login(profile_name)
        album_id = client.create_album(name, desc, rate)
    except (ApiError, SystemExit) as exc:
        return _fail(str(exc))
    return _ok({"albumId": album_id, "name": name, "frequency": label})


def _album_update(argv: list[str], profile_name: str | None) -> int:
    from creator_publish.api import ApiError
    from creator_publish.manage import FREQUENCIES, album_row, find_album, frequency_label, limit_text, parse_frequency

    parser = argparse.ArgumentParser(prog="creator album +update")
    parser.add_argument("--album-id", required=True)
    parser.add_argument("--name")
    parser.add_argument("--desc")
    parser.add_argument("--frequency", choices=tuple(FREQUENCIES))
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)
    if not any([args.name, args.desc, args.frequency]):
        return _fail("请至少提供 --name、--desc 或 --frequency 中的一项。")
    try:
        rate = parse_frequency(args.frequency) if args.frequency else None
    except SystemExit as exc:
        return _fail(str(exc))
    from creator_publish.profiles import apply_profile

    item = apply_profile(profile_name)
    try:
        _, client = _login(profile_name)
        current = find_album(client.list_albums(), args.album_id)
    except (ApiError, SystemExit) as exc:
        return _fail(str(exc))
    current_view = album_row(current)
    next_name = limit_text(args.name, "cn", "合辑名称") if args.name else current_view["name"]
    next_desc = limit_text(args.desc, "cn", "合辑简介") if args.desc else current_view["desc"]
    next_label = FREQUENCIES[args.frequency][1] if args.frequency else current_view["frequency"]
    if not args.yes:
        return _confirm(
            "修改合辑",
            {
                "creator": item["name"],
                "albumId": args.album_id,
                "name": next_name,
                "frequency": next_label,
            },
            f"将把合辑简介改成：{next_desc}",
        )
    try:
        client.update_album(args.album_id, next_name, next_desc, rate)
    except (ApiError, SystemExit) as exc:
        return _fail(str(exc))
    return _ok({"albumId": args.album_id, "name": next_name, "frequency": next_label})


def _album_delete(argv: list[str], profile_name: str | None) -> int:
    from creator_publish.api import ApiError
    from creator_publish.manage import album_row, find_album

    parser = argparse.ArgumentParser(prog="creator album +delete")
    parser.add_argument("--album-id", required=True)
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)
    from creator_publish.profiles import apply_profile

    item = apply_profile(profile_name)
    try:
        _, client = _login(profile_name)
        current = find_album(client.list_albums(), args.album_id)
    except (ApiError, SystemExit) as exc:
        return _fail(str(exc))
    view = album_row(current)
    if not args.yes:
        return _confirm(
            "删除合辑",
            {"creator": item["name"], "albumId": args.album_id, "name": view["name"]},
            "将从线上删除这个合辑，无法恢复。合辑里的作品需要另行处理。",
        )
    try:
        client.delete_album(args.album_id)
    except (ApiError, SystemExit) as exc:
        return _fail(str(exc))
    return _ok({"albumId": args.album_id, "removed": True})


def _update_work(argv: list[str], profile_name: str | None) -> int:
    from creator_publish.api import ApiError
    from creator_publish.manage import (
        album_ids_from_info,
        pick_cover,
        schedule_ms,
        work_summary,
        work_update_body,
    )

    parser = argparse.ArgumentParser(prog="creator work +update")
    parser.add_argument("--group-id", required=True)
    parser.add_argument("--content")
    parser.add_argument("--album-id")
    parser.add_argument("--immediate", action="store_true", help="改成立即上线")
    parser.add_argument("--start-date", help="预约上线日期 YYYY-MM-DD")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)
    if not any([args.content is not None, args.album_id, args.immediate, args.start_date]):
        return _fail("请至少提供 --content、--album-id、--immediate 或 --start-date 中的一项。")
    if args.immediate and args.start_date:
        return _fail("--immediate 和 --start-date 不要同时写。")
    from creator_publish.profiles import apply_profile

    item = apply_profile(profile_name)
    try:
        _, client = _login(profile_name)
        rows = client.list_works(args.group_id)
        info = client.work_info(args.group_id)
        if not rows and not info:
            return _fail(f"没有找到作品 {args.group_id}。")
        summary = work_summary(rows[0] if rows else info, args.group_id)
        current_albums = album_ids_from_info(info) or summary.get("album", "")
        next_content = (args.content if args.content is not None else summary["content"]).strip()
        if len(next_content) > 100:
            return _fail("作品描述不能超过 100 个字。")
        next_albums = args.album_id or current_albums
        end_ms = None
        start_ms = None
        if args.start_date:
            from creator_publish.manage import schedule_day_bounds

            start_ms, end_ms = schedule_day_bounds(args.start_date)
        change_bits = []
        if args.content is not None:
            change_bits.append(f"描述改成：{next_content or '（空）'}")
        if args.album_id:
            change_bits.append(f"合辑改成：{args.album_id}")
        if args.immediate:
            change_bits.append("改成立即上线")
        elif args.start_date:
            change_bits.append(f"上线日期改成：{args.start_date}")
        if not args.yes:
            return _confirm(
                "修改作品",
                {
                    "creator": item["name"],
                    "groupId": args.group_id,
                    "albumId": next_albums,
                    "content": next_content,
                },
                "；".join(change_bits) or "将保存作品修改。",
            )
        cover = pick_cover(client.work_sizes(args.group_id))
        body = work_update_body(
            info,
            cover,
            args.group_id,
            next_content,
            next_albums,
            args.immediate,
            start_ms,
            end_ms,
        )
        group_id = client.update_work(body)
    except (ApiError, SystemExit) as exc:
        return _fail(str(exc))
    return _ok({"groupId": group_id})


def _delete_work(argv: list[str], profile_name: str | None) -> int:
    from creator_publish.api import ApiError
    from creator_publish.manage import work_summary

    parser = argparse.ArgumentParser(prog="creator work +delete")
    parser.add_argument("--group-id", required=True)
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)
    from creator_publish.profiles import apply_profile

    item = apply_profile(profile_name)
    try:
        _, client = _login(profile_name)
        rows = client.list_works(args.group_id)
        info = client.work_info(args.group_id)
        summary = work_summary(rows[0] if rows else info, args.group_id)
    except (ApiError, SystemExit) as exc:
        return _fail(str(exc))
    if not args.yes:
        return _confirm(
            "删除作品",
            {
                "creator": item["name"],
                "groupId": summary["groupId"],
                "content": summary["content"],
                "album": summary["album"],
            },
            "将从线上删除这件作品，无法恢复。",
        )
    try:
        client.delete_work(args.group_id)
    except (ApiError, SystemExit) as exc:
        return _fail(str(exc))
    return _ok({"groupId": args.group_id, "removed": True})


def _me(argv: list[str], profile_name: str | None) -> int:
    if not argv or argv[0] in {"-h", "--help"}:
        print("creator me +show")
        print("creator me +update --name 昵称 [--description 简介] [--avatar-url 头像地址]")
        print("creator me +update --social-platform xiaohongshu --social-url https://...")
        print("creator me +update --clear-social")
        print("先看基本信息和变动。用户确认后，在原命令末尾加上 --yes 再执行。")
        return 0
    action = argv[0]
    if action == "+show":
        return _me_show(profile_name)
    if action == "+update":
        return _me_update(argv[1:], profile_name)
    return _later("me " + action)


def _me_show(profile_name: str | None) -> int:
    from creator_publish.api import ApiError
    from creator_publish.manage import SOCIALS, creator_row

    try:
        item, client = _login(profile_name)
        row = creator_row(client.creator_info())
    except (ApiError, SystemExit) as exc:
        return _fail(str(exc))
    platform = row.get("socialPlatform") or ""
    return _ok(
        {
            "creator": item["name"],
            "name": row["name"],
            "description": row["description"],
            "avatarUrl": row["avatarUrl"],
            "socialPlatform": platform,
            "socialLabel": SOCIALS.get(platform, ""),
            "socialUrl": row.get("socialUrl") or "",
        }
    )


def _me_update(argv: list[str], profile_name: str | None) -> int:
    from creator_publish.api import ApiError
    from creator_publish.manage import SOCIALS, creator_row, limit_text, social_change

    parser = argparse.ArgumentParser(prog="creator me +update")
    parser.add_argument("--name")
    parser.add_argument("--description")
    parser.add_argument("--avatar-url")
    parser.add_argument("--social-platform", choices=tuple(SOCIALS))
    parser.add_argument("--social-url")
    parser.add_argument("--clear-social", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)
    if not any([args.name, args.description is not None, args.avatar_url, args.social_platform, args.social_url, args.clear_social]):
        return _fail("请至少提供一项要修改的资料。")
    if args.clear_social and (args.social_platform or args.social_url):
        return _fail("--clear-social 不要和社交链接参数一起写。")
    from creator_publish.profiles import apply_profile

    item = apply_profile(profile_name)
    region = item.get("region") or "cn"
    try:
        _, client = _login(profile_name)
        current = creator_row(client.creator_info())
    except (ApiError, SystemExit) as exc:
        return _fail(str(exc))
    next_name = limit_text(args.name, region, "昵称") if args.name else current["name"]
    if args.description is not None:
        next_description = limit_text(args.description, region, "简介")
    else:
        next_description = current["description"]
    next_avatar = (args.avatar_url or current["avatarUrl"]).strip()
    try:
        page_type, homepage = social_change(args.social_platform, args.social_url, args.clear_social)
    except SystemExit as exc:
        return _fail(str(exc))
    if not page_type and not homepage and not args.clear_social:
        page_type = current.get("socialPlatform") or ""
        homepage = current.get("socialUrl") or ""
    changes = []
    if args.name:
        changes.append(f"昵称改成：{next_name}")
    if args.description is not None:
        changes.append("将更新简介")
    if args.avatar_url:
        changes.append("将更新头像")
    if args.clear_social:
        changes.append("将移除社交链接")
    elif args.social_platform or args.social_url:
        changes.append(f"社交链接改成：{SOCIALS.get(page_type, page_type)}")
    if not args.yes:
        return _confirm(
            "修改创作者资料",
            {"creator": item["name"], "name": next_name},
            "；".join(changes) or "将保存资料修改。",
        )
    try:
        client.update_creator(next_name, next_avatar, next_description, page_type, homepage)
    except (ApiError, SystemExit) as exc:
        return _fail(str(exc))
    return _ok({"name": next_name, "updated": True})


def _later(group: str) -> int:
    return _fail(f"{group} 还没有开放。不要自己请求创作者接口。")


def _confirm(action: str, basic: dict, change: str) -> int:
    print(
        json.dumps(
            {
                "ok": False,
                "error": {
                    "type": "confirmation",
                    "action": action,
                    "basic": basic,
                    "change": change,
                    "hint": "把基本信息和变动告诉用户。用户明确同意后，在原命令末尾加上 --yes 再执行。不要自行加上 --yes。",
                },
            },
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )
    return 10


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

账号、密码和密钥需要联系谢峰申请。还没有这些配置时，先申请，不要自己查找或编造。

后台配置：
  creator config status
  creator config import <谢峰提供的文件>

账号：
  creator profile list
  printf '%s' '密码' | creator profile add --name 创作者名 --phone +8613800138000 --password-stdin
  creator profile use 创作者名
  creator --profile 创作者名 auth status

合辑：
  creator album list
  creator album +create --name 合辑名 --desc 简介 --frequency daily --yes
  creator album +update --album-id <ID> --name 新名称 --yes
  creator album +delete --album-id <ID> --yes

作品：
  creator work +publish --dir <文件夹> --album-id <合辑ID> --start-date 2026-07-13
  creator work +publish --dir <文件夹> --album-id <合辑ID> --yes
  creator work +update --group-id <作品ID> --content 描述 --yes
  creator work +delete --group-id <作品ID> --yes

资料：
  creator me +show
  creator me +update --description 新简介 --yes

更新：
  creator update
"""
