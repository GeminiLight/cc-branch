import unittest

from cc_branch.schema import (
    CURRENT_CONFIG_SCHEMA_VERSION,
    CURRENT_STATE_SCHEMA_VERSION,
    require_current_config_schema,
    require_current_state_schema,
    schema_summary,
)


class SchemaGuardTests(unittest.TestCase):
    def test_current_config_schema_is_stable(self):
        raw = {"version": CURRENT_CONFIG_SCHEMA_VERSION, "project": "demo", "tabs": []}

        checked = require_current_config_schema(raw)

        self.assertEqual(checked, raw)
        self.assertIsNot(checked, raw)

    def test_current_state_schema_is_stable(self):
        raw = {"version": CURRENT_STATE_SCHEMA_VERSION, "windows": {}, "slots": {}}

        checked = require_current_state_schema(raw)

        self.assertEqual(checked, raw)
        self.assertIsNot(checked, raw)

    def test_old_config_schema_is_rejected_instead_of_migrated(self):
        with self.assertRaisesRegex(ValueError, "unsupported"):
            require_current_config_schema({"version": CURRENT_CONFIG_SCHEMA_VERSION - 1, "tabs": []})

    def test_old_public_config_fields_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "slots"):
            require_current_config_schema({"version": CURRENT_CONFIG_SCHEMA_VERSION, "slots": []})
        with self.assertRaisesRegex(ValueError, "default_opener"):
            require_current_config_schema({"version": CURRENT_CONFIG_SCHEMA_VERSION, "default_opener": "warp", "tabs": []})
        with self.assertRaisesRegex(ValueError, "tab field 'runtime'"):
            require_current_config_schema({
                "version": CURRENT_CONFIG_SCHEMA_VERSION,
                "tabs": [{"name": "dev", "runtime": "tmux", "panes": []}],
            })
        with self.assertRaisesRegex(ValueError, "tab field 'windows'"):
            require_current_config_schema({
                "version": CURRENT_CONFIG_SCHEMA_VERSION,
                "tabs": [{"name": "dev", "windows": []}],
            })
        with self.assertRaisesRegex(ValueError, "runtime"):
            require_current_config_schema({
                "version": CURRENT_CONFIG_SCHEMA_VERSION,
                "tabs": [{"name": "dev", "panes": [{"name": "shell", "runtime": "tmux"}]}],
            })
        with self.assertRaisesRegex(ValueError, "session_id"):
            require_current_config_schema({
                "version": CURRENT_CONFIG_SCHEMA_VERSION,
                "tabs": [{"name": "dev", "panes": [{"name": "shell", "session_id": "old"}]}],
            })

    def test_future_schema_versions_fail_closed(self):
        with self.assertRaises(ValueError):
            require_current_config_schema({"version": CURRENT_CONFIG_SCHEMA_VERSION + 1, "tabs": []})
        with self.assertRaises(ValueError):
            require_current_state_schema({"version": CURRENT_STATE_SCHEMA_VERSION + 1})

    def test_summary_lists_current_schema_versions_only(self):
        summary = schema_summary()

        self.assertEqual(summary["config"]["current_version"], CURRENT_CONFIG_SCHEMA_VERSION)
        self.assertEqual(summary["state"]["current_version"], CURRENT_STATE_SCHEMA_VERSION)
        self.assertNotIn("registered", summary["config"])


if __name__ == "__main__":
    unittest.main()
