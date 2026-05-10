# Web UI Navigation Notes

> **Status**: current-state notes for the shipped Web UI surface.
>
> The authoritative reference for the shipped Web UI is [`docs/webui-spec.md`](webui-spec.md).

## Current navigation model

The current Web UI/backend surface centers on a small set of views and actions:

- Status
- Config
- Doctor
- Profile discovery / Init flow

These are backed directly by shipped APIs:

- `/api/status`
- `/api/config`
- `/api/doctor`
- `/api/profiles`
- `/api/init`

## What this means for documentation

When describing the Web UI today, assume the primary information architecture is:

1. observe current workspace state
2. inspect or edit config
3. inspect health / diagnostics
4. initialize missing projects from built-in profiles

## Avoid overclaiming

Do not document older mockups as if they are guaranteed shipped behavior unless they map to current backend capabilities.

Examples of ideas that may still be roadmap-only depending on frontend state:

- more advanced multi-pane navigation
- richer per-slot control surfaces
- project scanning sidebars
- live push updates
