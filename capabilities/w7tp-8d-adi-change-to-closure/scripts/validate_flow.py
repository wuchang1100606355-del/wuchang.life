#!/usr/bin/env python3
"""W7TP V2.3 change-to-closure minimum evidence verifier; no effect or authority."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

STAGES = (
    "BOUND", "LOCALIZED", "ISOLATED", "VERIFIED", "REVIEW_REQUESTED",
    "DECIDED", "EXECUTED", "REOBSERVED", "CLOSED",
)
GIT_STATES = {"NONE", "LOCAL_CANDIDATE", "GIT_DRAFT_ONLY", "REMOTE_REVIEWED", "MERGED"}
D8_STATES = {"NOT_SUBMITTED", "REQUEST_ACCEPTED", "ALLOW", "HOLD", "BLOCK"}
EFFECT_STATES = {"NO_EFFECT", "AUTHORIZED", "EXECUTED", "VERIFIED"}
REQUIRED = {
    "task_id", "desired_result", "stage", "git_state", "git_head",
    "d8_review_state", "d8_request_id", "d8_receipt_ref",
    "effect_state", "action_receipt_ref", "evidence_refs", "dependencies",
    "completion_conditions_met", "blockers", "next_action",
    "founder_approval_ref",
}


def validate(doc: object) -> dict:
    errors: list[str] = []
    if not isinstance(doc, dict):
        return {"state": "HOLD_FLOW_INPUT_NOT_OBJECT", "errors": ["input_not_object"], "authority_granted": False}
    missing = sorted(REQUIRED - set(doc))
    if missing:
        errors.append("missing:" + ",".join(missing))
    val = lambda k: doc.get(k)
    stage = val("stage")
    if stage not in STAGES:
        errors.append("invalid_stage")
    if val("git_state") not in GIT_STATES:
        errors.append("invalid_git_state")
    if val("d8_review_state") not in D8_STATES:
        errors.append("invalid_d8_state")
    if val("effect_state") not in EFFECT_STATES:
        errors.append("invalid_effect_state")
    if not isinstance(val("task_id"), str) or not val("task_id").strip():
        errors.append("task_id_required")
    if not isinstance(val("desired_result"), str) or not val("desired_result").strip():
        errors.append("desired_result_required")
    for key in ("evidence_refs", "dependencies", "blockers"):
        if not isinstance(val(key), list):
            errors.append(key + "_must_be_list")
    if stage in STAGES[4:] and not (isinstance(val("d8_request_id"), str) and val("d8_request_id").strip()):
        errors.append("formal_d8_request_id_required")
    if stage in STAGES[4:] and val("d8_review_state") == "NOT_SUBMITTED":
        errors.append("review_not_submitted")
    if stage in STAGES[5:] and val("d8_review_state") != "ALLOW":
        errors.append("formal_d8_allow_required")
    if stage in STAGES[5:] and not (isinstance(val("d8_receipt_ref"), str) and val("d8_receipt_ref").strip()):
        errors.append("d8_decision_receipt_required")
    if stage in STAGES[6:] and val("effect_state") not in {"EXECUTED", "VERIFIED"}:
        errors.append("verified_effect_required")
    if stage in STAGES[6:] and not (isinstance(val("action_receipt_ref"), str) and val("action_receipt_ref").strip()):
        errors.append("action_receipt_required")
    if stage in STAGES[7:] and val("effect_state") != "VERIFIED":
        errors.append("effect_reobservation_required")
    if stage == "CLOSED":
        if val("completion_conditions_met") is not True:
            errors.append("completion_conditions_not_met")
        if val("blockers"):
            errors.append("blockers_remain")
        if val("next_action") != "NONE":
            errors.append("next_action_not_closed")
        if val("dependencies"):
            errors.append("dependencies_not_closed")
    if val("d8_review_state") in {"HOLD", "BLOCK"} and stage in STAGES[5:]:
        errors.append("d8_hold_cannot_progress")
    return {
        "state": "PASS_FLOW_EVIDENCE_SHAPE_ONLY" if not errors else "HOLD_FLOW_EVIDENCE_INCOMPLETE",
        "errors": errors,
        "stage": stage,
        "task_id": val("task_id"),
        "authority_granted": False,
        "d8_review_executed": False,
        "effect_executed": False,
    }


def selftest() -> dict:
    sample = {
        "task_id": "T-EXAMPLE", "desired_result": "exact verified result",
        "stage": "ISOLATED", "git_state": "GIT_DRAFT_ONLY",
        "git_head": "abc", "d8_review_state": "NOT_SUBMITTED",
        "d8_request_id": None, "d8_receipt_ref": None,
        "effect_state": "NO_EFFECT", "action_receipt_ref": None,
        "evidence_refs": [], "dependencies": [], "completion_conditions_met": False,
        "blockers": ["D8_NOT_SUBMITTED"], "next_action": "formal request",
        "founder_approval_ref": None,
    }
    a=validate(sample)
    sample["stage"]="CLOSED"
    b=validate(sample)
    sample.update(stage="CLOSED",git_state="REMOTE_REVIEWED",d8_review_state="ALLOW",
        d8_request_id="req:1",d8_receipt_ref="d8:receipt:1",
        effect_state="VERIFIED",action_receipt_ref="effect:receipt:1",
        completion_conditions_met=True,blockers=[],next_action="NONE",
        founder_approval_ref="founder:approval:1")
    c=validate(sample)
    passed=(a["state"].startswith("PASS_") and b["state"].startswith("HOLD_") and c["state"].startswith("PASS_"))
    return {"state":"PASS_SELFTEST" if passed else "HOLD_SELFTEST", "draft_stage":a["state"], "unsafe_closed":b["state"], "eligible_shape":c["state"],"authority_granted":False}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    m=parser.add_mutually_exclusive_group(required=True)
    m.add_argument("--input",type=Path)
    m.add_argument("--selftest",action="store_true")
    args=parser.parse_args()
    try: result=selftest() if args.selftest else validate(json.loads(args.input.read_text(encoding="utf-8")))
    except (OSError,ValueError) as e:
        result={"state":"HOLD_FLOW_INPUT_INVALID","error_type":type(e).__name__,"authority_granted":False}
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0 if result["state"].startswith("PASS_") else 1

if __name__=="__main__":
    raise SystemExit(main())
