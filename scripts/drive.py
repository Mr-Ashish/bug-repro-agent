#!/usr/bin/env python3
"""
browser-use bug reproduction driver.

Replaces the old Stagehand TypeScript drivers. Single script handles all issues.
Usage: python scripts/drive.py --issue 9329
"""
import asyncio
import argparse
import json
import base64
import os
import sys
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

LONG_TITLE = "A" * 256

# ── Issue-specific task prompts ───────────────────────────────

ISSUE_TASKS: dict[str, dict] = {
    "9329": {
        "title": "255+ char title shows generic error instead of descriptive",
        "url": "https://github.com/makeplane/plane/issues/9329",
        "bug_class": "form-validation",
        "task": f"""You are a QA engineer reproducing a bug in Plane (project management app at {PLANE_URL}).

BUG: When creating a work item with a title longer than 255 characters, the error
message should say "Title should be less than 255 characters" but instead shows
a generic "Some error occurred" toast.

STEPS — follow these EXACTLY:
1. You are on the Plane login page. Enter email "{PLANE_EMAIL}" and click Continue.
2. Enter password "{PLANE_PASSWORD}" and click "Go to workspace".
3. Wait for the dashboard to load. Navigate to the SEED project's Issues/Work Items page.
   URL pattern: {PLANE_URL}/{PLANE_WORKSPACE}/projects/*/issues
4. Click the "Add work item" button (or similar — might say "Add Item", "New Issue", etc).
5. In the Title field, type exactly this 256-character string: {LONG_TITLE}
6. Press Enter or click Create/Submit to save the work item.
7. OBSERVE what happens. Look for any error message, toast notification, or validation text.

REPORT your findings:
- What is the EXACT error message text you see?
- Is it DESCRIPTIVE (mentions "255 characters" or character limit)?
- Or is it GENERIC (says "Some error occurred" or similar vague text)?
- Or did it succeed with NO error?

Be precise about the exact error text you observe.""",
    },

    "9050": {
        "title": "Deleted stickies reappear after page reload",
        "url": "https://github.com/makeplane/plane/issues/9050",
        "bug_class": "state-persistence",
        "task": f"""You are a QA engineer reproducing a bug in Plane (project management app at {PLANE_URL}).

BUG: When you delete a sticky note and reload the page, the deleted sticky reappears.

STEPS — follow these EXACTLY:
1. You are on the Plane login page. Enter email "{PLANE_EMAIL}" and click Continue.
2. Enter password "{PLANE_PASSWORD}" and click "Go to workspace".
3. Wait for the dashboard to load.
4. Navigate to the Stickies section. Look for "Stickies" in the sidebar or navigate to
   {PLANE_URL}/{PLANE_WORKSPACE}/stickies
5. Create a NEW sticky note with this UNIQUE text: "REPRO-9050-DELETE-TEST"
6. Verify the sticky was created and is visible.
7. DELETE that sticky (right-click → delete, or find the delete option).
8. Verify the sticky is GONE from the page.
9. RELOAD the page (press F5 or navigate away and back).
10. Check: Is the deleted sticky "REPRO-9050-DELETE-TEST" still gone, or did it reappear?

REPORT your findings:
- Did the sticky reappear after reload? (BUG REPRODUCED)
- Or did it stay deleted? (BUG NOT REPRODUCED)
- Include what you see on the stickies page after reload.""",
    },

    "9124": {
        "title": "Sub-task expand requires 3 clicks instead of 1",
        "url": "https://github.com/makeplane/plane/issues/9124",
        "bug_class": "ui-interaction",
        "task": f"""You are a QA engineer reproducing a bug in Plane (project management app at {PLANE_URL}).

BUG: Expanding a sub-task in the issue list requires 3 clicks on the expand arrow
instead of 1 click. The first two clicks do nothing visible.

STEPS — follow these EXACTLY:
1. You are on the Plane login page. Enter email "{PLANE_EMAIL}" and click Continue.
2. Enter password "{PLANE_PASSWORD}" and click "Go to workspace".
3. Wait for the dashboard to load.
4. Navigate to the SEED project's Issues/Work Items page.
   URL pattern: {PLANE_URL}/{PLANE_WORKSPACE}/projects/*/issues
5. Find a work item/issue that HAS sub-tasks (look for expand arrows or child indicators).
6. Click the expand/collapse arrow ONCE. Did the sub-tasks appear?
7. If not, click again. Did they appear on the second click?
8. If not, click a third time. Did they appear on the third click?

REPORT your findings:
- How many clicks did it take to expand the sub-tasks? (1, 2, or 3)
- If it took more than 1 click, describe what happened on each click.
- If there are no sub-tasks visible, say so.""",
    },
}

