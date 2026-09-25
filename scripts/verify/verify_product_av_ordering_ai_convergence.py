#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/evidence/product_av_ordering_ai"
PACKET = ROOT / "packets/product_av_ordering_ai"
EVIDENCE = ROOT / "runtime/total_field/evidence/TOTAL_FIELD_PRODUCT_AV_ORDERING_AI_20260621_230000"


REQUIRED_DOCS = [
    DOC / "README_FOR_PATENT_PRODUCT.md",
    DOC / "README_FOR_CREDITOR_PRODUCT.md",
    DOC / "W7TP_AUDIO_VIDEO_ORDERING_AI_ARCHITECTURE.md",
    DOC / "MARKET_FEATURE_PARITY_MATRIX.md",
    DOC / "8D_OPERATION_CODE_SPEC.json",
    DOC / "PRODUCT_ROADMAP.md",
    DOC / "MINIMAL_PATCH_PLAN.md",
    DOC / "SECURITY_BOUNDARY.md",
    DOC / "BROWSER_PACKAGED_PAGES.md",
    DOC / "IMAGE_SKELETON_PROCESSING.md",
]


REQUIRED_PACKETS = [
    PACKET / "8d_function_registry.json",
    PACKET / "function_call_spec.json",
    PACKET / "browser_gui_action_map.json",
    PACKET / "cloud_candidate_contract.json",
    PACKET / "no_llm_backbrain_contract.json",
    PACKET / "formal_gate_contract.json",
    PACKET / "open_source_candidate_review.json",
    PACKET / "browser_packaged_pages.json",
    PACKET / "image_skeleton_processing_contract.json",
]


REQUIRED_EVIDENCE = [
    EVIDENCE / "PRODUCT_AV_ORDERING_AI_CONVERGENCE_SEAL.json",
    EVIDENCE / "README_PRODUCT_AV_ORDERING_AI.md",
    EVIDENCE / "sha256_manifest.txt",
]


REQUIRED_FEATURES = [
    "Menu browsing", "Categories", "Product photos", "Product specifications",
    "Add-ons", "Ice level", "Sweetness", "Temperature", "Combo meal", "Cart",
    "Quantity edit", "Notes", "Cancel", "Reorder", "Order summary",
    "Amount calculation", "Discount", "Coupon", "Member price", "Pre-checkout confirm",
    "Product intro", "Recommendation", "Add-on suggestion", "Q&A", "Multi-turn dialogue",
    "Voice readout", "Customer screen mode", "Staff mode", "Creditor demo display",
    "70B candidate brain", "No-LLM backbrain", "Cloud anchor interface",
    "Anchor iframe/SDK placeholder", "Sound output", "SUNMI voice container",
    "TTS adapter", "Volume/speed/role switch", "Offline prompts", "Queue call voice",
    "LINE login", "Google login", "Phone/email fallback", "Group member 8D code",
    "group_ref", "packet_ref", "d8_ref", "Provisional registration", "Human review",
    "Member permissions", "Masking", "No member plaintext", "Odoo POS", "Product",
    "Price", "Tax", "Inventory", "Receipt", "Table number", "Takeout/dine-in",
    "Kitchen ticket", "Accounting", "Reports", "Multi-store", "Permissions",
    "Audit trail", "CRM", "Loyalty", "Points / happiness coin", "Campaigns",
    "Community broadcast", "LINE OA", "Google member", "Revisit reminder",
    "Group member", "Volunteer/community welfare", "Public benefit feedback",
    "No direct LLM write", "Formal POS gate", "Payment capture gate", "W7TP 8D packet",
    "Hash chain", "Evidence seal", "Role permission", "Privacy boundary",
    "No plaintext to cloud", "Dry-run/formal split",
]


FORBIDDEN_PATTERNS = [
    r"login\.tailscale\.com/admin/invite",
    r"sk-[A-Za-z0-9]{16,}",
    r"access_token\s*=\s*['\"][^'\"]+['\"]",
    r"refresh_token\s*=\s*['\"][^'\"]+['\"]",
    r"id_token\s*=\s*['\"][^'\"]+['\"]",
    r"client_secret\s*=\s*['\"][^'\"]+['\"]",
]


def fail(message):
    print(f"VERIFY_FAIL={message}")
    raise SystemExit(1)


def read(path):
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def load_json(path):
    try:
        return json.loads(read(path))
    except json.JSONDecodeError as exc:
        fail(f"json_invalid:{path.relative_to(ROOT)}:{exc}")


