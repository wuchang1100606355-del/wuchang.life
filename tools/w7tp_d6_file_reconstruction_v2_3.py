#!/usr/bin/env python3
"""V2.3 bridge from discrete D6 state lookup to exact file reconstruction.

This is the minimum adapter between the repository's V2.3 joint-state gate and
the already recovered W7B1 previous-base codec.  It does not reactivate the
V2.1 mesh runtime.  It reconstructs into an anonymous memory map, emits a
metadata-only event stream while materializing the mapped state, re-reads the
target digest, and leaves persistent materialization behind the D8 gate.
"""

from __future__ import annotations

import base64
import hashlib
import json
import mmap
import os
import stat
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

from services.w7tp_gt_mesh_v21.v3_candidate.known_novel_v3 import (
    MODE_PREVIOUS_BASE,
    KnownNovelV3Error,
    canonical_json_bytes as codec_canonical_json_bytes,
    decode_packet,
    encode_previous_base_packet,
)
from tools.w7tp_d6_generative_transmission_verifier_v2_3 import (
    DIMENSIONS,
    verify_d6_generative_transmission,
)
from tools.w7tp_transfer_rule_common import (
    CANONICAL_IDENTITY,
    RuleHold,
    canonical_json,
    object_sha256,
    validate_schema,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKET_SCHEMA = REPO_ROOT / "schemas/8d/d6_generative_transmission_packet_v2_3.schema.json"
FILE_OPERATION_PROFILE = "DISCRETE_FILE_RECONSTRUCTION"
FILE_RECONSTRUCTION_RULE = "W7B1_PREVIOUS_BASE_DISCRETE_FILE_RECONSTRUCTION"
TRANSITION_RULE_ID = "TARGET_BASE_PLUS_MINIMUM_REQUIRED_INDEX_DELTA_V1"
MAX_STORED_PACKET_BYTES = 16 * 1024 * 1024
DEFAULT_STREAM_SEGMENT_BYTES = 64 * 1024


EventSink = Callable[[Mapping[str, Any]], None]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def state_integer_index(value: bytes) -> int:
    """Map exact bytes to one deterministic, lossless-width integer index."""

    return int.from_bytes(hashlib.sha256(value).digest(), "big", signed=False)


def transition_rule() -> dict[str, Any]:
    return {
        "DISCRETE_TRANSITION_RULE_ID": TRANSITION_RULE_ID,
        "OPERATION": "TARGET_BASE_PLUS_MINIMUM_REQUIRED_INDEX_DELTA",
        "NUMERIC_DOMAIN": "INTEGER",
    }


def _validate_output_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise RuleHold("HOLD_OUTPUT_COORDINATE_INVALID")
    if unicodedata.normalize("NFC", value) != value or "\\" in value or "\x00" in value:
        raise RuleHold("HOLD_OUTPUT_COORDINATE_INVALID")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise RuleHold("HOLD_OUTPUT_COORDINATE_INVALID")
    return path.as_posix()


def _joint_state_field(
    *,
    target_identity: str,
    target_snapshot_reference: str,
    reconstruction_coordinate: str,
    design_file_reference: str,
    target_base_reference: str,
    target_base_sha256: str,
    expected_target_sha256: str,
    evidence_destination: str,
    dynamic_context_reference: str,
    codec_packet_sha256: str,
) -> dict[str, Any]:
    return {
        "SEMANTICS": "8_IN_1_SINGLE_STATE_FIELD",
        "REPRESENTATION": "ONE_IMMUTABLE_PACKET_STATE_WITH_EIGHT_COUPLED_PROJECTIONS",
        "PROJECTIONS": {
            "D1": {
                "INTENT_REFERENCE": design_file_reference,
                "TARGET_EFFECT": "RECONSTRUCT_EQUIVALENT_FILE_AT_TARGET_ENDPOINT",
            },
            "D2": {
                "TARGET_FIELD_SNAPSHOT_REFERENCE": target_snapshot_reference,
                "TARGET_BASE_REFERENCE": target_base_reference,
                "TARGET_BASE_SHA256": target_base_sha256,
                "EXPECTED_TARGET_SHA256": expected_target_sha256,
            },
            "D3": {
                "TARGET_IDENTITY": target_identity,
                "RECONSTRUCTION_COORDINATE": reconstruction_coordinate,
            },
            "D4": {
                "CODEC_PACKET_SHA256": codec_packet_sha256,
                "EVIDENCE_DESTINATION": evidence_destination,
            },
            "D5": {
                "EXECUTION_SCOPE": "ANONYMOUS_MMAP_CANDIDATE_NO_PERSISTENT_EFFECT",
                "PERSISTENT_MATERIALIZATION": False,
            },
            "D6": {
                "RECONSTRUCTION_RULE": FILE_RECONSTRUCTION_RULE,
                "TARGET_AWARE": True,
                "DYNAMIC_CONTEXT_REFERENCE": dynamic_context_reference,
            },
            "D7": {
                "MISMATCH_ACTION": "HOLD_WHOLE_STATE_FIELD",
                "RAW_BYTES_IN_EVENT_STREAM": False,
            },
            "D8": {
                "AUTHORITY_SCOPE": "NONE",
                "PERSISTENT_FILE_WRITE_AUTHORIZED": False,
            },
        },
        "COUPLING_GRAPH": {
            "D1": ["D2", "D5", "D8"],
            "D2": ["D3", "D4", "D6", "D7"],
            "D3": ["D2", "D4", "D6"],
            "D4": ["D2", "D5", "D7", "D8"],
            "D5": ["D2", "D4", "D6", "D7"],
            "D6": ["D2", "D3", "D4", "D8"],
            "D7": ["D5", "D6", "D8"],
            "D8": ["D1", "D2", "D4", "D7"],
        },
        "CROSS_DIMENSION_CONSTRAINTS": [
            "D1_D2_TARGET_BOUND",
            "D2_D3_BASE_COORDINATE_BOUND",
            "D3_D4_HASH_EVIDENCE_BOUND",
            "D4_D5_EXECUTION_GATED",
            "D5_D6_RECONSTRUCTION_ONLY",
            "D6_D7_MISMATCH_HOLDS",
            "D7_D8_NO_AUTHORITY_ESCALATION",
            "D8_D1_SCOPE_BOUND",
        ],
        "JOINT_STATE_TRANSITION": "CURRENT_8D_FIELD_TO_RECONSTRUCTED_TARGET_8D_FIELD",
        "CLOSURE_RULE": "ALL_EIGHT_PROJECTIONS_AND_TARGET_EFFECT_REOBSERVED",
        "FAIL_CLOSED_RULE": "ANY_MISMATCH_HOLDS_WHOLE_STATE_FIELD",
    }


def build_file_d6_bundle(
    *,
    target: bytes,
    previous_base: bytes,
    block_size: int,
    source_identity: str,
    target_identity: str,
    target_snapshot_reference: str,
    reconstruction_coordinate: str,
    design_file_reference: str,
    target_base_reference: str,
    output_relative_path: str,
    local_packet_reference: str,
    cloud_packet_reference: str,
    local_llm_organ_reference: str,
    dynamic_context_reference: str,
    nonce: str,
    logical_time: int,
    ttl: int,
    evidence_destination: str,
    lookup_table_id: str = "lookup:file-state-transition:v2.3",
    lookup_table_version: str = "1",
) -> dict[str, Any]:
    """Build one V2.3 packet and all read-only verifier inputs.

    The recovered codec rejects unsupported geometry and high-size inputs with
    stable reasons.  This adapter deliberately does not invent the still
    unknown formal 64-state or 5D transition formula.
    """

    if not isinstance(target, bytes) or not isinstance(previous_base, bytes):
        raise RuleHold("HOLD_FILE_BYTES_INVALID")
    output_coordinate = _validate_output_relative_path(output_relative_path)
    try:
        codec_packet = encode_previous_base_packet(
            target,
            previous_base=previous_base,
            block_size=block_size,
            lookup_ref=target_base_reference,
            lookup_version=lookup_table_version,
        )
        codec_document = json.loads(codec_packet)
    except (KnownNovelV3Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        reason = str(exc) if str(exc) else "CODEC_BUILD_FAILED"
        raise RuleHold(f"HOLD_{reason}") from exc

    source_index = state_integer_index(target)
    target_base_index = state_integer_index(previous_base)
    expected_target_index = source_index
    lookup_table = {
        "LOOKUP_TABLE_ID": lookup_table_id,
        "LOOKUP_TABLE_VERSION": lookup_table_version,
        "ENTRIES": {f"{source_index}:{target_base_index}": expected_target_index},
    }
    rule = transition_rule()
    codec_packet_digest = sha256_bytes(codec_packet)
    target_digest = sha256_bytes(target)
    base_digest = sha256_bytes(previous_base)
    packet = {
        "PACKET_TYPE": "D6_GENERATIVE_TRANSMISSION_PACKET",
        "CAPABILITY_ID": "D6_GENERATIVE_TRANSMISSION",
        "PRIMARY_OPERATION": "D6_GENERATIVE_TRANSMISSION",
        "OPERATION_PROFILE": FILE_OPERATION_PROFILE,
        "CARRIER": "REFERENCE_ONLY",
        "SOURCE_IDENTITY": source_identity,
        "TARGET_IDENTITY": target_identity,
        "CANONICAL_IDENTITY": CANONICAL_IDENTITY,
        "TARGET_FIELD_SNAPSHOT_REFERENCE": target_snapshot_reference,
        "SOURCE_STATE_INTEGER_INDEX": source_index,
        "TARGET_BASE_INTEGER_INDEX": target_base_index,
        "EXPECTED_TARGET_STATE_INTEGER_INDEX": expected_target_index,
        "MINIMUM_REQUIRED_INDEX_DELTA": expected_target_index - target_base_index,
        "LOOKUP_TABLE_ID": lookup_table_id,
        "LOOKUP_TABLE_VERSION": lookup_table_version,
        "LOOKUP_TABLE_DIGEST": object_sha256(lookup_table),
        "DISCRETE_TRANSITION_RULE_ID": TRANSITION_RULE_ID,
        "DISCRETE_TRANSITION_RULE_DIGEST": object_sha256(rule),
        "REFERENCES": sorted(
            {
                design_file_reference,
                target_base_reference,
                local_packet_reference,
                cloud_packet_reference,
                dynamic_context_reference,
            }
        ),
        "RECONSTRUCTION_COORDINATE": reconstruction_coordinate,
        "RECONSTRUCTION_RULES": [
            FILE_RECONSTRUCTION_RULE,
            "TARGET_NATIVE_INTEGER_LOOKUP",
            "NO_PERSISTENT_MATERIALIZATION_WITHOUT_D8",
        ],
        "VERIFICATION_RULES": [
            "TARGET_BASE_SHA256_MATCH",
            "CODEC_PACKET_SHA256_MATCH",
            "EXPECTED_TARGET_STATE_INTEGER_INDEX_MATCH",
            "RECONSTRUCTED_FILE_SHA256_MATCH",
            "D1_D8_JOINT_STATE_RECEIPT_MATCH",
        ],
        "RECEIVER_IDENTITY": target_identity,
        "JOINT_STATE_FIELD": _joint_state_field(
            target_identity=target_identity,
            target_snapshot_reference=target_snapshot_reference,
            reconstruction_coordinate=reconstruction_coordinate,
            design_file_reference=design_file_reference,
            target_base_reference=target_base_reference,
            target_base_sha256=base_digest,
            expected_target_sha256=target_digest,
            evidence_destination=evidence_destination,
            dynamic_context_reference=dynamic_context_reference,
            codec_packet_sha256=codec_packet_digest,
        ),
        "MODEL_ORGAN": {
            "LOCAL_LLM_ORGAN_REFERENCE": local_llm_organ_reference,
            "ROLE": "PASSIVE_REPLACEABLE_REASONING_GENERATION_ORGAN",
            "DYNAMIC_CONTEXT_REFERENCE": dynamic_context_reference,
            "AUTHORITY": "NONE",
        },
        "FILE_RECONSTRUCTION": {
            "DESIGN_FILE_REFERENCE": design_file_reference,
            "CODEC_MODE": "PREVIOUS_BASE_BLOCK_LOOKUP",
            "CODEC_PACKET_ENCODING": "base64",
            "CODEC_PACKET_BYTES": len(codec_packet),
            "CODEC_PACKET_SHA256": codec_packet_digest,
            "CODEC_PACKET_B64": base64.b64encode(codec_packet).decode("ascii"),
            "TARGET_BASE_REFERENCE": target_base_reference,
            "TARGET_BASE_BYTES": len(previous_base),
            "TARGET_BASE_SHA256": base_digest,
            "EXPECTED_TARGET_BYTES": len(target),
            "EXPECTED_TARGET_SHA256": target_digest,
            "OUTPUT_RELATIVE_PATH": output_coordinate,
            "LOCAL_PACKET_REFERENCE": local_packet_reference,
            "CLOUD_PACKET_REFERENCE": cloud_packet_reference,
            "STORAGE_RESOLUTION_ORDER": ["LOCAL", "CLOUD"],
            "MEMORY_MAPPING_MODE": "MMAP_EXCLUSIVE_CREATE",
            "EVENT_STREAM_MODE": "GENERATED_BLOCK_EVENT_STREAM",
            "RAW_BYTES_IN_EVENTS": False,
        },
        "RUNTIME_BOUNDARY": "REPOSITORY_RULE_ONLY_NO_LIVE_EFFECT",
        "NONCE": nonce,
        "LOGICAL_TIME": logical_time,
        "TTL": ttl,
        "EVIDENCE_DESTINATION": evidence_destination,
    }
    validate_schema(packet, PACKET_SCHEMA)
    if codec_document.get("codec_mode") != MODE_PREVIOUS_BASE:
        raise RuleHold("HOLD_FILE_CODEC_MODE_MISMATCH")
    target_snapshot = {
        "TARGET_IDENTITY": target_identity,
        "SNAPSHOT_REFERENCE": target_snapshot_reference,
        "TARGET_BASE_INTEGER_INDEX": target_base_index,
        "RECONSTRUCTION_COORDINATE": reconstruction_coordinate,
    }
    return {
        "PACKET": packet,
        "PACKET_BYTES": canonical_json(packet),
        "LOOKUP_TABLE": lookup_table,
        "TRANSITION_RULE": rule,
        "TARGET_FIELD_SNAPSHOT": target_snapshot,
    }


def build_joint_verification_receipt(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Build D4 verification evidence; this receipt grants no D8 authority."""

    field = packet.get("JOINT_STATE_FIELD")
    if not isinstance(field, Mapping):
        raise RuleHold("HOLD_D1_D8_JOINT_STATE_REPRESENTATION_MISSING")
    return {
        "RECEIPT_TYPE": "D1_D8_JOINT_VERIFICATION_RECEIPT",
        "DIMENSIONS": {dimension: "VERIFIED" for dimension in DIMENSIONS},
        "JOINTLY_CLOSED": True,
        "RESULT": "VERIFIED",
        "PACKET_DIGEST": object_sha256(dict(packet)),
        "JOINT_STATE_DIGEST": object_sha256(dict(field)),
        "AUTHORITY_SCOPE": "NONE",
    }


def _read_bound_packet(path: Path, expected_sha256: str, state_prefix: str) -> bytes | None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RuleHold(f"HOLD_{state_prefix}_PACKET_NOT_REGULAR")
    if metadata.st_size <= 0 or metadata.st_size > MAX_STORED_PACKET_BYTES:
        raise RuleHold(f"HOLD_{state_prefix}_PACKET_SIZE_INVALID")
    data = path.read_bytes()
    if sha256_bytes(data) != expected_sha256:
        raise RuleHold(f"HOLD_{state_prefix}_PACKET_DIGEST_MISMATCH")
    return data


def load_packet_from_dual_storage(
    *,
    local_packet_path: Path,
    cloud_packet_path: Path,
    expected_sha256: str,
) -> tuple[dict[str, Any], str]:
    """Resolve a digest-bound packet local-first, cloud only when local is absent."""

    if len(expected_sha256) != 64 or any(char not in "0123456789abcdef" for char in expected_sha256):
        raise RuleHold("HOLD_PACKET_DIGEST_INVALID")
    data = _read_bound_packet(local_packet_path, expected_sha256, "LOCAL")
    source = "LOCAL"
    if data is None:
        data = _read_bound_packet(cloud_packet_path, expected_sha256, "CLOUD")
        source = "CLOUD"
    if data is None:
        raise RuleHold("HOLD_DUAL_STORAGE_PACKET_NOT_FOUND")
    try:
        packet = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuleHold("HOLD_PACKET_JSON_INVALID") from exc
    if not isinstance(packet, dict) or canonical_json(packet) != data:
        raise RuleHold("HOLD_PACKET_NOT_CANONICAL")
    validate_schema(packet, PACKET_SCHEMA)
    return packet, source


def _read_regular_base(path: Path, expected_size: int, expected_sha256: str) -> bytes:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise RuleHold("HOLD_TARGET_BASE_NOT_FOUND") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RuleHold("HOLD_TARGET_BASE_NOT_REGULAR")
    if metadata.st_size != expected_size:
        raise RuleHold("HOLD_TARGET_BASE_SIZE_MISMATCH")
    value = path.read_bytes()
    if sha256_bytes(value) != expected_sha256:
        raise RuleHold("HOLD_TARGET_BASE_HASH_MISMATCH")
    return value


def reconstruct_file_to_mmap_stream(
    packet: Mapping[str, Any],
    *,
    target_field_snapshot: Mapping[str, Any],
    lookup_table: Mapping[str, Any],
    transition_rule_document: Mapping[str, Any],
    previous_base_path: Path,
    current_logical_time: int,
    event_sink: EventSink | None = None,
    segment_bytes: int = DEFAULT_STREAM_SEGMENT_BYTES,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Reconstruct exact bytes in an ephemeral map and emit ordered metadata events."""

    if packet.get("OPERATION_PROFILE") != FILE_OPERATION_PROFILE:
        raise RuleHold("HOLD_FILE_OPERATION_PROFILE_REQUIRED")
    if isinstance(segment_bytes, bool) or not isinstance(segment_bytes, int) or segment_bytes < 1:
        raise RuleHold("HOLD_STREAM_SEGMENT_SIZE_INVALID")
    file_contract = packet.get("FILE_RECONSTRUCTION")
    if not isinstance(file_contract, Mapping):
        raise RuleHold("HOLD_FILE_RECONSTRUCTION_CONTRACT_MISSING")
    _validate_output_relative_path(str(file_contract.get("OUTPUT_RELATIVE_PATH", "")))

    joint_receipt = build_joint_verification_receipt(packet)
    gate = verify_d6_generative_transmission(
        packet,
        target_field_snapshot=target_field_snapshot,
        lookup_table=lookup_table,
        transition_rule=transition_rule_document,
        current_logical_time=current_logical_time,
        d1_d8_receipt=joint_receipt,
        total_field_decision=None,
        observed_at=observed_at,
    )
    if gate.get("STATE") != "HOLD_TOTAL_FIELD_AUTHORITY_REQUIRED":
        raise RuleHold(str(gate.get("STATE", "HOLD_D6_GATE_FAILED")))
    if gate.get("D1_D8_VERIFICATION") != "VERIFIED_EXTERNAL_RECEIPT":
        raise RuleHold("HOLD_D1_D8_JOINT_VERIFICATION_REQUIRED")

    previous_base = _read_regular_base(
        previous_base_path,
        int(file_contract["TARGET_BASE_BYTES"]),
        str(file_contract["TARGET_BASE_SHA256"]),
    )
    try:
        codec_packet = base64.b64decode(
            str(file_contract["CODEC_PACKET_B64"]).encode("ascii"), validate=True
        )
    except (UnicodeEncodeError, ValueError) as exc:
        raise RuleHold("HOLD_CODEC_PACKET_ENCODING_INVALID") from exc
    if len(codec_packet) != file_contract["CODEC_PACKET_BYTES"]:
        raise RuleHold("HOLD_CODEC_PACKET_SIZE_MISMATCH")
    if sha256_bytes(codec_packet) != file_contract["CODEC_PACKET_SHA256"]:
        raise RuleHold("HOLD_CODEC_PACKET_HASH_MISMATCH")
    try:
        decoded = decode_packet(codec_packet, previous_base=previous_base)
    except KnownNovelV3Error as exc:
        raise RuleHold(f"HOLD_{str(exc)}") from exc
    state = decoded.state
    if len(state) != file_contract["EXPECTED_TARGET_BYTES"]:
        raise RuleHold("HOLD_RECONSTRUCTED_FILE_SIZE_MISMATCH")
    if sha256_bytes(state) != file_contract["EXPECTED_TARGET_SHA256"]:
        raise RuleHold("HOLD_RECONSTRUCTED_FILE_HASH_MISMATCH")

    events: list[dict[str, Any]] = []

    def emit(event: str, **fields: Any) -> None:
        record = {
            "SEQUENCE": len(events),
            "EVENT": event,
            "TARGET_IDENTITY": packet["TARGET_IDENTITY"],
            "RAW_BYTES_INCLUDED": False,
            **fields,
        }
        events.append(record)
        if event_sink is not None:
            event_sink(record)

    emit("JOINT_D1_D8_PACKET_VERIFIED", PACKET_DIGEST=object_sha256(dict(packet)))
    mapped = mmap.mmap(-1, len(state), access=mmap.ACCESS_WRITE)
    try:
        emit("ANONYMOUS_MMAP_OPENED", MAPPED_BYTES=len(state))
        for offset in range(0, len(state), segment_bytes):
            end = min(offset + segment_bytes, len(state))
            segment = state[offset:end]
            mapped[offset:end] = segment
            emit(
                "GENERATED_SEGMENT_MATERIALIZED",
                BYTE_OFFSET=offset,
                BYTE_COUNT=len(segment),
                SEGMENT_SHA256=sha256_bytes(segment),
            )
        mapped.flush()
        mapped.seek(0)
        reobserved_sha256 = hashlib.sha256(mapped).hexdigest()
        if reobserved_sha256 != file_contract["EXPECTED_TARGET_SHA256"]:
            raise RuleHold("HOLD_MMAP_REOBSERVED_HASH_MISMATCH")
        emit(
            "TARGET_STATE_REOBSERVED",
            TARGET_BYTES=len(state),
            TARGET_SHA256=reobserved_sha256,
        )
        mapped[:] = b"\x00" * len(state)
        mapped.flush()
        emit("ANONYMOUS_MMAP_ZEROED_AND_RELEASED", MAPPED_BYTES=len(state))
    finally:
        mapped.close()

    return {
        "STATE": "CANDIDATE_FILE_RECONSTRUCTION_VERIFIED_IN_ANONYMOUS_MMAP_NO_LIVE_EFFECT",
        "SOURCE_IDENTITY": packet["SOURCE_IDENTITY"],
        "TARGET_IDENTITY": packet["TARGET_IDENTITY"],
        "TARGET_STATE_INTEGER_INDEX": gate["TARGET_STATE_INTEGER_INDEX"],
        "RECONSTRUCTED_FILE_BYTES": len(state),
        "RECONSTRUCTED_FILE_SHA256": file_contract["EXPECTED_TARGET_SHA256"],
        "KNOWN_BLOCK_COUNT": decoded.known_count,
        "NOVEL_BLOCK_COUNT": decoded.novel_count,
        "MMAP_MODE": "ANONYMOUS_EPHEMERAL",
        "EVENT_STREAM_MODE": "CALLBACK_ORDERED_METADATA_ONLY",
        "EVENT_COUNT": len(events),
        "EVENTS": events,
        "RAW_BYTES_EMITTED": False,
        "PERSISTENT_FILE_WRITTEN": False,
        "PYTHON_IMMUTABLE_BUFFER_ZEROIZATION": "NOT_GUARANTEED",
        "D1_D8_JOINT_VERIFICATION": "VERIFIED_D4_ONLY",
        "D8_AUTHORITY": "NONE",
        "D6_PASS": False,
        "TARGET_PASS": False,
        "CROSS_NODE_PASS": False,
        "END_TO_END_PASS": False,
    }


__all__ = [
    "FILE_OPERATION_PROFILE",
    "FILE_RECONSTRUCTION_RULE",
    "build_file_d6_bundle",
    "build_joint_verification_receipt",
    "load_packet_from_dual_storage",
    "reconstruct_file_to_mmap_stream",
    "sha256_bytes",
    "state_integer_index",
    "transition_rule",
]
