#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused tempfile-only tests for TFCT TRUE8D runtime policy promotion."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tools.promote_tfct_true8d_runtime_policy_canonical import (  # noqa: E402
    PromotionFailure,
    canonical_sha256,
    load_strict_json,
    promote,
    rollback_plan,
    verify_active,
    verify_source,
)


EXPECTED_POLICY_SHA256 = "d27230aba7a4ecd051f4169184c1fa5357ce5efa1d62019238d68991b0140960"
PROMOTION_RUN_ID = "TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL_PROMOTION_V0_1"
SOURCE_RUN_ID = "TFCT_TRUE8D_RUNTIME_CANDIDATE_V0_1"
PACKAGE_RUN_ID = "TFCT_TRUE8D_RUNTIME_CANDIDATE_POLICY_PACKAGE_V0_1"
SOURCE_POLICY = Path("manifests/tfct_true8d_runtime_candidate_v0_1/policy.json")
RUNTIME_POLICY = Path("runtime/total_field/candidate/tfct_true8d_runtime_policy_v0_1.json")
SOURCE_PACKAGE = Path("manifests/tfct_true8d_runtime_policy_canonical_v0_1")
VERSIONED_DIRECTORY = Path(
    "runtime/total_field/TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL_V0_1_D27230ABA7A4"
)
VERSIONED_CANONICAL = VERSIONED_DIRECTORY / "TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL.json"
ACTIVE_CANONICAL = Path(
    "runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL.json"
)
ACTIVE_POINTER = Path(
    "runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_POINTER.txt"
)
OTHER_ACTIVE = Path(
    "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json"
)
OTHER_POINTER = Path(
    "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_POINTER.txt"
)
D3_ENGINE = Path("tools/d3_coordinate_transition_candidate.py")
PACKET_RUNTIME = Path("tools/w7tp_packet_inference_runtime.py")
OPEN_PROBLEMS = {
    "OBSERVATION_DOMAIN_COMPLETENESS",
    "FIXED_POINT_EXISTENCE_THEOREM",
    "FIXED_POINT_UNIQUENESS_THEOREM",
    "GLOBAL_FINITE_CONVERGENCE_THEOREM",
    "DISTRIBUTED_CONSENSUS_PROTOCOL",
    "CANONICAL_TFID_HASH_CONTRACT",
    "PRODUCTION_ADI_ALGORITHM",
    "AGENT_PACKAGING",
    "PERFORMANCE_EVIDENCE",
}


def _canonical_bytes(value: Any) -> bytes:
    """Serialize JSON using the promotion identity contract."""

    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    """Write deterministic UTF-8 JSON below one temporary test root."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _digest(path: Path) -> str:
    """Hash exact sentinel bytes without interpreting their content."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_snapshot(root: Path) -> dict[str, str]:
    """Capture deterministic hashes for all files inside a temporary root."""

    return {
        str(path.relative_to(root)): _digest(path)
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    }


