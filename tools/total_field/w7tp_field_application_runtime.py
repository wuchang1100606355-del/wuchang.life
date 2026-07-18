#!/usr/bin/env python3
"""Local W7TP field-application packet runtime.

The runtime reads the existing scenario route table and capability registry,
then constructs one deterministic protocol-native 8D candidate packet. It
does not call cloud services or perform any persistent/external side effect.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
# The installed release invokes this file by path. In that mode Python places
# tools/total_field, not the release root, on sys.path; add the content-addressed
# release root so the single shared suite remains directly executable without
# relying on a caller-provided PYTHONPATH.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCENARIO_ROUTE_TABLE_PATH = (
    ROOT / "runtime/total_field/secondary_cloud/scenario_route_table.json"
)
CAPABILITY_REGISTRY_PATH = (
    ROOT / "runtime/total_field/secondary_cloud/capability_registry.json"
)
SCENARIO_TOKEN = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")

SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "credential",
        "member_plaintext",
        "model_context",
        "model_weights",
        "password",
        "private_key",
        "raw_credential",
        "raw_llm_prompt",
        "raw_prompt",
        "raw_secret",
        "raw_token",
        "secret",
        "system_prompt",
        "token",
    }
)
AUTHORITY_KEYS = frozenset(
    {
        "admin_override",
        "authority_escalation_attempt",
        "cloud_model_authorized",
        "commit_applied",
        "d8_decision",
        "final_decision",
        "formal_execution_authority",
        "founder_command_ref",
        "google_account_binding_ref",
        "llm_execution_location",
        "local_founder_id",
        "server_llm_execution",
        "server_model_authority",
    }
)
SIDE_EFFECTS = {
    "secret_read": False,
    "member_plaintext": False,
    "network_call": False,
    "db_write": False,
    "deploy": False,
    "restart": False,
    "router_write": False,
    "formal_submission": False,
}


def device_llm_execution_policy() -> dict[str, str]:
    """Return the immutable split between device inference and Total Field.

    The shared server may validate a user-confirmed, minimized intent candidate;
    it is never an LLM inference host and never accepts model context or weights.
    """

    return {
        "llm_inference_location": "USER_DEVICE_ONLY",
        "server_llm_execution": "BLOCK",
        "server_role": "TOTAL_FIELD_VALIDATION_HASH_AND_SEAL_ONLY",
        "device_output": "USER_CONFIRMED_MINIMIZED_INTENT_CANDIDATE",
        "server_input": "MINIMIZED_INTENT_CANDIDATE_AND_EVIDENCE_REFS_ONLY",
        "raw_prompt_upload": "BLOCK",
        "model_context_upload": "BLOCK",
        "model_weights_upload": "BLOCK",
        "fallback": "USER_DEVICE_LOCAL_QUEUE_OR_USER_DECISION",
    }


class FieldApplicationError(ValueError):
    """Stable local rejection that never includes caller data."""

    def __init__(self, reason_code: str, path: str = "$") -> None:
        self.reason_code = reason_code
        self.path = path
        super().__init__(f"{reason_code}:{path}")


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise FieldApplicationError("JSON_VALUE_INVALID") from exc


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _load_json_object(path: Path, reason_code: str) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise FieldApplicationError(reason_code) from exc
    if not isinstance(value, dict):
        raise FieldApplicationError(reason_code)
    return value


def parse_intent(value: str) -> dict[str, Any]:
    if not isinstance(value, str) or not value.strip():
        raise FieldApplicationError("INTENT_JSON_REQUIRED")
    try:
        parsed = json.loads(
            value,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise FieldApplicationError("INTENT_JSON_INVALID") from exc
    if not isinstance(parsed, dict):
        raise FieldApplicationError("INTENT_OBJECT_REQUIRED")
    canonical_json(parsed)
    return parsed


def _protected_key_path(
    value: Any,
    protected: frozenset[str],
    path: str = "$",
) -> str | None:
    if isinstance(value, Mapping):
        for key in sorted(value, key=str):
            normalized = str(key).strip().casefold()
            child = f"{path}.{key}"
            if normalized in protected:
                return child
            found = _protected_key_path(value[key], protected, child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found = _protected_key_path(item, protected, f"{path}[{index}]")
            if found is not None:
                return found
    return None


def _validate_intent_boundaries(intent: Mapping[str, Any]) -> None:
    sensitive_path = _protected_key_path(intent, SENSITIVE_KEYS)
    if sensitive_path is not None:
        raise FieldApplicationError("SENSITIVE_INTENT_BLOCKED", sensitive_path)
    authority_path = _protected_key_path(intent, AUTHORITY_KEYS)
    if authority_path is not None:
        raise FieldApplicationError("AUTHORITY_ESCALATION_BLOCKED", authority_path)


def _resolve_route_and_capability(
    scenario: str,
    route_table: Mapping[str, Any],
    capability_registry: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(scenario, str) or not SCENARIO_TOKEN.fullmatch(scenario):
        raise FieldApplicationError("SCENARIO_TOKEN_INVALID")
    routes = route_table.get("routes")
    if not isinstance(routes, dict):
        raise FieldApplicationError("SCENARIO_ROUTE_TABLE_INVALID")
    route = routes.get(scenario)
    if not isinstance(route, dict):
        raise FieldApplicationError("SCENARIO_NOT_REGISTERED")
    capability_ref = route.get("capability_ref")
    if not isinstance(capability_ref, str) or not capability_ref:
        raise FieldApplicationError("SCENARIO_CAPABILITY_REF_INVALID")

    capabilities = capability_registry.get("capabilities")
    if not isinstance(capabilities, list):
        raise FieldApplicationError("CAPABILITY_REGISTRY_INVALID")
    matched = [
        item
        for item in capabilities
        if isinstance(item, dict) and item.get("capability_ref") == capability_ref
    ]
    if len(matched) != 1:
        raise FieldApplicationError("SCENARIO_CAPABILITY_REGISTRY_MISMATCH")
    return json.loads(canonical_json(route)), json.loads(canonical_json(matched[0]))


def load_authoritative_route_and_capability(
    scenario: str,
    *,
    route_table_path: Path = SCENARIO_ROUTE_TABLE_PATH,
    capability_registry_path: Path = CAPABILITY_REGISTRY_PATH,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Read and resolve the two authoritative sources for one profile.

    This public helper lets the shared product layer perform guided completion
    only after the route and capability have been proven. It does not create a
    fallback table or mutate either source.
    """

    route_table = _load_json_object(
        route_table_path,
        "SCENARIO_ROUTE_TABLE_READ_FAILED",
    )
    capability_registry = _load_json_object(
        capability_registry_path,
        "CAPABILITY_REGISTRY_READ_FAILED",
    )
    route, capability = _resolve_route_and_capability(
        scenario,
        route_table,
        capability_registry,
    )
    return route, capability, route_table, capability_registry


