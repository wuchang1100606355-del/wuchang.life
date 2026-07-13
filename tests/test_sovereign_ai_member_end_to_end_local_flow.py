from __future__ import annotations

import importlib.util
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
    registration_source = (ROOT / "Taiji_Odoo/addons/wuchang_member_registration/controllers/main.py").read_text()
    assert '"/google/member/login"' in login_source
    assert '"/google/member/callback"' in login_source
    assert "wuchang_group_auth_ref" in login_source
    assert '"/wuchang/member/register/start"' in registration_source
    assert '"/wuchang/member/register/group/<string:packet_ref>"' in registration_source

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
