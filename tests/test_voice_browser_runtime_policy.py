from runtime_adapters.voice_browser_runtime_policy import (
    evaluate_voice_browser_action,
    policy_health,
)


def manifest(action_type="voice_to_intent_draft", modality="voice", **overrides):
    data = {
        "request_id": "vb_test_001",
        "source": "voice_gateway",
        "modality": modality,
        "action_type": action_type,
        "target_system": "pos_draft",
        "node_identity": "MSI",
        "permission_window": "runtime",
        "data_sensitivity": "order_draft",
        "raw_text_hash": "sha256:" + "0" * 64,
        "redacted_summary": "beverage draft",
        "created_at": "2026-05-13T00:00:00+08:00",
        "replay_safe": True,
    }
    data.update(overrides)
    return data


def test_policy_health_is_fail_closed_for_sensitive_actions():
    health = policy_health()
    assert health["voice_browser_runtime"] == "ok"
    assert health["payment_execute_allowed"] is False
    assert health["admin_browser_session_allowed"] is False
    assert health["raw_plaintext_context_allowed"] is False


def test_voice_to_intent_draft_allowed_with_audit():
    result = evaluate_voice_browser_action(manifest())
    assert result["allowed"] is True
    assert result["risk_level"] == "L1"
    assert result["action"] == "allow_with_audit"
    assert result["audit_required"] is True


def test_browser_read_visible_text_l0_read_only():
    result = evaluate_voice_browser_action(
        manifest(
            action_type="browser_read_visible_text",
            modality="browser",
            target_system="local_dashboard",
            data_sensitivity="non_sensitive_metadata",
        )
    )
    assert result["allowed"] is True
    assert result["risk_level"] == "L0"
    assert result["audit_required"] is False


def test_order_confirm_requires_human_confirmation_queue():
    result = evaluate_voice_browser_action(manifest(action_type="pos_order_confirm"))
    assert result["allowed"] is False
    assert result["risk_level"] == "L2"
    assert result["route"] == "human_confirmation_queue"
    assert result["requires_human_confirmation"] is True


def test_payment_execute_blocked_l3():
    result = evaluate_voice_browser_action(manifest(action_type="payment_execute"))
    assert result["allowed"] is False
    assert result["risk_level"] == "L3"
    assert "blocked_action:payment_execute" in result["errors"]


def test_admin_browser_session_blocked():
    result = evaluate_voice_browser_action(
        manifest(action_type="browser_fill_draft", modality="browser", admin_session=True)
    )
    assert result["allowed"] is False
    assert "admin_browser_session_forbidden" in result["errors"]


def test_raw_plaintext_context_blocked():
    result = evaluate_voice_browser_action(manifest(raw_plaintext_context_stored=True))
    assert result["allowed"] is False
    assert "raw_plaintext_context_stored_forbidden" in result["errors"]


def test_replay_unsafe_routes_deadbox():
    result = evaluate_voice_browser_action(manifest(replay_safe=False))
    assert result["allowed"] is False
    assert result["action"] == "deadbox"
    assert result["route"] == "deadbox"


def test_tensorpacket_shape_supported():
    packet = {
        "TensorPacket": {
            "packet_id": "tp_voice_browser",
            "tau": {
                "I": {
                    "type": "browser_fill_draft",
                    "modality": "browser",
                    "data_sensitivity": "order_draft",
                },
                "A": {
                    "permission_window": "runtime",
                    "payment_allowed": False,
                },
                "P": {
                    "source_node": "MSI",
                    "target_runtime": "pos_draft",
                },
            },
            "pi": {
                "raw_plaintext_context_stored": False,
            },
            "alpha": {
                "secret_material_included": False,
            },
        }
    }
    result = evaluate_voice_browser_action(packet)
    assert result["allowed"] is True
    assert result["risk_level"] == "L1"
