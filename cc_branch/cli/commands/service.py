"""CLI service lifecycle commands for the local Web UI backend."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ...app_state.paths import app_data_dir
from ...context import WorkspaceContext
from ...constants import CONFIG_DIR


SERVICE_METADATA = "webui-service.json"
SERVICE_LOG = "webui-service.log"


@dataclass(frozen=True)
class ServicePaths:
    metadata: Path
    log: Path


@dataclass
class ServiceMetadata:
    pid: int
    url: str
    host: str
    port: int
    project_dir: str
    config_path: str
    state_path: str
    log_path: str
    started_at: float
    command: list[str]


def service_paths(ctx: WorkspaceContext) -> ServicePaths:
    del ctx
    generated_dir = app_data_dir()
    return ServicePaths(
        metadata=generated_dir / SERVICE_METADATA,
        log=generated_dir / SERVICE_LOG,
    )


def service_backend_workspace_dir() -> Path:
    return app_data_dir() / "backend-workspace"


def service_backend_paths() -> tuple[Path, Path]:
    backend_dir = service_backend_workspace_dir()
    return (
        backend_dir / CONFIG_DIR / "config.yaml",
        backend_dir / CONFIG_DIR / "state.yaml",
    )


def process_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def terminate_process(pid: int) -> None:
    if os.name == "nt":
        os.kill(pid, signal.SIGTERM)
    else:
        os.kill(pid, signal.SIGTERM)


def run_service(ctx: WorkspaceContext, args: Any) -> int:
    command = getattr(args, "service_command", None)
    if command == "start":
        return run_service_start(ctx, args)
    if command == "status":
        return run_service_status(ctx)
    if command == "stop":
        return run_service_stop(ctx, args)
    if command == "restart":
        stop_code = run_service_stop(ctx, args, quiet=True)
        if stop_code not in (0, 3):
            return stop_code
        return run_service_start(ctx, args)
    if command == "logs":
        return run_service_logs(ctx, args)
    print("Usage: cc-branch service <start|status|stop|restart|logs>")
    return 2


def run_service_start(ctx: WorkspaceContext, args: Any) -> int:
    import cc_branch.cli as cli

    from ...webui.server.static import missing_static_assets_message, static_assets_available
    from .serve import is_loopback_host

    paths = service_paths(ctx)
    existing = _load_metadata(paths.metadata)
    if existing and process_is_running(int(existing.get("pid", 0))):
        print(f"CC Branch Web UI service is already running at {existing.get('url')} (pid {existing.get('pid')})")
        return 0

    token = args.token or os.environ.get("CC_BRANCH_WEB_TOKEN")
    if not is_loopback_host(args.host) and not token:
        cli.console.print(
            "[red]✗[/red] Refusing to bind Web UI service to a non-loopback host without authentication."
        )
        cli.console.print(
            "[dim]Use --token or CC_BRANCH_WEB_TOKEN when serving beyond localhost.[/dim]"
        )
        return 1
    if not static_assets_available():
        cli.console.print(f"[red]✗[/red] {missing_static_assets_message()}")
        return 1

    paths.metadata.parent.mkdir(parents=True, exist_ok=True)
    config_path, state_path = service_backend_paths()
    project_dir = service_backend_workspace_dir()
    project_dir.mkdir(parents=True, exist_ok=True)
    host = args.host
    port = int(args.port)
    url = f"http://{host}:{port}"
    command = [
        sys.executable,
        "-m",
        "cc_branch",
        "--project",
        str(project_dir),
        "--config",
        str(config_path),
        "--state",
        str(state_path),
        "serve",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if token:
        command.extend(["--token", token])

    env = os.environ.copy()
    env["CC_BRANCH_BACKEND_SCOPE"] = "app"

    log_file = paths.log.open("ab")
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=str(project_dir),
            close_fds=(os.name != "nt"),
            start_new_session=(os.name != "nt"),
            creationflags=_creation_flags(),
            env=env,
        )
    finally:
        log_file.close()

    metadata = ServiceMetadata(
        pid=process.pid,
        url=url,
        host=host,
        port=port,
        project_dir=str(project_dir),
        config_path=str(config_path),
        state_path=str(state_path),
        log_path=str(paths.log),
        started_at=time.time(),
        command=command,
    )
    _write_metadata(paths.metadata, metadata)
    print(f"Started CC Branch Web UI service at {url} (pid {process.pid})")
    print(f"Logs: {paths.log}")
    return 0


def run_service_status(ctx: WorkspaceContext) -> int:
    paths = service_paths(ctx)
    metadata = _load_metadata(paths.metadata)
    if not metadata:
        print("CC Branch Web UI service is not running")
        return 3

    pid = int(metadata.get("pid", 0))
    if process_is_running(pid):
        print(f"CC Branch Web UI service is running at {metadata.get('url')} (pid {pid})")
        print(f"Logs: {metadata.get('log_path', paths.log)}")
        return 0

    print(f"CC Branch Web UI service is not running (stale pid {pid})")
    return 3


def run_service_stop(ctx: WorkspaceContext, args: Any, *, quiet: bool = False) -> int:
    paths = service_paths(ctx)
    metadata = _load_metadata(paths.metadata)
    if not metadata:
        if not quiet:
            print("CC Branch Web UI service is not running")
        return 3

    pid = int(metadata.get("pid", 0))
    if not process_is_running(pid):
        paths.metadata.unlink(missing_ok=True)
        if not quiet:
            print(f"CC Branch Web UI service was not running (removed stale pid {pid})")
        return 3

    terminate_process(pid)
    deadline = time.time() + float(getattr(args, "timeout", 5.0))
    while time.time() < deadline:
        if not process_is_running(pid):
            paths.metadata.unlink(missing_ok=True)
            if not quiet:
                print("Stopped CC Branch Web UI service")
            return 0
        time.sleep(0.05)

    print(f"Timed out waiting for CC Branch Web UI service to stop (pid {pid})")
    return 1


def run_service_logs(ctx: WorkspaceContext, args: Any) -> int:
    paths = service_paths(ctx)
    lines = int(getattr(args, "lines", 100))
    if not paths.log.exists():
        print(f"No service log found at {paths.log}")
        return 3
    content = paths.log.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in content[-lines:]:
        print(line)
    return 0


def _creation_flags() -> int:
    if os.name != "nt":
        return 0
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    return flags


def _load_metadata(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _write_metadata(path: Path, metadata: ServiceMetadata) -> None:
    path.write_text(json.dumps(asdict(metadata), indent=2, sort_keys=True) + "\n", encoding="utf-8")
