#!/usr/bin/env python3
"""Reference-only adapters for plan-defined non-live Total Field work.

Every adapter returns candidate evidence, never final authority or a side
effect.  No network, database, model, container, deployment, or secret API is
imported or called.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from tools.total_field.w7tp_true8d_contract_sandbox import canonical_sha256


SCENE_PROFILES = frozenset({
    "ASSOCIATION", "CAFE_POS", "GENERIC", "HOUSEHOLD", "PROPERTY",
    "IDENTITY", "MEDICAL", "BUSINESS", "COMMUNITY", "IMAGE_STEP_UP",
})
FORBIDDEN_IDENTITY_KEYS = frozenset({
    "access_token", "api_key", "credential", "email", "member_plaintext",
    "name", "password", "raw_image", "raw_token", "refresh_token", "secret",
    "token",
})
FORBIDDEN_IMAGE_KEYS = frozenset({
    "age", "biometric_template", "demographic", "frame", "gender", "image",
    "image_bytes", "raw_image", "retained_abstract_image",
})


class NonLiveContractError(ValueError):
    """Stable non-live contract failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _forbidden_path(value: Any, forbidden: frozenset[str]) -> bool:
    if isinstance(value, Mapping):
        return any(str(key).casefold() in forbidden or _forbidden_path(item, forbidden) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_forbidden_path(item, forbidden) for item in value)
    return False


def validate_scene_state(value: Any) -> dict[str, Any]:
    """Validate the five-key D2 Scene State Genesis candidate contract."""

    required = {"profile_ref", "source", "baseline", "proposed", "transition"}
    if not isinstance(value, Mapping):
        return {"state": "HOLD_D2_META_CONTRACT_INCOMPLETE", "candidate_only": True}
    copied = dict(value)
    if set(copied) != required:
        return {"state": "HOLD_D2_META_CONTRACT_INCOMPLETE", "candidate_only": True}
    if copied["profile_ref"] not in SCENE_PROFILES:
        return {"state": "HOLD_UNKNOWN_SCENE", "candidate_only": True}
    if not isinstance(copied["baseline"], Mapping) or not isinstance(copied["proposed"], Mapping) or not isinstance(copied["transition"], Mapping) or not copied["transition"]:
        return {"state": "HOLD_D2_META_CONTRACT_INCOMPLETE", "candidate_only": True}
    return {
        "state": "PASS_CANDIDATE",
        "profile_ref": copied["profile_ref"],
        "input_hash": canonical_sha256(copied),
        "proposed_state_hash": canonical_sha256(copied["proposed"]),
        "transition_hash": canonical_sha256(copied["transition"]),
        "candidate_only": True,
        "canonical_change": False,
        "commit_applied": False,
    }


