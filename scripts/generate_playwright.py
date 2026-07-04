#!/usr/bin/env python3
"""
generate_playwright.py — Convert a reproduction run into a Playwright test.

Reads action-log.json + verdict.md from a reproduction run and generates
a Playwright (sync API, pytest-playwright) test. The test captures the
reproduction flow as documented steps with the actual URLs visited.

Usage:
    python scripts/generate_playwright.py --issue 8591
    python scripts/generate_playwright.py --issue 8591 --output test_8591.py
"""

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


# ── Action parsing ────────────────────────────────────────────

def parse_action_str(action_str: str) -> dict | None:
    """Parse browser-use action strings.

    Handles the nested format from browser-use:
        root=ClickActionModel(click=ClickElementAction(index=1103, ...))
        root=InputActionModel(input=InputTextAction(index=3547, text='Test State', clear=True))
        root=NavigateActionModel(navigate=NavigateAction(url='http://...'))
        root=ScrollActionModel(scroll=ScrollAction(direction='down', amount=300))
        root=EvaluateActionModel(evaluate=EvaluateAction(code='...'))
        root=DoneActionModel(done=DoneAction(text='...'))
    """
    # Detect the action type from the outer model name
    type_match = re.search(r"root=(\w+)ActionModel", action_str)
    if not type_match:
        # Fallback: try simple format like 'click(index=5)'
        m = re.match(r"(\w+)\((.+)\)", action_str, re.DOTALL)
        if not m:
            return None
        name = m.group(1).lower()
        raw = m.group(2)
    else:
        name = type_match.group(1).lower()
        raw = action_str

    params = {}

    # Extract key=value pairs from anywhere in the string
    # Handles: index=1103, text='Test State', url='http://...', clear=True
    for kv in re.finditer(
        r"(\w+)\s*=\s*(?:'([^']*)'|\"([^\"]*)\"|(\d+(?:\.\d+)?)|(\w+))",
        raw,
    ):
        key = kv.group(1)
        val = kv.group(2) or kv.group(3) or kv.group(4) or kv.group(5)
        # Skip internal model field names
        if key in ("root", "click", "input", "navigate", "scroll",
                    "evaluate", "done", "wait", "extract", "search",
                    "coordinate_x", "coordinate_y"):
            continue
        if kv.group(4):
            val = float(val) if "." in val else int(val)
        params[key] = val

    return {"type": name, "params": params}


def _result_text_for(results: list[dict], action_idx: int = 0) -> str:
    """Get extracted_content from the result matching this action index."""
    if action_idx < len(results):
        return results[action_idx].get("extracted_content", "") or ""
    return ""


def _selector_from_result(result_text: str) -> str | None:
    """Parse a browser-use result string into a Playwright selector.

    Result strings look like:
        'Clicked button "Continue"'
        'Clicked a "Work items"'
        'Clicked span "New work item"'
        'Clicked button "Go to workspace"'
        'Clicked button "Plane Dev" id=headlessui-disclosur aria-label=Open project menu'
    """
    if not result_text:
        return None

    # Pattern: 'Clicked <tag> "<text>"' with optional attributes
    m = re.match(
        r'Clicked\s+(\w+)\s+"([^"]+)"(?:\s+id=(\S+))?(?:\s+aria-label=(.+))?',
        result_text,
    )
    if m:
        tag = m.group(1)   # button, a, span, div, etc.
        text = m.group(2)
        elem_id = m.group(3)
        aria = m.group(4)

        # Prefer id if available (skip headlessui dynamic ids)
        if elem_id and not elem_id.startswith("headlessui-"):
            return f'#{elem_id}'

        # Clean up the text: take first line only, strip trailing dots
        clean = text.split("\n")[0].strip().rstrip(".").rstrip(".")
        # Remove emoji prefixes (broad Unicode emoji ranges)
        clean = re.sub(
            r'^[\U0001f000-\U0001fFFF\u2600-\u27BF\u2700-\u27BF\uFE00-\uFE0F\u200d]+\s*',
            '', clean,
        ).strip()
        if not clean:
            return None

        # Use role + name for buttons/links
        if tag == "button":
            return f'button:has-text("{clean}")'
        if tag == "a":
            return f'a:has-text("{clean}")'
        # Fallback: text selector
        return f'text="{clean}"'

    return None


