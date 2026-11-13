import os
import stat
import tempfile
import unittest
from pathlib import Path

from creator_publish.config_cmd import import_backend, inspect_backend


class ConfigCmdTests(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        os.environ["HAOKAN_CREATOR_HOME"] = self.home.name

    def tearDown(self):
        os.environ.pop("HAOKAN_CREATOR_HOME", None)
        self.home.cleanup()

    def test_status_when_missing(self):
        payload = inspect_backend()
        self.assertFalse(payload["ready"])
        self.assertFalse(payload["backendEnvExists"])
        self.assertIn("CREATOR_SIGN_KEY", payload["missingKeys"])

    def test_import_writes_backend_env(self):
        source = Path(self.home.name) / "from-xiefeng.env"
        source.write_text("CREATOR_SIGN_KEY=test-sign\n", encoding="utf-8")
        target = import_backend(source)
        self.assertTrue(target.is_file())
        mode = stat.S_IMODE(target.stat().st_mode)
        self.assertEqual(mode & 0o077, 0)
        text = target.read_text(encoding="utf-8")
        self.assertIn("CREATOR_SIGN_KEY=test-sign", text)
        self.assertNotIn("CREATOR_CN_API", text)
        payload = inspect_backend()
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["missingKeys"], [])

    def test_import_rejects_incomplete_file(self):
        source = Path(self.home.name) / "bad.env"
        source.write_text("CREATOR_REGION=cn\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            import_backend(source)


if __name__ == "__main__":
    unittest.main()
