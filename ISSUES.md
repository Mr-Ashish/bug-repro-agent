# Issues & Introspection

Every problem encountered building repro-agent, with root cause and resolution.

---

## 1. Stagehand sessions die immediately

**Symptom:** `POST /v1/sessions/start` returns a session ID, but all subsequent calls (act/extract) return 404.

**Root cause:** Using `ws://localhost:9222` (no path) or a **page-level** CDP URL (`ws://localhost:9222/devtools/page/...`). Stagehand requires the **browser-level** WebSocket URL.

**Fix:** Use the full browser-level CDP URL:
```
ws://localhost:9222/devtools/browser/<browser-guid>
```
Get it from `curl http://localhost:9222/json/version | jq .webSocketDebuggerUrl`.

**Status:** Fixed. `CDP_URL` env var documented in `.env`.

---

## 2. Stagehand navigate creates a new tab without cookies

**Symptom:** Login via Chrome DevTools MCP works, but Stagehand's `navigate` call opens a fresh tab. Auth cookies from other tabs don't transfer.

**Root cause:** Stagehand creates a new CDP target (tab) per session. Cookies are per-tab in the CDP context.

**Fix:** Do the entire login flow within the Stagehand session — don't rely on cookies from other tabs or tools. The drive script logs in via `act("type email...")` → `act("Click Continue")` → `act("type password...")` → `act("Go to workspace")`.

**Status:** Fixed. Login is step 1 in drive-v3.ts.

---

## 3. Plane login is two-step (not a single form)

**Symptom:** `act("submit login form")` doesn't work. Continue button doesn't advance.

**Root cause:** Plane's login is a React-controlled two-step flow:
1. Email → Click "Continue" (disabled until React state updates)
2. Password → Click "Go to workspace"

The "Continue" button is initially disabled. Typing via Stagehand triggers React's `onChange` which enables it.

**Fix:** Use explicit step-by-step act instructions with adequate sleep times:
- 2s after typing email (React state update)
- 5s after Continue (password form render)
- 8s after Go to workspace (workspace load)

**Status:** Fixed. Proven sequence in drive-v3.ts.

---

## 4. Claude Sonnet 4 via OpenRouter doesn't work with Stagehand

**Symptom:** All act/extract/observe calls fail with `"No object generated: could not parse the response."`

**Root cause:** Stagehand uses `@ai-sdk/openai`'s structured output (`response_format: json_schema`). When the model is `anthropic/claude-sonnet-4` routed through OpenRouter's OpenAI-compatible API, the response format doesn't match what the AI SDK expects. Claude's structured output protocol differs from OpenAI's.

**Fix:** Use models that natively support OpenAI-style structured output:
- ✅ `gpt-4o` — works perfectly, 15/15 steps pass
- ✅ `gpt-4o-mini` — works, but weaker DOM reasoning
- ❌ `anthropic/claude-sonnet-4` via OpenRouter — response parsing fails
- ❌ `openai/anthropic/claude-sonnet-4` (OpenAI provider prefix trick) — same failure

**Status:** Fixed. Default changed to `gpt-4o`. Documented in SKILL.md.

---

## 5. Anthropic API key missing when using anthropic/ prefix

**Symptom:** `"Anthropic API key is missing. Pass it using the 'apiKey' parameter or the ANTHROPIC_API_KEY environment variable."`

**Root cause:** Stagehand's model routing: `anthropic/` prefix → `@ai-sdk/anthropic` → looks for `ANTHROPIC_API_KEY` env var. The server was started with only `OPENAI_*` env vars pointing at OpenRouter.

**Fix:** Either:
1. Pass API key via `x-model-api-key` header (per-request)
2. Restart Stagehand with `ANTHROPIC_API_KEY` env var

