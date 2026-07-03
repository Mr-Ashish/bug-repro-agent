#!/usr/bin/env python3
"""
Environment readiness checker and seed data populator for Plane.

Verifies that Plane is running and has the data the repro-agent needs.
Uses Plane's internal API (session cookie auth, same as the web frontend).

Usage:
    python scripts/seed.py check      # exit 0 = ready, exit 1 = not ready
    python scripts/seed.py populate    # create seed data if missing (idempotent)
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
import http.cookiejar
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Configuration ─────────────────────────────────────────────

PLANE_URL = os.getenv("PLANE_URL", "http://localhost:3000")
PLANE_EMAIL = os.getenv("PLANE_EMAIL", "admin@admin.com")
PLANE_PASSWORD = os.getenv("PLANE_PASSWORD", "qweQWE123!@#")
PLANE_WORKSPACE = os.getenv("PLANE_WORKSPACE", "plane-dev")

# API base — Plane's Django backend serves the internal API
# on the same host as the frontend (Next.js proxies /api/ → Django)
API_BASE = PLANE_URL.rstrip("/")


# ── HTTP helpers (stdlib only, no requests) ───────────────────


class PlaneAPI:
    """Minimal Plane API client using stdlib urllib + cookie auth."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar)
        )
        self.csrf_token = ""

    def _get_csrf_token(self) -> str:
        """Fetch CSRF token from the auth endpoint."""
        try:
            req = urllib.request.Request(
                f"{self.base_url}/auth/get-csrf-token/",
                method="GET",
            )
            resp = self.opener.open(req, timeout=10)
            data = json.loads(resp.read())
            return data.get("csrf_token", "")
        except Exception:
            return ""

    def authenticate(self) -> bool:
        """Sign in via Plane's session auth. Returns True on success."""
        try:
            # 1. Get CSRF token
            self.csrf_token = self._get_csrf_token()

            # 2. POST sign-in (form-encoded, like the web frontend)
            form_data = urllib.parse.urlencode({
                "email": PLANE_EMAIL,
                "password": PLANE_PASSWORD,
            }).encode()
            req = urllib.request.Request(
                f"{self.base_url}/auth/sign-in/",
                data=form_data,
                method="POST",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": self.base_url,
                    "X-CSRFToken": self.csrf_token,
                },
            )
            resp = self.opener.open(req, timeout=10)
            # Plane redirects on success — any non-error response is good
            return resp.status in (200, 301, 302)
        except urllib.error.HTTPError as e:
            # 302 redirects are treated as errors by urllib but mean success
            if e.code == 302:
                return True
            return False
        except Exception as e:
            print(f"  ❌ Auth failed: {e}")
            return False

    def get(self, path: str) -> dict | list | None:
        """GET a JSON API endpoint. Returns parsed JSON or None."""
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api{path}",
                method="GET",
                headers={
                    "Accept": "application/json",
                    "Referer": self.base_url,
                    "X-CSRFToken": self.csrf_token,
                },
            )
            resp = self.opener.open(req, timeout=10)
            return json.loads(resp.read())
        except Exception as e:
            return None

    def post(self, path: str, data: dict) -> dict | None:
        """POST JSON to an API endpoint. Returns parsed response or None."""
        try:
            body = json.dumps(data).encode()
            req = urllib.request.Request(
                f"{self.base_url}/api{path}",
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Referer": self.base_url,
                    "X-CSRFToken": self.csrf_token,
                },
            )
            resp = self.opener.open(req, timeout=15)
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode()
                print(f"  ⚠️ POST {path} → {e.code}: {err_body[:200]}")
            except Exception:
                print(f"  ⚠️ POST {path} → {e.code}")
            return None
        except Exception as e:
            print(f"  ⚠️ POST {path} failed: {e}")
            return None


# ── Check mode ────────────────────────────────────────────────


