"""Pure production-shape Founder identity evidence snapshot builder candidate.

The builder consumes one sealed, attested, deidentified projection of the
existing Odoo sovereign-root ledger plus opaque Founder/device/capability/
access/8D-ADI references.  It emits the exact snapshot coordinates consumed
by ``ReadOnlyFounderIdentityEvidenceProviderCandidate``.  Composition is
deterministic and has no writes, database operation, network operation,
activation, receiver call, or test-fixture synthesis.  Source attestation and
the governed P1 contract are checked through read-only verifier interfaces.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Collection, Mapping
from typing import Any, Protocol

from . import founder_identity_evidence_provider as _provider_contract
from . import member_sovereign_identity as _p1_contract


PROVIDER_EVIDENCE_SCHEMA_VERSION = (
    _provider_contract.PROVIDER_EVIDENCE_SCHEMA_VERSION
)
REGISTRY_COORDINATE = _provider_contract.REGISTRY_COORDINATE


BUILDER_SCHEMA_VERSION = (
    "W7TP-FOUNDER-IDENTITY-EVIDENCE-SNAPSHOT-BUILDER/1.0"
)
SOURCE_SNAPSHOT_SCHEMA_VERSION = (
    "W7TP-ODOO-FOUNDER-SOVEREIGN-ROOT-LEDGER-DEIDENTIFIED-SNAPSHOT/1.0"
)
SOURCE_LEDGER_MODEL = "wuchang.member.sovereign.root.ledger"
SOURCE_ATTESTATION_SCHEMA_VERSION = (
    "W7TP-ODOO-SOVEREIGN-ROOT-LEDGER-EXPORT-ATTESTATION/1.0"
)

_HASH_REF = re.compile(r"^[a-z][a-z0-9_.-]*:sha256:[0-9a-f]{64}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_FIELDS = frozenset(
    {
        "schema_version",
        "ledger_model",
        "registry_coordinate",
        "process_authority",
        "deidentified",
        "p1_evidence_payloads",
        "founders",
        "role_seats",
        "registered_devices",
        "adi_binding",
        "source_attestation",
        "snapshot_sha256",
    }
)
_FOUNDER_FIELDS = frozenset(
    {
        "founder_person_packet_ref",
        "identity_root_ref",
        "role_seat_ref",
        "registered_device_ref",
        "founder_capability_assignment_ref",
        "access_profile_ref",
    }
)
_ROLE_SEAT_FIELDS = frozenset(
    {
        "identity_root_ref",
        "role_seat_ref",
        "role_ref",
        "seat_ref",
        "issuing_process_authority",
    }
)
_REGISTERED_DEVICE_FIELDS = frozenset(
    {
        "identity_root_ref",
        "registered_device_ref",
        "device_binding_ref",
    }
)
_ADI_BINDING_FIELDS = frozenset(
    {
        "identity_root_ref",
        "role_seat_ref",
        "protocol",
        "state_packet_ref",
        "total_field_verify_ref",
        "adi_binding_ref",
    }
)
_SOURCE_ATTESTATION_FIELDS = frozenset(
    {
        "schema_version",
        "registry_coordinate",
        "ledger_model",
        "ledger_event_ref",
        "export_receipt_ref",
        "verifier_ref",
        "attested_payload_sha256",
        "attestation_ref",
    }
)
_FORBIDDEN_KEYS = frozenset(
    {
        "access_token",
        "address",
        "amount",
        "credential",
        "currency",
        "display_name",
        "email",
        "member_name",
        "member_plaintext",
        "mobile",
        "name",
        "password",
        "phone",
        "private_key",
        "provider_profile",
        "provider_subject",
        "raw_credential",
        "raw_key",
        "raw_provider_profile",
        "raw_provider_subject",
        "refresh_token",
        "secret",
        "token",
    }
)


class SnapshotBuildHold(RuntimeError):
    """Fail-closed production snapshot-builder result."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class TrustedReadOnlyOdooSnapshotVerifier(Protocol):
    """Injected verifier for an already-issued immutable Odoo export receipt."""

    trusted_odoo_snapshot_verifier: bool

    def verify_snapshot(
        self,
        *,
        registry_coordinate: str,
        ledger_model: str,
        ledger_event_ref: str,
        export_receipt_ref: str,
        verifier_ref: str,
        attested_payload_sha256: str,
        attestation_ref: str,
    ) -> bool: ...


