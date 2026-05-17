# Agent Session Discovery Audit

Date: 2026-05-13
Project under test: `/Users/geminilight/code/cli-workspace`

Update: Codex under-discovery was fixed after this audit. The provider now uses transcript metadata as the authoritative source and uses `session_index.jsonl` only for label/timestamp enrichment.

## Scope

This audit checks whether the GUI session picker is showing reusable agent sessions that actually belong to the current project directory.

The GUI path is:

1. A pane selects an agent and switches session intent to `resume`.
2. `SlotsSection` calls `useAgentSessions(scope, enabled, agentKey)`.
3. The hook calls `/api/agent-sessions?project_path=...&config_path=...&agent=...`.
4. The server resolves the selected config path, then calls `agent_session_options(config_path, agent=agent)`.

Important test detail: `agent_session_options()` expects a config file path, not a project directory. Passing `/Users/geminilight/code/cli-workspace` directly makes `project_dir_for_config()` resolve the project as `/Users/geminilight/code`, which returns empty results. The GUI/API path is correct because it resolves `.cc-branch/config.yaml` first.

## API Results

I verified the real API with:

```bash
./bin/cc-branch serve --host 127.0.0.1 --port 8766
curl "http://127.0.0.1:8766/api/agent-sessions?project_path=/Users/geminilight/code/cli-workspace&agent=<agent>"
```

Results:

| Agent | GUI/API count | Returned project path | Verdict |
| --- | ---: | --- | --- |
| Codex | 34 | `/Users/geminilight/code/cli-workspace` | Correctly scoped after fix |
| Claude | 15 | `/Users/geminilight/code/cli-workspace` | Correctly scoped |
| Gemini / Antigravity | 0 | n/a | No project-scoped metadata found |
| Cursor | 4 | `/Users/geminilight/code/cli-workspace` | Correctly scoped |
| Kimi | 4 | `/Users/geminilight/code/cli-workspace` | Correctly scoped |

## Raw Store Verification

### Codex

Original implementation:

- reads `~/.codex/session_index.jsonl` for display rows
- scans `~/.codex/sessions/**/*.jsonl` only to map session id to `session_meta.payload.cwd`
- filters by exact normalized cwd

Raw evidence:

- Raw Codex transcripts with `session_meta.payload.cwd == /Users/geminilight/code/cli-workspace`: **34**
- Returned by GUI/API before fix: **9**
- Returned after fix: **34**
- Current-project Codex sessions missing after fix: **0**

Conclusion: Codex filtering was not mixing in unrelated projects, but it was heavily under-reporting. The bug was source selection: `session_index.jsonl` is not a complete index of current Codex transcripts. The provider now scans transcript metadata as the authoritative source, then uses `session_index.jsonl` only to enrich labels and timestamps when available.

### Claude

Current implementation:

- checks `~/.claude/projects/-Users-geminilight-code-cli-workspace`
- reads both `sessions-index.json` and `*.jsonl`
- uses the Claude project-folder slug as the primary project boundary

Raw evidence:

- Transcript files in project slug folder: **15**
- Returned by GUI/API: **15**
- Raw project-folder sessions missing from GUI/API: **0**

Some recent transcript files do not contain a `cwd` field inside the JSONL, but they live under Claude's per-project folder, so the project boundary is still credible. This is acceptable for Claude because Claude Code itself stores sessions under a path-derived project slug.

Conclusion: Claude is correctly scoped for this project.

### Gemini / Antigravity

Current implementation:

- scans `~/.gemini/antigravity/brain/*/*.metadata.json`
- only returns sessions when metadata contains a project path field such as `projectPath`, `workspacePath`, `cwd`, or nested workspace path

Raw evidence:

- Antigravity metadata files found: **60**
- Metadata files with any discoverable project path: **0**
- Metadata files provably belonging to current project: **0**
- Returned by GUI/API: **0**

