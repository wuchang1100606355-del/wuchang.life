#!/usr/bin/env python3
"""Source-generated-rule Origin Cell candidate for W7TP/8D ADI 2.3.

The source verifies a real source state against explicit source-side generative
provenance, then emits serializable state cells and an inline reconstruction
rule body. A clean receiver needs the committed generic executor, but no prior
target state, target-data base, delta, or target-specific rule profile.

Git, SSH, and the packet carrier are not authority.  This module never writes
canonical pointers, activates a service, or issues a Total Field decision.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any


MIB = 1024 * 1024
PACKET_SCHEMA = "w7tp-8dadi-origin-cell-generative-rule-packet/2.3-candidate"
RECEIPT_SCHEMA = "w7tp-8dadi-origin-cell-generative-rule-receipt/2.3-candidate"
GENERATOR_CONTRACT = "w7tp-8dadi-generic-rule-executor/2.3-candidate"
MIN_DATASET_MIB = 32
MAX_DATASET_MIB = 4096
PREDECESSOR_PROGRAM_SHA256 = "8ff6cb34dca458a33c108b7ae53acd3ac23cf38a8e8ceb67c40fd55ae68cdef1"
PREDECESSOR_RECEIPT_FILE_SHA256 = "a5459ea4edae607ee691844130639f76a822151d14e7a3cf25e9897cdb66e23e"
PREDECESSOR_RECEIPT_BODY_SHA256 = "dc38b90d71f80705e9fca78134196a49f1042a3da6bec3d0173ee3eec5e337fe"
DIMENSIONS = tuple(f"D{i}" for i in range(1, 9))
FORBIDDEN_PACKET_KEYS = frozenset(
    {
        "blob",
        "blobs",
        "base64",
        "literal_bytes",
        "file_fragment",
        "changed_bytes",
        "chunk_payload",
        "chunks",
        "diff",
        "patch",
        "patch_cells",
        "payload",
        "source_target",
        "target_artifact",
    }
)

RULE_ALLOWED_KEYS = {
    "CREATE_DIRECTORY": frozenset({"id", "primitive", "path"}),
    "WRITE_PRNG_BYTES": frozenset({"id", "primitive", "path", "size", "seed"}),
    "WRITE_DETERMINISTIC_BYTES_AT_OFFSETS": frozenset({"id", "primitive", "path", "writes", "size"}),
    "JSONL_WRITE": frozenset({"id", "primitive", "path", "row_count", "default_state", "changed_rows", "namespace"}),
    "SQLITE_BUILD": frozenset({"id", "primitive", "path", "base_rows", "update_rows", "insert_rows", "namespace"}),
    "WRITE_DETERMINISTIC_FILE_SERIES": frozenset({
        "id", "primitive", "directory", "base_count", "file_size", "replace_count",
        "delete_start", "delete_end", "rename_start", "rename_end", "new_count", "namespace",
    }),
}
WRITE_ALLOWED_KEYS = frozenset({"offset", "seed"})


class OriginCellHold(RuntimeError):
    """Fail-closed candidate state with a stable machine-readable code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(MIB)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _validate_dataset_mib(dataset_mib: int) -> None:
    if not isinstance(dataset_mib, int) or isinstance(dataset_mib, bool):
        raise OriginCellHold("HOLD_DATASET_MIB_TYPE")
    if dataset_mib < MIN_DATASET_MIB or dataset_mib > MAX_DATASET_MIB or dataset_mib % 8:
        raise OriginCellHold("HOLD_DATASET_MIB_OUTSIDE_GENERATOR_CONTRACT")


def file_manifest(root: Path) -> tuple[list[dict[str, Any]], int, str]:
    if not root.is_dir():
        raise OriginCellHold("HOLD_STATE_ROOT_MISSING")
    rows: list[dict[str, Any]] = []
    total = 0
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        if path.is_symlink():
            raise OriginCellHold("HOLD_STATE_SYMLINK_FORBIDDEN")
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        rows.append({"path": relative, "size": size, "sha256": sha256_file(path)})
        total += size
    return rows, total, sha256_bytes(canonical_json_bytes(rows))


def deterministic_bytes(seed: bytes, size: int) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < size:
        output.extend(hashlib.sha256(seed + counter.to_bytes(8, "big")).digest())
        counter += 1
    return bytes(output[:size])


