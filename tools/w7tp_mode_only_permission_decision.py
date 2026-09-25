#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W7TP Mode-Only Permission Decision.

- Does not write repo files.
- Does not stage files.
- Does not commit.
- Does not deploy.
- Observes permission-bit hygiene only.

Total Field constraints:
- af7d186 router USB governance is sealed; this tool does not modify it.
- a5fde27 member sovereignty + AI quality gates is sealed; this tool does not
  modify it.
- ffff3fe synthetic generator sandbox is isolated; this tool does not mix it.
- Mode-only changes are not functional changes and require an independent
  explicit decision.
"""

import argparse
import json
import subprocess
from typing import Dict, List


MODE_ONLY_ALLOWLIST = {
    "tools/w7tp_codex_task_adapter.py",
    "tools/w7tp_packet_inference_cockpit_server.py",
    "tools/w7tp_packet_inference_runtime.py",
    "tools/w7tp_pos_p2_candidate_projection.py",
    "tools/w7tp_total_branch_runtime.py",
    "tools/w7tp_total_field_pr_layer.py",
}

DECISION_OPTIONS = [
    "COMMIT_MODE_ONLY_SEPARATELY",
    "DISCARD_MODE_ONLY_CHANGES",
]


def run_git(args: List[str]) -> str:
    return subprocess.check_output(["git", *args], text=True)


def diff_summary(staged: bool) -> List[str]:
    cmd = ["diff", "--summary"]
    if staged:
        cmd.append("--cached")
    return [line.strip() for line in run_git(cmd).splitlines() if line.strip()]


def name_only(staged: bool) -> List[str]:
    cmd = ["diff", "--name-only"]
    if staged:
        cmd.append("--cached")
    return [line.strip() for line in run_git(cmd).splitlines() if line.strip()]


def name_status(staged: bool) -> List[str]:
    cmd = ["diff", "--name-status"]
    if staged:
        cmd.append("--cached")
    return [line.strip() for line in run_git(cmd).splitlines() if line.strip()]


def parse_mode_changes(lines: List[str]) -> List[Dict[str, str]]:
    changes = []
    prefix = "mode change "
    for line in lines:
        if not line.startswith(prefix):
            continue
        parts = line.split()
        if len(parts) >= 6 and parts[0] == "mode" and parts[1] == "change":
            changes.append({
                "old_mode": parts[2],
                "new_mode": parts[4],
                "path": parts[5],
            })
    return changes


def content_changed_paths(staged: bool, mode_paths: List[str]) -> List[str]:
    changed = []
    for path in mode_paths:
        cmd = ["diff", "--numstat"]
        if staged:
            cmd.append("--cached")
        cmd.extend(["--", path])
        output = run_git(cmd).strip().splitlines()
        has_content_delta = False
        for line in output:
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            insertions, deletions = parts[0], parts[1]
            if insertions.isdigit() and deletions.isdigit():
                has_content_delta = has_content_delta or int(insertions) > 0 or int(deletions) > 0
            else:
                has_content_delta = True
        if has_content_delta:
            changed.append(path)
    return changed


def decide(staged: bool = False) -> Dict[str, object]:
    mode_changes = parse_mode_changes(diff_summary(staged))
    mode_paths = [change["path"] for change in mode_changes]
    mode_path_set = set(mode_paths)
    all_changed = name_only(staged)
    all_name_status = name_status(staged)
    mode_only_name_status = [
        line for line in all_name_status
        if line.split("\t")[-1] in mode_path_set
    ]
    non_mode_paths = sorted(set(all_changed) - set(mode_paths))
    unapproved = sorted(path for path in mode_paths if path not in MODE_ONLY_ALLOWLIST)
    content_changed = content_changed_paths(staged, mode_paths)

    if not mode_changes:
        state = "PASS_MODE_ONLY_PERMISSION_NO_CHANGES"
    elif unapproved:
        state = "HOLD_MODE_ONLY_PERMISSION_UNAPPROVED_PATH"
    elif content_changed:
        state = "HOLD_MODE_ONLY_PERMISSION_WITH_CONTENT_CHANGE"
    elif non_mode_paths:
        state = "HOLD_MODE_ONLY_PERMISSION_MIXED_WITH_FUNCTIONAL"
    else:
        state = "PASS_MODE_ONLY_PERMISSION_INDEPENDENT_DECISION_READY"

    return {
        "STATE": state,
        "review_state": "REVIEW_MODE_ONLY_PERMISSION" if mode_changes else "PASS_NO_MODE_ONLY",
        "mode": "staged" if staged else "worktree",
        "mode_changes": mode_changes,
        "mode_only_changes": mode_only_name_status,
        "mode_change_count": len(mode_changes),
        "unapproved_mode_paths": unapproved,
        "content_changed_mode_paths": content_changed,
        "non_mode_changed_paths": non_mode_paths,
        "decision_options": DECISION_OPTIONS if mode_changes else [],
        "recommended_action": (
            "independent_commit_or_restore_only_after_explicit_total_field_decision"
            if mode_changes and state.startswith("PASS_")
            else "review_required"
        ),
        "writes_repo": False,
        "auto_stage": False,
        "auto_commit": False,
        "deploy": False,
        "db_write": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staged", action="store_true", help="inspect staged diff instead of working tree diff")
    args = parser.parse_args()

    result = decide(staged=args.staged)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["STATE"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