Conclusion: Returning zero is conservative and correct with the current evidence. It may be incomplete if Antigravity stores project identity somewhere else, but the current provider is not falsely showing unrelated sessions.

### Cursor

Current implementation:

- reads Cursor global state DB: `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`
- reads key `composer.composerHeaders`
- filters non-draft agent composers by `workspaceIdentifier.uri`

Raw evidence:

- Non-draft Cursor composers: **218**
- Agent-mode Cursor composers: **153**
- Agent composers with workspace path equal to current project: **4**
- Returned by GUI/API: **4**
- Current-project Cursor sessions missing from GUI/API: **0**

Conclusion: Cursor filtering is correctly scoped and complete for the data currently available in `composer.composerHeaders`.

### Kimi

Current implementation:

- hashes the normalized project path with MD5
- reads `~/.kimi/sessions/<md5(project_path)>/*`

Raw evidence:

- Bucket used: `~/.kimi/sessions/8133738426bec7561197a583270bf8fe`
- Session directories in that bucket: **4**
- Returned by GUI/API: **4**
- Current-project Kimi sessions missing from GUI/API: **0**

Conclusion: Kimi is correctly scoped if Kimi's bucket contract is stable. The provider does not independently verify cwd from each session, but the bucket path is project-derived and matches the current project hash.

## Findings

1. **Codex had a real completeness bug.**
   The GUI previously returned 9 Codex sessions, but raw transcript metadata proved there were 34 sessions for this repo. This has been fixed; the current provider returns 34.

2. **No evidence of cross-project leakage in the returned rows.**
   For Claude, Cursor, and Kimi, returned rows all map to `/Users/geminilight/code/cli-workspace`. For Gemini, the provider returns nothing because it cannot prove project ownership.

3. **The provider API is easy to misuse internally.**
   `agent_session_options(config_path, ...)` is named clearly enough in code, but tests or future callers may accidentally pass a project directory. That silently scopes to the parent directory. A safer API would accept an explicit `project_dir` or detect directory input.

4. **Gemini support is metadata-limited, not functionally complete.**
   The current Antigravity brain metadata on this machine does not expose project paths. The provider is conservative, but users may still expect Gemini sessions to appear.

## Recommended Fixes

### P0: Fix Codex completeness

Status: completed.

`~/.codex/sessions/**/*.jsonl` is now the authoritative Codex source:

- parse each transcript's first `session_meta`
- require `payload.cwd` to match the current project
- use `payload.id` as session id
- use transcript mtime or latest record timestamp as `updated_at`
- enrich label from `session_index.jsonl` when the id exists there

Verified result for this project: Codex now shows **34** project-scoped sessions, not 9.

### P1: Harden the API boundary

Add a project-dir-safe wrapper or rename the internal function:

- `agent_session_options_for_project(project_dir, agent=...)`
- `agent_session_options_for_config(config_path, agent=...)`

This removes ambiguity between config path and project path.

### P1: Add provider-level tests

Add fixtures for:

- Codex transcript exists but is absent from `session_index.jsonl`
- Codex transcript cwd belongs to another project and must be excluded
- Claude project slug folder contains transcript without `cwd`
- Cursor composer without `workspaceIdentifier` is excluded
- Kimi bucket hash matches current project
- Gemini metadata without project path is excluded

### P2: Improve GUI trust signals

In the session picker, show a small source hint or tooltip:

- `Codex transcript`
- `Claude project store`
- `Cursor workspace`
- `Kimi project bucket`

This helps users understand why some agents show sessions and others do not.

## Final Assessment

The user's suspicion was valid, but the main problem was not "wrong directory sessions are being mixed in." The main problem was **Codex under-discovery**. Current GUI results for Claude, Cursor, and Kimi are scoped correctly for this repo. Gemini returns zero because the local metadata does not prove workspace ownership. Codex now scans transcript metadata directly, so the picker reflects the actual sessions that worked in this directory.
