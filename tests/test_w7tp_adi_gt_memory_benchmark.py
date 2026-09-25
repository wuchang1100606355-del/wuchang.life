from __future__ import annotations

import unittest

from tools.total_field.w7tp_adi_gt_memory_benchmark import (
    decide_winner,
    initial_records,
    make_candidate_packet,
    run_benchmark,
)


class W7TPADIGTDynamicMemoryBenchmarkTest(unittest.TestCase):
    def test_candidate_packet_has_complete_d1_d8_and_no_body(self) -> None:
        record = next(iter(initial_records(8, 64).values()))
        packet = make_candidate_packet(1, record)
        self.assertTrue(all(f"D{field}" in packet for field in range(1, 9)))
        self.assertNotIn("body", packet)
        self.assertFalse(packet["D7"]["raw_payload_included"])

    def test_small_benchmark_reconstructs_equivalent_results(self) -> None:
        result = run_benchmark(record_count=32, update_count=12, body_bytes=256)
        self.assertEqual(result["adi_5d_existing_verifier"]["dry_run"], "PASS")
        self.assertTrue(result["comparison"]["gates"]["equivalent_result_hashes"])
        self.assertTrue(result["comparison"]["gates"]["complete_d1_d8_packet_no_body"])
        self.assertGreaterEqual(
            result["comparison"]["reductions_basis_points"]["transport_reduction_bp"],
            8_000,
        )
        self.assertGreaterEqual(
            result["comparison"]["reductions_basis_points"]["working_set_reduction_bp"],
            8_000,
        )

    def test_winner_gate_holds_when_results_are_not_equivalent(self) -> None:
        baseline = {
            "transport_bytes": 100,
            "working_set_bytes": 100,
            "latency_p95_ns": 100,
            "peak_allocated_bytes": 100,
            "result_hashes": ["a"],
        }
        candidate = {
            "transport_bytes": 1,
            "working_set_bytes": 1,
            "latency_p95_ns": 1,
            "peak_allocated_bytes": 1,
            "packet_shape_pass": True,
            "result_hashes": ["b"],
        }
        result = decide_winner(baseline, candidate)
        self.assertEqual(result["candidate_verdict"], "HOLD_CANDIDATE_NOT_PROVEN_TO_WIN")


if __name__ == "__main__":
    unittest.main()
