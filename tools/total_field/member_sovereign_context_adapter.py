"""T-011A member-sovereign context adapter candidate.

This adapter reuses the existing member-sovereign identity/session gates and the
existing dynamic-context validator. It creates no identity root, seat, consent,
D8, GST, Total Field, runtime effect, or persistence authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from tools.total_field_dynamic_context_pull import validate_model_visible_context


SCHEMA_VERSION = "w7tp-member-sovereign-context/1.0-candidate"
MODEL_INTERFACE_REF = "interface:member-sovereign-context:v1"
DYNAMIC_CONTEXT_INTERFACE_REF = "interface:total-field-dynamic-context-pull:v1"
CONTRACT_SCHEMA_REF = "schema:w7tp-member-sovereign-context:v1"
OPAQUE_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/+:-]{0,511}$")
P3_PASS_REASON = "PASS_P3_SESSION_DUAL_RECEIPT_9107_GATE_CANDIDATE"
P3_AUTHORITY = {
    "member_consent_authority": "member",
    "safety_and_landing_authority": "total_field_verifier",
    "process_authority": "odoo",
    "candidate_authority": "none",
}
FORBIDDEN_CAPABILITY_CLASSES = (
    "MEMBER_CONSENT_PROXY",
    "MEMBER_REFUSAL_PROXY",
    "PLAINTEXT_DISCLOSURE",
    "PAYMENT_EXECUTION",
    "LEGAL_OR_ORGANIZATION_EFFECT",
    "ROLE_ELEVATION",
    "D8_SELF_PROMOTION",
    "TOTAL_FIELD_REPLACEMENT",
    "AUTOMATIC_RECONSTRUCTION_TO_PLAINTEXT",
)


class MemberSovereignContextHold(RuntimeError):
    """Fail-closed T-011A candidate outcome."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise MemberSovereignContextHold(code)


def _ref(value: Any, code: str) -> str:
    _require(isinstance(value, str) and OPAQUE_REF_RE.fullmatch(value) is not None, code)
    return str(value)


def _refs(value: Any, code: str, *, allow_empty: bool = False) -> list[str]:
    _require(isinstance(value, Sequence) and not isinstance(value, (str, bytes)), code)
    result = [_ref(item, code) for item in value]
    _require(len(result) == len(set(result)), code)
    _require(allow_empty or bool(result), code)
    return sorted(result)


def _role_seat_payload(request: Mapping[str, Any]) -> Mapping[str, Any]:
    try:
        payload = request["p1_identity_candidate"]["derived_packets_evidence"]["payload"]
        role_seat = payload["role_seat"]["payload"]
    except (KeyError, TypeError):
        raise MemberSovereignContextHold("HOLD_MEMBER_ROLE_SEAT_EVIDENCE_REQUIRED")
    _require(isinstance(role_seat, Mapping), "HOLD_MEMBER_ROLE_SEAT_EVIDENCE_REQUIRED")
    return role_seat


