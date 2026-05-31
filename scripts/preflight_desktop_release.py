#!/usr/bin/env python3
"""Preflight-check GitHub desktop release prerequisites."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_release_version import normalize_expected, verify_versions

WORKFLOW_NAME = "Release Desktop App"
RELEASE_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "release-desktop.yml"
DESKTOP_SMOKE_SCRIPT_PATH = ROOT / "scripts" / "smoke-test-desktop-app.py"
BACKEND_SIDECAR_SMOKE_SCRIPT_PATH = ROOT / "scripts" / "smoke-test-backend-sidecar.py"
GITHUB_RELEASE_VERIFIER_PATH = ROOT / "scripts" / "verify_github_release.py"
MACOS_DMG_VERIFIER_PATH = ROOT / "scripts" / "verify-macos-dmg.py"
DESKTOP_INSTALLER_VERIFIER_PATH = ROOT / "scripts" / "verify-desktop-installers.py"
RELEASE_NOTES_RENDERER_PATH = ROOT / "scripts" / "render_desktop_release_notes.py"
RELEASE_CANARY_VERIFIER_PATH = ROOT / "scripts" / "verify_release_canary.py"
DESKTOP_BACKEND_ENTRYPOINT_PATH = ROOT / "cc_branch" / "desktop_backend.py"
TAURI_CONFIG_PATH = ROOT / "apps" / "desktop" / "src-tauri" / "tauri.conf.json"
DESKTOP_TAURI_LIB_PATH = ROOT / "apps" / "desktop" / "src-tauri" / "src" / "lib.rs"
WEB_APP_PATH = ROOT / "apps" / "web" / "src" / "App.tsx"
WEB_I18N_PATH = ROOT / "apps" / "web" / "src" / "i18n" / "index.tsx"
WEB_API_CLIENT_PATH = ROOT / "apps" / "web" / "src" / "api" / "client.ts"
REQUIRED_SECRETS = (
    "TAURI_SIGNING_PRIVATE_KEY",
    "TAURI_SIGNING_PRIVATE_KEY_PASSWORD",
    "APPLE_CERTIFICATE_BASE64",
    "APPLE_CERTIFICATE_PASSWORD",
    "APPLE_SIGNING_IDENTITY",
    "APPLE_API_KEY_BASE64",
    "APPLE_API_KEY_ID",
    "APPLE_API_ISSUER",
    "APPLE_TEAM_ID",
)
REQUIRED_RELEASE_WORKFLOW_ACTION_REFS = (
    "actions/checkout@v6",
    "actions/setup-node@v6",
    "actions/setup-python@v6",
    "dtolnay/rust-toolchain@stable",
    "tauri-apps/tauri-action@v0",
    "actions/upload-artifact@v7",
)


def run_text(command: list[str], *, check: bool = True) -> str:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if check and result.returncode != 0:
        result.check_returncode()
    if not check and result.returncode != 0 and command[:3] == ["gh", "release", "view"]:
        details = (result.stderr or result.stdout or "").strip()
        if is_gh_release_not_found(details):
            return ""
        raise ValueError(
            "Could not verify GitHub release availability"
            + (f": {details}" if details else "")
        )
    return result.stdout


def is_gh_release_not_found(output: str) -> bool:
    normalized = output.lower()
    return (
        "not found" in normalized
        or "could not resolve to a release" in normalized
    )


def run_json(command: list[str]) -> dict[str, Any]:
    return json.loads(run_text(command))


def gh_command(args: list[str], repo: str) -> list[str]:
    return ["gh", *args, "--repo", repo]


def parse_tabular_names(output: str) -> set[str]:
    names = set()
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        names.add(line.split("\t", 1)[0])
    return names


def require_release_workflow(repo: str) -> dict[str, str]:
    output = run_text(gh_command(["workflow", "list"], repo))
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) >= 2 and fields[0] == WORKFLOW_NAME:
            if fields[1] != "active":
                raise ValueError(f"{WORKFLOW_NAME} workflow is not active: {fields[1]}")
            return {"name": fields[0], "state": fields[1], "id": fields[2] if len(fields) > 2 else ""}
    raise ValueError(f"Missing GitHub Actions workflow: {WORKFLOW_NAME}")


def require_required_secrets(repo: str) -> list[str]:
    output = run_text(gh_command(["secret", "list"], repo))
    available = parse_tabular_names(output)
    missing = [name for name in REQUIRED_SECRETS if name not in available]
    if missing:
        raise ValueError(f"Missing required GitHub secrets: {', '.join(missing)}")
    return sorted(available.intersection(REQUIRED_SECRETS))


def require_actions_enabled(repo: str) -> dict[str, Any]:
    permissions = run_json(["gh", "api", f"repos/{repo}/actions/permissions"])
    if permissions.get("enabled") is not True:
        raise ValueError("GitHub Actions are not enabled for this repository")
    allowed = permissions.get("allowed_actions")
    if allowed not in {"all", "selected"}:
        raise ValueError(f"GitHub Actions allowed_actions is not usable: {allowed}")
    return permissions


def require_workflow_write_permissions(repo: str) -> dict[str, Any]:
    remote_permissions = run_json(["gh", "api", f"repos/{repo}/actions/permissions/workflow"])
    workflow = yaml.safe_load(RELEASE_WORKFLOW_PATH.read_text(encoding="utf-8"))
    if not isinstance(workflow, dict):
        raise ValueError(f"Release workflow is not a YAML mapping: {RELEASE_WORKFLOW_PATH}")
    workflow_permissions = workflow.get("permissions")
    if not isinstance(workflow_permissions, dict):
        raise ValueError("Release workflow must declare permissions.contents: write")
    contents_permission = workflow_permissions.get("contents")
    if contents_permission != "write":
        raise ValueError(
            "Release workflow must declare permissions.contents: write so "
            "the release workflow can upload assets and publish the draft release"
        )
    try:
        workflow_path = str(RELEASE_WORKFLOW_PATH.relative_to(ROOT))
    except ValueError:
        workflow_path = str(RELEASE_WORKFLOW_PATH)
    return {
        "default_workflow_permissions": remote_permissions.get("default_workflow_permissions"),
        "contents": contents_permission,
        "workflow": workflow_path,
    }


def require_job(workflow: dict[str, Any], job_name: str) -> dict[str, Any]:
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        raise ValueError("Release workflow must define jobs")
    job = jobs.get(job_name)
    if not isinstance(job, dict):
        raise ValueError(f"Release workflow must define {job_name} job")
    return job


def require_step_run(job: dict[str, Any], step_name: str) -> str:
    steps = job.get("steps")
    if not isinstance(steps, list):
        raise ValueError("Release workflow job must define steps")
    step = next(
        (
            item
            for item in steps
            if isinstance(item, dict) and item.get("name") == step_name
        ),
        None,
    )
    if step is None:
        raise ValueError(f"Release workflow is missing step: {step_name}")
    run = step.get("run")
    if not isinstance(run, str):
        raise ValueError(f"Release workflow step has no run script: {step_name}")
    return run


def require_step(job: dict[str, Any], step_name: str) -> dict[str, Any]:
    steps = job.get("steps")
    if not isinstance(steps, list):
        raise ValueError("Release workflow job must define steps")
    step = next(
        (
            item
            for item in steps
            if isinstance(item, dict) and item.get("name") == step_name
        ),
        None,
    )
    if step is None:
        raise ValueError(f"Release workflow is missing step: {step_name}")
    return step


def require_desktop_smoke_report_artifact_gate(workflow: dict[str, Any]) -> None:
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict) or "build" not in jobs:
        return
    build_job = require_job(workflow, "build")
    step = require_step(build_job, "Upload desktop smoke reports")
    if step.get("if") != "always()":
        raise ValueError("Release workflow desktop smoke reports upload must use if: always()")
    if step.get("uses") != "actions/upload-artifact@v7":
        raise ValueError("Release workflow desktop smoke reports upload must use actions/upload-artifact@v7")
    options = step.get("with")
    if not isinstance(options, dict):
        raise ValueError("Release workflow desktop smoke reports upload must define with options")
    if options.get("path") != "smoke-reports/*.json":
        raise ValueError("Release workflow desktop smoke reports upload must include smoke-reports/*.json")
    if options.get("if-no-files-found") != "error":
        raise ValueError("Release workflow desktop smoke reports upload must set if-no-files-found: error")


def require_job_needs(job_name: str, job: dict[str, Any], expected: set[str]) -> None:
    needs = job.get("needs")
    if isinstance(needs, str):
        actual = {needs}
    elif isinstance(needs, list):
        actual = {str(item) for item in needs}
    else:
        actual = set()
    missing = expected.difference(actual)
    if missing:
        raise ValueError(f"Release workflow {job_name} job is missing needs: {', '.join(sorted(missing))}")


def require_verifier_matrix(job_name: str, job: dict[str, Any]) -> None:
    strategy = job.get("strategy")
    matrix = strategy.get("matrix") if isinstance(strategy, dict) else None
    include = matrix.get("include") if isinstance(matrix, dict) else None
    if not isinstance(include, list):
        raise ValueError(f"Release workflow {job_name} job must define a matrix include list")

    by_platform = {
        str(entry.get("platform")): entry
        for entry in include
        if isinstance(entry, dict)
    }
    expected_args = {
        "mac-apple-silicon": [
            "--verify-dmg",
            "--launch-dmg-app",
            "--verify-dmg-installed-copy",
            "--verify-macos-gatekeeper",
            "--sample-platform darwin-aarch64",
        ],
        "mac-intel": [
            "--verify-dmg",
            "--launch-dmg-app",
            "--verify-dmg-installed-copy",
            "--verify-macos-gatekeeper",
            "--sample-platform darwin-x86_64",
        ],
        "linux": [
            "--skip-dmg",
            "--verify-linux-installers",
            "--launch-linux-packages",
            "--launch-linux-appimage",
        ],
        "windows": [
            "--skip-dmg",
            "--verify-windows-installer",
            "--launch-windows-msi",
            "--launch-windows-nsis",
        ],
    }
    missing_platforms = set(expected_args).difference(by_platform)
    if missing_platforms:
        raise ValueError(
            f"Release workflow {job_name} verifier matrix is missing platform(s): "
            + ", ".join(sorted(missing_platforms))
        )

    for platform, required_args in expected_args.items():
        args = by_platform[platform].get("verifier-args")
        if not isinstance(args, str):
            raise ValueError(f"Release workflow {job_name} matrix entry for {platform} has no verifier-args")
        missing_args = [arg for arg in required_args if arg not in args]
        if missing_args:
            raise ValueError(
                f"Release workflow {job_name} matrix entry for {platform} is missing verifier arg(s): "
                + ", ".join(missing_args)
            )


def collect_workflow_uses(value: Any) -> set[str]:
    uses: set[str] = set()
    if isinstance(value, dict):
        item = value.get("uses")
        if isinstance(item, str):
            uses.add(item)
        for nested in value.values():
            uses.update(collect_workflow_uses(nested))
    elif isinstance(value, list):
        for item in value:
            uses.update(collect_workflow_uses(item))
    return uses


def require_release_workflow_bash_syntax(workflow: dict[str, Any]) -> None:
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for index, step in enumerate(steps):
            if not isinstance(step, dict) or step.get("shell") != "bash":
                continue
            run = step.get("run")
            if not isinstance(run, str) or not run.strip():
                continue
            result = subprocess.run(
                ["bash", "-n"],
                input=run,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                step_name = step.get("name") or f"{job_name} step {index + 1}"
                details = (result.stderr or result.stdout or "").strip()
                raise ValueError(
                    f"Release workflow step {step_name} has bash syntax errors"
                    + (f": {details}" if details else "")
                )
            for unsupported in ("mapfile", "readarray"):
                if unsupported in run:
                    step_name = step.get("name") or f"{job_name} step {index + 1}"
                    raise ValueError(
                        f"Release workflow step {step_name} uses {unsupported}, "
                        "which is not available in the macOS runner Bash 3.2"
                    )


def require_release_workflow_action_refs(workflow: dict[str, Any]) -> None:
    uses = collect_workflow_uses(workflow)
    if not uses:
        return
    missing = [
        action_ref
        for action_ref in REQUIRED_RELEASE_WORKFLOW_ACTION_REFS
        if action_ref not in uses
    ]
    if missing:
        raise ValueError(
            "Release workflow is missing required action ref(s): "
            + ", ".join(missing)
        )


def require_build_quality_gates(workflow: dict[str, Any]) -> None:
    build_job = require_job(workflow, "build")
    backend_run = require_step_run(build_job, "Smoke test bundled backend sidecar")
    if "scripts/smoke-test-backend-sidecar.py" not in backend_run:
        raise ValueError("Release workflow bundled backend sidecar smoke step does not run the sidecar smoke script")
    for arg in ["--expected-version", "--expected-platform", "--expected-arch"]:
        if arg not in backend_run:
            raise ValueError(
                f"Release workflow bundled backend sidecar smoke step is missing desktop metadata arg: {arg}"
            )
    for value in ["inputs.release_tag || github.ref_name", "matrix.desktop-platform", "matrix.desktop-arch"]:
        if value not in backend_run:
            raise ValueError(
                f"Release workflow bundled backend sidecar smoke step is missing desktop metadata value: {value}"
            )

    packaged_smoke_steps = {
        "macOS": "Smoke test packaged macOS desktop app",
        "Linux": "Smoke test packaged Linux desktop app",
        "Windows": "Smoke test packaged Windows desktop app",
    }
    for platform, step_name in packaged_smoke_steps.items():
        run = require_step_run(build_job, step_name)
        if "scripts/smoke-test-desktop-app.py" not in run:
            raise ValueError(f"Release workflow packaged desktop smoke step for {platform} does not run desktop smoke")
        if "--use-auto-port" not in run:
            raise ValueError(
                f"Release workflow packaged desktop smoke step for {platform} is missing auto port smoke"
            )
        if "--expect-startup-failure" not in run:
            raise ValueError(
                f"Release workflow packaged desktop smoke step for {platform} is missing sidecar failure smoke"
            )
        if "--expect-startup-failure-recovery" not in run or "--recovery-sidecar" not in run:
            raise ValueError(
                f"Release workflow packaged desktop smoke step for {platform} is missing startup failure recovery smoke"
            )
        if "--expect-stale-backend-rejection" not in run:
            raise ValueError(
                f"Release workflow packaged desktop smoke step for {platform} is missing stale backend rejection smoke"
            )
        for arg in ["--expected-version", "--expected-platform", "--expected-arch"]:
            if arg not in run:
                raise ValueError(
                    f"Release workflow packaged desktop smoke step for {platform} "
                    f"is missing desktop metadata arg: {arg}"
                )
        for value in ["inputs.release_tag || github.ref_name", "matrix.desktop-platform", "matrix.desktop-arch"]:
            if value not in run:
                raise ValueError(
                    f"Release workflow packaged desktop smoke step for {platform} "
                    f"is missing desktop metadata value: {value}"
                )
    require_desktop_startup_diagnostics_metadata()

    dmg_run = require_step_run(build_job, "Verify macOS DMG contains backend sidecar")
    for arg in [
        "scripts/verify-macos-dmg.py",
        "--launch-app",
        "--verify-installed-copy",
        "--verify-stale-backend-rejection",
        "--expected-version",
    ]:
        if arg not in dmg_run:
            raise ValueError(f"Release workflow macOS DMG verifier is missing stale backend gate: {arg}")

    linux_installer_run = require_step_run(build_job, "Verify Linux installers contain backend sidecar")
    for arg in [
        "scripts/verify-desktop-installers.py",
        "--launch-linux-packages",
        "--launch-appimage",
        "--expected-version",
    ]:
        if arg not in linux_installer_run:
            raise ValueError(f"Release workflow Linux installer verifier is missing launch gate: {arg}")

    windows_installer_run = require_step_run(build_job, "Verify Windows installers contain backend sidecar")
    for arg in [
        "scripts/verify-desktop-installers.py",
        "--launch-windows-msi",
        "--launch-windows-nsis",
        "--expected-version",
    ]:
        if arg not in windows_installer_run:
            raise ValueError(f"Release workflow Windows installer verifier is missing launch gate: {arg}")
    require_standalone_installer_metadata_gates()


def require_packaged_recovery_report_gates(workflow: dict[str, Any]) -> None:
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict) or "build" not in jobs:
        return
    build_job = require_job(workflow, "build")
    packaged_smoke_steps = {
        "macOS": "Smoke test packaged macOS desktop app",
        "Linux": "Smoke test packaged Linux desktop app",
        "Windows": "Smoke test packaged Windows desktop app",
    }
    for platform, step_name in packaged_smoke_steps.items():
        run = require_step_run(build_job, step_name)
        for token in ["desktop-app-recovery-", "Startup failure recovery smoke"]:
            if token not in run:
                raise ValueError(
                    f"Release workflow packaged desktop smoke step for {platform} "
                    f"is missing startup failure recovery report: {token}"
                )


def require_windows_missing_sidecar_temp_cleanup_gate(workflow: dict[str, Any]) -> None:
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict) or "build" not in jobs:
        return
    build_job = require_job(workflow, "build")
    run = require_step_run(build_job, "Smoke test packaged Windows desktop app")
    cleanup = "Remove-Item -Recurse -Force $missingSidecarDir"
    create = "New-Item -ItemType Directory -Force -Path $missingSidecarDir"
    if cleanup not in run:
        raise ValueError(
            "Release workflow Windows packaged desktop smoke step must clean missing sidecar temp directory"
        )
    if create not in run or run.index(cleanup) > run.index(create):
        raise ValueError(
            "Release workflow Windows packaged desktop smoke step must clean missing sidecar temp directory before creating it"
        )


def require_desktop_bundle_output_cleanup_gate(workflow: dict[str, Any]) -> None:
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict) or "build" not in jobs:
        return
    build_job = require_job(workflow, "build")
    steps = build_job.get("steps")
    if not isinstance(steps, list):
        raise ValueError("Release workflow build job must define steps")
    step_names = [step.get("name") for step in steps if isinstance(step, dict)]
    try:
        clean_index = step_names.index("Clean previous desktop bundle outputs")
        build_index = step_names.index("Build desktop app and upload release assets")
    except ValueError as error:
        raise ValueError(
            "Release workflow must clean previous desktop bundle outputs before Tauri build"
        ) from error
    if clean_index > build_index:
        raise ValueError(
            "Release workflow must clean previous desktop bundle outputs before Tauri build"
        )
    step = require_step(build_job, "Clean previous desktop bundle outputs")
    if step.get("shell") != "bash":
        raise ValueError("Release workflow desktop bundle cleanup step must use bash")
    run = step.get("run")
    if not isinstance(run, str):
        raise ValueError("Release workflow desktop bundle cleanup step must define run script")
    required_tokens = [
        "find apps/desktop/src-tauri/target",
        "*/release/bundle",
        "rm -rf",
    ]
    missing = [token for token in required_tokens if token not in run]
    if missing:
        raise ValueError(
            "Release workflow desktop bundle cleanup step is incomplete: "
            + ", ".join(missing)
        )


def require_desktop_startup_diagnostics_metadata() -> None:
    script_text = DESKTOP_SMOKE_SCRIPT_PATH.read_text(encoding="utf-8")
    required_tokens = [
        "def require_desktop_metadata",
        "desktop_metadata = require_desktop_metadata(",
        "expected_version=expected_version",
        "expected_platform=expected_platform",
        "expected_arch=expected_arch",
        "**desktop_metadata",
        "desktop_version",
        "desktop_platform",
        "desktop_arch",
        "port_mode",
        '"port_mode": "auto" if use_auto_port else "fixed"',
    ]
    missing = [token for token in required_tokens if token not in script_text]
    if missing:
        raise ValueError(
            "Desktop app smoke test no longer requires startup diagnostics metadata: "
            + ", ".join(missing)
        )


def require_desktop_smoke_windows_cleanup_gate() -> None:
    script_text = DESKTOP_SMOKE_SCRIPT_PATH.read_text(encoding="utf-8")
    required_tokens = [
        "def temporary_directory",
        "ignore_cleanup_errors=True",
        "with temporary_directory(",
    ]
    missing = [token for token in required_tokens if token not in script_text]
    if missing:
        raise ValueError(
            "Desktop app smoke test must ignore temporary directory cleanup errors "
            "so Windows file locks cannot fail otherwise successful smoke runs: "
            + ", ".join(missing)
        )


def require_desktop_smoke_process_table_port_discovery_gate() -> None:
    script_text = DESKTOP_SMOKE_SCRIPT_PATH.read_text(encoding="utf-8")
    required_tokens = [
        "def discover_backend_port_from_process_table",
        "ps",
        "cc-branch-backend",
        "parse_backend_port_arg",
        "discovery_root=home_dir",
        "Discovered bundled backend sidecar port",
    ]
    missing = [token for token in required_tokens if token not in script_text]
    if missing:
        raise ValueError(
            "Desktop app auto-port smoke test must fall back to process-table port "
            "discovery when packaged macOS stdout is delayed: "
            + ", ".join(missing)
        )


def require_startup_failure_recovery_auto_port_gate() -> None:
    script_text = DESKTOP_SMOKE_SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(script_text, filename=str(DESKTOP_SMOKE_SCRIPT_PATH))
    recovery_function = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "verify_desktop_startup_failure_recovery"
        ),
        None,
    )
    if recovery_function is None:
        raise ValueError("Desktop smoke script is missing startup failure recovery verifier")

    for node in ast.walk(recovery_function):
        if not isinstance(node, ast.Call):
            continue
        function_name = node.func.id if isinstance(node.func, ast.Name) else ""
        if function_name != "verify_desktop_app":
            continue
        for keyword in node.keywords:
            if keyword.arg != "use_auto_port":
                continue
            if isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                return
        break

    raise ValueError(
        "Desktop smoke startup failure recovery must relaunch with auto port"
    )


def require_smoke_scripts_no_proxy_loopback_gate() -> None:
    for path in [DESKTOP_SMOKE_SCRIPT_PATH, BACKEND_SIDECAR_SMOKE_SCRIPT_PATH]:
        script_text = path.read_text(encoding="utf-8")
        required_tokens = [
            "ProxyHandler",
            "build_opener",
            "def local_urlopen",
            "ProxyHandler({})",
            "local_urlopen(",
        ]
        missing = [token for token in required_tokens if token not in script_text]
        if missing:
            raise ValueError(
                f"{path.name} must bypass proxy settings for loopback backend smoke checks: "
                + ", ".join(missing)
            )
        if "from urllib.request import Request, urlopen" in script_text or "urlopen(" in script_text.replace("local_urlopen(", ""):
            raise ValueError(
                f"{path.name} must not use proxy-aware urlopen for loopback backend smoke checks"
            )


def require_github_download_launch_desktop_metadata_gate() -> None:
    script_text = GITHUB_RELEASE_VERIFIER_PATH.read_text(encoding="utf-8")
    required_tokens = [
        "def collect_launch_desktop_metadata",
        "def require_launch_desktop_metadata",
        "def collect_launch_port_modes",
        "def require_launch_port_modes",
        "def build_verification_summary",
        "def expected_desktop_platform_arch",
        "launch_desktop_metadata",
        "launch_port_modes",
        "verification_summary",
        "release_state",
        "latest_matches_tag",
        "latest_checked",
        "is_public",
        "public_required",
        "latest_required",
        "public_release_requirement_met",
        "latest_release_requirement_met",
        "release_notes_verified",
        "latest_json_notes_verified",
        "all_required_launches_verified",
        "all_required_stale_backend_rejections_verified",
        "all_launch_backend_sources_bundled_sidecar",
        "all_launch_port_modes_auto",
        "all_launch_desktop_metadata_present",
        "required_launch_labels",
        "required_stale_labels",
        "expected_version=expected_version",
        "port_mode",
        "desktop_version",
        "desktop_platform",
        "desktop_arch",
    ]
    missing = [token for token in required_tokens if token not in script_text]
    if missing:
        raise ValueError(
            "GitHub release verifier no longer checks launch desktop metadata: "
            + ", ".join(missing)
        )


def require_standalone_installer_metadata_gates() -> None:
    verifier_requirements = {
        MACOS_DMG_VERIFIER_PATH: [
            "def dmg_expected_arch",
            "expected_version=expected_version",
            'expected_platform="darwin" if expected_version else None',
            "expected_arch=expected_arch if expected_version else None",
            "use_auto_port=True",
        ],
        DESKTOP_INSTALLER_VERIFIER_PATH: [
            "def verify_desktop_app_launch",
            "expected_version=expected_version",
            'expected_platform="linux" if expected_version else None',
            'expected_platform="windows" if expected_version else None',
            'expected_arch="x86_64" if expected_version else None',
            "use_auto_port=True",
        ],
    }
    missing_by_file: list[str] = []
    for path, required_tokens in verifier_requirements.items():
        script_text = path.read_text(encoding="utf-8")
        missing = [token for token in required_tokens if token not in script_text]
        if missing:
            missing_by_file.append(f"{path.name}: {', '.join(missing)}")
    if missing_by_file:
        raise ValueError(
            "standalone installer verifiers no longer check launch desktop metadata: "
            + "; ".join(missing_by_file)
        )


def require_installer_sidecar_colocation_gate() -> None:
    script_text = DESKTOP_INSTALLER_VERIFIER_PATH.read_text(encoding="utf-8")
    required_tokens = [
        "def listing_line_path",
        "def require_listing_entries_colocated",
        "def require_same_directory",
        "must be in the same directory",
        "require_listing_entries_colocated(app, backend, label=deb.name)",
        "require_listing_entries_colocated(app, backend, label=rpm.name)",
        "require_same_directory(app, backend, label=label)",
        "require_same_directory(app, backend, label=msi.name)",
        "require_same_directory(app, backend, label=nsis.name)",
    ]
    missing = [token for token in required_tokens if token not in script_text]
    if missing:
        raise ValueError(
            "Desktop installer verifier must require the app executable and backend sidecar to be in the same directory: "
            + ", ".join(missing)
        )


def require_windows_installer_acl_repair_gate() -> None:
    script_text = DESKTOP_INSTALLER_VERIFIER_PATH.read_text(encoding="utf-8")
    required_tokens = [
        "def temporary_directory",
        "ignore_cleanup_errors=True",
        "def grant_windows_tree_access",
        "icacls",
        "grant_windows_tree_access(target)",
        "def stat_file",
        "could not be read after Windows ACL repair",
    ]
    missing = [token for token in required_tokens if token not in script_text]
    if missing:
        raise ValueError(
            "Desktop installer verifier must repair Windows MSI/NSIS extraction ACLs and tolerate cleanup locks: "
            + ", ".join(missing)
        )


def require_release_notes_support_copy_report_gate() -> None:
    required_tokens = [
        "Copy report",
        "attach the report when filing an issue",
    ]
    missing_by_file: list[str] = []
    for path in [RELEASE_NOTES_RENDERER_PATH, RELEASE_CANARY_VERIFIER_PATH]:
        script_text = path.read_text(encoding="utf-8")
        missing = [token for token in required_tokens if token not in script_text]
        if missing:
            missing_by_file.append(f"{path.name}: {', '.join(missing)}")
    if missing_by_file:
        raise ValueError(
            "Release notes no longer include the Copy report support path: "
            + "; ".join(missing_by_file)
        )
    renderer_text = RELEASE_NOTES_RENDERER_PATH.read_text(encoding="utf-8")
    canary_text = RELEASE_CANARY_VERIFIER_PATH.read_text(encoding="utf-8")
    if "download the installer for your platform from the table above" not in renderer_text:
        raise ValueError(
            "Release notes must direct reinstall attempts to the current release download table"
        )
    if "download the installer for your platform from the table above" not in canary_text:
        raise ValueError(
            "Release canary must verify reinstall attempts point to the current release download table"
        )
    forbidden = [
        "download the latest installer",
        "download latest installer",
    ]
    present = [token for token in forbidden if token in renderer_text.lower()]
    if present:
        raise ValueError(
            "Release notes must not send failed reinstall attempts to the latest release instead of the current release: "
            + ", ".join(present)
        )
    if "latest release instead of the current release" not in canary_text:
        raise ValueError(
            "Release canary must reject release notes that send failed reinstall attempts to latest"
        )
    release_download_guard_tokens = [
        "releases/latest/download",
        "linked_release_downloads",
        "linked_tag != tag",
        "outside the current release",
    ]
    missing_download_guard_tokens = [
        token for token in release_download_guard_tokens if token not in canary_text
    ]
    if missing_download_guard_tokens:
        raise ValueError(
            "Release canary must reject floating latest and non-current release download links: "
            + ", ".join(missing_download_guard_tokens)
        )
    table_guard_tokens = [
        "table_rows",
        "download table",
        "Release notes download table is missing recommended asset",
    ]
    missing_table_guard_tokens = [
        token for token in table_guard_tokens if token not in canary_text
    ]
    if missing_table_guard_tokens:
        raise ValueError(
            "Release canary must require every recommended asset to appear in the download table: "
            + ", ".join(missing_table_guard_tokens)
        )
    first_launch_tokens = [
        "Local backend ready",
        "Add project",
        "local directory or SSH workspace",
    ]
    missing_first_launch_by_file = []
    for label, text in [
        ("render_desktop_release_notes.py", renderer_text),
        ("verify_release_canary.py", canary_text),
    ]:
        missing = [token for token in first_launch_tokens if token not in text]
        if missing:
            missing_first_launch_by_file.append(f"{label}: {', '.join(missing)}")
    if missing_first_launch_by_file:
        raise ValueError(
            "Release notes must include first launch guidance after install: "
            + "; ".join(missing_first_launch_by_file)
        )


def require_release_checksum_manifest_gate(workflow: dict[str, Any]) -> None:
    required_script_tokens = {
        RELEASE_NOTES_RENDERER_PATH: [
            "CHECKSUMS_ASSET_NAME",
            "Verify your download",
        ],
        RELEASE_CANARY_VERIFIER_PATH: [
            "CHECKSUMS_ASSET_NAME",
            "SHA256SUMS",
            "def validate_checksum_manifest",
            "checksum_manifest",
        ],
        GITHUB_RELEASE_VERIFIER_PATH: [
            "SHA256SUMS",
            "release_download_command",
            "validate_checksum_manifest",
            "def require_checksum_verified_assets",
            "all_required_checksum_assets_verified",
            "required_checksum_assets",
            '"checksum_manifest": checksum_manifest',
        ],
    }
    missing_by_file: list[str] = []
    for path, tokens in required_script_tokens.items():
        script_text = path.read_text(encoding="utf-8")
        missing = [token for token in tokens if token not in script_text]
        if missing:
            missing_by_file.append(f"{path.name}: {', '.join(missing)}")
    if missing_by_file:
        raise ValueError(
            "Desktop release checksum manifest guard is incomplete: "
            + "; ".join(missing_by_file)
        )
    if not isinstance(workflow.get("jobs"), dict):
        # Workflow structure is already owned by the broader release workflow gates.
        # This guard only checks checksum-specific release behavior.
        return

    publish_job = require_job(workflow, "publish-updater-json")
    publish_run = require_step_run(publish_job, "Publish complete latest.json")
    for token in [
        "SHA256SUMS",
        "sha256sum",
        "gh release download",
        "gh release upload",
    ]:
        if token not in publish_run:
            raise ValueError(
                "Publish updater metadata job must generate and upload SHA256SUMS: "
                + token
            )
    dmg_checksum_tokens = [
        "mac_arm_dmg",
        "mac_intel_dmg",
        "aarch64.*\\.dmg$",
        "x64.*\\.dmg$",
        '"$mac_arm_dmg"',
        '"$mac_intel_dmg"',
    ]
    missing_dmg_tokens = [
        token for token in dmg_checksum_tokens if token not in publish_run
    ]
    if missing_dmg_tokens:
        raise ValueError(
            "Publish updater metadata job must include macOS DMG user downloads in SHA256SUMS: "
            + ", ".join(missing_dmg_tokens)
        )

    canary_job = require_job(workflow, "canary-release")
    canary_run = require_step_run(canary_job, "Download canary assets")
    for token in ['--pattern "SHA256SUMS"', "verify_release_canary.py"]:
        if token not in canary_run:
            raise ValueError(
                "Release canary must download and verify SHA256SUMS: " + token
            )


def require_backend_failure_current_release_gate() -> None:
    requirements = {
        WEB_APP_PATH: [
            "https://github.com/GeminiLight/cc-branch/releases",
            "releaseUrlForBackendFailure",
            "/tag/${encodeURIComponent(tag)}",
            "downloadLatestInstaller",
            "copyReport",
            "Open ${releaseUrlForBackendFailure(message)}",
        ],
        WEB_I18N_PATH: [
            "downloadLatestInstaller",
            "Open GitHub Releases",
            "打开 GitHub Releases",
        ],
        WEB_API_CLIENT_PATH: [
            "Cannot reach the local CC Branch backend",
            "GitHub Releases page",
            "desktop installer for this platform",
        ],
    }
    missing_by_file: list[str] = []
    for path, required_tokens in requirements.items():
        text = path.read_text(encoding="utf-8")
        if path == WEB_APP_PATH and "releases/latest" in text:
            missing_by_file.append(f"{path.name}: must not link backend failures to releases/latest")
        missing = [token for token in required_tokens if token not in text]
        if missing:
            missing_by_file.append(f"{path.name}: {', '.join(missing)}")
    if missing_by_file:
        raise ValueError(
            "Backend failure panel no longer links GitHub Releases with current-platform reinstall guidance: "
            + "; ".join(missing_by_file)
        )
    combined_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [WEB_API_CLIENT_PATH, WEB_I18N_PATH]
    )
    forbidden = [
        "Make sure the backend server is running",
        "cc-branch server is running",
    ]
    present = [token for token in forbidden if token in combined_text]
    app_text = WEB_APP_PATH.read_text(encoding="utf-8")
    if "cc-branch serve" in app_text:
        present.append("cc-branch serve")
    if present:
        raise ValueError(
            "Backend failure network errors still use terminal/server wording: "
            + ", ".join(present)
        )


def require_backend_failure_native_release_open_gate() -> None:
    app_text = WEB_APP_PATH.read_text(encoding="utf-8")
    client_text = WEB_API_CLIENT_PATH.read_text(encoding="utf-8")
    tauri_text = DESKTOP_TAURI_LIB_PATH.read_text(encoding="utf-8")
    requirements = {
        "Web failure panel": [
            "onOpenRelease",
            "handleOpenRelease",
            "event.preventDefault()",
            "client.openExternalUrl(url)",
        ],
        "Web API client": [
            "openExternalUrl(url: string)",
            'this._invoke("open_external_url", { url })',
            'window.open(url, "_blank", "noopener,noreferrer")',
        ],
        "Tauri launcher": [
            "GITHUB_RELEASES_URL_PREFIX",
            "validate_external_release_url",
            "is_valid_release_tag",
            'strip_prefix("/tag/")',
            "chars()",
            ".all(",
            "fn open_external_url",
            "open_external_url,",
            'Command::new("open")',
            'Command::new("cmd")',
            'Command::new("xdg-open")',
            "Only GitHub Releases URLs can be opened",
        ],
    }
    texts = {
        "Web failure panel": app_text,
        "Web API client": client_text,
        "Tauri launcher": tauri_text,
    }
    missing_by_area = []
    for area, required_tokens in requirements.items():
        missing = [token for token in required_tokens if token not in texts[area]]
        if missing:
            missing_by_area.append(f"{area}: {', '.join(missing)}")
    if missing_by_area:
        raise ValueError(
            "Backend failure release links must open through the native shell with a restricted URL allowlist: "
            + "; ".join(missing_by_area)
        )


def require_desktop_backend_port_retry_gate() -> None:
    text = DESKTOP_TAURI_LIB_PATH.read_text(encoding="utf-8")
    required_tokens = [
        "BACKEND_START_MAX_ATTEMPTS",
        "desktop_backend_port_from_env",
        "pick_desktop_backend_port",
        "let attempts = if fixed_port.is_some()",
        "for attempt in 1..=attempts",
        "attempt_errors.push",
    ]
    missing = [token for token in required_tokens if token not in text]
    if missing:
        raise ValueError(
            "Desktop backend startup no longer retries auto-selected ports: "
            + ", ".join(missing)
        )


def require_desktop_backend_fixed_port_test_gate() -> None:
    tauri_text = DESKTOP_TAURI_LIB_PATH.read_text(encoding="utf-8")
    smoke_text = DESKTOP_SMOKE_SCRIPT_PATH.read_text(encoding="utf-8")
    required_tauri_tokens = [
        "DESKTOP_BACKEND_ALLOW_FIXED_PORT_ENV",
        "CC_BRANCH_DESKTOP_ALLOW_FIXED_PORT",
        "desktop_backend_fixed_port_allowed",
        "if !desktop_backend_fixed_port_allowed()",
        "return Ok(None);",
    ]
    required_smoke_tokens = [
        "DESKTOP_ALLOW_FIXED_PORT_ENV",
        "CC_BRANCH_DESKTOP_ALLOW_FIXED_PORT",
        "env.pop(DESKTOP_ALLOW_FIXED_PORT_ENV, None)",
        "env[DESKTOP_ALLOW_FIXED_PORT_ENV] = \"1\"",
    ]
    missing_tauri = [token for token in required_tauri_tokens if token not in tauri_text]
    missing_smoke = [token for token in required_smoke_tokens if token not in smoke_text]
    if missing_tauri or missing_smoke:
        details = []
        if missing_tauri:
            details.append("Tauri launcher: " + ", ".join(missing_tauri))
        if missing_smoke:
            details.append("desktop smoke script: " + ", ".join(missing_smoke))
        raise ValueError(
            "The fixed desktop backend port must be gated for smoke tests so "
            "user environments cannot force packaged desktop startup onto a stale or occupied port: "
            + "; ".join(details)
        )


def require_desktop_backend_python_env_sanitized_gate() -> None:
    tauri_text = DESKTOP_TAURI_LIB_PATH.read_text(encoding="utf-8")
    desktop_smoke_text = DESKTOP_SMOKE_SCRIPT_PATH.read_text(encoding="utf-8")
    backend_smoke_text = BACKEND_SIDECAR_SMOKE_SCRIPT_PATH.read_text(encoding="utf-8")
    poison_names = [
        "PYTHONHOME",
        "PYTHONPATH",
        "VIRTUAL_ENV",
        "CONDA_PREFIX",
        "LD_LIBRARY_PATH",
        "DYLD_LIBRARY_PATH",
    ]
    required_tauri_tokens = [
        "DESKTOP_BACKEND_POISON_ENV",
        "sanitized_backend_environment",
        ".env_clear()",
        ".envs(sanitized_backend_environment())",
        "env_remove",
    ]
    required_smoke_tokens = [
        "BACKEND_POISON_ENV",
        "env.pop(name, None)",
    ]
    missing_tauri = [
        token
        for token in [*poison_names, *required_tauri_tokens]
        if token not in tauri_text
    ]
    missing_desktop_smoke = [
        token
        for token in [*poison_names, *required_smoke_tokens]
        if token not in desktop_smoke_text
    ]
    missing_backend_smoke = [
        token
        for token in [*poison_names, *required_smoke_tokens]
        if token not in backend_smoke_text
    ]
    if missing_tauri or missing_desktop_smoke or missing_backend_smoke:
        details = []
        if missing_tauri:
            details.append("Tauri launcher: " + ", ".join(missing_tauri))
        if missing_desktop_smoke:
            details.append("desktop smoke script: " + ", ".join(missing_desktop_smoke))
        if missing_backend_smoke:
            details.append("backend sidecar smoke script: " + ", ".join(missing_backend_smoke))
        raise ValueError(
            "Desktop backend Python environment sanitization is missing; "
            "packaged sidecars must not inherit user Python, Conda, virtualenv, or library-path pollution: "
            + "; ".join(details)
        )


def require_desktop_backend_output_tail_gate() -> None:
    text = DESKTOP_TAURI_LIB_PATH.read_text(encoding="utf-8")
    required_tokens = [
        "BackendLogBuffer",
        "push_backend_log",
        "backend_log_tail",
        "CommandEvent::Stdout",
        "CommandEvent::Stderr",
        '"stdout"',
        '"stderr"',
        "Bundled backend output:",
    ]
    missing = [token for token in required_tokens if token not in text]
    if missing:
        raise ValueError(
            "Desktop backend startup failure reports must include sidecar output tail: "
            + ", ".join(missing)
        )


def require_tauri_backend_no_proxy_gate() -> None:
    text = DESKTOP_TAURI_LIB_PATH.read_text(encoding="utf-8")
    required_tokens = [
        "fn backend_http_client",
        ".no_proxy()",
        "backend_http_client(Duration::from_secs(2))",
        "backend_http_client(Duration::from_millis(600))",
    ]
    missing = [token for token in required_tokens if token not in text]
    if missing:
        raise ValueError(
            "Tauri backend readiness checks must bypass proxy settings for loopback requests: "
            + ", ".join(missing)
        )


def require_tauri_backend_transient_probe_retry_gate() -> None:
    text = DESKTOP_TAURI_LIB_PATH.read_text(encoding="utf-8")
    required_tokens = [
        "enum BackendProbeError",
        "Transient(String)",
        "Fatal(String)",
        "BackendProbeError::Transient(e.to_string())",
        "Err(BackendProbeError::Transient(error))",
        "last_transient_error = Some(error)",
        "Err(BackendProbeError::Fatal(error)) => return Err(error)",
    ]
    missing = [token for token in required_tokens if token not in text]
    if missing:
        raise ValueError(
            "Tauri backend startup must retry transient backend probe errors while "
            "still rejecting stale backends: "
            + ", ".join(missing)
        )


def require_desktop_webview_fetch_diagnostics_gate() -> None:
    text = WEB_API_CLIENT_PATH.read_text(encoding="utf-8")
    required_tokens = [
        "Cannot reach the local CC Branch backend from the desktop WebView.",
        "Desktop version:",
        "Desktop platform:",
        "Backend source:",
        "Port:",
        "Config:",
        "State:",
        "proxy, VPN, firewall, or security tool",
        "_lastApiInfo",
        "_fetchApi",
    ]
    missing = [token for token in required_tokens if token not in text]
    if missing:
        raise ValueError(
            "Desktop WebView backend fetch diagnostics no longer include support-ready context: "
            + ", ".join(missing)
        )


def require_desktop_csp_local_backend_gate() -> None:
    config = json.loads(TAURI_CONFIG_PATH.read_text(encoding="utf-8"))
    csp = (
        config.get("app", {})
        .get("security", {})
        .get("csp")
    )
    if not isinstance(csp, str) or not csp.strip():
        raise ValueError("Desktop CSP must be explicit and allow only the local backend connection")
    required_tokens = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline'",
        "connect-src 'self' http://127.0.0.1:* http://localhost:* ws:",
        "img-src 'self' data:",
    ]
    missing = [token for token in required_tokens if token not in csp]
    forbidden = ["connect-src *", "default-src *", "https:"]
    present = [token for token in forbidden if token in csp]
    if missing or present:
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if present:
            details.append("forbidden " + ", ".join(present))
        raise ValueError(
            "Desktop CSP no longer constrains WebView networking to the local backend: "
            + "; ".join(details)
        )


def require_desktop_backend_ignores_user_web_token_gate() -> None:
    requirements = {
        DESKTOP_TAURI_LIB_PATH: [
            'const WEB_TOKEN_ENV: &str = "CC_BRANCH_WEB_TOKEN"',
            '.env(WEB_TOKEN_ENV, "")',
        ],
        BACKEND_SIDECAR_SMOKE_SCRIPT_PATH: [
            'env["CC_BRANCH_WEB_TOKEN"] = ""',
        ],
        DESKTOP_SMOKE_SCRIPT_PATH: [
            'env["CC_BRANCH_WEB_TOKEN"] = ""',
        ],
        DESKTOP_BACKEND_ENTRYPOINT_PATH: [
            "default=None",
        ],
    }
    forbidden_tokens = {
        DESKTOP_BACKEND_ENTRYPOINT_PATH: [
            'os.environ.get("CC_BRANCH_WEB_TOKEN")',
            "os.environ.get('CC_BRANCH_WEB_TOKEN')",
        ],
    }
    missing_by_file: list[str] = []
    for path, required_tokens in requirements.items():
        text = path.read_text(encoding="utf-8")
        missing = [token for token in required_tokens if token not in text]
        if path == DESKTOP_TAURI_LIB_PATH and text.count('.env(WEB_TOKEN_ENV, "")') < 2:
            missing.append('second .env(WEB_TOKEN_ENV, "")')
        forbidden = [
            token
            for token in forbidden_tokens.get(path, [])
            if token in text
        ]
        if forbidden:
            missing.append("forbidden " + ", ".join(forbidden))
        if missing:
            missing_by_file.append(f"{path.name}: {', '.join(missing)}")
    if missing_by_file:
        raise ValueError(
            "Desktop backend startup must ignore inherited CC_BRANCH_WEB_TOKEN so user shell state cannot make the packaged app unusable: "
            + "; ".join(missing_by_file)
        )


def require_canary_and_live_quality_gates(workflow: dict[str, Any]) -> None:
    canary_job = require_job(workflow, "canary-installers")
    require_job_needs("canary-installers", canary_job, {"publish-updater-json"})
    require_verifier_matrix("canary-installers", canary_job)
    canary_run = require_step_run(canary_job, "Download and verify draft installer assets")
    if "scripts/verify_github_release.py" not in canary_run:
        raise ValueError("Release workflow canary-installers job does not run verify_github_release.py")
    if "--expected-version" not in canary_run:
        raise ValueError("Release workflow draft installer verification step is missing --expected-version")
    for token in [
        "#### Verification summary",
        "verification_summary missing from release verification report",
        "verification_summary checks missing from release verification report",
        "verification_summary checks failed",
        "ready_for_public_download",
        "verification_summary ready_for_public_download is not true",
        "failed_checks",
        "json.dumps(report['verification_summary']",
    ]:
        if token not in canary_run:
            raise ValueError(
                f"Release workflow draft installer verification step is missing verification summary: {token}"
            )

    publish_job = require_job(workflow, "publish-release")
    require_job_needs("publish-release", publish_job, {"canary-release", "canary-installers"})
    publish_run = require_step_run(publish_job, "Publish draft release")
    for arg in ["gh release edit", "--draft=false", "--prerelease=false", "--latest"]:
        if arg not in publish_run:
            raise ValueError(f"Release workflow publish-release step is missing {arg}")

    live_job = require_job(workflow, "verify-live-release")
    require_job_needs("verify-live-release", live_job, {"publish-release"})
    require_verifier_matrix("verify-live-release", live_job)
    live_run = require_step_run(live_job, "Download and verify published assets")
    for arg in ["scripts/verify_github_release.py", "--expected-version", "--require-latest", "--require-public"]:
        if arg not in live_run:
            raise ValueError(f"Release workflow live verification step is missing {arg}")
    for token in [
        "#### Verification summary",
        "verification_summary missing from release verification report",
        "verification_summary checks missing from release verification report",
        "verification_summary checks failed",
        "ready_for_public_download",
        "verification_summary ready_for_public_download is not true",
        "failed_checks",
        "json.dumps(report['verification_summary']",
    ]:
        if token not in live_run:
            raise ValueError(
                f"Release workflow live verification step is missing verification summary: {token}"
            )

    rollback_job = require_job(workflow, "rollback-live-release")
    require_job_needs(
        "rollback-live-release",
        rollback_job,
        {"publish-release", "verify-live-release"},
    )
    rollback_if = str(rollback_job.get("if") or "")
    for token in [
        "always()",
        "needs.publish-release.result == 'success'",
        "needs.verify-live-release.result != 'success'",
    ]:
        if token not in rollback_if:
            raise ValueError(f"Release workflow rollback-live-release condition is missing {token}")
    rollback_run = require_step_run(rollback_job, "Rollback failed live release")
    for arg in ["gh release edit", "--draft=true", "--prerelease=true"]:
        if arg not in rollback_run:
            raise ValueError(f"Release workflow rollback-live-release step is missing {arg}")


def require_release_workflow_concurrency_gate(workflow: dict[str, Any]) -> None:
    concurrency = workflow.get("concurrency")
    if not isinstance(concurrency, dict):
        if "jobs" not in workflow:
            return
        raise ValueError("Release workflow must define concurrency by release tag")
    group = concurrency.get("group")
    if not isinstance(group, str):
        raise ValueError("Release workflow concurrency group must include the release tag")
    required_tokens = ["release-desktop", "inputs.release_tag || github.ref_name"]
    missing = [token for token in required_tokens if token not in group]
    if missing:
        raise ValueError(
            "Release workflow concurrency group must include the release tag: "
            + ", ".join(missing)
        )
    if concurrency.get("cancel-in-progress") is not False:
        raise ValueError(
            "Release workflow concurrency must not cancel an in-progress release build"
        )


def require_release_quality_gates() -> dict[str, bool]:
    workflow_text = RELEASE_WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)
    if not isinstance(workflow, dict):
        raise ValueError(f"Release workflow is not a YAML mapping: {RELEASE_WORKFLOW_PATH}")
    require_release_workflow_action_refs(workflow)
    require_release_workflow_bash_syntax(workflow)
    require_build_quality_gates(workflow)
    require_desktop_smoke_report_artifact_gate(workflow)
    require_canary_and_live_quality_gates(workflow)
    require_packaged_recovery_report_gates(workflow)
    require_windows_missing_sidecar_temp_cleanup_gate(workflow)
    require_desktop_bundle_output_cleanup_gate(workflow)
    require_desktop_smoke_windows_cleanup_gate()
    require_desktop_smoke_process_table_port_discovery_gate()
    require_github_download_launch_desktop_metadata_gate()
    require_release_notes_support_copy_report_gate()
    require_release_checksum_manifest_gate(workflow)
    require_backend_failure_current_release_gate()
    require_backend_failure_native_release_open_gate()
    require_desktop_backend_port_retry_gate()
    require_desktop_backend_fixed_port_test_gate()
    require_desktop_backend_python_env_sanitized_gate()
    require_desktop_backend_output_tail_gate()
    require_tauri_backend_no_proxy_gate()
    require_tauri_backend_transient_probe_retry_gate()
    require_desktop_webview_fetch_diagnostics_gate()
    require_desktop_csp_local_backend_gate()
    require_desktop_backend_ignores_user_web_token_gate()
    require_startup_failure_recovery_auto_port_gate()
    require_smoke_scripts_no_proxy_loopback_gate()
    require_installer_sidecar_colocation_gate()
    require_windows_installer_acl_repair_gate()
    require_release_workflow_concurrency_gate(workflow)

    return {
        "release_workflow_action_refs": True,
        "release_workflow_bash_syntax": True,
        "release_workflow_concurrency": True,
        "desktop_smoke_report_artifact_upload": True,
        "desktop_smoke_windows_cleanup": True,
        "desktop_smoke_process_table_port_discovery": True,
        "desktop_bundle_output_cleanup": True,
        "desktop_backend_port_retry": True,
        "desktop_backend_fixed_port_test_gate": True,
        "desktop_backend_python_env_sanitized": True,
        "desktop_backend_output_tail": True,
        "tauri_backend_no_proxy_loopback": True,
        "tauri_backend_transient_probe_retry": True,
        "desktop_webview_fetch_diagnostics": True,
        "desktop_csp_local_backend": True,
        "desktop_backend_ignores_user_web_token": True,
        "installer_sidecar_same_directory": True,
        "windows_installer_acl_repair": True,
        "startup_failure_recovery_auto_port": True,
        "desktop_smoke_no_proxy_loopback": True,
        "packaged_desktop_auto_port_smoke": True,
        "release_verification_expected_version": True,
        "bundled_backend_sidecar_smoke": True,
        "backend_sidecar_desktop_metadata_smoke": True,
        "packaged_desktop_app_smoke": True,
        "packaged_desktop_startup_diagnostics_metadata": True,
        "desktop_smoke_port_mode_report": True,
        "backend_failure_current_release_link": True,
        "backend_failure_native_release_open": True,
        "packaged_desktop_metadata_value_smoke_per_platform": True,
        "missing_sidecar_failure_smoke": True,
        "packaged_desktop_missing_sidecar_smoke_per_platform": True,
        "packaged_desktop_startup_failure_recovery_smoke_per_platform": True,
        "packaged_desktop_startup_failure_recovery_report": True,
        "Windows_missing_sidecar_clean_temp_directory": True,
        "packaged_desktop_stale_backend_rejection_smoke_per_platform": True,
        "standalone_installer_launch_desktop_metadata": True,
        "draft_installer_canary": True,
        "live_GitHub_download_verification": True,
        "live_release_rollback_on_failed_verification": True,
        "GitHub_download_launch_desktop_metadata": True,
        "GitHub_download_launch_port_mode": True,
        "GitHub_download_verification_summary": True,
        "release_verification_summary_step_summary": True,
        "latest_release_assertion": True,
        "public_release_assertion": True,
        "release_notes_platform_install_copy": True,
        "release_notes_source_code_warning": True,
        "release_notes_copy_report_support": True,
        "release_checksum_manifest": True,
        "macOS_DMG_launch": True,
        "macOS_DMG_applications_shortcut": True,
        "macOS_DMG_installed_copy_launch": True,
        "macOS_DMG_stale_backend_rejection": True,
        "Linux_AppImage_launch": True,
        "Linux_DEB_launch": True,
        "Linux_DEB_stale_backend_rejection": True,
        "Linux_RPM_launch": True,
        "Linux_RPM_stale_backend_rejection": True,
        "Linux_AppImage_stale_backend_rejection": True,
        "Windows_MSI_launch": True,
        "Windows_MSI_stale_backend_rejection": True,
        "Windows_NSIS_launch": True,
        "Windows_NSIS_stale_backend_rejection": True,
    }


def require_tag_available(tag: str) -> None:
    output = run_text(["git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}"])
    if output.strip():
        raise ValueError(f"Remote tag already exists: {tag}")


def require_release_available(tag: str, repo: str) -> None:
    output = run_text(
        gh_command(["release", "view", tag], repo),
        check=False,
    )
    if output.strip():
        raise ValueError(f"GitHub release already exists: {tag}")


def preflight(tag: str, repo: str) -> dict[str, Any]:
    version_result = verify_versions(tag, require_v_prefix=True)
    normalized = normalize_expected(tag, require_v_prefix=True)
    require_tag_available(f"v{normalized}")
    require_release_available(f"v{normalized}", repo)
    workflow = require_release_workflow(repo)
    secrets = require_required_secrets(repo)
    actions = require_actions_enabled(repo)
    workflow_permissions = require_workflow_write_permissions(repo)
    quality_gates = require_release_quality_gates()
    return {
        "ok": True,
        "tag": f"v{normalized}",
        "version": normalized,
        "workflow": workflow,
        "secrets": secrets,
        "actions": actions,
        "workflow_permissions": workflow_permissions,
        "quality_gates": quality_gates,
        "version_files": version_result.get("files", {}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="release tag, for example v1.0.2")
    parser.add_argument("--repo", default="GeminiLight/cc-branch")
    args = parser.parse_args(argv)

    result = preflight(args.tag, args.repo)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
