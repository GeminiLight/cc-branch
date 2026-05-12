# Session Discovery And Binding Spec

Status: product and architecture spec. Discovery picker providers are partially
implemented for Codex, Claude Code, Cursor, Kimi, and Gemini/Antigravity.

CC Branch should let users start agent workspaces without understanding session
IDs, while still giving advanced users a clean way to resume, pick, or bind
existing Codex, Claude Code, Cursor, Kimi, and Gemini-family sessions when the
local tool exposes stable metadata.

The core product rule is:

> Users should not need to understand sessions before they can start working.
> Sessions become visible only when they help users recover prior work or fix a
> specific ambiguity.

## Goals

- Start a fresh workspace with no prior sessions and no extra user decisions.
- Automatically bind newly created agent sessions when the agent supports a
  reliable create or post-launch discovery path.
- Discover existing local sessions for the current project and let users bind
  them explicitly.
- Keep session bindings in local state, never in shared config.
- Support both Web UI and CLI workflows with the same application use cases.
- Avoid reading or exposing conversation content by default.
- Make uncertainty explicit: recommend, do not silently bind, when confidence is
  not high.

## Non-Goals

- Do not sync sessions across machines.
- Do not upload or index conversation content.
- Do not make `config.yaml` depend on user-specific session IDs.
- Do not guarantee that every agent CLI can create a deterministic session ID.
- Do not replace the agent CLI's native picker; CC Branch should complement it.

## Terms

| Term | Meaning |
| --- | --- |
| Agent session | A resumable conversation/session owned by a tool such as Codex or Claude Code. |
| Runtime window | A tmux window or external terminal process launched by CC Branch. |
| Binding | The association between a CC Branch target such as `dev:planner` and an agent session ID. |
| Discovery | Local metadata scan that finds agent sessions related to the selected project. |
| Confidence | How certain CC Branch is that a discovered session belongs to the current project and target. |
| Session policy | A launch-time choice: auto, new, latest, pick, manual, or unbound. |

## State Ownership

Session bindings are machine-local state:

```text
.cc-branch/state.yaml
.cc-branch/states/<config>.yaml
```

They must not be written to:

```text
.cc-branch/config.yaml
.cc-branch/configs/<config>.yaml
```

Reason:

- `config.yaml` describes desired workspace structure and is shareable.
- `state.yaml` describes this user's local recovery metadata.
- The same team config can map to different session IDs on different machines.

## Current Agent Capabilities

Provider discovery uses the most stable local metadata available and fails
closed: missing directories, unreadable files, or changed formats produce an
empty picker for that provider instead of blocking the workspace.

| Agent | Discovery source | Project binding |
| --- | --- | --- |
| Codex | `~/.codex/session_index.jsonl` | Agent-maintained session index |
| Claude Code | `~/.claude/projects/<project-slug>/sessions-index.json` and top-level project JSONL transcript summaries | Project-slug bucket |
| Cursor | `User/globalStorage/state.vscdb` `composer.composerHeaders` | Composer workspace identifier path |
| Kimi | `~/.kimi/sessions/<md5(project path)>/<session>/state.json` | Project path hash bucket |
| Gemini / Antigravity | `~/.gemini/antigravity/brain/*/*.metadata.json` | Global metadata; shown only as available local metadata |

### Claude Code

Claude Code supports deterministic creation and resume:

```bash
claude --session-id <uuid>
claude -r <session_id>
claude --resume <session_id>
claude -c
```

Current built-in profile:

```yaml
claude:
  resume_mode: flag
  create_mode: generated_uuid
  create_template: "claude --session-id {session_id}"
  resume_template: "-r {session_id}"
```

UX implication:

- CC Branch can generate a UUID before first launch.
- First launch can be bound immediately.
- Later launch can reliably resume.

### Codex

Codex supports resume and picker flows:

```bash
codex resume <SESSION_ID>
codex resume --last
codex resume
codex fork <SESSION_ID>
```

Current built-in profile:

```yaml
codex:
  resume_mode: flag
  resume_template: "resume {session_id}"
```

UX implication:

- If CC Branch already has a `session_id`, it can run `codex resume <id>`.
- If there is no binding, CC Branch should start `codex` normally and attempt
  post-launch discovery.
