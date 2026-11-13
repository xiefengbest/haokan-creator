import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image

from creator_publish.api import ensure_ok
from creator_publish.config import parse_phone
from creator_publish.crop import PlanError
from creator_publish.manifest import Work, load_csv, load_inbox, parse_time
from creator_publish.pipeline import release_body, run
from creator_publish.sign import build_header, canonical_body, dumps, make_sign
from creator_publish.images import plan_work


class SignTest(unittest.TestCase):
    def test_body_json_matches_frontend(self):
        body = {"b": 1, "a": "查看更多", "ok": False, "r": 0.562, "n": "", "nest": {"z": 1, "a": 2}}
        text = dumps(canonical_body(body))
        node = subprocess.check_output(
            [
                "node",
                "-e",
                """
                const body = {b:1, a:"查看更多", ok:false, r:0.562, n:"", nest:{z:1, a:2}};
                function sortByKey(obj) {
                  const sorted = {};
                  for (const key of Object.keys(obj).sort()) sorted[key] = obj[key];
                  return sorted;
                }
                process.stdout.write(JSON.stringify(sortByKey(body)));
                """,
            ],
            text=True,
        )
        self.assertEqual(text, node)

    def test_sign_matches_node_md5(self):
        body = {"subTitle": "查看更多", "isVideo": False, "pStatus": 1}
        message_id = "20261105160000123"
        time_stamp = "20261105160000"
        secret = "test-sign-key"
        signed = make_sign(message_id, time_stamp, body, secret)
        node = subprocess.check_output(
            [
                "node",
                "-e",
                f"""
                const crypto = require("crypto");
                const body = {{subTitle:"查看更多", isVideo:false, pStatus:1}};
                function sortByKey(obj) {{
                  const sorted = {{}};
                  for (const key of Object.keys(obj).sort()) sorted[key] = obj[key];
                  return sorted;
                }}
                const raw = "{message_id}" + "{time_stamp}" + "{secret}" + JSON.stringify(sortByKey(body));
                process.stdout.write(crypto.createHash("md5").update(raw).digest("hex"));
                """,
            ],
            text=True,
        )
        self.assertEqual(signed, node)
        header = build_header(
            body,
            "123",
            "token",
            "",
            now=datetime(2026, 11, 5, 16, 0, 0),
            message_id=message_id,
            secret=secret,
            company_id=1,
            client_type=1,
            api_version="1",
        )
        self.assertEqual(header["sign"], signed)
        self.assertEqual(header["timeStamp"], time_stamp)


class ApiShapeTest(unittest.TestCase):
    def test_success_can_include_msg(self):
        body = ensure_ok({"header": {}, "body": {"status": 0, "msg": "ok", "imageGroupId": "9"}}, "创建作品")
        self.assertEqual(body["imageGroupId"], "9")

    def test_business_error(self):
        from creator_publish.api import ApiError

        with self.assertRaises(ApiError):
            ensure_ok({"header": {"resCode": "1001"}, "body": {"status": 1, "err": "签名错误"}}, "创建作品")


