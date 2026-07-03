# Feature: Post Rich Reproduction Report to GitHub Issue

> **Priority:** P0 — required for hackathon demo (July 4, 2026)
> **Depends on:** A successful `drive.py` run that produces artifacts in `reproductions/<issue>/`

---

## Context — What This Project Is

**repro-agent** is a hackathon project for the Browser-Use Hackathon (July 4, 2026, Bengaluru).

It autonomously reproduces bugs from GitHub issues in a running [Plane](https://github.com/makeplane/plane) instance using [browser-use](https://github.com/browser-use/browser-use) (Python agent on Playwright), then emits deterministic Playwright tests + evidence artifacts.

### Architecture (two phases)

- **Phase 1 — Author:** Python `scripts/drive.py` runs a browser-use agent (Claude Sonnet 4 via OpenRouter) that drives Chrome via CDP, reproduces the bug, saves artifacts to `reproductions/<issue>/`.
- **Phase 2 — Replay:** The emitted `reproductions/<issue>/repro.spec.ts` is a standard Playwright test. No AI, no browser-use. Runs with `npx playwright test`.

### Existing artifact bundle (produced by `drive.py`)

After a successful run, `reproductions/<issue>/` contains:

```
reproductions/9329/
├── repro-plan.json          # structured reproduction plan
├── action-log.json          # every agent step (thought, actions, result, URL)
├── repro.spec.ts            # deterministic Playwright test
├── traces/
│   └── full-trace.json      # complete browser-use agent history
├── conversation.json        # full LLM conversation log
├── evidence-*.png           # screenshots at each step
├── agent-run.gif            # animated GIF of browser session
└── verdict.md               # human-readable verdict (current format)
```

### Key files to understand

| File | What it does | Language |
|------|-------------|----------|
| `scripts/drive.py` | Main driver — runs browser-use agent, saves all artifacts | Python |
| `lib/artifact-emitter.ts` | Generates `repro.spec.ts` and `verdict.md` from action log | TypeScript |
| `lib/plane-adapter.ts` | Plane URLs, credentials, nav patterns | TypeScript |
| `lib/plane_config.py` | Same as above, Python version | Python |
| `lib/repro-plan.schema.ts` | TypeScript types for `ReproPlan`, `ActionLogEntry`, `Verdict` | TypeScript |
| `HLD.md` | Full architecture doc | — |
| `DESIGN.md` | Core design principle (author vs replay) | — |

---

## Feature Request

### What

After a successful reproduction run, generate a **rich GitHub issue comment** and post it to the source issue using `gh issue comment`. The comment should contain:

1. **Verdict header** — reproduced/not reproduced/inconclusive, confidence, bug class, run stats
2. **Agent-run GIF** — embedded animated GIF showing the full browser session
3. **Step-by-step action table** — every action the agent took, formatted as a Markdown table
4. **Key evidence screenshot** — the critical frame (e.g., the error toast for #9329)
5. **Regression test code block** — the `repro.spec.ts` content as a syntax-highlighted TypeScript block
6. **Footer** — tool attribution, links to full trace and action log

### Why

The demo currently ends with artifacts sitting in a local folder. This feature closes the loop: the agent reports back to the GitHub issue where the bug was filed. The person who reported the bug gets a complete QA investigation — video, steps, evidence, and a regression test — without a human touching it.

This is the climactic "kicker" beat in the hackathon demo. The audience sees the GitHub issue page (which started with a text report from a user) now has a comment from the agent with a GIF, a structured investigation, and executable code. The response is richer than the report.

### Demo flow

1. `python scripts/drive.py --issue 9329` → agent reproduces the bug, saves artifacts
2. `npx playwright test reproductions/9329/repro.spec.ts` → deterministic replay works
3. **NEW:** Agent posts the reproduction report to the GitHub issue as a comment
4. Refresh the issue page → the comment renders with GIF, table, code block

---

## Detailed Specification

### 1. New script: `scripts/post_comment.py`

Create a Python script that:

1. Reads artifacts from `reproductions/<issue>/`
2. Uploads images (GIF + key screenshot) to get publicly accessible URLs
3. Generates a formatted Markdown comment body
4. Posts it via `gh issue comment <number> --repo makeplane/plane --body-file <path>`

**CLI interface:**
```bash
python scripts/post_comment.py --issue 9329
```

**Or add npm script:**
```json
{
  "report:9329": "python scripts/post_comment.py --issue 9329"
}
```

### 2. Comment body format

The generated Markdown must render correctly on GitHub. Here is the exact template:

````markdown
### 🔍 Reproduction Report — `repro-agent`

**Verdict:** ✅ REPRODUCED
**Confidence:** high
**Bug class:** form-validation
**Run time:** 87.3s  ·  **Steps:** 14  ·  **Cost:** $0.14

---

#### Agent Run

![agent-run](<GIF_URL>)

---

#### Steps Taken

| # | Action | Detail | Result |
|---|--------|--------|--------|
| 1 | Navigate | Plane login page | ✅ Login form visible |
| 2 | Type | Email: `admin@admin.com` | ✅ Entered |
| 3 | Click | "Continue" button | ✅ Password field appeared |
| 4 | Type | Password: `••••••` | ✅ Entered |
| 5 | Click | "Go to workspace" | ✅ Dashboard loaded |
| 6 | Navigate | SEED project → Issues | ✅ Work items visible |
| 7 | Click | "Add work item" | ✅ Modal opened |
| 8 | Type | 256-character title (`AAAA...`) | ✅ Entered |
| 9 | Press | Enter to submit | ⚠️ Error toast appeared |
| 10 | Observe | Error message text | 🔴 **"Some error occurred"** — generic, no character limit mentioned |

---

#### Evidence

![error-toast](<SCREENSHOT_URL>)

---

#### Regression Test

```typescript
test('reproduce #9329: 255+ char title shows generic error', async ({ page }) => {
  await page.goto('/');
  await page.fill('input[name="email"]', 'admin@admin.com');
  await page.click('button:has-text("Continue")');
  await page.fill('input[type="password"]', '***');
  await page.click('button:has-text("Go to workspace")');
  await page.waitForURL('**/plane-dev/**');
  // ... reproduction steps ...
});
```

---

<sub>Generated by <b>repro-agent</b> · browser-use + Claude Sonnet 4 via OpenRouter · <a href="<TRACE_URL>">full trace</a> · <a href="<LOG_URL>">action log</a></sub>
````

### 3. Image hosting for the comment

GitHub Markdown comments need publicly accessible URLs for images. Three approaches, in order of preference for the hackathon:

#### Option A — Pre-upload before demo (recommended for hackathon day)

1. After a successful `drive.py` run, manually upload `agent-run.gif` and the key `evidence-*.png` to a GitHub repo, gist, or any image host
2. Store the URLs in a file (e.g., `reproductions/9329/image-urls.json`)
3. `post_comment.py` reads these URLs when generating the comment body

This is the safest path for demo day — no live uploading, no network risk.

#### Option B — Upload via GitHub API (preferred for real implementation)

Use the GitHub upload API to upload images and get `user-images.githubusercontent.com` URLs. This is what GitHub's web UI does when you drag-drop images into a comment box. Requires:

1. Upload the GIF and screenshot via the GitHub upload endpoint
2. Parse the returned URL
3. Embed in the Markdown body

This automates the full flow but adds network dependency.

#### Option C — Commit artifacts to repo and use raw URLs

1. `git add reproductions/9329/agent-run.gif reproductions/9329/evidence-09.png`
2. `git commit -m "repro: #9329 artifacts"`
3. `git push`
4. Reference via `https://raw.githubusercontent.com/<owner>/<repo>/main/reproductions/9329/agent-run.gif`

Works, but requires a commit+push before posting the comment. Heavier.

### 4. Building the step table from `action-log.json`

The `action-log.json` file (written by `drive.py`) has this structure per step:

```json
{
  "step": 1,
  "timestamp": "2026-07-04T10:30:00",
  "thought": "I see a login form with email and password fields...",
  "actions": ["click_element(selector='input[name=email]')", "input_text(text='admin@admin.com')"],
  "results": [
    {
      "extracted_content": "Login form visible",
      "error": null,
      "is_done": false
    }
  ],
  "url": "http://localhost:3000/"
}
```

The script must transform this into the Markdown table format. Logic:

1. Parse each step from `action-log.json`
2. Extract the primary action type from the `actions` array (click, type, navigate, etc.)
3. Extract a human-readable detail from the action parameters
4. Determine the result emoji:
   - `✅` if no error and not done
   - `⚠️` if the step is where the bug manifests
   - `🔴` if it's the final observation confirming the bug
   - `❌` if error occurred
5. Pull the result text from `results[0].extracted_content`

For the hackathon, it's acceptable to use heuristics or even have per-issue formatting logic (like `drive.py` already does for verdict generation). Generalization can come later.

### 5. Reading the Playwright test for the code block

Read `reproductions/<issue>/repro.spec.ts` and embed it as a fenced TypeScript code block. Mask the password (replace the actual password with `***`).

### 6. Cost calculation

The cost can be estimated from:
- `conversation.json` — count input/output tokens (if available in the conversation metadata)
- Or hardcode an approximate per-run cost based on the model pricing (Claude Sonnet 4 via OpenRouter ≈ $3/1M input, $15/1M output)
- For the hackathon, an approximate number (e.g., "$0.14") from a real run is fine

### 7. Run stats

Pull from `action-log.json`:
- **Steps:** length of the array
- **Duration:** difference between first and last timestamp
- Or from the verdict.md which already contains `history.total_duration_seconds()` and `history.number_of_steps()`

---

## Implementation Steps

1. **Create `scripts/post_comment.py`** — new Python script
2. **Add the comment template** — Markdown string with placeholders for verdict, GIF URL, step table, screenshot URL, test code, stats
3. **Add `action-log.json` → step table parser** — transforms raw action log into the `| # | Action | Detail | Result |` format
4. **Add image URL resolution** — reads URLs from `reproductions/<issue>/image-urls.json` (Option A) or uploads via API (Option B)
5. **Add password masking** — when embedding `repro.spec.ts`, replace real password with `***`
6. **Shell out to `gh issue comment`** — use `subprocess.run()` to post
7. **Add npm scripts** in `package.json`:
   ```json
   {
     "report": "python scripts/post_comment.py --issue 9329",
     "report:9329": "python scripts/post_comment.py --issue 9329",
     "report:9050": "python scripts/post_comment.py --issue 9050",
     "report:9124": "python scripts/post_comment.py --issue 9124"
   }
   ```
8. **Test against a fork** first — don't post to the real `makeplane/plane` issue until demo day

---

## Constraints

- **Python only** — this script is part of the Python side of the codebase (alongside `drive.py`), not the TypeScript side
- **`gh` CLI required** — the script uses `gh issue comment`, so `gh` must be installed and authenticated
- **No new dependencies** — use stdlib (`json`, `subprocess`, `pathlib`, `re`) and `dotenv` (already in requirements)
- **Password masking is mandatory** — never embed real passwords in a GitHub comment, even on a demo repo
- **The script must work standalone** — it reads from the artifacts directory, it doesn't depend on a prior `drive.py` process being in memory
- **Repo targeting** — the `--repo` flag for `gh issue comment` should default to `makeplane/plane` but be overridable via env var `GITHUB_REPO` for testing against forks
- **Sensitive data in actions** — if any `actions` entries in `action-log.json` contain the password string, mask those too in the step table

---

## Acceptance Criteria

1. `python scripts/post_comment.py --issue 9329` generates a Markdown file at `reproductions/9329/github-comment.md`
2. The generated Markdown renders correctly on GitHub (test by pasting into any issue comment box)
3. The comment contains: verdict header, GIF (via URL), step table (from action log), evidence screenshot (via URL), Playwright test code block (with masked password), footer
4. The script posts the comment via `gh issue comment` (with a `--dry-run` flag that only generates the file without posting)
5. Passwords are masked everywhere in the output
6. The script exits cleanly with an error message if `reproductions/<issue>/` doesn't exist or is missing required files

---

## Files to Create

| File | Purpose |
|------|---------|
| `scripts/post_comment.py` | Main script — generates and posts the GitHub comment |

## Files to Modify

| File | Change |
|------|--------|
| `package.json` | Add `report`, `report:9329`, `report:9050`, `report:9124` npm scripts |
| `HLD.md` | Add a REPORT phase after EMIT in the architecture section |
| `SKILL.md` (`.claude/skills/repro-agent/SKILL.md`) | Add REPORT phase to the phase table |

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

## Demo Day Preparation

Before the hackathon demo:

1. Run `drive.py` for issue #9329 — get a clean successful run
2. Upload `agent-run.gif` and the key evidence screenshot to a persistent URL
3. Create `reproductions/9329/image-urls.json`:
   ```json
   {
     "gif": "https://raw.githubusercontent.com/..../agent-run.gif",
     "screenshot": "https://raw.githubusercontent.com/..../evidence-09.png"
   }
   ```
4. Run `post_comment.py --dry-run` and verify the Markdown renders on GitHub
5. On demo day: run `post_comment.py` live (posts in <2 seconds), refresh the issue page