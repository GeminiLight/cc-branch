# CC Branch Documentation Index

This page is the single source of truth for navigating CC Branch documentation.
**Status labels** are the authoritative reference for what is shipped vs. roadmap vs. not-yet-implemented.

---

## Quick Navigation

| What you need | Start here |
|---|---|
| First time using CC Branch | [`docs/getting-started.md`](getting-started.md) |
| 5-minute quick start | [`docs/quickstart.md`](quickstart.md) |
| Comprehensive usage guide | [`docs/user-guide.md`](user-guide.md) |
| Feature overview (中文) | [`docs/features.md`](features.md) |
| Architecture for contributors | [`docs/architecture.md`](architecture.md) |
| Web UI documentation | [`docs/webui-spec.md`](webui-spec.md) |
| Installation problems | [`docs/install-troubleshooting.md`](install-troubleshooting.md) |
| Contributing guidelines | [`docs/contributing.md`](contributing.md) |

---

## Document Map

### Getting Started (User-Facing)

| File | Language | Status | Notes |
|---|---|---|---|
| `getting-started.md` | English | ✅ Shipped | Primary getting started guide |
| `quickstart.md` | 中文 | ✅ Shipped | 5-minute quick start |
| `user-guide.md` | 中文 | ✅ Shipped | Comprehensive usage guide |
| `features.md` | 中文 | ✅ Shipped | Feature overview |

### Architecture

| File | Language | Status | Notes |
|---|---|---|---|
| `architecture.md` | English | ✅ Shipped | Current shipped architecture |
| `architecture-application-layer-spec.md` | English | 🚧 In Progress | Application layer refactor spec |
| `package-architecture-spec.md` | English | ✅ Shipped | Package structure decisions |
| `module-package-candidates.md` | English | 🚧 In Progress | Module-to-package migration status |

**Key relationship**: `architecture.md` describes the current shipped architecture.
`architecture-application-layer-spec.md` describes the ongoing refactor. The refactor spec
will replace the relevant sections of `architecture.md` once Phase 7 cleanup is complete.

### Web UI

| File | Language | Status | Notes |
|---|---|---|---|
| `webui-spec.md` | English | ✅ Shipped | Current shipped Web UI backend/frontend surface |
| `webui-sidebar-spec.md` | English | ✅ Shipped | Current navigation notes |
| `webui-dashboard2-spec.md` | English | 🚧 Roadmap | Multi-project dashboard (roadmap boundary) |
| `webui-userflow.md` | English | 🚧 Roadmap | User flows (verify implementation) |
| `workspace-terminology.zh.md` | 中文 | 🚧 Roadmap | Workspace / Tab / Pane terminology for the next Web UI model |
| `dashboard-ux-comparison.html` | English | 🚧 Roadmap | Dashboard UX comparison (output file) |

**Key relationship**: `webui-spec.md` is the authoritative reference for the shipped Web UI.
`webui-dashboard2-spec.md` and `webui-userflow.md` are roadmap documents that should not be
presented as shipped behavior.

### Specifications

| File | Language | Status | Notes |
|---|---|---|---|
| `session-discovery-binding-spec.md` | English | ❌ Not Yet Implemented | Product/architecture spec for session discovery |
| `multi-config-spec.md` | English | 🚧 In Progress | Multi-config workspace implementation |
| `global-project-index-spec.md` | English | 🚧 In Progress | Global project index implementation |
| `openers-refactor-spec.md` | English | 🚧 In Progress | Openers package refactor |

**Key relationship**: These are implementation specs for features not yet shipped.
Users should not encounter these features in normal usage until they are implemented.

### UX / Testing

| File | Language | Status | Notes |
|---|---|---|---|
| `ux-state-matrix.md` | English | ✅ Shipped | UX state definitions |
| `user-use-conditions.md` | English | ✅ Shipped | User boundary conditions for QA |

### Operations

