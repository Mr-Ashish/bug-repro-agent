# Bug Reproduction Agent

Reproduce bugs from GitHub issues in a running local Plane instance via browser automation.

## Invoke

```
/repro-agent https://github.com/makeplane/plane/issues/<N>
```

Read `.claude/skills/repro-agent/SKILL.md` first — it has the full pre-flight checklist, context-building workflow, and `drive.py` usage.

## Key files

| File | Purpose |
|---|---|
| `scripts/drive.py` | Main driver — fetches issue, runs browser-use agent, saves artifacts |
| `scripts/seed.py` | Verifies Plane readiness + populates seed data |
| `scripts/generate_playwright.py` | Converts action log → Playwright test |
| `scripts/post_comment.py` | Posts verdict to GitHub issue |
| `.claude/skills/repro-agent/SKILL.md` | **Full skill definition — read before any run** |
| `ARCHITECTURE.md` | System design, sequence diagram, layer ownership |
| `FINAL-DEMO-RANKING.md` | 15 demo-worthy issues ranked by confidence (human reference — don't read during runs) |

## Architecture

```
Human → Grok (reads SKILL.md) → drive.py (infra) → browser-use Agent (bug reasoning)
```

## Config

All config lives in `.env` with defaults in `scripts/drive.py` and `scripts/seed.py`. To see current defaults:
```bash
grep -n 'PLANE_URL\|MODEL\|max_steps\|viewport\|DEFAULT_REPO\|PLANE_EMAIL\|PLANE_WORKSPACE' scripts/drive.py
```

## Rules

- **Reproducer, not fixer.** Verdicts: `REPRODUCED` · `NOT_REPRODUCED` · `INCONCLUSIVE`. Never "FIXED".
- **Pure Python.** No TypeScript/Node.js.
- **No hardcoded issues.** Prompt is built dynamically from the issue body.
- **Plane source path:** `plane/apps/web/`, NOT `plane/web/`.
- **Infra time limit:** If Plane isn't ready in 60s, stop. Don't debug Docker/Caddyfile.
- **No stale docs.** When editing `.md` files, don't hardcode config values (ports, creds, viewport sizes). Point to `.env` or `scripts/*.py` instead. Verify: `grep -rn 'localhost:80\|admin@admin\|qweQWE\|plane-dev' *.md .claude/`