def extract_steps(action_log: list[dict]) -> list[dict]:
    """Extract meaningful steps from action log, skipping noise."""
    steps = []
    for entry in action_log:
        step_num = entry.get("step", 0)
        thought = entry.get("thought", "").replace("\n", " ").strip()
        url = entry.get("url", "")
        results = entry.get("results", [])

        for action_idx, action_raw in enumerate(entry.get("actions", [])):
            # Actions may be dicts (from model_dump) or strings (legacy format)
            if isinstance(action_raw, dict):
                # Dict format: {"click": {"index": 123}} or {"input": {"index": 1, "text": "..."}}
                for action_name, action_params in action_raw.items():
                    if isinstance(action_params, dict):
                        parsed = {"type": action_name, "params": action_params}
                    else:
                        parsed = {"type": action_name, "params": {}}
                    break  # one action per dict
            else:
                parsed = parse_action_str(action_raw)
            if not parsed:
                continue

            t = parsed["type"]
            p = parsed["params"]

            # Skip file writes, waits, and other non-browser actions
            if t in ("writefile", "write_file", "done"):
                continue

            # Attach result text for selector extraction
            result_text = _result_text_for(results, action_idx)

            steps.append({
                "step": step_num,
                "type": t,
                "params": p,
                "thought": thought[:500],
                "url": url,
                "had_error": any(r.get("error") for r in results),
                "result_text": result_text,
            })

    return steps


# ── Test generation ───────────────────────────────────────────

