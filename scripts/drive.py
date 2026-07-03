#!/usr/bin/env python3
"""
bug reproduction driver — works on ANY GitHub issue.

Fetches the issue via `gh`, builds a task prompt from the issue body,
runs browser-use agent, and parses the agent's structured verdict line.

Usage:
    python scripts/drive.py --issue 9329
    python scripts/drive.py --issue 9329 --repo makeplane/plane
    python scripts/drive.py --url https://github.com/makeplane/plane/issues/9329
"""
import asyncio
import argparse
import json
import base64
import os
import re
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from browser_use import Agent, Browser, BrowserProfile, ChatOpenAI, AgentHistoryList

load_dotenv()

# ── Configuration ─────────────────────────────────────────────

CDP_URL = os.getenv("CDP_URL", "")
PLANE_URL = os.getenv("PLANE_URL", "http://localhost:3000")
PLANE_EMAIL = os.getenv("PLANE_EMAIL", "admin@admin.com")
PLANE_PASSWORD = os.getenv("PLANE_PASSWORD", "qweQWE123!@#")
PLANE_WORKSPACE = os.getenv("PLANE_WORKSPACE", "plane-dev")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = os.getenv("BROWSER_USE_MODEL", "anthropic/claude-sonnet-4")
DEFAULT_REPO = os.getenv("GITHUB_REPO", "makeplane/plane")

# Exit codes
EXIT_REPRODUCED = 0
EXIT_NOT_REPRODUCED = 1
EXIT_INCONCLUSIVE = 2
EXIT_ERROR = 3


# ── Pre-flight checks ────────────────────────────────────────


def discover_cdp_url(debug_port: int = 9222) -> str:
    """Auto-discover Chrome CDP browser-level WebSocket URL."""
    try:
        resp = urllib.request.urlopen(
            f"http://localhost:{debug_port}/json/version", timeout=3
        )
        data = json.loads(resp.read())
        ws_url = data["webSocketDebuggerUrl"]
        print(f"  🔗 Auto-discovered CDP: {ws_url}")
        return ws_url
    except Exception:
        return ""


def preflight(cdp_url: str, plane_url: str) -> None:
    """Fail fast if infrastructure isn't ready."""
    errors = []

    # 1. Chrome CDP reachable?
    try:
        ws_host = cdp_url.split("//")[1].split("/")[0]
        host, port = ws_host.rsplit(":", 1)
        sock = socket.create_connection((host, int(port)), timeout=3)
        sock.close()
    except Exception:
        errors.append(f"Chrome CDP not reachable at {cdp_url}")

    # 2. Plane frontend responding?
    try:
        urllib.request.urlopen(plane_url, timeout=5)
    except Exception:
        errors.append(f"Plane not responding at {plane_url}")

    # 3. Plane API backend healthy? (frontend can return 200 while backend is dead)
    try:
        api_url = f"{plane_url.rstrip('/')}/api/users/me/"
        urllib.request.urlopen(api_url, timeout=5)
    except urllib.error.HTTPError as e:
        # 401/403 = API is alive but we're not authenticated — that's fine
        if e.code not in (401, 403):
            errors.append(f"Plane API unhealthy at {plane_url} (HTTP {e.code})")
    except Exception:
        errors.append(
            f"Plane API not reachable at {plane_url} "
            f"(frontend responds but backend may be down)"
        )

    # 4. gh CLI authenticated?
    try:
        subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, check=True, timeout=5,
        )
    except FileNotFoundError:
        errors.append("`gh` CLI not installed (https://cli.github.com/)")
    except subprocess.CalledProcessError:
        errors.append("`gh` CLI not authenticated (run `gh auth login`)")
    except Exception:
        errors.append("`gh` CLI check failed")

    if errors:
        print("❌ Pre-flight checks failed:")
        for e in errors:
            print(f"   • {e}")
        sys.exit(EXIT_ERROR)
    print("✅ Pre-flight: Chrome CDP, Plane, gh — all ready")


# ── Issue fetching ────────────────────────────────────────────


def fetch_issue(issue_number: str, repo: str) -> dict:
    """Fetch issue title and body via `gh` CLI. Returns {number, title, body, url}."""
    try:
        result = subprocess.run(
            ["gh", "issue", "view", issue_number, "--repo", repo,
             "--json", "title,body,url,number"],
            capture_output=True, text=True, check=True, timeout=30,
        )
        data = json.loads(result.stdout)
        return {
            "number": str(data["number"]),
            "title": data["title"],
            "body": data.get("body", "") or "",
            "url": data["url"],
        }
    except FileNotFoundError:
        print("❌ `gh` CLI not found. Install: https://cli.github.com/")
        sys.exit(EXIT_ERROR)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to fetch issue #{issue_number} from {repo}")
        print(f"   {e.stderr.strip()}")
        sys.exit(EXIT_ERROR)


