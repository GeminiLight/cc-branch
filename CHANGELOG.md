# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.4] - 2026-06-11

### Fixed
- Fixed Workspace pane grip dragging in the GUI so the drag handle is no longer covered by invisible pane action buttons, pointer dragging reorders panes, and saved YAML preserves the new order.

## [1.1.3] - 2026-06-11

### Fixed
- Fixed desktop release notes so CLI users are directed to the published PyPI install path while desktop users keep the bundled backend.

## [1.1.2] - 2026-06-11

### Added
- Added agent session hook capture so coding agents can report resumed session IDs back to CC Branch state.

### Fixed
- Fixed Workspace pane drag ordering so panes dropped before or after a target land at the intended visual position and persist in YAML.
- Fixed desktop release installer canaries so downloaded Windows installers use the same extended backend startup timeout as the packaged Windows smoke test.

## [1.1.0] - 2026-06-02

### Added
- Added a built-in `research` starter profile for idea, paper, code, and experiment workflows.
- Added LINUX DO community acknowledgements to the English and Chinese README files.

### Changed
- Changed the default `development` starter profile to use direct terminal panes instead of tmux-backed tabs.
- Replaced the old `design` starter profile with the `research` profile across the CLI, Web UI, setup flow, and documentation.

## [1.0.0] - 2026-06-01

### Added
- First public baseline for CC Branch.
- CLI, Web UI, and desktop shell for restoring multi-agent terminal workspaces.
- App-scoped Web UI service commands: `cc-branch service start`, `status`, `stop`, `restart`, and `logs`.
- Project-level foreground Web UI command: `cc-branch serve`.
- Config editor and dashboard support for enabling or disabling individual windows.
- Tmux and direct-layout workspace execution, SSH targets, opener integrations, diagnostics, and local project index.
- Desktop release packaging with bundled backend sidecar and GitHub release verification.

[1.1.4]: https://github.com/GeminiLight/cc-branch/releases/tag/v1.1.4
[1.1.3]: https://github.com/GeminiLight/cc-branch/releases/tag/v1.1.3
[1.1.2]: https://github.com/GeminiLight/cc-branch/releases/tag/v1.1.2
[1.1.0]: https://github.com/GeminiLight/cc-branch/releases/tag/v1.1.0
[1.0.0]: https://github.com/GeminiLight/cc-branch/releases/tag/v1.0.0
