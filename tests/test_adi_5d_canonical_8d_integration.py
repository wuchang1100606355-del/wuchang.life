from __future__ import annotations

import copy
import os
import tempfile
import time
import unittest

from tools.intent_field.adi_5d_absolute_index_verifier import base_pass_packet as base_adi_5d_packet
from tools.taiji_8d_canonical_verifier import (
    ALLOW,
    BLOCK,
    EXEC_POS_ORDER,
    HOLD,
    Canonical8DVerifier,
    PersistentNonceLedger,
    VerifierConfig,
    VerifierSecrets,
    sign_d7_packet,
)
from tools import w7tp_packet_inference_runtime as packet_runtime


D7_SECRET = b"dummy-d7-secret-for-test-only"
TRAJ_SECRET = b"dummy-trajectory-secret-for-test-only"
AUDIT_SECRET = b"dummy-audit-secret-for-test-only"


def make_verifier(sqlite_path: str) -> Canonical8DVerifier:
    secrets = VerifierSecrets(
        d7_secret=D7_SECRET,
        trajectory_secret=TRAJ_SECRET,
        audit_secret=AUDIT_SECRET,
        key_version="test-key-v1",
    )
    ledger = PersistentNonceLedger(sqlite_path)
    return Canonical8DVerifier(secrets=secrets, nonce_ledger=ledger, config=VerifierConfig(ttl_seconds=30))


def make_payload(now: float, nonce: str, task: str = "intent_order_latte") -> dict:
    payload = {
        "delta_D1": "user1",
        "ref_D2": task,
        "delta_D4": "route_local",
        "env_D8": {"nonce": nonce, "timestamp": now},
        "adi_5d_absolute_index": base_adi_5d_packet(),
    }
    payload["proof_D7"] = sign_d7_packet(payload, D7_SECRET)
    return payload


class ADI5DCanonical8DIntegrationTest(unittest.TestCase):
    def run_packet(self, payload: dict, now: float) -> tuple[str, dict]:
        with tempfile.TemporaryDirectory() as td:
            verifier = make_verifier(os.path.join(td, "nonce.sqlite3"))
            return verifier.process_transmission(payload, now=now)

    def test_valid_adi_5d_gate_allows_then_tensor_candidate(self) -> None:
        now = time.time()
        decision, log = self.run_packet(make_payload(now, "nonce-valid-adi"), now)
        self.assertEqual(decision, ALLOW)
        self.assertEqual(log["gate_stage"], "tensor_collapse")
        self.assertEqual(log["execution_candidate"], EXEC_POS_ORDER)
        self.assertEqual(log["adi_5d_gate_result"]["result_code"], "ADI_5D_GATE_PASS")

    def test_missing_adi_5d_index_holds_before_tensor(self) -> None:
        now = time.time()
        payload = make_payload(now, "nonce-missing-adi")
        payload.pop("adi_5d_absolute_index")
        decision, log = self.run_packet(payload, now)
        self.assertEqual(decision, HOLD)
        self.assertEqual(log["gate_stage"], "adi_5d_gate")
        self.assertIn("ADI_5D_ABSOLUTE_INDEX_MISSING", log["adi_5d_gate_result"]["errors"])

    def test_invalid_adi_5d_structure_holds(self) -> None:
        now = time.time()
        payload = make_payload(now, "nonce-invalid-adi")
        payload["adi_5d_absolute_index"]["generic_5d_schema_used"] = True
        decision, log = self.run_packet(payload, now)
        self.assertEqual(decision, HOLD)
        self.assertEqual(log["gate_stage"], "adi_5d_gate")
        self.assertIn("GENERIC_5D_SCHEMA_USED", log["adi_5d_gate_result"]["errors"])

    def test_gt_core_definition_drift_holds(self) -> None:
        now = time.time()
        payload = make_payload(now, "nonce-gt-drift")
        payload["generative_transmission_core"] = "cloud encrypted sync backup file transfer"
        decision, log = self.run_packet(payload, now)
        self.assertEqual(decision, HOLD)
        self.assertEqual(log["gate_stage"], "adi_5d_gate")
        self.assertIn("GT_CORE_DEFINITION_DRIFT_FILE_TRANSFER_OR_CLOUD_SYNC", log["adi_5d_gate_result"]["errors"])

    def test_unknown_task_blocks_after_valid_adi_gate(self) -> None:
        now = time.time()
        decision, log = self.run_packet(make_payload(now, "nonce-unknown-task", task="intent_unknown"), now)
        self.assertEqual(decision, BLOCK)
        self.assertEqual(log["gate_stage"], "tensor_collapse")
        self.assertNotEqual(log["execution_candidate"], EXEC_POS_ORDER)

    def test_packet_runtime_consumes_canonical_result_only(self) -> None:
        advisory_results = [{"decision": "ALLOW", "reasons": ["runtime advisory only"]}]
        without_canonical = packet_runtime.final_verifier(advisory_results)
        self.assertEqual(without_canonical["decision"], HOLD)
        self.assertFalse(without_canonical["runtime_authority"])

        canonical_allow = {"decision": ALLOW, "reasons": ["canonical 8D verifier pass"]}
        with_canonical = packet_runtime.final_verifier(copy.deepcopy(advisory_results), canonical_allow)
        self.assertEqual(with_canonical["decision"], ALLOW)
        self.assertEqual(with_canonical["authority"], "canonical_8d_verifier")
        self.assertFalse(with_canonical["runtime_authority"])


if __name__ == "__main__":
    unittest.main()
