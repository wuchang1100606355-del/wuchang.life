"""Versioned cognition policy that cannot modify Total Field authority."""

from __future__ import annotations

from typing import Any, Mapping

from tools.total_field.w7tp_field_application_runtime import (
    FieldApplicationError,
    device_llm_execution_policy,
)

from .canonical_hash import canonical_sha256, normalize_content


IMMUTABLE_POLICY_KEYS = frozenset(
    {
        "founder_authority",
        "total_field_authority",
        "d8_authority",
        "scenario_route_table",
        "capability_registry",
        "sensitive_data_rules",
        "generative_transmission_canonical",
        "llm_inference_location",
        "model_context_upload",
        "raw_prompt_upload",
        "server_llm_execution",
        "transaction_authority",
        "cloud_fallback",
    }
).union(device_llm_execution_policy())
ALLOWED_ADAPTIVE_KEYS = frozenset(
    {
        "question_order",
        "safe_explanations",
        "evidence_candidate_order",
        "cpu_gpu_assignment",
        "ui_detail_level",
        "sourced_memory_candidates",
    }
)
DEFAULT_POLICY = {
    "version": "1.1.0",
    "source_refs": ["repo:docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1_FOUNDER_LOCKED_SUCCESSOR_20260728.md"],
    "legacy_source_refs": ["repo:docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2.md"],
    "migration_mode": "APPEND_ONLY_SUCCESSOR",
    "question_order": "CONTRACT_ORDER",
    "safe_explanations": "PROFILE_SPECIFIC",
    "evidence_candidate_order": "SOURCE_THEN_PASS_THEN_USER",
    "cpu_gpu_assignment": "USER_DEVICE_LLM_SERVER_NON_LLM_GPU_OPTIONAL",
    **device_llm_execution_policy(),
    "ui_detail_level": "ACCESSIBLE_PROGRESSIVE_DISCLOSURE",
    "sourced_memory_candidates": "CANDIDATE_ONLY",
    "immutable_controls": sorted(IMMUTABLE_POLICY_KEYS),
}


def active_policy() -> dict[str, Any]:
    policy = normalize_content(DEFAULT_POLICY)
    policy["policy_hash"] = canonical_sha256(policy)
    return policy


def build_cognition_update_candidate(changes: Mapping[str, Any], evidence_refs: list[str]) -> dict[str, Any]:
    normalized = normalize_content(dict(changes))
    forbidden = sorted(set(normalized).intersection(IMMUTABLE_POLICY_KEYS))
    unknown = sorted(set(normalized).difference(ALLOWED_ADAPTIVE_KEYS))
    if forbidden:
        raise FieldApplicationError("COGNITION_IMMUTABLE_CONTROL_BLOCKED", f"$.{forbidden[0]}")
    if unknown:
        raise FieldApplicationError("COGNITION_CHANGE_NOT_ALLOWED", f"$.{unknown[0]}")
    if not evidence_refs:
        raise FieldApplicationError("COGNITION_EVIDENCE_REQUIRED")
    candidate: dict[str, Any] = {
        "schema_version": "W7TP-ADAPTIVE-COGNITION/1.0",
        "state": "COGNITION_UPDATE_CANDIDATE",
        "base_policy_hash": active_policy()["policy_hash"],
        "changes": normalized,
        "evidence_refs": normalize_content(evidence_refs),
        "adoption": "REQUIRES_VERIFIED_FOUNDER_AND_TOTAL_FIELD",
        "candidate_only": True,
    }
    candidate["policy_hash"] = canonical_sha256(candidate)
    return candidate
