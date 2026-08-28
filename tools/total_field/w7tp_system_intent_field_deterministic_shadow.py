"""Deterministic, no-effect L03 shadow controller for the governed intent field.

The module performs no file, network, database, service, clock, environment, or
model access.  Callers provide a reference-only request, an in-memory scoped
state mapping, and a validated rule bundle.  Unknown intent codes are held
before the scoped state mapping is accessed.
"""

from __future__ import annotations

import hashlib
import json


CONTROLLER_ID = "W7TP_SYSTEM_INTENT_FIELD_DETERMINISTIC_SHADOW_V1"
TRACE_VERSION = "W7TP-SYSTEM-INTENT-FIELD-DECISION-TRACE/1.0"
REQUEST_VERSION = "W7TP-SYSTEM-INTENT-FIELD-SHADOW-REQUEST/1.0"
DELTA_VERSION = "W7TP-SYSTEM-INTENT-MINIMUM-DELTA/1.0"

_REQUEST_KEYS = frozenset(
    {
        "request_version",
        "attempt_ref",
        "idempotency_ref",
        "nonce_ref",
        "intent_code",
        "intent_root_ref",
        "scope_ref",
        "expected_state_version",
        "expected_state_sha256",
        "requested_effect_ref",
        "human_confirmation_state",
        "declared_unknown_slots",
        "raw_input_included",
        "member_plaintext_included",
        "secret_material_included",
    }
)

_STATE_KEYS = frozenset(
    {
        "scope_ref",
        "state_root_ref",
        "state_version",
        "state_sha256",
        "verified",
        "canonical_lock_state",
        "coordinate_bound",
        "evidence_complete",
        "hard_risk",
        "current_product_ref",
        "stable_state_refs",
    }
)

_RULE_KEYS = frozenset(
    {
        "rule_id",
        "intent_code",
        "outcome_code",
        "template_ref",
        "target_effect_ref",
        "route_mode",
        "coordinate_ref",
        "candidate_product_ref",
        "human_confirmation_required",
        "model_allowed",
        "formal_effect_allowed",
    }
)

_BUNDLE_KEYS = frozenset(
    {
        "$schema",
        "bundle_version",
        "bundle_id",
        "status",
        "phase_id",
        "objective",
        "predecessor",
        "controller",
        "construction_order",
        "templates",
        "rules",
        "unresolved_intent_effect",
        "unknown_slot_effect",
        "replay_controls",
        "data_boundaries",
        "authority",
        "current_decision",
    }
)

_CONTROLLER_KEYS = frozenset(
    {
        "controller_id",
        "path",
        "sha256",
        "mode",
        "external_io_allowed",
        "model_interface_present",
    }
)

_TEMPLATE_KEYS = frozenset(
    {
        "template_ref",
        "template_version",
        "output_kind",
        "output_schema_ref",
        "model_allowed",
        "authority",
        "formal_effect_allowed",
    }
)

_AUTHORITY_KEYS = frozenset(
    {
        "decision_authority",
        "controller_authority",
        "formal_landing_allowed",
        "applies_change",
        "memory_effect",
        "database_write",
        "deployment",
        "restart",
        "remote_write",
        "model_has_authority",
    }
)

_CONFIRMATION_STATES = frozenset(
    {"CONFIRMED", "REQUIRED_PENDING", "REJECTED", "NOT_APPLICABLE"}
)

_ROUTE_MODES = frozenset(
    {"NO_STATE_CHANGE", "CANDIDATE_REFERENCE_REPLACE", "UNKNOWN_SLOT_HOLD"}
)

_TEMPLATE_OUTPUT_BY_ROUTE = {
    "NO_STATE_CHANGE": "NO_STATE_CHANGE",
    "CANDIDATE_REFERENCE_REPLACE": "REFERENCE_DELTA",
    "UNKNOWN_SLOT_HOLD": "UNKNOWN_SLOT_HOLD",
}

_SAFE_REQUEST_FINGERPRINT_KEYS = (
    "request_version",
    "attempt_ref",
    "idempotency_ref",
    "nonce_ref",
    "intent_code",
    "intent_root_ref",
    "scope_ref",
    "expected_state_version",
    "expected_state_sha256",
    "requested_effect_ref",
    "human_confirmation_state",
    "declared_unknown_slots",
    "raw_input_included",
    "member_plaintext_included",
    "secret_material_included",
)


