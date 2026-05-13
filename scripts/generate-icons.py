#!/usr/bin/env python3
"""
Generate all icon assets from a single SVG source.

Usage:
    python scripts/generate-icons.py

Requirements:
    - rsvg-convert (from librsvg, install via `brew install librsvg` on macOS)
    - ImageMagick (for .ico generation, optional)
    - iconutil (for .icns generation, built-in on macOS)

Single source of truth:
    apps/web/src/assets/logo/logo.svg

Generated outputs:
    - Web UI assets (apps/web/src/assets/logo/)
    - Web UI public files (apps/web/public/)
    - Web UI backend static files (cc_branch/webui/static/)
    - Desktop app icons (apps/desktop/src-tauri/icons/)
"""

import subprocess
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SOURCE_SVG = PROJECT_ROOT / "apps/web/src/assets/logo/logo.svg"

OUTPUTS = {
    "web_assets": {
        "dir": PROJECT_ROOT / "apps/web/src/assets/logo",
        "files": [
            (32, "logo-32.png"),
            (180, "logo-180.png"),
            (512, "logo-512.png"),
        ],
    },
    "web_public": {
        "dir": PROJECT_ROOT / "apps/web/public",
        "files": [
            (None, "favicon.svg"),   # copy SVG as-is
            (32, "favicon.png"),
            (180, "apple-touch-icon.png"),
            (512, "icon-512.png"),
        ],
    },
    "webui_static": {
        "dir": PROJECT_ROOT / "cc_branch/webui/static",
        "files": [
            (None, "favicon.svg"),   # copy SVG as-is
            (32, "favicon.png"),
            (180, "apple-touch-icon.png"),
            (512, "icon-512.png"),
        ],
    },
    "desktop": {
        "dir": PROJECT_ROOT / "apps/desktop/src-tauri/icons",
        "files": [
            (32, "32x32.png"),
            (128, "128x128.png"),
            (256, "128x128@2x.png"),
            (512, "icon.png"),
            (30, "Square30x30Logo.png"),
            (44, "Square44x44Logo.png"),
            (71, "Square71x71Logo.png"),
            (89, "Square89x89Logo.png"),
            (107, "Square107x107Logo.png"),
            (142, "Square142x142Logo.png"),
            (150, "Square150x150Logo.png"),
            (284, "Square284x284Logo.png"),
            (310, "Square310x310Logo.png"),
            (50, "StoreLogo.png"),
        ],
    },
}


def check_deps():
    """Ensure required tools are available."""
    if not shutil.which("rsvg-convert"):
        print("ERROR: rsvg-convert not found. Install librsvg:")
        print("  macOS: brew install librsvg")
        print("  Linux: sudo apt-get install librsvg2-bin")
        sys.exit(1)

    if not SOURCE_SVG.exists():
        print(f"ERROR: Source SVG not found: {SOURCE_SVG}")
        sys.exit(1)


def generate_png(svg_path: Path, size: int, output_path: Path):
    """Generate a PNG from SVG at the specified size."""
    subprocess.run(
        ["rsvg-convert", "-w", str(size), "-h", str(size), str(svg_path), "-o", str(output_path)],
        check=True,
    )
    print(f"  Generated: {output_path}")


def copy_file(src: Path, dst: Path):
    """Copy a file."""
    shutil.copy2(src, dst)
    print(f"  Copied: {dst}")


def generate_ico(svg_path: Path, output_path: Path):
    """Generate Windows .ico from SVG (requires ImageMagick)."""
    if not shutil.which("convert"):
        print("  WARNING: ImageMagick not found, skipping icon.ico")
        return

    tmp_dir = Path("/tmp/cc-branch-ico")
    tmp_dir.mkdir(exist_ok=True)

    sizes = [16, 32, 48, 256]
    pngs = []
    for size in sizes:
        png_path = tmp_dir / f"logo-{size}.png"
        generate_png(svg_path, size, png_path)
        pngs.append(str(png_path))

    subprocess.run(
        ["convert"] + pngs + [str(output_path)],
        check=True,
    )
    print(f"  Generated: {output_path}")
    shutil.rmtree(tmp_dir)


def generate_icns(svg_path: Path, output_path: Path):
    """Generate macOS .icns from SVG (requires iconutil)."""
    if not shutil.which("iconutil"):
        print("  WARNING: iconutil not found, skipping icon.icns")
        return

    iconset_dir = Path("/tmp/cc-branch.iconset")
    iconset_dir.mkdir(exist_ok=True)

    sizes = [16, 32, 64, 128, 256, 512]
    for size in sizes:
        # 1x
        generate_png(svg_path, size, iconset_dir / f"icon_{size}x{size}.png")
        # 2x
        generate_png(svg_path, size * 2, iconset_dir / f"icon_{size}x{size}@2x.png")

    subprocess.run(
        ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(output_path)],
        check=True,
    )
    print(f"  Generated: {output_path}")
    shutil.rmtree(iconset_dir)


def main():
    check_deps()

    print(f"Source: {SOURCE_SVG}")
    print("=" * 50)

    for name, config in OUTPUTS.items():
        output_dir = config["dir"]
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n[{name}] -> {output_dir}")

        for size, filename in config["files"]:
            output_path = output_dir / filename

            if size is None:
                # Copy SVG as-is
                copy_file(SOURCE_SVG, output_path)
            else:
                generate_png(SOURCE_SVG, size, output_path)

    # Desktop-specific formats
    print("\n[desktop_extra]")
    generate_ico(SOURCE_SVG, OUTPUTS["desktop"]["dir"] / "icon.ico")
    generate_icns(SOURCE_SVG, OUTPUTS["desktop"]["dir"] / "icon.icns")

    print("\n" + "=" * 50)
    print("All icons generated successfully.")
    print("\nRemember to rebuild the Web UI if needed:")
    print("  python scripts/build-webui.py")


if __name__ == "__main__":
    main()
