from __future__ import annotations

import copy
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORIGIN_PATH = ROOT / (
    "products/eight_dimensional_generative_memory/"
    "w7tp_origin_cell_generative_v2.py"
)
MINIMUM_PATH = ROOT / (
    "products/eight_dimensional_generative_memory/"
    "w7tp_origin_state_minimum_packet_v1.py"
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


origin = load_module(ORIGIN_PATH, "origin_cell_for_minimum_packet_test")
minimum = load_module(MINIMUM_PATH, "minimum_packet_test_target")
class MinimumPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpfs_root = Path("/dev/shm")
        if not cls.tmpfs_root.is_dir():
            raise unittest.SkipTest("/dev/shm unavailable")
        cls.base = Path(
            tempfile.mkdtemp(
                prefix="w7tp-minimum-packet-test-",
                dir=cls.tmpfs_root,
            )
        )
        cls.source = cls.base / "source"
        origin.generate_target(
            cls.source,
            origin.MIN_DATASET_MIB,
            variant=23,
        )
        cls.packet = minimum.build_fixture_minimum_packet(
            cls.source,
            adi_coordinate_ref="adi:test:minimum-packet",
            state_ref="state:test:origin-family",
            state_version_ref="state-version:test:23",
            packet_ref="packet:test:minimum:23",
        )

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.base, ignore_errors=True)

    def test_packet_has_no_rule_body_diff_or_compression(self) -> None:
        serialized = minimum.canonical_json_bytes(self.packet)
        self.assertNotIn(b"reconstruction_rules", serialized)
        self.assertNotIn(b"execution_order", serialized)
        self.assertNotIn(b"compressed_payload", serialized)
        self.assertNotIn(b"delta", serialized)
        self.assertNotIn(b"patch_cells", serialized)
        self.assertFalse(
            self.packet["joint_state_field"]["D6"]["rule_body_transmitted"]
        )
        self.assertEqual(
            self.packet["joint_state_field"]["D6"][
                "target_bytes_transmitted"
            ],
            0,
        )

    def test_valid_packet_reconstructs_in_volatile_workset(self) -> None:
        workset_parent: Path | None = None
        with minimum.volatile_reconstruction(self.packet) as result:
            workset = result["workset_path"]
            workset_parent = workset.parent
            self.assertTrue(workset.is_dir())
            receipt = result["receipt"]
            self.assertEqual(
                receipt["state"],
                "PASS_VOLATILE_LOCAL_RULE_RECONSTRUCTION",
            )
            self.assertFalse(receipt["persistent_materialization"])
            self.assertFalse(receipt["rule_body_transmitted"])
            self.assertEqual(
                receipt["target_manifest_sha256"],
                self.packet["verification"][
                    "expected_target_manifest_sha256"
                ],
            )
        assert workset_parent is not None
        self.assertFalse(workset_parent.exists())

    def test_packet_hash_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.packet)
        tampered["minimum_new_information"]["variant"] += 1
        with self.assertRaisesRegex(
            minimum.MinimumPacketHold,
            "HOLD_MINIMUM_PACKET_SELF_HASH_MISMATCH",
        ):
            minimum.validate_minimum_packet(tampered)
    def test_unknown_local_rule_ref_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.packet)
        tampered["rule_binding"]["rule_ref"] = "local-rule:missing"
        tampered["packet_sha256"] = minimum.packet_sha256(tampered)
        with self.assertRaisesRegex(
            minimum.MinimumPacketHold,
            "HOLD_LOCAL_RULE_REF_UNRESOLVED",
        ):
            minimum.validate_minimum_packet(tampered)

    def test_cloud_packet_cannot_carry_rule_body(self) -> None:
        tampered = copy.deepcopy(self.packet)
        tampered["reconstruction_rules"] = []
        tampered["packet_sha256"] = minimum.packet_sha256(tampered)
        with self.assertRaisesRegex(
            minimum.MinimumPacketHold,
            "HOLD_MINIMUM_PACKET_SHAPE_INVALID",
        ):
            minimum.validate_minimum_packet(tampered)

    def test_secret_memory_backend_is_available_on_taiji01(self) -> None:
        probe = minimum.probe_secret_memory()
        self.assertTrue(probe["supported"])
        self.assertEqual(probe["backend"], "MEMFD_SECRET")


if __name__ == "__main__":
    unittest.main()
