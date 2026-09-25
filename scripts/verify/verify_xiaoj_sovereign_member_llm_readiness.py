#!/usr/bin/env python3
"""Verify current landing status for sovereign member, 8D, XiaoJ, and Gemini LLM flows.

This verifier is intentionally conservative: it must not let prototype Gemini
or personal-data flows be reported as production-ready.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "packets/product_av_ordering_ai/sovereign_member_llm_readiness_contract.json"
DOC = ROOT / "docs/product/XIAOJ_SOVEREIGN_MEMBER_LLM_READINESS_MATRIX.md"
MEMBER_MODEL = ROOT / "Taiji_Odoo/addons/wuchang_member_registration/models/member_registration.py"
MEMBER_CTRL = ROOT / "Taiji_Odoo/addons/wuchang_member_registration/controllers/main.py"
GOOGLE_CTRL = ROOT / "Taiji_Odoo/addons/wuchang_google_member_login/controllers/main.py"
GOOGLE_PARTNER = ROOT / "Taiji_Odoo/addons/wuchang_google_member_login/models/res_partner.py"
CORE_SETTINGS = ROOT / "Taiji_Odoo/addons/wuchang_core/models/settings.py"
CORE_SETTINGS_VIEW = ROOT / "Taiji_Odoo/addons/wuchang_core/views/settings_views.xml"
CORE_CTRL = ROOT / "Taiji_Odoo/addons/wuchang_core/controllers/main.py"
API_SEPARATION = ROOT / "Taiji_Odoo/addons/wuchang_core/models/api_account_separation.py"
GEMINI_WORKER_CONTRACT = ROOT / "packets/product_av_ordering_ai/gemini_no_plaintext_candidate_worker_contract.json"
GEMINI_WORKER_TOOL = ROOT / "tools/xiaoj_gemini_no_plaintext_candidate_packet.py"
GEMINI_WORKER_VERIFY = ROOT / "scripts/verify/verify_xiaoj_gemini_no_plaintext_candidate_worker.py"
GROUP_8D_VERIFY = ROOT / "scripts/verify/verify_group_member_8d_registration.py"
MEMBER_BROWSER_VERIFY = ROOT / "scripts/verify/verify_xiaoj_member_browser_release.py"
SOVEREIGN_1B_VERIFY = ROOT / "scripts/verify/verify_xiaoj_sovereign_1b_product_goal.py"
ACTIVE_MEMBER_BROWSER = ROOT / "runtime/member_browser/ACTIVE_XIAOJ_MEMBER_BROWSER_RELEASE.json"


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    print("STATE=HOLD_XIAOJ_SOVEREIGN_MEMBER_LLM_READINESS")
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require(path: Path, needles: list[str]) -> str:
    text = read(path)
    for needle in needles:
        if needle not in text:
            fail(f"missing_text:{path.relative_to(ROOT)}:{needle}")
    return text


def main() -> int:
    contract = json.loads(read(CONTRACT))
    if contract.get("state") != "HOLD_P2_PRODUCT_RELEASE_GAPS_PRESENT":
        fail("contract_must_hold_until_p2_gaps_closed")
    if contract.get("overall_assessment") != "partial_landing_not_full_product_release":
        fail("contract_overall_assessment_wrong")
    side_effects = contract.get("p1_side_effects", {})
    for key in [
        "db_write_performed_by_this_contract",
        "deploy",
        "service_restart",
        "raw_member_plaintext_read",
        "raw_api_key_read",
        "external_api_call",
    ]:
        if side_effects.get(key) is not False:
            fail(f"contract_side_effect_not_false:{key}")

    status_by_id = {row.get("id"): row.get("status") for row in contract.get("capabilities", [])}
    expected_status = {
        "association_human_world_authority_governance": "PARTIAL_LANDED",
        "odoo_member_pii_to_local_packet_return": "NOT_FULLY_LANDED",
        "replace_8d_delegate_identity": "PARTIAL_LANDED",
        "claim_sovereign_xiaoj": "PARTIAL_LANDED",
        "total_field_llm_reality_layer_governance": "P1_CONTRACT_LANDED",
        "user_google_gemini_api_dedicated_llm": "P1_NO_PLAINTEXT_CONTRACT_LANDED_RUNTIME_NOT_RELEASE_READY",
    }
    if status_by_id != expected_status:
        fail(f"capability_status_mismatch:{status_by_id}")

    require(DOC, [
        "STATE=HOLD_P2_PRODUCT_RELEASE_GAPS_PRESENT",
        "Odoo 個資回傳本機",
        "如何更換八維碼代理身分",
        "如何領用主權小J",
        "使用者 Google Gemini API 專屬 LLM",
        "總場 LLM 真實/幻境分層治理",
        "LLM hallucination: `CONDITIONALLY_ALLOWED_AS_IMAGINED_CANDIDATE`",
        "LLM 本身不是事實權威。",
        "truth boundary、evidence anchor、本地重構上下文與 verifier status",
        "real claims require local evidence refs",
        "execution claims require the local gate",
        "P1_NO_PLAINTEXT_CONTRACT_LANDED_RUNTIME_NOT_RELEASE_READY",
        "P1 no-plaintext Gemini candidate-worker packet contract",
        "Odoo personal data return to local: `NO",
        "Replace 8D delegate identity: `NO",
        "User Gemini API dedicated LLM: `P1 no-plaintext candidate contract exists",
    ])

    require(MEMBER_MODEL, [
        '_name = "wuchang.member.registration"',
        '_name = "wuchang.member.group.registration.batch"',
        '_name = "wuchang.member.group.registration.packet"',
        "create_from_group_claim",
        "hash_provider_ref",
        "D8_ENVELOPE",
        "member_plaintext_policy",
    ])
    require(MEMBER_CTRL, [
        "/wuchang/member/register/group/<string:packet_ref>",
        "/wuchang/member/register/group/<string:packet_ref>/claim",
        "/wuchang/member/register/group/<string:packet_ref>/confirm_dry_run",
    ])
    require(GOOGLE_CTRL, [
        "GOOGLE_AUTH_URL",
        "GOOGLE_TOKEN_URL",
        "GOOGLE_USERINFO_URL",
        "wuchang_group_auth_ref",
        "google_member_masked",
    ])
    require(GOOGLE_PARTNER, [
        "wuchang_google_sub",
        "wuchang_google_email_verified",
        "_wuchang_get_or_create_google_member",
    ])
    require(CORE_SETTINGS, [
        "ai_mode",
        "gen_model",
        "google_api_key",
        "ollama_model",
        "params.set_param('wuchang.google_api_key'",
    ])
    require(CORE_SETTINGS_VIEW, [
        "ai_mode",
        "gen_model",
        "google_api_key",
        "password=\"True\"",
    ])
    core_ctrl = require(CORE_CTRL, [
        "@http.route('/wuchang/config/llm'",
        "@http.route('/wuchang/llm/generate'",
        "wuchang.google_api_key",
        "generativelanguage.googleapis.com",
    ])
    if "params.set_param('wuchang.google_api_key', key)" not in core_ctrl:
        fail("gemini_raw_key_storage_not_detected_as_prototype")
    if not re.search(r"@http\.route\('/wuchang/llm/generate', type='http', auth='public'", core_ctrl):
        fail("public_llm_generate_route_not_detected")
    require(API_SEPARATION, [
        "wuchang.api.account.separation",
        "google_api_key",
        "commercial",
        "nonprofit",
    ])
    gemini_contract = json.loads(read(GEMINI_WORKER_CONTRACT))
    if gemini_contract.get("state") != "P1_CONTRACT_READY_NO_EXTERNAL_CALL":
        fail("gemini_worker_contract_state_wrong")
    if gemini_contract.get("authority_boundary", {}).get("gemini_authority") is not False:
        fail("gemini_worker_contract_gemini_authority_not_false")
    if gemini_contract.get("zero_latency_local_decision", {}).get("decision_latency_class") != "LOCAL_ZERO_NETWORK_RTT":
        fail("gemini_worker_zero_latency_missing")
    reality_boundary = gemini_contract.get("reality_boundary", {})
    if reality_boundary.get("llm_hallucination_allowed") != "conditional":
        fail("gemini_reality_boundary_hallucination_policy_missing")
    if reality_boundary.get("allowed_hallucination_layer") != "IMAGINED_CANDIDATE":
        fail("gemini_reality_boundary_layer_wrong")
    if reality_boundary.get("environment_provided_by_total_field") is not True:
        fail("gemini_reality_boundary_environment_missing")
    if reality_boundary.get("llm_self_truth_authority") is not False:
        fail("gemini_llm_self_truth_authority_not_false")
    if reality_boundary.get("truth_boundary_ref_required") is not True:
        fail("gemini_truth_boundary_required_missing")
    if reality_boundary.get("real_claim_requires_evidence_ref") is not True:
        fail("gemini_real_claim_evidence_policy_missing")
    if reality_boundary.get("execution_claim_requires_local_gate") is not True:
        fail("gemini_execution_gate_policy_missing")
    if reality_boundary.get("cloud_can_mark_real_verified") is not False:
        fail("gemini_cloud_can_mark_real_verified_not_false")
    if reality_boundary.get("total_field_distinguishes_real_or_imagined") is not True:
        fail("gemini_total_field_reality_distinction_missing")

    for path in [GROUP_8D_VERIFY, MEMBER_BROWSER_VERIFY, SOVEREIGN_1B_VERIFY, ACTIVE_MEMBER_BROWSER, GEMINI_WORKER_TOOL, GEMINI_WORKER_VERIFY]:
        if not path.exists():
            fail(f"missing_evidence:{path.relative_to(ROOT)}")

    print("STATE=PASS_XIAOJ_SOVEREIGN_MEMBER_LLM_READINESS_MATRIX")
    print("OVERALL=PARTIAL_LANDING_NOT_FULL_PRODUCT_RELEASE")
    print("GOOGLE_MEMBER_LOGIN=LANDED_IF_CONFIGURED")
    print("GROUP_8D_REGISTRATION=P1_CANDIDATE_DRY_RUN_LANDED")
    print("ODOO_PII_LOCAL_RETURN=NOT_FULLY_LANDED")
    print("REPLACE_8D_DELEGATE=NOT_FULLY_LANDED")
    print("CLAIM_SOVEREIGN_XIAOJ=PARTIAL_LANDED")
    print("LLM_HALLUCINATION=CONDITIONALLY_ALLOWED_AS_IMAGINED_CANDIDATE")
    print("USER_GEMINI_DEDICATED_LLM=P1_NO_PLAINTEXT_CONTRACT_LANDED_RUNTIME_NOT_RELEASE_READY")
    print("RAW_MEMBER_PLAINTEXT_READ=FALSE")
    print("RAW_API_KEY_READ=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
