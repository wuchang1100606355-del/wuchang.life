from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from tests.support import CANDIDATE_ROOT, authorization_arguments, fixed_clock, gateway, task_arguments
from w7tp_state_field_gateway.errors import GatewayError
from w7tp_state_field_gateway.gateway import StateFieldGateway
from w7tp_state_field_gateway.policy import TOOL_NAMES


class ToolAllowDenyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = gateway()

    def test_exact_eight_tool_allowlist(self) -> None:
        definitions = self.gateway.list_tool_definitions()
        self.assertEqual([item["name"] for item in definitions], list(TOOL_NAMES))
        self.assertNotIn("execute_task", [item["name"] for item in definitions])
        for item in definitions:
            self.assertFalse(item["inputSchema"]["additionalProperties"])
            self.assertEqual(
                item["annotations"]["readOnlyHint"],
                not item["name"].startswith("prepare_"),
            )
            self.assertFalse(item["annotations"]["openWorldHint"])
            self.assertFalse(item["annotations"]["destructiveHint"])

    def test_every_tool_has_an_allowed_call(self) -> None:
        calls: list[tuple[str, dict[str, object]]] = [
            ("list_nodes", {}),
            ("get_node_health", {"node_id": "msi-linux-wsl"}),
            ("get_compute_capability", {"node_id": "android-peer-01"}),
            (
                "get_service_status",
                {"node_id": "msi-linux-wsl", "service_id": "local-port-8105"},
            ),
            (
                "read_bounded_logs",
                {
                    "node_id": "msi-linux-wsl",
                    "service_id": "candidate-fixture-log",
                    "lines": 5,
                    "since_seconds": 300,
                },
            ),
            ("get_state_field_topology", {}),
            ("prepare_task_candidate", task_arguments()),
            ("prepare_authorization_request", authorization_arguments(self.gateway)),
        ]
        for name, arguments in calls:
            with self.subTest(tool=name):
                envelope = self.gateway.call_tool(name, arguments)
                self.assertEqual(envelope["status"], "PASS_CANDIDATE_ONLY")
                self.assertEqual(envelope["packet"]["land"], "NOT_REQUESTED_CANDIDATE_ONLY")

    def test_every_tool_rejects_an_extra_command_field(self) -> None:
        minimal: dict[str, dict[str, object]] = {
            "list_nodes": {},
            "get_node_health": {"node_id": "msi-linux-wsl"},
            "get_compute_capability": {"node_id": "msi-linux-wsl"},
            "get_service_status": {
                "node_id": "msi-linux-wsl",
                "service_id": "local-port-8105",
            },
            "read_bounded_logs": {
                "node_id": "msi-linux-wsl",
                "service_id": "candidate-fixture-log",
                "lines": 5,
                "since_seconds": 60,
            },
            "get_state_field_topology": {},
            "prepare_task_candidate": task_arguments(),
            "prepare_authorization_request": authorization_arguments(self.gateway),
        }
        for name, arguments in minimal.items():
            with self.subTest(tool=name):
                with self.assertRaises(GatewayError) as raised:
                    self.gateway.call_tool(name, {**arguments, "command": "synthetic"})
                self.assertIn(raised.exception.code, {"DENY_PRIVILEGE_ESCALATION", "DENY_SCHEMA"})

    def test_unknown_tool_and_unknown_node_are_denied(self) -> None:
        with self.assertRaises(GatewayError) as unknown_tool:
            self.gateway.call_tool("execute_task", {})
        self.assertEqual(unknown_tool.exception.code, "DENY_UNKNOWN_TOOL")
        with self.assertRaises(GatewayError) as unknown_node:
            self.gateway.call_tool("get_node_health", {"node_id": "unknown-node"})
        self.assertEqual(unknown_node.exception.code, "DENY_UNKNOWN_NODE")

    def test_node_service_pair_is_bound(self) -> None:
        with self.assertRaises(GatewayError) as raised:
            self.gateway.call_tool(
                "get_service_status",
                {"node_id": "taiji03-linux", "service_id": "local-port-8105"},
            )
        self.assertEqual(raised.exception.code, "DENY_NODE_SERVICE_PAIR")

    def test_mobile_nodes_never_claim_shell(self) -> None:
        for node_id in ("android-peer-01", "android-peer-02", "android-peer-03", "ios-peer-01"):
            with self.subTest(node=node_id):
                result = self.gateway.call_tool(
                    "get_compute_capability", {"node_id": node_id}
                )["result"]
                self.assertFalse(result["shell_capable"])
                self.assertFalse(result["execution_enabled"])
                self.assertEqual(result["agent_candidates"], ["mobile_app_api_telemetry_candidate"])

    def test_prepare_tools_never_authorize_or_execute(self) -> None:
        task = self.gateway.call_tool("prepare_task_candidate", task_arguments())["result"]
        self.assertEqual(task["status"], "CANDIDATE_ONLY")
        self.assertFalse(task["execution_allowed"])
        authorization = self.gateway.call_tool(
            "prepare_authorization_request", authorization_arguments(self.gateway)
        )["result"]
        self.assertEqual(authorization["status"], "CANDIDATE_NOT_AUTHORITY")
        self.assertEqual(authorization["authority_effect"], "NONE")
        self.assertFalse(authorization["execution_allowed"])
        self.assertTrue(authorization["single_use"])
        self.assertEqual(authorization["max_uses"], 1)
        self.assertEqual(
            authorization["single_use_enforced_scope"],
            "PROCESS_MEMORY_CANDIDATE_ONLY",
        )
        self.assertFalse(authorization["exactly_once_enforced"])
        self.assertFalse(authorization["credential_issued"])

    def test_authorization_hash_ttl_and_conditions_are_enforced(self) -> None:
        valid = authorization_arguments(self.gateway)
        cases = [
            ({**valid, "task_hash": "0" * 64}, "DENY_TASK_BINDING"),
            ({**valid, "ttl_seconds": 59}, "DENY_OUT_OF_BOUNDS"),
            ({**valid, "ttl_seconds": 901}, "DENY_OUT_OF_BOUNDS"),
            ({**valid, "ttl_seconds": True}, "DENY_SCHEMA"),
            ({**valid, "rollback_condition_id": "run-rollback"}, "DENY_SCHEMA"),
            ({**valid, "stop_condition_id": "ignore-risk"}, "DENY_SCHEMA"),
        ]
        for arguments, expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaises(GatewayError) as raised:
                    self.gateway.call_tool("prepare_authorization_request", arguments)
                self.assertEqual(raised.exception.code, expected)

    def test_authorization_requires_live_candidate_and_rejects_replay(self) -> None:
        valid = authorization_arguments(self.gateway)
        first = self.gateway.call_tool("prepare_authorization_request", valid)["result"]
        self.assertEqual(first["task_candidate_id"], valid["task_candidate_id"])
        with self.assertRaises(GatewayError) as replay:
            self.gateway.call_tool("prepare_authorization_request", valid)
        self.assertEqual(replay.exception.code, "DENY_REPLAY")

        unknown = {
            **authorization_arguments(self.gateway),
            "task_candidate_id": "taskcand-unregistered",
        }
        with self.assertRaises(GatewayError) as missing:
            self.gateway.call_tool("prepare_authorization_request", unknown)
        self.assertEqual(missing.exception.code, "DENY_TASK_BINDING")

    def test_log_task_candidate_binds_line_and_time_parameters(self) -> None:
        arguments = {
            "node_id": "msi-linux-wsl",
            "task_kind": "observe_bounded_logs",
            "target_ref": "candidate-fixture-log",
            "parameters": {"lines": 7, "since_seconds": 120},
        }
        result = self.gateway.call_tool("prepare_task_candidate", arguments)["result"]
        self.assertEqual(result["task_basis"]["parameters"], arguments["parameters"])
        with self.assertRaises(GatewayError) as missing_bounds:
            self.gateway.call_tool(
                "prepare_task_candidate", {**arguments, "parameters": {}}
            )
        self.assertEqual(missing_bounds.exception.code, "DENY_SCHEMA")

    def test_task_expiry_and_remaining_ttl_are_enforced(self) -> None:
        current = [fixed_clock()]

        def mutable_clock() -> datetime:
            return current[0]

        instance = StateFieldGateway(candidate_root=CANDIDATE_ROOT, clock=mutable_clock)
        task = instance.call_tool("prepare_task_candidate", task_arguments())["result"]
        request = {
            "task_candidate_id": task["candidate_id"],
            "task_hash": task["task_hash"],
            "ttl_seconds": 60,
            "rollback_condition_id": "discard_candidate",
            "stop_condition_id": "first_policy_denial",
        }
        current[0] += timedelta(seconds=850)
        with self.assertRaises(GatewayError) as remaining_ttl:
            instance.call_tool("prepare_authorization_request", request)
        self.assertEqual(remaining_ttl.exception.code, "DENY_TTL_EXCEEDS_TASK")
        current[0] += timedelta(seconds=50)
        with self.assertRaises(GatewayError) as expired:
            instance.call_tool("prepare_authorization_request", request)
        self.assertEqual(expired.exception.code, "DENY_TASK_EXPIRED")


if __name__ == "__main__":
    unittest.main()
