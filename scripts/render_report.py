#!/usr/bin/env python3
"""
render_report.py — Generate a self-contained HTML report from reproduction artifacts.

Bundles verdict, root cause, action log, screenshots (base64-embedded),
video, GIF, and Playwright test into a single .html file that opens
in any browser with no server needed.

Usage:
    python scripts/render_report.py --issue 9329
    python scripts/render_report.py --issue 9329 --open   # opens in browser
"""
import argparse
import base64
import html
import json
import re
import subprocess
import sys
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def b64_image(path: Path) -> str:
    """Encode an image file as a data URI."""
    suffix = path.suffix.lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif"}
    mime_type = mime.get(suffix.lstrip("."), "image/png")
    data = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime_type};base64,{data}"


def b64_video(path: Path) -> str:
    """Encode a video file as a data URI."""
    data = base64.b64encode(path.read_bytes()).decode()
    return f"data:video/mp4;base64,{data}"


def read_json(path: Path) -> dict | list:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def mask_password(text: str) -> str:
    pw = __import__("os").getenv("PLANE_PASSWORD", "")
    if pw:
        text = text.replace(pw, "***")
    return text


def render_html(issue_number: str, repro_dir: Path) -> str:
    """Build the full self-contained HTML report."""

    # ── Read all artifacts ────────────────────────────────────
    verdict_text = (repro_dir / "verdict.md").read_text() if (repro_dir / "verdict.md").exists() else ""
    context_text = (repro_dir / "context.txt").read_text() if (repro_dir / "context.txt").exists() else ""
    action_log = read_json(repro_dir / "action-log.json") if (repro_dir / "action-log.json").exists() else []
    issue_data = read_json(repro_dir / "issue.json") if (repro_dir / "issue.json").exists() else {}
    test_path = repro_dir / f"test_{issue_number}.py"
    test_code = test_path.read_text() if test_path.exists() else ""

    # Parse verdict
    status = "UNKNOWN"
    summary = ""
    m = re.search(r"\*\*Status:\*\*\s*(.+)", verdict_text)
    if m:
        status = re.sub(r'^[✅❌⚠️\s]+', '', m.group(1)).strip()
    m = re.search(r"\*\*Summary:\*\*\s*(.+)", verdict_text)
    if m:
        summary = m.group(1).strip()
    m_steps = re.search(r"- Steps:\s*(\d+)", verdict_text)
    m_dur = re.search(r"- Duration:\s*([\d.]+)s", verdict_text)
    steps_count = m_steps.group(1) if m_steps else "?"
    duration = f"{m_dur.group(1)}s" if m_dur else "?"

    status_class = "reproduced" if "REPRODUCED" in status and "NOT" not in status else "not-reproduced" if "NOT" in status else "inconclusive"

    # ── Screenshots ───────────────────────────────────────────
    screenshots = sorted(repro_dir.glob("evidence-*.png"))

    # ── Video / GIF ───────────────────────────────────────────
    mp4_files = sorted(repro_dir.glob("*.mp4"))
    video_file = mp4_files[-1] if mp4_files else None
    gif_file = repro_dir / "agent-run.gif"

    # ── Build HTML ────────────────────────────────────────────
    issue_title = html.escape(issue_data.get("title", f"Issue #{issue_number}"))
    issue_url = issue_data.get("url", f"https://github.com/makeplane/plane/issues/{issue_number}")

    # Action log rows
    action_rows = []
    for step in (action_log if isinstance(action_log, list) else []):
        num = step.get("step", "?")
        thought = html.escape(mask_password(str(step.get("thought", ""))[:120]))
        url = html.escape(str(step.get("url", ""))[-50:])
        actions = step.get("actions", [])
        action_desc = ""
        if actions and isinstance(actions[0], dict):
            for name, params in actions[0].items():
                action_desc = html.escape(mask_password(f"{name}: {json.dumps(params, default=str)[:80]}"))
                break
        elif actions:
            action_desc = html.escape(mask_password(str(actions[0])[:80]))

        results = step.get("results", [])
        result_text = ""
        result_class = ""
        for r in results:
            if r.get("error"):
                result_text = html.escape(str(r["error"])[:80])
                result_class = "error"
            elif r.get("extracted_content"):
                result_text = html.escape(mask_password(str(r["extracted_content"])[:80]))
                result_class = "success"
            if r.get("is_done"):
                result_class = "done"

        action_rows.append(
            f'<tr class="{result_class}">'
            f'<td class="step-num">{num}</td>'
            f'<td class="action">{action_desc}</td>'
            f'<td class="thought">{thought}</td>'
            f'<td class="url">{url}</td>'
            f'<td class="result">{result_text}</td>'
            f'</tr>'
        )

    # Screenshot gallery items
    gallery_items = []
    for i, ss in enumerate(screenshots):
        data_uri = b64_image(ss)
        gallery_items.append(
            f'<div class="screenshot" onclick="openLightbox(this)">'
            f'<img src="{data_uri}" alt="Evidence {i}" loading="lazy" />'
            f'<span class="label">Step {i}</span>'
            f'</div>'
        )

    # Video section
    video_html = ""
    if video_file and video_file.stat().st_size > 1000:
        video_data = b64_video(video_file)
        video_html = f'<video src="{video_data}" controls width="100%"></video>'
    elif gif_file.exists():
        gif_data = b64_image(gif_file)
        video_html = f'<img src="{gif_data}" alt="Agent run GIF" style="width:100%;border-radius:8px;" />'

    # Context / root cause
    context_html = ""
    if context_text.strip():
        context_html = f'<pre class="context">{html.escape(mask_password(context_text))}</pre>'

    # Playwright test
    test_html = ""
    if test_code.strip():
        test_html = f'<pre class="code"><code>{html.escape(mask_password(test_code))}</code></pre>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Repro Report — #{issue_number}</title>