def _validate_verified_gate(
    request: Mapping[str, Any],
    gate_result: Mapping[str, Any],
) -> Mapping[str, Any]:
    _require(gate_result.get("state") == "PASS", "HOLD_MEMBER_SESSION_GATE_PASS_REQUIRED")
    _require(gate_result.get("reason_code") == P3_PASS_REASON, "HOLD_MEMBER_SESSION_GATE_PASS_REQUIRED")
    _require(gate_result.get("generic_gateway_ready") is True, "HOLD_MEMBER_SESSION_GATE_NOT_READY")
    _require(gate_result.get("runtime_released") is False, "HOLD_MEMBER_GATE_RUNTIME_RELEASE_FORBIDDEN")
    _require(gate_result.get("action_executed") is False, "HOLD_MEMBER_GATE_ACTION_EFFECT_FORBIDDEN")
    for key, expected in P3_AUTHORITY.items():
        _require(gate_result.get(key) == expected, "HOLD_MEMBER_GATE_AUTHORITY_MODEL_DRIFT")

    material = gate_result.get("gate_material")
    _require(isinstance(material, Mapping), "HOLD_MEMBER_GATE_MATERIAL_REQUIRED")
    expected_ref = "member_action_gate_ref:sha256:" + canonical_sha256(material)
    _require(gate_result.get("gate_ref") == expected_ref, "HOLD_MEMBER_GATE_HASH_BINDING_MISMATCH")

    try:
        session = request["session"]
        scene = request["scene"]
        action = request["action"]
        member_receipt = request["member_consent_receipt"]
        total_field_receipt = request["total_field_receipt"]
    except (KeyError, TypeError):
        raise MemberSovereignContextHold("HOLD_MEMBER_ACTION_REQUEST_BINDING_REQUIRED")

    bindings = {
        "identity_root_ref": request.get("identity_root_ref"),
        "root_generation": request.get("root_generation"),
        "revocation_epoch": request.get("revocation_epoch"),
        "session_ref": session.get("session_ref"),
        "scene_ref": scene.get("scene_ref"),
        "action_hash": action.get("action_hash"),
        "scope_refs": action.get("scope_refs"),
        "effect_class": action.get("effect_class"),
        "member_consent_receipt_ref": member_receipt.get("receipt_ref"),
        "total_field_receipt_ref": total_field_receipt.get("receipt_ref"),
    }
    for key, value in bindings.items():
        _require(material.get(key) == value, "HOLD_MEMBER_GATE_REQUEST_BINDING_MISMATCH")
    return material


