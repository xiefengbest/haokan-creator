import os
import stat
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from creator_publish.manifest import Work
from creator_publish.pipeline import schedule_daily
from creator_publish.profiles import add_profile, list_profiles, resolve_profile


class ScheduleTest(unittest.TestCase):
    def test_one_image_per_day(self):
        works = [
            Work("第 1 张", Path("a.jpg"), Path("b.jpg"), None, "", None, None),
            Work("第 2 张", Path("c.jpg"), Path("d.jpg"), None, "", None, None),
        ]
        scheduled = schedule_daily(works, "2026-07-13")
        shanghai = ZoneInfo("Asia/Shanghai")
        first = datetime.fromtimestamp(scheduled[0].start_time / 1000, shanghai)
        second = datetime.fromtimestamp(scheduled[1].start_time / 1000, shanghai)
        self.assertEqual(first.strftime("%Y-%m-%d %H:%M"), "2026-07-13 00:00")
        self.assertEqual(second.strftime("%Y-%m-%d %H:%M"), "2026-07-14 00:00")


class ProfileTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        os.environ["HAOKAN_CREATOR_HOME"] = self.home.name

    def tearDown(self):
        os.environ.pop("HAOKAN_CREATOR_HOME", None)
        self.home.cleanup()

    def test_add_and_resolve_without_printing_password(self):
        add_profile("测试账号", "13800138000", "secret-value", "cn")
        listed = list_profiles()
        self.assertEqual(listed[0]["name"], "测试账号")
        self.assertNotIn("secret-value", str(listed))
        resolved = resolve_profile(None)
        self.assertEqual(resolved["password"], "secret-value")
        mode = os.stat(Path(self.home.name) / "profiles.json").st_mode
        self.assertEqual(stat.S_IMODE(mode) & 0o077, 0)


if __name__ == "__main__":
    unittest.main()
