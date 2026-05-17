# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- First-run bootstrap experience with environment checks
- Profile templates (solo-dev, ai-pair, minimal)
- Automatic session ID bootstrapping
- `--minimal` flag for lightweight initialization
- `--profile` flag for template selection
- Smart config generation based on available agents
- Graceful degradation when agents are missing
- Beautiful rich-formatted output with clear next steps

### Changed
- `init` command now performs environment checks by default

### Fixed
- Improved error messages for invalid profiles
- Better handling of missing agent CLIs

## [0.1.0] - 2024-04-23

### Added
- Initial release
- YAML-first workspace configuration
- Tmux session orchestration
- Multi-agent support (Claude Code, Codex, Gemini CLI, etc.)
- Session state persistence
- Dashboard view
- Doctor command for health checks
- Plan preview before execution

[Unreleased]: https://github.com/GeminiLight/cc-branch/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/GeminiLight/cc-branch/releases/tag/v0.1.0
