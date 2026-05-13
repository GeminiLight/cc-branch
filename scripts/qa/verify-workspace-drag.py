#!/usr/bin/env python3
"""Browser-level QA for workspace canvas drag-and-drop.

Run against a local `cc-branch serve` instance:

    python scripts/qa/verify-workspace-drag.py http://127.0.0.1:5197 tmp/browser-qa/workspace-drag-after.png
    python scripts/qa/verify-workspace-drag.py http://127.0.0.1:5197 tmp/browser-qa/workspace-drag-after.png /tmp/project/.cc-branch/config.yaml

The fixture project in `tests/fixtures/browser-drag-project` contains a single
terminal-pane tab, a tab with multiple panes, and a legacy tmux tab. The check
drags the terminal pane and the tmux group into the multi-pane tab and verifies
the resulting DOM. When a config path is provided, the script also clicks Save
and verifies that the YAML persisted the same workspace shape.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - optional save verification dependency
    yaml = None

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


def save_config(page: Page) -> None:
    save = page.get_by_role("button", name="Save")
    save.wait_for(state="visible")
    save.click()
    page.wait_for_function(
        """
        () => Array.from(document.querySelectorAll('button'))
          .some((button) => button.textContent?.trim() === 'Save' && button.disabled)
        """
    )


def verify_saved_config(config_path: Path) -> None:
    if yaml is None:
        fail("PyYAML is required when a config path is provided")
    if not config_path.exists():
        fail(f"saved config does not exist: {config_path}")
    doc = yaml.safe_load(config_path.read_text()) or {}
    tabs = doc.get("tabs")
    if not isinstance(tabs, list) or len(tabs) != 1:
        fail(f"expected one persisted tab; got {tabs!r}")

    tab = tabs[0]
    if not isinstance(tab, dict) or tab.get("name") != "dev":
        fail(f"expected persisted tab named dev; got {tab!r}")

    panes = tab.get("panes")
    if not isinstance(panes, list):
        fail(f"expected dev panes list; got {panes!r}")
    pane_names = [pane.get("name") for pane in panes if isinstance(pane, dict)]
    if pane_names != ["shell", "review", "ui", "spec"]:
        fail(f"expected persisted pane order shell/review/ui/spec; got {pane_names!r}")
    shell = panes[0]
    if not isinstance(shell, dict) or shell.get("command") != "zsh":
        fail(f"expected shell command zsh to persist; got {shell!r}")

    review = panes[1]
    if not isinstance(review, dict) or review.get("layoutBackend") != "tmux":
        fail(f"expected review pane to remain a tmux group; got {review!r}")
    review_windows = review.get("windows")
    if not isinstance(review_windows, list):
        fail(f"expected review tmux group to persist nested windows; got {review_windows!r}")
    review_names = [pane.get("name") for pane in review_windows if isinstance(pane, dict)]
    if review_names != ["audit", "docs"]:
        fail(f"expected review tmux windows audit/docs; got {review_names!r}")


def main() -> int:
    if len(sys.argv) not in {3, 4}:
        print("usage: verify-workspace-drag.py <url> <screenshot> [config.yaml]", file=sys.stderr)
        return 2

    url = sys.argv[1]
    screenshot = Path(sys.argv[2])
    config_path = Path(sys.argv[3]) if len(sys.argv) == 4 else None
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
        if config_path is not None:
            save_config(page)
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
    if config_path is not None:
        verify_saved_config(config_path)

    print("PASS: browser drag moved terminal pane and tmux group into another tab")
    if config_path is not None:
        print("PASS: saved YAML persisted the moved terminal pane and tmux group")
    print("pane labels:", labels)
    print("tab labels:", tabs)
    print("screenshot:", screenshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
