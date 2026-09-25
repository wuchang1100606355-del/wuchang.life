from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from .distance import (
    BreakpointReachabilityDenied,
    TransitionRuleHold,
    resolve_canonical_path,
)
from .models import NativeLookupReceipt, NativeTransitionRule, StatePacket8D
from .projection import metric_signature_f, positive_negative_boundaries, project_8d_state

SOURCE_REF = "FOUNDER_NATIVE_ADI_RULE_DECLARATION_V1.md#evidence-closure-unique-fixed-point-and-stop"


FORBIDDEN_NATIVE_PROXIES = (
    "morton",
    "z-order",
    "z order",
    "bit interleaving",
    "manhattan",
    "chebyshev",
    "euclidean",
    "cosine similarity",
    "gray code",
    "gray-code",
    "hilbert",
    "vector similarity",
    "generic nearest-neighbor",
    "generic nearest neighbor",
    "speculative decoding",
    "kv cache",
    "pagedattention",
    "token-level constrained decoding",
    "tree index",
    "tree-index",
    "geometric helix",
    "fixed phase",
    "模型投票",
    "模型平均",
)


@dataclass(frozen=True)
class ValidationDecision:
    state: str
    reason: str


def _canonical_bytes(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def candidate_state_root_f(packet: StatePacket8D) -> str:
    """Reproduce the candidate root without trusting its supplied root field."""
    material = {
        "dimensions": list(packet.dimensions),
        "event_time": packet.event_time,
        "namespace": packet.namespace,
        "state_profile": packet.state_profile,
        "native_state_ref": packet.native_state_ref,
        "parent_state_root": packet.parent_state_root,
        "evidence_root": packet.evidence_root,
        "snapshot_id": packet.snapshot_id,
        "canonical_version": packet.canonical_version,
        "rule_version": packet.rule_version,
        "logical_time": packet.logical_time,
        "topology_coordinate_ref": packet.topology_coordinate_ref,
        "event_hash_ref": packet.event_hash_ref,
    }
    if packet.breakpoint_segment_ref is not None:
        material["breakpoint_segment_ref"] = packet.breakpoint_segment_ref
    return hashlib.sha256(_canonical_bytes(material)).hexdigest()


def validate_8d(packet: StatePacket8D) -> ValidationDecision:
    try:
        project_8d_state(packet)
    except ValueError as exc:
        return ValidationDecision("BLOCK", str(exc))
    if packet.logical_time < 0:
        return ValidationDecision("BLOCK", "BLOCK_INVALID_LOGICAL_TIME")
    required = (
        packet.namespace,
        packet.state_profile,
        packet.native_state_ref,
        packet.parent_state_root,
        packet.evidence_root,
        packet.snapshot_id,
        packet.canonical_version,
        packet.rule_version,
        packet.topology_coordinate_ref,
        packet.event_hash_ref,
    )
    if not all(isinstance(value, str) and value for value in required):
        return ValidationDecision("BLOCK", "BLOCK_INVALID_8D_BINDING")
    if any(facts.life_harm or facts.other_rights_harm for facts in packet.boundary_facts):
        return ValidationDecision("BLOCK", "BLOCK_ABSOLUTE_REDLINE")
    return ValidationDecision("PASS", "VALID_8D_CANDIDATE_STRUCTURE")


def validate_native_adi(
    profile_definition: str,
    evidence_status: Mapping[str, str],
) -> ValidationDecision:
    lowered = profile_definition.casefold()
    if any(token in lowered for token in FORBIDDEN_NATIVE_PROXIES):
        return ValidationDecision("BLOCK", "BLOCK_NATIVE_ADI_DEFINITION_DRIFT")
    accepted = {"CONFIRMED", "CURRENT_FOUNDER_CANONICAL", "DERIVED_DETERMINISTICALLY"}
    unresolved = sorted(rule for rule, status in evidence_status.items() if status not in accepted)
    if unresolved:
        return ValidationDecision(
            "HOLD",
            "HOLD_NATIVE_RULE_EVIDENCE_MISSING:" + ",".join(unresolved),
        )
    return ValidationDecision("PASS", "NATIVE_RULE_EVIDENCE_CONFIRMED")


def validate_ethics(
    ethics_vector: Sequence[int],
    *,
    harms_life: bool = False,
    harms_others_rights: bool = False,
) -> ValidationDecision:
    if harms_life or harms_others_rights:
        return ValidationDecision("BLOCK", "BLOCK_ABSOLUTE_REDLINE")
    if not ethics_vector or any(value < 2 for value in ethics_vector):
        return ValidationDecision("BLOCK", "BLOCK_ETHICS_VECTOR_BELOW_2")
    return ValidationDecision("PASS", "ETHICS_GATE_PASS")


def evidence_closed_f(
    origin: StatePacket8D,
    packet: StatePacket8D,
    transition_rules: Iterable[NativeTransitionRule],
    *,
    authoritative_parent_state_root: str,
) -> ValidationDecision:
    structural = validate_8d(packet)
    if structural.state != "PASS":
        return structural
    boundaries = positive_negative_boundaries(packet)
    if any(value < 0 for value in boundaries):
        return ValidationDecision("HOLD", "HOLD_NEGATIVE_BOUNDARY")
    if any(value != 1 for value in boundaries):
        return ValidationDecision("HOLD", "HOLD_POSITIVE_BOUNDARY_UNRESOLVED")
    if packet.parent_state_root != authoritative_parent_state_root:
        return ValidationDecision("HOLD", "HOLD_PARENT_STATE_ROOT_MISMATCH")
    if packet.state_root != candidate_state_root_f(packet):
        return ValidationDecision("HOLD", "HOLD_CANDIDATE_STATE_ROOT_NOT_REPRODUCIBLE")
    if packet.previous_logical_time is not None and packet.previous_logical_time >= packet.logical_time:
        return ValidationDecision("HOLD", "HOLD_CAUSAL_TIME_TOPOLOGY_DIVERGENCE")
    metric = metric_signature_f(packet).as_tuple()
    if packet.claimed_metric_signature is not None and tuple(packet.claimed_metric_signature) != metric:
        return ValidationDecision("HOLD", "HOLD_METRIC_SIGNATURE_DIVERGENCE")
    if set(packet.expected_evidence_digests) - set(packet.evidence_digests):
        return ValidationDecision("HOLD", "HOLD_REQUIRED_EVIDENCE_MISSING")
    if any(
        packet.evidence_digests.get(ref) != digest
        for ref, digest in packet.expected_evidence_digests.items()
    ):
        return ValidationDecision("HOLD", "HOLD_EVIDENCE_DIGEST_MISMATCH")
    try:
        path = resolve_canonical_path(origin, packet, transition_rules)
    except BreakpointReachabilityDenied as exc:
        return ValidationDecision("DENY", exc.code)
    except TransitionRuleHold as exc:
        return ValidationDecision("HOLD", exc.code)
    required_refs = {ref for rule in path.rules for ref in rule.required_evidence_refs}
    if not required_refs.issubset(packet.evidence_digests):
        return ValidationDecision("HOLD", "HOLD_REQUIRED_EVIDENCE_MISSING")
    return ValidationDecision("PASS", "EVIDENCE_CLOSED")


def total_field_candidate_decision(
    *,
    shell: int,
    candidate_state_root: str,
    total_field_state_root: str,
    examined: int = 0,
    query_budget: int | None = None,
) -> NativeLookupReceipt:
    if query_budget is not None and examined > query_budget:
        return NativeLookupReceipt(
            "HOLD_QUERY_BUDGET_EXCEEDED",
            None,
            None,
            total_field_state_root,
            {"partial_pass": False, "examined": examined, "budget": query_budget},
        )
    if candidate_state_root != total_field_state_root:
        return NativeLookupReceipt(
            "HOLD_LOCAL_CANDIDATE_ROOT_MISMATCH",
            shell,
            candidate_state_root,
            total_field_state_root,
        )
    if shell != 0:
        return NativeLookupReceipt(
            "RECONSTRUCTION_CANDIDATE_ONLY",
            shell,
            candidate_state_root,
            total_field_state_root,
            {"authoritative": False},
        )
    return NativeLookupReceipt(
        "AUTHORITATIVE_EXACT_STATE",
        0,
        candidate_state_root,
        total_field_state_root,
        {"authoritative": True},
    )
