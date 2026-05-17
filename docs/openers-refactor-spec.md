# Openers Package Refactor Spec

> **Status**: 🚧 In Progress. Implementation underway, not yet shipped.

## Decision

Refactor `cc_branch/openers.py` into a package named `cc_branch/openers/`.

The public import surface remains `cc_branch.openers`. Callers should still be
able to import:

- `OpenCommandSpec`
- `OpenerError`
- `OpenIntent`
- `OpenerInfo`
- `list_openers`
- `opener_label`
- `opener_supports`
- `open_command`
- `open_command_layout`
- `open_with`
- `open_workspace_file`

The directory name is `openers`, matching the existing domain language,
configuration key, API endpoint, and frontend type names.

## Goals

- Separate opener concerns by reason to change.
- Preserve existing runtime behavior and public API.
- Make platform-specific launch code easier to review.
- Keep the package dependency graph simple and mostly one-way.
- Give each major responsibility an explicit adapter object instead of hiding
  the implementation behind piles of `_private_function` helpers.

## Non-Goals

- No user-visible behavior changes.
- No rename to `OpenR`, `OpenRS`, or any other new domain term.
- No new opener plugin architecture in this change.
- No migration of workspace action policy out of the former
  `application/workspace_actions.py` module.

## Module Layout

```text
cc_branch/openers/
  __init__.py      Public facade and compatibility re-exports.
  types.py         Dataclasses, capability constants, and exceptions.
  commands.py      Intent validation, intent-to-command conversion, shell quoting.
  registry.py      `OpenerRegistry`: built-in and configured opener discovery.
  dispatcher.py    `OpenerDispatcher`: public open_* operations and opener routing.
  terminal.py      `TerminalLauncher`: system, macOS, Windows, and Linux terminals.
  editors.py       `EditorWorkspaceOpener`: editor folder opener with integrated-terminal automation where supported.
  warp.py          `WarpLauncher`: Warp launch configuration rendering and URIs.
  platform.py      Shared OS helpers: cache paths, app lookup, URI open, popen.
```

## Dependency Rules

- `types.py` must not import other opener modules.
- `commands.py` may depend on `types.py`.
- `platform.py` may depend on `types.py`.
- `registry.py` may depend on `types.py`, `platform.py`, and `models.OpenerSpec`.
- `terminal.py`, `editors.py`, and `warp.py` may depend on `types.py`,
  `commands.py`, and `platform.py`.
- `dispatcher.py` coordinates modules but should not contain platform-specific
  subprocess argument construction.
- `__init__.py` re-exports public API only, plus narrow legacy private helpers
  still used by existing internal tests/callers.
- Legacy `_open_*` functions may exist as compatibility wrappers, but the main
  implementation path should flow through the explicit adapter classes.

## Behavioral Invariants

- Unknown opener IDs still raise `OpenerError("Unknown opener: ...")`.
- Unavailable openers still include their `reason`.
- `auto-terminal` keeps the same platform resolution behavior.
- Custom opener argument rendering keeps `{cwd}`, `{command}`, and `{target}`.
- Warp still uses launch configurations for command execution and layouts.
- VS Code and Cursor open the project folder directly for normal workspace opens.
- Editor workspace cleanup only removes stale generated files for the same
  opener and project folder.
- Windows command quoting remains PowerShell-safe for paths and targets with
  apostrophes.

## Test Strategy

- Add an architecture test proving `cc_branch.openers` is a package facade and
  the expected internal modules are importable.
- Keep existing opener behavior tests, updating patch targets to the owning
  module instead of the old monolithic module.
- Run `python -m unittest tests.test_openers`.
- Run the full Python unittest suite after focused tests pass.