def make_json_line(index: int, state: str, namespace: str = "row") -> bytes:
    record = {
        "id": f"{index:010d}",
        "group": f"g{index % 97:02d}",
        "state": state,
        "value": hashlib.sha256(f"{namespace}:{index}".encode()).hexdigest(),
    }
    prefix = json.dumps(record, separators=(",", ":"), ensure_ascii=True)[:-1] + ',"pad":"'
    suffix = '"}\n'
    padding = 512 - len(prefix.encode()) - len(suffix.encode())
    if padding < 0:
        raise OriginCellHold("HOLD_JSON_RULE_RECORD_TOO_LARGE")
    line = (prefix + ("x" * padding) + suffix).encode()
    if len(line) != 512:
        raise OriginCellHold("HOLD_JSON_RULE_RECORD_SIZE_MISMATCH")
    return line


def _require_new_root(root: Path) -> None:
    if root.exists():
        raise OriginCellHold("HOLD_OUTPUT_ROOT_ALREADY_EXISTS")
    root.mkdir(parents=True)


def _source_recipe_path(source_root: Path) -> Path:
    return source_root.parent / f"{source_root.name}.gst-source-recipe.json"


def _build_fixture_recipe(dataset_mib: int, variant: int) -> dict[str, Any]:
    """Build synthetic source provenance; this is not used by the receiver."""

    _validate_dataset_mib(dataset_mib)
    if not isinstance(variant, int) or isinstance(variant, bool) or variant < 0:
        raise OriginCellHold("HOLD_SOURCE_VARIANT_INVALID")
    binary_mib = dataset_mib * 3 // 8
    json_mib = dataset_mib // 4
    sqlite_mib = dataset_mib // 4
    small_mib = dataset_mib - binary_mib - json_mib - sqlite_mib
    binary_size = binary_mib * MIB
    json_rows = (json_mib * MIB) // 512
    sqlite_rows = max(1, (sqlite_mib * MIB) // (64 * 1024))
    file_count = max(1, (small_mib * MIB) // (32 * 1024))
    namespace = f"source-{variant}"
    rules: list[dict[str, Any]] = [
        {"id": "r001", "primitive": "CREATE_DIRECTORY", "path": "binary"},
        {"id": "r002", "primitive": "WRITE_PRNG_BYTES", "path": "binary/random.bin", "size": binary_size, "seed": 580305 + variant},
        {"id": "r003", "primitive": "CREATE_DIRECTORY", "path": "json"},
        {"id": "r004", "primitive": "JSONL_WRITE", "path": "json/records.jsonl", "row_count": json_rows, "default_state": f"state-{variant}", "changed_rows": [], "namespace": namespace},
        {"id": "r005", "primitive": "CREATE_DIRECTORY", "path": "database"},
        {"id": "r006", "primitive": "SQLITE_BUILD", "path": "database/data.db", "base_rows": sqlite_rows, "update_rows": 0, "insert_rows": 0, "namespace": namespace},
        {"id": "r007", "primitive": "CREATE_DIRECTORY", "path": "files"},
        {"id": "r008", "primitive": "WRITE_DETERMINISTIC_FILE_SERIES", "directory": "files", "base_count": file_count, "file_size": 32 * 1024, "replace_count": 0, "delete_start": 0, "delete_end": 0, "rename_start": 0, "rename_end": 0, "new_count": 16 + variant, "namespace": namespace},
    ]
    return {"schema": "w7tp-source-generative-provenance/1-candidate", "dataset_mib": dataset_mib, "variant": variant, "rules": rules, "execution_order": [rule["id"] for rule in rules]}


def generate_target(root: Path, dataset_mib: int, variant: int = 0) -> None:
    """Create a real synthetic source plus separate source-side provenance."""

    recipe = _build_fixture_recipe(dataset_mib, variant)
    _require_new_root(root)
    execute_reconstruction_rules(root, recipe["rules"], recipe["execution_order"])
    _source_recipe_path(root).write_bytes(canonical_json_bytes(recipe) + b"\n")


def analyze_source_and_generate_rules(source_root: Path) -> dict[str, Any]:
    """Observe a real source state and emit this transition's inline rule body."""

    rows, source_bytes, source_manifest = file_manifest(source_root)
    try:
        recipe = json.loads(_source_recipe_path(source_root).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OriginCellHold("HOLD_SOURCE_GENERATIVE_PROVENANCE_MISSING") from exc
    if not isinstance(recipe, dict) or recipe.get("schema") != "w7tp-source-generative-provenance/1-candidate":
        raise OriginCellHold("HOLD_SOURCE_GENERATIVE_PROVENANCE_INVALID")
    dataset_mib = recipe.get("dataset_mib")
    _validate_dataset_mib(dataset_mib)
    rules = copy.deepcopy(recipe.get("rules"))
    execution_order = copy.deepcopy(recipe.get("execution_order"))
    if not isinstance(rules, list) or not isinstance(execution_order, list):
        raise OriginCellHold("HOLD_SOURCE_GENERATIVE_PROVENANCE_INVALID")
    verification_root = Path(tempfile.mkdtemp(prefix="w7tp-source-analysis-"))
    try:
        execute_reconstruction_rules(verification_root, rules, execution_order)
        _, verification_bytes, verification_manifest = file_manifest(verification_root)
    finally:
        shutil.rmtree(verification_root, ignore_errors=True)
    if verification_manifest != source_manifest or verification_bytes != source_bytes:
        raise OriginCellHold("HOLD_SOURCE_RULES_DO_NOT_RECONSTRUCT_OBSERVED_STATE")
    state_cells = [
        {"cell": "SOURCE_MANIFEST", "manifest_sha256": source_manifest, "bytes": source_bytes, "files": len(rows)},
        {"cell": "DATASET_COORDINATE", "dataset_mib": dataset_mib},
        {"cell": "CONSTRUCTION_GRAPH", "rule_ids": [rule["id"] for rule in rules]},
    ]
    relations = [
        {"from": rules[index]["id"], "to": rules[index + 1]["id"], "relation": "PRECEDES"}
        for index in range(len(rules) - 1)
    ]
    conditions = {
        "receiver_root": "EMPTY_CLEAN_ROOM",
        "executor": "GENERIC_PRIMITIVES_ONLY",
        "previous_state_allowed": False,
        "differential_input_allowed": False,
    }
    return {
        "dataset_mib": dataset_mib,
        "source_manifest_sha256": source_manifest,
        "source_bytes": source_bytes,
        "source_files": len(rows),
        "state_cells": state_cells,
        "reconstruction_rules": rules,
        "execution_order": execution_order,
        "relations": relations,
        "construction_conditions": conditions,
    }


def _safe_rule_path(root: Path, relative: str) -> Path:
    path = root / relative
    if path.resolve() != root.resolve() and root.resolve() not in path.resolve().parents:
        raise OriginCellHold("HOLD_RULE_PATH_ESCAPES_OUTPUT")
    return path


def execute_reconstruction_rules(output_root: Path, rules: list[dict[str, Any]], execution_order: list[str]) -> None:
    """Execute only generic, data-driven primitives received in the packet."""

    by_id = {rule.get("id"): rule for rule in rules if isinstance(rule, dict)}
    if len(by_id) != len(rules) or set(execution_order) != set(by_id):
        raise OriginCellHold("HOLD_RULE_ORDER_INVALID")
    for rule_id in execution_order:
        rule = by_id[rule_id]
        primitive = rule.get("primitive")
        if primitive == "CREATE_DIRECTORY":
            _safe_rule_path(output_root, rule["path"]).mkdir()
        elif primitive == "WRITE_PRNG_BYTES":
            rng = random.Random(rule["seed"])
            with _safe_rule_path(output_root, rule["path"]).open("wb") as handle:
                for _ in range(rule["size"] // MIB):
                    handle.write(rng.randbytes(MIB))
                handle.write(rng.randbytes(rule["size"] % MIB))
        elif primitive == "WRITE_DETERMINISTIC_BYTES_AT_OFFSETS":
            with _safe_rule_path(output_root, rule["path"]).open("r+b") as handle:
                for write in rule["writes"]:
                    handle.seek(write["offset"])
                    handle.write(deterministic_bytes(write["seed"].encode(), rule["size"]))
        elif primitive == "JSONL_WRITE":
            changed = set(rule["changed_rows"])
            with _safe_rule_path(output_root, rule["path"]).open("wb") as handle:
                for index in range(rule["row_count"]):
                    handle.write(make_json_line(index, "changed" if index in changed else rule["default_state"], rule["namespace"]))
        elif primitive == "SQLITE_BUILD":
            connection = sqlite3.connect(_safe_rule_path(output_root, rule["path"]))
            try:
                connection.execute("PRAGMA journal_mode=OFF")
                connection.execute("PRAGMA synchronous=OFF")
                connection.execute("PRAGMA temp_store=MEMORY")
                connection.execute("CREATE TABLE records(id INTEGER PRIMARY KEY, k TEXT, v BLOB)")
                for index in range(rule["base_rows"]):
                    connection.execute("INSERT INTO records(id,k,v) VALUES(?,?,?)", (index, f"key-{index:08d}", deterministic_bytes(f"{rule['namespace']}:db:{index}".encode(), 64 * 1024)))
                    if index % 64 == 63:
                        connection.commit()
                for index in range(rule["update_rows"]):
                    connection.execute("UPDATE records SET k=?,v=? WHERE id=?", (f"changed-{index:08d}", deterministic_bytes(f"{rule['namespace']}:db-change:{index}".encode(), 64 * 1024), index))
                for index in range(rule["insert_rows"]):
                    row_id = rule["base_rows"] + index
                    connection.execute("INSERT INTO records(id,k,v) VALUES(?,?,?)", (row_id, f"new-{row_id:08d}", deterministic_bytes(f"{rule['namespace']}:db-new:{index}".encode(), 64 * 1024)))
                connection.commit()
            finally:
                connection.close()
        elif primitive == "WRITE_DETERMINISTIC_FILE_SERIES":
            directory = _safe_rule_path(output_root, rule["directory"])
            for index in range(rule["base_count"]):
                (directory / f"f{index:05d}.bin").write_bytes(deterministic_bytes(f"{rule['namespace']}:file:{index}".encode(), rule["file_size"]))
            for index in range(rule["replace_count"]):
                (directory / f"f{index:05d}.bin").write_bytes(deterministic_bytes(f"{rule['namespace']}:small-change:{index}".encode(), rule["file_size"]))
            for index in range(rule["delete_start"], rule["delete_end"]):
                (directory / f"f{index:05d}.bin").unlink()
            for renamed_index, index in enumerate(range(rule["rename_start"], rule["rename_end"])):
                (directory / f"f{index:05d}.bin").rename(directory / f"renamed_{renamed_index:03d}.bin")
            for index in range(rule["new_count"]):
                (directory / f"new_{index:03d}.bin").write_bytes(deterministic_bytes(f"{rule['namespace']}:small-new:{index}".encode(), rule["file_size"]))
        else:
            raise OriginCellHold("HOLD_RULE_PRIMITIVE_UNSUPPORTED")


def _without_self_hash(packet: dict[str, Any]) -> dict[str, Any]:
    material = copy.deepcopy(packet)
    material.pop("packet_sha256", None)
    return material


def packet_sha256(packet: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(_without_self_hash(packet)))


def build_rule_packet(
    *,
    source_analysis: dict[str, Any],
    generator_base_sha256: str,
) -> dict[str, Any]:
    dataset_mib = source_analysis.get("dataset_mib")
    _validate_dataset_mib(dataset_mib)
    target_manifest_sha256 = source_analysis.get("source_manifest_sha256")
    for commitment in (target_manifest_sha256, generator_base_sha256):
        if not _is_sha256(commitment):
            raise OriginCellHold("HOLD_PACKET_COMMITMENT_INVALID")
    rules = source_analysis.get("reconstruction_rules")
    execution_order = source_analysis.get("execution_order")
    relations = source_analysis.get("relations")
    conditions = source_analysis.get("construction_conditions")
    state_cells = source_analysis.get("state_cells")
    if not all(isinstance(value, list) for value in (rules, execution_order, relations, state_cells)) or not isinstance(conditions, dict):
        raise OriginCellHold("HOLD_SOURCE_ANALYSIS_INCOMPLETE")
    rule_body_sha256 = sha256_bytes(canonical_json_bytes(rules))

    packet: dict[str, Any] = {
        "schema_version": PACKET_SCHEMA,
        "packet_type": "ORIGIN_CELL_GENERATIVE_RULE_PACKET",
        "protocol_version": "2.3-candidate",
        "joint_state_field": {
            "D1": {"intent": "RECONSTRUCT_EXACT_SOURCE_STATE_FROM_TRANSMITTED_RULE_BODY"},
            "D2": {
                "transition": "EMPTY_RECEIVER_TO_SOURCE_EQUIVALENT_TARGET",
                "target_manifest_sha256": target_manifest_sha256,
            },
            "D3": {
                "dataset_mib": dataset_mib,
                "generator_contract": GENERATOR_CONTRACT,
            },
            "D4": {
                "predecessor_program_sha256": PREDECESSOR_PROGRAM_SHA256,
                "predecessor_receipt_file_sha256": PREDECESSOR_RECEIPT_FILE_SHA256,
                "predecessor_receipt_body_sha256": PREDECESSOR_RECEIPT_BODY_SHA256,
                "generator_base_sha256": generator_base_sha256,
            },
            "D5": {
                "execution_policy": "ISOLATED_TARGET_NATIVE_RECONSTRUCTION_ONLY",
                "canonical_write": False,
                "pointer_write": False,
                "service_restart": False,
            },
            "D6": {
                "mode": "SOURCE_GENERATED_RULE_BODY",
                "generator_base_required": False,
                "target_data_base_required": False,
                "shared_generic_executor_required": True,
                "source_generative_provenance_required": True,
                "byte_materialization_mechanism": "RECONSTRUCTION_RULES_AND_EXECUTION_ORDER",
                "eight_dimensional_role": "GOVERNANCE_CONSTRAINTS_VERIFICATION",
                "transmitted_target_bytes": 0,
                "rule_body_sha256": rule_body_sha256,
            },
            "D7": {
                "fail_closed_on_base_mismatch": True,
                "fail_closed_on_generator_mismatch": True,
                "fail_closed_on_final_manifest_mismatch": True,
            },
            "D8": {
                "authority": "CANDIDATE_ONLY",
                "canonical": False,
                "total_field_decision": "NOT_RUN",
            },
            "coupling_rule": "ALL_D1_D8_COORDINATES_BIND_ONE_GENERATION_TRANSITION",
            "cross_dimension_constraint": "SOURCE_CELLS_RULE_BODY_RELATIONS_CONDITIONS_AND_FINAL_COMMITMENT_MUST_ALL_MATCH",
            "joint_state_transition": "CLEAN_RECEIVER_TO_RULE_GENERATED_TARGET",
            "closure_rule": "EXACT_FINAL_MANIFEST_MATCH",
            "fail_closed_rule": "ANY_COORDINATE_OR_COMMITMENT_MISMATCH_HOLDS",
        },
        "source_state_cells": state_cells,
        "minimum_new_information": {"dataset_mib": dataset_mib},
        "generator_executor": {"contract": GENERATOR_CONTRACT, "implementation_sha256": generator_base_sha256},
        "references": {
            "predecessor_classification": "PROVEN_HISTORICAL_DIFFERENTIAL_RECONSTRUCTION",
            "predecessor_preserved": True,
        },
        "reconstruction_rules": rules,
        "execution_order": execution_order,
        "rule_body_sha256": rule_body_sha256,
        "relations": relations,
        "construction_conditions": conditions,
        "verification_rules": {
            "level": "L1_EXACT_MANIFEST",
            "expected_target_manifest_sha256": target_manifest_sha256,
        },
    }
    packet["packet_sha256"] = packet_sha256(packet)
    return packet


def _walk_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.append(str(key).lower())
            keys.extend(_walk_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.extend(_walk_keys(nested))
    return keys


def transmitted_rule_literal_bytes(value: Any) -> int:
    """Auxiliary byte-literal detector; never use as the authoritative transmission metric."""

    if isinstance(value, (bytes, bytearray, memoryview)):
        return len(value)
    if isinstance(value, dict):
        return sum(transmitted_rule_literal_bytes(nested) for nested in value.values())
    if isinstance(value, list):
        return sum(transmitted_rule_literal_bytes(nested) for nested in value)
    return 0


def validate_reconstruction_rule_schema(rules: list[dict[str, Any]]) -> None:
    """Fail closed on unknown primitives, unknown fields, or malformed nested writes."""

    if not isinstance(rules, list):
        raise OriginCellHold("HOLD_RULE_SCHEMA_INVALID")
    for rule in rules:
        if not isinstance(rule, dict):
            raise OriginCellHold("HOLD_RULE_SCHEMA_INVALID")
        primitive = rule.get("primitive")
        allowed = RULE_ALLOWED_KEYS.get(primitive)
        if allowed is None:
            raise OriginCellHold("HOLD_RULE_PRIMITIVE_UNSUPPORTED")
        if set(rule) != allowed:
            raise OriginCellHold("HOLD_RULE_SCHEMA_UNKNOWN_OR_MISSING_FIELD")
        if primitive == "WRITE_DETERMINISTIC_BYTES_AT_OFFSETS":
            writes = rule.get("writes")
            if not isinstance(writes, list):
                raise OriginCellHold("HOLD_RULE_SCHEMA_INVALID")
            for write in writes:
                if not isinstance(write, dict) or set(write) != WRITE_ALLOWED_KEYS:
                    raise OriginCellHold("HOLD_RULE_SCHEMA_UNKNOWN_OR_MISSING_FIELD")


def validate_rule_packet(packet: dict[str, Any], generator_path: Path | None = None) -> None:
    if not isinstance(packet, dict) or packet.get("schema_version") != PACKET_SCHEMA:
        raise OriginCellHold("HOLD_PACKET_SCHEMA_MISMATCH")
    if packet.get("packet_type") != "ORIGIN_CELL_GENERATIVE_RULE_PACKET":
        raise OriginCellHold("HOLD_PACKET_TYPE_MISMATCH")
    if packet.get("packet_sha256") != packet_sha256(packet):
        raise OriginCellHold("HOLD_PACKET_SELF_HASH_MISMATCH")
    if FORBIDDEN_PACKET_KEYS.intersection(_walk_keys(packet)):
        raise OriginCellHold("HOLD_DIFFERENTIAL_OR_TARGET_BYTES_FORBIDDEN")

    field = packet.get("joint_state_field")
    if not isinstance(field, dict) or any(dimension not in field for dimension in DIMENSIONS):
        raise OriginCellHold("HOLD_JOINT_8D_FIELD_INCOMPLETE")
    for required in (
        "coupling_rule",
        "cross_dimension_constraint",
        "joint_state_transition",
        "closure_rule",
        "fail_closed_rule",
    ):
        if not field.get(required):
            raise OriginCellHold("HOLD_JOINT_8D_COUPLING_INCOMPLETE")

    minimum = packet.get("minimum_new_information")
    if not isinstance(minimum, dict):
        raise OriginCellHold("HOLD_MINIMUM_NEW_INFORMATION_MISSING")
    _validate_dataset_mib(minimum.get("dataset_mib"))
    d6 = field["D6"]
    if not isinstance(d6, dict) or d6.get("mode") != "SOURCE_GENERATED_RULE_BODY":
        raise OriginCellHold("HOLD_D6_SOURCE_RULE_BODY_REQUIRED")
    if d6.get("transmitted_target_bytes") != 0 or d6.get("generator_base_required") is not False:
        raise OriginCellHold("HOLD_D6_TARGET_BYTES_OR_BASE_CONTRACT_INVALID")
    if (
        d6.get("target_data_base_required") is not False
        or d6.get("shared_generic_executor_required") is not True
        or d6.get("source_generative_provenance_required") is not True
        or d6.get("byte_materialization_mechanism") != "RECONSTRUCTION_RULES_AND_EXECUTION_ORDER"
        or d6.get("eight_dimensional_role") != "GOVERNANCE_CONSTRAINTS_VERIFICATION"
    ):
        raise OriginCellHold("HOLD_D6_CLAIM_BOUNDARY_INVALID")

    executor = packet.get("generator_executor")
    verification = packet.get("verification_rules")
    if not isinstance(executor, dict) or not isinstance(verification, dict):
        raise OriginCellHold("HOLD_EXECUTOR_OR_VERIFICATION_CONTRACT_MISSING")
    for commitment in (
        executor.get("implementation_sha256"),
        verification.get("expected_target_manifest_sha256"),
        packet.get("rule_body_sha256"),
    ):
        if not _is_sha256(commitment):
            raise OriginCellHold("HOLD_PACKET_COMMITMENT_INVALID")
    if executor.get("contract") != GENERATOR_CONTRACT:
        raise OriginCellHold("HOLD_GENERATOR_CONTRACT_MISMATCH")
    rules = packet.get("reconstruction_rules")
    if not isinstance(rules, list) or packet["rule_body_sha256"] != sha256_bytes(canonical_json_bytes(rules)):
        raise OriginCellHold("HOLD_RULE_BODY_HASH_MISMATCH")
    validate_reconstruction_rule_schema(rules)
    if transmitted_rule_literal_bytes(rules) != 0:
        raise OriginCellHold("FAIL_HIDDEN_FULL_TRANSFER")
    if any(rule.get("primitive") in {"WRITE_BYTES", "WRITE_FILE_BYTES"} for rule in rules if isinstance(rule, dict)):
        raise OriginCellHold("FAIL_HIDDEN_FULL_TRANSFER")
    if d6.get("rule_body_sha256") != packet["rule_body_sha256"]:
        raise OriginCellHold("HOLD_D6_RULE_BODY_BINDING_MISMATCH")
    if not isinstance(packet.get("execution_order"), list) or not isinstance(packet.get("relations"), list) or not isinstance(packet.get("construction_conditions"), dict):
        raise OriginCellHold("HOLD_RULE_CONTRACT_INCOMPLETE")
    if generator_path is not None and sha256_file(generator_path) != executor["implementation_sha256"]:
        raise OriginCellHold("HOLD_GENERATOR_BASE_HASH_MISMATCH")


def reconstruct_from_rule_packet(packet: dict[str, Any], receiver_root: Path, output_root: Path) -> dict[str, Any]:
    validate_rule_packet(packet, Path(__file__).resolve())
    if not receiver_root.is_dir() or any(receiver_root.iterdir()):
        raise OriginCellHold("HOLD_RECEIVER_NOT_CLEAN_ROOM")
    if output_root.exists():
        raise OriginCellHold("HOLD_OUTPUT_ROOT_ALREADY_EXISTS")

    output_root.mkdir(parents=True)
    execute_reconstruction_rules(output_root, packet["reconstruction_rules"], packet["execution_order"])
    rows, target_bytes, observed_target = file_manifest(output_root)
    expected_target = packet["verification_rules"]["expected_target_manifest_sha256"]
    if observed_target != expected_target:
        raise OriginCellHold("HOLD_FINAL_MANIFEST_MISMATCH")

    receipt: dict[str, Any] = {
        "schema_version": RECEIPT_SCHEMA,
        "state": "PASS_CANDIDATE_SOURCE_GENERATED_RULE_RECONSTRUCTION",
        "packet_sha256": packet["packet_sha256"],
        "packet_bytes": len(canonical_json_bytes(packet)),
        "authoritative_transmission_bytes": len(canonical_json_bytes(packet)),
        "authoritative_transmission_metric": "CANONICAL_SERIALIZED_PACKET_BYTES",
        "dataset_mib": packet["minimum_new_information"]["dataset_mib"],
        "source_generated_rules": len(packet["reconstruction_rules"]),
        "rule_body_transmitted": True,
        "rule_body_bytes": len(canonical_json_bytes(packet["reconstruction_rules"])),
        "state_cell_bytes": len(canonical_json_bytes(packet["source_state_cells"])),
        "transmitted_rule_literal_bytes": transmitted_rule_literal_bytes(packet["reconstruction_rules"]),
        "transmitted_rule_literal_bytes_role": "AUXILIARY_DETECTOR_ONLY",
        "transmitted_rule_structure_bytes": len(canonical_json_bytes(packet["reconstruction_rules"])),
        "transmitted_state_cell_bytes": len(canonical_json_bytes(packet["source_state_cells"])),
        "transmitted_total_bytes": len(canonical_json_bytes(packet)),
        "target_manifest_sha256": observed_target,
        "target_bytes": target_bytes,
        "target_files": len(rows),
        "transmitted_target_bytes": 0,
        "differential_payload_bytes": 0,
        "target_preloaded_special_rules": 0,
        "target_preloaded_target_data": 0,
        "target_preloaded_base_bytes": 0,
        "target_preloaded_special_rule_bytes": 0,
        "full_target_bytes_transmitted": 0,
        "hidden_full_transfer": False,
        "previous_state_used": False,
        "target_data_base_required": False,
        "shared_generic_executor_required": True,
        "source_generative_provenance_required": True,
        "byte_materialization_mechanism": "RECONSTRUCTION_RULES_AND_EXECUTION_ORDER",
        "eight_dimensional_role": "GOVERNANCE_CONSTRAINTS_VERIFICATION",
        "generator_base_sha256": packet["generator_executor"]["implementation_sha256"],
        "canonical": False,
        "runtime_activation": False,
        "total_field_decision": "NOT_RUN",
    }
    receipt["receipt_sha256"] = sha256_bytes(canonical_json_bytes(receipt))
    return receipt


def prepare_workspace(workspace: Path, dataset_mib: int) -> dict[str, Any]:
    if workspace.exists():
        raise OriginCellHold("HOLD_WORKSPACE_ALREADY_EXISTS")
    workspace.mkdir(parents=True)
    source_root = workspace / "source_state"
    receiver_root = workspace / "clean_receiver"
    generate_target(source_root, dataset_mib)
    receiver_root.mkdir()
    analysis = analyze_source_and_generate_rules(source_root)
    rows, target_bytes, target_manifest = file_manifest(source_root)
    generator_hash = sha256_file(Path(__file__).resolve())
    packet = build_rule_packet(
        source_analysis=analysis,
        generator_base_sha256=generator_hash,
    )
    packet_path = workspace / "origin_cell_rule_packet.json"
    packet_path.write_bytes(canonical_json_bytes(packet) + b"\n")
    return {
        "state": "PASS_CANDIDATE_SOURCE_RULE_WORKSPACE_PREPARED",
        "workspace": str(workspace),
        "source_root": str(source_root),
        "receiver_root": str(receiver_root),
        "packet_path": str(packet_path),
        "packet_bytes": packet_path.stat().st_size,
        "target_bytes": target_bytes,
        "target_files": len(rows),
        "target_manifest_sha256": target_manifest,
        "generator_base_sha256": generator_hash,
        "source_generated_rules": len(analysis["reconstruction_rules"]),
        "rule_body_bytes": len(canonical_json_bytes(analysis["reconstruction_rules"])),
        "state_cell_bytes": len(canonical_json_bytes(analysis["state_cells"])),
        "transmitted_rule_literal_bytes": transmitted_rule_literal_bytes(analysis["reconstruction_rules"]),
    }


def _load_packet(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OriginCellHold("HOLD_PACKET_READ_FAILED") from exc
    if not isinstance(value, dict):
        raise OriginCellHold("HOLD_PACKET_SCHEMA_MISMATCH")
    return value


def run_selftest(dataset_mib: int) -> dict[str, Any]:
    root = Path(tempfile.mkdtemp(prefix="w7tp-origin-cell-generative-v2-"))
    try:
        workspace = root / "workspace"
        prepared = prepare_workspace(workspace, dataset_mib)
        packet = _load_packet(Path(prepared["packet_path"]))
        receipt = reconstruct_from_rule_packet(packet, Path(prepared["receiver_root"]), root / "reconstructed")
        if receipt["target_manifest_sha256"] != prepared["target_manifest_sha256"]:
            raise OriginCellHold("HOLD_SELFTEST_TARGET_COMMITMENT_MISMATCH")
        return {
            "state": "PASS_CANDIDATE_TRUE_GST_SELFTEST",
            "dataset_mib": dataset_mib,
            "packet_bytes": prepared["packet_bytes"],
            "target_bytes": receipt["target_bytes"],
            "target_files": receipt["target_files"],
            "target_manifest_sha256": receipt["target_manifest_sha256"],
            "reconstructed_manifest_sha256": receipt["target_manifest_sha256"],
            "manifest_match": True,
            "source_generated_rules": receipt["source_generated_rules"],
            "rule_body_transmitted": receipt["rule_body_transmitted"],
            "rule_body_bytes": receipt["rule_body_bytes"],
            "state_cell_bytes": receipt["state_cell_bytes"],
            "transmitted_rule_literal_bytes": receipt["transmitted_rule_literal_bytes"],
            "transmitted_rule_structure_bytes": receipt["transmitted_rule_structure_bytes"],
            "transmitted_state_cell_bytes": receipt["transmitted_state_cell_bytes"],
            "transmitted_total_bytes": receipt["transmitted_total_bytes"],
            "authoritative_transmission_bytes": receipt["authoritative_transmission_bytes"],
            "authoritative_transmission_metric": receipt["authoritative_transmission_metric"],
            "target_preloaded_special_rules": receipt["target_preloaded_special_rules"],
            "target_preloaded_target_data": receipt["target_preloaded_target_data"],
            "target_preloaded_base_bytes": receipt["target_preloaded_base_bytes"],
            "target_preloaded_special_rule_bytes": receipt["target_preloaded_special_rule_bytes"],
            "full_target_bytes_transmitted": receipt["full_target_bytes_transmitted"],
            "hidden_full_transfer": receipt["hidden_full_transfer"],
            "previous_state_used": receipt["previous_state_used"],
            "transmitted_target_bytes": receipt["transmitted_target_bytes"],
            "differential_payload_bytes": receipt["differential_payload_bytes"],
            "canonical": False,
            "total_field_decision": "NOT_RUN",
        }
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    selftest_parser = subparsers.add_parser("selftest")
    selftest_parser.add_argument("--dataset-mib", type=int, default=MIN_DATASET_MIB)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--workspace", type=Path, required=True)
    prepare_parser.add_argument("--dataset-mib", type=int, default=MIN_DATASET_MIB)

    reconstruct_parser = subparsers.add_parser("reconstruct")
    reconstruct_parser.add_argument("--packet", type=Path, required=True)
    reconstruct_parser.add_argument("--receiver", "--base", dest="receiver", type=Path, required=True)
    reconstruct_parser.add_argument("--output", type=Path, required=True)
    reconstruct_parser.add_argument("--receipt", type=Path)

    manifest_parser = subparsers.add_parser("manifest")
    manifest_parser.add_argument("--root", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "selftest":
            result = run_selftest(args.dataset_mib)
        elif args.command == "prepare":
            result = prepare_workspace(args.workspace, args.dataset_mib)
        elif args.command == "reconstruct":
            packet = _load_packet(args.packet)
            result = reconstruct_from_rule_packet(packet, args.receiver, args.output)
            if args.receipt:
                if args.receipt.exists():
                    raise OriginCellHold("HOLD_RECEIPT_ALREADY_EXISTS")
                args.receipt.parent.mkdir(parents=True, exist_ok=True)
                args.receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            rows, total, digest = file_manifest(args.root)
            result = {
                "state": "PASS_CANDIDATE_MANIFEST_OBSERVED",
                "root": str(args.root),
                "bytes": total,
                "files": len(rows),
                "manifest_sha256": digest,
            }
    except OriginCellHold as exc:
        print(json.dumps({"state": exc.code, "canonical": False, "total_field_decision": "NOT_RUN"}))
        return 1

    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
