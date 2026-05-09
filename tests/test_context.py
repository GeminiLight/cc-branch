import tempfile
import unittest
from pathlib import Path

from cc_branch.context import WorkspaceContext


class WorkspaceContextTests(unittest.TestCase):
    def test_named_config_argument_selects_named_state_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            ctx = WorkspaceContext(root, config_path="review")

            self.assertEqual(ctx.config_path, root / ".cc-branch/configs/review.yaml")
            self.assertEqual(ctx.state_path, root / ".cc-branch/states/review.yaml")
