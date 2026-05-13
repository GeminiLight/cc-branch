#!/usr/bin/env python3
"""Browser-level QA for workspace canvas drag-and-drop.

Run against a local `cc-branch serve` instance:

    python scripts/qa/verify-workspace-drag.py http://127.0.0.1:5197 tmp/browser-qa/workspace-drag-after.png

The fixture project in `tests/fixtures/browser-drag-project` contains an
implicit terminal tab, a tab with explicit panes, and a legacy tmux tab. The
check drags the implicit terminal pane and the tmux group into the explicit tab
and verifies the resulting DOM.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    from playwright.sync_api import Page, sync_playwright
except ImportError as exc:  # pragma: no cover - optional local QA dependency
    raise SystemExit(
        "Playwright is required for this QA script. Install it with `python -m pip install playwright` "
        "and `python -m playwright install chromium`."
    ) from exc


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def pane_labels(page: Page) -> list[str]:
    labels = page.locator("[role='button'][aria-label^='Edit pane ']").evaluate_all(
        "(nodes) => nodes.map((node) => node.getAttribute('aria-label'))"
    )
    return [label for label in labels if isinstance(label, str)]


def tab_labels(page: Page) -> list[str]:
    labels = page.locator("button[aria-label^='Edit tab ']").evaluate_all(
        "(nodes) => nodes.map((node) => node.getAttribute('aria-label'))"
    )
    return [label for label in labels if isinstance(label, str)]


def drag_pane(page: Page, source_name: str, target_name: str) -> None:
    source = page.get_by_role("button", name=f"Edit pane {source_name}")
    target = page.get_by_role("button", name=f"Edit pane {target_name}")
    source.drag_to(target, target_position={"x": 18, "y": 18}, force=True)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: verify-workspace-drag.py <url> <screenshot>", file=sys.stderr)
        return 2

    url = sys.argv[1]
    screenshot = Path(sys.argv[2])
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 980})
        page.on(
            "console",
            lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
        )
        page.add_init_script(
            """
            localStorage.setItem('cc-branch-lang', 'en');
            localStorage.setItem('cc-branch-theme', 'light');
            """
        )

        page.goto(url, wait_until="networkidle")
        page.get_by_role("tab", name=re.compile(r"^Workspace$")).click()
        page.get_by_role("button", name="Edit pane shell").wait_for(state="visible")

        drag_pane(page, "shell", "ui")

        page.wait_for_function(
            """
            () => !document.querySelector("button[aria-label='Edit tab shell']")
              && Array.from(document.querySelectorAll("[role='button'][aria-label^='Edit pane ']"))
                .map((node) => node.getAttribute('aria-label'))
                .includes('Edit pane shell')
            """
        )

        drag_pane(page, "review", "ui")

        page.wait_for_function(
            """
            () => !document.querySelector("button[aria-label='Edit tab review']")
              && Array.from(document.querySelectorAll("[role='button'][aria-label^='Edit pane ']"))
                .map((node) => node.getAttribute('aria-label'))
                .includes('Edit pane review')
            """
        )

        labels = pane_labels(page)
        tabs = tab_labels(page)
        page.screenshot(path=str(screenshot), full_page=True)
        browser.close()

    expected_panes = {"Edit pane shell", "Edit pane ui", "Edit pane spec", "Edit pane review"}
    missing = expected_panes.difference(labels)
    if missing:
        fail(f"missing expected panes {sorted(missing)}; got {labels}")
    if tabs != ["Edit tab dev"]:
        fail(f"expected all moved panes to land in dev tab; got tabs {tabs}")
    if console_errors:
        fail("console errors: " + " | ".join(console_errors[:5]))

    print("PASS: browser drag moved implicit terminal pane and tmux group into another tab")
    print("pane labels:", labels)
    print("tab labels:", tabs)
    print("screenshot:", screenshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
