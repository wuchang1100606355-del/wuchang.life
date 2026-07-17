from __future__ import annotations

import csv
import hashlib
import importlib.util
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from tools.total_field.w7tp_core_encoding import build_thing_code


ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "Taiji_Odoo/addons/wuchang_cafe_menu_options"
SERVICE_PATH = ADDON / "services/menu_change_governance.py"
SPEC = importlib.util.spec_from_file_location(
    "wuchang_cafe_menu_change_governance", SERVICE_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load cafe menu governance service")
GOVERNANCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GOVERNANCE)


class CafeMenuGovernanceTest(unittest.TestCase):
    def _candidate(self, **overrides):
        values = {
            "change_type": "update",
            "group_ref": "group:wuchang-community",
            "store_ref": "store:liaoguo-main",
            "requester_ref": "odoo-user:7",
            "responsible_person_ref": "person:founder",
            "same_principal_dual_role": True,
            "action_at_utc": "2026-07-17T09:30:00Z",
            "support_reason_sha256": hashlib.sha256(
                "price display mismatch".encode("utf-8")
            ).hexdigest(),
            "current_values": {
                "thing_code": GOVERNANCE.build_odoo_product_thing_code(3, 27),
                "name": "測試商品",
                "list_price": 100.0,
                "pos_category_ids": [9],
                "option_group_id": None,
                "available_in_pos": True,
                "active": True,
            },
            "proposed_values": {"list_price": 110.0},
        }
        values.update(overrides)
        return GOVERNANCE.build_menu_change_candidate(**values)

    def test_odoo_product_code_matches_total_field_core(self):
        self.assertEqual(
            GOVERNANCE.build_odoo_product_thing_code(3, 27),
            build_thing_code(
                "PRODUCT", "ODOO_COMPANY_3", "product.template:27"
            ),
        )

    def test_candidate_is_deterministic_complete_and_single_account_safe(self):
        first = self._candidate()
        second = self._candidate()
        self.assertEqual(first, second)
        self.assertEqual(set(first) & {f"D{index}" for index in range(1, 9)}, {f"D{index}" for index in range(1, 9)})
        self.assertEqual(first["D4"]["who"]["actor_ref"], "odoo-user:7")
        self.assertEqual(first["D3"]["where"]["store_ref"], "store:liaoguo-main")
        self.assertEqual(first["D4"]["when"]["submitted_at_utc"], "2026-07-17T09:30:00Z")
        self.assertEqual(first["D1"]["what"], {"list_price": 110.0})
        self.assertTrue(first["D7"]["single_human_identity_single_account"])
        self.assertFalse(first["D7"]["distinct_second_person_required"])
        self.assertEqual(first["D7"]["automatic_apply_after_request"], "BLOCK")
        self.assertFalse(first["D5"]["remote_support_direct_write"])
        self.assertFalse(first["D5"]["payment_capture"])

    def test_candidate_rejects_invalid_time_reason_hash_and_price(self):
        for overrides, expected in (
            ({"action_at_utc": "2026-07-17 09:30:00"}, "ACTION_AT_UTC_INVALID"),
            ({"support_reason_sha256": "bad"}, "SUPPORT_REASON_SHA256_INVALID"),
            ({"proposed_values": {"list_price": True}}, "PROPOSED_VALUES_PRICE_INVALID"),
        ):
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(
                    GOVERNANCE.MenuChangeGovernanceError, expected
                ):
                    self._candidate(**overrides)

    def test_approval_seal_records_four_w_event_without_second_account(self):
        candidate = self._candidate()
        applied = dict(candidate["D2"]["current_values"])
        applied["list_price"] = 110.0
        seal = GOVERNANCE.build_responsible_approval_seal(
            candidate_sha256=candidate["candidate_sha256"],
            responsible_person_ref="person:founder",
            product_thing_code=applied["thing_code"],
            applied_values=applied,
            same_principal_dual_role=True,
            review_note_sha256=hashlib.sha256(b"confirmed").hexdigest(),
            actor_ref="odoo-user:7",
            action_location_ref="store:liaoguo-main",
            reviewed_at_utc="2026-07-17T09:35:00Z",
        )
        self.assertEqual(
            seal["event"],
            {
                "who": "odoo-user:7",
                "where": "store:liaoguo-main",
                "when": "2026-07-17T09:35:00Z",
                "what": "APPROVE_AND_APPLY_ONE_ODOO_MENU_ITEM_CHANGE",
            },
        )
        self.assertTrue(seal["same_principal_dual_role"])
        self.assertFalse(seal["automatic_apply_after_request"])

    def test_safe_views_security_and_acl_are_closed(self):
        views = ET.parse(ADDON / "views/menu_option_views.xml").getroot()
        security_text = (ADDON / "security/menu_change_security.xml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("point_of_sale.group_pos_manager", security_text)
        self.assertIn("One human keeps one account", security_text)

        action = next(
            record
            for record in views.findall("record")
            if record.attrib.get("id") == "action_wuchang_cafe_menu_products"
        )
        action_xml = ET.tostring(action, encoding="unicode")
        for view_id in (
            "view_wuchang_cafe_menu_product_kanban",
            "view_wuchang_cafe_menu_product_list",
            "view_wuchang_cafe_menu_product_form",
        ):
            self.assertIn(view_id, action_xml)
        self.assertNotIn("product_template_form_view", action_xml)
        self.assertNotIn(
            "招牌咖啡",
            (ADDON / "views/menu_option_views.xml").read_text(encoding="utf-8"),
        )

        with (ADDON / "security/ir.model.access.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.DictReader(handle))
        guarded = [
            row
            for row in rows
            if "responsible" in row["id"] or "remote" in row["id"]
        ]
        self.assertTrue(guarded)
        self.assertTrue(all(row["perm_unlink"] == "0" for row in guarded))

    def test_workflow_source_blocks_remote_direct_write_and_seals_events(self):
        manager_source = (ADDON / "models/menu_manager.py").read_text(
            encoding="utf-8"
        )
        request_source = (ADDON / "models/menu_change_request.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("and not self._wuchang_menu_is_responsible()", manager_source)
        self.assertIn("remote_support_direct_write", request_source)
        self.assertIn("current_check[\"candidate_sha256\"]", request_source)
        self.assertIn("single_account_multi_role", request_source)
        self.assertIn("submitted_location_ref", request_source)
        self.assertIn("wuchang.cafe.ai.eventbook", manager_source)
        self.assertIn("single_human_identity_single_account", manager_source)
        self.assertIn("wuchang_w5c_code_unique", manager_source)
        self.assertIn("Human menu audit events are immutable.", manager_source)
        self.assertIn('payload["content_sha256"]', manager_source)
        self.assertIn('event_payload["content_sha256"]', request_source)


if __name__ == "__main__":
    unittest.main()
