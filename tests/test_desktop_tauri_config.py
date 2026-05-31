from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from xml.etree import ElementTree

import yaml

ROOT = Path(__file__).resolve().parents[1]
TAURI_DIR = ROOT / "apps" / "desktop" / "src-tauri"


class DesktopTauriConfigTests(unittest.TestCase):
    def test_desktop_product_name_uses_human_readable_app_bundle_name(self):
        config = json.loads((TAURI_DIR / "tauri.conf.json").read_text(encoding="utf-8"))

        self.assertEqual(config["productName"], "CC Branch")

    def test_macos_entitlements_disable_library_validation_for_pyinstaller_sidecar(self):
        config = json.loads((TAURI_DIR / "tauri.conf.json").read_text(encoding="utf-8"))
        entitlements = config["bundle"]["macOS"]["entitlements"]
        self.assertEqual(entitlements, "entitlements.plist")

        tree = ElementTree.parse(TAURI_DIR / entitlements)
        keys = [
            element.text
            for element in tree.findall("./dict/key")
        ]
        self.assertIn("com.apple.security.cs.disable-library-validation", keys)

    def test_updater_artifacts_and_signed_release_endpoint_are_configured(self):
        config = json.loads((TAURI_DIR / "tauri.conf.json").read_text(encoding="utf-8"))
        updater = config["plugins"]["updater"]

        self.assertFalse(config["bundle"]["createUpdaterArtifacts"])
        self.assertIn("https://github.com/GeminiLight/cc-branch/releases/latest/download/latest.json", updater["endpoints"])
        self.assertGreater(len(updater["pubkey"]), 80)
        self.assertEqual(updater["windows"]["installMode"], "passive")

    def test_desktop_capabilities_allow_updater_and_relaunch(self):
        capabilities = json.loads((TAURI_DIR / "capabilities/default.json").read_text(encoding="utf-8"))

        self.assertIn("updater:default", capabilities["permissions"])
        self.assertIn("process:default", capabilities["permissions"])

    def test_desktop_csp_allows_only_local_backend_connections(self):
        config = json.loads((TAURI_DIR / "tauri.conf.json").read_text(encoding="utf-8"))
        csp = config["app"]["security"]["csp"]

        self.assertIsInstance(csp, str)
        self.assertIn("default-src 'self'", csp)
        self.assertIn("connect-src 'self' http://127.0.0.1:* http://localhost:* ws:", csp)
        self.assertNotIn("connect-src *", csp)
        self.assertNotIn("https:", csp)

    def test_macos_release_builds_app_bundle_for_updater_metadata(self):
        workflow = (ROOT / ".github" / "workflows" / "release-desktop.yml").read_text(encoding="utf-8")

        self.assertIn("--target aarch64-apple-darwin --bundles app,dmg", workflow)
        self.assertIn("--target x86_64-apple-darwin --bundles app,dmg", workflow)
        self.assertIn('"createUpdaterArtifacts":true', workflow)
        self.assertIn("includeUpdaterJson: false", workflow)
        self.assertIn("publish-updater-json:", workflow)
        self.assertIn("uses: actions/checkout@v6", workflow)
        self.assertIn("canary-installers:", workflow)
        self.assertIn("Canary installer downloads", workflow)
        self.assertIn("publish-release:", workflow)
        self.assertIn("verify-live-release:", workflow)
        self.assertIn("Verify live GitHub downloads", workflow)
        self.assertIn("verifier-args: --verify-dmg --launch-dmg-app --verify-dmg-installed-copy --verify-macos-gatekeeper", workflow)
        self.assertIn("verifier-args: --skip-dmg --verify-linux-installers --launch-linux-packages --launch-linux-appimage", workflow)
        self.assertIn("verifier-args: --skip-dmg --verify-windows-installer --launch-windows-msi --launch-windows-nsis", workflow)
        self.assertIn("Download and verify draft installer assets", workflow)
        self.assertIn("needs.canary-installers.result == 'success'", workflow)
        self.assertIn("github-release-verification-draft-${{ matrix.platform }}.json", workflow)
        self.assertIn("Upload draft installer verification report", workflow)
        self.assertIn("draft-installer-verification-${{ matrix.platform }}", workflow)
        self.assertIn("github-release-verification-live-${{ matrix.platform }}.json", workflow)
        self.assertIn("Upload live installer verification report", workflow)
        self.assertIn("live-installer-verification-${{ matrix.platform }}", workflow)
        self.assertIn("#### Verification summary", workflow)
        self.assertIn("verification_summary missing from release verification report", workflow)
        self.assertIn("json.dumps(report['verification_summary']", workflow)
        self.assertIn("Install Linux verifier tools", workflow)
        self.assertIn("libwebkit2gtk-4.1-dev", workflow)
        self.assertIn("libappindicator3-dev", workflow)
        self.assertIn("librsvg2-dev", workflow)
        self.assertIn('"darwin-aarch64"', workflow)
        self.assertIn('"darwin-x86_64"', workflow)
        self.assertIn("Verify release version matches tag", workflow)
        self.assertIn("scripts/verify_release_version.py --expected \"$RELEASE_TAG\" --require-v-prefix", workflow)
        self.assertIn("Notarize and replace macOS DMG asset", workflow)
        self.assertIn("Smoke test bundled backend sidecar", workflow)
        self.assertIn("scripts/smoke-test-backend-sidecar.py", workflow)
        self.assertIn("scripts/smoke-test-desktop-app.py", workflow)
        self.assertIn("--use-auto-port", workflow)
        self.assertIn("--expect-startup-failure", workflow)
        self.assertIn("--expect-stale-backend-rejection", workflow)
        self.assertIn("smoke-reports/desktop-app-missing-sidecar-", workflow)
        self.assertIn('missing_sidecar_app="$missing_sidecar_dir/CC Branch.app"', workflow)
        self.assertIn('cp -R "$app_path" "$missing_sidecar_app"', workflow)
        self.assertIn('rm -f "$missing_sidecar_app/Contents/MacOS/cc-branch-backend"', workflow)
        self.assertIn("smoke-reports/desktop-app-stale-backend-", workflow)
        self.assertIn("smoke-reports/backend-sidecar-", workflow)
        self.assertIn("smoke-reports/desktop-app-", workflow)
        self.assertIn("GITHUB_STEP_SUMMARY", workflow)
        self.assertIn("Upload desktop smoke reports", workflow)
        self.assertIn("uses: actions/upload-artifact@v7", workflow)
        self.assertIn("if-no-files-found: error", workflow)
        self.assertIn("smoke-reports/dmg-verification-", workflow)
        self.assertIn("smoke-reports/linux-installers-", workflow)
        self.assertIn("smoke-reports/windows-installers-", workflow)
        self.assertIn("Smoke test packaged Linux desktop app", workflow)
        self.assertIn("Smoke test packaged Windows desktop app", workflow)
        self.assertIn("xvfb-run -a python scripts/smoke-test-desktop-app.py", workflow)
        self.assertIn("xvfb-run -a python scripts/verify-desktop-installers.py", workflow)
        self.assertIn("--launch-appimage", workflow)
        self.assertIn("--launch-linux-packages", workflow)
        self.assertIn("--launch-linux-appimage", workflow)
        self.assertIn("--launch-windows-msi", workflow)
        self.assertIn("--launch-windows-nsis", workflow)
        self.assertIn("xvfb-run -a python scripts/verify_github_release.py", workflow)
        self.assertIn("apps/desktop/src-tauri/target/release/cc-branch.exe", workflow)
        self.assertIn("scripts/verify-macos-dmg.py", workflow)
        self.assertIn('python scripts/verify-macos-dmg.py "$dmg_path" --launch-app --verify-installed-copy --verify-stale-backend-rejection --expected-version "$version"', workflow)
        self.assertIn("scripts/verify-desktop-installers.py", workflow)
        self.assertIn("scripts/verify_github_release.py", workflow)
        self.assertIn("scripts/render_desktop_release_notes.py", workflow)
        self.assertIn("--notes-file \"$release_notes\"", workflow)
        self.assertIn("notes=\"$(cat \"$release_notes\")\"", workflow)
        self.assertNotIn("notes=\"$(gh release view", workflow)
        self.assertIn("Download the right installer", (ROOT / "scripts" / "render_desktop_release_notes.py").read_text(encoding="utf-8"))
        self.assertIn("--verify-dmg", workflow)
        self.assertIn("--launch-app", workflow)
        self.assertIn("--verify-installed-copy", workflow)
        self.assertIn("--launch-dmg-app", workflow)
        self.assertIn("--verify-dmg-installed-copy", workflow)
        self.assertIn("--verify-macos-gatekeeper", workflow)
        self.assertIn("--require-latest", workflow)
        self.assertIn("--require-public", workflow)
        self.assertIn("--platform linux", workflow)
        self.assertIn('--expected-version "$version"', workflow)
        self.assertIn("--platform windows", workflow)
        self.assertIn("--expected-version $version `", workflow)
        self.assertIn("rpm cpio", workflow)
        self.assertIn("--expected-version \"$version\"", workflow)
        self.assertIn("--assets-json \"$assets_json\"", workflow)
        self.assertIn("--release-body-file \"$release_body\"", workflow)
        self.assertIn("macos_updater_assets=", workflow)
        self.assertIn("grep -E '\\.app\\.tar\\.gz$'", workflow)
        self.assertIn("--pattern \"*.sig\"", workflow)
        self.assertIn("while IFS= read -r updater_asset", workflow)
        self.assertIn("xcrun notarytool submit", workflow)
        self.assertIn("xcrun stapler staple", workflow)
        self.assertIn("pick_asset 'aarch64\\.app\\.tar\\.gz$'", workflow)
        self.assertIn("urllib.parse.quote", workflow)

    def test_macos_notarization_shell_step_is_syntactically_valid(self):
        workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "release-desktop.yml").read_text(encoding="utf-8"))
        build_steps = workflow["jobs"]["build"]["steps"]
        step = next(
            step
            for step in build_steps
            if step.get("name") == "Notarize and replace macOS DMG asset"
        )

        result = subprocess.run(
            ["bash", "-n"],
            input=step["run"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_publish_updater_json_shell_step_is_syntactically_valid(self):
        workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "release-desktop.yml").read_text(encoding="utf-8"))
        steps = workflow["jobs"]["publish-updater-json"]["steps"]
        step = next(
            step
            for step in steps
            if step.get("name") == "Publish complete latest.json"
        )

        result = subprocess.run(
            ["bash", "-n"],
            input=step["run"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_publish_updater_json_rejects_ambiguous_asset_matches(self):
        workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "release-desktop.yml").read_text(encoding="utf-8"))
        steps = workflow["jobs"]["publish-updater-json"]["steps"]
        step = next(
            step
            for step in steps
            if step.get("name") == "Publish complete latest.json"
        )

        self.assertIn("match_count=", step["run"])
        self.assertIn('[ "$match_count" -gt 1 ]', step["run"])
        self.assertIn("Multiple release assets matching pattern", step["run"])

    def test_release_workflow_rejects_ambiguous_generated_artifact_matches(self):
        workflow = (ROOT / ".github" / "workflows" / "release-desktop.yml").read_text(encoding="utf-8")

        self.assertNotIn("head -n 1", workflow)
        self.assertIn("Multiple generated macOS app bundles", workflow)
        self.assertIn("Multiple generated macOS DMGs", workflow)
        self.assertIn("Multiple macOS Apple Silicon updater assets", workflow)

    def test_release_workflow_serializes_runs_for_same_release_tag(self):
        workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "release-desktop.yml").read_text(encoding="utf-8"))
        concurrency = workflow["concurrency"]

        self.assertIn("release-desktop", concurrency["group"])
        self.assertIn("inputs.release_tag || github.ref_name", concurrency["group"])
        self.assertFalse(concurrency["cancel-in-progress"])

    def test_release_workflow_cleans_old_bundle_outputs_before_build(self):
        workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "release-desktop.yml").read_text(encoding="utf-8"))
        steps = workflow["jobs"]["build"]["steps"]
        step_names = [step.get("name") for step in steps]

        clean_index = step_names.index("Clean previous desktop bundle outputs")
        build_index = step_names.index("Build desktop app and upload release assets")
        self.assertLess(clean_index, build_index)

        clean_step = steps[clean_index]
        self.assertEqual(clean_step["shell"], "bash")
        self.assertIn("find apps/desktop/src-tauri/target", clean_step["run"])
        self.assertIn("*/release/bundle", clean_step["run"])
        self.assertIn("rm -rf", clean_step["run"])

    def test_windows_missing_sidecar_smoke_uses_clean_temp_directory(self):
        workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "release-desktop.yml").read_text(encoding="utf-8"))
        steps = workflow["jobs"]["build"]["steps"]
        step = next(
            step
            for step in steps
            if step.get("name") == "Smoke test packaged Windows desktop app"
        )

        self.assertIn('$missingSidecarDir = Join-Path $env:RUNNER_TEMP "cc-branch-missing-sidecar"', step["run"])
        self.assertIn("Remove-Item -Recurse -Force $missingSidecarDir", step["run"])
        self.assertLess(
            step["run"].index("Remove-Item -Recurse -Force $missingSidecarDir"),
            step["run"].index("New-Item -ItemType Directory -Force -Path $missingSidecarDir"),
        )

    def test_desktop_release_body_has_no_duplicate_headings(self):
        workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "release-desktop.yml").read_text(encoding="utf-8"))
        steps = workflow["jobs"]["build"]["steps"]
        step = next(
            step
            for step in steps
            if step.get("name") == "Build desktop app and upload release assets"
        )
        body = step["with"]["releaseBody"]
        headings = [line.strip() for line in body.splitlines() if line.strip().startswith("#")]

        self.assertEqual(len(headings), len(set(headings)))

    def test_publish_release_marks_release_public_non_prerelease_and_latest(self):
        workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "release-desktop.yml").read_text(encoding="utf-8"))
        steps = workflow["jobs"]["publish-release"]["steps"]
        step = next(
            step
            for step in steps
            if step.get("name") == "Publish draft release"
        )

        self.assertIn('gh release edit "$RELEASE_TAG"', step["run"])
        self.assertIn("--draft=false", step["run"])
        self.assertIn("--prerelease=false", step["run"])
        self.assertIn("--latest", step["run"])

    def test_release_workflow_rolls_back_public_release_when_live_verification_fails(self):
        workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "release-desktop.yml").read_text(encoding="utf-8"))
        job = workflow["jobs"]["rollback-live-release"]

        self.assertEqual(set(job["needs"]), {"publish-release", "verify-live-release"})
        self.assertIn("always()", job["if"])
        self.assertIn("needs.publish-release.result == 'success'", job["if"])
        self.assertIn("needs.verify-live-release.result != 'success'", job["if"])
        step = next(
            step
            for step in job["steps"]
            if step.get("name") == "Rollback failed live release"
        )
        self.assertIn('gh release edit "$RELEASE_TAG"', step["run"])
        self.assertIn("--draft=true", step["run"])
        self.assertIn("--prerelease=true", step["run"])

    def test_release_workflow_uses_current_checkout_action_everywhere(self):
        workflow_path = ROOT / ".github" / "workflows" / "release-desktop.yml"
        workflow = workflow_path.read_text(encoding="utf-8")

        self.assertNotIn("uses: actions/checkout@v4", workflow)
        self.assertGreaterEqual(workflow.count("uses: actions/checkout@v6"), 5)

        data = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        checkout_steps = [
            step
            for job in data["jobs"].values()
            for step in job.get("steps", [])
            if step.get("uses") == "actions/checkout@v6"
        ]
        self.assertGreaterEqual(len(checkout_steps), 5)
        for step in checkout_steps:
            self.assertEqual(
                step.get("with", {}).get("ref"),
                "${{ inputs.release_tag || github.ref }}",
            )

    def test_canary_release_uploads_verification_report(self):
        workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "release-desktop.yml").read_text(encoding="utf-8"))
        steps = workflow["jobs"]["canary-release"]["steps"]
        run_step = next(
            step
            for step in steps
            if step.get("name") == "Download canary assets"
        )

        self.assertIn("release-verification/release-canary-verification.json", run_step["run"])
        self.assertIn("tee \"$report\"", run_step["run"])
        self.assertIn("GITHUB_STEP_SUMMARY", run_step["run"])
        self.assertTrue(any(step.get("name") == "Upload release canary verification report" for step in steps))
        upload_step = next(
            step
            for step in steps
            if step.get("name") == "Upload release canary verification report"
        )
        self.assertEqual(upload_step["with"]["name"], "release-canary-verification")
        self.assertEqual(upload_step["with"]["if-no-files-found"], "error")

    def test_tauri_backend_ready_reflects_http_health_not_only_process_handle(self):
        source = (TAURI_DIR / "src" / "lib.rs").read_text(encoding="utf-8")

        self.assertIn("fn backend_http_ready", source)
        self.assertIn("http://127.0.0.1:{}/api/info", source)
        self.assertIn("Desktop backend process is not responding", source)
        self.assertIn("expected_backend_source: &str", source)
        self.assertIn(".json::<serde_json::Value>()", source)
        self.assertIn('.get("backend_source")', source)
        self.assertIn("Unexpected backend source", source)
        self.assertIn("fn backend_http_ready(", source)
        self.assertIn("Err(error) => return (false, Some(error))", source)

    def test_tauri_backend_readiness_rejects_stale_backend_workspace_paths(self):
        source = (TAURI_DIR / "src" / "lib.rs").read_text(encoding="utf-8")

        self.assertIn("expected_config_path: &str", source)
        self.assertIn("expected_state_path: &str", source)
        self.assertIn('.get("config_path")', source)
        self.assertIn('.get("state_path")', source)
        self.assertIn("Unexpected backend config path", source)
        self.assertIn("Unexpected backend state path", source)
        self.assertIn("Err(BackendProbeError::Fatal(error)) => return Err(error)", source)

    def test_tauri_backend_startup_retries_transient_probe_errors(self):
        source = (TAURI_DIR / "src" / "lib.rs").read_text(encoding="utf-8")

        self.assertIn("enum BackendProbeError", source)
        self.assertIn("Transient(String)", source)
        self.assertIn("Fatal(String)", source)
        self.assertIn("BackendProbeError::Transient(e.to_string())", source)
        self.assertIn("Err(BackendProbeError::Transient(error))", source)
        self.assertIn("last_transient_error = Some(error)", source)
        self.assertIn("Err(BackendProbeError::Fatal(error)) => return Err(error)", source)

    def test_tauri_backend_startup_errors_include_sidecar_output_tail(self):
        source = (TAURI_DIR / "src" / "lib.rs").read_text(encoding="utf-8")

        self.assertIn("BackendLogBuffer", source)
        self.assertIn("push_backend_log", source)
        self.assertIn("backend_log_tail", source)
        self.assertIn("Bundled backend output:", source)
        self.assertIn("stdout", source)
        self.assertIn("stderr", source)

    def test_tauri_backend_readiness_validates_desktop_metadata(self):
        source = (TAURI_DIR / "src" / "lib.rs").read_text(encoding="utf-8")

        self.assertIn("expected_desktop_version: &str", source)
        self.assertIn("expected_desktop_platform: &str", source)
        self.assertIn("expected_desktop_arch: &str", source)
        self.assertIn('.get("desktop_version")', source)
        self.assertIn('.get("desktop_platform")', source)
        self.assertIn('.get("desktop_arch")', source)
        self.assertIn("Unexpected backend desktop version", source)
        self.assertIn("Unexpected backend desktop platform", source)
        self.assertIn("Unexpected backend desktop arch", source)

    def test_tauri_backend_readiness_ignores_system_proxy_for_loopback(self):
        source = (TAURI_DIR / "src" / "lib.rs").read_text(encoding="utf-8")

        self.assertIn("fn backend_http_client", source)
        self.assertIn(".no_proxy()", source)
        self.assertIn("backend_http_client(Duration::from_secs(2))", source)
        self.assertIn("backend_http_client(Duration::from_millis(600))", source)

    def test_tauri_marks_bundled_sidecar_backend_source(self):
        source = (TAURI_DIR / "src" / "lib.rs").read_text(encoding="utf-8")

        self.assertIn("CC_BRANCH_BACKEND_SOURCE", source)
        self.assertIn("bundled-sidecar", source)
        self.assertIn("python-fallback", source)

    def test_tauri_passes_desktop_metadata_to_backend_process(self):
        source = (TAURI_DIR / "src" / "lib.rs").read_text(encoding="utf-8")

        self.assertIn("CC_BRANCH_DESKTOP_VERSION", source)
        self.assertIn("CC_BRANCH_DESKTOP_PLATFORM", source)
        self.assertIn("CC_BRANCH_DESKTOP_ARCH", source)
        self.assertIn("fn desktop_platform()", source)
        self.assertIn('"darwin"', source)
        self.assertIn(".env(DESKTOP_VERSION_ENV", source)
        self.assertIn(".env(DESKTOP_PLATFORM_ENV", source)
        self.assertIn(".env(DESKTOP_ARCH_ENV", source)

    def test_tauri_desktop_backend_ignores_user_web_token_environment(self):
        source = (TAURI_DIR / "src" / "lib.rs").read_text(encoding="utf-8")

        self.assertIn('const WEB_TOKEN_ENV: &str = "CC_BRANCH_WEB_TOKEN"', source)
        self.assertGreaterEqual(source.count(".env(WEB_TOKEN_ENV, \"\")"), 2)

    def test_tauri_sidecar_sanitizes_python_environment_before_launch(self):
        source = (TAURI_DIR / "src" / "lib.rs").read_text(encoding="utf-8")

        self.assertIn("DESKTOP_BACKEND_POISON_ENV", source)
        self.assertIn('"PYTHONHOME"', source)
        self.assertIn('"PYTHONPATH"', source)
        self.assertIn('"VIRTUAL_ENV"', source)
        self.assertIn('"CONDA_PREFIX"', source)
        self.assertIn('"LD_LIBRARY_PATH"', source)
        self.assertIn('"DYLD_LIBRARY_PATH"', source)
        self.assertIn("sanitized_backend_environment", source)
        self.assertIn(".env_clear()", source)
        self.assertIn(".envs(sanitized_backend_environment())", source)

    def test_release_build_does_not_fall_back_to_user_python(self):
        source = (TAURI_DIR / "src" / "lib.rs").read_text(encoding="utf-8")

        self.assertIn("Python fallback is disabled in release builds", source)
        self.assertIn("if cfg!(debug_assertions) {\n                match start_python_server", source)

    def test_tauri_backend_retry_can_restart_backend_process(self):
        source = (TAURI_DIR / "src" / "lib.rs").read_text(encoding="utf-8")

        self.assertIn("fn restart_backend", source)
        self.assertIn("start_backend_runtime(&app", source)
        self.assertIn("restart_backend,", source)
        self.assertIn("runtime.process.take()", source)

    def test_tauri_can_reveal_desktop_app_for_uninstall_flow(self):
        source = (TAURI_DIR / "src" / "lib.rs").read_text(encoding="utf-8")

        self.assertIn("fn reveal_desktop_app", source)
        self.assertIn("desktop_app_path()", source)
        self.assertIn("reveal_desktop_app,", source)

    def test_tauri_opens_release_support_links_through_native_shell(self):
        source = (TAURI_DIR / "src" / "lib.rs").read_text(encoding="utf-8")

        self.assertIn("const GITHUB_RELEASES_URL_PREFIX", source)
        self.assertIn("fn validate_external_release_url", source)
        self.assertIn("fn open_external_url", source)
        self.assertIn("open_external_url,", source)
        self.assertIn('Command::new("open")', source)
        self.assertIn('Command::new("cmd")', source)
        self.assertIn('Command::new("xdg-open")', source)
        self.assertIn("Only GitHub Releases URLs can be opened", source)
        self.assertIn('strip_prefix("/tag/")', source)
        self.assertIn("is_valid_release_tag", source)
        self.assertIn('value.starts_with("v")', source)
        self.assertIn("chars()", source)
        self.assertIn(".all(", source)

    def test_tauri_backend_allows_fixed_desktop_smoke_test_port_only_with_test_gate(self):
        source = (TAURI_DIR / "src" / "lib.rs").read_text(encoding="utf-8")

        self.assertIn("CC_BRANCH_DESKTOP_PORT", source)
        self.assertIn("CC_BRANCH_DESKTOP_ALLOW_FIXED_PORT", source)
        self.assertIn("DESKTOP_BACKEND_ALLOW_FIXED_PORT_ENV", source)
        self.assertIn("fn desktop_backend_port", source)
        self.assertIn("desktop_backend_fixed_port_allowed", source)
        self.assertIn("Configured desktop backend port must be between 1 and 65535", source)
        self.assertIn("desktop_backend_port()?", source)

    def test_github_download_verification_launches_both_macos_dmgs(self):
        workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "release-desktop.yml").read_text(encoding="utf-8"))

        for job_name in ("canary-installers", "verify-live-release"):
            entries = workflow["jobs"][job_name]["strategy"]["matrix"]["include"]
            mac_entries = {
                entry["platform"]: entry
                for entry in entries
                if str(entry["platform"]).startswith("mac-")
            }

            self.assertEqual(
                {
                    platform: entry["os"]
                    for platform, entry in mac_entries.items()
                },
                {
                    "mac-apple-silicon": "macos-14",
                    "mac-intel": "macos-15-intel",
                },
            )
            self.assertIn(
                "--sample-platform darwin-aarch64",
                mac_entries["mac-apple-silicon"]["verifier-args"],
            )
            self.assertIn(
                "--sample-platform darwin-x86_64",
                mac_entries["mac-intel"]["verifier-args"],
            )
            self.assertIn("--launch-dmg-app", mac_entries["mac-apple-silicon"]["verifier-args"])
            self.assertIn("--launch-dmg-app", mac_entries["mac-intel"]["verifier-args"])


if __name__ == "__main__":
    unittest.main()
