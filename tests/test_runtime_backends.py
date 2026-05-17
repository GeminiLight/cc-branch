import unittest
from unittest.mock import patch

from cc_branch.runtime.backends import TmuxBackend


class TmuxBackendTargetTests(unittest.TestCase):
    def test_session_lookup_uses_exact_target(self):
        backend = TmuxBackend()
        with patch("cc_branch.runtime.backends.subprocess.run") as run:
            run.return_value.returncode = 0

            self.assertTrue(backend.has_session("research-projects-development"))

        self.assertEqual(
            run.call_args.args[0],
            ["tmux", "has-session", "-t", "=research-projects-development"],
        )

    def test_window_operations_use_exact_session_and_window_targets(self):
        backend = TmuxBackend()
        with patch("cc_branch.runtime.backends.subprocess.run") as run:
            backend.send_keys("research-projects-development:frontend", "codex")
            backend.kill_window("research-projects-development:frontend")
            backend.attach_session("research-projects-development:frontend")

        self.assertEqual(
            run.call_args_list[0].args[0],
            ["tmux", "send-keys", "-t", "=research-projects-development:=frontend", "codex", "Enter"],
        )
        self.assertEqual(
            run.call_args_list[1].args[0],
            ["tmux", "kill-window", "-t", "=research-projects-development:=frontend"],
        )
        self.assertEqual(
            run.call_args_list[2].args[0],
            ["tmux", "attach-session", "-t", "=research-projects-development:=frontend"],
        )


if __name__ == "__main__":
    unittest.main()
