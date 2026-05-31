# SSH Remote Workspaces

> Status: shipped in the planner/config model for command execution through local `ssh`.

CC Branch can run individual tabs, panes, or tmux windows on a remote machine through SSH. This is for workflows where the project control surface stays on the user's local computer, but the actual command should execute on a server, GPU box, or dev VM.

## Model

Use the `remote` field on a tab, pane, or nested tmux window.
In the desktop/web editor, the Run location control can stay local, inherit a
parent target, or switch to SSH. SSH targets from `~/.ssh/config` are shown as a
picker so users can choose an existing alias without retyping host details.

```yaml
version: 2
project: demo
root: .

tabs:
  - name: gpu
    layoutBackend: tmux
    remote:
      host: gpu-dev
      user: ubuntu
      port: 2222
      cwd: /srv/demo
      args:
        - -A
      options:
        ServerAliveInterval: 30
    panes:
      - name: trainer
        command: uv run python train.py
      - name: agent
        agent: codex
```

The planner resolves each remote pane into an SSH command:

```bash
ssh -p 2222 -o ServerAliveInterval=30 -A ubuntu@gpu-dev 'cd /srv/demo && uv run python train.py'
```

## Inheritance

`remote` inherits downward:

- tab `remote` applies to all panes in that tab
- pane `remote` overrides tab fields for that pane
- nested tmux-window `remote` overrides pane fields for that window

Overrides merge field by field. This lets a tab define the host while a pane changes only `cwd`.

```yaml
tabs:
  - name: services
    remote:
      host: devbox
      cwd: /srv/app
    panes:
      - name: api
        command: pnpm api
      - name: logs
        remote:
          cwd: /var/log/app
        command: tail -f app.log
```

Set `remote: false` on a pane or nested tmux window when a parent tab is remote
but that one command should still run locally:

```yaml
tabs:
  - name: mixed
    remote: devbox
    panes:
      - name: server
        command: pnpm dev
      - name: editor
        remote: false
        command: code .
```

## Fields

| Field | Type | Meaning |
| --- | --- | --- |
| `host` | string | SSH host or alias. Required where no parent `remote` provides a host. |
| `user` | string | Optional SSH username. |
| `port` | integer | Optional SSH port. |
| `cwd` | string | Optional remote working directory. |
| `args` | list of strings | Extra SSH arguments, one argv item per list entry, such as `-A` or `["-J", "bastion"]`. |
| `options` | mapping | SSH `-o key=value` options. |

For simple cases, `remote` can be a string:

```yaml
remote: devbox
```

This is equivalent to:

```yaml
remote:
  host: devbox
```

When a pane or nested tmux window only needs to change one inherited field, the
mapping can omit `host`:

```yaml
remote:
  cwd: /var/log/app
```

## Boundaries

- CC Branch does not store passwords, private keys, or passphrases.
- Authentication is delegated to the user's SSH config, agent, and local `ssh` command.
- Doctor checks the local `ssh` executable for remote panes. It does not require the remote agent CLI to exist locally.
- Local `cwd` still controls where the local terminal/editor opens. `remote.cwd` controls where the command runs after SSH connects.
- Remote filesystem sync is not implemented. Use Git, rsync, NFS, or an existing remote workspace mount when code needs to be present on the server.
