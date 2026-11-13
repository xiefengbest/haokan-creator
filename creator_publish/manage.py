"""合辑、作品和创作者资料的变动说明。真正请求由调用方在用户确认后发出。"""

from __future__ import annotations

FREQUENCIES = {
    "daily": (1, "每日更新"),
    "weekly": (2, "每周更新"),
    "monthly": (3, "每月更新"),
    "yearly": (4, "每年更新"),
    "rotate": (5, "每日轮换"),
}
SOCIALS = {
    "xiaohongshu": "小红书",
    "weibo": "微博",
    "instagram": "Instagram",
    "facebook": "Facebook",
    "x": "X",
}
COVER_CANDIDATES = ((7, 2), (6, 0), (10, 0))


def _as_int(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def frequency_label(value: int | None) -> str:
    for _key, (number, label) in FREQUENCIES.items():
        if number == value:
            return label
    return "未设置"


def parse_frequency(value: str | None) -> int | None:
    if not value:
        return None
    item = FREQUENCIES.get(value.strip().lower())
    if not item:
        raise SystemExit("更新频率只能是 daily、weekly、monthly、yearly 或 rotate。")
    return item[0]


def limit_text(text: str, region: str, label: str) -> str:
    cleaned = text.strip()
    if region == "xjp":
        too_long = len(cleaned.split()) > 200
        rule = "200 个单词"
    else:
        too_long = len(cleaned) > 200
        rule = "200 个字"
    if too_long:
        raise SystemExit(f"{label}不能超过 {rule}。")
    return cleaned


def album_row(row: dict) -> dict:
    return {
        "albumId": str(row.get("albumId") or row.get("id") or ""),
        "name": row.get("albumName") or row.get("name") or "",
        "desc": row.get("desc") or row.get("albumDesc") or "",
        "frequency": frequency_label(_as_int(row.get("refreshRate"))),
    }


def find_album(rows: list[dict], album_id: str) -> dict:
    for row in rows:
        if str(row.get("albumId") or row.get("id") or "") == str(album_id):
            return row
    raise SystemExit(f"没有找到合辑 {album_id}。先执行 creator album list 看这台账号下的合辑。")


def work_summary(row: dict, group_id: str) -> dict:
    albums = row.get("albums") if isinstance(row.get("albums"), list) else []
    names = [item.get("albumName") for item in albums if isinstance(item, dict) and item.get("albumName")]
    return {
        "groupId": str(row.get("groupId") or row.get("imageId") or group_id),
        "content": (row.get("content") or row.get("desc") or row.get("description") or "").strip(),
        "album": row.get("albumName") or "、".join(names),
    }


def _cover_match(sizes: list[dict]) -> tuple[int, str, int] | None:
    for size_type, work_type in COVER_CANDIDATES:
        for item in sizes:
            filename = str(item.get("imageFilename") or "").strip()
            if item.get("imageSizeType") == size_type and filename:
                return size_type, filename, work_type
    return None


def annotate_size_rows(sizes: list[dict]) -> list[dict]:
    match = _cover_match(sizes)
    cover_type = match[0] if match else None
    cover_name = match[1] if match else ""
    rows: list[dict] = []
    for item in sizes:
        row = dict(item)
        filename = str(item.get("imageFilename") or "").strip()
        row["isCover"] = bool(
            cover_type is not None
            and item.get("imageSizeType") == cover_type
            and filename
            and filename == cover_name
        )
        rows.append(row)
    return rows


def work_info_missing(info: dict, group_id: str) -> bool:
    if not isinstance(info, dict) or not info:
        return True
    if any(info.get(key) not in (None, "", [], {}) for key in ("content", "albums", "startTime", "endTime", "coverUrl")):
        return False
    gid = str(info.get("groupId") or info.get("imageGroupId") or info.get("imageId") or "").strip()
    return not gid or gid != str(group_id)


def pick_cover(sizes: list[dict]) -> dict:
    match = _cover_match(sizes)
    if not match:
        raise SystemExit("没有读到这件作品的封面，暂时不能只改文字。请到创作者后台里修改图片。")
    size_type, filename, work_type = match
    for item in sizes:
        if item.get("imageSizeType") == size_type and str(item.get("imageFilename") or "").strip() == filename:
            return {
                "filename": filename,
                "width": item.get("imageWidth") or 0,
                "height": item.get("imageHeight") or 0,
                "workType": work_type,
            }
    raise SystemExit("没有读到这件作品的封面，暂时不能只改文字。请到创作者后台里修改图片。")


def work_update_body(info: dict, cover: dict, group_id: str, content: str, album_ids: str, immediate: bool, start: int | None, end: int | None) -> dict:
    body = {
        "groupId": group_id,
        "pStatus": 2,
        "albumIds": album_ids,
        "content": content,
        "coverFileName": cover["filename"],
        "coverW": cover["width"],
        "coverH": cover["height"],
        "workType": cover["workType"],
        "subTitle": "查看更多",
        "deepLink": "",
        "skipUrl": "",
        "skipType": 0,
        "isVideo": False,
        "syncImageStorage": False,
    }
    if immediate:
        body["startTime"] = None
        body["endTime"] = None
    elif start is not None or end is not None:
        body["startTime"] = start if start is not None else info.get("startTime")
        body["endTime"] = end if end is not None else info.get("endTime")
    else:
        if info.get("startTime") is not None:
            body["startTime"] = info.get("startTime")
        if info.get("endTime") is not None:
            body["endTime"] = info.get("endTime")
    return body


def album_ids_from_info(info: dict) -> str:
    albums = info.get("albums") if isinstance(info.get("albums"), list) else []
    ids = [str(item.get("albumId")) for item in albums if isinstance(item, dict) and item.get("albumId")]
    return ",".join(ids)


def schedule_ms(date_text: str) -> int:
    start, _end = schedule_day_bounds(date_text)
    return start


def schedule_day_bounds(date_text: str) -> tuple[int, int]:
    """上海时区：排期当天 00:00:00 至 23:59:59（毫秒时间戳）。"""
    from datetime import datetime, time
    from zoneinfo import ZoneInfo

    shanghai = ZoneInfo("Asia/Shanghai")
    day = datetime.strptime(date_text.strip(), "%Y-%m-%d").date()
    start = datetime.combine(day, time(0, 0, 0), tzinfo=shanghai)
    end = datetime.combine(day, time(23, 59, 59), tzinfo=shanghai)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def creator_row(body: dict) -> dict:
    page_type = str(body.get("pageType") or "").strip()
    homepage = str(body.get("homepage") or "").strip()
    if not page_type and not homepage:
        raw = str(body.get("homePage") or "").strip()
        if "---" in raw:
            page_type, homepage = raw.split("---", 1)
    return {
        "name": body.get("name") or body.get("userName") or "",
        "description": (body.get("description") or body.get("userSign") or "").strip(),
        "avatarUrl": body.get("url") or body.get("userUrl") or "",
        "socialPlatform": page_type,
        "socialUrl": homepage,
    }


def social_change(platform: str | None, url: str | None, clear: bool) -> tuple[str, str]:
    if clear:
        return "", ""
    if not platform and not url:
        return "", ""
    if (platform and not url) or (url and not platform):
        raise SystemExit("社交链接要同时提供平台和地址。平台可以是 xiaohongshu、weibo、instagram、facebook、x。")
    if platform not in SOCIALS or not url:
        raise SystemExit("社交链接要同时提供平台和地址。平台可以是 xiaohongshu、weibo、instagram、facebook、x。")
    if not url.startswith("https://"):
        raise SystemExit("社交链接需要以 https:// 开头。")
    return platform, url
