#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W7TP Staged Packet Classifier.

Read-only staged diff classifier:
- does not write repo files
- does not stage files
- does not commit
- outputs a JSON decision for staged files only

Total Field boundaries:
- af7d186 router USB governance is sealed; classify only, do not mutate.
- a5fde27 member sovereignty + AI quality gates is sealed; classify only, do not mutate.
- synthetic fixture tooling and mode-only permission hygiene must remain separate lanes.
- runtime artifacts must not be staged.
"""

import json
import subprocess
import sys
from typing import Dict, List


CATEGORIES = {
    # Sealed router USB governance lane. Classification only; no backfill.
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
    # Sealed member sovereignty / AI quality lane. Classification only; no backfill.
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
    # Synthetic generator sandbox lane. Must not mix with sealed governance lanes.
    "synthetic_fixture_tooling": [
        "tools/w7tp_synthetic_seed_fixture_generator.py",
    ],
    # Repo gate tooling lane. Commit gates must be able to land independently.
    "repo_gate_tooling": [
        "tools/w7tp_staged_packet_classifier.py",
        "tools/w7tp_commit_envelope_gate.py",
        "tools/w7tp_mode_only_permission_decision.py",
        "tools/w7tp_runtime_artifact_guard.py",
    ],
    # Total Field governance suite observers/checkers. They are tooling, not
    # sealed governance packets.
    "total_field_governance_suite_tooling": [
        "tools/w7tp_data_breathing_flow_guard.py",
        "tools/w7tp_data_breathing_flow_monitor.py",
        "tools/w7tp_flow_rhythm_aggregator.py",
        "tools/w7tp_governance_packet_auditor.py",
        "tools/w7tp_packet_coordinate_map.py",
        "tools/w7tp_total_field_governance_engine_v2.py",
    ],
    # Permission hygiene lane. Not a functional change.
    "mode_only_permission": [
        "tools/w7tp_codex_task_adapter.py",
        "tools/w7tp_packet_inference_cockpit_server.py",
        "tools/w7tp_packet_inference_runtime.py",
        "tools/w7tp_pos_p2_candidate_projection.py",
        "tools/w7tp_total_branch_runtime.py",
        "tools/w7tp_total_field_pr_layer.py",
    ],
    # Runtime evidence/artifacts are ignored and must not enter git history.
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
