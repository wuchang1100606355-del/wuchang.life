from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/field/w7tp_8d_dependency_supply_demand_matrix_v1.schema.json"
MATRIX_PATH = ROOT / "configs/total_field/w7tp_8d_dependency_supply_demand_matrix_v1.candidate.json"
POLICY_SCHEMA_PATH = ROOT / "schemas/field/w7tp_moving_v_route_policy_v2.schema.json"
POLICY_INSTANCE_PATH = ROOT / "configs/total_field/w7tp_moving_v_route_policy_v2.schema_instance.candidate.json"
POLICY_SOURCE_PATH = ROOT / "configs/total_field/w7tp_moving_v_route_cleanup_v2.candidate.json"
V1_PATH = ROOT / "schemas/field/w7tp_moving_v_preload_cleanup_v1.schema.json"

ALLOWED_STATES = {
    "DIRECT_NATIVE",
    "VERIFIED_ADAPTER",
    "ADAPTER_REQUIRED",
    "AUTHORITY_REQUIRED",
    "HOLD",
}
PASS_STATES = {"DIRECT_NATIVE", "VERIFIED_ADAPTER"}
EXPECTED_V1_SHA256 = "ef8a6c236924aed7dfbc17b6f97c9de26ab0abaea8cee99ec3d0a5a752945384"
EXPECTED_CORE_SHA256 = "58622b646223bc95916bd9557b2683ab57290fdd7065401f2c91137b6b042e76"
EXPECTED_CORE_TEST_SHA256 = "e16061ce08065ee902a9ca665ab53e46c7f3300edc86cd6b86e6b98754125905"
EXPECTED_GATEWAY_SHA256 = "84cd27898af90ef9fc4efa3ecd5d901061253b3e816525bf8442a90a8ccb502f"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(value: dict[str, Any], omitted_key: str) -> str:
    payload = {key: item for key, item in value.items() if key != omitted_key}
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256_bytes(encoded)


def all_receipts(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        receipt
        for component in matrix["components"]
        for capability in component["producer_capabilities"]
        for receipt in capability["producer_receipts"]
    ]


def all_demands(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        demand
        for component in matrix["components"]
        for capability in component["consumer_requirements"]
        for demand in capability["demands"]
    ]


def edge_is_qualified(edge: dict[str, Any]) -> bool:
    scalar_keys = (
        "bridge_state",
        "time_alignment_state",
        "authority_state",
        "replay_state",
        "canonicality_state",
        "provenance_state",
        "resource_state",
    )
    return all(edge[key] in PASS_STATES for key in scalar_keys) and all(
        value in PASS_STATES for value in edge["dimension_states"].values()
    )


