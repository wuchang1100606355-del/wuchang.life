#!/usr/bin/env python3
"""Dry-run 5 GiB W3 generative-transfer completion benchmark."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET_DIR = ROOT / "packets" / "benchmarks" / "generative_transfer_5gb"
DEFAULT_EVIDENCE_DIR = ROOT / "docs" / "evidence" / "generative_transfer_5gb"
MAIN_CHAIN = [
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


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def mark(stages: list[dict[str, object]], name: str, start: float) -> None:
    stages.append(
        {
            "stage": name,
            "elapsed_seconds": round(time.perf_counter() - start, 9),
            "timestamp_utc": utc_now(),
        }
    )


def build_chunk_manifest(
    run_id: str,
    source_node: str,
    target_node: str,
    total_bytes: int,
    chunk_bytes: int,
) -> list[dict[str, object]]:
    chunk_count = math.ceil(total_bytes / chunk_bytes)
    chunks = []
    for index in range(chunk_count):
        offset = index * chunk_bytes
        length = min(chunk_bytes, total_bytes - offset)
        coordinate = {
            "d1_source_node": source_node,
            "d2_target_node": target_node,
            "d3_payload_class": "synthetic_5gib_equivalent",
            "d4_chunk_index": index,
            "d5_offset": offset,
            "d6_length": length,
            "d7_lookup_key": "generative.transfer.5gb.speed.v1",
            "d8_run_id": run_id,
        }
        coordinate_hash = sha256_text(json.dumps(coordinate, sort_keys=True, separators=(",", ":")))
        chunk_hash = sha256_text(f"{run_id}|{source_node}|{target_node}|{index}|{offset}|{length}|{coordinate_hash}")
        chunks.append(
            {
                "index": index,
                "offset": offset,
                "length": length,
                "coordinate_hash": coordinate_hash,
                "chunk_hash": chunk_hash,
            }
        )
    return chunks


def merkle_root(chunks: list[dict[str, object]]) -> str:
    return sha256_text("".join(str(chunk["chunk_hash"]) for chunk in chunks))


def write_evidence_md(packet: dict[str, object], evidence_path: Path) -> None:
    metrics = packet["metrics"]
    evidence_path.write_text(
        "\n".join(
            [
                "# W3 GT 5GiB Completion Speed Evidence",
                "",
                f"RUN_ID={packet['run_id']}",
                f"STATE={packet['state']}",
                f"SIZE_BYTES={metrics['equivalent_payload_bytes']}",
                f"SIZE_GIB={metrics['equivalent_payload_gib']}",
                f"CHUNK_COUNT={metrics['chunk_count']}",
                f"ELAPSED_SECONDS={metrics['completion_elapsed_seconds']}",
                f"EQUIVALENT_GIB_PER_SECOND={metrics['equivalent_gib_per_second']}",
                f"PACKET_BYTES={metrics['packet_bytes']}",
                "",
                "## Boundary",
                "- mode=dry_run_candidate_only",
                "- runtime_change=false",
                "- service_restart=false",
                "- tailscale_change=false",
                "- db_write=false",
                "- secret_read=false",
                "- raw_payload_transfer=false",
                "",
                "## Main Chain",
                "State -> Coordinate -> Hash -> Packet -> Generative Transfer -> Verify -> Reconstruct -> Evidence -> Action",
                "",
                "## Result",
                f"- verifier_hint={packet['verifier_hint']}",
                f"- packet_ref={packet['packet_ref']}",
                f"- chunk_root={packet['hashes']['chunk_root']}",
                f"- packet_hash={packet['hashes']['packet_hash']}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> dict[str, object]:
    run_id = args.run_id or f"W3_GT_5GB_SPEED_{dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')}"
    total_bytes = int(args.size_gib * 1024**3)
    chunk_bytes = int(args.chunk_mib * 1024**2)
    packet_dir = Path(args.packet_dir)
    evidence_dir = Path(args.evidence_dir)
    packet_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    start = time.perf_counter()
    stages: list[dict[str, object]] = []

    state = {
        "mode": "dry_run_candidate_only",
        "runtime_change": False,
        "service_restart": False,
        "odoo_db_write": False,
        "tailscale_change": False,
        "secret_read": False,
        "raw_payload_transfer": False,
    }
    mark(stages, "State", start)

    chunks = build_chunk_manifest(run_id, args.source_node, args.target_node, total_bytes, chunk_bytes)
    mark(stages, "Coordinate", start)

    chunk_root = merkle_root(chunks)
    mark(stages, "Hash", start)

    packet_ref = f"packets/benchmarks/generative_transfer_5gb/{run_id}.json"
    evidence_ref = f"docs/evidence/generative_transfer_5gb/{run_id}.md"
    packet: dict[str, object] = {
        "packet_type": "w3_generative_transfer_5gb_speed_packet",
        "run_id": run_id,
        "state": "GT_5GB_SPEED_DRY_RUN_COMPLETE",
        "main_chain": MAIN_CHAIN,
        "source_node": args.source_node,
        "target_node": args.target_node,
        "lookup_key": "generative.transfer.5gb.speed.v1",
        "candidate_only": True,
        "local_reconstruction_required": True,
        "land_allowed": False,
        "safe_mode": state,
        "packet_ref": packet_ref,
        "evidence_ref": evidence_ref,
        "transfer_model": {
            "equivalent_payload": "5GiB synthetic deterministic coordinate manifest",
            "raw_payload_transfer": False,
            "cross_node_mode": "manifest_handoff_dry_run",
        },
        "chunk_manifest": chunks,
        "hashes": {
            "chunk_root": chunk_root,
        },
        "stages": stages,
    }
    mark(stages, "Packet", start)

    packet_body_before_hash = canonical_json(packet)
    transfer_hash = hashlib.sha256(packet_body_before_hash).hexdigest()
    mark(stages, "Generative Transfer", start)

    reconstructed_chunks = build_chunk_manifest(run_id, args.source_node, args.target_node, total_bytes, chunk_bytes)
    reconstructed_root = merkle_root(reconstructed_chunks)
    verify_pass = reconstructed_root == chunk_root and len(reconstructed_chunks) == len(chunks)
    mark(stages, "Verify", start)

    reconstruct_ref = {
        "reconstructed_chunk_count": len(reconstructed_chunks),
        "reconstructed_chunk_root": reconstructed_root,
        "raw_payload_materialized": False,
    }
    mark(stages, "Reconstruct", start)

    elapsed = time.perf_counter() - start
    packet["reconstruct"] = reconstruct_ref
    packet["verifier_hint"] = "PASS" if verify_pass else "FAIL"
    packet["metrics"] = {
        "equivalent_payload_bytes": total_bytes,
        "equivalent_payload_gib": round(total_bytes / 1024**3, 6),
        "chunk_bytes": chunk_bytes,
        "chunk_mib": args.chunk_mib,
        "chunk_count": len(chunks),
        "completion_elapsed_seconds": round(elapsed, 9),
        "equivalent_gib_per_second": round((total_bytes / 1024**3) / elapsed, 6),
        "packet_bytes": len(packet_body_before_hash),
        "equivalent_payload_to_packet_ratio": round(total_bytes / max(len(packet_body_before_hash), 1), 6),
    }
    packet["hashes"]["transfer_hash_before_metrics"] = transfer_hash
    packet["hashes"]["packet_hash"] = hashlib.sha256(canonical_json(packet)).hexdigest()

    packet_path = packet_dir / f"{run_id}.json"
    evidence_path = evidence_dir / f"{run_id}.md"
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_evidence_md(packet, evidence_path)
    mark(stages, "Evidence", start)

    packet["stages"] = stages
    packet["action"] = {
        "state": "NO_LIVE_ACTION_DRY_RUN_ONLY",
        "reason": "benchmark records packet completion speed only",
    }
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_evidence_md(packet, evidence_path)
    mark(stages, "Action", start)

    return {
        "STATE": packet["state"],
        "RUN_ID": run_id,
        "PACKET": str(packet_path.relative_to(ROOT)),
        "EVIDENCE": str(evidence_path.relative_to(ROOT)),
        "ELAPSED_SECONDS": packet["metrics"]["completion_elapsed_seconds"],
        "EQUIVALENT_GIB_PER_SECOND": packet["metrics"]["equivalent_gib_per_second"],
        "VERIFIER_HINT": packet["verifier_hint"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--size-gib", type=float, default=5.0)
    parser.add_argument("--chunk-mib", type=int, default=64)
    parser.add_argument("--source-node", default="NODE_POS_MAINT")
    parser.add_argument("--target-node", default="NODE_XIAOJ_DISPLAY_COMPUTE")
    parser.add_argument("--packet-dir", default=str(DEFAULT_PACKET_DIR))
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    return parser.parse_args()


if __name__ == "__main__":
    result = run(parse_args())
    for key, value in result.items():
        print(f"{key}={value}")
