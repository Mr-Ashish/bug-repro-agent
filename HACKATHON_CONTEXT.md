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

1. **Visual impact matters** — judges need to see the browser clicking around
2. **Reliability is 30% of score** — we need graceful failure handling, not just happy path
3. **7 hours to build** — scope down HARD
4. **Pre-seed the app** — Plane should be running + populated with test data BEFORE the hackathon starts
5. **Pick 3 bugs** — nail those, don't try to generalize

---

## Prior Art: ERPNext Bug QA Agent

**Location:** `/Users/ashishmishra/Documents/experimentation/browser-use-hackathon/bug-qa-agent/` (reference only)

We previously built a bug reproduction agent for ERPNext using Browser-Use + GPT-4o + Claude Sonnet judge. That architecture has been **replaced** by the current design:

### Old → New Architecture Shift

| Old (ERPNext) | New (Plane) | Why |
|---|---|---|
| Python orchestrator | Grok skill + /loop | Claude Code IS the meta-agent |
| Browser-Use Agent class | Claude Code + Stagehand | No separate agent framework |
| GPT-4o for actions | Stagehand (Gemini Flash) | Stagehand handles NL→DOM |
| Claude Sonnet judge (OpenRouter) | Claude Code vision | Same agent, different phase |
| Python CLI | `/repro <url>` skill trigger | Native to Grok |
| `scenarios.json` | Real GitHub issues | No planted bugs |

### What We Carry Forward (patterns, not code)

1. **Stagehand REST API pattern** — `stagehand_client.py` is reference for the TS client
2. **Evidence-first approach** — capture screenshots before judging
3. **Structured traces** — record what the agent did at each step
