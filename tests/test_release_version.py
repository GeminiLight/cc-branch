import unittest
import re
from pathlib import Path

from scripts.verify_release_version import collect_versions, require_v_prefixed_tag, verify_versions


class ReleaseVersionTests(unittest.TestCase):
    def test_release_versions_are_consistent(self):
        result = verify_versions()

        self.assertTrue(result["ok"])
        self.assertEqual(len(set(result["files"].values())), 1)

    def test_release_version_accepts_current_v_tag(self):
        version = next(iter(set(collect_versions().values())))

        result = verify_versions(f"v{version}")

        self.assertEqual(result["version"], version)

    def test_release_version_accepts_current_v_tag_when_v_prefix_required(self):
        version = next(iter(set(collect_versions().values())))

        result = verify_versions(f"v{version}", require_v_prefix=True)

        self.assertEqual(result["version"], version)

    def test_release_version_rejects_bare_tag_when_v_prefix_required(self):
        with self.assertRaisesRegex(ValueError, "must start with 'v'"):
            verify_versions("1.1.0", require_v_prefix=True)

    def test_release_version_rejects_wrong_tag(self):
        with self.assertRaisesRegex(ValueError, "does not match expected"):
            verify_versions("v0.0.0")

    def test_require_v_prefixed_tag_accepts_current_v_tag(self):
        version = next(iter(set(collect_versions().values())))

        self.assertEqual(require_v_prefixed_tag(f"v{version}"), f"v{version}")

    def test_require_v_prefixed_tag_rejects_bare_version(self):
        with self.assertRaisesRegex(ValueError, "must start with 'v'"):
            require_v_prefixed_tag("1.1.0")

    def test_publish_workflow_auto_publishes_npm_on_release_when_token_is_configured(self):
        workflow = Path(".github/workflows/publish-python.yml").read_text(encoding="utf-8")

        self.assertIn("npm publish dist/cc-branch-*.tgz --access public", workflow)
        self.assertRegex(
            workflow,
            re.compile(
                r"name: Publish to npm registry\s+"
                r"if: \$\{\{ env\.NPM_TOKEN != '' && "
                r"\(github\.event_name == 'release' \|\| inputs\.publish_to_npm == 'true'\) \}\}",
                re.MULTILINE,
            ),
        )


if __name__ == "__main__":
    unittest.main()
