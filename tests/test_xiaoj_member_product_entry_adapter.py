#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from argparse import Namespace
from pathlib import Path

from tools.member_browser.xiaoj_member_browser_gateway import build_gateway_result
from tools.total_field.xiaoj_member_product_entry_adapter import (
    build_xiaoj_member_product_entry_candidate,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests/test_member_sovereign_session_dual_receipt_9107.py"

spec = importlib.util.spec_from_file_location("t019_p3_fixture", FIXTURE_PATH)
assert spec is not None and spec.loader is not None
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def odoo_projection(candidate: dict) -> dict:
    return {
        "auth_state": "AUTHENTICATED_LOCAL_MEMBER",
        "member_ref": candidate["member_ref"],
        "odoo_identity_ref": "odoo_identity_ref:member:local",
        "odoo_role_ref": "odoo_role_ref:resident",
        "odoo_function_scope_ref": "odoo_function_scope_ref:member_daily",
        "odoo_permission_bucket_ref": "odoo_permission_bucket_ref:resident_readonly",
        "member_preference_ref": "preference_ref:member:concise",
        "service_style_ref": "service_style_ref:community_xiaoj_warm_daily",
        "quota_bucket_ref": "quota_ref:member:daily",
        "benefit_ref": "benefit_ref:community_ai_member_daily",
        "behavior_info_ref": "",
        "cloud_compute_ref": "cloud_compute_ref:local_member_candidate",
    }


def product_entry(candidate: dict | None = None) -> dict:
    candidate = copy.deepcopy(candidate or fixture._candidate())
    role_payload = candidate["p1_identity_candidate"]["derived_packets_evidence"]["payload"]["role_seat"]["payload"]
    role_payload["organization_ref"] = fixture._ref("organization", "wuchang-community")
    return build_xiaoj_member_product_entry_candidate(
        odoo_member_projection=odoo_projection(candidate),
        member_action_request=candidate,
        current_epoch=fixture.NOW,
        nonce_consumer=fixture.DurableNonceDouble(),
        p1_verifier=fixture._p1_pass,
        organization_request_ref=fixture._ref("organization_request", "member-entry"),
        audit_ref=fixture._ref("audit", "t019"),
        allowed_capability_refs=[
            fixture._ref("capability", "xiaoj-member-browser"),
            fixture._ref("capability", "candidate-return"),
        ],
    )


class XiaoJMemberProductEntryAdapterTest(unittest.TestCase):
    def test_passes_existing_member_sovereign_chain(self) -> None:
        result = product_entry()
        self.assertEqual(result["state"], "PASS_XIAOJ_MEMBER_PRODUCT_ENTRY_CANDIDATE")
        self.assertTrue(result["candidate_only"])
        self.assertFalse(result["runtime_effect"])
        self.assertFalse(result["execution_allowed"])
        self.assertTrue(result["requires_total_field_verify"])
        self.assertEqual(result["member_consent_authority"], "member")
        self.assertEqual(result["safety_and_landing_authority"], "total_field_verifier")
        self.assertEqual(result["candidate_authority"], "none")
        self.assertEqual(
            result["odoo_role"],
            "PROCESS_AND_MASKED_PROJECTION_NOT_SOVEREIGN_ROOT",
        )

    def test_browser_binding_is_ref_only_and_matches_member(self) -> None:
        result = product_entry()
        binding = result["xiaoj_member_browser_binding"]
        sovereign_ref = result["member_model_visible_context"]["state_projection"]["member_sovereign_context"]["member_coordinate"]["natural_person_ref"]
        self.assertEqual(binding["sovereign_member_ref"], sovereign_ref)
        self.assertTrue(binding["member_ref"].startswith("actor_ref:member:"))
        self.assertNotEqual(binding["member_ref"], sovereign_ref)
        self.assertEqual(binding["safe_context_ref"], result["member_context_ref"])
        self.assertTrue(binding["requires_total_field_verify"])
        self.assertTrue(binding["submit_forbidden"])
        encoded = json.dumps(result, ensure_ascii=False).lower()
        self.assertFalse(result["member_plaintext_read"])
        self.assertFalse(result["secret_read"])
        for forbidden in (
            "raw_member",
            "password_value",
            "bearer ",
            "private_key_value",
            "full_address_value",
            "phone_number_value",
        ):
            self.assertNotIn(forbidden, encoded)

    def test_google_and_line_are_not_core_entry_blockers(self) -> None:
        result = product_entry()
        optional = result["optional_channel_bindings"]
        self.assertFalse(optional["google_required_for_core_member_entry"])
        self.assertFalse(optional["line_required_for_core_member_entry"])

    def test_odoo_member_mismatch_holds(self) -> None:
        candidate = fixture._candidate()
        role_payload = candidate["p1_identity_candidate"]["derived_packets_evidence"]["payload"]["role_seat"]["payload"]
        role_payload["organization_ref"] = fixture._ref("organization", "wuchang-community")
        projection = odoo_projection(candidate)
        projection["member_ref"] = fixture._ref("member", "other")
        result = build_xiaoj_member_product_entry_candidate(
            odoo_member_projection=projection,
            member_action_request=candidate,
            current_epoch=fixture.NOW,
            nonce_consumer=fixture.DurableNonceDouble(),
            p1_verifier=fixture._p1_pass,
            organization_request_ref=fixture._ref("organization_request", "member-entry"),
            audit_ref=fixture._ref("audit", "t019"),
            allowed_capability_refs=[],
        )
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["reason_code"], "HOLD_ODOO_MEMBER_REF_MISMATCH")

    def test_unverified_member_receipt_holds(self) -> None:
        candidate = fixture._candidate()
        role_payload = candidate["p1_identity_candidate"]["derived_packets_evidence"]["payload"]["role_seat"]["payload"]
        role_payload["organization_ref"] = fixture._ref("organization", "wuchang-community")
        candidate["member_consent_receipt"]["receipt_state"] = "HOLD"
        result = build_xiaoj_member_product_entry_candidate(
            odoo_member_projection=odoo_projection(candidate),
            member_action_request=candidate,
            current_epoch=fixture.NOW,
            nonce_consumer=fixture.DurableNonceDouble(),
            p1_verifier=fixture._p1_pass,
            organization_request_ref=fixture._ref("organization_request", "member-entry"),
            audit_ref=fixture._ref("audit", "t019"),
            allowed_capability_refs=[],
        )
        self.assertEqual(result["state"], "HOLD")

    def test_output_binds_directly_to_existing_member_browser_gateway(self) -> None:
        entry = product_entry()
        b = entry["xiaoj_member_browser_binding"]
        args = Namespace(
            intent="幫我打開會員小J側邊欄",
            safe_context_ref=b["safe_context_ref"],
            selected_text="",
            local_draft_text="",
            active_field_type="textarea",
            member_ref=b["member_ref"],
            device_ref=b["device_ref"],
            key_ref="key_ref:member_browser_gateway:broker_default",
            api_ref="api_ref:member_browser_gateway:local_1b",
            quota_ref=b["quota_ref"],
            member_preference_ref=b["member_preference_ref"],
            service_style_ref=b["service_style_ref"],
            behavior_info_ref=b["behavior_info_ref"],
            cloud_compute_ref=b["cloud_compute_ref"],
            benefit_ref=b["benefit_ref"],
            odoo_identity_ref=b["odoo_identity_ref"],
            odoo_role_ref=b["odoo_role_ref"],
            odoo_function_scope_ref=b["odoo_function_scope_ref"],
            odoo_permission_bucket_ref=b["odoo_permission_bucket_ref"],
            payment_tool_ref="payment_tool_ref:member_selected_external_tool",
            management_fee_bill_ref="management_fee_bill_ref:none",
            payment_amount_bucket_ref="payment_amount_bucket_ref:not_requested",
            out="",
            smoke=False,
        )
        gateway = build_gateway_result(args)
        self.assertIn(gateway["state"], {"CANDIDATE_READY", "HOLD"})
        self.assertFalse(gateway["browser_bridge_result"]["execution_allowed"])
        self.assertFalse(gateway["association_usage_admission_packet"]["execution_allowed"])
        self.assertFalse(gateway["member_plaintext_transferred"])
        self.assertFalse(gateway["secret_transferred"])
        self.assertTrue(all(value is False for value in gateway["safety_flags"].values()))


if __name__ == "__main__":
    unittest.main()
