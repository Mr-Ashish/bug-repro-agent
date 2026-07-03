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

## Constraints

- **Pure Python** — no TypeScript/Node.js
- **Any issue** — prompt is built dynamically from the issue body, no hardcoded steps
- **Plane target** — app runs at `localhost:80`, workspace `plane-dev`, project `SEED`
- **Chrome CDP** — browser-use connects via `localhost:9222`
- **OpenRouter** — LLM calls go through OpenRouter (API key in `.env`)
- **Max 50 steps** — browser agent budget per run

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