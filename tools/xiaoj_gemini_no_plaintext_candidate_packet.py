#!/usr/bin/env python3
"""Build a no-plaintext Gemini candidate-worker packet.

This tool performs no external API call and reads no API key. It demonstrates
the total-field pattern where Gemini receives only a redacted candidate task
view while local verifier state remains authoritative.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from typing import Any


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+"),
    re.compile(r"(?i)client_secret\s*[:=]\s*\S+"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}"),
]

MEMBER_PLAINTEXT_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    re.compile(r"09\d{2}[- ]?\d{3}[- ]?\d{3}"),
    re.compile(r"\b[A-Z][12]\d{8}\b"),
    re.compile(r"(電話|手機|地址|身分證|身份證|生日|住址)[:：]?\s*\S+"),
]


REALITY_BOUNDARY = {
    "schema": "W7TP_LLM_REALITY_BOUNDARY_V1",
    "principle": "LLM hallucination is conditionally allowed only inside an imagined candidate layer.",
    "reality_layers": ["REAL_VERIFIED", "IMAGINED_CANDIDATE", "EXECUTABLE_AUTHORIZED"],
    "llm_hallucination_allowed": "conditional",
    "allowed_hallucination_layer": "IMAGINED_CANDIDATE",
    "environment_provided_by_total_field": True,
    "llm_self_truth_authority": False,
    "truth_boundary_ref_required": True,
    "reality_discrimination_method": (
        "total_field_supplied_environment_with_evidence_anchors_truth_boundary_ref_"
        "local_reconstruction_and_discrete_verifier_status"
    ),
    "imagined_content_must_be_labeled": True,
    "real_claim_requires_evidence_ref": True,
    "execution_claim_requires_local_gate": True,
    "cloud_can_mark_real_verified": False,
    "cloud_can_mark_executable_authorized": False,
    "total_field_distinguishes_real_or_imagined": True,
    "real_verified_source": "local_reconstruction_plus_evidence",
    "execution_source": "local_discrete_state_verifier",
}


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def redact_text(text: str) -> tuple[str, list[str]]:
    redacted = " ".join(str(text or "").split())
    flags: list[str] = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(redacted):
            flags.append("secret_shape_redacted")
            redacted = pattern.sub("[SECRET_REF]", redacted)
    for pattern in MEMBER_PLAINTEXT_PATTERNS:
        if pattern.search(redacted):
            flags.append("member_plaintext_shape_redacted")
            redacted = pattern.sub("[MEMBER_REF]", redacted)
    return redacted[:360], sorted(set(flags))


def build_packet(
    task: str,
    intent_code: str = "member_service_reply",
    member_ref: str = "MEMBER_REF_LOCAL_ONLY",
    style_ref: str = "STYLE_REF_XIAOJ_WARM_HIGH_QUALITY",
    quality_rubric_ref: str = "RUBRIC_REF_POLITE_PRECISE_ACTIONABLE",
    candidate_schema_ref: str = "SCHEMA_REF_CANDIDATE_TEXT_OR_OPTIONS_V1",
) -> dict:
    redacted_task_view, redaction_flags = redact_text(task)
    task_hash = stable_hash({"task": str(task or ""), "member_ref": member_ref})
    packet_seed = {
        "schema": "W7TP_XIAOJ_GEMINI_NO_PLAINTEXT_CANDIDATE_PACKET_V1",
        "provider": "gemini",
        "intent_code": intent_code,
        "state_code": "CANDIDATE_WORKER_REQUEST",
        "route_key": "local_zero_rtt_gemini_candidate_verifier",
        "style_ref": style_ref,
        "quality_rubric_ref": quality_rubric_ref,
        "candidate_schema_ref": candidate_schema_ref,
        "task_hash": task_hash,
        "member_ref_hash": stable_hash({"member_ref": member_ref}),
        "candidate_only": True,
        "cloud_authority": False,
        "full_body_transmitted": False,
        "reality_mode": "IMAGINED_CANDIDATE",
        "llm_hallucination_allowed": "conditional_candidate_only",
    }
    packet_hash = stable_hash(packet_seed)
    evidence_hash = stable_hash({"packet_hash": packet_hash, "route_key": packet_seed["route_key"], "task_hash": task_hash})
    cloud_payload = {
        "packet_ref": f"PACKET_REF:{packet_hash[:24]}",
        "intent_code": intent_code,
        "state_code": "CANDIDATE_WORKER_REQUEST",
        "route_key": packet_seed["route_key"],
        "style_ref": style_ref,
        "quality_rubric_ref": quality_rubric_ref,
        "candidate_schema_ref": candidate_schema_ref,
        "redacted_task_view": redacted_task_view,
        "task_hash": task_hash,
        "local_reconstruction_index": f"gemini:{intent_code}:no_plaintext:v1",
        "ttl": 30,
        "nonce": packet_hash[:24],
        "evidence_hash": evidence_hash,
        "reality_mode": "IMAGINED_CANDIDATE",
        "truth_boundary_ref": "TRUTH_BOUNDARY_REF_TOTAL_FIELD_REALITY_LAYER_V1",
        "reality_discrimination_context_ref": "REALITY_CONTEXT_REF_TOTAL_FIELD_EVIDENCE_ANCHORED_SANDBOX_V1",
        "evidence_anchor_policy": "real_claim_requires_local_evidence_ref_execution_claim_requires_local_gate",
        "hallucination_policy": "allowed_for_candidate_wording_forbidden_for_real_or_execution_claims",
    }
    return {
        **packet_seed,
        "packet_hash": packet_hash,
        "created_at_epoch": int(time.time()),
        "redaction_flags": redaction_flags,
        "reality_boundary": REALITY_BOUNDARY,
        "generative_transmission": {
            "provider": "gemini",
            "cloud_role": "candidate_worker_only",
            "reality_mode": "IMAGINED_CANDIDATE",
            "member_plaintext_transmitted": False,
            "raw_api_key_transmitted": False,
            "raw_audio_transmitted": False,
            "payment_data_transmitted": False,
            "full_body_transmitted": False,
            "local_reconstruction_required": True,
            "local_reconstruction_index": cloud_payload["local_reconstruction_index"],
            "generation_parameters": [
                "intent_code",
                "state_code",
                "route_key",
                "style_ref",
                "quality_rubric_ref",
                "candidate_schema_ref",
                "redacted_task_view",
                "task_hash",
                "evidence_hash",
                "reality_mode",
                "truth_boundary_ref",
                "reality_discrimination_context_ref",
                "evidence_anchor_policy",
                "hallucination_policy",
            ],
            "excluded_bodies": [
                "member_plaintext",
                "raw_member_profile",
                "raw_api_key",
                "oauth_token",
                "private_lookup_table",
                "full_odoo_record",
                "raw_audio",
                "payment_data",
            ],
        },
        "cloud_candidate_request": cloud_payload,
        "local_zero_latency_decision": {
            "decision_latency_class": "LOCAL_ZERO_NETWORK_RTT",
            "meaning": "authority decision does not wait for Gemini network round trip",
            "cloud_request_allowed": True,
            "safe_ui_state_before_cloud": "CANDIDATE_PENDING_OR_LOCAL_FALLBACK",
            "execution_allowed": False,
            "execution_allowed_source": "local_discrete_state_authority_only",
            "cloud_timeout_state": "QUEUE_OR_HOLD_NOT_AUTHORITY",
            "human_release_required_for_execution": True,
            "reality_decision_before_cloud_return": "IMAGINED_CANDIDATE_NOT_EXECUTABLE",
        },
        "local_verifier": {
            "verifier": "local_zero_rtt_gemini_candidate_verifier",
            "cloud_candidate_can_override": False,
            "total_field_distinguishes_real_or_imagined": True,
            "llm_hallucination_allowed_only_as_candidate": True,
            "checks": [
                "candidate_only_true",
                "cloud_authority_false",
                "reality_mode_imagined_candidate",
                "truth_boundary_ref_present",
                "cloud_cannot_mark_real_verified",
                "cloud_cannot_mark_executable_authorized",
                "no_member_plaintext_to_cloud",
                "no_raw_api_key_to_cloud",
                "ttl_present",
                "nonce_present",
                "evidence_hash_present",
                "candidate_schema_ref_present",
            ],
            "decision": "CANDIDATE_REQUEST_ALLOWED_EXECUTION_HOLD",
        },
        "evidence_seal": {
            "packet_hash": packet_hash,
            "task_hash": task_hash,
            "evidence_hash": evidence_hash,
            "redaction_flags": redaction_flags,
            "side_effects": {
                "external_api_call": False,
                "raw_api_key_read": False,
                "secret_read": False,
                "member_plaintext_read": False,
                "member_plaintext_to_cloud": False,
                "formal_db_write": False,
                "payment_capture": False,
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a no-plaintext Gemini candidate-worker packet")
    parser.add_argument("--task", default="請用溫暖、精準、可行動的方式回覆會員服務問題。")
    parser.add_argument("--intent-code", default="member_service_reply")
    parser.add_argument("--member-ref", default="MEMBER_REF_LOCAL_ONLY")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    packet = build_packet(args.task, intent_code=args.intent_code, member_ref=args.member_ref)
    print(json.dumps(packet, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
