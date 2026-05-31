import importlib.util
import json
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "preflight_desktop_release.py"
SPEC = importlib.util.spec_from_file_location("preflight_desktop_release", SCRIPT_PATH)
assert SPEC and SPEC.loader
preflight_desktop_release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight_desktop_release)


RELEASE_VERIFICATION_SUMMARY_SNIPPET = (
    "\n#### Verification summary"
    "\nverification_summary missing from release verification report"
    "\nverification_summary checks missing from release verification report"
    "\nverification_summary checks failed"
    "\nready_for_public_download"
    "\nverification_summary ready_for_public_download is not true"
    "\nfailed_checks"
    "\njson.dumps(report['verification_summary']"
)


class PreflightDesktopReleaseTests(unittest.TestCase):
    def test_preflight_accepts_ready_release_environment(self):
        def fake_run_json(command: list[str]) -> dict:
            if command[:3] == ["gh", "api", "repos/owner/repo/actions/permissions"]:
                return {"enabled": True, "allowed_actions": "all"}
            if command[:3] == ["gh", "api", "repos/owner/repo/actions/permissions/workflow"]:
                return {"default_workflow_permissions": "read"}
            raise AssertionError(f"Unexpected json command: {command}")

        def fake_run_text(command: list[str], *, check: bool = True) -> str:
            joined = " ".join(command)
            if command[:3] == ["gh", "workflow", "list"]:
                return "Release Desktop App\tactive\t267280456\n"
            if command[:3] == ["gh", "secret", "list"]:
                return "\n".join(f"{name}\t2026-05-18T00:00:00Z" for name in preflight_desktop_release.REQUIRED_SECRETS)
            if command[:2] == ["git", "ls-remote"]:
                return ""
            if command[:3] == ["gh", "release", "view"]:
                return "" if not check else ""
            raise AssertionError(f"Unexpected text command: {joined}")

        with mock.patch.object(preflight_desktop_release, "verify_versions", return_value={"ok": True, "version": "1.0.2"}), \
             mock.patch.object(preflight_desktop_release, "run_json", side_effect=fake_run_json), \
             mock.patch.object(preflight_desktop_release, "run_text", side_effect=fake_run_text):
            result = preflight_desktop_release.preflight("v1.0.2", "owner/repo")

        self.assertTrue(result["ok"])
        self.assertEqual(result["tag"], "v1.0.2")
        self.assertEqual(result["version"], "1.0.2")
        self.assertEqual(result["workflow_permissions"]["default_workflow_permissions"], "read")
        self.assertEqual(result["workflow_permissions"]["contents"], "write")

    def test_preflight_requires_v_prefixed_tag(self):
        with self.assertRaisesRegex(ValueError, "must start with 'v'"):
            preflight_desktop_release.preflight("1.0.2", "owner/repo")

    def test_preflight_rejects_missing_required_secrets(self):
        def fake_run_text(command: list[str], *, check: bool = True) -> str:
            if command[:3] == ["gh", "workflow", "list"]:
                return "Release Desktop App\tactive\t267280456\n"
            if command[:3] == ["gh", "secret", "list"]:
                return "TAURI_SIGNING_PRIVATE_KEY\t2026-05-18T00:00:00Z\n"
            if command[:2] == ["git", "ls-remote"]:
                return ""
            if command[:3] == ["gh", "release", "view"]:
                return ""
            return ""

        with mock.patch.object(preflight_desktop_release, "verify_versions", return_value={"ok": True, "version": "1.0.2"}), \
             mock.patch.object(preflight_desktop_release, "run_json", return_value={"enabled": True, "allowed_actions": "all"}), \
             mock.patch.object(preflight_desktop_release, "run_text", side_effect=fake_run_text):
            with self.assertRaisesRegex(ValueError, "Missing required GitHub secrets"):
                preflight_desktop_release.preflight("v1.0.2", "owner/repo")

    def test_preflight_rejects_existing_remote_tag(self):
        def fake_run_text(command: list[str], *, check: bool = True) -> str:
            if command[:3] == ["gh", "workflow", "list"]:
                return "Release Desktop App\tactive\t267280456\n"
            if command[:3] == ["gh", "secret", "list"]:
                return "\n".join(f"{name}\t2026-05-18T00:00:00Z" for name in preflight_desktop_release.REQUIRED_SECRETS)
            if command[:2] == ["git", "ls-remote"]:
                return "abc123\trefs/tags/v1.0.2\n"
            if command[:3] == ["gh", "release", "view"]:
                return ""
            return ""

        with mock.patch.object(preflight_desktop_release, "verify_versions", return_value={"ok": True, "version": "1.0.2"}), \
             mock.patch.object(preflight_desktop_release, "run_json", return_value={"enabled": True, "allowed_actions": "all"}), \
             mock.patch.object(preflight_desktop_release, "run_text", side_effect=fake_run_text):
            with self.assertRaisesRegex(ValueError, "Remote tag already exists"):
                preflight_desktop_release.preflight("v1.0.2", "owner/repo")

    def test_preflight_rejects_release_lookup_failures_that_are_not_not_found(self):
        def fake_run(command: list[str], *, check: bool, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
            self.assertEqual(command[:3], ["gh", "release", "view"])
            self.assertFalse(check)
            self.assertTrue(capture_output)
            self.assertTrue(text)
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="HTTP 500 from GitHub API")

        with mock.patch.object(preflight_desktop_release.subprocess, "run", side_effect=fake_run):
            with self.assertRaisesRegex(ValueError, "Could not verify GitHub release availability"):
                preflight_desktop_release.require_release_available("v1.0.2", "owner/repo")

    def test_preflight_accepts_release_not_found_as_available(self):
        def fake_run(command: list[str], *, check: bool, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
            self.assertEqual(command[:3], ["gh", "release", "view"])
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="release not found")

        with mock.patch.object(preflight_desktop_release.subprocess, "run", side_effect=fake_run):
            preflight_desktop_release.require_release_available("v1.0.2", "owner/repo")

    def test_preflight_rejects_release_workflow_without_contents_write_permission(self):
        def fake_run_json(command: list[str]) -> dict:
            if command[:3] == ["gh", "api", "repos/owner/repo/actions/permissions"]:
                return {"enabled": True, "allowed_actions": "all"}
            if command[:3] == ["gh", "api", "repos/owner/repo/actions/permissions/workflow"]:
                return {"default_workflow_permissions": "read"}
            raise AssertionError(f"Unexpected json command: {command}")

        def fake_run_text(command: list[str], *, check: bool = True) -> str:
            if command[:3] == ["gh", "workflow", "list"]:
                return "Release Desktop App\tactive\t267280456\n"
            if command[:3] == ["gh", "secret", "list"]:
                return "\n".join(f"{name}\t2026-05-18T00:00:00Z" for name in preflight_desktop_release.REQUIRED_SECRETS)
            if command[:2] == ["git", "ls-remote"]:
                return ""
            if command[:3] == ["gh", "release", "view"]:
                return ""
            raise AssertionError(f"Unexpected text command: {command}")

        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            workflow_path = Path(tmp) / "release-desktop.yml"
            workflow_path.write_text(
                "name: Release Desktop App\npermissions:\n  contents: read\n",
                encoding="utf-8",
            )
            with mock.patch.object(preflight_desktop_release, "RELEASE_WORKFLOW_PATH", workflow_path), \
                 mock.patch.object(preflight_desktop_release, "verify_versions", return_value={"ok": True, "version": "1.0.2"}), \
                 mock.patch.object(preflight_desktop_release, "run_json", side_effect=fake_run_json), \
                 mock.patch.object(preflight_desktop_release, "run_text", side_effect=fake_run_text):
                with self.assertRaisesRegex(ValueError, "contents: write"):
                    preflight_desktop_release.preflight("v1.0.2", "owner/repo")

    def test_preflight_rejects_release_workflow_without_missing_sidecar_gate(self):
        def fake_run_json(command: list[str]) -> dict:
            if command[:3] == ["gh", "api", "repos/owner/repo/actions/permissions"]:
                return {"enabled": True, "allowed_actions": "all"}
            if command[:3] == ["gh", "api", "repos/owner/repo/actions/permissions/workflow"]:
                return {"default_workflow_permissions": "read"}
            raise AssertionError(f"Unexpected json command: {command}")

        def fake_run_text(command: list[str], *, check: bool = True) -> str:
            if command[:3] == ["gh", "workflow", "list"]:
                return "Release Desktop App\tactive\t267280456\n"
            if command[:3] == ["gh", "secret", "list"]:
                return "\n".join(f"{name}\t2026-05-18T00:00:00Z" for name in preflight_desktop_release.REQUIRED_SECRETS)
            if command[:2] == ["git", "ls-remote"]:
                return ""
            if command[:3] == ["gh", "release", "view"]:
                return ""
            raise AssertionError(f"Unexpected text command: {command}")

        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            workflow_path = Path(tmp) / "release-desktop.yml"
            workflow_path.write_text(
                "\n".join(
                    [
                        "name: Release Desktop App",
                        "permissions:",
                        "  contents: write",
                        "jobs:",
                        "  build:",
                        "    steps:",
                        "      - name: Smoke test bundled backend sidecar",
                        '        run: python scripts/smoke-test-backend-sidecar.py sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"',
                        "      - name: Smoke test packaged macOS desktop app",
                        '        run: python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"',
                    ]
                ),
                encoding="utf-8",
            )
            with mock.patch.object(preflight_desktop_release, "RELEASE_WORKFLOW_PATH", workflow_path), \
                 mock.patch.object(preflight_desktop_release, "verify_versions", return_value={"ok": True, "version": "1.0.2"}), \
                 mock.patch.object(preflight_desktop_release, "run_json", side_effect=fake_run_json), \
                 mock.patch.object(preflight_desktop_release, "run_text", side_effect=fake_run_text):
                with self.assertRaisesRegex(ValueError, "missing sidecar failure smoke"):
                    preflight_desktop_release.preflight("v1.0.2", "owner/repo")

    def test_preflight_requires_missing_sidecar_gate_on_each_packaged_app_smoke_step(self):
        def fake_run_json(command: list[str]) -> dict:
            if command[:3] == ["gh", "api", "repos/owner/repo/actions/permissions"]:
                return {"enabled": True, "allowed_actions": "all"}
            if command[:3] == ["gh", "api", "repos/owner/repo/actions/permissions/workflow"]:
                return {"default_workflow_permissions": "read"}
            raise AssertionError(f"Unexpected json command: {command}")

        def fake_run_text(command: list[str], *, check: bool = True) -> str:
            if command[:3] == ["gh", "workflow", "list"]:
                return "Release Desktop App\tactive\t267280456\n"
            if command[:3] == ["gh", "secret", "list"]:
                return "\n".join(f"{name}\t2026-05-18T00:00:00Z" for name in preflight_desktop_release.REQUIRED_SECRETS)
            if command[:2] == ["git", "ls-remote"]:
                return ""
            if command[:3] == ["gh", "release", "view"]:
                return ""
            raise AssertionError(f"Unexpected text command: {command}")

        workflow = {
            "name": "Release Desktop App",
            "permissions": {"contents": "write"},
            "jobs": {
                "build": {
                    "steps": [
                        {"uses": "actions/checkout@v6"},
                        {"uses": "actions/setup-node@v6"},
                        {"uses": "actions/setup-python@v6"},
                        {"uses": "dtolnay/rust-toolchain@stable"},
                        {"uses": "tauri-apps/tauri-action@v0"},
                        {"uses": "actions/upload-artifact@v7"},
                        {
                            "name": "Smoke test bundled backend sidecar",
                            "run": 'python scripts/smoke-test-backend-sidecar.py sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"',
                        },
                        {
                            "name": "Smoke test packaged macOS desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\nrecovery_report="smoke-reports/desktop-app-recovery-${{ matrix.sidecar-target }}.json"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\necho "### Startup failure recovery smoke"\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Smoke test packaged Linux desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"',
                        },
                        {
                            "name": "Smoke test packaged Windows desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"',
                        },
                    ]
                },
                "canary-installers": {
                    "needs": "publish-updater-json",
                    "strategy": {
                        "matrix": {
                            "include": [
                                {"platform": "mac-apple-silicon", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-aarch64"},
                                {"platform": "mac-intel", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-x86_64"},
                                {"platform": "linux", "verifier-args": "--skip-dmg --verify-linux-installers --launch-linux-packages --launch-linux-appimage"},
                                {"platform": "windows", "verifier-args": "--skip-dmg --verify-windows-installer --launch-windows-msi --launch-windows-nsis"},
                            ]
                        }
                    },
                    "steps": [{"name": "Download and verify draft installer assets", "run": "python scripts/verify_github_release.py tag --expected-version \"$version\" ${{ matrix.verifier-args }}" + RELEASE_VERIFICATION_SUMMARY_SNIPPET}],
                },
                "publish-release": {
                    "needs": ["canary-release", "canary-installers"],
                    "steps": [{"name": "Publish draft release", "run": "gh release edit \"$RELEASE_TAG\" --draft=false --prerelease=false --latest"}],
                },
                "verify-live-release": {
                    "needs": "publish-release",
                    "strategy": {
                        "matrix": {
                            "include": [
                                {"platform": "mac-apple-silicon", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-aarch64"},
                                {"platform": "mac-intel", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-x86_64"},
                                {"platform": "linux", "verifier-args": "--skip-dmg --verify-linux-installers --launch-linux-packages --launch-linux-appimage"},
                                {"platform": "windows", "verifier-args": "--skip-dmg --verify-windows-installer --launch-windows-msi --launch-windows-nsis"},
                            ]
                        }
                    },
                    "steps": [{"name": "Download and verify published assets", "run": "python scripts/verify_github_release.py tag --require-latest --require-public ${{ matrix.verifier-args }}"}],
                },
            },
        }
        workflow_text = preflight_desktop_release.yaml.safe_dump(workflow)

        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            workflow_path = Path(tmp) / "release-desktop.yml"
            workflow_path.write_text(workflow_text, encoding="utf-8")
            with mock.patch.object(preflight_desktop_release, "RELEASE_WORKFLOW_PATH", workflow_path), \
                 mock.patch.object(preflight_desktop_release, "verify_versions", return_value={"ok": True, "version": "1.0.2"}), \
                 mock.patch.object(preflight_desktop_release, "run_json", side_effect=fake_run_json), \
                 mock.patch.object(preflight_desktop_release, "run_text", side_effect=fake_run_text):
                with self.assertRaisesRegex(ValueError, "Linux.*missing sidecar"):
                    preflight_desktop_release.preflight("v1.0.2", "owner/repo")

    def test_preflight_requires_stale_backend_rejection_gate_on_each_packaged_app_smoke_step(self):
        workflow = {
            "name": "Release Desktop App",
            "permissions": {"contents": "write"},
            "jobs": {
                "build": {
                    "steps": [
                        {
                            "name": "Smoke test bundled backend sidecar",
                            "run": 'python scripts/smoke-test-backend-sidecar.py sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"',
                        },
                        {
                            "name": "Smoke test packaged macOS desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\nrecovery_report="smoke-reports/desktop-app-recovery-${{ matrix.sidecar-target }}.json"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\necho "### Startup failure recovery smoke"\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Smoke test packaged Linux desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"',
                        },
                        {
                            "name": "Smoke test packaged Windows desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\n$recoveryReport = "smoke-reports/desktop-app-recovery-${{ matrix.sidecar-target }}.json"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\n"### Startup failure recovery smoke" >> $env:GITHUB_STEP_SUMMARY\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Verify macOS DMG contains backend sidecar",
                            "run": "python scripts/verify-macos-dmg.py dmg --launch-app --verify-installed-copy --verify-stale-backend-rejection --expected-version \"$version\"",
                        },
                        {
                            "name": "Verify Linux installers contain backend sidecar",
                            "run": "python scripts/verify-desktop-installers.py --platform linux --launch-linux-packages --launch-appimage --expected-version \"$version\"",
                        },
                        {
                            "name": "Verify Windows installers contain backend sidecar",
                            "run": "python scripts/verify-desktop-installers.py --platform windows --launch-windows-msi --launch-windows-nsis --expected-version \"$version\"",
                        },
                        {
                            "name": "Upload desktop smoke reports",
                            "if": "always()",
                            "uses": "actions/upload-artifact@v7",
                            "with": {
                                "name": "desktop-smoke-reports-${{ matrix.platform }}-${{ matrix.sidecar-target }}",
                                "path": "smoke-reports/*.json",
                                "if-no-files-found": "error",
                            },
                        },
                    ]
                },
                "canary-installers": {
                    "needs": "publish-updater-json",
                    "strategy": {
                        "matrix": {
                            "include": [
                                {"platform": "mac-apple-silicon", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-aarch64"},
                                {"platform": "mac-intel", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-x86_64"},
                                {"platform": "linux", "verifier-args": "--skip-dmg --verify-linux-installers --launch-linux-packages --launch-linux-appimage"},
                                {"platform": "windows", "verifier-args": "--skip-dmg --verify-windows-installer --launch-windows-msi --launch-windows-nsis"},
                            ]
                        }
                    },
                    "steps": [{"name": "Download and verify draft installer assets", "run": "python scripts/verify_github_release.py tag --expected-version \"$version\" ${{ matrix.verifier-args }}" + RELEASE_VERIFICATION_SUMMARY_SNIPPET}],
                },
                "publish-release": {
                    "needs": ["canary-release", "canary-installers"],
                    "steps": [{"name": "Publish draft release", "run": "gh release edit \"$RELEASE_TAG\" --draft=false --prerelease=false --latest"}],
                },
                "verify-live-release": {
                    "needs": "publish-release",
                    "strategy": {
                        "matrix": {
                            "include": [
                                {"platform": "mac-apple-silicon", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-aarch64"},
                                {"platform": "mac-intel", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-x86_64"},
                                {"platform": "linux", "verifier-args": "--skip-dmg --verify-linux-installers --launch-linux-packages --launch-linux-appimage"},
                                {"platform": "windows", "verifier-args": "--skip-dmg --verify-windows-installer --launch-windows-msi --launch-windows-nsis"},
                            ]
                        }
                    },
                    "steps": [{"name": "Download and verify published assets", "run": "python scripts/verify_github_release.py tag --require-latest --require-public ${{ matrix.verifier-args }}"}],
                },
            },
        }
        with self.assertRaisesRegex(ValueError, "Linux.*stale backend"):
            preflight_desktop_release.require_build_quality_gates(workflow)

    def test_preflight_requires_expected_version_on_draft_and_live_download_verification(self):
        workflow = {
            "jobs": {
                "canary-installers": {
                    "needs": "publish-updater-json",
                    "strategy": {
                        "matrix": {
                            "include": [
                                {"platform": "mac-apple-silicon", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-aarch64"},
                                {"platform": "mac-intel", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-x86_64"},
                                {"platform": "linux", "verifier-args": "--skip-dmg --verify-linux-installers --launch-linux-packages --launch-linux-appimage"},
                                {"platform": "windows", "verifier-args": "--skip-dmg --verify-windows-installer --launch-windows-msi --launch-windows-nsis"},
                            ]
                        }
                    },
                    "steps": [
                        {
                            "name": "Download and verify draft installer assets",
                            "run": "python scripts/verify_github_release.py tag ${{ matrix.verifier-args }}",
                        }
                    ],
                },
                "publish-release": {
                    "needs": ["canary-release", "canary-installers"],
                    "steps": [{"name": "Publish draft release", "run": "gh release edit \"$RELEASE_TAG\" --draft=false --prerelease=false --latest"}],
                },
                "verify-live-release": {
                    "needs": "publish-release",
                    "strategy": {
                        "matrix": {
                            "include": [
                                {"platform": "mac-apple-silicon", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-aarch64"},
                                {"platform": "mac-intel", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-x86_64"},
                                {"platform": "linux", "verifier-args": "--skip-dmg --verify-linux-installers --launch-linux-packages --launch-linux-appimage"},
                                {"platform": "windows", "verifier-args": "--skip-dmg --verify-windows-installer --launch-windows-msi --launch-windows-nsis"},
                            ]
                        }
                    },
                    "steps": [
                        {
                            "name": "Download and verify published assets",
                            "run": "python scripts/verify_github_release.py tag --expected-version \"$version\" --require-latest --require-public ${{ matrix.verifier-args }}",
                        }
                    ],
                },
            }
        }

        with self.assertRaisesRegex(ValueError, "draft.*--expected-version"):
            preflight_desktop_release.require_canary_and_live_quality_gates(workflow)

    def test_preflight_requires_expected_version_on_live_download_verification(self):
        workflow = {
            "jobs": {
                "canary-installers": {
                    "needs": "publish-updater-json",
                    "strategy": {
                        "matrix": {
                            "include": [
                                {"platform": "mac-apple-silicon", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-aarch64"},
                                {"platform": "mac-intel", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-x86_64"},
                                {"platform": "linux", "verifier-args": "--skip-dmg --verify-linux-installers --launch-linux-packages --launch-linux-appimage"},
                                {"platform": "windows", "verifier-args": "--skip-dmg --verify-windows-installer --launch-windows-msi --launch-windows-nsis"},
                            ]
                        }
                    },
                    "steps": [
                        {
                            "name": "Download and verify draft installer assets",
                            "run": "python scripts/verify_github_release.py tag --expected-version \"$version\" ${{ matrix.verifier-args }}" + RELEASE_VERIFICATION_SUMMARY_SNIPPET,
                        }
                    ],
                },
                "publish-release": {
                    "needs": ["canary-release", "canary-installers"],
                    "steps": [{"name": "Publish draft release", "run": "gh release edit \"$RELEASE_TAG\" --draft=false --prerelease=false --latest"}],
                },
                "verify-live-release": {
                    "needs": "publish-release",
                    "strategy": {
                        "matrix": {
                            "include": [
                                {"platform": "mac-apple-silicon", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-aarch64"},
                                {"platform": "mac-intel", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-x86_64"},
                                {"platform": "linux", "verifier-args": "--skip-dmg --verify-linux-installers --launch-linux-packages --launch-linux-appimage"},
                                {"platform": "windows", "verifier-args": "--skip-dmg --verify-windows-installer --launch-windows-msi --launch-windows-nsis"},
                            ]
                        }
                    },
                    "steps": [
                        {
                            "name": "Download and verify published assets",
                            "run": "python scripts/verify_github_release.py tag --require-latest --require-public ${{ matrix.verifier-args }}",
                        }
                    ],
                },
            }
        }

        with self.assertRaisesRegex(ValueError, "live.*--expected-version"):
            preflight_desktop_release.require_canary_and_live_quality_gates(workflow)

    def test_preflight_requires_release_verification_summary_in_step_summary(self):
        workflow = {
            "jobs": {
                "canary-installers": {
                    "needs": "publish-updater-json",
                    "strategy": {
                        "matrix": {
                            "include": [
                                {"platform": "mac-apple-silicon", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-aarch64"},
                                {"platform": "mac-intel", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-x86_64"},
                                {"platform": "linux", "verifier-args": "--skip-dmg --verify-linux-installers --launch-linux-packages --launch-linux-appimage"},
                                {"platform": "windows", "verifier-args": "--skip-dmg --verify-windows-installer --launch-windows-msi --launch-windows-nsis"},
                            ]
                        }
                    },
                    "steps": [{"name": "Download and verify draft installer assets", "run": "python scripts/verify_github_release.py tag --expected-version \"$version\" ${{ matrix.verifier-args }}" + RELEASE_VERIFICATION_SUMMARY_SNIPPET}],
                },
                "publish-release": {
                    "needs": ["canary-release", "canary-installers"],
                    "steps": [{"name": "Publish draft release", "run": "gh release edit \"$RELEASE_TAG\" --draft=false --prerelease=false --latest"}],
                },
                "verify-live-release": {
                    "needs": "publish-release",
                    "strategy": {
                        "matrix": {
                            "include": [
                                {"platform": "mac-apple-silicon", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-aarch64"},
                                {"platform": "mac-intel", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-x86_64"},
                                {"platform": "linux", "verifier-args": "--skip-dmg --verify-linux-installers --launch-linux-packages --launch-linux-appimage"},
                                {"platform": "windows", "verifier-args": "--skip-dmg --verify-windows-installer --launch-windows-msi --launch-windows-nsis"},
                            ]
                        }
                    },
                    "steps": [{"name": "Download and verify published assets", "run": "python scripts/verify_github_release.py tag --expected-version \"$version\" --require-latest --require-public ${{ matrix.verifier-args }}"}],
                },
            }
        }

        with self.assertRaisesRegex(ValueError, "verification summary"):
            preflight_desktop_release.require_canary_and_live_quality_gates(workflow)

    def test_preflight_requires_release_verification_summary_checks_to_pass(self):
        summary_snippet_without_checks = (
            "\n#### Verification summary"
            "\nverification_summary missing from release verification report"
            "\njson.dumps(report['verification_summary']"
        )
        workflow = {
            "jobs": {
                "canary-installers": {
                    "needs": "publish-updater-json",
                    "strategy": {
                        "matrix": {
                            "include": [
                                {"platform": "mac-apple-silicon", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-aarch64"},
                                {"platform": "mac-intel", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-x86_64"},
                                {"platform": "linux", "verifier-args": "--skip-dmg --verify-linux-installers --launch-linux-packages --launch-linux-appimage"},
                                {"platform": "windows", "verifier-args": "--skip-dmg --verify-windows-installer --launch-windows-msi --launch-windows-nsis"},
                            ]
                        }
                    },
                    "steps": [{"name": "Download and verify draft installer assets", "run": "python scripts/verify_github_release.py tag --expected-version \"$version\" ${{ matrix.verifier-args }}" + summary_snippet_without_checks}],
                },
                "publish-release": {
                    "needs": ["canary-release", "canary-installers"],
                    "steps": [{"name": "Publish draft release", "run": "gh release edit \"$RELEASE_TAG\" --draft=false --prerelease=false --latest"}],
                },
                "verify-live-release": {
                    "needs": "publish-release",
                    "strategy": {
                        "matrix": {
                            "include": [
                                {"platform": "mac-apple-silicon", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-aarch64"},
                                {"platform": "mac-intel", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-x86_64"},
                                {"platform": "linux", "verifier-args": "--skip-dmg --verify-linux-installers --launch-linux-packages --launch-linux-appimage"},
                                {"platform": "windows", "verifier-args": "--skip-dmg --verify-windows-installer --launch-windows-msi --launch-windows-nsis"},
                            ]
                        }
                    },
                    "steps": [{"name": "Download and verify published assets", "run": "python scripts/verify_github_release.py tag --expected-version \"$version\" --require-latest --require-public ${{ matrix.verifier-args }}" + summary_snippet_without_checks}],
                },
                "rollback-live-release": {
                    "needs": ["publish-release", "verify-live-release"],
                    "if": "${{ always() && needs.publish-release.result == 'success' && needs.verify-live-release.result != 'success' }}",
                    "steps": [{"name": "Rollback failed live release", "run": "gh release edit \"$RELEASE_TAG\" --draft=true --prerelease=true"}],
                },
            }
        }

        with self.assertRaisesRegex(ValueError, "summary checks"):
            preflight_desktop_release.require_canary_and_live_quality_gates(workflow)

    def test_preflight_requires_packaged_app_smoke_to_use_auto_port(self):
        workflow = {
            "jobs": {
                "build": {
                    "steps": [
                        {
                            "name": "Smoke test bundled backend sidecar",
                            "run": 'python scripts/smoke-test-backend-sidecar.py sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"',
                        },
                        {
                            "name": "Smoke test packaged macOS desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Smoke test packaged Linux desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Smoke test packaged Windows desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Verify macOS DMG contains backend sidecar",
                            "run": "python scripts/verify-macos-dmg.py dmg --launch-app --verify-installed-copy --verify-stale-backend-rejection --expected-version \"$version\"",
                        },
                        {
                            "name": "Verify Linux installers contain backend sidecar",
                            "run": "python scripts/verify-desktop-installers.py --platform linux --launch-linux-packages --launch-appimage --expected-version \"$version\"",
                        },
                        {
                            "name": "Verify Windows installers contain backend sidecar",
                            "run": "python scripts/verify-desktop-installers.py --platform windows --launch-windows-msi --launch-windows-nsis --expected-version \"$version\"",
                        },
                    ]
                }
            }
        }

        with self.assertRaisesRegex(ValueError, "macOS.*auto port"):
            preflight_desktop_release.require_build_quality_gates(workflow)

    def test_preflight_requires_startup_failure_recovery_gate_on_each_packaged_app_smoke_step(self):
        workflow = {
            "jobs": {
                "build": {
                    "steps": [
                        {
                            "name": "Smoke test bundled backend sidecar",
                            "run": 'python scripts/smoke-test-backend-sidecar.py sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"',
                        },
                        {
                            "name": "Smoke test packaged macOS desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\n$recoveryReport = "smoke-reports/desktop-app-recovery-${{ matrix.sidecar-target }}.json"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\n"### Startup failure recovery smoke" >> $env:GITHUB_STEP_SUMMARY\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Smoke test packaged Linux desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Smoke test packaged Windows desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                    ]
                }
            }
        }

        with self.assertRaisesRegex(ValueError, "Linux.*startup failure recovery"):
            preflight_desktop_release.require_build_quality_gates(workflow)

    def test_preflight_requires_startup_failure_recovery_report_on_each_packaged_app_smoke_step(self):
        workflow = {
            "jobs": {
                "build": {
                    "steps": [
                        {
                            "name": "Smoke test bundled backend sidecar",
                            "run": 'python scripts/smoke-test-backend-sidecar.py sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"',
                        },
                        {
                            "name": "Smoke test packaged macOS desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Smoke test packaged Linux desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\nrecovery_report="smoke-reports/desktop-app-recovery-${{ matrix.sidecar-target }}.json"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\necho "### Startup failure recovery smoke"\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Smoke test packaged Windows desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\n$recoveryReport = "smoke-reports/desktop-app-recovery-${{ matrix.sidecar-target }}.json"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\n"### Startup failure recovery smoke" >> $env:GITHUB_STEP_SUMMARY\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Verify macOS DMG contains backend sidecar",
                            "run": "python scripts/verify-macos-dmg.py dmg --launch-app --verify-installed-copy --verify-stale-backend-rejection --expected-version \"$version\"",
                        },
                        {
                            "name": "Verify Linux installers contain backend sidecar",
                            "run": "python scripts/verify-desktop-installers.py --platform linux --launch-linux-packages --launch-appimage --expected-version \"$version\"",
                        },
                        {
                            "name": "Verify Windows installers contain backend sidecar",
                            "run": "python scripts/verify-desktop-installers.py --platform windows --launch-windows-msi --launch-windows-nsis --expected-version \"$version\"",
                        },
                    ]
                }
            }
        }

        with self.assertRaisesRegex(ValueError, "macOS.*startup failure recovery report"):
            preflight_desktop_release.require_packaged_recovery_report_gates(workflow)

    def test_preflight_requires_windows_missing_sidecar_smoke_to_clean_temp_directory(self):
        workflow = {
            "jobs": {
                "build": {
                    "steps": [
                        {
                            "name": "Smoke test packaged Windows desktop app",
                            "run": '\n'.join(
                                [
                                    '$missingSidecarDir = Join-Path $env:RUNNER_TEMP "cc-branch-missing-sidecar"',
                                    "New-Item -ItemType Directory -Force -Path $missingSidecarDir | Out-Null",
                                    "python scripts/smoke-test-desktop-app.py app --expect-startup-failure",
                                ]
                            ),
                        }
                    ]
                }
            }
        }

        with self.assertRaisesRegex(ValueError, "Windows.*clean missing sidecar temp"):
            preflight_desktop_release.require_windows_missing_sidecar_temp_cleanup_gate(workflow)

    def test_preflight_rejects_release_workflow_bash_run_syntax_errors(self):
        workflow = {
            "jobs": {
                "build": {
                    "steps": [
                        {
                            "name": "Broken bash release step",
                            "shell": "bash",
                            "run": "if true; then\n  echo broken\n",
                        }
                    ]
                }
            }
        }

        with self.assertRaisesRegex(ValueError, "Broken bash release step.*bash syntax"):
            preflight_desktop_release.require_release_workflow_bash_syntax(workflow)

    def test_preflight_rejects_release_workflow_bash_4_only_helpers(self):
        workflow = {
            "jobs": {
                "build": {
                    "steps": [
                        {
                            "name": "macOS smoke",
                            "shell": "bash",
                            "run": "mapfile -t apps < <(find target -name '*.app')\n",
                        }
                    ]
                }
            }
        }

        with self.assertRaisesRegex(ValueError, "mapfile.*macOS runner Bash 3.2"):
            preflight_desktop_release.require_release_workflow_bash_syntax(workflow)

    def test_preflight_requires_desktop_smoke_reports_upload_on_failure(self):
        workflow = {
            "jobs": {
                "build": {
                    "steps": [
                        {
                            "name": "Upload desktop smoke reports",
                            "uses": "actions/upload-artifact@v7",
                            "with": {
                                "name": "desktop-smoke-reports-${{ matrix.platform }}-${{ matrix.sidecar-target }}",
                                "path": "smoke-reports/*.json",
                                "if-no-files-found": "warn",
                            },
                        }
                    ]
                }
            }
        }

        with self.assertRaisesRegex(ValueError, "desktop smoke reports.*if: always"):
            preflight_desktop_release.require_desktop_smoke_report_artifact_gate(workflow)

    def test_preflight_requires_stale_backend_rejection_on_macos_dmg_verifier(self):
        workflow = {
            "name": "Release Desktop App",
            "permissions": {"contents": "write"},
            "jobs": {
                "build": {
                    "steps": [
                        {
                            "name": "Smoke test bundled backend sidecar",
                            "run": 'python scripts/smoke-test-backend-sidecar.py sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"',
                        },
                        {
                            "name": "Smoke test packaged macOS desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Smoke test packaged Linux desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Smoke test packaged Windows desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Verify macOS DMG contains backend sidecar",
                            "run": "python scripts/verify-macos-dmg.py dmg --launch-app --verify-installed-copy",
                        },
                        {
                            "name": "Verify Linux installers contain backend sidecar",
                            "run": "python scripts/verify-desktop-installers.py --platform linux --launch-linux-packages --launch-appimage",
                        },
                        {
                            "name": "Verify Windows installers contain backend sidecar",
                            "run": "python scripts/verify-desktop-installers.py --platform windows --launch-windows-msi --launch-windows-nsis",
                        },
                    ]
                },
                "canary-installers": {
                    "needs": "publish-updater-json",
                    "strategy": {
                        "matrix": {
                            "include": [
                                {"platform": "mac-apple-silicon", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-aarch64"},
                                {"platform": "mac-intel", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-x86_64"},
                                {"platform": "linux", "verifier-args": "--skip-dmg --verify-linux-installers --launch-linux-packages --launch-linux-appimage"},
                                {"platform": "windows", "verifier-args": "--skip-dmg --verify-windows-installer --launch-windows-msi --launch-windows-nsis"},
                            ]
                        }
                    },
                    "steps": [
                        {
                            "name": "Download and verify draft installer assets",
                            "run": "python scripts/verify_github_release.py tag --expected-version \"$version\" ${{ matrix.verifier-args }}" + RELEASE_VERIFICATION_SUMMARY_SNIPPET,
                        }
                    ],
                },
                "publish-release": {
                    "needs": ["canary-release", "canary-installers"],
                    "steps": [{"name": "Publish draft release", "run": "gh release edit \"$RELEASE_TAG\" --draft=false --prerelease=false --latest"}],
                },
                "verify-live-release": {
                    "needs": "publish-release",
                    "strategy": {
                        "matrix": {
                            "include": [
                                {"platform": "mac-apple-silicon", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-aarch64"},
                                {"platform": "mac-intel", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-x86_64"},
                                {"platform": "linux", "verifier-args": "--skip-dmg --verify-linux-installers --launch-linux-packages --launch-linux-appimage"},
                                {"platform": "windows", "verifier-args": "--skip-dmg --verify-windows-installer --launch-windows-msi --launch-windows-nsis"},
                            ]
                        }
                    },
                    "steps": [{"name": "Download and verify published assets", "run": "python scripts/verify_github_release.py tag --require-latest --require-public ${{ matrix.verifier-args }}"}],
                },
            },
        }
        workflow_text = preflight_desktop_release.yaml.safe_dump(workflow)

        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            workflow_path = Path(tmp) / "release-desktop.yml"
            workflow_path.write_text(workflow_text, encoding="utf-8")
            with mock.patch.object(preflight_desktop_release, "RELEASE_WORKFLOW_PATH", workflow_path):
                with self.assertRaisesRegex(ValueError, "macOS DMG.*stale backend"):
                    preflight_desktop_release.require_release_quality_gates()

    def test_preflight_requires_standalone_installer_metadata_gates(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            tmp_path = Path(tmp)
            dmg_verifier = tmp_path / "verify-macos-dmg.py"
            installer_verifier = tmp_path / "verify-desktop-installers.py"
            dmg_verifier.write_text(
                "\n".join(
                    [
                        "def verify_app_launches_backend(): pass",
                        "expected_version=expected_version",
                        "desktop_version",
                    ]
                ),
                encoding="utf-8",
            )
            installer_verifier.write_text(
                "\n".join(
                    [
                        "def verify_desktop_app_launch(): pass",
                        'expected_platform="linux" if expected_version else None',
                        'expected_platform="windows" if expected_version else None',
                        'expected_arch="x86_64" if expected_version else None',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "MACOS_DMG_VERIFIER_PATH",
                dmg_verifier,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "DESKTOP_INSTALLER_VERIFIER_PATH",
                installer_verifier,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "standalone.*metadata"):
                    preflight_desktop_release.require_release_quality_gates()

    def test_preflight_requires_backend_sidecar_desktop_metadata_args(self):
        workflow = {
            "jobs": {
                "build": {
                    "steps": [
                        {
                            "name": "Smoke test bundled backend sidecar",
                            "run": (
                                "python scripts/smoke-test-backend-sidecar.py sidecar "
                                "--expected-version \"${{ inputs.release_tag || github.ref_name }}\" "
                                "--expected-platform \"${{ matrix.desktop-platform }}\""
                            ),
                        },
                        {
                            "name": "Smoke test packaged macOS desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Smoke test packaged Linux desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Smoke test packaged Windows desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Verify macOS DMG contains backend sidecar",
                            "run": "python scripts/verify-macos-dmg.py dmg --launch-app --verify-installed-copy --verify-stale-backend-rejection --expected-version \"$version\"",
                        },
                        {
                            "name": "Verify Linux installers contain backend sidecar",
                            "run": "python scripts/verify-desktop-installers.py --platform linux --launch-linux-packages --launch-appimage --expected-version \"$version\"",
                        },
                        {
                            "name": "Verify Windows installers contain backend sidecar",
                            "run": "python scripts/verify-desktop-installers.py --platform windows --launch-windows-msi --launch-windows-nsis --expected-version \"$version\"",
                        },
                    ]
                }
            }
        }

        with self.assertRaisesRegex(ValueError, "--expected-arch"):
            preflight_desktop_release.require_build_quality_gates(workflow)

    def test_preflight_quality_gates_include_backend_sidecar_desktop_metadata(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_github_download_launch_desktop_metadata_gate",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["backend_sidecar_desktop_metadata_smoke"])

    def test_preflight_quality_gates_include_macos_drag_install_shortcut(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["macOS_DMG_applications_shortcut"])

    def test_preflight_quality_gates_include_macos_installed_copy_launch(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["macOS_DMG_installed_copy_launch"])

    def test_preflight_quality_gates_include_linux_package_launches(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["Linux_DEB_launch"])
        self.assertTrue(gates["Linux_DEB_stale_backend_rejection"])
        self.assertTrue(gates["Linux_RPM_launch"])
        self.assertTrue(gates["Linux_RPM_stale_backend_rejection"])

    def test_preflight_requires_installers_to_colocate_app_and_backend(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            verifier_path = Path(tmp) / "verify-desktop-installers.py"
            verifier_path.write_text(
                "def verify_msi(): pass\n"
                "def verify_nsis(): pass\n"
                "def find_extracted_linux_executables(): pass\n",
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "DESKTOP_INSTALLER_VERIFIER_PATH",
                verifier_path,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "same directory"):
                    preflight_desktop_release.require_installer_sidecar_colocation_gate()

    def test_preflight_requires_installer_listing_colocation_checks(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            verifier_path = Path(tmp) / "verify-desktop-installers.py"
            verifier_path.write_text(
                "def require_same_directory(): pass\n"
                "must be in the same directory\n"
                "require_same_directory(app, backend, label=label)\n"
                "require_same_directory(app, backend, label=msi.name)\n"
                "require_same_directory(app, backend, label=nsis.name)\n",
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "DESKTOP_INSTALLER_VERIFIER_PATH",
                verifier_path,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "listing"):
                    preflight_desktop_release.require_installer_sidecar_colocation_gate()

    def test_preflight_quality_gates_include_installer_sidecar_colocation(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["installer_sidecar_same_directory"])

    def test_preflight_requires_windows_installer_acl_repair(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            verifier_path = Path(tmp) / "verify-desktop-installers.py"
            verifier_path.write_text(
                "def verify_msi(): pass\n"
                "def verify_nsis(): pass\n",
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "DESKTOP_INSTALLER_VERIFIER_PATH",
                verifier_path,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "ACL"):
                    preflight_desktop_release.require_windows_installer_acl_repair_gate()

    def test_preflight_quality_gates_include_windows_installer_acl_repair(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["windows_installer_acl_repair"])

    def test_preflight_quality_gates_include_desktop_startup_diagnostics_metadata(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["packaged_desktop_startup_diagnostics_metadata"])

    def test_preflight_quality_gates_include_packaged_desktop_metadata_value_smoke(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_github_download_launch_desktop_metadata_gate",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["packaged_desktop_metadata_value_smoke_per_platform"])

    def test_preflight_quality_gates_include_packaged_desktop_startup_failure_recovery_smoke(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["packaged_desktop_startup_failure_recovery_smoke_per_platform"])

    def test_preflight_quality_gates_include_packaged_desktop_startup_failure_recovery_report(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["packaged_desktop_startup_failure_recovery_report"])

    def test_preflight_quality_gates_include_github_download_launch_metadata(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["GitHub_download_launch_desktop_metadata"])
        self.assertTrue(gates["GitHub_download_launch_port_mode"])
        self.assertTrue(gates["GitHub_download_verification_summary"])
        self.assertTrue(gates["release_verification_summary_step_summary"])
        self.assertTrue(gates["startup_failure_recovery_auto_port"])
        self.assertTrue(gates["desktop_smoke_no_proxy_loopback"])
        self.assertTrue(gates["desktop_smoke_windows_cleanup"])

    def test_preflight_requires_live_release_rollback_job(self):
        workflow = preflight_desktop_release.yaml.safe_load(
            preflight_desktop_release.RELEASE_WORKFLOW_PATH.read_text(encoding="utf-8")
        )
        workflow["jobs"].pop("rollback-live-release")

        with self.assertRaisesRegex(ValueError, "rollback-live-release"):
            preflight_desktop_release.require_canary_and_live_quality_gates(workflow)

    def test_preflight_quality_gates_include_live_release_rollback(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["live_release_rollback_on_failed_verification"])

    def test_preflight_requires_smoke_scripts_to_bypass_proxy_for_loopback(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            desktop_script_path = Path(tmp) / "smoke-test-desktop-app.py"
            backend_script_path = Path(tmp) / "smoke-test-backend-sidecar.py"
            desktop_script_path.write_text(
                "from urllib.request import Request, urlopen\n"
                "def request_json():\n"
                "    return urlopen('http://127.0.0.1:1234/api/info')\n",
                encoding="utf-8",
            )
            backend_script_path.write_text(
                "from urllib.request import Request, urlopen\n"
                "def wait_for_info():\n"
                "    return urlopen('http://127.0.0.1:1234/api/info')\n",
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "DESKTOP_SMOKE_SCRIPT_PATH",
                desktop_script_path,
            ), mock.patch.object(
                preflight_desktop_release,
                "BACKEND_SIDECAR_SMOKE_SCRIPT_PATH",
                backend_script_path,
            ):
                with self.assertRaisesRegex(ValueError, "proxy"):
                    preflight_desktop_release.require_smoke_scripts_no_proxy_loopback_gate()

    def test_preflight_requires_windows_safe_desktop_smoke_cleanup(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            desktop_script_path = Path(tmp) / "smoke-test-desktop-app.py"
            desktop_script_path.write_text(
                "import tempfile\n"
                "def verify_desktop_app():\n"
                "    with tempfile.TemporaryDirectory(prefix='cc-branch-desktop-smoke-'):\n"
                "        pass\n",
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "DESKTOP_SMOKE_SCRIPT_PATH",
                desktop_script_path,
            ):
                with self.assertRaisesRegex(ValueError, "Windows file locks"):
                    preflight_desktop_release.require_desktop_smoke_windows_cleanup_gate()

    def test_preflight_requires_desktop_smoke_process_table_port_discovery(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            desktop_script_path = Path(tmp) / "smoke-test-desktop-app.py"
            desktop_script_path.write_text(
                "def wait_for_backend_port(process, timeout):\n"
                "    return 18123, []\n",
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "DESKTOP_SMOKE_SCRIPT_PATH",
                desktop_script_path,
            ):
                with self.assertRaisesRegex(ValueError, "process-table port discovery"):
                    preflight_desktop_release.require_desktop_smoke_process_table_port_discovery_gate()

    def test_preflight_quality_gates_include_desktop_smoke_process_table_port_discovery(self):
        gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["desktop_smoke_process_table_port_discovery"])

    def test_preflight_requires_github_download_launch_metadata_verifier(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            script_path = Path(tmp) / "verify_github_release.py"
            script_path.write_text(
                "\n".join(
                    [
                        "def collect_launch_desktop_metadata(result):",
                        "    return {'launch_desktop_metadata': result}",
                        "def require_launch_desktop_metadata(metadata):",
                        "    return metadata['desktop_version']",
                        "def collect_launch_port_modes(result):",
                        "    return {'linux.appimage': result['port_mode']}",
                        "def require_launch_port_modes(port_modes):",
                        "    return port_modes['linux.appimage']",
                        "def build_verification_summary(**kwargs):",
                        "    return kwargs",
                        "release_state = {'latest_matches_tag': True, 'latest_checked': True, 'is_public': True}",
                        "latest_matches_tag = True",
                        "latest_checked = True",
                        "is_public = True",
                        "public_required = True",
                        "latest_required = True",
                        "public_release_requirement_met = True",
                        "latest_release_requirement_met = True",
                        "all_required_launches_verified = True",
                        "all_required_stale_backend_rejections_verified = True",
                        "all_launch_backend_sources_bundled_sidecar = True",
                        "all_launch_port_modes_auto = True",
                        "all_launch_desktop_metadata_present = True",
                        "launch_port_modes = {'linux.appimage': 'auto'}",
                        "verification_summary = build_verification_summary()",
                        "port_mode = 'auto'",
                        "desktop_platform = 'linux'",
                        "desktop_arch = 'x86_64'",
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(preflight_desktop_release, "GITHUB_RELEASE_VERIFIER_PATH", script_path):
                with self.assertRaisesRegex(ValueError, "expected_desktop_platform_arch"):
                    preflight_desktop_release.require_github_download_launch_desktop_metadata_gate()

    def test_preflight_requires_desktop_startup_metadata_in_smoke_script(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            script_path = Path(tmp) / "smoke-test-desktop-app.py"
            script_path.write_text(
                "\n".join(
                    [
                        "def require_desktop_metadata(info):",
                        "    return {'desktop_version': info['desktop_version'], 'desktop_platform': info['desktop_platform']}",
                        "desktop_metadata = require_desktop_metadata(info)",
                        "result = {**desktop_metadata}",
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(preflight_desktop_release, "DESKTOP_SMOKE_SCRIPT_PATH", script_path):
                with self.assertRaisesRegex(ValueError, "desktop_arch"):
                    preflight_desktop_release.require_desktop_startup_diagnostics_metadata()

    def test_preflight_requires_desktop_smoke_port_mode_report(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            script_path = Path(tmp) / "smoke-test-desktop-app.py"
            script_path.write_text(
                "\n".join(
                    [
                        "def require_desktop_metadata(info):",
                        "    return {'desktop_version': info['desktop_version'], 'desktop_platform': info['desktop_platform'], 'desktop_arch': info['desktop_arch']}",
                        "desktop_metadata = require_desktop_metadata(info, expected_version=expected_version, expected_platform=expected_platform, expected_arch=expected_arch)",
                        "result = {**desktop_metadata}",
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(preflight_desktop_release, "DESKTOP_SMOKE_SCRIPT_PATH", script_path):
                with self.assertRaisesRegex(ValueError, "port_mode"):
                    preflight_desktop_release.require_desktop_startup_diagnostics_metadata()

    def test_preflight_requires_startup_failure_recovery_to_use_auto_port(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            script_path = Path(tmp) / "smoke-test-desktop-app.py"
            script_path.write_text(
                "\n".join(
                    [
                        "def verify_desktop_startup_failure_recovery(executable):",
                        "    return verify_desktop_app(executable)",
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(preflight_desktop_release, "DESKTOP_SMOKE_SCRIPT_PATH", script_path):
                with self.assertRaisesRegex(ValueError, "startup failure recovery.*auto port"):
                    preflight_desktop_release.require_startup_failure_recovery_auto_port_gate()

    def test_preflight_quality_gates_include_release_notes_install_copy(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["release_notes_platform_install_copy"])

    def test_preflight_quality_gates_include_source_code_download_warning(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["release_notes_source_code_warning"])

    def test_preflight_requires_release_notes_copy_report_support_path(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            tmp_path = Path(tmp)
            renderer = tmp_path / "render_desktop_release_notes.py"
            canary = tmp_path / "verify_release_canary.py"
            renderer.write_text("Do not use GitHub's Source code zip or tar.gz downloads\n", encoding="utf-8")
            canary.write_text("drag CC Branch to Applications\n", encoding="utf-8")

            with mock.patch.object(
                preflight_desktop_release,
                "RELEASE_NOTES_RENDERER_PATH",
                renderer,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "RELEASE_CANARY_VERIFIER_PATH",
                canary,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "Copy report"):
                    preflight_desktop_release.require_release_notes_support_copy_report_gate()

    def test_preflight_rejects_release_notes_that_send_reinstall_to_latest(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            tmp_path = Path(tmp)
            renderer = tmp_path / "render_desktop_release_notes.py"
            canary = tmp_path / "verify_release_canary.py"
            renderer.write_text(
                "Copy report\n"
                "attach the report when filing an issue\n"
                "download the latest installer for your platform\n",
                encoding="utf-8",
            )
            canary.write_text(
                "Copy report\n"
                "attach the report when filing an issue\n",
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "RELEASE_NOTES_RENDERER_PATH",
                renderer,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "RELEASE_CANARY_VERIFIER_PATH",
                canary,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "current release"):
                    preflight_desktop_release.require_release_notes_support_copy_report_gate()

    def test_preflight_requires_canary_to_reject_latest_reinstall_guidance(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            tmp_path = Path(tmp)
            renderer = tmp_path / "render_desktop_release_notes.py"
            canary = tmp_path / "verify_release_canary.py"
            renderer.write_text(
                "Copy report\n"
                "attach the report when filing an issue\n"
                "download the installer for your platform from the table above\n",
                encoding="utf-8",
            )
            canary.write_text(
                "Copy report\n"
                "attach the report when filing an issue\n",
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "RELEASE_NOTES_RENDERER_PATH",
                renderer,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "RELEASE_CANARY_VERIFIER_PATH",
                canary,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "current release"):
                    preflight_desktop_release.require_release_notes_support_copy_report_gate()

    def test_preflight_requires_canary_to_reject_floating_latest_download_links(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            tmp_path = Path(tmp)
            renderer = tmp_path / "render_desktop_release_notes.py"
            canary = tmp_path / "verify_release_canary.py"
            renderer.write_text(
                "Copy report\n"
                "attach the report when filing an issue\n"
                "download the installer for your platform from the table above\n",
                encoding="utf-8",
            )
            canary.write_text(
                "Copy report\n"
                "attach the report when filing an issue\n"
                "download the installer for your platform from the table above\n"
                "latest release instead of the current release\n",
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "RELEASE_NOTES_RENDERER_PATH",
                renderer,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "RELEASE_CANARY_VERIFIER_PATH",
                canary,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "floating latest"):
                    preflight_desktop_release.require_release_notes_support_copy_report_gate()

    def test_preflight_requires_canary_to_enforce_download_table_rows(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            tmp_path = Path(tmp)
            renderer = tmp_path / "render_desktop_release_notes.py"
            canary = tmp_path / "verify_release_canary.py"
            renderer.write_text(
                "Copy report\n"
                "attach the report when filing an issue\n"
                "download the installer for your platform from the table above\n",
                encoding="utf-8",
            )
            canary.write_text(
                "Copy report\n"
                "attach the report when filing an issue\n"
                "download the installer for your platform from the table above\n"
                "latest release instead of the current release\n"
                "releases/latest/download\n"
                "linked_release_downloads\n"
                "linked_tag != tag\n"
                "outside the current release\n",
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "RELEASE_NOTES_RENDERER_PATH",
                renderer,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "RELEASE_CANARY_VERIFIER_PATH",
                canary,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "download table"):
                    preflight_desktop_release.require_release_notes_support_copy_report_gate()

    def test_preflight_requires_release_notes_first_launch_guidance(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            tmp_path = Path(tmp)
            renderer = tmp_path / "render_desktop_release_notes.py"
            canary = tmp_path / "verify_release_canary.py"
            renderer.write_text(
                "Copy report\n"
                "attach the report when filing an issue\n"
                "download the installer for your platform from the table above\n",
                encoding="utf-8",
            )
            canary.write_text(
                "Copy report\n"
                "attach the report when filing an issue\n"
                "download the installer for your platform from the table above\n"
                "latest release instead of the current release\n"
                "releases/latest/download\n"
                "linked_release_downloads\n"
                "linked_tag != tag\n"
                "outside the current release\n"
                "table_rows\n"
                "download table\n"
                "Release notes download table is missing recommended asset\n"
                "Local backend ready\n"
                "Add project\n"
                "local directory or SSH workspace\n",
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "RELEASE_NOTES_RENDERER_PATH",
                renderer,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "RELEASE_CANARY_VERIFIER_PATH",
                canary,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "first launch"):
                    preflight_desktop_release.require_release_notes_support_copy_report_gate()

    def test_preflight_quality_gates_include_release_notes_copy_report_support(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_release_notes_support_copy_report_gate",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["release_notes_copy_report_support"])

    def test_preflight_requires_release_checksum_manifest(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            tmp_path = Path(tmp)
            renderer = tmp_path / "render_desktop_release_notes.py"
            canary = tmp_path / "verify_release_canary.py"
            renderer.write_text(
                "CHECKSUMS_ASSET_NAME = 'SHA256SUMS'\nVerify your download\n",
                encoding="utf-8",
            )
            canary.write_text(
                "CHECKSUMS_ASSET_NAME = 'SHA256SUMS'\ndef validate_checksum_manifest(): pass\nchecksum_manifest\n",
                encoding="utf-8",
            )
            workflow = {
                "jobs": {
                    "publish-updater-json": {
                        "steps": [
                            {
                                "name": "Publish complete latest.json",
                                "run": "python scripts/render_desktop_release_notes.py\n",
                            }
                        ]
                    },
                    "canary-release": {
                        "steps": [
                            {
                                "name": "Download canary assets",
                                "run": "gh release download --pattern latest.json\n",
                            }
                        ]
                    },
                }
            }

            with mock.patch.object(
                preflight_desktop_release,
                "RELEASE_NOTES_RENDERER_PATH",
                renderer,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "RELEASE_CANARY_VERIFIER_PATH",
                canary,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "SHA256SUMS"):
                    preflight_desktop_release.require_release_checksum_manifest_gate(workflow)

    def test_preflight_requires_checksum_manifest_to_cover_macos_dmg_downloads(self):
        workflow = {
            "jobs": {
                "publish-updater-json": {
                    "steps": [
                        {
                            "name": "Publish complete latest.json",
                            "run": "\n".join(
                                [
                                    "mac_arm=\"$(pick_asset 'aarch64\\.app\\.tar\\.gz$')\"",
                                    "mac_intel=\"$(pick_asset 'x64\\.app\\.tar\\.gz$')\"",
                                    "win_msi=\"$(pick_asset 'x64_en-US\\.msi$')\"",
                                    "checksum_assets=(",
                                    "  \"$mac_arm\"",
                                    "  \"$mac_intel\"",
                                    "  \"$win_msi\"",
                                    ")",
                                    "gh release download \"$RELEASE_TAG\" --pattern \"$asset\"",
                                    "sha256sum -- \"$asset\"",
                                    "gh release upload \"$RELEASE_TAG\" \"$tmp/SHA256SUMS\"",
                                ]
                            ),
                        }
                    ]
                },
                "canary-release": {
                    "steps": [
                        {
                            "name": "Download canary assets",
                            "run": 'gh release download "$RELEASE_TAG" --pattern "SHA256SUMS"\npython scripts/verify_release_canary.py',
                        }
                    ]
                },
            }
        }

        with self.assertRaisesRegex(ValueError, "macOS DMG"):
            preflight_desktop_release.require_release_checksum_manifest_gate(workflow)

    def test_preflight_quality_gates_include_release_checksum_manifest(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_release_notes_support_copy_report_gate",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_release_checksum_manifest_gate",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["release_checksum_manifest"])

    def test_preflight_requires_backend_failure_current_release_link(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            app_path = Path(tmp) / "App.tsx"
            i18n_path = Path(tmp) / "index.tsx"
            api_client_path = Path(tmp) / "client.ts"
            app_path.write_text("copyReport\nRetry\n", encoding="utf-8")
            i18n_path.write_text("copyReport: 'Copy report'\n", encoding="utf-8")
            api_client_path.write_text("Make sure the backend server is running\n", encoding="utf-8")

            with mock.patch.object(
                preflight_desktop_release,
                "WEB_APP_PATH",
                app_path,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "WEB_I18N_PATH",
                i18n_path,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "WEB_API_CLIENT_PATH",
                api_client_path,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "GitHub Releases"):
                    preflight_desktop_release.require_backend_failure_current_release_gate()

    def test_preflight_rejects_backend_failure_copy_that_uses_latest_release_url(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            app_path = Path(tmp) / "App.tsx"
            i18n_path = Path(tmp) / "index.tsx"
            api_client_path = Path(tmp) / "client.ts"
            app_path.write_text(
                "\n".join(
                    [
                        "const GITHUB_RELEASES_URL = 'https://github.com/GeminiLight/cc-branch/releases';",
                        "https://github.com/GeminiLight/cc-branch/releases/latest",
                        "releaseUrlForBackendFailure",
                        "releases/tag/${tag}",
                        "downloadLatestInstaller",
                        "copyReport",
                        "Open ${releaseUrlForBackendFailure(message)} and reinstall the desktop installer for this platform.",
                    ]
                ),
                encoding="utf-8",
            )
            i18n_path.write_text(
                "\n".join(
                    [
                        "downloadLatestInstaller",
                        "Download latest installer",
                        "下载最新安装包",
                    ]
                ),
                encoding="utf-8",
            )
            api_client_path.write_text(
                "Cannot reach the local CC Branch backend. GitHub Releases page desktop installer for this platform",
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "WEB_APP_PATH",
                app_path,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "WEB_I18N_PATH",
                i18n_path,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "WEB_API_CLIENT_PATH",
                api_client_path,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "releases/latest"):
                    preflight_desktop_release.require_backend_failure_current_release_gate()

    def test_preflight_requires_backend_failure_release_links_to_use_native_shell(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            app_path = Path(tmp) / "App.tsx"
            client_path = Path(tmp) / "client.ts"
            lib_path = Path(tmp) / "lib.rs"
            app_path.write_text(
                "releaseUrlForBackendFailure\nOpen ${releaseUrlForBackendFailure(message)}\n",
                encoding="utf-8",
            )
            client_path.write_text(
                "openExternalUrl(url: string)\nopen_external_url\n",
                encoding="utf-8",
            )
            lib_path.write_text(
                "fn open_external_url() {}\nCommand::new(\"open\")\n",
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "WEB_APP_PATH",
                app_path,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "WEB_API_CLIENT_PATH",
                client_path,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "DESKTOP_TAURI_LIB_PATH",
                lib_path,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "native shell"):
                    preflight_desktop_release.require_backend_failure_native_release_open_gate()

    def test_preflight_requires_desktop_backend_port_retry_for_auto_selected_ports(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            lib_path = Path(tmp) / "lib.rs"
            lib_path.write_text(
                "\n".join(
                    [
                        "fn desktop_backend_port() -> Result<u16, String> {",
                        "    portpicker::pick_unused_port().ok_or_else(|| \"No available port\".to_string())",
                        "}",
                        "fn start_sidecar_server() {",
                        "    let port = desktop_backend_port()?;",
                        "}",
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "DESKTOP_TAURI_LIB_PATH",
                lib_path,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "auto-selected ports"):
                    preflight_desktop_release.require_desktop_backend_port_retry_gate()

    def test_preflight_requires_fixed_desktop_port_to_be_test_gated(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            lib_path = Path(tmp) / "lib.rs"
            lib_path.write_text(
                "\n".join(
                    [
                        'const DESKTOP_BACKEND_PORT_ENV: &str = "CC_BRANCH_DESKTOP_PORT";',
                        "fn desktop_backend_port_from_env() -> Result<Option<u16>, String> {",
                        "    match std::env::var(DESKTOP_BACKEND_PORT_ENV) {",
                        "        Ok(value) => Ok(Some(parse_desktop_backend_port(&value)?)),",
                        "        Err(std::env::VarError::NotPresent) => Ok(None),",
                        "        Err(error) => Err(error.to_string()),",
                        "    }",
                        "}",
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "DESKTOP_TAURI_LIB_PATH",
                lib_path,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "fixed desktop backend port"):
                    preflight_desktop_release.require_desktop_backend_fixed_port_test_gate()

    def test_preflight_requires_sidecar_python_environment_sanitization(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            lib_path = Path(tmp) / "lib.rs"
            lib_path.write_text(
                "\n".join(
                    [
                        "fn start_sidecar_server() {",
                        "    let command = app.shell().sidecar(\"cc-branch-backend\")?.env(WEB_TOKEN_ENV, \"\");",
                        "}",
                    ]
                ),
                encoding="utf-8",
            )
            desktop_smoke_path = Path(tmp) / "smoke-test-desktop-app.py"
            desktop_smoke_path.write_text("def isolated_desktop_env():\n    return {}\n", encoding="utf-8")
            backend_smoke_path = Path(tmp) / "smoke-test-backend-sidecar.py"
            backend_smoke_path.write_text("def isolated_backend_env():\n    return {}\n", encoding="utf-8")

            with mock.patch.object(
                preflight_desktop_release,
                "DESKTOP_TAURI_LIB_PATH",
                lib_path,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "DESKTOP_SMOKE_SCRIPT_PATH",
                desktop_smoke_path,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "BACKEND_SIDECAR_SMOKE_SCRIPT_PATH",
                backend_smoke_path,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "Python environment"):
                    preflight_desktop_release.require_desktop_backend_python_env_sanitized_gate()

    def test_preflight_requires_sidecar_output_in_startup_failure_reports(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            lib_path = Path(tmp) / "lib.rs"
            lib_path.write_text(
                "\n".join(
                    [
                        "fn start_sidecar_server() {",
                        "    eprintln!(\"[cc-branch-backend] failed\");",
                        "}",
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "DESKTOP_TAURI_LIB_PATH",
                lib_path,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "sidecar output"):
                    preflight_desktop_release.require_desktop_backend_output_tail_gate()

    def test_preflight_requires_tauri_backend_readiness_to_bypass_proxy(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            lib_path = Path(tmp) / "lib.rs"
            lib_path.write_text(
                "fn wait_for_server() {\n"
                "    let client = reqwest::blocking::Client::builder().build()?;\n"
                "}\n",
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "DESKTOP_TAURI_LIB_PATH",
                lib_path,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "proxy"):
                    preflight_desktop_release.require_tauri_backend_no_proxy_gate()

    def test_preflight_requires_tauri_backend_startup_to_retry_transient_probe_errors(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            lib_path = Path(tmp) / "lib.rs"
            lib_path.write_text(
                "fn wait_for_server() {\n"
                "    match backend_info_matches_source() {\n"
                "        Err(error) => return Err(error),\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "DESKTOP_TAURI_LIB_PATH",
                lib_path,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "transient backend probe"):
                    preflight_desktop_release.require_tauri_backend_transient_probe_retry_gate()

    def test_preflight_requires_desktop_bundle_output_cleanup_before_tauri_build(self):
        workflow = {
            "jobs": {
                "build": {
                    "steps": [
                        {"name": "Build desktop app and upload release assets", "uses": "tauri-apps/tauri-action@v0"},
                    ]
                }
            }
        }

        with self.assertRaisesRegex(ValueError, "clean previous desktop bundle outputs"):
            preflight_desktop_release.require_desktop_bundle_output_cleanup_gate(workflow)

    def test_preflight_requires_release_workflow_concurrency_by_tag(self):
        workflow = {
            "concurrency": {
                "group": "release-desktop-${{ github.workflow }}",
                "cancel-in-progress": True,
            }
        }

        with self.assertRaisesRegex(ValueError, "concurrency"):
            preflight_desktop_release.require_release_workflow_concurrency_gate(workflow)

    def test_preflight_requires_desktop_webview_fetch_failure_diagnostics(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            api_client_path = Path(tmp) / "client.ts"
            api_client_path.write_text(
                "throw new Error('Cannot reach the local CC Branch backend')\n",
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "WEB_API_CLIENT_PATH",
                api_client_path,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "WebView"):
                    preflight_desktop_release.require_desktop_webview_fetch_diagnostics_gate()

    def test_preflight_requires_desktop_csp_to_allow_only_local_backend_connections(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            config_path = Path(tmp) / "tauri.conf.json"
            config_path.write_text(
                json.dumps({"app": {"security": {"csp": None}}}),
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "TAURI_CONFIG_PATH",
                config_path,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "CSP"):
                    preflight_desktop_release.require_desktop_csp_local_backend_gate()

    def test_preflight_requires_desktop_backend_to_ignore_user_web_token(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            lib_path = Path(tmp) / "lib.rs"
            backend_smoke_path = Path(tmp) / "smoke-test-backend-sidecar.py"
            desktop_smoke_path = Path(tmp) / "smoke-test-desktop-app.py"
            desktop_backend_path = Path(tmp) / "desktop_backend.py"
            lib_path.write_text(
                'const WEB_TOKEN_ENV: &str = "CC_BRANCH_WEB_TOKEN";\n'
                'command.env(WEB_TOKEN_ENV, "").env(WEB_TOKEN_ENV, "");\n',
                encoding="utf-8",
            )
            backend_smoke_path.write_text('env["CC_BRANCH_WEB_TOKEN"] = ""\n', encoding="utf-8")
            desktop_smoke_path.write_text('env["CC_BRANCH_WEB_TOKEN"] = ""\n', encoding="utf-8")
            desktop_backend_path.write_text(
                'default=os.environ.get("CC_BRANCH_WEB_TOKEN")\n',
                encoding="utf-8",
            )

            with mock.patch.object(
                preflight_desktop_release,
                "DESKTOP_TAURI_LIB_PATH",
                lib_path,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "BACKEND_SIDECAR_SMOKE_SCRIPT_PATH",
                backend_smoke_path,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "DESKTOP_SMOKE_SCRIPT_PATH",
                desktop_smoke_path,
                create=True,
            ), mock.patch.object(
                preflight_desktop_release,
                "DESKTOP_BACKEND_ENTRYPOINT_PATH",
                desktop_backend_path,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "CC_BRANCH_WEB_TOKEN"):
                    preflight_desktop_release.require_desktop_backend_ignores_user_web_token_gate()

    def test_preflight_quality_gates_include_backend_failure_current_release_link(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_backend_failure_current_release_gate",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_backend_failure_native_release_open_gate",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["backend_failure_current_release_link"])
        self.assertTrue(gates["backend_failure_native_release_open"])

    def test_preflight_quality_gates_include_desktop_backend_port_retry(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_desktop_backend_port_retry_gate",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_desktop_backend_fixed_port_test_gate",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_desktop_backend_python_env_sanitized_gate",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_desktop_backend_output_tail_gate",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_tauri_backend_no_proxy_gate",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_tauri_backend_transient_probe_retry_gate",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_desktop_bundle_output_cleanup_gate",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_release_workflow_concurrency_gate",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_desktop_webview_fetch_diagnostics_gate",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_desktop_csp_local_backend_gate",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_desktop_backend_ignores_user_web_token_gate",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["desktop_backend_port_retry"])
        self.assertTrue(gates["desktop_backend_fixed_port_test_gate"])
        self.assertTrue(gates["desktop_backend_python_env_sanitized"])
        self.assertTrue(gates["desktop_backend_output_tail"])
        self.assertTrue(gates["tauri_backend_no_proxy_loopback"])
        self.assertTrue(gates["tauri_backend_transient_probe_retry"])
        self.assertTrue(gates["desktop_bundle_output_cleanup"])
        self.assertTrue(gates["release_workflow_concurrency"])
        self.assertTrue(gates["desktop_webview_fetch_diagnostics"])
        self.assertTrue(gates["desktop_csp_local_backend"])
        self.assertTrue(gates["desktop_backend_ignores_user_web_token"])

    def test_preflight_rejects_release_workflow_missing_required_action_refs(self):
        workflow = {
            "jobs": {
                "build": {
                    "steps": [
                        {"uses": "actions/checkout@v5"},
                        {"uses": "actions/setup-node@v6"},
                        {"uses": "actions/setup-python@v6"},
                        {"uses": "dtolnay/rust-toolchain@stable"},
                        {"uses": "tauri-apps/tauri-action@v0"},
                        {"uses": "actions/upload-artifact@v7"},
                    ]
                }
            }
        }

        with self.assertRaisesRegex(ValueError, "actions/checkout@v6"):
            preflight_desktop_release.require_release_workflow_action_refs(workflow)

    def test_preflight_quality_gates_include_release_workflow_action_refs(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_release_workflow_action_refs",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["release_workflow_action_refs"])

    def test_preflight_quality_gates_include_release_workflow_bash_syntax(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_release_workflow_bash_syntax",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["release_workflow_bash_syntax"])

    def test_preflight_quality_gates_include_desktop_smoke_report_artifact_upload(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_desktop_smoke_report_artifact_gate",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["desktop_smoke_report_artifact_upload"])

    def test_preflight_quality_gates_include_release_verification_expected_version(self):
        with mock.patch.object(
            preflight_desktop_release,
            "require_build_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_canary_and_live_quality_gates",
        ), mock.patch.object(
            preflight_desktop_release,
            "require_desktop_smoke_report_artifact_gate",
        ), mock.patch.object(
            preflight_desktop_release.yaml,
            "safe_load",
            return_value={},
        ):
            gates = preflight_desktop_release.require_release_quality_gates()

        self.assertTrue(gates["release_verification_expected_version"])

    def test_preflight_requires_release_verification_summary_to_report_notes_checks(self):
        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            script_path = Path(tmp) / "verify_github_release.py"
            script_text = preflight_desktop_release.GITHUB_RELEASE_VERIFIER_PATH.read_text(encoding="utf-8")
            script_text = script_text.replace('"release_notes_verified": release_notes_checked,', "")
            script_text = script_text.replace('"latest_json_notes_verified": latest_json_notes_checked,', "")
            script_path.write_text(script_text, encoding="utf-8")

            with mock.patch.object(
                preflight_desktop_release,
                "GITHUB_RELEASE_VERIFIER_PATH",
                script_path,
                create=True,
            ):
                with self.assertRaisesRegex(ValueError, "release_notes_verified"):
                    preflight_desktop_release.require_github_download_launch_desktop_metadata_gate()

    def test_preflight_rejects_live_verification_without_public_release_assertion_in_run_step(self):
        def fake_run_json(command: list[str]) -> dict:
            if command[:3] == ["gh", "api", "repos/owner/repo/actions/permissions"]:
                return {"enabled": True, "allowed_actions": "all"}
            if command[:3] == ["gh", "api", "repos/owner/repo/actions/permissions/workflow"]:
                return {"default_workflow_permissions": "read"}
            raise AssertionError(f"Unexpected json command: {command}")

        def fake_run_text(command: list[str], *, check: bool = True) -> str:
            if command[:3] == ["gh", "workflow", "list"]:
                return "Release Desktop App\tactive\t267280456\n"
            if command[:3] == ["gh", "secret", "list"]:
                return "\n".join(f"{name}\t2026-05-18T00:00:00Z" for name in preflight_desktop_release.REQUIRED_SECRETS)
            if command[:2] == ["git", "ls-remote"]:
                return ""
            if command[:3] == ["gh", "release", "view"]:
                return ""
            raise AssertionError(f"Unexpected text command: {command}")

        workflow = {
            "name": "Release Desktop App",
            "permissions": {"contents": "write"},
            "jobs": {
                "action-refs": {
                    "steps": [
                        {"uses": "actions/checkout@v6"},
                        {"uses": "actions/setup-node@v6"},
                        {"uses": "actions/setup-python@v6"},
                        {"uses": "dtolnay/rust-toolchain@stable"},
                        {"uses": "tauri-apps/tauri-action@v0"},
                    ]
                },
                "build": {
                    "steps": [
                        {
                            "name": "Smoke test bundled backend sidecar",
                            "run": 'python scripts/smoke-test-backend-sidecar.py sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"',
                        },
                        {
                            "name": "Smoke test packaged macOS desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Smoke test packaged Linux desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Smoke test packaged Windows desktop app",
                            "run": 'python scripts/smoke-test-desktop-app.py app --use-auto-port --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure\npython scripts/smoke-test-desktop-app.py app --expect-startup-failure-recovery --recovery-sidecar sidecar --expected-version "${{ inputs.release_tag || github.ref_name }}" --expected-platform "${{ matrix.desktop-platform }}" --expected-arch "${{ matrix.desktop-arch }}"\npython scripts/smoke-test-desktop-app.py app --expect-stale-backend-rejection',
                        },
                        {
                            "name": "Verify macOS DMG contains backend sidecar",
                            "run": "python scripts/verify-macos-dmg.py dmg --launch-app --verify-installed-copy --verify-stale-backend-rejection --expected-version \"$version\"",
                        },
                        {
                            "name": "Verify Linux installers contain backend sidecar",
                            "run": "python scripts/verify-desktop-installers.py --platform linux --launch-linux-packages --launch-appimage --expected-version \"$version\"",
                        },
                        {
                            "name": "Verify Windows installers contain backend sidecar",
                            "run": "python scripts/verify-desktop-installers.py --platform windows --launch-windows-msi --launch-windows-nsis --expected-version \"$version\"",
                        },
                        {
                            "name": "Upload desktop smoke reports",
                            "if": "always()",
                            "uses": "actions/upload-artifact@v7",
                            "with": {
                                "name": "desktop-smoke-reports-${{ matrix.platform }}-${{ matrix.sidecar-target }}",
                                "path": "smoke-reports/*.json",
                                "if-no-files-found": "error",
                            },
                        },
                    ]
                },
                "canary-installers": {
                    "needs": "publish-updater-json",
                    "strategy": {
                        "matrix": {
                            "include": [
                                {"platform": "mac-apple-silicon", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-aarch64"},
                                {"platform": "mac-intel", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-x86_64"},
                                {"platform": "linux", "verifier-args": "--skip-dmg --verify-linux-installers --launch-linux-packages --launch-linux-appimage"},
                                {"platform": "windows", "verifier-args": "--skip-dmg --verify-windows-installer --launch-windows-msi --launch-windows-nsis"},
                            ]
                        }
                    },
                    "steps": [
                        {
                            "name": "Download and verify draft installer assets",
                            "run": "python scripts/verify_github_release.py tag --expected-version \"$version\" ${{ matrix.verifier-args }}" + RELEASE_VERIFICATION_SUMMARY_SNIPPET,
                        }
                    ],
                },
                "publish-release": {
                    "needs": ["canary-release", "canary-installers"],
                    "steps": [{"name": "Publish draft release", "run": "gh release edit \"$RELEASE_TAG\" --draft=false --prerelease=false --latest"}],
                },
                "verify-live-release": {
                    "needs": "publish-release",
                    "strategy": {
                        "matrix": {
                            "include": [
                                {"platform": "mac-apple-silicon", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-aarch64"},
                                {"platform": "mac-intel", "verifier-args": "--verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper --sample-platform darwin-x86_64"},
                                {"platform": "linux", "verifier-args": "--skip-dmg --verify-linux-installers --launch-linux-packages --launch-linux-appimage"},
                                {"platform": "windows", "verifier-args": "--skip-dmg --verify-windows-installer --launch-windows-msi --launch-windows-nsis"},
                            ]
                        }
                    },
                    "steps": [
                        {
                            "name": "Download and verify published assets",
                            "run": "python scripts/verify_github_release.py tag --expected-version \"$version\" --require-latest ${{ matrix.verifier-args }}",
                        }
                    ],
                },
            },
        }
        workflow_text = preflight_desktop_release.yaml.safe_dump(workflow)
        workflow_text += "\n# --require-public\n"

        with tempfile.TemporaryDirectory(dir=preflight_desktop_release.ROOT) as tmp:
            workflow_path = Path(tmp) / "release-desktop.yml"
            workflow_path.write_text(workflow_text, encoding="utf-8")
            with mock.patch.object(preflight_desktop_release, "RELEASE_WORKFLOW_PATH", workflow_path), \
                 mock.patch.object(preflight_desktop_release, "verify_versions", return_value={"ok": True, "version": "1.0.2"}), \
                 mock.patch.object(preflight_desktop_release, "run_json", side_effect=fake_run_json), \
                 mock.patch.object(preflight_desktop_release, "run_text", side_effect=fake_run_text):
                with self.assertRaisesRegex(ValueError, "live.*--require-public"):
                    preflight_desktop_release.preflight("v1.0.2", "owner/repo")


if __name__ == "__main__":
    unittest.main()
