#!/usr/bin/env python3
from pathlib import Path
import re
import json
import datetime as dt

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "docs/project/PROJECT_CONTROL_BOARD.md"
OUT = ROOT / "docs/project/TASK_CARDS.md"
REPORTS = ROOT / "runtime/reports"

RULES = "本機開發效率優先，但必須任務隔離；不得 git add .；不得 SSH；不得重啟服務；不得提交 runtime 產物或 local.json。"

def slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()[:50] or "task"

def parse_board():
    rows = []
    if not BOARD.exists():
        return rows
    for line in BOARD.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| M"):
            continue
        cells = [x.strip() for x in line.strip().strip("|").split("|")]
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

def git_preview(files):
    if not files:
        return "cd /home/taiji_admin/Taiji_Hub || exit 1\\ngit status --short"
    return "cd /home/taiji_admin/Taiji_Hub || exit 1\\ngit status --short -- \\\\n" + " \\\\n".join("  " + f for f in files)

def render(row):
    task_id = row["id"] + "_" + slug(row["name"])
    allowed = "\\n".join("- " + f for f in row["files"]) if row["files"] else "- none"
    preview = git_preview(row["files"])
    return "\\n".join([
        "## TASK_ID: " + task_id,
        "",
        "- Status: `" + row["status"] + "`",
        "- Done: `" + row["done"] + "`",
        "- Risk: `" + row["risk"] + "`",
        "- Commit: `" + row["commit"] + "`",
        "- Next: " + row["next"],
        "",
        "### Allowed files",
        "",
        allowed,
        "",
        "### Git preview",
        "",
        "```bash",
        preview,
        "```",
        "",
        "### Agent prompt",
        "",
        "```text",
        "TASK_ID: " + task_id,
        "",
        "目標：",
        row["name"],
        "",
        "允許讀取 / 修改：",
        allowed,
        "",
        "規則：",
        RULES,
        "",
        "完成後只回報 created files、modified files、smoke result、git preview。",
        "```",
        "",
    ])

def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = parse_board()
    lines = [
        "# Task Cards",
        "",
        "- Generated: `" + dt.datetime.now(dt.timezone.utc).isoformat() + "`",
        "- Count: `" + str(len(rows)) + "`",
        "",
        "## Rules",
        "",
        "```text",
        RULES,
        "```",
        "",
    ]
    for row in rows:
        lines.append(render(row))
    OUT.write_text("\\n".join(lines), encoding="utf-8")
    report = REPORTS / ("task_cards_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S") + ".json")
    report.write_text(json.dumps({"count": len(rows), "output": str(OUT), "execution": False}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"decision": "task_cards_generated", "count": len(rows), "markdown": str(OUT)}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
