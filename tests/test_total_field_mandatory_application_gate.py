from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.total_field_hourly_reviewed_commit import (
    HOLD_COMMIT,
    PASS_COMMIT,
    PASS_NOOP,
    hourly_reviewed_commit,
)
from tools.total_field_mandatory_application_gate import (
    HOLD_STATE,
    PASS_STATE,
    reviewed_prompt_text,
    scan_operation,
    write_change_review_receipt,
)


RULE_REFS = [
    "01_admin/boot/root_authority_guard.yaml",
    "01_admin/boot/boot_policy.yaml",
    "boot/taiji_boot_order.yaml",
    "configs/total_field/w7tp_8dadi_d6_contract_v2_3.json",
]


def context_packet() -> dict:
    return {
        "state": "TOTAL_FIELD_DYNAMIC_CONTEXT_READY",
        "retrieval_method": "8DADI_MEMORY_INDEX_ONLY",
        "authority": "READ_ONLY_CONTEXT_EVIDENCE_NO_DECISION_AUTHORITY",
        "founder_intent_projection": {
            "state": "CURRENT",
            "target_lock": {"locked": True},
            "D8": {"this_target_lock_grants_external_effect": False},
        },
        "intent_translation_application_rules": {"application_sequence": ["FOUNDER_INTENT", "TOTAL_FIELD_DECISION"]},
        "work_target_lock_contract": {"model_tool_cloud_or_historical_evidence_may_change_target": False},
        "adi_discrete_integer_lookup_math_contract": {"operations": ["EXACT_INTEGER_COMPARISON"]},
    }


class MandatoryApplicationGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        config = {
            "schema_id": "W7TP_8DADI_MANDATORY_APPLICATION_GATE_V1",
            "state": "ACTIVE_FAIL_CLOSED",
            "authority": "TOTAL_FIELD_RULE_APPLICATION_REVIEW",
            "required_local_rule_refs": [
                *RULE_REFS,
                "configs/total_field/mandatory_application_gate_v1.json",
            ],
            "required_dynamic_context": {
                "state": "TOTAL_FIELD_DYNAMIC_CONTEXT_READY",
                "retrieval_method": "8DADI_MEMORY_INDEX_ONLY",
                "authority": "READ_ONLY_CONTEXT_EVIDENCE_NO_DECISION_AUTHORITY",
            },
            "policy": {"clean_worktree_required": True},
            "operations": {
                "PREFLIGHT": {"effect": False, "require_clean_worktree": True},
                "AI_INFERENCE": {
                    "effect": False,
                    "require_clean_worktree": True,
                    "require_expected_work_target": True,
                },
                "CHANGE_COMPLETION_REVIEW": {
                    "effect": False,
                    "require_clean_worktree": False,
                    "require_expected_work_target": True,
                },
                "HOURLY_REVIEWED_COMMIT": {
                    "effect": True,
                    "require_clean_worktree": False,
                    "require_expected_work_target": True,
                    "required_scope": "REVIEWED_CHANGE_SET_ONLY",
                    "required_authority_state": "PASS_TOTAL_FIELD_RULE_APPLICATION_REVIEW_RECEIPT",
                },
                "DEPLOY": {
                    "effect": True,
                    "require_clean_worktree": True,
                    "require_expected_work_target": True,
                    "required_scope": "AUTHORIZE_EXACT_DEPLOY_RESTART",
                },
                "DB_WRITE": {
                    "effect": True,
                    "require_clean_worktree": True,
                    "required_scope": "UNAVAILABLE_FAIL_CLOSED",
                },
            },
        }
        config_path = self.root / "configs/total_field/mandatory_application_gate_v1.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(json.dumps(config), encoding="utf-8")
        (self.root / ".gitignore").write_text("runtime/\n", encoding="utf-8")
        for relative in RULE_REFS:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"rule: {relative}\n", encoding="utf-8")
        subprocess.run(["git", "init", "-b", "main", self.root], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "-C", self.root, "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", self.root, "config", "user.name", "Gate Test"], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                self.root,
                "add",
                "--",
                ".gitignore",
                *RULE_REFS,
                str(config_path.relative_to(self.root)),
            ],
            check=True,
        )
        subprocess.run(["git", "-C", self.root, "commit", "-m", "fixture"], check=True, stdout=subprocess.DEVNULL)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def builder(*args, **kwargs) -> dict:
        return context_packet()

    def scan(self, operation: str, **kwargs) -> dict:
        return scan_operation(
            repo_root=self.root,
            operation=operation,
            actor_class=kwargs.pop("actor_class", "SYSTEM"),
            query=kwargs.pop("query", "current founder work cell"),
            context_builder=self.builder,
            **kwargs,
        )

    def target_lock(self) -> str:
        return self.scan("PREFLIGHT")["work_target_sha256"]

    def test_clean_preflight_passes_total_field_review(self) -> None:
        result = self.scan("PREFLIGHT")
        self.assertEqual(result["state"], PASS_STATE)
        self.assertTrue(result["operation_authorized"])
        self.assertEqual(result["review"], "TOTAL_FIELD_RULE_APPLICATION_REVIEW")
        self.assertEqual(result["ai_output_state"], "CANDIDATE_ONLY")
        self.assertIn("TOTAL_FIELD", reviewed_prompt_text(result))

    def test_dirty_worktree_blocks_ai_inference(self) -> None:
        target = self.target_lock()
        (self.root / "dirty.txt").write_text("unreviewed", encoding="utf-8")
        result = self.scan(
            "AI_INFERENCE", actor_class="AI", expected_work_target_sha256=target
        )
        self.assertEqual(result["state"], HOLD_STATE)
        self.assertEqual(result["reason"], "DIRTY_WORKTREE_BLOCKED")
        self.assertFalse(result["operation_authorized"])

    def test_change_completion_review_can_measure_dirty_change(self) -> None:
        target = self.target_lock()
        (self.root / "dirty.txt").write_text("awaiting review", encoding="utf-8")
        result = self.scan(
            "CHANGE_COMPLETION_REVIEW",
            actor_class="AI",
            expected_work_target_sha256=target,
        )
        self.assertEqual(result["state"], PASS_STATE)
        self.assertTrue(result["operation_authorized"])
        self.assertFalse(result["effect"])
        review = result["change_review_packet"]
        self.assertEqual(review["state"], "PASS_TOTAL_FIELD_COMPLETED_CHANGE_REVIEW")
        self.assertEqual(review["change_bindings"][0]["path"], "dirty.txt")
        self.assertFalse(review["effect_authority"])

    def test_change_review_receipt_is_append_only_and_exact(self) -> None:
        target = self.target_lock()
        (self.root / "dirty.txt").write_text("awaiting review", encoding="utf-8")
        result = self.scan(
            "CHANGE_COMPLETION_REVIEW",
            expected_work_target_sha256=target,
        )
        first = write_change_review_receipt(self.root, result)
        second = write_change_review_receipt(self.root, result)
        self.assertEqual(first, second)
        self.assertEqual(
            json.loads(first.read_text(encoding="utf-8"))["review_sha256"],
            result["change_review_packet"]["review_sha256"],
        )

    def test_missing_work_target_lock_is_blocked(self) -> None:
        result = self.scan("AI_INFERENCE", actor_class="AI")
        self.assertEqual(result["reason"], "WORK_TARGET_LOCK_REQUIRED")

    def test_null_founder_intent_projection_is_blocked(self) -> None:
        packet = context_packet()
        packet["founder_intent_projection"] = None
        result = scan_operation(
            repo_root=self.root,
            operation="PREFLIGHT",
            actor_class="SYSTEM",
            query="current founder work cell",
            context_builder=lambda *args, **kwargs: packet,
        )
        self.assertEqual(result["reason"], "CURRENT_FOUNDER_INTENT_REQUIRED")

    def test_changed_intent_cannot_reuse_old_target_lock(self) -> None:
        target = self.target_lock()
        result = self.scan(
            "AI_INFERENCE",
            actor_class="AI",
            query="different endpoint",
            expected_work_target_sha256=target,
        )
        self.assertEqual(result["reason"], "WORK_TARGET_DRIFT")

    def test_expected_coordinate_drift_is_blocked(self) -> None:
        result = self.scan("PREFLIGHT", expected_head="0" * 40)
        self.assertEqual(result["reason"], "EXPECTED_COORDINATE_DRIFT")

    def test_missing_local_rule_is_blocked(self) -> None:
        target = self.target_lock()
        (self.root / RULE_REFS[0]).unlink()
        result = self.scan(
            "CHANGE_COMPLETION_REVIEW", expected_work_target_sha256=target
        )
        self.assertEqual(result["reason"], "LOCAL_RULE_SOURCE_INVALID")

    def test_effect_requires_total_field_d8(self) -> None:
        target = self.target_lock()
        result = self.scan(
            "DEPLOY", actor_class="AI", expected_work_target_sha256=target
        )
        self.assertEqual(result["reason"], "AI_MAY_NOT_AUTHORIZE_EFFECT")
        self.assertFalse(result["deploy_authorized"])
        self.assertFalse(result["ai_effect_authorized"])

        human_result = self.scan(
            "DEPLOY", actor_class="HUMAN", expected_work_target_sha256=target
        )
        self.assertEqual(human_result["reason"], "TOTAL_FIELD_D8_REQUIRED")

    def test_exact_effect_scope_can_authorize_human_deploy_but_not_ai_authority(self) -> None:
        target = self.target_lock()
        authority = {
            "state": "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED",
            "authority_verified": True,
            "scope": ["AUTHORIZE_EXACT_DEPLOY_RESTART"],
        }
        result = self.scan(
            "DEPLOY",
            actor_class="HUMAN",
            expected_work_target_sha256=target,
            effect_authority=authority,
        )
        self.assertEqual(result["state"], PASS_STATE)
        self.assertTrue(result["deploy_authorized"])
        self.assertFalse(result["ai_effect_authorized"])

    def test_unavailable_effect_scope_stays_fail_closed(self) -> None:
        result = self.scan("DB_WRITE", effect_authority={"authority_verified": True})
        self.assertEqual(result["reason"], "EFFECT_SCOPE_UNAVAILABLE_FAIL_CLOSED")

    def test_hourly_clean_tree_records_noop(self) -> None:
        result = hourly_reviewed_commit(
            self.root,
            context_builder=self.builder,
            now=datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(result["state"], PASS_NOOP)
        self.assertFalse(result["commit_created"])

    def test_hourly_dirty_tree_without_review_is_held(self) -> None:
        (self.root / "dirty.txt").write_text("unreviewed", encoding="utf-8")
        result = hourly_reviewed_commit(self.root, context_builder=self.builder)
        self.assertEqual(result["state"], HOLD_COMMIT)
        self.assertEqual(result["reason"], "REVIEW_RECEIPT_REQUIRED")

    def test_hourly_commits_only_exact_reviewed_snapshot(self) -> None:
        base = subprocess.run(
            ["git", "-C", self.root, "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        target = self.target_lock()
        (self.root / "dirty.txt").write_text("reviewed", encoding="utf-8")
        review = self.scan(
            "CHANGE_COMPLETION_REVIEW",
            expected_work_target_sha256=target,
        )
        write_change_review_receipt(self.root, review)
        result = hourly_reviewed_commit(self.root, context_builder=self.builder)
        self.assertEqual(result["state"], PASS_COMMIT)
        self.assertTrue(result["commit_created"])
        parent = subprocess.run(
            ["git", "-C", self.root, "rev-parse", "HEAD^"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(parent, base)
        self.assertEqual(
            subprocess.run(
                ["git", "-C", self.root, "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout,
            "",
        )

    def test_hourly_holds_when_content_changes_after_review(self) -> None:
        target = self.target_lock()
        path = self.root / "dirty.txt"
        path.write_text("reviewed", encoding="utf-8")
        review = self.scan(
            "CHANGE_COMPLETION_REVIEW",
            expected_work_target_sha256=target,
        )
        write_change_review_receipt(self.root, review)
        path.write_text("drifted", encoding="utf-8")
        result = hourly_reviewed_commit(self.root, context_builder=self.builder)
        self.assertEqual(result["state"], HOLD_COMMIT)
        self.assertEqual(result["reason"], "REVIEW_RECEIPT_REQUIRED")


if __name__ == "__main__":
    unittest.main()
