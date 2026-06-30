#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W7TP Staged Packet Classifier.

Read-only staged diff classifier:
- does not write repo files
- does not stage files
- does not commit
- outputs a JSON decision for staged files only
"""

import json
import subprocess
import sys
from typing import Dict, List


CATEGORIES = {
    "router_usb_governance": [
        "configs/data_breathing_flow/",
        "configs/router/",
        "schemas/w7tp_data_breathing_flow_record.schema.json",
        "schemas/w7tp_router_",
        "schemas/w7tp_usb_",
        "tools/w7tp_router_usb_",
        "tools/w7tp_usb_dead_letter_",
        "docs/governance/W7TP_DATA_BREATHING_FLOW_ROUTER_",
    ],
    "member_sovereignty_quality": [
        "docs/governance/XIAOJ_",
        "docs/product/AI_BROWSER_",
        "docs/product/D8_BIG_TECH_",
        "docs/total_field/MEMBER_SOVEREIGNTY_",
        "docs/total_field/ODOO_MEMBER_SCENARIO_",
        "tools/w7tp_8d_lookup_",
        "tools/w7tp_big_tech_quality_tester.py",
        "tools/w7tp_candidate_packet_extractor.py",
    ],
    "synthetic_fixture_tooling": [
        "tools/w7tp_synthetic_seed_fixture_generator.py",
    ],
    "repo_gate_tooling": [
        "tools/w7tp_staged_packet_classifier.py",
    ],
    "mode_only_permission": [
        "tools/w7tp_codex_task_adapter.py",
        "tools/w7tp_packet_inference_cockpit_server.py",
        "tools/w7tp_packet_inference_runtime.py",
        "tools/w7tp_pos_p2_candidate_projection.py",
        "tools/w7tp_total_branch_runtime.py",
        "tools/w7tp_total_field_pr_layer.py",
    ],
    "runtime_artifact": [
        "runtime/",
    ],
}


def classify(path: str) -> str:
    for category, prefixes in CATEGORIES.items():
        for prefix in prefixes:
            if path.startswith(prefix):
                return category
    return "unknown"


def staged_name_status() -> List[Dict[str, str]]:
    raw = subprocess.check_output(
        ["git", "diff", "--cached", "--name-status"],
        text=True,
    ).splitlines()
    entries = []
    for line in raw:
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        entries.append({"status": status, "path": path, "category": classify(path)})
    return entries


def decide(entries: List[Dict[str, str]]) -> str:
    categories = {entry["category"] for entry in entries}
    functional_categories = categories - {"mode_only_permission"}

    if not entries:
        return "PASS_STAGED_PACKET_CLASSIFIER_EMPTY"
    if "runtime_artifact" in categories:
        return "HOLD_RUNTIME_ARTIFACT_STAGED"
    if "unknown" in categories:
        return "HOLD_UNKNOWN_STAGED_PATH"
    if "mode_only_permission" in categories and functional_categories:
        return "HOLD_MODE_ONLY_MIXED_WITH_FUNCTIONAL"
    if len(functional_categories) > 1:
        return "HOLD_MIXED_GOVERNANCE_PACKET"
    return "PASS_STAGED_PACKET_CLASSIFIER"


def main() -> int:
    entries = staged_name_status()
    decision = decide(entries)
    categories = sorted({entry["category"] for entry in entries})
    result = {
        "STATE": decision,
        "decision": decision,
        "files": entries,
        "categories": categories,
        "writes_repo": False,
        "auto_stage": False,
        "auto_commit": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if decision.startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
