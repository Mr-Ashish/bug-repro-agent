# Bug Reproduction Agent

Autonomously reproduces bugs from GitHub issues in a running local Plane instance.
Built for the Browser-Use Hackathon (July 4, 2026, Bengaluru).

## What this repo does

Given a GitHub issue URL → drives a real browser → reproduces the bug → generates a Playwright test → posts verdict to GitHub.

**This agent is a REPRODUCER, not a fixer.** Verdicts: `REPRODUCED` · `NOT_REPRODUCED` · `INCONCLUSIVE`.

## Key files

| File | Purpose |
|------|---------|
| `scripts/drive.py` | Main reproduction driver — fetches issue, runs browser-use agent, saves artifacts |
| `scripts/generate_playwright.py` | Converts action-log.json into a Playwright regression test |
| `scripts/post_comment.py` | Formats and posts verdict as GitHub issue comment |
| `scripts/seed.py` | Environment readiness checker + seed data populator |
| `.claude/skills/repro-agent/SKILL.md` | Full skill definition — **read this before any reproduction run** |
| `FINAL-DEMO-RANKING.md` | 15 demo-worthy issues ranked by reproducibility confidence |

## How to reproduce a bug

Invoke the skill with a GitHub issue URL:
```
/repro-agent https://github.com/makeplane/plane/issues/<N>
```

The skill (`.claude/skills/repro-agent/SKILL.md`) handles everything:
1. Pre-flight checklist (sync Plane, verify Chrome, seed data)
2. Source code grepping to build `--context` for the browser agent
3. Running `drive.py --post` with the right flags
4. Reviewing the generated Playwright test

## Configuration source of truth

All runtime config lives in **two places**. Never hardcode these values in docs — reference the source.

| Config | Source of truth | How to read |
|--------|----------------|-------------|
| Plane URL, port | `.env` → `PLANE_URL`; default in `scripts/drive.py` `PLANE_URL` | `grep PLANE_URL .env scripts/drive.py` |
| Credentials | `.env` → `PLANE_EMAIL`, `PLANE_PASSWORD` | `grep PLANE_EMAIL .env` |
| Workspace | `.env` → `PLANE_WORKSPACE`; default in `scripts/drive.py` | `grep PLANE_WORKSPACE .env scripts/drive.py` |
| Project | `scripts/seed.py` → `SEED_PROJECT_NAME`, `SEED_PROJECT_ID` | `grep SEED_PROJECT seed.py` |
| CDP port | `scripts/drive.py` → `discover_cdp_url()` default arg | `grep debug_port scripts/drive.py` |
| Browser model | `.env` → `BROWSER_USE_MODEL`; default in `scripts/drive.py` | `grep BROWSER_USE_MODEL .env scripts/drive.py` |
| Max steps | `scripts/drive.py` → `agent.run(max_steps=...)` | `grep max_steps scripts/drive.py` |
| Viewport | `scripts/drive.py` → `BrowserConfig(...)` | `grep viewport scripts/drive.py` |
| Seed data | `scripts/seed.py` → `SEED_STATES`, `SEED_ISSUES` lists | `grep -c "name" scripts/seed.py` in those lists |
| Default repo | `scripts/drive.py` → `DEFAULT_REPO` | `grep DEFAULT_REPO scripts/drive.py` |

## Constraints

- **Pure Python** — no TypeScript/Node.js
- **Any issue** — prompt is built dynamically from the issue body, no hardcoded steps
- **Plane target** — URL, workspace, project configured in `.env` (see table above)
- **Chrome CDP** — port configured in `scripts/drive.py` `discover_cdp_url()`
- **OpenRouter** — API key in `.env`
- **Max steps** — configured in `scripts/drive.py` `agent.run()`

## Architecture (4 layers)

```
Human → Grok (meta-agent, reads SKILL.md) → drive.py (infra) → browser-use Agent (bug reasoning)
```

The meta-agent's job:
1. Read the SKILL.md
2. Run pre-flight checks
3. Read Plane source code (`plane/apps/web/`, NOT `plane/web/`) to discover URL patterns and UI structure
4. Pass discoveries via `--context` flag to `drive.py`
5. Run `drive.py --url <issue-url> --post`
6. Review artifacts and generated Playwright test

## Output

All artifacts go to `reproductions/<issue-number>/` — screenshots, action log, GIF, verdict, Playwright test, GitHub comment.

## Do NOT

- Fix bugs — only reproduce them
- Debug Docker/Caddyfile/docker-compose — if infra isn't ready in 60s, stop
- Hardcode issue-specific logic — everything is driven by the issue body
- Use `plane/web/` — the correct path is `plane/apps/web/`

## Documentation staleness rule

**When you encounter a hardcoded value in any `.md` file that duplicates config from `.env` or a script, fix it immediately:**

1. Replace the hardcoded value with a reference to the source-of-truth file and variable (see table above)
2. For pre-flight commands that need actual values (e.g., `curl` URLs), read `.env` or the script default at runtime — don't copy-paste the value
3. If you must show a value as an example, mark it clearly: `(default: X — see scripts/drive.py)`
4. After fixing, verify no other `.md` file has the same stale value: `grep -r "<old_value>" *.md .claude/`

**This is an automatic task.** Whenever you read or edit any markdown file and notice a value that could drift from its source, fix it in the same commit.