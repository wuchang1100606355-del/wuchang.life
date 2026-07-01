#!/usr/bin/env python3
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CTRL = ROOT / "Taiji_Odoo/addons/wuchang_core/controllers/xiaoj_ordering_app_controller.py"
API_CTRL = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/controllers/main.py"
INIT = ROOT / "Taiji_Odoo/addons/wuchang_core/controllers/__init__.py"
JS = ROOT / "Taiji_Odoo/addons/wuchang_core/static/src/xiaoj_ordering/xiaoj_ordering_app.js"
CSS = ROOT / "Taiji_Odoo/addons/wuchang_core/static/src/xiaoj_ordering/xiaoj_ordering_app.css"
MANIFEST = ROOT / "Taiji_Odoo/addons/wuchang_core/static/src/xiaoj_ordering/xiaoj_ordering.webmanifest"
AVATAR_DIR = ROOT / "Taiji_Odoo/addons/wuchang_core/static/src/xiaoj_ordering/avatar"
PACKET = ROOT / "packets/product_av_ordering_ai/browser_packaged_pages.json"
LINEWORKS_CONTRACT = ROOT / "packets/product_av_ordering_ai/lineworks_notification_gate_contract.json"
DOC = ROOT / "docs/evidence/product_av_ordering_ai/BROWSER_PACKAGED_PAGES.md"
LINEWORKS_DOC = ROOT / "docs/product/XIAOJ_LINE_WORKS_PRODUCTIZATION_PLAN.md"
LINEWORKS_GUIDE = ROOT / "docs/product/XIAOJ_LINE_WORKS_OPERATOR_GUIDE.html"

PAGES = [
    "staff_pos",
    "counter_service_touch",
    "av_ai_menu_display",
    "business_management",
    "hardware_menu_business_settings",
]

FORBIDDEN = [
    r"login\.tailscale\.com/admin/invite",
    r"sk-[A-Za-z0-9]{16,}",
    r"access_token\s*=\s*['\"][^'\"]+['\"]",
    r"refresh_token\s*=\s*['\"][^'\"]+['\"]",
    r"id_token\s*=\s*['\"][^'\"]+['\"]",
    r"client_secret\s*=\s*['\"][^'\"]+['\"]",
    r"payment_capture\s*:\s*true",
    r"formal_pos_write\s*:\s*true",
]

FORBIDDEN_MENU_TERMS_IN_JS = [
    "紅茶",
    "綠茶",
    "煎餃",
    "蘿蔔糕",
    "漢堡",
    "三明治",
    "套餐",
    "豆漿",
    "蛋餅",
    "拿鐵",
    "美式咖啡",
]


def fail(message):
    print(f"VERIFY_FAIL={message}")
    raise SystemExit(1)


def read(path):
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require(path, needles):
    text = read(path)
    for needle in needles:
        if needle not in text:
            fail(f"missing_text:{path.relative_to(ROOT)}:{needle}")
    return text


