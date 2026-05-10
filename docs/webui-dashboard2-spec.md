# Multi-Project Dashboard Notes

> **Status**: current-state implementation notes plus near-term roadmap boundary.
>
> **This is NOT shipped behavior.** Do not describe anything in this document as
> currently available to users unless it maps to an existing shipped API documented
> in [`docs/webui-spec.md`](webui-spec.md).
>
> The "What is already supported" section lists backend primitives only. The
> "What is not yet a committed shipped surface" section lists everything else.

## What is already supported

The backend already supports loading another project by passing `project_path` to the existing APIs:

- `GET /api/status?project_path=/abs/path`
- `GET /api/config?project_path=/abs/path`
- `GET /api/doctor?project_path=/abs/path`
- `POST /api/init?project_path=/abs/path`
- `POST /api/config?project_path=/abs/path`
- `POST /api/action?project_path=/abs/path`

This gives desktop wrappers and richer frontends a stable primitive for multi-project dashboards.

For workspace controls, `action: "open"` is the visible path: the local backend opens a system terminal and runs `cc-branch dashboard` or `cc-branch attach <target>`. `action: "launch"` is the background path and should not be presented as if it opens a window.

## What is not yet a committed shipped surface

The following should still be treated as roadmap ideas unless the frontend explicitly implements them:

- project auto-scan endpoint
- persistent project registry in the backend
- advanced dashboard cards for many projects at once
- background watchers or push updates

## Recommended framing

Document the current feature as:

- a project-path-aware backend
- compatible with future multi-project dashboards
- already usable by wrappers or custom frontends

But avoid presenting a full project-scanning dashboard as fully shipped unless you verify the frontend implementation itself.
