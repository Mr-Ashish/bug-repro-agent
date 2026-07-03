# Plane Issue Taxonomy — Bug Reproduction Agent Target Analysis

> **Target app:** [Plane](https://github.com/makeplane/plane) (makeplane)
> **Stack:** Next.js (React Router) + Django REST + PostgreSQL + Redis + RabbitMQ + MinIO
> **Local clone:** `~/bug-repro-agent/plane/` — being set up by a parallel Claude Code session
> **Dataset:** 200 most recent issues (July 2026 → April 2026)
> **Date:** 2026-07-03

---

## Architecture Context

Plane is a **full-stack web app** (project management tool), not a widget library:

```
apps/
  web/          → Next.js frontend (React Router, TypeScript)
  api/          → Django REST backend (Python)
  admin/        → Admin panel (god-mode)
  space/        → Public pages
  live/         → Real-time collaboration
  proxy/        → Nginx reverse proxy

Infrastructure: PostgreSQL + Redis (Valkey) + RabbitMQ + MinIO (S3)
Local dev:      docker-compose-local.yml boots all services
```

This changes EVERYTHING about the bug repro agent design vs Panel:
- Bugs are **not Python snippets** — they're "navigate to X, click Y, observe Z"
- Seeding requires **database state** (workspaces, projects, work items), not Python scripts
- The app needs a **full docker-compose stack** running, not just `panel serve app.py`

---

## Raw Numbers

| Category | Total | Open | Closed |
|---|---|---|---|
| Non-bugs filtered (features, spam, docs, security advisories) | ~55 | — | — |
| **Actual bugs** | **~149** | ~120 | ~29 |

---

## Bug Clusters

### Cluster A: UI Interaction / Frontend Behavior Bugs (~40 issues)
> User clicks/types/drags something → wrong thing happens (or nothing happens) in the browser. **This is the sweet spot for a Playwright-based repro agent.**

| # | Title | State | Repro Complexity | Demo Quality |
|---|---|---|---|---|
| **9329** | Inline work item creation shows generic error on 255+ char title | OPEN | Low — type long text, press Enter | ⭐⭐⭐ |
| **9124** | Sub-task expand requires 3 clicks | OPEN | Low — click chevron, observe | ⭐⭐⭐ |
| **9051** | Link click opens duplicate tabs | OPEN | Low — click any link in comment | ⭐⭐⭐ |
| **9050** | Deleted Stickies reappear on page reload | OPEN | Low — delete sticky, reload | ⭐⭐⭐ |
| **8882** | Cursor jumps to next line while typing in text editor | CLOSED | Low — type in editor | ⭐⭐⭐ |
| **8913** | Chinese IME enter sends comment prematurely | OPEN | Medium — needs IME simulation | ⭐⭐ |
| **9342** | Work items show wrong URL in browser | CLOSED | Low — open item, check URL bar | ⭐⭐ |
| **8877** | Hotkeys don't work in side peek / modal | OPEN | Low — open item, press hotkey | ⭐⭐ |
| **9280** | Special characters rejected in project title | OPEN | Low — create project with dash | ⭐⭐ |
| **8926** | MCP Auth opens tabs non-stop | OPEN | Medium — needs MCP setup | ⭐ |
| **8998** | Truncated Epic name | OPEN | Low — create long-name epic | ⭐⭐ |
| **9182** | Close (X) button poor contrast on Cycles modal | OPEN | Low — visual inspection | ⭐ |

### Cluster B: State Management / Optimistic Update Bugs (~25 issues)
> Frontend shows stale state, drag-drop doesn't update, filters produce wrong results. Backend is correct but UI is wrong.

| # | Title | State | Repro Complexity | Demo Quality |
|---|---|---|---|---|
| **9049** | Kanban drag/drop silently no-ops in epic-filtered views | OPEN | Medium — needs epic + filter setup | ⭐⭐⭐ |
| **9320** | Some work item state transitions missing from history | OPEN | Medium — needs state change sequence | ⭐⭐ |
| **9316** | "Updated At" filter with "IS" returns no results | OPEN | Low — apply filter, observe | ⭐⭐ |
| **8936** | Filter "no cycle" → infinite loading (None → UUID validation) | OPEN | Low — dashboard → no-cycle items | ⭐⭐⭐ |
| **9260** | Sidebar pin/unpin not persisted | CLOSED | Low — pin sidebar item, reload | ⭐⭐ |
| **9183** | AI Build mode "awaiting" state not shown until reload | OPEN | Medium — needs AI feature | ⭐ |

### Cluster C: Backend / API Bugs (~35 issues)
> Server returns wrong data, crashes with 500, or silently drops operations. These can be reproduced with API calls (no browser needed).

| # | Title | State | Repro Complexity | Demo Quality |
|---|---|---|---|---|
| **9172** | Password reset with non-existent user ID → unhandled 500 | OPEN | Low — single API call | ⭐⭐⭐ |
| **9169** | Archiving cycle with no end date → TypeError crash | OPEN | Low — API call | ⭐⭐⭐ |
| **9166** | Project invitations broken — `.delay()` on list | OPEN | Low — API call | ⭐⭐⭐ |
| **9165** | `is_signup` flag inverted | OPEN | Low — signup flow | ⭐⭐⭐ |
| **9167** | WorkspaceMember.filter().role returns QuerySet not int | OPEN | Low — invite creation | ⭐⭐ |
| **9168** | Accept invitation doesn't update member role | OPEN | Low — accept invite API | ⭐⭐ |
| **9170** | Delete intake issue crashes when linked issue deleted | OPEN | Medium — needs linked issue setup | ⭐⭐ |
| **9175** | Comment reaction activity crashes Celery task | OPEN | Medium — needs reaction + deleted reaction | ⭐⭐ |
| **9177** | Analytics charts show wrong data — queryset anchored to wrong model | OPEN | Medium — needs cycle/module data | ⭐⭐ |
| **9158** | `dispatch()` returns exception object instead of HTTP response | OPEN | Low — trigger any API error | ⭐⭐ |
| **9340** | Public API pagination ignores `?page=` | OPEN | Low — API call | ⭐⭐⭐ |
| **9252** | Mixed types expression error (UUID vs Char) | OPEN | Medium | ⭐⭐ |
| **9012** | Any update to completed item resets completed_at | OPEN | Low — PATCH API call | ⭐⭐⭐ |
| **9011** | API doesn't respect `completed_at` field | OPEN | Low — API call | ⭐⭐ |
| **9115** | API allows archiving non-completed items | OPEN | Low — PATCH archived_at | ⭐⭐ |

### Cluster D: OAuth / Authentication Bugs (~12 issues)
> Login flows crash, OAuth callbacks fail, signup flags inverted.

| # | Title | State |
|---|---|---|
| 9164 | GitLab OAuth callback crashes — variable shadowing | OPEN |
| 9159 | GitHub OAuth callback crashes — variable shadowing | OPEN |
| 9295 | Onboarding redirect loop — workspace URL taken | OPEN |
| 9221 | Google login not working on CE | OPEN |
| 9259 | DEFAULT_EMAIL/PASSWORD env vars ignored | OPEN |

### Cluster E: Deployment / Infrastructure Bugs (~20 issues)
> Docker, Helm, Nginx, MinIO, SMTP config issues. Not reproducible without specific infra.

| # | Title | State |
|---|---|---|
| 9321 | API container restarts — missing table | OPEN |
| 9199 | Setup script fails on RHEL x86_64 | OPEN |
| 9045 | Helm chart generates HTTP URLs behind HTTPS proxy | OPEN |
| 9234 | Proxy corrupts multipart uploads → all uploads fail | OPEN |
| 8971 | SMTP fails with Brevo/Sendinblue — SSL mismatch | OPEN |
| 9266 | Migrator log path doesn't exist | OPEN |

### Cluster F: Mobile / Safari / Browser-Specific Bugs (~8 issues)
> Crashes only in WebKit, iOS, or specific browsers.

| # | Title | State |
|---|---|---|
| 9231 | iOS WebKit: gantt-layout-loader crashes on requestIdleCallback | OPEN |
| 9134 | Safari: project open crashes — same requestIdleCallback | CLOSED |
| 8904 | WebKit Kanban view crash | OPEN |
| 8867 | React hydration error on mobile browsers | OPEN |
| 9328 | Header not responsive on mobile | OPEN |

### Cluster G: Security Vulnerabilities (~6 issues)
> XSS, injection, file sanitization — important but different scope.

| # | Title | State |
|---|---|---|
| 9218 | Stored XSS via `actor_comment|safe` in email notifications | OPEN |
| 9066 | URL parameter injection in Unsplash proxy | CLOSED |
| 9127 | Filename sanitization doesn't strip control chars | OPEN |
| 9067 | Data dir world-readable (755) | OPEN |

---

## Key Insight: Plane Bugs Are Fundamentally Different From Panel Bugs

| Dimension | Panel (old target) | Plane (new target) |
|---|---|---|
| **Seed** | Python snippet from issue | Database state (workspaces, projects, work items) |
| **Boot** | `panel serve app.py` | Full docker-compose stack (6+ services) |
| **Drive** | Interact with widgets | Navigate multi-page SPA, fill forms, drag-drop |
| **Oracle** | Widget value assertion | API response + UI state + URL + toast/error |
| **Issue structure** | Has code snippet (~80%) | Has "steps to reproduce" (~70%) |
| **Auth** | None | Login required for all actions |

---

## Demo Candidate Recommendations

### 🏆 Tier 1: Perfect Demo Candidates

These bugs have: clear steps, low setup complexity, deterministic reproduction, and obvious pass/fail.

**UI Bugs (Playwright-driven):**

| # | Title | Why Perfect |
|---|---|---|
| **9329** | Inline creation error on 255+ char title | Login → go to Work Items → type long title → assert error message is descriptive (not generic) |
| **9050** | Deleted stickies reappear on reload | Login → create sticky → delete → reload → assert sticky gone |
| **9051** | Link click opens duplicate tabs | Login → open work item with link → click → assert only 1 new tab |
| **9124** | Sub-task expand needs 3 clicks | Login → navigate to issue with sub-tasks → click chevron → assert expanded |
| **8936** | No-cycle filter → infinite loading | Login → dashboard → click "no cycle" items → assert no infinite spinner |

**API Bugs (curl/httpx-driven, no browser needed):**

| # | Title | Why Perfect |
|---|---|---|
| **9172** | Password reset with bad user ID → 500 | Single POST request → assert status != 500 |
| **9169** | Archive cycle with no end date → TypeError | Create cycle without end date → PATCH archive → assert no crash |
| **9012** | Update completed item resets completed_at | PATCH any field → assert completed_at unchanged |
| **9340** | API pagination ignores `?page=` | GET /work-items/?page=2 → assert different results from page=1 |
| **9166** | Project invitations → `.delay()` on list object | POST invitation → assert no 500 |

### 🥈 Tier 2: Good But More Setup

| # | Title | Gap |
|---|---|---|
| **9049** | Kanban drag/drop no-op in epic-filtered views | Needs epic + multiple states + filter setup |
| **9177** | Analytics charts show wrong data | Needs cycles/modules with populated data |
| **8877** | Hotkeys in side peek | Needs work item + specific peek mode |

### 🚫 Out of Scope for Demo
- **Cluster E** (deployment/infra) — Helm, RHEL, proxy-specific
- **Cluster F** (mobile/Safari) — browser-specific
- **Cluster G** (security) — different tool/approach
- **Cluster D** (OAuth) — needs external OAuth providers configured

---

## What This Means for the Agent Design

The original DESIGN.md was written for Panel (Python widget library). For Plane, the agent needs:

1. **No "seeder" as code** — seed state via API calls (create workspace, project, work items) or a database fixture
2. **Auth layer** — every reproduction starts with login
3. **Docker-compose lifecycle** — boot 6+ services, not a single Python process
4. **Two reproduction modes:**
   - **UI mode** (Clusters A, B): Playwright navigates the SPA
   - **API mode** (Cluster C): httpx/curl hits Django endpoints directly
5. **Richer oracles** — check toast messages, URL bar, tab count, loading spinners, API response codes
6. **State cleanup** — delete test data between runs to avoid pollution

This is a **redesign**, not a tweak.