def canonical_sha256(value: Any) -> str:
    """Use the already-governed P0/P1 canonical JSON SHA-256 rule."""

    return _p1_contract._P0.sha256_json(value)


def source_snapshot_sha256(snapshot: Mapping[str, Any]) -> str:
    """Hash a source snapshot with only its digest carrier excluded."""

    material = copy.deepcopy(dict(snapshot))
    material.pop("snapshot_sha256", None)
    return canonical_sha256(material)


def source_attested_payload_sha256(snapshot: Mapping[str, Any]) -> str:
    """Hash exactly the Odoo-export payload covered by its attestation."""

    material = copy.deepcopy(dict(snapshot))
    material.pop("snapshot_sha256", None)
    material.pop("source_attestation", None)
    return canonical_sha256(material)


def _output_snapshot_sha256(snapshot: Mapping[str, Any]) -> str:
    material = copy.deepcopy(dict(snapshot))
    material.pop("snapshot_sha256", None)
    return canonical_sha256(material)


def _require(condition: bool, reason_code: str) -> None:
    if not condition:
        raise SnapshotBuildHold(reason_code)


def _mapping(value: Any, reason_code: str) -> Mapping[str, Any]:
    _require(isinstance(value, Mapping), reason_code)
    assert isinstance(value, Mapping)
    return value


def _hash_ref(value: Any, reason_code: str) -> str:
    _require(
        isinstance(value, str) and _HASH_REF.fullmatch(value) is not None,
        reason_code,
    )
    return str(value)


