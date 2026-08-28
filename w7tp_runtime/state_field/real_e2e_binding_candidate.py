"""Deterministic real-E2E binding bundle candidate construction.

All packets produced here are candidate evidence.  They do not grant D8,
authority, activation, deployment, or permission to execute a real effect.
The builder performs no writes; callers may seal the returned bytes into an
``ObjectPacketStore`` after their own bounded review.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .canonical import canonical_json_bytes, sha256_hex, sha256_ref
from .native_cli_adapters import (
    ARTIFACT_PINS,
    CANDIDATE_VERSION,
    CANDIDATE_VERSION_SOURCE,
    SOURCE_BRANCH,
    SOURCE_COMMIT,
    SOURCE_NODE,
    SOURCE_REPOSITORY,
    SOURCE_TREE,
)
from .object_packet_store import ObjectPacketStore


INDEX_RUN_ID = "20260823T060504Z"
TARGET_NODE = "MSI"
TARGET_REPOSITORY = "/home/taiji_admin/Taiji_Hub"
TARGET_BRANCH = "agent/moving-v-v2-taiji8d-local-canary"
TARGET_HEAD = "348e4f440b4a2d62a9f9cc169f94ab7fb3964e44"
ADAPTER_SOURCE_PATH = "w7tp_runtime/state_field/native_cli_adapters.py"
TEST_SOURCE_PATH = "tests/test_w7tp_state_field_native_binding_candidate.py"
EXPIRED_PROMOTION_D8_SHA256 = (
    "732ee84588896aba0cb4ce8fb5ea9698c3992a7806095c5b36dcbbf1793ec716"
)


@dataclass(frozen=True, slots=True)
class SealedCandidatePacket:
    schema_id: str
    body: Mapping[str, object]
    raw: bytes
    sha256: str
    ref: str


@dataclass(frozen=True, slots=True)
class RealE2EBindingBundleCandidate:
    verification_evidence: tuple[SealedCandidatePacket, ...]
    manifests: tuple[SealedCandidatePacket, ...]
    binding_records: tuple[SealedCandidatePacket, ...]
    binding_packet: SealedCandidatePacket
    base_state: SealedCandidatePacket
    effect_input: bytes
    effect_input_ref: str
    effect_contract: SealedCandidatePacket
    authorization_request: SealedCandidatePacket
    document: SealedCandidatePacket

    @property
    def manifest_refs(self) -> Mapping[str, str]:
        return {
            str(packet.body["CAPABILITY_ID"]): packet.ref
            for packet in self.manifests
        }

    @property
    def binding_refs(self) -> Mapping[str, str]:
        return {
            str(packet.body["CAPABILITY_ID"]): packet.ref
            for packet in self.binding_records
        }

    def seal_all(self, objects: ObjectPacketStore) -> tuple[str, ...]:
        """Seal exact candidate bytes; this still creates no authority."""

        packets = (
            *self.verification_evidence,
            *self.manifests,
            *self.binding_records,
            self.binding_packet,
            self.base_state,
            self.effect_contract,
            self.authorization_request,
            self.document,
        )
        refs: list[str] = []
        for packet in packets:
            stored = objects.put_exact(packet.ref, packet.raw)
            if stored != packet.ref or objects.get_exact(packet.ref) != packet.raw:
                raise RuntimeError("CANDIDATE_PACKET_SEAL_CONFLICT")
            refs.append(packet.ref)
        stored_input = objects.put_exact(self.effect_input_ref, self.effect_input)
        if (
            stored_input != self.effect_input_ref
            or objects.get_exact(self.effect_input_ref) != self.effect_input
        ):
            raise RuntimeError("CANDIDATE_EFFECT_INPUT_SEAL_CONFLICT")
        refs.append(self.effect_input_ref)
        return tuple(refs)


def _seal(body: Mapping[str, object]) -> SealedCandidatePacket:
    schema_id = body.get("SCHEMA_ID")
    if not isinstance(schema_id, str) or not schema_id:
        raise ValueError("candidate packet schema is required")
    raw = canonical_json_bytes(body)
    return SealedCandidatePacket(
        schema_id=schema_id,
        body=body,
        raw=raw,
        sha256=sha256_hex(raw),
        ref=sha256_ref(raw),
    )


def _source_file_sha256(relative_path: str) -> str:
    component_root = Path(__file__).resolve().parents[2]
    path = component_root / relative_path
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _target_coordinate() -> str:
    from .native_ports import encode_local_file_coordinate

    return encode_local_file_coordinate(
        TARGET_REPOSITORY,
        "MSI_W7TP_STATE_FIELD_REAL_E2E_CANDIDATE",
        (
            "runtime/total_field/state_field/real_e2e_candidate/"
            "W7TP_STATE_FIELD_REAL_E2E_OUTPUT.bin"
        ),
    )


def build_real_e2e_binding_bundle_candidate() -> RealE2EBindingBundleCandidate:
    """Build the exact candidate bundle from frozen source evidence."""

    adapter_sha256 = _source_file_sha256(ADAPTER_SOURCE_PATH)
    test_sha256 = _source_file_sha256(TEST_SOURCE_PATH)
    target_coordinate = _target_coordinate()

    verification_packets: list[SealedCandidatePacket] = []
    manifest_packets: list[SealedCandidatePacket] = []
    binding_packets: list[SealedCandidatePacket] = []

    for capability_id in sorted(ARTIFACT_PINS):
        pin = ARTIFACT_PINS[capability_id]
        evidence = _seal(
            {
                "SCHEMA_ID": "W7TP_NATIVE_BINDING_VERIFICATION_EVIDENCE_V1",
                "ADAPTER_SHA256": adapter_sha256,
                "CAPABILITY_ID": capability_id,
                "CLI_PROTOCOL_CLASSIFICATION": pin.compatibility,
                "CONFLICT_INTERSECTIONS": 0,
                "INDEX_RUN_ID": INDEX_RUN_ID,
                "IMPLEMENTATION_SHA256": pin.implementation_sha256,
                "PROTOCOL_CONFORMANCE_TEST": TEST_SOURCE_PATH,
                "PROTOCOL_CONFORMANCE_TEST_SHA256": test_sha256,
                "SOURCE_COMMIT": SOURCE_COMMIT,
                "SOURCE_TREE": SOURCE_TREE,
                "UNKNOWN_INTERSECTIONS": 0,
                "VERIFICATION_SCOPE": "BINDING_CANDIDATE_ONLY",
                "VERIFICATION_STATE": "VERIFIED_BINDING_CANDIDATE",
                "AUTHORITY_CREATED": False,
                "D8_CREATED": False,
                "REAL_E2E_EXECUTED": False,
            }
        )
        verification_packets.append(evidence)

        manifest = _seal(
            {
                "SCHEMA_ID": "W7TP_NATIVE_BINDING_MANIFEST_CANDIDATE_V1",
                "ADAPTER_REF": pin.adapter_ref,
                "ADAPTER_SHA256": adapter_sha256,
                "AUTHORITY_LIMIT": (
                    "CANDIDATE_ONLY_NO_D8_NO_AUTHORITY_NO_EFFECT_AUTHORIZATION"
                ),
                "CAPABILITY_ID": capability_id,
                "CREATED_AS_CANDIDATE": True,
                "EVIDENCE_CONTRACT": evidence.ref,
                "FAILURE_CONTRACT": (
                    "UNKNOWN_OR_MALFORMED_OR_TIMEOUT_OR_FAILURE_TO_HOLD;"
                    "HASH_OR_COORDINATE_CONFLICT_TO_QUARANTINE"
                ),
                "IMPLEMENTATION_REF": pin.raw_implementation_ref,
                "IMPLEMENTATION_SHA256": pin.implementation_sha256,
                "INPUT_SCHEMA": pin.input_schema,
                "NOT_ACTIVE_VERSION": True,
                "NOT_HISTORICAL_VERSION": True,
                "OUTPUT_SCHEMA": pin.output_schema,
                "PROTOCOL_ID": pin.protocol_id,
                "SOURCE_BRANCH": SOURCE_BRANCH,
                "SOURCE_COMMIT": SOURCE_COMMIT,
                "SOURCE_NODE": SOURCE_NODE,
                "SOURCE_REPOSITORY": SOURCE_REPOSITORY,
                "SOURCE_TREE": SOURCE_TREE,
                "TARGET_ADAPTER_IMPLEMENTATION": (
                    f"{ADAPTER_SOURCE_PATH}#{pin.adapter_class_name}"
                ),
                "VERSION": CANDIDATE_VERSION,
                "VERSION_SOURCE": CANDIDATE_VERSION_SOURCE,
            }
        )
        manifest_packets.append(manifest)

        binding = _seal(
            {
                "SCHEMA_ID": "W7TP_NATIVE_BINDING_CANDIDATE_V1",
                "ADAPTER_REF": pin.adapter_ref,
                "ADAPTER_SHA256": adapter_sha256,
                "BINDING_STATE": "VERIFIED_BINDING_CANDIDATE",
                "CAPABILITY_ID": capability_id,
                "IMPLEMENTATION_REF": pin.raw_implementation_ref,
                "IMPLEMENTATION_SHA256": pin.implementation_sha256,
                "MANIFEST_REF": manifest.ref,
                "MANIFEST_SHA256": manifest.sha256,
                "PROTOCOL_ID": pin.protocol_id,
                "SOURCE_COORDINATE": pin.artifact_coordinate,
                "TARGET_COORDINATE": (
                    f"{TARGET_NODE}:{TARGET_REPOSITORY}@{TARGET_BRANCH}"
                    f"#{TARGET_HEAD}:{ADAPTER_SOURCE_PATH}"
                    f"#{pin.adapter_class_name}"
                ),
                "VERIFICATION_EVIDENCE": evidence.ref,
                "VERSION": CANDIDATE_VERSION,
                "RUNTIME_BINDING_AUTHORIZED": False,
            }
        )
        binding_packets.append(binding)

    binding_packet = _seal(
        {
            "SCHEMA_ID": "W7TP_STATE_FIELD_NATIVE_BINDING_PACKET_CANDIDATE_v1",
            "AUTHORITY_STATE": "NOT_GRANTED",
            "BINDINGS": [
                {
                    **dict(packet.body),
                    "BINDING_REF": packet.ref,
                    "BINDING_SHA256": packet.sha256,
                }
                for packet in binding_packets
            ],
            "BINDING_STATE": "VERIFIED_BINDING_CANDIDATE",
            "D8_STATE": "NOT_GRANTED",
            "INDEX_RUN_ID": INDEX_RUN_ID,
            "REAL_E2E_EXECUTED": False,
            "SOURCE_COMMIT": SOURCE_COMMIT,
            "SOURCE_NODE": SOURCE_NODE,
            "SOURCE_TREE": SOURCE_TREE,
            "TARGET_HEAD": TARGET_HEAD,
            "TARGET_NODE": TARGET_NODE,
            "VERIFIED_BINDING_CANDIDATE_COUNT": 5,
        }
    )

    base_state = _seal(
        {
            "SCHEMA_ID": "W7TP_REAL_E2E_CANDIDATE_BASE_STATE_V1",
            "GENERATION": 0,
            "POINTER_VERSION": None,
            "PROVEN_CURRENT_STATE": "UNKNOWN_UNVERIFIED",
            "REQUIRED_PRE_EFFECT_STATE": "TARGET_ABSENT_AND_POINTER_EXACT",
            "RUNTIME_AUTHORITY": False,
            "TARGET": target_coordinate,
        }
    )
    effect_input = b"W7TP_STATE_FIELD_REAL_E2E_CANDIDATE_v1\n"
    effect_input_ref = sha256_ref(effect_input)
    expected_output_sha256 = sha256_hex(effect_input)
    nonce = sha256_ref(
        canonical_json_bytes(
            {
                "binding_packet_ref": binding_packet.ref,
                "contract_id": "W7TP_STATE_FIELD_REAL_E2E_CANDIDATE_001",
                "target": target_coordinate,
            }
        )
    )

    effect_contract = _seal(
        {
            "SCHEMA_ID": "W7TP_EFFECT_CONTRACT_V1",
            "ACCEPTANCE_RULE": {
                "ACTUAL_SHA256": expected_output_sha256,
                "EFFECT_STATE": "COMPLETE",
                "SIZE_BYTES": len(effect_input),
            },
            "BASE_STATE_REF": base_state.ref,
            "CONTRACT_ID": "W7TP_STATE_FIELD_REAL_E2E_CANDIDATE_001",
            "CONTRACT_STATE": "CANDIDATE_AWAITING_D8_AUTHORIZATION",
            "EVIDENCE_DESTINATION": {
                "JOURNAL": "STATE_FIELD_OPERATION_JOURNAL_CANDIDATE",
                "OBJECT_STORE": "STATE_FIELD_IMMUTABLE_OBJECT_PACKET_STORE",
                "RECEIPT": "STATE_FIELD_RECEIPT_CANDIDATE",
            },
            "EXPECTED_EFFECT": "CREATE_EXACTLY_ONE_NEW_FILE_WITH_EXACT_INPUT_BYTES",
            "GENERATION": 0,
            "IDEMPOTENCY": {
                "CLASS": "IDEMPOTENT",
                "KEY": "w7tp-state-field-real-e2e-candidate-001",
                "REPLAY_EFFECT_LIMIT": 1,
            },
            "INPUT_REFS": [effect_input_ref, binding_packet.ref],
            "MAXIMUM_EFFECT": {
                "CREATE_DIRECTORIES": 0,
                "CREATE_FILES": 1,
                "DELETE_PATHS": 0,
                "OVERWRITE_PATHS": 0,
                "TARGETS": [target_coordinate],
            },
            "NONCE": nonce,
            "OBSERVATION_RULE": (
                "RECEIVER_BACKED_OPENAT_O_NOFOLLOW_FSTAT_STREAMING_SHA256"
            ),
            "OUTPUT_CONTRACT": {
                "FILE_SHA256": expected_output_sha256,
                "SIZE_BYTES": len(effect_input),
                "TARGET": target_coordinate,
            },
            "POINTER_VERSION": None,
            "RECEIVER": {
                "ADAPTER_REF": "receiver.local.create-new-file.v1",
                "HANDLER_REF": "effect.local.create-new-file.v1",
            },
            "RISK": "CANDIDATE_EXTERNAL_FILE_CREATE_NOT_AUTHORIZED",
            "ROLLBACK_OR_COMPENSATION": (
                "NO_AUTOMATIC_ROLLBACK_AFTER_EXTERNAL_EFFECT;"
                "QUARANTINE_NO_REAPPLY_ON_PARTIAL_UNKNOWN_OR_POST_EFFECT_CAS"
            ),
            "STOP_CONDITIONS": [
                "D8_NOT_EXACT_OR_EXPIRED",
                "AUTHORITY_NOT_EXACT_OR_EXPIRED",
                "BINDING_NOT_EXACT",
                "BASE_STATE_UNKNOWN_OR_DRIFT",
                "TARGET_NOT_ABSENT",
                "PREPARE_NOT_PROVEN_NO_EFFECT",
                "PERMIT_EXPIRED",
                "OBSERVATION_PARTIAL_OR_UNKNOWN",
                "POST_EFFECT_CAS_CONFLICT",
            ],
            "TARGET": target_coordinate,
            "TIMEOUT": {"SECONDS": 30},
            "TTL": {"SECONDS": 300},
        }
    )

    authorization_request = _seal(
        {
            "SCHEMA_ID": "W7TP_REAL_E2E_SINGLE_USE_AUTHORIZATION_REQUEST_v1",
            "AUTHORITY_STATE": "NOT_GRANTED",
            "BASE_STATE_REF": base_state.ref,
            "BINDING_PACKET_REF": binding_packet.ref,
            "D8_STATE": "NOT_GRANTED",
            "EFFECT_CONTRACT_REF": effect_contract.ref,
            "EFFECT_CONTRACT_SHA256": effect_contract.sha256,
            "EVIDENCE_DESTINATION": effect_contract.body["EVIDENCE_DESTINATION"],
            "EXPECTED_EFFECT": effect_contract.body["EXPECTED_EFFECT"],
            "EXPIRY_PROPOSAL": "FOUNDER_DECISION_TIME_PLUS_300_SECONDS",
            "FIVE_ADAPTER_HASHES": [
                packet.body["ADAPTER_SHA256"] for packet in manifest_packets
            ],
            "FIVE_BINDING_MANIFEST_HASHES": [
                packet.sha256 for packet in manifest_packets
            ],
            "FOUNDER_DECISION_REQUIRED": True,
            "MAXIMUM_EFFECT": effect_contract.body["MAXIMUM_EFFECT"],
            "NONCE": nonce,
            "REJECTED_D8": {
                "SHA256": EXPIRED_PROMOTION_D8_SHA256,
                "REASONS": [
                    "EXPIRED",
                    "SCOPE=PROMOTE_ACCEPTED_CANDIDATE",
                    "RUNTIME_EFFECT_SCOPE_MISMATCH",
                ],
                "REUSED": False,
            },
            "REQUEST_IS_NOT_AUTHORITY": True,
            "ROLLBACK_OR_COMPENSATION": effect_contract.body[
                "ROLLBACK_OR_COMPENSATION"
            ],
            "STOP_CONDITIONS": effect_contract.body["STOP_CONDITIONS"],
            "TARGET": target_coordinate,
            "TOTAL_FIELD_REVIEW_REQUIRED": True,
        }
    )

    document = _seal(
        {
            "SCHEMA_ID": "W7TP_STATE_FIELD_REAL_E2E_BINDING_BUNDLE_CANDIDATE_v1",
            "AUTHORIZATION_REQUEST": {
                **dict(authorization_request.body),
                "REF": authorization_request.ref,
                "SHA256": authorization_request.sha256,
            },
            "BINDING_PACKET": {
                **dict(binding_packet.body),
                "REF": binding_packet.ref,
                "SHA256": binding_packet.sha256,
            },
            "EFFECT_CONTRACT": {
                **dict(effect_contract.body),
                "REF": effect_contract.ref,
                "SHA256": effect_contract.sha256,
            },
            "MANIFESTS": [
                {**dict(packet.body), "REF": packet.ref, "SHA256": packet.sha256}
                for packet in manifest_packets
            ],
            "STATE": "REAL_E2E_BINDING_BUNDLE_CANDIDATE_READY",
            "AUTHORITY_STATE": "NOT_GRANTED",
            "D8_STATE": "NOT_GRANTED",
            "REAL_E2E_EXECUTED": False,
        }
    )

    return RealE2EBindingBundleCandidate(
        verification_evidence=tuple(verification_packets),
        manifests=tuple(manifest_packets),
        binding_records=tuple(binding_packets),
        binding_packet=binding_packet,
        base_state=base_state,
        effect_input=effect_input,
        effect_input_ref=effect_input_ref,
        effect_contract=effect_contract,
        authorization_request=authorization_request,
        document=document,
    )
