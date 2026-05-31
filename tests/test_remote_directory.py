import unittest
from unittest.mock import patch

from cc_branch.application.remote_directory import list_remote_directories


class RemoteDirectoryTests(unittest.TestCase):
    def test_list_remote_directories_uses_ssh_and_parses_directories(self):
        with patch("cc_branch.application.remote_directory.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "/srv\n./app\n./.cache\n"
            run.return_value.stderr = ""

            listing = list_remote_directories(
                {"host": "gpu-dev", "user": "ubuntu", "port": 2222},
                "/srv",
            )

        run.assert_called_once()
        command = run.call_args.args[0]
        self.assertEqual(command[:7], ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "-p", "2222"])
        self.assertEqual(command[7], "ubuntu@gpu-dev")
        self.assertIn("cd /srv", command[8])
        self.assertEqual(listing["path"], "/srv")
        self.assertEqual(listing["parent"], "/")
        self.assertEqual(
            listing["entries"],
            [
                {"name": "app", "path": "/srv/app", "hidden": False},
                {"name": ".cache", "path": "/srv/.cache", "hidden": True},
            ],
        )

    def test_rejects_missing_remote_host(self):
        with self.assertRaisesRegex(ValueError, "remote host is required"):
            list_remote_directories({}, "/srv")

    def test_list_remote_directories_caps_large_directory_results(self):
        with patch("cc_branch.application.remote_directory.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "/srv\n" + "\n".join(f"./dir-{index}" for index in range(305))
            run.return_value.stderr = ""

            listing = list_remote_directories({"host": "gpu-dev"}, "/srv", max_entries=300)

        command = run.call_args.args[0]
        self.assertIn("sed -n '1,301p'", command[-1])
        self.assertEqual(len(listing["entries"]), 300)
        self.assertTrue(listing["truncated"])


if __name__ == "__main__":
    unittest.main()