class RuntimePolicyCanonicalPromotionTests(unittest.TestCase):
    """Exercise promotion only against isolated temporary directory trees."""

    def setUp(self) -> None:
        """Create a complete candidate source fixture and protected sentinels."""

        self.temporary = tempfile.TemporaryDirectory(prefix="tfct-promotion-test-")
        self.root = Path(self.temporary.name)
        self.policy = load_strict_json(REPOSITORY_ROOT / SOURCE_POLICY)
        _write_json(self.root / SOURCE_POLICY, self.policy)
        _write_json(self.root / RUNTIME_POLICY, copy.deepcopy(self.policy))
        package_manifest = load_strict_json(
            REPOSITORY_ROOT
            / "manifests/tfct_true8d_runtime_candidate_v0_1/package_manifest.json"
        )
        _write_json(
            self.root
            / "manifests/tfct_true8d_runtime_candidate_v0_1/package_manifest.json",
            package_manifest,
        )
        copied_evidence = (
            "docs/total_field/TFCT_TRUE8D_RUNTIME_CANDIDATE_IMPLEMENTATION_REPORT.md",
            "docs/total_field/TFCT_TRUE8D_RUNTIME_CANDIDATE_PACKAGE_REPORT.md",
            "scripts/verify/verify_tfct_true8d_runtime_candidate.py",
            "scripts/verify/verify_tfct_true8d_runtime_candidate_package.py",
        )
        for relative in copied_evidence:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((REPOSITORY_ROOT / relative).read_bytes())
        sentinels = {
            OTHER_ACTIVE: b'{"protected":"other-active"}\n',
            OTHER_POINTER: b"/protected/other-pointer\n",
            D3_ENGINE: b"# protected D3 sentinel\n",
            PACKET_RUNTIME: b"# protected packet sentinel\n",
        }
        for relative, content in sentinels.items():
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

    def tearDown(self) -> None:
        """Release the isolated directory after each test."""

        self.temporary.cleanup()

    def _promote(self) -> None:
        """Verify the fixture source and perform an authorized temporary promotion."""

        verify_source(self.root)
        promote(self.root, owner_confirmation="YES")

    def _runtime_canonical(self) -> dict[str, Any]:
        """Load the versioned canonical envelope from the temporary root."""

        value = load_strict_json(self.root / VERSIONED_CANONICAL)
        self.assertIsInstance(value, dict)
        return value

    def test_01_candidate_source_hash_is_correct(self) -> None:
        """The approved candidate source retains its locked canonical identity."""

        self.assertEqual(canonical_sha256(self.policy), EXPECTED_POLICY_SHA256)

    def test_02_tracked_and_runtime_policy_match(self) -> None:
        """Tracked and runtime candidate policies are canonically equivalent."""

        tracked = load_strict_json(self.root / SOURCE_POLICY)
        runtime = load_strict_json(self.root / RUNTIME_POLICY)
        self.assertEqual(_canonical_bytes(tracked), _canonical_bytes(runtime))

    def test_03_canonical_manifest_is_valid(self) -> None:
        """The tracked canonical manifest contains the locked promotion contract."""

        self._promote()
        manifest = load_strict_json(self.root / SOURCE_PACKAGE / "canonical_manifest.json")
        self.assertEqual(manifest["canonical_scope"], "TFCT_TRUE8D_RUNTIME_POLICY")
        self.assertEqual(manifest["status"], "ACTIVE_CANONICAL")
        self.assertEqual(manifest["source_policy_sha256"], EXPECTED_POLICY_SHA256)
        self.assertEqual(manifest["distributed_consensus"], "OPEN_PROBLEM")
        self.assertEqual(manifest["production_adi"], "OPEN_PROBLEM")
        self.assertIs(manifest["deploy"], False)
        self.assertIs(manifest["restart"], False)

    def test_04_promotion_evidence_is_complete(self) -> None:
        """Promotion evidence records owner, source runs, checks, and review boundary."""

        self._promote()
        evidence = load_strict_json(self.root / SOURCE_PACKAGE / "promotion_evidence.json")
        rendered = json.dumps(evidence, sort_keys=True, ensure_ascii=False)
        for marker in (
            PROMOTION_RUN_ID,
            SOURCE_RUN_ID,
            PACKAGE_RUN_ID,
            EXPECTED_POLICY_SHA256,
            "45",
            "15",
            "PASS_VERIFY_TFCT_TRUE8D_RUNTIME_CANDIDATE",
            "PASS_VERIFY_TFCT_TRUE8D_RUNTIME_CANDIDATE_PACKAGE",
            "YES",
        ):
            self.assertIn(marker, rendered)
        self.assertEqual(evidence["PATENT_CANDIDATE_REVIEW_REQUIRED"], "YES")

    def test_05_rollback_manifest_is_complete(self) -> None:
        """Rollback metadata is complete and requires renewed owner confirmation."""

        self._promote()
        rollback = load_strict_json(self.root / SOURCE_PACKAGE / "rollback_manifest.json")
        required = {
            "promotion_run_id",
            "previous_active_pointer_exists",
            "previous_active_pointer_content",
            "previous_active_canonical_sha256",
            "promoted_pointer",
            "promoted_canonical",
            "rollback_requires_owner_confirmation",
        }
        self.assertTrue(required.issubset(rollback))
        self.assertEqual(rollback["promotion_run_id"], PROMOTION_RUN_ID)
        self.assertIs(rollback["rollback_requires_owner_confirmation"], True)

    def test_06_versioned_canonical_is_created(self) -> None:
        """Promotion creates the immutable versioned runtime canonical envelope."""

        self._promote()
        self.assertTrue((self.root / VERSIONED_CANONICAL).is_file())

    def test_07_active_mirror_is_created(self) -> None:
        """Promotion creates the dedicated active runtime-policy mirror."""

        self._promote()
        self.assertTrue((self.root / ACTIVE_CANONICAL).is_file())

    def test_08_pointer_targets_versioned_canonical(self) -> None:
        """The dedicated pointer contains the exact versioned canonical path."""

        self._promote()
        pointer = (self.root / ACTIVE_POINTER).read_text(encoding="utf-8").strip()
        self.assertEqual(pointer, str((self.root / VERSIONED_CANONICAL).resolve()))

    def test_09_pointer_target_exists_and_active_verifies(self) -> None:
        """The pointer resolves to an existing file accepted by active verification."""

        self._promote()
        pointer = Path((self.root / ACTIVE_POINTER).read_text(encoding="utf-8").strip())
        self.assertTrue(pointer.is_file())
        verify_active(self.root)

    def test_10_active_mirror_matches_versioned_canonical(self) -> None:
        """Active mirror and versioned canonical are canonically identical."""

        self._promote()
        active = load_strict_json(self.root / ACTIVE_CANONICAL)
        versioned = load_strict_json(self.root / VERSIONED_CANONICAL)
        self.assertEqual(_canonical_bytes(active), _canonical_bytes(versioned))

    def test_11_tracked_canonical_matches_runtime_policy(self) -> None:
        """Tracked canonical policy and runtime envelope preserve source semantics."""

        self._promote()
        tracked = load_strict_json(self.root / SOURCE_PACKAGE / "policy.json")
        envelope = self._runtime_canonical()
        self.assertEqual(_canonical_bytes(tracked), _canonical_bytes(envelope["policy"]))

    def test_12_d6_semantic_lock_is_correct(self) -> None:
        """D6 remains the Sovereign Privacy Field."""

        self._promote()
        self.assertEqual(
            self._runtime_canonical()["semantic_locks"]["D6"],
            "Sovereign Privacy Field",
        )

    def test_13_d7_semantic_lock_is_correct(self) -> None:
        """D7 remains the protocol-native generative routing field."""

        self._promote()
        self.assertEqual(
            self._runtime_canonical()["semantic_locks"]["D7"],
            "Generative Transmission & Resource Routing Field",
        )

    def test_14_d8_semantic_lock_is_correct(self) -> None:
        """D8 remains the detour-alert and quarantine adjudication field."""

        self._promote()
        self.assertEqual(
            self._runtime_canonical()["semantic_locks"]["D8"],
            "Red-Team Detour Alert & Quarantine Field",
        )

    def test_15_allow_only_commit_is_preserved(self) -> None:
        """The semantic lock and embedded policy both retain ALLOW-only commit."""

        self._promote()
        envelope = self._runtime_canonical()
        self.assertEqual(envelope["semantic_locks"]["commit_rule"], "ALLOW_ONLY")
        self.assertEqual(envelope["policy"]["commit_rule"]["final_decision"], "ALLOW")

    def test_16_open_problems_are_preserved(self) -> None:
        """Promotion keeps every excluded theorem and engineering gap open."""

        self._promote()
        envelope = self._runtime_canonical()
        self.assertEqual(set(envelope["open_problems"]), OPEN_PROBLEMS)
        self.assertEqual(
            envelope["semantic_locks"]["consensus_mode"],
            "LOCAL_EQUIVALENCE_ONLY",
        )

    def test_17_owner_confirmation_is_required(self) -> None:
        """Promotion is rejected when the exact owner confirmation is absent."""

        verify_source(self.root)
        with self.assertRaises(PromotionFailure) as raised:
            promote(self.root, owner_confirmation="NO")
        self.assertIn("OWNER", raised.exception.reason_code)
        self.assertFalse((self.root / VERSIONED_CANONICAL).exists())
        self.assertFalse((self.root / ACTIVE_CANONICAL).exists())

    def test_18_unknown_existing_entry_causes_conflict(self) -> None:
        """An unverifiable dedicated active entry is never overwritten."""

        conflict = self.root / ACTIVE_CANONICAL
        _write_json(conflict, {"unknown_source": True})
        before = conflict.read_bytes()
        with self.assertRaises(PromotionFailure) as raised:
            promote(self.root, owner_confirmation="YES")
        self.assertIn("CONFLICT", raised.exception.reason_code)
        self.assertEqual(conflict.read_bytes(), before)

    def test_19_promotion_is_idempotent(self) -> None:
        """A repeated authorized promotion produces no identity or byte drift."""

        self._promote()
        first = _tree_snapshot(self.root)
        promote(self.root, owner_confirmation="YES")
        second = _tree_snapshot(self.root)
        self.assertEqual(second, first)

    def test_20_other_active_canonical_is_unchanged(self) -> None:
        """Promotion does not modify the existing TRUE8D active canonical."""

        target = self.root / OTHER_ACTIVE
        before = _digest(target)
        self._promote()
        self.assertEqual(_digest(target), before)

    def test_21_other_pointer_is_unchanged(self) -> None:
        """Promotion does not modify any unrelated active pointer."""

        target = self.root / OTHER_POINTER
        before = _digest(target)
        self._promote()
        self.assertEqual(_digest(target), before)

    def test_22_d3_engine_is_unchanged(self) -> None:
        """Promotion does not modify the existing D3 transition engine."""

        target = self.root / D3_ENGINE
        before = _digest(target)
        self._promote()
        self.assertEqual(_digest(target), before)

    def test_23_packet_runtime_is_unchanged(self) -> None:
        """Promotion does not modify the packet inference runtime."""

        target = self.root / PACKET_RUNTIME
        before = _digest(target)
        self._promote()
        self.assertEqual(_digest(target), before)

    def test_24_rollback_plan_performs_no_write(self) -> None:
        """Rollback planning is read-only and states the confirmation boundary."""

        self._promote()
        before = _tree_snapshot(self.root)
        plan = rollback_plan(self.root)
        after = _tree_snapshot(self.root)
        self.assertEqual(after, before)
        self.assertIn("OWNER", json.dumps(plan, sort_keys=True, ensure_ascii=False).upper())

    def test_25_error_reason_codes_are_stable(self) -> None:
        """Repeated equivalent failures expose the same nonempty reason code."""

        changed = copy.deepcopy(self.policy)
        changed["max_iterations"] = changed["max_iterations"] + 1
        _write_json(self.root / SOURCE_POLICY, changed)
        reason_codes: list[str] = []
        for _index in range(2):
            with self.assertRaises(PromotionFailure) as raised:
                verify_source(self.root)
            reason_codes.append(raised.exception.reason_code)
        self.assertEqual(reason_codes[0], reason_codes[1])
        self.assertTrue(reason_codes[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
