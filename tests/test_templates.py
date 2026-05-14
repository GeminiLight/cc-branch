import unittest

from cc_branch.templates import render_template


class TemplateTests(unittest.TestCase):
    def test_render_template_supports_single_brace_placeholders(self):
        self.assertEqual(
            render_template("codex resume {session_id}", {"session_id": "session-123"}),
            "codex resume session-123",
        )

    def test_render_template_tolerates_double_brace_placeholders(self):
        self.assertEqual(
            render_template("codex resume {{session_id}}", {"session_id": "session-123"}),
            "codex resume session-123",
        )

