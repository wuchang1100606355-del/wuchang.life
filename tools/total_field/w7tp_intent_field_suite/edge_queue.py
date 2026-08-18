"""Offline L3 candidate queue bound to one sealed read-only snapshot.

The edge worker can guide and construct only L3 candidates. It cannot assign
D8, mutate Total Field, read credentials, use a cloud fallback, or write a
database. Queue persistence is an explicit local file operation using atomic
replacement; taiji01 revalidates the full hash chain before convergence.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping

from tools.total_field.w7tp_field_application_runtime import (
    CAPABILITY_REGISTRY_PATH,
    SCENARIO_ROUTE_TABLE_PATH,
    FieldApplicationError,
)

from .canonical_hash import canonical_sha256, normalize_content


ROOT = Path(__file__).resolve().parents[3]
LEGACY_CANONICAL_V2_PATH = (
    ROOT
    / "docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2.md"
)
LEGACY_CANONICAL_V2_SHA256 = "a5281f229ced0943072cce373125be16f0d361b9352a71094ad5450a6022d5d0"
CANONICAL_V2_PATH = LEGACY_CANONICAL_V2_PATH
CANONICAL_V2_SHA256 = LEGACY_CANONICAL_V2_SHA256
CANONICAL_V2_1_PATH = (
    ROOT
    / "docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1_FOUNDER_LOCKED_SUCCESSOR_20260728.md"
)
CANONICAL_V2_1_SHA256 = "383aba5b7a9f5d0e948d9b43b83e7dd6b6ec9c27f025fb9069e83810f0ae870d"
NODE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json_object(path: Path, reason_code: str) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise FieldApplicationError(reason_code) from exc
    if not isinstance(value, dict):
        raise FieldApplicationError(reason_code)
    return value


def build_sealed_snapshot(
    *,
    route_table_path: Path = SCENARIO_ROUTE_TABLE_PATH,
    capability_registry_path: Path = CAPABILITY_REGISTRY_PATH,
    canonical_v2_path: Path = CANONICAL_V2_1_PATH,
) -> dict[str, Any]:
    """Seal the exact read-only sources required for offline L3 generation."""

    route_table = _load_json_object(route_table_path, "SCENARIO_ROUTE_TABLE_INVALID")
    registry = _load_json_object(
        capability_registry_path, "CAPABILITY_REGISTRY_INVALID"
    )
    canonical_hash = _file_sha256(canonical_v2_path)
    if canonical_hash != CANONICAL_V2_1_SHA256:
        raise FieldApplicationError("CANONICAL_V2_1_SHA256_MISMATCH")
    routes = route_table.get("routes")
    if not isinstance(routes, dict):
        raise FieldApplicationError("SCENARIO_ROUTE_TABLE_INVALID")
    profile_packet_types = {
        profile: route.get("packet_type")
        for profile, route in sorted(routes.items())
        if isinstance(profile, str) and isinstance(route, dict)
    }
    snapshot: dict[str, Any] = {
        "schema_version": "W7TP-SEALED-EDGE-SNAPSHOT/1.1",
        "authority": "READ_ONLY_CANDIDATE_ONLY",
        "canonical_v2_1_sha256": canonical_hash,
        "canonical_parent_v2_sha256": LEGACY_CANONICAL_V2_SHA256,
        "scenario_route_table_sha256": canonical_sha256(route_table),
        "capability_registry_sha256": canonical_sha256(registry),
        "profile_packet_types": profile_packet_types,
        "generative_transmission": "PROTOCOL_NATIVE_8D_INTENT_FIELD_PACKET",
        "offline_output_level": "L3_CANDIDATE_ONLY",
        "cloud_fallback": "BLOCK",
        "founder_root_included": False,
        "mutable": False,
    }
    snapshot["content_sha256"] = canonical_sha256(snapshot)
    return snapshot


def validate_sealed_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a snapshot's self-seal and immutable authority boundary."""

    candidate = normalize_content(dict(snapshot))
    supplied = candidate.pop("content_sha256", None)
    schema_version = candidate.get("schema_version")
    checks = {
        "schema": schema_version
        in {"W7TP-SEALED-EDGE-SNAPSHOT/1.0", "W7TP-SEALED-EDGE-SNAPSHOT/1.1"},
        "self_hash": isinstance(supplied, str)
        and supplied == canonical_sha256(candidate),
        "authority": candidate.get("authority") == "READ_ONLY_CANDIDATE_ONLY",
        "offline_level": candidate.get("offline_output_level")
        == "L3_CANDIDATE_ONLY",
        "cloud_fallback": candidate.get("cloud_fallback") == "BLOCK",
        "founder_root_excluded": candidate.get("founder_root_included") is False,
        "immutable": candidate.get("mutable") is False,
    }
    if schema_version == "W7TP-SEALED-EDGE-SNAPSHOT/1.1":
        checks["canonical_v2_1"] = (
            candidate.get("canonical_v2_1_sha256") == CANONICAL_V2_1_SHA256
        )
        checks["canonical_parent_v2"] = (
            candidate.get("canonical_parent_v2_sha256")
            == LEGACY_CANONICAL_V2_SHA256
        )
        canonical_version = "2.1"
    else:
        checks["canonical_v2_legacy"] = (
            candidate.get("canonical_v2_sha256") == LEGACY_CANONICAL_V2_SHA256
        )
        canonical_version = "2.0"
    if not all(checks.values()):
        raise FieldApplicationError("EDGE_SNAPSHOT_INVALID")
    return {
        "state": "PASS",
        "checks": checks,
        "content_sha256": supplied,
        "canonical_version": canonical_version,
    }