# ── Artifact saving ───────────────────────────────────────────


def save_artifacts(history: AgentHistoryList, issue_id: str, repro_dir: Path, issue: dict) -> None:
    """Extract and save all reproduction artifacts from browser-use history."""

    # 1. Action log — step-by-step trace
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

        if step.state:
            entry["url"] = getattr(step.state, "url", "")
        else:
            entry["url"] = ""

        action_log.append(entry)

    (repro_dir / "action-log.json").write_text(json.dumps(action_log, indent=2))
    print(f"  📁 Action log: {len(action_log)} steps → {repro_dir}/action-log.json")

    # 2. Screenshots — save each step's screenshot as PNG
    screenshots = history.screenshots()
    saved_count = 0
    for i, b64 in enumerate(screenshots):
        if b64:
            path = repro_dir / f"evidence-{i:02d}.png"
            path.write_bytes(base64.b64decode(b64))
            saved_count += 1
    print(f"  📸 Screenshots: {saved_count} saved to {repro_dir}/evidence-*.png")

    # 3. Full trace — browser-use native format
    traces_dir = repro_dir / "traces"
    traces_dir.mkdir(exist_ok=True)
    try:
        history.save_to_file(str(traces_dir / "full-trace.json"))
        print(f"  📁 Full trace → {traces_dir}/full-trace.json")
    except Exception as e:
        print(f"  ⚠️ Could not save full trace: {e}")

    # 4. Verdict
    result_text = history.final_result() or ""
    verdict_md = generate_verdict(issue_id, issue, result_text, history)
    (repro_dir / "verdict.md").write_text(verdict_md)
    print(f"  📄 Verdict → {repro_dir}/verdict.md")


def generate_verdict(issue_id: str, issue: dict, result_text: str, history: AgentHistoryList) -> str:
    """Generate verdict.md from agent's final result."""
    result_lower = result_text.lower()

    # Issue-specific verdict logic
    # IMPORTANT: Match against the agent's CONCLUSION, not quotes from the bug report.
    # The agent text often contains the bug description as context (e.g. "Some error occurred"
    # as a quote), so naive keyword matching causes false positives.

    if issue_id == "9329":
        # Check for NOT REPRODUCED first (agent says bug behavior was NOT observed)
        not_repro_signals = [
            "does not appear" in result_lower,
            "not present" in result_lower,
            "bug not reproduced" in result_lower,
            "correct behavior" in result_lower,
            "correctly showing" in result_lower,
            ("descriptive" in result_lower and "not generic" in result_lower),
        ]
        repro_signals = [
            "generic error" in result_lower and "descriptive" not in result_lower,
            "bug is reproduced" in result_lower,
            "bug reproduced" in result_lower and "not" not in result_lower.split("reproduced")[0][-10:],
        ]
        if any(not_repro_signals):
            status = "❌ NOT REPRODUCED"
            reproduced = False
            confidence = "high"
        elif any(repro_signals):
            status = "✅ REPRODUCED"
            reproduced = True
            confidence = "high"
        else:
            status = "⚠️ INCONCLUSIVE"
            reproduced = False
            confidence = "low"

    elif issue_id == "9050":
        not_repro_signals = [
            "stayed deleted" in result_lower,
            "did not reappear" in result_lower,
            "still gone" in result_lower,
            "bug not reproduced" in result_lower,
            "not reproduced" in result_lower,
        ]
        repro_signals = [
            "reappear" in result_lower and "did not reappear" not in result_lower,
            "came back" in result_lower,
            "still there" in result_lower,
            "bug reproduced" in result_lower,
        ]
        if any(not_repro_signals):
            status = "❌ NOT REPRODUCED"
            reproduced = False
            confidence = "high"
        elif any(repro_signals):
            status = "✅ REPRODUCED"
            reproduced = True
            confidence = "high"
        else:
            status = "⚠️ INCONCLUSIVE"
            reproduced = False
            confidence = "low"

    elif issue_id == "9124":
        not_repro_signals = [
            "1 click" in result_lower,
            "one click" in result_lower,
            "single click" in result_lower,
            "first click" in result_lower and "did not" not in result_lower,
            "expanded on the first" in result_lower,
        ]
        repro_signals = [
            "3 click" in result_lower,
            "three click" in result_lower,
            "took 3" in result_lower,
            "required 3" in result_lower,
            "third click" in result_lower and "expanded" in result_lower,
        ]
        if any(not_repro_signals):
            status = "❌ NOT REPRODUCED"
            reproduced = False
            confidence = "high"
        elif any(repro_signals):
            status = "✅ REPRODUCED"
            reproduced = True
            confidence = "high"
        else:
            status = "⚠️ INCONCLUSIVE"
            reproduced = False
            confidence = "low"

    else:
        status = "⚠️ INCONCLUSIVE"
        reproduced = False
        confidence = "low"

    return f"""# Reproduction Verdict — #{issue_id}

**Status:** {status}
**Confidence:** {confidence}
**Issue:** [{issue["title"]}]({issue["url"]})
**Bug class:** {issue["bug_class"]}
**Tool:** browser-use (Python) + Claude Sonnet 4 via OpenRouter
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

## Identity

This agent is a **reproducer**, not a fixer.
Allowed verdicts: REPRODUCED / NOT REPRODUCED / INCONCLUSIVE
"""


