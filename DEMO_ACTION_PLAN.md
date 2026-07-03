# Live Demo Action Plan — Bug Repro Agent

**Date:** 2026-07-04  
**Target:** Browser-Use Hackathon, Bengaluru  
**Goal:** E2E reliable reproduction of any Plane GitHub issue in a single `/repro-agent <url>` command

---

## Issues Discovered (from session introspection)

### 1. Plane Infrastructure Fixes (in `plane/` repo)

The meta-agent had to fix two files before Plane would run. These changes are currently **unstaged** on the `preview` branch and will be lost on any `git clean` or re-clone.

| File | Fix | Root Cause |
|------|-----|------------|
| `apps/proxy/Caddyfile.ce` | Moved global options `{ }` block from bottom to top | Caddy 2.11.3 requires global block FIRST |
| `apps/proxy/Caddyfile.ce` | Fixed indentation on `redir` lines | Whitespace was inconsistent |
| `docker-compose.yml` | Added 5 env vars to proxy service: `SITE_ADDRESS`, `CERT_EMAIL`, `CERT_ACME_CA`, `CERT_ACME_DNS`, `TRUSTED_PROXIES` | Caddyfile references `{$VAR}` placeholders but docker-compose didn't pass them through |

**Action:** Create branch `plane-local-fixes` off `preview`, commit these changes. The meta-agent will `git pull --rebase` main/preview, then cherry-pick or merge this branch.

### 2. Meta-Agent Must Rebase Plane to Latest

Currently SKILL.md doesn't tell the meta-agent to sync Plane before running. If upstream Plane changes (e.g., Caddyfile structure changes again), the agent runs against stale code.

**Action:** Add to SKILL.md pre-flight:
```
cd plane && git pull --rebase origin preview && git merge plane-local-fixes --no-edit
```

### 3. SKILL.md Pre-flight Ordering Bug

**Current order (wrong):**
1. seed.py check ← runs HTTP calls against Plane
2. seed.py populate ← runs HTTP calls against Plane  
3. Verify Chrome
4. Verify Plane ← should be FIRST

**Correct order:**
1. ✅ Verify Plane is running (`docker ps`, health check on port 80)
2. ✅ Verify Chrome with `--remote-debugging-port=9222`
3. ✅ `python scripts/seed.py check`
4. ✅ `python scripts/seed.py populate` (if check fails)

### 4. SKILL.md Port Number Wrong

Line 31 says `localhost:3000` — should be `localhost:80` (Caddy proxy).

### 5. Infrastructure Debugging Time Boundary

The meta-agent spent ~3 minutes debugging Caddy + docker-compose. For a live demo, this is too long. If infra isn't ready in ~60s, fail fast with a clear error rather than becoming a sysadmin.

**Action:** Add to SKILL.md:
```
⏱ Hard boundary: If Plane is not healthy after 60 seconds of checking/waiting, 
STOP and report: "Plane infrastructure not ready. Run setup manually."
Do NOT attempt to debug Docker, edit Caddyfiles, or modify docker-compose.yml.
```

### 6. `.env` Fixes (already applied)

| Key | Old | New | Why |
|-----|-----|-----|-----|
| `PLANE_URL` | `http://localhost:3000` | `http://localhost:80` | Port 3000 = nginx (no API proxy). Port 80 = Caddy (routes API+auth) |
| `CDP_URL` | Stale WebSocket UUID | Commented out | drive.py auto-discovers via `http://localhost:9222/json/version` |

### 8. Browser Viewport Too Small (1280×720)

drive.py sets `viewport={"width": 1280, "height": 720}` — a laptop-sized window. Plane's sidebar collapses or hides items (like Settings gear icon) at this size, causing the agent to waste 14+ steps hunting for Project Settings.