def _validate_l3_packet(packet: Mapping[str, Any]) -> str:
    candidate = normalize_content(dict(packet))
    supplied = candidate.pop("content_sha256", None)
    candidate.pop("execution_metadata", None)
    if not isinstance(supplied, str) or supplied != canonical_sha256(candidate):
        raise FieldApplicationError("EDGE_PACKET_CONTENT_SHA256_MISMATCH")
    dimensions = {f"D{index}" for index in range(1, 9)}
    if not dimensions.issubset(candidate):
        raise FieldApplicationError("EDGE_PACKET_DIMENSIONS_INCOMPLETE")
    d5 = candidate.get("D5")
    d6 = candidate.get("D6")
    d8 = candidate.get("D8")
    if (
        not isinstance(d5, Mapping)
        or d5.get("candidate_only") is not True
        or not isinstance(d6, Mapping)
        or not isinstance(d6.get("reconstruction_conditions"), Mapping)
        or d6["reconstruction_conditions"].get("equivalence_level")
        != "L3_CANDIDATE"
        or not isinstance(d8, Mapping)
        or d8.get("candidate_only") is not True
        or d8.get("decision") != "PENDING_TOTAL_FIELD_REVIEW"
    ):
        raise FieldApplicationError("EDGE_FORMAL_AUTHORITY_BLOCKED")
    return supplied