# ── Prompt template ───────────────────────────────────────────

TASK_TEMPLATE = """You are a QA engineer reproducing a bug in Plane (project management app).

## App details
- URL: {plane_url}
- Login: email "{email}", password "{password}"
- Workspace: {workspace}

## Bug report (GitHub issue #{number})
Title: {title}
URL: {url}

{body}

## Your job
1. Log in to Plane at {plane_url}.
2. Read the bug report above. Figure out what steps reproduce it.
3. Execute those steps in the browser.
4. Observe what actually happens vs what the bug report says should happen.

## Rules
- You are a REPRODUCER, not a fixer. You observe and report.
- Explore the app to find the right place. Don't give up if the first path doesn't work.
- Take screenshots at key moments, especially when you see the bug (or don't).
- If the bug report mentions specific data (long text, special characters, etc), create or use that exact data.

## Plane UI navigation map
- **Dashboard/Home:** {plane_url}/{workspace}/
- **Projects list:** {plane_url}/{workspace}/projects/
- **Issues (work items):** click a project → "Work Items" in left sidebar
- **Cycles:** left sidebar → "Cycles"
- **Modules:** left sidebar → "Modules"
- **Pages:** left sidebar → "Pages"
- **Stickies:** icon in the bottom-right floating toolbar (sticky note icon)
- **Settings:** left sidebar bottom → gear icon
- **Create issue:** "Add work item" button (top-right of issues list) or press 'C'
- **Sub-issues:** open an issue → "Sub-work items" section below description
- **Filters/Views:** toolbar above issue list → "Filters" dropdown
Note: "Work Items" is Plane's term for issues. The left sidebar shows: Work Items, Cycles, Modules, Pages, Views.

## Required output format
End your final message with EXACTLY one of these verdict lines:

VERDICT: REPRODUCED | <one-line summary of what you saw>
VERDICT: NOT_REPRODUCED | <one-line summary — the feature worked correctly>
VERDICT: INCONCLUSIVE | <one-line summary — why you couldn't determine>

The verdict line must start with "VERDICT:" and use one of the three values above.
Include a pipe separator and a brief description after it."""


def build_task(issue: dict) -> str:
    """Build the agent task prompt from a fetched issue."""
    return TASK_TEMPLATE.format(
        plane_url=PLANE_URL,
        email=PLANE_EMAIL,
        password=PLANE_PASSWORD,
        workspace=PLANE_WORKSPACE,
        number=issue["number"],
        title=issue["title"],
        url=issue["url"],
        body=issue["body"],
    )


# ── Verdict parsing ──────────────────────────────────────────

VERDICT_PATTERN = re.compile(
    r"VERDICT:\s*(REPRODUCED|NOT_REPRODUCED|INCONCLUSIVE)\s*\|\s*(.+)",
    re.IGNORECASE,
)

VERDICT_DISPLAY = {
    "reproduced": "✅ REPRODUCED",
    "not_reproduced": "❌ NOT REPRODUCED",
    "inconclusive": "⚠️ INCONCLUSIVE",
}

VERDICT_EXIT_CODES = {
    "reproduced": EXIT_REPRODUCED,
    "not_reproduced": EXIT_NOT_REPRODUCED,
    "inconclusive": EXIT_INCONCLUSIVE,
}


def parse_verdict(result_text: str) -> tuple[str, str, str]:
    """Parse the agent's structured verdict line.

    Returns (status_display, verdict_key, summary).
    Falls back to INCONCLUSIVE if no verdict line found.
    """
    for line in reversed(result_text.strip().splitlines()):
        m = VERDICT_PATTERN.match(line.strip())
        if m:
            key = m.group(1).lower()
            summary = m.group(2).strip()
            return VERDICT_DISPLAY.get(key, "⚠️ INCONCLUSIVE"), key, summary

    return "⚠️ INCONCLUSIVE", "inconclusive", "Agent did not emit a structured verdict line"


# ── Artifact saving ───────────────────────────────────────────


