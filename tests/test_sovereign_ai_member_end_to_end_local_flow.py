from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_sovereign_ai_member_end_to_end_local_flow() -> None:
    login_source = (ROOT / "Taiji_Odoo/addons/wuchang_google_member_login/controllers/main.py").read_text()
    line_login_source = (ROOT / "Taiji_Odoo/addons/wuchang_line_login/controllers/main.py").read_text()
    registration_source = (ROOT / "Taiji_Odoo/addons/wuchang_member_registration/controllers/main.py").read_text()
    candidate_shell_source = (
        ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/controllers/main.py"
    ).read_text()
    assert '"/google/member/login"' in login_source
    assert '"/google/member/callback"' in login_source
    assert "'/line/login'" in line_login_source
    assert "'/line/callback'" in line_login_source
    assert "wuchang_group_auth_ref" in login_source
    assert '"/wuchang/member/register/start"' in registration_source
    assert '"/wuchang/member/register/group/<string:packet_ref>"' in registration_source
    assert '@http.route("/line/login"' not in candidate_shell_source
    assert '@http.route("/line/callback"' not in candidate_shell_source
    assert (
        '@http.route("/wuchang/member/register/start"'
        not in candidate_shell_source
    )
    assert 'href="/web/signup"' in candidate_shell_source

    member_model_source = (
        ROOT
        / "Taiji_Odoo/addons/wuchang_member_registration/models/member_registration.py"
    ).read_text()
    signup_source = (
        ROOT
        / "Taiji_Odoo/addons/wuchang_member_registration/views/signup_templates.xml"
    ).read_text()
    member_views_source = (
        ROOT
        / "Taiji_Odoo/addons/wuchang_member_registration/views/member_registration_views.xml"
    ).read_text()
    member_manifest_source = (
        ROOT / "Taiji_Odoo/addons/wuchang_member_registration/__manifest__.py"
    ).read_text()
    core_model_init_source = (
        ROOT / "Taiji_Odoo/addons/wuchang_core/models/__init__.py"
    ).read_text()
    caddy_source = (
        ROOT / "deploy/caddy/w7tp-odoo-identity-projection.caddy"
    ).read_text()
    core_main_source = (
        ROOT / "Taiji_Odoo/addons/wuchang_core/controllers/main.py"
    ).read_text()
    order_source = (
        ROOT / "Taiji_Odoo/addons/wuchang_core/controllers/order_site.py"
    ).read_text()
    member_groups = (
        ROOT
        / "Taiji_Odoo/addons/wuchang_member_registration/security/wuchang_member_groups.xml"
    ).read_text()
    for surface in {
        "external_api",
        "google_login",
        "line_login",
        "member_ai",
        "member_registration",
        "payment",
        "pos_order",
    }:
        assert f'"{surface}"' in member_model_source
    assert "is_landing_enabled" in login_source
    assert "is_landing_enabled" in line_login_source
    assert "is_landing_enabled" in registration_source
    assert "identity_projection_response_headers" in login_source
    assert "IDENTITY_PREFIX_NOT_BOUND" in login_source
    for route in {
        "/google/member/*",
        "/line/*",
        "/web/login*",
        "/web/signup*",
        "/wuchang/home",
        "/wuchang/business/onboarding*",
        "/forum*",
    }:
        assert route in caddy_source
    assert "INDIVIDUAL_JURISDICTION_CATEGORIES" in member_model_source
    assert "Individual registrations do not require manual approval." in member_model_source
    assert "from . import member_registration" not in core_model_init_source
    assert "existing_binding = external_auth.search" in member_model_source
    assert "if not existing_binding:" in member_model_source
    assert "the system will not create a duplicate record" in member_model_source
    assert "HOLD_FOUNDER_APPROVAL_REQUIRED" in registration_source
    assert "founder.identity.google_accounts" in registration_source
    assert "def _founder_review_authorized" in registration_source
    assert 'name="organization_name"' in signup_source
    assert 'name="membership_category"' in signup_source
    assert "in_community_jurisdiction" in signup_source
    assert "outside_community_jurisdiction" in signup_source
    assert '<field name="mode">discussions</field>' in member_views_source
    assert '<field name="privacy">connected</field>' in member_views_source
    assert '"website_forum"' in member_manifest_source
    assert "copy_headers X-W7TP-Identity-Schema" in caddy_source
    assert "w7tp_odoo_public_member_redirects_candidate" in caddy_source
    assert "https://member.wuchang.life{uri}" in caddy_source
    assert "The nonprofit homepage remains the sole public/Ad Grants destination" in caddy_source
    assert "handle /api/intent-field" in caddy_source
    assert "handle /wuchang/intent-field" in caddy_source
    assert 'header_down Location "^/google/member/welcome$" "/wuchang/intent-field"' in caddy_source
    assert "return False" in core_main_source[
        core_main_source.index("def _check_auth"):core_main_source.index(
            "def _find_partner_by_unit"
        )
    ]
    assert "BLOCK_DEMO_PAYMENT_CALLBACK_NOT_PRODUCT_AUTHORITY" in order_source
    for group_id in {
        "group_wuchang_member_staff",
        "group_wuchang_member_manager",
        "group_wuchang_member_admin",
    }:
        assert group_id in member_groups

    menu_lock = json.loads(
        (
            ROOT / "runtime/total_field/xiaoj_p1_console/menu_source_lock.json"
        ).read_text()
    )
    assert menu_lock["state"] == "HOLD_REAL_MENU_SOURCE_LOCK"
    assert menu_lock["authority"]["merchant_is_content_authority"] is True
    assert menu_lock["authority"]["current_menu_authority"] is False
    assert menu_lock["active_product_rows"] == []
    policy = menu_lock["merchant_review_policy"]
    assert policy["variants_generated"] is False
    assert policy["demo_products_in_formal_pos"] is False
    assert policy["medium_size_is_price_baseline"] is True
    assert policy["medium_size_price_delta"] == 0
    assert policy["total_field_may_choose_products_or_prices"] is False

    scene_table = json.loads(
        (
            ROOT
            / "runtime/total_field/secondary_cloud/scenario_route_table.json"
        ).read_text()
    )
    assert set(scene_table["routes"]) == {
        "ASSOCIATION",
        "CAFE_POS",
        "GENERIC",
        "HOUSEHOLD",
        "PROPERTY",
    }

    oauth = load(
        ROOT / "Taiji_Odoo/addons/wuchang_google_member_login/services/oauth_config.py",
        "sovereign_member_oauth_contract",
    )
    callback = oauth.build_callback_uri(
        configured_base_url="https://members.example.test"
    )
    assert oauth.login_health_state(
        True, True, True, True, "https://members.example.test", callback
    ) == "PASS"

    intent_engine = load(
        ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/p1_intent_engine.py",
        "sovereign_member_intent_engine",
    )
    intent_result = intent_engine.candidate_action(
        "我要加入會員", explicit_intent="member_register"
    )
    assert intent_result["intent"] == "member_register"
    assert intent_result["candidate_action"]["confirm_state"] == "draft"
    assert intent_result["requires_human_release"] is True
    assert intent_result["evidence_seal"]["member_plaintext_read"] is False

    cloud_packet = load(
        ROOT / "tools/xiaoj_gemini_no_plaintext_candidate_packet.py",
        "sovereign_member_cloud_packet",
    ).build_packet(
        "會員服務候選",
        intent_code="member_service_reply",
        member_ref="MEMBER_REF_SYNTHETIC",
    )
    assert cloud_packet["generative_transmission"]["cloud_role"] == "candidate_worker_only"
    assert cloud_packet["generative_transmission"]["member_plaintext_transmitted"] is False
    assert cloud_packet["local_zero_latency_decision"]["execution_allowed"] is False

    local_result = load(
        ROOT / "tools/w7tp_packet_inference_runtime.py",
        "sovereign_member_local_execution_gate",
    ).run(
        "我要加入會員",
        authenticated_role_ref="ROLE_MEMBER_SYNTHETIC",
        canonical_verifier_result={
            "decision": "HOLD",
            "reasons": ["manual confirmation required"],
        },
    )
    assert local_result["FINAL_VERIFIER"]["decision"] == "HOLD"
    assert local_result["FINAL_VERIFIER"]["runtime_authority"] is False
    assert len(local_result["PACKET_CHAIN"]) == 8
    assert all(
        packet.get("D8_envelope", {}).get("packet_hash")
        for packet in local_result["PACKET_CHAIN"]
    )