def evaluate_identity_evidence(value: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate hashed identity evidence without privilege inflation."""

    required = {
        "issuer_hash", "subject_hash", "device_principal_hash", "session_ref_hash",
        "connection_ref_hash", "explicit_intent_hash",
        "local_natural_person_verifier_ref", "authority_state_ref",
    }
    if _forbidden_path(value, FORBIDDEN_IDENTITY_KEYS):
        return _candidate_result("BLOCK_REQUEST_FORBIDDEN_FIELD")
    if set(value) != required:
        return _candidate_result("HOLD_IDENTITY_OR_AUTHORITY_NOT_CONVERGED")
    hashes = [value[key] for key in required if key.endswith("_hash")]
    if not all(isinstance(item, str) and len(item) == 64 and all(char in "0123456789abcdef" for char in item) for item in hashes):
        return _candidate_result("HOLD_IDENTITY_OR_AUTHORITY_NOT_CONVERGED")
    if not value["local_natural_person_verifier_ref"]:
        return _candidate_result("HOLD_LOCAL_NATURAL_PERSON_VERIFIER_NOT_BOUND")
    result = _candidate_result("PASS_CANDIDATE_IDENTITY_EVIDENCE")
    result["evidence_bundle_hash"] = canonical_sha256(value)
    result["single_factor_highest_authority"] = False
    return result


def evaluate_image_step_up(value: Mapping[str, Any]) -> dict[str, Any]:
    """Accept result-only step-up evidence and reject retained image material."""

    required = {"result_state", "evidence_ref", "algorithm_version_ref", "result_hash", "volatile_lifecycle_complete", "zeroization_evidence_ref"}
    if _forbidden_path(value, FORBIDDEN_IMAGE_KEYS):
        return _candidate_result("BLOCK_RAW_IMAGE_RETENTION_UPLINK_OR_PROFILING")
    if set(value) != required:
        return _candidate_result("HOLD_STEP_UP_RESULT_OR_LIFECYCLE_EVIDENCE_MISSING")
    if value["volatile_lifecycle_complete"] is not True or not value["zeroization_evidence_ref"]:
        return _candidate_result("HOLD_STEP_UP_RESULT_OR_LIFECYCLE_EVIDENCE_MISSING")
    if value["result_state"] not in {"PASS", "HOLD", "BLOCK"}:
        return _candidate_result("HOLD_STEP_UP_RESULT_OR_LIFECYCLE_EVIDENCE_MISSING")
    result = _candidate_result("PASS_STEP_UP_RESULT_REFERENCE_ONLY")
    result.update({"raw_image_disk_count": 0, "raw_image_uplink_count": 0, "raw_image_log_count": 0, "demographic_profiling_count": 0, "evidence_hash": canonical_sha256(value)})
    return result


def adi_direct_slot(value: Mapping[str, Any]) -> dict[str, Any]:
    """Calculate a finite-interval candidate slot with explicit collisions."""

    required = {"interval_start", "interval_end", "timestamp", "slot_count", "collision_refs"}
    if set(value) != required or any(isinstance(item, float) for item in value.values()):
        return _candidate_result("HOLD_UNRESOLVED_COLLISION_OR_INTERVAL_POLICY")
    start, end, timestamp, slot_count = value["interval_start"], value["interval_end"], value["timestamp"], value["slot_count"]
    if not all(isinstance(item, int) and not isinstance(item, bool) for item in (start, end, timestamp, slot_count)) or end <= start or slot_count <= 0 or timestamp < start or timestamp >= end:
        return _candidate_result("HOLD_UNRESOLVED_COLLISION_OR_INTERVAL_POLICY")
    width = end - start
    slot = min(slot_count - 1, ((timestamp - start) * slot_count) // width)
    collisions = value["collision_refs"]
    if not isinstance(collisions, list):
        return _candidate_result("HOLD_UNRESOLVED_COLLISION_OR_INTERVAL_POLICY")
    result = _candidate_result("PASS_ADI_DIRECT_SLOT_CANDIDATE")
    result.update({"slot": slot, "collision_bucket_size": len(collisions), "worst_case_lookup_steps": len(collisions), "unconditional_o1_claim": False, "adi_authority": False, "adi_database": False, "result_hash": canonical_sha256({"slot": slot, "collision_refs": collisions})})
    return result


def verify_temporal_chain(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Verify reference-only ordering, chaining, nonce, TTL, and replay rules."""

    if not records:
        return _candidate_result("HOLD_TRUSTED_TIME_OR_INTEGRITY_BINDING_MISSING")
    previous = "0" * 64
    nonces: set[str] = set()
    chain_hashes: list[str] = []
    for index, raw in enumerate(records):
        required = {"record_ref", "previous_hash", "payload_hash", "logical_index", "nonce", "ttl_seconds", "trusted_time_ref", "signature_ref"}
        if set(raw) != required or raw["logical_index"] != index or raw["previous_hash"] != previous:
            return _candidate_result("HOLD_TEMPORAL_INSERT_OR_REORDER")
        if raw["nonce"] in nonces:
            return _candidate_result("QUARANTINE_TEMPORAL_REPLAY")
        if not raw["trusted_time_ref"] or not raw["signature_ref"] or not isinstance(raw["ttl_seconds"], int) or raw["ttl_seconds"] <= 0:
            return _candidate_result("HOLD_TRUSTED_TIME_OR_INTEGRITY_BINDING_MISSING")
        nonces.add(raw["nonce"])
        previous = canonical_sha256(raw)
        chain_hashes.append(previous)
    result = _candidate_result("PASS_TEMPORAL_EVIDENCE_CHAIN_CANDIDATE")
    result.update({"chain_head_hash": previous, "record_hashes": chain_hashes, "metric_as_encryption_claim": False, "confidentiality_claim": "NOT_PROVIDED", "integrity_verifier": "HASH_CHAIN_SIGNATURE_TRUSTED_TIME_APPEND_ONLY_NONCE_TTL"})
    return result


def build_read_only_canary_proposal(evidence_hashes: Sequence[str]) -> dict[str, Any]:
    """Build a canary proposal that cannot start or change live state."""

    return {
        "state": "PROPOSAL_ONLY",
        "consumer": "INTENT_REFERENCE_ONLY",
        "evidence_hashes": list(evidence_hashes),
        "admission_gate": {"load1_milli_max": 2000, "memory_available_mib_min": 12288, "disk_available_gib_min": 20},
        "abort_conditions": ["FOUNDER_ABORT", "HEALTH_HOLD", "RESOURCE_HOLD", "ANY_SIDE_EFFECT"],
        "rollback": "STOP_AND_DISCARD_CANDIDATE_STATE",
        "founder_authorization_required": True,
        "canary_start_authorized": False,
        "execution_count": 0,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
        "server_llm": "BLOCK",
    }


def _candidate_result(state: str) -> dict[str, Any]:
    return {
        "state": state,
        "candidate_only": True,
        "final_authority": False,
        "execution_authority": False,
        "commit_applied": False,
        "seal_applied": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
        "external_network_called": False,
        "server_llm_called": False,
    }


__all__ = [
    "adi_direct_slot", "build_read_only_canary_proposal", "evaluate_identity_evidence",
    "evaluate_image_step_up", "validate_scene_state", "verify_temporal_chain",
]
