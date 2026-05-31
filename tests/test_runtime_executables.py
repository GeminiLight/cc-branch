import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cc_branch.runtime.executables import which


class RuntimeExecutableLookupTests(unittest.TestCase):
    def test_lookup_includes_platform_paths_when_gui_path_is_minimal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "homebrew" / "bin"
            bin_dir.mkdir(parents=True)
            tmux = bin_dir / "tmux"
            tmux.write_text("#!/bin/sh\n", encoding="utf-8")
            tmux.chmod(0o755)

            with (
                patch.dict("os.environ", {"PATH": "/definitely/missing"}),
                patch("cc_branch.runtime.executables._PLATFORM_EXECUTABLE_DIRS", (str(bin_dir),)),
            ):
                self.assertEqual(which("tmux"), str(tmux))


if __name__ == "__main__":
    unittest.main()
