#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Control Board Generator

Generates docs/project/PROJECT_CONTROL_BOARD.md from known W7TP/XiaoJ
mainline anchors and current Git state.

Safety:
- read-only Git inspection
- writes only docs/project/PROJECT_CONTROL_BOARD.md and runtime report
- no service restart
- no SSH
- no DB write
- no git add / commit by this script
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "project" / "PROJECT_CONTROL_BOARD.md"
REPORT_DIR = ROOT / "runtime" / "reports"


WORK_ITEMS: List[Dict[str, object]] = [
    {
        "id": "M01",
        "name": "EAMTP-7D internal intent-state language",
        "risk": "medium",
        "files": [
            "docs/governance/EAMTP_7D_INTERNAL_LANGUAGE_SPEC.md",
            "schemas/eamtp_7d_packet.schema.json",
            "runtime/router/eamtp_7d_translator.py",
            "runtime/dead_letter/eamtp_policy_gate.py",
        ],
        "next": "Keep as base packet language; extend only through compatible schemas.",
    },
    {
        "id": "M02",
        "name": "Router Guard Dry-Run + Merlin physical boundary",
        "risk": "medium",
        "files": [
            "docs/governance/EAMTP_ROUTER_GUARD_DRYRUN.md",
            "docs/governance/W7TP_ROUTER_FIELD_MERLIN_BOUNDARY.md",
            "runtime/router/eamtp_router_guard_dryrun.py",
        ],
        "next": "Expose dry-run route only after gateway adapter review.",
    },
    {
        "id": "M03",
        "name": "Merlin Intent Driver plan-only",
        "risk": "high",
        "files": [
            "docs/governance/MERLIN_INTENT_DRIVER_GOVERNANCE.md",
            "runtime/router/merlin_intent_driver.py",
        ],
        "next": "Add more intent classes only as plan-only tickets.",
    },
    {
        "id": "M04",
        "name": "Merlin Apply Queue human-review",
        "risk": "high",
        "files": [
            "docs/governance/MERLIN_APPLY_QUEUE_GOVERNANCE.md",
            "runtime/router/merlin_apply_queue.py",
        ],
        "next": "Maintain ticket-only boundary; no router login.",
    },
    {
        "id": "M05",
        "name": "Merlin Approval Gate record-only",
        "risk": "high",
        "files": [
            "docs/governance/MERLIN_APPROVAL_GATE_GOVERNANCE.md",
            "runtime/router/merlin_approval_gate.py",
        ],
        "next": "Use exact approval phrase; still no automatic execution.",
    },
    {
        "id": "M06",
        "name": "Merlin Human Execution Checklist",
        "risk": "high",
        "files": [
            "docs/governance/MERLIN_HUMAN_EXECUTION_CHECKLIST_GOVERNANCE.md",
            "runtime/router/merlin_human_execution_checklist.py",
        ],
        "next": "Generate manual UI checklist for approved records only.",
    },
    {
        "id": "M07",
        "name": "Merlin Execution Result Recorder",
        "risk": "medium",
        "files": [
            "docs/governance/MERLIN_EXECUTION_RESULT_RECORDER.md",
            "runtime/router/merlin_execution_result_recorder.py",
        ],
        "next": "Record completed / abandoned / failed / observation_only results.",
    },
    {
        "id": "M08",
        "name": "Merlin redacted full config inventory",
        "risk": "high",
        "files": [
            "docs/governance/MERLIN_ROUTER_FULL_CONFIG_INVENTORY_SPEC.md",
            "configs/merlin/router_inventory_redacted.template.json",
            "configs/merlin/README.md",
        ],
        "next": "Keep local inventory untracked; validate before W7TP use.",
    },
    {
        "id": "M09",
        "name": "Merlin redacted inventory validator + EAMTP adapter",
        "risk": "high",
        "files": [
            "docs/governance/MERLIN_REDACTED_INVENTORY_VALIDATOR.md",
            "tools/merlin_inventory_validator.py",
            "docs/governance/MERLIN_INVENTORY_EAMTP_ADAPTER.md",
            "tools/merlin_inventory_to_eamtp.py",
        ],
        "next": "Convert only redacted local inventory into pending_review EAMTP.",
    },
    {
        "id": "M10",
        "name": "W7TP HA Mesh plan-only governance",
        "risk": "high",
        "files": [
            "docs/governance/W7TP_HA_MESH_PLAN_ONLY.md",
            "docs/governance/HA_MESH_LEGACY_SCRIPT_ANALYZER.md",
            "configs/w7tp/ha_mesh_inventory.template.json",
            "schemas/w7tp_ha_mesh_inventory.schema.json",
            "tools/ha_mesh_script_analyzer.py",
        ],
        "next": "Analyze legacy HA scripts; never execute sudo/SSH/rsync/crontab/iptables.",
    },
    {
        "id": "M11",
        "name": "W7TP Causal Ledger plan-only layer",
        "risk": "high",
        "files": [
            "docs/governance/W7TP_CAUSAL_LEDGER_PLAN_ONLY.md",
            "schemas/w7tp_causal_event_packet.schema.json",
            "runtime/router/w7tp_causal_event_builder.py",
            "tools/causal_ledger_text_analyzer.py",
        ],
        "next": "Use causal packets for audit links; no production finance or Odoo ledger writes.",
    },    {
        "id": "M12",
        "name": "Merlin redacted inventory fill helper",
        "risk": "medium",
        "files": [
            "tools/merlin_inventory_fill_helper.py",
        ],
        "next": "Use allowlisted --set updates for local redacted inventory; never commit local.json.",
    },
    {
        "id": "M13",
        "name": "Readonly service health checker",
        "risk": "low",
        "files": [
            "tools/service_health_readonly.py",
        ],
        "next": "Use GET-only health summaries before deciding whether a service needs action.",
    },
    {
        "id": "M14",
        "name": "Runtime shadow inventory",
        "risk": "low",
        "files": [
            "tools/runtime_shadow_inventory.py",
            "docs/project/RUNTIME_SHADOW_INVENTORY.md",
        ],
        "next": "Use inventory-only reports before any cleanup or archive decision.",
    },
    {
        "id": "M15",
        "name": "EAMTP packet summarizer",
        "risk": "low",
        "files": [
            "tools/eamtp_packet_summarizer.py",
        ],
        "next": "Use read-only packet summaries before router/gateway integration reviews.",
    },
    {
        "id": "M16",
        "name": "W7TP smoke all checker",
        "risk": "low",
        "files": [
            "tools/w7tp_smoke_all.sh",
        ],
        "next": "Run before integration commits to verify mainline tools are still usable.",
    },
    {
        "id": "M17",
        "name": "Safe git stage allowlist tool",
        "risk": "low",
        "files": [
            "tools/safe_git_stage.py",
            "docs/project/git_stage_allowlist.txt",
            "tests/test_safe_git_stage.py",
        ],
        "next": "Use before multi-agent commits to preview/stage only allowlisted canonical files.",
    },
    {
        "id": "M18",
        "name": "Project dashboard HTML generator",
        "risk": "low",
        "files": [
            "tools/project_dashboard_generator.py",
            "docs/project/PROJECT_DASHBOARD.html",
        ],
        "next": "Open local dashboard to copy task commands and inspect mainline status.",
    },
    {
        "id": "M19",
        "name": "Project dashboard launcher",
        "risk": "low",
        "files": [
            "tools/open_project_dashboard.sh",
        ],
        "next": "Use this launcher to regenerate and open the local project dashboard.",
    },
    {
        "id": "M20",
        "name": "Multi-agent task card generator",
        "risk": "low",
        "files": [
            "tools/task_card_generator.py",
            "docs/project/TASK_CARDS.md",
        ],
        "next": "Use generated task cards to delegate isolated work to code agents.",
    },
    {
        "id": "M21",
        "name": "Container server offload plan-only",
        "risk": "medium",
        "files": [
            "docs/governance/W7TP_CONTAINER_SERVER_OFFLOAD_PLAN.md",
            "configs/containers/container_offload_registry.template.json",
            "schemas/w7tp_container_offload_registry.schema.json",
            "tools/container_offload_linter.py",
        ],
        "next": "Use offload registry and linter before moving background containers to pure Linux server nodes.",
    },
    {
        "id": "M22",
        "name": "Indexer one-shot server job package",
        "risk": "medium",
        "files": [
            "configs/containers/wuchang_indexer_oneshot_job.template.json",
            "docs/governance/W7TP_INDEXER_ONE_SHOT_SERVER_JOB.md",
            "tools/indexer_oneshot_job_linter.py",
        ],
        "next": "Use one-shot job template and linter before moving indexer workload to a pure Linux server.",
    },

]


