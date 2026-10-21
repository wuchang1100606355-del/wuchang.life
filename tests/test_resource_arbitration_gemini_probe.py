from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core import resource_arbitration as ra


class GeminiProbeTests(unittest.TestCase):
    def test_agent_card_identity_works_without_process_name_in_ss(self):
        ss_output = (
            "LISTEN 0 128 127.0.0.1:12345 0.0.0.0:*\n"
            "LISTEN 0 128 127.0.0.1:46239 0.0.0.0:*\n"
        )

        def fake_http(url, timeout=1.0):
            if url == "http://127.0.0.1:46239/.well-known/agent-card.json":
                return {
                    "ok": True,
                    "data": {
                        "name": "Gemini SDLC Agent",
                        "version": "0.0.2",
                    },
                }
            return {"ok": False, "error_type": "URLError"}

        with (
            patch.object(
                ra.subprocess,
                "run",
                return_value=SimpleNamespace(stdout=ss_output),
            ),
            patch.object(ra, "_http_json", side_effect=fake_http),
        ):
            result = ra.probe_gemini_code_assist()

        self.assertEqual(result["CURRENT_STATE"], "AVAILABLE")
        self.assertEqual(result["A2A_URL"], "http://127.0.0.1:46239/")
        self.assertEqual(
            result["CONTEXT_BINDING_STATE"],
            "POINTER_FIRST_TOTAL_FIELD_BOUND",
        )


if __name__ == "__main__":
    unittest.main()
