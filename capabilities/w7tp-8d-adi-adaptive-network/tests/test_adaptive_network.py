from __future__ import annotations

import sys
import tempfile
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from w7tp_adaptive_network.drift_detector import (  # noqa: E402
    detect_asymmetric_route,
    detect_container_binding,
    detect_port_collisions,
    detect_router_internet,
    detect_secondary_double_nat,
    detect_service_localhost_only,
    detect_stale_tailscale_ip,
)
from w7tp_adaptive_network.candidate_learning import build_learning_candidate  # noqa: E402
from w7tp_adaptive_network.evidence_writer import ALLOWED_FILES, write_bundle  # noqa: E402
from w7tp_adaptive_network.healing import plan_low_risk_healing  # noqa: E402
from w7tp_adaptive_network.path_evaluator import IPV6_GATES, qualify_ipv6  # noqa: E402
from w7tp_adaptive_network.policy_engine import evaluate_policy  # noqa: E402


def _intent(*permitted: str) -> dict:
    return {
        "intent_id": "TEST",
        "target_identity_state": "OBSERVED_PARTIAL",
        "permitted_paths": list(permitted) if permitted else None,
    }


def _path(
    path_type: str,
    *,
    available: bool = True,
    host: bool = True,
    service: bool = True,
    qualified: bool = True,
    score: float = 1.0,
    remote_agent_online: bool | None = None,
) -> dict:
    return {
        "path_type": path_type,
        "available": available,
        "host_reachable": host,
        "service_reachable": service,
        "qualified": qualified,
        "candidate_score": score,
        "remote_agent_online": remote_agent_online,
        "interface": "test0",
        "target": "candidate-target",
    }


def _all_ipv6_gates(value: bool = True) -> dict[str, bool]:
    return {gate: value for gate in IPV6_GATES}


def test_t1_lan_pass() -> None:
    decision = evaluate_policy(_intent(), [_path("LAN_IPV4")])
    assert decision["decision"] == "ALLOW_LAN_IPV4"


def test_t2_lan_fail_tailscale_pass() -> None:
    decision = evaluate_policy(
        _intent(),
        [_path("LAN_IPV4", available=False), _path("TAILSCALE_IPV4")],
    )
    assert decision["decision"] == "ALLOW_TAILSCALE_IPV4"


def test_t3_lan_and_tailscale_pass_lan_must_win_even_if_score_is_lower() -> None:
    decision = evaluate_policy(
        _intent(),
        [_path("LAN_IPV4", score=1.0), _path("TAILSCALE_IPV4", score=100.0)],
    )
    assert decision["decision"] == "ALLOW_LAN_IPV4"
    assert decision["score_used_as_authority"] is False


def test_t4_ipv6_address_exists_but_route_fails_ipv6_deny() -> None:
    gates = _all_ipv6_gates()
    gates["DEFAULT_ROUTE_PRESENT"] = False
    qualification = qualify_ipv6(gates)
    decision = evaluate_policy(
        _intent("NATIVE_IPV6"),
        [_path("NATIVE_IPV6", qualified=qualification["qualified"])],
    )
    assert qualification["qualified"] is False
    assert decision["decision"] == "DENY"


def test_t5_ipv6_route_exists_but_tcp_fails_ipv6_deny() -> None:
    gates = _all_ipv6_gates()
    gates["TCP_SERVICE_REACHABLE"] = False
    qualification = qualify_ipv6(gates)
    decision = evaluate_policy(
        _intent("NATIVE_IPV6"),
        [
            _path(
                "NATIVE_IPV6",
                service=False,
                qualified=qualification["qualified"],
            )
        ],
    )
    assert "TCP_SERVICE_REACHABLE" in qualification["missing_gates"]
    assert decision["decision"] == "DENY"


def test_t6_remote_agent_offline_but_host_and_service_reachable() -> None:
    decision = evaluate_policy(
        _intent(),
        [
            _path("LAN_IPV4", available=False),
            _path("TAILSCALE_IPV4", remote_agent_online=False),
        ],
    )
    assert decision["decision"] == "ALLOW_TAILSCALE_IPV4"


def test_t7_host_reachable_but_service_localhost_only() -> None:
    decision = evaluate_policy(
        _intent(),
        [_path("LAN_IPV4", host=True, service=False)],
    )
    findings = detect_service_localhost_only(
        {
            "service": "candidate-service",
            "port": 8080,
            "bind_address": "127.0.0.1",
            "loopback": True,
        },
        "LAN",
    )
    assert decision["decision"] == "HOLD"
    assert findings[0]["risk_id"] == "SERVICE_BIND_DRIFT"


