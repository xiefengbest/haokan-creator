"""居中裁切。像素取整与 JS Math.round 一致（半数向上）。"""

from __future__ import annotations

import math
from dataclasses import dataclass


MIN_SHORT_EDGE = 1080
COMPRESS_BYTES = 10 * 1024 * 1024
MAX_BYTES = 15 * 1024 * 1024
COMPRESS_LONG_EDGE = 3000

SIZE_TYPES = {
    "portrait": {"raw": 7, "compress": 9, "crop": 2},
    "landscape": {"raw": 6, "compress": 8, "crop": 3},
    "square": {"raw": 10, "compress": 11, "crop": 4},
}

COVER_PRESET = {"portrait": "9:16", "landscape": "16:9", "square": "1:1"}


@dataclass(frozen=True)
class Preset:
    label: str
    width_units: float
    height_units: float
    max_long_edge: int


PORTRAIT_PRESETS = (
    Preset("9:21", 9, 21, 2520),
    Preset("9:20", 9, 20, 2400),
    Preset("9:19.5", 9, 19.5, 2556),
    Preset("3:4", 3, 4, 2160),
    Preset("9:16", 9, 16, 3840),
)
LANDSCAPE_PRESETS = (
    Preset("21:9", 21, 9, 3440),
    Preset("16:9", 16, 9, 3840),
    Preset("16:10", 16, 10, 3840),
    Preset("4:3", 4, 3, 2160),
)
SQUARE_PRESETS = (Preset("1:1", 1, 1, 3840),)

PRESETS = {
    "portrait": PORTRAIT_PRESETS,
    "landscape": LANDSCAPE_PRESETS,
    "square": SQUARE_PRESETS,
}

FULL_AREA = {"x": 0, "y": 0, "width": 100, "height": 100}


class PlanError(Exception):
    pass


def round_half_up(value: float) -> int:
    if value >= 0:
        return int(math.floor(value + 0.5))
    return int(math.ceil(value - 0.5))


def fitted_size(width: int, height: int, max_long: int) -> tuple[int, int]:
    long_edge = max(width, height)
    if long_edge <= max_long:
        return width, height
    if width >= height:
        return max_long, max(1, round_half_up(height * max_long / width))
    return max(1, round_half_up(width * max_long / height)), max_long


@dataclass(frozen=True)
class CropBox:
    x: int
    y: int
    width: int
    height: int
    out_width: int
    out_height: int

    @property
    def short_edge(self) -> int:
        return min(self.out_width, self.out_height)


def center_crop(src_width: int, src_height: int, preset: Preset) -> CropBox:
    if src_width <= 0 or src_height <= 0:
        raise PlanError("图片宽高无效")
    target = preset.width_units / preset.height_units
    source = src_width / src_height
    if source > target:
        crop_height = src_height
        crop_width = min(
            src_width,
            max(1, round_half_up(src_height * preset.width_units / preset.height_units)),
        )
        x = (src_width - crop_width) // 2
        y = 0
    else:
        crop_width = src_width
        crop_height = min(
            src_height,
            max(1, round_half_up(src_width * preset.height_units / preset.width_units)),
        )
        x = 0
        y = (src_height - crop_height) // 2
    out_width, out_height = fitted_size(crop_width, crop_height, preset.max_long_edge)
    return CropBox(x, y, crop_width, crop_height, out_width, out_height)


def crops_for(src_width: int, src_height: int, slot: str) -> list[tuple[Preset, CropBox]]:
    return [(preset, center_crop(src_width, src_height, preset)) for preset in PRESETS[slot]]


def short_edge_problems(src_width: int, src_height: int, slot: str) -> list[str]:
    problems = []
    for preset, box in crops_for(src_width, src_height, slot):
        if box.short_edge < MIN_SHORT_EDGE:
            problems.append(f"{preset.label} 窄边 {box.short_edge}")
    return problems


def json_number(value: float):
    rounded = round(float(value), 4)
    if abs(rounded - round(rounded)) < 1e-9:
        return int(round(rounded))
    return rounded


def crop_area(box: CropBox, src_width: int, src_height: int) -> dict:
    return {
        "x": json_number(box.x / src_width * 100),
        "y": json_number(box.y / src_height * 100),
        "width": json_number(box.width / src_width * 100),
        "height": json_number(box.height / src_height * 100),
    }


def image_crop_payload(area: dict, single_replaced: bool) -> dict:
    return {
        "crop": {"x": 0, "y": 0},
        "croppedArea": {
            "x": area["x"],
            "y": area["y"],
            "width": area["width"],
            "height": area["height"],
        },
        "zoom": 1,
        "singleReplaced": single_replaced,
    }


def oss_crop_process(box: CropBox) -> str:
    process = f"image/crop,w_{box.width},h_{box.height},x_{box.x},y_{box.y},r_1"
    if (box.out_width, box.out_height) != (box.width, box.height):
        process += f"/resize,m_lfit,w_{box.out_width},h_{box.out_height}"
    return process


def image_ratio(width: int, height: int) -> float:
    if height <= 0:
        raise PlanError("图片高度无效")
    return float(f"{width / height:.3f}")


def square_side_box(width: int, height: int) -> tuple[int, int, int]:
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return left, top, side
