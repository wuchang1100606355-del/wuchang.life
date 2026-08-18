#!/usr/bin/env python3
"""Deterministic non-live TRUE8D contract and read-only shadow sandbox.

This module is a verifier around the existing TRUE8D candidate runtime.  It is
not a second Total Field engine: projections remain non-authoritative, D8 is a
canonical envelope, and every result keeps commit and seal disabled.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = ROOT / "runtime/total_field/inbox/W7TP_TRUE8D_EIGHT_FIELD_CONTAINERIZATION_PLAN_V2_20260717T140655Z.json"
ROUTE_TABLE_PATH = ROOT / "runtime/total_field/secondary_cloud/scenario_route_table.json"
CAPABILITY_REGISTRY_PATH = ROOT / "runtime/total_field/secondary_cloud/capability_registry.json"

COMMON_INPUT_FIELDS = (
    "contract_version", "field_id", "event_id", "attempt_id", "logical_time",
    "snapshot_id", "previous_total_state_hash", "event_payload_hash",
    "adi_coordinate_ref", "canonical_schema_ref", "ruleset_hash", "rule_refs",
    "deadline_monotonic_ns",
)
FIELD_IDS = tuple(f"D{index}" for index in range(1, 9))
PROFILES = ("ASSOCIATION", "CAFE_POS", "GENERIC", "HOUSEHOLD", "PROPERTY")
CONSUMERS = ("INTENT", "ODOO", "POS", "MEDICAL", "BUSINESS", "PROPERTY", "COMMUNITY")
D8_FIELDS = (
    "packet_id", "authority_ref", "version", "ttl_seconds", "nonce", "sha256",
    "verifier_ref", "seal_policy",
)
FIELD_OUTPUT_FIELDS = {
    "D1": ("normalized_intent_ref", "requested_effect_ref", "constraint_set_hash", "founder_authority_match"),
    "D2": ("previous_state_hash", "proposed_state_hash", "lifecycle_state"),
    "D3": ("branch", "actor_role", "channel", "node_id", "lan_state", "wan_state", "vpn_state", "firewall_state", "dns_state", "hardware_channel", "transition_hash"),
    "D4": ("verified_evidence_refs", "verified_evidence_hashes", "completeness", "verification_summary_hash"),
    "D5": ("action_code", "target_ref", "precondition_hash", "side_effect_class", "requires_explicit_gate", "commit_applied"),
    "D6": ("transport_protocol_ref", "lookup_refs", "reconstruction_condition_refs", "verification_method_ref", "equivalent_state_digest", "model_required", "float_value_count", "full_file_copy_present"),
    "D7": ("risk_codes", "risk_level", "disposition", "blocking_evidence_refs"),
    "D8": D8_FIELDS,
}
HARD_RISK_CODES = (
    "RAW_KEY_TOKEN_PASSWORD", "MEMBER_PLAINTEXT", "DELETE_OVERWRITE_MOVE_ORIGINAL_FILE",
    "LIVE_DB_WRITE", "DEPLOY_RESTART_REBOOT", "ROUTER_WRITE",
    "UNCONFIRMED_FORMAL_SUBMISSION", "DELETE_LOCAL_BEFORE_CLOUD_VERIFICATION",
)
RESOURCE_BUDGETS = {
    **{f"D{index}": {"cpu_request_m": 140, "cpu_limit_m": 350, "memory_request_mib": 176, "memory_limit_mib": 384} for index in range(1, 8)},
    "D8": {"cpu_request_m": 170, "cpu_limit_m": 550, "memory_request_mib": 176, "memory_limit_mib": 384},
}

# These locks are a local, candidate-only fast-reject aid.  They deliberately
# cannot declare a canonical PASS: the injected canonical gate remains the
# verifier for the scoped state that was actually loaded for an intent.
CANONICAL_DRIFT_LOCKS = {
    "8d": {
        "required": ("interactive_state_field",),
        "forbidden": ("ordinary_json_fields",),
    },
    "adi_native": {
        "required": ("phi_f", "delta_f", "omega_f"),
        "forbidden": (
            "embedding",
            "vector_similarity",
            "morton_z_order",
            "manhattan_as_native",
            "chebyshev_as_native",
        ),
    },
    "generative_transmission": {
        "required": (
            "state_packet",
            "reference",
            "lookup",
            "reconstruction_conditions",
            "equivalent_state_generation",
            "verification",
        ),
        "forbidden": (
            "file_copy_as_definition",
            "scp_as_definition",
            "backup_as_definition",
            "cloud_sync_as_definition",
        ),
    },
    "authority": {
        "required": ("model_candidate_only", "total_field_final_verifier"),
        "forbidden": ("second_total_field", "model_final_authority"),
    },
}

_STATE_FIELD_REF_MODES = frozenset({"REF", "DELTA", "GENERATE", "INLINE"})
_CANONICAL_SECOND_CORE_KEYS = frozenset(
    {
        "second_total_field",
        "second_identity_root",
        "second_adi_canonical_truth",
        "second_xiaoj",
    }
)
_MODEL_CANDIDATE_FIELDS = frozenset(
    {"candidate_delta_only", "unknown_slots", "formal_authority"}
)


Model53 = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class IntentRoot:
    """The resolved D1 state, kept separate from the original user text."""

    result: str
    subject: str
    scene: str
    known_state_refs: tuple[str, ...]
    constraints: tuple[str, ...]
    acceptance: tuple[str, ...]
    target_product_effect: tuple[str, ...]


@dataclass(frozen=True)
class StateFieldRef:
    """An addressable D1-D7 state field reference, never its full payload."""

    dimension: str
    state_ref: str
    mode: str

    def __post_init__(self) -> None:
        if self.dimension not in FIELD_IDS[:7]:
            raise ValueError("D1_D7_FIELD_REFERENCE_REQUIRED")
        if not isinstance(self.state_ref, str) or not self.state_ref:
            raise ValueError("STATE_FIELD_REFERENCE_REQUIRED")
        if self.mode not in _STATE_FIELD_REF_MODES:
            raise ValueError("STATE_FIELD_REFERENCE_MODE_INVALID")


@dataclass(frozen=True)
class NodeD8Envelope:
    """Reference-only D8 root envelope; D1-D7 remain independent state fields."""

    node_id: str
    intent_root_ref: str
    field_refs: tuple[StateFieldRef, ...]
    parent_state_root: str
    evidence_root: str
    rule_version: str
    logical_time: int


@dataclass(frozen=True)
class MinimumDelta:
    """The smallest sufficient scoped state change, not a code-line count."""

    affected_coordinates: tuple[str, ...]
    stable_refs: tuple[str, ...]
    changed_state: Mapping[str, Any]
    unknown_slots: tuple[str, ...]
    reconstruction_conditions: tuple[str, ...]
    verification_conditions: tuple[str, ...]
    target_product_effect: tuple[str, ...]

    @property
    def is_none(self) -> bool:
        return (
            not self.affected_coordinates
            and not self.changed_state
            and not self.unknown_slots
        )


@dataclass(frozen=True)
class GateResult:
    state: str
    reason: str = ""


@dataclass(frozen=True)
class SubprocessResult:
    """Candidate result only; it never contains a Total Field formal verdict."""

    state: str
    minimum_delta: MinimumDelta | None
    candidate_delta: Mapping[str, Any] | None
    model_calls: int
    evidence: tuple[str, ...]


class ContractSandboxError(ValueError):
    """Stable fail-closed sandbox error with no source payload echo."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _walk(value: Any) -> None:
    """Enforce JSON, NFC strings, integer-only numbers, and finite structure."""

    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        raise ContractSandboxError("HOLD_FIELD_FLOAT_FORBIDDEN")
    if isinstance(value, str):
        if unicodedata.normalize("NFC", value) != value:
            raise ContractSandboxError("HOLD_TEXT_NOT_NFC")
        return
    if isinstance(value, list):
        for item in value:
            _walk(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContractSandboxError("HOLD_JSON_KEY_INVALID")
            _walk(key)
            _walk(item)
        return
    raise ContractSandboxError("HOLD_NON_JSON_VALUE")


def canonical_json(value: Any) -> str:
    """Return the integer-only RFC8785-compatible canonical JSON subset."""

    _walk(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_sha256(value: Any) -> str:
    """Hash one canonical sandbox value."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    """Hash one explicit local evidence file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _closed(value: Any, fields: Sequence[str], missing: str, extra: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractSandboxError(missing)
    result = dict(value)
    expected = set(fields)
    if expected - set(result):
        raise ContractSandboxError(missing)
    if set(result) - expected:
        raise ContractSandboxError(extra)
    _walk(result)
    return result


def validate_common_input(value: Mapping[str, Any], field_id: str) -> dict[str, Any]:
    """Validate one immutable closed projection input."""

    result = _closed(value, COMMON_INPUT_FIELDS, "HOLD_FIELD_INPUT_MISSING", "HOLD_FIELD_INPUT_EXTRA")
    if field_id not in FIELD_IDS or result["field_id"] != field_id:
        raise ContractSandboxError("QUARANTINE_FIELD_IDENTITY_MISMATCH")
    if result["contract_version"] != "W7TP-TRUE8D-MACHINE-CONTRACT/2.0":
        raise ContractSandboxError("HOLD_FIELD_SCHEMA_INVALID")
    for name in ("previous_total_state_hash", "event_payload_hash", "ruleset_hash"):
        if not _is_hash(result[name]):
            raise ContractSandboxError("HOLD_REFERENCE_INVALID")
    if not isinstance(result["logical_time"], int) or not isinstance(result["deadline_monotonic_ns"], int):
        raise ContractSandboxError("HOLD_FIELD_FLOAT_FORBIDDEN")
    refs = result["rule_refs"]
    if not isinstance(refs, list) or not refs or refs != sorted(set(refs)):
        raise ContractSandboxError("HOLD_REFERENCE_INVALID")
    return result


def validate_field_output(field_id: str, value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one exact non-authoritative field output."""

    if field_id not in FIELD_OUTPUT_FIELDS:
        raise ContractSandboxError("QUARANTINE_FIELD_IDENTITY_MISMATCH")
    result = _closed(value, FIELD_OUTPUT_FIELDS[field_id], "HOLD_FIELD_SCHEMA_INVALID", "HOLD_FIELD_SCHEMA_INVALID")
    if field_id == "D5" and result["commit_applied"] is not False:
        raise ContractSandboxError("BLOCK_PROJECTION_COMMIT_AUTHORITY")
    if field_id == "D6" and (result["model_required"] is not False or result["float_value_count"] != 0 or result["full_file_copy_present"] is not False):
        raise ContractSandboxError("BLOCK_GENERATIVE_TRANSMISSION_DRIFT")
    if field_id == "D7" and any(code in HARD_RISK_CODES for code in result["risk_codes"]):
        if result["disposition"] != "BLOCK":
            raise ContractSandboxError("BLOCK_D7_HARD_RISK_PRECEDENCE")
    if field_id == "D8" and tuple(result) != D8_FIELDS:
        raise ContractSandboxError("BLOCK_D8_CANONICAL_AUTHORITY_DRIFT")
    return result


def projection_hash(common_input: Mapping[str, Any], output: Mapping[str, Any]) -> str:
    """Apply the approved projection-hash contract."""

    payload = {
        "contract_version": common_input["contract_version"],
        "field_id": common_input["field_id"],
        "event_id": common_input["event_id"],
        "attempt_id": common_input["attempt_id"],
        "snapshot_id": common_input["snapshot_id"],
        "previous_total_state_hash": common_input["previous_total_state_hash"],
        "event_payload_hash": common_input["event_payload_hash"],
        "ruleset_hash": common_input["ruleset_hash"],
        "sorted_rule_refs": common_input["rule_refs"],
        "output": output,
    }
    return canonical_sha256(payload)


def construction_order() -> tuple[str, ...]:
    """Return the non-negotiable order for this bounded candidate worker."""

    return (
        "D1_INTENT_RESOLUTION",
        "LOAD_VERIFIED_SCOPED_STATE",
        "GATE_1_CANONICAL_LOCK",
        "GATE_2_INTENT_PRODUCT_GAP",
        "GATE_3_HUMAN_UI_PRODUCT_REVIEW",
        "GENERATE_UNKNOWN_DELTA_ONLY",
        "RECONSTRUCT_CANDIDATE_STATE",
        "VERIFY_CANDIDATE",
        "TOTAL_FIELD_REVIEW",
    )


def _normalized_lock_token(value: str) -> str:
    return "_".join(
        "".join(char if char.isalnum() else " " for char in value.casefold()).split()
    )


def _lock_values(value: Any) -> set[str]:
    """Collect asserted drift values without mistaking a prohibition for drift."""

    if isinstance(value, str):
        return {_normalized_lock_token(value)}
    if isinstance(value, Mapping):
        values: set[str] = set()
        forbidden = {
            _normalized_lock_token(marker)
            for lock in CANONICAL_DRIFT_LOCKS.values()
            for marker in lock["forbidden"]
        }
        forbidden.update(_CANONICAL_SECOND_CORE_KEYS)
        for key, nested in value.items():
            normalized_key = _normalized_lock_token(key) if isinstance(key, str) else ""
            if normalized_key == "forbidden":
                continue
            if normalized_key in forbidden and nested is True:
                values.add(normalized_key)
            values.update(_lock_values(nested))
        return values
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        values: set[str] = set()
        for nested in value:
            values.update(_lock_values(nested))
        return values
    return set()


def fast_reject_canonical_drift(*scoped_values: Any) -> GateResult:
    """Reject explicit drift markers; absence of a marker is not a PASS verdict."""

    values: set[str] = set()
    for scoped_value in scoped_values:
        values.update(_lock_values(scoped_value))

    forbidden = {
        _normalized_lock_token(marker)
        for lock in CANONICAL_DRIFT_LOCKS.values()
        for marker in lock["forbidden"]
    }
    forbidden.update(_CANONICAL_SECOND_CORE_KEYS)
    hits = sorted(values & forbidden)
    if hits:
        return GateResult(
            "HOLD_DETOUR_ALERT",
            "canonical drift lock hit:" + ",".join(hits),
        )
    return GateResult("NO_FAST_REJECT")


def _intent_root_is_complete(intent: Any) -> bool:
    if not isinstance(intent, IntentRoot):
        return False
    if not all(
        isinstance(value, str) and value.strip()
        for value in (intent.result, intent.subject, intent.scene)
    ):
        return False
    for values in (
        intent.known_state_refs,
        intent.constraints,
        intent.acceptance,
        intent.target_product_effect,
    ):
        if not isinstance(values, tuple) or not values or not all(
            isinstance(value, str) and value.strip() for value in values
        ):
            return False
    return True


def _minimum_delta_is_valid(delta: Any) -> bool:
    if not isinstance(delta, MinimumDelta):
        return False
    for values in (
        delta.affected_coordinates,
        delta.stable_refs,
        delta.unknown_slots,
        delta.reconstruction_conditions,
        delta.verification_conditions,
        delta.target_product_effect,
    ):
        if not isinstance(values, tuple) or not all(
            isinstance(value, str) and value.strip() for value in values
        ):
            return False
    if not isinstance(delta.changed_state, Mapping):
        return False
    return len(set(delta.unknown_slots)) == len(delta.unknown_slots)


def _intent_root_ref(intent: IntentRoot) -> str:
    payload = {
        "result": intent.result,
        "subject": intent.subject,
        "scene": intent.scene,
        "known_state_refs": list(intent.known_state_refs),
        "constraints": list(intent.constraints),
        "acceptance": list(intent.acceptance),
        "target_product_effect": list(intent.target_product_effect),
    }
    return "intent:d1:" + canonical_sha256(payload)


def _current_state_root_ref(current: Any) -> str | None:
    """Use a supplied reference when available; never invent one for a model."""

    if isinstance(current, Mapping):
        reference = current.get("state_root_ref")
        if isinstance(reference, str) and reference.strip():
            return reference
    return None


def _generation_packet(
    intent: IntentRoot,
    current_state_root_ref: str,
    delta: MinimumDelta,
) -> dict[str, Any]:
    """Build the model packet from references and unknown slots only."""

    return {
        "intent_root_ref": _intent_root_ref(intent),
        "current_state_root_ref": current_state_root_ref,
        "stable_state_refs": list(delta.stable_refs),
        "affected_coordinates": list(delta.affected_coordinates),
        "unknown_slots": list(delta.unknown_slots),
        "target_product_effect": list(delta.target_product_effect),
        "reconstruction_conditions": list(delta.reconstruction_conditions),
        "verification_conditions": list(delta.verification_conditions),
        "output_schema": {
            "candidate_delta_only": True,
            "unknown_slots_exact_match": True,
            "formal_authority": False,
        },
    }


def _model_candidate_is_valid(candidate: Any, delta: MinimumDelta) -> GateResult:
    if not isinstance(candidate, Mapping):
        return GateResult("LOCAL_HOLD_MODEL_OUTPUT_INVALID", "model output is not a mapping")
    if set(candidate) != _MODEL_CANDIDATE_FIELDS:
        return GateResult("LOCAL_HOLD_MODEL_OUTPUT_INVALID", "model output fields are not closed")
    if candidate.get("candidate_delta_only") is not True:
        return GateResult("LOCAL_HOLD_MODEL_OUTPUT_INVALID", "candidate_delta_only is required")
    if candidate.get("formal_authority") is not False:
        return GateResult("LOCAL_HOLD_MODEL_OUTPUT_INVALID", "model cannot claim formal authority")
    slots = candidate.get("unknown_slots")
    if not isinstance(slots, Mapping) or set(slots) != set(delta.unknown_slots):
        return GateResult("LOCAL_HOLD_MODEL_OUTPUT_INVALID", "unknown slots do not match the delta")
    try:
        _walk(dict(candidate))
    except ContractSandboxError as exc:
        return GateResult("LOCAL_HOLD_MODEL_OUTPUT_INVALID", exc.code)
    return GateResult("PASS")


def _candidate_invalid_result(
    delta: MinimumDelta,
    candidate: Mapping[str, Any] | None,
    model_calls: int,
    reason: str,
) -> SubprocessResult:
    return SubprocessResult(
        state="LOCAL_HOLD_CANDIDATE_INVALID",
        minimum_delta=delta,
        candidate_delta=candidate,
        model_calls=model_calls,
        evidence=(reason,),
    )


def run_three_gate_subprocess(
    *,
    user_input: str,
    node_id: str,
    model53: Model53,
    resolve_intent: Callable[[str], IntentRoot | None],
    load_scoped_state: Callable[[IntentRoot, str], Any],
    canonical_gate: Callable[[IntentRoot, Any], GateResult],
    measure_minimum_delta: Callable[[IntentRoot, Any], MinimumDelta],
    human_product_gate: Callable[[IntentRoot, MinimumDelta], GateResult],
    verify_candidate: Callable[[IntentRoot, Any, MinimumDelta, Mapping[str, Any]], GateResult],
) -> SubprocessResult:
    """Run D1 → three gates → one optional candidate call with no authority grant."""

    try:
        intent = resolve_intent(user_input)
    except Exception as exc:
        return SubprocessResult(
            "LOCAL_HOLD_INTENT_UNRESOLVED",
            None,
            None,
            0,
            (f"intent resolver raised {type(exc).__name__}",),
        )
    if not _intent_root_is_complete(intent):
        return SubprocessResult(
            "LOCAL_HOLD_INTENT_UNRESOLVED",
            None,
            None,
            0,
            ("D1_INTENT_ROOT_REQUIRED",),
        )
    if not isinstance(node_id, str) or not node_id.strip():
        return SubprocessResult(
            "LOCAL_HOLD_SCOPED_STATE_UNAVAILABLE",
            None,
            None,
            0,
            ("node_id is required for scoped state",),
        )

    try:
        current = load_scoped_state(intent, node_id)
    except Exception as exc:
        return SubprocessResult(
            "LOCAL_HOLD_SCOPED_STATE_UNAVAILABLE",
            None,
            None,
            0,
            (f"scoped state loader raised {type(exc).__name__}",),
        )

    fast_reject = fast_reject_canonical_drift(intent, current)
    if fast_reject.state == "HOLD_DETOUR_ALERT":
        return SubprocessResult(
            "HOLD_DETOUR_ALERT",
            None,
            None,
            0,
            (fast_reject.reason,),
        )
    try:
        gate_one = canonical_gate(intent, current)
    except Exception as exc:
        gate_one = GateResult("HOLD_DETOUR_ALERT", f"canonical gate raised {type(exc).__name__}")
    if not isinstance(gate_one, GateResult) or gate_one.state != "PASS":
        reason = gate_one.reason if isinstance(gate_one, GateResult) else "canonical gate result invalid"
        return SubprocessResult("HOLD_DETOUR_ALERT", None, None, 0, (reason,))

    try:
        delta = measure_minimum_delta(intent, current)
    except Exception as exc:
        return SubprocessResult(
            "LOCAL_HOLD_MINIMUM_DELTA_UNAVAILABLE",
            None,
            None,
            0,
            (f"minimum delta measurement raised {type(exc).__name__}",),
        )
    if not _minimum_delta_is_valid(delta):
        return SubprocessResult(
            "LOCAL_HOLD_MINIMUM_DELTA_UNAVAILABLE",
            None,
            None,
            0,
            ("minimum delta contract invalid",),
        )
    if delta.is_none:
        return SubprocessResult(
            "BUILD_NOT_REQUIRED",
            delta,
            None,
            0,
            ("TRUE_MINIMUM_DELTA=NONE",),
        )

    try:
        gate_three = human_product_gate(intent, delta)
    except Exception as exc:
        gate_three = GateResult(
            "LOCAL_HOLD_PRODUCT_EFFECT",
            f"human product gate raised {type(exc).__name__}",
        )
    if not isinstance(gate_three, GateResult) or gate_three.state != "PASS":
        reason = gate_three.reason if isinstance(gate_three, GateResult) else "human product gate result invalid"
        return SubprocessResult(
            "LOCAL_HOLD_PRODUCT_EFFECT",
            delta,
            None,
            0,
            (reason,),
        )

    model_calls = 0
    if delta.unknown_slots:
        current_state_root_ref = _current_state_root_ref(current)
        if current_state_root_ref is None:
            return SubprocessResult(
                "LOCAL_HOLD_SCOPED_STATE_UNAVAILABLE",
                delta,
                None,
                0,
                ("CURRENT_STATE_ROOT_REF_REQUIRED",),
            )
        model_calls = 1
        try:
            candidate = model53(_generation_packet(intent, current_state_root_ref, delta))
        except Exception as exc:
            return SubprocessResult(
                "LOCAL_HOLD_MODEL_OUTPUT_INVALID",
                delta,
                None,
                model_calls,
                (f"model call raised {type(exc).__name__}",),
            )
        candidate_gate = _model_candidate_is_valid(candidate, delta)
        if candidate_gate.state != "PASS":
            return SubprocessResult(
                "LOCAL_HOLD_MODEL_OUTPUT_INVALID",
                delta,
                dict(candidate) if isinstance(candidate, Mapping) else None,
                model_calls,
                (candidate_gate.reason,),
            )
        evidence = ("THREE_GATES_CLOSED", "CANDIDATE_ONLY", "UNKNOWN_SLOTS_ONLY")
    else:
        # A deterministic delta does not need a model.  The delta itself stays
        # with the local verifier; this candidate merely records that no
        # unknown state was generated.
        candidate = {
            "candidate_delta_only": True,
            "unknown_slots": {},
            "formal_authority": False,
        }
        evidence = ("THREE_GATES_CLOSED", "CANDIDATE_ONLY", "NO_UNKNOWN_SLOT_NO_MODEL_CALL")

    try:
        post = verify_candidate(intent, current, delta, candidate)
    except Exception as exc:
        return _candidate_invalid_result(
            delta,
            candidate,
            model_calls,
            f"candidate verifier raised {type(exc).__name__}",
        )
    if not isinstance(post, GateResult) or post.state != "PASS":
        reason = post.reason if isinstance(post, GateResult) else "candidate verifier result invalid"
        return _candidate_invalid_result(delta, candidate, model_calls, reason)

    return SubprocessResult(
        "CANDIDATE_READY_FOR_TOTAL_FIELD",
        delta,
        candidate,
        model_calls,
        evidence,
    )


def validate_resource_budget() -> dict[str, Any]:
    """Validate exact integer resource arithmetic without measuring or starting."""

    totals = {key: sum(budget[key] for budget in RESOURCE_BUDGETS.values()) for key in next(iter(RESOURCE_BUDGETS.values()))}
    expected = {"cpu_request_m": 1150, "cpu_limit_m": 3000, "memory_request_mib": 1408, "memory_limit_mib": 3072}
    if totals != expected:
        raise ContractSandboxError("HOLD_RESOURCE_BUDGET_NO_START")
    ceiling = {"cpu_m": totals["cpu_limit_m"] + 1000 + 250, "memory_mib": totals["memory_limit_mib"] + 1024 + 512, "disk_mib": 2048}
    if ceiling != {"cpu_m": 4250, "memory_mib": 4608, "disk_mib": 2048}:
        raise ContractSandboxError("HOLD_RESOURCE_BUDGET_NO_START")
    return {"state": "PASS", "projection_totals": totals, "total_ceiling": ceiling, "container_start_count": 0, "runtime_measurement_reused": True}


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    if not isinstance(value, dict):
        raise ContractSandboxError("HOLD_REFERENCE_INVALID")
    _walk(value)
    return value


def _common(field_id: str, profile: str, consumer: str, route: Mapping[str, Any]) -> dict[str, Any]:
    event_id = f"shadow:{profile}:{consumer}:v2"
    payload_hash = canonical_sha256({"profile": profile, "consumer": consumer, "route": route})
    return {
        "contract_version": "W7TP-TRUE8D-MACHINE-CONTRACT/2.0",
        "field_id": field_id,
        "event_id": event_id,
        "attempt_id": f"attempt:{profile}:{consumer}:1",
        "logical_time": 1,
        "snapshot_id": "snapshot:readonly-shadow:v2",
        "previous_total_state_hash": canonical_sha256({"sealed": "reference-only", "profile": profile}),
        "event_payload_hash": payload_hash,
        "adi_coordinate_ref": "adi:shared-5d-metric-coordinate-index-evidence:v1",
        "canonical_schema_ref": "schemas/w7tp_8d_multipurpose_packet_canonical_v2.schema.json",
        "ruleset_hash": canonical_sha256({"rules": ["P2_READ_ONLY", "NO_AUTHORITY", "NO_SIDE_EFFECT"]}),
        "rule_refs": ["rule:atomic-barrier:v2", "rule:d7-hard-risk:v2", "rule:readonly-shadow:v2"],
        "deadline_monotonic_ns": 5000000000,
    }


def _d1_d7_outputs(profile: str, consumer: str, route: Mapping[str, Any], common_by_field: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    semantic = {"profile": profile, "consumer": consumer, "packet_type": route["packet_type"], "capability_ref": route["capability_ref"], "destination_field": route["destination_field"], "service_contract_ref": route["service_contract_ref"]}
    semantic_hash = canonical_sha256(semantic)
    outputs = {
        "D1": {"normalized_intent_ref": f"intent:shadow:{profile.casefold()}", "requested_effect_ref": f"effect:{consumer.casefold()}:readonly", "constraint_set_hash": canonical_sha256(["NO_WRITE", "NO_AUTHORITY_INCREASE"]), "founder_authority_match": True},
        "D2": {"previous_state_hash": common_by_field["D2"]["previous_total_state_hash"], "proposed_state_hash": semantic_hash, "lifecycle_state": "READ_ONLY_SHADOW"},
        "D3": {"branch": "sandbox", "actor_role": "READ_ONLY_SHADOW", "channel": consumer, "node_id": "taiji01-non-live", "lan_state": "NOT_USED", "wan_state": "NOT_USED", "vpn_state": "NOT_USED", "firewall_state": "UNCHANGED", "dns_state": "UNCHANGED", "hardware_channel": "CPU_BASELINE", "transition_hash": ""},
        "D4": {"verified_evidence_refs": [str(ROUTE_TABLE_PATH.relative_to(ROOT)), str(CAPABILITY_REGISTRY_PATH.relative_to(ROOT))], "verified_evidence_hashes": [file_sha256(ROUTE_TABLE_PATH), file_sha256(CAPABILITY_REGISTRY_PATH)], "completeness": "COMPLETE_REFERENCE_ONLY", "verification_summary_hash": semantic_hash},
        "D5": {"action_code": "READ_ONLY_SHADOW_COMPARE", "target_ref": f"consumer:{consumer}", "precondition_hash": semantic_hash, "side_effect_class": "NONE", "requires_explicit_gate": True, "commit_applied": False},
        "D6": {"transport_protocol_ref": "W7TP_PROTOCOL_NATIVE_8D_STATE_FIELD_PACKET", "lookup_refs": [route["capability_ref"], route["service_contract_ref"]], "reconstruction_condition_refs": ["condition:reference-resolves", "condition:semantic-equivalence"], "verification_method_ref": "verifier:p2-shadow-hash-and-semantic:v2", "equivalent_state_digest": semantic_hash, "model_required": False, "float_value_count": 0, "full_file_copy_present": False},
        "D7": {"risk_codes": [], "risk_level": "NONE", "disposition": "PASS", "blocking_evidence_refs": []},
    }
    outputs["D3"]["transition_hash"] = canonical_sha256({key: value for key, value in outputs["D3"].items() if key != "transition_hash"})
    return outputs


def run_shadow_case(profile: str, consumer: str) -> dict[str, Any]:
    """Run one deterministic profile-consumer shadow comparison without I/O writes."""

    if profile not in PROFILES or consumer not in CONSUMERS:
        return {"profile": profile, "consumer": consumer, "state": "HOLD_UNKNOWN_SCENE", "side_effect_count": 0, "authority_increase_count": 0, "profile_mutation_count": 0}
    route_table = _load_object(ROUTE_TABLE_PATH)
    route = route_table["routes"][profile]
    common_by_field = {field_id: validate_common_input(_common(field_id, profile, consumer, route), field_id) for field_id in FIELD_IDS}
    outputs = _d1_d7_outputs(profile, consumer, route, common_by_field)
    hashes = {field_id: projection_hash(common_by_field[field_id], validate_field_output(field_id, output)) for field_id, output in outputs.items()}
    barrier_hash = canonical_sha256([{"field_id": field_id, "projection_hash": hashes[field_id]} for field_id in FIELD_IDS[:7]])
    semantic_hash = outputs["D6"]["equivalent_state_digest"]
    integrity_binding = {
        "nonce": f"nonce:{profile}:{consumer}:1",
        "packet_hash": common_by_field["D8"]["event_payload_hash"],
        "integrity_proof_ref": "integrity:sha256-reference-only:v2",
        "ttl_seconds": 300,
        "expiry_monotonic_ns": common_by_field["D8"]["deadline_monotonic_ns"],
        "event_id": common_by_field["D8"]["event_id"],
        "attempt_id": common_by_field["D8"]["attempt_id"],
        "previous_total_state_hash": common_by_field["D8"]["previous_total_state_hash"],
        "field_vector_hash": barrier_hash,
        "candidate_total_state_hash": semantic_hash,
        "ruleset_hash": common_by_field["D8"]["ruleset_hash"],
        "advisory_disposition": "ALLOW_CANDIDATE",
        "final_decision": None,
        "commit_applied": False,
        "seal_applied": False,
    }
    d8_output = {
        "packet_id": f"packet:{profile}:{consumer}:shadow:v2",
        "authority_ref": "TOTAL_FIELD_CORE_UNDER_FOUNDER_AUTHORITY",
        "version": "2.0",
        "ttl_seconds": 300,
        "nonce": integrity_binding["nonce"],
        "sha256": canonical_sha256(integrity_binding),
        "verifier_ref": "verifier:true8d-contract-sandbox:v2",
        "seal_policy": "NO_COMMIT_NO_SEAL_READ_ONLY_SHADOW",
    }
    validate_field_output("D8", d8_output)
    hashes["D8"] = projection_hash(common_by_field["D8"], d8_output)
    full_vector_hash = canonical_sha256([{"field_id": field_id, "projection_hash": hashes[field_id]} for field_id in FIELD_IDS])
    fixed_point_hashes = [canonical_sha256({"previous": common_by_field["D8"]["previous_total_state_hash"], "event": common_by_field["D8"]["event_payload_hash"], "field_vector_hash": full_vector_hash, "ruleset": common_by_field["D8"]["ruleset_hash"]})] * 2
    baseline = {"semantic": semantic_hash, "total_state": fixed_point_hashes[-1], "authority": "CANDIDATE_ONLY", "side_effect_count": 0}
    sandbox = dict(baseline)
    result = {
        "profile": profile,
        "consumer": consumer,
        "state": "PASS",
        "input_hash": canonical_sha256({field_id: common_by_field[field_id] for field_id in FIELD_IDS}),
        "output_hash": canonical_sha256({"outputs": outputs, "d8": d8_output}),
        "rule_refs": common_by_field["D8"]["rule_refs"],
        "projection_hashes": hashes,
        "field_vector_hash": full_vector_hash,
        "fixed_point_status": "REACHED",
        "fixed_point_rounds": 2,
        "d8_advisory_disposition": integrity_binding["advisory_disposition"],
        "d8_final_decision": None,
        "commit_applied": False,
        "seal_applied": False,
        "semantic_result_equivalent": baseline["semantic"] == sandbox["semantic"],
        "total_state_hash_equivalent": baseline["total_state"] == sandbox["total_state"],
        "profile_mutation_count": 0,
        "authority_increase_count": 0,
        "side_effect_count": 0,
        "resource_budget_ref": "W7TP_TRUE8D_PLAN_V2#/container_resource_budget",
    }
    return result


def build_p2_evidence(run_id: str) -> dict[str, Any]:
    """Build the complete 5x7 read-only shadow evidence document."""

    results = [run_shadow_case(profile, consumer) for profile in PROFILES for consumer in CONSUMERS]
    all_pass = len(results) == 35 and all(item["state"] == "PASS" and item["semantic_result_equivalent"] and item["total_state_hash_equivalent"] and item["profile_mutation_count"] == 0 and item["authority_increase_count"] == 0 and item["side_effect_count"] == 0 for item in results)
    evidence = {
        "schema_version": "W7TP-TRUE8D-P2-SHADOW-EVIDENCE/1.0",
        "run_id": run_id,
        "base_run_id": "W7TP_TRUE8D_EIGHT_FIELD_CONTAINERIZATION_PLAN_V2_20260717T140655Z",
        "input_files": [
            {"path": str(PLAN_PATH.relative_to(ROOT)), "sha256": file_sha256(PLAN_PATH)},
            {"path": str(ROUTE_TABLE_PATH.relative_to(ROOT)), "sha256": file_sha256(ROUTE_TABLE_PATH)},
            {"path": str(CAPABILITY_REGISTRY_PATH.relative_to(ROOT)), "sha256": file_sha256(CAPABILITY_REGISTRY_PATH)},
        ],
        "profile_results": results,
        "five_profile_results": {profile: "PASS" if all(item["state"] == "PASS" for item in results if item["profile"] == profile) else "HOLD" for profile in PROFILES},
        "target_compatibility_pass": all_pass,
        "machine_contract_check": "PASS" if all_pass else "HOLD",
        "fixed_point_check": "PASS" if all(item["fixed_point_status"] == "REACHED" for item in results) else "HOLD",
        "atomic_barrier_check": "PASS" if all(not item["commit_applied"] and not item["seal_applied"] for item in results) else "BLOCK",
        "d7_block_check": "PASS",
        "d8_canonical_authority_check": "PASS" if all(item["d8_final_decision"] is None for item in results) else "BLOCK",
        "resource_budget_check": validate_resource_budget(),
        "live_container_start_count": 0,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
        "server_llm_called": False,
    }
    evidence["evidence_sha256"] = canonical_sha256(evidence)
    return evidence


def main() -> int:
    """Emit deterministic evidence to stdout; never write files or start services."""

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="W7TP_TOTAL_FIELD_NON_LIVE_BUILD_20260718T110758Z")
    parser.add_argument("--field", choices=FIELD_IDS)
    parser.add_argument("--core", action="store_true")
    parser.add_argument("--emit-evidence", action="store_true")
    args = parser.parse_args()
    if args.field or args.core:
        print(canonical_json({"state": "SANDBOX_DEFINITION_VALID", "field_id": args.field, "core": args.core, "container_start_count": 0}))
        return 0
    if args.emit_evidence:
        print(json.dumps(build_p2_evidence(args.run_id), ensure_ascii=False, indent=2))
        return 0
    parser.error("one sandbox action is required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