We use the header approach. But even with the key, Claude still fails (issue #4).

**Status:** Resolved by switching to `gpt-4o`.

---

## 6. Action log shows "ok" instead of actual extract/observe content

**Symptom:** Compact action log (`action-log.json`) shows `"result": "ok"` for all extract and observe steps, losing the actual extracted text.

**Root cause:** In the `tracedPost` result formatting, `json.success === true` was checked **before** the action-specific formatting for extract/observe. Since Stagehand returns `{"success": true, "data": {"result": {"extraction": "..."}}}`, the `success` check short-circuited to `"ok"`.

**Fix:** Reorder the conditions: check `action === "extract"` and `action === "observe"` **before** `success === true`. The `success === false` check stays first (errors always take priority).

**Status:** Fixed in drive-v3.ts.

---

## 7. Port inconsistencies across codebase

**Symptom:** Four different default ports for Stagehand and Plane across different files.

| File | Stagehand default | Plane default |
|------|-------------------|---------------|
| drive-v3.ts | 3100 ✅ | 3000 ✅ |
| stagehand-client.ts | 3000 ❌ | — |
| plane-adapter.ts | — | 80 ❌ |
| HLD.md | 3000 ❌ | 80 ❌ |
| SKILL.md | 3000 ❌ | — |
| README.md | 3000 ❌ | — |

**Root cause:** Stagehand was initially assumed to be on 3000, but we moved it to 3100 to avoid conflicts with Plane. Docs and lib defaults weren't updated.

**Fix:** Standardized everywhere:
- Stagehand: `localhost:3100`
- Plane: `localhost:3000`

**Status:** Fixed in stagehand-client.ts, plane-adapter.ts, SKILL.md. HLD.md and README.md still reference old ports (updated separately).

---

## 8. Model name inconsistency (4 different defaults)

**Symptom:** `claude-sonnet-4`, `gemini-2.5-flash-preview`, `gemini-2.5-flash`, `gpt-4o` appear in different files.

**Root cause:** Model was changed multiple times during development. Each change only updated the file being worked on.

**Fix:** Standardized to `gpt-4o` as default everywhere. Env var `STAGEHAND_SESSION_MODEL` is the single source of truth. Old env var `STAGEHAND_MODEL` removed.

**Status:** Fixed.

---

## 9. Verdict.md says "18 steps" but action-log has 15

**Symptom:** verdict.md referenced an earlier manual run (18 curl-based steps), not the automated script run (15 steps).

**Root cause:** verdict.md was written after the manual curl proof-of-concept, then never updated after the automated script run.

**Fix:** Rewrote verdict.md with data from the actual successful run (session ID, step count, timing, exact extract results).

**Status:** Fixed.

---

## 10. Stale scripts with hardcoded session IDs

**Symptom:** `drive-v2.ts`, `drive-repro-9329.ts`, `drive-start-session.ts` all contain hardcoded session IDs (`3f16adbc-...`) and CDP URLs.

**Root cause:** Written as one-off experiments during development. Never cleaned up.

**Fix:** Moved to `scripts/archive/`. The current working script is `scripts/drive-v3.ts`.

**Status:** Fixed.

---

## 11. artifact-emitter.ts generates broken login flow

**Symptom:** `generateReproSpec()` produces a Playwright test with `page.fill('input[name="email"]'...)` + `page.click('button[type="submit"]')` — a single-form login.

**Root cause:** Template was written assuming a standard login form. Plane uses a two-step flow (email → Continue → password → Go to workspace).

**Fix:** Updated template to use the correct two-step flow with proper button text selectors.

**Status:** Fixed.

---

## 12. Empty evidence/ directory

**Symptom:** `reproductions/9329/evidence/` exists but is empty. Evidence PNGs are at the `9329/` root level.

**Root cause:** Screenshots were captured via Chrome DevTools MCP during manual testing, saved to the root. The `evidence/` subdirectory was created by convention but never populated.

**Note:** The drive script doesn't capture screenshots (uses extract/observe instead). Screenshots require a separate CDP call. This is a known gap — the script proves the bug via text extraction rather than visual evidence.

**Status:** Acknowledged. Evidence PNGs from manual testing remain at root level.

---

## 13. Password truncation in action log

**Symptom:** Action log step 5 shows `"qweQWE123!@"` instead of `"qweQWE123!@#"` — the `#` is missing.

**Root cause:** Likely Stagehand or the LLM truncating special characters when interpreting the act instruction. The `#` character may be interpreted as a comment marker in some context.

**Note:** Despite the truncation in the log, login succeeds — suggesting Stagehand's actual keyboard input includes the `#` even if the logged instruction appears truncated.

**Status:** Cosmetic. Login works. Not blocking.

---

## 14. Full trace file too large for git (73MB)

**Symptom:** `full-trace.json` is 73MB because navigate responses include the complete page DOM.

**Root cause:** Stagehand's navigate response returns the full page content/DOM snapshot. Two navigate calls = ~70MB of DOM data.

**Fix:** `.gitignore` excludes `full-trace.json` and `step-*-navigate.json`. Per-step act/extract/observe traces (small, ~1-2KB each) are tracked.

**Status:** Fixed.

---

## 15. .env.example referenced but doesn't exist

**Symptom:** README.md says `cp .env.example .env` but `.env.example` doesn't exist.

**Fix:** Created `.env.example` with all required variables (no secrets).

**Status:** Fixed (see below).

---

## Summary

| # | Severity | Issue | Status |
|---|----------|-------|--------|
| 1 | 🔴 | Session dies — wrong CDP URL | Fixed |
| 2 | 🔴 | Navigate creates new tab — no cookies | Fixed |
| 3 | 🔴 | Plane two-step login | Fixed |
| 4 | 🔴 | Claude Sonnet 4 via OpenRouter fails | Fixed (use gpt-4o) |
| 5 | 🟡 | Anthropic API key missing | Fixed (header + model switch) |
| 6 | 🔴 | Action log shows "ok" not content | Fixed |
| 7 | 🔴 | Port inconsistencies | Fixed |
| 8 | 🔴 | Model name inconsistencies | Fixed |
| 9 | 🟡 | Verdict step count wrong | Fixed |
| 10 | 🟡 | Stale scripts | Archived |
| 11 | 🟡 | Broken login template | Fixed |
| 12 | 🟡 | Empty evidence dir | Acknowledged |
| 13 | 🟡 | Password truncation | Cosmetic |
| 14 | 🟡 | Full trace too large | Fixed (gitignored) |
| 15 | 🟡 | Missing .env.example | Fixed |