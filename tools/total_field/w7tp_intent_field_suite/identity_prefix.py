"""Immutable natural-person identity prefix for the one shared W7TP runtime.

This is a ref-only projection of the existing 8D identity-packet canonical.
It never stores identity plaintext and does not create a parallel identity
registry.  A trusted Total Field identity issuer builds the prefix; an LLM may
only produce a candidate body around that unchanged prefix.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from tools.total_field.w7tp_field_application_runtime import FieldApplicationError

from .canonical_hash import canonical_sha256, normalize_content


SCHEMA_VERSION = "W7TP-NATURAL-PERSON-IDENTITY-PREFIX/1.0"
PACKET_TYPE = "NATURAL_PERSON_IDENTITY_IMMUTABLE_PREFIX"
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
REF_PATTERNS = {
    "identity_packet_ref": re.compile(r"^identity_packet_ref:sha256:[0-9a-f]{64}$"),
    "protected_plaintext_binding_ref": re.compile(r"^identity_binding_ref:sha256:[0-9a-f]{64}$"),
    "identity_registry_ref": re.compile(r"^identity_registry_ref:sha256:[0-9a-f]{64}$"),
    "field_context_ref": re.compile(r"^field_context_ref:[A-Za-z0-9._:-]+$"),
    "device_ref": re.compile(r"^device_ref:sha256:[0-9a-f]{64}$"),
    "binding_ref": re.compile(r"^binding_ref:sha256:[0-9a-f]{64}$"),
    "provider_ref": re.compile(r"^provider_ref:[a-z0-9][a-z0-9._-]{0,63}$"),
    "source_ref": re.compile(r"^source_ref:sha256:[0-9a-f]{64}$"),
    "evidence_ref": re.compile(r"^evidence_ref:sha256:[0-9a-f]{64}$"),
}
RESERVED_LLM_KEYS = frozenset(
    {
        "identity_prefix",
        "identity_prefix_sha256",
        "identity_packet_ref",
        "protected_plaintext_binding_ref",
        "provider_bindings",
        "device_bindings",
        "llm_mutable",
        "llm_may_modify_prefix",
    }
)
FORBIDDEN_BINDING_KEYS = frozenset(
    {
        "access_token",
        "credential",
        "email",
        "id_token",
        "line_user_id",
        "name",
        "password",
        "phone",
        "raw_subject",
        "refresh_token",
        "secret",
        "token",
    }
)


def _require_ref(value: Any, field: str) -> str:
    if not isinstance(value, str) or REF_PATTERNS[field].fullmatch(value) is None:
        raise FieldApplicationError("IDENTITY_PREFIX_REF_INVALID", f"$.{field}")
    return value


def _require_hash(value: Any, path: str) -> str:
    if not isinstance(value, str) or SHA256_HEX.fullmatch(value) is None:
        raise FieldApplicationError("IDENTITY_PREFIX_SHA256_INVALID", path)
    return value


def _normalized_binding_items(
    items: Sequence[Mapping[str, Any]], *, provider: bool
) -> list[dict[str, str]]:
    if not isinstance(items, (list, tuple)) or not items:
        path = "$.D6.provider_bindings" if provider else "$.D6.device_bindings"
        raise FieldApplicationError("IDENTITY_PREFIX_BINDING_REQUIRED", path)
    normalized: list[dict[str, str]] = []
    expected = (
        {"provider_ref", "provider_subject_sha256", "binding_ref", "state"}
        if provider
        else {"device_ref", "binding_ref", "state"}
    )
    for index, raw in enumerate(items):
        path = f"$.D6.{'provider_bindings' if provider else 'device_bindings'}[{index}]"
        if not isinstance(raw, Mapping) or set(raw) != expected:
            raise FieldApplicationError("IDENTITY_PREFIX_BINDING_SHAPE_INVALID", path)
        if FORBIDDEN_BINDING_KEYS & {str(key).casefold() for key in raw}:
            raise FieldApplicationError("IDENTITY_PREFIX_PLAINTEXT_OR_SECRET_BLOCKED", path)
        state = raw.get("state")
        if state not in {"ACTIVE", "SUSPENDED", "REVOKED"}:
            raise FieldApplicationError("IDENTITY_PREFIX_BINDING_STATE_INVALID", f"{path}.state")
        item = {
            "binding_ref": _require_ref(raw.get("binding_ref"), "binding_ref"),
            "state": str(state),
        }
        if provider:
            item["provider_ref"] = _require_ref(raw.get("provider_ref"), "provider_ref")
            item["provider_subject_sha256"] = _require_hash(
                raw.get("provider_subject_sha256"),
                f"{path}.provider_subject_sha256",
            )
        else:
            item["device_ref"] = _require_ref(raw.get("device_ref"), "device_ref")
        normalized.append(item)
    identity_key = "provider_ref" if provider else "device_ref"
    if len({item[identity_key] for item in normalized}) != len(normalized):
        raise FieldApplicationError("IDENTITY_PREFIX_DUPLICATE_BINDING", path)
    return sorted(
        normalized,
        key=lambda item: (item[identity_key], item["binding_ref"]),
    )


def _prefix_hash_basis(packet: Mapping[str, Any]) -> dict[str, Any]:
    basis = normalize_content(dict(packet))
    d8 = dict(basis.get("D8", {}))
    d8.pop("prefix_sha256", None)
    basis["D8"] = d8
    return basis


def build_natural_person_identity_prefix(
    *,
    identity_packet_ref: str,
    protected_plaintext_binding_ref: str,
    identity_registry_ref: str,
    field_context_ref: str,
    device_bindings: Sequence[Mapping[str, Any]],
    provider_bindings: Sequence[Mapping[str, Any]],
    source_refs: Sequence[str],
    binding_evidence_refs: Sequence[str],
    identity_state: str = "ACTIVE",
    revocation_state: str = "CLEAR",
) -> dict[str, Any]:
    """Build one deterministic, ref-only identity prefix outside the LLM."""

    if identity_state not in {"ACTIVE", "SUSPENDED", "RECOVERY_PENDING"}:
        raise FieldApplicationError("IDENTITY_PREFIX_STATE_INVALID", "$.D2.identity_state")
    if revocation_state not in {"CLEAR", "REVOKED"}:
        raise FieldApplicationError("IDENTITY_PREFIX_REVOCATION_INVALID", "$.D2.revocation_state")
    sources = sorted({_require_ref(item, "source_ref") for item in source_refs})
    evidence = sorted({_require_ref(item, "evidence_ref") for item in binding_evidence_refs})
    if not sources or not evidence:
        raise FieldApplicationError("IDENTITY_PREFIX_EVIDENCE_REQUIRED", "$.D4")
    packet: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "packet_type": PACKET_TYPE,
        "D1": {
            "subject_type": "NATURAL_PERSON",
            "identity_packet_ref": _require_ref(identity_packet_ref, "identity_packet_ref"),
            "protected_plaintext_binding_ref": _require_ref(
                protected_plaintext_binding_ref,
                "protected_plaintext_binding_ref",
            ),
            "one_natural_person_one_packet": True,
            "plaintext_identity_visible": False,
        },
        "D2": {
            "identity_state": identity_state,
            "revocation_state": revocation_state,
        },
        "D3": {
            "identity_registry_ref": _require_ref(identity_registry_ref, "identity_registry_ref"),
            "field_context_ref": _require_ref(field_context_ref, "field_context_ref"),
        },
        "D4": {
            "source_refs": sources,
            "binding_evidence_refs": evidence,
        },
        "D5": {
            "identity_prefix_writer": "TOTAL_FIELD_IDENTITY_ISSUER_ONLY",
            "llm_writable_region": "CANDIDATE_BODY_ONLY",
            "llm_may_create_prefix": False,
            "llm_may_modify_prefix": False,
        },
        "D6": {
            "device_bindings": _normalized_binding_items(device_bindings, provider=False),
            "provider_bindings": _normalized_binding_items(provider_bindings, provider=True),
            "device_and_provider_are_carriers": True,
            "plaintext_inside_packet": False,
            "credential_material_inside_packet": False,
        },
        "D7": {
            "missing_binding_evidence_state": "NOT_YET_EVIDENCED",
            "missing_evidence_is_denial": False,
            "binding_conflict_decision": "HOLD_IDENTITY_PACKET_CONFLICT",
            "prefix_mismatch_decision": "HOLD_IDENTITY_PREFIX_INTEGRITY",
        },
        "D8": {
            "prefix_position": "SYSTEM_IMMUTABLE_PREFIX",
            "llm_mutable": False,
            "verify_on_every_state_transition": True,
            "requires_total_field_verify": True,
            "prefix_sha256": "",
        },
    }
    packet["D8"]["prefix_sha256"] = canonical_sha256(_prefix_hash_basis(packet))
    return normalize_content(packet)


def _shape_errors(packet: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        rebuilt = build_natural_person_identity_prefix(
            identity_packet_ref=packet.get("D1", {}).get("identity_packet_ref"),
            protected_plaintext_binding_ref=packet.get("D1", {}).get(
                "protected_plaintext_binding_ref"
            ),
            identity_registry_ref=packet.get("D3", {}).get("identity_registry_ref"),
            field_context_ref=packet.get("D3", {}).get("field_context_ref"),
            device_bindings=packet.get("D6", {}).get("device_bindings", []),
            provider_bindings=packet.get("D6", {}).get("provider_bindings", []),
            source_refs=packet.get("D4", {}).get("source_refs", []),
            binding_evidence_refs=packet.get("D4", {}).get("binding_evidence_refs", []),
            identity_state=packet.get("D2", {}).get("identity_state"),
            revocation_state=packet.get("D2", {}).get("revocation_state"),
        )
    except FieldApplicationError as exc:
        return [exc.reason_code]
    supplied_hash = packet.get("D8", {}).get("prefix_sha256")
    if supplied_hash != rebuilt["D8"]["prefix_sha256"]:
        errors.append("IDENTITY_PREFIX_SHA256_MISMATCH")
    if normalize_content(dict(packet)) != rebuilt:
        errors.append("IDENTITY_PREFIX_CANONICAL_SHAPE_MISMATCH")
    return errors


def verify_natural_person_identity_prefix(
    packet: Mapping[str, Any],
    *,
    identity_registry_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify integrity and optional one-person/one-packet registry evidence.

    Missing registry evidence is explicitly NOT_YET_EVIDENCED, never a denial.
    A positive duplicate mapping or prefix mismatch is a hard HOLD.
    """

    if not isinstance(packet, Mapping):
        return {
            "state": "HOLD_IDENTITY_PREFIX_INTEGRITY",
            "integrity": "FAIL",
            "registry_evidence": "NOT_YET_EVIDENCED",
            "formal_adoption_allowed": False,
            "candidate_processing_allowed": False,
            "reason_codes": ["IDENTITY_PREFIX_OBJECT_REQUIRED"],
        }
    errors = _shape_errors(packet)
    if errors:
        return {
            "state": "HOLD_IDENTITY_PREFIX_INTEGRITY",
            "integrity": "FAIL",
            "registry_evidence": "NOT_YET_EVIDENCED",
            "formal_adoption_allowed": False,
            "candidate_processing_allowed": False,
            "reason_codes": errors,
        }

    registry_state = "NOT_YET_EVIDENCED"
    reason_codes: list[str] = []
    if identity_registry_snapshot is not None:
        entries = identity_registry_snapshot.get("entries")
        if not isinstance(entries, list):
            reason_codes.append("IDENTITY_REGISTRY_ENTRIES_INVALID")
        else:
            binding_ref = packet["D1"]["protected_plaintext_binding_ref"]
            packet_ref = packet["D1"]["identity_packet_ref"]
            matches = {
                item.get("identity_packet_ref")
                for item in entries
                if isinstance(item, Mapping)
                and item.get("protected_plaintext_binding_ref") == binding_ref
            }
            if len(matches) > 1 or (matches and packet_ref not in matches):
                return {
                    "state": "HOLD_IDENTITY_PACKET_CONFLICT",
                    "integrity": "PASS",
                    "registry_evidence": "CONFLICT",
                    "formal_adoption_allowed": False,
                    "candidate_processing_allowed": False,
                    "reason_codes": ["ONE_NATURAL_PERSON_MULTIPLE_PACKET_REFS"],
                }
            if matches == {packet_ref}:
                registry_state = "PASS_ONE_NATURAL_PERSON_ONE_PACKET"
            else:
                reason_codes.append("IDENTITY_BINDING_NOT_FOUND_IN_REGISTRY_SNAPSHOT")

    verified = registry_state == "PASS_ONE_NATURAL_PERSON_ONE_PACKET"
    return {
        "state": "PASS_IDENTITY_PREFIX_VERIFIED" if verified else "NOT_YET_EVIDENCED",
        "integrity": "PASS",
        "registry_evidence": registry_state,
        "formal_adoption_allowed": verified,
        "candidate_processing_allowed": True,
        "reason_codes": reason_codes,
    }


