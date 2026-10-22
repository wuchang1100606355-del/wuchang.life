#!/usr/bin/env python3
"""F3 negative isolation tests. Do not create a real founder receipt."""
from __future__ import annotations
import copy
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from f3_delivery_evidence_gate_candidate import audit, canonical

BASE = Path(__file__).parent
CONTRACT = json.loads((BASE/"F3_ACTION_CONTRACT_CANDIDATE.json").read_text(encoding="utf-8"))
MANIFEST = CONTRACT["source"]["manifest_sha256"]
PAYLOAD = CONTRACT["source"]["payload_sha256"]
NOW = datetime.fromisoformat(CONTRACT["created_at_utc"].replace("Z","+00:00"))+timedelta(minutes=2)

def rehash(c: dict) -> dict:
    c["candidate_sha256"] = hashlib.sha256(canonical({k:v for k,v in c.items() if k!="candidate_sha256"})).hexdigest()
    return c

class F3EvidenceOnlyTests(unittest.TestCase):
    def runcheck(self, c=None, **kw):
        return audit(c if c is not None else CONTRACT, observed_manifest_sha256=MANIFEST,
                     observed_payload_sha256=PAYLOAD, now=NOW, **kw)

    def test_live_candidate_structure_yields_hold_only(self):
        r=self.runcheck()
        self.assertEqual(r["decision"],"HOLD")
        self.assertTrue(r["structural_candidate_pass"])
        self.assertFalse(r["signable_release"])
        self.assertFalse(r["verified_F3_closure"])

    def test_unsigned_allow_claim_is_not_authority(self):
        r=self.runcheck(claimed_receipt={"decision":"ALLOW","actor_role":"FOUNDER"})
        self.assertEqual(r["decision"],"HOLD")
        self.assertIn("HOLD_F3_UNTRUSTED_RECEIPT_CLAIM_NOT_AUTHORITY",r["reasons"])

    def test_legacy_receipt_copied_to_MSI_blocked_as_scope_mismatch(self):
        r=self.runcheck(receiver_node="MSI",claimed_receipt={"decision":"ALLOW"})
        self.assertEqual(r["decision"],"BLOCK")
        self.assertIn("BLOCK_F3_RECEIVER_SCOPE_MISMATCH",r["reasons"])

    def test_manifest_hash_drift_blocks(self):
        r=audit(CONTRACT, observed_manifest_sha256="f"*64, observed_payload_sha256=PAYLOAD, now=NOW)
        self.assertIn("BLOCK_F3_PACKAGE_MANIFEST_SHA256_MISMATCH",r["reasons"])

    def test_payload_hash_drift_blocks(self):
        r=audit(CONTRACT, observed_manifest_sha256=MANIFEST, observed_payload_sha256="f"*64, now=NOW)
        self.assertIn("BLOCK_F3_PACKAGE_PAYLOAD_SHA256_MISMATCH",r["reasons"])

    def test_candidate_self_hash_tampering_blocks(self):
        c=copy.deepcopy(CONTRACT)
        c["source"]["version"]="fictional"
        self.assertIn("BLOCK_F3_CONTRACT_SELF_HASH_MISMATCH", self.runcheck(c)["reasons"])

    def test_altered_action_id_blocks_even_when_rehashed(self):
        c=rehash(copy.deepcopy(CONTRACT))
        c["ACTION_ID"]="A-UNKNOWN"
        rehash(c)
        self.assertIn("BLOCK_F3_ACTION_OR_TASK_MISMATCH",self.runcheck(c)["reasons"])

    def test_candidate_expired_holds(self):
        r=audit(CONTRACT, observed_manifest_sha256=MANIFEST, observed_payload_sha256=PAYLOAD,
                now=datetime.fromisoformat(CONTRACT["review_expires_at_utc"])+timedelta(seconds=1))
        self.assertEqual(r["decision"],"HOLD")
        self.assertIn("HOLD_F3_CANDIDATE_EXPIRED_OR_INVALID_TIME",r["reasons"])

    def test_candidate_premature_authority_claim_blocks(self):
        c=copy.deepcopy(CONTRACT); c["authority"]["decision"]="ALLOW"; rehash(c)
        self.assertIn("BLOCK_F3_UNVERIFIED_AUTHORITY_CLAIM",self.runcheck(c)["reasons"])

    def test_signable_release_promotion_blocks(self):
        c=copy.deepcopy(CONTRACT); c["signable_release"]=True; rehash(c)
        self.assertIn("BLOCK_F3_AUTHORITY_OVERCLAIM",self.runcheck(c)["reasons"])

    def test_f4_f5_missing_stop_conditions_blocks(self):
        c=copy.deepcopy(CONTRACT);c["stop_conditions"].pop("F5");rehash(c)
        self.assertIn("BLOCK_F3_F4_F5_STOP_CONDITIONS_MISSING",self.runcheck(c)["reasons"])

    def test_untrusted_device_ref_blocks(self):
        c=copy.deepcopy(CONTRACT);c["target"]["receiver_device_ref"]="RemoteDesktop:unknown";rehash(c)
        self.assertIn("BLOCK_F3_RECEIVER_SCOPE_MISMATCH",self.runcheck(c)["reasons"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
