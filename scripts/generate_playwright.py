#!/usr/bin/env python3
"""
generate_playwright.py — Convert a browser-use action-log.json into a Playwright test.

Reads the action log from a reproduction run and emits a deterministic
Playwright (Python) test that replays the same steps. The test is meant
to be runnable standalone for regression verification.

Usage:
    python scripts/generate_playwright.py --issue 8591
    python scripts/generate_playwright.py --issue 8591 --output test_8591.py
"""

import argparse
import json
import re
import sys
import textwrap
from pathlib import Path


# ── Action → Playwright mapping ──────────────────────────────

def parse_action(action_str: str) -> dict | None:
    """Parse a browser-use action string into {type, params}."""
    # browser-use actions look like: ActionName(param1=value1, param2=value2)
    m = re.match(r"(\w+)\((.+)\)", action_str, re.DOTALL)
    if not m:
        return None
    name = m.group(1)
    params_str = m.group(2)

    params = {}
    # Simple key=value parsing (handles quoted strings)
    for kv in re.finditer(r"(\w+)=(?:'([^']*)'|\"([^\"]*)\"|(\d+(?:\.\d+)?)|(\[.*?\]))", params_str):
        key = kv.group(1)
        val = kv.group(2) or kv.group(3) or kv.group(4) or kv.group(5)
        if kv.group(4):
            val = int(val) if "." not in val else float(val)
        params[key] = val

    return {"type": name, "params": params}


def action_to_playwright(action: dict, step_num: int) -> str | None:
    """Convert a parsed action to a Playwright code line."""
    t = action["type"].lower()
    p = action["params"]

    if t == "navigate" or t == "go_to_url":
        url = p.get("url", "")
        return f'    await page.goto("{url}")'

    elif t == "click" or t == "click_element":
        index = p.get("index", p.get("element_id", ""))
        desc = p.get("description", "")
        if desc:
            return f'    # Click: {desc}\n    await page.locator("[data-step-{step_num}]").click()  # element index {index}'
        return f'    await page.locator("[data-step-{step_num}]").click()  # element index {index}'

    elif t == "input_text" or t == "type":
        text = p.get("text", p.get("value", ""))
        index = p.get("index", "")
        return f'    await page.locator("[data-step-{step_num}]").fill("{text}")  # element index {index}'

    elif t == "scroll":
        direction = p.get("direction", "down")
        amount = p.get("amount", 300)
        if direction == "down":
            return f'    await page.mouse.wheel(0, {amount})'
        elif direction == "up":
            return f'    await page.mouse.wheel(0, -{amount})'

    elif t == "wait":
        duration = p.get("duration", p.get("seconds", 2))
        return f'    await page.wait_for_timeout({int(float(str(duration)) * 1000)})'

    elif t == "key_press" or t == "press_key":
        key = p.get("key", "")
        return f'    await page.keyboard.press("{key}")'

    elif t == "write_file":
        return None  # Skip file writes

    return f'    # TODO: Unsupported action: {action["type"]}({action["params"]})'


# ── Test generator ────────────────────────────────────────────

