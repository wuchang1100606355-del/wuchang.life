import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT))
sys.path.insert(0, str(MODULE_ROOT.parent))

import drive_spool_projector as projector  # noqa: E402
from w7tp_gt_mesh import core as mesh_core  # noqa: E402
from w7tp_gt_mesh.spool import produce_drive_projection_envelopes  # noqa: E402


def canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def make_envelope(relative_path, artifact, **overrides):
    document = {
        "schema_id": projector.ENVELOPE_SCHEMA_ID,
        "projection_relative_path": relative_path,
        "artifact_sha256": digest(artifact),
        "artifact": artifact,
        "source_node_ref": "MSI-LOCAL",
        "packet_id": "packet-001",
        "logical_time": 7,
        "created_at": "2026-08-29T12:00:00+08:00",
    }
    document.update(overrides)
    without_hash = dict(document)
    document["envelope_sha256"] = digest(without_hash)
    return document


class ProjectorTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.spool = self.base / "spool"
        self.receipts = self.base / "receipts"
        self.drive = self.base / "drive" / "8D_ADI_INDEX"
        self.spool.mkdir()
        self.drive.mkdir(parents=True)
        for partition in projector.ALLOWED_PARTITIONS:
            (self.drive / partition).mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def install_test_core_binding(self):
        def canonical_loads(raw, require_canonical=False):
            value = json.loads(raw.decode("utf-8"))
            if require_canonical and canonical(value) != raw:
                raise ValueError("not canonical")
            return value

        previous = mesh_core._CORE
        mesh_core._CORE = mesh_core.CoreBindings(
            canonical_json_bytes=canonical,
            canonical_json_loads=canonical_loads,
            sha256_hex=lambda raw: hashlib.sha256(raw).hexdigest(),
            sha256_ref=lambda raw: "sha256:" + hashlib.sha256(raw).hexdigest(),
            object_store_type=object,
            build_delta=lambda _base, _target: {},
            apply_delta=lambda base, _delta: base,
        )
        self.addCleanup(setattr, mesh_core, "_CORE", previous)

    def write_envelope(self, name, document):
        path = self.spool / name
        path.write_bytes(canonical(document))
        return path

    def run_once(self, watch_state=None):
        return projector.run_once(
            self.spool,
            self.drive,
            self.receipts,
            watch_state=watch_state,
        )

    def test_valid_projection_and_two_immutable_receipts(self):
        artifact = {"node": "MSI", "state": "candidate"}
        envelope = make_envelope("01_NODE_INDEX/MSI/node.json", artifact)
        self.write_envelope("0001.json", envelope)

        summary = self.run_once()

        self.assertEqual("PASS_BYTES_PROJECTED", summary.state)
        result = summary.results[0]
        self.assertEqual("CREATED", result.artifact_write_state)
        target = self.drive / "01_NODE_INDEX" / "MSI" / "node.json"
        self.assertEqual(canonical(artifact), target.read_bytes())
        local_receipt = self.receipts / f"{result.receipt_id}.json"
        drive_receipt = self.drive / "08_RECEIPTS" / f"CLOUD_WRITE_RECEIPT_{result.receipt_id}.json"
        self.assertTrue(local_receipt.is_file())
        self.assertEqual(local_receipt.read_bytes(), drive_receipt.read_bytes())
        receipt = json.loads(local_receipt.read_text(encoding="utf-8"))
        self.assertEqual("NOT_AUTHORITY", receipt["authority_state"])
        self.assertEqual("NOT_ESTABLISHED", receipt["live_effect_state"])

    def test_repeat_accepts_only_identical_bytes_without_new_receipt(self):
        artifact = {"evidence": [1, 2, 3]}
        self.write_envelope("0001.json", make_envelope("04_EVIDENCE/e.json", artifact))
        first = self.run_once()
        receipt_id = first.results[0].receipt_id
        local_receipt = self.receipts / f"{receipt_id}.json"
        receipt_before = local_receipt.read_bytes()

        second = self.run_once()

        self.assertEqual("PASS_BYTES_PROJECTED", second.state)
        self.assertEqual("ALREADY_PRESENT_IDENTICAL", second.results[0].artifact_write_state)
        self.assertEqual("ALREADY_PRESENT_IDENTICAL", second.results[0].local_receipt_state)
        self.assertEqual("ALREADY_PRESENT_IDENTICAL", second.results[0].drive_receipt_state)
        self.assertEqual(receipt_before, local_receipt.read_bytes())
        self.assertEqual(1, len(list(self.receipts.glob("*.json"))))

    def test_receipt_validation_is_linear_per_run(self):
        for index in range(3):
            self.write_envelope(
                f"{index:04d}.json",
                make_envelope(
                    f"04_EVIDENCE/linear-{index}.json",
                    {"value": index},
                    packet_id=f"packet-{index}",
                ),
            )
        first = self.run_once()
        self.assertEqual(3, first.passed)

        original_validator = projector._validated_receipt_document
        with mock.patch.object(
            projector,
            "_validated_receipt_document",
            wraps=original_validator,
        ) as validator:
            second = self.run_once()

        self.assertEqual(3, second.passed)
        self.assertEqual(6, validator.call_count)

    def test_watch_state_skips_unchanged_successful_envelope(self):
        self.write_envelope(
            "0001.json",
            make_envelope("04_EVIDENCE/watch.json", {"value": 1}),
        )
        watch_state = projector.WatchState()
        first = self.run_once(watch_state)
        self.assertEqual("PASS_BYTES_PROJECTED", first.state)

        with mock.patch.object(
            projector,
            "process_envelope",
            wraps=projector.process_envelope,
        ) as process:
            second = self.run_once(watch_state)

        self.assertEqual("IDLE_NO_NEW_OR_CHANGED_ENVELOPES", second.state)
        self.assertEqual(0, second.processed)
        self.assertEqual((), second.results)
        process.assert_not_called()

    def test_watch_state_processes_only_new_envelope(self):
        self.write_envelope(
            "0001.json",
            make_envelope("04_EVIDENCE/first-watch.json", {"value": 1}),
        )
        watch_state = projector.WatchState()
        first = self.run_once(watch_state)
        self.assertEqual(1, first.processed)
        self.write_envelope(
            "0002.json",
            make_envelope(
                "04_EVIDENCE/second-watch.json",
                {"value": 2},
                packet_id="packet-002",
            ),
        )

        second = self.run_once(watch_state)

        self.assertEqual("PASS_BYTES_PROJECTED", second.state)
        self.assertEqual(1, second.processed)
        self.assertEqual("0002.json", second.results[0].envelope_file)

    def test_watch_state_revalidates_changed_spool_path(self):
        path = self.write_envelope(
            "fixed-watch-name.json",
            make_envelope("04_EVIDENCE/watch-first.json", {"value": 1}),
        )
        watch_state = projector.WatchState()
        first = self.run_once(watch_state)
        self.assertEqual("PASS_BYTES_PROJECTED", first.state)
        path.write_bytes(
            canonical(
                make_envelope(
                    "04_EVIDENCE/watch-second.json",
                    {"value": "changed-and-longer"},
                )
            )
        )

        second = self.run_once(watch_state)

        self.assertEqual("HOLD", second.state)
        self.assertEqual(
            "ENVELOPE_SPOOL_ENVELOPE_PATH_REBOUND",
            second.results[0].code,
        )
        self.assertFalse((self.drive / "04_EVIDENCE" / "watch-second.json").exists())

    def test_watch_state_does_not_cache_hold(self):
        (self.drive / "05_CONFLICT").rmdir()
        self.write_envelope(
            "0001.json",
            make_envelope("05_CONFLICT/retry.json", {"value": 1}),
        )
        watch_state = projector.WatchState()
        first = self.run_once(watch_state)
        self.assertEqual("HOLD", first.state)
        self.assertEqual({}, watch_state.successful_coordinates)
        (self.drive / "05_CONFLICT").mkdir()

        second = self.run_once(watch_state)

        self.assertEqual("PASS_BYTES_PROJECTED", second.state)
        self.assertEqual(1, second.processed)

    def test_fresh_watch_state_reconciles_missing_drive_receipt(self):
        self.write_envelope(
            "0001.json",
            make_envelope("04_EVIDENCE/reconcile.json", {"value": 1}),
        )
        first = self.run_once(projector.WatchState())
        receipt_id = first.results[0].receipt_id
        local_receipt = self.receipts / f"{receipt_id}.json"
        drive_receipt = (
            self.drive
            / "08_RECEIPTS"
            / f"CLOUD_WRITE_RECEIPT_{receipt_id}.json"
        )
        drive_receipt.unlink()

        second = self.run_once(projector.WatchState())

        self.assertEqual("PASS_BYTES_PROJECTED", second.state)
        self.assertEqual("ALREADY_PRESENT_IDENTICAL", second.results[0].artifact_write_state)
        self.assertEqual("ALREADY_PRESENT_IDENTICAL", second.results[0].local_receipt_state)
        self.assertEqual("CREATED", second.results[0].drive_receipt_state)
        self.assertEqual(local_receipt.read_bytes(), drive_receipt.read_bytes())

    def test_existing_different_bytes_are_never_overwritten(self):
        target = self.drive / "04_EVIDENCE" / "conflict.json"
        original = b'{"existing":true}'
        target.write_bytes(original)
        self.write_envelope(
            "0001.json",
            make_envelope("04_EVIDENCE/conflict.json", {"incoming": True}),
        )

        summary = self.run_once()

        self.assertEqual("HOLD", summary.state)
        self.assertEqual("ARTIFACT_EXISTING_TARGET_BYTES_CONFLICT", summary.results[0].code)
        self.assertEqual(original, target.read_bytes())
        self.assertEqual([], list(self.receipts.glob("*.json")))

    def test_artifact_hash_mismatch_is_rejected_before_drive_write(self):
        envelope = make_envelope("04_EVIDENCE/bad.json", {"value": 1})
        envelope["artifact_sha256"] = "0" * 64
        without_hash = dict(envelope)
        without_hash.pop("envelope_sha256")
        envelope["envelope_sha256"] = digest(without_hash)
        self.write_envelope("0001.json", envelope)

        summary = self.run_once()

        self.assertEqual("ARTIFACT_SHA256_MISMATCH", summary.results[0].code)
        self.assertFalse((self.drive / "04_EVIDENCE" / "bad.json").exists())

    def test_envelope_hash_mismatch_is_rejected(self):
        envelope = make_envelope("04_EVIDENCE/bad-envelope.json", {"value": 1})
        envelope["envelope_sha256"] = "f" * 64
        self.write_envelope("0001.json", envelope)

        summary = self.run_once()

        self.assertEqual("ENVELOPE_SHA256_MISMATCH", summary.results[0].code)

    def test_path_traversal_and_unallowlisted_partition_are_rejected(self):
        cases = {
            "traversal.json": "04_EVIDENCE/../escape.json",
            "absolute.json": "/04_EVIDENCE/escape.json",
            "backslash.json": "04_EVIDENCE\\escape.json",
            "other.json": "10_OTHER/escape.json",
        }
        for name, relative_path in cases.items():
            self.write_envelope(name, make_envelope(relative_path, {"value": name}))

        summary = self.run_once()

        self.assertEqual("HOLD", summary.state)
        self.assertEqual(4, summary.held)
        self.assertFalse((self.drive / "escape.json").exists())

    def test_github_partition_requires_exact_d4_evidence_gate(self):
        accepted = {
            "dimension": "D4_EVIDENCE",
            "authority_state": "EVIDENCE_ONLY",
            "live_effect_state": "NOT_ESTABLISHED_BY_GIT",
            "coordinate": {"object_id": "opaque"},
        }
        rejected = dict(accepted, authority_state="AUTHORITY")
        self.write_envelope("0001.json", make_envelope("07_GITHUB/coordinates/ok.json", accepted))
        self.write_envelope("0002.json", make_envelope("07_GITHUB/coordinates/reject.json", rejected))

        summary = self.run_once()

        self.assertEqual("HOLD", summary.state)
        self.assertEqual("PASS_BYTES_PROJECTED", summary.results[0].state)
        self.assertEqual("GITHUB_PROJECTION_AUTHORITY_GATE_FAILED", summary.results[1].code)
        self.assertTrue((self.drive / "07_GITHUB" / "coordinates" / "ok.json").is_file())
        self.assertFalse((self.drive / "07_GITHUB" / "coordinates" / "reject.json").exists())

    def test_spool_cannot_target_projector_generated_receipt_name(self):
        name = "CLOUD_WRITE_RECEIPT_" + ("a" * 64) + ".json"
        self.write_envelope("0001.json", make_envelope(f"08_RECEIPTS/{name}", {"value": 1}))

        summary = self.run_once()

        self.assertEqual("PROJECTOR_RECEIPT_TARGET_RESERVED", summary.results[0].code)

    def test_missing_allowlisted_partition_is_hold_and_not_created(self):
        (self.drive / "05_CONFLICT").rmdir()
        self.write_envelope("0001.json", make_envelope("05_CONFLICT/c.json", {"value": 1}))

        summary = self.run_once()

        self.assertEqual("ARTIFACT_DRIVE_ALLOWLIST_PARTITION_MISSING", summary.results[0].code)
        self.assertFalse((self.drive / "05_CONFLICT").exists())

    def test_receipt_path_inside_drive_is_rejected_before_directory_creation(self):
        unsafe_receipt_dir = self.drive / "04_EVIDENCE" / "accidental-local-receipts"
        self.assertFalse(unsafe_receipt_dir.exists())

        with self.assertRaises(projector.SetupHold) as caught:
            projector.run_once(self.spool, self.drive, unsafe_receipt_dir)

        self.assertEqual(
            "RECEIPT_DIR_MUST_BE_LOCAL_OUTSIDE_DRIVE_ROOT",
            caught.exception.code,
        )
        self.assertFalse(unsafe_receipt_dir.exists())

    def test_drive_receipt_conflict_does_not_overwrite(self):
        envelope = make_envelope("04_EVIDENCE/value.json", {"value": 1})
        self.write_envelope("0001.json", envelope)
        receipt_id = projector._receipt_id(envelope["envelope_sha256"])
        drive_receipt = self.drive / "08_RECEIPTS" / f"CLOUD_WRITE_RECEIPT_{receipt_id}.json"
        original = b'{"foreign":true}'
        drive_receipt.write_bytes(original)

        summary = self.run_once()

        self.assertEqual("HOLD", summary.state)
        self.assertEqual("DRIVE_RECEIPT_EXISTING_TARGET_BYTES_CONFLICT", summary.results[0].code)
        self.assertEqual(original, drive_receipt.read_bytes())
        self.assertTrue((self.receipts / f"{receipt_id}.json").is_file())

    def test_successful_spool_path_cannot_be_rebound_to_new_bytes(self):
        path = self.write_envelope(
            "fixed-name.json",
            make_envelope("04_EVIDENCE/first.json", {"value": 1}),
        )
        first = self.run_once()
        self.assertEqual("PASS_BYTES_PROJECTED", first.state)
        path.write_bytes(canonical(make_envelope("04_EVIDENCE/second.json", {"value": 2})))

        second = self.run_once()

        self.assertEqual("HOLD", second.state)
        self.assertEqual(
            "ENVELOPE_SPOOL_ENVELOPE_PATH_REBOUND",
            second.results[0].code,
        )
        self.assertFalse((self.drive / "04_EVIDENCE" / "second.json").exists())

    def test_nested_producer_style_spool_tree_is_read_recursively(self):
        artifact = {"schema_id": "W7TP_GT_MESH_NODE_INDEX_V21", "node": "MSI"}
        envelope = make_envelope("01_NODE_INDEX/MSI/node/value.json", artifact)
        nested = self.spool / "01_NODE_INDEX" / "MSI" / "node" / "value.json"
        nested.parent.mkdir(parents=True)
        nested.write_bytes(canonical(envelope))

        summary = self.run_once()

        self.assertEqual("PASS_BYTES_PROJECTED", summary.state)
        self.assertEqual(
            "01_NODE_INDEX/MSI/node/value.json",
            summary.results[0].envelope_file,
        )
        self.assertEqual(
            canonical(artifact),
            (self.drive / "01_NODE_INDEX" / "MSI" / "node" / "value.json").read_bytes(),
        )

    def test_live_producer_to_projector_contract_round_trip(self):
        self.install_test_core_binding()
        snapshot = {
            "source_node_ref": "sha256:" + ("1" * 64),
            "logical_time": 11,
            "node": {"node_id": "MSI", "observation_state": "PRESENT"},
            "services": [],
            "containers": [],
            "curated_files": [],
            "listeners": [],
            "git_evidence": [
                {
                    "dimension": "D4_EVIDENCE",
                    "authority_state": "EVIDENCE_ONLY",
                    "live_effect_state": "NOT_ESTABLISHED_BY_GIT",
                    "coordinate": {"object_id": "opaque-integration-coordinate"},
                }
            ],
            "probe_evidence": [],
        }
        packet = {
            "schema_id": "W7TP_GT_MESH_PACKET_V21",
            "envelope": {"packet_id": "packet-integration-001"},
        }
        profile = {
            "schema_id": "W7TP_GT_MESH_DOMAIN_PROFILE_V21",
            "issued_at": "2026-08-29T12:00:00+08:00",
        }
        lineage = {
            "schema_id": "W7TP_GT_MESH_LINEAGE_V21",
            "source_node_ref": snapshot["source_node_ref"],
            "logical_time": snapshot["logical_time"],
        }

        emitted = produce_drive_projection_envelopes(
            self.spool,
            snapshot=snapshot,
            packet=packet,
            profile=profile,
            lineage=lineage,
        )
        summary = self.run_once()

        self.assertGreaterEqual(len(emitted), 4)
        self.assertEqual(len(emitted), summary.processed)
        self.assertEqual("PASS_BYTES_PROJECTED", summary.state)
        self.assertEqual(len(emitted), len(list(self.receipts.glob("*.json"))))
        for envelope_path in emitted:
            envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
            target = self.drive.joinpath(*envelope["projection_relative_path"].split("/"))
            self.assertEqual(canonical(envelope["artifact"]), target.read_bytes())
        generated_drive_receipts = list(
            (self.drive / "08_RECEIPTS").glob("CLOUD_WRITE_RECEIPT_*.json")
        )
        self.assertEqual(len(emitted), len(generated_drive_receipts))
        self.assertTrue(any("07_GITHUB" in path.parts for path in emitted))
        self.assertTrue(any((self.drive / "07_GITHUB").rglob("*.json")))


if __name__ == "__main__":
    unittest.main()
