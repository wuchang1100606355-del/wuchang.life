#!/usr/bin/env python3
"""W7TP / 8D ADI V2.3 Origin Cell Generative State Transmission successor.

Founder-defined semantics implemented here:
- Difference Analysis is source-side understanding only. It is not transmission.
- Rule Formation converts reconstructable material into deterministic rules.
- U is the remaining raw material that the rule base cannot provide.
- A packet can therefore have raw_material_u_bytes == 0 while wire_bytes > 0.
- Reconstruction is model-agnostic: any AI or conventional program can reproduce
  the state by following the JSON contract and deterministic opcode semantics.
- D1..D8 are one coupled state field, not eight sequential workflow steps.

This file is a canonical-quality successor candidate. It does not mutate any
canonical pointer, D8 authority record, service, or runtime binding by itself.
"""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

PROTOCOL_VERSION = "2.3"
PACKET_SCHEMA = "w7tp-8dadi-origin-cell-gst-universal/2.3-founder-successor-candidate"
PACKET_TYPE = "ORIGIN_CELL_GENERATIVE_STATE_PACKET"
EXECUTOR_CONTRACT = "w7tp-origin-cell-universal-executor/1"
FOUNDER_DEFINITION = "W7TP/8D ADI V2.3"
DIMENSIONS = tuple(f"D{i}" for i in range(1, 9))
MAX_RECONSTRUCTED_BYTES = 8 * 1024 * 1024 * 1024
MAX_U_SEGMENT_BYTES = 16 * 1024 * 1024

FORBIDDEN_TRANSFER_KEYS = frozenset(
    {
        "delta",
        "diff",
        "patch",
        "patch_blob",
        "patch_cells",
        "changed_bytes",
        "binary_delta",
        "rsync_delta",
    }
)
ALLOWED_OPS = frozenset({"BASE_INDICES", "BASE_RLE", "U_SEGMENT"})


