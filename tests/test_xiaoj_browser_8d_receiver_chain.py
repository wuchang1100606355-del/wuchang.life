from __future__ import annotations

import copy
import datetime as dt
from unittest.mock import patch

import pytest

from tools.member_browser import xiaoj_member_browser_gateway as browser_gateway
from tools.member_browser import xiaoj_member_browser_native_host as native_host
from tools.total_field.w7tp_intent_field_suite.canonical_hash import canonical_sha256
from tools.total_field_candidate_gateway import (
    TotalFieldGatewayError,
    receive_candidate,
)


NOW = dt.datetime(2026, 7, 26, 12, 30, tzinfo=dt.timezone.utc)


def browser_packet(*, created_at: dt.datetime = NOW) -> dict:
    packet = {
        "packet_type": "xiaoj_8d_action_packet",
        "D1_identity": {
            "actor_ref": "actor_ref:member_browser_extension:test_member",
            "actor_type": "member",
            "device_ref": "device_ref:member_browser_extension:test_device",
            "role": "member_role_ref",
            "plaintext_identity_forbidden": True,
        },
        "D2_intent": {
            "primary_intent": "intent_ref:0123456789abcdef",
            "secondary_intent": "redacted_ref:test",
            "transaction_intent": "browse",
            "risk_level": "low",
        },
        "D3_state": {
            "session_state": "active",
            "task_state": "dry_run",
            "browser_state": "dry_run",
            "order_state": "none",
            "context_mode": "ref_only",
        },
        "D4_topology": {
            "channel": "browser_action_bus",
            "site_ref": "site_ref:test",
            "device_topology": "member_browser_extension_to_total_field",
            "origin_scope": "member_owned",
        },
        "D5_resource": {
            "key_policy": "hybrid_ref_only",
            "selected_key_ref": "key_ref:test",
            "api_refs": ["api_ref:test"],
            "model_tier": "small",
            "cache_policy": "ref_cache_only",
            "cost_policy": "budget_cap_ref",
        },
        "D6_governance": {
            "allowed_actions": ["read_text_ref"],
            "forbidden_actions": ["submit_payment"],
            "no_plaintext_context": True,
            "reconstruction_level": "L3_CANDIDATE",
            "human_confirm_required": False,
            "staff_confirm_required": False,
        },
        "D7_verification": {
            "redaction_check_required": True,
            "leak_check_required": True,
            "action_allowlist_required": True,
            "response_verify_required": True,
            "usage_log_required": True,
        },
        "D8_envelope": {
            "packet_id": "PKT_BROWSER_" + "1" * 32,
            "packet_ref": "packet_ref:0123456789abcdef",
            "trace_id": "TRACE_BROWSER_" + "2" * 32,
            "nonce": "nonce_ref:33333333-3333-4333-8333-333333333333",
            "counter": 1,
            "ttl_seconds": 300,
            "created_at": created_at.isoformat().replace("+00:00", "Z"),
            "schema_version": "8d.packet.v1",
            "content_hash": "",
            "content_sha256": "",
            "hmac_ref": "hmac_ref:verifier_required",
            "signature_ref": "signature_ref:verifier_required",
            "replay_protection": True,
            "authority_granted": False,
        },
        "browser_action": {
            "action_ref": "action_ref:0123456789abcdef",
            "action_type": "read_text_ref",
            "target_ref": "target_ref:0123456789abcdef",
            "params": {
                "controller_ref": "controller_ref:xiaoj_member_browser_1b",
                "intent_ref": "intent_ref:0123456789abcdef",
                "safe_context_ref": "redacted_ref:test",
                "behavior_info_ref": "behavior_ref:0123456789abcdef",
                "cloud_candidate_only": True,
                "candidate_only": True,
                "requires_total_field_verify": True,
            },
            "dry_run": True,
            "submit_forbidden": True,
        },
    }
    unsigned = copy.deepcopy(packet)
    unsigned["D8_envelope"]["content_hash"] = ""
    unsigned["D8_envelope"]["content_sha256"] = ""
    content_sha256 = canonical_sha256(unsigned)
    packet["D8_envelope"]["content_hash"] = content_sha256
    packet["D8_envelope"]["content_sha256"] = content_sha256
    return packet


def transport_envelope(packet: dict | None = None) -> dict:
    original = packet or browser_packet()
    d8 = original["D8_envelope"]
    return {
        "schema_version": "w7tp.browser-8d-transport-envelope.v1",
        "profile_type": "BROWSER_8D_TRANSPORT_ENVELOPE",
        "sender_ref": "web.xiaoj_member_browser_extension.background",
        "receiver_ref": "tools.total_field_candidate_gateway.receive_candidate",
        "return_coordinate": "chrome.runtime.sendMessage",
        "packet_id": d8["packet_id"],
        "trace_id": d8["trace_id"],
        "content_sha256": d8["content_sha256"],
        "reconstruction_level": "L3_CANDIDATE",
        "authority_granted": False,
        "browser_packet": original,
    }