def require_text(path, needles):
    text = read(path)
    for needle in needles:
        if needle not in text:
            fail(f"missing_text:{path.relative_to(ROOT)}:{needle}")
    return text


def check_docs():
    for path in REQUIRED_DOCS:
        if not path.exists():
            fail(f"missing_doc:{path.relative_to(ROOT)}")
    require_text(DOC / "W7TP_AUDIO_VIDEO_ORDERING_AI_ARCHITECTURE.md", [
        "STATE=READONLY_TOTAL_FIELD_PRODUCT_ALIGNMENT_DONE",
        "EXISTING_MODULES:",
        "NO_SECRET_READ=TRUE",
        "NO_MEMBER_PLAINTEXT_READ=TRUE",
        "not a sidecar",
        "/wuchang/xiaoj/ordering",
        "Cloud/70B AI generates candidates only",
    ])
    require_text(DOC / "SECURITY_BOUNDARY.md", [
        "FORMAL_DB_WRITE=FALSE",
        "FORMAL_POS_WRITE=FALSE",
        "PAYMENT_CAPTURE=FALSE",
        "SERVICE_RESTART=FALSE",
        "DEPLOY=FALSE",
        "PRODUCTION_RELEASE=FALSE",
        "SECRET_READ=FALSE",
        "MEMBER_PLAINTEXT_READ=FALSE",
    ])
    matrix = read(DOC / "MARKET_FEATURE_PARITY_MATRIX.md")
    for feature in REQUIRED_FEATURES:
        if feature not in matrix:
            fail(f"matrix_missing_feature:{feature}")


def check_json_specs():
    spec = load_json(DOC / "8D_OPERATION_CODE_SPEC.json")
    if spec.get("state") != "SPEC_CONVERGED":
        fail("8d_spec_state_drift")
    for dim in ["D1_IDENTITY", "D2_INTENT", "D3_STATE", "D4_TOPOLOGY", "D5_RESOURCE", "D6_GOVERNANCE", "D7_VERIFICATION", "D8_ENVELOPE"]:
        if dim not in spec.get("dimensions", {}):
            fail(f"8d_spec_missing_dimension:{dim}")
    for path in REQUIRED_PACKETS:
        data = load_json(path)
        if data.get("state") not in {"SPEC_CONVERGED", "REVIEW_NEEDED_NO_INSTALL", "BROWSER_PACKAGED_APP_PATCH_READY", "IMAGE_SKELETON_PROCESSING_SPEC_READY"}:
            fail(f"packet_state_drift:{path.relative_to(ROOT)}")
    cloud = load_json(PACKET / "cloud_candidate_contract.json")
    if cloud["authority"]["can_write_odoo"] is not False:
        fail("cloud_can_write_odoo")
    if cloud["authority"]["can_capture_payment"] is not False:
        fail("cloud_can_capture_payment")
    formal = load_json(PACKET / "formal_gate_contract.json")
    if formal["dry_run_gate"]["formal_pos_write"] is not False:
        fail("formal_gate_dry_run_write_drift")
    skeleton = load_json(PACKET / "image_skeleton_processing_contract.json")
    if skeleton["authority"]["avatar_layer"] != "display_only":
        fail("skeleton_avatar_authority_drift")
    if "mouth_track" not in skeleton.get("tracks", {}):
        fail("skeleton_missing_mouth_track")


def check_evidence():
    for path in REQUIRED_EVIDENCE:
        if not path.exists():
            fail(f"missing_evidence:{path.relative_to(ROOT)}")
    seal = load_json(EVIDENCE / "PRODUCT_AV_ORDERING_AI_CONVERGENCE_SEAL.json")
    if seal.get("state") != "PASS_PRODUCT_DESIGN_CONVERGED":
        fail("seal_state_drift")
    safety = seal.get("safety", {})
    for flag in [
        "formal_db_write", "formal_pos_write", "payment_capture", "service_restart",
        "deploy", "production_release", "secret_read", "member_plaintext_read",
    ]:
        if safety.get(flag) is not False:
            fail(f"safety_flag_not_false:{flag}")


def check_forbidden_strings():
    targets = REQUIRED_DOCS + REQUIRED_PACKETS + REQUIRED_EVIDENCE
    for path in targets:
        text = read(path)
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, text):
                fail(f"forbidden_pattern:{path.relative_to(ROOT)}:{pattern}")


def main():
    check_docs()
    check_json_specs()
    check_evidence()
    check_forbidden_strings()
    print("STATE=PASS_PRODUCT_DESIGN_CONVERGED")
    print("READ_EXISTING_ODOO=TRUE")
    print("READ_TOTAL_FIELD=TRUE")
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
