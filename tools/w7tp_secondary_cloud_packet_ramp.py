#!/usr/bin/env python3
"""Deterministic W7TP packet-native ramp for the taiji01 secondary cloud.

The module accepts references and protocol packets only.  It performs no network,
database, deployment, router, or service-control operation.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
ROUTE_TABLE_PATH = ROOT / "runtime/total_field/secondary_cloud/scenario_route_table.json"

CLOUD_MODE = "PULL_PACKET_ONLY"
MEMBER_UPLOAD = "DENY"
RECONSTRUCTION_LOCATION = "TAIJI01_LOCAL"
VERIFICATION_LOCATION = "LOCAL_OR_TOTAL_FIELD"
PACKET_PROTOCOL = "W7TP-8D-PACKET-NATIVE/1.0"
PULL_PROTOCOL = "W7TP-PULL-PACKET-ONLY/1.0"

CONTAINERS = {"ASSOCIATION", "PROPERTY", "CAFE_POS", "HOUSEHOLD", "GENERIC"}
MINIMAL_PULL_FIELDS = {
    "capability_id",
    "capability_ref",
    "packet_type",
    "schema_version",
    "domain_code",
    "language_code",
    "compatibility_profile",
    "request_nonce",
    "return_protocol",
}
FORBIDDEN_UPLINK_KEYS = {
    "name",
    "member_name",
    "full_name",
    "phone",
    "telephone",
    "mobile",
    "address",
    "email",
    "identity_plaintext",
    "member_plaintext",
    "full_intent",
    "intent_text",
    "local_context",
    "local_state",
    "database_replica",
    "database_content",
    "private_core",
    "raw_key",
    "raw_token",
    "password",
}

SCHEMA_FILES = {
    "member_entry": "w7tp_member_entry_packet.schema.json",
    "identity_authority": "w7tp_identity_authority_packet.schema.json",
    "scenario_translation": "w7tp_scenario_translation_packet.schema.json",
    "capability_pull": "w7tp_capability_pull_request_packet.schema.json",
    "capability": "w7tp_capability_packet.schema.json",
    "local_reconstruction": "w7tp_local_reconstruction_packet.schema.json",
    "verification": "w7tp_secondary_cloud_verification_packet.schema.json",
}


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def deterministic_sha256(value: Any) -> str:
    """Return a real SHA256 over canonical JSON content."""

    return hashlib.sha256(_canonical_json(value)).hexdigest()


def packet_content_sha256(packet: Mapping[str, Any]) -> str:
    """Hash packet content while excluding the field that carries the digest."""

    content = copy.deepcopy(dict(packet))
    content.pop("sha256", None)
    envelope = content.get("d8_envelope")
    if isinstance(envelope, dict):
        envelope.pop("sha256", None)
    return deterministic_sha256(content)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_errors(schema_key: str, packet: Mapping[str, Any]) -> list[str]:
    schema = _load_json(SCHEMA_DIR / SCHEMA_FILES[schema_key])
    errors = Draft202012Validator(schema).iter_errors(packet)
    return [
        f"{schema_key}:{'.'.join(str(part) for part in error.path) or '$'}:{error.validator}"
        for error in sorted(errors, key=lambda item: list(item.path))
    ]


def _decision(errors: Sequence[str], **values: Any) -> dict[str, Any]:
    result = {"state": "HOLD" if errors else "PASS", "errors": list(errors)}
    result.update(values)
    return result


def _unsafe_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            child_path = f"{path}.{key}"
            if normalized in FORBIDDEN_UPLINK_KEYS:
                found.append(child_path)
            found.extend(_unsafe_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_unsafe_paths(child, f"{path}[{index}]"))
    return found


def validate_no_uplink_plaintext(
    packet: Mapping[str, Any], *, require_minimal_pull: bool = False
) -> dict[str, Any]:
    """Reject member plaintext, complete intent, local state, and secret-bearing keys."""

    errors = [f"FORBIDDEN_UPLINK_FIELD:{path}" for path in _unsafe_paths(packet)]
    if require_minimal_pull and set(packet) != MINIMAL_PULL_FIELDS:
        errors.append("CAPABILITY_PULL_NOT_MINIMAL")
    return _decision(errors, disclosed_fields=sorted(packet))


def validate_member_entry_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a member entrance envelope without accepting member plaintext."""

    errors = _schema_errors("member_entry", packet)
    errors.extend(validate_no_uplink_plaintext(packet)["errors"])
    envelope = packet.get("envelope", {})
    if envelope.get("consent_state") == "DENIED":
        errors.append("CONSENT_DENIED")
    if envelope.get("revocation_state") == "REVOKED":
        errors.append("IDENTITY_REVOKED")
    return _decision(errors, packet_id=packet.get("packet_id"))


