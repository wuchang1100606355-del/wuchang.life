"""One XiaoJ / one natural-person identity packet / seven scene prefixes.

CANDIDATE-ONLY preflight evaluator. It NEVER performs a read, write, tool
invocation, signature issuance, or permission mutation.

The "trusted_verifier" callback is an interface dependency and not
implemented by this file. Only the existing Total Field D8 may provide an
authenticated decision in production; LLM text and UI-supplied booleans
never qualify as verifier output.
"""
from __future__ import annotations
import hashlib
import json
import re
from collections.abc import Callable, Mapping
from typing import Any

IDENTITY_PACKET_RE = re.compile(r"^identity_packet_ref:sha256:[0-9a-f]{64}$")
IMMUTABLE_PREFIX_RE = re.compile(r"^identity_prefix_ref:sha256:[0-9a-f]{64}$")
ACTION_RECEIPT_RE = re.compile(r"^d8_action_receipt_ref:sha256:[0-9a-f]{64}$")
SCENE_KEYS = frozenset(
    {"work", "business", "developer", "housing", "association", "life", "my-community"}
)
ALLOWED_OPERATIONS = frozenset({"read", "write"})
ALLOWED_RISKS = frozenset({"low", "medium", "high"})

def _result(state: str, reason: str, *, eligible: bool = False) -> dict[str, Any]:
    return {
        "state": state, "reason": reason,
        "candidate_only": True, "eligible_candidate": eligible,
        "execution_allowed": False, "read_performed": False,
        "write_performed": False, "identity_root_modified": False,
        "privilege_granted": False,
    }

def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",",":"),
        allow_nan=False,
    ).encode()).hexdigest()

def _int_field(value: Any) -> bool:
    return isinstance(value,int) and not isinstance(value,bool) and value>=0

