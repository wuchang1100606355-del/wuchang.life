#!/usr/bin/env python3
import importlib.util, json, tempfile, unittest
from pathlib import Path
P=Path(__file__).resolve().parent/"resolve_3d_behavior.py"
spec=importlib.util.spec_from_file_location("resolve_3d_behavior",P)
r=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

J="615f5ab25daab0fa326bfcf1c0e49d09c8f23dc8c9217d3876962937455cc205"
R1="98986d8e96a9822494172043c463cda35268289fb3e0b97b7656bb94076c7ca2"

class HumanSemanticRouterTest(unittest.TestCase):
    def test_single_human_semantic_two_real_models(self):
        a=r.resolve(J,"微笑");b=r.resolve(R1,"smile")
        self.assertNotEqual(a["model_sha256"],b["model_sha256"])
        self.assertNotEqual(a["control_targets"],b["control_targets"])
        self.assertEqual(a["source_semantic_control"],"VRMC_vrm.expressions.preset.happy")
        self.assertEqual(b["source_semantic_control"],"glTF_mesh.extras.targetNames")
        self.assertEqual([x["name"] for x in b["control_targets"]],["mouthSmileLeft","mouthSmileRight"])
        self.assertEqual(a["time_duration_ms"],b["time_duration_ms"])
        self.assertEqual(a["human_intent"],b["human_intent"])
    def test_unknown_model_has_no_fallback(self):
        with self.assertRaisesRegex(r.ModelRouteHold,"HOLD_MODEL_IDENTITY_NOT_UNIQUELY_BOUND"):
            r.resolve("f"*64,"微笑")
    def test_sha_invalid_hold(self):
        with self.assertRaisesRegex(r.ModelRouteHold,"HOLD_MODEL_SOURCE_SHA_INVALID"):
            r.resolve("not-hash","微笑")
    def test_unspecified_behavior_hold(self):
        with self.assertRaisesRegex(r.ModelRouteHold,"HOLD_BEHAVIOR_NOT_SUPPORTED"):
            r.resolve(J,"小J眨眼")
    def test_unverified_anatomical_mouth_requires_independent_evidence(self):
        for model in (J,R1):
            with self.subTest(model=model),self.assertRaisesRegex(r.ModelRouteHold,"HOLD_MOUTH_ANATOMICAL_POINT_NOT_INDEPENDENTLY_VERIFIED"):
                r.resolve(model,"微笑",require_anatomical_landmark=True)
    def test_disabled_effect_authority(self):
        for model in (J,R1):
            result=r.resolve(model,"smile")
            for forbidden in ("effect_execution_granted","d8_authority","canonical"):
                self.assertFalse(result[forbidden])
    def test_tampered_mapping_authority_hold(self):
        with tempfile.TemporaryDirectory() as td:
            data=json.loads(r.MAP.read_text())
            data["authority"]="CANONICAL"
            p=Path(td)/"tampered.json";p.write_text(json.dumps(data))
            with self.assertRaisesRegex(r.ModelRouteHold,"HOLD_MAPPING_AUTHORITY_DRIFT"):
                r.resolve(J,"微笑",registry_path=p)
    def test_duplicate_source_identity_hold(self):
        with tempfile.TemporaryDirectory() as td:
            data=json.loads(r.MAP.read_text())
            data["model_variants"].append(data["model_variants"][0])
            p=Path(td)/"dup.json";p.write_text(json.dumps(data))
            with self.assertRaisesRegex(r.ModelRouteHold,"HOLD_MODEL_IDENTITY_NOT_UNIQUELY_BOUND"):
                r.resolve(J,"smile",registry_path=p)

if __name__=="__main__":unittest.main(verbosity=2)
