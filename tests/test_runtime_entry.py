from deploy.runtime import runtime_entry


def test_health_is_local_and_policy_locked():
    data = runtime_entry.health()
    assert data["runtime"] == "taiji_formal_tensor_runtime"
    assert data["bind_host"] == "127.0.0.1"
    assert data["policy_locked"] is True
    assert data["external_api_allowed"] is False
    assert data["live_deploy_allowed"] is False


def test_route_blocks_payment_execute():
    packet = {
        "TensorPacket": {
            "packet_id": "tp_test_payment",
            "tau": {
                "I": {"type": "payment_execute"},
                "R": {},
                "T": {},
                "A": {
                    "governance_level": "L3_block",
                    "human_confirmation_required": True,
                    "credential_boundary": "no_credential_access",
                },
                "P": {},
            },
            "pi": {},
            "sigma": {},
            "lambda": {"target_runtime": "pos"},
            "gamma": {},
            "rho": {},
            "kappa": {},
            "epsilon": {},
            "zeta": {},
            "alpha": {
                "raw_plaintext_stored": False,
                "secret_material_printed": False,
                "external_api_called": False,
                "live_deploy_executed": False,
            },
        }
    }
    result = runtime_entry.route_packet(packet)
    assert result["decision"] == "deadbox"
    assert result["validation"]["risk_level"] == "L3"