def canonical_sha256(value: object) -> str:
    """Return the SHA-256 of canonical, ASCII JSON for a JSON-compatible value."""

    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _is_ref(value: object) -> bool:
    if not isinstance(value, str) or not (3 <= len(value) <= 256):
        return False
    if any(character.isspace() for character in value):
        return False
    scheme, separator, remainder = value.partition(":")
    return bool(separator and scheme and scheme[0].islower() and remainder)


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_ref_list(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) <= 64
        and all(_is_ref(item) for item in value)
        and len(value) == len(set(value))
    )


def _safe_request_fingerprint(request: object) -> dict[str, object]:
    if not isinstance(request, dict):
        return {"request_shape": type(request).__name__}
    return {
        key: request[key]
        for key in _SAFE_REQUEST_FINGERPRINT_KEYS
        if key in request
        and (
            isinstance(request[key], (str, int, bool, type(None)))
            or (
                isinstance(request[key], list)
                and all(isinstance(item, (str, int, bool, type(None))) for item in request[key])
            )
        )
    }


def _safe_bundle_fingerprint(bundle: object) -> object:
    if not isinstance(bundle, dict):
        return {"bundle_shape": type(bundle).__name__}
    try:
        canonical_sha256(bundle)
    except (TypeError, ValueError):
        return {
            key: value
            for key in ("bundle_version", "bundle_id", "status", "phase_id")
            if isinstance((value := bundle.get(key)), (str, int, bool, type(None)))
        }
    return bundle


def _validate_request(request: object) -> str | None:
    if not isinstance(request, dict) or set(request) != _REQUEST_KEYS:
        return "HOLD_SCHEMA_UNKNOWN_FIELD"
    if request["request_version"] != REQUEST_VERSION:
        return "HOLD_VERSION_UNSUPPORTED"
    for key in (
        "attempt_ref",
        "idempotency_ref",
        "nonce_ref",
        "intent_root_ref",
        "scope_ref",
        "requested_effect_ref",
    ):
        if not _is_ref(request[key]):
            return "HOLD_ENVELOPE_INVALID"
    if not isinstance(request["intent_code"], str) or not request["intent_code"]:
        return "HOLD_ENVELOPE_INVALID"
    if (
        not isinstance(request["expected_state_version"], int)
        or isinstance(request["expected_state_version"], bool)
        or request["expected_state_version"] < 0
    ):
        return "HOLD_ENVELOPE_INVALID"
    if not _is_sha256(request["expected_state_sha256"]):
        return "HOLD_ENVELOPE_INVALID"
    if request["human_confirmation_state"] not in _CONFIRMATION_STATES:
        return "HOLD_ENVELOPE_INVALID"
    if not _is_ref_list(request["declared_unknown_slots"]):
        return "HOLD_ENVELOPE_INVALID"
    for key in (
        "raw_input_included",
        "member_plaintext_included",
        "secret_material_included",
    ):
        if request[key] is not False:
            return "HOLD_FORBIDDEN_DATA_MATERIAL"
    return None


