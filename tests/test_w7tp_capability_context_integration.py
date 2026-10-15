"""Regression tests for bounded capability-to-context handoff; no live effects."""
from __future__ import annotations
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from core.capability_internalization import (
    ROOT, REQUIRED_CLASSES, CapabilityInternalizationError,
    build_capability_context_projection, validate_capability_context_projection,
    load_internalization_registry,
)
from tools.total_field_dynamic_context_pull import (
    DynamicContextPullHold, validate_model_visible_context,
)


def rehash(value):
    value.pop("projection_sha256", None)
    value["projection_sha256"] = hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()).hexdigest()
    return value


class CapabilityContextIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.task = {"TASK_ID": "T-TEST-CAPABILITY-HANDOFF", "STATE": "DOING",
                     "DEPENDENCIES": [], "REQUIRED_CAPABILITY_IDS": ["CAP_INTERNAL_DYNAMIC_CONTEXT_V1"]}
        self.projection = build_capability_context_projection(self.task)

    def context(self, projection=None):
        p = copy.deepcopy(projection or self.projection)
        return {"context_ref": "context:test:capability-handoff",
                "state_projection": {"task": {"task_ref": p["task_ref"]}, "capability_context": p},
                "evidence_refs": [], "capability_refs": [r["capability_ref"] for r in p["catalogue"]],
                "acceptance_conditions": [], "schema_refs": [], "interface_refs": [],
                "non_core_rule_capsule_refs": []}

    def test_all_existing_classes_retained_without_runtime_promotion(self):
        p = self.projection
        self.assertEqual(len(p["catalogue"]), 8)
        self.assertEqual({r["capability_class"] for r in p["catalogue"]}, REQUIRED_CLASSES)
        self.assertFalse(p["coverage"]["all_technologies_complete"])
        self.assertTrue(all(r["runtime_readiness"] == "NOT_REOBSERVED" for r in p["catalogue"]))
        self.assertTrue(all(r["effect_authorization"] == "NOT_GRANTED_BY_CONTEXT" for r in p["catalogue"]))

    def test_declared_dependency_is_included(self):
        self.assertIn("CAP_INTERNAL_ORIGIN_CELL_V1", self.projection["required_capability_ids"])
        self.assertEqual(self.projection["missing_required_capability_ids"], [])

    def test_nvr_status_and_authority_are_preserved(self):
        r = next(r for r in self.projection["catalogue"] if r["capability_class"] == "NVR_READ")
        self.assertEqual(r["registered_status"], "IMPLEMENTED_SOURCE_COMPATIBILITY_TRANSPORT")
        self.assertEqual(r["effect_policy"], "READ_ONLY")
        self.assertEqual(r["effect_authorization"], "NOT_GRANTED_BY_CONTEXT")

    def test_current_v23_frame_is_read_not_v22_mapped(self):
        f = self.projection["system_frame"]
        self.assertEqual(f["version"], "2.3")
        self.assertEqual(f["dimensions"]["D1"], "Intent")
        self.assertEqual(f["dimensions"]["D6"], "Generative State Transmission")
        self.assertEqual(f["semantics"], "8_IN_1_SINGLE_DYNAMIC_STATE_FIELD")

    def test_external_indices_are_not_falsely_counted_complete(self):
        self.assertEqual(len(self.projection["source_index_refs"]), 5)
        self.assertEqual(self.projection["coverage"]["external_index_contents"],
                         "DECLARED_IDENTIFIERS_ONLY_NO_RULE_BODY_OR_AUTHORITY")
        # Check exact source identifiers, not an assumed total count.
        source_ids = {x["ref"]: {v["id"] for v in x["entries"]}
                      for x in self.projection["source_index_refs"]}
        rules = {"TAU_F", "DIRECT_SLOT_F", "METRIC_SIGNATURE_F", "X_F", "B_PLUS", "B_MINUS",
                 "SIGMA_F", "TRANSITION_STEP_COST", "THETA_F", "DELTA_F", "PHI_F",
                 "SPIRAL_SHELL_FORMATION", "OMEGA_F", "SPIRAL_STOP_CONDITION",
                 "EVIDENCE_CLOSURE", "UNIQUE_FIXED_POINT", "STATE8D_ADI_IO"}
        self.assertEqual(source_ids["docs/adi_native/NATIVE_ADI_SOURCE_RULE_MATRIX.md"], rules)
        skills = json.loads((ROOT / "capabilities/W7TP_NATIVE_SKILLS_INDEX.json").read_text())["skills"]
        self.assertEqual(source_ids["capabilities/W7TP_NATIVE_SKILLS_INDEX.json"], set(skills))
        cloud = json.loads((ROOT / "runtime/total_field/secondary_cloud/capability_registry.json").read_text())["capabilities"]
        self.assertEqual(source_ids["runtime/total_field/secondary_cloud/capability_registry.json"],
                         {r["capability_ref"] for r in cloud})
        self.assertIn("core/resource_arbitration.py", self.projection["coverage"]["unexpanded_index_refs"])

    def test_same_task_source_has_deterministic_projection(self):
        self.assertEqual(self.projection, build_capability_context_projection(self.task))

    def test_required_unknown_stops_only_dependent_model_context(self):
        t = copy.deepcopy(self.task); t["REQUIRED_CAPABILITY_IDS"] = ["CAP_INTERNAL_UNKNOWN_V1"]
        p = build_capability_context_projection(t)
        self.assertEqual(p["state"], "HOLD_REQUIRED_CAPABILITY_UNRESOLVED")
        with self.assertRaisesRegex(DynamicContextPullHold, "HOLD_CONTEXT_REQUIRED_CAPABILITY_MISSING"):
            validate_model_visible_context(self.context(p))
        validate_model_visible_context(self.context())

    def test_context_reference_omission_is_rejected(self):
        c = self.context(); c["capability_refs"].pop()
        with self.assertRaisesRegex(DynamicContextPullHold, "REFERENCE_OMITTED"):
            validate_model_visible_context(c)

    def test_wrong_task_is_rejected(self):
        c = self.context(); c["state_projection"]["task"]["task_ref"] = "task:T-028"
        with self.assertRaisesRegex(DynamicContextPullHold, "TASK_MISMATCH"):
            validate_model_visible_context(c)

    def test_inventory_removal_cannot_be_hidden_by_rehash(self):
        p = copy.deepcopy(self.projection); p["catalogue"].pop(); p["catalogue_count"] -= 1; rehash(p)
        with self.assertRaisesRegex(CapabilityInternalizationError, "CATALOGUE_INCOMPLETE"):
            validate_capability_context_projection(p, task_ref=p["task_ref"])

    def test_forged_complete_all_technologies_is_rejected(self):
        p = copy.deepcopy(self.projection); p["coverage"]["all_technologies_complete"] = True; rehash(p)
        with self.assertRaisesRegex(CapabilityInternalizationError, "COVERAGE_OVERCLAIM"):
            validate_capability_context_projection(p, task_ref=p["task_ref"])

    def test_forged_model_authority_is_rejected(self):
        p = copy.deepcopy(self.projection); p["system_frame"]["provider_authority"] = True; rehash(p)
        with self.assertRaisesRegex(CapabilityInternalizationError, "AUTHORITY_ESCALATION"):
            validate_capability_context_projection(p, task_ref=p["task_ref"])

    def test_source_binding_tamper_is_rejected(self):
        p = copy.deepcopy(self.projection); p["source_bindings"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(CapabilityInternalizationError, "HASH_MISMATCH"):
            validate_capability_context_projection(p, task_ref=p["task_ref"])

    def test_missing_inventory_is_not_silent_legacy_fallback(self):
        c = self.context(); del c["state_projection"]["capability_context"]
        with self.assertRaisesRegex(DynamicContextPullHold, "INVENTORY_MISSING"):
            validate_model_visible_context(c)

    def test_undeclared_schema_class_still_rejected(self):
        registry = load_internalization_registry()
        registry["capabilities"][0]["capability_class"] = "UNAPPROVED"
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "registry.json"; p.write_text(json.dumps(registry))
            with self.assertRaisesRegex(CapabilityInternalizationError, "SCHEMA_INVALID"):
                load_internalization_registry(p)

    def test_dependency_cycle_and_missing_target_rejected(self):
        registry = load_internalization_registry()
        for dep in ["CAP_INTERNAL_UNKNOWN_V1", "CAP_INTERNAL_DYNAMIC_CONTEXT_V1"]:
            r = copy.deepcopy(registry)
            row = next(x for x in r["capabilities"] if x["capability_id"] == "CAP_INTERNAL_ORIGIN_CELL_V1")
            row["requires_capability_ids"] = [dep]
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / "registry.json"; p.write_text(json.dumps(r))
                with self.assertRaisesRegex(CapabilityInternalizationError, "DEPENDENCY_"):
                    load_internalization_registry(p)

    def test_existing_pointer_only_context_stays_compatible(self):
        c = {"context_ref": "context:test:fixture", "state_projection": {"fixture": True},
             "evidence_refs": [], "capability_refs": [], "acceptance_conditions": [],
             "schema_refs": [], "interface_refs": [], "non_core_rule_capsule_refs": []}
        self.assertEqual(validate_model_visible_context(c), c)

    def test_old_design_index_identifiers_do_not_become_current_rules(self):
        src = next(x for x in self.projection["source_index_refs"] if x["ref"].endswith("merchant_invention_capability_map.json"))
        self.assertEqual(len(src["entries"]), 11)
        self.assertTrue(all(x["role"] == "SOURCE_RECORDED_CAPABILITY_NOT_ACTIVE_CLAIM" for x in src["entries"]))
        self.assertEqual(src["effect_authorization"], "NOT_GRANTED_BY_CONTEXT")
        self.assertNotIn("local_authority", json.dumps(src))

    def test_bound_implementation_sources_are_part_of_context_snapshot(self):
        refs = {x["ref"] for x in self.projection["source_bindings"]}
        self.assertIn("core/capability_internalization.py", refs)
        self.assertIn("tools/w7tp_task_state_local_rule.py", refs)
        self.assertIn("tools/total_field_dynamic_context_pull.py", refs)

    def test_registered_nonlegacy_task_id_never_rolls_back_to_t028(self):
        from tools.w7tp_bridge_dynamic_context_transport_v1 import _bind_task
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / "state").mkdir()
            (root / "state/WORK_LEDGER.json").write_text(json.dumps({"TASKS": [
                {"TASK_ID": "CAPABILITY_CONTEXT_INTEGRATION_20261015"}, {"TASK_ID": "T-028"}]}))
            (root / "state/CURRENT_CONVERSATION_CHECKPOINT.json").write_text(json.dumps({"current_goal": "T-028"}))
            # Published base and live inherited overlay have different optional planner signatures.
            # In both, exact registered task selection must take precedence.
            import inspect
            extra = {"plan": {}} if "plan" in inspect.signature(_bind_task).parameters else {}
            selected, origin = _bind_task(intent="只核對 CAPABILITY_CONTEXT_INTEGRATION_20261015 的狀態", root=root, **extra)
            self.assertEqual(selected, "CAPABILITY_CONTEXT_INTEGRATION_20261015")
            self.assertEqual(origin, "EXPLICIT_INTENT_TASK")

    def test_empty_or_malformed_requirements_do_not_escape_validation(self):
        t = copy.deepcopy(self.task); t["REQUIRED_CAPABILITY_IDS"] = [{}]
        with self.assertRaisesRegex(CapabilityInternalizationError, "REQUIREMENTS_INVALID"):
            build_capability_context_projection(t)


class BoundTaskBrokerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tools.w7tp_task_state_minimum_packet import build_task_state_minimum_packet
        from tests.test_w7tp_task_state_minimum_packet import TASK_ID, ACTION_REFS, ADI_REFS
        cls.task_ref = "task:" + TASK_ID
        cls.packet = build_task_state_minimum_packet(task_id=TASK_ID, action_refs=ACTION_REFS, adi_record_ids=ADI_REFS)

    def registered(self, builder=None, task_ref=None):
        from datetime import datetime, timedelta, timezone
        from tools.total_field_dynamic_context_pull import TotalFieldDynamicContextPullBroker
        from tools.w7tp_task_state_minimum_packet import build_task_model_visible_context
        b = TotalFieldDynamicContextPullBroker()
        refs = b.register(packet=self.packet, task_ref=task_ref or self.task_ref,
                          provider_ref="provider:test:capability", model_ref="model:test:one",
                          expires_at=(datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat(),
                          return_coordinate="total-field:test:candidate", context_builder=builder or build_task_model_visible_context)
        return b, refs

    def pull(self, b, refs):
        return b.pull(refs["pull_coordinate"], task_ref=self.task_ref,
                      provider_ref="provider:test:capability", model_ref="model:test:one")

    def test_packet_task_cannot_register_as_another_task(self):
        with self.assertRaisesRegex(DynamicContextPullHold, "PACKET_TASK_MISMATCH"):
            self.registered(task_ref="task:T-028")

    def test_builder_cannot_omit_both_task_and_inventory(self):
        def hidden(*args):
            return {"context_ref": "context:test:hidden", "state_projection": {},
                    "evidence_refs": [], "capability_refs": [], "acceptance_conditions": [],
                    "schema_refs": [], "interface_refs": [], "non_core_rule_capsule_refs": []}
        b, refs = self.registered(builder=hidden)
        with self.assertRaisesRegex(DynamicContextPullHold, "CAPABILITY_BINDING_MISMATCH"):
            self.pull(b, refs)
        self.assertTrue(b.is_consumed(refs["pull_coordinate"]))

    def test_builder_cannot_rehash_changed_bound_projection(self):
        from tools.w7tp_task_state_minimum_packet import build_task_model_visible_context
        def altered(*args):
            c = build_task_model_visible_context(*args)
            p = c["state_projection"]["capability_context"]
            p["system_frame"]["version"] = "9.9"
            rehash(p)
            return c
        b, refs = self.registered(builder=altered)
        with self.assertRaisesRegex(DynamicContextPullHold, "CAPABILITY_BINDING_MISMATCH"):
            self.pull(b, refs)

    def test_valid_pull_carries_inventory_hash_and_destroys_workset(self):
        b, refs = self.registered(); r = self.pull(b, refs)
        p = r["model_visible_context"]["state_projection"]["capability_context"]
        self.assertEqual(r["reconstruction_evidence"]["capability_context_sha256"], p["projection_sha256"])
        self.assertTrue(r["reconstruction_evidence"]["workset_destroyed"])
        self.assertNotIn("catalogue", json.dumps(refs))
        self.assertFalse(r["authority"]["model_authority"])
        with self.assertRaisesRegex(DynamicContextPullHold, "REPLAY_BLOCKED"):
            self.pull(b, refs)


if __name__ == "__main__":
    unittest.main()