def preview_scene_decision(
    envelope: Mapping[str,Any],
    *,
    scene_key: str,
    operation: str,
    capability_ref: str,
    data_scope_ref: str,
    now_epoch: int,
    requested_records: int = 0,
    requested_cost_units: int = 0,
    risk: str = "low",
    trusted_verifier: Callable[[Mapping[str,Any],str,str],Mapping[str,Any]] | None = None,
) -> dict[str,Any]:
    """Return only a bounded preflight result for a D8-verified scene.

    Without the real Total Field verifier, this ALWAYS returns HOLD.
    The same immutable identity must be used for every prefix.
    """
    if not isinstance(envelope, Mapping):
        return _result("HOLD_PACKET_REQUIRED", "single_identity_envelope_missing")
    identity = envelope.get("identity_packet_ref")
    prefix = envelope.get("immutable_identity_prefix_ref")
    if not isinstance(identity,str) or not IDENTITY_PACKET_RE.fullmatch(identity):
        return _result("HOLD_IDENTITY_REF_INVALID", "canonical_ref_required")
    if not isinstance(prefix,str) or not IMMUTABLE_PREFIX_RE.fullmatch(prefix):
        return _result("HOLD_IMMUTABLE_PREFIX_INVALID", "immutable_prefix_ref_required")
    if envelope.get("one_natural_person_one_identity_packet") is not True:
        return _result("HOLD_MULTIPLE_IDENTITY_ROOT", "one_natural_person_required")
    if envelope.get("revocation_state") != "CLEAR":
        return _result("HOLD_IDENTITY_REVOKED", "revocation_or_unknown")
    if scene_key not in SCENE_KEYS or operation not in ALLOWED_OPERATIONS:
        return _result("HOLD_SCENE_OR_OPERATION_UNKNOWN", "unrecognized_scene_or_operation")
    if risk not in ALLOWED_RISKS or not all(_int_field(v) for v in (now_epoch,requested_records,requested_cost_units)):
        return _result("HOLD_REQUEST_BOUND_INVALID", "risk_or_quantity_invalid")
    expiry = envelope.get("expires_at_epoch")
    if not _int_field(expiry) or now_epoch >= expiry:
        return _result("HOLD_IDENTITY_ENVELOPE_EXPIRED", "expiry_required")
    if trusted_verifier is None:
        return _result("HOLD_TOTAL_FIELD_VERIFIER_UNBOUND", "no_trusted_D8_authority")
    scene_grants = envelope.get("scene_prefix_grants")
    if not isinstance(scene_grants, Mapping):
        return _result("HOLD_SCENE_GRANTS_REQUIRED", "no_authenticated_capability_scope")
    grant = scene_grants.get(scene_key)
    if not isinstance(grant, Mapping):
        return _result("HOLD_SCENE_NOT_GRANTED", "scene_selection_does_not_grant")
    if set(grant) != {"allowed_skill_refs","read_scope_refs","write_scope_refs","limits","prefix_ref"}:
        return _result("HOLD_SCENE_GRANT_SHAPE", "unexpected_authority_or_shape")
    # Semantic isolation: only the selected prefix contributes its scopes.
    if grant["prefix_ref"] != "xiaoj.scene."+scene_key:
        return _result("HOLD_SCENE_PREFIX_MISMATCH", "cross_scene_prefix_forbidden")
    allowed_skills = grant["allowed_skill_refs"]
    requested_scopes = grant["read_scope_refs" if operation=="read" else "write_scope_refs"]
    if not isinstance(allowed_skills,list) or not isinstance(requested_scopes,list):
        return _result("HOLD_SCOPE_LIST_INVALID", "scope_not_a_list")
    if capability_ref not in allowed_skills or data_scope_ref not in requested_scopes:
        return _result("HOLD_CAPABILITY_OR_SCOPE_DENIED", "not_in_current_scene_scope")
    limit = grant["limits"]
    if not isinstance(limit, Mapping) or set(limit) != {
        "max_records_per_action","max_cost_units_per_action","quota_remaining","risk_ceiling"}:
        return _result("HOLD_LIMITS_UNVERIFIED", "bounded_limit_contract_required")
    if not all(_int_field(limit[k]) for k in (
        "max_records_per_action","max_cost_units_per_action","quota_remaining"
    )):
        return _result("HOLD_LIMIT_VALUES_INVALID", "nonnegative_int_limit_required")
    if limit["risk_ceiling"] not in ALLOWED_RISKS:
        return _result("HOLD_RISK_POLICY_INVALID", "risk_ceiling_required")
    if requested_records > limit["max_records_per_action"] or requested_cost_units > limit["max_cost_units_per_action"] or requested_cost_units > limit["quota_remaining"]:
        return _result("HOLD_MARGINAL_LIMIT_EXCEEDED", "records_cost_or_remaining_quota")
    if ["low","medium","high"].index(risk) > ["low","medium","high"].index(limit["risk_ceiling"]):
        return _result("HOLD_RISK_LIMIT_EXCEEDED", "risk_over_current_policy")
    # A trusted callback must verify the original signed envelope, time, actor,
    # action, registry, dependency states and D8 receipt. Matching refs/hashes
    # here alone do not establish that verifier's trustworthiness.
    try:
        verdict=trusted_verifier(envelope,scene_key,operation)
    except Exception:
        return _result("HOLD_TOTAL_FIELD_VERIFIER_ERROR", "trusted_verifier_not_available")
    if not isinstance(verdict,Mapping) or verdict.get("state")!="PASS_VERIFIED_TOTAL_FIELD_SCENE_PREVIEW":
        return _result("HOLD_D8_ACTION_AUTHORITY", "unverified_or_rejected_action")
    if verdict.get("identity_packet_ref") != identity or verdict.get("immutable_identity_prefix_ref") != prefix:
        return _result("HOLD_D8_IDENTITY_BINDING_MISMATCH", "verified_identity_changed")
    if verdict.get("scene_prefix_ref") != grant["prefix_ref"] or verdict.get("scope_sha256") != _canonical_sha256(grant):
        return _result("HOLD_D8_SCOPE_BINDING_MISMATCH", "verified_scope_changed")
    receipt=verdict.get("action_receipt_ref")
    if not isinstance(receipt,str) or ACTION_RECEIPT_RE.fullmatch(receipt) is None:
        return _result("HOLD_D8_RECEIPT_REQUIRED", "signed_action_receipt_not_available")
    # Still a presentation/preflight, not a legal effect or tool execution.
    return _result("CANDIDATE_SCENE_ELIGIBLE", "preflight_only_execute_through_governed_backend", eligible=True)
