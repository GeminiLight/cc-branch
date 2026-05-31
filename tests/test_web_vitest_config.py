import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WebVitestConfigTests(unittest.TestCase):
    def test_vitest_timeout_allows_interaction_heavy_ui_tests(self):
        config = (ROOT / "apps" / "web" / "vitest.config.ts").read_text(encoding="utf-8")
        match = re.search(r"testTimeout:\s*(\d+)", config)

        self.assertIsNotNone(match)
        self.assertGreaterEqual(int(match.group(1)), 15000)

    def test_webui_http_tests_use_shared_timeout_budget(self):
        test_source = (ROOT / "tests" / "test_webui.py").read_text(encoding="utf-8")

        self.assertIn("HTTP_TIMEOUT = 10", test_source)
        self.assertNotIn("timeout=2", test_source)


if __name__ == "__main__":
    unittest.main()
