# Plane GitHub Issues — Complete Analysis & Demo-Worthiness Ranking

**Repo:** [makeplane/plane](https://github.com/makeplane/plane) — open-source project management  
**Total open issues analyzed:** 791  
**Date:** 2026-07-04  
**Purpose:** Rank every open issue for [repro-agent](./README.md) — a browser-use hackathon project that autonomously reproduces bugs from GitHub issues  

---

## Table of Contents

1. [Part A — Clustering: All 791 Issues Across 10 Dimensions](#part-a--clustering-all-791-issues-across-10-dimensions)
2. [Part B — First Principles: What the Agent Can and Cannot Do](#part-b--first-principles-what-the-agent-can-and-cannot-do)
3. [Part C — The Funnel: 791 → 284 → 40 → 15](#part-c--the-funnel-791--284--40--15)
4. [Part D — Final Ranking: 15 Verified Demo-Worthy Issues](#part-d--final-ranking-15-verified-demo-worthy-issues)
5. [Part E — Demoted Issues (and Why)](#part-e--demoted-issues-and-why)
6. [Part F — Hackathon Demo Recommendation](#part-f--hackathon-demo-recommendation)

---

# Part A — Clustering: All 791 Issues Across 10 Dimensions

### Dimension 1: Issue Type

| Type | Count | % |
|------|------:|--:|
| Feature Request | 413 | 52.2% |
| Bug | 289 | 36.5% |
| Uncategorized | 89 | 11.3% |

> The backlog is feature-heavy (52%). Bugs at 36.5% are the target for repro-agent.

### Dimension 2: Label Distribution

| Label | Count |
|-------|------:|
| ✨feature | 366 |
| 🐛bug | 250 |
| plane | 215 |
| 🏠self-hosted | 14 |
| pages | 12 |
| 🌟enhancement | 11 |
| ✍️editor | 9 |
| 🔗integrations | 8 |
| importers | 6 |
| 📡api | 4 |
| 🎨UI / UX | 4 |
| 🌟improvement | 3 |
| ⚙️backend | 3 |
| 🐳docker | 2 |
| 📖docs | 2 |
| ⚡performance | 1 |
| 🔥urgent | 1 |
| devops | 1 |
| 🎣webhooks | 1 |
| non-docker-setup | 1 |

- **Labeled:** 638 (80.7%)
- **Unlabeled / untriaged:** 153 (19.3%)

### Dimension 3: Temporal Distribution

**By Year (creation date):**

| Year | Issues |
|------|-------:|
| 2023 | 98 |
| 2024 | 207 |
| 2025 | 206 |
| 2026 (6 months) | 280 |

**Recent months:**

| Month | Issues |
|-------|-------:|
| 2026-02 | 24 |
| 2026-03 | 39 |
| 2026-04 | 36 |
| **2026-05** | **98** ⚡ spike |
| 2026-06 | 38 |
| 2026-07 | 4 (partial) |

> Issue creation is accelerating. 2026 is already the largest year at 280 issues in 6 months. May 2026 saw a 2.7× spike.

### Dimension 4: Issue Age & Staleness

**Age since creation:**

| Bucket | Count | % |
|--------|------:|--:|
| < 1 week | 7 | 0.9% |
| 1–4 weeks | 30 | 3.8% |
| 1–3 months | 135 | 17.1% |
| 3–6 months | 106 | 13.4% |
| 6–12 months | 125 | 15.8% |
| 1–2 years | 178 | 22.5% |
| **> 2 years** | **210** | **26.5%** |

**Last activity:**

| Status | Count | % |
|--------|------:|--:|
| Active (< 1 week) | 29 | 3.7% |
| Recent (1–4 weeks) | 44 | 5.6% |
| Aging (1–3 months) | 175 | 22.1% |
| Stale (3–12 months) | 265 | 33.5% |
| **Abandoned (> 1 year)** | **278** | **35.1%** |

> ⚠️ 68.6% of issues have had no activity in 3+ months. 210 issues are older than 2 years.

### Dimension 5: Deployment Target

| Target | Count | % |
|--------|------:|--:|
| Self-Hosted | 281 | 35.5% |
| Cloud | 116 | 14.7% |
| Unspecified | 394 | 49.8% |

> Self-hosted pain is 2.4× cloud issues.

### Dimension 6: Contributor Landscape

- **553 unique authors** filed 791 issues
- **442 (79.9%)** filed exactly 1 issue (drive-by reporters)
- Top 5 authors account for only 68 issues (8.6%)
- Broad community distribution — not concentrated

### Dimension 7: Severity Signal

| Severity | Count | % |
|----------|------:|--:|
| Critical | 1 | 0.1% |
| High (crashes, data loss) | 51 | 6.4% |
| Medium (errors, broken features) | 240 | 30.3% |
| Low (enhancements) | 393 | 49.7% |
| Unassessed | 106 | 13.4% |

### Dimension 8: Product Component Hotspots

The top areas by issue volume (issues touch multiple components):

| Component | Issues |
|-----------|-------:|
| Pages/Documents | 176 |
| Work Items/Issues | 164 |
| Workspace | 144 |
| Authentication/SSO | 131 |
| Import/Export | 107 |
| Filters/Sorting | 91 |
| Comments/Activity | 84 |
| Members/Permissions | 83 |
| Modules | 75 |
| Cycles/Sprints | 74 |
| Performance | 63 |
| Labels | 58 |
| Dashboard/Analytics | 48 |
| Notifications | 44 |
| Editor | 42 |
| Gantt/Timeline | 27 |
| Inbox/Triage | 26 |
| Kanban/Board View | 25 |
| Calendar View | 19 |
| Spreadsheet/List View | 17 |
| Estimates | 16 |

### Dimension 9: Bug-Heavy Components (where bugs > 50%)

| Component | Bugs | Features | Bug % | |
|-----------|-----:|---------:|------:|-|
| **Docker/Self-Hosted** | 199 | 79 | **71.6%** | 🔥 |
| **API** | 102 | 85 | **54.5%** | 🔥 |

> Docker/Self-Hosted has the worst quality signal — nearly 3:1 bugs vs features.

### Dimension 10: Semantic Themes

| Theme | Issues |
|-------|-------:|
| UI/UX Polish (alignment, overflow, truncation) | 64 |
| Real-time / Sync | 53 |
| Dependencies / Relations | 35 |
| Data Loss / Corruption | 31 |
| Bulk Operations | 25 |
| Mobile / Responsive | 21 |
| Localization / i18n | 21 |
| Time Tracking | 20 |
| Custom Fields | 19 |
| Keyboard / Shortcuts | 11 |

---

# Part B — First Principles: What the Agent Can and Cannot Do

### The agent (`scripts/drive.py`)

- **Library:** [browser-use](https://github.com/browser-use/browser-use) (Python)
- **Model:** Claude Sonnet 4 via OpenRouter
- **Browser:** Chrome via CDP (WebSocket, localhost:9222)
- **Target:** Plane running on `localhost:80` via docker-compose
- **Credentials:** `admin@admin.com` / `qweQWE123!@#`
- **Workspace:** `plane-dev`
- **Seed data:** Project SEED — 5 work items (incl. edge cases), 5 states
- **Max steps:** 50
- **Viewport:** 1920 × 1080

### CAN do

- Navigate to any page on localhost:80
- Log in with admin credentials
- Click buttons, links, dropdowns, chevrons, menu items
- Type text into input fields (including long strings, special characters)
- Read visible text on screen via vision model
- Scroll, interact with menus, close modals
- Navigate Plane sidebar: Work Items, Cycles, Modules, Pages, Views, Settings
- Create/edit/delete work items, projects, states, stickies, pages
- Reload the page (navigate to same URL)
- Observe and screenshot error toasts, broken UI, missing elements
- Switch between Kanban/Board, List, Spreadsheet, Gantt views

### CANNOT do

| Limitation | Why it matters |
|-----------|----------------|
| Only Chrome (no Safari, Firefox) | Safari-only bugs won't reproduce |
| Only desktop viewport 1920×1080 | Mobile-only bugs won't reproduce |
| No CLI tools | `plane push`, `prime-cli` bugs are unreachable |
| No email send/receive | Can't verify email notifications |
| No external services | GitHub OAuth, Slack, JIRA import all unreachable |
| No Japanese IME or input methods | IME-dependent bugs won't reproduce |
| No Django admin or .env changes | Backend/config bugs are unreachable |
| No direct API calls | API-only bugs with no browser path are unreachable |
| Only one user (admin) | Bugs requiring multiple user accounts can't be tested |
| No PDF/file content inspection | Downloads go to disk, not visible in browser |
| No URL bar editing | Agent interacts with DOM elements, not the address bar |
| No native file picker control | OS-level file upload dialogs are unreliable |

---

# Part C — The Funnel: 791 → 284 → 40 → 15

```
791 total open issues
 │
 ├─ 413 feature requests ──────────────────────── SKIP (not bugs)
 ├─  31 infra/docker setup ────────────────────── SKIP (not browser-reproducible)
 ├─  31 need external integrations ────────────── SKIP (agent can't reach)
 ├─  18 enterprise/paid features ──────────────── SKIP (not in CE)
 ├─   8 backend-only ──────────────────────────── SKIP (no UI)
 ├─   7 API-only ──────────────────────────────── SKIP (no browser path)
 ├─   2 mobile-app only ───────────────────────── SKIP (no mobile)
 └─   2 docs-only ─────────────────────────────── SKIP (not bugs)
       │
       ▼
284 browser-reproducible bug candidates
       │
       ├─ Scored algorithmically across 6 dimensions
       ├─ Top ~40 full issue bodies fetched and read
       ├─ Each evaluated: "Can the agent actually do these steps?"
       │
       ▼
 15 verified demo-worthy issues (this ranking)
```

### Scoring dimensions used in initial algorithmic pass

| Dimension | Weight | What it measures |
|-----------|-------:|------------------|
| Visual Drama | /25 | Can the audience SEE the bug? |
| Speed | /20 | How many steps? How fast? |
| Reliability | /20 | Deterministic vs flaky? |
| Comprehensibility | /15 | Can audience understand in seconds? |
| Wow Factor | /10 | Does autonomous reproduction look impressive? |
| Feasibility | /10 | Works with seed data, no external deps? |

### Why the algorithmic scores were wrong

The keyword-based heuristics gave high scores to issues the agent **physically cannot reproduce**. Examples:

- **#8008 scored 88/100** — but requires a second user account (agent only has admin)
- **#6740 scored 84/100** — but it's a config/env variable issue (not browser-reproducible)
- **#5728 scored 84/100** — but requires editing the URL bar (agent can't do this)
- **#9158 scored 82/100** — backend dispatch error with no UI manifestation
- **#6359 scored 74/100** — timezone bug is DST-dependent and won't reproduce on July 4

The final ranking below was produced by **reading every issue body** and asking: *"Can browser-use, with the agent's exact capabilities, actually reproduce this?"*

---

# Part D — Final Ranking: 15 Verified Demo-Worthy Issues

Confidence ratings:
- 🟢 **HIGH** — Agent can definitely execute these steps and the bug will be visible
- 🟡 **MEDIUM** — Probably works but one step is uncertain
- 🔴 **LOW** — Significant risk the agent gets stuck or bug isn't visible

---

### 🥇 #1 — [#9329](https://github.com/makeplane/plane/issues/9329) — Inline work item creation shows generic error when title exceeds 255 characters

| | |
|---|---|
| **Labels** | 🐛bug, plane |
| **Filed** | 2026-06-28 |
| **Bug class** | form-validation |
| **Confidence** | 🟢 HIGH |
| **Step count** | ~8 |
| **Estimated time** | ~30s |

**Reproduction steps for the agent:**
1. Log in to Plane at localhost:80
2. Navigate to the SEED project
3. Go to Work Items
4. Click the inline "New work item" input (not the modal)
5. Type or paste a string longer than 255 characters
6. Press Enter to submit
7. Observe the error toast

**What the agent sees:** Error toast reads **"Some error occurred. Please try again."** instead of a descriptive validation message like "Title must be under 255 characters."

**Why the bug is real:** The sidebar/modal creation path correctly shows a descriptive error for the same input. This is an inconsistency between two creation code paths.

**Why it's #1:** Fastest execution. All steps are basic browser actions (navigate, click, type, read toast). No setup needed beyond seed data. The error is unambiguously visible on screen. Clear expected-vs-actual. The agent types text, submits, and a wrong error appears — simple narrative for the audience.

**Risk:** The inline creation input row might be harder to locate than the modal button. The agent needs to click the right creation path.

---

### 🥈 #2 — [#8591](https://github.com/makeplane/plane/issues/8591) — Soft-deleted states still visible after page refresh

| | |
|---|---|
| **Labels** | 🐛bug, plane |
| **Filed** | 2026-01-27 |
| **Bug class** | state-persistence |
| **Confidence** | 🟢 HIGH |
| **Step count** | ~12 |
| **Estimated time** | ~60s |

**Reproduction steps for the agent:**
1. Log in to Plane
2. Navigate to the SEED project
3. Click the gear icon → Project Settings
4. Go to States
5. Create a new state (e.g., "Test State")
6. Click the delete button on "Test State"
7. Confirm deletion
8. Observe the state disappears from the list
9. Refresh the page (F5 / re-navigate)
10. Observe: the deleted state has reappeared

**What the agent sees:** The state visually disappears after deletion, but reappears after page refresh. The soft-delete did not persist.

**Why it's #2:** "Zombie data" is the most dramatic bug class for a demo. The audience sees something get deleted, then sees it come back from the dead. Settings → States is a clean, uncluttered page so the reappearing state is impossible to miss. All steps are standard CRUD — high confidence the agent can execute them.

**Risk:** Agent needs to find the project settings gear icon. On Plane, this is typically at the bottom of the left sidebar within a project context.

**Note:** [#8590](https://github.com/makeplane/plane/issues/8590) is a duplicate of this issue.

---

### 🥉 #3 — [#9050](https://github.com/makeplane/plane/issues/9050) — Deleted stickies reappear on page reload

| | |
|---|---|
| **Labels** | 🐛bug, plane |
| **Filed** | 2026-05-11 |
| **Bug class** | state-persistence |
| **Confidence** | 🟡 MEDIUM |
| **Step count** | ~10 |
| **Estimated time** | ~60s |

**Reproduction steps for the agent:**
1. Log in to Plane
2. Navigate to the Home page or find the Stickies section
3. Look for the sticky note icon in the bottom-right floating toolbar
4. Create a new sticky note and write some text
5. Delete the sticky note
6. Confirm deletion when prompted
7. Observe the sticky disappears and a success toast appears
8. Reload the page
9. Observe: the deleted sticky is back

**What the agent sees:** The sticky disappears after deletion and a success toast confirms it. But after page reload, the sticky has returned.

**Why it's #3:** Same dramatic "zombie data" narrative as #2, but in a different product area (stickies vs states). This shows the agent can find bugs across different UI areas. The narrative is very strong for a demo — "I deleted this. I reloaded. It's back."

**Risk:** The stickies feature is accessed via a floating toolbar icon in the bottom-right corner, not through the main sidebar. The agent might struggle to find this icon since it's not in the standard navigation hierarchy. This is why confidence is MEDIUM instead of HIGH.

---

### #4 — [#8770](https://github.com/makeplane/plane/issues/8770) — Issue card state switching doesn't regroup kanban view

| | |
|---|---|
| **Labels** | 🐛bug, plane |
| **Filed** | 2026-03-18 |
| **Bug class** | ui-state-sync |
| **Confidence** | 🟢 HIGH |
| **Step count** | ~10 |
| **Estimated time** | ~45s |

**Reproduction steps for the agent:**
1. Log in to Plane
2. Navigate to the SEED project → Work Items
3. Switch to Board/Kanban view layout
4. Find an issue card in the "Backlog" column
5. Change its state to "Todo" (via the state dropdown on the card)
6. Observe: the card stays in the "Backlog" column instead of moving to "Todo"
7. Reload the page
8. Observe: the card is now correctly in the "Todo" column

**What the agent sees:** The state label on the card changes, but the card doesn't move to the correct column. Only a page refresh fixes the visual grouping.

**Why #4:** The kanban view is a natural, visual context. The audience instantly understands "the card should move when I change its state." The bug is unambiguous — the card stubbornly stays in the wrong column. The SEED project should have issues with multiple states.

**Risk:** The agent needs to find the state-change dropdown on a kanban card, which might be behind a hover action or a small icon. Low risk overall since kanban is a standard view.

---

### #5 — [#9226](https://github.com/makeplane/plane/issues/9226) — Project creation fails with special characters in project name

| | |
|---|---|
| **Labels** | 🐛bug, plane |
| **Filed** | 2026-06-11 |
| **Bug class** | form-validation |
| **Confidence** | 🟡 MEDIUM |
| **Step count** | ~7 |
| **Estimated time** | ~45s |

**Reproduction steps for the agent:**
1. Log in to Plane
2. Go to the Projects page
3. Click "Create Project"
4. Enter a project name containing special characters (e.g., `Test!Project` or `Project@2026`)
5. Submit the form
6. Observe: HTTP 400 error with `PROJECT_NAME_CANNOT_CONTAIN_SPECIAL_CHARACTERS`

**What the agent sees:** The project creation form breaks. The frontend may show React errors or a generic error toast instead of a clear validation message explaining which characters are not allowed.

**Why #5:** Fast to reproduce (just fill a form and submit). The name with special characters is a natural thing a user might try. The error is either dramatic (React error boundary = blank page) or informative (toast) — either way, the agent has something to report.

**Risk:** The exact visual manifestation depends on Plane's error handling. If the error is caught gracefully with a toast, it's less dramatic. If React error boundary fires, it's very dramatic. The exact special characters that trigger it may vary.

---

### #6 — [#7338](https://github.com/makeplane/plane/issues/7338) — Comment formatting toolbar disabled until text is typed

| | |
|---|---|
| **Labels** | 🐛bug, ✍️editor |
| **Filed** | 2025-07-04 |
| **Bug class** | ui-interaction |
| **Confidence** | 🟢 HIGH |
| **Step count** | ~7 |
| **Estimated time** | ~30s |

**Reproduction steps for the agent:**
1. Log in to Plane
2. Navigate to SEED project → Work Items
3. Open any existing issue
4. Scroll down to the comment section
5. Click on the comment input area
6. Observe: the formatting toolbar (including Upload Image) is disabled/grayed out
7. Type one character
8. Observe: the toolbar becomes active

**What the agent sees:** All formatting buttons (bold, italic, image upload, etc.) are grayed out and unclickable when the comment field is empty. They only enable after at least one character is typed.

**Why #6:** This is a clean before/after demonstration. The agent shows the disabled state, types a single character, then shows the enabled state. Very clear visual contrast. The audience immediately understands the bug — "why should I need to type text before I can upload an image?"

**Risk:** Very low. Opening an issue and looking at the comment area is straightforward. The SEED project has work items to choose from.

---

### #7 — [#5529](https://github.com/makeplane/plane/issues/5529) — Wrong menu text "Remove parent issue" when unlinking sub-issue

| | |
|---|---|
| **Labels** | 🐛bug |
| **Filed** | 2024-09-04 |
| **Bug class** | ui-copy-error |
| **Confidence** | 🟢 HIGH |
| **Step count** | ~8 |
| **Estimated time** | ~30s |

**Reproduction steps for the agent:**
1. Log in to Plane
2. Navigate to SEED project → Work Items
3. Open an issue that has sub-issues (the SEED data has these)
4. Scroll to the "Sub-work items" section
5. Click the "..." (three-dot) menu next to a sub-issue
6. Read the menu item text

**What the agent sees:** The menu shows **"Remove parent issue"** when the context clearly calls for "Remove sub-issue" or "Unlink sub-issue." The text is backwards.

**Why #7:** This is a subtle, charming bug that shows the agent reads and understands UI copy. The agent will note the semantic mismatch — "I'm looking at a sub-issue's context menu, but it says 'Remove parent issue.'" Good for demonstrating the agent's comprehension, not just its clicking ability.

**Risk:** The menu text might have been fixed since the issue was filed (Sept 2024). The SEED project needs parent-child issue relationships, which the seed data should include.

---

### #8 — [#8514](https://github.com/makeplane/plane/issues/8514) — Valid password rejected by validation

| | |
|---|---|
| **Labels** | 🐛bug, plane |
| **Filed** | 2026-01-09 |
| **Bug class** | form-validation |
| **Confidence** | 🟡 MEDIUM |
| **Step count** | ~8 |
| **Estimated time** | ~45s |

**Reproduction steps for the agent:**
1. Log in to Plane
2. Navigate to Profile (sidebar bottom) → Security
3. Click "Change Password"
4. Enter current password: `qweQWE123!@#`
5. Enter new password: `SecurePassword123!` (meets all stated criteria)
6. Click "Update Password"
7. Observe: "Password validation failed" error

**What the agent sees:** A password that meets every criterion listed in the UI (8+ chars, uppercase, lowercase, number, special char) is rejected.

**Why #8:** Good irony factor — the agent follows the rules exactly and gets punished for it. Fast to reproduce.

**Risk:** ⚠️ **DANGER:** If the bug has been fixed and the password actually changes, the admin account password changes to `SecurePassword123!` and all subsequent demo runs break (they use the old password). Since the bug is that validation *rejects* valid passwords, it should be safe — but this is worth testing in a dry run first.

---

### #9 — [#9124](https://github.com/makeplane/plane/issues/9124) — Collapsible sub-tasks require three clicks to expand

| | |
|---|---|
| **Labels** | 🐛bug, plane |
| **Filed** | 2026-05-24 |
| **Bug class** | ui-interaction |
| **Confidence** | 🟡 MEDIUM |
| **Step count** | ~10 |
| **Estimated time** | ~45s |

**Reproduction steps for the agent:**
1. Log in to Plane
2. Navigate to SEED project → Work Items
3. Open an issue that has nested sub-tasks (sub-tasks with their own sub-tasks)
4. After the page loads, click the expand chevron on a sub-task
5. Observe: nothing happens
6. Click the expand chevron again
7. Observe: nothing happens
8. Click the expand chevron a third time
9. Observe: the sub-tasks finally expand

**What the agent sees:** The expand/collapse chevron ignores the first two clicks and only responds on the third click.

**Why #9:** Visually satisfying — the audience can count the clicks. The agent demonstrates patience and persistence.

**Risk:** The bug is timing-dependent — it only manifests "just after loading the page." The agent might click too quickly (before the state is set up) or too slowly (after the state resolves). Also requires nested sub-tasks in seed data, which may or may not exist at the right depth.

---

### #10 — [#5866](https://github.com/makeplane/plane/issues/5866) — Code block collapses with hashtags

| | |
|---|---|
| **Labels** | 🐛bug, pages |
| **Filed** | 2024-10-18 |
| **Bug class** | editor |
| **Confidence** | 🟢 HIGH |
| **Step count** | ~10 |
| **Estimated time** | ~60s |

**Reproduction steps for the agent:**
1. Log in to Plane
2. Navigate to SEED project → create or open an issue
3. In the description editor, insert a code block
4. Type multiple lines with `#` comment lines:
   ```
   ### FastAPI ###
   ENVIRONMENT="development"
   BASEPATH_PREFIX="/v1"
   ```
5. Save the issue
6. Reopen/reload the issue
7. Observe: hashtags and newlines have been stripped from the code block

**What the agent sees:** The formatted code block has been mangled — `#` comment lines are removed and newlines are collapsed, destroying the formatting.

**Why #10:** Shows the agent interacting with the rich text editor, which is visually interesting. The before/after contrast (clean code vs mangled code) is dramatic.

**Risk:** Creating a code block in the editor might require the agent to use the formatting toolbar or type ``` markers. This is doable but slightly more complex than clicking a button.

---

### #11 — [#8998](https://github.com/makeplane/plane/issues/8998) — Epic name truncated after 10 characters

| | |
|---|---|
| **Labels** | 🐛bug, plane |
| **Filed** | 2026-05-03 |
| **Bug class** | ui-rendering |
| **Confidence** | 🟡 MEDIUM |
| **Step count** | ~12 |
| **Estimated time** | ~60s |

**Reproduction steps for the agent:**
1. Log in to Plane
2. Navigate to SEED project
3. Enable Epics (if not already enabled in project settings)
4. Create an Epic with a long name (e.g., "User Authentication Improvements Q3")
5. Go to Work Items
6. Open the Filter dropdown → Epics
7. Observe: the epic name is truncated after ~10 characters despite plenty of space

**What the agent sees:** The filter dropdown shows a truncated epic name like "User Au..." instead of the full name.

**Risk:** Epics might not be available in Plane Community Edition, or might need to be enabled via a project setting the agent hasn't navigated to before. Multiple setup steps increase failure risk.

---

### #12 — [#8683](https://github.com/makeplane/plane/issues/8683) — Bulk operations with Epic grouping don't save

| | |
|---|---|
| **Labels** | 🐛bug, plane |
| **Filed** | 2026-03-03 |
| **Bug class** | state-persistence |
| **Confidence** | 🟡 MEDIUM |
| **Step count** | ~15 |

**Reproduction:** Group work items by Epic → select multiple → bulk assign module → switch view → "Are you sure you want to leave?" dialog → changes lost.

**Risk:** Many steps, requires Epics and Modules. Complex workflow increases failure probability.

---

### #13 — [#8521](https://github.com/makeplane/plane/issues/8521) — Notifications panel empty

| | |
|---|---|
| **Labels** | 🐛bug, plane |
| **Filed** | 2026-01-09 |
| **Bug class** | ui-rendering |
| **Confidence** | 🟡 MEDIUM |
| **Step count** | ~4 |

**Reproduction:** Click notification bell → see "All (5)" header → no notification content renders.

**Risk:** Requires existing notifications. Seed data may not have pending notifications for the admin user.

---

### #14 — [#9182](https://github.com/makeplane/plane/issues/9182) — Low-contrast close button on Cycles onboarding modal

| | |
|---|---|
| **Labels** | 🐛bug, plane |
| **Filed** | 2026-05-31 |
| **Bug class** | ui-accessibility |
| **Confidence** | 🟡 MEDIUM |
| **Step count** | ~5 |

**Reproduction:** Navigate to Cycles → observe onboarding modal → close (X) button blends into background.

**Risk:** Onboarding modal only appears for first-time visitors. If the workspace is already past onboarding, the modal won't show.

---

### #15 — [#7894](https://github.com/makeplane/plane/issues/7894) — Table layout column header not sticky on horizontal scroll

| | |
|---|---|
| **Labels** | 🐛bug, plane |
| **Filed** | 2025-10-02 |
| **Bug class** | ui-rendering |
| **Confidence** | 🟡 MEDIUM |
| **Step count** | ~6 |

**Reproduction:** Work Items → Table/Spreadsheet layout → scroll right → column headers desync from data.

**Risk:** Needs enough property columns visible to trigger horizontal scrolling at 1920px viewport width. Might need to add extra property columns first.

---

# Part E — Demoted Issues (and Why)

These issues scored high in the algorithmic pass but **cannot be reproduced by the agent** based on first-principles analysis:

| Issue | Algorithmic Score | Title | Why the agent can't reproduce it |
|-------|------------------:|-------|----------------------------------|
| [#8008](https://github.com/makeplane/plane/issues/8008) | 88 | Invitation with different email | Requires **second user account** — agent only has admin@admin.com |
| [#6740](https://github.com/makeplane/plane/issues/6740) | 84 | MinIO/S3 config mismatch | **Config/env variable issue** — no browser manifestation |
| [#5728](https://github.com/makeplane/plane/issues/5728) | 84 | Invalid URL query params | Agent **cannot edit the URL bar** — only interacts with DOM elements |
| [#9158](https://github.com/makeplane/plane/issues/9158) | 82 | dispatch() returns exception | **Backend error** — no UI manifestation visible in browser |
| [#8078](https://github.com/makeplane/plane/issues/8078) | 82 | API container not found | **Docker infrastructure** — not a browser bug |
| [#9172](https://github.com/makeplane/plane/issues/9172) | 79 | Password reset 500 | **API-only** — requires crafted URL with non-existent user ID |
| [#8909](https://github.com/makeplane/plane/issues/8909) | 79 | POST /projects/ missing identifier | **API-only** — no browser path to observe the missing data |
| [#9055](https://github.com/makeplane/plane/issues/9055) | 76 | MCP integration failure | **External service** — Supergrok/connectors not available locally |
| [#7570](https://github.com/makeplane/plane/issues/7570) | 76 | God Mode 403 after update | **Coolify-specific** — not a Plane bug, deployment platform issue |
| [#8567](https://github.com/makeplane/plane/issues/8567) | 74 | CJK fonts in PDF export | Agent **cannot inspect downloaded PDFs** — content goes to disk |
| [#6359](https://github.com/makeplane/plane/issues/6359) | 74 | US timezone offsets wrong | **DST-dependent** — on July 4, US timezones ARE in EDT, offsets are correct |
| [#9084](https://github.com/makeplane/plane/issues/9084) | 61 | Mobile text overlap | **Mobile viewport only** — agent viewport is 1920×1080 desktop |
| [#5485](https://github.com/makeplane/plane/issues/5485) | 64 | Japanese IME submits comment | Agent **cannot use input methods** — browser-use types directly |
| [#8901](https://github.com/makeplane/plane/issues/8901) | 54 | macOS ⌘F not working | **Desktop app only** — agent tests the web app, not Electron/Tauri |
| [#9041](https://github.com/makeplane/plane/issues/9041) | 51 | admin* slug 403s API | Requires **creating new workspace** — risky, changes global state |
| [#9218](https://github.com/makeplane/plane/issues/9218) | 62 | Stored XSS via email template | Requires **email delivery** to see XSS execute |
| [#9001](https://github.com/makeplane/plane/issues/9001) | 69 | plane push creates duplicates | **CLI tool** — `plane push` is a terminal command, not browser |
| [#8988](https://github.com/makeplane/plane/issues/8988) | 69 | Safari requestIdleCallback crash | **Safari-only** — Chrome supports `requestIdleCallback` |
| [#8867](https://github.com/makeplane/plane/issues/8867) | 65 | React hydration error on mobile | **Mobile browser only** — desktop Chrome recovers |

**Key lesson:** Keyword heuristics (presence of "error", "crash", "visible") are unreliable for scoring demo-worthiness. First-principles analysis of agent capabilities is essential.

---

# Part F — Hackathon Demo Recommendation

## Primary Demo Set (recommended order)

| Slot | Issue | Bug | Time | Confidence | Demo Narrative |
|------|-------|-----|------|------------|----------------|
| **Demo 1** | [**#9329**](https://github.com/makeplane/plane/issues/9329) | Title >255 chars → generic error | ~30s | 🟢 HIGH | "Watch the agent type a long title and get a useless error" |
| **Demo 2** | [**#8591**](https://github.com/makeplane/plane/issues/8591) | Deleted states reappear after refresh | ~60s | 🟢 HIGH | "Agent creates a state, deletes it, refreshes — zombie data returns from the dead" |
| **Demo 3** | [**#8770**](https://github.com/makeplane/plane/issues/8770) | Kanban card doesn't move on state change | ~45s | 🟢 HIGH | "Agent changes a card's state, but it stubbornly stays in the wrong column" |

**Total time:** ~2 min 15s  
**All three are 🟢 HIGH confidence**  
**Three different bug classes:** form-validation → state-persistence → ui-state-sync

## Why this order

1. **#9329 first** — Fastest, simplest. Gets the audience oriented. They see "type → submit → error." Success builds confidence.
2. **#8591 second** — Most dramatic. "Create → delete → refresh → it's back." The narrative arc is satisfying. 
3. **#8770 third** — Different visual context (kanban board). Shows the agent works across UI areas, not just forms.

## Backup picks (if any primary fails)

| Backup | Issue | Swap for | Why |
|--------|-------|----------|-----|
| **A** | [#9050](https://github.com/makeplane/plane/issues/9050) — Stickies reappear | #8591 | Same bug class (state-persistence), different area |
| **B** | [#7338](https://github.com/makeplane/plane/issues/7338) — Comment toolbar disabled | #8770 | Fast, visual before/after, 🟢 HIGH confidence |
| **C** | [#5529](https://github.com/makeplane/plane/issues/5529) — Wrong menu text | Any | Ultra-reliable, shows agent reads and comprehends text |

## Pre-demo checklist

- [ ] Plane running on localhost:80 (`docker-compose up`)
- [ ] Chrome open with `--remote-debugging-port=9222`
- [ ] `.env` configured (OPENROUTER_API_KEY, CDP_URL, PLANE credentials)
- [ ] Seed data loaded (SEED project with issues, states, sub-issues)
- [ ] Dry-run `python scripts/drive.py --issue 9329 --dry-run` to verify prompt generation
- [ ] Test one real run before going on stage
