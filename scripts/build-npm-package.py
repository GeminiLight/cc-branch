"""Build the npm wrapper package for cc-branch."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "packaging" / "npm"
DIST = ROOT / "dist"
STAGE = DIST / "npm-package"


def project_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def ensure_wheel(version: str) -> Path:
    wheel = DIST / f"cc_branch-{version}-py3-none-any.whl"
    if not wheel.exists():
        raise FileNotFoundError(
            f"Missing {wheel}. Run `python -m build` before building the npm package."
        )
    return wheel


def copy_tree(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def main() -> int:
    version = project_version()
    wheel = ensure_wheel(version)

    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    for name in ("bin", "scripts"):
        copy_tree(TEMPLATE / name, STAGE / name)
    shutil.copy2(TEMPLATE / "README.md", STAGE / "README.md")
    shutil.copy2(ROOT / "LICENSE", STAGE / "LICENSE")

    vendor = STAGE / "vendor"
    vendor.mkdir()
    shutil.copy2(wheel, vendor / wheel.name)

    package = json.loads((TEMPLATE / "package.json").read_text(encoding="utf-8"))
    package["version"] = version
    (STAGE / "package.json").write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")

    subprocess.run(["npm", "pack", str(STAGE), "--pack-destination", str(DIST)], check=True)
    print(DIST / f"cc-branch-{version}.tgz")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