<style>
  :root {{
    --bg: #0d1117; --surface: #161b22; --surface2: #21262d;
    --border: #30363d; --text: #e6edf3; --text2: #8b949e;
    --green: #3fb950; --red: #f85149; --yellow: #d29922;
    --blue: #58a6ff; --purple: #bc8cff;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.6;
    padding: 0; max-width: 100%;
  }}
  .header {{
    background: linear-gradient(135deg, #161b22 0%, #1a1f2b 100%);
    border-bottom: 1px solid var(--border);
    padding: 32px 40px;
  }}
  .header h1 {{ font-size: 24px; font-weight: 600; margin-bottom: 8px; }}
  .header h1 a {{ color: var(--blue); text-decoration: none; }}
  .header h1 a:hover {{ text-decoration: underline; }}
  .verdict-badge {{
    display: inline-block; padding: 6px 16px; border-radius: 20px;
    font-weight: 600; font-size: 14px; letter-spacing: 0.5px;
  }}
  .verdict-badge.reproduced {{ background: rgba(63,185,80,0.15); color: var(--green); border: 1px solid rgba(63,185,80,0.3); }}
  .verdict-badge.not-reproduced {{ background: rgba(248,81,73,0.15); color: var(--red); border: 1px solid rgba(248,81,73,0.3); }}
  .verdict-badge.inconclusive {{ background: rgba(210,153,34,0.15); color: var(--yellow); border: 1px solid rgba(210,153,34,0.3); }}
  .meta {{ color: var(--text2); font-size: 14px; margin-top: 8px; }}
  .meta span {{ margin-right: 20px; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 24px 40px; }}

  section {{ margin-bottom: 32px; }}
  section h2 {{
    font-size: 18px; font-weight: 600; margin-bottom: 16px;
    padding-bottom: 8px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 8px;
  }}

  /* Video */
  .video-container {{ border-radius: 8px; overflow: hidden; border: 1px solid var(--border); }}
  .video-container video, .video-container img {{ display: block; width: 100%; }}

  /* Action log table */
  .action-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .action-table th {{
    background: var(--surface2); padding: 10px 12px; text-align: left;
    font-weight: 600; font-size: 12px; text-transform: uppercase;
    letter-spacing: 0.5px; color: var(--text2);
    position: sticky; top: 0; z-index: 1;
  }}
  .action-table td {{ padding: 8px 12px; border-top: 1px solid var(--border); vertical-align: top; }}
  .action-table tr:hover {{ background: var(--surface); }}
  .action-table .step-num {{ font-weight: 600; color: var(--blue); width: 40px; text-align: center; }}
  .action-table .thought {{ color: var(--text2); font-style: italic; max-width: 250px; }}
  .action-table .url {{ color: var(--purple); font-family: monospace; font-size: 11px; max-width: 180px; word-break: break-all; }}
  .action-table .action {{ font-family: monospace; font-size: 12px; max-width: 280px; word-break: break-all; }}
  .action-table .result {{ max-width: 200px; }}
  .action-table tr.error td {{ background: rgba(248,81,73,0.05); }}
  .action-table tr.done td {{ background: rgba(63,185,80,0.05); }}
  .action-table tr.error .result {{ color: var(--red); }}
  .action-table tr.done .result {{ color: var(--green); font-weight: 600; }}
  .table-wrapper {{ border: 1px solid var(--border); border-radius: 8px; overflow: auto; max-height: 500px; }}

  /* Screenshot gallery */
  .gallery {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 12px;
  }}
  .screenshot {{
    border: 1px solid var(--border); border-radius: 8px; overflow: hidden;
    cursor: pointer; transition: transform 0.15s, box-shadow 0.15s;
    position: relative;
  }}
  .screenshot:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.4); }}
  .screenshot img {{ width: 100%; display: block; }}
  .screenshot .label {{
    position: absolute; bottom: 8px; left: 8px;
    background: rgba(0,0,0,0.7); color: #fff; padding: 2px 8px;
    border-radius: 4px; font-size: 11px;
  }}

  /* Lightbox */
  .lightbox {{
    display: none; position: fixed; inset: 0; z-index: 100;
    background: rgba(0,0,0,0.9); justify-content: center; align-items: center;
    cursor: zoom-out;
  }}
  .lightbox.active {{ display: flex; }}
  .lightbox img {{ max-width: 95vw; max-height: 95vh; border-radius: 8px; }}
  .lightbox-nav {{
    position: absolute; top: 50%; transform: translateY(-50%);
    background: rgba(255,255,255,0.1); border: none; color: #fff;
    font-size: 32px; padding: 12px 16px; cursor: pointer; border-radius: 8px;
  }}
  .lightbox-nav:hover {{ background: rgba(255,255,255,0.2); }}
  .lightbox-nav.prev {{ left: 20px; }}
  .lightbox-nav.next {{ right: 20px; }}
  .lightbox-close {{
    position: absolute; top: 20px; right: 20px;
    background: none; border: none; color: #fff; font-size: 28px; cursor: pointer;
  }}

  /* Code blocks */
  pre.context, pre.code {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; padding: 16px; overflow-x: auto;
    font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
    font-size: 13px; line-height: 1.5; white-space: pre-wrap;
    word-wrap: break-word;
  }}
  pre.code {{ max-height: 600px; overflow-y: auto; }}

  /* Summary card */
  .summary {{ display: flex; gap: 12px; margin-top: 12px; flex-wrap: wrap; }}
  .stat {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; padding: 12px 20px; text-align: center;
    min-width: 120px;
  }}
  .stat .value {{ font-size: 24px; font-weight: 700; color: var(--blue); }}
  .stat .label {{ font-size: 12px; color: var(--text2); text-transform: uppercase; letter-spacing: 0.5px; }}

  /* Nav tabs */
  .tabs {{
    display: flex; gap: 0; border-bottom: 1px solid var(--border);
    margin-bottom: 24px; overflow-x: auto;
  }}
  .tab {{
    padding: 10px 20px; cursor: pointer; font-size: 14px; font-weight: 500;
    color: var(--text2); border-bottom: 2px solid transparent;
    transition: color 0.2s, border-color 0.2s; white-space: nowrap;
  }}
  .tab:hover {{ color: var(--text); }}
  .tab.active {{ color: var(--text); border-bottom-color: var(--blue); }}
  .tab-content {{ display: none; }}
  .tab-content.active {{ display: block; }}

  .footer {{
    text-align: center; padding: 24px; color: var(--text2); font-size: 12px;
    border-top: 1px solid var(--border); margin-top: 40px;
  }}
  .footer a {{ color: var(--blue); text-decoration: none; }}