def assert_llm_candidate_does_not_mutate_identity(value: Any, path: str = "$") -> None:
    """Reject reserved identity-prefix keys from every LLM-writable region."""

    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key).strip().casefold()
            child_path = f"{path}.{raw_key}"
            if key in RESERVED_LLM_KEYS:
                raise FieldApplicationError(
                    "LLM_IDENTITY_PREFIX_MUTATION_ATTEMPT",
                    child_path,
                )
            assert_llm_candidate_does_not_mutate_identity(child, child_path)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            assert_llm_candidate_does_not_mutate_identity(child, f"{path}[{index}]")


def identity_prefix_projection(
    packet: Mapping[str, Any],
    *,
    identity_registry_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return verified packet fields that the shared builder may attach."""

    verification = verify_natural_person_identity_prefix(
        packet,
        identity_registry_snapshot=identity_registry_snapshot,
    )
    if verification["integrity"] != "PASS" or not verification["candidate_processing_allowed"]:
        raise FieldApplicationError(verification["state"])
    return {
        "identity_prefix": normalize_content(dict(packet)),
        "identity_prefix_sha256": packet["D8"]["prefix_sha256"],
        "identity_binding_evidence_state": verification["state"],
        "identity_formal_adoption_allowed": verification["formal_adoption_allowed"],
        "llm_identity_prefix_mutable": False,
    }
