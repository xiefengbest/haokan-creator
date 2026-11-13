import os
import tempfile
import unittest
from pathlib import Path

from creator_publish.config import load_env_files


class EnvLoadTests(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        os.environ["HAOKAN_CREATOR_HOME"] = self.home.name
        for key in list(os.environ):
            if key.startswith("CREATOR_"):
                os.environ.pop(key, None)

    def tearDown(self):
        os.environ.pop("HAOKAN_CREATOR_HOME", None)
        self.home.cleanup()

    def test_backend_env_is_loaded(self):
        path = Path(self.home.name) / "backend.env"
        path.write_text("CREATOR_REGION=xjp\n", encoding="utf-8")
        load_env_files()
        self.assertEqual(os.environ.get("CREATOR_REGION"), "xjp")


if __name__ == "__main__":
    unittest.main()
