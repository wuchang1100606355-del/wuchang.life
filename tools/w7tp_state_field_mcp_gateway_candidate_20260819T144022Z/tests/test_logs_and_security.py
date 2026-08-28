from __future__ import annotations

import json
import unittest

from tests.support import gateway
from w7tp_state_field_gateway.errors import GatewayError
from w7tp_state_field_gateway.redaction import contains_sensitive_canary, redact_text


class LogAndSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = gateway()

    def test_log_lines_time_and_mask_are_bounded(self) -> None:
        envelope = self.gateway.call_tool(
            "read_bounded_logs",
            {
                "node_id": "msi-linux-wsl",
                "service_id": "candidate-fixture-log",
                "lines": 5,
                "since_seconds": 60,
            },
        )
        result = envelope["result"]
        self.assertLessEqual(result["returned_lines"], 3)
        self.assertTrue(result["masked"])
        self.assertNotIn("synthetic.user", result["text"])
        self.assertNotIn("SYNTHETICONLY", result["text"])
        self.assertNotIn("SYNTHETIC_UNKNOWN_TIME_MUST_NOT_APPEAR", result["text"])
        self.assertIn("<redacted", result["text"])

    def test_log_bounds_fail_closed(self) -> None:
        base = {
            "node_id": "msi-linux-wsl",
            "service_id": "candidate-fixture-log",
            "lines": 5,
            "since_seconds": 60,
        }
        for field, value in (("lines", 0), ("lines", 201), ("since_seconds", 0), ("since_seconds", 3601)):
            with self.subTest(field=field, value=value):
                with self.assertRaises(GatewayError) as raised:
                    self.gateway.call_tool("read_bounded_logs", {**base, field: value})
                self.assertEqual(raised.exception.code, "DENY_OUT_OF_BOUNDS")

    def test_real_service_log_source_is_not_authorized(self) -> None:
        with self.assertRaises(GatewayError) as raised:
            self.gateway.call_tool(
                "read_bounded_logs",
                {
                    "node_id": "msi-linux-wsl",
                    "service_id": "local-port-8105",
                    "lines": 10,
                    "since_seconds": 60,
                },
            )
        self.assertEqual(raised.exception.code, "DENY_PROTECTED_RESOURCE")

    def test_path_traversal_arbitrary_command_and_privilege_inputs_are_denied(self) -> None:
        base = {
            "node_id": "msi-linux-wsl",
            "service_id": "candidate-fixture-log",
            "lines": 5,
            "since_seconds": 60,
        }
        payloads = (
            {"path": "../protected"},
            {"cmd": "synthetic"},
            {"shell": True},
            {"run_as": "administrator"},
            {"url": "file:protected"},
        )
        for payload in payloads:
            with self.subTest(payload=list(payload)):
                with self.assertRaises(GatewayError):
                    self.gateway.call_tool("read_bounded_logs", {**base, **payload})

    def test_synthetic_sensitive_patterns_are_masked(self) -> None:
        synthetic_ip = "100." + "64.12.34"
        synthetic_email = "person" + "@example.invalid"
        synthetic_key = "tskey-" + "auth-SYNTHETICONLY1234"
        synthetic_bearer = "Bearer " + "SYNTHETICONLY123456"
        raw = " ".join((synthetic_ip, synthetic_email, synthetic_key, synthetic_bearer))
        masked = redact_text(raw)
        for canary in (synthetic_ip, synthetic_email, synthetic_key, synthetic_bearer):
            self.assertNotIn(canary, masked)
        self.assertFalse(contains_sensitive_canary(masked))

    def test_json_basic_auth_jwt_and_quoted_assignments_are_masked(self) -> None:
        canaries = (
            '{"token":"SYNTHETIC_JSON_TOKEN_123456789"}',
            "Authorization: Basic U1lOVEhFVElDX0JBU0lDX0NBTkFSWQ==",
            '{"authorization":"Basic U1lOVEhFVElDX0pTT05fQkFTSUM="}',
            "eyJzeW50aGV0aWMiOiJvbmx5In0.c3ludGhldGljLWNhbmFyeQ.c2lnbmF0dXJlLWNhbmFyeQ",
            "api_key='SYNTHETIC_QUOTED_KEY_123456789'",
        )
        for raw in canaries:
            with self.subTest(raw=raw.split(":", 1)[0]):
                self.assertTrue(contains_sensitive_canary(raw))
                masked = redact_text(raw)
                self.assertNotIn("SYNTHETIC_", masked)
                self.assertNotIn("U1lOVEh", masked)
                self.assertNotIn("eyJzeW", masked)
                self.assertFalse(contains_sensitive_canary(masked))

    def test_tool_metadata_and_results_do_not_contain_sensitive_canaries(self) -> None:
        metadata = json.dumps(self.gateway.list_tool_definitions(), sort_keys=True)
        self.assertFalse(contains_sensitive_canary(metadata))
        topology = self.gateway.call_tool("get_state_field_topology", {})
        self.assertFalse(contains_sensitive_canary(json.dumps(topology, sort_keys=True)))
        for protected in topology["result"]["protected_opaque_nodes"]:
            self.assertEqual(protected["state"], "PROTECTED_OPAQUE_NODE")
            self.assertFalse(protected["read"])
            self.assertFalse(protected["hashed"])


if __name__ == "__main__":
    unittest.main()
