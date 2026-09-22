from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = (
    ROOT
    / ".skill-build"
    / "w7tp-router-wireguard-control"
    / "scripts"
    / "router_total_field_adapter.py"
)


def load_adapter():
    spec = importlib.util.spec_from_file_location("router_total_field_adapter", ADAPTER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_wireguard_plan_routes_into_existing_chain_and_holds_effect():
    adapter = load_adapter()
    packet = adapter.build_router_packet("wireguard_dual_stack_plan", "dual stack")

    assert packet["state"] == "HOLD_D8_ROUTER_NETWORK_EFFECT_NOT_REGISTERED"
    assert packet["D2_STATE"]["router_effect_performed"] is False
    assert packet["D5_EXECUTION_POLICY"]["maximum_effect"] == "HOLD_NO_NETWORK_EFFECT"
    assert packet["D5_EXECUTION_POLICY"]["required_effect_scope"] == (
        "AUTHORIZE_EXACT_ROUTER_NETWORK_CHANGE"
    )
    assert packet["D6_MAPPING"] == "NOT_APPLICABLE_NETWORK_TRANSPORT_ONLY"
    assert packet["D8_ENVELOPE"]["model_is_authority"] is False
    assert "runtime/router/merlin_intent_driver.py" in packet["D3_COORDINATE"][
        "existing_total_field_chain"
    ]


def test_observation_plan_is_read_only_and_sensitive_note_is_rejected():
    adapter = load_adapter()
    packet = adapter.build_router_packet("observe_status", "redacted status")
    assert packet["state"] == "OBSERVE_PLAN_READY"
    assert packet["D5_EXECUTION_POLICY"]["maximum_effect"] == "READ_ONLY_PLAN"

    try:
        adapter.build_router_packet("wireguard_peer_plan", "private key = forbidden")
    except ValueError as exc:
        assert str(exc) == "SENSITIVE_NOTE_REJECTED"
    else:
        raise AssertionError("sensitive note must be rejected")
