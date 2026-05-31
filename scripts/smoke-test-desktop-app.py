#!/usr/bin/env python3
"""Smoke-test a packaged desktop app launching its bundled backend."""

from __future__ import annotations

import argparse
import json
import os
import queue
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import ProxyHandler
from urllib.request import Request
from urllib.request import build_opener


BACKEND_PORT_RE = re.compile(
    r"\[tauri\]\s+Bundled backend sidecar started on port\s+(?P<port>\d+)"
)
BACKEND_PORT_ARG_RE = re.compile(r"(?:^|\s)--port(?:=|\s+)(?P<port>\d+)(?:\s|$)")
DESKTOP_PORT_ENV = "CC_BRANCH_DESKTOP_PORT"
DESKTOP_ALLOW_FIXED_PORT_ENV = "CC_BRANCH_DESKTOP_ALLOW_FIXED_PORT"
BACKEND_SOURCE_ENV = "CC_BRANCH_BACKEND_SOURCE"
BUNDLED_BACKEND_SOURCE = "bundled-sidecar"
BACKEND_POISON_ENV = (
    "PYTHONHOME",
    "PYTHONPATH",
    "VIRTUAL_ENV",
    "CONDA_PREFIX",
    "CONDA_DEFAULT_ENV",
    "LD_LIBRARY_PATH",
    "DYLD_LIBRARY_PATH",
)


def temporary_directory(prefix: str):
    try:
        return tempfile.TemporaryDirectory(
            prefix=prefix,
            ignore_cleanup_errors=True,
        )
    except TypeError:
        return tempfile.TemporaryDirectory(prefix=prefix)


def local_urlopen(request, *, timeout: float):
    return build_opener(ProxyHandler({})).open(request, timeout=timeout)


def parse_backend_port(line: str) -> int | None:
    match = BACKEND_PORT_RE.search(line)
    if not match:
        return None
    port = int(match.group("port"))
    if port <= 0 or port > 65535:
        raise ValueError(f"Invalid backend port in desktop app log: {line.strip()}")
    return port


def parse_backend_port_arg(command: str) -> int | None:
    match = BACKEND_PORT_ARG_RE.search(command)
    if not match:
        return None
    port = int(match.group("port"))
    if port <= 0 or port > 65535:
        return None
    return port


