#!/usr/bin/env python3
"""
generate_playwright.py — Emit a skeleton Playwright test from a reproduction run.

Produces a MINIMAL scaffold with:
  - Working login() fixture for Plane's two-step auth
  - Raw action log dumped as structured comments (action, result, URL)
  - Empty test body for the meta-agent to fill in with real selectors

The meta-agent reads this skeleton + action-log.json, then rewrites
the test with proper Playwright selectors and assertions.

Usage:
    python scripts/generate_playwright.py --issue 9329
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


def generate_test(issue_number: str, repro_dir: Path) -> str:
    """Generate a skeleton Playwright test from reproduction artifacts."""
    action_log_path = repro_dir / "action-log.json"
    verdict_path = repro_dir / "verdict.md"
    issue_path = repro_dir / "issue.json"

    if not action_log_path.exists():
        print(f"❌ No action-log.json in {repro_dir}")
        sys.exit(1)

    action_log = json.loads(action_log_path.read_text())

    # ── Read metadata ─────────────────────────────────────────
    issue_title = f"Issue #{issue_number}"
    issue_body = ""
    if issue_path.exists():
        issue_data = json.loads(issue_path.read_text())
        issue_title = issue_data.get("title", issue_title)
        issue_body = issue_data.get("body", "")

    verdict_status = "unknown"
    verdict_summary = ""
    if verdict_path.exists():
        for line in verdict_path.read_text().splitlines():
            if line.startswith("**Status:**"):
                verdict_status = line.split("**Status:**")[1].strip()
            elif line.startswith("**Summary:**"):
                verdict_summary = line.split("**Summary:**")[1].strip()

    # ── Detect base URL ──────────────────────────────────────
    base_url = "http://localhost:80"
    for entry in action_log:
        url = entry.get("url", "")
        if url and url != "about:blank":
            p = urlparse(url)
            base_url = f"{p.scheme}://{p.netloc}"
            break

    # ── Build raw action log as structured comments ──────────
    step_comments = []
    for entry in action_log:
        step_num = entry.get("step", "?")
        url = entry.get("url", "")
        actions = entry.get("actions", [])
        results = entry.get("results", [])

        # Format each action
        for i, action in enumerate(actions):
            if isinstance(action, dict):
                action_str = json.dumps(action)
            else:
                action_str = str(action)

            result_str = ""
            if i < len(results):
                r = results[i]
                content = r.get("extracted_content", "")
                error = r.get("error", "")
                if error:
                    result_str = f"ERROR: {error}"
                elif content:
                    result_str = str(content)[:120]

            step_comments.append(
                f"    # Step {step_num}: {action_str[:200]}"
            )
            if result_str:
                step_comments.append(
                    f"    #   → {result_str}"
                )
            if url:
                step_comments.append(
                    f"    #   URL: {url}"
                )
            step_comments.append("")

    steps_block = "\n".join(step_comments) if step_comments else "    # No steps in action log"

    # ── Extract repro steps from issue body ───────────────────
    repro_steps = ""
    if "steps to reproduce" in issue_body.lower():
        in_steps = False
        for line in issue_body.splitlines():
            if "steps to reproduce" in line.lower():
                in_steps = True
                continue
            elif in_steps and line.startswith("###"):
                break
            elif in_steps and line.strip():
                repro_steps += f"    {line}\n"

    # ── Emit skeleton ─────────────────────────────────────────
    test_code = f'''"""
Playwright regression test for: {issue_title}

Auto-generated SKELETON by bug-repro-agent.
The meta-agent should rewrite this with real Playwright selectors and assertions.

Verdict: {verdict_status} — {verdict_summary}

Steps from bug report:
{repro_steps or "    (see issue body)"}

Usage:
    pytest {f"test_{issue_number}.py"} -v --headed    # watch it run
    pytest {f"test_{issue_number}.py"} -v              # headless
"""

from playwright.sync_api import Page, expect


# ── Config ────────────────────────────────────────────────────

BASE_URL = "{base_url}"
EMAIL = "admin@admin.com"
PASSWORD = "qweQWE123!@#"
WORKSPACE = "plane-dev"


# ── Fixtures ──────────────────────────────────────────────────

def login(page: Page) -> None:
    """Log into Plane (two-step: email → continue → password → submit)."""
    page.goto(f"{{BASE_URL}}")
    page.wait_for_load_state("networkidle")

    # Step 1: Enter email and click Continue
    page.locator('input[name="email"]').fill(EMAIL)
    page.locator('button:has-text("Continue")').click()
    page.wait_for_timeout(1000)

    # Step 2: Enter password and click Go to workspace
    page.locator('input[type="password"]').fill(PASSWORD)
    page.locator('button:has-text("Go to workspace")').click()

    # Wait for workspace dashboard or onboarding
    page.wait_for_url(f"**/{{WORKSPACE}}/**", timeout=15000)
    page.wait_for_load_state("networkidle")

    # Handle onboarding if it appears
    if "/onboarding/" in page.url:
        continue_btn = page.locator('button:has-text("Continue")')
        if continue_btn.is_visible(timeout=3000):
            continue_btn.click()
            page.wait_for_url(f"**/{{WORKSPACE}}/**", timeout=15000)
            page.wait_for_load_state("networkidle")


# ── Test ──────────────────────────────────────────────────────

def test_issue_{issue_number}(page: Page) -> None:
    """
    Regression test: {issue_title}

    Expected behavior: {verdict_summary or "see original bug report"}
    """
    login(page)

    # ══════════════════════════════════════════════════════════
    # RAW ACTION LOG — meta-agent: rewrite these comments as
    # real Playwright calls with proper selectors and assertions.
    #
    # Each step shows: action JSON, result, and URL at that point.
    # Use the result text (e.g. Clicked button "X") to pick selectors.
    # See action-log.json for full details.
    # ══════════════════════════════════════════════════════════

{steps_block}
    # ── Assertions ────────────────────────────────────────────
    # TODO: meta-agent should add assertions here based on the verdict.
    pass
'''

    return test_code


# ── CLI ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate a skeleton Playwright test from a reproduction action log",
    )
    parser.add_argument("--issue", required=True, help="Issue number")
    parser.add_argument(
        "--output", "-o",
        help="Output file (default: reproductions/<issue>/test_<issue>.py)",
    )
    parser.add_argument(
        "--dir",
        help="Reproductions directory (default: reproductions/<issue>/)",
    )
    args = parser.parse_args()

    repro_dir = Path(args.dir) if args.dir else Path(f"reproductions/{args.issue}")
    output_path = (
        Path(args.output) if args.output
        else repro_dir / f"test_{args.issue}.py"
    )

    test_code = generate_test(args.issue, repro_dir)
    output_path.write_text(test_code)
    print(f"✅ Playwright skeleton: {output_path}")
    print(f"   Meta-agent should refine with real selectors")


if __name__ == "__main__":
    main()
