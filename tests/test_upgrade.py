import tempfile
import unittest
from pathlib import Path
from unittest import mock

from creator_publish.upgrade import upgrade_via_cdn, upgrade_via_github


class Completed:
    def __init__(self, code=0, stdout="", stderr=""):
        self.returncode = code
        self.stdout = stdout
        self.stderr = stderr


class UpgradeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_github_pull_success(self):
        (self.repo / ".git").mkdir()
        with mock.patch("subprocess.run", return_value=Completed(stdout="Already up to date.\n")):
            with mock.patch(
                "creator_publish.venv_install.install_repo_into_venv",
                return_value=(0, ""),
            ):
                ok, detail, via = upgrade_via_github(self.repo)
        self.assertTrue(ok)
        self.assertEqual(via, "github")

    def test_github_pull_failure(self):
        (self.repo / ".git").mkdir()
        with mock.patch(
            "subprocess.run",
            return_value=Completed(code=1, stderr="Could not resolve host"),
        ):
            ok, detail, via = upgrade_via_github(self.repo)
        self.assertFalse(ok)
        self.assertEqual(via, "github")

    def test_cdn_missing_script(self):
        ok, detail = upgrade_via_cdn(self.repo)
        self.assertFalse(ok)
        self.assertIn("install-from-cdn", detail)

    def test_cdn_runs_script(self):
        script = self.repo / "scripts"
        script.mkdir(parents=True)
        (script / "install-from-cdn.sh").write_text("#!/bin/bash\n", encoding="utf-8")
        with mock.patch("subprocess.run", return_value=Completed(stdout="ok\n")):
            ok, detail = upgrade_via_cdn(self.repo)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
