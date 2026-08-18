from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "tools" / "total_field" / "verify_v2_1_schema_binding.py"
SPEC = importlib.util.spec_from_file_location("verify_v2_1_schema_binding", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
binding = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(binding)


class V21SchemaBindingTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.schema_rel = Path("schemas/w7tp_8d_multipurpose_packet_canonical_v2_1.schema.json")
        self.pointer_rel = binding.DEFAULT_POINTER_REL
        self.receipt_rel = binding.DEFAULT_RECEIPT_REL
        self.manifest_rel = binding.DEFAULT_MANIFEST_REL
        self._git("init")
        self._git("config", "user.email", "tests@example.com")
        self._git("config", "user.name", "Codex Tests")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        )

    def _write_json(self, rel_path: Path, payload: dict[str, Any]) -> str:
        path = self.root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _commit_schema(self, payload: dict[str, Any], message: str = "commit schema") -> str:
        self._write_json(self.schema_rel, payload)
        self._git("add", self.schema_rel.as_posix())
        self._git("commit", "-m", message)
        return hashlib.sha256((self.root / self.schema_rel).read_bytes()).hexdigest()

    def _schema_v21(self) -> dict[str, Any]:
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://wuchang.life/schemas/w7tp_8d_multipurpose_packet_canonical_v2_1.schema.json",
            "title": "W7TP 8D Multipurpose Generative Transmission Packet Canonical V2.1",
            "type": "object",
            "additionalProperties": False,
            "required": ["canonical_id", "version", "canonical_binding", "envelope"],
            "properties": {
                "canonical_id": {"const": binding.DEFAULT_CANONICAL_ID},
                "version": {"const": "2.1"},
                "canonical_binding": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "canonical_path",
                        "canonical_sha256",
                        "parent_version",
                        "parent_path",
                        "parent_sha256",
                        "migration_mode",
                    ],
                    "properties": {
                        "canonical_path": {"const": binding.DEFAULT_CANONICAL_PATH},
                        "canonical_sha256": {"const": binding.DEFAULT_CANONICAL_SHA256},
                        "parent_version": {"const": "2.0"},
                        "parent_path": {"const": binding.DEFAULT_PARENT_PATH},
                        "parent_sha256": {"const": binding.DEFAULT_PARENT_SHA256},
                        "migration_mode": {"const": "APPEND_ONLY_SUCCESSOR"},
                    },
                },
                "envelope": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["payload_sha256", "canonical_json_sha256"],
                    "properties": {
                        "payload_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                        "canonical_json_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    },
                },
            },
        }

    def _schema_v21_drift(self) -> dict[str, Any]:
        payload = self._schema_v21()
        payload["title"] = "W7TP 8D Multipurpose Generative Transmission Packet Canonical V2.1 Drift"
        return payload

    def _schema_v2_impostor(self) -> dict[str, Any]:
        payload = self._schema_v21()
        payload["properties"]["version"]["const"] = "2.0"
        return payload

    def _pointer(self, promoted_sha256: str) -> dict[str, Any]:
        return {
            "schema": "w7tp.total_field.active_w7tp_canonical_pointer.v1",
            "namespace": "w7tp_canonical",
            "state": "ACTIVE_CANONICAL",
            "canonical_id": binding.DEFAULT_CANONICAL_ID,
            "version": "2.1",
            "canonical_path": binding.DEFAULT_CANONICAL_PATH,
            "canonical_sha256": binding.DEFAULT_CANONICAL_SHA256,
            "machine_schema_path": self.schema_rel.as_posix(),
            "machine_schema_sha256": promoted_sha256,
            "promotion_receipt_path": self.receipt_rel.as_posix(),
            "promotion_receipt_sha256": "receipt-placeholder",
        }

    def _receipt(self, *, successor_sha256: str | None = None, pointer_path: str | None = None) -> dict[str, Any]:
        return {
            "schema": "w7tp.total_field.w7tp_canonical_successor_activation_receipt.v1",
            "state": "PASS_CANONICAL_SUCCESSOR_ACTIVATED_APPEND_ONLY",
            "target": {
                "canonical_id": binding.DEFAULT_CANONICAL_ID,
                "version": "2.1",
                "successor_path": binding.DEFAULT_CANONICAL_PATH,
                "successor_sha256": successor_sha256 or binding.DEFAULT_CANONICAL_SHA256,
                "active_pointer_path": pointer_path or self.pointer_rel.as_posix(),
            },
            "validation": {
                "pointer_exists": True,
                "pointer_points_to_successor": True,
                "pointer_object_sha256_match": True,
                "rollback_snapshot_present": True,
                "successor_manifest_not_modified": True,
            },
        }

    def _manifest(self) -> dict[str, Any]:
        return {
            "schema": "W7TP-8D-CANONICAL-V2.1-FOUNDER-LOCKED-SUCCESSOR-MANIFEST/1.0",
            "state": "APPEND_ONLY_CANONICAL_SUCCESSOR_NOT_ACTIVATED",
            "source_canonical": {"path": "docs/total_field/base.md", "sha256": "x" * 64, "unchanged": True},
            "successor_canonical": {
                "path": binding.DEFAULT_CANONICAL_PATH,
                "sha256": binding.DEFAULT_CANONICAL_SHA256,
                "version": "2.1",
            },
            "adi_binding_receipt": {"binding_verification": "PASS"},
        }

    def _resolve(self) -> dict[str, Any]:
        return binding.resolve_schema_binding(
            self.root,
            pointer_rel=self.pointer_rel,
            receipt_rel=self.receipt_rel,
            manifest_rel=self.manifest_rel,
            schema_rel=self.schema_rel,
        )

    def test_01_correct_cf3_binding_passes(self) -> None:
        promoted_sha256 = self._commit_schema(self._schema_v21(), "promote schema")
        current_sha256 = self._write_json(self.schema_rel, self._schema_v21_drift())
        self._write_json(self.pointer_rel, self._pointer(promoted_sha256))
        self._write_json(self.receipt_rel, self._receipt())
        self._write_json(self.manifest_rel, self._manifest())

        result = self._resolve()

        self.assertEqual(result["state"], "PASS_PROMOTED_SCHEMA_ARTIFACT_RESOLVED")
        self.assertEqual(result["pointer_schema_sha256"], promoted_sha256)
        self.assertEqual(result["promotion_receipt_schema_sha256"], promoted_sha256)
        self.assertEqual(result["current_schema_sha256"], current_sha256)
        self.assertEqual(result["authoritative_schema_sha256"], promoted_sha256)
        self.assertEqual(result["current_4ac_status"], "UNSEALED_DRIFT")

    def test_02_schema_bytes_drift_without_promoted_artifact_holds(self) -> None:
        self._write_json(self.schema_rel, self._schema_v21_drift())
        unknown_sha256 = "a" * 64
        self._write_json(self.pointer_rel, self._pointer(unknown_sha256))
        self._write_json(self.receipt_rel, self._receipt())
        self._write_json(self.manifest_rel, self._manifest())

        result = self._resolve()

        self.assertEqual(result["state"], "SYSTEM_VALIDITY_HOLD")
        self.assertEqual(result["hold_code"], "PROMOTED_SCHEMA_ARTIFACT_NOT_RESOLVED")

    def test_03_pointer_and_receipt_mismatch_fails(self) -> None:
        promoted_sha256 = self._commit_schema(self._schema_v21(), "promote schema")
        self._write_json(self.pointer_rel, self._pointer(promoted_sha256))
        self._write_json(self.receipt_rel, self._receipt(pointer_path="runtime/total_field/other_pointer.json"))
        self._write_json(self.manifest_rel, self._manifest())

        result = self._resolve()

        self.assertEqual(result["state"], "SYSTEM_VALIDITY_HOLD")
        self.assertEqual(result["hold_code"], "POINTER_RECEIPT_OR_MANIFEST_MISMATCH")

    def test_04_unsealed_current_schema_cannot_promote(self) -> None:
        promoted_sha256 = self._commit_schema(self._schema_v21(), "promote schema")
        current_sha256 = self._write_json(self.schema_rel, self._schema_v21_drift())
        self._write_json(self.pointer_rel, self._pointer(promoted_sha256))
        self._write_json(self.receipt_rel, self._receipt())
        self._write_json(self.manifest_rel, self._manifest())

        result = self._resolve()

        self.assertNotEqual(current_sha256, promoted_sha256)
        self.assertEqual(result["authoritative_schema_sha256"], promoted_sha256)
        self.assertNotEqual(result["authoritative_schema_sha256"], current_sha256)

    def test_05_old_v2_cannot_impersonate_v21(self) -> None:
        promoted_sha256 = self._commit_schema(self._schema_v2_impostor(), "commit v2 impostor")
        self._write_json(self.pointer_rel, self._pointer(promoted_sha256))
        self._write_json(self.receipt_rel, self._receipt())
        self._write_json(self.manifest_rel, self._manifest())

        result = self._resolve()

        self.assertEqual(result["state"], "SYSTEM_VALIDITY_HOLD")
        self.assertEqual(result["hold_code"], "VERSION_NOT_V2_1")

    def test_06_missing_original_cf3_artifact_holds(self) -> None:
        self._write_json(self.schema_rel, self._schema_v21())
        self._write_json(self.pointer_rel, self._pointer("b" * 64))
        self._write_json(self.receipt_rel, self._receipt())
        self._write_json(self.manifest_rel, self._manifest())

        result = self._resolve()

        self.assertEqual(result["state"], "SYSTEM_VALIDITY_HOLD")
        self.assertEqual(result["hold_code"], "PROMOTED_SCHEMA_ARTIFACT_NOT_RESOLVED")

    def test_07_canonical_serialization_rejects_float_and_normalizes_unicode(self) -> None:
        self.assertEqual(binding.canonical_json({"e\u0301": "x"}), '{"é":"x"}')
        with self.assertRaises(binding.BindingResolutionError):
            binding.canonical_json({"value": 3.14})


if __name__ == "__main__":
    unittest.main()
