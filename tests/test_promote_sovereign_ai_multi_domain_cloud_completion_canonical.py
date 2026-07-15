#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Twenty-eight focused isolated tests for multi-domain canonical promotion."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.promote_sovereign_ai_multi_domain_cloud_completion_canonical import (  # noqa: E402
    ACTIVE_CANONICAL,
    ACTIVE_POINTER,
    ROLLBACK_MANIFEST,
    RUNTIME_CANONICAL,
    SOURCE_POLICY,
    SOURCE_POLICY_SHA256,
    SOURCE_REPORT,
    SOURCE_SCHEMA,
    SOURCE_VERIFIER,
    TRACKED_POLICY,
    PromotionFailure,
    canonical_json,
    canonical_sha256,
    load_strict_json,
    promote,
    rollback_plan,
    verify_active,
    verify_source,
)


OTHER_ACTIVE = Path("runtime/total_field/active/ACTIVE_OTHER_CANONICAL.json")
OTHER_POINTER = Path("runtime/total_field/active/ACTIVE_OTHER_POINTER.txt")
PROMOTION_TOOL = ROOT / "tools/promote_sovereign_ai_multi_domain_cloud_completion_canonical.py"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SovereignAIMultiDomainCanonicalPromotionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="sovereign-ai-promotion-")
        self.root = Path(self.temporary.name)
        for relative in (SOURCE_POLICY, SOURCE_SCHEMA, SOURCE_VERIFIER, SOURCE_REPORT):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative).read_bytes())
        for relative, content in (
            (OTHER_ACTIVE, b'{"protected":"active"}\n'),
            (OTHER_POINTER, b"/protected/other-pointer\n"),
        ):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        self.other_active_hash = _digest(self.root / OTHER_ACTIVE)
        self.other_pointer_hash = _digest(self.root / OTHER_POINTER)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _promote(self) -> None:
        promote(self.root, owner_confirmation="YES")

    def _runtime(self) -> dict[str, object]:
        value = load_strict_json(self.root / RUNTIME_CANONICAL)
        self.assertIsInstance(value, dict)
        return value

    def test_01_candidate_policy_is_parseable(self) -> None:
        result = verify_source(self.root)
        self.assertEqual(result.source_policy_sha256, SOURCE_POLICY_SHA256)

    def test_02_candidate_and_tracked_policy_are_equivalent(self) -> None:
        self._promote()
        source = load_strict_json(self.root / SOURCE_POLICY)
        tracked = load_strict_json(self.root / TRACKED_POLICY)
        self.assertEqual(canonical_json(source), canonical_json(tracked))

    def test_03_all_three_domains_exist(self) -> None:
        self._promote()
        self.assertEqual(
            self._runtime()["domains"],
            {"COMMUNITY": "ACTIVE_CANONICAL", "COMMERCE": "ACTIVE_CANONICAL", "PROPERTY": "ACTIVE_CANONICAL"},
        )

    def test_04_cloud_completion_is_candidate_only(self) -> None:
        self._promote()
        self.assertEqual(self._runtime()["cloud_completion"], "SUPPORTED_AS_CANDIDATE_ONLY")

    def test_05_cloud_has_no_direct_commit_authority(self) -> None:
        self._promote()
        self.assertEqual(self._runtime()["semantic_locks"]["CLOUD_LLM_AUTHORITY"], "NONE")

    def test_06_xiaoj_has_no_final_authority(self) -> None:
        self._promote()
        self.assertEqual(self._runtime()["semantic_locks"]["XIAOJ_FINAL_AUTHORITY"], "NO")

    def test_07_total_field_pull_uses_common_gateway(self) -> None:
        self._promote()
        self.assertEqual(self._runtime()["source_modes"]["TOTAL_FIELD_PULL"], "TOTAL_FIELD_GATEWAY_REQUIRED")

    def test_08_llm_push_uses_common_gateway(self) -> None:
        self._promote()
        self.assertEqual(self._runtime()["source_modes"]["LLM_PUSH"], "TOTAL_FIELD_GATEWAY_REQUIRED")

    def test_09_xiaoj_local_uses_common_gateway(self) -> None:
        self._promote()
        self.assertEqual(self._runtime()["source_modes"]["XIAOJ_LOCAL"], "TOTAL_FIELD_GATEWAY_REQUIRED")

    def test_10_d6_gate_is_locked(self) -> None:
        self._promote()
        self.assertEqual(self._runtime()["semantic_locks"]["D6_PRIVACY_GATE"], "REQUIRED")

    def test_11_d4_gate_is_locked(self) -> None:
        self._promote()
        self.assertEqual(self._runtime()["semantic_locks"]["D4_EVIDENCE_GATE"], "REQUIRED")

    def test_12_d8_gate_is_locked(self) -> None:
        self._promote()
        self.assertEqual(self._runtime()["semantic_locks"]["D8_ADJUDICATION"], "REQUIRED")

    def test_13_allow_only_commit_is_locked(self) -> None:
        self._promote()
        self.assertEqual(self._runtime()["semantic_locks"]["ALLOW_ONLY_COMMIT"], "REQUIRED")

    def test_14_sensitive_attributes_are_restricted(self) -> None:
        self._promote()
        self.assertEqual(self._runtime()["semantic_locks"]["SENSITIVE_ATTRIBUTES"], "PRIVACY_RESTRICTED")

    def test_15_owner_attributes_require_confirmation(self) -> None:
        self._promote()
        self.assertEqual(self._runtime()["semantic_locks"]["OWNER_ATTRIBUTES"], "OWNER_CONFIRMATION_REQUIRED")

    def test_16_legal_attributes_require_review(self) -> None:
        self._promote()
        self.assertEqual(self._runtime()["semantic_locks"]["LEGAL_ATTRIBUTES"], "LEGAL_REVIEW_REQUIRED")

    def test_17_financial_attributes_require_review(self) -> None:
        self._promote()
        self.assertEqual(self._runtime()["semantic_locks"]["FINANCIAL_ATTRIBUTES"], "FINANCIAL_REVIEW_REQUIRED")

    def test_18_owner_confirmation_is_mandatory(self) -> None:
        with self.assertRaises(PromotionFailure) as caught:
            promote(self.root, owner_confirmation="NO")
        self.assertEqual(caught.exception.reason_code, "OWNER_CONFIRMATION_REQUIRED")

    def test_19_dedicated_active_canonical_is_correct(self) -> None:
        self._promote()
        self.assertEqual((self.root / ACTIVE_CANONICAL).read_bytes(), (self.root / RUNTIME_CANONICAL).read_bytes())
        self.assertEqual(verify_active(self.root).status, "ACTIVE_MATCH")

    def test_20_dedicated_pointer_is_correct(self) -> None:
        self._promote()
        self.assertEqual((self.root / ACTIVE_POINTER).read_text(encoding="utf-8").strip(), str((self.root / RUNTIME_CANONICAL).resolve()))

    def test_21_other_active_canonical_is_unchanged(self) -> None:
        self._promote()
        self.assertEqual(_digest(self.root / OTHER_ACTIVE), self.other_active_hash)

    def test_22_other_pointer_is_unchanged(self) -> None:
        self._promote()
        self.assertEqual(_digest(self.root / OTHER_POINTER), self.other_pointer_hash)

    def test_23_no_database_write_api(self) -> None:
        tree = ast.parse(PROMOTION_TOOL.read_text(encoding="utf-8"))
        imports = {node.names[0].name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)}
        self.assertTrue(imports.isdisjoint({"sqlite3", "psycopg", "psycopg2", "sqlalchemy", "odoo"}))

    def test_24_no_deploy_api(self) -> None:
        source = PROMOTION_TOOL.read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("deploy(", source)

    def test_25_no_restart_api(self) -> None:
        source = PROMOTION_TOOL.read_text(encoding="utf-8")
        self.assertNotIn("restart(", source)
        self.assertNotIn("reboot(", source)

    def test_26_promotion_is_idempotent(self) -> None:
        first = promote(self.root, owner_confirmation="YES")
        snapshot = {str(path.relative_to(self.root)): _digest(path) for path in self.root.rglob("*") if path.is_file()}
        second = promote(self.root, owner_confirmation="YES")
        after = {str(path.relative_to(self.root)): _digest(path) for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(first.status, "PROMOTED")
        self.assertEqual(second.status, "ALREADY_ACTIVE")
        self.assertEqual(snapshot, after)

    def test_27_rollback_plan_does_not_write(self) -> None:
        self._promote()
        before = {str(path.relative_to(self.root)): _digest(path) for path in self.root.rglob("*") if path.is_file()}
        plan = rollback_plan(self.root)
        after = {str(path.relative_to(self.root)): _digest(path) for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(plan["status"], "PLAN_ONLY")
        self.assertFalse(plan["automatic_rollback"])
        self.assertEqual(before, after)

    def test_28_error_codes_are_stable(self) -> None:
        policy = load_strict_json(self.root / SOURCE_POLICY)
        policy["cloud_completion"] = "INVALID"
        (self.root / SOURCE_POLICY).write_text(json.dumps(policy), encoding="utf-8")
        codes = []
        for _ in range(2):
            with self.assertRaises(PromotionFailure) as caught:
                verify_source(self.root)
            codes.append(caught.exception.reason_code)
        self.assertEqual(codes, ["SOURCE_POLICY_MISMATCH", "SOURCE_POLICY_MISMATCH"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
