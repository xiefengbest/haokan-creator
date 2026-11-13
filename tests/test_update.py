import json
import tempfile
import unittest
from pathlib import Path

from creator_publish.update_check import sync_repo


class Completed:
    def __init__(self, code=0, stdout="", stderr=""):
        self.returncode = code
        self.stdout = stdout
        self.stderr = stderr


def scripted(replies):
    calls = []

    def run(cmd, **kwargs):
        name = " ".join(cmd[3:])
        calls.append(name)
        reply = replies[name]
        if isinstance(reply, list):
            return reply.pop(0)
        return reply

    return run, calls


class UpdateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        (self.repo / ".git").mkdir(parents=True)
        self.cache = Path(self.tmp.name) / "update-check.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_same_revision_does_not_pull(self):
        run, calls = scripted({
            "fetch origin main": Completed(),
            "rev-parse HEAD": Completed(stdout="abc\n"),
            "rev-parse origin/main": Completed(stdout="abc\n"),
        })
        self.assertEqual(sync_repo(self.repo, self.cache, allow_apply=True, now=10, runner=run), "current")
        self.assertNotIn("pull --ff-only", calls)

    def test_new_revision_pulls_when_allowed(self):
        run, calls = scripted({
            "fetch origin main": Completed(),
            "rev-parse HEAD": Completed(stdout="old\n"),
            "rev-parse origin/main": Completed(stdout="new\n"),
            "status --porcelain": Completed(stdout=""),
            "pull --ff-only": Completed(stdout="updated\n"),
        })
        self.assertEqual(sync_repo(self.repo, self.cache, allow_apply=True, now=10, runner=run), "updated")
        self.assertIn("pull --ff-only", calls)
        self.assertEqual(json.loads(self.cache.read_text())["state"], "current")

    def test_publish_does_not_pull(self):
        run, calls = scripted({
            "fetch origin main": Completed(),
            "rev-parse HEAD": Completed(stdout="old\n"),
            "rev-parse origin/main": Completed(stdout="new\n"),
        })
        self.assertEqual(sync_repo(self.repo, self.cache, allow_apply=False, now=10, runner=run), "pending")
        self.assertNotIn("pull --ff-only", calls)

    def test_local_edits_do_not_pull(self):
        run, calls = scripted({
            "fetch origin main": Completed(),
            "rev-parse HEAD": Completed(stdout="old\n"),
            "rev-parse origin/main": Completed(stdout="new\n"),
            "status --porcelain": Completed(stdout=" M README.md\n"),
        })
        self.assertEqual(sync_repo(self.repo, self.cache, allow_apply=True, now=10, runner=run), "pending")
        self.assertNotIn("pull --ff-only", calls)

    def test_fresh_current_skips_network(self):
        self.cache.write_text(json.dumps({"checked_at": 10, "state": "current"}))
        run, calls = scripted({})
        self.assertEqual(sync_repo(self.repo, self.cache, allow_apply=True, now=20, runner=run), "current")
        self.assertEqual(calls, [])

    def test_fetch_failure_does_not_block(self):
        run, calls = scripted({"fetch origin main": Completed(code=1, stderr="offline")})
        self.assertEqual(sync_repo(self.repo, self.cache, allow_apply=True, now=10, runner=run), "skipped")
        self.assertEqual(calls, ["fetch origin main"])


if __name__ == "__main__":
    unittest.main()
