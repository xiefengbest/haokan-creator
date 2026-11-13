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
        source.write_text(
            "\n".join(
                [
                    "CREATOR_REGION=cn",
                    "CREATOR_SIGN_KEY=test",
                    "CREATOR_COMPANY_ID=1",
                    "CREATOR_CLIENT_TYPE=1",
                    "CREATOR_API_VERSION=1",
                    "CREATOR_STS_URL=https://example.com/token",
                    "CREATOR_CN_API=https://example.com",
                    "CREATOR_CN_OSS_RES=https://img.example.com/",
                    "CREATOR_CN_BUCKET=b",
                    "CREATOR_CN_ENDPOINT=https://oss.example.com",
                ]
            ),
            encoding="utf-8",
        )
        target = import_backend(source)
        self.assertTrue(target.is_file())
        mode = stat.S_IMODE(target.stat().st_mode)
        self.assertEqual(mode & 0o077, 0)
        payload = inspect_backend()
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["missingKeys"], [])

    def test_import_rejects_incomplete_file(self):
        source = Path(self.home.name) / "bad.env"
        source.write_text("CREATOR_SIGN_KEY=test\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            import_backend(source)


if __name__ == "__main__":
    unittest.main()