def _validate_rule_bundle(bundle: object) -> tuple[dict[str, dict[str, object]], str | None]:
    if not isinstance(bundle, dict) or set(bundle) != _BUNDLE_KEYS:
        return {}, "HOLD_RULE_BUNDLE_INVALID"
    if bundle["bundle_version"] != "W7TP-SYSTEM-INTENT-FIELD-DETERMINISTIC-SHADOW/1.0":
        return {}, "HOLD_VERSION_UNSUPPORTED"
    if bundle["bundle_id"] != "W7TP_SYSTEM_INTENT_FIELD_DETERMINISTIC_SHADOW_V1_CANDIDATE":
        return {}, "HOLD_RULE_BUNDLE_INVALID"
    if bundle["status"] != "CANDIDATE_SHADOW_ONLY":
        return {}, "HOLD_AUTHORITY_ESCALATION"
    if bundle["phase_id"] != "L03_DETERMINISTIC_CORE_SHADOW":
        return {}, "HOLD_VERSION_UNSUPPORTED"
    if bundle["unresolved_intent_effect"] != "LOCAL_HOLD_INTENT_UNRESOLVED":
        return {}, "HOLD_RULE_BUNDLE_INVALID"
    if bundle["unknown_slot_effect"] != "LOCAL_HOLD_UNKNOWN_SLOT_REQUIRES_L04":
        return {}, "HOLD_RULE_BUNDLE_INVALID"
    controller = bundle["controller"]
    if not isinstance(controller, dict) or set(controller) != _CONTROLLER_KEYS:
        return {}, "HOLD_RULE_BUNDLE_INVALID"
    if (
        controller["controller_id"] != CONTROLLER_ID
        or controller["path"]
        != "tools/total_field/w7tp_system_intent_field_deterministic_shadow.py"
        or not _is_sha256(controller["sha256"])
        or controller["mode"] != "PURE_LOCAL_DETERMINISTIC_REFERENCE_ONLY"
    ):
        return {}, "HOLD_RULE_BUNDLE_INVALID"
    if controller["external_io_allowed"] is not False or controller["model_interface_present"] is not False:
        return {}, "HOLD_AUTHORITY_ESCALATION"
    authority = bundle["authority"]
    if not isinstance(authority, dict) or set(authority) != _AUTHORITY_KEYS:
        return {}, "HOLD_RULE_BUNDLE_INVALID"
    if authority["decision_authority"] != "TOTAL_FIELD" or authority["controller_authority"] != "NONE":
        return {}, "HOLD_AUTHORITY_ESCALATION"
    false_flags = (
        "formal_landing_allowed",
        "applies_change",
        "memory_effect",
        "database_write",
        "deployment",
        "restart",
        "remote_write",
        "model_has_authority",
    )
    if any(authority.get(flag) is not False for flag in false_flags):
        return {}, "HOLD_AUTHORITY_ESCALATION"

    templates = bundle["templates"]
    if not isinstance(templates, list) or not templates:
        return {}, "HOLD_RULE_BUNDLE_INVALID"
    indexed_templates: dict[str, dict[str, object]] = {}
    for template in templates:
        if not isinstance(template, dict) or set(template) != _TEMPLATE_KEYS:
            return {}, "HOLD_RULE_BUNDLE_INVALID"
        if not _is_ref(template["template_ref"]) or not _is_ref(template["output_schema_ref"]):
            return {}, "HOLD_RULE_BUNDLE_INVALID"
        if template["template_ref"] in indexed_templates or template["template_version"] != "1.0":
            return {}, "HOLD_RULE_BUNDLE_INVALID"
        if template["output_kind"] not in set(_TEMPLATE_OUTPUT_BY_ROUTE.values()):
            return {}, "HOLD_RULE_BUNDLE_INVALID"
        if (
            template["model_allowed"] is not False
            or template["authority"] != "NONE"
            or template["formal_effect_allowed"] is not False
        ):
            return {}, "HOLD_AUTHORITY_ESCALATION"
        indexed_templates[template["template_ref"]] = template

    rules = bundle["rules"]
    if not isinstance(rules, list) or not rules:
        return {}, "HOLD_RULE_BUNDLE_INVALID"
    indexed: dict[str, dict[str, object]] = {}
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != _RULE_KEYS:
            return {}, "HOLD_RULE_BUNDLE_INVALID"
        if not isinstance(rule["intent_code"], str) or not rule["intent_code"]:
            return {}, "HOLD_RULE_BUNDLE_INVALID"
        if rule["intent_code"] in indexed:
            return {}, "HOLD_RULE_BUNDLE_INVALID"
        if rule["route_mode"] not in _ROUTE_MODES:
            return {}, "HOLD_RULE_BUNDLE_INVALID"
        for key in (
            "rule_id",
            "template_ref",
            "target_effect_ref",
            "coordinate_ref",
            "candidate_product_ref",
        ):
            if not _is_ref(rule[key]):
                return {}, "HOLD_RULE_BUNDLE_INVALID"
        if not isinstance(rule["outcome_code"], str) or not rule["outcome_code"]:
            return {}, "HOLD_RULE_BUNDLE_INVALID"
        if rule["human_confirmation_required"] is not True:
            return {}, "HOLD_RULE_BUNDLE_INVALID"
        if rule["model_allowed"] is not False or rule["formal_effect_allowed"] is not False:
            return {}, "HOLD_AUTHORITY_ESCALATION"
        template = indexed_templates.get(rule["template_ref"])
        if template is None or template["output_kind"] != _TEMPLATE_OUTPUT_BY_ROUTE[rule["route_mode"]]:
            return {}, "HOLD_RULE_BUNDLE_INVALID"
        indexed[rule["intent_code"]] = rule
    return indexed, None