class OriginCellHold(RuntimeError):
    """Fail-closed protocol error with a stable code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _walk_keys(value: Any) -> Iterator[str]:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            yield str(key)
            yield from _walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_keys(nested)


def _safe_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise OriginCellHold("HOLD_PATH_INVALID")
    posix = Path(value)
    if posix.is_absolute() or ".." in posix.parts:
        raise OriginCellHold("HOLD_PATH_ESCAPES_ROOT")
    normalized = posix.as_posix()
    if normalized in {".", ""}:
        raise OriginCellHold("HOLD_PATH_INVALID")
    return normalized


def material_base_atoms(base_id: str) -> tuple[bytes, ...]:
    """Return deterministic material atoms supplied by the rule base.

    ASCII26_SYMBOLS_V1 includes the Latin alphabet, digits, punctuation,
    space, TAB, LF and CR. OCTET256_V1 is a generic byte-atom base.
    These are receiver-side rule materials, not source raw payload.
    """

    if base_id == "ASCII26_SYMBOLS_V1":
        codes = [9, 10, 13, *range(32, 127)]
        return tuple(bytes([code]) for code in codes)
    if base_id == "OCTET256_V1":
        return tuple(bytes([code]) for code in range(256))
    raise OriginCellHold("HOLD_MATERIAL_BASE_UNSUPPORTED")


def material_base_contract(base_id: str) -> dict[str, Any]:
    atoms = material_base_atoms(base_id)
    if base_id == "ASCII26_SYMBOLS_V1":
        derivation = "bytes:[0x09,0x0a,0x0d]+range(0x20,0x7f)"
    else:
        derivation = "bytes:range(0x00,0x100)"
    serialized_atoms = [base64.b64encode(atom).decode("ascii") for atom in atoms]
    return {
        "base_id": base_id,
        "derivation": derivation,
        "atom_count": len(atoms),
        "atom_table_sha256": sha256_bytes(canonical_json_bytes(serialized_atoms)),
    }


def protocol_descriptor() -> dict[str, Any]:
    """Machine-readable semantics for model-independent implementations."""

    return {
        "schema_version": "w7tp-origin-cell-universal-protocol-descriptor/1",
        "founder_definition": FOUNDER_DEFINITION,
        "packet_schema": PACKET_SCHEMA,
        "packet_type": PACKET_TYPE,
        "executor_contract": EXECUTOR_CONTRACT,
        "difference_analysis": {
            "role": "SOURCE_SIDE_UNDERSTANDING_ONLY",
            "transmission_method": False,
            "payload": False,
        },
        "rule_formation": {
            "role": "CONVERT_RECONSTRUCTABLE_STRUCTURE_TO_RULES",
            "remaining_material_symbol": "U",
        },
        "raw_material_accounting": {
            "definition": "sum(decoded U segment bytes)",
            "zero_raw_material_does_not_mean_zero_wire_bytes": True,
        },
        "material_bases": [
            material_base_contract("ASCII26_SYMBOLS_V1"),
            material_base_contract("OCTET256_V1"),
        ],
        "opcodes": {
            "BASE_INDICES": "append base atom for each integer in indices, in order",
            "BASE_RLE": "append base atom[index] exactly count times",
            "U_SEGMENT": "append base64-decoded U segment referenced by segment_id",
        },
        "verification": "reconstructed bytes and SHA-256 must equal packet commitments",
        "authority": "packet reconstruction never creates D8 authority",
    }


def observe_perspectives(data: bytes, *, base_id: str) -> list[dict[str, Any]]:
    """Create incomplete source-side views P_i of one factual byte state F."""

    atoms = material_base_atoms(base_id)
    index_by_atom = {atom: index for index, atom in enumerate(atoms)}
    covered = sum(1 for byte in data if bytes([byte]) in index_by_atom)
    counts = Counter(data)
    runs: list[tuple[int, int]] = []
    if data:
        current = data[0]
        count = 1
        for byte in data[1:]:
            if byte == current:
                count += 1
            else:
                runs.append((current, count))
                current, count = byte, 1
        runs.append((current, count))
    return [
        {
            "perspective": "SEQUENCE",
            "bytes": len(data),
            "sha256": sha256_bytes(data),
        },
        {
            "perspective": "MATERIAL_COVERAGE",
            "base_id": base_id,
            "covered_bytes": covered,
            "uncovered_bytes": len(data) - covered,
        },
        {
            "perspective": "FREQUENCY",
            "distinct_byte_values": len(counts),
            "top": sorted(
                ({"byte": byte, "count": count} for byte, count in counts.items()),
                key=lambda item: (-item["count"], item["byte"]),
            )[:16],
        },
        {
            "perspective": "RUN_STRUCTURE",
            "run_count": len(runs),
            "repeated_runs": sum(1 for _, count in runs if count >= 4),
            "longest_run": max((count for _, count in runs), default=0),
        },
    ]


def difference_analysis(perspectives: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Analyze differences/relations between P_i without creating transport data."""

    by_name = {
        item.get("perspective"): dict(item)
        for item in perspectives
        if isinstance(item, Mapping) and isinstance(item.get("perspective"), str)
    }
    sequence = by_name.get("SEQUENCE", {})
    coverage = by_name.get("MATERIAL_COVERAGE", {})
    runs = by_name.get("RUN_STRUCTURE", {})
    if not sequence or not coverage or not runs:
        raise OriginCellHold("HOLD_PERSPECTIVES_INCOMPLETE")
    if sequence.get("bytes") != (
        int(coverage.get("covered_bytes", -1))
        + int(coverage.get("uncovered_bytes", -1))
    ):
        raise OriginCellHold("HOLD_PERSPECTIVE_RELATION_MISMATCH")
    return {
        "analysis_role": "UNDERSTANDING_NOT_TRANSMISSION",
        "same_fact_binding": sequence.get("sha256"),
        "relations": {
            "all_material_available_in_base": coverage.get("uncovered_bytes") == 0,
            "has_repeat_structure": int(runs.get("repeated_runs", 0)) > 0,
            "source_bytes": sequence.get("bytes"),
        },
        "candidate_rule_opportunities": [
            name
            for name, enabled in (
                ("BASE_MATERIAL_REFERENCE", coverage.get("covered_bytes", 0) > 0),
                ("RUN_LENGTH_RULE", int(runs.get("repeated_runs", 0)) > 0),
                ("U_MATERIAL_REQUIRED", int(coverage.get("uncovered_bytes", 0)) > 0),
            )
            if enabled
        ],
    }


