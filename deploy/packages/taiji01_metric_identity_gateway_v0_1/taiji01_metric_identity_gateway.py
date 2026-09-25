#!/usr/bin/env python3
"""Taiji01 metric identity gateway.

This is an Ollama-compatible local proxy for node taiji01.  It is intentionally
small and dependency-free so it can run in a container or directly on Linux.
It does not store prompts; audit records contain only hashes and routing facts.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

try:
    from runtime_adapters.sovereign_ai_candidate_intake import (
        INTAKE_PATH as MEMBER_TOTAL_FIELD_CANDIDATE_PATH,
        MAX_REQUEST_BYTES as MEMBER_TOTAL_FIELD_CANDIDATE_MAX_BYTES,
        run_sovereign_ai_candidate_intake,
    )
except ModuleNotFoundError:
    repository_root = Path(__file__).resolve().parents[3]
    if str(repository_root) not in sys.path:
        sys.path.insert(0, str(repository_root))
    from runtime_adapters.sovereign_ai_candidate_intake import (
        INTAKE_PATH as MEMBER_TOTAL_FIELD_CANDIDATE_PATH,
        MAX_REQUEST_BYTES as MEMBER_TOTAL_FIELD_CANDIDATE_MAX_BYTES,
        run_sovereign_ai_candidate_intake,
    )


VERSION = "taiji01_metric_identity_gateway_v0_1"
MEMBER_SOVEREIGN_SCHEMA_VERSION = "W7TP-MEMBER-SOVEREIGN-8D/1.0"
MEMBER_AUTHORIZATION_SCHEMA_VERSION = "W7TP-MEMBER-AUTHORIZATION/1.0"
MEMBER_GOVERNANCE_SCHEMA_VERSION = "W7TP-MEMBER-GOVERNANCE-EVENT/1.0"
IDENTITY_STATES = {"anonymous", "authenticated", "registered", "suspended", "revoked"}
SUBJECT_TYPES = {
    "visitor",
    "resident",
    "supporter",
    "association_member",
    "volunteer",
    "association_staff",
    "merchant_owner",
    "merchant_staff",
    "property_or_committee_actor",
    "system_operator",
}
CONSENT_STATES = {
    "not_requested",
    "pending",
    "granted",
    "partially_granted",
    "withdrawn",
    "expired",
}
AUTHORIZATION_SCOPES = {
    "profile_reference",
    "membership_status_reference",
    "service_area_reference",
    "volunteer_status_reference",
    "merchant_role_reference",
    "communication_permission",
    "data_access_request",
    "anonymized_research_permission",
    "sovereign_ai_candidate_submission",
}
PROVIDER_LINK_DENY_STATES = {
    "LINKING_PENDING",
    "REAUTHENTICATION_REQUIRED",
    "EXPLICIT_LINK_CONSENT_REQUIRED",
    "HUMAN_REVIEW_REQUIRED",
    "LINK_DENIED",
}
PROVIDER_LINK_ALLOW_STATES = {"PROVIDER_LINK_FOUND", "LINK_CONFIRMED"}
PRIVILEGED_NATURAL_PERSON_ASSURANCE_PREFIXES = {
    "usage_pattern": "assurance:usage-pattern:sha256:",
    "login_location": "assurance:login-location:sha256:",
    "trusted_device": "assurance:trusted-device:sha256:",
    "connection_pattern": "assurance:connection-pattern:sha256:",
}
FORBIDDEN_MEMBER_FIELDS = {
    "national_id",
    "identity_number",
    "full_name",
    "birth_date",
    "full_address",
    "full_phone",
    "private_email",
    "oauth_token",
    "cookie_secret",
    "service_account_key",
    "raw_member_record",
    "password",
    "raw_image",
    "image_bytes",
    "video_frame",
    "face_image",
    "selfie",
    "biometric_template",
}
AUDIT_LOCK = threading.Lock()
LOCAL_PRIVILEGED_MEMBER_VERIFIER = None
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def env(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


ROOT = Path(env("TAIJI_ROOT", "/home/taiji_01/Taiji_Hub"))
TARGET = env("TAIJI_OLLAMA_TARGET", "http://127.0.0.1:11434").rstrip("/")
ALLOWED_MODELS = {
    item.strip()
    for item in env("TAIJI_ALLOWED_MODELS", "metric-language-gateway-ai:latest").split(",")
    if item.strip()
}
ALLOWLIST_PATH = Path(
    env(
        "TAIJI_IDENTITY_ALLOWLIST",
        str(ROOT / "deploy/packages/taiji01_metric_identity_gateway_v0_1/identity_allowlist.json"),
    )
)
AUDIT_PATH = Path(
    env(
        "TAIJI_GATEWAY_AUDIT_LOG",
        str(ROOT / "Taiji_Governance/logs/taiji01_metric_identity_gateway.jsonl"),
    )
)
REQUIRE_FIVE_CODE_HASH = env("TAIJI_REQUIRE_FIVE_CODE_HASH", "false").lower() in {
    "1",
    "true",
    "yes",
}
MEMORY_REFS = [
    ROOT / "data/f5_core_memory.db",
    ROOT / "data/wuchang_5d_knowledge_vault.db",
    ROOT / "data/ledger/metric_memory.sqlite3",
]


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_hash(value: Any) -> str:
    return sha256_text(canonical_json(value))


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _forbidden_member_paths(value: Any, prefix: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if str(key).lower() in FORBIDDEN_MEMBER_FIELDS:
                findings.append(path)
            findings.extend(_forbidden_member_paths(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(_forbidden_member_paths(item, f"{prefix}[{index}]"))
    return findings


def subject_proxy_ref(local_source_ref: str) -> str:
    if not local_source_ref or len(local_source_ref) > 256:
        raise ValueError("local_source_ref_required")
    return "subject:sha256:" + sha256_text(f"taiji01-member-sovereign:{local_source_ref}")


def _packet_hash_payload(packet: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(canonical_json(packet))
    payload.get("D8_ENVELOPE", {}).pop("hash", None)
    return payload


def issue_member_sovereign_packet(authority: dict[str, Any]) -> dict[str, Any]:
    """Issue a reference-only 8D packet from already verified local authority facts."""
    forbidden = _forbidden_member_paths(authority)
    if forbidden:
        raise ValueError("member_plaintext_forbidden:" + ",".join(forbidden))
    identity_state = str(authority.get("identity_state") or "")
    consent_state = str(authority.get("consent_state") or "")
    subject_types = sorted(set(authority.get("subject_types") or []))
    scopes = sorted(set(authority.get("authorization_scopes") or []))
    if identity_state not in IDENTITY_STATES:
        raise ValueError("invalid_identity_state")
    if consent_state not in CONSENT_STATES:
        raise ValueError("invalid_consent_state")
    if not subject_types or not set(subject_types).issubset(SUBJECT_TYPES):
        raise ValueError("invalid_subject_types")
    if not set(scopes).issubset(AUTHORIZATION_SCOPES):
        raise ValueError("invalid_authorization_scopes")
    required_refs = (
        "local_source_ref",
        "issuer",
        "purpose",
        "service_scope",
        "target_system",
        "issued_at",
        "expires_at",
        "nonce",
        "local_state_check_ref",
    )
    missing = [key for key in required_refs if not authority.get(key)]
    if missing:
        raise ValueError("missing_authority_fields:" + ",".join(missing))
    if not str(authority["issuer"]).startswith("taiji01:"):
        raise ValueError("local_issuer_required")
    if not str(authority["local_source_ref"]).startswith(("odoo:", "anonymous:")):
        raise ValueError("odoo_or_anonymous_source_ref_required")
    issued_at = str(authority["issued_at"])
    expires_at = str(authority["expires_at"])
    if _parse_time(expires_at) <= _parse_time(issued_at):
        raise ValueError("invalid_validity_window")
    if identity_state != "anonymous" and not authority.get("consent_record_ref"):
        raise ValueError("consent_record_ref_required")
    subject_ref = subject_proxy_ref(str(authority["local_source_ref"]))
    packet_id = "member8d:" + canonical_hash(
        {
            "subject_ref": subject_ref,
            "purpose": authority["purpose"],
            "target_system": authority["target_system"],
            "issued_at": issued_at,
            "nonce": authority["nonce"],
        }
    )
    packet: dict[str, Any] = {
        "D1_INTENT": {
            "purpose": str(authority["purpose"]),
            "requested_result": "identity_or_qualification_reference",
        },
        "D2_STATE": {
            "identity_state": identity_state,
            "subject_types": subject_types,
            "role_refs": sorted(set(authority.get("role_refs") or [])),
            "qualification_states": authority.get("qualification_states") or {},
            "consent_state": consent_state,
            "authorization_scopes": scopes,
        },
        "D3_COORDINATE": {
            "subject_ref": subject_ref,
            "issuer": str(authority["issuer"]),
            "service_scope": str(authority["service_scope"]),
            "target_system": str(authority["target_system"]),
            "valid_from": issued_at,
            "valid_until": expires_at,
        },
        "D4_EVIDENCE": {
            "local_qualification_source_refs": sorted(set(authority.get("qualification_source_refs") or [])),
            "consent_record_ref": authority.get("consent_record_ref"),
            "local_state_check_ref": str(authority["local_state_check_ref"]),
            "identity_verifier_result": "verified_local_reference",
            "verified_at": str(authority.get("verified_at") or issued_at),
        },
        "D5_EXECUTION": {
            "allowed_actions": ["allow", "deny", "hold", "require_reauthentication", "require_human_review"],
            "decision": "hold",
            "decision_reason": "downstream_request_and_current_authority_state_required",
        },
        "D6_GENERATIVE_TRANSMISSION": {
            "protocol": "protocol_native_8d_intent_field_packet",
            "reconstruction_condition": "reconstruct_only_required_reference_state",
            "verification_level": "L2_equivalent_task_state_control_effect",
            "equivalent_state_condition": "same_subject_proxy_scope_consent_and_expiry",
            "member_plaintext_included": False,
            "file_transfer_semantics": False,
            "cloud_invocation_allowed": False,
        },
        "D7_RISK": {
            "flags": [],
            "evaluated_risks": [
                "plaintext_exposure",
                "expired_consent",
                "scope_mismatch",
                "identity_conflict",
                "unauthorized_downstream_access",
                "human_review_required",
            ],
        },
        "D8_ENVELOPE": {
            "packet_id": packet_id,
            "issuer": str(authority["issuer"]),
            "issued_at": issued_at,
            "expires_at": expires_at,
            "nonce": str(authority["nonce"]),
            "schema_version": MEMBER_SOVEREIGN_SCHEMA_VERSION,
            "signature_or_local_verification_reference": str(authority["local_state_check_ref"]),
        },
    }
    packet["D8_ENVELOPE"]["hash"] = "sha256:" + canonical_hash(_packet_hash_payload(packet))
    return packet


def validate_member_sovereign_packet(packet: dict[str, Any], now: str | None = None) -> list[str]:
    errors: list[str] = []
    forbidden = _forbidden_member_paths(packet)
    if forbidden:
        errors.append("plaintext_exposure:" + ",".join(forbidden))
    required_dimensions = [f"D{i}_{name}" for i, name in enumerate(
        ("INTENT", "STATE", "COORDINATE", "EVIDENCE", "EXECUTION", "GENERATIVE_TRANSMISSION", "RISK", "ENVELOPE"),
        start=1,
    )]
    errors.extend(f"missing_dimension:{key}" for key in required_dimensions if not isinstance(packet.get(key), dict))
    if errors:
        return errors
    state = packet["D2_STATE"]
    envelope = packet["D8_ENVELOPE"]
    if state.get("identity_state") not in IDENTITY_STATES:
        errors.append("invalid_identity_state")
    if state.get("consent_state") not in CONSENT_STATES:
        errors.append("invalid_consent_state")
    if not set(state.get("subject_types") or []).issubset(SUBJECT_TYPES):
        errors.append("invalid_subject_types")
    if not set(state.get("authorization_scopes") or []).issubset(AUTHORIZATION_SCOPES):
        errors.append("invalid_authorization_scopes")
    if envelope.get("schema_version") != MEMBER_SOVEREIGN_SCHEMA_VERSION:
        errors.append("invalid_schema_version")
    expected_hash = "sha256:" + canonical_hash(_packet_hash_payload(packet))
    if envelope.get("hash") != expected_hash:
        errors.append("packet_tampering_detected")
    if envelope.get("issuer") != packet["D3_COORDINATE"].get("issuer"):
        errors.append("issuer_mismatch")
    try:
        if _parse_time(str(envelope.get("expires_at"))) <= _parse_time(str(envelope.get("issued_at"))):
            errors.append("invalid_validity_window")
        if now and _parse_time(str(envelope.get("expires_at"))) <= _parse_time(now):
            errors.append("packet_expired")
    except (TypeError, ValueError):
        errors.append("invalid_time")
    if packet["D6_GENERATIVE_TRANSMISSION"].get("member_plaintext_included") is not False:
        errors.append("plaintext_exposure")
    if packet["D6_GENERATIVE_TRANSMISSION"].get("cloud_invocation_allowed") is not False:
        errors.append("cloud_auto_invoke_forbidden")
    return sorted(set(errors))


def evaluate_member_authorization(
    packet: dict[str, Any], request_state: dict[str, Any], now: str
) -> dict[str, Any]:
    errors = validate_member_sovereign_packet(packet, now=now)
    if errors:
        reason = "packet_tampering_detected" if "packet_tampering_detected" in errors else errors[0]
        return authorization_decision("deny", reason, packet, [], now)
    state = packet["D2_STATE"]
    coordinate = packet["D3_COORDINATE"]
    evidence = packet["D4_EVIDENCE"]
    requested_scopes = sorted(set(request_state.get("requested_scopes") or []))
    if not set(requested_scopes).issubset(AUTHORIZATION_SCOPES):
        return authorization_decision("deny", "invalid_requested_scope", packet, [], now)
    if request_state.get("target_system") != coordinate.get("target_system"):
        return authorization_decision("deny", "target_system_mismatch", packet, [], now)
    if request_state.get("purpose") != packet["D1_INTENT"].get("purpose"):
        return authorization_decision("deny", "purpose_mismatch", packet, [], now)
    provider_link_state = request_state.get("provider_link_state")
    if provider_link_state in PROVIDER_LINK_DENY_STATES:
        return authorization_decision(
            "deny", f"provider_link_{provider_link_state.lower()}", packet, [], now
        )
    if provider_link_state and provider_link_state not in PROVIDER_LINK_ALLOW_STATES:
        return authorization_decision("deny", "provider_link_state_invalid", packet, [], now)
    identity_state = state.get("identity_state")
    if identity_state == "revoked":
        return authorization_decision("deny", "identity_revoked", packet, [], now)
    if identity_state == "suspended":
        return authorization_decision("require_human_review", "identity_suspended", packet, [], now)
    if identity_state == "anonymous":
        if requested_scopes or request_state.get("purpose") != "anonymous_public_service":
            return authorization_decision("deny", "anonymous_privilege_forbidden", packet, [], now)
        return authorization_decision("allow", "anonymous_limited_entry", packet, [], now)
    current = request_state.get("current_authority_state")
    if not isinstance(current, dict):
        return authorization_decision("hold", "current_authority_state_check_required", packet, [], now)
    if current.get("consent_record_ref") != evidence.get("consent_record_ref"):
        return authorization_decision("deny", "consent_reference_mismatch", packet, [], now)
    current_consent = current.get("consent_state")
    if current_consent == "withdrawn":
        return authorization_decision("deny", "consent_withdrawn", packet, [], now)
    if current_consent == "expired":
        return authorization_decision("deny", "consent_expired", packet, [], now)
    if current_consent not in {"granted", "partially_granted"}:
        return authorization_decision("deny", "consent_not_granted", packet, [], now)
    if current.get("identity_state") in {"revoked", "suspended"}:
        action = "deny" if current.get("identity_state") == "revoked" else "require_human_review"
        return authorization_decision(action, f"identity_{current.get('identity_state')}", packet, [], now)
    if not set(requested_scopes).issubset(set(state.get("authorization_scopes") or [])):
        return authorization_decision("deny", "scope_mismatch", packet, [], now)
    return authorization_decision("allow", "minimum_disclosure_authorized", packet, requested_scopes, now)


def authorization_decision(
    decision: str,
    reason: str,
    packet: dict[str, Any],
    scopes: list[str],
    decided_at: str,
) -> dict[str, Any]:
    envelope = packet.get("D8_ENVELOPE") or {}
    state = packet.get("D2_STATE") or {}
    coordinate = packet.get("D3_COORDINATE") or {}
    evidence = packet.get("D4_EVIDENCE") or {}
    disclosed = {}
    if decision == "allow":
        disclosed = {
            "subject_ref": coordinate.get("subject_ref"),
            "role_refs": state.get("role_refs") or [],
            "qualification_states": state.get("qualification_states") or {},
            "authorization_scopes": scopes,
            "valid_until": envelope.get("expires_at"),
            "source_refs": evidence.get("local_qualification_source_refs") or [],
            "verifier_result": "PASS",
        }
    result = {
        "schema_version": MEMBER_AUTHORIZATION_SCHEMA_VERSION,
        "packet_id": envelope.get("packet_id"),
        "decision": decision,
        "reason": reason,
        "decided_at": decided_at,
        "minimum_disclosure": disclosed,
        "member_plaintext_included": False,
        "cloud_invoked": False,
    }
    result["decision_hash"] = "sha256:" + canonical_hash(result)
    return result


def member_api_public_response(
    authorization: dict[str, Any],
    packet: dict[str, Any],
    provider_link_state: str,
) -> dict[str, Any]:
    """Map an internal decision to the fixed public minimum-disclosure contract."""
    state = packet.get("D2_STATE") or {}
    coordinate = packet.get("D3_COORDINATE") or {}
    envelope = packet.get("D8_ENVELOPE") or {}
    minimum = authorization.get("minimum_disclosure") or {}
    decision = str(authorization.get("decision") or "deny").upper()
    if provider_link_state in PROVIDER_LINK_DENY_STATES:
        decision = "DENY"
    elif provider_link_state not in PROVIDER_LINK_ALLOW_STATES:
        decision = "DENY"
    elif decision != "ALLOW":
        decision = "DENY"
    roles = state.get("role_refs") or []
    return {
        "subject_reference": coordinate.get("subject_ref"),
        "provider_link_state": provider_link_state,
        "identity_state": state.get("identity_state"),
        "necessary_role": roles[0] if roles else None,
        "qualification_status": state.get("qualification_states") or {},
        "granted_scope": minimum.get("authorization_scopes") or [],
        "decision": decision,
        "issued_at": envelope.get("issued_at"),
        "expires_at": envelope.get("expires_at"),
        "verifier_result": "PASS" if decision == "ALLOW" else "BLOCK",
    }


def classify_data_export(request_state: dict[str, Any]) -> tuple[str, str]:
    request_type = request_state.get("request_type")
    if request_type == "MEMBER_ACCESS_REQUEST":
        if request_state.get("requester_subject_ref") != request_state.get("subject_ref"):
            return "deny", "member_subject_mismatch"
        return "allow", "member_controlled_access"
    if request_type == "AUTHORITY_REQUEST":
        if not request_state.get("human_confirmed") or not request_state.get("legal_case_ref"):
            return "require_human_review", "legal_authority_and_human_confirmation_required"
        return "allow", "authority_request_governance_complete"
    if request_type == "DEIDENTIFIED_RESEARCH":
        if not request_state.get("deidentified") or not request_state.get("research_permission_ref"):
            return "deny", "deidentification_and_permission_required"
        return "allow", "deidentified_research_only"
    return "deny", "unsupported_data_export_type"


def governance_event(
    actor_ref: str,
    action: str,
    reason: str,
    scope: str,
    source_ref: str | None,
    previous_state_hash: str,
    logical_time: str,
    verifier_result: str,
) -> dict[str, Any]:
    event = {
        "schema_version": MEMBER_GOVERNANCE_SCHEMA_VERSION,
        "actor_ref": actor_ref,
        "action": action,
        "reason": reason,
        "scope": scope,
        "source_ref": source_ref,
        "previous_state_hash": previous_state_hash,
        "logical_time": logical_time,
        "verifier_result": verifier_result,
    }
    if _forbidden_member_paths(event):
        raise ValueError("member_plaintext_forbidden")
    event["resulting_state_hash"] = "sha256:" + canonical_hash(event)
    return event


def verify_governance_chain(events: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    previous = "sha256:" + ("0" * 64)
    for index, event in enumerate(events):
        if event.get("previous_state_hash") != previous:
            errors.append(f"chain_link_mismatch:{index}")
        candidate = dict(event)
        recorded = candidate.pop("resulting_state_hash", None)
        expected = "sha256:" + canonical_hash(candidate)
        if recorded != expected:
            errors.append(f"event_tampering_detected:{index}")
        previous = str(recorded or "")
    return errors


def load_allowlist() -> dict[str, Any]:
    if not ALLOWLIST_PATH.exists():
        return {"nodes": []}
    try:
        return json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"nodes": []}


def ip_matches(client_ip: str, patterns: list[str]) -> bool:
    try:
        ip = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    for pattern in patterns:
        pattern = pattern.strip()
        if not pattern:
            continue
        try:
            if "/" in pattern:
                if ip in ipaddress.ip_network(pattern, strict=False):
                    return True
            elif ip == ipaddress.ip_address(pattern):
                return True
        except ValueError:
            continue
    return False


def authorize(client_ip: str, supplied_hash: str | None) -> tuple[bool, str, str | None]:
    allowlist = load_allowlist()
    nodes = allowlist.get("nodes") or []
    for node in nodes:
        allowed_ips = node.get("allowed_ips") or []
        if not ip_matches(client_ip, allowed_ips):
            continue
        node_id = str(node.get("node_id") or "unnamed_node")
        expected_hash = str(node.get("five_code_sha256") or "").replace("sha256:", "")
        if REQUIRE_FIVE_CODE_HASH and expected_hash:
            if supplied_hash and supplied_hash.replace("sha256:", "") == expected_hash:
                return True, "allow_ip_and_five_code_hash", node_id
            return False, "five_code_hash_required", node_id
        return True, "allow_device_mapped_identity", node_id
    return False, "client_not_allowlisted", None


def memory_ref_state() -> dict[str, Any]:
    refs = []
    for path in MEMORY_REFS:
        refs.append({"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path), "exists": path.exists()})
    return {"count": sum(1 for item in refs if item["exists"]), "refs": refs}


def audit(record: dict[str, Any]) -> None:
    timestamp = now_iso()
    client_ip = str(record.pop("client_ip", ""))
    actor_ref = "node:" + str(record.get("node_id") or "unmapped")
    if client_ip:
        actor_ref += ":ip_sha256:" + sha256_text(client_ip)
    record = {"ts": timestamp, "gateway": VERSION, **record}
    try:
        with AUDIT_LOCK:
            AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
            previous = "sha256:" + ("0" * 64)
            if AUDIT_PATH.exists():
                with AUDIT_PATH.open("rb") as existing:
                    existing.seek(0, os.SEEK_END)
                    size = existing.tell()
                    existing.seek(max(0, size - 65536))
                    lines = existing.read().decode("utf-8", errors="ignore").splitlines()
                for line in reversed(lines):
                    try:
                        candidate = json.loads(line).get("governance_event") or {}
                    except json.JSONDecodeError:
                        continue
                    if candidate.get("resulting_state_hash"):
                        previous = str(candidate["resulting_state_hash"])
                        break
            event = governance_event(
                actor_ref=actor_ref,
                action="gateway_request",
                reason=str(record.get("reason") or "unspecified"),
                scope=str(record.get("path") or "gateway"),
                source_ref="sha256:" + canonical_hash(record),
                previous_state_hash=previous,
                logical_time=timestamp,
                verifier_result="PASS" if record.get("allowed") else "BLOCK",
            )
            record["governance_event"] = event
            with AUDIT_PATH.open("a", encoding="utf-8") as handle:
                handle.write(canonical_json(record) + "\n")
    except Exception:
        return


def parse_model(body: bytes) -> str | None:
    if not body:
        return None
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return None
    model = payload.get("model")
    return str(model) if model else None


def block_payload(body: bytes) -> str | None:
    if not body:
        return None
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return None
    text = json.dumps(payload, ensure_ascii=False).lower()
    if '"payment_allowed": true' in text:
        return "payment_allowed_true_blocked"
    if '"plaintext_context_stored": true' in text:
        return "plaintext_context_stored_true_blocked"
    return None


def verify_privileged_member_locally(
    packet: dict[str, Any], request_state: dict[str, Any], now: str
) -> dict[str, str]:
    """Require a process-local authority verifier; never trust a laptop assertion."""

    verifier = LOCAL_PRIVILEGED_MEMBER_VERIFIER
    if not callable(verifier):
        return {
            "decision": "hold",
            "reason": "local_natural_person_authority_verifier_not_bound",
        }
    result = verifier(packet, request_state, now)
    if not isinstance(result, dict):
        return {"decision": "hold", "reason": "local_verifier_result_invalid"}
    decision = str(result.get("decision") or "hold").lower()
    evidence_ref = str(result.get("evidence_ref") or "")
    digest = evidence_ref.rsplit(":", 1)[-1]
    valid_digest = len(digest) == 64 and all(
        char in "0123456789abcdef" for char in digest
    )
    if decision == "allow":
        if (
            result.get("verifier_result") == "PASS"
            and evidence_ref.startswith("authority-verifier:sha256:")
            and valid_digest
        ):
            return {
                "decision": "allow",
                "reason": str(result.get("reason") or "natural_person_authority_verified"),
                "evidence_ref": evidence_ref,
            }
        return {"decision": "hold", "reason": "positive_authority_evidence_incomplete"}
    if decision == "block":
        if (
            result.get("verifier_result") == "BLOCK"
            and evidence_ref.startswith("red-team-contradiction:sha256:")
            and valid_digest
        ):
            return {
                "decision": "block",
                "reason": str(result.get("reason") or "red_team_proven_not_subject"),
                "evidence_ref": evidence_ref,
            }
        return {"decision": "hold", "reason": "red_team_contradiction_evidence_required"}
    if decision in {"step_up", "require_reauthentication"}:
        if result.get("step_up_method") == "w7tp_privacy_preserving_no_retention_image":
            return {
                "decision": "hold",
                "reason": "privacy_preserving_image_reverification_required",
                "step_up_method": "w7tp_privacy_preserving_no_retention_image",
            }
        return {"decision": "hold", "reason": "step_up_method_not_verified"}
    return {
        "decision": "hold",
        "reason": str(result.get("reason") or "identity_or_authority_not_converged"),
    }


def member_total_field_candidate_intake(
    payload: dict[str, Any], now: str
) -> dict[str, Any]:
    """Authorize one member reference before candidate-only Total Field intake."""

    required = {"schema_version", "packet", "request_state", "candidate_request"}
    if set(payload) != required:
        raise ValueError("member_candidate_bridge_keys_invalid")
    if payload.get("schema_version") != "w7tp-member-sovereign-candidate-bridge/0.1":
        raise ValueError("member_candidate_bridge_schema_invalid")
    packet = payload.get("packet")
    request_state = payload.get("request_state")
    candidate_request = payload.get("candidate_request")
    if not isinstance(packet, dict):
        raise ValueError("member_packet_required")
    if not isinstance(request_state, dict):
        raise ValueError("member_request_state_required")
    if not isinstance(candidate_request, dict):
        raise ValueError("candidate_request_required")
    if request_state.get("purpose") != "sovereign_ai_candidate_submission":
        raise ValueError("candidate_submission_purpose_required")
    if request_state.get("target_system") != "total_field_candidate_gateway":
        raise ValueError("candidate_gateway_target_required")
    if request_state.get("requested_scopes") != [
        "sovereign_ai_candidate_submission"
    ]:
        raise ValueError("candidate_submission_scope_required")
    if request_state.get("provider_link_state") not in PROVIDER_LINK_ALLOW_STATES:
        return {
            "schema_version": "w7tp-member-sovereign-candidate-bridge-result/0.1",
            "state": "HOLD_IDENTITY_OR_AUTHORITY_NOT_CONVERGED",
            "member_authorization_decision": "hold",
            "member_authorization_reason": "verified_provider_link_required",
            "candidate_only": True,
            "execution_authority": False,
            "production_commit_applied": False,
            "seal_applied": False,
            "member_plaintext_included": False,
        }
    packet_state = packet.get("D2_STATE")
    if not isinstance(packet_state, dict):
        raise ValueError("member_packet_state_required")
    if "system_operator" not in set(packet_state.get("subject_types") or []):
        return {
            "schema_version": "w7tp-member-sovereign-candidate-bridge-result/0.1",
            "state": "HOLD_IDENTITY_OR_AUTHORITY_NOT_CONVERGED",
            "member_authorization_decision": "hold",
            "member_authorization_reason": "system_operator_membership_required",
            "candidate_only": True,
            "execution_authority": False,
            "production_commit_applied": False,
            "seal_applied": False,
            "member_plaintext_included": False,
        }
    if not packet_state.get("role_refs"):
        return {
            "schema_version": "w7tp-member-sovereign-candidate-bridge-result/0.1",
            "state": "HOLD_IDENTITY_OR_AUTHORITY_NOT_CONVERGED",
            "member_authorization_decision": "hold",
            "member_authorization_reason": "developer_role_reference_required",
            "candidate_only": True,
            "execution_authority": False,
            "production_commit_applied": False,
            "seal_applied": False,
            "member_plaintext_included": False,
        }
    packet_evidence = packet.get("D4_EVIDENCE")
    if not isinstance(packet_evidence, dict):
        raise ValueError("member_packet_evidence_required")
    assurance_refs = packet_evidence.get("local_qualification_source_refs") or []
    missing_assurance = []
    for assurance_name, prefix in PRIVILEGED_NATURAL_PERSON_ASSURANCE_PREFIXES.items():
        valid_ref = False
        for ref in assurance_refs:
            text = str(ref)
            digest = text.removeprefix(prefix) if text.startswith(prefix) else ""
            if len(digest) == 64 and all(char in "0123456789abcdef" for char in digest):
                valid_ref = True
                break
        if not valid_ref:
            missing_assurance.append(assurance_name)
    if missing_assurance:
        return {
            "schema_version": "w7tp-member-sovereign-candidate-bridge-result/0.1",
            "state": "HOLD_IDENTITY_OR_AUTHORITY_NOT_CONVERGED",
            "member_authorization_decision": "hold",
            "member_authorization_reason": (
                "natural_person_assurance_incomplete:" + ",".join(missing_assurance)
            ),
            "candidate_only": True,
            "execution_authority": False,
            "production_commit_applied": False,
            "seal_applied": False,
            "member_plaintext_included": False,
        }
    local_verification = verify_privileged_member_locally(packet, request_state, now)
    if local_verification["decision"] != "allow":
        proven_not_subject = local_verification["decision"] == "block"
        step_up_method = local_verification.get("step_up_method")
        return {
            "schema_version": "w7tp-member-sovereign-candidate-bridge-result/0.1",
            "state": (
                "BLOCK_NOT_NATURAL_PERSON"
                if proven_not_subject
                else "HOLD_IDENTITY_OR_AUTHORITY_NOT_CONVERGED"
            ),
            "member_authorization_decision": (
                "deny" if proven_not_subject else "hold"
            ),
            "member_authorization_reason": local_verification["reason"],
            "step_up_required": bool(step_up_method),
            "step_up_method": step_up_method,
            "candidate_only": True,
            "execution_authority": False,
            "production_commit_applied": False,
            "seal_applied": False,
            "member_plaintext_included": False,
        }
    authorization = evaluate_member_authorization(packet, request_state, now)
    authorization_decision = str(authorization.get("decision") or "hold")
    if authorization_decision != "allow":
        return {
            "schema_version": "w7tp-member-sovereign-candidate-bridge-result/0.1",
            "state": (
                "BLOCK_MEMBER_AUTHORIZATION"
                if authorization_decision == "deny"
                else "HOLD_MEMBER_AUTHORIZATION"
            ),
            "member_authorization_decision": authorization_decision,
            "member_authorization_reason": str(
                authorization.get("reason") or "member_authorization_required"
            ),
            "candidate_only": True,
            "execution_authority": False,
            "production_commit_applied": False,
            "seal_applied": False,
            "member_plaintext_included": False,
        }
    result = run_sovereign_ai_candidate_intake(candidate_request)
    result["member_entry"] = True
    result["member_authorization_decision"] = "allow"
    result["member_authorization_reason"] = str(
        authorization.get("reason") or "member_controlled_access"
    )
    result["member_plaintext_included"] = False
    return result


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _client_ip(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        return forwarded or self.client_address[0]

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _authorize_or_reply(self) -> tuple[bool, str | None, str]:
        client_ip = self._client_ip()
        supplied = self.headers.get("X-Taiji-Five-Code-Sha256")
        ok, reason, node_id = authorize(client_ip, supplied)
        if not ok:
            audit({"client_ip": client_ip, "path": self.path, "allowed": False, "reason": reason, "node_id": node_id})
            self._json(403, {"ok": False, "risk_level": "L3", "action": "block", "reason": reason})
            return False, node_id, reason
        return True, node_id, reason

    def do_GET(self) -> None:
        if self.path == "/health":
            target_ok = False
            try:
                urllib.request.urlopen(f"{TARGET}/api/tags", timeout=1.5).read(1)
                target_ok = True
            except Exception:
                target_ok = False
            self._json(
                200,
                {
                    "ok": target_ok,
                    "runtime": VERSION,
                    "target": TARGET,
                    "allowed_models": sorted(ALLOWED_MODELS),
                    "memory": memory_ref_state(),
                    "identity_allowlist_exists": ALLOWLIST_PATH.exists(),
                    "audit_path": str(AUDIT_PATH),
                },
            )
            return
        if self.path == "/w7tp/member-sovereign/capabilities":
            allowed, _node_id, _reason = self._authorize_or_reply()
            if not allowed:
                return
            self._json(
                200,
                {
                    "ok": True,
                    "schema_version": MEMBER_SOVEREIGN_SCHEMA_VERSION,
                    "identity_states": sorted(IDENTITY_STATES),
                    "subject_types": sorted(SUBJECT_TYPES),
                    "authorization_scopes": sorted(AUTHORIZATION_SCOPES),
                    "cloud_role": "candidate_fallback_only",
                    "cloud_auto_invoke": False,
                    "member_plaintext_accepted": False,
                    "total_field_candidate_path": MEMBER_TOTAL_FIELD_CANDIDATE_PATH,
                    "total_field_candidate_scope": "sovereign_ai_candidate_submission",
                },
            )
            return
        if self.path.startswith("/api/"):
            allowed, node_id, reason = self._authorize_or_reply()
            if not allowed:
                return
            self._proxy("GET", b"", node_id, reason)
            return
        self._json(404, {"ok": False, "reason": "not_found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or "0")
        if (
            self.path == MEMBER_TOTAL_FIELD_CANDIDATE_PATH
            and length > MEMBER_TOTAL_FIELD_CANDIDATE_MAX_BYTES
        ):
            self._json(
                413,
                {
                    "ok": False,
                    "state": "HOLD_REQUEST_TOO_LARGE",
                    "candidate_only": True,
                },
            )
            return
        body = self.rfile.read(length) if length else b""
        allowed, node_id, reason = self._authorize_or_reply()
        if not allowed:
            return
        if (
            self.path == MEMBER_TOTAL_FIELD_CANDIDATE_PATH
            and self.headers.get("X-Forwarded-For")
        ):
            audit(
                {
                    "client_ip": self.client_address[0],
                    "path": self.path,
                    "body_sha256": sha256_bytes(body),
                    "allowed": False,
                    "reason": "forwarded_header_forbidden",
                    "node_id": node_id,
                }
            )
            self._json(
                403,
                {
                    "ok": False,
                    "state": "BLOCK_FORWARDED_IDENTITY_FORBIDDEN",
                    "candidate_only": True,
                },
            )
            return
        if self.path.startswith("/w7tp/member-sovereign/"):
            try:
                payload = json.loads(body.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("json_object_required")
                forbidden = _forbidden_member_paths(payload)
                if forbidden:
                    raise ValueError("member_plaintext_forbidden:" + ",".join(forbidden))
                if self.path == "/w7tp/member-sovereign/issue":
                    authority = payload.get("authority") or {}
                    claimed_subject_types = set(authority.get("subject_types") or [])
                    claimed_scopes = set(authority.get("authorization_scopes") or [])
                    if (
                        "system_operator" in claimed_subject_types
                        or "sovereign_ai_candidate_submission" in claimed_scopes
                    ):
                        raise ValueError("privileged_packet_local_authority_only")
                    result = issue_member_sovereign_packet(authority)
                elif self.path == "/w7tp/member-sovereign/authorize":
                    result = evaluate_member_authorization(
                        payload.get("packet") or {},
                        payload.get("request_state") or {},
                        str(payload.get("now") or now_iso()),
                    )
                elif self.path == "/w7tp/member-sovereign/data-export":
                    decision, export_reason = classify_data_export(payload.get("request_state") or {})
                    result = {
                        "decision": decision,
                        "reason": export_reason,
                        "member_plaintext_included": False,
                        "cloud_invoked": False,
                    }
                elif self.path == MEMBER_TOTAL_FIELD_CANDIDATE_PATH:
                    result = member_total_field_candidate_intake(
                        payload, str(payload.get("now") or now_iso())
                    )
                else:
                    self._json(404, {"ok": False, "reason": "not_found"})
                    return
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                audit(
                    {
                        "path": self.path,
                        "body_sha256": sha256_bytes(body),
                        "allowed": False,
                        "reason": type(exc).__name__,
                        "node_id": node_id,
                    }
                )
                self._json(400, {"ok": False, "action": "block", "reason": str(exc)})
                return
            audit(
                {
                    "path": self.path,
                    "body_sha256": sha256_bytes(body),
                    "allowed": (
                        result.get("state") == "PASS_CANDIDATE_ACCEPTED"
                        if self.path == MEMBER_TOTAL_FIELD_CANDIDATE_PATH
                        else result.get("decision", "allow") == "allow"
                    ),
                    "reason": str(result.get("reason") or "member_sovereign_packet_issued"),
                    "node_id": node_id,
                }
            )
            self._json(200, result)
            return
        hazard = block_payload(body)
        model = parse_model(body)
        if hazard:
            audit(
                {
                    "client_ip": self._client_ip(),
                    "path": self.path,
                    "model": model,
                    "body_sha256": sha256_bytes(body),
                    "allowed": False,
                    "reason": hazard,
                    "node_id": node_id,
                }
            )
            self._json(403, {"ok": False, "risk_level": "L3", "action": "block", "reason": hazard})
            return
        if model and model not in ALLOWED_MODELS:
            audit(
                {
                    "client_ip": self._client_ip(),
                    "path": self.path,
                    "model": model,
                    "body_sha256": sha256_bytes(body),
                    "allowed": False,
                    "reason": "model_not_allowlisted",
                    "node_id": node_id,
                }
            )
            self._json(403, {"ok": False, "risk_level": "L2", "action": "warn_block", "reason": "model_not_allowlisted"})
            return
        self._proxy("POST", body, node_id, reason)

    def _proxy(self, method: str, body: bytes, node_id: str | None, auth_reason: str) -> None:
        target_url = f"{TARGET}{self.path}"
        headers = {"Content-Type": self.headers.get("Content-Type", "application/json")}
        request = urllib.request.Request(target_url, data=body if method == "POST" else None, headers=headers, method=method)
        body_hash = sha256_bytes(body) if body else None
        model = parse_model(body)
        audit(
            {
                "client_ip": self._client_ip(),
                "path": self.path,
                "model": model,
                "body_sha256": body_hash,
                "allowed": True,
                "reason": auth_reason,
                "node_id": node_id,
                "memory_ref_count": memory_ref_state()["count"],
            }
        )
        try:
            with urllib.request.urlopen(request, timeout=float(env("TAIJI_PROXY_TIMEOUT_SEC", "300"))) as response:
                self.send_response(response.status)
                for key, value in response.headers.items():
                    if key.lower() not in HOP_BY_HOP and key.lower() != "content-length":
                        self.send_header(key, value)
                self.end_headers()
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except urllib.error.HTTPError as exc:
            self._json(exc.code, {"ok": False, "reason": "target_http_error", "status": exc.code})
        except Exception as exc:
            self._json(502, {"ok": False, "reason": "target_not_reachable", "error_type": type(exc).__name__})


def main() -> int:
    bind = env("TAIJI_GATEWAY_BIND", "127.0.0.1")
    port = int(env("TAIJI_GATEWAY_PORT", "11435"))
    server = ThreadingHTTPServer((bind, port), Handler)
    print(json.dumps({"ok": True, "runtime": VERSION, "bind": bind, "port": port, "target": TARGET}, ensure_ascii=False), flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