def _walk_forbidden(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            _require(
                isinstance(key, str)
                and key.casefold() not in _FORBIDDEN_KEYS,
                "HOLD_MEMBER_PLAINTEXT_BOUNDARY",
            )
            _walk_forbidden(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _walk_forbidden(nested)


def _apply_existing_plaintext_boundary(value: Any) -> None:
    try:
        _p1_contract._P0._walk_forbidden(value)
    except _p1_contract._P0.ContractHold as exc:
        raise SnapshotBuildHold("HOLD_MEMBER_PLAINTEXT_BOUNDARY") from exc


def _exact_single(
    source: Mapping[str, Any],
    field: str,
    *,
    empty_code: str,
    second_code: str,
) -> Mapping[str, Any]:
    values = source.get(field)
    _require(isinstance(values, list), empty_code)
    assert isinstance(values, list)
    if len(values) == 0:
        raise SnapshotBuildHold(empty_code)
    if len(values) != 1:
        raise SnapshotBuildHold(second_code)
    return _mapping(values[0], empty_code)


def _evidence_wrapper(
    *,
    schema_version: str,
    kind: str,
    payload: Mapping[str, Any],
    provider_hash_rule: bool = False,
) -> dict[str, Any]:
    payload_value = copy.deepcopy(dict(payload))
    payload_sha256 = (
        _provider_contract._sha256_json(payload_value)
        if provider_hash_rule
        else canonical_sha256(payload_value)
    )
    return {
        "schema_version": schema_version,
        "evidence_ref": f"{kind}_ref:sha256:{payload_sha256}",
        "payload_sha256": payload_sha256,
        "payload": payload_value,
    }


def _hold(reason_code: str) -> dict[str, Any]:
    return {
        "schema_version": BUILDER_SCHEMA_VERSION,
        "state": "HOLD",
        "reason_code": reason_code,
        "candidate_only": True,
        "db_write": False,
        "active_authority_created": False,
        "receiver_call_count": 0,
        "synthetic_call_count": 0,
    }


def build_founder_identity_evidence_snapshot(
    *,
    sovereign_root_ledger_snapshot: Mapping[str, Any],
    founder_person_packet_ref: str,
    registered_device_ref: str,
    founder_capability_assignment_ref: str,
    access_profile_ref: str,
    adi_binding_ref: str,
    source_attestation_verifier: TrustedReadOnlyOdooSnapshotVerifier,
    trusted_source_verifier_refs: Collection[str],
) -> dict[str, Any]:
    """Build one deterministic Provider/P1-compatible evidence snapshot."""

    try:
        source = copy.deepcopy(
            dict(
                _mapping(
                    sovereign_root_ledger_snapshot,
                    "HOLD_SOURCE_LEDGER_SNAPSHOT_INVALID",
                )
            )
        )
        _walk_forbidden(source)
        _apply_existing_plaintext_boundary(source)
        _require(
            set(source) == _SOURCE_FIELDS
            and source.get("schema_version")
            == SOURCE_SNAPSHOT_SCHEMA_VERSION
            and source.get("ledger_model") == SOURCE_LEDGER_MODEL
            and source.get("registry_coordinate") == REGISTRY_COORDINATE
            and source.get("process_authority") == "odoo"
            and source.get("deidentified") is True,
            "HOLD_SOURCE_LEDGER_SNAPSHOT_INVALID",
        )
        supplied_source_sha256 = source.get("snapshot_sha256")
        _require(
            isinstance(supplied_source_sha256, str)
            and _SHA256.fullmatch(supplied_source_sha256) is not None
            and supplied_source_sha256 == source_snapshot_sha256(source),
            "HOLD_SOURCE_LEDGER_SNAPSHOT_HASH_MISMATCH",
        )

        source_attestation = _mapping(
            source.get("source_attestation"),
            "HOLD_SOURCE_ATTESTATION_NOT_EVIDENCED",
        )
        _require(
            set(source_attestation) == _SOURCE_ATTESTATION_FIELDS
            and source_attestation.get("schema_version")
            == SOURCE_ATTESTATION_SCHEMA_VERSION
            and source_attestation.get("registry_coordinate")
            == REGISTRY_COORDINATE
            and source_attestation.get("ledger_model") == SOURCE_LEDGER_MODEL,
            "HOLD_SOURCE_ATTESTATION_NOT_EVIDENCED",
        )
        ledger_event_ref = _hash_ref(
            source_attestation.get("ledger_event_ref"),
            "HOLD_SOURCE_ATTESTATION_NOT_EVIDENCED",
        )
        export_receipt_ref = _hash_ref(
            source_attestation.get("export_receipt_ref"),
            "HOLD_SOURCE_ATTESTATION_NOT_EVIDENCED",
        )
        source_verifier_ref = _hash_ref(
            source_attestation.get("verifier_ref"),
            "HOLD_SOURCE_ATTESTATION_NOT_EVIDENCED",
        )
        try:
            trusted_verifier_refs = set(trusted_source_verifier_refs)
        except Exception as exc:
            raise SnapshotBuildHold(
                "HOLD_SOURCE_ATTESTATION_VERIFIER_UNTRUSTED"
            ) from exc
        _require(
            source_verifier_ref in trusted_verifier_refs
            and all(
                isinstance(item, str)
                and _HASH_REF.fullmatch(item) is not None
                for item in trusted_verifier_refs
            ),
            "HOLD_SOURCE_ATTESTATION_VERIFIER_UNTRUSTED",
        )
        attested_payload_sha256 = source_attestation.get(
            "attested_payload_sha256"
        )
        _require(
            isinstance(attested_payload_sha256, str)
            and _SHA256.fullmatch(attested_payload_sha256) is not None
            and attested_payload_sha256
            == source_attested_payload_sha256(source),
            "HOLD_SOURCE_ATTESTATION_PAYLOAD_MISMATCH",
        )
        attestation_ref = _hash_ref(
            source_attestation.get("attestation_ref"),
            "HOLD_SOURCE_ATTESTATION_NOT_EVIDENCED",
        )
        attestation_material = {
            key: copy.deepcopy(value)
            for key, value in source_attestation.items()
            if key != "attestation_ref"
        }
        _require(
            attestation_ref
            == "odoo_snapshot_attestation_ref:sha256:"
            + canonical_sha256(attestation_material),
            "HOLD_SOURCE_ATTESTATION_HASH_MISMATCH",
        )
        try:
            trusted_source_verifier = getattr(
                source_attestation_verifier,
                "trusted_odoo_snapshot_verifier",
                False,
            )
        except Exception as exc:
            raise SnapshotBuildHold(
                "HOLD_SOURCE_ATTESTATION_VERIFIER_UNAVAILABLE"
            ) from exc
        _require(
            trusted_source_verifier is True,
            "HOLD_SOURCE_ATTESTATION_VERIFIER_UNTRUSTED",
        )
        try:
            source_verified = source_attestation_verifier.verify_snapshot(
                registry_coordinate=REGISTRY_COORDINATE,
                ledger_model=SOURCE_LEDGER_MODEL,
                ledger_event_ref=ledger_event_ref,
                export_receipt_ref=export_receipt_ref,
                verifier_ref=source_verifier_ref,
                attested_payload_sha256=attested_payload_sha256,
                attestation_ref=attestation_ref,
            )
        except Exception as exc:
            raise SnapshotBuildHold(
                "HOLD_SOURCE_ATTESTATION_VERIFIER_UNAVAILABLE"
            ) from exc
        _require(
            isinstance(source_verified, bool),
            "HOLD_SOURCE_ATTESTATION_VERIFIER_RESULT_INVALID",
        )
        _require(
            source_verified,
            "HOLD_SOURCE_ATTESTATION_VERIFICATION_FAILED",
        )

        supplied_refs = {
            "founder_person_packet_ref": _hash_ref(
                founder_person_packet_ref,
                "HOLD_FOUNDER_PERSON_REF_INVALID",
            ),
            "registered_device_ref": _hash_ref(
                registered_device_ref,
                "HOLD_REGISTERED_DEVICE_REF_INVALID",
            ),
            "founder_capability_assignment_ref": _hash_ref(
                founder_capability_assignment_ref,
                "HOLD_FOUNDER_CAPABILITY_REF_INVALID",
            ),
            "access_profile_ref": _hash_ref(
                access_profile_ref,
                "HOLD_ACCESS_PROFILE_REF_INVALID",
            ),
            "adi_binding_ref": _hash_ref(
                adi_binding_ref,
                "HOLD_8D_ADI_REF_INVALID",
            ),
        }

        payloads = _mapping(
            source.get("p1_evidence_payloads"),
            "HOLD_P1_EVIDENCE_NOT_EVIDENCED",
        )
        _require(
            set(payloads) == set(_p1_contract.EVIDENCE_KIND_BY_FIELD),
            "HOLD_P1_EVIDENCE_NOT_EVIDENCED",
        )
        p1_candidate = {
            field: _evidence_wrapper(
                schema_version=_p1_contract.EVIDENCE_SCHEMA_VERSION,
                kind=kind,
                payload=_mapping(
                    payloads[field],
                    "HOLD_P1_EVIDENCE_NOT_EVIDENCED",
                ),
            )
            for field, kind in _p1_contract.EVIDENCE_KIND_BY_FIELD.items()
        }
        root_chain = _mapping(
            payloads["root_chain_evidence"],
            "HOLD_ROOT_CHAIN_NOT_EVIDENCED",
        )
        roots = root_chain.get("roots")
        _require(
            isinstance(roots, list)
            and bool(roots)
            and all(isinstance(item, Mapping) for item in roots),
            "HOLD_ROOT_CHAIN_NOT_EVIDENCED",
        )
        assert isinstance(roots, list)
        current_root = _mapping(
            roots[-1], "HOLD_CURRENT_ROOT_NOT_EVIDENCED"
        )
        identity_root_ref = _hash_ref(
            current_root.get("identity_root_ref"),
            "HOLD_IDENTITY_ROOT_CROSS_BINDING",
        )
        subject_binding_ref = _hash_ref(
            current_root.get("subject_binding_ref"),
            "HOLD_IDENTITY_ROOT_CROSS_BINDING",
        )

        root_registry = _mapping(
            payloads["root_registry_evidence"],
            "HOLD_ROOT_REGISTRY_NOT_EVIDENCED",
        )
        entries = root_registry.get("entries")
        _require(
            isinstance(entries, list)
            and all(isinstance(item, Mapping) for item in entries),
            "HOLD_ROOT_REGISTRY_NOT_EVIDENCED",
        )
        assert isinstance(entries, list)
        current_entries = [
            item for item in entries if item.get("current") is True
        ]
        if len(current_entries) == 0:
            raise SnapshotBuildHold("HOLD_CURRENT_ROOT_CARDINALITY")
        if len(current_entries) != 1:
            raise SnapshotBuildHold("HOLD_SECOND_CURRENT_ROOT")
        current_entry = _mapping(
            current_entries[0], "HOLD_CURRENT_ROOT_NOT_EVIDENCED"
        )
        _require(
            current_entry.get("identity_root_ref") == identity_root_ref
            and current_entry.get("root_packet_ref")
            == current_root.get("root_packet_ref")
            and current_entry.get("subject_binding_ref") == subject_binding_ref
            and current_entry.get("root_generation")
            == current_root.get("root_generation")
            and current_entry.get("revocation_epoch")
            == current_root.get("revocation_epoch"),
            "HOLD_IDENTITY_ROOT_CROSS_BINDING",
        )

        founder = _exact_single(
            source,
            "founders",
            empty_code="HOLD_FOUNDER_CARDINALITY",
            second_code="HOLD_SECOND_FOUNDER",
        )
        role_seat_entry = _exact_single(
            source,
            "role_seats",
            empty_code="HOLD_ROLE_SEAT_CARDINALITY",
            second_code="HOLD_SECOND_ROLE_SEAT",
        )
        registered_device = _exact_single(
            source,
            "registered_devices",
            empty_code="HOLD_REGISTERED_DEVICE_CARDINALITY",
            second_code="HOLD_SECOND_REGISTERED_DEVICE",
        )
        _require(set(founder) == _FOUNDER_FIELDS, "HOLD_FOUNDER_BINDING")
        _require(
            set(role_seat_entry) == _ROLE_SEAT_FIELDS,
            "HOLD_ROLE_SEAT_CROSS_BINDING",
        )
        _require(
            set(registered_device) == _REGISTERED_DEVICE_FIELDS,
            "HOLD_REGISTERED_DEVICE_CROSS_BINDING",
        )

        derived = _mapping(
            payloads["derived_packets_evidence"],
            "HOLD_DERIVED_PACKETS_NOT_EVIDENCED",
        )
        role_seat_packet = _mapping(
            derived.get("role_seat"), "HOLD_ROLE_SEAT_NOT_EVIDENCED"
        )
        role_seat_payload = _mapping(
            role_seat_packet.get("payload"),
            "HOLD_ROLE_SEAT_NOT_EVIDENCED",
        )
        role_seat_ref = _hash_ref(
            role_seat_payload.get("role_seat_ref"),
            "HOLD_ROLE_SEAT_CROSS_BINDING",
        )
        role_ref = _hash_ref(
            role_seat_payload.get("role_ref"),
            "HOLD_ROLE_SEAT_CROSS_BINDING",
        )
        seat_ref = _hash_ref(
            role_seat_payload.get("seat_ref"),
            "HOLD_ROLE_SEAT_CROSS_BINDING",
        )
        _require(
            role_seat_packet.get("identity_root_ref") == identity_root_ref
            and role_seat_payload.get(
                "founder_role_requires_explicit_member_root_binding"
            )
            is True
            and role_seat_payload.get("issuing_process_authority") == "odoo"
            and role_seat_entry
            == {
                "identity_root_ref": identity_root_ref,
                "role_seat_ref": role_seat_ref,
                "role_ref": role_ref,
                "seat_ref": seat_ref,
                "issuing_process_authority": "odoo",
            },
            "HOLD_ROLE_SEAT_CROSS_BINDING",
        )

        session_packet = _mapping(
            derived.get("session"), "HOLD_SESSION_NOT_EVIDENCED"
        )
        session_payload = _mapping(
            session_packet.get("payload"), "HOLD_SESSION_NOT_EVIDENCED"
        )
        device_binding_ref = _hash_ref(
            session_payload.get("device_binding_ref"),
            "HOLD_REGISTERED_DEVICE_CROSS_BINDING",
        )
        _require(
            registered_device
            == {
                "identity_root_ref": identity_root_ref,
                "registered_device_ref": supplied_refs[
                    "registered_device_ref"
                ],
                "device_binding_ref": device_binding_ref,
            },
            "HOLD_REGISTERED_DEVICE_CROSS_BINDING",
        )

        _require(
            founder
            == {
                "founder_person_packet_ref": supplied_refs[
                    "founder_person_packet_ref"
                ],
                "identity_root_ref": identity_root_ref,
                "role_seat_ref": role_seat_ref,
                "registered_device_ref": supplied_refs[
                    "registered_device_ref"
                ],
                "founder_capability_assignment_ref": supplied_refs[
                    "founder_capability_assignment_ref"
                ],
                "access_profile_ref": supplied_refs["access_profile_ref"],
            },
            "HOLD_FOUNDER_BINDING",
        )

        generative_transmission = _mapping(
            role_seat_packet.get("generative_transmission"),
            "HOLD_8D_ADI_BINDING_NOT_EVIDENCED",
        )
        state_packet_ref = _hash_ref(
            generative_transmission.get("state_packet_ref"),
            "HOLD_8D_ADI_CROSS_BINDING",
        )
        total_field_verify_ref = _hash_ref(
            generative_transmission.get("total_field_verify_ref"),
            "HOLD_8D_ADI_CROSS_BINDING",
        )
        source_adi_binding = _mapping(
            source.get("adi_binding"),
            "HOLD_8D_ADI_BINDING_NOT_EVIDENCED",
        )
        _require(
            set(source_adi_binding) == _ADI_BINDING_FIELDS
            and source_adi_binding
            == {
                "identity_root_ref": identity_root_ref,
                "role_seat_ref": role_seat_ref,
                "protocol": "W7TP_8D_INTENT_FIELD_PACKET",
                "state_packet_ref": state_packet_ref,
                "total_field_verify_ref": total_field_verify_ref,
                "adi_binding_ref": supplied_refs["adi_binding_ref"],
            },
            "HOLD_8D_ADI_CROSS_BINDING",
        )

        p1_verifier_result = (
            _p1_contract.verify_member_sovereign_identity_candidate(
                copy.deepcopy(p1_candidate)
            )
        )
        _require(
            isinstance(p1_verifier_result, Mapping)
            and p1_verifier_result.get("state") == "PASS",
            "HOLD_P1_VERIFIER_REJECTED",
        )

        root_registry_wrapper = p1_candidate["root_registry_evidence"]
        cardinality_payload = {
            "registry_coordinate": REGISTRY_COORDINATE,
            "registry_ref": _hash_ref(
                root_registry.get("registry_ref"),
                "HOLD_ROOT_REGISTRY_NOT_EVIDENCED",
            ),
            "root_registry_snapshot_sha256": root_registry_wrapper[
                "payload_sha256"
            ],
            "cardinality": 1,
        }
        cardinality_evidence = _evidence_wrapper(
            schema_version=PROVIDER_EVIDENCE_SCHEMA_VERSION,
            kind="current_root_registry_cardinality_evidence",
            payload=cardinality_payload,
            provider_hash_rule=True,
        )

        p1_candidate_sha256 = canonical_sha256(p1_candidate)
        binding_receipt_payload = {
            "registry_coordinate": REGISTRY_COORDINATE,
            "source_ledger_snapshot_sha256": supplied_source_sha256,
            "source_attested_payload_sha256": attested_payload_sha256,
            "source_attestation_ref": attestation_ref,
            "source_ledger_event_ref": ledger_event_ref,
            "source_export_receipt_ref": export_receipt_ref,
            "source_verifier_ref": source_verifier_ref,
            "p1_candidate_sha256": p1_candidate_sha256,
            "founder_person_packet_ref": supplied_refs[
                "founder_person_packet_ref"
            ],
            "identity_root_ref": identity_root_ref,
            "role_seat_ref": role_seat_ref,
            "role_ref": role_ref,
            "seat_ref": seat_ref,
            "registered_device_ref": supplied_refs["registered_device_ref"],
            "device_binding_ref": device_binding_ref,
            "founder_capability_assignment_ref": supplied_refs[
                "founder_capability_assignment_ref"
            ],
            "access_profile_ref": supplied_refs["access_profile_ref"],
            "adi_binding_ref": supplied_refs["adi_binding_ref"],
        }
        binding_receipt = _evidence_wrapper(
            schema_version=PROVIDER_EVIDENCE_SCHEMA_VERSION,
            kind="founder_identity_binding_receipt",
            payload=binding_receipt_payload,
            provider_hash_rule=True,
        )
        adi_binding_payload = {
            "registry_coordinate": REGISTRY_COORDINATE,
            "identity_root_ref": identity_root_ref,
            "role_seat_ref": role_seat_ref,
            "protocol": "W7TP_8D_INTENT_FIELD_PACKET",
            "state_packet_ref": state_packet_ref,
            "total_field_verify_ref": total_field_verify_ref,
            "adi_binding_ref": supplied_refs["adi_binding_ref"],
            "receipt_ref": binding_receipt["evidence_ref"],
        }
        adi_binding_evidence = _evidence_wrapper(
            schema_version=PROVIDER_EVIDENCE_SCHEMA_VERSION,
            kind="8d_adi_binding_evidence",
            payload=adi_binding_payload,
            provider_hash_rule=True,
        )

        result: dict[str, Any] = {
            "schema_version": BUILDER_SCHEMA_VERSION,
            "state": "BUILT_FOUNDER_IDENTITY_EVIDENCE_SNAPSHOT_CANDIDATE",
            "reason_code": "BUILT_PROVIDER_AND_P1_COMPATIBLE_CANDIDATE",
            "candidate_only": True,
            "registry_coordinate": REGISTRY_COORDINATE,
            "source_ledger_model": SOURCE_LEDGER_MODEL,
            "source_ledger_snapshot_sha256": supplied_source_sha256,
            "source_attestation_ref": attestation_ref,
            "source_ledger_event_ref": ledger_event_ref,
            "source_export_receipt_ref": export_receipt_ref,
            "p1_candidate": p1_candidate,
            "p1_candidate_sha256": p1_candidate_sha256,
            "p1_verifier_result": copy.deepcopy(p1_verifier_result),
            "current_root_registry_cardinality_evidence": (
                cardinality_evidence
            ),
            "founder_identity_binding_receipt": binding_receipt,
            "8d_adi_binding_evidence": adi_binding_evidence,
            "db_write": False,
            "active_authority_created": False,
            "receiver_call_count": 0,
            "synthetic_call_count": 0,
        }
        result["snapshot_sha256"] = _output_snapshot_sha256(result)
        return result
    except SnapshotBuildHold as exc:
        return _hold(exc.reason_code)
    except (
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
        _p1_contract._P0.ContractHold,
    ):
        return _hold("HOLD_SOURCE_LEDGER_SNAPSHOT_INVALID")


__all__ = [
    "BUILDER_SCHEMA_VERSION",
    "SOURCE_LEDGER_MODEL",
    "SOURCE_ATTESTATION_SCHEMA_VERSION",
    "SOURCE_SNAPSHOT_SCHEMA_VERSION",
    "TrustedReadOnlyOdooSnapshotVerifier",
    "build_founder_identity_evidence_snapshot",
    "canonical_sha256",
    "source_attested_payload_sha256",
    "source_snapshot_sha256",
]
