# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.2] - 2026-06-14

### Added
- Added explicit `columns x rows` display layout controls in the Web UI config editor and carried those grid dimensions through Warp launch specs.
- Added detected worktree selection for agent panes, with branch and dirty-state indicators in the workspace editor and canvas.
- Added SSH project authentication controls for default SSH config, identity-file, and password/keyboard-interactive login modes.

### Changed
- The desktop sidebar title area now participates in native window dragging on macOS desktop builds.
- The SSH Add Project flow now treats saved and manual SSH targets as connection sources, removes premature agent selection, and emphasizes project name and remote directory setup.

## [1.4.1] - 2026-06-14

### Added
- Added project/all-project session discovery scopes for Codex, Claude, Gemini, Cursor, and Kimi session pickers.
- Added `cc-branch session restore --session-scope all` and matching Web API/client support for restoring a selected session from outside the current project.

### Changed
- Session pickers now default to sessions from the active project, with an explicit "All projects" switch for broader recovery.
- The Dashboard now merges live agent runtime details into the matching workspace pane instead of showing a separate agent-status panel above the layout.

## [1.4.0] - 2026-06-14

### Added
- Added file-level workspace snapshots with `cc-branch snapshot create --include-files`, restore preview file diffs, and `snapshot restore --state-only`.
- Added `cc-branch session restore --session-id` and matching Web API support for binding a specific agent-native session.
- Added remote agent selection to the desktop/Web SSH Add Project flow.
- Added automatic npm registry publishing on GitHub release events when `NPM_TOKEN` is configured.

### Changed
- Workspace snapshot file capture now prunes heavy runtime/build directories and enforces bounded file-size and total-size limits.

## [1.3.0] - 2026-06-14

### Added
- Added `cc-branch project list/add/add-remote`, including SSH project preflight with `--dry-run` and selectable remote agent command.
- Added snapshot restore preview, dry-run restore, show, export, and import commands plus matching Web API endpoints.
- Added stronger session restore controls: `--dry-run`, `--target`, `--agent`, `--force`, candidate reporting, and skipped-reason reporting.
- Added Web API support for remote project preflight without writing the project index.

### Changed
- Remote project metadata workspaces now record the selected agent command instead of always assuming `codex`.
- Snapshot and session restore documentation now distinguishes restored local runtime state from remote file sync or credential management.

## [1.1.5] - 2026-06-12

### Fixed
- Fixed project-scoped `cc-branch serve` so the current directory is always the active project, allowing the Workspace canvas to load and persist pane drag ordering even when another project was previously active.

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

[1.4.2]: https://github.com/GeminiLight/cc-branch/releases/tag/v1.4.2
[1.4.1]: https://github.com/GeminiLight/cc-branch/releases/tag/v1.4.1
[1.4.0]: https://github.com/GeminiLight/cc-branch/releases/tag/v1.4.0
[1.3.0]: https://github.com/GeminiLight/cc-branch/releases/tag/v1.3.0
[1.1.5]: https://github.com/GeminiLight/cc-branch/releases/tag/v1.1.5
[1.1.4]: https://github.com/GeminiLight/cc-branch/releases/tag/v1.1.4
[1.1.3]: https://github.com/GeminiLight/cc-branch/releases/tag/v1.1.3
[1.1.2]: https://github.com/GeminiLight/cc-branch/releases/tag/v1.1.2
[1.1.0]: https://github.com/GeminiLight/cc-branch/releases/tag/v1.1.0
[1.0.0]: https://github.com/GeminiLight/cc-branch/releases/tag/v1.0.0
