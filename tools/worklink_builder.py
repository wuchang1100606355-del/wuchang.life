#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Worklinks Builder

Builds docs/project/WORKLINKS.md from docs/project/PROJECT_CONTROL_BOARD.md.

Safety:
- reads project board
- writes WORKLINKS.md and runtime report only
- no service restart
- no SSH
- no DB write
- no git add / commit by this script
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "docs" / "project" / "PROJECT_CONTROL_BOARD.md"
OUT = ROOT / "docs" / "project" / "WORKLINKS.md"
REPORT_DIR = ROOT / "runtime" / "reports"


SMOKE_BY_ID: Dict[str, List[str]] = {
    "M01": [
        "python3 runtime/router/eamtp_7d_translator.py --summary 'worklink smoke low risk' --intent-type ask --entry local --source-field local_ops --target-field router | python3 runtime/dead_letter/eamtp_policy_gate.py"
    ],
    "M02": [
        "python3 runtime/router/eamtp_router_guard_dryrun.py --summary 'worklink router guard dry-run smoke' --intent-type ask --entry local --source-field local_ops --target-field router"
    ],
    "M03": [
        "python3 runtime/router/merlin_intent_driver.py --intent observe_status --note 'worklink smoke only'"
    ],
    "M04": [
        "python3 runtime/router/merlin_apply_queue.py --intent observe_status --note 'worklink smoke only'"
    ],
    "M05": [
        "python3 runtime/router/merlin_approval_gate.py --latest-pending --phrase 'approve' || true"
    ],
    "M06": [
        "python3 runtime/router/merlin_human_execution_checklist.py --latest-approved || true"
    ],
    "M07": [
        "python3 runtime/router/merlin_execution_result_recorder.py --checklist latest --status observation_only --note 'worklink smoke only' || true"
    ],
    "M08": [
        "python3 tools/merlin_inventory_validator.py --file configs/merlin/router_inventory_redacted.local.json || true"
    ],
    "M09": [
        "python3 tools/merlin_inventory_to_eamtp.py --file configs/merlin/router_inventory_redacted.local.json || true"
    ],
    "M10": [
        "python3 tools/ha_mesh_script_analyzer.py --file tools/ha_mesh_script_analyzer.py --dry-run || true"
    ],
    "M11": [
        "python3 runtime/router/w7tp_causal_event_builder.py --summary 'worklink causal ledger smoke metadata only'"
    ],    "M12": [
        "python3 tools/merlin_inventory_fill_helper.py --dry-run --set router_identity.firmware_version=3006.102.7",
        "python3 tools/merlin_inventory_fill_helper.py --dry-run --set admin_surface.ssh_scope=lan_only",
        "python3 tools/merlin_inventory_validator.py --file configs/merlin/router_inventory_redacted.local.json || true"
    ],
    "M13": [
        "python3 tools/service_health_readonly.py"
    ],
    "M14": [
        "python3 tools/runtime_shadow_inventory.py --no-doc --limit 20"
    ],
    "M15": [
        "python3 tools/eamtp_packet_summarizer.py"
    ],
    "M16": [
        "tools/w7tp_smoke_all.sh || true"
    ],
    "M17": [
        "python3 -m unittest tests/test_safe_git_stage.py -v",
        "python3 tools/safe_git_stage.py --dry-run"
    ],
    "M18": [
        "python3 tools/project_dashboard_generator.py",
        "explorer.exe $(wslpath -w docs/project/PROJECT_DASHBOARD.html) || true"
    ],
    "M19": [
        "tools/open_project_dashboard.sh"
    ],
    "M20": [
        "python3 tools/task_card_generator.py",
        "code docs/project/TASK_CARDS.md"
    ],

}


def parse_board() -> List[Dict[str, object]]:
    if not BOARD.exists():
        return []

    items: List[Dict[str, object]] = []
    for line in BOARD.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| M"):
            continue

        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 8:
            continue

        files = re.findall(r"`([^`]+)`", cells[6])
        items.append({
            "id": cells[0],
            "name": cells[1],
            "status": cells[2],
            "done": cells[3],
            "risk": cells[4],
            "latest_commit": cells[5],
            "files": files,
            "next": cells[7],
        })
    return items


def code_block(lines: List[str]) -> str:
    return "```bash\n" + "\n".join(lines) + "\n```"


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    items = parse_board()
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"worklinks_{ts}.json"
    report_path.write_text(json.dumps({
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "board": str(BOARD),
        "worklinks": str(OUT),
        "items": items,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    lines: List[str] = []
    lines.append("# Worklinks")
    lines.append("")
    lines.append("Scope: Wuchang Smart Cloud / XiaoJ / W7TP mainline work entrypoints")
    lines.append("")
    lines.append(f"- Generated: `{dt.datetime.now(dt.timezone.utc).isoformat()}`")
    lines.append(f"- Source: `{BOARD}`")
    lines.append("- Rule: copy one block at a time; do not run unrelated task blocks together.")
    lines.append("")
    lines.append("## Global Safe Entry")
    lines.append("")
    lines.append(code_block([
        "cd /home/taiji_admin/Taiji_Hub || exit 1",
        "git --no-pager log --oneline -5",
        "git diff --cached --name-only",
        "git diff --name-only",
    ]))
    lines.append("")
    lines.append("## Mainline Worklinks")
    lines.append("")

    for item in items:
        wid = str(item["id"])
        files: List[str] = item["files"]  # type: ignore
        lines.append(f"### {wid}｜{item['name']}")
        lines.append("")
        lines.append(f"- Status: `{item['status']}`")
        lines.append(f"- Done: `{item['done']}`")
        lines.append(f"- Risk: `{item['risk']}`")
        lines.append(f"- Latest Commit: `{item['latest_commit']}`")
        lines.append(f"- Next: {item['next']}")
        lines.append("")
        lines.append("#### Open files in VS Code")
        lines.append("")
        lines.append(code_block(["cd /home/taiji_admin/Taiji_Hub || exit 1"] + [f"code {f}" for f in files]))
        lines.append("")
        lines.append("#### Smoke test")
        lines.append("")
        smoke = SMOKE_BY_ID.get(wid, ["echo 'No smoke test registered for this item.'"])
        lines.append(code_block(["cd /home/taiji_admin/Taiji_Hub || exit 1"] + smoke))
        lines.append("")
        lines.append("#### Git preview for this item")
        lines.append("")
        lines.append(code_block(["cd /home/taiji_admin/Taiji_Hub || exit 1", "git status --short -- \\"] + [f"  {f} \\" for f in files[:-1]] + ([f"  {files[-1]}"] if files else ["  ."])))
        lines.append("")

    lines.append("## Commit Safety")
    lines.append("")
    lines.append(code_block([
        "cd /home/taiji_admin/Taiji_Hub || exit 1",
        "git diff --cached --stat",
        "git diff --cached --name-only",
        "git --no-pager log --oneline -10",
    ]))
    lines.append("")
    lines.append("Do not use `git add .` or `git add -A`.")
    lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "decision": "worklinks_generated",
        "markdown": str(OUT),
        "report": str(report_path),
        "items": len(items),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