def build_member_sovereign_context_candidate(
    *,
    member_action_request: Mapping[str, Any],
    verified_gate_result: Mapping[str, Any],
    organization_request_ref: str,
    audit_ref: str,
    allowed_capability_refs: Sequence[str],
    authority_basis_mode: str = "MEMBER_CONSENT",
    legal_basis_ref: str | None = None,
    legal_basis_verification_ref: str | None = None,
    risk_state: str = "PASS",
) -> dict[str, Any]:
    """Build a reference-only member context without creating new authority."""

    _require(isinstance(member_action_request, Mapping), "HOLD_MEMBER_ACTION_REQUEST_REQUIRED")
    _require(isinstance(verified_gate_result, Mapping), "HOLD_MEMBER_GATE_RESULT_REQUIRED")
    gate_material = _validate_verified_gate(member_action_request, verified_gate_result)

    # T-011A models the separate legal-basis path but does not invent a verifier.
    if authority_basis_mode == "LEGAL_BASIS":
        _require(
            legal_basis_ref is not None and legal_basis_verification_ref is not None,
            "HOLD_LEGAL_BASIS_VERIFIER_NOT_BOUND",
        )
        raise MemberSovereignContextHold("HOLD_LEGAL_BASIS_VERIFIER_NOT_BOUND")
    _require(authority_basis_mode == "MEMBER_CONSENT", "HOLD_AUTHORITY_BASIS_MODE_UNSUPPORTED")

    role_seat = _role_seat_payload(member_action_request)
    natural_person_ref = _ref(member_action_request.get("member_ref"), "HOLD_NATURAL_PERSON_REF_REQUIRED")
    identity_root_ref = _ref(member_action_request.get("identity_root_ref"), "HOLD_IDENTITY_ROOT_REF_REQUIRED")
    organization_ref = _ref(role_seat.get("organization_ref"), "HOLD_ORGANIZATION_REF_REQUIRED")
    seat_ref = _ref(role_seat.get("seat_ref"), "HOLD_SEAT_REF_REQUIRED")
    role_ref = _ref(role_seat.get("role_ref"), "HOLD_ROLE_REF_REQUIRED")
    org_request_ref = _ref(organization_request_ref, "HOLD_ORGANIZATION_REQUEST_REF_REQUIRED")
    audit = _ref(audit_ref, "HOLD_AUDIT_REF_REQUIRED")
    capabilities = _refs(
        allowed_capability_refs,
        "HOLD_ALLOWED_CAPABILITY_REFS_INVALID",
        allow_empty=True,
    )
    _require(
        natural_person_ref not in {seat_ref, organization_ref}
        and identity_root_ref not in {seat_ref, organization_ref},
        "HOLD_IDENTITY_SEAT_OR_ORGANIZATION_COLLAPSE",
    )

    session = member_action_request["session"]
    scene = member_action_request["scene"]
    action = member_action_request["action"]
    member_receipt = member_action_request["member_consent_receipt"]
    total_field_receipt = member_action_request["total_field_receipt"]

    scope_refs = _refs(action.get("scope_refs"), "HOLD_MEMBER_SCOPE_REFS_INVALID")
    _require(
        scope_refs == sorted(session.get("scope_refs", []))
        == sorted(scene.get("scope_refs", [])),
        "HOLD_MEMBER_CONTEXT_SCOPE_DRIFT",
    )
    _require(member_receipt.get("authority") == "member", "HOLD_MEMBER_AUTHORIZATION_AUTHORITY_INVALID")
    _require(member_receipt.get("receipt_state") == "CONSENT", "HOLD_MEMBER_AUTHORIZATION_REQUIRED")
    _require(
        total_field_receipt.get("authority") == "total_field_verifier"
        and total_field_receipt.get("receipt_state") == "PASS",
        "HOLD_TOTAL_FIELD_SAFETY_RECEIPT_REQUIRED",
    )

    member_coordinate = {
        "natural_person_ref": natural_person_ref,
        "identity_root_ref": identity_root_ref,
        "organization_ref": organization_ref,
        "seat_ref": seat_ref,
        "role_ref": role_ref,
        "session_ref": _ref(session.get("session_ref"), "HOLD_SESSION_REF_REQUIRED"),
        "scene_ref": _ref(scene.get("scene_ref"), "HOLD_SCENE_REF_REQUIRED"),
    }
    request_authorization = {
        "organization_request_ref": org_request_ref,
        "organization_request_is_member_authorization": False,
        "member_authorization_ref": _ref(
            member_receipt.get("receipt_ref"),
            "HOLD_MEMBER_AUTHORIZATION_REF_REQUIRED",
        ),
        "member_authorization_state": "CONSENT_VERIFIED",
        "member_authorization_authority": "member",
        "legal_basis_ref": None,
        "legal_basis_verification_ref": None,
        "authority_basis_mode": "MEMBER_CONSENT",
    }
    task_scope = {
        "purpose_ref": _ref(action.get("purpose_ref"), "HOLD_PURPOSE_REF_REQUIRED"),
        "scope_refs": scope_refs,
        "effect_class": str(action.get("effect_class")),
        "issued_at_epoch": int(session.get("issued_at_epoch")),
        "expires_at_epoch": int(session.get("expires_at_epoch")),
    }
    data_boundary = {
        "model_visible_member_data": "OPAQUE_REFERENCES_ONLY",
        "plaintext_policy": "LOCAL_ONLY_NEVER_MODEL_VISIBLE",
        "reconstruction_policy": "NO_AUTOMATIC_PLAINTEXT_RECONSTRUCTION",
        "odoo_role": "PROCESS_AND_MASKED_PROJECTION_NOT_SOVEREIGN_ROOT",
        "dynamic_context_persistence": "REFERENCES_ONLY",
    }
    authority_route = {
        "member_gate_ref": _ref(verified_gate_result.get("gate_ref"), "HOLD_MEMBER_GATE_REF_REQUIRED"),
        "member_authorization_ref": request_authorization["member_authorization_ref"],
        "total_field_receipt_ref": _ref(
            total_field_receipt.get("receipt_ref"),
            "HOLD_TOTAL_FIELD_RECEIPT_REF_REQUIRED",
        ),
        "nonce_consumption_evidence_ref": _ref(
            gate_material.get("nonce_consumption_evidence_ref"),
            "HOLD_NONCE_EVIDENCE_REF_REQUIRED",
        ),
        "candidate_authority": "NONE",
        "provider_authority": "NONE",
        "model_authority": "NONE",
        "formal_effect_route": "EXISTING_TAIJI01_TOTAL_FIELD",
    }

    contract: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "state": "PASS_MEMBER_SOVEREIGN_CONTEXT_CANDIDATE",
        "candidate_only": True,
        "runtime_effect": False,
        "second_identity_root_created": False,
        "second_8d_created": False,
        "second_d8_created": False,
        "second_gst_created": False,
        "second_total_field_created": False,
        "member_coordinate": member_coordinate,
        "request_authorization_separation": request_authorization,
        "task_scope": task_scope,
        "data_boundary": data_boundary,
        "capability_boundary": {
            "allowed_capability_refs": capabilities,
            "forbidden_capability_classes": list(FORBIDDEN_CAPABILITY_CLASSES),
        },
        "risk_state": str(risk_state),
        "audit_ref": audit,
        "authority_route": authority_route,
        "context_sha256": "",
    }
    contract["context_sha256"] = canonical_sha256(
        {key: value for key, value in contract.items() if key != "context_sha256"}
    )
    return contract