| File | Language | Status | Notes |
|---|---|---|---|
| `contributing.md` | English | ✅ Shipped | Contributing guidelines |
| `github-actions.md` | 中文 | ⚠️ Deprecated | Content covered by `publishing.md` |
| `publishing.md` | 中文 | ✅ Shipped | Publishing and distribution guide |
| `release-readiness-review.md` | English | ⚠️ Archived | One-time pre-release review (2026-04-28), see `publishing.md` for current procedures |
| `install-troubleshooting.md` | English | ✅ Shipped | Installation troubleshooting |

### HTML Outputs

| File | Status | Notes |
|---|---|---|
| `dashboard-ux-comparison.html` | 🚧 Roadmap | Generated output, not source documentation |
| `config-layout-options.html` | 🚧 Roadmap | Generated output, not source documentation |

---

## Status Definitions

| Status | Meaning |
|---|---|
| ✅ Shipped | This document describes behavior that is currently available to users. |
| 🚧 In Progress | Implementation is underway. Behavior may change before shipping. |
| 🚧 Roadmap | Feature or design is planned but not yet implemented. Do not present as shipped. |
| ❌ Not Yet Implemented | Spec exists but the feature has not been built yet. |
| ⚠️ Historical | Document was correct at time of writing but may now be stale. Verify before trusting. |
| ⚠️ Dated | Document has a specific date and may need review. |

---

## Cross-Reference Guide

When you update behavior, these docs must be kept in sync:

**User-facing changes** → update in order:
1. `docs/getting-started.md`
2. `docs/quickstart.md` / `docs/user-guide.md` / `docs/features.md` (whichever applies)
3. `docs/architecture.md` (if architecture is affected)
4. `docs/webui-spec.md` (if Web UI is affected)
5. `README.md` / `README.zh.md`
6. `docs/README.md` (documentation index)

**Architecture changes** → update:
1. `docs/architecture.md` (shipped architecture)
2. `docs/architecture-application-layer-spec.md` (refactor spec, until Phase 7 cleanup)
3. `docs/contributing.md` (if workflow boundaries change)

**Web UI changes** → update:
1. `docs/webui-spec.md` (shipped surface)
2. `docs/webui-sidebar-spec.md` (navigation notes)
3. `docs/contributing.md`

**Spec documents** (session-discovery, multi-config, global-project-index, openers-refactor)
are implementation guides. They should not be linked from user-facing docs until the feature ships.

---

## Language Guidance

User-facing docs should be available in both English and Chinese for accessibility:

| English | Chinese | Notes |
|---|---|---|
| `getting-started.md` | `quickstart.md` (中文 quickstart) | Different content, not direct translation |
| `features.md` | 中文 | Feature overview |
| `user-guide.md` | 中文 | Comprehensive guide |
| `contributing.md` | — | English only is acceptable for contributors |
| `architecture.md` | — | English only is acceptable |

If you add a new user-facing doc, prefer English as the primary version and note the
Chinese equivalent in the doc header.

---

## Common Issues

### Wiki references
`wiki/README.md` exists and correctly directs users to `docs/` for current behavior.
The wiki contains historical design docs and phase specifications. It is a valid
resource but should not be the primary reference for shipped behavior.

**Note**: `features.md`, `user-guide.md`, and `quickstart.md` previously linked to
`wiki/README.md`. Those links have been removed to avoid suggesting the wiki is
required reading for current users.

### Duplicate release docs
Resolved: `github-release-checklist.md` was deleted (historical initial-setup checklist).
`github-actions.md` was marked deprecated (content covered by `publishing.md`).
The authoritative release guide is now [`docs/publishing.md`](publishing.md).

### Session discovery is NOT shipped
`session-discovery-binding-spec.md` is clearly marked "Not yet implemented".
Do not link to it from shipped user-facing docs.

### Dashboard spec is roadmap
`webui-dashboard2-spec.md` explicitly warns against presenting it as shipped.
The "Recommended framing" section in that doc explains the correct way to describe it.

---

*Last reviewed: 2026-05-10*