def generate_test(issue_number: str, repro_dir: Path) -> str:
    """Generate a Playwright test from action-log.json."""
    action_log_path = repro_dir / "action-log.json"
    verdict_path = repro_dir / "verdict.md"
    issue_path = repro_dir / "issue.json"

    if not action_log_path.exists():
        print(f"❌ No action-log.json in {repro_dir}")
        sys.exit(1)

    actions = json.loads(action_log_path.read_text())
    
    # Read issue info
    issue_title = f"Issue #{issue_number}"
    if issue_path.exists():
        issue_data = json.loads(issue_path.read_text())
        issue_title = issue_data.get("title", issue_title)

    # Read verdict
    verdict_status = "unknown"
    verdict_summary = ""
    if verdict_path.exists():
        for line in verdict_path.read_text().splitlines():
            if line.startswith("**Status:**"):
                verdict_status = line.split("**Status:**")[1].strip()
            elif line.startswith("**Summary:**"):
                verdict_summary = line.split("**Summary:**")[1].strip()

    # Build Playwright steps
    pw_steps = []
    urls_visited = []
    
    for entry in actions:
        step = entry.get("step", 0)
        thought = entry.get("thought", "")
        url = entry.get("url", "")
        
        if url and url not in urls_visited:
            urls_visited.append(url)

        for action_str in entry.get("actions", []):
            parsed = parse_action(action_str)
            if parsed:
                pw_line = action_to_playwright(parsed, step)
                if pw_line:
                    # Add the agent's thought as a comment
                    if thought:
                        # Extract just the key thought, truncate
                        clean_thought = thought.replace("\n", " ").strip()[:120]
                        if clean_thought:
                            pw_steps.append(f'    # Step {step}: {clean_thought}')
                    pw_steps.append(pw_line)

    # Determine the base URL from visited URLs
    base_url = "http://localhost:80"
    if urls_visited:
        from urllib.parse import urlparse
        parsed = urlparse(urls_visited[0])
        base_url = f"{parsed.scheme}://{parsed.netloc}"

    steps_code = "\n".join(pw_steps) if pw_steps else "    # No actionable steps extracted — review action-log.json manually"

    test_code = textwrap.dedent(f'''\
        """
        Playwright regression test for {issue_title}
        
        Auto-generated from browser-use reproduction run.
        Original verdict: {verdict_status} — {verdict_summary}
        
        This test replays the reproduction steps. Selectors marked with
        [data-step-N] are placeholders — replace with actual selectors
        from the Plane UI.
        
        Usage:
            pip install pytest-playwright
            playwright install chromium
            pytest {f"test_{issue_number}.py"} -v
        """
        
        import pytest
        from playwright.async_api import async_playwright, expect
        
        
        BASE_URL = "{base_url}"
        EMAIL = "admin@admin.com"
        PASSWORD = "qweQWE123!@#"
        WORKSPACE = "plane-dev"
        
        
        @pytest.fixture
        async def authenticated_page():
            """Launch browser and log into Plane."""
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(viewport={{"width": 1920, "height": 1080}})
                
                # Login
                await page.goto(f"{{BASE_URL}}")
                await page.fill('input[name="email"]', EMAIL)
                await page.fill('input[name="password"]', PASSWORD)
                await page.click('button[type="submit"]')
                await page.wait_for_url(f"**/{WORKSPACE}/**", timeout=15000)
                
                yield page
                
                await browser.close()
        
        
        @pytest.mark.asyncio
        async def test_issue_{issue_number}(authenticated_page):
            """
            Regression test: {issue_title}
            
            Expected: {verdict_summary or "see original bug report"}
            """
            page = authenticated_page
            
        {steps_code}
            
            # Verify final state
            # TODO: Add assertions based on the expected behavior from the bug report
            # If bug was REPRODUCED, assert the buggy behavior is now fixed
            # If NOT_REPRODUCED, assert the correct behavior still holds
    ''')

    return test_code


# ── CLI ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate a Playwright test from a reproduction action log",
    )
    parser.add_argument("--issue", required=True, help="Issue number")
    parser.add_argument("--output", "-o", help="Output file (default: reproductions/<issue>/test_<issue>.py)")
    parser.add_argument("--dir", help="Reproductions directory (default: reproductions/<issue>/)")
    args = parser.parse_args()

    repro_dir = Path(args.dir) if args.dir else Path(f"reproductions/{args.issue}")
    output_path = Path(args.output) if args.output else repro_dir / f"test_{args.issue}.py"

    test_code = generate_test(args.issue, repro_dir)
    output_path.write_text(test_code)
    print(f"✅ Playwright test written to {output_path}")
    print(f"   Run: pytest {output_path} -v")


if __name__ == "__main__":
    main()
