#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import re
import subprocess
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "docs/project/PROJECT_CONTROL_BOARD.md"
WORKLINKS = ROOT / "docs/project/WORKLINKS.md"
OUT = ROOT / "docs/project/PROJECT_DASHBOARD.html"

def sh(cmd):
    return subprocess.check_output(cmd, cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()

def parse_board():
    rows = []
    if not BOARD.exists():
        return rows
    for line in BOARD.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| M"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 8:
            continue
        files = re.findall(r"`([^`]+)`", cells[6])
        rows.append({
            "id": cells[0],
            "name": cells[1],
            "status": cells[2],
            "done": cells[3],
            "risk": cells[4],
            "commit": cells[5],
            "files": files,
            "next": cells[7],
        })
    return rows

def build_html(rows):
    generated = dt.datetime.now(dt.timezone.utc).isoformat()
    head = sh(["git", "--no-pager", "log", "--oneline", "-1"])
    cards = []
    for r in rows:
        file_links = "".join(
            f'<li><code>{html.escape(f)}</code></li>' for f in r["files"]
        )
        smoke = f"grep -n \"{r['id']}\" -A30 docs/project/WORKLINKS.md"
        git_preview = "git status --short -- " + " ".join(r["files"])
        cards.append(f"""
<section class="card risk-{html.escape(r['risk'])}">
  <div class="row">
    <h2>{html.escape(r['id'])}｜{html.escape(r['name'])}</h2>
    <span class="badge">{html.escape(r['status'])} · {html.escape(r['done'])}</span>
  </div>
  <p><b>Risk:</b> {html.escape(r['risk'])}</p>
  <p><b>Commit:</b> <code>{html.escape(r['commit'])}</code></p>
  <p><b>Next:</b> {html.escape(r['next'])}</p>
  <details>
    <summary>Canonical files</summary>
    <ul>{file_links}</ul>
  </details>
  <details>
    <summary>Copy commands</summary>
    <pre>cd /home/taiji_admin/Taiji_Hub || exit 1

# Open files
{"".join("code " + f + chr(10) for f in r["files"])}

# Worklink section
{smoke}

# Git preview
{git_preview}</pre>
  </details>
</section>
""")
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<title>W7TP Project Dashboard</title>
<style>
body {{
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  margin: 0;
  background: #0f172a;
  color: #e5e7eb;
}}
header {{
  padding: 24px;
  background: #111827;
  position: sticky;
  top: 0;
  z-index: 1;
  border-bottom: 1px solid #374151;
}}
h1 {{ margin: 0 0 8px 0; }}
main {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 16px;
  padding: 16px;
}}
.card {{
  background: #111827;
  border: 1px solid #374151;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 8px 24px rgba(0,0,0,.25);
}}
.row {{
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: start;
}}
h2 {{
  font-size: 18px;
  margin: 0 0 8px 0;
}}
.badge {{
  white-space: nowrap;
  background: #065f46;
  color: #d1fae5;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
}}
.risk-high {{ border-left: 5px solid #f59e0b; }}
.risk-medium {{ border-left: 5px solid #3b82f6; }}
.risk-low {{ border-left: 5px solid #10b981; }}
code, pre {{
  background: #020617;
  color: #bfdbfe;
  border-radius: 8px;
}}
code {{ padding: 2px 5px; }}
pre {{
  padding: 12px;
  overflow-x: auto;
}}
summary {{
  cursor: pointer;
  color: #93c5fd;
  margin-top: 8px;
}}
a {{ color: #93c5fd; }}
</style>
</head>
<body>
<header>
<h1>W7TP / 小J Project Dashboard</h1>
<div>Generated: <code>{html.escape(generated)}</code></div>
<div>HEAD: <code>{html.escape(head)}</code></div>
<div>Items: <code>{len(rows)}</code></div>
</header>
<main>
{''.join(cards)}
</main>
</body>
</html>
"""

def main():
    rows = parse_board()
    OUT.write_text(build_html(rows), encoding="utf-8")
    print(f"DASHBOARD={OUT}")
    print(f"ITEMS={len(rows)}")

if __name__ == "__main__":
    main()
