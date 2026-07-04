# Feature: Post Rich Reproduction Report to GitHub Issue

> **Priority:** P0 — required for hackathon demo (July 4, 2026)
> **Depends on:** A successful `drive.py` run that produces artifacts in `reproductions/<issue>/`
>
> **Status as of July 4 2026 (evening):**
> | Area | Status |
> |------|--------|
> | `post_comment.py` exists | ✅ Done — but has dict-format bug |
> | `drive.py --post` wiring | ⚠️ Uses INLINE simple version, not `post_comment.py` |
> | GIF/screenshot upload | 🔴 Not implemented — no images in comment |
> | Step trace table | 🔴 Broken — `extract_action_type()` regex fails on dict-format actions |
> | Playwright test gen | ✅ Fixed (dict-format fix in `a1587d3`) — needs E2E verification |
> | Meta-agent artifact verification | 🔴 Missing — doesn't verify all artifacts exist |

---

## Context — What This Project Is

**repro-agent** is a hackathon project for the Browser-Use Hackathon (July 4, 2026, Bengaluru).

It autonomously reproduces bugs from GitHub issues in a running [Plane](https://github.com/makeplane/plane) instance using [browser-use](https://github.com/browser-use/browser-use) (Python agent on Playwright) and saves evidence artifacts.

> **Updated:** Reflects pure-Python architecture. No TypeScript/Node.js layer.

### Architecture

Python `scripts/drive.py` runs a browser-use agent (Claude Sonnet 4 via OpenRouter) that drives Chrome via CDP, reproduces the bug, saves artifacts to `reproductions/<issue>/`.

### Existing artifact bundle (produced by `drive.py`)

After a successful run, `reproductions/<issue>/` contains:

```
reproductions/9329/
├── issue.json               # fetched issue (title, body, URL)
├── task-prompt.txt           # full prompt sent to agent
├── action-log.json          # every agent step (thought, actions, result, URL) — NOW DICT FORMAT
├── evidence-*.png           # screenshots at each step
├── agent-run.gif            # animated GIF of browser session (browser-use built-in)
├── conversation.json        # full LLM conversation log
├── verdict.md               # parsed verdict + run stats
├── error.txt                # written on crash/timeout (if any)
├── github-comment.md        # generated GitHub comment (from post_comment.py)
├── test_<N>.py              # auto-generated Playwright regression test
└── traces/
    └── full-trace.json      # complete browser-use agent history
```

### Key files

| File | What it does |
|------|-------------|
| `scripts/drive.py` | Main driver — fetches issue, runs browser-use agent, saves all artifacts |
| `scripts/post_comment.py` | Reads artifacts, generates + posts GitHub comment (standalone) |
| `scripts/generate_playwright.py` | Converts action-log.json → Playwright regression test |
| `ARCHITECTURE.md` | Full architecture doc (merged from HLD.md + DESIGN.md) |

---

## Feature Request

### What

After a successful reproduction run, generate a **rich GitHub issue comment** and post it to the source issue using `gh issue comment`. The comment should contain:

1. **Verdict header** — reproduced/not reproduced/inconclusive, summary, run stats
2. **Agent-run GIF** — embedded animated GIF showing the full browser session
3. **Step-by-step action table** — every action the agent took, formatted as a Markdown table with agent thoughts
4. **Key evidence screenshot** — the critical frame showing the bug
5. **Regression test snippet** — link to or inline the generated Playwright test
6. **Footer** — tool attribution

> **Current state:** Items 1 and 6 work. Items 2-5 are broken or missing (see status table above).

### Why

The demo currently ends with artifacts sitting in a local folder. This feature closes the loop: the agent reports back to the GitHub issue where the bug was filed. The person who reported the bug gets a complete QA investigation — video, steps, and evidence — without a human touching it.

This is the climactic "kicker" beat in the hackathon demo. The audience sees the GitHub issue page (which started with a text report from a user) now has a comment from the agent with a GIF, a structured investigation, and step-by-step evidence. The response is richer than the report.

### Demo flow

1. `python scripts/drive.py --issue 9329 --post` → agent reproduces the bug, saves artifacts, posts rich comment
2. Refresh the issue page → the comment renders with verdict, GIF, step table, evidence

---

## Detailed Specification

### 1. Script: `scripts/post_comment.py` — ✅ EXISTS, NEEDS FIXES

The script exists (270 lines) and does:
1. ✅ Reads artifacts from `reproductions/<issue>/`
2. ✅ Reads optional `image-urls.json` (but nothing ever creates this file)
3. ⚠️ Generates Markdown body — step table is **broken** (dict-format actions)
4. ✅ Posts via `gh issue comment`

**But `drive.py --post` doesn't call it.** Instead, `drive.py` uses an inline `post_github_comment()` (lines 376-450) that produces a much simpler comment without step table, GIF, or screenshots.

**Fix needed:** Replace `drive.py`'s inline `post_github_comment()` with a call to `post_comment.py`.

**CLI interface (already works):**
```bash
python scripts/post_comment.py --issue 9329
python scripts/post_comment.py --issue 9329 --dry-run    # generate only
python scripts/post_comment.py --issue 9329 --repo user/fork
```

### 2. Comment body format

The generated Markdown must render correctly on GitHub. Here is the exact template:

````markdown
### 🔍 Reproduction Report — `repro-agent`

**Verdict:** ✅ REPRODUCED
**Summary:** Generic "Some error occurred" toast appears when creating a work item with 256+ character title. No character limit validation, no specific error message.
**Run time:** 64.6s  ·  **Steps:** 4  ·  **Agent:** browser-use + Claude Sonnet 4 via OpenRouter

---

#### 🎬 Agent Run

![agent-run](<GIF_URL>)

> The GIF above shows the full autonomous browser session — login, navigation, reproduction steps, and bug observation.

---

#### 📋 Steps Taken

| # | Action | Detail | Agent Thought | Result |
|---|--------|--------|---------------|--------|
| 1 | Navigate | Plane login page | "I see a login form..." | ✅ Login form visible |
| 2 | Type | Email: `admin@admin.com` | "Need to enter credentials" | ✅ Entered |
| 3 | Click | "Continue" button | "Submitting email" | ✅ Password field appeared |
| 4 | Type | Password: `••••••` | "Entering password" | ✅ Entered |
| 5 | Click | "Go to workspace" | "Logging in" | ✅ Dashboard loaded |
| 6 | Navigate | SEED project → Issues | "Going to project issues" | ✅ Work items visible |
| 7 | Click | "Add work item" | "Creating new item" | ✅ Modal opened |
| 8 | Type | 256-character title | "Entering long title to trigger bug" | ✅ Entered |
| 9 | Press | Enter to submit | "Submitting" | ⚠️ Error toast appeared |
| 10 | Observe | Error message text | "Checking error details" | 🔴 **"Some error occurred"** — generic, no char limit |

---

#### 🖼️ Evidence

![error-toast](<SCREENSHOT_URL>)

---

#### 🧪 Regression Test

<details>
<summary>Auto-generated Playwright test (click to expand)</summary>

```python
# reproductions/9329/test_9329.py — auto-generated by repro-agent
# Run: pytest test_9329.py -v --headed
def test_issue_9329(page):
    # ... (abbreviated — full test in artifact bundle)
    pass
```

</details>

---

<sub>🤖 Generated by <a href="https://github.com/Mr-Ashish/bug-repro-agent"><b>repro-agent</b></a> · browser-use + Claude Sonnet 4 via OpenRouter · <a href="https://github.com/Mr-Ashish/bug-repro-agent/tree/main/reproductions/9329">Full artifacts</a></sub>
````

### 3. Image hosting for the comment — 🔴 NOT IMPLEMENTED

GitHub Markdown comments need publicly accessible URLs for images. Three approaches:

#### Option A — Commit artifacts to repo + raw URLs (RECOMMENDED — simplest, fully automated)

> **This is the right approach for the hackathon.** No external service, no API tokens, fully deterministic.

1. After `drive.py` saves artifacts, `post_comment.py` does:
   ```bash
   git add reproductions/9329/agent-run.gif reproductions/9329/evidence-*.png
   git commit -m "repro: #9329 artifacts"
   git push
   ```
2. Build URLs: `https://raw.githubusercontent.com/Mr-Ashish/bug-repro-agent/main/reproductions/9329/agent-run.gif`
3. Embed in the Markdown body
4. Post the comment

**Why this over the others:**
- Zero external dependencies
- GIF and screenshots permanently available (they're in the repo)
- `git push` is a single `subprocess.run()` call
- Raw URLs work immediately after push

#### Option B — GitHub upload API (future improvement)

Use the GitHub upload API to upload images and get `user-images.githubusercontent.com` URLs. This is what GitHub's web UI does when you drag-drop images. More complex, requires undocumented API.

#### Option C — Pre-upload to `image-urls.json` (original plan — too manual)

Requires manual upload before posting. Defeats the purpose of automation.

### 4. Building the step table from `action-log.json` — 🔴 BROKEN

The `action-log.json` format **changed** in commit `f41b554`. Actions are now **dicts** (from `model_dump()`), not strings:

```json
{
  "step": 1,
  "timestamp": "2026-07-04T10:30:00",
  "thought": "I see a login form with email and password fields...",
  "actions": [{"click": {"index": 1103}}, {"input_text": {"index": 3547, "text": "admin@admin.com"}}],
  "results": [
    {
      "extracted_content": "Login form visible",
      "error": null,
      "is_done": false
    }
  ],
  "url": "http://localhost/"
}
```

`generate_playwright.py` was fixed for this in commit `a1587d3` (handles both dict and string formats). **`post_comment.py`'s `extract_action_type()` still uses the old regex approach** and will break on dict-format actions.

**Fix needed:** Apply the same dict-handling pattern from `generate_playwright.py` to `post_comment.py`'s `extract_action_type()`.

The step table should also include the **agent's thought** as a column — this is the most valuable part for the person reading the issue. The agent's reasoning about what it's seeing is unique evidence.

Logic for result emoji:
- `✅` if no error and not done
- `⚠️` if the step is where the bug manifests
- `🔴` if it's the final observation confirming the bug
- `❌` if error occurred
- `🏁` if `is_done` is true

### 5. Cost calculation

The cost can be estimated from:
- `conversation.json` — count input/output tokens (if available in the conversation metadata)
- Or hardcode an approximate per-run cost based on the model pricing (Claude Sonnet 4 via OpenRouter ≈ $3/1M input, $15/1M output)
- For the hackathon, an approximate number (e.g., "$0.14") from a real run is fine

### 6. Run stats

Pull from `verdict.md` which already contains `history.total_duration_seconds()` and `history.number_of_steps()`, or from `action-log.json` (length of array, first/last timestamp).

---

## Implementation Steps (Revised — what's left)

> Steps 1, 2, 5, 6 are done. Steps 3, 4, 7, 8, 9 are the remaining work.

1. ~~**Create `scripts/post_comment.py`**~~ — ✅ EXISTS (270 lines)
2. ~~**Add the comment template**~~ — ✅ EXISTS (needs enhancement for thoughts + regression test)
3. 🔴 **Fix `extract_action_type()` in `post_comment.py`** — handle dict-format actions (same pattern as `generate_playwright.py` fix)
4. 🔴 **Implement image upload** — Option A: `git add` + `git push` + raw URLs. Add `upload_artifacts()` function to `post_comment.py`
5. ~~**Add password masking**~~ — ✅ DONE
6. ~~**Shell out to `gh issue comment`**~~ — ✅ DONE
7. 🔴 **Wire `post_comment.py` into `drive.py`** — replace inline `post_github_comment()` with subprocess call to `post_comment.py`
8. 🟡 **Add agent thought column** to step table — the agent's reasoning is the most valuable evidence
9. 🟡 **Add regression test section** — embed the generated Playwright test (abbreviated) in the comment
10. 🟡 **Add SKILL.md instruction** — meta-agent should verify: Playwright test generated + comment posted + all artifacts present

---

## Constraints

- **Python only** — pure Python, no TypeScript/Node.js dependencies
- **`gh` CLI required** — the script uses `gh issue comment`, so `gh` must be installed and authenticated
- **No new dependencies** — use stdlib (`json`, `subprocess`, `pathlib`, `re`) and `dotenv` (already in requirements)
- **Password masking is mandatory** — never embed real passwords in a GitHub comment, even on a demo repo
- **The script must work standalone** — it reads from the artifacts directory, it doesn't depend on a prior `drive.py` process being in memory
- **Repo targeting** — the `--repo` flag for `gh issue comment` should default to `makeplane/plane` but be overridable via env var `GITHUB_REPO` for testing against forks
- **Sensitive data in actions** — if any `actions` entries in `action-log.json` contain the password string, mask those too in the step table

---

## Acceptance Criteria

1. ✅ `python scripts/post_comment.py --issue 9329` generates a Markdown file at `reproductions/9329/github-comment.md`
2. 🔴 The generated Markdown renders correctly on GitHub **with embedded GIF and screenshots**
3. 🔴 The comment contains: verdict header, **GIF**, step table **with agent thoughts**, evidence screenshot, **regression test snippet**, footer
4. ✅ The script posts the comment via `gh issue comment` (with a `--dry-run` flag)
5. ✅ Passwords are masked everywhere in the output
6. ✅ The script exits cleanly with an error message if `reproductions/<issue>/` doesn't exist
7. 🔴 **`drive.py --post` calls `post_comment.py`** instead of the inline simplified version
8. 🔴 **Images are committed and pushed** before posting, so GIF/screenshots have public URLs
9. 🟡 **Meta-agent verifies** all artifacts exist after run (Playwright test, comment, screenshots, GIF)

---

## Files to Modify

| File | Change | Status |
|------|--------|--------|
| `scripts/post_comment.py` | Fix dict-format actions, add image upload, add thought column, add regression test section | 🔴 TODO |
| `scripts/drive.py` | Replace inline `post_github_comment()` with subprocess call to `post_comment.py` | 🔴 TODO |
| `.claude/skills/repro-agent/SKILL.md` | Add artifact verification checklist for meta-agent | 🟡 TODO |

---

## Example Usage

```bash
# After a successful drive run:
python scripts/drive.py --issue 9329

# Generate the comment (dry run — just creates the markdown file):
python scripts/post_comment.py --issue 9329 --dry-run

# Preview what it looks like:
cat reproductions/9329/github-comment.md

# Post it for real:
python scripts/post_comment.py --issue 9329

# Or against a test fork:
GITHUB_REPO=your-username/plane-fork python scripts/post_comment.py --issue 9329
```

---

## Demo Day Flow (Revised — Fully Automated)

The entire flow should be **one command** → rich comment appears on GitHub:

```bash
python scripts/drive.py --issue 9329 --post
```

What happens:
1. `drive.py` reproduces the bug → saves all artifacts
2. `drive.py` generates Playwright test → `reproductions/9329/test_9329.py`
3. `drive.py` calls `post_comment.py` which:
   a. Reads all artifacts (verdict, action-log, screenshots, test)
   b. Commits GIF + key screenshot to repo, pushes
   c. Builds raw.githubusercontent.com URLs for images
   d. Generates rich Markdown with GIF, step table, evidence, regression test
   e. Posts to GitHub issue via `gh issue comment`
4. Refresh the issue page → **rich report with video, steps, evidence, test**

No manual `image-urls.json`. No pre-upload. Fully automated.