- If post-launch discovery cannot confidently identify the new Codex session,
  CC Branch should leave the window unbound and offer a Bind action later.

## Product Principles

1. **Start first, explain later.**
   The primary button remains Start. Session choices are secondary.

2. **Never silently bind ambiguous history.**
   If multiple plausible sessions exist, users choose.

3. **Do not punish empty state.**
   "No previous sessions found" should lead directly to "Start will create one".

4. **State is reversible.**
   Users can bind, rebind, unbind, start new, and recover from failed resume.

5. **Metadata only by default.**
   Discovery reads IDs, timestamps, cwd/project hints, and source path. It does
   not parse prompt text or assistant messages unless a future explicit opt-in
   feature is added.

## User Journey

### First-Time User, No Sessions

User intent: "Start the workspace."

Path:

1. User runs `cc-branch start` or clicks Start in Web UI.
2. CC Branch checks state for bound sessions.
3. No binding exists.
4. CC Branch checks whether the agent supports deterministic creation.
5. If supported, create and bind automatically.
6. If not supported, launch normally and try post-launch discovery.
7. Dashboard shows either `Bound` or `Started, not bound yet`.

User-facing copy:

```text
No previous sessions found.
Starting this window will create a new session automatically.
```

Success state:

```text
planner · Claude Code · Bound
planner · Codex · Started · Binding pending
```

### Returning User With Existing Binding

User intent: "Continue where I left off."

Path:

1. State contains `session_id` for `slot.window`.
2. Start uses the agent resume command.
3. UI shows `Resuming bound session`.
4. If resume succeeds, status remains Bound.

Failure path:

1. Resume command exits or agent reports missing session.
2. CC Branch preserves the binding.
3. User is offered:
   - Retry resume
   - Start new
   - Pick another session
   - Unbind

Copy:

```text
Could not resume this session. The binding is still saved.
```

### User Has Prior Sessions But No Binding

User intent: "Maybe continue an old thread."

Path:

1. Discovery finds local sessions for the current project.
2. If one high-confidence candidate exists, show it as a recommendation.
3. If multiple exist, show a picker.
4. Start new remains the primary action.

Copy:

```text
3 previous sessions found for this project.
Start new, or resume one of them.
```

### User Wants To Paste A Session ID

User intent: "I know exactly which session I want."

Path:

1. User opens Change session.
2. User pastes ID.
3. CC Branch validates basic shape and agent compatibility.
4. Binding is written to state.
5. Next start resumes the pasted session.

Copy:

```text
Session ID bound locally for dev:planner.
```

### User Wants A Clean New Session

User intent: "Do not resume old work."

Path:

1. User clicks Start new or runs `cc-branch session new dev:planner`.
2. CC Branch clears or supersedes the old binding for that target.
3. It creates a new session when possible.
4. Old binding may be kept in binding history for rollback.

Copy:

```text
New session started. Previous binding is no longer active.
```

## Session Policies

| Policy | Behavior | Default? |
| --- | --- | --- |
| `auto` | Resume if bound; otherwise create new when possible; otherwise launch unbound and discover. | Yes |
| `new` | Force a new agent session and replace active binding if creation succeeds. | No |
| `latest` | Use the most recent high-confidence discovered session. | No |
| `pick` | Show CLI/Web picker before launch. | No |
| `manual` | Require explicit session ID input. | No |
| `unbound` | Launch agent without binding or resume. | No |

Policy is a launch-time control. It should not be persisted in shared config in
v1. A future local preference may remember the user's last choice per window,
but the safe default remains `auto`.

## Launch Decision Matrix

| Condition | Default action | User prompt? |
| --- | --- | --- |
| State has bound session and agent supports resume | Resume bound session. | No |
| State has bound session but resume fails | Preserve binding and offer recovery actions. | Yes, after failure |
| No binding, deterministic create supported | Generate session ID, start, write state. | No |
| No binding, one high-confidence existing session | Start new by default; show Resume previous as secondary. | No blocking prompt |
| No binding, multiple candidates | Start new by default; picker available. | No blocking prompt |
| No binding, no candidates | Start new / unbound depending on agent capability. | No |
| User explicitly chooses latest | Bind/use most recent high-confidence candidate. | Confirm if replacing binding |
| User explicitly pastes ID | Bind after validation. | Confirm if replacing binding |

CLI examples:

