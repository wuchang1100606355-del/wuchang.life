from services.gateway.policies.formal_tensor_validator import validate_formal_tensor_packet


def packet(intent_type="order_create", governance_level="L2_confirm", risk_level="L2"):
    return {
        "TensorPacket": {
            "packet_id": "tp_20260511T184500Z_ab12cd",
            "schema": "taiji.formal_tensor_packet.v1",
            "tau": {
                "I": {
                    "type": intent_type,
                    "modality": "voice",
                    "confidence": 0.96,
                    "semantic_hash": "sha256:" + "0" * 64,
                },
                "R": {
                    "ai_cost": "low",
                    "gpu_required": False,
                    "voice_api_required": False,
                    "browser_runtime_cost": "low",
                    "estimated_tokens": 32,
                    "io_cost": "low",
                },
                "T": {
                    "created_at": "2026-05-11T18:45:00+08:00",
                    "replay_window_sec": 30,
                    "continuity_state": "active",
                    "cache_ttl_sec": 300,
                    "rollback_horizon": "discard_draft",
                },
                "A": {
                    "governance_level": governance_level,
                    "human_confirmation_required": risk_level in {"L2", "L3"},
                    "payment_boundary": "blocked" if intent_type == "payment_execute" else "prepare_only",
                    "deployment_boundary": "no_live_deploy",
                    "credential_boundary": "no_credential_access",
                    "production_overwrite_boundary": "blocked",
                },
                "P": {
                    "source_node": "TDI-NODE-sunmi-pos",
                    "gateway": "TDI-SERVICE-taiji-gateway",
                    "target_runtime": "pos_draft",
                    "container_scope": "cafe_pos_reopen",
                    "domain_route": "pos.wuchang.life",
                    "odoo_scope": "community_industry_branch",
                    "pos_node": "TDI-NODE-sunmi-pos",
                    "line_gateway": "none",
                    "browser_runtime": "none",
                    "audit_runtime": "taiji_audit",
                },
            },
            "pi": {
                "payload_hash": "sha256:" + "1" * 64,
                "raw_plaintext_stored": False,
                "redacted_summary": "Hot beverage order draft.",
            },
            "sigma": {
                "continuity": "reuse",
                "tensor_hash": "tx_91ae7f",
                "pattern": "beverage_hot_standard",
            },
            "lambda": {
                "route": "gateway_to_pos_draft",
                "allowed_targets": ["pos_draft", "audit_runtime"],
            },
            "gamma": {
                "risk_level": risk_level,
                "action": "warn" if risk_level == "L2" else "allow_with_audit",
                "human_decision": "required" if risk_level in {"L2", "L3"} else "not_required",
                "audit_required": risk_level in {"L1", "L2", "L3"},
                "rollback_required": risk_level in {"L2", "L3"},
            },
            "rho": {
                "nonce_hash": "sha256:" + "2" * 64,
                "parent_hash": "root",
                "replay_allowed": False,
            },
            "kappa": {
                "cache_key": "beverage_hot_standard",
                "cache_ttl_sec": 300,
            },
            "epsilon": {
                "entropy_level": "low",
                "retry_budget": 1,
                "gpu_wake_allowed": False,
            },
            "zeta": {
                "deadbox_state": "none",
                "deadbox_reason": "none",
            },
            "alpha": {
                "audit_event_id": "audit_pending",
                "audit_channel": "Taiji_Governance/logs/audit.log",
                "secret_material_printed": False,
                "external_api_called": False,
                "live_deploy_executed": False,
            },
        }
    }


def test_order_create_l2_warn():
    result = validate_formal_tensor_packet(packet())
    assert result["allowed"] is True
    assert result["risk_level"] == "L2"
    assert result["action"] == "warn"


def test_payment_execute_blocked():
    result = validate_formal_tensor_packet(packet(intent_type="payment_execute", governance_level="L3_block", risk_level="L3"))
    assert result["allowed"] is False
    assert result["risk_level"] == "L3"


def test_raw_plaintext_blocked():
    p = packet()
    p["TensorPacket"]["pi"]["raw_plaintext_stored"] = True
    result = validate_formal_tensor_packet(p)
    assert result["allowed"] is False
    assert "raw_plaintext_runtime_memory_forbidden" in result["errors"]
