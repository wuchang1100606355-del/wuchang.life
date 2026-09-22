#!/usr/bin/env python3
"""Rule-generated Origin Cell successor candidate for W7TP/8D ADI 2.3.

The historical V1 benchmark reconstructed the right target, but its packet
carried changed cell bytes.  This successor keeps that receipt as historical
evidence and changes the active candidate mechanism: the packet carries only
an admitted generator-base reference, a fixed rule profile, coordinates, and
verification commitments.  The receiver applies the rule profile locally.

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
GENERATOR_CONTRACT = "w7tp-8dadi-origin-cell-generator-base/2.3-candidate"
RULE_PROFILE = "COMPLEX_DATASET_TARGET_RULES_V1"
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


def make_json_line(index: int, state: str) -> bytes:
    record = {
        "id": f"{index:010d}",
        "group": f"g{index % 97:02d}",
        "state": state,
        "value": hashlib.sha256(f"row:{index}".encode()).hexdigest(),
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


def generate_base(root: Path, dataset_mib: int) -> None:
    """Materialize the admitted deterministic base without reading a target."""

    _validate_dataset_mib(dataset_mib)
    _require_new_root(root)
    binary_mib = dataset_mib * 3 // 8
    json_mib = dataset_mib // 4
    sqlite_mib = dataset_mib // 4
    small_mib = dataset_mib - binary_mib - json_mib - sqlite_mib

    (root / "binary").mkdir()
    rng = random.Random(0x8DAD1)
    with (root / "binary" / "random.bin").open("wb") as handle:
        for _ in range(binary_mib):
            handle.write(rng.randbytes(MIB))

    (root / "json").mkdir()
    line_count = (json_mib * MIB) // 512
    with (root / "json" / "records.jsonl").open("wb") as handle:
        for index in range(line_count):
            handle.write(make_json_line(index, "base"))

    (root / "database").mkdir()
    database = root / "database" / "data.db"
    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute("PRAGMA synchronous=OFF")
        connection.execute("PRAGMA temp_store=MEMORY")
        connection.execute("CREATE TABLE records(id INTEGER PRIMARY KEY, k TEXT, v BLOB)")
        blob_size = 64 * 1024
        row_count = max(1, (sqlite_mib * MIB) // blob_size)
        for index in range(row_count):
            blob = deterministic_bytes(f"db:{index}".encode(), blob_size)
            connection.execute(
                "INSERT INTO records(id,k,v) VALUES(?,?,?)",
                (index, f"key-{index:08d}", blob),
            )
            if index % 64 == 63:
                connection.commit()
        connection.commit()
    finally:
        connection.close()

    files_dir = root / "files"
    files_dir.mkdir()
    per_file = 32 * 1024
    file_count = max(1, (small_mib * MIB) // per_file)
    for index in range(file_count):
        (files_dir / f"f{index:05d}.bin").write_bytes(
            deterministic_bytes(f"file:{index}".encode(), per_file)
        )


def apply_rule_profile(root: Path, profile_id: str = RULE_PROFILE) -> None:
    """Apply the fixed generation rules; no target bytes or diff are accepted."""

    if profile_id != RULE_PROFILE:
        raise OriginCellHold("HOLD_RULE_PROFILE_UNSUPPORTED")

    binary = root / "binary" / "random.bin"
    size = binary.stat().st_size
    with binary.open("r+b") as handle:
        for index in range(64):
            offset = ((index + 1) * 15485863) % max(4096, size - 4096)
            offset = (offset // 4096) * 4096
            handle.seek(offset)
            handle.write(deterministic_bytes(f"binary-change:{index}".encode(), 4096))

    jsonl = root / "json" / "records.jsonl"
    line_count = jsonl.stat().st_size // 512
    with jsonl.open("r+b") as handle:
        for index in range(min(128, line_count)):
            row = ((index + 1) * 1009) % line_count
            handle.seek(row * 512)
            handle.write(make_json_line(row, "changed"))

    database = root / "database" / "data.db"
    connection = sqlite3.connect(database)
    try:
        maximum_id = connection.execute("SELECT MAX(id) FROM records").fetchone()[0] or 0
        row_ids = [row[0] for row in connection.execute("SELECT id FROM records ORDER BY id LIMIT 64")]
        for index, row_id in enumerate(row_ids):
            connection.execute(
                "UPDATE records SET k=?, v=? WHERE id=?",
                (
                    f"changed-{row_id:08d}",
                    deterministic_bytes(f"db-change:{index}".encode(), 64 * 1024),
                    row_id,
                ),
            )
        for index in range(16):
            row_id = maximum_id + 1 + index
            connection.execute(
                "INSERT INTO records(id,k,v) VALUES(?,?,?)",
                (
                    row_id,
                    f"new-{row_id:08d}",
                    deterministic_bytes(f"db-new:{index}".encode(), 64 * 1024),
                ),
            )
        connection.commit()
    finally:
        connection.close()

    files_dir = root / "files"
    existing = sorted(files_dir.glob("f*.bin"))
    for index, path in enumerate(existing[:32]):
        path.write_bytes(deterministic_bytes(f"small-change:{index}".encode(), path.stat().st_size))
    for path in existing[32:48]:
        path.unlink()
    for index, path in enumerate(existing[48:64]):
        path.rename(files_dir / f"renamed_{index:03d}.bin")
    for index in range(16):
        (files_dir / f"new_{index:03d}.bin").write_bytes(
            deterministic_bytes(f"small-new:{index}".encode(), 32 * 1024)
        )


def generate_target(root: Path, dataset_mib: int, profile_id: str = RULE_PROFILE) -> None:
    generate_base(root, dataset_mib)
    apply_rule_profile(root, profile_id)


def _without_self_hash(packet: dict[str, Any]) -> dict[str, Any]:
    material = copy.deepcopy(packet)
    material.pop("packet_sha256", None)
    return material


def packet_sha256(packet: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(_without_self_hash(packet)))


def build_rule_packet(
    *,
    dataset_mib: int,
    base_manifest_sha256: str,
    target_manifest_sha256: str,
    generator_base_sha256: str,
) -> dict[str, Any]:
    _validate_dataset_mib(dataset_mib)
    for commitment in (base_manifest_sha256, target_manifest_sha256, generator_base_sha256):
        if not _is_sha256(commitment):
            raise OriginCellHold("HOLD_PACKET_COMMITMENT_INVALID")

    packet: dict[str, Any] = {
        "schema_version": PACKET_SCHEMA,
        "packet_type": "ORIGIN_CELL_GENERATIVE_RULE_PACKET",
        "protocol_version": "2.3-candidate",
        "joint_state_field": {
            "D1": {"intent": "RECONSTRUCT_EXACT_TARGET_FROM_ADMITTED_GENERATOR_RULES"},
            "D2": {
                "transition": "GENERATE_FROM_BASE_WITH_RULE_PROFILE",
                "base_manifest_sha256": base_manifest_sha256,
                "target_manifest_sha256": target_manifest_sha256,
            },
            "D3": {
                "dataset_mib": dataset_mib,
                "rule_profile": RULE_PROFILE,
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
                "mode": "RULE_PROFILE_REFERENCE",
                "generator_base_required": True,
                "transmitted_target_bytes": 0,
                "rule_profile": RULE_PROFILE,
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
            "cross_dimension_constraint": "BASE_GENERATOR_PROFILE_AND_FINAL_COMMITMENT_MUST_ALL_MATCH",
            "joint_state_transition": "VERIFIED_BASE_TO_RULE_GENERATED_TARGET",
            "closure_rule": "EXACT_FINAL_MANIFEST_MATCH",
            "fail_closed_rule": "ANY_COORDINATE_OR_COMMITMENT_MISMATCH_HOLDS",
        },
        "target_base_state": {
            "manifest_sha256": base_manifest_sha256,
            "generator_contract": GENERATOR_CONTRACT,
            "generator_base_sha256": generator_base_sha256,
        },
        "minimum_new_information": {
            "dataset_mib": dataset_mib,
            "rule_profile": RULE_PROFILE,
        },
        "references": {
            "predecessor_classification": "PROVEN_HISTORICAL_DIFFERENTIAL_RECONSTRUCTION",
            "predecessor_preserved": True,
        },
        "reconstruction_rules": {
            "operation": "COPY_VERIFIED_BASE_THEN_APPLY_FIXED_RULE_PROFILE",
            "implementation": "apply_rule_profile",
            "target_bytes_embedded": False,
        },
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
    if minimum.get("rule_profile") != RULE_PROFILE:
        raise OriginCellHold("HOLD_RULE_PROFILE_UNSUPPORTED")

    d6 = field["D6"]
    if not isinstance(d6, dict) or d6.get("mode") != "RULE_PROFILE_REFERENCE":
        raise OriginCellHold("HOLD_D6_RULE_MODE_REQUIRED")
    if d6.get("transmitted_target_bytes") != 0 or not d6.get("generator_base_required"):
        raise OriginCellHold("HOLD_D6_TARGET_BYTES_OR_BASE_CONTRACT_INVALID")

    base = packet.get("target_base_state")
    verification = packet.get("verification_rules")
    if not isinstance(base, dict) or not isinstance(verification, dict):
        raise OriginCellHold("HOLD_BASE_OR_VERIFICATION_CONTRACT_MISSING")
    for commitment in (
        base.get("manifest_sha256"),
        base.get("generator_base_sha256"),
        verification.get("expected_target_manifest_sha256"),
    ):
        if not _is_sha256(commitment):
            raise OriginCellHold("HOLD_PACKET_COMMITMENT_INVALID")
    if base.get("generator_contract") != GENERATOR_CONTRACT:
        raise OriginCellHold("HOLD_GENERATOR_CONTRACT_MISMATCH")
    if generator_path is not None and sha256_file(generator_path) != base["generator_base_sha256"]:
        raise OriginCellHold("HOLD_GENERATOR_BASE_HASH_MISMATCH")


def reconstruct_from_rule_packet(packet: dict[str, Any], base_root: Path, output_root: Path) -> dict[str, Any]:
    validate_rule_packet(packet, Path(__file__).resolve())
    _, base_bytes, observed_base = file_manifest(base_root)
    expected_base = packet["target_base_state"]["manifest_sha256"]
    if observed_base != expected_base:
        raise OriginCellHold("HOLD_BASE_MANIFEST_MISMATCH")
    if output_root.exists():
        raise OriginCellHold("HOLD_OUTPUT_ROOT_ALREADY_EXISTS")

    shutil.copytree(base_root, output_root)
    apply_rule_profile(output_root, packet["minimum_new_information"]["rule_profile"])
    rows, target_bytes, observed_target = file_manifest(output_root)
    expected_target = packet["verification_rules"]["expected_target_manifest_sha256"]
    if observed_target != expected_target:
        raise OriginCellHold("HOLD_FINAL_MANIFEST_MISMATCH")

    receipt: dict[str, Any] = {
        "schema_version": RECEIPT_SCHEMA,
        "state": "PASS_CANDIDATE_EXACT_RULE_RECONSTRUCTION",
        "packet_sha256": packet["packet_sha256"],
        "packet_bytes": len(canonical_json_bytes(packet)),
        "dataset_mib": packet["minimum_new_information"]["dataset_mib"],
        "rule_profile": packet["minimum_new_information"]["rule_profile"],
        "base_manifest_sha256": observed_base,
        "base_bytes": base_bytes,
        "target_manifest_sha256": observed_target,
        "target_bytes": target_bytes,
        "target_files": len(rows),
        "transmitted_target_bytes": 0,
        "differential_payload_bytes": 0,
        "generator_base_sha256": packet["target_base_state"]["generator_base_sha256"],
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
    base_root = workspace / "base"
    expected_root = workspace / "expected_target"
    generate_base(base_root, dataset_mib)
    shutil.copytree(base_root, expected_root)
    apply_rule_profile(expected_root)
    _, base_bytes, base_manifest = file_manifest(base_root)
    rows, target_bytes, target_manifest = file_manifest(expected_root)
    generator_hash = sha256_file(Path(__file__).resolve())
    packet = build_rule_packet(
        dataset_mib=dataset_mib,
        base_manifest_sha256=base_manifest,
        target_manifest_sha256=target_manifest,
        generator_base_sha256=generator_hash,
    )
    packet_path = workspace / "origin_cell_rule_packet.json"
    packet_path.write_bytes(canonical_json_bytes(packet) + b"\n")
    return {
        "state": "PASS_CANDIDATE_RULE_WORKSPACE_PREPARED",
        "workspace": str(workspace),
        "base_root": str(base_root),
        "expected_target_root": str(expected_root),
        "packet_path": str(packet_path),
        "packet_bytes": packet_path.stat().st_size,
        "base_bytes": base_bytes,
        "target_bytes": target_bytes,
        "target_files": len(rows),
        "base_manifest_sha256": base_manifest,
        "target_manifest_sha256": target_manifest,
        "generator_base_sha256": generator_hash,
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
        receipt = reconstruct_from_rule_packet(packet, Path(prepared["base_root"]), root / "reconstructed")
        if receipt["target_manifest_sha256"] != prepared["target_manifest_sha256"]:
            raise OriginCellHold("HOLD_SELFTEST_TARGET_COMMITMENT_MISMATCH")
        return {
            "state": "PASS_CANDIDATE_RULE_GENERATIVE_SELFTEST",
            "dataset_mib": dataset_mib,
            "packet_bytes": prepared["packet_bytes"],
            "target_bytes": receipt["target_bytes"],
            "target_files": receipt["target_files"],
            "target_manifest_sha256": receipt["target_manifest_sha256"],
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
    reconstruct_parser.add_argument("--base", type=Path, required=True)
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
            result = reconstruct_from_rule_packet(packet, args.base, args.output)
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
