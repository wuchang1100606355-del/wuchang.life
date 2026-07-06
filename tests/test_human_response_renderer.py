from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field.human_response_renderer import render_human_response


class HumanResponseRendererTest(unittest.TestCase):
    def test_pass_reply_hides_internal_markers(self) -> None:
        response = render_human_response(
            {
                "decision": "PASS",
                "risk_level": "LOW",
                "reply_candidate": {
                    "text": "D1 D8 proof_D7 env_D8 H64 TD 可以回覆候選資訊",
                },
            },
            channel="web",
        )

        self.assertEqual(response["decision"], "PASS")
        self.assertFalse(response["requires_confirmation"])
        self.assertFalse(response["formal_send_executed"])
        for forbidden in ("D1", "D8", "proof_D7", "env_D8", "H64", "TD"):
            self.assertNotIn(forbidden, response["reply_text"])
        self.assertFalse(response["redaction"]["raw_d_dimensions_exposed"])
        self.assertFalse(response["redaction"]["h64_td_exposed"])

    def test_high_risk_hold_requires_confirmation(self) -> None:
        response = render_human_response(
            {
                "decision": "HOLD",
                "risk_level": "HIGH",
                "gate_code": "HOLD_HARD_RISK_SIDE_EFFECT",
            },
            channel="line",
        )

        self.assertEqual(response["decision"], "HOLD")
        self.assertEqual(response["channel"], "LINE")
        self.assertTrue(response["requires_confirmation"])
        self.assertIn("暫停", response["reply_text"])
        self.assertFalse(response["line_reply_sent"])
        self.assertFalse(response["db_write"])
        self.assertFalse(response["deploy"])
        self.assertFalse(response["restart"])

    def test_missing_adi_hold_has_plain_language(self) -> None:
        response = render_human_response(
            {
                "decision": "HOLD",
                "risk_level": "MEDIUM",
                "gate_code": "HOLD_ADI_5D_ABSOLUTE_INDEX",
            },
            channel="odoo",
        )

        self.assertEqual(response["decision"], "HOLD")
        self.assertEqual(response["channel"], "ODOO")
        self.assertTrue(response["requires_confirmation"])
        self.assertIn("缺少必要索引條件", response["reply_text"])
        self.assertNotIn("D8", response["reply_text"])


if __name__ == "__main__":
    unittest.main()
