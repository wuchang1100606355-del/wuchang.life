import unittest

from fastapi import HTTPException

from services.xiaoj_intent_field.app import (
    FOUNDER_REF,
    FounderIntentPacket,
    _build_snapshot,
)
from w7tp_gt_mesh import core


def request(**overrides):
    values = {
        "intent": "Founder intent",
        "state_ref": "state:test",
        "coordinate_ref": "adi:test",
        "evidence_refs": ["sha256:" + "0" * 64],
        "execution_policy": "INTERNAL_EVIDENCE_ONLY",
        "generative_target": "receiver-local reconstruction",
        "risk_state": "FAIL_CLOSED_NO_EXTERNAL_EFFECT",
        "founder_ref": FOUNDER_REF,
    }
    values.update(overrides)
    return FounderIntentPacket(**values)


class FounderIntentRouteTests(unittest.TestCase):
    def test_candidate_snapshot_has_fixed_8d_and_no_final_authority(self):
        snapshot = _build_snapshot(request(), 1)
        self.assertEqual(core.SNAPSHOT_SCHEMA, snapshot["schema_id"])
        self.assertEqual(1, snapshot["logical_time"])
        for dimension in (
            "D1_INTENT",
            "D2_STATE",
            "D3_COORDINATE",
            "D4_EVIDENCE",
            "D5_EXECUTION",
            "D6_GENERATIVE_TRANSMISSION",
            "D7_RISK_QUARANTINE",
            "D8_ENVELOPE_VERIFICATION",
        ):
            self.assertIn(dimension, snapshot)
        self.assertFalse(snapshot["D8_ENVELOPE_VERIFICATION"]["final_authority_granted"])

    def test_wrong_founder_ref_is_rejected(self):
        with self.assertRaises(HTTPException) as caught:
            _build_snapshot(request(founder_ref="founder:OTHER"), 1)
        self.assertEqual(403, caught.exception.status_code)

    def test_external_effect_is_rejected(self):
        with self.assertRaises(HTTPException) as caught:
            _build_snapshot(request(execution_policy="EXTERNAL_EFFECT"), 1)
        self.assertEqual(409, caught.exception.status_code)


if __name__ == "__main__":
    unittest.main()
