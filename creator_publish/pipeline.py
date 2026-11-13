"""预览裁切，或登录后上传并发布。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import time
from datetime import datetime, timedelta
from dataclasses import replace
from pathlib import Path

from creator_publish.config import TOOL_ROOT, Settings, describe_account, load_settings, output_dir
from creator_publish.crop import MIN_SHORT_EDGE, PlanError
from creator_publish.images import (
    SLOT_LABELS,
    WorkPlan,
    content_type_for,
    describe_plan,
    plan_work,
    read_upload_body,
)
from creator_publish.manifest import Work, load_csv, load_inbox

def done_path() -> Path:
    return output_dir() / "done.json"


def pending_dir() -> Path:
    return output_dir() / "pending"


def result_path() -> Path:
    return output_dir() / "results.jsonl"


def run(argv=None) -> int:
    parser = argparse.ArgumentParser(description="把竖图和横图发布到创作者后台")
    parser.add_argument("--publish", action="store_true", help="真正上传并发布。不加则只预览裁切")
    parser.add_argument("--works", type=Path, help="作品 CSV")
    parser.add_argument("--inbox", type=Path, help="资料目录，每个子文件夹一件作品")
    parser.add_argument("--limit", type=int, default=0, help="只处理前几件")
    parser.add_argument("--force", action="store_true", help="已发布过的作品再发一条")
    parser.add_argument("--sleep", type=float, default=0.5, help="每件作品之间的间隔秒数")
    parser.add_argument("--retry-pending", action="store_true", help="只补登记上次创建成功但尺寸失败的作品")
    parser.add_argument("--square-from", choices=("portrait", "landscape"), help="没有方图时从竖图或横图裁")
    parser.add_argument("--album-id", help="这次发布的合辑 ID")
    parser.add_argument("--start-date", help="从这一天起按序号一天一张，例如 2026-07-13")
    parser.add_argument("--content", help="覆盖每件作品的描述（最多 100 字）")
    args = parser.parse_args(argv)
    if args.album_id:
        os.environ["CREATOR_ALBUM_ID"] = args.album_id.strip()

    publishing = args.publish or args.retry_pending
    settings = load_settings(require_account=publishing, require_album=publishing)
    if args.square_from:
        settings = replace(settings, square_from=args.square_from)

    if args.retry_pending:
        from creator_publish.api import CreatorClient

        client = CreatorClient(settings)
        print("正在登录…")
        client.login()
        print("登录成功")
        return retry_pending(client)

    try:
        works = discover(args)
        if args.content is not None:
            text = args.content.strip()
            if len(text) > 100:
                raise PlanError("作品描述不能超过 100 字")
            works = [replace(work, content=text) for work in works]
        if args.start_date:
            works = schedule_daily(works, args.start_date)
    except PlanError as exc:
        raise SystemExit(str(exc)) from exc
    if args.limit > 0:
        works = works[: args.limit]
    print(describe_account(settings))
    if not publishing:
        return dry_run(works, settings.square_from)

    from creator_publish.api import ApiError, CreatorClient

    print(f"区域 {settings.region}")
    if settings.square_from == "portrait":
        print("没有单独方图时，从竖图正中间裁")
    else:
        print("没有单独方图时，从横图正中间裁")
    client = CreatorClient(settings)
    print("正在登录…")
    try:
        client.login()
    except ApiError as exc:
        write_error(exc.payload)
        raise SystemExit(str(exc)) from exc
    print("登录成功")
    return publish_all(client, settings, works, args.force, args.sleep)


def schedule_daily(works: list[Work], day: str) -> list[Work]:
    from creator_publish.manifest import SHANGHAI

    try:
        start = datetime.strptime(day.strip(), "%Y-%m-%d")
    except ValueError as exc:
        raise SystemExit("开始日期格式应为 2026-07-13") from exc
    start = start.replace(hour=0, minute=0, second=0, tzinfo=SHANGHAI)
    scheduled = []
    for offset, work in enumerate(works):
        moment = start + timedelta(days=offset)
        end_moment = moment.replace(hour=23, minute=59, second=59, microsecond=0)
        scheduled.append(
            replace(
                work,
                start_time=int(moment.timestamp() * 1000),
                end_time=int(end_moment.timestamp() * 1000),
            )
        )
    return scheduled


def discover(args) -> list[Work]:
    if args.works and args.inbox:
        raise PlanError("请只指定 --works 或 --inbox 其中一个")
    if args.works:
        print(f"读取表格 {args.works}")
        return _require_works(load_csv(args.works))
    if args.inbox:
        print(f"读取资料 {args.inbox}")
        return _require_works(load_inbox(args.inbox))
    csv_path = TOOL_ROOT / "works.csv"
    inbox = TOOL_ROOT / "资料"
    if csv_path.is_file():
        print(f"读取表格 {csv_path}")
        return _require_works(load_csv(csv_path))
    if inbox.is_dir():
        works = load_inbox(inbox)
        if works:
            print(f"读取资料 {inbox}")
            return works
    raise PlanError(
        "还没有作品资料。\n"
        "把每个作品放进一个文件夹，例如 资料/海边日落/竖图.jpg 和 横图.jpg。\n"
        "也可以按 works.example.csv 写一份 works.csv。"
    )


def _require_works(works: list[Work]) -> list[Work]:
    if not works:
        raise PlanError("资料是空的")
    return works


def dry_run(works: list[Work], square_from: str) -> int:
    print("这是预览，没有上传。")
    failed = 0
    for index, work in enumerate(works, start=1):
        print(f"\n[{index}/{len(works)}]")
        try:
            plan = plan_work(work, square_from)
        except PlanError as exc:
            failed += 1
            print(f"{work.title} 不能发布：{exc}")
            continue
        print(describe_plan(plan))
    passed = len(works) - failed
    print(f"\n预览完成：通过 {passed}，不能发布 {failed}")
    return 1 if failed else 0


def publish_all(client, settings: Settings, works: list[Work], force: bool, pause: float) -> int:
    from creator_publish.api import ApiError

    done = load_json(done_path(), {})
    pending = load_pending()
    uploader = Uploader(client, settings)
    success = 0
    skipped = 0
    failed = 0
    for index, work in enumerate(works, start=1):
        print(f"\n[{index}/{len(works)}] {work.title}")
        digest = work_digest(work, settings.album_id, settings.square_from)
        if digest in done and not force:
            skipped += 1
            print(f"已经发布过，作品 {done[digest].get('imageGroupId')}。要再发一条请加 --force")
            continue
        used_network = False
        try:
            if digest in pending and not force:
                group_id = finish_pending(client, pending[digest], digest, done, work)
                used_network = True
            else:
                plan = plan_work(work, settings.square_from)
                print(describe_plan(plan))
                print("正在上传并裁切…")
                used_network = True
                upload_plan(uploader, plan)
                group_id = client.release(release_body(plan, settings.album_id))
                entries = [item.list_entry() for slot in plan.slots() for item in slot.items]
                path = write_pending(group_id, digest, work.title, entries)
                used_network = True
                try:
                    client.add_sizes(group_id, entries)
                except Exception:
                    print(f"作品 {group_id} 已创建，尺寸登记失败。稍后执行 publish.py --retry-pending")
                    raise
                path.unlink(missing_ok=True)
                remember_done(done, digest, group_id, work.title, settings, plan.cover.oss_key)
            success += 1
            record = done[digest]
            print(f"发布成功，作品 {group_id}")
            if record.get("cover"):
                print(f"封面 {record['cover']}")
            append_result({"ok": True, "title": work.title, "imageGroupId": group_id, "cover": record.get("cover", "")})
        except (PlanError, ApiError, RuntimeError, OSError) as exc:
            failed += 1
            print(f"失败：{exc}")
            if isinstance(exc, ApiError):
                write_error(exc.payload)
            append_result({"ok": False, "title": work.title, "error": str(exc)})
        if used_network and index < len(works) and pause > 0:
            time.sleep(pause)
    print(f"\n完成：成功 {success}，跳过 {skipped}，失败 {failed}")
    if failed:
        print(f"失败记录在 {result_path()}")
    return 1 if failed else 0


def finish_pending(client, path: Path, digest: str, done: dict, work: Work) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    group_id = str(data["imageGroupId"])
    print(f"作品 {group_id} 已创建，继续登记尺寸…")
    client.add_sizes(group_id, data["list"])
    path.unlink(missing_ok=True)
    remember_done(done, digest, group_id, work.title, client.settings, cover_filename(data["list"]))
    return group_id


def upload_plan(uploader, plan: WorkPlan) -> None:
    for attempt in range(2):
        store = uploader.store(force=attempt > 0)
        try:
            for slot in plan.slots():
                upload_slot(store, slot)
            return
        except Exception as exc:
            if attempt == 0 and token_expired(exc):
                print("上传凭证过期，正在刷新…")
                continue
            raise


def upload_slot(store, slot) -> None:
    raw_key = new_object_key(slot.ext)
    raw_bytes = read_upload_body(slot)
    call_with_retry(
        f"上传{SLOT_LABELS[slot.slot]}原图",
        lambda: store.put_bytes(raw_key, raw_bytes, content_type_for(slot.ext)),
    )
    slot.raw_item.oss_key = raw_key
    if slot.shares_raw_key:
        slot.compress_item.oss_key = raw_key
        source_key = raw_key
    else:
        if not slot.compress_body:
            raise PlanError(f"{SLOT_LABELS[slot.slot]}缺少压缩图")
        compress_key = new_object_key("jpg")
        compress_bytes = slot.compress_body
        call_with_retry(
            f"上传{SLOT_LABELS[slot.slot]}压缩图",
            lambda: store.put_bytes(compress_key, compress_bytes, "image/jpeg"),
        )
        slot.compress_item.oss_key = compress_key
        source_key = compress_key
    for item in slot.crop_items():
        if not item.process:
            raise PlanError(f"{SLOT_LABELS[slot.slot]} {item.resolution} 缺少裁切参数")
        target = new_crop_key(source_key, item.process)
        width, height = call_with_retry(
            f"裁切{SLOT_LABELS[slot.slot]} {item.resolution}",
            lambda process=item.process, key=target: store.crop_save(source_key, process, key),
        )
        item.oss_key = target
        item.width = width
        item.height = height
        short_edge = min(width, height)
        if short_edge < MIN_SHORT_EDGE:
            raise PlanError(f"{SLOT_LABELS[slot.slot]} {item.resolution} 实际窄边 {short_edge}，不足 1080")


def release_body(plan: WorkPlan, album_id: str) -> dict:
    cover = plan.cover
    if not cover.oss_key:
        raise PlanError("封面还没有上传")
    body = {
        "pStatus": 1,
        "albumIds": str(album_id),
        "coverFileName": cover.oss_key,
        "coverW": cover.width,
        "coverH": cover.height,
        "workType": 2,
        "subTitle": "查看更多",
        "deepLink": "",
        "skipUrl": "",
        "skipType": 0,
        "isVideo": False,
        "syncImageStorage": False,
    }
    if plan.work.content:
        body["content"] = plan.work.content
    if plan.work.start_time is not None:
        body["startTime"] = plan.work.start_time
    if plan.work.end_time is not None:
        body["endTime"] = plan.work.end_time
    return body


def retry_pending(client) -> int:
    from creator_publish.api import ApiError

    files = sorted(pending_dir().glob("*.json")) if pending_dir().is_dir() else []
    if not files:
        print("没有待补登记的作品")
        return 0
    failed = 0
    done = load_json(done_path(), {})
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        group_id = str(data.get("imageGroupId", ""))
        try:
            client.add_sizes(group_id, data["list"])
        except (ApiError, OSError, RuntimeError) as exc:
            failed += 1
            print(f"补登记失败 {group_id}：{exc}")
            if isinstance(exc, ApiError):
                write_error(exc.payload)
            continue
        path.unlink(missing_ok=True)
        digest = data.get("digest")
        if digest:
            done[digest] = {
                "imageGroupId": group_id,
                "title": data.get("title") or "",
                "cover": _cover_url(client.settings, cover_filename(data["list"])),
            }
            save_json(done_path(), done)
        print(f"已补登记 {group_id}")
    return 1 if failed else 0


class Uploader:
    def __init__(self, client, settings: Settings):
        self.client = client
        self.settings = settings
        self.creds = None
        self.fetched_at = 0.0

    def store(self, force: bool = False):
        from creator_publish.oss_store import OssStore, make_bucket

        if force or self.creds is None or time.time() - self.fetched_at > 45:
            self.creds = self.client.oss_token()
            self.fetched_at = time.time()
        return OssStore(make_bucket(self.creds, self.settings), self.settings.bucket)


def new_object_key(ext: str) -> str:
    cleaned = "jpg" if ext in {"jpg", "jpeg"} else ext
    return f"release/image/{int(time.time() * 1000):x}{secrets.token_hex(6)}.{cleaned}"


def new_crop_key(source_key: str, process: str) -> str:
    digest = hashlib.md5(f"{source_key}{process}{secrets.token_hex(8)}".encode()).hexdigest()
    return f"release/image/{digest}.jpg"


def token_expired(exc: Exception) -> bool:
    text = str(exc)
    return any(word in text for word in ("SecurityToken", "ExpiredToken", "InvalidAccessKeyId"))


def call_with_retry(label: str, func):
    last = None
    for attempt in range(3):
        try:
            return func()
        except PlanError:
            raise
        except Exception as exc:
            if token_expired(exc):
                raise
            last = exc
            if attempt == 2:
                break
            time.sleep(0.6 * (attempt + 1))
    raise RuntimeError(f"{label}失败：{last}") from last


def work_digest(work: Work, album_id: str, square_from: str) -> str:
    digest = hashlib.sha256()
    for part in (album_id, square_from, work.content, str(work.start_time or ""), str(work.end_time or "")):
        digest.update(part.encode())
        digest.update(b"\0")
    for label, path in (("portrait", work.portrait), ("landscape", work.landscape), ("square", work.square)):
        digest.update(label.encode())
        if path is not None:
            digest.update(hash_file(path).encode())
        digest.update(b"\0")
    return digest.hexdigest()


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_pending(group_id: str, digest: str, title: str, entries: list[dict]) -> Path:
    pending_dir().mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^0-9A-Za-z._-]", "_", group_id)[:80] or "unknown"
    path = pending_dir() / f"{safe}.json"
    path.write_text(
        json.dumps(
            {"imageGroupId": group_id, "digest": digest, "title": title, "list": entries},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def load_pending() -> dict[str, Path]:
    found = {}
    if not pending_dir().is_dir():
        return found
    for path in pending_dir().glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        digest = data.get("digest")
        if digest:
            found[digest] = path
    return found


def cover_filename(entries: list[dict]) -> str:
    for item in entries:
        if item.get("imageResolution") == "9:16" and item.get("imageSizeType") == 2:
            return item.get("imageFilename") or ""
    return ""


def _cover_url(settings: Settings, cover_key: str) -> str:
    if not cover_key:
        return ""
    if cover_key.startswith(("http://", "https://")):
        return cover_key
    return f"{settings.oss_res}{cover_key}"


def remember_done(done: dict, digest: str, group_id: str, title: str, settings: Settings, cover_key: str) -> None:
    done[digest] = {"imageGroupId": group_id, "title": title, "cover": _cover_url(settings, cover_key)}
    save_json(done_path(), done)


def write_error(payload) -> None:
    from creator_publish.api import redact

    output_dir().mkdir(parents=True, exist_ok=True)
    (output_dir() / "last-error.json").write_text(
        json.dumps(redact(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def append_result(record: dict) -> None:
    output_dir().mkdir(parents=True, exist_ok=True)
    with result_path().open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_json(path: Path, default):
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