def _append_base_ops(
    ops: list[dict[str, Any]],
    indices: list[int],
    *,
    rle_threshold: int = 4,
) -> None:
    if not indices:
        return
    plain: list[int] = []

    def flush_plain() -> None:
        if plain:
            ops.append({"op": "BASE_INDICES", "indices": list(plain)})
            plain.clear()

    start = 0
    while start < len(indices):
        end = start + 1
        while end < len(indices) and indices[end] == indices[start]:
            end += 1
        count = end - start
        if count >= rle_threshold:
            flush_plain()
            ops.append({"op": "BASE_RLE", "index": indices[start], "count": count})
        else:
            plain.extend(indices[start:end])
        start = end
    flush_plain()


def form_rules(data: bytes, *, base_id: str) -> dict[str, Any]:
    """Form deterministic reconstruction rules and isolate irreducible material U."""

    atoms = material_base_atoms(base_id)
    index_by_byte = {atom[0]: index for index, atom in enumerate(atoms)}
    ops: list[dict[str, Any]] = []
    u_segments: list[dict[str, Any]] = []
    pending_indices: list[int] = []
    pending_u = bytearray()

    def flush_indices() -> None:
        if pending_indices:
            _append_base_ops(ops, pending_indices)
            pending_indices.clear()

    def flush_u() -> None:
        if pending_u:
            segment_id = f"u{len(u_segments):06d}"
            raw = bytes(pending_u)
            u_segments.append(
                {
                    "segment_id": segment_id,
                    "bytes": len(raw),
                    "sha256": sha256_bytes(raw),
                    "base64": base64.b64encode(raw).decode("ascii"),
                }
            )
            ops.append({"op": "U_SEGMENT", "segment_id": segment_id})
            pending_u.clear()

    for byte in data:
        index = index_by_byte.get(byte)
        if index is None:
            flush_indices()
            pending_u.append(byte)
            if len(pending_u) >= MAX_U_SEGMENT_BYTES:
                flush_u()
        else:
            flush_u()
            pending_indices.append(index)
    flush_indices()
    flush_u()

    raw_u_bytes = sum(segment["bytes"] for segment in u_segments)
    return {
        "ops": ops,
        "u_segments": u_segments,
        "raw_material_u_bytes": raw_u_bytes,
        "rule_formed_bytes": len(data) - raw_u_bytes,
    }


def _packet_without_hash(packet: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(packet))
    copied.pop("packet_sha256", None)
    return copied


def packet_sha256(packet: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(_packet_without_hash(packet)))


def build_file_cell(
    data: bytes,
    *,
    relative_path: str,
    base_id: str = "ASCII26_SYMBOLS_V1",
) -> dict[str, Any]:
    path = _safe_relative_path(relative_path)
    perspectives = observe_perspectives(data, base_id=base_id)
    analysis = difference_analysis(perspectives)
    formed = form_rules(data, base_id=base_id)
    return {
        "path": path,
        "base_id": base_id,
        "target_bytes": len(data),
        "target_sha256": sha256_bytes(data),
        "program": formed["ops"],
        "material_u": formed["u_segments"],
        "formation_evidence": {
            "source_perspective_sha256": analysis["same_fact_binding"],
            "rule_formed_bytes": formed["rule_formed_bytes"],
            "raw_material_u_bytes": formed["raw_material_u_bytes"],
            "difference_analysis_transmitted": False,
        },
    }