# ── Main ──────────────────────────────────────────────────────


async def run(issue_id: str) -> None:
    """Run browser-use agent to reproduce a bug."""
    if issue_id not in ISSUE_TASKS:
        print(f"❌ Unknown issue: {issue_id}")
        print(f"   Available: {', '.join(ISSUE_TASKS.keys())}")
        sys.exit(1)

    if not CDP_URL:
        print("❌ Set CDP_URL in .env (e.g. ws://localhost:9222/devtools/browser/...)")
        sys.exit(1)

    if not OPENROUTER_API_KEY:
        print("❌ Set OPENROUTER_API_KEY in .env")
        sys.exit(1)

    issue = ISSUE_TASKS[issue_id]
    repro_dir = Path(f"reproductions/{issue_id}")
    repro_dir.mkdir(parents=True, exist_ok=True)
    (repro_dir / "traces").mkdir(exist_ok=True)

    print("╔══════════════════════════════════════════════════════╗")
    print("║  DRIVE — browser-use bug reproduction               ║")
    print("╚══════════════════════════════════════════════════════╝")
    print(f"  issue    : #{issue_id} — {issue['title']}")
    print(f"  model    : {MODEL}")
    print(f"  cdp      : {CDP_URL}")
    print(f"  plane    : {PLANE_URL}")
    print(f"  output   : {repro_dir}/")
    print()

    # ── Configure browser ─────────────────────────────────────
    profile = BrowserProfile(
        cdp_url=CDP_URL,
        headless=False,
        viewport={"width": 1280, "height": 720},
        highlight_elements=True,
        record_video_dir=str(repro_dir),
    )
    browser = Browser(browser_profile=profile)

    # ── Configure LLM — Claude via OpenRouter ─────────────────
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

    # ── Create and run agent ──────────────────────────────────
    print("── Starting browser-use agent ──")

    agent = Agent(
        task=issue["task"],
        llm=llm,
        browser=browser,
        use_vision=True,
        generate_gif=str(repro_dir / "agent-run.gif"),
        save_conversation_path=str(repro_dir / "conversation.json"),
        sensitive_data={
            "x_password": PLANE_PASSWORD,
        },
        max_failures=5,
        max_actions_per_step=5,
    )

    try:
        history = await agent.run(max_steps=50)
    except Exception as e:
        print(f"\n💀 Agent run failed: {e}")
        raise
    finally:
        # Always try to close browser session
        try:
            await browser.close()
        except Exception:
            pass

    # ── Save artifacts ────────────────────────────────────────
    print("\n── Saving artifacts ──")
    save_artifacts(history, issue_id, repro_dir, issue)

    # ── Summary ───────────────────────────────────────────────
    result = history.final_result() or "(no result)"
    print(f"\n{'═' * 54}")
    print(f"  Issue     : #{issue_id}")
    print(f"  Steps     : {history.number_of_steps()}")
    print(f"  Duration  : {history.total_duration_seconds():.1f}s")
    print(f"  Successful: {history.is_successful()}")
    print(f"  Result    : {result[:200]}")
    print(f"  Artifacts : {repro_dir}/")
    print(f"{'═' * 54}")
    print("\n✅ DRIVE COMPLETE")


def cli():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="browser-use bug reproduction driver")
    parser.add_argument(
        "--issue",
        required=True,
        help="Issue number to reproduce (e.g. 9329, 9050, 9124)",
    )
    args = parser.parse_args()
    asyncio.run(run(args.issue))


if __name__ == "__main__":
    cli()
