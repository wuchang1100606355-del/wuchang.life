from __future__ import annotations

import copy
import json
import unittest
from typing import Never

from tests.support import fixed_clock, gateway
from w7tp_state_field_gateway.errors import GatewayError, PolicyDenied
from w7tp_state_field_gateway.state_field import StateFieldRuntime, classify_8d_definition


class StateFieldRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = gateway()

    def test_eight_dimensions_are_executable_programs_with_dynamic_activation(self) -> None:
        self.assertEqual(
            self.gateway.runtime.dimension_names,
            ("identity", "intent", "authority", "relation", "resource", "time", "risk", "governance"),
        )
        list_state = self.gateway.call_tool("list_nodes", {})["state"]
        log_state = self.gateway.call_tool(
            "read_bounded_logs",
            {
                "node_id": "msi-linux-wsl",
                "service_id": "candidate-fixture-log",
                "lines": 2,
                "since_seconds": 60,
            },
        )["state"]
        self.assertNotEqual(list_state["active_dimensions"], log_state["active_dimensions"])
        self.assertEqual(len(list_state["dimension_states"]), 8)
        self.assertEqual(len(log_state["dimension_states"]), 8)
        self.assertEqual(log_state["fusion"]["status"], "FUSED")
        self.assertEqual(log_state["definition"], "EXECUTABLE_DYNAMIC_DIMENSION_PROGRAMS")

    def test_adi_is_a_non_executable_index_not_the_runtime(self) -> None:
        envelope = self.gateway.call_tool("get_node_health", {"node_id": "msi-linux-wsl"})
        self.assertIsNot(envelope["state"], envelope["coordinate"])
        self.assertFalse(envelope["coordinate"]["callable_present"])
        self.assertFalse(envelope["coordinate"]["activation_authority"])
        encoded = json.dumps(envelope["coordinate"], sort_keys=True).lower()
        self.assertNotIn("handler", encoded)
        self.assertNotIn("command", encoded)

    def test_adi_mutation_does_not_activate_a_dimension(self) -> None:
        envelope = self.gateway.call_tool("list_nodes", {})
        active_before = list(envelope["state"]["active_dimensions"])
        copied_index = copy.deepcopy(envelope["coordinate"])
        copied_index["coordinate"]["tool"] = "synthetic-index-change"
        self.assertEqual(envelope["state"]["active_dimensions"], active_before)

    def test_static_d1_d8_fixture_is_definition_drift_without_mutation(self) -> None:
        static_fixture = {f"D{index}_FIELD": {"value": index} for index in range(1, 9)}
        original = copy.deepcopy(static_fixture)
        self.assertEqual(classify_8d_definition(static_fixture), "TECHNICAL_DEFINITION_DRIFT")
        self.assertEqual(static_fixture, original)

    def test_state_coordinate_hash_packet_sequence_is_bound(self) -> None:
        envelope = self.gateway.call_tool("list_nodes", {})
        self.assertEqual(envelope["packet"]["sequence"], "State->Coordinate->Hash->Packet")
        self.assertEqual(envelope["packet"]["hash"]["value"], envelope["hash"])
        self.assertEqual(envelope["packet"]["sandbox"], "LOCAL_LOOPBACK_ONLY")
        self.assertEqual(envelope["packet"]["land"], "NOT_REQUESTED_CANDIDATE_ONLY")

    def test_carriers_are_not_generative_transport(self) -> None:
        topology = self.gateway.call_tool("get_state_field_topology", {})["result"]
        for carrier in topology["carriers"]:
            self.assertEqual(carrier["role"], "CARRIER_ONLY")
            self.assertFalse(carrier["generative_transport"])
            self.assertFalse(carrier["enabled_or_modified_by_candidate"])

    def test_logical_planes_share_evidenced_physical_domains(self) -> None:
        nodes = {
            node["id"]: node
            for node in self.gateway.call_tool("get_state_field_topology", {})["result"]["nodes"]
        }
        self.assertEqual(
            nodes["msi-linux-wsl"]["physical_fault_domain_id"],
            nodes["msi-windows"]["physical_fault_domain_id"],
        )
        self.assertEqual(
            nodes["taiji03-linux"]["physical_fault_domain_id"],
            nodes["taiji03-windows"]["physical_fault_domain_id"],
        )

    def test_authority_denial_is_fused_inside_runtime_before_adapter(self) -> None:
        with self.assertRaises(GatewayError) as denied:
            self.gateway.call_tool("get_node_health", {"node_id": "unknown-node"})
        self.assertEqual(denied.exception.code, "DENY_UNKNOWN_NODE")
        self.assertEqual(self.gateway.runtime.last_decision["decision"], "DENY")
        self.assertEqual(
            self.gateway.runtime.last_decision["policy_code"], "DENY_UNKNOWN_NODE"
        )
        self.assertFalse(self.gateway.runtime.last_decision["adapter_invoked"])

    def test_governance_gate_never_invokes_adapter_after_dimension_denial(self) -> None:
        runtime = StateFieldRuntime(clock=fixed_clock)
        adapter_calls = 0

        def adapter() -> dict[str, object]:
            nonlocal adapter_calls
            adapter_calls += 1
            return {"unexpected": True}

        def denied_gate() -> Never:
            raise PolicyDenied("DENY_SYNTHETIC_POLICY", "Synthetic policy denial.")

        with self.assertRaises(PolicyDenied):
            runtime.execute("list_nodes", {}, denied_gate)
        self.assertEqual(adapter_calls, 0)
        self.assertFalse(runtime.last_decision["adapter_invoked"])

        envelope = runtime.execute("list_nodes", {}, lambda: adapter)
        self.assertEqual(envelope["state"]["fusion"]["status"], "FUSED")
        self.assertEqual(adapter_calls, 1)
        self.assertTrue(runtime.last_decision["adapter_invoked"])


if __name__ == "__main__":
    unittest.main()