```bash
cc-branch start
cc-branch start --session-policy auto
cc-branch start --session-policy new dev:planner
cc-branch session discover
cc-branch session pick dev:planner
cc-branch session bind dev:planner --session-id <id>
cc-branch session unbind dev:planner
```

Web UI examples:

- Primary: Start
- Secondary: Resume previous
- Tertiary: Change session
- Menu actions:
  - Start new
  - Pick existing
  - Use latest
  - Enter session ID
  - Unbind

## Discovery Model

### Provider Interface

```python
class AgentSessionProvider(Protocol):
    agent_id: str

    def discover(self, project_dir: Path) -> list[DiscoveredSession]:
        ...

    def validate(self, session_id: str, project_dir: Path) -> SessionValidation:
        ...

    def supports_deterministic_create(self) -> bool:
        ...

    def supports_post_launch_discovery(self) -> bool:
        ...
```

### Data Model

```python
@dataclass(frozen=True)
class DiscoveredSession:
    agent_id: str
    session_id: str
    title: str | None
    project_dir: Path | None
    updated_at: datetime | None
    source: Literal["claude", "codex", "manual", "state"]
    source_path: Path | None
    confidence: Literal["high", "medium", "low"]
    metadata: dict[str, str]
```

No conversation body fields are included.

### Confidence Rules

High confidence:

- Session metadata explicitly references the same project directory.
- Or session is already bound in current state.
- Or the agent provider exposes a project-specific index.

Medium confidence:

- Session is in a path-derived project bucket.
- Or cwd-like metadata normalizes to the same path, but source format is not
  officially stable.

Low confidence:

- Only timestamp or global recency matches.
- Only agent type matches.
- User manually pasted an ID that cannot be locally verified.

Auto-binding is allowed only for high-confidence sessions produced by
deterministic create or post-launch discovery within the launch window.

## Post-Launch Discovery Contract

Post-launch discovery is needed for agents that can resume by ID but cannot be
started with a preselected ID.

Algorithm:

1. Take a metadata snapshot for the agent and project before launch.
2. Launch the agent normally.
3. After a short debounce, take a second metadata snapshot.
4. Compute newly created or newly updated sessions.
5. Bind only if exactly one high-confidence candidate is found.
6. If zero or multiple candidates are found, leave the target unbound and show a
   non-blocking Bind action.

Timing:

- Initial debounce: 1-3 seconds after launch returns control to CC Branch.
- Optional refresh window: allow manual Refresh in Web UI.
- Do not keep background filesystem watchers running in v1.

Safety:

- Never bind based only on global "latest" if another session was created in a
  different project during the same window.
- Never parse conversation bodies to improve confidence.
- Do not fail the launch if discovery fails.

## Architecture

Proposed package:

```text
cc_branch/agent_sessions/
  __init__.py
  models.py
  discovery.py
  binding.py
  providers/
    __init__.py
    claude.py
    codex.py
```

Application use cases:

```text
cc_branch/application/session_workflows/
  discover.py
  bind.py
  unbind.py
  policy.py
```

Why separate from `runtime.sessions`:

- `runtime.sessions` currently describes CC Branch planned/running window
  session state.
- Agent session discovery is about external CLI conversation metadata.
- Mixing the two would blur tmux runtime sessions with agent conversation
  sessions.

## State Schema Extension

Existing state should continue to work.

Current shape:

```yaml
windows:
  dev.planner:
    session_id: "..."
    label: "..."
```

Proposed additive fields:

```yaml
windows:
  dev.planner:
    session_id: "..."
    label: "demo/dev/planner"
    session_source: "discovered"
    session_agent: "codex"
    session_bound_at: "2026-05-10T12:00:00Z"
    session_confidence: "high"
```

Optional binding history:

```yaml
session_bindings:
  dev.planner:
    active_session_id: "..."
    previous:
      - session_id: "..."
        unbound_at: "2026-05-10T12:00:00Z"
        reason: "start_new"
```

Implementation should start with additive window fields only. Binding history
can be added later if needed.

## Web UI Design

### Dashboard Row States

Each agent window should show one compact session indicator:

| State | Label | Action |
| --- | --- | --- |
| Bound and resumable | `Bound` | Change session |
| No session found | `New session on start` | Start |
| Candidates found | `3 previous sessions` | Resume previous |
| Binding pending | `Binding pending` | Refresh / Bind manually |
| Resume failed | `Resume failed` | Retry / Start new |
| Agent unsupported | `Session not supported` | Start unbound |

Avoid showing full UUIDs inline. Use shortened ID in detail panel:

```text
0bdc1c42...52e
```

### Session Panel

Opened from window row or card.

Structure:

```text
Session

Current
Bound to 0bdc1c42...52e
Claude Code · updated 2h ago

Actions
[Resume] [Start new] [Unbind]

Found sessions
○ 0bdc1c42...52e  Today 14:20  high confidence
○ e68930f3...70   Yesterday    medium confidence

Manual
[ Paste session id              ] [Bind]
```

Rules:

- Primary action depends on context.
- If no candidates exist, the panel explains that Start will create one.
- Destructive or state-changing actions require clear copy, but not heavy
  confirmation unless they discard an existing binding.
- Rebinding should show old and new short IDs before confirming.

### Empty State

Do not show a blank picker.

```text
No previous sessions found.
Start will create a new session and bind it when possible.
```

### Accessibility

- Session picker is keyboard navigable.
- Radio options expose agent, short ID, updated time, and confidence.
- Manual input has clear validation error text.
- Loading discovery does not block Start.

## CLI Design

### `cc-branch session discover`

Shows sessions for current project and selected config:

```text
Found 3 sessions for /repo

Agent    Session          Updated       Confidence
claude   0bdc1c42...52e   2h ago        high
codex    019df4b0...472   yesterday     medium
```

JSON output:

```bash
cc-branch --format json session discover
```

### `cc-branch session pick dev:planner`

Interactive picker:

```text
Select session for dev:planner
> Start new session
  Claude 0bdc1c42...52e  2h ago
  Enter session ID manually
```

Non-interactive fallback:

```bash
cc-branch session bind dev:planner --session-id <id>
cc-branch session unbind dev:planner
cc-branch session new dev:planner
```

### `start` Behavior

Default:

```bash
cc-branch start
```

Equivalent:

```bash
cc-branch start --session-policy auto
```

If no binding exists:

- Deterministic create agents create and bind.
- Other agents launch unbound and schedule/offer discovery.

Output should stay quiet on the happy path. Show session details only when they
help explain a state transition:

```text
✓ Started dev:planner
  Bound new Claude Code session 0bdc1c42...52e
```

For unbound agents:

```text
✓ Started dev:planner
  Session binding pending. Run `cc-branch session discover` to bind an existing session.
```

## Backend API

New endpoints:

```text
GET  /api/sessions/discover?project_path=...&config_path=...
POST /api/sessions/bind
POST /api/sessions/unbind
POST /api/sessions/new
```

Example discover response:

```json
{
  "project_path": "/repo",
  "config_path": "/repo/.cc-branch/config.yaml",
  "sessions": [
    {
      "agent_id": "claude",
      "session_id": "0bdc1c42-4926-4dc6-be6a-35d05a48a52e",
      "short_id": "0bdc1c42...52e",
      "updated_at": "2026-05-10T12:00:00Z",
      "confidence": "high",
      "source": "claude",
      "project_dir": "/repo"
    }
  ]
}
```

Bind request:

```json
{
  "project_path": "/repo",
  "config_path": "/repo/.cc-branch/config.yaml",
  "target": "dev:planner",
  "agent_id": "claude",
  "session_id": "0bdc1c42-4926-4dc6-be6a-35d05a48a52e"
}
```

All session APIs must honor `project_path` and `config_path` in the same way as
status/config/action APIs. Binding writes to the selected config's state path.

## Privacy And Safety

- Discovery must be local-only.
- Default discovery reads metadata and filenames, not message bodies.
- API must never expose raw conversation text.
- Web UI must not show full filesystem paths unless the user opens details.
- Manual session ID entry should not validate by launching the agent.
- Binding writes only local state.
- Existing binding should not be replaced silently.

## Error Handling

| Problem | UX |
| --- | --- |
| Provider directory missing | Treat as no sessions found. |
| Provider format changed | Show provider unavailable warning, do not block Start. |
| Multiple high-confidence sessions | Ask user to pick. |
| Resume command fails | Preserve binding, offer Retry / Start new / Rebind. |
| Manual ID invalid shape | Show inline validation. |
| Agent mismatch | Warn before binding. |
| State save conflict | Re-read state and retry once; otherwise show conflict. |

