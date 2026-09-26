#!/usr/bin/env python3
"""T-019 XiaoJ sovereign-member product entry adapter.

This module composes existing member-session, member-sovereign-context, and
member-browser contracts. It creates no second identity root, consent system,
8D/D8/Total Field, database write path, or runtime authority.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from tools.total_field.member_sovereign_context_adapter import (
    MemberSovereignContextHold,
    build_member_model_visible_context,
    build_member_sovereign_context_candidate,
    canonical_sha256,
)
from tools.total_field.xiaoj_member_bound_session_candidate import (
    DurableNonceConsumer,
    evaluate_member_action_session,
)
from tools.total_field.xiaoj_human_need_router import route_human_need

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/field/w7tp_xiaoj_member_product_entry_v1.schema.json"
SCHEMA_VERSION = "w7tp.xiaoj-member-product-entry.v1"
OPAQUE_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/+:-]{0,511}$")

ODOO_REQUIRED_KEYS = frozenset(
    {
        "auth_state",
        "member_ref",
        "odoo_identity_ref",
        "odoo_role_ref",
        "odoo_function_scope_ref",
        "odoo_permission_bucket_ref",
        "member_preference_ref",
        "service_style_ref",
        "quota_bucket_ref",
        "benefit_ref",
    }
)
ODOO_OPTIONAL_KEYS = frozenset({"behavior_info_ref", "cloud_compute_ref"})
FORBIDDEN_KEY_TOKENS = (
    "name",
    "phone",
    "email",
    "address",
    "identity_number",
    "id_number",
    "password",
    "token",
    "secret",
    "credential",
    "cookie",
    "plaintext",
    "raw_audio",
)


def _base(state: str, reason_code: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "state": state,
        "reason_code": reason_code,
        "candidate_only": True,
        "runtime_effect": False,
        "execution_allowed": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "member_plaintext_read": False,
        "secret_read": False,
        "second_identity_root_created": False,
        "second_8d_created": False,
        "second_d8_created": False,
        "second_total_field_created": False,
    }


def _hold(code: str) -> dict[str, Any]:
    result = _base("HOLD", code)
    result["requires_total_field_verify"] = True
    return result


def _safe_ref(value: Any) -> bool:
    return isinstance(value, str) and OPAQUE_REF_RE.fullmatch(value) is not None


def _browser_actor_ref(sovereign_member_ref: str) -> str:
    """Derive a browser-local actor ref without changing sovereign identity."""
    digest = canonical_sha256({"sovereign_member_ref": sovereign_member_ref})
    return "actor_ref:member:" + digest


def _validate_odoo_projection(
    projection: Mapping[str, Any],
    member_action_request: Mapping[str, Any],
) -> str | None:
    if not isinstance(projection, Mapping):
        return "HOLD_ODOO_MEMBER_PROJECTION_REQUIRED"
    keys = set(projection)
    if not ODOO_REQUIRED_KEYS.issubset(keys):
        return "HOLD_ODOO_MEMBER_PROJECTION_REQUIRED_FIELD_MISSING"
    if keys - (ODOO_REQUIRED_KEYS | ODOO_OPTIONAL_KEYS):
        return "HOLD_ODOO_MEMBER_PROJECTION_KEYS_INVALID"
    for key in keys:
        lower = key.lower()
        if any(token in lower for token in FORBIDDEN_KEY_TOKENS):
            return "HOLD_ODOO_MEMBER_PLAINTEXT_OR_SECRET_FIELD_FORBIDDEN"
    if projection.get("auth_state") != "AUTHENTICATED_LOCAL_MEMBER":
        return "HOLD_ODOO_LOCAL_MEMBER_AUTH_REQUIRED"
    if projection.get("member_ref") != member_action_request.get("member_ref"):
        return "HOLD_ODOO_MEMBER_REF_MISMATCH"
    for key, value in projection.items():
        if key == "auth_state":
            continue
        if value == "" and key in ODOO_OPTIONAL_KEYS:
            continue
        if not _safe_ref(value):
            return "HOLD_ODOO_MEMBER_REF_INVALID"
    return None


def build_xiaoj_member_product_entry_candidate(
    *,
    odoo_member_projection: Mapping[str, Any],
    member_action_request: Mapping[str, Any],
    current_epoch: int,
    nonce_consumer: DurableNonceConsumer | None,
    organization_request_ref: str,
    audit_ref: str,
    allowed_capability_refs: Sequence[str],
    p1_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    active_seat_leases: Sequence[Mapping[str, Any]] = (),
    active_role_refs: Sequence[str] = (),
    human_intent: str = "",
) -> dict[str, Any]:
    """Compose the existing member sovereignty chain into one product entry."""

    reason = _validate_odoo_projection(
        odoo_member_projection,
        member_action_request,
    )
    if reason is not None:
        return _hold(reason)

    gate = evaluate_member_action_session(
        member_action_request,
        current_epoch=current_epoch,
        nonce_consumer=nonce_consumer,
        p1_verifier=p1_verifier,
        active_seat_leases=active_seat_leases,
    )
    if gate.get("state") != "PASS":
        result = _hold(str(gate.get("reason_code") or "HOLD_MEMBER_SESSION_GATE_REQUIRED"))
        result["member_gate_state"] = gate.get("state", "HOLD")
        return result

    try:
        member_contract = build_member_sovereign_context_candidate(
            member_action_request=member_action_request,
            verified_gate_result=gate,
            organization_request_ref=organization_request_ref,
            audit_ref=audit_ref,
            allowed_capability_refs=allowed_capability_refs,
        )
        model_context = build_member_model_visible_context(member_contract)
    except MemberSovereignContextHold as exc:
        return _hold(exc.code)

    projection = copy.deepcopy(dict(odoo_member_projection))
    sovereign_member_ref = str(member_action_request["member_ref"])
    effective_role_refs = list(active_role_refs) or [str(projection["odoo_role_ref"])]
    human_need_route = route_human_need(
        active_role_refs=effective_role_refs,
        intent=human_intent,
    )
    browser_binding = {
        "member_ref": _browser_actor_ref(sovereign_member_ref),
        "sovereign_member_ref": sovereign_member_ref,
        "device_ref": member_action_request["session"]["device_ref"],
        "safe_context_ref": model_context["context_ref"],
        "member_preference_ref": projection["member_preference_ref"],
        "service_style_ref": projection["service_style_ref"],
        "behavior_info_ref": projection.get("behavior_info_ref", ""),
        "cloud_compute_ref": projection.get(
            "cloud_compute_ref", "cloud_compute_ref:local_member_candidate"
        ),
        "benefit_ref": projection["benefit_ref"],
        "quota_ref": projection["quota_bucket_ref"],
        "odoo_identity_ref": projection["odoo_identity_ref"],
        "odoo_role_ref": projection["odoo_role_ref"],
        "odoo_function_scope_ref": projection["odoo_function_scope_ref"],
        "odoo_permission_bucket_ref": projection["odoo_permission_bucket_ref"],
        "requires_total_field_verify": True,
        "submit_forbidden": True,
    }

    result = _base(
        "PASS_XIAOJ_MEMBER_PRODUCT_ENTRY_CANDIDATE",
        "PASS_T019_MEMBER_PRODUCT_ENTRY",
    )
    result.update(
        {
            "requires_total_field_verify": True,
            "odoo_role": "PROCESS_AND_MASKED_PROJECTION_NOT_SOVEREIGN_ROOT",
            "member_consent_authority": "member",
            "safety_and_landing_authority": "total_field_verifier",
            "candidate_authority": "none",
            "optional_channel_bindings": {
                "google_required_for_core_member_entry": False,
                "line_required_for_core_member_entry": False,
            },
            "odoo_projection_sha256": canonical_sha256(projection),
            "member_gate_ref": gate["gate_ref"],
            "member_context_ref": model_context["context_ref"],
            "member_context_sha256": member_contract["context_sha256"],
            "member_model_visible_context": model_context,
            "human_need_route": human_need_route,
            "open_source_product_mode": {
                "mode": "OPEN_SOURCE_LOCAL_FIRST",
                "single_node_core_supported": True,
                "paid_cloud_required": False,
                "enterprise_sso_required": False,
                "kubernetes_required": False,
                "google_required": False,
                "line_required": False,
                "cloud_llm_required": False,
            },
            "xiaoj_member_browser_binding": browser_binding,
            "next_route": "HUMAN_NEED_ROUTE_THEN_EXISTING_TAIJI01_TOTAL_FIELD_THEN_XIAOJ_MEMBER_BROWSER_GATEWAY",
        }
    )
    material = copy.deepcopy(result)
    result["entry_sha256"] = canonical_sha256(material)

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(result))
    if errors:
        return _hold("HOLD_T019_ENTRY_SCHEMA_INVALID")
    return result


__all__ = [
    "SCHEMA_VERSION",
    "build_xiaoj_member_product_entry_candidate",
]