def check(api: PlaneAPI) -> bool:
    """Verify Plane is ready for reproduction. Returns True if ready."""
    print("── Plane Environment Check ──\n")
    all_ok = True

    # 1. Auth
    print("  1. Authentication...", end=" ", flush=True)
    if not api.authenticate():
        print("❌ Cannot sign in")
        print(f"     Email: {PLANE_EMAIL}")
        print(f"     URL: {PLANE_URL}")
        return False
    print("✅")

    # 2. Workspace
    print(f"  2. Workspace '{PLANE_WORKSPACE}'...", end=" ", flush=True)
    workspaces = api.get("/users/me/workspaces/")
    if workspaces is None:
        print("❌ Cannot fetch workspaces (API may be down)")
        return False
    ws_slugs = [w.get("slug", "") for w in workspaces]
    if PLANE_WORKSPACE not in ws_slugs:
        print(f"❌ Not found (available: {ws_slugs})")
        return False
    print("✅")

    # 3. Projects
    print(f"  3. Projects...", end=" ", flush=True)
    projects = api.get(f"/workspaces/{PLANE_WORKSPACE}/projects/")
    if not projects or (isinstance(projects, dict) and "results" in projects):
        proj_list = projects.get("results", []) if isinstance(projects, dict) else projects
    else:
        proj_list = projects if isinstance(projects, list) else []
    if not proj_list:
        print("❌ No projects found")
        all_ok = False
    else:
        names = [p.get("name", "?") for p in proj_list[:5]]
        print(f"✅ ({len(proj_list)} projects: {', '.join(names)})")

    # 4. States (check first project)
    if proj_list:
        proj = proj_list[0]
        proj_id = proj.get("id", "")
        print(f"  4. States in '{proj.get('name', '?')}'...", end=" ", flush=True)
        states = api.get(f"/workspaces/{PLANE_WORKSPACE}/projects/{proj_id}/states/")
        if not states:
            print("❌ No states found")
            all_ok = False
        else:
            state_list = states if isinstance(states, list) else states.get("results", [])
            names = [s.get("name", "?") for s in state_list[:5]]
            print(f"✅ ({len(state_list)} states: {', '.join(names)})")

        # 5. Issues
        print(f"  5. Work items...", end=" ", flush=True)
        issues = api.get(f"/workspaces/{PLANE_WORKSPACE}/projects/{proj_id}/issues/")
        if issues is None:
            print("⚠️ Cannot check (API may not support this endpoint)")
        else:
            issue_list = issues if isinstance(issues, list) else issues.get("results", [])
            if not issue_list:
                print("⚠️ No work items (run 'populate' to create sample data)")
                all_ok = False
            else:
                print(f"✅ ({len(issue_list)} work items)")
    else:
        print("  4. States... ⏭️ skipped (no projects)")
        print("  5. Work items... ⏭️ skipped (no projects)")

    # Summary
    print()
    if all_ok:
        print("✅ Plane is ready for reproduction")
    else:
        print("⚠️ Plane needs setup — run: python scripts/seed.py populate")
    return all_ok


# ── Populate mode ─────────────────────────────────────────────

SEED_STATES = [
    {"name": "Backlog", "color": "#A3A3A3", "group": "backlog"},
    {"name": "Todo", "color": "#3A3A3A", "group": "unstarted"},
    {"name": "In Progress", "color": "#F59E0B", "group": "started"},
    {"name": "Done", "color": "#16A34A", "group": "completed"},
    {"name": "Cancelled", "color": "#EF4444", "group": "cancelled"},
]

SEED_ISSUES = [
    {
        "name": "Sample issue with a normal title",
        "description_html": "<p>This is a basic test issue for reproduction testing.</p>",
        "priority": "medium",
    },
    {
        "name": "A" * 256,  # Long title — edge-case testing for truncation bugs
        "description_html": "<p>This issue has a very long title (256 chars) for edge-case testing.</p>",
        "priority": "high",
    },
    {
        "name": "Issue with special characters: <script>alert('xss')</script> & 'quotes'",
        "description_html": "<p>Tests special character handling in titles and descriptions.</p>",
        "priority": "low",
    },
    {
        "name": "Sub-issue parent for testing hierarchy",
        "description_html": "<p>This issue should have sub-issues attached for hierarchy testing.</p>",
        "priority": "medium",
    },
    {
        "name": "Issue assigned to a cycle and module",
        "description_html": "<p>This issue is part of a cycle and module for cross-feature testing.</p>",
        "priority": "urgent",
    },
]