</style>
</head>
<body>

<div class="header">
  <h1>🔍 <a href="{issue_url}" target="_blank">{issue_title}</a></h1>
  <div>
    <span class="verdict-badge {status_class}">{html.escape(status)}</span>
  </div>
  <p class="meta" style="margin-top:12px;">{html.escape(summary)}</p>
  <div class="summary">
    <div class="stat"><div class="value">{steps_count}</div><div class="label">Steps</div></div>
    <div class="stat"><div class="value">{duration}</div><div class="label">Duration</div></div>
    <div class="stat"><div class="value">{len(screenshots)}</div><div class="label">Screenshots</div></div>
    <div class="stat"><div class="value">{'✓' if video_file else '—'}</div><div class="label">Video</div></div>
  </div>
</div>

<div class="container">

  <div class="tabs">
    <div class="tab active" onclick="switchTab('session')">🎬 Session</div>
    <div class="tab" onclick="switchTab('steps')">📋 Steps ({len(action_log) if isinstance(action_log, list) else 0})</div>
    <div class="tab" onclick="switchTab('screenshots')">📸 Screenshots ({len(screenshots)})</div>
    <div class="tab" onclick="switchTab('rootcause')">🔬 Root Cause</div>
    <div class="tab" onclick="switchTab('test')">🧪 Playwright Test</div>
  </div>

  <!-- Session tab -->
  <div id="tab-session" class="tab-content active">
    <section>
      <h2>🎬 Reproduction Session</h2>
      <div class="video-container">
        {video_html if video_html else '<p style="padding:40px;text-align:center;color:var(--text2);">No video recorded</p>'}
      </div>
    </section>
  </div>

  <!-- Steps tab -->
  <div id="tab-steps" class="tab-content">
    <section>
      <h2>📋 Action Log</h2>
      <div class="table-wrapper">
        <table class="action-table">
          <thead><tr>
            <th>#</th><th>Action</th><th>Agent Thought</th><th>URL</th><th>Result</th>
          </tr></thead>
          <tbody>{''.join(action_rows)}</tbody>
        </table>
      </div>
    </section>
  </div>

  <!-- Screenshots tab -->
  <div id="tab-screenshots" class="tab-content">
    <section>
      <h2>📸 Evidence Screenshots</h2>
      <div class="gallery">
        {''.join(gallery_items) if gallery_items else '<p style="color:var(--text2);">No screenshots captured</p>'}
      </div>
    </section>
  </div>

  <!-- Root cause tab -->
  <div id="tab-rootcause" class="tab-content">
    <section>
      <h2>🔬 Root Cause Analysis</h2>
      {context_html if context_html else '<p style="color:var(--text2);">No source-code context available</p>'}
    </section>
  </div>

  <!-- Test tab -->
  <div id="tab-test" class="tab-content">
    <section>
      <h2>🧪 Playwright Regression Test</h2>
      {test_html if test_html else '<p style="color:var(--text2);">No Playwright test generated</p>'}
    </section>
  </div>

