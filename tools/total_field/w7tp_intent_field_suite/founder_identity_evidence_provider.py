"""Candidate-only read-only Founder identity evidence provider.

The provider accepts one injected snapshot reader for the existing Odoo 18
member authority ledger candidate.  It never creates a root, registry, seat,
receipt, or runtime state.  Complete hash-bound evidence is passed to the
existing P1 verifier once; only opaque references, hashes, cardinality, and
candidate PASS/HOLD/BLOCK state are returned.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Callable, Mapping
from typing import Any

from .member_sovereign_identity import (
    EVIDENCE_KIND_BY_FIELD,
    verify_member_sovereign_identity_candidate,
)


REGISTRY_COORDINATE = (
    "odoo18://wuchang_member_registration/"
    "wuchang.member.registration/sovereign-authority-ledger-candidate-v1"
)
PROVIDER_ID = "READ_ONLY_FOUNDER_IDENTITY_EVIDENCE_PROVIDER_CANDIDATE_V1"
PROVIDER_EVIDENCE_SCHEMA_VERSION = (
    "W7TP-FOUNDER-IDENTITY-PROVIDER-EVIDENCE/1.0"
)
_HASH_REF = re.compile(r"^[a-z][a-z0-9_.-]*:sha256:[0-9a-f]{64}$")
_FORBIDDEN_KEYS = frozenset(
    {
        "access_token",
        "address",
        "credential",
        "email",
        "member_name",
        "member_plaintext",
        "mobile",
        "name",
        "password",
        "phone",
        "private_key",
        "provider_profile",
        "raw_credential",
        "raw_key",
        "raw_provider_profile",
        "raw_provider_subject",
        "refresh_token",
        "secret",
        "token",
    }
)


class ProviderHold(RuntimeError):
    """Fail-closed provider candidate result."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _walk_forbidden(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str) or key.casefold() in _FORBIDDEN_KEYS:
                raise ProviderHold("HOLD_MEMBER_PLAINTEXT_BOUNDARY")
            _walk_forbidden(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _walk_forbidden(nested)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ProviderHold(code)


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProviderHold(code)
    return value


def _hash_ref(value: Any, code: str) -> str:
    if not isinstance(value, str) or _HASH_REF.fullmatch(value) is None:
        raise ProviderHold(code)
    return value


def _provider_evidence(
    wrapper: Any,
    *,
    kind: str,
    missing_code: str,
) -> Mapping[str, Any]:
    item = _mapping(wrapper, missing_code)
    _require(
        set(item)
        == {"schema_version", "evidence_ref", "payload_sha256", "payload"},
        missing_code,
    )
    payload = _mapping(item.get("payload"), missing_code)
    payload_sha256 = _sha256_json(payload)
    _require(
        item.get("schema_version") == PROVIDER_EVIDENCE_SCHEMA_VERSION
        and item.get("payload_sha256") == payload_sha256
        and item.get("evidence_ref")
        == f"{kind}_ref:sha256:{payload_sha256}",
        "HOLD_PROVIDER_EVIDENCE_HASH_MISMATCH",
    )
    return payload


def _hold(
    code: str,
    *,
    cardinality: int | str = "NOT_EVIDENCED",
) -> dict[str, Any]:
    return {
        "state": "HOLD",
        "reason_code": code,
        "candidate_only": True,
        "provider_id": PROVIDER_ID,
        "registry_coordinate": REGISTRY_COORDINATE,
        "root_registry_cardinality": cardinality,
        "founder_role_seat_ref": "NOT_EVIDENCED",
        "founder_identity_root_ref": "NOT_EVIDENCED",
        "founder_identity_binding_receipt_ref": "NOT_EVIDENCED",
        "8d_adi_binding_evidence_ref": "NOT_EVIDENCED",
        "current_root_registry_cardinality_evidence_ref": "NOT_EVIDENCED",
        "p1_verifier_result": {
            "state": "NOT_RUN",
            "reason_code": code,
        },
        "second_registry_created": False,
        "member_plaintext_read": False,
    }


class ReadOnlyFounderIdentityEvidenceProviderCandidate:
    """Bind one Odoo ledger snapshot to the unchanged P1 verifier."""

    def __init__(
        self,
        snapshot_reader: Callable[[str], Mapping[str, Any] | None],
    ) -> None:
        self._snapshot_reader = snapshot_reader

    def collect_and_verify(self) -> dict[str, Any]:
        """Read once, fail closed, and return a ref/hash/status-only result."""

        try:
            supplied = self._snapshot_reader(REGISTRY_COORDINATE)
        except Exception:
            return _hold("HOLD_EVIDENCE_PROVIDER_UNAVAILABLE")
        if not isinstance(supplied, Mapping):
            return _hold("HOLD_REGISTRY_NOT_CONFIGURED")

        try:
            snapshot = copy.deepcopy(supplied)
            _walk_forbidden(snapshot)
            _require(
                snapshot.get("registry_coordinate") == REGISTRY_COORDINATE,
                "HOLD_REGISTRY_COORDINATE_MISMATCH",
            )
            candidate = _mapping(
                snapshot.get("p1_candidate"),
                "HOLD_P1_EVIDENCE_NOT_EVIDENCED",
            )
            _require(
                set(candidate) == set(EVIDENCE_KIND_BY_FIELD),
                "HOLD_P1_EVIDENCE_NOT_EVIDENCED",
            )

            root_chain_wrapper = _mapping(
                candidate.get("root_chain_evidence"),
                "HOLD_ROOT_CHAIN_NOT_EVIDENCED",
            )
            root_registry_wrapper = _mapping(
                candidate.get("root_registry_evidence"),
                "HOLD_ROOT_REGISTRY_NOT_EVIDENCED",
            )
            root_chain = _mapping(
                root_chain_wrapper.get("payload"),
                "HOLD_ROOT_CHAIN_NOT_EVIDENCED",
            )
            root_registry = _mapping(
                root_registry_wrapper.get("payload"),
                "HOLD_ROOT_REGISTRY_NOT_EVIDENCED",
            )
            roots = root_chain.get("roots")
            entries = root_registry.get("entries")
            _require(
                isinstance(roots, list)
                and roots
                and all(isinstance(item, Mapping) for item in roots),
                "HOLD_ROOT_CHAIN_NOT_EVIDENCED",
            )
            _require(
                isinstance(entries, list)
                and all(isinstance(item, Mapping) for item in entries),
                "HOLD_ROOT_REGISTRY_NOT_EVIDENCED",
            )
            current_root = roots[-1]
            subject_binding_ref = _hash_ref(
                current_root.get("subject_binding_ref"),
                "HOLD_ROOT_BINDING_INVALID",
            )
            current_entries = [
                item
                for item in entries
                if item.get("current") is True
                and item.get("subject_binding_ref") == subject_binding_ref
            ]
            cardinality = len(current_entries)
            if cardinality == 0:
                return _hold("HOLD_ROOT_REGISTRY_EMPTY", cardinality=0)
            if cardinality != 1:
                return _hold("HOLD_SECOND_IDENTITY_ROOT", cardinality=cardinality)

            cardinality_evidence = _provider_evidence(
                snapshot.get("current_root_registry_cardinality_evidence"),
                kind="current_root_registry_cardinality_evidence",
                missing_code="HOLD_ROOT_REGISTRY_CARDINALITY_NOT_EVIDENCED",
            )
            _require(
                set(cardinality_evidence)
                == {
                    "registry_coordinate",
                    "registry_ref",
                    "root_registry_snapshot_sha256",
                    "cardinality",
                }
                and cardinality_evidence.get("registry_coordinate")
                == REGISTRY_COORDINATE
                and cardinality_evidence.get("registry_ref")
                == root_registry.get("registry_ref")
                and cardinality_evidence.get("root_registry_snapshot_sha256")
                == root_registry_wrapper.get("payload_sha256")
                and cardinality_evidence.get("cardinality") == cardinality,
                "HOLD_ROOT_REGISTRY_CARDINALITY_MISMATCH",
            )

            identity_root_ref = _hash_ref(
                current_root.get("identity_root_ref"),
                "HOLD_ROOT_BINDING_INVALID",
            )
            _require(
                current_entries[0].get("identity_root_ref") == identity_root_ref,
                "HOLD_ROOT_REGISTRY_BINDING_MISMATCH",
            )
            derived_wrapper = _mapping(
                candidate.get("derived_packets_evidence"),
                "HOLD_DERIVED_PACKETS_NOT_EVIDENCED",
            )
            derived = _mapping(
                derived_wrapper.get("payload"),
                "HOLD_DERIVED_PACKETS_NOT_EVIDENCED",
            )
            role_seat = _mapping(
                derived.get("role_seat"),
                "HOLD_ROLE_SEAT_NOT_EVIDENCED",
            )
            role_seat_payload = _mapping(
                role_seat.get("payload"),
                "HOLD_ROLE_SEAT_NOT_EVIDENCED",
            )
            role_seat_ref = _hash_ref(
                role_seat_payload.get("role_seat_ref"),
                "HOLD_ROLE_SEAT_BINDING_INVALID",
            )
            _require(
                role_seat.get("identity_root_ref") == identity_root_ref
                and role_seat_payload.get(
                    "founder_role_requires_explicit_member_root_binding"
                )
                is True
                and role_seat_payload.get("issuing_process_authority") == "odoo",
                "HOLD_FOUNDER_SEAT_BINDING",
            )

            generative_transmission = _mapping(
                role_seat.get("generative_transmission"),
                "HOLD_8D_ADI_BINDING_NOT_EVIDENCED",
            )
            binding = _provider_evidence(
                snapshot.get("8d_adi_binding_evidence"),
                kind="8d_adi_binding_evidence",
                missing_code="HOLD_8D_ADI_BINDING_NOT_EVIDENCED",
            )
            required_binding_keys = {
                "registry_coordinate",
                "identity_root_ref",
                "role_seat_ref",
                "protocol",
                "state_packet_ref",
                "total_field_verify_ref",
                "adi_binding_ref",
                "receipt_ref",
            }
            _require(
                set(binding) == required_binding_keys
                and binding.get("registry_coordinate") == REGISTRY_COORDINATE
                and binding.get("identity_root_ref") == identity_root_ref
                and binding.get("role_seat_ref") == role_seat_ref
                and binding.get("protocol") == "W7TP_8D_INTENT_FIELD_PACKET"
                and binding.get("state_packet_ref")
                == generative_transmission.get("state_packet_ref")
                and binding.get("total_field_verify_ref")
                == generative_transmission.get("total_field_verify_ref"),
                "HOLD_8D_ADI_BINDING_MISMATCH",
            )
            _hash_ref(
                binding.get("adi_binding_ref"),
                "HOLD_8D_ADI_BINDING_MISMATCH",
            )
            binding_receipt_ref = _hash_ref(
                binding.get("receipt_ref"),
                "HOLD_FOUNDER_IDENTITY_BINDING_RECEIPT_NOT_EVIDENCED",
            )

            p1_result = verify_member_sovereign_identity_candidate(
                copy.deepcopy(candidate)
            )
            state = p1_result.get("state", "HOLD")
            reason_code = p1_result.get("reason_code", "HOLD_P1_RESULT_INVALID")
            if state == "PASS":
                reason_code = (
                    "PASS_READ_ONLY_FOUNDER_IDENTITY_EVIDENCE_PROVIDER_CANDIDATE"
                )
            elif state not in {"HOLD", "BLOCK"}:
                state = "HOLD"
                reason_code = "HOLD_P1_RESULT_INVALID"
            return {
                "state": state,
                "reason_code": reason_code,
                "candidate_only": True,
                "provider_id": PROVIDER_ID,
                "registry_coordinate": REGISTRY_COORDINATE,
                "root_registry_cardinality": cardinality,
                "founder_role_seat_ref": role_seat_ref,
                "founder_identity_root_ref": identity_root_ref,
                "founder_identity_binding_receipt_ref": binding_receipt_ref,
                "8d_adi_binding_evidence_ref": snapshot[
                    "8d_adi_binding_evidence"
                ]["evidence_ref"],
                "current_root_registry_cardinality_evidence_ref": snapshot[
                    "current_root_registry_cardinality_evidence"
                ]["evidence_ref"],
                "p1_verifier_result": copy.deepcopy(p1_result),
                "second_registry_created": False,
                "member_plaintext_read": False,
            }
        except ProviderHold as exc:
            return _hold(
                exc.code,
                cardinality=locals().get("cardinality", "NOT_EVIDENCED"),
            )
        except (TypeError, ValueError):
            return _hold(
                "HOLD_PROVIDER_CANDIDATE_INVALID",
                cardinality=locals().get("cardinality", "NOT_EVIDENCED"),
            )