**Action:** In drive.py, change BrowserProfile to:
```python
profile = BrowserProfile(
    cdp_url=cdp_url,
    headless=False,
    viewport={"width": 1920, "height": 1080},
    screen={"width": 1920, "height": 1080},
    highlight_elements=True,
    record_video_dir=str(repro_dir),
)
```
Also update SKILL.md Chrome launch to include `--start-maximized`:
```
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --start-maximized
```

### 9. Task Prompt Missing Settings URL Pattern

The navigation map in drive.py's prompt template includes URLs for Dashboard, Projects, Issues, Cycles, etc. but **NOT for Project Settings**. The agent has no idea the URL pattern is:
```
http://localhost:80/<workspace>/projects/<project-id>/settings/
http://localhost:80/<workspace>/projects/<project-id>/settings/states/
```

Without this, the agent burned 14 steps (10-24 of 50) clicking randomly looking for Settings. With 50 max steps, that's 28% of its budget wasted on navigation.

**Action:** Add to the navigation map in drive.py's `TASK_PROMPT_TEMPLATE`:
```
- **Project Settings:** click gear icon at bottom of left sidebar (below project nav items)
- **Project Settings URL pattern:** http://localhost:80/{workspace}/projects/{project_id}/settings/
- **States settings:** http://localhost:80/{workspace}/projects/{project_id}/settings/states/
- **Members settings:** http://localhost:80/{workspace}/projects/{project_id}/settings/members/
```

**Introspection finding:** The agent's trace shows step 10 goal was "Find and access Project Settings to navigate to the States section" — it knew WHAT to do but not WHERE/HOW. A direct URL would have solved this in 1 step instead of 14+. This is the difference between a 2-minute demo and a 10-minute one.

### 10. `plane-live` Crash-Loop (non-blocking)

`plane-live` keeps restarting due to missing `LIVE_SERVER_SECRET_KEY`. This is the real-time collaboration service — app works fine without it. **No action needed for demo**, but could add the env var later.

---

## Execution Plan

### Step 1: Commit Plane fixes to local branch
```bash
cd plane/
git checkout -b plane-local-fixes
git add apps/proxy/Caddyfile.ce docker-compose.yml
git commit -m "fix: Caddy global block ordering + proxy env vars for local dev"
git checkout preview  # go back to working branch
```

### Step 2: Update SKILL.md
- Fix pre-flight ordering (Plane → Chrome → seed check → seed populate)
- Add `git pull --rebase` + merge local fixes instruction
- Fix port 3000 → 80
- Add 60s infra debugging time boundary

### Step 3: Persist .env
- Already correct — commit to main

### Step 4: Commit bug-repro-agent changes
```bash
git add .env .claude/skills/repro-agent/SKILL.md
git commit -m "fix: SKILL.md ordering, port, rebase instruction, infra time boundary"
git push origin main
```

### Step 5: Verify E2E
Run `/repro-agent https://github.com/makeplane/plane/issues/8591` in a clean session and confirm:
- No infra debugging
- seed.py check passes immediately
- drive.py runs and produces verdict

---

## Introspection Log (from watching meta-agent session)

1. **SKILL.md ordering bug** — seed.py ran before Plane was verified running
2. **Good autonomous recovery** — meta-agent self-corrected when seed.py failed
3. **Docker cold start ~45s** — services need time to come up after `docker compose up -d`
4. **Sysadmin scope creep** — agent edited Caddyfile and docker-compose.yml (should be pre-fixed)
5. **Plane repo modifications not persisted** — changes lost on next clone/reset
6. **plane-live non-critical** — crash-loop doesn't block reproduction
7. **Port confusion** — 3000 vs 80, must be documented clearly
8. **Infra debugging consumed ~3min** — too long for live demo
9. **Docker rebuild used cache** — `docker compose up -d --build` was fast (~10s) because layers cached
10. **Meta-agent did `git pull --rebase`** — good instinct, but not in SKILL.md instructions
11. **Plane fixes need persistence** — the whole point of this action plan
12. **60s hard boundary** — prevents demo from becoming an infra debugging session