def _validate_state(state: object, scope_ref: str) -> str | None:
    if not isinstance(state, dict) or set(state) != _STATE_KEYS:
        return "HOLD_STATE_UNVERIFIED"
    if state["scope_ref"] != scope_ref:
        return "HOLD_COORDINATE_UNBOUND"
    if not _is_ref(state["state_root_ref"]) or not _is_sha256(state["state_sha256"]):
        return "HOLD_STATE_UNVERIFIED"
    if (
        not isinstance(state["state_version"], int)
        or isinstance(state["state_version"], bool)
        or state["state_version"] < 0
    ):
        return "HOLD_STATE_UNVERIFIED"
    if not _is_ref(state["current_product_ref"]) or not _is_ref_list(state["stable_state_refs"]):
        return "HOLD_STATE_UNVERIFIED"
    if state["verified"] is not True:
        return "HOLD_STATE_UNVERIFIED"
    if state["coordinate_bound"] is not True:
        return "HOLD_COORDINATE_UNBOUND"
    if state["canonical_lock_state"] != "LOCKED":
        return "HOLD_CANONICAL_LOCK_FAILED"
    if state["evidence_complete"] is not True:
        return "HOLD_EVIDENCE_INCOMPLETE"
    if state["hard_risk"] is not False:
        return "HOLD_HARD_RISK"
    return None


def _trace_result(
    *,
    bundle: object,
    request: object,
    decision: str,
    reason_code: str,
    intent_resolution: str,
    state_load_calls: int,
    state: dict[str, object] | None,
    gates: list[dict[str, str]],
    candidate_delta: dict[str, object] | None,
) -> dict[str, object]:
    safe_request = _safe_request_fingerprint(request)
    bundle_fingerprint = _safe_bundle_fingerprint(bundle)
    trace: dict[str, object] = {
        "trace_version": TRACE_VERSION,
        "controller_id": CONTROLLER_ID,
        "bundle_id": bundle.get("bundle_id") if isinstance(bundle, dict) else None,
        "bundle_sha256": canonical_sha256(bundle_fingerprint),
        "request_sha256": canonical_sha256(safe_request),
        "intent_resolution": intent_resolution,
        "state_load_calls": state_load_calls,
        "model_call_count": 0,
        "formal_effect_count": 0,
        "state_root_ref": state.get("state_root_ref") if state else None,
        "state_version": state.get("state_version") if state else None,
        "state_sha256": state.get("state_sha256") if state else None,
        "gates": gates,
        "decision": decision,
        "reason_code": reason_code,
        "candidate_delta_sha256": canonical_sha256(candidate_delta) if candidate_delta else None,
        "authority": {
            "decision_authority": "TOTAL_FIELD",
            "controller_authority": "NONE",
            "formal_landing_allowed": False,
            "applies_change": False,
            "memory_effect": False,
            "database_write": False,
            "deployment": False,
            "restart": False,
            "remote_write": False,
        },
    }
    trace["trace_sha256"] = canonical_sha256(trace)
    return {
        "decision": decision,
        "reason_code": reason_code,
        "candidate_delta": candidate_delta,
        "decision_trace": trace,
    }


