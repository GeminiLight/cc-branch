#!/usr/bin/env python3
"""Smoke-test a built desktop backend sidecar."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener


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


def local_urlopen(request, *, timeout: float):
    return build_opener(ProxyHandler({})).open(request, timeout=timeout)


def pick_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def isolated_backend_env(
    home_dir: Path,
    base_env: dict[str, str] | None = None,
    *,
    desktop_version: str | None = None,
    desktop_platform: str | None = None,
    desktop_arch: str | None = None,
) -> dict[str, str]:
    env = dict(os.environ if base_env is None else base_env)
    env["HOME"] = str(home_dir)
    env["USERPROFILE"] = str(home_dir)
    env["APPDATA"] = str(home_dir / "AppData" / "Roaming")
    env["LOCALAPPDATA"] = str(home_dir / "AppData" / "Local")
    env["XDG_CONFIG_HOME"] = str(home_dir / ".config")
    env["XDG_DATA_HOME"] = str(home_dir / ".local" / "share")
    for name in BACKEND_POISON_ENV:
        env.pop(name, None)
    env["CC_BRANCH_BACKEND_SOURCE"] = BUNDLED_BACKEND_SOURCE
    env["CC_BRANCH_WEB_TOKEN"] = ""
    if desktop_version:
        env["CC_BRANCH_DESKTOP_VERSION"] = normalize_version(desktop_version)
    if desktop_platform:
        env["CC_BRANCH_DESKTOP_PLATFORM"] = desktop_platform
    if desktop_arch:
        env["CC_BRANCH_DESKTOP_ARCH"] = desktop_arch
    return env


def normalize_version(version: str) -> str:
    value = version.strip()
    return value[1:] if value.startswith("v") else value


def wait_for_info(port: int, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{port}/api/info"
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with local_urlopen(url, timeout=1) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError) as error:
            last_error = error
            time.sleep(0.2)
    raise RuntimeError(f"Backend sidecar did not answer {url}: {last_error}")


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


def assert_backend_source(info: dict) -> None:
    if info.get("backend_source") != BUNDLED_BACKEND_SOURCE:
        raise RuntimeError(
            "Backend sidecar did not report the bundled-sidecar source marker: "
            f"{info.get('backend_source')!r}"
        )


def assert_desktop_metadata(
    info: dict,
    *,
    expected_version: str | None,
    expected_platform: str | None,
    expected_arch: str | None,
) -> dict[str, str]:
    expected = {
        "desktop_version": normalize_version(expected_version) if expected_version else None,
        "desktop_platform": expected_platform,
        "desktop_arch": expected_arch,
    }
    metadata: dict[str, str] = {}
    for key, expected_value in expected.items():
        if expected_value is None:
            continue
        value = info.get(key)
        if value != expected_value:
            raise RuntimeError(
                f"Backend sidecar reported wrong {key}: got {value!r}, expected {expected_value!r}"
            )
        metadata[key] = value
    return metadata


def assert_first_run_api_ready(
    port: int,
    workspace: Path,
    config_path: Path,
    state_path: Path,
    home_dir: Path,
) -> dict:
    """Verify the desktop first-run API path works against an isolated home."""
    projects = request_json(port, "/api/projects")
    if projects.get("projects") != []:
        raise RuntimeError(f"Expected empty first-run project index: {projects!r}")
    storage_path = Path(str(projects.get("storage_path") or ""))
    if home_dir.resolve() not in [parent.resolve() for parent in storage_path.parents]:
        raise RuntimeError(f"Project index escaped isolated home: {projects!r}")

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
    if Path(str(status.get("config_path"))).resolve() != config_path.resolve():
        raise RuntimeError(f"Workspace status reported wrong config path: {status!r}")

    initialized = request_json(
        port,
        f"/api/init?project_path={quote(str(workspace))}",
        method="POST",
        body={"profile": "development", "bootstrap_sessions": False},
    )
    if initialized.get("success") is not True:
        raise RuntimeError(f"Workspace init did not succeed: {initialized!r}")
    if Path(str(initialized.get("config_path") or "")).resolve() != config_path.resolve():
        raise RuntimeError(f"Workspace init reported wrong config path: {initialized!r}")
    if Path(str(initialized.get("state_path") or "")).resolve() != state_path.resolve():
        raise RuntimeError(f"Workspace init reported wrong state path: {initialized!r}")
    if not config_path.exists():
        raise RuntimeError(f"Workspace init did not create config: {config_path}")
    if not state_path.exists():
        raise RuntimeError(f"Workspace init did not create state: {state_path}")

    ready_status = request_json(port, f"/api/status?project_path={quote(str(workspace))}")
    if ready_status.get("status") != "ready":
        raise RuntimeError(f"Workspace status did not become ready after init: {ready_status!r}")
    if Path(str(ready_status.get("config_path"))).resolve() != config_path.resolve():
        raise RuntimeError(f"Ready workspace status reported wrong config path: {ready_status!r}")

    return {
        "projects_storage_path": str(storage_path),
        "project_status": status["status"],
        "ready_status": ready_status["status"],
        "config_path": str(config_path),
        "state_path": str(state_path),
        "initialized": True,
    }


def build_smoke_result(
    *,
    port: int,
    executable: Path,
    backend_source: str,
    first_run: dict,
    desktop_metadata: dict[str, str] | None = None,
) -> dict:
    return {
        "ok": True,
        "port": port,
        "executable": str(executable),
        "backend_source": backend_source,
        **(desktop_metadata or {}),
        "first_run": first_run,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path, help="path to cc-branch-backend sidecar")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--expected-version", default=None)
    parser.add_argument("--expected-platform", default=None)
    parser.add_argument("--expected-arch", default=None)
    args = parser.parse_args(argv)

    executable = args.executable.resolve()
    if not executable.exists():
        raise FileNotFoundError(executable)

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "backend-workspace"
        workspace.mkdir(parents=True)
        home_dir = Path(tmp) / "home"
        home_dir.mkdir()
        config_path = workspace / ".cc-branch" / "config.yaml"
        state_path = workspace / ".cc-branch" / "state.yaml"
        port = pick_port()
        env = isolated_backend_env(
            home_dir,
            desktop_version=args.expected_version,
            desktop_platform=args.expected_platform,
            desktop_arch=args.expected_arch,
        )
        process = subprocess.Popen(
            [
                str(executable),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--config",
                str(config_path),
                "--state",
                str(state_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        try:
            info = wait_for_info(port, args.timeout)
            if info.get("port") != port:
                raise RuntimeError(f"Backend reported wrong port: {info!r}")
            assert_backend_source(info)
            desktop_metadata = assert_desktop_metadata(
                info,
                expected_version=args.expected_version,
                expected_platform=args.expected_platform,
                expected_arch=args.expected_arch,
            )
            if Path(str(info.get("config_path"))).resolve() != config_path.resolve():
                raise RuntimeError(f"Backend reported wrong config path: {info!r}")
            first_run = assert_first_run_api_ready(
                port,
                workspace,
                config_path,
                state_path,
                home_dir,
            )
            print(
                json.dumps(
                    build_smoke_result(
                        port=port,
                        executable=executable,
                        backend_source=info["backend_source"],
                        first_run=first_run,
                        desktop_metadata=desktop_metadata,
                    ),
                    indent=2,
                )
            )
            return 0
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
