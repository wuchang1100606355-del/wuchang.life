from runtime_adapters.intent_flow_cache_policy import cache_health, evaluate_intent_flow_cache


def packet(intent_type="pos_order_create", risk_level="L1", raw_plaintext=False):
    return {
        "TensorPacket": {
            "packet_id": "tp_cache_test",
            "schema": "taiji.formal_tensor_packet.v1",
            "tau": {
                "I": {
                    "type": intent_type,
                    "modality": "voice",
                    "semantic_hash": "sha256:" + "0" * 64,
                    "data_sensitivity": "order_draft",
                },
                "R": {},
                "T": {"cache_ttl_sec": 300},
                "A": {
                    "governance_level": "L1_audit",
                    "human_confirmation_required": True,
                    "payment_boundary": "prepare_only",
                    "credential_boundary": "no_credential_access",
                    "production_overwrite_boundary": "blocked",
                },
                "P": {"target_runtime": "pos_draft"},
            },
            "pi": {
                "raw_plaintext_stored": raw_plaintext,
                "redacted_summary": "beverage draft",
            },
            "sigma": {
                "continuity": "reuse",
                "tensor_hash": "tx_91ae7f",
                "pattern": "beverage_hot_standard",
            },
            "lambda": {"route": "gateway_to_pos_draft"},
            "gamma": {
                "risk_level": risk_level,
                "audit_required": True,
                "rollback_required": False,
            },
            "rho": {},
            "kappa": {"cache_ttl_sec": 300},
            "epsilon": {},
            "zeta": {},
            "alpha": {
                "secret_material_printed": False,
                "external_api_called": False,
                "live_deploy_executed": False,
            },
        }
    }


def test_cache_health_active():
    data = cache_health()
    assert data["intent_flow_cache"] == "ok"
    assert data["raw_plaintext_cache_allowed"] is False
    assert data["payment_cache_allowed"] is False


def test_pos_order_draft_flow_cache_allowed():
    result = evaluate_intent_flow_cache(packet())
    assert result["cache_allowed"] is True
    assert result["cache_mode"] == "flow_template_only"
    assert result["requires_human_confirmation_before_pos_submit"] is True


def test_payment_execute_cache_blocked():
    result = evaluate_intent_flow_cache(packet(intent_type="payment_execute", risk_level="L3"))
    assert result["cache_allowed"] is False
    assert result["risk_level"] == "L3"


def test_raw_plaintext_cache_blocked():
    result = evaluate_intent_flow_cache(packet(raw_plaintext=True))
    assert result["cache_allowed"] is False
    assert "raw_plaintext_cache_forbidden" in result["errors"]