def run(cmd: List[str]) -> str:
    try:
        return subprocess.check_output(cmd, cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except subprocess.CalledProcessError as e:
        return e.output.strip()


def is_tracked(path: str) -> bool:
    out = run(["git", "ls-files", "--", path])
    return bool(out.strip())


def git_status(path: str) -> str:
    return run(["git", "status", "--short", "--", path])


def latest_commit_for(path: str) -> str:
    out = run(["git", "--no-pager", "log", "-1", "--format=%h %s", "--", path])
    return out if out else ""


def completion(files: List[str]) -> int:
    if not files:
        return 0
    tracked = sum(1 for f in files if is_tracked(f))
    return round(tracked / len(files) * 100)


def status_for(files: List[str]) -> str:
    pct = completion(files)
    dirty = any(bool(git_status(f)) for f in files)
    if pct == 100 and not dirty:
        return "done_clean"
    if pct == 100 and dirty:
        return "done_dirty"
    if pct > 0:
        return "partial"
    return "missing"


def md_table_rows() -> List[str]:
    rows = []
    for item in WORK_ITEMS:
        files = item["files"]  # type: ignore
        pct = completion(files)
        st = status_for(files)
        commits = [latest_commit_for(f) for f in files if latest_commit_for(f)]
        latest = commits[0] if commits else ""
        file_links = "<br>".join(f"`{f}`" for f in files)
        rows.append(
            f"| {item['id']} | {item['name']} | {st} | {pct}% | {item['risk']} | {latest} | {file_links} | {item['next']} |"
        )
    return rows


def build_report() -> Dict[str, object]:
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "head": run(["git", "--no-pager", "log", "--oneline", "-1"]),
        "items": [
            {
                "id": item["id"],
                "name": item["name"],
                "status": status_for(item["files"]),  # type: ignore
                "completion": completion(item["files"]),  # type: ignore
                "risk": item["risk"],
                "files": item["files"],
                "next": item["next"],
            }
            for item in WORK_ITEMS
        ],
    }


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report = build_report()
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"project_control_board_{ts}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append("# Project Control Board")
    lines.append("")
    lines.append("Scope: Wuchang Smart Cloud / XiaoJ / W7TP mainline anchors")
    lines.append("")
    lines.append(f"- Generated: `{report['generated_at']}`")
    lines.append(f"- HEAD: `{report['head']}`")
    lines.append("- Rule: runtime reports/proofs/queues are not canonical commit targets.")
    lines.append("")
    lines.append("## Mainline Board")
    lines.append("")
    lines.append("| ID | Work Item | Status | Done | Risk | Latest Commit | Canonical Files | Next Step |")
    lines.append("|---|---|---:|---:|---|---|---|---|")
    lines.extend(md_table_rows())
    lines.append("")
    lines.append("## Integration Rules")
    lines.append("")
    lines.append("- Do not use `git add .` or `git add -A`.")
    lines.append("- Only stage explicit canonical files for the active task.")
    lines.append("- Do not commit `runtime/reports`, `runtime/proofs`, `runtime/merlin_*`, or local inventories.")
    lines.append("- Router, SSH, Odoo/Postgres, service restart, and credential operations require explicit review.")
    lines.append("")
    lines.append("## Recommended Next Work")
    lines.append("")
    lines.append("1. Build `WORKLINKS.md` from this board.")
    lines.append("2. Add isolated task cards for A06/A07/A08 if needed.")
    lines.append("3. Keep mainline and side tasks separated.")
    lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "decision": "project_board_generated",
        "markdown": str(OUT),
        "report": str(report_path),
        "items": len(WORK_ITEMS),
        "head": report["head"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
