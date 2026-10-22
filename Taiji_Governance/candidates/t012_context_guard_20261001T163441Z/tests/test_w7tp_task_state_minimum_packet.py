from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from core.work_ledger import WorkLedger
from tools import w7tp_task_state_local_rule as task_rule

from products.eight_dimensional_generative_memory import (
    w7tp_origin_state_minimum_packet_v1 as minimum_packet_module,
)
from products.eight_dimensional_generative_memory.w7tp_origin_state_minimum_packet_v1 import (
    packet_sha256,
    validate_minimum_packet,
    volatile_reconstruction,
)
from tools.total_field_dynamic_context_pull import (
    validate_model_visible_context,
)
from tools.w7tp_task_state_local_rule import TaskStateRuleError
from tools.w7tp_task_state_minimum_packet import (
    RULE_REF,
    build_task_model_visible_context,
    build_task_state_minimum_packet,
    select_task_state_support_refs,
    _adi_payload_context_eligible,
)


TASK_ID = "NLDEV-005"
CANDIDATE_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_REGISTRY = (
    CANDIDATE_ROOT
    / "configs/total_field/w7tp_local_origin_state_rule_registry_v1.json"
)
ACTION_REFS = [
    "A-NLDEV-005-MIN-PACKET-MAINLINE-20260926",
    "A-NLDEV-005-ORIGIN-CELL-PURITY-LAND-20260926",
    "A-NLDEV-005-NL-CONTROL-TOTAL-FIELD-GATE-LAND-20260926",
    "A-NLDEV-005-CONTEXT-PULL-SUCCESSOR-20260926",
    "A-NLDEV-005-GEMINI-A2A-20260925",
]
ADI_REFS = [
    "capability:total-field-pointer-first-context-pull:20260926:v1",
    "capability:gemini-code-assist-a2a-pointer-first:20260926:v1",
    "design:cloud-model-dynamic-context-pull:20260926:v1",
    "design:origin-state-minimum-packet-transmission:20260926:v1",
    "design:local-rules-cloud-packet-adi-coordinate-ref:20260926:v1",
    "evidence:origin-state-minimum-packet-logic-validation:20260926",
]
_ORIGINAL_LOAD_JSON = task_rule._load_json


def _load_task_bound_test_json(path: Path, code: str) -> dict:
    value = _ORIGINAL_LOAD_JSON(path, code)
    if path.name == "CURRENT_CONVERSATION_CHECKPOINT.json":
        value = copy.deepcopy(value)
        value["current_task_id"] = TASK_ID
    return value


def _validate_candidate_packet(packet: dict) -> dict:
    return validate_minimum_packet(
        packet,
        root=CANDIDATE_ROOT,
        registry_path=CANDIDATE_REGISTRY,
    )


def _candidate_volatile_reconstruction(packet: dict):
    return volatile_reconstruction(
        packet,
        root=CANDIDATE_ROOT,
        registry_path=CANDIDATE_REGISTRY,
    )


class TaskStateMinimumPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.checkpoint_patcher = patch.object(
            task_rule,
            "_load_json",
            side_effect=_load_task_bound_test_json,
        )
        cls.checkpoint_patcher.start()
        cls.rule_loader_patcher = patch.object(
            minimum_packet_module,
            "_load_python_module",
            return_value=task_rule,
        )
        cls.rule_loader_patcher.start()
        try:
            cls.packet = build_task_state_minimum_packet(
                task_id=TASK_ID,
                action_refs=ACTION_REFS,
                adi_record_ids=ADI_REFS,
                root=CANDIDATE_ROOT,
                registry_path=CANDIDATE_REGISTRY,
            )
        except Exception:
            cls.rule_loader_patcher.stop()
            cls.checkpoint_patcher.stop()
            raise

    @classmethod
    def tearDownClass(cls) -> None:
        cls.rule_loader_patcher.stop()
        cls.checkpoint_patcher.stop()

    def test_packet_reuses_origin_state_minimum_contract(self) -> None:
        resolved = _validate_candidate_packet(self.packet)
        self.assertEqual(
            resolved["rule_entry"]["rule_ref"],
            RULE_REF,
        )
        self.assertEqual(
            self.packet["packet_type"],
            "ORIGIN_STATE_MINIMUM_PACKET",
        )
        self.assertEqual(
            set(self.packet["minimum_new_information"]),
            {"task_id", "action_refs", "adi_record_ids"},
        )
        self.assertEqual(
            self.packet["minimum_new_information"]["task_id"],
            TASK_ID,
        )

    def test_packet_is_reference_minimum_not_full_task_state(self) -> None:
        encoded = json.dumps(
            self.packet,
            ensure_ascii=False,
            sort_keys=True,
        )
        self.assertNotIn(
            "Stabilize the server-first control path",
            encoded,
        )
        self.assertNotIn("LAST_CONFIRMED_EFFECT", encoded)
        def keys(value):
            if isinstance(value, dict):
                for key, nested in value.items():
                    yield str(key)
                    yield from keys(nested)
            elif isinstance(value, list):
                for nested in value:
                    yield from keys(nested)

        packet_keys = set(keys(self.packet))
        self.assertNotIn("reconstruction_rules", packet_keys)
        self.assertNotIn("rule_body", packet_keys)
        self.assertNotIn("full_dynamic_context", packet_keys)
        self.assertIn(
            "local-rule:w7tp-task-state-ledger-reconstruction/v1",
            encoded,
        )

    def test_real_task_state_reconstructs_volatile_and_projects_context(self) -> None:
        workset_parent: Path | None = None
        with _candidate_volatile_reconstruction(self.packet) as reconstructed:
            workset = reconstructed["workset_path"]
            workset_parent = workset.parent
            self.assertTrue(workset.is_dir())
            for name in (
                "task_state.json",
                "action_state.json",
                "checkpoint.json",
                "native_adi_packet.json",
            ):
                self.assertTrue((workset / name).is_file())

            context = build_task_model_visible_context(
                workset,
                self.packet,
                reconstructed["receipt"],
            )
            validated = validate_model_visible_context(context)
            projection = validated["state_projection"]
            self.assertEqual(
                projection["task"]["task_ref"],
                "task:NLDEV-005",
            )
            self.assertEqual(
                projection["task"]["state"],
                WorkLedger()._task(TASK_ID)["STATE"],
            )
            self.assertEqual(
                len(projection["actions"]),
                len(ACTION_REFS),
            )
            self.assertEqual(
                set(projection["native_adi"]["record_refs"]),
                set(ADI_REFS),
            )
            self.assertFalse(
                reconstructed["receipt"]["persistent_materialization"]
            )
        assert workset_parent is not None
        self.assertFalse(workset_parent.exists())

    def test_unknown_action_ref_fails_closed_at_local_rule(self) -> None:
        tampered = copy.deepcopy(self.packet)
        tampered["minimum_new_information"]["action_refs"] = [
            *ACTION_REFS[:-1],
            "A-NLDEV-005-DOES-NOT-EXIST",
        ]
        tampered["packet_sha256"] = packet_sha256(tampered)
        _validate_candidate_packet(tampered)
        with self.assertRaisesRegex(
            RuntimeError,
            "HOLD_TASK_STATE_ACTION_REF_NOT_FOUND",
        ):
            with _candidate_volatile_reconstruction(tampered):
                pass

    def test_packet_hash_tamper_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.packet)
        tampered["minimum_new_information"]["task_id"] = "NLDEV-XXX"
        with self.assertRaisesRegex(
            Exception,
            "HOLD_MINIMUM_PACKET_SELF_HASH_MISMATCH",
        ):
            _validate_candidate_packet(tampered)

    def test_dynamic_context_rejects_superseded_historical_evidence(self) -> None:
        self.assertFalse(_adi_payload_context_eligible({
            "status": "SUPERSEDED_HISTORICAL_EVIDENCE_ONLY",
            "CURRENT_CONTEXT_ELIGIBLE": False,
        }))

    def test_dynamic_context_accepts_current_capability_evidence(self) -> None:
        self.assertTrue(_adi_payload_context_eligible({
            "knowledge_type": "OBSERVED_IMPLEMENTED_CAPABILITY",
            "state": "LANDED_LIVE_VERIFIED_CANDIDATE_REASONING_ORGAN",
        }))

    def test_selector_uses_real_task_actions_and_existing_adi_refs(self) -> None:
        selected = select_task_state_support_refs(
            task_id=TASK_ID,
            current_action_id=(
                "A-NLDEV-005-AUTO-TASK-PACKET-GEMINI-RUNNER-20260926"
            ),
            max_actions=8,
            max_adi_refs=16,
        )
        self.assertIn(
            "A-NLDEV-005-AUTO-TASK-PACKET-GEMINI-RUNNER-20260926",
            selected["action_refs"],
        )
        self.assertLessEqual(len(selected["action_refs"]), 8)
        self.assertTrue(selected["adi_record_ids"])
        self.assertLessEqual(len(selected["adi_record_ids"]), 16)
        self.assertIn(
            "capability:gemini-code-assist-a2a-pointer-first:20260926:v1",
            selected["adi_record_ids"],
        )
        self.assertIn(
            "capability:total-field-pointer-first-context-pull:20260926:v1",
            selected["adi_record_ids"],
        )


class TaskStateCheckpointBindingTests(unittest.TestCase):
    def test_checkpoint_for_other_task_fails_closed(self) -> None:
        work = {"TASKS": [{"TASK_ID": "T-012"}]}
        action = {"ACTIONS": []}
        checkpoint = {"current_task_id": "XJ-002"}
        with (
            patch.object(task_rule, "_root", return_value=Path("/tmp/not-read")),
            patch.object(
                task_rule,
                "_load_json",
                side_effect=[work, action, checkpoint],
            ),
        ):
            with self.assertRaisesRegex(
                TaskStateRuleError,
                "HOLD_TASK_STATE_CHECKPOINT_TASK_MISMATCH",
            ):
                task_rule.build_task_state_snapshot(
                    task_id="T-012",
                    action_refs=["A-T012"],
                    adi_record_ids=["evidence:test"],
                )


if __name__ == "__main__":
    unittest.main()
