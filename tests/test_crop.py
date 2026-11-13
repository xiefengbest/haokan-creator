import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from creator_publish.crop import (
    LANDSCAPE_PRESETS,
    PORTRAIT_PRESETS,
    Preset,
    center_crop,
    image_crop_payload,
    image_ratio,
    oss_crop_process,
    FULL_AREA,
)
from creator_publish.oss_store import parse_image_info
from creator_publish.sign import dumps


class CropMathTest(unittest.TestCase):
    def test_portrait_presets(self):
        expected = {
            "9:21": (257, 0, 1646, 3840, 1080, 2520),
            "9:20": (216, 0, 1728, 3840, 1080, 2400),
            "9:19.5": (194, 0, 1772, 3840, 1179, 2556),
            "3:4": (0, 480, 2160, 2880, 1620, 2160),
            "9:16": (0, 0, 2160, 3840, 2160, 3840),
        }
        for preset in PORTRAIT_PRESETS:
            box = center_crop(2160, 3840, preset)
            self.assertEqual(
                (box.x, box.y, box.width, box.height, box.out_width, box.out_height),
                expected[preset.label],
            )

    def test_landscape_presets(self):
        expected = {
            "21:9": (0, 377, 3840, 1646, 3440, 1475),
            "16:9": (0, 120, 3840, 2160, 3840, 2160),
            "16:10": (0, 0, 3840, 2400, 3840, 2400),
            "4:3": (320, 0, 3200, 2400, 2160, 1620),
        }
        for preset in LANDSCAPE_PRESETS:
            box = center_crop(3840, 2400, preset)
            self.assertEqual(
                (box.x, box.y, box.width, box.height, box.out_width, box.out_height),
                expected[preset.label],
            )

    def test_exact_ratio_is_not_resized(self):
        box = center_crop(2160, 3840, Preset("9:16", 9, 16, 3840))
        self.assertEqual(oss_crop_process(box), "image/crop,w_2160,h_3840,x_0,y_0,r_1")

    def test_long_edge_adds_resize(self):
        box = center_crop(2160, 3840, Preset("9:21", 9, 21, 2520))
        self.assertIn("/resize,m_lfit,w_1080,h_2520", oss_crop_process(box))

    def test_ratio_matches_example(self):
        self.assertEqual(image_ratio(2160, 3840), 0.562)

    def test_full_crop_json_uses_integers(self):
        text = dumps(image_crop_payload(FULL_AREA, True))
        self.assertIn('"width":100', text)
        self.assertIn('"singleReplaced":true', text)

    def test_small_portrait_fails_short_edge(self):
        from creator_publish.crop import short_edge_problems

        problems = short_edge_problems(1200, 2000, "portrait")
        self.assertTrue(problems)

    def test_image_info(self):
        width, height = parse_image_info(
            {"ImageWidth": {"value": "2160"}, "ImageHeight": {"value": "3840"}}
        )
        self.assertEqual((width, height), (2160, 3840))


if __name__ == "__main__":
    unittest.main()
