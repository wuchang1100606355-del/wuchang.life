import tempfile
import unittest
from pathlib import Path
from core.adi_native.evidence_ledger import (
    VerifiableSpacetimeSystem, GENESIS_HASH
)
from tools.total_field.d4_adi_v2_record_wiring import (
    append_fact, append_privacy_access, verify
)

class WiringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "ledger.jsonl"
        self.ledger = VerifiableSpacetimeSystem(
            self.path,
            legacy_file_sha256="a" * 64,
            legacy_chain_head=GENESIS_HASH,
        )

    def fact(self):
        return append_fact(
            self.ledger,
            event_id="fixture-1",
            action="read_only_test",
            actor_ref="agent:test",
            accountable_person_ref="person:test",
            result="PASS",
        )

    def privacy(self, fields=None):
        return append_privacy_access(
            self.ledger,
            request_id="request:test",
            requester_ref="operator:test",
            accountable_person_ref="person:test",
            authority_ref="authority:test",
            purpose="access_audit_test",
            disclosed_fields=fields or ["masked_id"],
            result="PASS",
        )

    def test_01_fact_append(self):
        self.assertEqual(self.fact()["event_type"], "W7TP_FACT")

    def test_02_fact_verify(self):
        self.fact()
        self.assertEqual(verify(self.ledger)["state"], "PASS")

    def test_03_privacy_append(self):
        self.assertEqual(
            self.privacy()["event_type"], "W7TP_PRIVACY_ACCESS"
        )

    def test_04_privacy_verify(self):
        self.privacy()
        self.assertEqual(verify(self.ledger)["state"], "PASS")

    def test_05_actor_accountability(self):
        r = self.fact()
        self.assertNotEqual(
            r["actor_ref"], r["accountable_person_ref"]
        )

    def test_06_field_scope_reject(self):
        with self.assertRaises(ValueError):
            self.privacy(["password"])

    def test_07_tamper_detect(self):
        self.fact()
        self.path.write_text(
            self.path.read_text().replace(
                "read_only_test", "modified_test"
            )
        )
        with self.assertRaises(ValueError):
            verify(self.ledger)

    def test_08_append_chain(self):
        self.fact()
        self.privacy()
        self.assertEqual(verify(self.ledger)["state"], "PASS")

    def test_09_no_member_plaintext(self):
        self.privacy()
        record = self.privacy()
        self.assertIs(record["content"]["contains_member_plaintext"], False)
        self.assertIn('"contains_member_plaintext": false', self.path.read_text())

    def test_10_logical_time(self):
        a = self.fact()
        b = self.privacy()
        self.assertGreater(
            b["logical_time"], a["logical_time"]
        )

if __name__ == "__main__":
    unittest.main()
