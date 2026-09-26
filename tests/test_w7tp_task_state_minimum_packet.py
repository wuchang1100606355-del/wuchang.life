from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from core.work_ledger import WorkLedger

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
)


TASK_ID = "NLDEV-005"
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


class TaskStateMinimumPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = build_task_state_minimum_packet(
            task_id=TASK_ID,
            action_refs=ACTION_REFS,
            adi_record_ids=ADI_REFS,
        )

    def test_packet_reuses_origin_state_minimum_contract(self) -> None:
        resolved = validate_minimum_packet(self.packet)
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
        with volatile_reconstruction(self.packet) as reconstructed:
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
        validate_minimum_packet(tampered)
        with self.assertRaisesRegex(
            RuntimeError,
            "HOLD_TASK_STATE_ACTION_REF_NOT_FOUND",
        ):
            with volatile_reconstruction(tampered):
                pass

    def test_packet_hash_tamper_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.packet)
        tampered["minimum_new_information"]["task_id"] = "NLDEV-XXX"
        with self.assertRaisesRegex(
            Exception,
            "HOLD_MINIMUM_PACKET_SELF_HASH_MISMATCH",
        ):
            validate_minimum_packet(tampered)

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


if __name__ == "__main__":
    unittest.main()
