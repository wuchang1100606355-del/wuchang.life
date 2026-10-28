import datetime as dt
import hashlib
import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from PIL import Image

from core.google_credit_discovery_channel import (
    build_converse_endpoint,
    inspect_discovery_credit_channel_status,
    query_discovery_credit_channel,
    validate_discovery_endpoint_url,
)
from core.xiaoj_brain_router import (
    PREBAKED_PATH,
    pack_72b_origin_cell,
    reconstruct_from_72b_origin_cell,
    route_xiaoj_brain,
)
import core.xiaoj_rig_decomposer as rig_mod
from tools.total_field.validate_state_field import classify


class TestP104BrainAndDiscovery(unittest.TestCase):
    def test_01_empty_and_invalid_query_hold(self):
        for bad in ("", "   ", None, 12345, "啡" * 305):
            res = route_xiaoj_brain(bad)
            self.assertFalse(res["ok"])
            self.assertEqual(res["state"], "HOLD_EMPTY_OR_INVALID_QUERY")

    def test_02_status_get_never_calls_cloud(self):
        with mock.patch("urllib.request.urlopen") as m_open:
            st = inspect_discovery_credit_channel_status("wuchang-menu-64")
            self.assertEqual(st["state"], "READY_GUARDED_ENDPOINT_CONFIGURED")
            self.assertFalse(st["network_called"])
            q_preview = query_discovery_credit_channel("測試64項菜單", execute_network=False)
            self.assertFalse(q_preview["network_called"])
            m_open.assert_not_called()

    def test_03_cloud_requires_exact_scope_and_seat(self):
        with mock.patch("urllib.request.urlopen") as m_open:
            res = query_discovery_credit_channel(
                "查詢無糖美式搭配",
                execute_network=True,
                seat_ref=None,
                authority_scope=None,
            )
            self.assertEqual(res["state"], "HOLD_CLOUD_SCOPE_OR_SEAT_MISSING")
            self.assertFalse(res["network_called"])
            m_open.assert_not_called()

    def test_04_discovery_endpoint_allowlist(self):
        url = build_converse_endpoint("wuchang-menu-64")
        self.assertTrue(url.startswith("https://discoveryengine.googleapis.com/"))
        with self.assertRaises(ValueError):
            validate_discovery_endpoint_url("http://discoveryengine.googleapis.com/v1beta/projects/my-j-483304/locations/global")
        with self.assertRaises(ValueError):
            validate_discovery_endpoint_url("https://aiplatform.googleapis.com/v1/projects/my-j-483304")
        with self.assertRaises(ValueError):
            build_converse_endpoint("unapproved-datastore-999")

    def test_05_no_member_plaintext_to_provider(self):
        for pii_q in ("我的電話是 0912-345-678 請查券", "身分證 A123456789", "帳號 user@example.com"):
            r1 = route_xiaoj_brain(pii_q)
            self.assertFalse(r1["ok"])
            self.assertEqual(r1["state"], "HOLD_MEMBER_PLAINTEXT_DETECTED")
            self.assertFalse(r1["contains_member_plaintext"])
            r2 = query_discovery_credit_channel(pii_q, execute_network=True, seat_ref="seat:01", authority_scope="cloud.discovery.converse")
            self.assertEqual(r2["state"], "HOLD_MEMBER_PLAINTEXT_DETECTED")

    def test_06_tier_fallback_and_cost_receipt(self):
        with mock.patch("core.xiaoj_brain_router._try_local_llm", return_value=None):
            res = route_xiaoj_brain("請問店內有沒有衣索比亞日曬淺焙單品？")
            self.assertTrue(res["ok"])
            self.assertEqual(res["tier"], "TIER1_COMMERCIAL_KNOWLEDGE_GRAPH")
            self.assertEqual(res["cost_twd"], 0.0)
            self.assertIn("cost_evidence", res)
            self.assertFalse(res["contains_member_plaintext"])


