import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from PIL import Image

from creator_publish.cli import main
from creator_publish.profiles import add_profile, list_profiles


class ConfirmTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        os.environ["HAOKAN_CREATOR_HOME"] = self.home.name
        os.environ["HAOKAN_CREATOR_SKIP_UPDATE"] = "1"
        self.stderr = io.StringIO()

    def tearDown(self):
        os.environ.pop("HAOKAN_CREATOR_HOME", None)
        os.environ.pop("HAOKAN_CREATOR_SKIP_UPDATE", None)
        self.home.cleanup()

    def test_profile_add_waits_for_confirmation(self):
        with redirect_stderr(self.stderr):
            code = main(["profile", "add", "--name", "甲", "--phone", "13800138000", "--password-stdin"])
        self.assertEqual(code, 10)
        self.assertEqual(list_profiles(), [])
        payload = json.loads(self.stderr.getvalue())
        self.assertEqual(payload["error"]["type"], "confirmation")
        self.assertEqual(payload["error"]["basic"]["name"], "甲")
        self.assertNotIn("secret", self.stderr.getvalue())

    def test_profile_add_saves_after_yes(self):
        stdin = sys_stdin("secret-value")
        with stdin, redirect_stderr(self.stderr):
            code = main(
                ["profile", "add", "--name", "甲", "--phone", "13800138000", "--password-stdin", "--yes"]
            )
        self.assertEqual(code, 0)
        self.assertEqual(list_profiles()[0]["name"], "甲")

    def test_publish_waits_without_uploading(self):
        add_profile("甲", "13800138000", "secret-value", "cn")
        folder = Path(self.home.name) / "pics"
        folder.mkdir()
        Image.new("RGB", (2160, 3840), (1, 2, 3)).save(folder / "1.jpg", quality=70)
        Image.new("RGB", (3840, 2400), (3, 2, 1)).save(folder / "1横.jpg", quality=70)
        with redirect_stderr(self.stderr):
            code = main(["--profile", "甲", "work", "+publish", "--dir", str(folder), "--album-id", "1"])
        self.assertEqual(code, 10)
        payload = json.loads(self.stderr.getvalue())
        self.assertEqual(payload["error"]["basic"]["albumId"], "1")
        self.assertEqual(payload["error"]["basic"]["creator"], "甲")


class sys_stdin:
    def __init__(self, text):
        self.text = text
        self.previous = None

    def __enter__(self):
        import sys

        self.previous = sys.stdin
        sys.stdin = io.StringIO(self.text)
        return sys.stdin

    def __exit__(self, exc_type, exc, tb):
        import sys

        sys.stdin = self.previous


if __name__ == "__main__":
    unittest.main()
