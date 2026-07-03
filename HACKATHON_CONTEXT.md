# Hackathon Context — Browser-Use Hackathon

> **Date:** Saturday, July 4, 2026 (TOMORROW)
> **Time:** 10:00 AM – 5:00 PM IST (7 hours to build)
> **Venue:** Techspace HSR Layout 2743, Bengaluru
> **Hosted by:** HSR FC / Perch Club / Skill Engineers
> **Team size:** 1–4

---

## Our Track

**🧪 QA and Web Testing:**
> Autonomous exploratory testing, self-healing E2E flows, **bug reproduction from a plain-English description.**

---

## Judging Criteria (100 points)

| Criterion | Weight | What Matters |
|---|---|---|
| 🟢 **Live reliability** | 30 pts | Does it actually complete the task on stage? |
| 💡 **Usefulness** | 25 pts | Is it a real problem? |
| 🧠 **Technical depth** | 20 pts | How sophisticated is the approach? |
| ✨ **Creativity** | 15 pts | Novel approach? |
| 🎤 **Demo & storytelling** | 10 pts | Presentation quality |

**Hard rule:** Demo runs LIVE or on a screen recording of a real run. Browser agents are flaky by nature — they reward teams that handle flakiness gracefully.

---

## Allowed Stack

- **Browser-Use** ← primary tool for the hackathon
- Stagehand / Browserbase
- Playwright
- Codex
- Anthropic Computer Use
- Bring your own keys

---

## Our Pitch (QA Track)

**"Point a browser agent at a GitHub issue, and watch it reproduce the bug — live."**

- Input: A GitHub issue URL from Plane (real open-source project)
- Agent reads the issue, extracts steps to reproduce
- Boots the app (Plane is running locally via docker-compose)
- Logs in, navigates, performs the steps
- Captures video/screenshot evidence
- Reports: "Reproduced ✅" or "Could not reproduce ❌" with evidence

---

## Target App

**[Plane](https://github.com/makeplane/plane)** — open-source project management (Jira alternative)
- **Stack:** Next.js + Django + PostgreSQL + Redis + RabbitMQ + MinIO
- **Local clone:** `~/bug-repro-agent/plane/` (being set up by parallel Claude Code session)
- **Dev compose:** `docker-compose-local.yml` boots all 6+ services

---

## What This Means for Design

1. **Browser-Use is the driver** (not Stagehand/Playwright directly — Browser-Use wraps those)
2. **Visual impact matters** — judges need to see the browser clicking around
3. **Reliability is 30% of score** — we need graceful failure handling, not just happy path
4. **7 hours to build** — scope down HARD
5. **Pre-seed the app** — Plane should be running + populated with test data BEFORE the hackathon starts
6. **Pick 3-5 bugs max** — nail those, don't try to generalize

---

## Prior Art: ERPNext Bug QA Agent

**Location:** `/Users/ashishmishra/Documents/experimentation/browser-use-hackathon/bug-qa-agent/`

We already built a working bug reproduction agent for ERPNext. The architecture is ~80% reusable:

### Architecture (from prior build)

```
CLI (click) → Orchestrator → Browser-Use Session → Agent Loop (GPT-4o)
                                                  ↓ tools ↓
                                            [Stagehand act/extract/observe]
                                            [mark_reproduced / mark_not_reproduced]
                                            [capture_evidence]
                                                  ↓
                                            Judge (Claude Sonnet via OpenRouter)
                                                  ↓
                                            Report (report.md + trace.json + artifacts/)
```

### What We Reuse (No Changes)

| Component | File |
|---|---|
| CLI entry point | `cli.py` |
| Orchestrator pipeline | `orchestrator.py` |
| Browser-Use launcher | `browser_launcher.py` |
| Stagehand HTTP client | `stagehand_client.py` |
| Repro verdict tools | `tools/repro.py` |
| Test verdict tools | `tools/test.py` |
| Stagehand agent tools | `tools/stagehand_tools.py` |
| Evidence collector | `evidence/collector.py` |
| Judge (OpenRouter) | `judge/openrouter_judge.py` |
| Report generator | `report/generator.py` |
| Trace framework | `trace/models.py`, `trace/collector.py` |
| Batch runner | `scripts/run_all_scenarios.py` |

### What We Replace (Plane-specific)

| Component | Adaptation |
|---|---|
| `config.py` | `erpnext_url` → `plane_url`, credentials |
| `subprocess_manager.py` | ERPNext health check → Plane docker-compose health |
| `prompts/repro_system.md` | ERPNext UI patterns → Plane UI patterns (Next.js SPA) |
| `prompts/test_system.md` | Same |
| `scenarios.json` | Replace all 13 ERPNext scenarios with 3-5 Plane bug scenarios |
| `scripts/seed_erpnext_api.py` | Replace with Plane API seeder (create workspace, project, work items) |

### Key Design Patterns to Preserve

1. **Two-LLM split:** GPT-4o for browser actions, Claude Sonnet for verdict judgment
2. **Mode-specific tools:** Clean repro vs test mode separation
3. **Stagehand as optional sidecar** — graceful degradation
4. **Structured trace:** Per-step thinking, goals, tool calls, costs
5. **Evidence-first prompting:** "Extract before judging"
6. **Scenario JSON format:** Tiered complexity, expected verdicts
7. **Planted bugs for reliable demos**
