#!/usr/bin/env python3
"""Read-only P0 verifier for the member-sovereign identity contract candidate.

The verifier uses synthetic references only. It validates contract shape,
canonical hashes, root/derived bindings, dual-receipt equality, replay signals,
and the exact SHA-256 manifest. It does not issue an identity, validate a live
signature, consume a runtime nonce, call Odoo, write a database, or authorize an
action.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, ValidationError


ROOT = Path(__file__).resolve().parents[2]
ROOT_SCHEMA_PATH = (
    ROOT / "schemas/field/w7tp_member_sovereign_identity_root_v1.schema.json"
)
DERIVED_SCHEMA_PATH = (
    ROOT / "schemas/field/w7tp_member_sovereign_derived_packets_v1.schema.json"
)
DUAL_RECEIPT_SCHEMA_PATH = (
    ROOT / "schemas/field/w7tp_member_action_dual_receipt_v1.schema.json"
)
TEST_PATH = ROOT / "tests/test_member_sovereign_identity_root_contract.py"
VERIFIER_PATH = (
    ROOT / "scripts/verify/verify_member_sovereign_identity_root_contract.py"
)
MANIFEST_PATH = (
    ROOT
    / "manifests/total_field/w7tp_member_sovereign_identity_root_v1/"
    "SHA256_MANIFEST.json"
)

MANIFEST_FILES = (
    "schemas/field/w7tp_member_action_dual_receipt_v1.schema.json",
    "schemas/field/w7tp_member_sovereign_derived_packets_v1.schema.json",
    "schemas/field/w7tp_member_sovereign_identity_root_v1.schema.json",
    "scripts/verify/verify_member_sovereign_identity_root_contract.py",
    "tests/test_member_sovereign_identity_root_contract.py",
)

AUTHORITY_MODEL = {
    "member_consent_authority": "member",
    "safety_and_landing_authority": "total_field_verifier",
    "process_authority": "odoo",
    "candidate_authority": "none",
}

FORBIDDEN_PACKET_KEYS = {
    "name",
    "member_name",
    "display_name",
    "email",
    "phone",
    "mobile",
    "address",
    "provider_subject",
    "raw_provider_subject",
    "provider_profile",
    "access_token",
    "refresh_token",
    "password",
    "secret",
    "credential",
    "private_key",
    "raw_key",
    "amount",
    "currency",
}

EMAIL_VALUE_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PRIVATE_KEY_VALUE_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")

FIXED_NOW = "2026-07-25T00:01:00Z"
FIXED_ISSUED_AT = "2026-07-25T00:00:00Z"
FIXED_EXPIRES_AT = "2026-07-25T00:10:00Z"


class ContractHold(RuntimeError):
    """Fail-closed candidate-contract result."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def ref(prefix: str, label: str) -> str:
    return f"{prefix}:sha256:{digest(label)}"


def _normalize_for_canonical_json(value: Any) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ContractHold("HOLD_NON_FINITE_NUMBER")
        raise ContractHold("HOLD_FLOAT_FORBIDDEN")
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize_for_canonical_json(item) for item in value]
    if isinstance(value, dict):
        return {
            unicodedata.normalize("NFC", str(key)): _normalize_for_canonical_json(item)
            for key, item in value.items()
        }
    if value is None or isinstance(value, (bool, int)):
        return value
    raise ContractHold("HOLD_UNSUPPORTED_CANONICAL_JSON_TYPE")


def canonical_bytes(value: Any) -> bytes:
    normalized = _normalize_for_canonical_json(value)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def amount_currency_hash(amount_minor: int, currency_code: str, target_ref: str) -> str:
    if isinstance(amount_minor, bool) or not isinstance(amount_minor, int):
        raise ContractHold("HOLD_AMOUNT_MINOR_INVALID")
    if amount_minor < 0:
        raise ContractHold("HOLD_AMOUNT_MINOR_INVALID")
    if not re.fullmatch(r"[A-Z]{3}", currency_code):
        raise ContractHold("HOLD_CURRENCY_CODE_INVALID")
    basis = {
        "schema_version": "W7TP-AMOUNT-CURRENCY-HASH-BASIS/1.0",
        "amount_minor": amount_minor,
        "currency_code": currency_code,
        "target_ref": target_ref,
    }
    return sha256_json(basis)


def action_hash_basis(action_binding: dict[str, Any]) -> dict[str, Any]:
    try:
        scope_refs = action_binding["scope_refs"]
        if not isinstance(scope_refs, list) or not all(
            isinstance(item, str) for item in scope_refs
        ):
            raise ContractHold("HOLD_ACTION_SCOPE_REFS_INVALID")
        basis = {
            "schema_version": action_binding["schema_version"],
            "root_ref": action_binding["identity_root_ref"],
            "root_packet_ref": action_binding["root_packet_ref"],
            "subject_binding_ref": action_binding["subject_binding_ref"],
            "root_generation": action_binding["root_generation"],
            "revocation_epoch": action_binding["revocation_epoch"],
            "session_ref": action_binding["session_ref"],
            "scene_ref": action_binding["scene_ref"],
            "action_ref": action_binding["action_ref"],
            "action_type": action_binding["action_code"],
            "action_class": action_binding["action_class"],
            "target_ref": action_binding["target_ref"],
            "parameters_sha256": action_binding["parameters_sha256"],
            "purpose_ref": action_binding["purpose_ref"],
            "scope_refs": sorted(set(scope_refs)),
            "resource_refs": action_binding["resource_refs"],
            "effect_class": action_binding["effect_class"],
            "member_display_hash": action_binding["member_display_hash"],
            "terms_version": action_binding["terms_version"],
            "amount_currency_hash_scope": action_binding[
                "amount_currency_hash_scope"
            ],
            "amount_currency_hash": action_binding["amount_currency_hash"],
            "action_hash_algorithm": action_binding["action_hash_algorithm"],
        }
    except KeyError as exc:
        raise ContractHold("HOLD_ACTION_HASH_BASIS_INCOMPLETE") from exc
    return basis


def action_hash(action_binding: dict[str, Any]) -> str:
    return sha256_json(action_hash_basis(action_binding))


def receipt_hash(receipt: dict[str, Any]) -> str:
    basis = copy.deepcopy(receipt)
    try:
        del basis["receipt_sha256"]
    except KeyError as exc:
        raise ContractHold("HOLD_RECEIPT_HASH_FIELD_MISSING") from exc
    return sha256_json(basis)


def content_hash(packet: dict[str, Any]) -> str:
    basis = copy.deepcopy(packet)
    try:
        del basis["integrity"]["content_sha256"]
    except (KeyError, TypeError) as exc:
        raise ContractHold("HOLD_CONTENT_HASH_FIELD_MISSING") from exc
    return sha256_json(basis)


def seal_content(packet: dict[str, Any]) -> dict[str, Any]:
    sealed = copy.deepcopy(packet)
    sealed["integrity"]["content_sha256"] = content_hash(sealed)
    return sealed


def seal_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    sealed = copy.deepcopy(receipt)
    sealed["receipt_sha256"] = receipt_hash(sealed)
    return sealed


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_schemas() -> dict[str, dict[str, Any]]:
    return {
        "root": load_json(ROOT_SCHEMA_PATH),
        "derived": load_json(DERIVED_SCHEMA_PATH),
        "dual_receipt": load_json(DUAL_RECEIPT_SCHEMA_PATH),
    }


def check_schemas() -> dict[str, dict[str, Any]]:
    schemas = load_schemas()
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
    return schemas


def validate_instance(schema: dict[str, Any], instance: dict[str, Any]) -> None:
    Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    ).validate(instance)


