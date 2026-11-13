"""作品清单：CSV，或资料目录里每个子文件夹一件作品。"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from creator_publish.crop import PlanError

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
SLOT_NAMES = {
    "portrait": ("竖图", "竖", "portrait", "vertical"),
    "landscape": ("横图", "横", "landscape", "horizontal"),
    "square": ("方图", "方", "square"),
}
COLUMN_ALIASES = {
    "portrait": ("portrait", "竖图", "竖图路径"),
    "landscape": ("landscape", "横图", "横图路径"),
    "square": ("square", "方图", "方图路径"),
    "content": ("content", "描述", "文案"),
    "start_time": ("start_time", "starttime", "开始时间"),
    "end_time": ("end_time", "endtime", "结束时间"),
}
SHANGHAI = ZoneInfo("Asia/Shanghai")


@dataclass
class Work:
    title: str
    portrait: Path
    landscape: Path
    square: Path | None
    content: str
    start_time: int | None
    end_time: int | None


def parse_time(value: str) -> int | None:
    text = value.strip()
    if not text:
        return None
    if re.fullmatch(r"\d{13}", text):
        return int(text)
    if re.fullmatch(r"\d{10}", text):
        return int(text) * 1000
    try:
        moment = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise PlanError("时间格式应为毫秒时间戳，或 2026-11-05 10:00:00") from exc
    return int(moment.replace(tzinfo=SHANGHAI).timestamp() * 1000)


def _numbered_role(path: Path) -> tuple[int, str] | None:
    stem = path.stem
    if re.fullmatch(r"\d+", stem):
        return int(stem), "portrait"
    landscape = re.fullmatch(r"(\d+)横图?", stem)
    if landscape:
        return int(landscape.group(1)), "landscape"
    square = re.fullmatch(r"(\d+)方图?", stem)
    if square:
        return int(square.group(1)), "square"
    return None


def _require_orientation(label: str, portrait: Path, landscape: Path) -> None:
    portrait_width, portrait_height = _size(portrait)
    landscape_width, landscape_height = _size(landscape)
    if portrait_height <= portrait_width:
        raise PlanError(f"{label} 的竖图宽大于或等于高，请换一张竖向图片")
    if landscape_width <= landscape_height:
        raise PlanError(f"{label} 的横图高大于或等于宽，请换一张横向图片")


def _works_from_numbered_files(directory: Path) -> list[Work] | None:
    """同一层目录里的 1.jpg + 1横图.jpg（或 1横.jpg）视为多件作品。"""
    images = _images_in(directory)
    if len(images) < 2:
        return None
    groups: dict[int, dict[str, Path]] = {}
    for path in images:
        parsed = _numbered_role(path)
        if parsed is None:
            return None
        number, role = parsed
        slots = groups.setdefault(number, {})
        if role in slots:
            label = {"portrait": "竖图", "landscape": "横图", "square": "方图"}[role]
            raise PlanError(f"第 {number} 张有重复的{label}：{slots[role].name}、{path.name}")
        slots[role] = path
    works: list[Work] = []
    for number in sorted(groups):
        slots = groups[number]
        if "portrait" not in slots or "landscape" not in slots:
            raise PlanError(f"第 {number} 张需要同时有竖图和横图")
        label = f"第 {number} 张"
        _require_orientation(label, slots["portrait"], slots["landscape"])
        works.append(
            Work(
                title=label,
                portrait=slots["portrait"],
                landscape=slots["landscape"],
                square=slots.get("square"),
                content=_read_content(directory) if len(groups) == 1 else "",
                start_time=None,
                end_time=None,
            )
        )
    return works


def _named_slot(path: Path) -> str | None:
    stem = path.stem.lower()
    for slot, names in SLOT_NAMES.items():
        for name in names:
            if stem == name or stem.startswith(name):
                return slot
    return None


def _images_in(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES and not path.name.startswith(".")
    )


def _read_content(directory: Path) -> str:
    for name in ("描述.txt", "文案.txt", "content.txt"):
        path = directory / name
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    return ""


def work_from_dir(directory: Path) -> Work:
    images = _images_in(directory)
    if not images:
        raise PlanError(f"{directory.name} 里没有 jpg、png 或 webp")
    assigned: dict[str, Path] = {}
    rest: list[Path] = []
    for path in images:
        slot = _named_slot(path)
        if slot and slot not in assigned:
            assigned[slot] = path
        else:
            rest.append(path)
    missing = [slot for slot in ("portrait", "landscape") if slot not in assigned]
    if rest and missing:
        if len(rest) == 1 and len(missing) == 1:
            assigned[missing[0]] = rest[0]
            rest = []
        elif set(missing) == {"portrait", "landscape"} and len(rest) >= 2:
            sized = [(path, _size(path)) for path in rest]
            sized.sort(key=lambda item: item[1][0] / item[1][1])
            assigned["portrait"] = sized[0][0]
            assigned["landscape"] = sized[-1][0]
            rest = [path for path, _ in sized[1:-1]]
            if assigned["portrait"] == assigned["landscape"]:
                raise PlanError(f"{directory.name} 里的图方向一样，请分别命名为竖图、横图")
    if rest:
        names = "、".join(path.name for path in rest)
        raise PlanError(f"{directory.name} 有多余图片：{names}。方图可以不放，文件名请用竖图、横图")
    if "portrait" not in assigned or "landscape" not in assigned:
        raise PlanError(f"{directory.name} 需要一张竖图和一张横图")
    _require_orientation(directory.name, assigned["portrait"], assigned["landscape"])
    return Work(
        title=directory.name,
        portrait=assigned["portrait"],
        landscape=assigned["landscape"],
        square=assigned.get("square"),
        content=_read_content(directory),
        start_time=None,
        end_time=None,
    )


def _size(path: Path) -> tuple[int, int]:
    from PIL import Image, ImageOps

    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        return image.size


def load_inbox(inbox: Path) -> list[Work]:
    if not inbox.is_dir():
        raise PlanError(f"找不到资料目录：{inbox}")
    folders = sorted(
        path for path in inbox.iterdir() if path.is_dir() and not path.name.startswith(".")
    )
    if folders:
        return [work_from_dir(path) for path in folders]
    numbered = _works_from_numbered_files(inbox)
    if numbered is not None:
        return numbered
    images = _images_in(inbox)
    if not images:
        return []
    return [work_from_dir(inbox)]


def _pick(row: dict[str, str], field: str) -> str:
    for alias in COLUMN_ALIASES[field]:
        for key, value in row.items():
            if key and key.strip().lower() == alias:
                return (value or "").strip()
    return ""


def load_csv(path: Path) -> list[Work]:
    works: list[Work] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise PlanError(f"{path.name} 没有表头")
        for index, row in enumerate(reader, start=2):
            if not row or not any((value or "").strip() for value in row.values()):
                continue
            portrait = _resolve(_pick(row, "portrait"), path.parent, index, "竖图")
            landscape = _resolve(_pick(row, "landscape"), path.parent, index, "横图")
            square_raw = _pick(row, "square")
            square = _resolve(square_raw, path.parent, index, "方图") if square_raw else None
            content = _pick(row, "content")
            title = content[:20] if content else portrait.stem
            try:
                start = parse_time(_pick(row, "start_time"))
                end = parse_time(_pick(row, "end_time"))
            except PlanError as exc:
                raise PlanError(f"{path.name} 第 {index} 行：{exc}") from exc
            works.append(
                Work(
                    title=title,
                    portrait=portrait,
                    landscape=landscape,
                    square=square,
                    content=content,
                    start_time=start,
                    end_time=end,
                )
            )
    return works


def _resolve(raw: str, base: Path, index: int, label: str) -> Path:
    if not raw:
        raise PlanError(f"第 {index} 行缺少{label}")
    path = Path(raw)
    if not path.is_absolute():
        path = (base / path).resolve()
    if not path.is_file():
        raise PlanError(f"第 {index} 行找不到{label}：{path}")
    return path