## MVP Scope

V1 should include:

- Metadata-only Claude and Codex discovery.
- Explicit bind/unbind/manual bind.
- Automatic deterministic create for Claude Code.
- Codex resume when a binding already exists.
- Codex post-launch discovery only when the provider can identify exactly one
  high-confidence new session.
- Web UI session indicator and Session panel.
- CLI discover/bind/unbind/new.

V1 should not include:

- Persistent user-level session policy preferences.
- Conversation previews.
- Background filesystem watchers.
- Cross-machine sync.
- Binding history UI.
- Automatic binding of medium/low-confidence historical sessions.

## Acceptance Criteria

### Product

- A first-time user can click Start without seeing a required session choice.
- A returning user with a bound session resumes without extra prompts.
- A user with prior local sessions can explicitly bind one from Web UI.
- A user can paste a session ID from CLI or Web UI.
- A user can start fresh even when prior sessions exist.

### Technical

- Bindings are stored in the selected config's state file.
- Binding workflows never write session IDs to config. Existing explicit
  `session_id` config overrides remain a separate advanced configuration
  feature.
- Discovery providers are isolated behind an interface.
- Claude deterministic create is supported.
- Codex resume is supported when a session ID is bound.
- Codex no-binding start does not block on discovery.
- Discovery failures do not fail workspace start.

### Test Coverage

- Unit tests for Claude discovery provider.
- Unit tests for Codex discovery provider.
- Unit tests for binding state mutation.
- Unit tests for post-launch before/after snapshot matching.
- CLI tests for `session discover`, `bind`, `unbind`, `new`.
- Web API tests for discover/bind/unbind.
- Frontend tests for empty state, candidates state, manual bind, start new.
- Regression test that config files are not modified by binding.
- Regression test that selected multi-config state file is used.
- Regression test that ambiguous post-launch discovery does not bind.

## Rollout Plan

1. Add provider interfaces and metadata-only discovery.
2. Add state binding use cases.
3. Add CLI `session discover/bind/unbind/new`.
4. Add Web API endpoints.
5. Add Dashboard session indicators and Session panel.
6. Add post-launch discovery for agents that cannot deterministic-create.
7. Add provider-specific confidence improvements.

## Open Questions

- Can current Codex expose the newly created interactive session ID reliably
  without parsing private message content?
- Should `latest` be allowed as a persistent policy, or only as a one-time
  command?
- Should binding history be included in v1, or delayed until users request
  undo/rollback?
- Do we need provider-level feature flags for unstable local metadata formats?

## Review Passes

### User Perspective Review 1: First-Time Flow

Concern:

- The first-time user may be forced to understand sessions before starting.

Resolution:

- The default `auto` policy starts without a session choice.
- Empty state copy says Start will create a session automatically.
- Discovery loading must not block Start.

### User Perspective Review 2: Returning Flow

Concern:

- Returning users care about "continue my work", not "bind a session ID".

Resolution:

- Bound sessions resume silently.
- UI labels say Bound, Resume, Start new, Change session.
- Full UUID is hidden behind details.

### User Perspective Review 3: Recovery Flow

Concern:

- A failed resume could make users fear their work is lost.

Resolution:

- Resume failure preserves the binding.
- UI offers Retry, Start new, Pick another, and Unbind.
- Copy explicitly says the saved binding is still present.

### Product Designer Review 1: Hierarchy

Concern:

- Too many session controls could clutter the Dashboard.

Resolution:

- Dashboard uses one compact session indicator per window.
- Full controls live in a Session panel.
- Primary workspace action remains Start/Open.

### Product Designer Review 2: Choice Architecture

Concern:

- If prior sessions exist, users may not know whether to resume or start new.

Resolution:

- Start new remains available and visible.
- Resume previous is recommended only for high-confidence candidates.
- Multiple candidates use a picker instead of automatic binding.

### Product Designer Review 3: Trust And Privacy

Concern:

- Users may worry CC Branch is reading AI conversation history.

Resolution:

- Spec requires metadata-only discovery.
- UI should say "Found previous sessions" rather than showing message previews.
- API response excludes conversation body fields by design.
