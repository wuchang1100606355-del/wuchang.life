from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any


PACKET_SCHEMA = "W7TP_9002_PHYSICAL_ACTUATOR_REQUEST_CANDIDATE_V1"
PASS_STATE = "PASS_9002_PHYSICAL_ACTUATOR_PREFLIGHT_CANDIDATE"
MAX_TTL_SECONDS = 60
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
NONCE_REF = re.compile(r"^nonce_ref:sha256:[0-9a-f]{64}$")
JOINT_8D_FIELDS = (
    "D1_INTENT",
    "D2_STATE",
    "D3_COORDINATE_RELATION",
    "D4_EVIDENCE_LINEAGE",
    "D5_EXECUTION_POLICY",
    "D6_GENERATIVE_TRANSMISSION",
    "D7_RISK_QUARANTINE",
    "D8_ENVELOPE_AUTHORITY",
)
SIGNED_FIELDS = frozenset(
    {
        "schema_id",
        "request_id",
        "application_identity_ref",
        "application_identity_proof",
        "issued_at",
        "expires_at",
        "ttl_seconds",
        "nonce",
        "actuator_id",
        "action",
        "parameters_sha256",
        "joint_8d_state",
        "joint_8d_state_sha256",
        "authority_ref",
        "verifier_ref",
    }
)
PACKET_FIELDS = SIGNED_FIELDS | {"request_sha256", "signature"}


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _parse_time(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("UTC_Z_TIME_REQUIRED")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo is None:
        raise ValueError("TIMEZONE_REQUIRED")
    return parsed.astimezone(timezone.utc)


def _blocked(state: str) -> dict[str, Any]:
    return {
        "state": state,
        "actuator_authorized": False,
        "final_authority": False,
        "total_field_decision": "NOT_RUN",
    }


class PhysicalActuatorAuthorityGate:
    """Fail-closed preflight for one exact physical actuator request.

    Authority and application identity are verified by injected trusted bindings.
    This gate does not derive authority from D1-D8 field presence or define D8.
    """

    candidate_only = True
    runtime_active = False

    def __init__(
        self,
        *,
        nonce_ledger: Any,
        signature_verifier: Any,
        application_identity_verifier: Callable[..., bool],
        authority_reference_verifier: Callable[..., bool],
    ) -> None:
        self.nonce_ledger = nonce_ledger
        self.signature_verifier = signature_verifier
        self.application_identity_verifier = application_identity_verifier
        self.authority_reference_verifier = authority_reference_verifier

    def validate_and_consume(
        self,
        packet: Mapping[str, Any] | None,
        *,
        actuator_id: str,
        action: str,
        parameters: Mapping[str, Any],
        now: datetime,
    ) -> dict[str, Any]:
        if not isinstance(packet, Mapping):
            return _blocked("BLOCK_9002_AUTHORITY_PACKET_REQUIRED")
        if set(packet) != PACKET_FIELDS or packet.get("schema_id") != PACKET_SCHEMA:
            return _blocked("BLOCK_9002_AUTHORITY_PACKET_SHAPE")
        for field in (
            "request_id",
            "application_identity_ref",
            "application_identity_proof",
            "actuator_id",
            "action",
            "authority_ref",
            "verifier_ref",
            "signature",
        ):
            if not isinstance(packet.get(field), str) or not packet[field].strip():
                return _blocked("BLOCK_9002_AUTHORITY_PACKET_SHAPE")

        signed = {field: packet[field] for field in SIGNED_FIELDS}
        request_sha256 = packet.get("request_sha256")
        if (
            not isinstance(request_sha256, str)
            or SHA256_HEX.fullmatch(request_sha256) is None
            or canonical_sha256(signed) != request_sha256
        ):
            return _blocked("BLOCK_9002_REQUEST_INTEGRITY")
        if packet.get("parameters_sha256") != canonical_sha256(dict(parameters)):
            return _blocked("BLOCK_9002_REQUEST_PARAMETERS_MISMATCH")
        if packet.get("actuator_id") != actuator_id or packet.get("action") != action:
            return _blocked("BLOCK_9002_REQUEST_TARGET_MISMATCH")

        joint_state = packet.get("joint_8d_state")
        if (
            not isinstance(joint_state, Mapping)
            or set(joint_state) != set(JOINT_8D_FIELDS)
            or any(
                not isinstance(joint_state[field], Mapping) or not joint_state[field]
                for field in JOINT_8D_FIELDS
            )
            or packet.get("joint_8d_state_sha256") != canonical_sha256(joint_state)
        ):
            return _blocked("BLOCK_9002_JOINT_8D_STATE_INVALID")
        d8 = joint_state["D8_ENVELOPE_AUTHORITY"]
        authority_ref = packet.get("authority_ref")
        if (
            not isinstance(authority_ref, str)
            or not authority_ref.strip()
            or d8.get("authority_ref") != authority_ref
            or d8.get("effect_scope") != "PHYSICAL_ACTUATOR_EFFECT"
        ):
            return _blocked("BLOCK_9002_EXPLICIT_AUTHORITY_REFERENCE")

        try:
            issued_at = _parse_time(packet.get("issued_at"))
            expires_at = _parse_time(packet.get("expires_at"))
        except (TypeError, ValueError):
            return _blocked("BLOCK_9002_FRESHNESS_TIME")
        ttl_seconds = packet.get("ttl_seconds")
        observed = now.astimezone(timezone.utc)
        if (
            isinstance(ttl_seconds, bool)
            or not isinstance(ttl_seconds, int)
            or not 1 <= ttl_seconds <= MAX_TTL_SECONDS
            or expires_at <= issued_at
            or int((expires_at - issued_at).total_seconds()) != ttl_seconds
            or observed < issued_at
            or observed >= expires_at
        ):
            return _blocked("BLOCK_9002_FRESHNESS_EXPIRED")

        nonce = packet.get("nonce")
        if not isinstance(nonce, str) or NONCE_REF.fullmatch(nonce) is None:
            return _blocked("BLOCK_9002_NONCE_INVALID")
        if (
            getattr(self.signature_verifier, "trusted_runtime_verifier", False) is not True
            or not callable(getattr(self.signature_verifier, "verify", None))
            or self.signature_verifier.verify(
                verifier_ref=packet.get("verifier_ref"),
                payload_sha256=request_sha256,
                signature=packet.get("signature"),
            )
            is not True
        ):
            return _blocked("BLOCK_9002_REQUEST_SIGNATURE")
        if (
            getattr(
                self.application_identity_verifier,
                "trusted_application_identity_verifier",
                False,
            )
            is not True
        ):
            return _blocked("BLOCK_9002_APPLICATION_IDENTITY_BINDING_REQUIRED")
        try:
            identity_verified = self.application_identity_verifier(
                application_identity_ref=packet.get("application_identity_ref"),
                application_identity_proof=packet.get("application_identity_proof"),
                request_sha256=request_sha256,
            )
        except Exception:
            identity_verified = False
        if identity_verified is not True:
            return _blocked("BLOCK_9002_APPLICATION_IDENTITY")
        if (
            getattr(
                self.authority_reference_verifier,
                "trusted_authority_reference_verifier",
                False,
            )
            is not True
        ):
            return _blocked("BLOCK_9002_AUTHORITY_BINDING_REQUIRED")
        try:
            authority_verified = self.authority_reference_verifier(
                authority_ref=authority_ref,
                effect_scope="PHYSICAL_ACTUATOR_EFFECT",
                joint_8d_state_sha256=packet.get("joint_8d_state_sha256"),
                request_sha256=request_sha256,
            )
        except Exception:
            authority_verified = False
        if authority_verified is not True:
            return _blocked("BLOCK_9002_AUTHORITY_REFERENCE_UNVERIFIED")

        if (
            getattr(self.nonce_ledger, "persistent", False) is not True
            or not callable(getattr(self.nonce_ledger, "mark_used_or_replay", None))
        ):
            return _blocked("BLOCK_9002_PERSISTENT_NONCE_LEDGER_REQUIRED")
        if self.nonce_ledger.mark_used_or_replay(
            nonce,
            request_sha256,
            observed.timestamp(),
            ttl_seconds,
        ) is not True:
            return _blocked("BLOCK_9002_REQUEST_REPLAY")
        return {
            "state": PASS_STATE,
            "actuator_authorized": True,
            "application_identity_verified": True,
            "request_integrity_verified": True,
            "freshness_verified": True,
            "anti_replay_consumed": True,
            "joint_8d_state_verified": True,
            "authority_reference_verified": True,
            "request_sha256": request_sha256,
            "final_authority": False,
            "total_field_decision": "NOT_RUN",
        }


__all__ = [
    "JOINT_8D_FIELDS",
    "PACKET_SCHEMA",
    "PASS_STATE",
    "PhysicalActuatorAuthorityGate",
    "canonical_sha256",
]
