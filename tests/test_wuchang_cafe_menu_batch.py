import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "Taiji_Odoo/addons/wuchang_cafe_menu_options/services"
PACKAGE = "wuchang_menu_test_services"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(PATH)]
sys.modules[PACKAGE] = package
spec = importlib.util.spec_from_file_location(PACKAGE + ".menu_batch_governance", PATH / "menu_batch_governance.py")
BATCH = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BATCH)
from wuchang_menu_test_services.menu_change_governance import MenuChangeGovernanceError, build_odoo_product_thing_code


class MenuBatchTest(unittest.TestCase):
    def snapshot(self, item=1):
        return {"thing_code": build_odoo_product_thing_code(1, item), "name": "隔離測試商品",
                "list_price": 85, "pos_category_ids": [2], "option_group_id": None,
                "image_sha256": None, "active": True, "available_in_pos": True}

    def test_preview_does_not_mutate_and_zero_price_is_valid(self):
        before = self.snapshot()
        preview = BATCH.build_batch_preview([before], "set_price", 0)
        self.assertEqual(before["list_price"], 85)
        self.assertEqual(preview["rows"][0]["diff"]["list_price"], {"before": 85, "after": 0})
        self.assertFalse(preview["product_write"])

    def test_noop_has_no_request_and_deterministic_hash(self):
        preview = BATCH.build_batch_preview([self.snapshot()], "set_price", 85)
        self.assertEqual(preview["changed_count"], 0)
        self.assertEqual(preview, BATCH.build_batch_preview([self.snapshot()], "set_price", 85))

    def test_duplicate_missing_identity_and_batch_limit(self):
        for snapshots in [[], [self.snapshot()] * 2, [self.snapshot(i) for i in range(1, 102)],
                          [{**self.snapshot(), "thing_code": ""}]]:
            with self.assertRaises(MenuChangeGovernanceError):
                BATCH.build_batch_preview(snapshots, "pause")

    def test_invalid_price_and_operations(self):
        for value in [-1, True, "85", float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                BATCH.build_batch_preview([self.snapshot()], "set_price", value)
        with self.assertRaises(MenuChangeGovernanceError):
            BATCH.build_batch_preview([self.snapshot()], "delete")

    def test_categories_and_archive_reversal_preserve_prior_pause(self):
        before = {**self.snapshot(), "available_in_pos": False}
        preview = BATCH.build_batch_preview([before], "archive")
        after = preview["rows"][0]["after"]
        reverse = BATCH.build_reversal_values(before, {"active": False, "available_in_pos": False}, after)
        self.assertEqual(reverse, {"active": True, "available_in_pos": False})
        self.assertEqual(BATCH.build_batch_preview([before], "set_categories", [])["rows"][0]["after"]["pos_category_ids"], [])

    def test_reversal_blocks_newer_state_and_missing_image_preimage(self):
        before = self.snapshot()
        with self.assertRaises(MenuChangeGovernanceError):
            BATCH.build_reversal_values(before, {"list_price": 90}, {**before, "list_price": 100})
        with self.assertRaises(MenuChangeGovernanceError):
            BATCH.build_reversal_values(before, {"image_sha256": "a" * 64}, {**before, "image_sha256": "a" * 64})


if __name__ == "__main__":
    unittest.main()