class TestP102PrebakedCells(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PREBAKED_PATH.read_text(encoding="utf-8"))
        cls.cells = cls.doc["cells"]

    def test_01_empty_query_hold(self):
        res = route_xiaoj_brain("")
        self.assertFalse(res["ok"])
        self.assertEqual(res["state"], "HOLD_EMPTY_OR_INVALID_QUERY")

    def test_02_ambiguous_partial_name(self):
        res = route_xiaoj_brain("咖啡")
        self.assertFalse(res["ok"])
        self.assertEqual(res["state"], "HOLD_AMBIGUOUS_PREBAKED_QUERY")
        self.assertGreater(len(res.get("candidates", [])), 1)

    def test_03_cell_schema_and_unique_ids(self):
        self.assertEqual(len(self.cells), 59)
        cids = set()
        for k, c in self.cells.items():
            cid = c["cell_id"]
            self.assertNotIn(cid, cids)
            cids.add(cid)
            self.assertTrue(isinstance(c.get("spoken_line"), str) and c["spoken_line"].strip())
            self.assertTrue(isinstance(c.get("category"), str) and c["category"].strip())
            self.assertIn(c.get("cell_kind"), ("PRODUCT_ITEM", "SYSTEM_INTERACTION"))
            self.assertIsInstance(c.get("price"), (int, float))
            self.assertIs(c.get("contains_member_plaintext"), False)

    def test_04_member_plaintext_excluded(self):
        res = route_xiaoj_brain("招牌咖啡 0988-111-222")
        self.assertFalse(res["ok"])
        self.assertEqual(res["state"], "HOLD_MEMBER_PLAINTEXT_DETECTED")

    def test_05_wire_size_reconstruction(self):
        for k, c in self.cells.items():
            pkt = pack_72b_origin_cell(k, c)
            self.assertEqual(len(pkt), 72)
            rec = reconstruct_from_72b_origin_cell(pkt, self.cells)
            self.assertEqual(rec["state"], "PASS_72B_ORIGIN_CELL_RECONSTRUCTED")
            self.assertEqual(rec["wire_bytes"], 72)
            self.assertEqual(rec["cell"]["cell_id"], c["cell_id"])


class TestP105ValidateStateField(unittest.TestCase):
    def _valid_doc(self):
        now_iso = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        s_ptr = "a" * 64
        s_con = "b" * 64
        s_fld = "c" * 64
        s_aut = "d" * 64
        s_rec = "e" * 64
        rec_path = "runtime/total_field/receipts/r1.json"
        return {
            "schema_version": "w7tp-8d-adi-v23-verification/1.0",
            "observation": {
                "source_node": "taiji01",
                "root": "/home/taiji_admin/Taiji_Hub",
                "live_verified": True,
                "core_paths_clean": True,
                "trusted_producer": True,
                "branch": "codex/current-live-state-consolidation-20260915",
                "head": "7c7ae515ea7087f8ce994045eace05df919ed70e",
                "observed_at": now_iso,
            },
            "canonical": {
                "pointer": {
                    "exists": True, "tracked": True, "git_status": "CLEAN",
                    "sha256": s_ptr, "canonical_sha256": s_con,
                    "canonical_id": "W7TP_8D_ADI_V2_3", "version": "2.3", "state": "ACTIVE_CANONICAL",
                },
                "contract": {
                    "exists": True, "tracked": True, "git_status": "CLEAN",
                    "sha256": s_con, "canonical_id": "W7TP_8D_ADI_V2_3", "version": "2.3",
                },
                "field": {
                    "exists": True, "tracked": True, "git_status": "CLEAN",
                    "sha256": s_fld, "canonical_id": "W7TP_8D_ADI_V2_3", "version": "2.3",
                    "state": "ACTIVE_TRUE8D_V23",
                    "dimensions": [
                        "Intent", "State", "Coordinate", "Evidence",
                        "Execution/Policy", "Generative State Transmission",
                        "Risk/Isolation", "Envelope/Authority",
                    ],
                    "activation_receipt_ref": rec_path,
                },
                "authority": {
                    "exists": True, "tracked": True, "git_status": "CLEAN",
                    "sha256": s_aut, "state": "ACTIVE_TOTAL_FIELD_AUTHORITY",
                    "contract_state": "ACTIVE_FORMAL",
                    "formal_decision_authority": True, "formal_seal_authority": True,
                },
                "receipt": {
                    "reference_exists": True, "referenced_by_active_field": True,
                    "exists": True, "tracked": True, "git_status": "CLEAN",
                    "path": rec_path, "sha256": s_rec, "state": "ACTIVATED",
                    "loaded_canonical_id": "W7TP_8D_ADI_V2_3", "loaded_version": "2.3",
                    "completion_mode": "CURRENT_FIELD_AFTER_ACTIVATION",
                    "pointer_postimage_sha256": s_ptr,
                    "field_postimage_sha256": s_fld,
                    "authority_postimage_sha256": s_aut,
                },
            },
            "request": {"mode": "READ_ONLY", "effect": "INSPECT_STATE"},
        }

    def test_01_missing_exact_receipt_hold(self):
        doc = self._valid_doc()
        del doc["canonical"]["receipt"]
        res = classify(doc)
        self.assertEqual(res["decision"], "HOLD_CONTRACT_OR_EVIDENCE_INVALID")

    def test_02_sha_postimage_mismatch_hold(self):
        doc = self._valid_doc()
        doc["canonical"]["receipt"]["pointer_postimage_sha256"] = "f" * 64
        res = classify(doc)
        self.assertEqual(res["decision"], "HOLD_CONTRACT_OR_EVIDENCE_INVALID")
        self.assertIn("BINDING:pointer_postimage_sha256", res["issues"])

    def test_03_boolean_type_strictness(self):
        doc = self._valid_doc()
        doc["observation"]["live_verified"] = 1
        res = classify(doc)
        self.assertEqual(res["decision"], "HOLD_CONTRACT_OR_EVIDENCE_INVALID")
        self.assertIn("MISMATCH:observation.live_verified", res["issues"])

    def test_04_readonly_effect_scope_reject(self):
        doc = self._valid_doc()
        doc["request"]["mode"] = "READ_ONLY"
        doc["request"]["effect"] = "DEPLOY_AND_RESTART_SERVICE"
        res = classify(doc)
        self.assertEqual(res["decision"], "HOLD_CONTRACT_OR_EVIDENCE_INVALID")
        self.assertIn("FORBIDDEN_EFFECT_IN_READ_ONLY:request.effect", res["issues"])

    def test_05_stale_future_timestamp_hold(self):
        doc_stale = self._valid_doc()
        doc_stale["observation"]["observed_at"] = "2020-01-01T00:00:00+00:00"
        self.assertIn("STALE:observation.observed_at", classify(doc_stale)["issues"])

        doc_naive = self._valid_doc()
        doc_naive["observation"]["observed_at"] = "2026-10-28T12:00:00"
        self.assertIn("INVALID:observation.observed_at_timezone", classify(doc_naive)["issues"])

    def test_06_untrusted_producer_binding(self):
        doc = self._valid_doc()
        doc["observation"]["trusted_producer"] = False
        res = classify(doc, verify_live_files=True)
        self.assertEqual(res["decision"], "HOLD_CONTRACT_OR_EVIDENCE_INVALID")
        self.assertIn("UNTRUSTED_PRODUCER:observation.trusted_producer", res["issues"])