def generate_test(issue_number: str, repro_dir: Path) -> str:
    """Generate a Playwright test from reproduction artifacts."""
    action_log_path = repro_dir / "action-log.json"
    verdict_path = repro_dir / "verdict.md"
    issue_path = repro_dir / "issue.json"

    if not action_log_path.exists():
        print(f"❌ No action-log.json in {repro_dir}")
        sys.exit(1)

    action_log = json.loads(action_log_path.read_text())

    # Read issue metadata
    issue_title = f"Issue #{issue_number}"
    issue_body = ""
    if issue_path.exists():
        issue_data = json.loads(issue_path.read_text())
        issue_title = issue_data.get("title", issue_title)
        issue_body = issue_data.get("body", "")

    # Read verdict
    verdict_status = "unknown"
    verdict_summary = ""
    if verdict_path.exists():
        for line in verdict_path.read_text().splitlines():
            if line.startswith("**Status:**"):
                verdict_status = line.split("**Status:**")[1].strip()
            elif line.startswith("**Summary:**"):
                verdict_summary = line.split("**Summary:**")[1].strip()

    # Extract reproduction steps
    steps = extract_steps(action_log)

    # Collect unique URLs visited (for navigation)
    urls = []
    for s in steps:
        if s["url"] and s["url"] not in urls and s["url"] != "about:blank":
            urls.append(s["url"])

    base_url = "http://localhost"
    if urls:
        p = urlparse(urls[0])
        base_url = f"{p.scheme}://{p.netloc}"

    # Detect where login/onboarding ends and real test steps begin.
    # Skip steps that are part of login flow (handled by login() fixture).
    # Login ends when the agent reaches the workspace URL (e.g. /plane-dev/...)
    post_login_idx = 0
    workspace_slug = "plane-dev"
    for i, s in enumerate(steps):
        url = s.get("url", "")
        result = s.get("result_text", "")
        # Once we're past onboarding and on a workspace page doing real actions
        if (f"/{workspace_slug}/projects/" in url or
            f"/{workspace_slug}/issues" in url or
            "Work items" in result or
            "work item" in result.lower()):
            post_login_idx = i
            break
        # Also detect navigation past the workspace home
        if (f"/{workspace_slug}/" in url and
            "/onboarding/" not in url and
            s["type"] in ("click",) and
            "project" in result.lower()):
            post_login_idx = i
            break

    # Build step comments showing what the agent did
    step_lines = []
    for s_idx, s in enumerate(steps):
        t = s["type"]
        p = s["params"]
        comment = f"    # Step {s['step']}: {s['thought'][:150]}" if s["thought"] else ""

        # Skip login/onboarding steps — handled by login() fixture
        if s_idx < post_login_idx:
            step_lines.append(f"    # (login step {s['step']} — handled by login())")
            step_lines.append("")
            continue

        if t in ("navigate", "go_to_url", "goto"):
            url = p.get("url", s.get("url", ""))
            if comment:
                step_lines.append(comment)
            step_lines.append(f'    page.goto("{url}")')
            step_lines.append('    page.wait_for_load_state("networkidle")')

        elif t in ("click", "clickelement"):
            idx = p.get("index", p.get("element_id", "?"))
            result_text = s.get("result_text", "")
            selector = _selector_from_result(result_text)
            if comment:
                step_lines.append(comment)
            if selector:
                step_lines.append(f'    page.locator(\'{selector}\').click()')
            else:
                step_lines.append(
                    f"    # Agent clicked element index={idx} — replace with real selector"
                )
                step_lines.append(f"    # page.locator('...').click()")

        elif t in ("input", "inputtext", "type", "input_text"):
            text = p.get("text", p.get("value", ""))
            idx = p.get("index", "?")
            result_text = s.get("result_text", "")
            if comment:
                step_lines.append(comment)
            # Try to find the input by common attributes from the thought
            thought_text = s.get("thought", "")
            input_selector = None
            # Look for name=, id=, placeholder= in the thought
            for attr in ("name", "id", "placeholder"):
                m = re.search(rf'{attr}[=\'"](\w[\w\-]*)', thought_text)
                if m:
                    val = m.group(1)
                    # Skip generic attribute values (but allow 'name' as input name)
                    if val not in ("text", "true", "false", "input", "submit"):
                        input_selector = f'input[{attr}="{val}"]'
                        break
            # Escape text for embedding in generated code
            safe_text = text.replace('\\', '\\\\').replace('"', '\\"')
            if input_selector:
                step_lines.append(f'    page.locator(\'{input_selector}\').fill("{safe_text}")')
            else:
                step_lines.append(
                    f"    # Agent typed into element index={idx}"
                )
                step_lines.append(f'    # page.locator("...").fill("{safe_text}")')

        elif t == "scroll":
            direction = p.get("direction", "down")
            amount = p.get("amount", 300)
            delta = amount if direction == "down" else -amount
            step_lines.append(f"    page.mouse.wheel(0, {delta})")

        elif t in ("key_press", "keypress", "press_key", "presskey", "sendkeys", "send_keys"):
            key = p.get("keys", p.get("key", ""))
            if key:
                step_lines.append(f'    page.keyboard.press("{key}")')
            else:
                step_lines.append(f"    # send_keys action — key not captured")

        elif t in ("evaluate",):
            code = p.get("code", p.get("js_code", ""))
            if comment:
                step_lines.append(comment)
            step_lines.append(f'    page.evaluate("{code}")')

        elif t == "wait":
            ms = int(float(str(p.get("duration", p.get("seconds", 2)))) * 1000)
            step_lines.append(f"    page.wait_for_timeout({ms})")

        elif t == "done":
            text = p.get("text", "")
            step_lines.append(f'    # Agent done: {text[:150]}')

        else:
            step_lines.append(f"    # Unsupported: {t}({p})")

        step_lines.append("")  # blank line between steps

    steps_block = "\n".join(step_lines) if step_lines else "    pass  # No steps extracted"

    # Extract reproduction steps from the issue body for the docstring
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

    test_code = f'''"""
Playwright regression test for: {issue_title}

Auto-generated by bug-repro-agent from browser-use reproduction run.
Verdict: {verdict_status} — {verdict_summary}

Steps from bug report:
{repro_steps or "    (see issue body)"}

Usage:
    pytest {f"test_{issue_number}.py"} -v --headed    # watch it run
    pytest {f"test_{issue_number}.py"} -v              # headless
"""

import re
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

    # ── Agent reproduction steps (from action log) ────────────
    # The steps below document what the browser-use agent did.
    # Selectors marked TODO need to be replaced with real Plane selectors.
    # URLs are exact from the reproduction run.

{steps_block}
    # ── Assertions ────────────────────────────────────────────
    # TODO: Add assertions based on expected behavior.
    #
    # If the bug was REPRODUCED, assert the fix works:
    #   expect(page.locator("...")).not_to_be_visible()
    #
    # If NOT_REPRODUCED, assert correct behavior holds:
    #   expect(page.locator("...")).to_be_visible()
'''

    return test_code


# ── CLI ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate a Playwright test from a reproduction action log",
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
    print(f"✅ Playwright test: {output_path}")
    print(f"   Run: pytest {output_path} -v")


if __name__ == "__main__":
    main()
