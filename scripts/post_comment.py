#!/usr/bin/env python3
"""
Post a reproduction report as a GitHub issue comment.

Reads artifacts from reproductions/<issue>/, generates a rich Markdown
comment, and posts it via `gh issue comment`.

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
PLANE_PASSWORD = os.getenv("PLANE_PASSWORD", "")


# ── Artifact readers ─────────────────────────────────────────


def read_verdict(repro_dir: Path) -> dict:
    """Parse verdict.md for status, summary, and run stats."""
    verdict_path = repro_dir / "verdict.md"
    if not verdict_path.exists():
        return {"status": "UNKNOWN", "summary": "verdict.md not found", "raw": ""}

    text = verdict_path.read_text()
    info = {"raw": text, "status": "UNKNOWN", "summary": ""}

    # Parse status line
    m = re.search(r"\*\*Status:\*\*\s*(.+)", text)
    if m:
        info["status"] = m.group(1).strip()

    # Parse summary
    m = re.search(r"\*\*Summary:\*\*\s*(.+)", text)
    if m:
        info["summary"] = m.group(1).strip()

    # Parse stats
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


def read_image_urls(repro_dir: Path) -> dict:
    """Read optional image-urls.json for pre-uploaded GIF/screenshot URLs."""
    urls_path = repro_dir / "image-urls.json"
    if not urls_path.exists():
        return {}
    try:
        return json.loads(urls_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


# ── Comment builder ──────────────────────────────────────────


def extract_action_type(actions: list[str]) -> tuple[str, str]:
    """Extract a human-readable action type and detail from action strings.

    Returns (action_type, detail).
    """
    if not actions:
        return "Observe", ""

    action = actions[0]

    # Common browser-use action patterns
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
        m = re.search(pattern, action, re.IGNORECASE)
        if m:
            return action_type, detail_fn(m)

    # Fallback: first 50 chars of action string
    return "Action", action[:50]


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


def build_comment(issue_number: str, verdict: dict, steps: list[dict], image_urls: dict) -> str:
    """Build the GitHub Markdown comment body."""
    parts = []

    # ── Header
    parts.append(f"### 🔍 Reproduction Report — `repro-agent`\n")
    parts.append(f"**Verdict:** {verdict['status']}")
    parts.append(f"**Summary:** {verdict['summary']}")
    parts.append(f"**Run time:** {verdict.get('duration', '?')}  ·  **Steps:** {verdict.get('steps', '?')}")
    parts.append("")

    # ── GIF (if available)
    gif_url = image_urls.get("gif")
    if gif_url:
        parts.append("---\n")
        parts.append("#### Agent Run\n")
        parts.append(f"![agent-run]({gif_url})\n")

    # ── Step table
    if steps:
        parts.append("---\n")
        parts.append("#### Steps Taken\n")
        parts.append("| # | Action | Detail | Result |")
        parts.append("|---|--------|--------|--------|")

        for step in steps[:25]:  # Cap at 25 rows to keep comment readable
            num = step.get("step", "?")
            action_type, detail = extract_action_type(step.get("actions", []))
            emoji = result_emoji(step)
            res = result_text(step)
            # Mask passwords and escape pipes
            detail = mask_password(detail).replace("|", "\\|")
            res = mask_password(res).replace("|", "\\|")
            parts.append(f"| {num} | {action_type} | {detail} | {emoji} {res} |")

        if len(steps) > 25:
            parts.append(f"\n*...and {len(steps) - 25} more steps (see full action log)*\n")
        parts.append("")

    # ── Evidence screenshot (if available)
    screenshot_url = image_urls.get("screenshot")
    if screenshot_url:
        parts.append("---\n")
        parts.append("#### Evidence\n")
        parts.append(f"![evidence]({screenshot_url})\n")

    # ── Footer
    parts.append("---\n")
    tool = verdict.get("tool", "browser-use + Claude Sonnet 4 via OpenRouter")
    parts.append(f"<sub>Generated by <b>repro-agent</b> · {mask_password(tool)}</sub>")

    return mask_password("\n".join(parts))


# ── Main ─────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Post a reproduction report as a GitHub issue comment",
        epilog="Examples:\n"
               "  python scripts/post_comment.py --issue 9329\n"
               "  python scripts/post_comment.py --issue 9329 --dry-run\n"
               "  python scripts/post_comment.py --issue 9329 --repo user/fork\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--issue", required=True, help="Issue number")
    parser.add_argument("--repo", default=DEFAULT_REPO, help=f"GitHub repo (default: {DEFAULT_REPO})")
    parser.add_argument("--dry-run", action="store_true", help="Generate comment file without posting")
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
    image_urls = read_image_urls(repro_dir)

    print(f"  Verdict:    {verdict['status']}")
    print(f"  Steps:      {len(steps)}")
    print(f"  Images:     {list(image_urls.keys()) or 'none'}")

    # Build comment
    comment = build_comment(args.issue, verdict, steps, image_urls)

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