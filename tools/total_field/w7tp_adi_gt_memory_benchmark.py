#!/usr/bin/env python3
"""Synthetic, side-effect-free benchmark for ADI-assisted memory updates.

The reference baseline re-emits a complete bounded context after every update.
The candidate sends a protocol-native D1-D8 reference packet, reconstructs one
deterministic record locally, and materializes only the ADI-selected working
set.  The benchmark does not read member data, write a database, call a model,
or grant execution/Canonical authority.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import statistics
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.intent_field.adi_5d_absolute_index_verifier import (
    base_pass_packet,
    hash_ref,
    verify_packet,
)


SCHEMA_VERSION = "W7TP-ADI-GT-DYNAMIC-MEMORY-BENCHMARK/1.0"
PACKET_TYPE = "W7TP_ADI_GT_DYNAMIC_MEMORY_UPDATE"
GENERATION_RULE_REF = "generation_rule_ref:synthetic_memory_record:v1"
RECONSTRUCTION_PROFILE_REF = "reconstruction_profile_ref:l2_memory_update:v1"
VERIFICATION_PROFILE_REF = "verification_profile_ref:sha256_result_equivalence:v1"
DEFAULT_RECORDS = 512
DEFAULT_UPDATES = 160
DEFAULT_BODY_BYTES = 2048


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def percentile_ns(values: list[int], percentile: int) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = ((len(ordered) - 1) * percentile + 99) // 100
    return ordered[min(index, len(ordered) - 1)]


def reduction_basis_points(baseline: int, candidate: int) -> int:
    if baseline <= 0:
        return 0
    return 10_000 - ((candidate * 10_000) // baseline)


def coordinates_for(index: int) -> tuple[int, int, int, int, int]:
    return (index % 64, index % 17, index % 11, index % 7, index % 5)


def materialize_body(record_ref: str, revision: int, body_bytes: int) -> str:
    seed = hashlib.sha256(
        f"{GENERATION_RULE_REF}|{record_ref}|{revision}".encode("utf-8")
    ).hexdigest()
    repeated = (seed * ((body_bytes // len(seed)) + 1))[:body_bytes]
    return repeated


def make_record(index: int, revision: int, body_bytes: int) -> dict[str, Any]:
    record_ref = f"memory_ref:synthetic:{index:05d}"
    body = materialize_body(record_ref, revision, body_bytes)
    coordinates = coordinates_for(index)
    return {
        "record_ref": record_ref,
        "coordinates": list(coordinates),
        "revision": revision,
        "body": body,
        "body_sha256": sha256_hex(body.encode("utf-8")),
    }


def initial_records(record_count: int, body_bytes: int) -> dict[str, dict[str, Any]]:
    records = [make_record(index, 0, body_bytes) for index in range(record_count)]
    return {record["record_ref"]: record for record in records}


def update_sequence(record_count: int, update_count: int) -> list[str]:
    return [f"memory_ref:synthetic:{((step * 97) + 13) % record_count:05d}" for step in range(update_count)]


def update_record(store: dict[str, dict[str, Any]], record_ref: str, body_bytes: int) -> dict[str, Any]:
    old = store[record_ref]
    replacement = make_record(int(record_ref.rsplit(":", 1)[1]), old["revision"] + 1, body_bytes)
    store[record_ref] = replacement
    return replacement


def query_result(store: dict[str, dict[str, Any]], coordinates: tuple[int, ...]) -> list[dict[str, Any]]:
    selected = [
        {
            "record_ref": record["record_ref"],
            "revision": record["revision"],
            "body_sha256": record["body_sha256"],
        }
        for record in store.values()
        if tuple(record["coordinates"]) == coordinates
    ]
    return sorted(selected, key=lambda item: item["record_ref"])


def result_hash(result: list[dict[str, Any]]) -> str:
    return sha256_hex(canonical_bytes(result))


def build_adi_index(store: dict[str, dict[str, Any]]) -> dict[tuple[int, ...], tuple[str, ...]]:
    mutable: dict[tuple[int, ...], list[str]] = {}
    for record in store.values():
        mutable.setdefault(tuple(record["coordinates"]), []).append(record["record_ref"])
    return {coordinate: tuple(sorted(refs)) for coordinate, refs in mutable.items()}


def make_candidate_packet(step: int, record: dict[str, Any]) -> dict[str, Any]:
    coordinate_ref = "adi_coordinate_ref:" + sha256_hex(canonical_bytes(record["coordinates"]))
    return {
        "packet_type": PACKET_TYPE,
        "schema_version": SCHEMA_VERSION,
        "mode": "L2_EQUIVALENT_RECONSTRUCTION",
        "D1": {"intent_ref": "intent_ref:update_memory_working_set"},
        "D2": {"state_ref": record["record_ref"], "revision": record["revision"]},
        "D3": {"adi_5d_coordinate_ref": coordinate_ref},
        "D4": {"expected_body_sha256": record["body_sha256"]},
        "D5": {"execution": "LOCAL_RECONSTRUCT_AND_VERIFY_ONLY"},
        "D6": {
            "generation_rule_ref": GENERATION_RULE_REF,
            "reconstruction_profile_ref": RECONSTRUCTION_PROFILE_REF,
            "materialization_scope": "ONE_UPDATED_RECORD_AND_ONE_QUERY_RESULT",
        },
        "D7": {
            "risk_state": "SYNTHETIC_NO_MEMBER_DATA",
            "raw_payload_included": False,
        },
        "D8": {
            "packet_ref": f"packet_ref:adi_gt_memory_benchmark:{step:06d}",
            "nonce_ref": f"nonce_ref:synthetic:{step:06d}",
            "ttl_seconds": 300,
            "verifier_ref": VERIFICATION_PROFILE_REF,
            "authority": "CANDIDATE_ONLY",
        },
    }


def run_baseline(
    record_count: int,
    update_refs: list[str],
    body_bytes: int,
) -> dict[str, Any]:
    tracemalloc.start()
    store = initial_records(record_count, body_bytes)
    transport_bytes = 0
    working_set_bytes = 0
    latencies: list[int] = []
    result_hashes: list[str] = []
    for record_ref in update_refs:
        started = time.perf_counter_ns()
        updated = update_record(store, record_ref, body_bytes)
        payload = canonical_bytes({"mode": "FULL_CONTEXT_REEMIT_EACH_UPDATE", "records": list(store.values())})
        transport_bytes += len(payload)
        receiver_store = {
            record["record_ref"]: record
            for record in json.loads(payload.decode("utf-8"))["records"]
        }
        coordinates = tuple(updated["coordinates"])
        result_hashes.append(result_hash(query_result(receiver_store, coordinates)))
        working_set_bytes += sum(len(canonical_bytes(record)) for record in receiver_store.values())
        latencies.append(time.perf_counter_ns() - started)
    _current, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "mode": "REFERENCE_FULL_CONTEXT_BASELINE",
        "transport_bytes": transport_bytes,
        "working_set_bytes": working_set_bytes,
        "latency_p50_ns": int(statistics.median(latencies)),
        "latency_p95_ns": percentile_ns(latencies, 95),
        "peak_allocated_bytes": peak_bytes,
        "result_hashes": result_hashes,
    }


def run_candidate(
    record_count: int,
    update_refs: list[str],
    body_bytes: int,
) -> dict[str, Any]:
    tracemalloc.start()
    source_store = initial_records(record_count, body_bytes)
    receiver_store = copy.deepcopy(source_store)
    adi_index = build_adi_index(receiver_store)
    transport_bytes = 0
    working_set_bytes = 0
    latencies: list[int] = []
    result_hashes: list[str] = []
    packet_shape_pass = True
    for step, record_ref in enumerate(update_refs):
        started = time.perf_counter_ns()
        source_record = update_record(source_store, record_ref, body_bytes)
        packet = make_candidate_packet(step, source_record)
        packet_shape_pass = packet_shape_pass and all(f"D{field}" in packet for field in range(1, 9))
        packet_text = json.dumps(packet, sort_keys=True, separators=(",", ":"))
        packet_shape_pass = packet_shape_pass and '"body":' not in packet_text
        transport_bytes += len(canonical_bytes(packet))

        old = receiver_store[record_ref]
        reconstructed_body = materialize_body(record_ref, int(packet["D2"]["revision"]), body_bytes)
        reconstructed_hash = sha256_hex(reconstructed_body.encode("utf-8"))
        if reconstructed_hash != packet["D4"]["expected_body_sha256"]:
            raise ValueError("HOLD_RECONSTRUCTED_BODY_HASH_MISMATCH")
        receiver_store[record_ref] = {
            **old,
            "revision": packet["D2"]["revision"],
            "body": reconstructed_body,
            "body_sha256": reconstructed_hash,
        }
        coordinates = tuple(receiver_store[record_ref]["coordinates"])
        selected_refs = adi_index.get(coordinates, ())
        selected_records = [receiver_store[selected_ref] for selected_ref in selected_refs]
        result = [
            {
                "record_ref": record["record_ref"],
                "revision": record["revision"],
                "body_sha256": record["body_sha256"],
            }
            for record in selected_records
        ]
        result_hashes.append(result_hash(sorted(result, key=lambda item: item["record_ref"])))
        working_set_bytes += sum(len(canonical_bytes(record)) for record in selected_records)
        latencies.append(time.perf_counter_ns() - started)
    _current, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "mode": "ADI_GT_DYNAMIC_CONTEXT_CANDIDATE",
        "transport_bytes": transport_bytes,
        "working_set_bytes": working_set_bytes,
        "latency_p50_ns": int(statistics.median(latencies)),
        "latency_p95_ns": percentile_ns(latencies, 95),
        "peak_allocated_bytes": peak_bytes,
        "packet_shape_pass": packet_shape_pass,
        "result_hashes": result_hashes,
    }


def decide_winner(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    reductions = {
        "transport_reduction_bp": reduction_basis_points(
            baseline["transport_bytes"], candidate["transport_bytes"]
        ),
        "working_set_reduction_bp": reduction_basis_points(
            baseline["working_set_bytes"], candidate["working_set_bytes"]
        ),
        "latency_p95_reduction_bp": reduction_basis_points(
            baseline["latency_p95_ns"], candidate["latency_p95_ns"]
        ),
        "peak_allocated_reduction_bp": reduction_basis_points(
            baseline["peak_allocated_bytes"], candidate["peak_allocated_bytes"]
        ),
    }
    gates = {
        "equivalent_result_hashes": baseline["result_hashes"] == candidate["result_hashes"],
        "complete_d1_d8_packet_no_body": candidate["packet_shape_pass"],
        "transport_reduction_at_least_9000bp": reductions["transport_reduction_bp"] >= 9_000,
        "working_set_reduction_at_least_9000bp": reductions["working_set_reduction_bp"] >= 9_000,
        "latency_p95_reduction_at_least_5000bp": reductions["latency_p95_reduction_bp"] >= 5_000,
        "peak_allocated_reduction_at_least_1000bp": reductions["peak_allocated_reduction_bp"] >= 1_000,
    }
    return {
        "reductions_basis_points": reductions,
        "gates": gates,
        "candidate_verdict": (
            "PASS_CANDIDATE_WINS_REFERENCE_BASELINE"
            if all(gates.values())
            else "HOLD_CANDIDATE_NOT_PROVEN_TO_WIN"
        ),
    }


def run_benchmark(record_count: int, update_count: int, body_bytes: int) -> dict[str, Any]:
    if record_count < 8 or update_count < 4 or body_bytes < 64:
        raise ValueError("record_count>=8 update_count>=4 body_bytes>=64 required")
    updates = update_sequence(record_count, update_count)
    baseline = run_baseline(record_count, updates, body_bytes)
    candidate = run_candidate(record_count, updates, body_bytes)
    winner = decide_winner(baseline, candidate)
    adi_verifier = verify_packet(base_pass_packet())
    initial_seed_bytes = len(canonical_bytes({"records": list(initial_records(record_count, body_bytes).values())}))
    recurring_savings = baseline["transport_bytes"] - candidate["transport_bytes"]
    cold_break_even_updates = 0
    if recurring_savings > 0:
        savings_per_update = recurring_savings // update_count
        cold_break_even_updates = (initial_seed_bytes + savings_per_update - 1) // savings_per_update
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": "W7TP_ADI_GT_DYNAMIC_MEMORY_BENCHMARK_V1",
        "state": "CANDIDATE_EVIDENCE_ONLY",
        "scope": "SYNTHETIC_DETERMINISTIC_REGENERABLE_MEMORY_RECORDS",
        "not_proven": [
            "ARBITRARY_HIGH_ENTROPY_CONTENT",
            "LIVE_D8_DATABASE_THROUGHPUT",
            "PRODUCTION_MULTI_NODE_CONCURRENCY",
        ],
        "configuration": {
            "record_count": record_count,
            "update_count": update_count,
            "body_bytes_per_record": body_bytes,
            "receiver_initial_snapshot_required": True,
            "candidate_reconstruction_level": "L2_EQUIVALENT_RECONSTRUCTION",
        },
        "economics": {
            "initial_seed_bytes": initial_seed_bytes,
            "warm_receiver_break_even_updates": 1,
            "cold_receiver_break_even_updates": cold_break_even_updates,
        },
        "baseline": {key: value for key, value in baseline.items() if key != "result_hashes"},
        "candidate": {key: value for key, value in candidate.items() if key != "result_hashes"},
        "comparison": winner,
        "adi_5d_existing_verifier": {
            "dry_run": adi_verifier["DRY_RUN"],
            "checks": adi_verifier["CHECKS"],
        },
        "authority": {
            "total_field_review_required": True,
            "canonical_write": False,
            "db_write": False,
            "deploy": False,
            "restart": False,
            "production_switch": False,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, default=DEFAULT_RECORDS)
    parser.add_argument("--updates", type=int, default=DEFAULT_UPDATES)
    parser.add_argument("--body-bytes", type=int, default=DEFAULT_BODY_BYTES)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_benchmark(args.records, args.updates, args.body_bytes)
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["comparison"]["candidate_verdict"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
