#!/usr/bin/env python3
"""
Post a rich reproduction report as a GitHub issue comment.

Reads artifacts from reproductions/<issue>/, uploads images via git push
to get raw.githubusercontent.com URLs, generates a rich Markdown comment
with GIF, step traces, evidence screenshots, and regression test, then
posts it via `gh issue comment`.

Usage:
    python scripts/post_comment.py --issue 9329
    python scripts/post_comment.py --issue 9329 --dry-run
    python scripts/post_comment.py --issue 9329 --repo user/fork
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_REPO = os.getenv("GITHUB_REPO", "makeplane/plane")
AGENT_REPO = os.getenv("AGENT_REPO", "Mr-Ashish/bug-repro-agent")
AGENT_BRANCH = os.getenv("AGENT_BRANCH", "main")
PLANE_PASSWORD = os.getenv("PLANE_PASSWORD", "")


# ── Artifact readers ─────────────────────────────────────────


def read_verdict(repro_dir: Path) -> dict:
    """Parse verdict.md for status, summary, and run stats."""
    verdict_path = repro_dir / "verdict.md"
    if not verdict_path.exists():
        return {"status": "UNKNOWN", "summary": "verdict.md not found", "raw": ""}

    text = verdict_path.read_text()
    info = {"raw": text, "status": "UNKNOWN", "summary": ""}

    m = re.search(r"\*\*Status:\*\*\s*(.+)", text)
    if m:
        info["status"] = m.group(1).strip()

    m = re.search(r"\*\*Summary:\*\*\s*(.+)", text)
    if m:
        info["summary"] = m.group(1).strip()

    m = re.search(r"- Steps:\s*(\d+)", text)
    info["steps"] = m.group(1) if m else "?"

    m = re.search(r"- Duration:\s*([\d.]+)s", text)
    info["duration"] = f"{m.group(1)}s" if m else "?"

    m = re.search(r"\*\*Tool:\*\*\s*(.+)", text)
    info["tool"] = m.group(1).strip() if m else "browser-use"

    return info


def read_action_log(repro_dir: Path) -> list[dict]:
    """Read action-log.json and return step entries."""
    log_path = repro_dir / "action-log.json"
    if not log_path.exists():
        return []
    try:
        return json.loads(log_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def read_playwright_test(repro_dir: Path, issue_number: str) -> str:
    """Read the auto-generated Playwright test, if it exists."""
    test_path = repro_dir / f"test_{issue_number}.py"
    if not test_path.exists():
        return ""
    return test_path.read_text()


def read_root_cause(repro_dir: Path) -> str:
    """Read root cause analysis from context.txt.

    The meta-agent writes source-code context to context.txt before
    running drive.py. This contains the root cause (which files,
    what validation is missing, etc.).
    """
    context_path = repro_dir / "context.txt"
    if not context_path.exists():
        return ""

    text = context_path.read_text().strip()
    if not text:
        return ""

    # Extract the TECHNICAL DETAILS section if present (most useful for RCA)
    sections = []

    # Look for TECHNICAL DETAILS block
    tech_match = re.search(
        r"TECHNICAL DETAILS:\s*\n((?:[-•].+\n?)+)", text, re.MULTILINE
    )
    if tech_match:
        sections.append(tech_match.group(1).strip())

    # Look for BUG description (first line)
    bug_match = re.match(r"BUG:\s*(.+)", text)
    if bug_match:
        sections.insert(0, bug_match.group(1).strip())

    # If we found structured sections, return them formatted
    if sections:
        return "\n\n".join(sections)

    # Fallback: return the whole context (truncated)
    lines = text.splitlines()
    if len(lines) > 20:
        return "\n".join(lines[:20]) + "\n..."
    return text


# ── Image upload via git ─────────────────────────────────────


def _pick_best_evidence(repro_dir: Path) -> Path | None:
    """Dumb fallback — returns the last evidence screenshot.

    Only used when the meta-agent doesn't specify --evidence.
    The meta-agent should review all screenshots with vision and
    pass the smoking-gun screenshot via --evidence instead.
    """
    evidence_files = sorted(repro_dir.glob("evidence-*.png"))
    if not evidence_files:
        return None
    return evidence_files[-1]


def upload_artifacts_via_git(
    repro_dir: Path, issue_number: str, evidence_path: Path | None = None,
) -> dict:
    """Commit and push GIF, video, + evidence screenshot, return raw URLs.

    Args:
        evidence_path: Explicit screenshot chosen by the meta-agent.
                       If None, falls back to _pick_best_evidence().

    Returns dict with optional 'gif', 'video', and 'screenshot' keys
    containing raw.githubusercontent.com URLs.
    """
    urls = {}
    files_to_add = []

    # Find GIF
    gif_path = repro_dir / "agent-run.gif"
    if gif_path.exists() and gif_path.stat().st_size > 0:
        files_to_add.append(str(gif_path))
        urls["gif"] = (
            f"https://raw.githubusercontent.com/{AGENT_REPO}/{AGENT_BRANCH}/"
            f"reproductions/{issue_number}/agent-run.gif"
        )

    # Find video (.mp4)
    mp4_files = sorted(repro_dir.glob("*.mp4"))
    if mp4_files:
        video = mp4_files[-1]
        if video.stat().st_size > 1000:  # skip empty/placeholder videos
            files_to_add.append(str(video))
            urls["video"] = (
                f"https://raw.githubusercontent.com/{AGENT_REPO}/{AGENT_BRANCH}/"
                f"reproductions/{issue_number}/{video.name}"
            )

    # Evidence screenshot — prefer explicit path from meta-agent
    best = evidence_path if evidence_path and evidence_path.exists() else _pick_best_evidence(repro_dir)
    if best and best.stat().st_size > 0:
        files_to_add.append(str(best))
        urls["screenshot"] = (
            f"https://raw.githubusercontent.com/{AGENT_REPO}/{AGENT_BRANCH}/"
            f"reproductions/{issue_number}/{best.name}"
        )

    if not files_to_add:
        print("  ⚠️ No GIF, video, or screenshots to upload")
        return urls

    # Git add + commit + push
    try:
        subprocess.run(["git", "add", "-f"] + files_to_add, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"repro: #{issue_number} artifacts (GIF + evidence)"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "push"],
            check=True, capture_output=True, timeout=60,
        )
        print(f"  📤 Pushed {len(files_to_add)} artifact(s) to {AGENT_REPO}")
        for key, url in urls.items():
            print(f"     {key}: {url}")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        # "nothing to commit" is fine — artifacts may already be pushed
        if "nothing to commit" in stderr or "no changes added" in stderr:
            print("  ℹ️ Artifacts already committed")
        else:
            print(f"  ⚠️ Git push failed: {stderr[:200]}")
            # URLs still valid if files were pushed in a previous run
    except Exception as e:
        print(f"  ⚠️ Git push failed: {e}")

    return urls


# ── Action parsing (handles both dict and string formats) ────


def extract_action_type(actions: list) -> tuple[str, str]:
    """Extract a human-readable action type and detail from actions.

    Handles both formats:
      - Dict format (current): [{"click": {"index": 123}}]
      - String format (legacy): ["click_element(index=123)"]

    Returns (action_type, detail).
    """
    if not actions:
        return "Observe", ""

    action = actions[0]

    # ── Dict format (from model_dump — current format since commit f41b554)
    if isinstance(action, dict):
        for action_name, params in action.items():
            if not isinstance(params, dict):
                params = {}
            name = action_name.lower()

            if name in ("click", "clickelement", "click_element"):
                idx = params.get("index", params.get("element_id", "?"))
                return "Click", f"element #{idx}"
            elif name in ("input", "inputtext", "input_text"):
                text = str(params.get("text", ""))
                if len(text) > 40:
                    return "Type", f"`{text[:40]}…`"
                return "Type", f"`{text}`"
            elif name in ("go_to_url", "gotourl", "navigate"):
                url = params.get("url", "")
                return "Navigate", url[:60]
            elif name in ("scroll", "scrollaction"):
                direction = params.get("direction", "down")
                return "Scroll", direction
            elif name in ("send_keys", "sendkeys", "key_press"):
                keys = params.get("keys", params.get("key", ""))
                return "Key", f"`{keys}`"
            elif name in ("extract_content", "extractcontent", "extract"):
                return "Extract", "page content"
            elif name in ("done", "doneaction"):
                text = params.get("text", "")
                return "Done", text[:50]
            else:
                return action_name.replace("_", " ").title(), str(params)[:50]
        return "Action", ""

    # ── String format (legacy)
    action_str = str(action)
    patterns = [
        (r"click_element.*index=(\d+)", "Click", lambda m: f"element #{m.group(1)}"),
        (r"input_text.*text=['\"](.{0,40})", "Type", lambda m: f"`{m.group(1)}…`" if len(m.group(1)) >= 40 else f"`{m.group(1)}`"),
        (r"go_to_url.*url=['\"]([^'\"]+)", "Navigate", lambda m: m.group(1)[:60]),
        (r"scroll", "Scroll", lambda _: "page"),
        (r"send_keys.*keys=['\"]([^'\"]+)", "Key", lambda m: f"`{m.group(1)}`"),
        (r"extract_content", "Extract", lambda _: "page content"),
        (r"done", "Done", lambda _: "task complete"),
    ]
    for pattern, action_type, detail_fn in patterns:
        m = re.search(pattern, action_str, re.IGNORECASE)
        if m:
            return action_type, detail_fn(m)

    return "Action", action_str[:50]


def result_emoji(step: dict) -> str:
    """Determine result emoji from step data."""
    results = step.get("results", [])
    if not results:
        return "➡️"

    for r in results:
        if r.get("error"):
            return "❌"
        if r.get("is_done"):
            return "🏁"

    return "✅"


def result_text(step: dict) -> str:
    """Extract result text from step."""
    results = step.get("results", [])
    for r in results:
        if r.get("error"):
            return str(r["error"])[:80]
        if r.get("extracted_content"):
            return str(r["extracted_content"])[:80]
    return ""


def mask_password(text: str) -> str:
    """Replace all occurrences of the Plane password with ***."""
    if not PLANE_PASSWORD:
        return text
    return text.replace(PLANE_PASSWORD, "***")


# ── Comment builder ──────────────────────────────────────────


def build_comment(
    issue_number: str,
    verdict: dict,
    steps: list[dict],
    image_urls: dict,
    playwright_test: str = "",
    repro_dir: Path | None = None,
) -> str:
    """Build the rich GitHub Markdown comment body."""
    parts = []

    # ── Header
    raw_status = verdict["status"]
    # Strip any existing emoji prefix (verdict.md already includes one)
    status_text = re.sub(r'^[✅❌⚠️🔍🤖\s]+', '', raw_status).strip()
    status_emoji = "✅" if "REPRODUCED" in status_text and "NOT" not in status_text else "❌" if "NOT" in status_text else "⚠️"
    parts.append(f"### 🔍 Reproduction Report — `repro-agent`\n")
    parts.append(f"**Verdict:** {status_emoji} {status_text}")
    parts.append(f"**Summary:** {verdict['summary']}")
    parts.append(f"**Run time:** {verdict.get('duration', '?')}  ·  **Steps:** {verdict.get('steps', '?')}")
    parts.append("")

    # ── Video (inline playback — preferred over GIF for full session)
    video_url = image_urls.get("video")
    gif_url = image_urls.get("gif")
    if video_url:
        parts.append("---\n")
        parts.append("#### 🎬 Reproduction Session\n")
        # GitHub renders <video> tags inline — no download needed
        parts.append(
            f'<video src="{video_url}" controls width="100%"'
            f' alt="Bug reproduction session"></video>\n'
        )
        parts.append("> Full autonomous browser session — login, navigation, reproduction, and bug observation.\n")
        if gif_url:
            parts.append("<details>")
            parts.append("<summary>GIF preview (click to expand)</summary>\n")
            parts.append(f"![agent-run]({gif_url})\n")
            parts.append("</details>\n")
    elif gif_url:
        parts.append("---\n")
        parts.append("#### 🎬 Reproduction Session\n")
        parts.append(f"![agent-run]({gif_url})\n")
        parts.append("> Full autonomous browser session — login, navigation, reproduction, and bug observation.\n")

    # ── Step table with agent thoughts
    if steps:
        parts.append("---\n")
        parts.append("#### 📋 Steps Taken\n")
        parts.append("| # | Action | Detail | Agent Thought | Result |")
        parts.append("|---|--------|--------|---------------|--------|")

        for step in steps[:25]:
            num = step.get("step", "?")
            action_type, detail = extract_action_type(step.get("actions", []))
            thought = step.get("thought", "")
            # Truncate thought for table readability
            if len(thought) > 60:
                thought = thought[:57] + "..."
            emoji = result_emoji(step)
            res = result_text(step)
            # Mask passwords and escape pipes
            detail = mask_password(detail).replace("|", "\\|")
            thought = mask_password(thought).replace("|", "\\|").replace("\n", " ")
            res = mask_password(res).replace("|", "\\|")
            parts.append(f"| {num} | {action_type} | {detail} | {thought} | {emoji} {res} |")

        if len(steps) > 25:
            parts.append(f"\n*...and {len(steps) - 25} more steps (see full action log)*\n")
        parts.append("")

    # ── Evidence screenshot (the bug moment — shows the actual error/state)
    screenshot_url = image_urls.get("screenshot")
    if screenshot_url:
        parts.append("---\n")
        parts.append("#### 🖼️ Bug Evidence\n")
        parts.append(f"![bug-evidence]({screenshot_url})\n")
        parts.append("> Screenshot captured at the moment the bug manifested.\n")

    # ── Root cause analysis (from source-code context)
    root_cause = read_root_cause(repro_dir) if repro_dir else ""
    if root_cause:
        parts.append("---\n")
        parts.append("#### 🔬 Root Cause Analysis\n")
        parts.append(mask_password(root_cause))
        parts.append("")

    # ── Regression test (full, not truncated)
    if playwright_test:
        parts.append("---\n")
        parts.append("#### 🧪 Playwright Regression Test\n")
        parts.append("```python")
        parts.append(mask_password(playwright_test))
        parts.append("```\n")

    # ── Footer
    parts.append("---\n")
    agent_repo_url = f"https://github.com/{AGENT_REPO}"
    artifacts_url = f"{agent_repo_url}/tree/{AGENT_BRANCH}/reproductions/{issue_number}"
    tool = verdict.get("tool", "browser-use + Claude Sonnet 4 via OpenRouter")
    parts.append(
        f'<sub>🤖 Generated by <a href="{agent_repo_url}"><b>repro-agent</b></a>'
        f" · {mask_password(tool)}"
        f' · <a href="{artifacts_url}">Full artifacts</a></sub>'
    )

    return mask_password("\n".join(parts))


# ── Main ─────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Post a rich reproduction report as a GitHub issue comment",
        epilog="Examples:\n"
               "  python scripts/post_comment.py --issue 9329\n"
               "  python scripts/post_comment.py --issue 9329 --dry-run\n"
               "  python scripts/post_comment.py --issue 9329 --repo user/fork\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--issue", required=True, help="Issue number")
    parser.add_argument("--repo", default=DEFAULT_REPO, help=f"GitHub repo (default: {DEFAULT_REPO})")
    parser.add_argument("--dry-run", action="store_true", help="Generate comment file without posting")
    parser.add_argument("--no-upload", action="store_true", help="Skip git push of artifacts (use existing URLs)")
    parser.add_argument(
        "--evidence",
        help="Path to the smoking-gun screenshot chosen by the meta-agent. "
             "If not specified, falls back to the last evidence screenshot.",
    )
    args = parser.parse_args()

    repro_dir = Path(f"reproductions/{args.issue}")
    if not repro_dir.exists():
        print(f"❌ No reproduction artifacts found at {repro_dir}/")
        print(f"   Run: python scripts/drive.py --issue {args.issue}")
        sys.exit(1)

    # Read artifacts
    print(f"── Reading artifacts from {repro_dir}/ ──")
    verdict = read_verdict(repro_dir)
    steps = read_action_log(repro_dir)
    playwright_test = read_playwright_test(repro_dir, args.issue)

    print(f"  Verdict:      {verdict['status']}")
    print(f"  Steps:        {len(steps)}")
    print(f"  PW test:      {'yes' if playwright_test else 'no'}")

    # Resolve evidence path from --evidence flag
    evidence_path = Path(args.evidence) if args.evidence else None
    if evidence_path and evidence_path.exists():
        print(f"  Evidence:     {evidence_path.name} (meta-agent picked)")
    elif evidence_path:
        print(f"  ⚠️ Evidence file not found: {evidence_path}, using fallback")
        evidence_path = None

    # Upload artifacts to get public URLs
    if args.dry_run or args.no_upload:
        print("  ℹ️ Skipping artifact upload")
        image_urls = {}
        # Build expected URLs even without pushing (for dry-run preview)
        gif_path = repro_dir / "agent-run.gif"
        if gif_path.exists():
            image_urls["gif"] = (
                f"https://raw.githubusercontent.com/{AGENT_REPO}/{AGENT_BRANCH}/"
                f"reproductions/{args.issue}/agent-run.gif"
            )
        best = evidence_path if evidence_path else _pick_best_evidence(repro_dir)
        if best:
            image_urls["screenshot"] = (
                f"https://raw.githubusercontent.com/{AGENT_REPO}/{AGENT_BRANCH}/"
                f"reproductions/{args.issue}/{best.name}"
            )
    else:
        print("\n── Uploading artifacts via git push ──")
        image_urls = upload_artifacts_via_git(repro_dir, args.issue, evidence_path=evidence_path)

    print(f"  Images:       {list(image_urls.keys()) or 'none'}")

    # Build comment
    comment = build_comment(args.issue, verdict, steps, image_urls, playwright_test, repro_dir=repro_dir)

    # Save to file
    comment_path = repro_dir / "github-comment.md"
    comment_path.write_text(comment)
    print(f"  💬 Comment saved: {comment_path}")

    if args.dry_run:
        print("\n── DRY RUN — comment generated, not posted ──")
        print(f"\n{comment}")
        return

    # Post via gh
    print(f"\n── Posting to {args.repo}#{args.issue} ──")
    try:
        subprocess.run(
            ["gh", "issue", "comment", args.issue,
             "--repo", args.repo,
             "--body-file", str(comment_path)],
            check=True, timeout=30,
        )
        print(f"✅ Comment posted to https://github.com/{args.repo}/issues/{args.issue}")
    except FileNotFoundError:
        print("❌ `gh` CLI not found. Install: https://cli.github.com/")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to post comment: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()