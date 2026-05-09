# Release Readiness Review

Date: 2026-04-28

This review checks whether CC Branch is ready to publish to GitHub and to use as the source for package builds.

## Scope

- CLI command surface and first-run user flow.
- Web UI local-server security boundary.
- Python packaging metadata and bundled Web UI assets.
- CI, tests, linting, and build commands.
- Documentation consistency for install, quick start, license, and release workflow.
- Repository hygiene before `git add .`.

## Findings

### Blockers

None remaining.

### Fixed During Review

- Web UI CORS handling no longer reflects arbitrary external origins. Cross-origin mutating requests from untrusted websites now fail with HTTP 403, while same-origin and localhost development origins still work.
- Tokenless local Web UI servers do not trust matching `Host` and `Origin` alone, which reduces DNS rebinding risk.
- Added regression tests for untrusted Origin handling and localhost development Origin support.
- Removed public pre-release stage wording from package metadata and the publishing guide examples.
- Ran Ruff import cleanup and removed stale import hygiene issues.
- Rebuilt the Web UI bundle and verified Python packaging includes static Web UI assets in both sdist and wheel.
- Fixed VS Code/Cursor workspace opening so tmux slots are not expanded into one auto-run editor task per tmux window.
- Added stale generated `.code-workspace` cleanup for editor openers and regression coverage for mixed tmux + terminal workspaces.
- Added `cc_branch.__version__` so the release checklist and package metadata have an explicit source version to update.
- Updated GitHub workflows to use reproducible `npm ci` installs and pinned Node.js 20.19.0 for current frontend dependency engine requirements.

### Non-Blocking Notes

- Built Web UI assets under `cc_branch/webui/static/` are ignored by Git and regenerated during packaging. This is expected because `setup.py` and CI run `scripts/build-webui.py` before package creation.
- Local build outputs and caches such as `build/`, `dist/`, `*.egg-info`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, and `node_modules/` are ignored. They should not be committed.
- The repository was reinitialized, so `git status` shows all source files as untracked until the first commit.

## Validation

The following checks passed locally:

```bash
python3.11 -m ruff check cc_branch tests
python3.11 -m unittest discover tests
python3.11 -m compileall cc_branch
npm run lint
npm run test
apps/web: npm run build
python3.11 scripts/build-webui.py
python3.11 -m build --no-isolation
python3.11 -m twine check dist/*
```

Results:

- Python 3.11 unit tests: 232 passed.
- Frontend Web UI tests: 51 passed.
- Ruff: all checks passed.
- Frontend build: passed.
- Package build: sdist and wheel built successfully. The local sandbox used `--no-isolation` because outbound package downloads are blocked; CI should continue using isolated builds.
- Twine check: sdist and wheel passed.

## GitHub Ready Checklist

- README and Chinese README describe the current `serve`, `init`, and `start` flows.
- The legacy launch alias is not exposed as a compatibility command.
- License is in a dedicated section and `LICENSE` is present.
- CI covers Python 3.10, 3.11, 3.12 on Linux/macOS, Web UI lint/test/build, Python package build, and desktop sidecar script validation.
- PyPI metadata includes Python 3.10, 3.11, and 3.12 classifiers and no pre-release stage classifier.
- Web UI mutating endpoints are protected against untrusted browser origins.

## Recommendation

The repository is ready for the first GitHub commit after ignored local artifacts are left out of the commit. Before publishing a tagged release, run CI once on GitHub and confirm the Homebrew tap workflow or formula update process matches the release tag.