def _walk_forbidden(value: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_lower = key.lower()
            if key_lower in FORBIDDEN_PACKET_KEYS:
                raise ContractHold(
                    "HOLD_MEMBER_PLAINTEXT_BOUNDARY:" + ".".join((*path, key))
                )
            _walk_forbidden(item, (*path, key))
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _walk_forbidden(item, (*path, str(index)))
        return
    if isinstance(value, str):
        if EMAIL_VALUE_RE.fullmatch(value) or PRIVATE_KEY_VALUE_RE.search(value):
            raise ContractHold(
                "HOLD_MEMBER_PLAINTEXT_BOUNDARY:" + ".".join(path)
            )


def _parse_zulu(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ContractHold("HOLD_PACKET_TIME_INVALID")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)
    except ValueError as exc:
        raise ContractHold("HOLD_PACKET_TIME_INVALID") from exc


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ContractHold(code)


def _common_integrity() -> dict[str, Any]:
    return {
        "canonicalization": "UTF8_NFC_SORTED_KEYS_NO_WHITESPACE_NO_FLOATS",
        "hash_algorithm": "SHA-256",
        "hash_scope": "ALL_PACKET_FIELDS_EXCEPT_INTEGRITY_CONTENT_SHA256",
        "content_sha256": "0" * 64,
    }


def _root_integrity() -> dict[str, Any]:
    value = _common_integrity()
    value.update(
        {
            "member_proof_verification_required": True,
            "trusted_issuer_registry_verification_required": True,
        }
    )
    return value


def _generative_transmission(label: str) -> dict[str, Any]:
    return {
        "protocol": "W7TP_8D_INTENT_FIELD_PACKET",
        "state_packet_ref": ref("state_packet_ref", f"{label}:state"),
        "reconstruction_condition_ref": ref(
            "reconstruction_condition_ref", f"{label}:reconstruction"
        ),
        "equivalent_state_ref": ref(
            "equivalent_state_ref", f"{label}:equivalent-state"
        ),
        "total_field_verify_ref": ref(
            "total_field_verify_ref", f"{label}:total-field-verify"
        ),
        "ordinary_file_movement": False,
        "cloud_sync": False,
        "backup": False,
        "download_decryption": False,
    }


def synthetic_root(label: str = "member-one", generation: int = 1) -> dict[str, Any]:
    packet = {
        "schema_version": "W7TP-MEMBER-SOVEREIGN-IDENTITY-ROOT/1.0",
        "packet_type": "MEMBER_SOVEREIGN_IDENTITY_ROOT",
        "lifecycle": "CANDIDATE",
        "identity_root_ref": ref("member_identity_root_ref", f"{label}:stable-root"),
        "root_packet_ref": ref(
            "member_root_packet_ref", f"{label}:root-generation:{generation}"
        ),
        "subject_binding_ref": ref(
            "member_subject_binding_ref", f"{label}:protected-subject"
        ),
        "root_generation": generation,
        "previous_root_packet_ref": (
            None
            if generation == 1
            else ref(
                "member_root_packet_ref",
                f"{label}:root-generation:{generation - 1}",
            )
        ),
        "root_state": "ACTIVE_CANDIDATE",
        "rotation_epoch": generation - 1,
        "revocation_epoch": generation - 1,
        "identity_registry_ref": ref(
            "identity_registry_ref", f"{label}:identity-registry"
        ),
        "member_display_hash": digest(f"{label}:member-display"),
        "terms_version": "member-terms-v1",
        "member_verification_key_commitment": ref(
            "member_key_commitment", f"{label}:verification-key:{generation}"
        ),
        "member_verification_method_ref": ref(
            "member_verification_method_ref", f"{label}:method"
        ),
        "member_verification_proof_ref": ref(
            "member_proof_ref", f"{label}:root-proof:{generation}"
        ),
        "issuer_attestation_ref": ref(
            "issuer_attestation_ref", f"{label}:issuer-attestation:{generation}"
        ),
        "trusted_issuer_registry_ref": ref(
            "trusted_issuer_registry_ref", "p0:synthetic-trusted-issuers"
        ),
        "revocation_registry_ref": ref(
            "revocation_registry_ref", f"{label}:revocations"
        ),
        "rotation_policy_ref": ref("rotation_policy_ref", "member-root-rotation-v1"),
        "recovery_policy_ref": ref("recovery_policy_ref", "member-root-recovery-v1"),
        "verified_channel_binding_set_ref": ref(
            "verified_channel_binding_set_ref", f"{label}:channels"
        ),
        "root_policy": {
            "one_active_root_generation_per_member": True,
            "unique": True,
            "verifiable": True,
            "rotatable": True,
            "revocable": True,
            "recoverable": True,
            "non_bearer": True,
            "possession_conveys_authority": False,
            "permanent_roles_in_root": False,
            "permanent_scopes_in_root": False,
            "verified_channel_binding_is_sovereign_identity": False,
        },
        "authority_model": copy.deepcopy(AUTHORITY_MODEL),
        "candidate_only": True,
        "runtime_enabled": False,
        "formal_execution_authority": False,
        "authority_granted": False,
        "bearer_authority": False,
        "member_plaintext_included": False,
        "credential_material_included": False,
        "issued_at": FIXED_ISSUED_AT,
        "generative_transmission": _generative_transmission(
            f"{label}:root:{generation}"
        ),
        "integrity": _root_integrity(),
    }
    return seal_content(packet)


def synthetic_root_registry(root: dict[str, Any]) -> dict[str, Any]:
    return {
        "registry_ref": root["identity_registry_ref"],
        "entries": [
            {
                "identity_root_ref": root["identity_root_ref"],
                "root_packet_ref": root["root_packet_ref"],
                "subject_binding_ref": root["subject_binding_ref"],
                "root_generation": root["root_generation"],
                "revocation_epoch": root["revocation_epoch"],
                "current": True,
            }
        ],
    }


def synthetic_proof_registry(root: dict[str, Any]) -> dict[str, Any]:
    return {
        "registry_ref": root["trusted_issuer_registry_ref"],
        "proofs": {
            root["member_verification_proof_ref"]: {
                "identity_root_ref": root["identity_root_ref"],
                "root_packet_ref": root["root_packet_ref"],
                "subject_binding_ref": root["subject_binding_ref"],
                "root_generation": root["root_generation"],
                "member_verification_key_commitment": root[
                    "member_verification_key_commitment"
                ],
                "issuer_attestation_ref": root["issuer_attestation_ref"],
                "verification_state": "VERIFIED_CANDIDATE_EVIDENCE",
            }
        },
    }


def verify_root(
    root: dict[str, Any],
    *,
    root_registry_snapshot: dict[str, Any] | None,
    proof_registry_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    schema = load_schemas()["root"]
    validate_instance(schema, root)
    _walk_forbidden(root)
    _require(
        root["integrity"]["content_sha256"] == content_hash(root),
        "HOLD_ROOT_CONTENT_HASH_MISMATCH",
    )
    _require(
        root["root_state"] == "ACTIVE_CANDIDATE",
        "HOLD_ROOT_NOT_CURRENT_ACTIVE_CANDIDATE",
    )
    _require(root_registry_snapshot is not None, "HOLD_ROOT_REGISTRY_NOT_EVIDENCED")
    _require(
        root_registry_snapshot.get("registry_ref") == root["identity_registry_ref"],
        "HOLD_ROOT_REGISTRY_REF_MISMATCH",
    )
    entries = [
        item
        for item in root_registry_snapshot.get("entries", [])
        if item.get("current") is True
        and item.get("subject_binding_ref") == root["subject_binding_ref"]
    ]
    _require(len(entries) == 1, "HOLD_ROOT_UNIQUENESS_NOT_EVIDENCED")
    entry = entries[0]
    for key in (
        "identity_root_ref",
        "root_packet_ref",
        "root_generation",
        "revocation_epoch",
    ):
        _require(entry.get(key) == root[key], "HOLD_ROOT_REGISTRY_BINDING_MISMATCH")

    _require(proof_registry_snapshot is not None, "HOLD_ROOT_PROOF_NOT_EVIDENCED")
    _require(
        proof_registry_snapshot.get("registry_ref")
        == root["trusted_issuer_registry_ref"],
        "HOLD_ROOT_ISSUER_REGISTRY_MISMATCH",
    )
    proof = proof_registry_snapshot.get("proofs", {}).get(
        root["member_verification_proof_ref"]
    )
    _require(isinstance(proof, dict), "HOLD_ROOT_PROOF_INVALID")
    for key in (
        "identity_root_ref",
        "root_packet_ref",
        "subject_binding_ref",
        "root_generation",
        "member_verification_key_commitment",
        "issuer_attestation_ref",
    ):
        _require(proof.get(key) == root[key], "HOLD_ROOT_PROOF_INVALID")
    _require(
        proof.get("verification_state") == "VERIFIED_CANDIDATE_EVIDENCE",
        "HOLD_ROOT_PROOF_INVALID",
    )
    return {
        "state": "PASS_ROOT_CONTRACT_CANDIDATE",
        "authority_granted": False,
        "runtime_enabled": False,
    }


def synthetic_action_binding(
    root: dict[str, Any],
    *,
    label: str,
    session_ref: str | None,
    scene_ref: str | None,
    transaction: bool,
    purpose_ref_value: str | None = None,
    scope_ref_values: list[str] | None = None,
    effect_class: str | None = None,
) -> dict[str, Any]:
    target_ref = ref("target_ref", f"{label}:target")
    scope_refs = (
        [ref("scope_ref", f"{label}:scope")]
        if scope_ref_values is None
        else sorted(set(scope_ref_values))
    )
    binding = {
        "schema_version": "W7TP-MEMBER-ACTION-HASH-BASIS/1.0",
        "identity_root_ref": root["identity_root_ref"],
        "root_packet_ref": root["root_packet_ref"],
        "subject_binding_ref": root["subject_binding_ref"],
        "root_generation": root["root_generation"],
        "revocation_epoch": root["revocation_epoch"],
        "session_ref": session_ref,
        "scene_ref": scene_ref,
        "action_ref": ref("action_ref", f"{label}:action"),
        "action_code": "TRANSACTION_CANDIDATE" if transaction else "READ_CANDIDATE",
        "action_class": "TRANSACTION" if transaction else "NON_TRANSACTION",
        "target_ref": target_ref,
        "parameters_sha256": digest(f"{label}:parameters"),
        "purpose_ref": (
            ref("purpose_ref", f"{label}:purpose")
            if purpose_ref_value is None
            else purpose_ref_value
        ),
        "scope_refs": scope_refs,
        "resource_refs": [ref("resource_ref", f"{label}:resource")],
        "effect_class": (
            "E4_REVERSIBLE_WRITE"
            if effect_class is None and transaction
            else effect_class or "E1_READ"
        ),
        "member_display_hash": root["member_display_hash"],
        "terms_version": root["terms_version"],
        "amount_currency_hash_scope": (
            "CANONICAL_AMOUNT_MINOR_CURRENCY_TARGET_REF/1.0"
        ),
        "amount_currency_hash": (
            amount_currency_hash(25900, "TWD", target_ref) if transaction else None
        ),
        "action_hash_algorithm": "SHA256_CANONICAL_MEMBER_ACTION_BASIS/1.0",
        "action_hash": "0" * 64,
    }
    binding["action_hash"] = action_hash(binding)
    return binding


def _derived_base(
    root: dict[str, Any],
    packet_type: str,
    label: str,
    action_binding: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "W7TP-MEMBER-SOVEREIGN-DERIVED-PACKETS/1.0",
        "packet_type": packet_type,
        "lifecycle": "CANDIDATE",
        "derived_packet_ref": ref("member_derived_packet_ref", label),
        "identity_root_ref": root["identity_root_ref"],
        "root_packet_ref": root["root_packet_ref"],
        "subject_binding_ref": root["subject_binding_ref"],
        "root_generation": root["root_generation"],
        "revocation_epoch": root["revocation_epoch"],
        "member_display_hash": root["member_display_hash"],
        "terms_version": root["terms_version"],
        "issued_at": FIXED_ISSUED_AT,
        "expires_at": FIXED_EXPIRES_AT,
        "nonce_ref": ref("nonce_ref", f"{label}:nonce"),
        "replay_domain_ref": ref("replay_domain_ref", f"{label}:replay-domain"),
        "atomic_nonce_consumption_required": True,
        "action_binding": copy.deepcopy(action_binding),
        "payload": {},
        "authority_model": copy.deepcopy(AUTHORITY_MODEL),
        "candidate_only": True,
        "runtime_enabled": False,
        "formal_execution_authority": False,
        "authority_granted": False,
        "root_packet_accepted_as_action_credential": False,
        "member_plaintext_included": False,
        "credential_material_included": False,
        "generative_transmission": _generative_transmission(label),
        "integrity": _common_integrity(),
    }


def synthetic_derived_packets(root: dict[str, Any]) -> dict[str, dict[str, Any]]:
    session_ref = ref("member_session_ref", "member-one:session")
    scene_ref = ref("member_scene_ref", "member-one:scene")
    member_service_scope = ref("scope_ref", "member-one:member-service")
    transaction_purpose = ref(
        "purpose_ref", "member-one:transaction-purpose"
    )
    session_action = synthetic_action_binding(
        root,
        label="member-one:open-session",
        session_ref=session_ref,
        scene_ref=None,
        transaction=False,
        scope_ref_values=[member_service_scope],
        effect_class="E1_READ",
    )
    transaction_action = synthetic_action_binding(
        root,
        label="member-one:scene-action",
        session_ref=session_ref,
        scene_ref=scene_ref,
        transaction=True,
        purpose_ref_value=transaction_purpose,
        scope_ref_values=[member_service_scope],
        effect_class="E4_REVERSIBLE_WRITE",
    )
    no_parent_action = synthetic_action_binding(
        root,
        label="member-one:root-governance",
        session_ref=None,
        scene_ref=None,
        transaction=False,
        effect_class="E4_REVERSIBLE_WRITE",
    )

    session = _derived_base(
        root, "MEMBER_SESSION", "member-one:session-packet", session_action
    )
    session["payload"] = {
        "session_ref": session_ref,
        "subject_binding_ref": root["subject_binding_ref"],
        "audience_ref": ref("audience_ref", "member-one:local-member-interface"),
        "scope_refs": [member_service_scope],
        "role_refs": [],
        "role_table_snapshot_ref": ref(
            "role_table_snapshot_ref", "member-one:role-table"
        ),
        "role_table_snapshot_hash": digest("member-one:role-table"),
        "verified_channel_binding_ref": ref(
            "verified_channel_binding_ref", "member-one:verified-channel"
        ),
        "device_binding_ref": ref(
            "device_binding_ref", "member-one:local-device"
        ),
        "session_proof_ref": ref("session_proof_ref", "member-one:session-proof"),
        "nonce_consumption_required": True,
        "root_packet_as_credential_accepted": False,
        "issuing_process_authority": "odoo",
    }

    scene = _derived_base(
        root, "MEMBER_SCENE", "member-one:scene-packet", transaction_action
    )
    scene["payload"] = {
        "session_ref": session_ref,
        "scene_ref": scene_ref,
        "scene_type_ref": ref("scene_type_ref", "member-one:merchant-scene"),
        "purpose_ref": transaction_purpose,
        "scope_refs": [member_service_scope],
        "capability_refs": [ref("capability_ref", "member-one:transaction-candidate")],
        "action_hash": transaction_action["action_hash"],
        "parent_session_required": True,
        "issuing_process_authority": "odoo",
    }

    consent = _derived_base(
        root, "MEMBER_CONSENT", "member-one:consent-packet", transaction_action
    )
    consent["payload"] = {
        "consent_ref": ref("member_consent_ref", "member-one:consent"),
        "session_ref": session_ref,
        "scene_ref": scene_ref,
        "decision": "CONSENT",
        "purpose_ref": transaction_purpose,
        "scope_refs": [member_service_scope],
        "action_hash": transaction_action["action_hash"],
        "amount_currency_hash": transaction_action["amount_currency_hash"],
        "member_proof_ref": ref("member_proof_ref", "member-one:consent-proof"),
        "supersedes_consent_ref": None,
        "independent_from_total_field_receipt": True,
        "decision_authority": "member",
    }

    revocation = _derived_base(
        root, "MEMBER_REVOCATION", "member-one:revocation-packet", no_parent_action
    )
    revocation["payload"] = {
        "revocation_ref": ref("member_revocation_ref", "member-one:revocation"),
        "target_type": "SESSION",
        "target_ref": session_ref,
        "previous_revocation_epoch": root["revocation_epoch"],
        "new_revocation_epoch": root["revocation_epoch"] + 1,
        "effective_at": "2026-07-25T00:02:00Z",
        "reason_code": "MEMBER_REQUEST",
        "member_or_recovery_proof_ref": ref(
            "member_proof_ref", "member-one:revocation-proof"
        ),
        "monotonic_epoch_required": True,
        "invalidates_descendants": True,
        "revocation_authority": "member",
    }

    recovery = _derived_base(
        root, "MEMBER_RECOVERY", "member-one:recovery-packet", no_parent_action
    )
    recovery["payload"] = {
        "recovery_ref": ref("member_recovery_ref", "member-one:recovery"),
        "previous_root_packet_ref": root["root_packet_ref"],
        "expected_root_generation": root["root_generation"],
        "expected_revocation_epoch": root["revocation_epoch"],
        "new_root_packet_ref": ref(
            "member_root_packet_ref",
            f"member-one:root-generation:{root['root_generation'] + 1}",
        ),
        "new_root_generation": root["root_generation"] + 1,
        "new_member_key_commitment": ref(
            "member_key_commitment",
            f"member-one:verification-key:{root['root_generation'] + 1}",
        ),
        "recovery_policy_ref": root["recovery_policy_ref"],
        "recovery_factor_refs": [
            ref("recovery_factor_ref", "member-one:factor-one"),
            ref("recovery_factor_ref", "member-one:factor-two"),
        ],
        "recovery_quorum_ref": ref(
            "recovery_quorum_ref", "member-one:recovery-quorum"
        ),
        "challenge_ref": ref(
            "recovery_challenge_ref", "member-one:recovery-challenge"
        ),
        "compare_and_swap_ref": ref(
            "recovery_cas_ref", "member-one:recovery-cas"
        ),
        "unique_completion_ref": ref(
            "recovery_completion_ref", "member-one:recovery-completion"
        ),
        "cooldown_until": "2026-07-25T00:05:00Z",
        "recovery_state": "PENDING_CANDIDATE",
        "old_root_revoked_on_success": True,
        "descendants_invalidated_on_success": True,
        "atomic_compare_and_swap_required": True,
        "recovery_authority": "member",
    }

    role_seat = _derived_base(
        root,
        "MEMBER_ROLE_SEAT_LEASE",
        "member-one:founder-seat-packet",
        transaction_action,
    )
    role_seat["payload"] = {
        "role_seat_ref": ref("member_role_seat_ref", "member-one:founder-seat"),
        "session_ref": session_ref,
        "scene_ref": scene_ref,
        "organization_ref": ref("organization_ref", "member-one:organization"),
        "role_ref": ref("role_ref", "founder"),
        "seat_ref": ref("seat_ref", "founder-seat"),
        "scope_refs": [member_service_scope],
        "role_table_snapshot_ref": ref(
            "role_table_snapshot_ref", "member-one:role-table"
        ),
        "role_table_snapshot_hash": digest("member-one:role-table"),
        "lease_ref": ref("seat_lease_ref", "member-one:founder-seat-lease"),
        "seat_lease_cas_ref": ref(
            "seat_lease_cas_ref", "member-one:founder-seat-cas"
        ),
        "transferable": False,
        "subdelegation_allowed": False,
        "founder_role_requires_explicit_member_root_binding": True,
        "atomic_seat_lease_required": True,
        "issuing_process_authority": "odoo",
    }

    packets = {
        "session": session,
        "scene": scene,
        "consent": consent,
        "revocation": revocation,
        "recovery": recovery,
        "role_seat": role_seat,
    }
    return {name: seal_content(packet) for name, packet in packets.items()}


def synthetic_role_seat_registry(
    root: dict[str, Any], role_seat_packet: dict[str, Any]
) -> dict[str, Any]:
    payload = role_seat_packet["payload"]
    return {
        "registry_ref": payload["role_table_snapshot_ref"],
        "registry_sha256": payload["role_table_snapshot_hash"],
        "seat_lease_cas_ref": payload["seat_lease_cas_ref"],
        "active_lease_refs": [],
        "entries": [
            {
                "identity_root_ref": root["identity_root_ref"],
                "role_ref": payload["role_ref"],
                "seat_ref": payload["seat_ref"],
                "scene_ref": payload["scene_ref"],
                "state": "AVAILABLE_CANDIDATE",
            }
        ],
    }


def verify_derived_packet(
    packet: dict[str, Any],
    root: dict[str, Any],
    *,
    root_registry_snapshot: dict[str, Any] | None,
    proof_registry_snapshot: dict[str, Any] | None,
    seen_nonces: set[tuple[str, str]] | None,
    role_seat_registry_snapshot: dict[str, Any] | None = None,
    now: str = FIXED_NOW,
) -> dict[str, Any]:
    verify_root(
        root,
        root_registry_snapshot=root_registry_snapshot,
        proof_registry_snapshot=proof_registry_snapshot,
    )
    schema = load_schemas()["derived"]
    validate_instance(schema, packet)
    _walk_forbidden(packet)
    _require(
        packet["integrity"]["content_sha256"] == content_hash(packet),
        "HOLD_DERIVED_CONTENT_HASH_MISMATCH",
    )
    for key in (
        "identity_root_ref",
        "root_packet_ref",
        "subject_binding_ref",
        "root_generation",
        "revocation_epoch",
        "member_display_hash",
        "terms_version",
    ):
        _require(packet[key] == root[key], "HOLD_DERIVED_ROOT_BINDING")

    binding = packet["action_binding"]
    for key in (
        "identity_root_ref",
        "root_packet_ref",
        "subject_binding_ref",
        "root_generation",
        "revocation_epoch",
        "member_display_hash",
        "terms_version",
    ):
        _require(binding[key] == packet[key], "HOLD_ACTION_ROOT_BINDING_MISMATCH")
    _require(
        binding["action_hash"] == action_hash(binding),
        "HOLD_ACTION_HASH_MISMATCH",
    )

    issued_at = _parse_zulu(packet["issued_at"])
    expires_at = _parse_zulu(packet["expires_at"])
    current = _parse_zulu(now)
    _require(issued_at <= current < expires_at, "HOLD_DERIVED_PACKET_TIME_INVALID")
    ttl_seconds = int((expires_at - issued_at).total_seconds())
    max_ttl = (
        86400
        if packet["packet_type"] in {"MEMBER_REVOCATION", "MEMBER_RECOVERY"}
        else 3600
    )
    _require(0 < ttl_seconds <= max_ttl, "HOLD_DERIVED_PACKET_TTL_INVALID")

    _require(seen_nonces is not None, "HOLD_REPLAY_LEDGER_NOT_EVIDENCED")
    replay_key = (packet["replay_domain_ref"], packet["nonce_ref"])
    _require(replay_key not in seen_nonces, "HOLD_DERIVED_PACKET_REPLAY")
    seen_nonces.add(replay_key)

    payload = packet["payload"]
    packet_type = packet["packet_type"]
    if packet_type == "MEMBER_SESSION":
        _require(
            binding["session_ref"] == payload["session_ref"]
            and binding["scene_ref"] is None,
            "HOLD_DERIVED_SESSION_BINDING",
        )
        _require(
            payload["subject_binding_ref"] == root["subject_binding_ref"],
            "HOLD_DERIVED_CROSS_MEMBER",
        )
    elif packet_type in {
        "MEMBER_SCENE",
        "MEMBER_CONSENT",
        "MEMBER_ROLE_SEAT_LEASE",
    }:
        _require(
            binding["session_ref"] == payload["session_ref"]
            and binding["scene_ref"] == payload["scene_ref"],
            "HOLD_DERIVED_SESSION_SCENE_BINDING",
        )
    else:
        _require(
            binding["session_ref"] is None and binding["scene_ref"] is None,
            "HOLD_DERIVED_ROOT_GOVERNANCE_BINDING",
        )

    if packet_type == "MEMBER_SCENE":
        _require(
            payload["purpose_ref"] == binding["purpose_ref"],
            "HOLD_ACTION_PURPOSE_MISMATCH",
        )
        _require(
            set(payload["scope_refs"]) == set(binding["scope_refs"]),
            "HOLD_ACTION_SCOPE_MISMATCH",
        )
        _require(
            payload["action_hash"] == binding["action_hash"],
            "HOLD_ACTION_HASH_MISMATCH",
        )
    elif packet_type == "MEMBER_CONSENT":
        _require(
            payload["purpose_ref"] == binding["purpose_ref"],
            "HOLD_ACTION_PURPOSE_MISMATCH",
        )
        _require(
            set(payload["scope_refs"]) == set(binding["scope_refs"]),
            "HOLD_ACTION_SCOPE_MISMATCH",
        )
        _require(
            payload["action_hash"] == binding["action_hash"],
            "HOLD_ACTION_HASH_MISMATCH",
        )
        _require(
            payload["amount_currency_hash"] == binding["amount_currency_hash"],
            "HOLD_AMOUNT_CURRENCY_HASH_MISMATCH",
        )
    elif packet_type == "MEMBER_REVOCATION":
        _require(
            payload["new_revocation_epoch"]
            > payload["previous_revocation_epoch"],
            "HOLD_REVOCATION_EPOCH_RACE",
        )
        _require(
            payload["previous_revocation_epoch"] == root["revocation_epoch"],
            "HOLD_REVOCATION_EPOCH_STALE",
        )
    elif packet_type == "MEMBER_RECOVERY":
        _require(
            payload["previous_root_packet_ref"] == root["root_packet_ref"],
            "HOLD_RECOVERY_ROOT_MISMATCH",
        )
        _require(
            payload["expected_root_generation"] == root["root_generation"]
            and payload["expected_revocation_epoch"] == root["revocation_epoch"],
            "HOLD_RECOVERY_COMPARE_AND_SWAP_MISMATCH",
        )
        _require(
            payload["new_root_generation"] == root["root_generation"] + 1
            and payload["new_root_packet_ref"] != root["root_packet_ref"],
            "HOLD_RECOVERY_ROTATION_RACE",
        )
    elif packet_type == "MEMBER_ROLE_SEAT_LEASE":
        _require(
            set(payload["scope_refs"]) == set(binding["scope_refs"]),
            "HOLD_ACTION_SCOPE_MISMATCH",
        )
        _require(
            role_seat_registry_snapshot is not None,
            "HOLD_ROLE_SEAT_REGISTRY_NOT_EVIDENCED",
        )
        _require(
            role_seat_registry_snapshot.get("registry_ref")
            == payload["role_table_snapshot_ref"]
            and role_seat_registry_snapshot.get("registry_sha256")
            == payload["role_table_snapshot_hash"],
            "HOLD_ROLE_SEAT_SNAPSHOT_MISMATCH",
        )
        matching_entries = [
            entry
            for entry in role_seat_registry_snapshot.get("entries", [])
            if entry.get("identity_root_ref") == root["identity_root_ref"]
            and entry.get("role_ref") == payload["role_ref"]
            and entry.get("seat_ref") == payload["seat_ref"]
            and entry.get("scene_ref") == payload["scene_ref"]
            and entry.get("state") == "AVAILABLE_CANDIDATE"
        ]
        _require(len(matching_entries) == 1, "HOLD_FOUNDER_SEAT_BINDING")
        _require(
            role_seat_registry_snapshot.get("seat_lease_cas_ref")
            == payload["seat_lease_cas_ref"]
            and role_seat_registry_snapshot.get("active_lease_refs") == [],
            "HOLD_SEAT_LEASE_RACE",
        )
    return {
        "state": f"PASS_{packet_type}_CONTRACT_CANDIDATE",
        "authority_granted": False,
        "runtime_enabled": False,
    }


def verify_derived_chain(
    packets: dict[str, dict[str, Any]],
    root: dict[str, Any],
    *,
    root_registry_snapshot: dict[str, Any] | None,
    proof_registry_snapshot: dict[str, Any] | None,
    role_seat_registry_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    seen_nonces: set[tuple[str, str]] = set()
    for packet in packets.values():
        verify_derived_packet(
            packet,
            root,
            root_registry_snapshot=root_registry_snapshot,
            proof_registry_snapshot=proof_registry_snapshot,
            seen_nonces=seen_nonces,
            role_seat_registry_snapshot=role_seat_registry_snapshot,
        )
    session = packets["session"]
    scene = packets["scene"]
    consent = packets["consent"]
    _require(
        scene["payload"]["session_ref"] == session["payload"]["session_ref"],
        "HOLD_SCENE_SESSION_MISMATCH",
    )
    _require(
        consent["payload"]["session_ref"] == session["payload"]["session_ref"]
        and consent["payload"]["scene_ref"] == scene["payload"]["scene_ref"],
        "HOLD_CONSENT_SESSION_SCENE_MISMATCH",
    )
    _require(
        set(scene["payload"]["scope_refs"])
        <= set(session["payload"]["scope_refs"]),
        "HOLD_SCENE_SCOPE_EXPANSION",
    )
    _require(
        set(consent["payload"]["scope_refs"])
        <= set(scene["payload"]["scope_refs"]),
        "HOLD_CONSENT_SCOPE_EXPANSION",
    )
    _require(
        consent["action_binding"]["action_hash"]
        == scene["action_binding"]["action_hash"],
        "HOLD_ACTION_HASH_RECEIPT_MISMATCH",
    )
    return {
        "state": "PASS_DERIVED_CHAIN_CONTRACT_CANDIDATE",
        "packet_count": len(packets),
        "authority_granted": False,
    }


def synthetic_dual_receipt(
    root: dict[str, Any],
    action_binding_value: dict[str, Any],
    *,
    member_decision: str = "CONSENT",
    total_field_decision: str = "PASS",
    odoo_state: str = "BOUND",
) -> dict[str, Any]:
    action = copy.deepcopy(action_binding_value)
    member_receipt = {
        "receipt_ref": ref(
            "member_consent_receipt_ref", "member-one:member-receipt"
        ),
        "authority": "member",
        "decision": member_decision,
        "identity_root_ref": root["identity_root_ref"],
        "root_packet_ref": root["root_packet_ref"],
        "subject_binding_ref": root["subject_binding_ref"],
        "root_generation": root["root_generation"],
        "revocation_epoch": root["revocation_epoch"],
        "session_ref": action["session_ref"],
        "scene_ref": action["scene_ref"],
        "action_hash": action["action_hash"],
        "purpose_ref": action["purpose_ref"],
        "scope_refs": action["scope_refs"],
        "effect_class": action["effect_class"],
        "member_display_hash": action["member_display_hash"],
        "terms_version": action["terms_version"],
        "amount_currency_hash": action["amount_currency_hash"],
        "member_proof_ref": ref(
            "member_proof_ref", "member-one:member-receipt-proof"
        ),
        "member_verification_key_commitment": root[
            "member_verification_key_commitment"
        ],
        "member_verification_method_ref": root[
            "member_verification_method_ref"
        ],
        "trusted_member_proof_registry_ref": ref(
            "trusted_member_proof_registry_ref",
            "p0:synthetic-member-proof-registry",
        ),
        "member_proof_verification_required": True,
        "issued_at": FIXED_ISSUED_AT,
        "expires_at": FIXED_EXPIRES_AT,
        "nonce_ref": ref("nonce_ref", "member-one:member-receipt-nonce"),
        "nonce_consumption_required": True,
        "independent_receipt": True,
        "receipt_hash_algorithm": (
            "SHA256_CANONICAL_RECEIPT_EXCLUDING_RECEIPT_SHA256/1.0"
        ),
        "receipt_sha256": "0" * 64,
    }
    total_field_receipt = {
        "receipt_ref": ref(
            "total_field_receipt_ref", "member-one:total-field-receipt"
        ),
        "authority": "total_field_verifier",
        "decision": total_field_decision,
        "identity_root_ref": root["identity_root_ref"],
        "root_packet_ref": root["root_packet_ref"],
        "subject_binding_ref": root["subject_binding_ref"],
        "root_generation": root["root_generation"],
        "revocation_epoch": root["revocation_epoch"],
        "session_ref": action["session_ref"],
        "scene_ref": action["scene_ref"],
        "action_hash": action["action_hash"],
        "purpose_ref": action["purpose_ref"],
        "scope_refs": action["scope_refs"],
        "effect_class": action["effect_class"],
        "member_display_hash": action["member_display_hash"],
        "terms_version": action["terms_version"],
        "amount_currency_hash": action["amount_currency_hash"],
        "verifier_ref": ref(
            "total_field_verifier_ref", "p0:synthetic-total-field-verifier"
        ),
        "verifier_version": "p0-contract-v1",
        "evidence_refs": [
            ref("evidence_ref", "member-one:total-field-safety-evidence")
        ],
        "verification_result_hash": digest(
            "member-one:synthetic-total-field-result"
        ),
        "issued_at": FIXED_ISSUED_AT,
        "expires_at": FIXED_EXPIRES_AT,
        "nonce_ref": ref("nonce_ref", "member-one:total-field-receipt-nonce"),
        "nonce_consumption_required": True,
        "independent_receipt": True,
        "receipt_hash_algorithm": (
            "SHA256_CANONICAL_RECEIPT_EXCLUDING_RECEIPT_SHA256/1.0"
        ),
        "receipt_sha256": "0" * 64,
    }
    member_receipt = seal_receipt(member_receipt)
    total_field_receipt = seal_receipt(total_field_receipt)

    if member_decision in {"DENY", "WITHDRAW"} or total_field_decision == "BLOCK":
        aggregate_state = "BLOCK"
    elif (
        member_decision == "CONSENT"
        and total_field_decision == "PASS"
        and odoo_state == "BOUND"
    ):
        aggregate_state = "READY_CANDIDATE"
    else:
        aggregate_state = "HOLD"

    packet = {
        "schema_version": "W7TP-MEMBER-ACTION-DUAL-RECEIPT/1.0",
        "packet_type": "MEMBER_ACTION_DUAL_RECEIPT",
        "lifecycle": "CANDIDATE",
        "receipt_set_ref": ref(
            "member_dual_receipt_set_ref", "member-one:dual-receipt-set"
        ),
        "identity_root_ref": root["identity_root_ref"],
        "root_packet_ref": root["root_packet_ref"],
        "subject_binding_ref": root["subject_binding_ref"],
        "root_generation": root["root_generation"],
        "revocation_epoch": root["revocation_epoch"],
        "session_ref": action["session_ref"],
        "scene_ref": action["scene_ref"],
        "action_binding": action,
        "member_receipt": member_receipt,
        "total_field_receipt": total_field_receipt,
        "odoo_binding": {
            "authority": "odoo",
            "not_authorization_receipt": True,
            "workflow_ref": ref(
                "odoo_workflow_ref", "member-one:synthetic-workflow"
            ),
            "workflow_state_hash": digest("member-one:synthetic-workflow-state"),
            "action_hash": action["action_hash"],
            "state": odoo_state,
        },
        "aggregate_state": aggregate_state,
        "join_policy": {
            "member_receipt_required": True,
            "total_field_receipt_required": True,
            "odoo_process_binding_required": True,
            "independent_receipt_authorities_required": True,
            "action_hash_equality_required": True,
            "purpose_ref_equality_required": True,
            "scope_refs_equality_required": True,
            "effect_class_equality_required": True,
            "member_display_hash_equality_required": True,
            "terms_version_equality_required": True,
            "amount_currency_hash_equality_required": True,
            "durable_atomic_nonce_consumption_required": True,
            "root_session_scene_equality_required": True,
            "revocation_epoch_equality_required": True,
            "ready_state_is_candidate_only": True,
            "execution_authority_granted": False,
        },
        "authority_model": copy.deepcopy(AUTHORITY_MODEL),
        "candidate_only": True,
        "runtime_enabled": False,
        "formal_execution_authority": False,
        "authority_granted": False,
        "member_plaintext_included": False,
        "credential_material_included": False,
        "raw_amount_currency_included": False,
        "generative_transmission": _generative_transmission(
            "member-one:dual-receipt"
        ),
        "integrity": _common_integrity(),
    }
    return seal_content(packet)


def synthetic_member_proof_registry(
    root: dict[str, Any], dual_receipt: dict[str, Any]
) -> dict[str, Any]:
    member = dual_receipt["member_receipt"]
    action = dual_receipt["action_binding"]
    return {
        "registry_ref": member["trusted_member_proof_registry_ref"],
        "proofs": {
            member["member_proof_ref"]: {
                "receipt_ref": member["receipt_ref"],
                "identity_root_ref": root["identity_root_ref"],
                "root_packet_ref": root["root_packet_ref"],
                "subject_binding_ref": root["subject_binding_ref"],
                "root_generation": root["root_generation"],
                "revocation_epoch": root["revocation_epoch"],
                "member_verification_key_commitment": root[
                    "member_verification_key_commitment"
                ],
                "member_verification_method_ref": root[
                    "member_verification_method_ref"
                ],
                "action_hash": action["action_hash"],
                "purpose_ref": action["purpose_ref"],
                "scope_refs": action["scope_refs"],
                "effect_class": action["effect_class"],
                "member_display_hash": action["member_display_hash"],
                "terms_version": action["terms_version"],
                "amount_currency_hash": action["amount_currency_hash"],
                "verification_state": "VERIFIED_CANDIDATE_EVIDENCE",
            }
        },
    }


def verify_dual_receipt(
    packet: dict[str, Any],
    root: dict[str, Any],
    *,
    root_registry_snapshot: dict[str, Any] | None,
    proof_registry_snapshot: dict[str, Any] | None,
    member_proof_registry_snapshot: dict[str, Any] | None,
    seen_nonces: set[tuple[str, str]] | None,
    now: str = FIXED_NOW,
) -> dict[str, Any]:
    verify_root(
        root,
        root_registry_snapshot=root_registry_snapshot,
        proof_registry_snapshot=proof_registry_snapshot,
    )
    schema = load_schemas()["dual_receipt"]
    validate_instance(schema, packet)
    _walk_forbidden(packet)
    _require(
        packet["integrity"]["content_sha256"] == content_hash(packet),
        "HOLD_DUAL_RECEIPT_CONTENT_HASH_MISMATCH",
    )
    for key in (
        "identity_root_ref",
        "root_packet_ref",
        "subject_binding_ref",
        "root_generation",
        "revocation_epoch",
    ):
        _require(packet[key] == root[key], "HOLD_RECEIPT_ROOT_BINDING_MISMATCH")

    action = packet["action_binding"]
    _require(action["action_hash"] == action_hash(action), "HOLD_ACTION_HASH_MISMATCH")
    for key in (
        "identity_root_ref",
        "root_packet_ref",
        "subject_binding_ref",
        "root_generation",
        "revocation_epoch",
    ):
        _require(
            action[key] == packet[key],
            "HOLD_ACTION_ROOT_BINDING_MISMATCH",
        )
    _require(
        action["member_display_hash"] == root["member_display_hash"]
        and action["terms_version"] == root["terms_version"],
        "HOLD_ACTION_ROOT_BINDING_MISMATCH",
    )
    _require(
        packet["session_ref"] == action["session_ref"]
        and packet["scene_ref"] == action["scene_ref"],
        "HOLD_RECEIPT_SESSION_SCENE_MISMATCH",
    )
    member = packet["member_receipt"]
    total_field = packet["total_field_receipt"]
    _require(
        member["receipt_sha256"] == receipt_hash(member),
        "HOLD_MEMBER_RECEIPT_HASH_MISMATCH",
    )
    _require(
        total_field["receipt_sha256"] == receipt_hash(total_field),
        "HOLD_TOTAL_FIELD_RECEIPT_HASH_MISMATCH",
    )
    _require(
        member["member_verification_key_commitment"]
        == root["member_verification_key_commitment"]
        and member["member_verification_method_ref"]
        == root["member_verification_method_ref"],
        "HOLD_MEMBER_RECEIPT_PROOF_BINDING_MISMATCH",
    )
    _require(
        member_proof_registry_snapshot is not None,
        "HOLD_MEMBER_PROOF_REGISTRY_NOT_EVIDENCED",
    )
    _require(
        member_proof_registry_snapshot.get("registry_ref")
        == member["trusted_member_proof_registry_ref"],
        "HOLD_MEMBER_PROOF_REGISTRY_MISMATCH",
    )
    member_proof = member_proof_registry_snapshot.get("proofs", {}).get(
        member["member_proof_ref"]
    )
    _require(isinstance(member_proof, dict), "HOLD_MEMBER_RECEIPT_INVALID")
    proof_expected = {
        "receipt_ref": member["receipt_ref"],
        "identity_root_ref": root["identity_root_ref"],
        "root_packet_ref": root["root_packet_ref"],
        "subject_binding_ref": root["subject_binding_ref"],
        "root_generation": root["root_generation"],
        "revocation_epoch": root["revocation_epoch"],
        "member_verification_key_commitment": root[
            "member_verification_key_commitment"
        ],
        "member_verification_method_ref": root["member_verification_method_ref"],
        "action_hash": action["action_hash"],
        "purpose_ref": action["purpose_ref"],
        "scope_refs": action["scope_refs"],
        "effect_class": action["effect_class"],
        "member_display_hash": action["member_display_hash"],
        "terms_version": action["terms_version"],
        "amount_currency_hash": action["amount_currency_hash"],
        "verification_state": "VERIFIED_CANDIDATE_EVIDENCE",
    }
    _require(
        all(member_proof.get(key) == value for key, value in proof_expected.items()),
        "HOLD_MEMBER_RECEIPT_INVALID",
    )

    common = {
        "identity_root_ref": packet["identity_root_ref"],
        "root_packet_ref": packet["root_packet_ref"],
        "subject_binding_ref": packet["subject_binding_ref"],
        "root_generation": packet["root_generation"],
        "revocation_epoch": packet["revocation_epoch"],
        "session_ref": packet["session_ref"],
        "scene_ref": packet["scene_ref"],
        "action_hash": action["action_hash"],
        "purpose_ref": action["purpose_ref"],
        "scope_refs": action["scope_refs"],
        "effect_class": action["effect_class"],
        "member_display_hash": action["member_display_hash"],
        "terms_version": action["terms_version"],
        "amount_currency_hash": action["amount_currency_hash"],
    }
    mismatch_codes = {
        "action_hash": "HOLD_ACTION_HASH_RECEIPT_MISMATCH",
        "purpose_ref": "HOLD_PURPOSE_REF_MISMATCH",
        "scope_refs": "HOLD_SCOPE_REFS_MISMATCH",
        "effect_class": "HOLD_EFFECT_CLASS_MISMATCH",
        "member_display_hash": "HOLD_MEMBER_DISPLAY_HASH_MISMATCH",
        "terms_version": "HOLD_TERMS_VERSION_MISMATCH",
        "amount_currency_hash": "HOLD_AMOUNT_CURRENCY_HASH_MISMATCH",
    }
    for receipt in (member, total_field):
        for key, expected in common.items():
            _require(
                receipt[key] == expected,
                mismatch_codes.get(key, "HOLD_RECEIPT_SUBJECT_MISMATCH"),
            )

    _require(
        packet["odoo_binding"]["action_hash"] == action["action_hash"],
        "HOLD_ACTION_HASH_RECEIPT_MISMATCH",
    )
    _require(seen_nonces is not None, "HOLD_REPLAY_LEDGER_NOT_EVIDENCED")
    current = _parse_zulu(now)
    for receipt in (member, total_field):
        _require(
            _parse_zulu(receipt["issued_at"])
            <= current
            < _parse_zulu(receipt["expires_at"]),
            "HOLD_RECEIPT_TIME_INVALID",
        )
        replay_key = (receipt["authority"], receipt["nonce_ref"])
        _require(replay_key not in seen_nonces, "HOLD_RECEIPT_REPLAY")
        seen_nonces.add(replay_key)

    if member["decision"] in {"DENY", "WITHDRAW"} or total_field["decision"] == "BLOCK":
        expected_state = "BLOCK"
        result_state = "BLOCK_MEMBER_OR_TOTAL_FIELD_DECISION"
    elif (
        member["decision"] == "CONSENT"
        and total_field["decision"] == "PASS"
        and packet["odoo_binding"]["state"] == "BOUND"
    ):
        expected_state = "READY_CANDIDATE"
        result_state = "PASS_DUAL_RECEIPT_READY_CANDIDATE"
    else:
        expected_state = "HOLD"
        result_state = "HOLD_DUAL_RECEIPT_NOT_READY"
    _require(
        packet["aggregate_state"] == expected_state,
        "HOLD_AGGREGATE_STATE_MISMATCH",
    )
    return {
        "state": result_state,
        "candidate_only": True,
        "authority_granted": False,
        "runtime_enabled": False,
    }


def verify_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    resolved = path.resolve()
    _require(resolved == MANIFEST_PATH.resolve(), "HOLD_MANIFEST_PATH_NOT_ALLOWED")
    manifest = load_json(resolved)
    _require(
        manifest.get("self_hash", {}).get("included") is False,
        "HOLD_MANIFEST_SELF_HASH_POLICY",
    )
    file_entries = manifest.get("files")
    _require(isinstance(file_entries, list), "HOLD_MANIFEST_FILES_INVALID")
    paths = [entry.get("path") for entry in file_entries]
    _require(paths == sorted(MANIFEST_FILES), "HOLD_MANIFEST_PATH_SET_MISMATCH")
    _require(len(paths) == len(set(paths)), "HOLD_MANIFEST_DUPLICATE_PATH")
    lines: list[str] = []
    for entry in file_entries:
        relative = entry["path"]
        relative_path = Path(relative)
        _require(
            not relative_path.is_absolute() and ".." not in relative_path.parts,
            "HOLD_MANIFEST_PATH_TRAVERSAL",
        )
        file_path = ROOT / relative_path
        data = file_path.read_bytes()
        actual_sha256 = hashlib.sha256(data).hexdigest()
        _require(
            entry.get("sha256") == actual_sha256,
            "HOLD_MANIFEST_FILE_HASH_MISMATCH",
        )
        _require(entry.get("size") == len(data), "HOLD_MANIFEST_FILE_SIZE_MISMATCH")
        lines.append(f"{actual_sha256}  {relative}\n")
    content_sha256 = hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
    _require(
        manifest.get("content_sha256") == content_sha256,
        "HOLD_MANIFEST_CONTENT_HASH_MISMATCH",
    )
    for flag in (
        "canonical_write",
        "runtime_activation",
        "deploy",
        "database_write",
        "odoo_upgrade",
        "restart",
        "pos_action",
        "payment_action",
        "oauth_action",
    ):
        _require(manifest.get(flag) is False, "HOLD_MANIFEST_EFFECT_FLAG")
    _require(manifest.get("candidate_only") is True, "HOLD_MANIFEST_CANDIDATE_ONLY")
    _require(manifest.get("final_decision") is None, "HOLD_MANIFEST_FINAL_DECISION")
    return {
        "state": "PASS_SHA256_MANIFEST",
        "file_count": len(file_entries),
        "content_sha256": content_sha256,
    }


def _expect_schema_reject(
    schema: dict[str, Any], instance: dict[str, Any], label: str
) -> str:
    try:
        validate_instance(schema, instance)
    except ValidationError:
        return label
    raise RuntimeError(f"red_team_case_accepted:{label}")


def _expect_hold(callable_object: Any, expected_code: str, label: str) -> str:
    try:
        callable_object()
    except ContractHold as exc:
        if exc.code != expected_code:
            raise RuntimeError(
                f"red_team_wrong_hold:{label}:{exc.code}:{expected_code}"
            ) from exc
        return label
    raise RuntimeError(f"red_team_case_accepted:{label}")


def run_contract_self_check() -> dict[str, Any]:
    schemas = check_schemas()
    root = synthetic_root()
    root_registry = synthetic_root_registry(root)
    proof_registry = synthetic_proof_registry(root)
    verify_root(
        root,
        root_registry_snapshot=root_registry,
        proof_registry_snapshot=proof_registry,
    )
    packets = synthetic_derived_packets(root)
    role_seat_registry = synthetic_role_seat_registry(root, packets["role_seat"])
    verify_derived_chain(
        packets,
        root,
        root_registry_snapshot=root_registry,
        proof_registry_snapshot=proof_registry,
        role_seat_registry_snapshot=role_seat_registry,
    )
    dual = synthetic_dual_receipt(root, packets["consent"]["action_binding"])
    member_proof_registry = synthetic_member_proof_registry(root, dual)
    verify_dual_receipt(
        dual,
        root,
        root_registry_snapshot=root_registry,
        proof_registry_snapshot=proof_registry,
        member_proof_registry_snapshot=member_proof_registry,
        seen_nonces=set(),
    )

    def check_derived(
        packet: dict[str, Any],
        *,
        seen_nonces: set[tuple[str, str]] | None = None,
    ) -> dict[str, Any]:
        return verify_derived_packet(
            packet,
            root,
            root_registry_snapshot=root_registry,
            proof_registry_snapshot=proof_registry,
            seen_nonces=set() if seen_nonces is None else seen_nonces,
            role_seat_registry_snapshot=role_seat_registry,
        )

    def check_dual(
        packet: dict[str, Any],
        *,
        seen_nonces: set[tuple[str, str]] | None = None,
        member_registry: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return verify_dual_receipt(
            packet,
            root,
            root_registry_snapshot=root_registry,
            proof_registry_snapshot=proof_registry,
            member_proof_registry_snapshot=(
                synthetic_member_proof_registry(root, packet)
                if member_registry is None
                else member_registry
            ),
            seen_nonces=set() if seen_nonces is None else seen_nonces,
        )

    cases: list[str] = []
    invalid = copy.deepcopy(root)
    invalid["role_refs"] = [ref("role_ref", "founder")]
    cases.append(_expect_schema_reject(schemas["root"], invalid, "root_role_embedded"))

    invalid = copy.deepcopy(root)
    invalid["authority_model"]["member_consent_authority"] = "odoo"
    cases.append(
        _expect_schema_reject(schemas["root"], invalid, "root_authority_constant")
    )

    invalid = copy.deepcopy(root)
    invalid["member_name"] = "synthetic-forbidden"
    cases.append(_expect_schema_reject(schemas["root"], invalid, "root_plaintext_key"))

    tampered = copy.deepcopy(root)
    tampered["member_display_hash"] = digest("tampered-display")
    cases.append(
        _expect_hold(
            lambda: verify_root(
                tampered,
                root_registry_snapshot=root_registry,
                proof_registry_snapshot=proof_registry,
            ),
            "HOLD_ROOT_CONTENT_HASH_MISMATCH",
            "root_content_tamper",
        )
    )

    cases.append(
        _expect_hold(
            lambda: verify_root(
                root,
                root_registry_snapshot=root_registry,
                proof_registry_snapshot=None,
            ),
            "HOLD_ROOT_PROOF_NOT_EVIDENCED",
            "root_proof_missing",
        )
    )

    seen_derived: set[tuple[str, str]] = set()
    check_derived(packets["session"], seen_nonces=seen_derived)
    cases.append(
        _expect_hold(
            lambda: check_derived(
                packets["session"], seen_nonces=seen_derived
            ),
            "HOLD_DERIVED_PACKET_REPLAY",
            "derived_replay",
        )
    )
    cases.append(
        _expect_hold(
            lambda: verify_derived_packet(
                packets["session"],
                root,
                root_registry_snapshot=root_registry,
                proof_registry_snapshot=proof_registry,
                seen_nonces=None,
            ),
            "HOLD_REPLAY_LEDGER_NOT_EVIDENCED",
            "derived_replay_ledger_missing",
        )
    )

    tampered = copy.deepcopy(packets["consent"])
    tampered["action_binding"]["member_display_hash"] = digest("other-display")
    tampered = seal_content(tampered)
    cases.append(
        _expect_hold(
            lambda: check_derived(tampered),
            "HOLD_ACTION_ROOT_BINDING_MISMATCH",
            "member_display_hash_action_binding",
        )
    )

    tampered = copy.deepcopy(packets["consent"])
    tampered["action_binding"]["terms_version"] = "other-terms-v2"
    tampered = seal_content(tampered)
    cases.append(
        _expect_hold(
            lambda: check_derived(tampered),
            "HOLD_ACTION_ROOT_BINDING_MISMATCH",
            "terms_version_action_binding",
        )
    )

    for field in ("purpose_ref", "scope_refs", "effect_class"):
        invalid = copy.deepcopy(packets["consent"])
        del invalid["action_binding"][field]
        cases.append(
            _expect_schema_reject(
                schemas["derived"],
                invalid,
                f"action_hash_basis_{field}_missing",
            )
        )

    tampered = copy.deepcopy(packets["scene"])
    tampered["payload"]["purpose_ref"] = ref("purpose_ref", "wrong-purpose")
    tampered = seal_content(tampered)
    cases.append(
        _expect_hold(
            lambda: check_derived(tampered),
            "HOLD_ACTION_PURPOSE_MISMATCH",
            "action_wrong_purpose",
        )
    )

    tampered = copy.deepcopy(packets["scene"])
    tampered["payload"]["scope_refs"].append(
        ref("scope_ref", "unbound-added-scope")
    )
    tampered = seal_content(tampered)
    cases.append(
        _expect_hold(
            lambda: check_derived(tampered),
            "HOLD_ACTION_SCOPE_MISMATCH",
            "action_scope_added",
        )
    )

    tampered = copy.deepcopy(packets["scene"])
    tampered["action_binding"]["scope_refs"].append(
        ref("scope_ref", "second-bound-scope")
    )
    tampered["action_binding"]["action_hash"] = action_hash(
        tampered["action_binding"]
    )
    tampered["payload"]["action_hash"] = tampered["action_binding"][
        "action_hash"
    ]
    tampered = seal_content(tampered)
    cases.append(
        _expect_hold(
            lambda: check_derived(tampered),
            "HOLD_ACTION_SCOPE_MISMATCH",
            "action_scope_removed",
        )
    )

    tampered = copy.deepcopy(packets["scene"])
    tampered["action_binding"]["effect_class"] = "E5_HIGH_IMPACT"
    tampered = seal_content(tampered)
    cases.append(
        _expect_hold(
            lambda: check_derived(tampered),
            "HOLD_ACTION_HASH_MISMATCH",
            "action_effect_class_replaced",
        )
    )

    ordered_scope_action = copy.deepcopy(
        packets["consent"]["action_binding"]
    )
    scope_one = ref("scope_ref", "order-one")
    scope_two = ref("scope_ref", "order-two")
    ordered_scope_action["scope_refs"] = [scope_two, scope_one, scope_two]
    reordered_scope_action = copy.deepcopy(ordered_scope_action)
    reordered_scope_action["scope_refs"] = [scope_one, scope_two]
    _require(
        action_hash(ordered_scope_action) == action_hash(reordered_scope_action),
        "HOLD_ACTION_SCOPE_CANONICALIZATION",
    )
    cases.append("action_scope_sort_dedup_canonicalization")

    invalid = copy.deepcopy(packets["consent"])
    invalid["action_binding"]["amount_currency_hash"] = None
    cases.append(
        _expect_schema_reject(
            schemas["derived"], invalid, "transaction_amount_currency_hash_missing"
        )
    )

    invalid = copy.deepcopy(packets["session"])
    invalid["action_binding"]["amount_currency_hash"] = digest("unexpected-amount")
    cases.append(
        _expect_schema_reject(
            schemas["derived"], invalid, "non_transaction_amount_hash_present"
        )
    )

    tampered = copy.deepcopy(packets["session"])
    tampered["subject_binding_ref"] = ref(
        "member_subject_binding_ref", "other-member"
    )
    tampered = seal_content(tampered)
    cases.append(
        _expect_hold(
            lambda: check_derived(tampered),
            "HOLD_DERIVED_ROOT_BINDING",
            "derived_cross_member",
        )
    )

    tampered = copy.deepcopy(packets["revocation"])
    tampered["payload"]["previous_revocation_epoch"] = 1
    tampered["payload"]["new_revocation_epoch"] = 1
    tampered = seal_content(tampered)
    cases.append(
        _expect_hold(
            lambda: check_derived(tampered),
            "HOLD_REVOCATION_EPOCH_RACE",
            "revocation_epoch_race",
        )
    )

    tampered = copy.deepcopy(packets["recovery"])
    tampered["payload"]["new_root_generation"] = root["root_generation"] + 2
    tampered = seal_content(tampered)
    cases.append(
        _expect_hold(
            lambda: check_derived(tampered),
            "HOLD_RECOVERY_ROTATION_RACE",
            "recovery_generation_race",
        )
    )

    invalid = copy.deepcopy(packets["role_seat"])
    invalid["payload"]["transferable"] = True
    cases.append(
        _expect_schema_reject(
            schemas["derived"], invalid, "founder_role_seat_transfer"
        )
    )

    invalid = copy.deepcopy(packets["scene"])
    invalid["payload"]["issuing_process_authority"] = "member"
    cases.append(
        _expect_schema_reject(
            schemas["derived"], invalid, "derived_process_authority_constant"
        )
    )

    invalid = copy.deepcopy(dual)
    del invalid["member_receipt"]
    cases.append(
        _expect_schema_reject(
            schemas["dual_receipt"], invalid, "member_receipt_missing"
        )
    )

    cross_root = copy.deepcopy(dual)
    cross_root["action_binding"]["identity_root_ref"] = ref(
        "member_identity_root_ref", "other-member:stable-root"
    )
    cross_root["action_binding"]["root_packet_ref"] = ref(
        "member_root_packet_ref", "other-member:root-generation:1"
    )
    cross_root["action_binding"]["subject_binding_ref"] = ref(
        "member_subject_binding_ref", "other-member:protected-subject"
    )
    cross_root["action_binding"]["member_display_hash"] = digest(
        "other-member:member-display"
    )
    cross_root["action_binding"]["action_hash"] = action_hash(
        cross_root["action_binding"]
    )
    for receipt_name in ("member_receipt", "total_field_receipt"):
        receipt = cross_root[receipt_name]
        for key in (
            "identity_root_ref",
            "root_packet_ref",
            "subject_binding_ref",
            "member_display_hash",
            "action_hash",
        ):
            receipt[key] = cross_root["action_binding"][key]
        cross_root[receipt_name] = seal_receipt(receipt)
    cross_root["odoo_binding"]["action_hash"] = cross_root["action_binding"][
        "action_hash"
    ]
    cross_root = seal_content(cross_root)
    cases.append(
        _expect_hold(
            lambda: check_dual(cross_root),
            "HOLD_ACTION_ROOT_BINDING_MISMATCH",
            "dual_cross_root_action_binding",
        )
    )

    tampered = copy.deepcopy(dual)
    tampered["total_field_receipt"]["action_hash"] = digest("other-action")
    tampered["total_field_receipt"] = seal_receipt(
        tampered["total_field_receipt"]
    )
    tampered = seal_content(tampered)
    cases.append(
        _expect_hold(
            lambda: check_dual(tampered),
            "HOLD_ACTION_HASH_RECEIPT_MISMATCH",
            "dual_action_hash_mismatch",
        )
    )

    tampered = copy.deepcopy(dual)
    tampered["total_field_receipt"]["member_display_hash"] = digest(
        "other-member-display"
    )
    tampered["total_field_receipt"] = seal_receipt(
        tampered["total_field_receipt"]
    )
    tampered = seal_content(tampered)
    cases.append(
        _expect_hold(
            lambda: check_dual(tampered),
            "HOLD_MEMBER_DISPLAY_HASH_MISMATCH",
            "dual_member_display_hash_mismatch",
        )
    )

    tampered = copy.deepcopy(dual)
    tampered["member_receipt"]["terms_version"] = "other-terms-v2"
    tampered["member_receipt"] = seal_receipt(tampered["member_receipt"])
    tampered = seal_content(tampered)
    cases.append(
        _expect_hold(
            lambda: check_dual(tampered),
            "HOLD_TERMS_VERSION_MISMATCH",
            "dual_terms_version_mismatch",
        )
    )

    tampered = copy.deepcopy(dual)
    tampered["member_receipt"]["amount_currency_hash"] = digest("other-amount")
    tampered["member_receipt"] = seal_receipt(tampered["member_receipt"])
    tampered = seal_content(tampered)
    cases.append(
        _expect_hold(
            lambda: check_dual(tampered),
            "HOLD_AMOUNT_CURRENCY_HASH_MISMATCH",
            "dual_amount_currency_hash_mismatch",
        )
    )

    receipt_basis_mismatches = (
        (
            "purpose_ref",
            ref("purpose_ref", "other-receipt-purpose"),
            "HOLD_PURPOSE_REF_MISMATCH",
        ),
        (
            "scope_refs",
            [ref("scope_ref", "other-receipt-scope")],
            "HOLD_SCOPE_REFS_MISMATCH",
        ),
        (
            "effect_class",
            "E5_HIGH_IMPACT",
            "HOLD_EFFECT_CLASS_MISMATCH",
        ),
    )
    for receipt_name in ("member_receipt", "total_field_receipt"):
        for field, replacement, expected_code in receipt_basis_mismatches:
            tampered = copy.deepcopy(dual)
            tampered[receipt_name][field] = replacement
            tampered[receipt_name] = seal_receipt(tampered[receipt_name])
            tampered = seal_content(tampered)
            cases.append(
                _expect_hold(
                    lambda packet=tampered: check_dual(packet),
                    expected_code,
                    f"dual_{receipt_name}_{field}_mismatch",
                )
            )

    invalid = copy.deepcopy(dual)
    invalid["member_receipt"]["authority"] = "total_field_verifier"
    cases.append(
        _expect_schema_reject(
            schemas["dual_receipt"], invalid, "dual_authority_constant"
        )
    )

    invalid = copy.deepcopy(dual)
    invalid["total_field_receipt"]["authority"] = "member"
    cases.append(
        _expect_schema_reject(
            schemas["dual_receipt"], invalid, "total_field_authority_constant"
        )
    )

    invalid = copy.deepcopy(dual)
    invalid["odoo_binding"]["authority"] = "member"
    cases.append(
        _expect_schema_reject(
            schemas["dual_receipt"], invalid, "odoo_process_authority_constant"
        )
    )

    cases.append(
        _expect_hold(
            lambda: verify_dual_receipt(
                dual,
                root,
                root_registry_snapshot=root_registry,
                proof_registry_snapshot=proof_registry,
                member_proof_registry_snapshot=None,
                seen_nonces=set(),
            ),
            "HOLD_MEMBER_PROOF_REGISTRY_NOT_EVIDENCED",
            "member_proof_registry_missing",
        )
    )

    invalid_proof_registry = synthetic_member_proof_registry(root, dual)
    invalid_proof_registry["proofs"][
        dual["member_receipt"]["member_proof_ref"]
    ]["action_hash"] = digest("forged-action-proof")
    cases.append(
        _expect_hold(
            lambda: check_dual(
                dual, member_registry=invalid_proof_registry
            ),
            "HOLD_MEMBER_RECEIPT_INVALID",
            "member_receipt_proof_invalid",
        )
    )

    cases.append(
        _expect_hold(
            lambda: verify_dual_receipt(
                dual,
                root,
                root_registry_snapshot=root_registry,
                proof_registry_snapshot=proof_registry,
                member_proof_registry_snapshot=member_proof_registry,
                seen_nonces=None,
            ),
            "HOLD_REPLAY_LEDGER_NOT_EVIDENCED",
            "dual_replay_ledger_missing",
        )
    )

    blocked = synthetic_dual_receipt(
        root,
        packets["consent"]["action_binding"],
        member_decision="DENY",
        total_field_decision="PASS",
    )
    blocked_result = check_dual(blocked)
    _require(
        blocked_result["state"] == "BLOCK_MEMBER_OR_TOTAL_FIELD_DECISION",
        "HOLD_TOTAL_FIELD_PASS_SUBSTITUTED_FOR_MEMBER_CONSENT",
    )
    cases.append("total_field_pass_does_not_replace_member_consent")

    seen_receipts: set[tuple[str, str]] = set()
    check_dual(dual, seen_nonces=seen_receipts)
    cases.append(
        _expect_hold(
            lambda: check_dual(dual, seen_nonces=seen_receipts),
            "HOLD_RECEIPT_REPLAY",
            "dual_receipt_replay",
        )
    )

    return {
        "state": "PASS_P0_SOURCE_CONTRACT_CANDIDATE",
        "schema_count": len(schemas),
        "derived_variant_count": len(packets),
        "red_team_case_count": len(cases),
        "red_team_results": [{"case": case, "result": "PASS"} for case in cases],
        "candidate_only": True,
        "authority_granted": False,
        "runtime_enabled": False,
        "runtime_signature_validation": "NOT_IMPLEMENTED_P0",
        "runtime_nonce_store": "NOT_IMPLEMENTED_P0",
        "runtime_revocation_atomicity": "NOT_IMPLEMENTED_P0",
        "next_hold": "HOLD_P1_RUNTIME_VERIFIER_NOT_AUTHORIZED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate schemas, synthetic fixtures, and contract red-team cases",
    )
    parser.add_argument(
        "--check-manifest",
        type=Path,
        help="validate the exact read-only P0 SHA-256 manifest",
    )
    args = parser.parse_args(argv)
    if not args.check and args.check_manifest is None:
        parser.error("one of --check or --check-manifest is required")
    try:
        result: dict[str, Any] = {}
        if args.check:
            result["contract"] = run_contract_self_check()
        if args.check_manifest is not None:
            result["manifest"] = verify_manifest(args.check_manifest)
    except (ContractHold, ValidationError, OSError, ValueError) as exc:
        code = exc.code if isinstance(exc, ContractHold) else type(exc).__name__
        print(
            json.dumps(
                {
                    "state": "HOLD",
                    "reason_code": code,
                    "detail": str(exc),
                    "candidate_only": True,
                    "authority_granted": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "state": "PASS",
                "candidate_only": True,
                "authority_granted": False,
                "runtime_enabled": False,
                **result,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
