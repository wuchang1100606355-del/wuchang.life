from __future__ import annotations

import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from tools.total_field_dynamic_context import (
    build_local_llm_working_memory_projection,
    build_total_field_capability_requirement_packet,
    canonical_sha256,
    classify_total_field_task,
    normalize_capability_missing_report,
    normalize_local_llm_result,
    route_sensitive_information,
    run_total_field_capability_completion,
    select_smallest_sufficient_memory_set,
    verify_completion_candidate,
)
from tools.total_field_receive_candidate_authority_adapter import (
    build_total_field_operation_packet,
    validate_total_field_operation_packet,
)


NOW = datetime(2026, 8, 21, 19, 0, tzinfo=timezone.utc)
NOW_TEXT = NOW.isoformat().replace("+00:00", "Z")
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


class TotalFieldFounderIntentDeltaTests(unittest.TestCase):
    def report(self) -> dict[str, object]:
        return {
            "task_id": "task-001",
            "receiver_id": "local-llm-001",
            "receiver_version": "1",
            "current_intent_ref": "intent:w7tp:completion",
            "missing_capability_id": "capability:exact-transform",
            "missing_input_class": "DEIDENTIFIED_TECHNICAL",
            "missing_schema_version": "1.0",
            "missing_lookup_resource": "schemas/exact-transform.json",
            "missing_verification_capability": "verify:exact-transform",
            "current_available_capabilities": ["capability:reason"],
            "current_context_refs": ["state:current"],
            "evidence": ["evidence:gap:001"],
        }

    def run_loop(self, local, cloud, target=None):
        return run_total_field_capability_completion(
            self.report(),
            target_native_provider=target,
            local_provider=local,
            cloud_provider=cloud,
            target_base_state={"sha256": HASH_B},
            reusable_capability_refs=["tools/total_field_dynamic_context.py"],
            created_at=NOW_TEXT,
        )

    def candidate(self, request_hash: str, **updates) -> dict[str, object]:
        value: dict[str, object] = {
            "schema_id": "W7TP_COMPLETION_CANDIDATE_PACKET_V1",
            "request_packet_sha256": request_hash,
            "candidate_only": True,
            "provider_authority": False,
            "unresolved_required_effects": [],
            "forbidden_effects": [],
            "capability_id": "capability:exact-transform",
            "object_refs": ["CAPABILITY_OBJECT"],
            "output_hashes": {"tools/exact_transform.py": HASH_A},
            "reused_objects": ["TARGET_NATIVE_RECONSTRUCTION_BASE"],
        }
        value.update(updates)
        value["candidate_sha256"] = canonical_sha256(value)
        return value

    def requirement(self) -> dict[str, object]:
        return build_total_field_capability_requirement_packet(
            normalize_capability_missing_report(self.report()),
            target_base_state={"sha256": HASH_B},
            reusable_capability_refs=["tools/total_field_dynamic_context.py"],
            created_at=NOW_TEXT,
        )

    def adi_objects(self) -> list[dict[str, object]]:
        return [
            {
                "object_id": "CAPABILITY_OBJECT",
                "coordinate": "schemas/capability-object.json",
                "sha256": HASH_A,
                "state": "QUALIFIED_CANDIDATE",
                "lineage_ref": "lineage:capability-object",
                "evidence_ref": "evidence:capability-object",
                "capability_ref": "capability:exact-transform",
                "dependencies": ["SCHEMA_OBJECT"],
                "consumers": ["local-llm-001", "local-llm-002"],
            },
            {
                "object_id": "SCHEMA_OBJECT",
                "coordinate": "schemas/exact-transform.json",
                "sha256": HASH_B,
                "state": "VERIFIED",
                "lineage_ref": "lineage:schema-object",
                "evidence_ref": "evidence:schema-object",
                "dependencies": [],
                "consumers": ["local-llm-001", "local-llm-002"],
            },
            {
                "object_id": "UNRELATED_OBJECT",
                "coordinate": "schemas/unrelated.json",
                "sha256": HASH_C,
                "state": "VERIFIED",
                "lineage_ref": "lineage:unrelated",
                "evidence_ref": "evidence:unrelated",
                "dependencies": [],
                "consumers": ["local-llm-001"],
            },
        ]

    def projection(self, qualified, memory_set, receiver="local-llm-001"):
        return build_local_llm_working_memory_projection(
            intent_ref="intent:w7tp:completion",
            current_state_ref="state:current",
            required_capability_id="capability:exact-transform",
            qualified_capability_packet=qualified,
            smallest_memory_set=memory_set,
            receiver_id=receiver,
            receiver_capability_boundary=["capability:exact-transform"],
            allowed_actions=["REASON", "PROPOSE"],
            forbidden_actions=["EXECUTE", "WRITE", "RESTART"],
            verification_procedure=["VERIFY_HASH", "VERIFY_RECEIVER"],
            stop_conditions=["HASH_MISMATCH", "TTL_EXPIRED"],
            context_ttl_seconds=300,
        )

    def test_case_01_local_can_complete_no_cloud(self):
        cloud_calls = []
        result = self.run_loop(
            lambda _: {"state": "CAPABILITY_AVAILABLE", "provider": "LOCAL_LLM"},
            lambda request: cloud_calls.append(request) or {},
            lambda _: {"state": "CAPABILITY_MISSING"},
        )
        self.assertEqual(result["state"], "QUALIFIED_LOCAL")
        self.assertEqual(result["cloud_calls"], 0)
        self.assertEqual(cloud_calls, [])

    def test_case_02_local_gap_cloud_pass_adi_projection_local_use(self):
        result = self.run_loop(
            lambda _: {"state": "CAPABILITY_MISSING"},
            lambda request: self.candidate(request["packet_sha256"]),
        )
        qualified = result["qualified_capability_packet"]
        memory = select_smallest_sufficient_memory_set(
            intent_ref="intent:w7tp:completion",
            qualified_capability_packet=qualified,
            current_task_state={"required_object_ids": []},
            adi_objects=self.adi_objects(),
            receiver_id="local-llm-001",
        )
        projection = self.projection(qualified, memory)
        self.assertEqual(result["state"], "QUALIFIED")
        self.assertEqual(projection["object_refs"], ["CAPABILITY_OBJECT", "SCHEMA_OBJECT"])

    def test_case_03_bad_first_candidate_second_repairs_only(self):
        original_request_hash = []
        calls = []

        def cloud(request):
            calls.append(deepcopy(request))
            if not original_request_hash:
                original_request_hash.append(request["packet_sha256"])
                return self.candidate(request["packet_sha256"], capability_id="wrong-capability")
            return self.candidate(original_request_hash[0])

        result = self.run_loop(lambda _: {"state": "CAPABILITY_MISSING"}, cloud)
        self.assertEqual(result["state"], "QUALIFIED")
        self.assertEqual(result["cloud_calls"], 2)
        self.assertEqual(calls[1]["schema_id"], "W7TP_TOTAL_FIELD_REJECTION_DELTA_PACKET_V1")
        self.assertEqual(result["rejection_deltas"][0]["next_minimum_delta"], ["capability:exact-transform"])
        self.assertEqual(result["rejection_deltas"][0]["preserved_accepted_objects"], ["TARGET_NATIVE_RECONSTRUCTION_BASE"])

    def test_case_04_cloud_operation_command_has_no_authority(self):
        decisions = []

        def cloud(request):
            candidate = self.candidate(
                request["packet_sha256"],
                operation_command="restart",
                operation_authority=True,
                provider_authority=True,
                promoted=True,
                canonical=True,
            )
            decisions.append(verify_completion_candidate(candidate, request, now=NOW))
            return candidate

        result = self.run_loop(lambda _: {"state": "CAPABILITY_MISSING"}, cloud)
        self.assertEqual(result["state"], "STOPPED_NON_CONVERGENCE")
        predicates = {item["predicate"] for item in decisions[0]["failures"]}
        self.assertIn("OPERATION_COMMAND_ABSENT", predicates)
        self.assertIn("PROVIDER_AUTHORITY_FALSE", predicates)
        self.assertIn("OPERATION_AUTHORITY_FALSE", predicates)
        self.assertIn("SELF_PROMOTION_FORBIDDEN", predicates)
        self.assertIn("SELF_CANONICALIZATION_FORBIDDEN", predicates)

    def test_case_05_local_restart_write_is_only_operation_proposal(self):
        result = normalize_local_llm_result(
            {
                "result_ref": "result:001",
                "result_sha256": HASH_A,
                "reasoning_result": "proposal only",
                "proposed_actions": ["RESTART", "WRITE"],
            }
        )
        self.assertFalse(result["operation_authority"])
        self.assertIsNone(result["operation_command"])
        self.assertFalse(result["operation_proposal"]["operation_authority"])

    def operation_proposal(self) -> dict[str, object]:
        return {
            "schema_id": "W7TP_OPERATION_PROPOSAL_V1",
            "operation_id": "op-001",
            "intent_ref": "intent:w7tp:completion",
            "target_node": "taiji01",
            "object_id": "CAPABILITY_OBJECT",
            "exact_coordinate": "runtime/candidate/CAPABILITY_OBJECT.json",
            "current_state_hash": HASH_A,
            "input_hashes": {"candidate": HASH_B},
            "authorized_action": "CREATE_CANDIDATE_ONLY",
            "authorized_steps": ["CREATE", "VERIFY"],
            "maximum_effect": "ONE_NEW_CANDIDATE_FILE",
            "forbidden_effects": ["DEPLOY", "RESTART", "CANONICAL_MUTATION"],
            "expected_effect": "CANDIDATE_FILE_EXISTS",
            "rollback": "REMOVE_NEW_UNREFERENCED_CANDIDATE",
            "evidence_refs": ["evidence:review:001"],
            "candidate_only": True,
            "operation_authority": False,
        }

    def test_case_06_no_operation_packet_executor_fails_closed(self):
        blocked = validate_total_field_operation_packet(None, now=NOW)
        authority = {
            "schema_id": "W7TP_VERIFIED_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLUTION_V1",
            "authority_resolution_sha256": HASH_C,
        }
        packet = build_total_field_operation_packet(
            self.operation_proposal(), verified_authority_ref=authority, issued_at=NOW_TEXT, ttl_seconds=60
        )
        passed = validate_total_field_operation_packet(packet, now=NOW + timedelta(seconds=1))
        forged = deepcopy(packet)
        forged["authorized_action"] = "DEPLOY"
        expired = validate_total_field_operation_packet(packet, now=NOW + timedelta(seconds=60))
        self.assertFalse(blocked["executor_authorized"])
        self.assertTrue(passed["executor_authorized"])
        self.assertFalse(validate_total_field_operation_packet(forged, now=NOW)["executor_authorized"])
        self.assertFalse(expired["executor_authorized"])

    def test_case_07_business_secret_cloud_plaintext_blocked(self):
        route = route_sensitive_information({"data_class": "BUSINESS_SECRET", "d8_ref": "d8:001"})
        self.assertFalse(route["cloud_plaintext_allowed"])
        self.assertEqual(route["route"], "CLOUD_PLAINTEXT_FORBIDDEN")

    def test_case_08_credential_secret_model_context_blocked(self):
        route = route_sensitive_information({"data_class": "CREDENTIAL_SECRET", "d8_ref": "d8:002"})
        self.assertFalse(route["model_context_allowed"])
        self.assertEqual(route["route"], "MODEL_CONTEXT_FORBIDDEN")

    def test_case_09_unknown_is_local_only_fail_closed(self):
        route = route_sensitive_information({"data_class": "UNCLASSIFIED"})
        self.assertEqual(route["data_class"], "UNKNOWN")
        self.assertEqual(route["route"], "FAIL_CLOSED_LOCAL_ONLY")

    def qualified_packet(self) -> dict[str, object]:
        packet = {
            "schema_id": "W7TP_QUALIFIED_CAPABILITY_PACKET_V1",
            "qualified": True,
            "object_refs": ["CAPABILITY_OBJECT"],
            "capability_id": "capability:exact-transform",
        }
        packet["packet_sha256"] = canonical_sha256(packet)
        return packet

    def test_case_10_projection_contains_only_smallest_set(self):
        memory = select_smallest_sufficient_memory_set(
            intent_ref="intent:w7tp:completion",
            qualified_capability_packet=self.qualified_packet(),
            current_task_state={"required_object_ids": []},
            adi_objects=self.adi_objects(),
            receiver_id="local-llm-001",
        )
        self.assertEqual([item["object_id"] for item in memory["selected_objects"]], ["CAPABILITY_OBJECT", "SCHEMA_OBJECT"])
        self.assertEqual(memory["excluded_object_count"], 1)

    def test_case_11_unrelated_adi_memory_excluded_and_spoofed_path_rejected(self):
        objects = self.adi_objects()
        memory = select_smallest_sufficient_memory_set(
            intent_ref="intent:w7tp:completion",
            qualified_capability_packet=self.qualified_packet(),
            current_task_state={"required_object_ids": []},
            adi_objects=objects,
            receiver_id="local-llm-001",
        )
        self.assertNotIn("UNRELATED_OBJECT", {item["object_id"] for item in memory["selected_objects"]})
        objects[2]["coordinate"] = "../spoofed.json"
        with self.assertRaisesRegex(ValueError, "ADI_OBJECT_COORDINATE_INVALID"):
            select_smallest_sufficient_memory_set(
                intent_ref="intent:w7tp:completion",
                qualified_capability_packet=self.qualified_packet(),
                current_task_state={"required_object_ids": []},
                adi_objects=objects,
                receiver_id="local-llm-001",
            )

    def test_case_12_same_packet_projects_to_compatible_receiver_without_mutation(self):
        qualified = self.qualified_packet()
        original = canonical_sha256(qualified)
        projections = []
        for receiver in ("local-llm-001", "local-llm-002"):
            memory = select_smallest_sufficient_memory_set(
                intent_ref="intent:w7tp:completion",
                qualified_capability_packet=qualified,
                current_task_state={"required_object_ids": []},
                adi_objects=self.adi_objects(),
                receiver_id=receiver,
            )
            projections.append(self.projection(qualified, memory, receiver))
        self.assertEqual(canonical_sha256(qualified), original)
        self.assertEqual(projections[0]["qualified_capability_ref"], projections[1]["qualified_capability_ref"])
        with self.assertRaisesRegex(ValueError, "ADI_RECEIVER_INCOMPATIBLE"):
            select_smallest_sufficient_memory_set(
                intent_ref="intent:w7tp:completion",
                qualified_capability_packet=qualified,
                current_task_state={"required_object_ids": []},
                adi_objects=self.adi_objects(),
                receiver_id="local-llm-incompatible",
            )

    def test_case_13_high_confidence_cannot_override_exact_failure(self):
        request = self.requirement()
        candidate = self.candidate(HASH_B, model_confidence=0.999999)
        decision = verify_completion_candidate(candidate, request, now=NOW + timedelta(seconds=901))
        self.assertEqual(decision["state"], "REJECTED")
        predicates = {item["predicate"] for item in decision["failures"]}
        self.assertIn("REQUEST_HASH_EXACT", predicates)
        self.assertIn("REQUIREMENT_TTL_ACTIVE", predicates)
        self.assertEqual(classify_total_field_task(capability_gap=True), "CAPABILITY_TASK")

    def test_case_14_all_exact_predicates_pass_unresolved_empty(self):
        request = self.requirement()
        decision = verify_completion_candidate(
            self.candidate(request["packet_sha256"]), request, now=NOW
        )
        self.assertEqual(decision["state"], "QUALIFIED")
        self.assertEqual(decision["failures"], [])
        self.assertTrue(decision["qualified_capability_packet"]["qualified"])
        self.assertFalse(decision["qualified_capability_packet"]["operation_authority"])


if __name__ == "__main__":
    unittest.main()