def save_artifacts(history: AgentHistoryList, issue: dict, repro_dir: Path) -> None:
    """Extract and save all reproduction artifacts from browser-use history."""
    issue_id = issue["number"]

    # 1. Action log
    action_log = []
    for i, step in enumerate(history.history):
        entry: dict = {
            "step": i + 1,
            "timestamp": datetime.now().isoformat(),
        }
        if step.model_output:
            entry["thought"] = str(getattr(step.model_output, "current_state", ""))
            actions = getattr(step.model_output, "action", [])
            entry["actions"] = [str(a) for a in actions] if actions else []
        else:
            entry["thought"] = ""
            entry["actions"] = []

        if step.result:
            entry["results"] = []
            for r in step.result:
                entry["results"].append({
                    "extracted_content": getattr(r, "extracted_content", None),
                    "error": getattr(r, "error", None),
                    "is_done": getattr(r, "is_done", False),
                })
        else:
            entry["results"] = []

        entry["url"] = getattr(step.state, "url", "") if step.state else ""
        action_log.append(entry)

    (repro_dir / "action-log.json").write_text(json.dumps(action_log, indent=2))
    print(f"  📁 Action log: {len(action_log)} steps")

    # 2. Screenshots
    screenshots = history.screenshots()
    saved = 0
    for i, b64 in enumerate(screenshots):
        if b64:
            (repro_dir / f"evidence-{i:02d}.png").write_bytes(base64.b64decode(b64))
            saved += 1
    print(f"  📸 Screenshots: {saved}")

    # 3. Full trace
    traces_dir = repro_dir / "traces"
    traces_dir.mkdir(exist_ok=True)
    try:
        history.save_to_file(str(traces_dir / "full-trace.json"))
        print("  📁 Full trace saved")
    except Exception as e:
        print(f"  ⚠️ Could not save full trace: {e}")

    # 4. Verdict
    result_text = history.final_result() or ""
    status, verdict_key, summary = parse_verdict(result_text)

    verdict_md = f"""# Reproduction Verdict — #{issue_id}

**Status:** {status}
**Summary:** {summary}
**Issue:** [{issue["title"]}]({issue["url"]})
**Tool:** browser-use + {MODEL} via OpenRouter
**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Agent Result

{result_text}

## Run Statistics

- Steps: {history.number_of_steps()}
- Duration: {history.total_duration_seconds():.1f}s
- Actions: {", ".join(history.action_names()[:20])}
- URLs visited: {", ".join(history.urls()[:10])}

## Evidence

- Screenshots: `evidence-*.png`
- Action log: `action-log.json`
- Full trace: `traces/full-trace.json`
- Agent GIF: `agent-run.gif`
"""
    (repro_dir / "verdict.md").write_text(verdict_md)
    print(f"  📄 Verdict: {status} — {summary}")


# ── Main ──────────────────────────────────────────────────────


