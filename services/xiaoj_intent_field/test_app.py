import unittest

from fastapi import HTTPException

from services.xiaoj_intent_field.app import (
    BROWSER_ORIGINS,
    FOUNDER_REF,
    FounderIntentPacket,
    _build_snapshot,
    _select_receiver_url,
    TOTAL_FIELD_LAN_URL,
    TOTAL_FIELD_VPN_URL,
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
    def test_browser_origins_are_exact_local_competition_origins(self):
        self.assertEqual(
            {
                "http://127.0.0.1:8069",
                "http://localhost:8069",
            },
            set(BROWSER_ORIGINS),
        )
        self.assertNotIn("*", BROWSER_ORIGINS)

    def test_receiver_route_uses_lan_before_vpn(self):
        calls = []

        def probe(url):
            calls.append(url)
            return True

        self.assertEqual((TOTAL_FIELD_LAN_URL, "LAN_PRIMARY"), _select_receiver_url(probe))
        self.assertEqual([TOTAL_FIELD_LAN_URL], calls)

    def test_receiver_route_uses_registered_vpn_only_after_lan_is_unavailable(self):
        calls = []

        def probe(url):
            calls.append(url)
            return url == TOTAL_FIELD_VPN_URL

        self.assertEqual(
            (TOTAL_FIELD_VPN_URL, "VPN_FALLBACK_AFTER_LAN_UNAVAILABLE"),
            _select_receiver_url(probe),
        )
        self.assertEqual([TOTAL_FIELD_LAN_URL, TOTAL_FIELD_VPN_URL], calls)

    def test_receiver_route_fails_closed_when_both_paths_are_unavailable(self):
        with self.assertRaises(HTTPException) as caught:
            _select_receiver_url(lambda _url: False)
        self.assertEqual(503, caught.exception.status_code)
        self.assertEqual("HOLD_TOTAL_FIELD_RECEIVER_UNAVAILABLE", caught.exception.detail)

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
