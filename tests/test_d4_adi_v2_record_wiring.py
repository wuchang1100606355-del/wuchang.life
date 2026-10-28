import tempfile
import unittest
from pathlib import Path
from core.adi_native.evidence_ledger import (
    VerifiableSpacetimeSystem, GENESIS_HASH
)
from tools.total_field.d4_adi_v2_record_wiring import (
    append_fact, append_privacy_access, append_stage_avatar_dispatch, verify
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

    def avatar_dispatch(self, target_node="taiji02", target_pid=1234):
        return append_stage_avatar_dispatch(
            self.ledger,
            request_id="req:avatar:01",
            authority_ref="authority:d8:test",
            actor_ref="operator:msi",
            accountable_person_ref="founder:jiang",
            avatar_asset_path="Taiji_Odoo/addons/wuchang_ordering_ui_suite/static/src/data/xiaoj_rig/closeup.webp",
            target_node=target_node,
            target_pid=target_pid,
            result="PASS_STAGE_DISPATCHED",
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

    def test_11_avatar_dispatch_append_and_mask(self):
        rec = self.avatar_dispatch()
        self.assertEqual(rec["event_type"], "W7TP_STAGE_AVATAR_DISPATCH")
        self.assertIs(rec["content"]["contains_member_plaintext"], False)
        self.assertEqual(rec["content"]["target_node"], "taiji02")

    def test_12_avatar_dispatch_chain_verify(self):
        self.fact()
        self.avatar_dispatch()
        res = verify(self.ledger)
        self.assertEqual(res["state"], "PASS")
        self.assertEqual(res["ledger_state"], "PASS_LEDGER_VERIFIED")

    def test_13_avatar_dispatch_tamper_detect(self):
        self.avatar_dispatch()
        self.path.write_text(
            self.path.read_text().replace("taiji02", "taiji03")
        )
        with self.assertRaises(ValueError):
            verify(self.ledger)

    def test_14_avatar_dispatch_fail_closed_invalid_node_or_empty(self):
        with self.assertRaises(ValueError):
            self.avatar_dispatch(target_node="w7tp-msi")
        with self.assertRaises(ValueError):
            append_stage_avatar_dispatch(
                self.ledger,
                request_id="",
                authority_ref="auth",
                actor_ref="actor",
                accountable_person_ref="founder",
                avatar_asset_path="",
                target_node="taiji02",
                target_pid=-1,
                result="PASS",
            )


if __name__ == "__main__":
    unittest.main()
