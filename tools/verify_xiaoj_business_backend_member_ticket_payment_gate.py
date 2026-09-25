#!/usr/bin/env python3
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/models/member_ticket_payment_gate.py"
INIT = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/models/__init__.py"
MANIFEST = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/__manifest__.py"
ACL = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/security/ir.model.access.csv"
VIEW = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/views/member_ticket_payment_gate_views.xml"
CONTRACT = ROOT / "contracts/w7tp_xiaoj_business_backend_member_ticket_payment_gate.contract.json"
DOC = ROOT / "docs/total_field/W7TP_XIAOJ_BUSINESS_BACKEND_MEMBER_TICKET_PAYMENT_GATE.md"

SCHEMA = "W7TP_XIAOJ_BUSINESS_BACKEND_MEMBER_TICKET_PAYMENT_GATE_PACKET_V1"
MODEL_NAME = "wuchang.business.backend.member.ticket.payment.gate"
ACTION_NAME = "Build Member Ticket Payment Gate"

REQUIRED_FIELDS = [
    "name",
    "member_identity_ref",
    "member_authority_state",
    "ticket_ref",
    "ticket_state",
    "entitlement_ref",
    "entitlement_state",
    "voucher_ref",
    "voucher_state",
    "happiness_coin_ref",
    "happiness_coin_state",
    "cart_ref",
    "product_menu_quality_ref",
    "odoo_product_ref",
    "price_ref",
    "custom_options_ref",
    "photo_evidence_ref",
    "consent_ref",
    "consent_state",
    "pre_payment_gate_state",
    "ai_candidate_state",
    "final_gate_decision",
    "packet_json",
    "packet_hash",
    "notes",
]

BLOCKERS = [
    "blocker_generated_image_only",
    "blocker_missing_member_authority",
    "blocker_missing_ticket_or_entitlement",
    "blocker_missing_price",
    "blocker_missing_custom_options",
    "blocker_missing_photo_evidence",
    "blocker_missing_consent",
    "blocker_product_menu_quality_not_pass",
    "blocker_payment_action_requested",
]

SIDE_EFFECTS = [
    "secret_read",
    "member_plaintext_read",
    "raw_audio_saved",
    "db_write",
    "pos_write",
    "payment_capture",
    "ticket_redeem",
    "external_api_call",
    "service_restart",
    "deploy",
]

DANGEROUS_ACTIONS = [
    "capture",
    "charge",
    "refund",
    "redeem",
    "write_pos",
    "production_db_write",
    "external_api_call",
]


def fail(msg):
    print(f"FAIL={msg}")
    sys.exit(1)


def read(path):
    if not path.exists():
        fail(f"MISSING:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require(text, needle, label):
    if needle not in text:
        fail(f"MISSING_{label}:{needle}")


def assert_no_executable_danger(model_text):
    executable_patterns = [
        r"\.(capture|charge|refund|redeem|write_pos|production_db_write|external_api_call)\s*\(",
        r"\b(capture|charge|refund|redeem|write_pos|production_db_write|external_api_call)\s*\(",
        r"\b(requests|urllib|httpx|subprocess)\.",
    ]
    for pattern in executable_patterns:
        match = re.search(pattern, model_text)
        if match:
            fail(f"EXECUTABLE_DANGEROUS_ACTION:{match.group(0)}")


def main():
    model_text = read(MODEL)
    init_text = read(INIT)
    manifest_text = read(MANIFEST)
    acl_text = read(ACL)
    view_text = read(VIEW)
    doc_text = read(DOC)

    contract = json.loads(read(CONTRACT))
    ET.parse(VIEW)

    require(model_text, f'_name = "{MODEL_NAME}"', "MODEL_NAME")
    require(model_text, SCHEMA, "PACKET_SCHEMA")
    require(model_text, "action_build_member_ticket_payment_gate", "ACTION_METHOD")
    require(model_text, "_stable_hash", "PACKET_HASH")
    require(model_text, "_check_ref_only_boundaries", "REF_ONLY_CONSTRAINT")
    require(model_text, "product_menu_quality_state not in {\"pass\", \"approved\", \"ready\"}", "PRODUCT_MENU_GATE")
    assert_no_executable_danger(model_text)

    for field in REQUIRED_FIELDS + BLOCKERS:
        require(model_text, field, f"FIELD_{field}")
        require(view_text, field, f"VIEW_FIELD_{field}")

    for decision in ["ALLOW_DRYRUN", "HOLD", "REJECT"]:
        require(model_text, decision, f"DECISION_{decision}")
        require(view_text, decision, f"VIEW_DECISION_{decision}")

    for state in [
        "unknown",
        "guest_ref_only",
        "member_ref_only",
        "verified_ref",
        "not_required",
        "missing",
        "ref_present",
        "expired",
        "mismatch",
        "pass",
        "draft",
        "ready_for_dryrun",
        "approved_dryrun_only",
    ]:
        require(model_text, state, f"STATE_{state}")

    for effect in SIDE_EFFECTS:
        require(model_text, f'"{effect}": False', f"SIDE_EFFECT_MODEL_{effect}")
        if contract["side_effects"].get(effect) is not False:
            fail(f"SIDE_EFFECT_NOT_FALSE:{effect}")

    for action in DANGEROUS_ACTIONS:
        if action not in contract.get("forbidden_actions", []):
            fail(f"MISSING_FORBIDDEN_ACTION:{action}")

    require(init_text, "member_ticket_payment_gate", "INIT_IMPORT")
    require(manifest_text, "views/member_ticket_payment_gate_views.xml", "MANIFEST_VIEW")
    require(acl_text, "model_wuchang_business_backend_member_ticket_payment_gate", "ACL_MODEL")
    require(view_text, ACTION_NAME, "ACTION_NAME")
    require(view_text, "action_wuchang_member_ticket_payment_gate", "WINDOW_ACTION")
    require(view_text, "menu_wuchang_member_ticket_payment_gate", "MENU")
    require(doc_text, SCHEMA, "DOC_SCHEMA")
    require(doc_text, MODEL_NAME, "DOC_MODEL")

    if contract.get("schema") != SCHEMA:
        fail("CONTRACT_SCHEMA")
    if contract.get("packet") != SCHEMA:
        fail("CONTRACT_PACKET")
    if contract.get("model") != MODEL_NAME:
        fail("CONTRACT_MODEL")
    if contract.get("action") != ACTION_NAME:
        fail("CONTRACT_ACTION")
    missing_blockers = sorted(set(BLOCKERS) - set(contract.get("blockers", [])))
    if missing_blockers:
        fail(f"CONTRACT_MISSING_BLOCKERS:{','.join(missing_blockers)}")

    print("STATE=PASS_XIAOJ_MEMBER_TICKET_PAYMENT_GATE")
    print(f"PACKET={SCHEMA}")
    print(f"MODEL={MODEL_NAME}")
    print(f"ACTION={ACTION_NAME}")


if __name__ == "__main__":
    main()