class ManifestTest(unittest.TestCase):
    def test_phone(self):
        self.assertEqual(parse_phone("13800138000"), ("+86", "13800138000"))
        self.assertEqual(parse_phone("+86 138-0013-8000"), ("+86", "13800138000"))
        with self.assertRaises(ValueError):
            parse_phone("12345")

    def test_time(self):
        self.assertEqual(parse_time("1730000000000"), 1730000000000)
        self.assertEqual(parse_time("1730000000"), 1730000000000)
        parsed = parse_time("2026-11-05 10:00:00")
        self.assertIsInstance(parsed, int)
        with self.assertRaises(PlanError):
            parse_time("昨天")

    def test_folder_and_csv(self):
        root = Path(tempfile.mkdtemp())
        try:
            folder = root / "海边日落"
            folder.mkdir()
            Image.new("RGB", (900, 1600), (1, 2, 3)).save(folder / "a.jpg", quality=80)
            Image.new("RGB", (1600, 900), (3, 2, 1)).save(folder / "b.jpg", quality=80)
            (folder / "描述.txt").write_text("日落", encoding="utf-8")
            work = load_inbox(root)[0]
            self.assertEqual(work.portrait.name, "a.jpg")
            self.assertEqual(work.landscape.name, "b.jpg")
            self.assertEqual(work.content, "日落")

            swapped = root / "放反了"
            swapped.mkdir()
            Image.new("RGB", (1600, 900), (1, 1, 1)).save(swapped / "竖图.jpg", quality=80)
            Image.new("RGB", (900, 1600), (1, 1, 1)).save(swapped / "横图.jpg", quality=80)
            with self.assertRaises(PlanError):
                load_inbox(root / "放反了")

            numbered = root / "序号"
            numbered.mkdir()
            Image.new("RGB", (900, 1600), (1, 2, 3)).save(numbered / "2.jpg", quality=80)
            Image.new("RGB", (1600, 900), (3, 2, 1)).save(numbered / "2横.jpg", quality=80)
            Image.new("RGB", (800, 1400), (4, 5, 6)).save(numbered / "10.jpg", quality=80)
            Image.new("RGB", (1400, 800), (6, 5, 4)).save(numbered / "10横图.jpg", quality=80)
            pairs = load_inbox(numbered)
            self.assertEqual([item.title for item in pairs], ["第 2 张", "第 10 张"])
            self.assertEqual(pairs[0].landscape.name, "2横.jpg")
            self.assertEqual(pairs[1].landscape.name, "10横图.jpg")

            csv_path = root / "works.csv"
            portrait = root / "竖图.jpg"
            landscape = root / "横图.jpg"
            portrait.write_bytes(b"placeholder")
            landscape.write_bytes(b"placeholder")
            csv_path.write_text(
                "竖图,横图,描述,开始时间\n竖图.jpg,横图.jpg,海边,2026-11-05 10:00:00\n",
                encoding="utf-8",
            )
            loaded = load_csv(csv_path)[0]
            self.assertEqual(loaded.content, "海边")
            self.assertIsNotNone(loaded.start_time)
        finally:
            shutil.rmtree(root)


class PlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(tempfile.mkdtemp())
        cls.folder = cls.root / "海边日落"
        cls.folder.mkdir()
        Image.new("RGB", (2160, 3840), (12, 40, 80)).save(cls.folder / "竖图.jpg", quality=75)
        Image.new("RGB", (3840, 2400), (80, 40, 12)).save(cls.folder / "横图.jpg", quality=75)
        (cls.folder / "描述.txt").write_text("海边日落", encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root)

    def test_two_images_cover_all_ratios(self):
        work = load_inbox(self.root)[0]
        plan = plan_work(work, "portrait")
        self.assertEqual(plan.square_generated_from, "portrait")
        self.assertEqual(len(plan.portrait.items), 7)
        self.assertEqual(len(plan.landscape.items), 6)
        self.assertEqual(len(plan.square.items), 3)
        by_ratio = {item.resolution: item for item in plan.portrait.crop_items()}
        self.assertEqual((by_ratio["9:16"].width, by_ratio["9:16"].height), (2160, 3840))
        self.assertEqual((by_ratio["9:21"].width, by_ratio["9:21"].height), (1080, 2520))
        self.assertNotIn("resize", by_ratio["9:16"].process)
        square = plan.square.crop_items()[0]
        self.assertEqual((square.width, square.height), (2160, 2160))
        self.assertIn("从竖图正中间裁出", plan_text(plan))
        plan.cover.oss_key = "release/image/cover.jpg"
        body = release_body(plan, "214231")
        self.assertEqual(body["albumIds"], "214231")
        self.assertEqual(body["workType"], 2)
        self.assertEqual(body["subTitle"], "查看更多")
        self.assertEqual(body["content"], "海边日落")
        self.assertFalse(body["isVideo"])

    def test_too_small(self):
        work = Work("小图", self.folder / "竖图.jpg", self.folder / "横图.jpg", None, "x" * 101, None, None)
        with self.assertRaises(PlanError):
            plan_work(work, "portrait")

    def test_dry_run_command(self):
        self.assertEqual(run(["--inbox", str(self.root)]), 0)


def plan_text(plan) -> str:
    from creator_publish.images import describe_plan

    return describe_plan(plan)


if __name__ == "__main__":
    unittest.main()