async def run(issue_number: str, repo: str, *, dry_run: bool = False, timeout: int = 300) -> str:
    """Fetch issue, build prompt, run agent, save artifacts.

    Returns verdict key: 'reproduced', 'not_reproduced', or 'inconclusive'.
    """
    if not OPENROUTER_API_KEY:
        print("❌ Set OPENROUTER_API_KEY in .env")
        sys.exit(EXIT_ERROR)

    # ── CDP: auto-discover or use env ─────────────────────────
    cdp_url = CDP_URL or discover_cdp_url()
    if not cdp_url:
        print("❌ Chrome not found. Start Chrome with --remote-debugging-port=9222")
        print("   Or set CDP_URL in .env")
        sys.exit(EXIT_ERROR)

    # ── Pre-flight checks ─────────────────────────────────────
    preflight(cdp_url, PLANE_URL)

    # ── Fetch issue ───────────────────────────────────────────
    print(f"\n── Fetching issue #{issue_number} from {repo} ──")
    issue = fetch_issue(issue_number, repo)
    task = build_task(issue)

    repro_dir = Path(f"reproductions/{issue['number']}")
    repro_dir.mkdir(parents=True, exist_ok=True)
    (repro_dir / "traces").mkdir(exist_ok=True)

    # Save issue + prompt for debugging
    (repro_dir / "issue.json").write_text(json.dumps(issue, indent=2))
    (repro_dir / "task-prompt.txt").write_text(task)

    if dry_run:
        print("\n── DRY RUN — prompt generated, not running agent ──")
        print(f"  Prompt saved: {repro_dir}/task-prompt.txt")
        print(f"  Issue saved:  {repro_dir}/issue.json")
        print(f"\n{task}")
        return "dry_run"

    print("╔══════════════════════════════════════════════════════╗")
    print("║  DRIVE — browser-use bug reproduction               ║")
    print("╚══════════════════════════════════════════════════════╝")
    print(f"  issue    : #{issue['number']} — {issue['title']}")
    print(f"  repo     : {repo}")
    print(f"  model    : {MODEL}")
    print(f"  cdp      : {cdp_url}")
    print(f"  plane    : {PLANE_URL}")
    print(f"  output   : {repro_dir}/")
    print()

    # ── Configure browser ─────────────────────────────────────
    profile = BrowserProfile(
        cdp_url=cdp_url,
        headless=False,
        viewport={"width": 1280, "height": 720},
        highlight_elements=True,
        record_video_dir=str(repro_dir),
    )
    browser = Browser(browser_profile=profile)

    # ── Configure LLM ─────────────────────────────────────────
    llm = ChatOpenAI(
        model=MODEL,
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        temperature=0.0,
        default_headers={
            "HTTP-Referer": "https://github.com/repro-agent",
            "X-Title": "Bug Repro Agent",
        },
    )

    # ── Run agent (crash-safe) ────────────────────────────────
    print("── Starting browser-use agent ──")

    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        use_vision=True,
        generate_gif=str(repro_dir / "agent-run.gif"),
        save_conversation_path=str(repro_dir / "conversation.json"),
        sensitive_data={"x_password": PLANE_PASSWORD},
        max_failures=5,
        max_actions_per_step=5,
    )

    history = None
    agent_error = None
    try:
        history = await asyncio.wait_for(
            agent.run(max_steps=50), timeout=timeout
        )
    except asyncio.TimeoutError:
        agent_error = f"Agent timed out after {timeout}s"
        print(f"\n💀 {agent_error}")
    except Exception as e:
        agent_error = f"{type(e).__name__}: {e}"
        print(f"\n💀 Agent run failed: {agent_error}")
    finally:
        # ── Save artifacts FIRST (before closing browser) ─────
        # browser.close() can hang if Chrome is unresponsive.
        # Artifacts come from the in-memory history object, so
        # saving them doesn't need a live browser connection.
        print("\n── Saving artifacts ──")
        if history and history.history:
            save_artifacts(history, issue, repro_dir)
        else:
            print("  ⚠️ No agent history — saving error report only")

        if agent_error:
            (repro_dir / "error.txt").write_text(
                f"Agent error: {agent_error}\n"
                f"Time: {datetime.now().isoformat()}\n"
            )
            print(f"  💀 Error saved: {repro_dir}/error.txt")

        # ── THEN close browser (with timeout) ─────────────────
        try:
            await asyncio.wait_for(browser.close(), timeout=10)
        except Exception:
            pass

    # ── Summary ───────────────────────────────────────────────
    if history and history.history:
        result = history.final_result() or "(no result)"
        status, verdict_key, summary = parse_verdict(result)
        print(f"\n{'═' * 54}")
        print(f"  Issue     : #{issue['number']} — {issue['title']}")
        print(f"  Steps     : {history.number_of_steps()}")
        print(f"  Duration  : {history.total_duration_seconds():.1f}s")
        print(f"  Verdict   : {status}")
        print(f"  Summary   : {summary}")
        print(f"  Artifacts : {repro_dir}/")
        print(f"{'═' * 54}")
        print("\n✅ DRIVE COMPLETE")
        return verdict_key
    else:
        print(f"\n{'═' * 54}")
        print(f"  Issue     : #{issue['number']} — {issue['title']}")
        print(f"  Verdict   : 💀 CRASHED")
        print(f"  Error     : {agent_error}")
        print(f"  Artifacts : {repro_dir}/ (partial)")
        print(f"{'═' * 54}")
        return "error"


def cli():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Reproduce any GitHub issue in a running Plane instance",
        epilog="Examples:\n"
               "  python scripts/drive.py --issue 9329\n"
               "  python scripts/drive.py --issue 9329 --repo makeplane/plane\n"
               "  python scripts/drive.py --url https://github.com/makeplane/plane/issues/9329\n"
               "  python scripts/drive.py --issue 9329 --dry-run\n"
               "  python scripts/drive.py --issue 9329 --timeout 600\n"
               "\nExit codes: 0=reproduced, 1=not reproduced, 2=inconclusive, 3=error",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--issue", help="Issue number (uses --repo for the repository)")
    group.add_argument("--url", help="Full GitHub issue URL")
    parser.add_argument(
        "--repo", default=DEFAULT_REPO,
        help=f"GitHub repo (default: {DEFAULT_REPO})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Generate prompt and exit without running agent",
    )
    parser.add_argument(
        "--timeout", type=int, default=300,
        help="Agent timeout in seconds (default: 300)",
    )
    args = parser.parse_args()

    if args.url:
        m = re.match(r"https?://github\.com/([^/]+/[^/]+)/issues/(\d+)", args.url)
        if not m:
            print(f"❌ Invalid GitHub issue URL: {args.url}")
            sys.exit(EXIT_ERROR)
        repo, issue_number = m.group(1), m.group(2)
    else:
        repo, issue_number = args.repo, args.issue

    verdict = asyncio.run(run(issue_number, repo, dry_run=args.dry_run, timeout=args.timeout))
    sys.exit(VERDICT_EXIT_CODES.get(verdict, EXIT_ERROR))


if __name__ == "__main__":
    cli()