</div>

<div class="footer">
  Generated by <a href="https://github.com/Mr-Ashish/bug-repro-agent">repro-agent</a>
  · Issue <a href="{issue_url}">#{issue_number}</a>
</div>

<!-- Lightbox -->
<div class="lightbox" id="lightbox" onclick="closeLightbox()">
  <button class="lightbox-close" onclick="closeLightbox()">&times;</button>
  <button class="lightbox-nav prev" onclick="event.stopPropagation();navLightbox(-1)">&#8249;</button>
  <img id="lightbox-img" src="" alt="Full size" onclick="event.stopPropagation()" />
  <button class="lightbox-nav next" onclick="event.stopPropagation();navLightbox(1)">&#8250;</button>
</div>

<script>
  // Tabs
  function switchTab(name) {{
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    document.querySelector('[onclick*="' + name + '"]').classList.add('active');
  }}

  // Lightbox
  let lightboxImages = [];
  let lightboxIndex = 0;
  document.querySelectorAll('.screenshot img').forEach((img, i) => {{
    lightboxImages.push(img.src);
  }});

  function openLightbox(el) {{
    const img = el.querySelector('img');
    lightboxIndex = lightboxImages.indexOf(img.src);
    document.getElementById('lightbox-img').src = img.src;
    document.getElementById('lightbox').classList.add('active');
  }}
  function closeLightbox() {{
    document.getElementById('lightbox').classList.remove('active');
  }}
  function navLightbox(dir) {{
    lightboxIndex = (lightboxIndex + dir + lightboxImages.length) % lightboxImages.length;
    document.getElementById('lightbox-img').src = lightboxImages[lightboxIndex];
  }}
  document.addEventListener('keydown', e => {{
    if (!document.getElementById('lightbox').classList.contains('active')) return;
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowLeft') navLightbox(-1);
    if (e.key === 'ArrowRight') navLightbox(1);
  }});
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(
        description="Generate a self-contained HTML report from reproduction artifacts",
    )
    parser.add_argument("--issue", required=True, help="Issue number")
    parser.add_argument("--dir", help="Reproduction directory (default: reproductions/<issue>)")
    parser.add_argument("--open", action="store_true", help="Open the report in the default browser")
    args = parser.parse_args()

    repro_dir = Path(args.dir) if args.dir else Path(f"reproductions/{args.issue}")
    if not repro_dir.exists():
        print(f"❌ No reproduction artifacts at {repro_dir}/")
        sys.exit(1)

    print(f"── Rendering HTML report from {repro_dir}/ ──")
    report_html = render_html(args.issue, repro_dir)

    out_path = repro_dir / "report.html"
    out_path.write_text(report_html)
    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"  📄 Report: {out_path} ({size_mb:.1f} MB)")

    if args.open:
        webbrowser.open(f"file://{out_path.resolve()}")
        print("  🌐 Opened in browser")


if __name__ == "__main__":
    main()