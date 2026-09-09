import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import drive_materializer_23 as resolver


class Materializer23Test(unittest.TestCase):
    def test_rejects_path_escape(self):
        for value in ("../secret", "/absolute", "a/../../b"):
            with self.assertRaises(ValueError):
                resolver.safe_relative(value)

    def test_materializes_only_manifest_files_and_holds_extra(self):
        payload = b"voice-material"
        digest = hashlib.sha256(payload).hexdigest()
        manifest = {
            "schema": resolver.SCHEMA,
            "package_id": "voice-test",
            "D8_authority": {
                "cloud_role": "MATERIAL_ONLY",
                "runtime_decider": "TOTAL_FIELD",
            },
            "files": [{"path": "model.bin", "size": len(payload), "sha256": digest}],
        }
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            local_root = root_path / "local"
            receipt_root = root_path / "receipts"

            def fake_load(_remote, _package):
                return manifest

            def fake_rclone(*args, capture=False):
                if args[0] == "copyto" and str(args[1]).endswith("/raw/voice-test/model.bin"):
                    Path(args[2]).write_bytes(payload)
                return ""

            with mock.patch.object(resolver, "load_remote_manifest", fake_load), mock.patch.object(
                resolver, "run_rclone", fake_rclone
            ):
                first = resolver.materialize("remote:", "voice-test", local_root, receipt_root)
                self.assertEqual(first["decision"], "PASS_MATERIALIZED")
                self.assertEqual(len(first["changed"]), 1)
                extra = local_root / "voice-test" / "untracked.bin"
                extra.write_bytes(b"hold")
                second = resolver.materialize("remote:", "voice-test", local_root, receipt_root)
                self.assertEqual(second["decision"], "HOLD_UNREFERENCED_LOCAL_FILES")
                self.assertEqual(second["unreferenced_not_deleted"], ["untracked.bin"])

    def test_materialization_survives_read_only_cloud_receipt_path(self):
        payload = b"voice-material"
        digest = hashlib.sha256(payload).hexdigest()
        manifest = {
            "schema": resolver.SCHEMA,
            "package_id": "voice-read-only",
            "D8_authority": {"cloud_role": "MATERIAL_ONLY", "runtime_decider": "TOTAL_FIELD"},
            "files": [{"path": "model.bin", "size": len(payload), "sha256": digest}],
        }
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)

            def fake_rclone(*args, capture=False):
                if args[0] == "copyto" and "/raw/" in str(args[1]):
                    Path(args[2]).write_bytes(payload)
                    return ""
                raise resolver.subprocess.CalledProcessError(1, args)

            with mock.patch.object(resolver, "load_remote_manifest", return_value=manifest), mock.patch.object(
                resolver, "run_rclone", fake_rclone
            ):
                result = resolver.materialize(
                    "remote:", "voice-read-only", root_path / "local", root_path / "receipts"
                )
                self.assertEqual(result["decision"], "PASS_MATERIALIZED")
                self.assertEqual(
                    result["cloud_receipt_state"], "HOLD_EXTERNAL_CONNECTOR_WRITE_REQUIRED"
                )


if __name__ == "__main__":
    unittest.main()
