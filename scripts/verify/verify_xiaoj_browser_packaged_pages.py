#!/usr/bin/env python3
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CTRL = ROOT / "Taiji_Odoo/addons/wuchang_core/controllers/xiaoj_ordering_app_controller.py"
INIT = ROOT / "Taiji_Odoo/addons/wuchang_core/controllers/__init__.py"
JS = ROOT / "Taiji_Odoo/addons/wuchang_core/static/src/xiaoj_ordering/xiaoj_ordering_app.js"
CSS = ROOT / "Taiji_Odoo/addons/wuchang_core/static/src/xiaoj_ordering/xiaoj_ordering_app.css"
MANIFEST = ROOT / "Taiji_Odoo/addons/wuchang_core/static/src/xiaoj_ordering/xiaoj_ordering.webmanifest"
AVATAR_DIR = ROOT / "Taiji_Odoo/addons/wuchang_core/static/src/xiaoj_ordering/avatar"
PACKET = ROOT / "packets/product_av_ordering_ai/browser_packaged_pages.json"
DOC = ROOT / "docs/evidence/product_av_ordering_ai/BROWSER_PACKAGED_PAGES.md"

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
    require(INIT, ["xiaoj_ordering_app_controller"])
    js = require(JS, PAGES + ["FORMAL_POS_WRITE", "PAYMENT_CAPTURE", "CONFIRM_DRY_RUN", "店內現金", "社群 AI", "維護排程", "displayTicker", "上方跑馬燈", "下方跑馬燈", "lung.vrm", "VRM_ASSET_SLOT_READY"])
    css = require(CSS, [".app-shell", ".mode-tabs", ".hero-card", ".display-ticker", ".avatar-stage", ".display-asset-panel", "@keyframes xiaojTicker", "@media"])
    if not AVATAR_DIR.exists():
        fail("missing_avatar_dir")
    manifest = json.loads(read(MANIFEST))
    if manifest.get("display") != "standalone":
        fail("manifest_display_not_standalone")
    packet = json.loads(read(PACKET))
    if packet.get("state") != "BROWSER_PACKAGED_APP_PATCH_READY":
        fail("packet_state_drift")
    if packet.get("standalone_server") is not False:
        fail("standalone_server_drift")
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
    for path, text in [(CTRL, ctrl), (JS, js), (CSS, css), (PACKET, read(PACKET)), (DOC, read(DOC))]:
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


if __name__ == "__main__":
    main()