def build_field_application_packet(
    scenario: str,
    intent: Mapping[str, Any],
    *,
    route_table_path: Path = SCENARIO_ROUTE_TABLE_PATH,
    capability_registry_path: Path = CAPABILITY_REGISTRY_PATH,
) -> dict[str, Any]:
    """Build one candidate-only packet from existing registered field state."""

    if not isinstance(intent, Mapping):
        raise FieldApplicationError("INTENT_OBJECT_REQUIRED")
    intent_copy = json.loads(canonical_json(dict(intent)))
    _validate_intent_boundaries(intent_copy)
    route, capability, route_table, capability_registry = (
        load_authoritative_route_and_capability(
        scenario,
        route_table_path=route_table_path,
        capability_registry_path=capability_registry_path,
        )
    )
    intent_sha256 = canonical_sha256(intent_copy)

    packet: dict[str, Any] = {
        "schema_version": "W7TP-FIELD-APPLICATION-PACKET/1.0",
        "D1": {
            "intent": "BUILD_FIELD_APPLICATION_CANDIDATE",
            "scenario": scenario,
            "requested_result": intent_copy.get("requested_result", "LOCAL_REVIEW_CANDIDATE"),
        },
        "D2": {
            "state": "CANDIDATE",
            "intent_sha256": intent_sha256,
            "intent": intent_copy,
        },
        "D3": {
            "node_ref": route_table.get("node_ref"),
            "scenario_ref": f"scenario:{scenario}",
            "packet_type": route.get("packet_type"),
            "destination_field": route.get("destination_field"),
        },
        "D4": {
            "capability_ref": route.get("capability_ref"),
            "capability_version": capability.get("version"),
            "packet_schema_ref": capability.get("packet_schema"),
            "source_refs": capability.get("source_refs", []),
            "route_table_sha256": canonical_sha256(route_table),
            "capability_registry_sha256": canonical_sha256(capability_registry),
        },
        "D5": {
            "execution": "LOCAL_TOTAL_FIELD_REVIEW",
            "candidate_only": True,
            "cpu_baseline": "CPU_BASELINE_CONTINUES",
            "gpu_support": "OPTIONAL_NON_LLM_ACCELERATION_ONLY",
            "llm_execution": device_llm_execution_policy(),
            "side_effects": dict(SIDE_EFFECTS),
        },
        "D6": {
            "generative_transmission": "PROTOCOL_NATIVE_8D_STATE_FIELD_PACKET",
            "references": True,
            "lookup": True,
            "reconstruction_conditions": {
                "scenario_route_match": True,
                "capability_registry_match": True,
                "equivalence_level": "L3_CANDIDATE",
            },
            "equivalent_state_generation": True,
            "packet_carried_protocol": True,
            "packet_carried_validation": True,
            "total_field_verification": True,
        },
        "D7": {
            "risk_status": "CLEAR_PRELIMINARY",
            "sensitive_input": "BLOCK",
            "authority_escalation": "BLOCK",
            "server_llm_execution": "BLOCK",
            "raw_prompt_or_model_context_upload": "BLOCK",
            "unknown_scenario": "BLOCK",
            "registry_mismatch": "BLOCK",
        },
        "D8": {
            "packet_identity": f"w7tp-field-application:{scenario}:{intent_sha256}",
            "authority": "LOCAL_TOTAL_FIELD_ONLY",
            "decision": "PENDING_TOTAL_FIELD_REVIEW",
            "candidate_only": True,
            "service_contract_ref": route.get("service_contract_ref"),
            "cloud_model_auto_enabled": False,
            "server_model_authority": "NONE",
        },
    }
    packet["packet_sha256"] = canonical_sha256(packet)
    return packet


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "suite":
        from tools.total_field.w7tp_intent_field_suite.cli import main as suite_main

        return suite_main(argv[1:])
    parser = argparse.ArgumentParser(description="W7TP local field-application packet runtime")
    parser.add_argument("scenario")
    parser.add_argument("intent_json")
    args = parser.parse_args(argv)
    try:
        intent = parse_intent(args.intent_json)
        result = build_field_application_packet(args.scenario, intent)
    except FieldApplicationError as exc:
        print(
            canonical_json(
                {
                    "state": "BLOCK",
                    "reason_code": exc.reason_code,
                    "path": exc.path,
                    "side_effects": dict(SIDE_EFFECTS),
                }
            )
        )
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
