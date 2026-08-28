"""Deterministic, receiver-evidence-bound acceptance for candidate effects."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

from .canonical import (
    canonical_hash,
    canonical_json_bytes,
    canonical_json_loads,
    sha256_ref,
    validate_sha256_hex,
    validate_sha256_ref,
)
from .models import (
    AcceptanceResult,
    EffectObservation,
    EffectState,
    Hold,
    Quarantine,
)
from .object_packet_store import (
    ObjectPacketStore,
    ObjectStoreConflict,
    ObjectStoreHold,
)


@dataclass(frozen=True, slots=True)
class ExactHashAcceptanceContract:
    """Accept only a proven COMPLETE effect with one exact SHA-256 identity."""

    schema_id: str
    expected_effect_state: EffectState
    expected_actual_hash: str
    acceptance_contract_hash: str
    acceptance_contract_ref: str

    @classmethod
    def seal(
        cls,
        expected_actual_hash: str,
        expected_effect_state: EffectState = EffectState.COMPLETE,
    ) -> "ExactHashAcceptanceContract":
        validate_sha256_hex(expected_actual_hash)
        if expected_effect_state is not EffectState.COMPLETE:
            raise Quarantine("ACCEPTANCE_NONCOMPLETE_STATE_CONFLICT")
        body = {
            "schema_id": "W7TP_EXACT_HASH_ACCEPTANCE_V1",
            "expected_effect_state": expected_effect_state,
            "expected_actual_hash": expected_actual_hash,
        }
        digest = canonical_hash(body)
        return cls(
            schema_id="W7TP_EXACT_HASH_ACCEPTANCE_V1",
            expected_effect_state=expected_effect_state,
            expected_actual_hash=expected_actual_hash,
            acceptance_contract_hash=digest,
            acceptance_contract_ref=f"sha256:{digest}",
        )

    def body(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "expected_effect_state": self.expected_effect_state,
            "expected_actual_hash": self.expected_actual_hash,
        }

    def require_integrity(self) -> None:
        if self.schema_id != "W7TP_EXACT_HASH_ACCEPTANCE_V1":
            raise Quarantine("ACCEPTANCE_SCHEMA_CONFLICT")
        if self.expected_effect_state is not EffectState.COMPLETE:
            raise Quarantine("ACCEPTANCE_NONCOMPLETE_STATE_CONFLICT")
        validate_sha256_hex(self.expected_actual_hash)
        expected_hash = canonical_hash(self.body())
        if self.acceptance_contract_hash != expected_hash:
            raise Quarantine("ACCEPTANCE_CONTRACT_HASH_CONFLICT")
        if self.acceptance_contract_ref != f"sha256:{expected_hash}":
            raise Quarantine("ACCEPTANCE_CONTRACT_REF_CONFLICT")


class DeterministicAcceptanceEngine:
    """Evaluate only pre-supplied immutable acceptance contracts."""

    def __init__(
        self,
        contracts: Sequence[ExactHashAcceptanceContract]
        | Mapping[str, ExactHashAcceptanceContract],
        *,
        objects: ObjectPacketStore,
    ) -> None:
        if not isinstance(objects, ObjectPacketStore):
            raise Quarantine("ACCEPTANCE_EVIDENCE_STORE_CONFLICT")
        if isinstance(contracts, Mapping):
            values = tuple(contracts.values())
        else:
            values = tuple(contracts)
        by_ref: dict[str, ExactHashAcceptanceContract] = {}
        for contract in values:
            contract.require_integrity()
            if contract.acceptance_contract_ref in by_ref:
                raise Quarantine("DUPLICATE_ACCEPTANCE_CONTRACT_CONFLICT")
            by_ref[contract.acceptance_contract_ref] = contract
        self._contracts = MappingProxyType(by_ref)
        self._objects = objects

    def _load_exact_packet(self, ref: str) -> dict[str, object]:
        try:
            validate_sha256_ref(ref)
            raw = self._objects.get_exact(ref)
        except ObjectStoreHold as error:
            raise Hold("HOLD_ACCEPTANCE_OBSERVATION_UNAVAILABLE") from error
        except (ObjectStoreConflict, ValueError) as error:
            raise Quarantine("ACCEPTANCE_OBSERVATION_BYTES_CONFLICT") from error
        if sha256_ref(raw) != ref:
            raise Quarantine("ACCEPTANCE_OBSERVATION_BYTES_CONFLICT")
        try:
            packet = canonical_json_loads(raw)
        except (TypeError, ValueError) as error:
            raise Quarantine("ACCEPTANCE_OBSERVATION_BYTES_CONFLICT") from error
        if not isinstance(packet, dict):
            raise Quarantine("ACCEPTANCE_OBSERVATION_BYTES_CONFLICT")
        return packet

    def _require_persisted_observation(
        self,
        observation: EffectObservation,
    ) -> None:
        observation_packet = self._load_exact_packet(
            observation.observation_ref
        )
        if observation.evidence_ref != observation.observation_ref:
            self._load_exact_packet(observation.evidence_ref)
        try:
            packet_state = EffectState(observation_packet["effect_state"])
        except (KeyError, TypeError, ValueError) as error:
            raise Quarantine("ACCEPTANCE_OBSERVATION_BODY_CONFLICT") from error
        if (
            packet_state is not observation.effect_state
            or observation_packet.get("actual_hash") != observation.actual_hash
        ):
            raise Quarantine("ACCEPTANCE_OBSERVATION_BODY_CONFLICT")

    def _seal_acceptance_evidence(
        self,
        evidence_body: Mapping[str, object],
    ) -> str:
        raw = canonical_json_bytes(dict(evidence_body))
        evidence_ref = sha256_ref(raw)
        try:
            stored_ref = self._objects.put_exact(evidence_ref, raw)
            loaded = self._objects.get_exact(evidence_ref)
        except ObjectStoreHold as error:
            raise Hold("HOLD_ACCEPTANCE_EVIDENCE_STORE_UNAVAILABLE") from error
        except ObjectStoreConflict as error:
            raise Quarantine("ACCEPTANCE_EVIDENCE_STORE_CONFLICT") from error
        if (
            stored_ref != evidence_ref
            or loaded != raw
            or sha256_ref(loaded) != evidence_ref
        ):
            raise Quarantine("ACCEPTANCE_EVIDENCE_STORE_CONFLICT")
        return evidence_ref

    def evaluate_exact(
        self,
        acceptance_ref: str,
        observation: EffectObservation,
    ) -> AcceptanceResult:
        contract = self._contracts.get(acceptance_ref)
        if contract is None:
            raise Hold("HOLD_ACCEPTANCE_CONTRACT_UNAVAILABLE")
        contract.require_integrity()
        observation.require_receiver_evidence()
        try:
            validate_sha256_ref(observation.observation_ref)
            validate_sha256_ref(observation.evidence_ref)
        except ValueError as exc:
            raise Quarantine("ACCEPTANCE_EVIDENCE_REF_CONFLICT") from exc
        self._require_persisted_observation(observation)

        if observation.effect_state is not contract.expected_effect_state:
            accepted = False
            reason = "EFFECT_STATE_NOT_ACCEPTED"
        elif observation.actual_hash is None:
            accepted = False
            reason = "ACTUAL_HASH_MISSING"
        elif observation.actual_hash != contract.expected_actual_hash:
            accepted = False
            reason = "ACTUAL_HASH_NOT_ACCEPTED"
        else:
            validate_sha256_hex(observation.actual_hash)
            accepted = True
            reason = None

        evidence_body = {
            "schema_id": "W7TP_ACCEPTANCE_EVIDENCE_V1",
            "acceptance_contract_ref": contract.acceptance_contract_ref,
            "observation_ref": observation.observation_ref,
            "observation_evidence_ref": observation.evidence_ref,
            "expected_effect_state": contract.expected_effect_state,
            "actual_effect_state": observation.effect_state,
            "expected_actual_hash": contract.expected_actual_hash,
            "actual_hash": observation.actual_hash,
            "accepted": accepted,
            "reason": reason,
        }
        evidence_ref = self._seal_acceptance_evidence(evidence_body)
        return AcceptanceResult(
            accepted=accepted,
            evidence_ref=evidence_ref,
            reason=reason,
        )