def receive(envelope: dict, ledger: set[str] | None = None, now: dt.datetime = NOW) -> dict:
    return receive_candidate(
        envelope,
        previous_state={},
        observation_domains={},
        browser_replay_ledger=ledger if ledger is not None else set(),
        browser_received_at=now,
    )


def rehash(envelope: dict) -> None:
    packet = envelope["browser_packet"]
    packet["D8_envelope"]["content_hash"] = ""
    packet["D8_envelope"]["content_sha256"] = ""
    digest = canonical_sha256(packet)
    packet["D8_envelope"]["content_hash"] = digest
    packet["D8_envelope"]["content_sha256"] = digest
    envelope["content_sha256"] = digest


def test_original_packet_hash_trace_reconstruction_and_receipt_are_preserved() -> None:
    envelope = transport_envelope()
    original = copy.deepcopy(envelope["browser_packet"])
    result = browser_gateway.forward_transport_envelope(
        envelope,
        replay_ledger=set(),
        received_at=NOW,
    )

    assert envelope["browser_packet"] == original
    assert result["packet_id"] == original["D8_envelope"]["packet_id"]
    assert result["trace_id"] == original["D8_envelope"]["trace_id"]
    assert result["content_sha256"] == original["D8_envelope"]["content_sha256"]
    assert result["reconstruction"]["mode"] == "L3_CANDIDATE"
    assert result["reconstruction"]["candidate_only"] is True
    assert result["verifier"]["state"] == "PASS"
    receipt = result["total_field_receipt"]
    assert receipt["receiver_call_count"] == 1
    assert receipt["trace_id"] == result["trace_id"]
    assert receipt["content_sha256"] == result["content_sha256"]
    assert receipt["authority_granted"] is False
    assert receipt["action_executed"] is False


def test_tampered_content_hash_is_rejected() -> None:
    envelope = transport_envelope()
    envelope["browser_packet"]["D2_intent"]["risk_level"] = "tampered"
    with pytest.raises(TotalFieldGatewayError, match="BROWSER_CONTENT_SHA256_MISMATCH"):
        receive(envelope)


def test_expired_ttl_is_rejected() -> None:
    envelope = transport_envelope(browser_packet(created_at=NOW - dt.timedelta(seconds=301)))
    with pytest.raises(TotalFieldGatewayError, match="BROWSER_TTL_EXPIRED"):
        receive(envelope)


def test_missing_intent_ref_is_rejected_after_valid_rehash() -> None:
    envelope = transport_envelope()
    del envelope["browser_packet"]["browser_action"]["params"]["intent_ref"]
    rehash(envelope)
    with pytest.raises(TotalFieldGatewayError, match="BROWSER_REQUIRED_REF_INVALID"):
        receive(envelope)


def test_nonce_replay_is_rejected_before_second_receiver_run() -> None:
    ledger: set[str] = set()
    envelope = transport_envelope()
    receive(envelope, ledger)
    with pytest.raises(TotalFieldGatewayError, match="BROWSER_NONCE_REPLAY"):
        receive(envelope, ledger)


def test_candidate_packet_cannot_escalate_to_l1_or_l2() -> None:
    for level in ("L1_FULL", "L2_EQUIVALENT"):
        envelope = transport_envelope()
        envelope["reconstruction_level"] = level
        envelope["browser_packet"]["D6_governance"]["reconstruction_level"] = level
        rehash(envelope)
        with pytest.raises(
            TotalFieldGatewayError,
            match="BROWSER_RECONSTRUCTION_LEVEL_ESCALATION_BLOCKED",
        ):
            receive(envelope)


def test_native_host_calls_the_existing_receiver_exactly_once() -> None:
    envelope = transport_envelope(browser_packet(created_at=dt.datetime.now(dt.timezone.utc)))
    native_host.BROWSER_REPLAY_LEDGER.clear()
    with patch.object(
        browser_gateway,
        "receive_candidate",
        wraps=browser_gateway.receive_candidate,
    ) as receiver:
        response = native_host.handle(
            {"type": "XIAOJ_NATIVE_GATEWAY_REQUEST", "transport_envelope": envelope}
        )
    assert receiver.call_count == 1
    assert response["trace_id"] == envelope["trace_id"]
    assert response["content_sha256"] == envelope["content_sha256"]
    assert response["total_field_receipt"]["receiver_call_count"] == 1


def test_native_host_fails_closed_when_receiver_is_unavailable() -> None:
    envelope = transport_envelope(browser_packet(created_at=dt.datetime.now(dt.timezone.utc)))
    with patch.object(browser_gateway, "receive_candidate", side_effect=OSError):
        response = native_host.handle(
            {"type": "XIAOJ_NATIVE_GATEWAY_REQUEST", "transport_envelope": envelope}
        )
    assert response["ok"] is False
    assert response["decision"] == "HOLD"
    assert response["reason"] == "total_field_receiver_unavailable"
    assert "gateway_result" not in response