def main():
    ctrl = require(CTRL, ["/wuchang/xiaoj/ordering", "auth=\"user\"", "formal_pos_write", "payment_capture"])
    api_ctrl = require(API_CTRL, [
        '"/wuchang/xiaoj/api/formal-release-status", type="json", auth="user"',
        '"/wuchang/xiaoj/api/lineworks-notify", type="json", auth="user"',
        '"/wuchang/xiaoj/api/lineworks-send-preflight", type="json", auth="user"',
        "formal_release_status_payload",
        "lineworks_notify_payload",
        "build_lineworks_send_preflight",
    ])
    require(INIT, ["xiaoj_ordering_app_controller"])
    js = require(JS, PAGES + [
        "FORMAL_POS_WRITE",
        "PAYMENT_CAPTURE",
        "FORMAL_LINEWORKS_SEND",
        "CONFIRM_DRY_RUN",
        "店內現金",
        "社群 AI",
        "維護排程",
        "displayTicker",
        "上方跑馬燈",
        "下方跑馬燈",
        "lung.vrm",
        "VRM_ASSET_SLOT_READY",
        "/wuchang/xiaoj/api/merchant-capabilities",
        "/wuchang/xiaoj/api/formal-release-status",
        "/wuchang/xiaoj/api/lineworks-notify",
        "/wuchang/xiaoj/api/lineworks-send-preflight",
        "LINE WORKS release",
        "LINE WORKS 候選通知",
        "data-lineworks-message",
        "data-lineworks-candidate",
        "data-lineworks-preflight",
        "TARGET_REF_UI_MASKED",
        "BOT_REF_UI_ONLY",
        "RUNTIME_TOKEN_PROVIDER_REF_ONLY",
        "HOLD_LINEWORKS_SEND_PREFLIGHT",
        "total_field_subfield_query",
        "authority_packet",
        "local_verifier",
        "evidence_seal",
        "quickclick_49180031",
        "quickclick_49180038",
        "QuickClick source lock",
        "待 QuickClick",
    ])
    for term in FORBIDDEN_MENU_TERMS_IN_JS:
        if term in js:
            fail(f"forbidden_menu_term_in_js:{term}")
    css = require(CSS, [".app-shell", ".mode-tabs", ".hero-card", ".display-ticker", ".avatar-stage", ".display-asset-panel", ".lineworks-panel", ".candidate-form textarea", "@keyframes xiaojTicker", "@media"])
    if not AVATAR_DIR.exists():
        fail("missing_avatar_dir")
    manifest = json.loads(read(MANIFEST))
    if manifest.get("display") != "standalone":
        fail("manifest_display_not_standalone")
    packet = json.loads(read(PACKET))
    lineworks_contract = json.loads(read(LINEWORKS_CONTRACT))
    if packet.get("state") != "BROWSER_PACKAGED_APP_PATCH_READY":
        fail("packet_state_drift")
    if packet.get("standalone_server") is not False:
        fail("standalone_server_drift")
    if packet.get("merchant_capability_api") != "/wuchang/xiaoj/api/merchant-capabilities":
        fail("merchant_capability_api_missing")
    if packet.get("formal_release_status_api") != "/wuchang/xiaoj/api/formal-release-status":
        fail("formal_release_status_api_missing")
    if packet.get("formal_release_status_auth") != "user":
        fail("formal_release_status_auth_not_user")
    if packet.get("formal_release_ref_contract") != "verified_ref_object_required":
        fail("formal_release_ref_contract_missing")
    if packet.get("raw_release_ref_echo") is not False:
        fail("raw_release_ref_echo_not_false")
    if packet.get("lineworks_notify_candidate_api") != "/wuchang/xiaoj/api/lineworks-notify":
        fail("lineworks_notify_candidate_api_missing")
    if packet.get("lineworks_notify_candidate_auth") != "user":
        fail("lineworks_notify_candidate_auth_not_user")
    if packet.get("lineworks_send_preflight_api") != "/wuchang/xiaoj/api/lineworks-send-preflight":
        fail("lineworks_send_preflight_api_missing")
    if packet.get("lineworks_send_preflight_auth") != "user":
        fail("lineworks_send_preflight_auth_not_user")
    if packet.get("formal_lineworks_send") is not False:
        fail("formal_lineworks_send_not_false")
    if packet.get("total_field_subfield_query_required_before_generation") is not True:
        fail("total_field_subfield_query_requirement_missing")
    if lineworks_contract.get("candidate_api") != "/wuchang/xiaoj/api/lineworks-notify":
        fail("lineworks_contract_candidate_api_missing")
    if lineworks_contract.get("candidate_api_auth") != "user":
        fail("lineworks_contract_auth_not_user")
    if lineworks_contract.get("formal_release_gate") != "lineworks_send":
        fail("lineworks_contract_gate_missing")
    delegate_boundary = lineworks_contract.get("total_field_delegate_boundary", {})
    if delegate_boundary.get("mode") != "bounded_digital_delegate":
        fail("lineworks_contract_delegate_boundary_missing")
    if delegate_boundary.get("root_of_trust") != "human_owner_admin":
        fail("lineworks_contract_delegate_root_of_trust_missing")
    if delegate_boundary.get("credential_material_in_repo") is not False:
        fail("lineworks_contract_delegate_credential_boundary_missing")
    if lineworks_contract.get("p1_side_effects", {}).get("formal_lineworks_send") is not False:
        fail("lineworks_contract_formal_send_not_false")
    if lineworks_contract.get("redaction_boundary", {}).get("raw_target_ref_echo") is not False:
        fail("lineworks_contract_raw_ref_echo_not_false")
    found_pages = {page.get("id") for page in packet.get("pages", [])}
    for page in PAGES:
        if page not in found_pages:
            fail(f"packet_missing_page:{page}")
    packet_text = read(PACKET)
    for needle in ["top_marquee", "bottom_marquee"]:
        if needle not in packet_text:
            fail(f"packet_missing_ticker:{needle}")
    for needle in ["xiaoj_vrm_asset_slot", "lung.vrm", "VRM_ASSET_SLOT_READY"]:
        if needle not in packet_text:
            fail(f"packet_missing_avatar_slot:{needle}")
    require(DOC, ["STATE=BROWSER_PACKAGED_APP_PATCH_READY", "ROUTE=/wuchang/xiaoj/ordering", "Top ticker", "Bottom ticker", "XiaoJ VRM Customer Display Slot", "lung.vrm"])
    require(LINEWORKS_DOC, [
        "STATE=LINE_WORKS_PRODUCTIZATION_P1_CANDIDATE_GATE_READY",
        "/wuchang/xiaoj/api/lineworks-notify",
        "lineworks_send",
        "formal_lineworks_send=false",
        "bot.message",
        "Total Field Digital Delegate Boundary",
        "human_owner_admin",
    ])
    require(LINEWORKS_GUIDE, [
        "STATE=LINE_WORKS_PRODUCTIZATION_P1_CANDIDATE_GATE_READY",
        "Simple Browser: Show",
        "bot.message",
        "不要把 LINE WORKS access token",
        "Verified Release Refs",
        "總場數位代理邊界",
        "root-of-trust",
    ])
    for path, text in [
        (CTRL, ctrl),
        (API_CTRL, api_ctrl),
        (JS, js),
        (CSS, css),
        (PACKET, read(PACKET)),
        (LINEWORKS_CONTRACT, read(LINEWORKS_CONTRACT)),
        (DOC, read(DOC)),
        (LINEWORKS_DOC, read(LINEWORKS_DOC)),
        (LINEWORKS_GUIDE, read(LINEWORKS_GUIDE)),
    ]:
        for pattern in FORBIDDEN:
            if re.search(pattern, text):
                fail(f"forbidden:{path.relative_to(ROOT)}:{pattern}")
    print("STATE=PASS_XIAOJ_BROWSER_PACKAGED_PAGES")
    print("ROUTE=/wuchang/xiaoj/ordering")
    print("FORMAL_DB_WRITE=FALSE")
    print("FORMAL_POS_WRITE=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    print("PRODUCTION_RELEASE=FALSE")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("MERCHANT_CAPABILITY_API=TRUE")
    print("FORMAL_RELEASE_STATUS_API=TRUE")
    print("TOTAL_FIELD_SUBFIELD_QUERY=TRUE")
    print("AUTHORITY_CHAIN_STATUS_UI=TRUE")


if __name__ == "__main__":
    main()
