"""Rule-only checks for the existing Dynamic Context transport bridge.

The tests mock ADI issuance and transport to avoid live writes or model calls.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tools import w7tp_bridge_dynamic_context_transport_v1 as bridge


class RuleGatewayOnlyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="w7tp-rule-gateway-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        state = self.root / "state"
        state.mkdir()
        (state / "WORK_LEDGER.json").write_text(
            json.dumps({"TASKS": [{"TASK_ID": "T-023"}, {"TASK_ID": "T-042"}]}),
            encoding="utf-8",
        )

    def test_explicit_known_task_wins_without_plan(self) -> None:
        task, origin = bridge._bind_task(intent="核對 T-023 的原胞", root=self.root)
        self.assertEqual((task, origin), ("T-023", "EXPLICIT_INTENT_TASK"))

    def test_current_checkpoint_can_bind_exact_known_task(self) -> None:
        (self.root / "state/CURRENT_CONVERSATION_CHECKPOINT.json").write_text(
            json.dumps({"current_goal": "依 T-042 完成收斂"}), encoding="utf-8",
        )
        task, origin = bridge._bind_task(intent="讀取現行狀態", root=self.root)
        self.assertEqual((task, origin), ("T-042", "CURRENT_CONVERSATION_CHECKPOINT"))

    def test_unknown_task_does_not_fall_back_to_model_plan(self) -> None:
        with self.assertRaisesRegex(
            bridge.BridgeDynamicContextHold, "HOLD_DYNAMIC_CONTEXT_TASK_BINDING_UNKNOWN"
        ):
            bridge._bind_task(intent="未註冊任務", root=self.root)

    def test_unknown_explicit_task_cannot_inherit_other_checkpoint(self) -> None:
        (self.root / "state/CURRENT_CONVERSATION_CHECKPOINT.json").write_text(
            json.dumps({"current_goal": "進行 T-042"}), encoding="utf-8",
        )
        with self.assertRaisesRegex(
            bridge.BridgeDynamicContextHold, "HOLD_DYNAMIC_CONTEXT_TASK_BINDING_UNKNOWN"
        ):
            bridge._bind_task(intent="進行 T-999", root=self.root)

    def test_multiple_explicit_tasks_are_not_arbitrated_by_model(self) -> None:
        with self.assertRaisesRegex(
            bridge.BridgeDynamicContextHold, "HOLD_DYNAMIC_CONTEXT_MULTIPLE_TASK_REFERENCES"
        ):
            bridge._bind_task(intent="請比較 T-023 與 T-042", root=self.root)

    def test_transport_bridge_does_not_import_model_resource_planner(self) -> None:
        source = Path(bridge.__file__).read_text(encoding="utf-8")
        self.assertNotIn("services.gateway.natural_language_control", source)
        self.assertNotIn("build_plan(", source)
        self.assertNotIn("run_local_agent(", source)

    def test_rule_only_payload_reuses_existing_context_broker(self) -> None:
        visible = {
            "context_ref": "context:task:T-023",
            "state_projection": {"task": {"task_ref": "task:T-023", "state": "DONE"}},
            "evidence_refs": ["evidence:test"],
            "capability_refs": ["capability:test"],
            "acceptance_conditions": ["condition:test"],
            "schema_refs": ["schema:test"],
            "interface_refs": ["interface:test"],
            "non_core_rule_capsule_refs": [],
        }
        broker = Mock()
        broker.register.return_value = {
            "pull_coordinate": "tfctx:mock", "expires_at": "2026-12-01T00:00:00Z"
        }
        broker.pull.return_value = {
            "model_visible_context": visible,
            "pull_result_sha256": "f" * 64,
            "authority": {"candidate_only": True},
            "persistence_policy": {"mode": "EPHEMERAL_CONTEXT_REFERENCES_ONLY"},
            "transmission_semantics": {"semantic_class": "NON_DIFFERENTIAL"},
        }
        with (
            patch.object(bridge, "select_task_state_support_refs",
                         return_value={"action_refs": ["A-1"], "adi_record_ids": ["ADI-1"]}) as select,
            patch.object(bridge, "issue_task_state_minimum_packet",
                         return_value={"packet": {
                             "packet_ref": "packet:test", "packet_sha256": "a" * 64,
                             "adi_coordinate_ref": "adi:test"
                         }}) as issue,
            patch.object(bridge, "TotalFieldDynamicContextPullBroker", return_value=broker),
        ):
            payload = bridge.build_dynamic_context_payload(
                intent="處理 T-023", model="xiaoj-receiver", root=self.root
            )
        self.assertEqual(payload["task_id"], "T-023")
        self.assertEqual(payload["state_projection"], visible["state_projection"])
        self.assertEqual(payload["task_profile"]["routing_mode"],
                         "DETERMINISTIC_RULE_GATEWAY")
        self.assertIs(payload["task_profile"]["model_inference_for_transport"], False)
        select.assert_called_once()
        issue.assert_called_once()
        broker.register.assert_called_once()
        broker.pull.assert_called_once()

    def test_delivery_delegates_to_existing_rule_based_selector(self) -> None:
        transport = SimpleNamespace(build_transport=Mock(return_value={"mode": "FULL_TRANSFER"}))
        with (
            patch.object(bridge, "build_dynamic_context_payload",
                         return_value={"state": "PASS_TOTAL_FIELD_DYNAMIC_CONTEXT"}) as payload,
            patch.object(bridge, "_load_context_transport", return_value=transport),
        ):
            result = bridge.build_bridge_delivery(
                intent="處理 T-023", model="xiaoj-receiver",
                receiver_handshake={"node_ref": "MSI"}, root=self.root,
            )
        self.assertEqual(result["mode"], "FULL_TRANSFER")
        payload.assert_called_once()
        transport.build_transport.assert_called_once()


if __name__ == "__main__":
    unittest.main()
