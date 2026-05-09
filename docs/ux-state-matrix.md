# UX State Matrix

CC Branch has several states that can look similar to users. This matrix defines
the user-facing meaning, primary action, and copy direction for each one.
Concrete debug and QA scenarios live in `docs/user-use-conditions.md`.

| State | User meaning | Primary action | UX rule |
| --- | --- | --- | --- |
| Project path missing | The selected folder is gone or inaccessible. | Pick another project or refresh. | Show path problem, not config advice. |
| Config missing | Project exists but has no `.cc-branch/config.yaml`. | Create from a starter template. | Keep setup first, not YAML-first. |
| Config invalid | Config exists but cannot be parsed or validated. | Open Config and fix errors. | Preserve content and show exact backend issues. |
| State missing | Runtime metadata has not been generated yet. | Plan/write state or start workspace. | Treat as recoverable local metadata, not config corruption. |
| tmux unavailable | Config may contain tmux slots, but this machine cannot run tmux. | Install tmux or switch slots to terminal runtime. | Disable tmux lifecycle actions before the user clicks them. |
| Tmux window missing | Configured tmux window is not currently running. | Start/update runtime. | Say "not running", not "config mismatch". |
| Tmux window changed | Running tmux window uses an older launch spec. | Start/update runtime. | Say "older launch command"; preserve current running state until user applies. |
| Tmux window untracked | A running window exists but lacks current metadata. | Start/update runtime. | Explain it was not launched from the current config. |
| Extra tmux window | A tmux window exists outside the current config. | Stop extra windows after confirmation. | Separate destructive cleanup from normal sync. |
| Terminal runtime | External shell/editor process, not managed by CC Branch. | Open manually through an opener. | Do not offer background start/stop semantics. |
| Opener unavailable | A configured terminal/editor cannot be found on this machine. | Choose another opener or install the tool. | Keep unavailable tools visible but disabled with a reason. |
| Save conflict | Config changed on disk after the UI loaded it. | Refresh before saving. | Prevent silent overwrite. |

Design target: users should always know whether they are fixing config,
starting missing runtime, updating running runtime, cleaning up extra runtime, or
working around a local machine capability.
