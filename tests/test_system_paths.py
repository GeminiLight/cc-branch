import unittest
from pathlib import Path
from unittest.mock import patch

from cc_branch.application.system_paths import reveal_path


class SystemPathsTests(unittest.TestCase):
    @patch("cc_branch.application.system_paths.subprocess.Popen")
    @patch("cc_branch.application.system_paths.platform.system", return_value="Darwin")
    def test_reveal_file_in_macos_finder(self, _system, popen):
        reveal_path(Path("/tmp/demo/.cc-branch/config.yaml"), exists=lambda _path: True)

        popen.assert_called_once_with(["open", "-R", "/tmp/demo/.cc-branch/config.yaml"])

    @patch("cc_branch.application.system_paths.subprocess.Popen")
    @patch("cc_branch.application.system_paths.platform.system", return_value="Darwin")
    def test_open_existing_directory_in_macos_finder(self, _system, popen):
        reveal_path(
            Path("/tmp/demo"),
            exists=lambda _path: True,
            is_dir=lambda _path: True,
        )

        popen.assert_called_once_with(["open", "/tmp/demo"])

    def test_missing_path_fails_before_launching_file_manager(self):
        with self.assertRaises(FileNotFoundError):
            reveal_path(Path("/tmp/missing"), exists=lambda _path: False)


if __name__ == "__main__":
    unittest.main()
