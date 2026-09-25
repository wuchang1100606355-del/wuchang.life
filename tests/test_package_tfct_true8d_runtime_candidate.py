#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused tests for the trackable TFCT TRUE8D runtime candidate package."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify.verify_tfct_true8d_runtime_candidate import HEAD_PROTECTED
from tools.package_tfct_true8d_runtime_candidate import (
    PackageFailure,
    canonical_sha256,
    check_package,
    load_strict_json,
    materialize,
)


PACKAGE_DIR = ROOT / "manifests" / "tfct_true8d_runtime_candidate_v0_1"
TRACKED_POLICY = PACKAGE_DIR / "policy.json"
PACKAGE_MANIFEST = PACKAGE_DIR / "package_manifest.json"
RUNTIME_POLICY = (
    ROOT / "runtime" / "total_field" / "candidate" / "tfct_true8d_runtime_policy_v0_1.json"
)
ACTIVE_PATHS = tuple(
    ROOT / path
    for path in HEAD_PROTECTED
    if Path(path).name.startswith("ACTIVE_") and not Path(path).name.endswith("_POINTER.txt")
)
POINTER_PATHS = tuple(ROOT / path for path in HEAD_PROTECTED if Path(path).name.endswith("_POINTER.txt"))


def _canonical_text(value: Any) -> str:
    """Serialize one test value with the package's deterministic JSON contract."""

    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def _write_json(path: Path, value: Any) -> None:
    """Write deterministic JSON inside a temporary test directory."""

    path.write_text(_canonical_text(value) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    """Hash one protected file without interpreting its content."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hashes(paths: tuple[Path, ...]) -> dict[str, str]:
    """Capture hashes for an exact, predeclared set of protected files."""

    return {str(path.relative_to(ROOT)): _sha256(path) for path in paths}


def _temporary_package(base: Path) -> Path:
    """Create an isolated package copy for mutation tests."""

    package_dir = base / "package"
    package_dir.mkdir()
    (package_dir / "policy.json").write_bytes(TRACKED_POLICY.read_bytes())
    (package_dir / "package_manifest.json").write_bytes(PACKAGE_MANIFEST.read_bytes())
    return package_dir


class RuntimeCandidatePackageTests(unittest.TestCase):
    """Verify deterministic packaging without changing the real runtime policy."""

    def test_01_tracked_and_runtime_policies_are_canonically_equivalent(self) -> None:
        result = check_package(package_dir=PACKAGE_DIR, runtime_policy_path=RUNTIME_POLICY)
        self.assertEqual(result.status, "MATCH")
        self.assertEqual(load_strict_json(TRACKED_POLICY), load_strict_json(RUNTIME_POLICY))

    def test_02_manifest_hash_matches_tracked_policy(self) -> None:
        manifest = load_strict_json(PACKAGE_MANIFEST)
        policy = load_strict_json(TRACKED_POLICY)
        self.assertEqual(manifest["policy_sha256"], canonical_sha256(policy))

    def test_03_object_key_order_does_not_change_policy_hash(self) -> None:
        policy = load_strict_json(TRACKED_POLICY)
        reordered = {key: policy[key] for key in reversed(tuple(policy))}
        self.assertEqual(canonical_sha256(policy), canonical_sha256(reordered))

    def test_04_rule_mutation_is_reported_as_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package_dir = _temporary_package(Path(directory))
            policy_path = package_dir / "policy.json"
            policy = load_strict_json(policy_path)
            policy["rule_refs"]["identity"]["ref"] = "rules/tfct/identity_mutated_for_test"
            manifest_path = package_dir / "package_manifest.json"
            manifest = load_strict_json(manifest_path)
            manifest["policy_sha256"] = canonical_sha256(policy)
            _write_json(policy_path, policy)
            _write_json(manifest_path, manifest)
            result = check_package(package_dir=package_dir, runtime_policy_path=RUNTIME_POLICY)
            self.assertEqual(result.status, "MISMATCH")

    def test_05_non_candidate_policy_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package_dir = _temporary_package(Path(directory))
            policy_path = package_dir / "policy.json"
            manifest_path = package_dir / "package_manifest.json"
            policy = load_strict_json(policy_path)
            policy["status"] = "COMMITTED"
            manifest = load_strict_json(manifest_path)
            manifest["policy_sha256"] = canonical_sha256(policy)
            _write_json(policy_path, policy)
            _write_json(manifest_path, manifest)
            with self.assertRaises(PackageFailure) as raised:
                check_package(package_dir=package_dir, runtime_policy_path=RUNTIME_POLICY)
            self.assertEqual(raised.exception.reason_code, "POLICY_STATUS_NOT_CANDIDATE")

    def test_06_nan_and_infinity_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nonfinite.json"
            for token in ("NaN", "Infinity", "-Infinity", "1e9999"):
                with self.subTest(token=token):
                    path.write_text('{"value":' + token + "}\n", encoding="utf-8")
                    with self.assertRaises(PackageFailure) as raised:
                        load_strict_json(path)
                    self.assertEqual(raised.exception.reason_code, "JSON_NONFINITE_VALUE")

    def test_07_materialize_creates_policy_in_empty_temporary_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "candidate_policy.json"
            result = materialize(target, package_dir=PACKAGE_DIR)
            self.assertEqual(result.status, "MATERIALIZED")
            self.assertEqual(load_strict_json(target), load_strict_json(TRACKED_POLICY))

    def test_08_materialize_existing_equal_policy_returns_already_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "candidate_policy.json"
            materialize(target, package_dir=PACKAGE_DIR)
            result = materialize(target, package_dir=PACKAGE_DIR)
            self.assertEqual(result.status, "ALREADY_MATCH")

    def test_09_materialize_existing_different_policy_returns_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "candidate_policy.json"
            _write_json(target, {"status": "CANDIDATE", "different": True})
            result = materialize(target, package_dir=PACKAGE_DIR)
            self.assertEqual(result.status, "HOLD_TARGET_CONFLICT")

    def test_10_materialize_conflict_does_not_overwrite_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "candidate_policy.json"
            original = b'{"status":"CANDIDATE","sentinel":"unchanged"}\n'
            target.write_bytes(original)
            result = materialize(target, package_dir=PACKAGE_DIR)
            self.assertEqual(result.status, "HOLD_TARGET_CONFLICT")
            self.assertEqual(target.read_bytes(), original)

    def test_11_materialize_does_not_change_real_runtime_policy(self) -> None:
        before = _sha256(RUNTIME_POLICY)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "candidate_policy.json"
            materialize(target, package_dir=PACKAGE_DIR)
        self.assertEqual(_sha256(RUNTIME_POLICY), before)

    def test_12_materialize_does_not_change_active_canonical(self) -> None:
        before = _hashes(ACTIVE_PATHS)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "candidate_policy.json"
            materialize(target, package_dir=PACKAGE_DIR)
            protected = Path(directory) / "active" / "candidate_policy.json"
            with self.assertRaises(PackageFailure) as raised:
                materialize(protected, package_dir=PACKAGE_DIR)
            self.assertEqual(raised.exception.reason_code, "HOLD_PROTECTED_TARGET")
        self.assertEqual(_hashes(ACTIVE_PATHS), before)

    def test_13_materialize_does_not_change_pointer_files(self) -> None:
        before = _hashes(POINTER_PATHS)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "candidate_policy.json"
            materialize(target, package_dir=PACKAGE_DIR)
            protected = Path(directory) / "candidate_POINTER.json"
            with self.assertRaises(PackageFailure) as raised:
                materialize(protected, package_dir=PACKAGE_DIR)
            self.assertEqual(raised.exception.reason_code, "HOLD_PROTECTED_TARGET")
        self.assertEqual(_hashes(POINTER_PATHS), before)

    def test_14_package_identity_replay_is_stable(self) -> None:
        first = check_package(package_dir=PACKAGE_DIR, runtime_policy_path=RUNTIME_POLICY)
        second = check_package(package_dir=PACKAGE_DIR, runtime_policy_path=RUNTIME_POLICY)
        self.assertEqual(first, second)
        self.assertEqual(canonical_sha256(load_strict_json(TRACKED_POLICY)), first.policy_sha256)

    def test_15_error_reason_codes_are_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"duplicate":1,"duplicate":2}\n', encoding="utf-8")
            nonfinite = Path(directory) / "nonfinite.json"
            nonfinite.write_text('{"value":Infinity}\n', encoding="utf-8")
            missing = Path(directory) / "missing.json"
            first_run: list[str] = []
            second_run: list[str] = []
            for _attempt in range(2):
                current = first_run if _attempt == 0 else second_run
                with self.assertRaises(PackageFailure) as raised:
                    load_strict_json(path)
                current.append(raised.exception.reason_code)
                with self.assertRaises(PackageFailure) as raised:
                    load_strict_json(nonfinite)
                current.append(raised.exception.reason_code)
                with self.assertRaises(PackageFailure) as raised:
                    load_strict_json(missing)
                current.append(raised.exception.reason_code)
            self.assertEqual(first_run, second_run)
            self.assertEqual(
                first_run,
                ["JSON_DUPLICATE_KEY", "JSON_NONFINITE_VALUE", "JSON_FILE_NOT_FOUND"],
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
