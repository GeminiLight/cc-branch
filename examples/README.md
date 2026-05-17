# CC Branch Examples

This directory contains example workspace configs for common terminal AI workflows.

## How to use an example

1. Copy an example into your project:

```bash
cp examples/scenario-solo-dev.yaml .cc-branch/config.yaml
```

2. Preview or launch the workspace:

```bash
cc-branch plan --write-state
cc-branch start
```

If you want a fresh profile-generated config instead of a copied example, use `cc-branch init`.

## Included examples

### `scenario-solo-dev.yaml`

Best for:

- one developer
- implementation + review split
- a dev-server pane
- a scratch shell

### `scenario-multi-project.yaml`

Best for:

- monorepos or related projects
- separate frontend/backend/library tabs
- different agents per project area

### `scenario-long-term.yaml`

Best for:

- persistent multi-week project context
- planning / implementation / testing separation
- multiple long-lived agent panes

### `agent-branch.yaml`

A clean starter-style config showing the canonical YAML shape.

## Tips

- run `cc-branch plan --write-state` when you want to generate local session metadata before launch
- use `cc-branch status` and `cc-branch session list` to inspect what exists
- commit `.cc-branch/config.yaml`, not `.cc-branch/state.yaml`
- use `cc-branch doctor` if commands, cwd paths, or session IDs look wrong