def populate(api: PlaneAPI) -> bool:
    """Create seed data in Plane. Idempotent — skips existing items."""
    print("── Populating Seed Data ──\n")

    # Auth
    print("  Authenticating...", end=" ", flush=True)
    if not api.authenticate():
        print("❌ Cannot sign in")
        return False
    print("✅")

    # Check workspace
    print(f"  Checking workspace '{PLANE_WORKSPACE}'...", end=" ", flush=True)
    workspaces = api.get("/users/me/workspaces/")
    if workspaces is None:
        print("❌ Cannot reach API")
        return False
    ws_slugs = [w.get("slug", "") for w in workspaces]
    if PLANE_WORKSPACE not in ws_slugs:
        print(f"❌ Workspace '{PLANE_WORKSPACE}' not found")
        print(f"     Available: {ws_slugs}")
        print(f"     Create it manually in the Plane admin panel first.")
        return False
    print("✅")

    # Find or create project
    print("  Checking projects...", end=" ", flush=True)
    projects = api.get(f"/workspaces/{PLANE_WORKSPACE}/projects/")
    proj_list = projects if isinstance(projects, list) else (projects or {}).get("results", [])

    project = None
    for p in proj_list:
        if p.get("identifier") == "SEED" or p.get("name") == "Seed Demo Project":
            project = p
            break

    if project:
        print(f"✅ Found '{project['name']}' (id: {project['id'][:8]}...)")
    else:
        print("creating SEED project...", end=" ", flush=True)
        project = api.post(f"/workspaces/{PLANE_WORKSPACE}/projects/", {
            "name": "Seed Demo Project",
            "identifier": "SEED",
            "description": "Auto-created by seed.py for bug reproduction testing",
            "network": 2,  # 2 = public to workspace
        })
        if not project:
            print("❌ Failed to create project")
            return False
        print(f"✅ Created (id: {project['id'][:8]}...)")

    proj_id = project["id"]

    # Check/create states
    print("  Checking states...", end=" ", flush=True)
    states = api.get(f"/workspaces/{PLANE_WORKSPACE}/projects/{proj_id}/states/")
    state_list = states if isinstance(states, list) else (states or {}).get("results", [])
    existing_names = {s.get("name", "").lower() for s in state_list}

    created_states = 0
    for state in SEED_STATES:
        if state["name"].lower() not in existing_names:
            result = api.post(
                f"/workspaces/{PLANE_WORKSPACE}/projects/{proj_id}/states/",
                state,
            )
            if result:
                created_states += 1

    if created_states > 0:
        print(f"✅ Created {created_states} new states")
    else:
        print(f"✅ All {len(SEED_STATES)} states exist")

    # Re-fetch states for issue creation
    states = api.get(f"/workspaces/{PLANE_WORKSPACE}/projects/{proj_id}/states/")
    state_list = states if isinstance(states, list) else (states or {}).get("results", [])
    default_state_id = ""
    for s in state_list:
        if s.get("group") == "backlog" or s.get("name", "").lower() == "backlog":
            default_state_id = s["id"]
            break
    if not default_state_id and state_list:
        default_state_id = state_list[0]["id"]

    # Check/create issues
    print("  Checking work items...", end=" ", flush=True)
    issues = api.get(f"/workspaces/{PLANE_WORKSPACE}/projects/{proj_id}/issues/")
    issue_list = issues if isinstance(issues, list) else (issues or {}).get("results", [])

    if len(issue_list) >= 5:
        print(f"✅ {len(issue_list)} work items exist (sufficient)")
    else:
        created_issues = 0
        for issue_data in SEED_ISSUES:
            if default_state_id:
                issue_data["state"] = default_state_id
            result = api.post(
                f"/workspaces/{PLANE_WORKSPACE}/projects/{proj_id}/issues/",
                issue_data,
            )
            if result:
                created_issues += 1
        print(f"✅ Created {created_issues} work items")

    # Summary
    print()
    print("✅ Seed data populated — run 'check' to verify:")
    print(f"   python scripts/seed.py check")
    return True


# ── CLI ───────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Plane environment readiness checker and seed data populator",
        epilog="Examples:\n"
               "  python scripts/seed.py check      # verify environment\n"
               "  python scripts/seed.py populate    # create seed data\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "command",
        choices=["check", "populate"],
        help="'check' verifies readiness (exit 0/1), 'populate' creates seed data",
    )
    args = parser.parse_args()

    api = PlaneAPI(API_BASE)

    if args.command == "check":
        ok = check(api)
        sys.exit(0 if ok else 1)
    elif args.command == "populate":
        ok = populate(api)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