def build_member_model_visible_context(
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Project the T-011A contract into the existing Dynamic Context shape."""

    _require(
        isinstance(contract, Mapping)
        and contract.get("state") == "PASS_MEMBER_SOVEREIGN_CONTEXT_CANDIDATE"
        and contract.get("candidate_only") is True
        and contract.get("runtime_effect") is False,
        "HOLD_MEMBER_CONTEXT_CANDIDATE_REQUIRED",
    )
    copied = copy.deepcopy(dict(contract))
    supplied_hash = copied.pop("context_sha256", None)
    _require(
        supplied_hash == canonical_sha256(copied),
        "HOLD_MEMBER_CONTEXT_HASH_MISMATCH",
    )

    authority_route = contract["authority_route"]
    capability_boundary = contract["capability_boundary"]
    evidence_refs = sorted(
        {
            _ref(contract["audit_ref"], "HOLD_AUDIT_REF_REQUIRED"),
            _ref(authority_route["member_gate_ref"], "HOLD_MEMBER_GATE_REF_REQUIRED"),
            _ref(
                authority_route["member_authorization_ref"],
                "HOLD_MEMBER_AUTHORIZATION_REF_REQUIRED",
            ),
            _ref(
                authority_route["total_field_receipt_ref"],
                "HOLD_TOTAL_FIELD_RECEIPT_REF_REQUIRED",
            ),
            _ref(
                authority_route["nonce_consumption_evidence_ref"],
                "HOLD_NONCE_EVIDENCE_REF_REQUIRED",
            ),
        }
    )
    capability_refs = _refs(
        capability_boundary["allowed_capability_refs"],
        "HOLD_ALLOWED_CAPABILITY_REFS_INVALID",
        allow_empty=True,
    )
    projection = {
        "member_sovereign_context": {
            "member_coordinate": copy.deepcopy(contract["member_coordinate"]),
            "request_authorization_separation": copy.deepcopy(
                contract["request_authorization_separation"]
            ),
            "task_scope": copy.deepcopy(contract["task_scope"]),
            "data_boundary": copy.deepcopy(contract["data_boundary"]),
            "capability_boundary": copy.deepcopy(contract["capability_boundary"]),
            "risk_state": contract["risk_state"],
            "authority_route": copy.deepcopy(contract["authority_route"]),
            "source_context_sha256": contract["context_sha256"],
        }
    }
    context: dict[str, Any] = {
        "context_ref": "memberctx:sha256:" + canonical_sha256(projection),
        "state_projection": projection,
        "evidence_refs": evidence_refs,
        "capability_refs": capability_refs,
        "acceptance_conditions": [
            "condition:member-context:opaque-references-only",
            "condition:member-context:no-proxy-consent",
            "condition:member-context:no-runtime-effect",
            "condition:member-context:existing-total-field-only",
        ],
        "schema_refs": [CONTRACT_SCHEMA_REF],
        "interface_refs": [
            MODEL_INTERFACE_REF,
            DYNAMIC_CONTEXT_INTERFACE_REF,
        ],
        "non_core_rule_capsule_refs": [],
    }
    return validate_model_visible_context(context)


__all__ = [
    "MemberSovereignContextHold",
    "SCHEMA_VERSION",
    "build_member_model_visible_context",
    "build_member_sovereign_context_candidate",
    "canonical_sha256",
]
