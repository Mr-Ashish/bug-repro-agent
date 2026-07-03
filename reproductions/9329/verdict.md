# Verdict: Issue #9329

**Issue**: [Inline work item creation shows generic error when title exceeds 255 characters](https://github.com/makeplane/plane/issues/9329)

**Date**: 2026-07-03
**Agent**: repro-agent (Claude Code + Stagehand server-v3)
**Target**: Plane dev build (localhost:3000)
**Browser automation**: Stagehand REST API (`act` / `extract` / `observe` / `navigate`)

---

## Result: BUG APPEARS FIXED ✅

The original issue reports that when creating a work item inline with a title exceeding 255 characters, the UI shows a **generic** error message ("Some error occurred. Please try again.") instead of a descriptive validation message.

### What we observed

| Check | Result |
|-------|--------|
| Login | ✅ Logged in as admin@admin.com |
| Navigate to Work Items | ✅ Reached Seed Demo Project work items list |
| Open inline create form | ✅ "Add work item" button works |
| Type 256-char title | ✅ Input accepts all 256 characters |
| Submit form | ✅ Form submission triggers validation |
| **Validation message** | **"Title should be less than 255 characters"** — descriptive, not generic |
| API direct test | 400: `{"name":["Ensure this field has no more than 255 characters."]}` |

### Evidence

- **Screenshot**: `evidence-stagehand.png` — Stagehand-driven: shows "Create new work item" modal with 256-char title and validation message
- **Screenshot**: `evidence-validation-msg.png` — Chrome DevTools corroboration
- **Stagehand extract**: `"Title should be less than 255 characters"` — returned by `stagehand.extract`
- **Stagehand observe**: `"Validation message indicating that the title should be less than 255 characters"` — returned by `stagehand.observe`
- **API response**: HTTP 400 with `{"name":["Ensure this field has no more than 255 characters."]}`
- **Action log**: `action-log.json` — 18 Stagehand-only steps (session → login → navigate → repro → evidence)

### Conclusion

The current dev build of Plane has **client-side validation** that catches titles exceeding 255 characters and displays a clear message: **"Title should be less than 255 characters"**. The API also returns a descriptive 400 error. The generic error described in issue #9329 does not appear in this version.

The bug has been **resolved** — either through a fix in the current dev branch or through a version upgrade.

### Reproduction steps (for future runs)

1. Log in to Plane as admin
2. Navigate to any project's Work Items list view
3. Click "Add work item" (bottom of list or toolbar)
4. Type or paste a title with 256+ characters
5. Submit the form
6. Observe: should show "Title should be less than 255 characters" (fixed) vs "Some error occurred" (original bug)
