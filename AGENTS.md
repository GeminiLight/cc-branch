# CC Branch

Multi-agent workspace orchestrator for terminal workflows.

## What It Does

Turns `.cc-branch.yaml` config into running tmux workspaces with persistent agent sessions.

## Cross-Platform Support

- **Platforms**: Mac, Windows, Linux
- **Architectures**: x86, ARM
- **Python**: 3.11, 3.12
- **Shells**: Tmux, Bash, PowerShell, Zsh
- **AI Tools**: Claude Code, Codex, Gemini CLI, Cursor CLI, and more

## Core Concepts

- **Slots**: Top-level workspaces (map to tmux sessions)
- **Windows**: Execution units within slots (can bind agents or run commands)
- **Agents**: Reusable definitions for AI CLI tools (Claude Code, Codex, etc.)
- **State**: `.cc-branch.state.toml` stores runtime metadata (session IDs, labels)

## Project Structure

```
cc_branch/
├── cli.py           # CLI entry point
├── bootstrap.py     # Session ID generation
├── doctor.py        # Health checks and auto-fix
├── profiles.py      # Config loading and validation
├── runtime.py       # Tmux workspace execution
└── application/     # DDD refactoring (in progress)
```

## Key Files

- `.cc-branch.yaml` - Workspace config (commit to git)
- `.cc-branch.state.toml` - Local runtime state (don't commit)
- `examples/` - Usage scenarios
- `docs/` - Full documentation

## Development

```bash
# Run tests
python -m unittest discover tests

# Test CLI
./bin/cc-branch --help
cc-branch plan
```

## Current Status

- ✅ Core functionality working
- 🚧 DDD refactoring in progress (application/ layer)
- 📝 Early stage, APIs may evolve before 1.0

## When Working on This Project

1. Read `docs/features.md` for complete feature list
2. Check `docs/architecture.md` for implementation details
3. Run `cc-branch doctor` to verify environment
4. Test changes with example configs in `examples/`