def resolve_identity_authority(
    member_entry_packet: Mapping[str, Any],
    identity_authority_packet: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve existing authority references; this function never elevates authority."""

    errors = validate_member_entry_packet(member_entry_packet)["errors"]
    errors.extend(_schema_errors("identity_authority", identity_authority_packet))
    envelope = member_entry_packet.get("envelope", {})
    comparisons = {
        "identity_ref": member_entry_packet.get("identity_ref")
        == identity_authority_packet.get("identity_ref"),
        "scenario_ref": member_entry_packet.get("scenario_ref")
        == identity_authority_packet.get("scenario_ref"),
        "device_binding_ref": member_entry_packet.get("device_binding_ref")
        == identity_authority_packet.get("device_binding_ref"),
        "authority_scope": set(envelope.get("authority_scope", []))
        <= set(identity_authority_packet.get("authority_scope", [])),
    }
    errors.extend(f"AUTHORITY_MISMATCH:{key}" for key, matched in comparisons.items() if not matched)
    if identity_authority_packet.get("consent_state") == "DENIED":
        errors.append("CONSENT_DENIED")
    if identity_authority_packet.get("revocation_state") != "CLEAR":
        errors.append("IDENTITY_REVOKED")
    if identity_authority_packet.get("envelope_verified") is not True:
        errors.append("IDENTITY_ENVELOPE_UNVERIFIED")
    return _decision(
        errors,
        identity_ref=identity_authority_packet.get("identity_ref"),
        role_refs=identity_authority_packet.get("role_refs", []),
        authority_scope=identity_authority_packet.get("authority_scope", []),
    )


def resolve_scenario_container(
    scenario_ref: str, route_table: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Resolve one scenario reference against the fixed five-container route table."""

    table = dict(route_table) if route_table is not None else _load_json(ROUTE_TABLE_PATH)
    matches = [
        (container, route)
        for container, route in table.get("routes", {}).items()
        if scenario_ref in route.get("scenario_refs", [])
    ]
    if len(matches) != 1:
        return _decision(["SCENARIO_ROUTE_NOT_UNIQUE"], scenario_ref=scenario_ref)
    container, route = matches[0]
    errors = [] if container in CONTAINERS else ["UNSUPPORTED_CONTAINER"]
    return _decision(
        errors,
        scenario_ref=scenario_ref,
        selected_container=container,
        packet_type=route.get("packet_type"),
        capability_ref=route.get("capability_ref"),
        destination_field=route.get("destination_field"),
        service_contract_ref=route.get("service_contract_ref"),
    )


def build_capability_pull_request(
    capability_id: str,
    packet_type: str,
    domain_code: str,
    language_code: str,
    compatibility_profile: str,
    request_nonce: str,
    *,
    capability_ref: str | None = None,
) -> dict[str, Any]:
    """Build the only payload permitted to leave taiji01 for capability pulling."""

    packet = {
        "capability_id": capability_id,
        "capability_ref": capability_ref or capability_id,
        "packet_type": packet_type,
        "schema_version": "W7TP-CAPABILITY-PULL/1.0",
        "domain_code": domain_code,
        "language_code": language_code,
        "compatibility_profile": compatibility_profile,
        "request_nonce": request_nonce,
        "return_protocol": PULL_PROTOCOL,
    }
    errors = _schema_errors("capability_pull", packet)
    errors.extend(validate_no_uplink_plaintext(packet, require_minimal_pull=True)["errors"])
    if errors:
        return _decision(errors, packet=packet)
    return packet


def reconstruct_local_state(
    scenario_translation_packet: Mapping[str, Any],
    capability_packet: Mapping[str, Any],
    *,
    comparison_result: str | None = None,
) -> dict[str, Any]:
    """Reconstruct only the packet-required result at taiji01."""

    errors = _schema_errors("scenario_translation", scenario_translation_packet)
    errors.extend(_schema_errors("capability", capability_packet))
    mode = capability_packet.get("reconstruction_spec", {}).get("mode")
    allowed_comparisons = {
        "L1_FULL": {"MATCH"},
        "L2_EQUIVALENT": {"MATCH", "EQUIVALENT"},
        "L3_CANDIDATE": {"CANDIDATE"},
    }
    if comparison_result is None:
        comparison_result = {
            "L1_FULL": "MATCH",
            "L2_EQUIVALENT": "EQUIVALENT",
            "L3_CANDIDATE": "CANDIDATE",
        }.get(mode, "MISMATCH")
    if comparison_result not in allowed_comparisons.get(mode, set()):
        errors.append("RECONSTRUCTION_COMPARISON_INVALID")

    seed = {
        "source_packet_id": scenario_translation_packet.get("packet_id"),
        "capability_ref": capability_packet.get("capability_ref"),
        "mode": mode,
        "effect_contract_ref": capability_packet.get("reconstruction_spec", {}).get(
            "effect_contract_ref"
        ),
        "comparison_result": comparison_result,
    }
    candidate_only = mode == "L3_CANDIDATE"
    local_verified = not errors and not candidate_only and comparison_result != "MISMATCH"
    packet = {
        "packet_id": f"RECON-{deterministic_sha256(seed)[:20]}",
        "schema_version": "W7TP-LOCAL-RECONSTRUCTION/1.0",
        "source_packet_id": scenario_translation_packet.get("packet_id"),
        "capability_ref": capability_packet.get("capability_ref"),
        "reconstruction_location": RECONSTRUCTION_LOCATION,
        "mode": mode,
        "result_ref": f"local-result:{deterministic_sha256(seed)[:24]}",
        "effect_contract_ref": seed["effect_contract_ref"],
        "comparison_result": comparison_result,
        "local_verified": local_verified,
        "candidate_only": candidate_only,
    }
    packet["sha256"] = packet_content_sha256(packet)
    packet_errors = _schema_errors("local_reconstruction", packet)
    if errors or packet_errors:
        packet["local_verified"] = False
        packet["errors"] = errors + packet_errors
    return packet


def _layer(layer: str, errors: Sequence[str], evidence: Sequence[str]) -> dict[str, Any]:
    return {
        "layer": layer,
        "state": "HOLD" if errors else "PASS",
        "evidence": list(errors) if errors else list(evidence),
    }


def run_multilayer_audit(
    *,
    member_entry_packet: Mapping[str, Any],
    identity_authority_packet: Mapping[str, Any],
    scenario_translation_packet: Mapping[str, Any],
    capability_pull_request_packet: Mapping[str, Any],
    capability_packet: Mapping[str, Any],
    local_reconstruction_packet: Mapping[str, Any],
    route_table: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run deterministic L1-L8 audits and HOLD on missing or conflicting evidence."""

    schema_errors: list[str] = []
    for key, packet in (
        ("member_entry", member_entry_packet),
        ("identity_authority", identity_authority_packet),
        ("scenario_translation", scenario_translation_packet),
        ("capability_pull", capability_pull_request_packet),
        ("capability", capability_packet),
        ("local_reconstruction", local_reconstruction_packet),
    ):
        schema_errors.extend(_schema_errors(key, packet))

    authority = resolve_identity_authority(member_entry_packet, identity_authority_packet)
    route = resolve_scenario_container(member_entry_packet.get("scenario_ref", ""), route_table)
    route_errors = list(route["errors"])
    for key in ("selected_container", "packet_type", "capability_ref", "destination_field"):
        if route.get(key) != scenario_translation_packet.get(key):
            route_errors.append(f"ROUTE_MISMATCH:{key}")

    minimal = validate_no_uplink_plaintext(
        capability_pull_request_packet, require_minimal_pull=True
    )
    evidence_errors: list[str] = []
    evidence = scenario_translation_packet.get("d4_evidence", {})
    if not evidence.get("evidence_refs") or not evidence.get("evidence_hashes"):
        evidence_errors.append("EVIDENCE_INCOMPLETE")
    if not capability_packet.get("source_refs") or not capability_packet.get("payload_refs"):
        evidence_errors.append("CAPABILITY_REFERENCES_INCOMPLETE")
    if capability_packet.get("sha256") != packet_content_sha256(capability_packet):
        evidence_errors.append("CAPABILITY_SHA256_MISMATCH")

    reconstruction_errors: list[str] = []
    if local_reconstruction_packet.get("reconstruction_location") != RECONSTRUCTION_LOCATION:
        reconstruction_errors.append("RECONSTRUCTION_NOT_LOCAL")
    if local_reconstruction_packet.get("sha256") != packet_content_sha256(
        local_reconstruction_packet
    ):
        reconstruction_errors.append("RECONSTRUCTION_SHA256_MISMATCH")
    if local_reconstruction_packet.get("candidate_only") is True:
        reconstruction_errors.append("CANDIDATE_REQUIRES_LOCAL_STATE_MACHINE")
    if local_reconstruction_packet.get("local_verified") is not True:
        reconstruction_errors.append("LOCAL_RECONSTRUCTION_UNVERIFIED")

    boundary_errors = list(validate_no_uplink_plaintext(capability_pull_request_packet)["errors"])
    if capability_pull_request_packet.get("return_protocol") != PULL_PROTOCOL:
        boundary_errors.append("NOT_PULL_PACKET_ONLY")
    if scenario_translation_packet.get("d3_coordinate", {}).get("node_ref") != "taiji01":
        boundary_errors.append("LOCAL_NODE_BOUNDARY_VIOLATION")

    envelope_errors: list[str] = []
    envelope = scenario_translation_packet.get("d8_envelope", {})
    if envelope.get("protocol") != PACKET_PROTOCOL:
        envelope_errors.append("PACKET_PROTOCOL_MISSING")
    if not isinstance(envelope.get("ttl_seconds"), int) or envelope.get("ttl_seconds", 0) <= 0:
        envelope_errors.append("TTL_INVALID")
    if len(str(envelope.get("nonce", ""))) < 8:
        envelope_errors.append("NONCE_INVALID")
    if envelope.get("sha256") != packet_content_sha256(scenario_translation_packet):
        envelope_errors.append("ENVELOPE_SHA256_MISMATCH")
    if not envelope.get("verifier_ref"):
        envelope_errors.append("VERIFIER_MISSING")

    layers = [
        _layer("L1_SCHEMA_VERSION", schema_errors, ["ALL_PACKET_SCHEMAS_VALID"]),
        _layer("L2_IDENTITY_AUTHORITY", authority["errors"], ["IDENTITY_AUTHORITY_VERIFIED"]),
        _layer("L3_SCENARIO_DESTINATION", route_errors, ["SCENARIO_ROUTE_VERIFIED"]),
        _layer("L4_CAPABILITY_MINIMAL_DISCLOSURE", minimal["errors"], ["NINE_FIELDS_ONLY"]),
        _layer("L5_REFERENCE_EVIDENCE", evidence_errors, ["REFERENCES_AND_HASHES_PRESENT"]),
        _layer("L6_RECONSTRUCTION_EQUIVALENCE", reconstruction_errors, ["LOCAL_EFFECT_VERIFIED"]),
        _layer("L7_NO_UPLINK_LOCAL_BOUNDARY", boundary_errors, ["PULL_ONLY_LOCAL_BOUNDARY_VERIFIED"]),
        _layer("L8_ENVELOPE_SEAL", envelope_errors, ["ENVELOPE_HASH_TTL_NONCE_VERIFIED"]),
    ]
    state = "PASS" if all(layer["state"] == "PASS" for layer in layers) else "HOLD"
    return {"state": state, "layers": layers}


def produce_verification_packet(
    *,
    run_id: str,
    scenario_translation_packet: Mapping[str, Any],
    local_reconstruction_packet: Mapping[str, Any],
    audit_result: Mapping[str, Any],
    confidence_basis: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Produce the stable JSON contract used to replace frontend mock state."""

    can_seal = (
        audit_result.get("state") == "PASS"
        and local_reconstruction_packet.get("local_verified") is True
        and local_reconstruction_packet.get("candidate_only") is False
    )
    confidence: float | None = None
    if confidence_basis is not None:
        passed = confidence_basis.get("passed_checks")
        total = confidence_basis.get("total_checks")
        if isinstance(passed, int) and isinstance(total, int) and total > 0 and 0 <= passed <= total:
            confidence = round((passed / total) * 100, 2)

    evidence_refs = list(
        scenario_translation_packet.get("d4_evidence", {}).get("evidence_refs", [])
    )
    evidence_refs.append(f"local-reconstruction:{local_reconstruction_packet.get('packet_id')}")
    packet = {
        "state": "PASS" if can_seal else "HOLD",
        "run_id": run_id,
        "packet_id": scenario_translation_packet.get("packet_id"),
        "selected_container": scenario_translation_packet.get("selected_container"),
        "packet_type": scenario_translation_packet.get("packet_type"),
        "capability_ref": scenario_translation_packet.get("capability_ref"),
        "current_stage": "SEAL" if can_seal else "HOLD",
        "verification_result": "VERIFIED" if can_seal else "UNVERIFIED",
        "evidence_refs": evidence_refs,
        "seal_status": "SEALED" if can_seal else "NOT_SEALED",
        "confidence": confidence,
        "cloud_mode": CLOUD_MODE,
        "member_upload": MEMBER_UPLOAD,
        "reconstruct": RECONSTRUCTION_LOCATION,
        "verify": VERIFICATION_LOCATION,
        "audit_layers": list(audit_result.get("layers", [])),
    }
    packet["sha256"] = packet_content_sha256(packet)
    schema_errors = _schema_errors("verification", packet)
    if schema_errors:
        packet["state"] = "HOLD"
        packet["current_stage"] = "HOLD"
        packet["verification_result"] = "REJECTED"
        packet["seal_status"] = "NOT_SEALED"
        packet["sha256"] = packet_content_sha256(packet)
    return packet


__all__ = [
    "build_capability_pull_request",
    "deterministic_sha256",
    "packet_content_sha256",
    "produce_verification_packet",
    "reconstruct_local_state",
    "resolve_identity_authority",
    "resolve_scenario_container",
    "run_multilayer_audit",
    "validate_member_entry_packet",
    "validate_no_uplink_plaintext",
]
