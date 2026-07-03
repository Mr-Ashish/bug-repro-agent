# Demo Bugs

> Selected from ~149 real Plane bugs (200 issues analyzed, 2026-07-03).
> All are Cluster A (UI Interaction) — low repro complexity, high demo quality.

---

## Locked Demo Bugs

### #9329 — Inline work item creation shows generic error on 255+ char title

- **Issue:** https://github.com/makeplane/plane/issues/9329
- **Bug class:** form-validation
- **Steps:** Login → navigate to SEED project Work Items → click inline "Add work item" → type 256+ character title → press Enter
- **Expected bug:** Generic/unhelpful error message appears instead of clear validation about title length
- **Repro complexity:** Low
- **Seeding needed:** None (existing SEED project is sufficient)

### #9050 — Deleted Stickies reappear on page reload

- **Issue:** https://github.com/makeplane/plane/issues/9050
- **Bug class:** state-persistence
- **Steps:** Login → navigate to Stickies → create a sticky note → delete it → reload the page
- **Expected bug:** Deleted sticky reappears after reload
- **Repro complexity:** Low
- **Seeding needed:** Create stickies via Stagehand UI (0 stickies exist currently)

### #9124 — Sub-task expand requires 3 clicks

- **Issue:** https://github.com/makeplane/plane/issues/9124
- **Bug class:** ui-interaction
- **Steps:** Login → navigate to an issue with sub-tasks → click the expand chevron
- **Expected bug:** First click does nothing; requires 3 clicks to expand
- **Repro complexity:** Low
- **Seeding needed:** Verify sub-issues exist in SEED project (they do — 5 issues with sub-issues)