def semantic_errors(matrix: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    observations = {
        f"live-observation://{item['observation_id']}": item
        for item in matrix["live_observations"]
    }
    for ref, observation in observations.items():
        actual = canonical_sha256(observation, "observation_sha256")
        if actual != observation["observation_sha256"]:
            errors.append(f"observation hash mismatch: {ref}")

    sources: dict[str, str] = {}
    for component in matrix["components"]:
        for evidence in component["source_evidence"]:
            ref = evidence["source_ref"]
            declared = evidence["source_sha256"]
            prior = sources.setdefault(ref, declared)
            if prior != declared:
                errors.append(f"conflicting source hash: {ref}")
            if ref.startswith("live-observation://"):
                observation = observations.get(ref)
                if observation is None or observation["observation_sha256"] != declared:
                    errors.append(f"live observation source mismatch: {ref}")
            else:
                path = ROOT / ref
                if not path.is_file():
                    errors.append(f"missing source: {ref}")
                elif sha256_bytes(path.read_bytes()) != declared:
                    errors.append(f"file source hash mismatch: {ref}")

    for ref, observation in observations.items():
        sources[ref] = observation["observation_sha256"]
    manifest_lines = "".join(
        f"{ref}:{sources[ref]}\n" for ref in sorted(sources)
    ).encode("utf-8")
    if str(len(sources)) != matrix["snapshot"]["source_count_uint_dec"]:
        errors.append("source count mismatch")
    if sha256_bytes(manifest_lines) != matrix["snapshot"]["source_manifest_sha256"]:
        errors.append("source manifest aggregate mismatch")

    receipts = all_receipts(matrix)
    demands = all_demands(matrix)
    receipt_by_hash: dict[str, dict[str, Any]] = {}
    demand_by_hash: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        if canonical_sha256(receipt, "receipt_sha256") != receipt["receipt_sha256"]:
            errors.append(f"producer receipt hash mismatch: {receipt['receipt_id']}")
        receipt_by_hash[receipt["receipt_sha256"]] = receipt
    for demand in demands:
        if canonical_sha256(demand, "demand_sha256") != demand["demand_sha256"]:
            errors.append(f"demand hash mismatch: {demand['demand_id']}")
        demand_by_hash[demand["demand_sha256"]] = demand

    components = {item["component_id"]: item for item in matrix["components"]}
    for edge in matrix["dependency_edges"]:
        producer = components.get(edge["producer_component_id"])
        consumer = components.get(edge["consumer_component_id"])
        if producer is None or consumer is None:
            errors.append(f"dangling component edge: {edge['edge_id']}")
            continue
        receipt = receipt_by_hash.get(edge["producer_receipt_sha256"])
        demand = demand_by_hash.get(edge["demand_sha256"])
        if receipt is None or receipt["producer_component_id"] != producer["component_id"]:
            errors.append(f"producer receipt edge mismatch: {edge['edge_id']}")
        if demand is None or demand["consumer_component_id"] != consumer["component_id"]:
            errors.append(f"consumer demand edge mismatch: {edge['edge_id']}")
        if receipt is not None and receipt["receipt_id"] != edge["producer_output_receipt"]:
            errors.append(f"producer receipt id mismatch: {edge['edge_id']}")
        if demand is not None and demand["demand_id"] != edge["consumer_input_receipt"]:
            errors.append(f"consumer demand id mismatch: {edge['edge_id']}")

    nodes = {node["node_id"]: node for node in matrix["nodes"]}
    for node in nodes.values():
        observation = observations.get(node["observation_ref"])
        if observation is None or observation["observation_sha256"] != node["observation_receipt_sha256"]:
            errors.append(f"node observation mismatch: {node['node_id']}")
    for edge in matrix["node_edges"]:
        if edge["source_node_id"] not in nodes or edge["target_node_id"] not in nodes:
            errors.append(f"dangling node edge: {edge['node_edge_id']}")
    return errors


def scc_sets(matrix: dict[str, Any]) -> set[frozenset[str]]:
    ids = [component["component_id"] for component in matrix["components"]]
    adjacency = {item: [] for item in ids}
    for edge in matrix["dependency_edges"]:
        adjacency[edge["producer_component_id"]].append(edge["consumer_component_id"])

    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indexes: dict[str, int] = {}
    lows: dict[str, int] = {}
    found: set[frozenset[str]] = set()

    def visit(node: str) -> None:
        nonlocal index
        indexes[node] = lows[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in adjacency[node]:
            if target not in indexes:
                visit(target)
                lows[node] = min(lows[node], lows[target])
            elif target in on_stack:
                lows[node] = min(lows[node], indexes[target])
        if lows[node] == indexes[node]:
            members: list[str] = []
            while True:
                target = stack.pop()
                on_stack.remove(target)
                members.append(target)
                if target == node:
                    break
            if len(members) > 1 or node in adjacency[node]:
                found.add(frozenset(members))

    for node in ids:
        if node not in indexes:
            visit(node)
    return found


class MatrixContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(SCHEMA_PATH)
        cls.matrix = load_json(MATRIX_PATH)
        cls.validator = jsonschema.Draft202012Validator(cls.schema)

    def test_schema_is_draft_2020_12_valid(self) -> None:
        jsonschema.Draft202012Validator.check_schema(self.schema)

    def test_candidate_is_schema_valid_and_fail_closed(self) -> None:
        self.validator.validate(self.matrix)
        self.assertEqual(self.matrix["matrix_state"], "HOLD")
        self.assertEqual(self.matrix["closure_state"], "HOLD")
        self.assertTrue(self.matrix["no_live_mutation"])

    def test_only_governed_integration_states_are_used(self) -> None:
        self.assertEqual(set(self.matrix["state_lexicon"]), ALLOWED_STATES)

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    if key == "state" or (
                        key.endswith("_state") and key != "artifact_or_state"
                    ):
                        self.assertIn(item, ALLOWED_STATES, key)
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(self.matrix)

    def test_all_object_schemas_are_closed_and_numeric_contracts_are_strings(self) -> None:
        def walk(value: Any, pointer: str = "#") -> None:
            if isinstance(value, dict):
                if value.get("type") == "object":
                    self.assertIs(value.get("additionalProperties"), False, pointer)
                declared_type = value.get("type")
                declared_types = declared_type if isinstance(declared_type, list) else [declared_type]
                self.assertNotIn("integer", declared_types, pointer)
                self.assertNotIn("number", declared_types, pointer)
                for key, item in value.items():
                    walk(item, f"{pointer}/{key}")
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    walk(item, f"{pointer}/{index}")

        walk(self.schema)

    def test_semantic_hash_and_reference_closure(self) -> None:
        self.assertEqual(semantic_errors(self.matrix), [])

    def test_fixed_core_and_v1_are_unchanged(self) -> None:
        self.assertEqual(
            sha256_bytes((ROOT / "tools/total_field/moving_v_route_cleanup_candidate_v2.py").read_bytes()),
            EXPECTED_CORE_SHA256,
        )
        self.assertEqual(
            sha256_bytes((ROOT / "tests/test_w7tp_moving_v_route_cleanup_v2.py").read_bytes()),
            EXPECTED_CORE_TEST_SHA256,
        )
        self.assertEqual(sha256_bytes(V1_PATH.read_bytes()), EXPECTED_V1_SHA256)
        self.assertEqual(
            sha256_bytes((ROOT / "legacy_core/taiji_unified_gateway_edge.py").read_bytes()),
            EXPECTED_GATEWAY_SHA256,
        )

    def test_typed_orphan_and_unsatisfied_sets_are_machine_recomputed(self) -> None:
        receipt_hashes = {item["receipt_sha256"] for item in all_receipts(self.matrix)}
        demand_hashes = {item["demand_sha256"] for item in all_demands(self.matrix)}
        referenced_receipts = {
            edge["producer_receipt_sha256"] for edge in self.matrix["dependency_edges"]
        }
        edges_by_demand = {
            demand_hash: [
                edge for edge in self.matrix["dependency_edges"]
                if edge["demand_sha256"] == demand_hash
            ]
            for demand_hash in demand_hashes
        }
        expected_orphans = receipt_hashes - referenced_receipts
        expected_unsatisfied = {
            demand_hash for demand_hash, edges in edges_by_demand.items()
            if not any(edge_is_qualified(edge) for edge in edges)
        }
        self.assertEqual(
            {item["producer_receipt_sha256"] for item in self.matrix["orphan_supplies"]},
            expected_orphans,
        )
        self.assertEqual(
            {item["demand_sha256"] for item in self.matrix["unsatisfied_demands"]},
            expected_unsatisfied,
        )

    def test_cycles_single_points_restart_and_partition_are_typed(self) -> None:
        self.assertEqual(
            {frozenset(item["subject_ids"]) for item in self.matrix["cycles"]},
            scc_sets(self.matrix),
        )
        demands = {item["demand_sha256"]: item for item in all_demands(self.matrix)}
        edges_by_demand = {
            demand_hash: [
                edge for edge in self.matrix["dependency_edges"]
                if edge["demand_sha256"] == demand_hash
            ]
            for demand_hash in demands
        }
        expected_spof_demands = {
            demand_hash
            for demand_hash, demand in demands.items()
            if demand["criticality"] == "SYSTEM_CRITICAL"
            and len(edges_by_demand[demand_hash]) == 1
        }
        actual_spof_demands = {
            item["demand_sha256"] for item in self.matrix["single_points"]
            if item["demand_sha256"] is not None
        }
        self.assertEqual(actual_spof_demands, expected_spof_demands)

        expected_partition_demands = {
            demand_hash
            for demand_hash, demand in demands.items()
            if demand["partition_constraint"] == "MUST_REMAIN_SAFE_UNDER_PARTITION"
            and not any(edge_is_qualified(edge) for edge in edges_by_demand[demand_hash])
        }
        actual_partition_demands = {
            item["demand_sha256"] for item in self.matrix["partition_findings"]
            if item["demand_sha256"] is not None
        }
        self.assertEqual(actual_partition_demands, expected_partition_demands)

        components = {item["component_id"]: item for item in self.matrix["components"]}
        expected_restart_demands: set[str] = set()
        for demand_hash, demand in demands.items():
            if demand["restart_constraint"] != "MUST_SURVIVE_RESTART":
                continue
            durable = False
            for edge in edges_by_demand[demand_hash]:
                producer = components[edge["producer_component_id"]]
                capability = producer["producer_capabilities"][0]
                durable = durable or (
                    edge_is_qualified(edge)
                    and capability["durability"]
                    in {"RESTART_PERSISTENT", "APPEND_ONLY_EVIDENCE", "STATIC_SOURCE"}
                )
            if not durable:
                expected_restart_demands.add(demand_hash)
        actual_restart_demands = {
            item["demand_sha256"] for item in self.matrix["restart_findings"]
            if item["demand_sha256"] is not None
        }
        self.assertEqual(actual_restart_demands, expected_restart_demands)

    def test_router_dlq_anti_replay_exact_binding_and_precommit_gate(self) -> None:
        receipt = next(
            item for item in all_receipts(self.matrix)
            if item["capability_id"] == "router_dlq.anti_replay_receipt"
        )
        binding = receipt["anti_replay_binding"]
        expected = {
            "nonce",
            "payload_sha256",
            "router_id",
            "router_epoch_uint_dec",
            "router_boot_id",
            "issued_at_ns",
            "expires_at_ns",
            "ledger_sequence_uint_dec",
            "dlq_record_sha256",
            "delivery_id",
            "attempt_uint_dec",
            "retry_of_delivery_id",
            "route_decision",
            "route_proof_sha256",
            "policy_epoch_uint_dec",
            "decision_token_sha256",
            "outcome",
            "authority_signature_sha256",
            "previous_ledger_sha256",
            "ledger_ref",
            "ledger_persistence",
            "atomic_insert_result",
            "binding_result",
        }
        self.assertEqual(set(binding), expected)
        self.assertEqual(binding["binding_result"], "HOLD")
        self.assertEqual(binding["ledger_persistence"], "NOT_PROVEN")

        moving_v = next(
            item for item in self.matrix["components"]
            if item["component_id"] == "moving_v_candidate_runtime"
        )
        for demand in moving_v["consumer_requirements"][0]["demands"]:
            self.assertTrue(all(demand["anti_replay_constraints"].values()))
            self.assertTrue(demand["commit_gate"]["must_be_pass_before_commit"])
            self.assertEqual(demand["commit_gate"]["required_outcome"], "PASS")

    def test_live_gateway_and_local_model_route_remain_hold(self) -> None:
        finding_ids = {item["finding_id"] for item in self.matrix["global_findings"]}
        self.assertIn("FINDING_LIVE_GATEWAY_HOLD", finding_ids)
        self.assertIn("FINDING_MODEL_SUPPLY_DEMAND_ENDPOINT_MISMATCH", finding_ids)
        self.assertIn("FINDING_LOCAL_MODEL_ROUTE_DEFAULT_BINDING_UNSATISFIED", finding_ids)
        self.assertIn("FINDING_LEGACY_SHELL_REPLAY_DISABLED_PENDING_PROOF", finding_ids)
        self.assertIn("shell=True", (ROOT / "runtime/deadletter_replay.py").read_text(encoding="utf-8"))

        local_edge = next(
            item for item in self.matrix["dependency_edges"]
            if item["edge_id"] == "taiji8d_local_supply_to_codex_default"
        )
        self.assertEqual(local_edge["bridge_state"], "HOLD")
        self.assertIn(
            local_edge["demand_sha256"],
            {item["demand_sha256"] for item in self.matrix["unsatisfied_demands"]},
        )
        supply_receipt = next(
            item for item in all_receipts(self.matrix)
            if item["capability_id"] == "taiji8d.local_model_route_supply"
        )
        self.assertEqual(supply_receipt["resource"]["capacity_uint_dec"], "2147483648")
        self.assertEqual(supply_receipt["resource"]["ownership"], "UNBOUND")

    def test_vpn_roles_and_cross_node_receipts_fail_closed(self) -> None:
        nodes = {item["node_id"]: item for item in self.matrix["nodes"]}
        self.assertEqual(nodes["msi-win11"]["tailscale_run_ssh"], "DISABLED")
        self.assertFalse(nodes["msi-win11"]["ssh_server_demand"])
        self.assertEqual(nodes["msi-wsl"]["tailscale_run_ssh"], "ENABLED")
        self.assertEqual(nodes["taiji01"]["passwordless_ssh_result"], "PASS")
        self.assertEqual(nodes["penguin"]["passwordless_ssh_result"], "DENIED_BY_TAILNET_POLICY")
        self.assertEqual(nodes["taiji03-linux"]["passwordless_ssh_result"], "CONNECTION_REFUSED")
        for node in nodes.values():
            if node["platform"] in {"ANDROID", "IOS"}:
                self.assertEqual(node["operational_role"], "APPROVAL_INPUT_ONLY")
                self.assertFalse(node["ssh_server_demand"])
        for edge in self.matrix["node_edges"]:
            if edge["critical_cross_node"]:
                self.assertEqual(edge["node_edge_state"], "HOLD")
                self.assertIsNone(edge["durability_receipt_ref"])
                self.assertIsNone(edge["replay_receipt_ref"])
                self.assertIsNone(edge["partition_receipt_ref"])

    def test_policy_instance_is_valid_but_source_config_is_not_same_namespace(self) -> None:
        policy_schema = load_json(POLICY_SCHEMA_PATH)
        instance = load_json(POLICY_INSTANCE_PATH)
        source = load_json(POLICY_SOURCE_PATH)
        validator = jsonschema.Draft202012Validator(policy_schema)
        validator.validate(instance)
        self.assertFalse(validator.is_valid(source))

        provenance = instance["instance_provenance"]
        binding_payload = {
            "source_contract_ref": provenance["source_contract_ref"],
            "source_contract_sha256": provenance["source_contract_sha256"],
            "source_scope": provenance["source_scope"],
            "mapping_version": provenance["mapping_version"],
            "mappings": provenance["mappings"],
        }
        actual = sha256_bytes(
            json.dumps(
                binding_payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        )
        self.assertEqual(actual, provenance["binding_sha256"])
        self.assertEqual(
            provenance["source_contract_sha256"],
            sha256_bytes(POLICY_SOURCE_PATH.read_bytes()),
        )

    def test_negative_illegal_state_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.matrix)
        candidate["components"][0]["component_state"] = "SATISFIED_VERIFIED"
        self.assertFalse(self.validator.is_valid(candidate))

    def test_negative_missing_structured_receipt_field_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.matrix)
        del candidate["components"][0]["producer_capabilities"][0]["producer_receipts"][0]["producer_version"]
        self.assertFalse(self.validator.is_valid(candidate))

    def test_negative_anti_replay_pass_without_durable_atomic_proof_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.matrix)
        receipt = next(
            item for item in all_receipts(candidate)
            if item["capability_id"] == "router_dlq.anti_replay_receipt"
        )
        receipt["anti_replay_binding"]["binding_result"] = "PASS"
        receipt["anti_replay_binding"]["outcome"] = "PASS"
        receipt["anti_replay_binding"]["ledger_persistence"] = "NOT_PROVEN"
        receipt["anti_replay_binding"]["atomic_insert_result"] = "NOT_PROVEN"
        self.assertFalse(self.validator.is_valid(candidate))

    def test_negative_verified_adapter_without_receipt_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.matrix)
        edge = next(
            item for item in candidate["dependency_edges"]
            if item["bridge_state"] == "VERIFIED_ADAPTER"
        )
        edge["adapter_receipt_ref"] = None
        edge["adapter_receipt_sha256"] = None
        self.assertFalse(self.validator.is_valid(candidate))

    def test_negative_critical_node_pass_without_cross_node_receipts_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.matrix)
        edge = next(item for item in candidate["node_edges"] if item["critical_cross_node"])
        edge["node_edge_state"] = "DIRECT_NATIVE"
        self.assertFalse(self.validator.is_valid(candidate))

    def test_negative_mobile_ssh_server_demand_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.matrix)
        node = next(item for item in candidate["nodes"] if item["platform"] == "ANDROID")
        node["ssh_server_demand"] = True
        self.assertFalse(self.validator.is_valid(candidate))

    def test_negative_hash_tamper_and_dangling_edge_are_semantically_rejected(self) -> None:
        receipt_tamper = copy.deepcopy(self.matrix)
        all_receipts(receipt_tamper)[0]["payload_sha256"] = "f" * 64
        self.assertTrue(any("producer receipt hash mismatch" in item for item in semantic_errors(receipt_tamper)))

        demand_tamper = copy.deepcopy(self.matrix)
        all_demands(demand_tamper)[0]["ttl_ns"] = "1"
        self.assertTrue(any("demand hash mismatch" in item for item in semantic_errors(demand_tamper)))

        dangling = copy.deepcopy(self.matrix)
        dangling["dependency_edges"][0]["consumer_component_id"] = "missing_component"
        self.assertTrue(any("dangling component edge" in item for item in semantic_errors(dangling)))

    def test_negative_policy_binding_tamper_is_detected(self) -> None:
        instance = load_json(POLICY_INSTANCE_PATH)
        provenance = instance["instance_provenance"]
        tampered = copy.deepcopy(provenance["mappings"])
        tampered[0]["note"] += " tampered"
        binding_payload = {
            "source_contract_ref": provenance["source_contract_ref"],
            "source_contract_sha256": provenance["source_contract_sha256"],
            "source_scope": provenance["source_scope"],
            "mapping_version": provenance["mapping_version"],
            "mappings": tampered,
        }
        actual = sha256_bytes(
            json.dumps(
                binding_payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        )
        self.assertNotEqual(actual, provenance["binding_sha256"])


if __name__ == "__main__":
    unittest.main()