def build_packet(
    files: Mapping[str, bytes],
    *,
    intent_ref: str = "FOUNDER_DEFINED_ORIGIN_CELL_RECONSTRUCTION",
    default_base_id: str = "ASCII26_SYMBOLS_V1",
    per_file_base: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if not isinstance(files, Mapping) or not files:
        raise OriginCellHold("HOLD_SOURCE_FILES_REQUIRED")
    per_file_base = per_file_base or {}
    cells = [
        build_file_cell(
            bytes(files[path]),
            relative_path=path,
            base_id=per_file_base.get(path, default_base_id),
        )
        for path in sorted(files)
    ]
    raw_u_bytes = sum(
        int(cell["formation_evidence"]["raw_material_u_bytes"]) for cell in cells
    )
    target_bytes = sum(int(cell["target_bytes"]) for cell in cells)
    bases = sorted({cell["base_id"] for cell in cells})
    packet: dict[str, Any] = {
        "schema_version": PACKET_SCHEMA,
        "packet_type": PACKET_TYPE,
        "protocol_version": PROTOCOL_VERSION,
        "executor_contract": EXECUTOR_CONTRACT,
        "founder_definition": FOUNDER_DEFINITION,
        "joint_state_field": {
            "D1": {
                "intent_ref": intent_ref,
                "effect": "RECONSTRUCT_FACT_STATE",
            },
            "D2": {
                "source_state": "OBSERVED",
                "target_state": "RECONSTRUCTED_EXACT_BYTES",
                "file_count": len(cells),
            },
            "D3": {
                "coordinate_type": "RELATIVE_STATE_TREE",
                "paths": [cell["path"] for cell in cells],
            },
            "D4": {
                "verification": "PER_FILE_SHA256_AND_SIZE",
                "packet_self_hash": True,
            },
            "D5": {
                "execution_policy": "DETERMINISTIC_ALLOWLISTED_REFERENCE_EXECUTOR",
                "arbitrary_code_execution": False,
                "canonical_pointer_write": False,
                "service_restart": False,
            },
            "D6": {
                "mode": "GENERATIVE_STATE_FROM_RULE_BASE_PLUS_U",
                "difference_analysis_role": "UNDERSTANDING_ONLY_NOT_TRANSMISSION",
                "difference_analysis_transmitted": False,
                "differential_payload_bytes": 0,
                "full_target_bytes_transmitted": 0,
                "raw_material_u_bytes": raw_u_bytes,
                "target_fact_bytes": target_bytes,
                "wire_bytes_metric": "CANONICAL_SERIALIZED_PACKET_BYTES",
            },
            "D7": {
                "fail_closed_on_packet_self_hash_mismatch": True,
                "fail_closed_on_rule_base_drift": True,
                "fail_closed_on_path_escape": True,
                "fail_closed_on_output_hash_mismatch": True,
                "max_reconstructed_bytes": MAX_RECONSTRUCTED_BYTES,
            },
            "D8": {
                "authority": "EXTERNAL_TOTAL_FIELD_REQUIRED",
                "canonical_runtime_effect": False,
                "model_authority": False,
            },
            "coupling_rule": "D1_D8_BIND_ONE_STATE_RECONSTRUCTION_FACT",
        },
        "protocol_descriptor_sha256": sha256_bytes(
            canonical_json_bytes(protocol_descriptor())
        ),
        "material_base_contracts": [
            material_base_contract(base_id) for base_id in bases
        ],
        "file_cells": cells,
        "metrics": {
            "raw_material_u_bytes": raw_u_bytes,
            "target_fact_bytes": target_bytes,
            "difference_analysis_payload_bytes": 0,
            "differential_payload_bytes": 0,
            "full_target_bytes_transmitted": 0,
        },
        "packet_sha256": "",
    }
    packet["packet_sha256"] = packet_sha256(packet)
    validate_packet(packet)
    return packet


def build_packet_from_tree(
    root: Path,
    *,
    default_base_id: str = "ASCII26_SYMBOLS_V1",
    per_file_base: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if not root.is_dir():
        raise OriginCellHold("HOLD_SOURCE_ROOT_MISSING")
    files: dict[str, bytes] = {}
    for path in sorted(
        candidate for candidate in root.rglob("*") if candidate.is_file()
    ):
        if path.is_symlink():
            raise OriginCellHold("HOLD_SOURCE_SYMLINK_FORBIDDEN")
        relative = path.relative_to(root).as_posix()
        files[relative] = path.read_bytes()
    if not files:
        raise OriginCellHold("HOLD_SOURCE_FILES_REQUIRED")
    return build_packet(
        files,
        default_base_id=default_base_id,
        per_file_base=per_file_base,
    )


def _validate_material_base_contracts(packet: Mapping[str, Any]) -> None:
    contracts = packet.get("material_base_contracts")
    if not isinstance(contracts, list) or not contracts:
        raise OriginCellHold("HOLD_MATERIAL_BASE_CONTRACTS_INVALID")
    seen: set[str] = set()
    for contract in contracts:
        if not isinstance(contract, Mapping):
            raise OriginCellHold("HOLD_MATERIAL_BASE_CONTRACT_INVALID")
        base_id = contract.get("base_id")
        if not isinstance(base_id, str) or base_id in seen:
            raise OriginCellHold("HOLD_MATERIAL_BASE_CONTRACT_INVALID")
        if dict(contract) != material_base_contract(base_id):
            raise OriginCellHold("HOLD_MATERIAL_BASE_DRIFT")
        seen.add(base_id)


def _validated_u_map(cell: Mapping[str, Any]) -> dict[str, bytes]:
    material_u = cell.get("material_u")
    if not isinstance(material_u, list):
        raise OriginCellHold("HOLD_MATERIAL_U_INVALID")
    result: dict[str, bytes] = {}
    for segment in material_u:
        if not isinstance(segment, Mapping):
            raise OriginCellHold("HOLD_MATERIAL_U_SEGMENT_INVALID")
        segment_id = segment.get("segment_id")
        if not isinstance(segment_id, str) or segment_id in result:
            raise OriginCellHold("HOLD_MATERIAL_U_SEGMENT_INVALID")
        try:
            raw = base64.b64decode(segment.get("base64", ""), validate=True)
        except Exception as exc:
            raise OriginCellHold("HOLD_MATERIAL_U_BASE64_INVALID") from exc
        if len(raw) > MAX_U_SEGMENT_BYTES:
            raise OriginCellHold("HOLD_MATERIAL_U_SEGMENT_TOO_LARGE")
        if (
            len(raw) != segment.get("bytes")
            or sha256_bytes(raw) != segment.get("sha256")
        ):
            raise OriginCellHold("HOLD_MATERIAL_U_COMMITMENT_MISMATCH")
        result[segment_id] = raw
    return result


def _iter_cell_bytes(cell: Mapping[str, Any]) -> Iterator[bytes]:
    base_id = cell.get("base_id")
    if not isinstance(base_id, str):
        raise OriginCellHold("HOLD_CELL_BASE_INVALID")
    atoms = material_base_atoms(base_id)
    u_map = _validated_u_map(cell)
    program = cell.get("program")
    if not isinstance(program, list):
        raise OriginCellHold("HOLD_PROGRAM_INVALID")
    for op in program:
        if not isinstance(op, Mapping) or op.get("op") not in ALLOWED_OPS:
            raise OriginCellHold("HOLD_OPCODE_INVALID")
        opcode = op["op"]
        if opcode == "BASE_INDICES":
            if set(op) != {"op", "indices"} or not isinstance(
                op["indices"], list
            ):
                raise OriginCellHold("HOLD_BASE_INDICES_INVALID")
            out = bytearray()
            for index in op["indices"]:
                if (
                    not isinstance(index, int)
                    or isinstance(index, bool)
                    or not 0 <= index < len(atoms)
                ):
                    raise OriginCellHold("HOLD_BASE_INDEX_OUT_OF_RANGE")
                out.extend(atoms[index])
            if out:
                yield bytes(out)
        elif opcode == "BASE_RLE":
            if set(op) != {"op", "index", "count"}:
                raise OriginCellHold("HOLD_BASE_RLE_INVALID")
            index, count = op["index"], op["count"]
            if (
                not isinstance(index, int)
                or isinstance(index, bool)
                or not 0 <= index < len(atoms)
                or not isinstance(count, int)
                or isinstance(count, bool)
                or count < 1
                or count > MAX_RECONSTRUCTED_BYTES
            ):
                raise OriginCellHold("HOLD_BASE_RLE_INVALID")
            yield atoms[index] * count
        else:
            if set(op) != {"op", "segment_id"}:
                raise OriginCellHold("HOLD_U_SEGMENT_OP_INVALID")
            segment_id = op["segment_id"]
            if segment_id not in u_map:
                raise OriginCellHold("HOLD_U_SEGMENT_REF_MISSING")
            yield u_map[segment_id]


def validate_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, Mapping):
        raise OriginCellHold("HOLD_PACKET_MAPPING_REQUIRED")
    if (
        packet.get("schema_version") != PACKET_SCHEMA
        or packet.get("packet_type") != PACKET_TYPE
    ):
        raise OriginCellHold("HOLD_PACKET_SCHEMA_MISMATCH")
    if (
        packet.get("protocol_version") != PROTOCOL_VERSION
        or packet.get("executor_contract") != EXECUTOR_CONTRACT
    ):
        raise OriginCellHold("HOLD_PROTOCOL_CONTRACT_MISMATCH")
    if packet.get("founder_definition") != FOUNDER_DEFINITION:
        raise OriginCellHold("HOLD_FOUNDER_DEFINITION_MISMATCH")
    if packet.get("packet_sha256") != packet_sha256(packet):
        raise OriginCellHold("HOLD_PACKET_SELF_HASH_MISMATCH")
    if packet.get("protocol_descriptor_sha256") != sha256_bytes(
        canonical_json_bytes(protocol_descriptor())
    ):
        raise OriginCellHold("HOLD_PROTOCOL_DESCRIPTOR_DRIFT")
    if FORBIDDEN_TRANSFER_KEYS.intersection(_walk_keys(packet)):
        raise OriginCellHold("HOLD_DIFFERENTIAL_TRANSFER_FORBIDDEN")
    field = packet.get("joint_state_field")
    if (
        not isinstance(field, Mapping)
        or not set(DIMENSIONS).issubset(field)
        or not all(
            isinstance(field.get(dim), Mapping)
            for dim in DIMENSIONS
        )
    ):
        raise OriginCellHold("HOLD_8D_FIELD_INCOMPLETE")
    d5 = field["D5"]
    d6 = field["D6"]
    d8 = field["D8"]
    if (
        d5.get("arbitrary_code_execution") is not False
        or d5.get("canonical_pointer_write") is not False
        or d5.get("service_restart") is not False
    ):
        raise OriginCellHold("HOLD_EXECUTION_POLICY_ESCALATION")
    if (
        d6.get("mode") != "GENERATIVE_STATE_FROM_RULE_BASE_PLUS_U"
        or d6.get("difference_analysis_role")
        != "UNDERSTANDING_ONLY_NOT_TRANSMISSION"
        or d6.get("difference_analysis_transmitted") is not False
        or d6.get("differential_payload_bytes") != 0
        or d6.get("wire_bytes_metric")
        != "CANONICAL_SERIALIZED_PACKET_BYTES"
    ):
        raise OriginCellHold("HOLD_D6_SEMANTICS_MISMATCH")
    if (
        d8.get("authority") != "EXTERNAL_TOTAL_FIELD_REQUIRED"
        or d8.get("canonical_runtime_effect") is not False
        or d8.get("model_authority") is not False
    ):
        raise OriginCellHold("HOLD_D8_AUTHORITY_ESCALATION")
    _validate_material_base_contracts(packet)

    cells = packet.get("file_cells")
    if not isinstance(cells, list) or not cells:
        raise OriginCellHold("HOLD_FILE_CELLS_REQUIRED")
    total_target = 0
    total_u = 0
    paths: set[str] = set()
    for cell in cells:
        if not isinstance(cell, Mapping):
            raise OriginCellHold("HOLD_FILE_CELL_INVALID")
        path = _safe_relative_path(cell.get("path"))
        if path in paths:
            raise OriginCellHold("HOLD_DUPLICATE_FILE_PATH")
        paths.add(path)
        if not _is_sha256(cell.get("target_sha256")):
            raise OriginCellHold("HOLD_TARGET_HASH_INVALID")
        target_bytes = cell.get("target_bytes")
        if (
            not isinstance(target_bytes, int)
            or isinstance(target_bytes, bool)
            or target_bytes < 0
        ):
            raise OriginCellHold("HOLD_TARGET_SIZE_INVALID")
        u_map = _validated_u_map(cell)
        u_bytes = sum(len(raw) for raw in u_map.values())
        evidence = cell.get("formation_evidence")
        if (
            not isinstance(evidence, Mapping)
            or evidence.get("raw_material_u_bytes") != u_bytes
        ):
            raise OriginCellHold("HOLD_RULE_FORMATION_EVIDENCE_MISMATCH")
        if evidence.get("difference_analysis_transmitted") is not False:
            raise OriginCellHold(
                "HOLD_DIFFERENCE_ANALYSIS_TRANSFER_FORBIDDEN"
            )
        produced = 0
        digest = hashlib.sha256()
        for block in _iter_cell_bytes(cell):
            produced += len(block)
            if produced > MAX_RECONSTRUCTED_BYTES:
                raise OriginCellHold(
                    "HOLD_RECONSTRUCTION_LIMIT_EXCEEDED"
                )
            digest.update(block)
        if (
            produced != target_bytes
            or digest.hexdigest() != cell["target_sha256"]
        ):
            raise OriginCellHold(
                "HOLD_CELL_PROGRAM_COMMITMENT_MISMATCH"
            )
        total_target += target_bytes
        total_u += u_bytes
        if total_target > MAX_RECONSTRUCTED_BYTES:
            raise OriginCellHold(
                "HOLD_RECONSTRUCTION_LIMIT_EXCEEDED"
            )
    metrics = packet.get("metrics")
    if not isinstance(metrics, Mapping):
        raise OriginCellHold("HOLD_METRICS_INVALID")
    if (
        metrics.get("raw_material_u_bytes") != total_u
        or metrics.get("target_fact_bytes") != total_target
        or metrics.get("difference_analysis_payload_bytes") != 0
        or metrics.get("differential_payload_bytes") != 0
        or metrics.get("full_target_bytes_transmitted") != 0
    ):
        raise OriginCellHold("HOLD_METRICS_MISMATCH")
    if (
        field["D6"].get("raw_material_u_bytes") != total_u
        or field["D6"].get("target_fact_bytes") != total_target
    ):
        raise OriginCellHold("HOLD_D6_ACCOUNTING_MISMATCH")
    return {
        "state": "PASS_PACKET_VALID",
        "file_count": len(cells),
        "target_fact_bytes": total_target,
        "raw_material_u_bytes": total_u,
        "wire_bytes": len(canonical_json_bytes(packet)),
        "packet_sha256": packet["packet_sha256"],
    }


def reconstruct_to_directory(
    packet: Mapping[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    validation = validate_packet(packet)
    if output_root.exists():
        raise OriginCellHold("HOLD_OUTPUT_ROOT_ALREADY_EXISTS")
    parent = output_root.parent
    parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(
        tempfile.mkdtemp(prefix=f".{output_root.name}.", dir=parent)
    )
    try:
        for cell in packet["file_cells"]:
            relative = _safe_relative_path(cell["path"])
            target = temp_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            written = 0
            with target.open("wb") as handle:
                for block in _iter_cell_bytes(cell):
                    handle.write(block)
                    digest.update(block)
                    written += len(block)
                handle.flush()
                os.fsync(handle.fileno())
            if (
                written != cell["target_bytes"]
                or digest.hexdigest() != cell["target_sha256"]
            ):
                raise OriginCellHold(
                    "HOLD_RECONSTRUCTED_FILE_MISMATCH"
                )
        os.replace(temp_root, output_root)
        temp_root = None
    finally:
        if temp_root is not None:
            shutil.rmtree(temp_root, ignore_errors=True)
    return {
        **validation,
        "state": "PASS_EXACT_GENERATIVE_STATE_RECONSTRUCTION",
        "output_root": str(output_root),
        "difference_analysis_was_transmission": False,
        "canonical_runtime_effect": False,
        "formal_effect_authority": "EXTERNAL_TOTAL_FIELD_REQUIRED",
    }


def reconstruct_single_file_bytes(packet: Mapping[str, Any]) -> bytes:
    validate_packet(packet)
    cells = packet["file_cells"]
    if len(cells) != 1:
        raise OriginCellHold("HOLD_SINGLE_FILE_PACKET_REQUIRED")
    if cells[0]["target_bytes"] > 64 * 1024 * 1024:
        raise OriginCellHold("HOLD_IN_MEMORY_RECONSTRUCTION_LIMIT")
    return b"".join(_iter_cell_bytes(cells[0]))


def selftest() -> dict[str, Any]:
    text = (
        b"HELLO, W7TP / 8D ADI!\n"
        b"ABCDEFGHIJKLMNOPQRSTUVWXYZ\n"
    )
    packet = build_packet(
        {"state.txt": text},
        default_base_id="ASCII26_SYMBOLS_V1",
    )
    rebuilt = reconstruct_single_file_bytes(packet)
    if rebuilt != text:
        raise OriginCellHold(
            "HOLD_SELFTEST_RECONSTRUCTION_MISMATCH"
        )
    if packet["metrics"]["raw_material_u_bytes"] != 0:
        raise OriginCellHold(
            "HOLD_SELFTEST_EXPECTED_ZERO_RAW_MATERIAL"
        )
    wire_bytes = len(canonical_json_bytes(packet))
    if wire_bytes <= 0:
        raise OriginCellHold("HOLD_SELFTEST_WIRE_BYTES_INVALID")
    return {
        "state": "PASS_FOUNDER_SEMANTICS_SELFTEST",
        "raw_source_material_bytes": 0,
        "wire_bytes": wire_bytes,
        "target_bytes": len(text),
        "target_sha256": sha256_bytes(text),
        "difference_analysis_is_transmission": False,
        "model_specific_reasoning_required": False,
        "protocol_descriptor_sha256": packet[
            "protocol_descriptor_sha256"
        ],
        "canonical_runtime_effect": False,
    }


def _load_packet(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise OriginCellHold("HOLD_PACKET_READ_FAILED") from exc
    if not isinstance(value, dict):
        raise OriginCellHold("HOLD_PACKET_MAPPING_REQUIRED")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    describe = sub.add_parser("describe")
    describe.add_argument("--pretty", action="store_true")

    build = sub.add_parser("build")
    build.add_argument("--source-root", type=Path, required=True)
    build.add_argument("--packet", type=Path, required=True)
    build.add_argument(
        "--base",
        choices=("ASCII26_SYMBOLS_V1", "OCTET256_V1"),
        default="ASCII26_SYMBOLS_V1",
    )

    validate = sub.add_parser("validate")
    validate.add_argument("--packet", type=Path, required=True)

    reconstruct = sub.add_parser("reconstruct")
    reconstruct.add_argument("--packet", type=Path, required=True)
    reconstruct.add_argument(
        "--output-root",
        type=Path,
        required=True,
    )

    sub.add_parser("selftest")
    args = parser.parse_args(argv)
    try:
        if args.command == "describe":
            result = protocol_descriptor()
        elif args.command == "build":
            packet = build_packet_from_tree(
                args.source_root,
                default_base_id=args.base,
            )
            if args.packet.exists():
                raise OriginCellHold(
                    "HOLD_PACKET_OUTPUT_ALREADY_EXISTS"
                )
            args.packet.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            args.packet.write_bytes(
                canonical_json_bytes(packet) + b"\n"
            )
            result = {
                "state": "PASS_PACKET_BUILT",
                "packet": str(args.packet),
                "packet_sha256": packet["packet_sha256"],
                "raw_material_u_bytes": packet["metrics"][
                    "raw_material_u_bytes"
                ],
                "wire_bytes": len(canonical_json_bytes(packet)),
            }
        elif args.command == "validate":
            result = validate_packet(_load_packet(args.packet))
        elif args.command == "reconstruct":
            result = reconstruct_to_directory(
                _load_packet(args.packet),
                args.output_root,
            )
        else:
            result = selftest()
    except OriginCellHold as exc:
        print(
            json.dumps(
                {
                    "state": exc.code,
                    "canonical_runtime_effect": False,
                }
            )
        )
        return 1

    if getattr(args, "pretty", False):
        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(
            json.dumps(
                result,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
