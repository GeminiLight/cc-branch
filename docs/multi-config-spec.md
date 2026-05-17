# Multi-Config Workspace Spec

> **Status**: 🚧 In Progress. Implementation underway, not yet shipped.
>
> Do not present content from this document as currently available to users.

CC Branch supports one default workspace config and any number of named
alternate configs inside the same project. This lets one repository expose
different work modes such as `dev`, `review`, `docs`, or `release` without
copying the project directory.

## File Layout

Default workflow:

```text
.cc-branch/config.yaml
.cc-branch/state.yaml
```

Named alternate workflow:

```text
.cc-branch/configs/review.yaml
.cc-branch/states/review.yaml
```

Rules:

- `.cc-branch/config.yaml` is the default config.
- `.cc-branch/configs/<name>.yaml` is the preferred path for alternates.
- `.cc-branch/states/<name>.yaml` stores runtime metadata for that alternate.
- `.cc-branch/state.yaml` remains the state path for the default config.
- State files are local runtime metadata and should not be committed.

## Selection Rules

CLI:

- No config argument selects `.cc-branch/config.yaml`.
- `--config /absolute/path/to/file.yaml` selects that exact file.
- `--config .cc-branch/configs/review.yaml` selects the relative path.
- `--config review` selects `.cc-branch/configs/review.yaml`.

Web UI:

- Requests may include `project_path` and `config_path`.
- `config_path` can be an absolute candidate path, a project-relative path, or
  a short config name.
- Web requests are restricted to config files inside the selected project's
  `.cc-branch` directory.
- The frontend lists discovered configs and sends the selected config with all
  status, config, doctor, opener, agent, init, save, and action requests.

## Config Discovery

The Web UI discovers candidates from:

- `.cc-branch/config.yaml`
- `.cc-branch/configs/*.yaml`
- `.cc-branch/configs/*.yml`
- `.cc-branch/*.yaml` except reserved local files such as `state.yaml` and
  `agents.yaml`
- `.cc-branch/*.yml` with the same exclusions

The default config is always listed, even if it does not exist yet, so a fresh
project can still be initialized.

## Invariants

- Different configs must not share runtime state by accident.
- Project path and config path are separate concepts.
- Tmux session/window state belongs to the selected config.
- The Web UI must not allow `config_path` to read arbitrary files outside the
  selected project metadata directory.
- Existing default-config behavior remains unchanged.
