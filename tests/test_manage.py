import unittest

from creator_publish.manage import (
    creator_row,
    parse_frequency,
    schedule_day_bounds,
    schedule_ms,
    social_change,
    work_update_body,
)


class ManageTests(unittest.TestCase):
    def test_parse_frequency(self):
        self.assertEqual(parse_frequency("daily"), 1)
        with self.assertRaises(SystemExit):
            parse_frequency("hourly")

    def test_schedule_ms(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo

        expected = int(datetime(2026, 7, 13, tzinfo=ZoneInfo("Asia/Shanghai")).timestamp() * 1000)
        self.assertEqual(schedule_ms("2026-07-13"), expected)

    def test_schedule_day_bounds(self):
        start, end = schedule_day_bounds("2026-11-13")
        from datetime import datetime
        from zoneinfo import ZoneInfo

        shanghai = ZoneInfo("Asia/Shanghai")
        self.assertEqual(datetime.fromtimestamp(start / 1000, shanghai).strftime("%Y-%m-%d %H:%M:%S"), "2026-11-13 00:00:00")
        self.assertEqual(datetime.fromtimestamp(end / 1000, shanghai).strftime("%Y-%m-%d %H:%M:%S"), "2026-11-13 23:59:59")

    def test_creator_row_parses_homepage(self):
        row = creator_row({"name": "甲", "description": "简介", "homePage": "xiaohongshu---https://example.com/a"})
        self.assertEqual(row["socialPlatform"], "xiaohongshu")
        self.assertEqual(row["socialUrl"], "https://example.com/a")

    def test_work_update_body_immediate(self):
        body = work_update_body(
            {"startTime": 1, "endTime": 2},
            {"filename": "cover.jpg", "width": 1, "height": 2, "workType": 2},
            "9",
            "海边",
            "1",
            True,
            None,
            None,
        )
        self.assertIsNone(body["startTime"])
        self.assertIsNone(body["endTime"])

    def test_social_change_requires_pair(self):
        with self.assertRaises(SystemExit):
            social_change("xiaohongshu", None, False)


if __name__ == "__main__":
    unittest.main()
