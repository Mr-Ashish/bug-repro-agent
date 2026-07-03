# Verdict: Issue #9329

**Issue**: [Inline work item creation shows generic error when title exceeds 255 characters](https://github.com/makeplane/plane/issues/9329)

**Date**: 2026-07-03
**Agent**: repro-agent (Claude Code + Stagehand server-v3)
**Target**: Plane dev build (localhost:3000)
**Browser automation**: Stagehand REST API (`act` / `extract` / `observe` / `navigate`)
**Model**: GPT-4o via OpenRouter
**Session**: `afa896d0-b5e2-4567-980a-797e5e1741b3`

---

## Result: BUG APPEARS FIXED ✅

The original issue reports that when creating a work item inline with a title exceeding 255 characters, the UI shows a **generic** error message ("Some error occurred. Please try again.") instead of a descriptive validation message.

### What we observed

15 Stagehand steps, 75 seconds total. Every step passed.

| Check | Result |
|-------|--------|
| Login (4 act steps) | ✅ Logged in as admin@admin.com via two-step flow |
| Navigate to Work Items | ✅ "Seed Demo Project - Work items" page |
| Open inline create form | ✅ `act("Click Add work item")` succeeded |
| Type 256-char title | ✅ `act("Click Title input and type AAAA...")` succeeded |
| Submit form | ✅ `act("Press Enter")` triggered validation |
| **Validation message** | **"Title should be less than 255 characters"** — descriptive, not generic |

### Evidence

- **Stagehand extract** (step 13): `"Title should be less than 255 characters"`
- **Stagehand observe** (step 14): Found validation message on page
- **Stagehand verdict** (step 15): `"DESCRIPTIVE - Title should be less than 255 characters"`
- **Screenshot**: `evidence-stagehand.png` — captured during earlier manual validation
- **Action log**: `action-log.json` — 15 steps with timing
- **Full traces**: `traces/step-*.json` — every request/response pair

### Conclusion

The current dev build of Plane has **client-side validation** that catches titles exceeding 255 characters and displays: **"Title should be less than 255 characters"**. The generic error described in issue #9329 does not appear in this version.

The bug has been **resolved** in the current dev branch.
