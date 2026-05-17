# Global Project Index Spec

> **Status**: 🚧 In Progress. Implementation underway, not yet shipped.
>
> Do not present content from this document as currently available to users.

## 1. Goal

Move Web UI project memory from browser-local storage to a backend-managed global index so the same project list and selection state are shared across:

- browser sessions
- desktop shell surfaces
- future frontends that call the same API

## 2. Scope

This spec covers only global project index state:

- project list shown in sidebar
- active project selection
- selected config path per project

Not in scope:

- theme/language migration from frontend local storage
- opener preference migration

## 3. Storage Layout

Global app data lives in user home:

```text
~/.cc-branch/
  agents.yaml               # existing global agent overrides
  app/
    projects.yaml           # new global project index
```

`projects.yaml` schema (v1):

```yaml
version: 1
active_project_id: "current"
projects:
  - id: "current"
    name: "cli-workspace"
    path: "/Users/alice/code/cli-workspace"
    selected_config_path: "/Users/alice/code/cli-workspace/.cc-branch/config.yaml"
```

## 4. API Contract

Authenticated endpoints:

- `GET /api/projects`
  - returns full index payload
- `POST /api/projects/add`
  - body: `{ path: string, name?: string }`
  - upserts by normalized path
- `POST /api/projects/remove`
  - body: `{ id: string }`
- `POST /api/projects/activate`
  - body: `{ id: string }`
- `POST /api/projects/current`
  - body: optional `{ config_path?: string }`
  - inject/update id `current` based on resolved project directory
- `POST /api/projects/config`
  - body: `{ project_path: string, config_path: string }`
  - updates selected config for that project path

All mutation endpoints return the same index payload as `GET`.

## 5. Backend Design

Add `cc_branch/app_state/` package:

- `paths.py`: resolve `~/.cc-branch/app/projects.yaml`
- `project_index.py`: typed load/save/mutate store

Rules:

- atomic writes (`.tmp` + replace) and `.bak` backup
- schema validation with safe defaults
- path normalization for dedupe (`expanduser().resolve(strict=False)`)
- stable behavior when file is missing or malformed: recover to empty index

## 6. Frontend Design

Project store becomes runtime state (non-persisted). Persistence source is API.

Startup flow:

1. load index from `GET /api/projects`
2. call `POST /api/projects/current` to inject current workspace
3. hydrate store from response

All project actions call backend first, then replace store snapshot from API response.

## 7. UX Expectations

- Project list is stable across browser refreshes and devices on the same machine.
- Active project and selected config are remembered globally.
- No silent divergence between frontend memory and backend context.

## 8. Migration Policy

No compatibility migration from legacy browser key `cc-branch-projects`. This is pre-1.0 cleanup.

## 9. Tests

Required:

- unit tests for project index store load/save/mutate semantics
- Web UI endpoint tests for `/api/projects*`
- frontend API client tests for new endpoints
- frontend store tests for snapshot-based behavior