class TestP103XiaojRigDecomposer(unittest.TestCase):
    def _create_valid_sources(self, src_dir: Path):
        c_im = Image.new("RGBA", (400, 400), (220, 180, 170, 255))
        c_im.save(src_dir / "closeup.webp", "WEBP", lossless=True)
        g_im = Image.new("RGBA", (600, 400), (210, 175, 165, 255))
        g_im.save(src_dir / "grid24.png", "PNG")
        u_im = Image.new("RGBA", (600, 600), (200, 190, 185, 255))
        u_im.save(src_dir / "uniform.png", "PNG")

    def test_01_import_has_no_write_effect(self):
        with mock.patch("pathlib.Path.mkdir") as m_mkdir:
            importlib.reload(rig_mod)
            m_mkdir.assert_not_called()

    def test_02_missing_or_corrupt_image_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            tp = Path(tmp)
            with self.assertRaises(ValueError):
                rig_mod.decompose_all(source_dir=tp, output_dir=tp / "out", fast_mode=True)
            self._create_valid_sources(tp)
            # 將 closeup.webp 故意存成 PNG 格式觸發格式不符拒絕
            Image.new("RGBA", (400, 400), (100, 100, 100, 255)).save(tp / "closeup.webp", "PNG")
            with self.assertRaises(ValueError):
                rig_mod.decompose_all(source_dir=tp, output_dir=tp / "out2", fast_mode=True)

    def test_03_full_24_cell_output_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            tp = Path(tmp)
            src = tp / "src"
            out = tp / "out"
            src.mkdir()
            self._create_valid_sources(src)
            manifest = rig_mod.decompose_all(source_dir=src, output_dir=out, fast_mode=True)
            self.assertTrue(manifest["ready"])
            self.assertEqual(len(manifest["cells"]), 24)
            self.assertEqual(len(manifest["tweens"]), 24)
            for nm in manifest["cells"]:
                self.assertEqual(len(manifest["tweens"][nm]), 3)
                with Image.open(out / f"cell_{nm}.webp") as im_c:
                    self.assertEqual(im_c.size, (400, 400))

    def test_04_atomic_output_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            tp = Path(tmp)
            src = tp / "src"
            out = tp / "out"
            src.mkdir()
            self._create_valid_sources(src)
            (src / "uniform.png").write_bytes(b"corrupt_bytes_not_a_png" * 20)
            with self.assertRaises(ValueError):
                rig_mod.decompose_all(source_dir=src, output_dir=out, fast_mode=True)
            self.assertFalse((out / "manifest.json").exists())

    def test_05_deterministic_output_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tp = Path(tmp)
            src = tp / "src"
            out1 = tp / "out1"
            out2 = tp / "out2"
            src.mkdir()
            self._create_valid_sources(src)
            m1 = rig_mod.decompose_all(source_dir=src, output_dir=out1, fast_mode=True)
            m2 = rig_mod.decompose_all(source_dir=src, output_dir=out2, fast_mode=True)
            self.assertEqual(m1["sha256_receipts"], m2["sha256_receipts"])

    def test_06_output_path_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tp = Path(tmp)
            src = tp / "src"
            src.mkdir()
            self._create_valid_sources(src)
            with self.assertRaises(ValueError):
                rig_mod.decompose_all(source_dir=src, output_dir=Path("/etc/forbidden_rig_out"), fast_mode=True)


if __name__ == "__main__":
    unittest.main()
