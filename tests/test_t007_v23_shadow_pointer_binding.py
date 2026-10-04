import copy
import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.total_field import w7tp_v2_3_candidate_source as source

ROOT = Path(__file__).resolve().parents[1]

def load_shadow(version):
    schema = source.V23_CANONICAL_SCHEMA_REF if version == "2.3" else "schemas/w7tp_8d_multipurpose_packet_canonical_v2_1.schema.json"
    spec = importlib.util.spec_from_file_location("t007_shadow_vector", ROOT / "tools/total_field/w7tp_true8d_contract_sandbox.py")
    module = importlib.util.module_from_spec(spec)
    with patch.object(source, "active_canonical_binding", return_value={"version": version, "machine_schema_path": schema}):
        spec.loader.exec_module(module)
    return module

class V23ShadowPointerBindingTest(unittest.TestCase):
    def test_v23_shadow_uses_successor_schema_without_effect(self):
        m = load_shadow("2.3")
        self.assertEqual(m.ACTIVE_CONTRACT_VERSION, "W7TP-TRUE8D-MACHINE-CONTRACT/2.3")
        for profile in m.PROFILES:
            for consumer in m.CONSUMERS:
                result = m.run_shadow_case(profile, consumer)
                self.assertEqual(result["state"], "PASS")
                self.assertEqual(result["side_effect_count"], 0)
                self.assertFalse(result["commit_applied"])
                self.assertFalse(result["seal_applied"])

    def test_v23_rejects_legacy_schema_under_active_version(self):
        m = load_shadow("2.3")
        route = json.loads(m.ROUTE_TABLE_PATH.read_text())["routes"]["GENERIC"]
        common = m._common("D1", "GENERIC", "INTENT", route)
        common["canonical_schema_ref"] = m.V21_COMPAT_CANONICAL_SCHEMA_REF
        with self.assertRaises(m.ContractSandboxError):
            m.validate_common_input(common, "D1")

    def test_v21_retains_explicit_compatibility_with_v23_active(self):
        old = load_shadow("2.1")
        new = load_shadow("2.3")
        route = json.loads(old.ROUTE_TABLE_PATH.read_text())["routes"]["GENERIC"]
        commons = {d: old._common(d, "GENERIC", "INTENT", route) for d in old.FIELD_IDS}
        outputs = old._d1_d7_outputs("GENERIC", "INTENT", route, commons)
        for d, output in outputs.items():
            new.validate_projection_contract(commons[d], output)
