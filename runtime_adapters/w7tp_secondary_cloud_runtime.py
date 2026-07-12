#!/usr/bin/env python3
"""Taiji01-local runtime integration for W7TP secondary-cloud packets.

The capability connector is dependency-injected.  The default connector has no
credentials and performs no external network call.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping, Protocol

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "runtime/total_field/secondary_cloud/capability_registry.json"
REQUEST_SCHEMA_PATH = ROOT / "schemas/w7tp_secondary_cloud_runtime_request.schema.json"
RAMP_PATH = ROOT / "tools/w7tp_secondary_cloud_packet_ramp.py"
RUNTIME_PATH = "/w7tp/secondary-cloud/runtime"
AUTO_CLOUD_CALL = "FORBIDDEN"
EXECUTION_CHAIN = [
    "SOURCE",
    "PACKET",
    "CAPABILITY_REF_RESOLVE",
    "PULL_CAPABILITY_PACKET",
    "LOCAL_RECONSTRUCT",
    "LOCAL_COMPARE",
    "VERIFY",
    "HOLD_OR_SEAL",
]
CHANNELS = {"OWNER_XIAOJ", "TOTAL_FIELD"}
CREDENTIAL_KEYS = {
    "access_token",
    "api_key",
    "client_secret",
    "credential",
    "credential_json",
    "password",
    "private_key",
    "private_key_id",
    "raw_key",
    "raw_token",
    "refresh_token",
    "service_account_key_file",
    "token",
}


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"MODULE_LOAD_FAILED:{name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ramp = _load_module("w7tp_secondary_cloud_packet_ramp_runtime", RAMP_PATH)


class CapabilityConnector(Protocol):
    """Connector boundary for a later credentialed implementation."""

    def readiness(self) -> Mapping[str, Any]: ...

    def pull_capability(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...


class CredentialNotProvisionedConnector:
    """Safe default connector: no credential inspection and no network."""

    def readiness(self) -> Mapping[str, Any]:
        return {
            "state": "HOLD_CREDENTIAL_NOT_PROVISIONED",
            "adc_check": "HOLD_CREDENTIAL_NOT_PROVISIONED",
            "live_connection": False,
        }

    def pull_capability(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        raise RuntimeError("AUTO_CLOUD_CALL_FORBIDDEN")


def _request_errors(request: Mapping[str, Any]) -> list[str]:
    schema = json.loads(REQUEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = Draft202012Validator(schema).iter_errors(request)
    return [
        f"RUNTIME_REQUEST:{'.'.join(str(part) for part in error.path) or '$'}:{error.validator}"
        for error in sorted(errors, key=lambda item: list(item.path))
    ]


def _forbidden_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            child_path = f"{path}.{key}"
            if normalized in ramp.FORBIDDEN_UPLINK_KEYS or normalized in CREDENTIAL_KEYS:
                found.append(child_path)
            found.extend(_forbidden_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_forbidden_paths(child, f"{path}[{index}]"))
    return found


def _hold(
    state: str,
    errors: list[str],
    *,
    channel: str | None,
    candidate_request: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "state": state,
        "current_stage": "HOLD",
        "channel": channel,
        "execution_chain": list(EXECUTION_CHAIN),
        "auto_cloud_call": AUTO_CLOUD_CALL,
        "candidate_request": copy.deepcopy(dict(candidate_request)) if candidate_request else None,
        "execution_authority": False,
        "verification_required": True,
        "xiaoj_started": False,
        "owner_identity_used": False,
        "member_identity_used": False,
        "external_network_called": False,
        "seal_status": "NOT_SEALED",
        "errors": errors,
    }


def resolve_capability_ref(capability_ref: str) -> dict[str, Any]:
    """Resolve exactly one capability from the committed taiji01 registry."""

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    matches = [
        capability
        for capability in registry.get("capabilities", [])
        if capability.get("capability_ref") == capability_ref
    ]
    if len(matches) != 1:
        return {"state": "HOLD", "errors": ["CAPABILITY_REF_NOT_UNIQUE"]}
    return {"state": "PASS", "errors": [], "capability": copy.deepcopy(matches[0])}


def _connector_capability_errors(
    request: Mapping[str, Any], capability_packet: Mapping[str, Any]
) -> list[str]:
    comparisons = {
        "capability_ref": request.get("capability_ref") == capability_packet.get("capability_ref"),
        "packet_type": request.get("packet_type") == capability_packet.get("packet_type"),
        "domain_code": request.get("domain_code") == capability_packet.get("domain_code"),
        "language_code": request.get("language_code") == capability_packet.get("language_code"),
        "compatibility_profile": request.get("compatibility_profile")
        == capability_packet.get("compatibility_profile"),
    }
    return [f"CAPABILITY_RETURN_MISMATCH:{key}" for key, matched in comparisons.items() if not matched]


def run_secondary_cloud_runtime(
    request: Mapping[str, Any], connector: CapabilityConnector | None = None
) -> dict[str, Any]:
    """Run the fixed packet chain with reconstruction and verification local."""

    if not isinstance(request, Mapping):
        return _hold(
            "HOLD_REQUEST_REJECTED",
            ["RUNTIME_REQUEST:$:type"],
            channel=None,
        )
    request_copy = copy.deepcopy(dict(request))
    channel = request_copy.get("channel")
    errors = _request_errors(request_copy)
    errors.extend(f"FORBIDDEN_RUNTIME_FIELD:{path}" for path in _forbidden_paths(request_copy))
    if errors:
        return _hold("HOLD_REQUEST_REJECTED", errors, channel=channel)
    if channel == "OWNER_XIAOJ" and request_copy["owner_explicit_authorization"] is not True:
        return _hold(
            "HOLD_OWNER_AUTHORIZATION_REQUIRED",
            ["OWNER_EXPLICIT_AUTHORIZATION_REQUIRED"],
            channel=channel,
        )

    registry_result = resolve_capability_ref(request_copy["capability_ref"])
    if registry_result["state"] != "PASS":
        return _hold("HOLD_CAPABILITY_REF", registry_result["errors"], channel=channel)
    if (
        registry_result["capability"].get("compatibility_profile")
        != request_copy["compatibility_profile"]
    ):
        return _hold(
            "HOLD_CAPABILITY_REF",
            ["CAPABILITY_COMPATIBILITY_MISMATCH"],
            channel=channel,
        )

    candidate_request = ramp.build_capability_pull_request(
        request_copy["capability_id"],
        request_copy["packet_type"],
        request_copy["domain_code"],
        request_copy["language_code"],
        request_copy["compatibility_profile"],
        request_copy["request_nonce"],
        capability_ref=request_copy["capability_ref"],
    )
    if candidate_request.get("state") == "HOLD":
        return _hold(
            "HOLD_CAPABILITY_PULL_REQUEST",
            list(candidate_request.get("errors", [])),
            channel=channel,
        )
    disclosure = ramp.validate_no_uplink_plaintext(candidate_request, require_minimal_pull=True)
    if disclosure["state"] != "PASS":
        return _hold(
            "HOLD_MINIMAL_DISCLOSURE",
            list(disclosure["errors"]),
            channel=channel,
            candidate_request=candidate_request,
        )

    active_connector = connector or CredentialNotProvisionedConnector()
    readiness = dict(active_connector.readiness())
    if readiness.get("state") != "PASS":
        state = str(readiness.get("state") or "HOLD_CREDENTIAL_NOT_PROVISIONED")
        return _hold(state, [state], channel=channel, candidate_request=candidate_request)

    connector_result = dict(active_connector.pull_capability(copy.deepcopy(candidate_request)))
    if connector_result.get("state") != "PASS" or not isinstance(
        connector_result.get("capability_packet"), Mapping
    ):
        return _hold(
            "HOLD_CAPABILITY_PACKET",
            list(connector_result.get("errors", ["CAPABILITY_PACKET_NOT_RETURNED"])),
            channel=channel,
            candidate_request=candidate_request,
        )
    capability_packet = copy.deepcopy(dict(connector_result["capability_packet"]))
    return_errors = _connector_capability_errors(candidate_request, capability_packet)
    if return_errors:
        return _hold(
            "HOLD_CAPABILITY_PACKET",
            return_errors,
            channel=channel,
            candidate_request=candidate_request,
        )

    reconstruction = ramp.reconstruct_local_state(
        request_copy["scenario_translation_packet"], capability_packet
    )
    audit = ramp.run_multilayer_audit(
        member_entry_packet=request_copy["member_entry_packet"],
        identity_authority_packet=request_copy["identity_authority_packet"],
        scenario_translation_packet=request_copy["scenario_translation_packet"],
        capability_pull_request_packet=candidate_request,
        capability_packet=capability_packet,
        local_reconstruction_packet=reconstruction,
    )
    verification = ramp.produce_verification_packet(
        run_id=request_copy["run_id"],
        scenario_translation_packet=request_copy["scenario_translation_packet"],
        local_reconstruction_packet=reconstruction,
        audit_result=audit,
    )
    active_questions = request_copy["active_question_refs"]
    if active_questions:
        verification["state"] = "HOLD"
        verification["current_stage"] = "HOLD"
        verification["verification_result"] = "UNVERIFIED"
        verification["seal_status"] = "NOT_SEALED"
        verification["sha256"] = ramp.packet_content_sha256(verification)

    sealed = (
        verification.get("verification_result") == "VERIFIED"
        and not active_questions
        and verification.get("seal_status") == "SEALED"
    )
    return {
        "state": "PASS" if sealed else "HOLD",
        "current_stage": "SEAL" if sealed else "HOLD",
        "channel": channel,
        "execution_chain": list(EXECUTION_CHAIN),
        "auto_cloud_call": AUTO_CLOUD_CALL,
        "candidate_request": candidate_request,
        "execution_authority": False,
        "verification_required": True,
        "xiaoj_started": False,
        "owner_identity_used": False,
        "member_identity_used": False,
        "external_network_called": False,
        "reconstruction": reconstruction,
        "verification": verification,
        "seal_status": verification["seal_status"],
        "errors": [] if sealed else ["LOCAL_VERIFICATION_OR_SEAL_GATE_HOLD"],
    }


__all__ = [
    "AUTO_CLOUD_CALL",
    "CredentialNotProvisionedConnector",
    "EXECUTION_CHAIN",
    "RUNTIME_PATH",
    "resolve_capability_ref",
    "run_secondary_cloud_runtime",
]
