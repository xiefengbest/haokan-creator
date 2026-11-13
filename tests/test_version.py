import importlib
import unittest
from pathlib import Path
from unittest import mock


class VersionTests(unittest.TestCase):
    def test_reads_installed_metadata_first(self):
        with mock.patch("importlib.metadata.version", return_value="9.9.9"):
            import creator_publish

            importlib.reload(creator_publish)
            self.assertEqual(creator_publish.__version__, "9.9.9")
        import creator_publish

        importlib.reload(creator_publish)

    def test_falls_back_to_pyproject_in_source_tree(self):
        import creator_publish

        root = Path(creator_publish.__file__).resolve().parents[1]
        with mock.patch("importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError("x")):
            importlib.reload(creator_publish)
            self.assertEqual(creator_publish.__version__, creator_publish._version_from_pyproject())
        importlib.reload(creator_publish)


if __name__ == "__main__":
    unittest.main()
