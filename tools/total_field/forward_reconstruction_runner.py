"""Forward-only Total Field generative reconstruction runner.

Hard rules:
- no delete
- no restore
- no DB write
- no deploy
- no restart
- no router write
- no user paste burden when existing evidence can reconstruct
- no nonessential validation
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from typing import Any, Dict, Iterable, List, Mapping, Sequence


CAFE_PACKET = "CAFE_BUSINESS_ONBOARDING_FINAL_FORM_LOCK"
COCKPIT_PREFIX = "web/packet_inference_cockpit/"

GATE_SCOPE_FILES = {
    "tools/total_field/final_state_gate.py",
    "tests/test_total_field_final_state_gate.py",
}

DELETE_ACTIONS = {
    "delete",
    "rm",
    "remove",
    "clean",
    "git_clean",
    "docker_prune",
    "apt_clean",
    "npm_cache_clean",
    "truncate",
    "clear_runtime",
    "restore",
    "git_restore",
}

PASTE_BURDEN_ACTIONS = {
    "paste",
    "repost",
    "rerun",
    "ask_user_to_paste",
    "ask_user_to_rerun",
    "ask_user_to_transfer",
    "send_to_codex",
    "new_thread_transfer",
}

UNAUTHORIZED_EXPANSION_MARKERS = {
    "cloud_translator",
    "ai_key_ui",
    "literary_flow",
    "scenario_deck",
    "frontend_demo_expansion",
    "whitepaper",
    "architecture_report",
}


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def fingerprint(value: Any, length: int = 16) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()[:length]


def _unique(values: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _lower_actions(actions: Sequence[str]) -> set[str]:
    return {str(action).strip().lower().replace("-", "_") for action in actions if str(action).strip()}


def parse_porcelain_path(line: str) -> str:
    raw = line[3:] if len(line) > 3 else line.strip()
    raw = raw.strip()
    if " -> " in raw:
        raw = raw.split(" -> ", 1)[1].strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    return raw


def gather_git_touched_paths(repo: str = ".") -> List[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        return []
    return _unique(parse_porcelain_path(line) for line in result.stdout.splitlines())


def classify_path(path: str) -> str:
    if path in GATE_SCOPE_FILES:
        return "detour_gate_scope"
    if path.startswith(COCKPIT_PREFIX):
        return "frontend_cockpit"
    if "cafe_business_onboarding" in path:
        return "cafe_business_onboarding"
    if "wuchang_cafe_ai_gateway" in path:
        return "cafe_gateway"
    if path.startswith("runtime/"):
        return "runtime_output"
    if path.startswith("docs/"):
        return "docs"
    if path.startswith("tests/"):
        return "tests"
    if path.startswith("tools/"):
        return "tools"
    return "other"


def evidence_is_sufficient(evidence: Mapping[str, Any]) -> bool:
    keys = {
        "STATE",
        "RUN_ID",
        "TESTS",
        "PY_COMPILE",
        "GIT_STATUS",
        "FILES_CHANGED",
        "state",
        "run_id",
        "tests",
        "py_compile",
        "git_status",
        "files_changed",
        "tests_pass",
    }
    return any(bool(evidence.get(key)) for key in keys)


def build_source_packet(
    *,
    target_packet: str,
    touched_paths: Sequence[str],
    evidence: Mapping[str, Any] | None = None,
    requested_actions: Sequence[str] | None = None,
) -> Dict[str, Any]:
    paths = _unique(touched_paths)
    return {
        "packet_type": "total_field_forward_reconstruction_source_packet",
        "target_packet": target_packet,
        "source": "existing_repo_state",
        "touched_paths": paths,
        "path_classes": {path: classify_path(path) for path in paths},
        "requested_actions": list(requested_actions or []),
        "evidence": dict(evidence or {}),
        "constraints": {
            "zero_delete": True,
            "zero_restore": True,
            "zero_db_write": True,
            "zero_deploy": True,
            "zero_restart": True,
            "zero_router_write": True,
            "zero_runtime_bulk_output": True,
            "user_extra_action_forbidden": True,
            "nonessential_validation_forbidden": True,
        },
        "required_route": "SOURCE -> PACKET -> RECONSTRUCT -> VERIFY -> TOTAL_FIELD_DECIDES -> SEAL/HOLD",
    }


def detect_detour(packet: Mapping[str, Any]) -> Dict[str, Any]:
    target = str(packet.get("target_packet", "")).upper()
    paths = [str(path) for path in packet.get("touched_paths", [])]
    actions = _lower_actions(packet.get("requested_actions", []))
    evidence = packet.get("evidence", {})
    if not isinstance(evidence, Mapping):
        evidence = {}

    reasons: List[str] = []

    if evidence.get("context_window_full") or "context_window_full" in actions:
        reasons.append("CONTEXT_WINDOW_FULL")

    if CAFE_PACKET in target and any(path.startswith(COCKPIT_PREFIX) for path in paths):
        reasons.append("CAFE_ONBOARDING_TOUCHED_COCKPIT_UI")
        reasons.append("TARGET_PACKET_MISMATCH")
        reasons.append("TOUCHED_OUT_OF_SCOPE_PATH")

    if "BACKEND" in target and any(path.startswith(COCKPIT_PREFIX) for path in paths):
        reasons.append("BACKEND_TASK_TOUCHED_FRONTEND")

    if evidence.get("target_packet_mismatch"):
        reasons.append("TARGET_PACKET_MISMATCH")

    if evidence.get("touched_out_of_scope_path"):
        reasons.append("TOUCHED_OUT_OF_SCOPE_PATH")

    if actions & DELETE_ACTIONS:
        if "restore" in actions or "git_restore" in actions:
            if evidence.get("diff_ownership_confirmed") is not True:
                reasons.append("RESTORE_WITHOUT_DIFF_OWNERSHIP")
        reasons.append("ZERO_DELETE_OR_RESTORE_VIOLATION")

    if actions & PASTE_BURDEN_ACTIONS and evidence_is_sufficient(evidence):
        reasons.append("PASTE_BURDEN_WHEN_RECONSTRUCTABLE")
        reasons.append("USER_EXTRA_ACTION_BURDEN")

    if ("rerun" in actions or "ask_user_to_rerun" in actions) and evidence_is_sufficient(evidence):
        reasons.append("PASS_EXISTS_BUT_RERUN_REQUESTED")
        reasons.append("NONESSENTIAL_VALIDATION_BURDEN")

    if actions & UNAUTHORIZED_EXPANSION_MARKERS:
        reasons.append("UNAUTHORIZED_FEATURE_EXPANSION")

    if evidence.get("min_landing") and evidence.get("long_report_or_architecture_expansion"):
        reasons.append("MIN_LANDING_BUT_REPORT_OR_ARCHITECTURE_EXPANSION")

    if evidence.get("user_operation_burden_increased"):
        reasons.append("USER_OPERATION_BURDEN_INCREASED")

    if evidence.get("non_generative_path") or "non_generative_path" in actions:
        reasons.append("NON_GENERATIVE_RECONSTRUCTION_PATH")

    reasons = _unique(reasons)

    if reasons:
        return {
            "decision": "HOLD_DETOUR_ALERT",
            "reasons": reasons,
            "rule": "凡可由總場、既有證據、diff、RUN_ID、TESTS、PY_COMPILE、GIT_STATUS、生成式重構判斷者，不得轉嫁使用者貼、跑、轉交、重驗。",
            "required_path": "SOURCE -> PACKET -> RECONSTRUCT -> VERIFY -> TOTAL_FIELD_DECIDES -> SEAL/HOLD",
            "next": "USE_EXISTING_EVIDENCE_AND_GENERATIVE_RECONSTRUCTION",
        }

    return {
        "decision": "PASS_DETOUR_GATE",
        "reasons": [],
        "required_path": "SOURCE -> PACKET -> RECONSTRUCT -> VERIFY -> TOTAL_FIELD_DECIDES -> SEAL/HOLD",
    }


def self_seed_onboarding_inputs(evidence: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    data = dict(evidence or {})
    return {
        "responsible_person_ref": data.get(
            "responsible_person_ref",
            "responsible_person_ref:existing_member_registration_owner_admin_review_required",
        ),
        "organization_ref": data.get(
            "organization_ref",
            "organization_ref:existing_member_type_organization_review_required",
        ),
        "business_info": data.get(
            "business_info",
            {
                "source": "self_seeded_candidate",
                "business_kind": "cafe",
                "store_role": "candidate_merchant",
                "activation": "review_required",
            },
        ),
    }


def reconstruct_cafe_onboarding_candidate(packet: Mapping[str, Any]) -> Dict[str, Any]:
    evidence = packet.get("evidence", {})
    if not isinstance(evidence, Mapping):
        evidence = {}
    seed = self_seed_onboarding_inputs(evidence)
    fp = fingerprint(
        {
            "target_packet": packet.get("target_packet"),
            "seed": seed,
            "path_classes": packet.get("path_classes", {}),
        }
    )

    merchant_packet = {
        "packet_type": "merchant_8d_7d_candidate",
        "authority": "total_field_candidate_not_production",
        "d1_intent": "cafe_business_onboarding",
        "d2_state": "candidate_only_waiting_owner_admin_review",
        "d3_coordinate": {
            "responsible_person_ref": seed["responsible_person_ref"],
            "organization_ref": seed["organization_ref"],
            "business_ref": f"merchant_candidate:{fp}",
        },
        "d4_evidence": {
            "source_packet_fingerprint": fp,
            "source": "existing_repo_state_and_self_seeded_refs",
        },
        "d5_execution": "no_db_write_no_deploy_no_restart_no_router_write_no_payment_capture",
        "d6_technical_definition": "generative_reconstruction_from_refs_and_state_packet_not_file_transfer",
        "d7_risk": {
            "production_activation_blocked": True,
            "human_owner_review_required": True,
            "formal_operation_not_enabled": True,
        },
        "d8_envelope": {
            "seal": f"candidate:{fp}",
            "ttl": "review_required",
            "decision_authority": "total_field",
        },
        "seven_d_functional_state": {
            "tenant_profile": "candidate",
            "service_profile": "candidate",
            "container_config": "candidate_no_create",
            "url_routing": "candidate_no_live_route",
        },
    }

    return {
        "candidate_type": "cafe_business_onboarding_final_form_candidate",
        "fingerprint": fp,
        "production_activation_ready": False,
        "responsible_person_ref": seed["responsible_person_ref"],
        "organization_ref": seed["organization_ref"],
        "business_info": seed["business_info"],
        "merchant_8d_7d_packet": merchant_packet,
        "adi_5d_ref": f"adi5d://wuchang/cafe_business_onboarding/candidate/{fp}",
        "tenant_profile_candidate": {
            "tenant_ref": f"tenant_candidate:{fp}",
            "mode": "candidate_only",
            "write_db": False,
        },
        "service_profile_candidate": {
            "service_ref": f"service_candidate:{fp}",
            "mode": "candidate_only",
            "formal_service_enabled": False,
        },
        "container_config_candidate": {
            "container_ref": f"container_config_candidate:{fp}",
            "create_container": False,
            "restart": False,
            "deploy": False,
        },
        "url_routing_candidate": {
            "route_ref": f"url_route_candidate:{fp}",
            "create_live_route": False,
            "router_write": False,
        },
        "hard_risk_controls": {
            "db_write": False,
            "deploy": False,
            "restart": False,
            "router_write": False,
            "payment_capture": False,
            "formal_activation": False,
            "delete": False,
            "restore": False,
        },
    }


def verify_reconstructed_candidate(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    required = [
        "merchant_8d_7d_packet",
        "adi_5d_ref",
        "tenant_profile_candidate",
        "service_profile_candidate",
        "container_config_candidate",
        "url_routing_candidate",
    ]
    missing = [key for key in required if key not in candidate]
    if missing:
        return {
            "decision": "HOLD",
            "reason": "MISSING_RECONSTRUCTED_FIELDS",
            "missing": missing,
        }

    hard_controls = candidate.get("hard_risk_controls", {})
    if not isinstance(hard_controls, Mapping):
        hard_controls = {}

    blocked = [key for key, value in hard_controls.items() if bool(value)]
    if bool(candidate.get("production_activation_ready")) or blocked:
        return {
            "decision": "BLOCK",
            "reason": "HARD_RISK_REQUESTED",
            "blocked": blocked or ["production_activation_ready"],
        }

    return {
        "decision": "PASS_RECONSTRUCTED_CANDIDATE",
        "reason": "candidate_only_no_hard_risk",
    }


def total_field_reconstruct(packet: Mapping[str, Any]) -> Dict[str, Any]:
    detour = detect_detour(packet)
    packet_fp = fingerprint(packet)

    if detour["decision"] == "HOLD_DETOUR_ALERT":
        return {
            "STATE": "HOLD_DETOUR_ALERT",
            "PACKET_FINGERPRINT": packet_fp,
            "DETOUR": detour,
            "TOTAL_FIELD_DECISION": "HOLD",
            "NEXT": "RECONSTRUCT_FROM_EXISTING_EVIDENCE_WITHOUT_USER_EXTRA_ACTION",
        }

    candidate = reconstruct_cafe_onboarding_candidate(packet)
    verification = verify_reconstructed_candidate(candidate)

    return {
        "STATE": verification["decision"],
        "PACKET_FINGERPRINT": packet_fp,
        "TOTAL_FIELD_DECISION": verification["decision"],
        "VERIFY": verification,
        "RECONSTRUCTED_CANDIDATE": candidate,
        "NEXT": "SEAL_OR_OWNER_ADMIN_REVIEW",
    }


def parse_evidence_json(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        return {"raw_evidence": parsed}
    return parsed


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--target", default=CAFE_PACKET)
    parser.add_argument("--action", action="append", default=[])
    parser.add_argument("--evidence-json", default="")
    parser.add_argument("--no-git", action="store_true")
    args = parser.parse_args(argv)

    touched_paths = [] if args.no_git else gather_git_touched_paths(args.repo)
    evidence = parse_evidence_json(args.evidence_json)
    packet = build_source_packet(
        target_packet=args.target,
        touched_paths=touched_paths,
        evidence=evidence,
        requested_actions=args.action,
    )
    result = total_field_reconstruct(packet)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    main()
