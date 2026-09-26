from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = ROOT / "products/eight_dimensional_generative_memory/w7tp_origin_cell_generative_v2.py"
CONSUMER = ROOT / "products/eight_dimensional_generative_memory/w7tp_gst_v23_runtime_consumer_candidate.py"
CONTRACT = ROOT / "products/eight_dimensional_generative_memory/w7tp_gst_v23_runtime_consumer_contract.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load_module("w7tp_gst_v23_runtime_test", ROOT / "services/w7tp_gst_v23_runtime.py")


class GstV23RuntimeDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = Path(tempfile.mkdtemp(prefix="test-gst-v23-runtime-"))
        product = self.temp / "products/eight_dimensional_generative_memory"
        product.mkdir(parents=True)
        for source in (ORIGIN, CONSUMER, CONTRACT):
            shutil.copy2(source, product / source.name)

        origin = load_module("w7tp_origin_cell_generative_v2_runtime_test", product / ORIGIN.name)
        prepared = origin.prepare_workspace(self.temp / "packet-workspace", origin.MIN_DATASET_MIB)
        self.packet = json.loads(Path(prepared["packet_path"]).read_text(encoding="utf-8"))

        contract_path = product / CONTRACT.name
        consumer_path = product / CONSUMER.name
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        activation_run = self.temp / "runtime/total_field/gst_v23_runtime_consumer/activation"
        activation_run.mkdir(parents=True)
        activation = {
            "schema_version": "w7tp-gst-v23-founder-runtime-activation/1",
            "state": "FOUNDER_DIRECT_RUNTIME_ACTIVATION_AUTHORIZED",
            "binding_id": contract["binding_id"],
            "founder_baseline": "W7TP_8D_ADI_V2.3",
            "contract_sha256": runtime.sha256_file(contract_path),
            "activation_scope": "GST_V23_RUNTIME_CONSUMER_BINDING_ONLY",
            "canonical_pointer_change": False,
            "service_restart": False,
            "rollback_operation": contract["rollback"]["operation"],
            "reviewed_commit": "synthetic-reviewed-commit",
            "founder_directive_ref": "SYNTHETIC_TEST_ONLY",
        }
        activation_path = activation_run / "FOUNDER_RUNTIME_ACTIVATION.json"
        activation_path.write_text(json.dumps(activation), encoding="utf-8")
        activation_result_path = activation_run / "receipts/ACTIVATION_RESULT.json"
        activation_result_path.parent.mkdir()
        activation_result = {
            "state": "PASS_FOUNDER_AUTHORIZED_GST_V23_RUNTIME_RECONSTRUCTION",
            "target_manifest_sha256": prepared["target_manifest_sha256"],
        }
        activation_result_path.write_text(json.dumps(activation_result), encoding="utf-8")

        self.binding_path = self.temp / "runtime/total_field/gst_v23_runtime_consumer/ACTIVE_BINDING.json"
        binding = {
            "state": "ACTIVE_FOUNDER_AUTHORIZED_RUNTIME_BINDING",
            "binding_id": contract["binding_id"],
            "founder_baseline": "W7TP_8D_ADI_V2.3",
            "consumer_path": str(consumer_path.relative_to(self.temp)),
            "consumer_sha256": runtime.sha256_file(consumer_path),
            "contract_path": str(contract_path.relative_to(self.temp)),
            "contract_sha256": runtime.sha256_file(contract_path),
            "activation_run": str(activation_run.relative_to(self.temp)),
            "activation_record_sha256": runtime.sha256_file(activation_path),
            "activation_result_sha256": runtime.sha256_file(activation_result_path),
            "last_verified_target_manifest_sha256": prepared["target_manifest_sha256"],
            "total_field_decision": "PASS",
        }
        self.binding_path.write_text(json.dumps(binding), encoding="utf-8")

        self.authority_path = self.temp / "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json"
        authority = {
            "state": "ACTIVE_TOTAL_FIELD_AUTHORITY",
            "contract_state": "ACTIVE_FORMAL",
            "formal_decision_authority": True,
            "allowed_effects": [runtime.REQUIRED_EFFECT],
        }
        self.authority_path.write_text(json.dumps(authority), encoding="utf-8")

        self.decision_path = self.temp / "evidence/d8/D8_FORMAL_CLOSURE_DECISION.json"
        self.decision_path.parent.mkdir(parents=True)
        decision = {
            "state": "PASS_D8_FORMAL_CLOSURE",
            "required_effect": runtime.REQUIRED_EFFECT,
            "total_field_decision": "PASS",
            "binding_id": contract["binding_id"],
            "active_binding_ref": str(self.binding_path.relative_to(self.temp)),
            "active_binding_sha256": runtime.sha256_file(self.binding_path),
            "authority_pointer_ref": str(self.authority_path.relative_to(self.temp)),
            "authority_pointer_sha256": runtime.sha256_file(self.authority_path),
            "consumer_sha256": runtime.sha256_file(consumer_path),
            "contract_sha256": runtime.sha256_file(contract_path),
            "activation_record_sha256": runtime.sha256_file(activation_path),
            "activation_result_ref": str(activation_result_path.relative_to(self.temp)),
            "activation_result_sha256": runtime.sha256_file(activation_result_path),
            "target_manifest_sha256": prepared["target_manifest_sha256"],
            "d8_closure": "CLOSED_FOR_EXACT_GST_V23_RUNTIME_CONSUMER_BINDING",
        }
        self.decision_path.write_text(json.dumps(decision), encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp, ignore_errors=True)

    def paths(self) -> dict:
        return {
            "root": self.temp,
            "active_binding_path": self.binding_path,
            "authority_path": self.authority_path,
            "d8_decision_path": self.decision_path,
        }

    def test_active_binding_status_is_fail_closed_and_ready(self) -> None:
        status = runtime.runtime_status(**self.paths())
        self.assertEqual(status["state"], "ACTIVE_GST_V23_USER_DELIVERY")
        self.assertTrue(status["runtime_activated"])
        self.assertTrue(status["formal_delivery"])
        self.assertEqual(status["total_field_decision"], "PASS")

        authority = json.loads(self.authority_path.read_text(encoding="utf-8"))
        authority["allowed_effects"].append("AUTHORIZE_ANOTHER_8D_ADI_RUNTIME_EFFECT")
        self.authority_path.write_text(json.dumps(authority), encoding="utf-8")
        successor_status = runtime.runtime_status(**self.paths())
        self.assertEqual(successor_status["state"], "ACTIVE_GST_V23_USER_DELIVERY")

    def test_real_packet_delivery_reconstructs_in_clean_workspace(self) -> None:
        result = runtime.deliver_packet(
            self.packet,
            **self.paths(),
            delivery_root=self.temp / "runtime/deliveries",
        )
        self.assertEqual(result["state"], "PASS_D8_AUTHORIZED_GST_V23_DELIVERY")
        self.assertEqual(result["differential_bytes"], 0)
        self.assertEqual(result["target_bytes_transmitted"], 0)
        self.assertGreater(result["reconstructed_bytes"], 32 * 1024 * 1024)
        self.assertTrue((self.temp / result["output_ref"]).is_dir())

    def test_semantic_purity_blocks_compression_and_delta_before_workspace(self) -> None:
        cases = []

        compressed = copy.deepcopy(self.packet)
        compressed["compressed_payload"] = "forbidden"
        cases.append(compressed)

        differential = copy.deepcopy(self.packet)
        differential["delta_payload"] = {"mode": "diff"}
        cases.append(differential)

        patched = copy.deepcopy(self.packet)
        patched["reconstruction_rules"][0]["patch_blob"] = "forbidden"
        cases.append(patched)

        for index, packet in enumerate(cases):
            delivery_root = self.temp / f"runtime/purity-block-{index}"
            with self.assertRaisesRegex(
                runtime.GstRuntimeHold,
                "HOLD_GST_RUNTIME_SEMANTIC_PURITY",
            ):
                runtime.deliver_packet(
                    packet,
                    **self.paths(),
                    delivery_root=delivery_root,
                )
            self.assertFalse(delivery_root.exists())

    def test_semantic_purity_blocks_previous_state_and_unknown_rule_fields(self) -> None:
        previous_state = copy.deepcopy(self.packet)
        previous_state["construction_conditions"]["previous_state_allowed"] = True
        with self.assertRaisesRegex(
            runtime.GstRuntimeHold,
            "HOLD_GST_RUNTIME_CONSTRUCTION_PURITY_CONTRACT",
        ):
            runtime.deliver_packet(
                previous_state,
                **self.paths(),
                delivery_root=self.temp / "runtime/previous-state-block",
            )

        unknown_rule_field = copy.deepcopy(self.packet)
        unknown_rule_field["reconstruction_rules"][0]["notes"] = "not executable rule data"
        with self.assertRaisesRegex(
            runtime.GstRuntimeHold,
            "HOLD_GST_RUNTIME_RULE_FIELDS_NOT_PURE",
        ):
            runtime.deliver_packet(
                unknown_rule_field,
                **self.paths(),
                delivery_root=self.temp / "runtime/unknown-rule-field-block",
            )

    def test_tampered_authority_fails_before_delivery_workspace(self) -> None:
        authority = json.loads(self.authority_path.read_text(encoding="utf-8"))
        authority["allowed_effects"] = []
        self.authority_path.write_text(json.dumps(authority), encoding="utf-8")
        delivery_root = self.temp / "runtime/forbidden-deliveries"
        with self.assertRaisesRegex(runtime.GstRuntimeHold, "HOLD_GST_RUNTIME_REQUIRED_EFFECT_NOT_ALLOWED"):
            runtime.deliver_packet(self.packet, **self.paths(), delivery_root=delivery_root)
        self.assertFalse(delivery_root.exists())


if __name__ == "__main__":
    unittest.main()
