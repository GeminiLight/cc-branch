# CC Branch Examples

This directory contains example workspace configs for common terminal AI workflows.

## How to use an example

1. Copy an example into your project:

```bash
cp examples/scenario-solo-dev.yaml .cc-branch.yaml
```

2. Create or refresh local state without overwriting your copied config:

```bash
cc-branch state bootstrap
```

3. Launch the workspace:

```bash
cc-branch up
```

If you want a fresh profile-generated config instead of a copied example, use `cc-branch init`.

## Included examples

### `scenario-solo-dev.yaml`

Best for:

- one developer
- implementation + review split
- a dev-server window
- a scratch shell

### `scenario-multi-project.yaml`

Best for:

- monorepos or related projects
- separate frontend/backend/library slots
- different agents per project area

### `scenario-long-term.yaml`

Best for:

- persistent multi-week project context
- planning / implementation / testing separation
- multiple long-lived agent windows

### `agent-branch.yaml`

A clean starter-style config showing the canonical YAML shape.

## Tips

- run `cc-branch state bootstrap` before `up` when you need to generate local session metadata
- use `cc-branch status` and `cc-branch session list` to inspect what exists
- commit `.cc-branch.yaml`, not `.cc-branch.state.toml`
- use `cc-branch doctor` if commands, cwd paths, or session IDs look wrong