def test_t8_stale_tailscale_ip() -> None:
    findings = detect_stale_tailscale_ip(
        ["100.64.0.9"], ["100.64.0.10"], "node.example.ts.net"
    )
    assert findings[0]["risk_id"] == "STALE_TAILSCALE_IP"


def test_t8b_missing_dns_ipv6_is_not_stale_when_observed_ipv4_matches() -> None:
    findings = detect_stale_tailscale_ip(
        ["100.64.0.10"],
        ["100.64.0.10", "fd7a:115c:a1e0::1"],
        "node.example.ts.net",
    )
    assert findings == []


def test_t9_dns_returns_aaaa_first_but_ipv6_unqualified() -> None:
    decision = evaluate_policy(
        _intent(),
        [
            _path("LAN_IPV4"),
            _path("NATIVE_IPV6", available=True, qualified=False, score=100.0),
        ],
    )
    assert decision["decision"] == "ALLOW_LAN_IPV4"


def test_t10_container_reachable_internally_but_host_binding_absent() -> None:
    findings = detect_container_binding(
        container_reachable=True,
        host_binding_present=False,
        service="container-api",
    )
    assert findings[0]["risk_id"] == "CONTAINER_NETWORK_DRIFT"


def test_t11_router_reachable_but_internet_unavailable() -> None:
    findings = detect_router_internet(router_reachable=True, internet_reachable=False)
    assert findings[0]["risk_id"] == "ROUTE_DRIFT"


def test_t12_asymmetric_route() -> None:
    findings = detect_asymmetric_route("enp1s0", "tailscale0")
    assert findings[0]["risk_id"] == "ASYMMETRIC_ROUTE"


def test_t13_duplicate_service_port() -> None:
    bindings = [
        {
            "transport": "tcp",
            "bind_address": "0.0.0.0",
            "port": 8080,
            "service": "service-a",
        },
        {
            "transport": "tcp",
            "bind_address": "0.0.0.0",
            "port": 8080,
            "service": "service-b",
        },
    ]
    findings = detect_port_collisions(bindings)
    assert findings[0]["risk_id"] == "PORT_COLLISION"


def test_t14_all_paths_fail_hold() -> None:
    decision = evaluate_policy(
        _intent(),
        [
            _path("LAN_IPV4", available=False, host=False, service=False),
            _path("TAILSCALE_IPV4", available=False, host=False, service=False),
            _path("NATIVE_IPV6", available=False, host=False, service=False, qualified=False),
            _path("TAILSCALE_IPV6", available=False, host=False, service=False, qualified=False),
        ],
    )
    assert decision["decision"] == "HOLD"


def test_secondary_private_default_is_double_nat_candidate() -> None:
    findings = detect_secondary_double_nat(
        [
            "default via 168.95.98.254 dev ppp0",
            "default via 192.168.1.1 dev eth1 metric 2",
        ],
        "PUBLIC_OR_OTHER",
    )
    assert findings[0]["risk_id"] == "DOUBLE_NAT"


def test_ipv6_all_eight_gates_are_required_and_sufficient() -> None:
    qualification = qualify_ipv6(_all_ipv6_gates())
    assert qualification["qualified"] is True
    assert qualification["missing_gates"] == []


def test_candidate_bundle_supersede_archives_hash_valid_preimage() -> None:
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        first = {name: {"run": 1} for name in ALLOWED_FILES}
        second = {name: {"run": 2} for name in ALLOWED_FILES}
        write_bundle(
            output,
            first,
            timestamp="2026-09-23T00:00:00Z",
            source_node="test-node",
        )
        result = write_bundle(
            output,
            second,
            timestamp="2026-09-23T00:01:00Z",
            source_node="test-node",
            supersede_existing=True,
        )
        archive = output / str(result["previous_candidate_archive"])
        assert archive.is_dir()
        assert '"run": 1' in (archive / "network_state.json").read_text(encoding="utf-8")
        assert '"run": 2' in (output / "network_state.json").read_text(encoding="utf-8")


def test_learning_signal_cannot_override_fixed_policy() -> None:
    learning = build_learning_candidate(
        [_path("LAN_IPV4", score=5.0), _path("TAILSCALE_IPV4", score=99.0)]
    )
    assert learning["observed_performance_order"][0] == "TAILSCALE_IPV4"
    assert learning["fixed_policy_priority"][0] == "LAN_IPV4"
    assert learning["can_override_policy_priority"] is False


def test_healing_plan_is_low_risk_and_not_executed() -> None:
    plan = plan_low_risk_healing(
        [
            {"risk_id": "IPV6_DRIFT"},
            {"risk_id": "SERVICE_BIND_DRIFT"},
        ]
    )
    assert plan["execution_performed"] is False
    assert plan["router_mutation"] is False
    assert {item["decision"] for item in plan["plans"]} == {"ALLOW_CANDIDATE_ONLY"}