def _hold(
    *,
    bundle: object,
    request: object,
    reason_code: str,
    intent_resolution: str,
    state_load_calls: int = 0,
    state: dict[str, object] | None = None,
    gates: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    return _trace_result(
        bundle=bundle,
        request=request,
        decision="HOLD",
        reason_code=reason_code,
        intent_resolution=intent_resolution,
        state_load_calls=state_load_calls,
        state=state,
        gates=gates or [],
        candidate_delta=None,
    )


def _minimum_delta(
    request: dict[str, object],
    state: dict[str, object],
    rule: dict[str, object],
) -> dict[str, object]:
    candidate_seed = {
        "intent_root_ref": request["intent_root_ref"],
        "state_root_ref": state["state_root_ref"],
        "state_version": state["state_version"],
        "coordinate_ref": rule["coordinate_ref"],
        "previous_state_ref": state["current_product_ref"],
        "candidate_state_ref": rule["candidate_product_ref"],
        "template_ref": rule["template_ref"],
    }
    delta_hash = canonical_sha256(candidate_seed)
    candidate_state_hash = canonical_sha256(
        {"candidate_state_ref": rule["candidate_product_ref"]}
    )
    stable_refs = sorted(
        set(state["stable_state_refs"])
        | {state["state_root_ref"], rule["template_ref"]}
    )
    return {
        "contract_version": DELTA_VERSION,
        "delta_id": f"delta:{delta_hash}",
        "intent_root_ref": request["intent_root_ref"],
        "current_state_root_ref": state["state_root_ref"],
        "minimum_delta_state": "DELTA_REQUIRED",
        "affected_coordinates": [rule["coordinate_ref"]],
        "stable_refs": stable_refs,
        "changed_state": [
            {
                "coordinate_ref": rule["coordinate_ref"],
                "operation": "REPLACE_REFERENCE",
                "previous_state_ref": state["current_product_ref"],
                "candidate_state_ref": rule["candidate_product_ref"],
                "candidate_state_sha256": candidate_state_hash,
                "authority": "NONE",
            }
        ],
        "unknown_slots": [],
        "reconstruction_conditions": [
            "condition:state-version-cas",
            "condition:source-state-hash-match",
            "condition:candidate-only",
        ],
        "verification_conditions": [
            "verification:closed-schema",
            "verification:reference-only",
            "verification:total-field-static-review",
        ],
        "target_product_effect": rule["target_effect_ref"],
        "none_effect": "BUILD_NOT_REQUIRED",
        "model_packet_policy": {
            "allowed_material": [
                "intent_root_ref",
                "current_state_root_ref",
                "stable_state_refs",
                "affected_coordinates",
                "unknown_slots",
                "target_product_effect",
                "reconstruction_conditions",
                "verification_conditions",
                "output_schema",
            ],
            "forbidden_material": [
                "RAW_USER_INPUT",
                "FULL_CONTEXT",
                "KNOWN_PRIVATE_STATE_VALUE",
                "MEMBER_PLAINTEXT",
                "PAYMENT_SECRET",
                "CREDENTIAL_OR_TOKEN",
            ],
            "output_authority": "CANDIDATE_ONLY",
        },
        "authority": "NONE",
        "raw_input_included": False,
        "full_context_included": False,
        "known_private_state_values_included": False,
        "member_plaintext_included": False,
        "secret_material_included": False,
    }


def run_shadow(
    request: object,
    scoped_state_by_ref: object,
    rule_bundle: object,
) -> dict[str, object]:
    """Evaluate one L03 request with deterministic, candidate-only semantics.

    ``scoped_state_by_ref`` must be an in-memory mapping-like object supporting
    ``__getitem__``.  It is never accessed until request validation, rule-bundle
    validation, and exact governed-intent resolution have succeeded.
    """

    request_error = _validate_request(request)
    if request_error:
        return _hold(
            bundle=rule_bundle,
            request=request,
            reason_code=request_error,
            intent_resolution="NOT_EVALUATED",
        )

    rules, bundle_error = _validate_rule_bundle(rule_bundle)
    if bundle_error:
        return _hold(
            bundle=rule_bundle,
            request=request,
            reason_code=bundle_error,
            intent_resolution="NOT_EVALUATED",
        )

    rule = rules.get(request["intent_code"])
    if rule is None:
        return _hold(
            bundle=rule_bundle,
            request=request,
            reason_code="LOCAL_HOLD_INTENT_UNRESOLVED",
            intent_resolution="UNRESOLVED_HOLD_BEFORE_STATE_LOAD_OR_MODEL",
        )

    try:
        state = scoped_state_by_ref[request["scope_ref"]]
    except (KeyError, TypeError, AttributeError):
        return _hold(
            bundle=rule_bundle,
            request=request,
            reason_code="HOLD_STATE_UNVERIFIED",
            intent_resolution="RESOLVED_DETERMINISTIC_RULE",
            state_load_calls=1,
            gates=[{"gate_id": "GATE_1_CANONICAL_LOCK", "result": "HOLD_STATE_MISSING"}],
        )

    if not isinstance(state, dict):
        return _hold(
            bundle=rule_bundle,
            request=request,
            reason_code="HOLD_STATE_UNVERIFIED",
            intent_resolution="RESOLVED_DETERMINISTIC_RULE",
            state_load_calls=1,
            gates=[{"gate_id": "GATE_1_CANONICAL_LOCK", "result": "HOLD_STATE_INVALID"}],
        )

    state_error = _validate_state(state, request["scope_ref"])
    if state_error:
        return _hold(
            bundle=rule_bundle,
            request=request,
            reason_code=state_error,
            intent_resolution="RESOLVED_DETERMINISTIC_RULE",
            state_load_calls=1,
            state=state,
            gates=[{"gate_id": "GATE_1_CANONICAL_LOCK", "result": state_error}],
        )

    if (
        state["state_version"] != request["expected_state_version"]
        or state["state_sha256"] != request["expected_state_sha256"]
    ):
        return _hold(
            bundle=rule_bundle,
            request=request,
            reason_code="HOLD_STATE_VERSION_RACE",
            intent_resolution="RESOLVED_DETERMINISTIC_RULE",
            state_load_calls=1,
            state=state,
            gates=[{"gate_id": "GATE_1_CANONICAL_LOCK", "result": "HOLD_CAS_MISMATCH"}],
        )

    gates = [{"gate_id": "GATE_1_CANONICAL_LOCK", "result": "PASS"}]
    if request["requested_effect_ref"] != rule["target_effect_ref"]:
        gates.append(
            {"gate_id": "GATE_2_INTENT_PRODUCT_GAP", "result": "HOLD_TARGET_EFFECT_MISMATCH"}
        )
        return _hold(
            bundle=rule_bundle,
            request=request,
            reason_code="HOLD_TARGET_EFFECT_MISMATCH",
            intent_resolution="RESOLVED_DETERMINISTIC_RULE",
            state_load_calls=1,
            state=state,
            gates=gates,
        )

    if rule["route_mode"] == "UNKNOWN_SLOT_HOLD" or request["declared_unknown_slots"]:
        gates.extend(
            [
                {"gate_id": "GATE_2_INTENT_PRODUCT_GAP", "result": "UNKNOWN_SLOTS_DECLARED"},
                {"gate_id": "GATE_3_HUMAN_UI_PRODUCT_REVIEW", "result": "NOT_EVALUATED"},
            ]
        )
        return _hold(
            bundle=rule_bundle,
            request=request,
            reason_code="LOCAL_HOLD_UNKNOWN_SLOT_REQUIRES_L04",
            intent_resolution="RESOLVED_UNKNOWN_SLOT_ROUTE_NO_MODEL",
            state_load_calls=1,
            state=state,
            gates=gates,
        )

    if (
        rule["route_mode"] == "NO_STATE_CHANGE"
        or state["current_product_ref"] == rule["candidate_product_ref"]
    ):
        gates.extend(
            [
                {"gate_id": "GATE_2_INTENT_PRODUCT_GAP", "result": "NO_MINIMUM_DELTA"},
                {"gate_id": "GATE_3_HUMAN_UI_PRODUCT_REVIEW", "result": "NOT_APPLICABLE_NO_GAP"},
            ]
        )
        return _trace_result(
            bundle=rule_bundle,
            request=request,
            decision="BUILD_NOT_REQUIRED",
            reason_code="NO_MINIMUM_DELTA",
            intent_resolution="RESOLVED_DETERMINISTIC_RULE",
            state_load_calls=1,
            state=state,
            gates=gates,
            candidate_delta=None,
        )

    gates.append({"gate_id": "GATE_2_INTENT_PRODUCT_GAP", "result": "PASS_MINIMUM_DELTA"})
    if request["human_confirmation_state"] != "CONFIRMED":
        review_result = (
            "HOLD_HUMAN_REJECTED"
            if request["human_confirmation_state"] == "REJECTED"
            else "HOLD_HUMAN_CONFIRMATION_REQUIRED"
        )
        gates.append({"gate_id": "GATE_3_HUMAN_UI_PRODUCT_REVIEW", "result": review_result})
        return _hold(
            bundle=rule_bundle,
            request=request,
            reason_code=review_result,
            intent_resolution="RESOLVED_DETERMINISTIC_RULE",
            state_load_calls=1,
            state=state,
            gates=gates,
        )

    gates.append({"gate_id": "GATE_3_HUMAN_UI_PRODUCT_REVIEW", "result": "PASS_CONFIRMED"})
    candidate_delta = _minimum_delta(request, state, rule)
    return _trace_result(
        bundle=rule_bundle,
        request=request,
        decision="CANDIDATE_READY_FOR_TOTAL_FIELD",
        reason_code="DETERMINISTIC_REFERENCE_DELTA_READY",
        intent_resolution="RESOLVED_DETERMINISTIC_RULE",
        state_load_calls=1,
        state=state,
        gates=gates,
        candidate_delta=candidate_delta,
    )


__all__ = ["CONTROLLER_ID", "canonical_sha256", "run_shadow"]