def build_queue_entry(
    packet: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    *,
    node_id: str,
    previous_entry_sha256: str | None = None,
) -> dict[str, Any]:
    """Build one deterministic, hash-chained offline queue entry."""

    if not isinstance(node_id, str) or NODE_ID.fullmatch(node_id) is None:
        raise FieldApplicationError("EDGE_NODE_ID_INVALID")
    snapshot_validation = validate_sealed_snapshot(snapshot)
    packet_hash = _validate_l3_packet(packet)
    packet_snapshot = packet.get("D4", {}).get("source_snapshot")
    expected_packet_snapshot = {
        "scenario_route_table_sha256": snapshot.get(
            "scenario_route_table_sha256"
        ),
        "capability_registry_sha256": snapshot.get(
            "capability_registry_sha256"
        ),
    }
    if packet_snapshot != expected_packet_snapshot:
        raise FieldApplicationError("EDGE_PACKET_SNAPSHOT_MISMATCH")
    if previous_entry_sha256 is not None and (
        not isinstance(previous_entry_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", previous_entry_sha256) is None
    ):
        raise FieldApplicationError("EDGE_PREVIOUS_ENTRY_SHA256_INVALID")
    entry: dict[str, Any] = {
        "schema_version": "W7TP-OFFLINE-L3-QUEUE-ENTRY/1.0",
        "state": "QUEUED_L3_CANDIDATE_PENDING_TOTAL_FIELD",
        "node_id": node_id,
        "snapshot_content_sha256": snapshot_validation["content_sha256"],
        "candidate_content_sha256": packet_hash,
        "previous_entry_sha256": previous_entry_sha256,
        "candidate_packet": normalize_content(dict(packet)),
        "authority": {
            "edge_d8": "BLOCK",
            "formal_pass": "BLOCK",
            "total_field_revalidation_required": True,
        },
        "side_effects": {
            "db_write": False,
            "cloud_call": False,
            "formal_transaction": False,
            "secret_read": False,
        },
    }
    entry["entry_sha256"] = canonical_sha256(entry)
    return entry


def _load_queue(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FieldApplicationError("EDGE_QUEUE_READ_FAILED") from exc
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise FieldApplicationError("EDGE_QUEUE_INVALID")
    return list(value)


def _atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_path = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(raw_path)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def enqueue_packet(
    queue_path: Path,
    packet: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    *,
    node_id: str,
) -> dict[str, Any]:
    """Atomically append one non-duplicate L3 packet to a local edge queue."""

    queue = _load_queue(queue_path)
    previous_hash = queue[-1].get("entry_sha256") if queue else None
    entry = build_queue_entry(
        packet,
        snapshot,
        node_id=node_id,
        previous_entry_sha256=previous_hash,
    )
    if any(
        item.get("candidate_content_sha256") == entry["candidate_content_sha256"]
        for item in queue
    ):
        return {
            "state": "ALREADY_QUEUED",
            "candidate_content_sha256": entry["candidate_content_sha256"],
            "queue_depth": len(queue),
        }
    queue.append(entry)
    _atomic_write_json(queue_path, queue)
    return {
        "state": "QUEUED_L3_CANDIDATE_PENDING_TOTAL_FIELD",
        "entry_sha256": entry["entry_sha256"],
        "candidate_content_sha256": entry["candidate_content_sha256"],
        "queue_depth": len(queue),
    }


def revalidate_queue(
    entries: Iterable[Mapping[str, Any]],
    current_snapshot: Mapping[str, Any],
    *,
    seen_candidate_hashes: Iterable[str] = (),
) -> dict[str, Any]:
    """Revalidate and deduplicate an edge chain after taiji01 returns."""

    snapshot_validation = validate_sealed_snapshot(current_snapshot)
    seen = set(seen_candidate_hashes)
    previous: str | None = None
    results: list[dict[str, Any]] = []
    for index, raw_entry in enumerate(entries):
        entry = normalize_content(dict(raw_entry))
        supplied_entry_hash = entry.pop("entry_sha256", None)
        if supplied_entry_hash != canonical_sha256(entry):
            raise FieldApplicationError("EDGE_QUEUE_ENTRY_SHA256_MISMATCH", f"$[{index}]")
        if entry.get("previous_entry_sha256") != previous:
            raise FieldApplicationError("EDGE_QUEUE_CHAIN_MISMATCH", f"$[{index}]")
        if entry.get("snapshot_content_sha256") != snapshot_validation["content_sha256"]:
            raise FieldApplicationError("EDGE_QUEUE_SNAPSHOT_STALE", f"$[{index}]")
        packet = entry.get("candidate_packet")
        if not isinstance(packet, Mapping):
            raise FieldApplicationError("EDGE_QUEUE_PACKET_INVALID", f"$[{index}]")
        candidate_hash = _validate_l3_packet(packet)
        if candidate_hash != entry.get("candidate_content_sha256"):
            raise FieldApplicationError("EDGE_QUEUE_PACKET_REF_MISMATCH", f"$[{index}]")
        duplicate = candidate_hash in seen
        seen.add(candidate_hash)
        results.append(
            {
                "entry_sha256": supplied_entry_hash,
                "candidate_content_sha256": candidate_hash,
                "state": (
                    "DEDUPLICATED"
                    if duplicate
                    else "TOTAL_FIELD_REVALIDATED_L3_CANDIDATE"
                ),
                "formal_d8_assigned": False,
            }
        )
        previous = supplied_entry_hash
    report: dict[str, Any] = {
        "schema_version": "W7TP-EDGE-QUEUE-REVALIDATION/1.0",
        "state": "PASS",
        "snapshot_content_sha256": snapshot_validation["content_sha256"],
        "results": results,
        "accepted_count": sum(
            item["state"] == "TOTAL_FIELD_REVALIDATED_L3_CANDIDATE"
            for item in results
        ),
        "deduplicated_count": sum(
            item["state"] == "DEDUPLICATED" for item in results
        ),
        "formal_d8_assigned": False,
        "archive_requires_explicit_operator_action": True,
    }
    report["content_sha256"] = canonical_sha256(report)
    return report


def revalidate_queue_file(
    queue_path: Path,
    current_snapshot: Mapping[str, Any],
    *,
    seen_candidate_hashes: Iterable[str] = (),
) -> dict[str, Any]:
    """Read and revalidate a queue without deleting or mutating it."""

    return revalidate_queue(
        _load_queue(queue_path),
        current_snapshot,
        seen_candidate_hashes=seen_candidate_hashes,
    )
