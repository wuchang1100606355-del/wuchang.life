#!/usr/bin/env python3
"""Verify a W3 5 GiB generative-transfer speed packet."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKET_DIR = ROOT / "packets" / "benchmarks" / "generative_transfer_5gb"
EXPECTED_CHAIN = [
    "State",
    "Coordinate",
    "Hash",
    "Packet",
    "Generative Transfer",
    "Verify",
    "Reconstruct",
    "Evidence",
    "Action",
]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def fail(reason: str) -> None:
    print("STATE=HOLD_VERIFY")
    print(f"reason={reason}")
    raise SystemExit(1)


def packet_path(arg_path: str | None) -> Path:
    if arg_path:
        path = Path(arg_path)
        return path if path.is_absolute() else ROOT / path
    candidates = sorted(PACKET_DIR.glob("W3_GT_5GB_SPEED_*.json"))
    if not candidates:
        fail("no 5GiB GT speed packet found")
    return candidates[-1]


def verify(path: Path) -> dict[str, object]:
    packet = json.loads(path.read_text(encoding="utf-8"))
    if packet.get("packet_type") != "w3_generative_transfer_5gb_speed_packet":
        fail("bad packet_type")
    if packet.get("state") != "GT_5GB_SPEED_DRY_RUN_COMPLETE":
        fail("bad state")
    if packet.get("main_chain") != EXPECTED_CHAIN:
        fail("main chain mismatch")
    if packet.get("candidate_only") is not True:
        fail("candidate_only must be true")
    if packet.get("local_reconstruction_required") is not True:
        fail("local reconstruction must be required")
    if packet.get("land_allowed") is not False:
        fail("land_allowed must be false")

    safe_mode = packet.get("safe_mode", {})
    for key in [
        "runtime_change",
        "service_restart",
        "odoo_db_write",
        "tailscale_change",
        "secret_read",
        "raw_payload_transfer",
    ]:
        if safe_mode.get(key) is not False:
            fail(f"safe_mode drift: {key}")

    metrics = packet.get("metrics", {})
    total_bytes = metrics.get("equivalent_payload_bytes")
    chunk_bytes = metrics.get("chunk_bytes")
    chunks = packet.get("chunk_manifest", [])
    if total_bytes != 5 * 1024**3:
        fail("equivalent payload is not 5GiB")
    if not isinstance(chunk_bytes, int) or chunk_bytes <= 0:
        fail("bad chunk_bytes")
    expected_count = (total_bytes + chunk_bytes - 1) // chunk_bytes
    if len(chunks) != expected_count:
        fail("chunk count mismatch")

    run_id = packet.get("run_id")
    source_node = packet.get("source_node")
    target_node = packet.get("target_node")
    recomputed_hashes = []
    for index, chunk in enumerate(chunks):
        expected_offset = index * chunk_bytes
        expected_length = min(chunk_bytes, total_bytes - expected_offset)
        if chunk.get("index") != index:
            fail(f"chunk index mismatch at {index}")
        if chunk.get("offset") != expected_offset:
            fail(f"chunk offset mismatch at {index}")
        if chunk.get("length") != expected_length:
            fail(f"chunk length mismatch at {index}")
        coordinate = {
            "d1_source_node": source_node,
            "d2_target_node": target_node,
            "d3_payload_class": "synthetic_5gib_equivalent",
            "d4_chunk_index": index,
            "d5_offset": expected_offset,
            "d6_length": expected_length,
            "d7_lookup_key": "generative.transfer.5gb.speed.v1",
            "d8_run_id": run_id,
        }
        coordinate_hash = sha256_text(json.dumps(coordinate, sort_keys=True, separators=(",", ":")))
        if chunk.get("coordinate_hash") != coordinate_hash:
            fail(f"coordinate hash mismatch at {index}")
        chunk_hash = sha256_text(
            f"{run_id}|{source_node}|{target_node}|{index}|{expected_offset}|{expected_length}|{coordinate_hash}"
        )
        if chunk.get("chunk_hash") != chunk_hash:
            fail(f"chunk hash mismatch at {index}")
        recomputed_hashes.append(chunk_hash)

    chunk_root = sha256_text("".join(recomputed_hashes))
    if packet.get("hashes", {}).get("chunk_root") != chunk_root:
        fail("chunk root mismatch")
    if packet.get("reconstruct", {}).get("reconstructed_chunk_root") != chunk_root:
        fail("reconstruct root mismatch")
    if packet.get("verifier_hint") != "PASS":
        fail("verifier hint is not PASS")

    return {
        "STATE": "PASS_VERIFY",
        "RUN_ID": run_id,
        "PACKET": str(path.relative_to(ROOT)),
        "ELAPSED_SECONDS": metrics.get("completion_elapsed_seconds"),
        "EQUIVALENT_GIB_PER_SECOND": metrics.get("equivalent_gib_per_second"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", nargs="?")
    return parser.parse_args()


if __name__ == "__main__":
    result = verify(packet_path(parse_args().packet))
    for key, value in result.items():
        print(f"{key}={value}")
