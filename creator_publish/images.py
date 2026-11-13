"""读图、压图、生成方图，并算出每个槽位要登记的尺寸。"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from creator_publish.crop import (
    COMPRESS_BYTES,
    COMPRESS_LONG_EDGE,
    COVER_PRESET,
    FULL_AREA,
    MAX_BYTES,
    MIN_SHORT_EDGE,
    SIZE_TYPES,
    PlanError,
    crop_area,
    crops_for,
    fitted_size,
    image_crop_payload,
    image_ratio,
    oss_crop_process,
    short_edge_problems,
    square_side_box,
)
from creator_publish.manifest import Work
from creator_publish.sign import dumps

SLOT_LABELS = {"portrait": "竖图", "landscape": "横图", "square": "方图"}
CONTENT_TYPES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


@dataclass
class PlannedItem:
    role: str
    resolution: str
    size_type: int
    width: int
    height: int
    image_crop: dict
    process: str | None = None
    oss_key: str = ""

    def list_entry(self) -> dict:
        if not self.oss_key:
            raise PlanError("图片还没有上传路径")
        return {
            "action": 1,
            "imageResolution": self.resolution,
            "imageRatio": image_ratio(self.width, self.height),
            "imageWidth": self.width,
            "imageHeight": self.height,
            "imageFilename": self.oss_key,
            "imageSizeType": self.size_type,
            "imageCrop": dumps(self.image_crop),
        }


@dataclass
class SlotPlan:
    slot: str
    width: int
    height: int
    crop_width: int
    crop_height: int
    ext: str
    source_path: Path | None
    body: bytes | None
    compress_body: bytes | None
    shares_raw_key: bool
    generated_from: str | None
    items: list[PlannedItem] = field(default_factory=list)

    @property
    def raw_item(self) -> PlannedItem:
        return self.items[0]

    @property
    def compress_item(self) -> PlannedItem:
        return self.items[1]

    def crop_items(self) -> list[PlannedItem]:
        return [item for item in self.items if item.role == "crop"]


@dataclass
class WorkPlan:
    work: Work
    portrait: SlotPlan
    landscape: SlotPlan
    square: SlotPlan
    square_generated_from: str | None
    cover: PlannedItem

    def slots(self) -> list[SlotPlan]:
        return [self.portrait, self.landscape, self.square]


def encode_jpeg(image: Image.Image, quality: int = 95) -> bytes:
    rgb = image.convert("RGB")
    buffer = BytesIO()
    rgb.save(buffer, format="JPEG", quality=quality, subsampling=0, optimize=True)
    return buffer.getvalue()


def _open_display(path: Path) -> Image.Image:
    image = Image.open(path)
    image = ImageOps.exif_transpose(image)
    image.load()
    return image


def load_original(path: Path) -> tuple[int, int, str, bytes | None, int]:
    if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise PlanError(f"{path.name} 不是 jpg、png 或 webp")
    file_size = path.stat().st_size
    if file_size <= 0:
        raise PlanError(f"{path.name} 是空文件")
    if file_size > MAX_BYTES:
        raise PlanError(f"{path.name} 有 {file_size / 1024 / 1024:.1f} MB，单张不能超过 15 MB")
    try:
        image_cm = Image.open(path)
    except (OSError, UnidentifiedImageError) as exc:
        raise PlanError(f"无法读取图片 {path.name}") from exc
    with image_cm as image:
        orientation = image.getexif().get(274)
        mode = image.mode
        if orientation not in (None, 0, 1) or mode not in ("RGB", "L", "RGBA"):
            fixed = ImageOps.exif_transpose(image)
            body = _jpeg_within_limit(fixed, path.name)
            return fixed.size[0], fixed.size[1], "jpg", body, len(body)
        width, height = image.size
    ext = "jpg" if path.suffix.lower() in {".jpg", ".jpeg"} else path.suffix.lower().lstrip(".")
    return width, height, ext, None, file_size


def _jpeg_within_limit(image: Image.Image, name: str) -> bytes:
    body = encode_jpeg(image, 95)
    if len(body) <= MAX_BYTES:
        return body
    body = encode_jpeg(image, 85)
    if len(body) <= MAX_BYTES:
        return body
    raise PlanError(f"{name} 转成 JPEG 后仍超过 15 MB")


def render_square(path: Path | None, body: bytes | None) -> tuple[int, bytes]:
    image = _pixels(path, body)
    try:
        left, top, side = square_side_box(image.size[0], image.size[1])
        if side < MIN_SHORT_EDGE:
            raise PlanError(f"正中间的方图只有 {side}×{side}，窄边至少要 {MIN_SHORT_EDGE}")
        cropped = image.crop((left, top, left + side, top + side)).copy()
        return side, _jpeg_within_limit(cropped, "方图")
    finally:
        image.close()


def _pixels(path: Path | None, body: bytes | None) -> Image.Image:
    if body is not None:
        image = Image.open(BytesIO(body))
    elif path is not None:
        image = _open_display(path)
        return image
    else:
        raise PlanError("没有可读取的图片")
    image = ImageOps.exif_transpose(image)
    image.load()
    return image


def compress_image(path: Path | None, body: bytes | None) -> tuple[int, int, bytes]:
    image = _pixels(path, body)
    try:
        target = fitted_size(image.size[0], image.size[1], COMPRESS_LONG_EDGE)
        working = image.resize(target, Image.Resampling.LANCZOS) if image.size != target else image
        blob = encode_jpeg(working, 90)
        return working.size[0], working.size[1], blob
    finally:
        image.close()


def _slot_from_source(
    slot: str,
    width: int,
    height: int,
    ext: str,
    path: Path | None,
    body: bytes | None,
    file_size: int,
    generated_from: str | None,
) -> SlotPlan:
    crop_width, crop_height = width, height
    compress_body = None
    shares_raw_key = True
    if file_size >= COMPRESS_BYTES:
        crop_width, crop_height, compress_body = compress_image(path, body)
        shares_raw_key = False
    problems = [
        f"{SLOT_LABELS[slot]} {text}"
        for text in short_edge_problems(crop_width, crop_height, slot)
    ]
    if problems:
        raise PlanError("裁完窄边不足 1080：" + "；".join(problems))
    types = SIZE_TYPES[slot]
    raw = PlannedItem(
        role="raw",
        resolution="0",
        size_type=types["raw"],
        width=width,
        height=height,
        image_crop=image_crop_payload(FULL_AREA, True),
    )
    compress = PlannedItem(
        role="compress",
        resolution="0",
        size_type=types["compress"],
        width=crop_width,
        height=crop_height,
        image_crop=image_crop_payload(FULL_AREA, True),
    )
    crops = []
    for preset, box in crops_for(crop_width, crop_height, slot):
        crops.append(
            PlannedItem(
                role="crop",
                resolution=preset.label,
                size_type=types["crop"],
                width=box.out_width,
                height=box.out_height,
                image_crop=image_crop_payload(crop_area(box, crop_width, crop_height), False),
                process=oss_crop_process(box),
            )
        )
    return SlotPlan(
        slot=slot,
        width=width,
        height=height,
        crop_width=crop_width,
        crop_height=crop_height,
        ext=ext,
        source_path=path,
        body=body,
        compress_body=compress_body,
        shares_raw_key=shares_raw_key,
        generated_from=generated_from,
        items=[raw, compress, *crops],
    )


def plan_work(work: Work, square_from: str) -> WorkPlan:
    if len(work.content) > 100:
        raise PlanError(f"描述有 {len(work.content)} 字，最多 100 字")
    if work.start_time is not None and work.end_time is not None and work.start_time >= work.end_time:
        raise PlanError("预约结束时间要晚于开始时间")
    portrait = _plan_file("portrait", work.portrait)
    landscape = _plan_file("landscape", work.landscape)
    generated_from = None
    if work.square is not None:
        square = _plan_file("square", work.square)
    else:
        source = portrait if square_from == "portrait" else landscape
        side, blob = render_square(source.source_path, source.body)
        square = _slot_from_source("square", side, side, "jpg", None, blob, len(blob), square_from)
        generated_from = square_from
    cover = _cover_item(portrait)
    return WorkPlan(work, portrait, landscape, square, generated_from, cover)


def _plan_file(slot: str, path: Path) -> SlotPlan:
    width, height, ext, body, file_size = load_original(path)
    if slot == "portrait" and height <= width:
        raise PlanError(f"{path.name} 不是竖图")
    if slot == "landscape" and width <= height:
        raise PlanError(f"{path.name} 不是横图")
    return _slot_from_source(slot, width, height, ext, path, body, file_size, None)


def _cover_item(portrait: SlotPlan) -> PlannedItem:
    label = COVER_PRESET["portrait"]
    for item in portrait.crop_items():
        if item.resolution == label:
            return item
    raise PlanError("竖图缺少 9:16 封面")


def describe_plan(plan: WorkPlan) -> str:
    lines = [plan.work.title]
    if plan.work.content:
        lines.append(f"  描述：{plan.work.content}")
    for slot in plan.slots():
        origin = ""
        if slot.generated_from:
            origin = f"，从{SLOT_LABELS[slot.generated_from]}正中间裁出"
        compress = ""
        if not slot.shares_raw_key:
            compress = f"，原图超过 10 MB，裁切用压缩图 {slot.crop_width}×{slot.crop_height}"
        lines.append(f"  {SLOT_LABELS[slot.slot]} {slot.width}×{slot.height}{origin}{compress}")
        for item in slot.crop_items():
            lines.append(f"    {item.resolution} → {item.width}×{item.height}")
    lines.append(f"  封面：竖图 9:16，{plan.cover.width}×{plan.cover.height}")
    if plan.work.start_time is not None or plan.work.end_time is not None:
        lines.append(
            "  上线："
            + _format_schedule(plan.work.start_time)
            + " 至 "
            + _format_schedule(plan.work.end_time)
        )
    return "\n".join(lines)


def _format_schedule(millis: int | None) -> str:
    if millis is None:
        return "不限"
    from datetime import datetime
    from zoneinfo import ZoneInfo

    moment = datetime.fromtimestamp(millis / 1000, ZoneInfo("Asia/Shanghai"))
    if moment.hour == 23 and moment.minute == 59 and moment.second == 59:
        return moment.strftime("%Y-%m-%d %H:%M:%S")
    return moment.strftime("%Y-%m-%d %H:%M")


def read_upload_body(slot: SlotPlan) -> bytes:
    if slot.body is not None:
        return slot.body
    if slot.source_path is None:
        raise PlanError("没有可上传的原图")
    return slot.source_path.read_bytes()


def content_type_for(ext: str) -> str:
    return CONTENT_TYPES[ext]