def discover_backend_port_from_process_table(home_dir: Path) -> int | None:
    if os.name == "nt":
        return None
    try:
        result = subprocess.run(
            ["ps", "-axo", "command"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    home = str(home_dir.resolve())
    for line in result.stdout.splitlines():
        if "cc-branch-backend" not in line or home not in line:
            continue
        port = parse_backend_port_arg(line)
        if port is not None:
            return port
    return None


def app_executable_from_bundle(path: Path) -> Path:
    if path.is_file():
        return path.resolve()
    contents = path / "Contents" / "MacOS"
    executable = contents / "cc-branch"
    if executable.exists():
        return executable.resolve()
    candidates = [item for item in contents.glob("*") if item.is_file() and os.access(item, os.X_OK)]
    if len(candidates) == 1:
        return candidates[0].resolve()
    raise FileNotFoundError(f"Could not find packaged app executable under {contents}")


def sidecar_executable_from_app_executable(executable: Path) -> Path:
    suffix = ".exe" if executable.suffix.lower() == ".exe" else ""
    sidecar = executable.with_name(f"cc-branch-backend{suffix}")
    if sidecar.exists():
        return sidecar.resolve()
    raise FileNotFoundError(f"Could not find bundled backend sidecar next to {executable}: {sidecar}")


def request_json(port: int, path: str, *, method: str = "GET", body: dict | None = None) -> dict:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    with local_urlopen(request, timeout=3) as response:
        return json.loads(response.read().decode("utf-8"))


def pick_unused_localhost_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def isolated_desktop_env(home_dir: Path, base_env: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if base_env is None else base_env)
    env["HOME"] = str(home_dir)
    env["USERPROFILE"] = str(home_dir)
    env["APPDATA"] = str(home_dir / "AppData" / "Roaming")
    env["LOCALAPPDATA"] = str(home_dir / "AppData" / "Local")
    env["XDG_CONFIG_HOME"] = str(home_dir / ".config")
    env["XDG_DATA_HOME"] = str(home_dir / ".local" / "share")
    for name in BACKEND_POISON_ENV:
        env.pop(name, None)
    env["CC_BRANCH_WEB_TOKEN"] = ""
    env.pop(DESKTOP_PORT_ENV, None)
    env.pop(DESKTOP_ALLOW_FIXED_PORT_ENV, None)
    return env


def write_backend_workspace(home_dir: Path, name: str) -> tuple[Path, Path]:
    cc_dir = home_dir / ".cc-branch" / "app" / "backend-workspace" / ".cc-branch"
    cc_dir.mkdir(parents=True, exist_ok=True)
    config_path = cc_dir / "config.yaml"
    state_path = cc_dir / "state.yaml"
    config_path.write_text(f"workspace:\n  name: {name}\n", encoding="utf-8")
    state_path.write_text("version: 1\nwindows: {}\nslots: {}\n", encoding="utf-8")
    return config_path, state_path


def assert_first_run_project_flow(port: int, home_dir: Path) -> dict:
    workspace = home_dir / "first-run-project"
    workspace.mkdir(parents=True, exist_ok=True)
    expected_config_path = workspace / ".cc-branch" / "config.yaml"
    expected_state_path = workspace / ".cc-branch" / "state.yaml"

    projects = request_json(port, "/api/projects")
    if projects.get("projects") != []:
        raise RuntimeError(f"Expected empty first-run project index: {projects!r}")
    storage_path = Path(str(projects.get("storage_path") or ""))
    if home_dir.resolve() not in [parent.resolve() for parent in storage_path.parents]:
        raise RuntimeError(f"Desktop project index escaped isolated home: {projects!r}")

    probe = request_json(port, f"/api/project/probe?project_path={quote(str(workspace))}")
    if probe.get("status") != "needs_init" or not probe.get("path_exists"):
        raise RuntimeError(f"Project probe did not report first-run setup state: {probe!r}")

    added = request_json(
        port,
        "/api/projects/add",
        method="POST",
        body={"path": str(workspace), "name": "Smoke Project"},
    )
    if added.get("active_project_id") is None or len(added.get("projects", [])) != 1:
        raise RuntimeError(f"Project add did not persist active project: {added!r}")
    if Path(str(added["projects"][0].get("path"))).resolve() != workspace.resolve():
        raise RuntimeError(f"Project add persisted wrong path: {added!r}")

    status = request_json(port, f"/api/status?project_path={quote(str(workspace))}")
    if status.get("status") != "needs_init":
        raise RuntimeError(f"Workspace status did not report first-run setup state: {status!r}")
    if Path(str(status.get("config_path"))).resolve() != expected_config_path.resolve():
        raise RuntimeError(f"Workspace status reported wrong config path: {status!r}")

    initialized = request_json(
        port,
        f"/api/init?project_path={quote(str(workspace))}",
        method="POST",
        body={"profile": "development", "bootstrap_sessions": False},
    )
    if initialized.get("success") is not True:
        raise RuntimeError(f"Workspace init did not succeed: {initialized!r}")
    if Path(str(initialized.get("config_path") or "")).resolve() != expected_config_path.resolve():
        raise RuntimeError(f"Workspace init reported wrong config path: {initialized!r}")
    if Path(str(initialized.get("state_path") or "")).resolve() != expected_state_path.resolve():
        raise RuntimeError(f"Workspace init reported wrong state path: {initialized!r}")
    if not expected_config_path.exists():
        raise RuntimeError(f"Workspace init did not create config: {expected_config_path}")
    if not expected_state_path.exists():
        raise RuntimeError(f"Workspace init did not create state: {expected_state_path}")

    ready_status = request_json(port, f"/api/status?project_path={quote(str(workspace))}")
    if ready_status.get("status") != "ready":
        raise RuntimeError(f"Workspace status did not become ready after init: {ready_status!r}")
    if Path(str(ready_status.get("config_path"))).resolve() != expected_config_path.resolve():
        raise RuntimeError(f"Ready workspace status reported wrong config path: {ready_status!r}")

    return {
        "project_path": str(workspace),
        "projects_storage_path": str(storage_path),
        "project_status": status["status"],
        "ready_status": ready_status["status"],
        "config_path": str(expected_config_path),
        "state_path": str(expected_state_path),
        "initialized": True,
    }


def wait_for_backend_port(
    process: subprocess.Popen[str],
    timeout: float,
    discovery_root: Path | None = None,
) -> tuple[int, list[str]]:
    deadline = time.monotonic() + timeout
    lines: list[str] = []
    next_discovery_at = 0.0
    assert process.stdout is not None
    line_queue: queue.Queue[str | None] = queue.Queue()

    def read_stdout() -> None:
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                line_queue.put(line.rstrip())
        finally:
            line_queue.put(None)

    threading.Thread(target=read_stdout, daemon=True).start()

    while time.monotonic() < deadline:
        remaining = max(0.0, min(0.2, deadline - time.monotonic()))
        try:
            line = line_queue.get(timeout=remaining)
        except queue.Empty:
            if process.poll() is not None:
                break
            if discovery_root is not None and time.monotonic() >= next_discovery_at:
                next_discovery_at = time.monotonic() + 0.5
                discovered_port = discover_backend_port_from_process_table(discovery_root)
                if discovered_port is not None:
                    lines.append(
                        "[smoke] Discovered bundled backend sidecar port "
                        f"{discovered_port} from process table"
                    )
                    return discovered_port, lines
            continue

        if line is None:
            if process.poll() is not None:
                break
            if discovery_root is not None and time.monotonic() >= next_discovery_at:
                next_discovery_at = time.monotonic() + 0.5
                discovered_port = discover_backend_port_from_process_table(discovery_root)
                if discovered_port is not None:
                    lines.append(
                        "[smoke] Discovered bundled backend sidecar port "
                        f"{discovered_port} from process table"
                    )
                    return discovered_port, lines
            continue

        lines.append(line)
        port = parse_backend_port(line)
        if port is not None:
            return port, lines

    output = "\n".join(lines[-40:])
    if process.poll() is not None:
        raise RuntimeError(f"Desktop app exited before backend startup.\n{output}")
    raise RuntimeError(f"Desktop app did not report bundled backend startup within {timeout}s.\n{output}")


def start_stdout_reader(process: subprocess.Popen[str]) -> list[str]:
    lines: list[str] = []
    if process.stdout is None:
        return lines

    def read_stdout() -> None:
        while True:
            line = process.stdout.readline()
            if not line or not isinstance(line, str):
                break
            lines.append(line.rstrip())

    threading.Thread(target=read_stdout, daemon=True).start()
    return lines


def wait_for_backend_info(
    port: int,
    process: subprocess.Popen[str],
    timeout: float,
    logs: list[str] | None = None,
) -> dict:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            info = request_json(port, "/api/info")
        except (OSError, TimeoutError, URLError, json.JSONDecodeError) as error:
            last_error = error
            if process.poll() is not None:
                output = "\n".join((logs or [])[-40:])
                raise RuntimeError(f"Desktop app exited before backend became ready.\n{output}") from error
            time.sleep(0.2)
            continue

        return info

    output = "\n".join((logs or [])[-40:])
    raise RuntimeError(
        f"Desktop backend did not respond on 127.0.0.1:{port} within {timeout}s. "
        f"Last error: {last_error}\n{output}"
    )


def normalize_expected_version(version: str | None) -> str | None:
    if version is None:
        return None
    value = version.strip()
    return value[1:] if value.startswith("v") else value


def require_desktop_metadata(
    info: dict,
    *,
    expected_version: str | None = None,
    expected_platform: str | None = None,
    expected_arch: str | None = None,
) -> dict:
    metadata = {}
    for key in ("desktop_version", "desktop_platform", "desktop_arch"):
        value = info.get(key)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"Desktop backend /api/info is missing {key}: {info!r}")
        metadata[key] = value
    expected_values = {
        "desktop_version": normalize_expected_version(expected_version),
        "desktop_platform": expected_platform,
        "desktop_arch": expected_arch,
    }
    for key, expected_value in expected_values.items():
        if expected_value is not None and metadata[key] != expected_value:
            raise RuntimeError(
                f"Desktop backend /api/info reported wrong {key}: got {metadata[key]!r}, "
                f"expected {expected_value!r}"
            )
    return metadata


def wait_for_startup_error(
    process: subprocess.Popen[str],
    timeout: float,
    expected_error: str,
) -> list[str]:
    deadline = time.monotonic() + timeout
    lines: list[str] = []
    assert process.stdout is not None
    line_queue: queue.Queue[str | None] = queue.Queue()

    def read_stdout() -> None:
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                line_queue.put(line.rstrip())
        finally:
            line_queue.put(None)

    threading.Thread(target=read_stdout, daemon=True).start()

    while time.monotonic() < deadline:
        remaining = max(0.0, min(0.2, deadline - time.monotonic()))
        try:
            line = line_queue.get(timeout=remaining)
        except queue.Empty:
            if process.poll() is not None:
                break
            continue

        if line is None:
            if process.poll() is not None:
                break
            continue

        lines.append(line)
        if parse_backend_port(line) is not None:
            raise RuntimeError(
                "Desktop app unexpectedly reported bundled backend startup while waiting "
                f"for startup failure {expected_error!r}.\n" + "\n".join(lines[-40:])
            )
        if expected_error in line:
            return lines

    output = "\n".join(lines[-40:])
    raise RuntimeError(
        f"Desktop app did not report expected startup error within {timeout}s: {expected_error!r}\n{output}"
    )


def verify_desktop_app(
    executable: Path,
    *,
    timeout: float,
    expected_version: str | None = None,
    expected_platform: str | None = None,
    expected_arch: str | None = None,
    use_auto_port: bool = False,
) -> dict:
    with temporary_directory(prefix="cc-branch-desktop-smoke-") as tmp:
        home_dir = Path(tmp) / "home"
        home_dir.mkdir()
        env = isolated_desktop_env(home_dir)
        port: int | None = None
        if not use_auto_port:
            port = pick_unused_localhost_port()
            env[DESKTOP_PORT_ENV] = str(port)
            env[DESKTOP_ALLOW_FIXED_PORT_ENV] = "1"

        process = subprocess.Popen(
            [str(executable)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            cwd=home_dir,
        )
        try:
            if use_auto_port:
                port, logs = wait_for_backend_port(process, timeout, discovery_root=home_dir)
            else:
                logs = start_stdout_reader(process)
            assert port is not None
            info = wait_for_backend_info(port, process, timeout, logs)
            if info.get("port") != port:
                raise RuntimeError(f"Desktop backend reported wrong port: {info!r}")
            if info.get("backend_source") != "bundled-sidecar":
                raise RuntimeError(
                    "Desktop smoke test reached a backend, but it was not the bundled backend sidecar. "
                    f"Expected backend_source='bundled-sidecar', got {info.get('backend_source')!r}."
                )
            desktop_metadata = require_desktop_metadata(
                info,
                expected_version=expected_version,
                expected_platform=expected_platform,
                expected_arch=expected_arch,
            )
            config_path = Path(str(info.get("config_path") or ""))
            state_path = Path(str(info.get("state_path") or ""))
            if home_dir.resolve() not in [parent.resolve() for parent in config_path.parents]:
                raise RuntimeError(f"Desktop backend config escaped isolated home: {info!r}")
            if home_dir.resolve() not in [parent.resolve() for parent in state_path.parents]:
                raise RuntimeError(f"Desktop backend state escaped isolated home: {info!r}")

            first_run = assert_first_run_project_flow(port, home_dir)

            return {
                "ok": True,
                "executable": str(executable),
                "port": port,
                "port_mode": "auto" if use_auto_port else "fixed",
                "backend_source": info["backend_source"],
                **desktop_metadata,
                "config_path": str(config_path),
                "state_path": str(state_path),
                "projects_storage_path": first_run["projects_storage_path"],
                "first_run": first_run,
                "startup_log": logs[-5:],
            }
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def verify_desktop_startup_failure(
    executable: Path,
    *,
    timeout: float,
    expected_error: str,
) -> dict:
    with temporary_directory(prefix="cc-branch-desktop-smoke-failure-") as tmp:
        home_dir = Path(tmp) / "home"
        home_dir.mkdir()
        env = isolated_desktop_env(home_dir)
        port = pick_unused_localhost_port()
        env[DESKTOP_PORT_ENV] = str(port)
        env[DESKTOP_ALLOW_FIXED_PORT_ENV] = "1"

        process = subprocess.Popen(
            [str(executable)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            cwd=home_dir,
        )
        try:
            logs = wait_for_startup_error(process, timeout, expected_error)
            try:
                info = request_json(port, "/api/info")
            except Exception:
                info = None
            if info is not None:
                raise RuntimeError(
                    "Desktop app reported an expected startup failure, but a backend API became ready: "
                    f"{info!r}"
                )

            return {
                "ok": True,
                "executable": str(executable),
                "port": port,
                "port_mode": "fixed",
                "backend_ready": False,
                "expected_error": expected_error,
                "startup_log": logs[-20:],
            }
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def verify_desktop_startup_failure_recovery(
    executable: Path,
    *,
    recovery_sidecar: Path,
    timeout: float,
    expected_error: str,
    expected_version: str | None = None,
    expected_platform: str | None = None,
    expected_arch: str | None = None,
) -> dict:
    failure = verify_desktop_startup_failure(
        executable,
        timeout=timeout,
        expected_error=expected_error,
    )
    restored_sidecar = executable.with_name(
        f"cc-branch-backend{'.exe' if executable.suffix.lower() == '.exe' else ''}"
    )
    shutil.copy2(recovery_sidecar, restored_sidecar)
    restored_sidecar.chmod(restored_sidecar.stat().st_mode | 0o111)
    recovery = verify_desktop_app(
        executable,
        timeout=timeout,
        expected_version=expected_version,
        expected_platform=expected_platform,
        expected_arch=expected_arch,
        use_auto_port=True,
    )
    return {
        "ok": True,
        "executable": str(executable),
        "restored_sidecar": str(restored_sidecar),
        "failure": failure,
        "recovery": recovery,
    }


def verify_desktop_rejects_stale_backend(
    executable: Path,
    *,
    sidecar_executable: Path,
    timeout: float,
    expected_error: str = "Unexpected backend",
) -> dict:
    with temporary_directory(prefix="cc-branch-desktop-stale-backend-") as old_tmp, temporary_directory(
        prefix="cc-branch-desktop-stale-reject-"
    ) as new_tmp:
        stale_home = Path(old_tmp) / "stale-home"
        desktop_home = Path(new_tmp) / "desktop-home"
        stale_home.mkdir()
        desktop_home.mkdir()
        stale_config_path, stale_state_path = write_backend_workspace(stale_home, "Stale Backend")
        port = pick_unused_localhost_port()

        stale_env = isolated_desktop_env(stale_home)
        stale_env[BACKEND_SOURCE_ENV] = BUNDLED_BACKEND_SOURCE
        stale_process = subprocess.Popen(
            [
                str(sidecar_executable.resolve()),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--config",
                str(stale_config_path),
                "--state",
                str(stale_state_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=stale_env,
            cwd=stale_home,
        )
        try:
            stale_logs = start_stdout_reader(stale_process)
            stale_info = wait_for_backend_info(port, stale_process, timeout, stale_logs)
            reported_config = str(stale_info.get("config_path") or "")
            if reported_config and Path(reported_config).resolve() != stale_config_path.resolve():
                raise RuntimeError(f"Stale backend reported wrong config path: {stale_info!r}")

            desktop_env = isolated_desktop_env(desktop_home)
            desktop_env[DESKTOP_PORT_ENV] = str(port)
            desktop_env[DESKTOP_ALLOW_FIXED_PORT_ENV] = "1"
            desktop_process = subprocess.Popen(
                [str(executable.resolve())],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=desktop_env,
                cwd=desktop_home,
            )
            try:
                logs = wait_for_startup_error(desktop_process, timeout, expected_error)
                return {
                    "ok": True,
                    "executable": str(executable.resolve()),
                    "stale_backend_executable": str(sidecar_executable.resolve()),
                    "port": port,
                    "port_mode": "fixed",
                    "stale_backend_source": stale_info.get("backend_source") or "unknown",
                    "stale_backend_config_path": str(stale_config_path),
                    "expected_error": expected_error,
                    "startup_log": logs[-20:],
                }
            finally:
                desktop_process.terminate()
                try:
                    desktop_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    desktop_process.kill()
                    desktop_process.wait(timeout=5)
        finally:
            stale_process.terminate()
            try:
                stale_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                stale_process.kill()
                stale_process.wait(timeout=5)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path, help="path to packaged .app bundle or executable")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--expect-startup-failure",
        action="store_true",
        help="verify that the app reports an expected backend startup failure instead of starting a backend",
    )
    parser.add_argument(
        "--expect-stale-backend-rejection",
        action="store_true",
        help="verify the app rejects a stale cc-branch backend already listening on the chosen port",
    )
    parser.add_argument(
        "--expect-startup-failure-recovery",
        action="store_true",
        help="verify missing-sidecar startup failure, restore the sidecar, then verify the app starts",
    )
    parser.add_argument(
        "--recovery-sidecar",
        type=Path,
        default=None,
        help="sidecar executable to copy next to the app for --expect-startup-failure-recovery",
    )
    parser.add_argument(
        "--sidecar",
        type=Path,
        default=None,
        help="backend sidecar executable to use for --expect-stale-backend-rejection; defaults to a sibling cc-branch-backend executable",
    )
    parser.add_argument(
        "--expect-error",
        default=None,
        help="substring that must appear in startup logs for the selected negative smoke mode",
    )
    parser.add_argument("--expected-version", default=None)
    parser.add_argument("--expected-platform", default=None)
    parser.add_argument("--expected-arch", default=None)
    parser.add_argument(
        "--use-auto-port",
        action="store_true",
        help="do not set CC_BRANCH_DESKTOP_PORT; follow the packaged app's normal auto-selected backend port",
    )
    args = parser.parse_args(argv)

    executable = app_executable_from_bundle(args.app.resolve())
    selected_modes = [
        args.expect_startup_failure,
        args.expect_stale_backend_rejection,
        args.expect_startup_failure_recovery,
    ]
    if sum(1 for selected in selected_modes if selected) > 1:
        raise ValueError("Choose only one negative smoke mode")
    if args.expect_startup_failure:
        result = verify_desktop_startup_failure(
            executable,
            timeout=args.timeout,
            expected_error=args.expect_error or "Python fallback is disabled in release builds",
        )
    elif args.expect_startup_failure_recovery:
        if args.recovery_sidecar is None:
            raise ValueError("--expect-startup-failure-recovery requires --recovery-sidecar")
        result = verify_desktop_startup_failure_recovery(
            executable,
            recovery_sidecar=args.recovery_sidecar.resolve(),
            timeout=args.timeout,
            expected_error=args.expect_error or "Python fallback is disabled in release builds",
            expected_version=args.expected_version,
            expected_platform=args.expected_platform,
            expected_arch=args.expected_arch,
        )
    elif args.expect_stale_backend_rejection:
        sidecar = args.sidecar.resolve() if args.sidecar else sidecar_executable_from_app_executable(executable)
        result = verify_desktop_rejects_stale_backend(
            executable,
            sidecar_executable=sidecar,
            timeout=args.timeout,
            expected_error=args.expect_error or "Unexpected backend",
        )
    else:
        result = verify_desktop_app(
            executable,
            timeout=args.timeout,
            expected_version=args.expected_version,
            expected_platform=args.expected_platform,
            expected_arch=args.expected_arch,
            use_auto_port=args.use_auto_port,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
