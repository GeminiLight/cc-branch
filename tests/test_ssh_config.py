import tempfile
import unittest
from pathlib import Path

from cc_branch.application.ssh_config import discover_ssh_hosts


class SSHConfigDiscoveryTests(unittest.TestCase):
    def test_discovers_concrete_ssh_hosts_with_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config"
            config.write_text(
                "\n".join([
                    "Host devbox prod-* !blocked",
                    "  HostName dev.example.com",
                    "  User ubuntu",
                    "  Port 2222",
                    "Host *",
                    "  User ignored",
                    "",
                ]),
                encoding="utf-8",
            )

            self.assertEqual(
                discover_ssh_hosts(config),
                [{"alias": "devbox", "hostname": "dev.example.com", "user": "ubuntu", "port": 2222}],
            )

    def test_follows_simple_include_directives(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            included = root / "hosts.conf"
            included.write_text("Host gpu\n  HostName gpu.internal\n", encoding="utf-8")
            config = root / "config"
            config.write_text("Include hosts.conf\nHost local\n", encoding="utf-8")

            self.assertEqual(
                discover_ssh_hosts(config),
                [
                    {"alias": "gpu", "hostname": "gpu.internal"},
                    {"alias": "local"},
                ],
            )


if __name__ == "__main__":
    unittest.main()
