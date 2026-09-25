from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from w7tp_adaptive_network import health_probe  # noqa: E402
from w7tp_adaptive_network.candidate_learning import build_learning_candidate  # noqa: E402
from w7tp_adaptive_network.consumer import resolve_service  # noqa: E402
from w7tp_adaptive_network.drift_detector import (  # noqa: E402
    detect_asymmetric_route,
    detect_container_binding,
    detect_port_collisions,
    detect_router_internet,
    detect_secondary_double_nat,
    detect_service_localhost_only,
    detect_stale_tailscale_ip,
    detect_wan_publication_drift,
)
from w7tp_adaptive_network.evidence_writer import ALLOWED_FILES, write_bundle  # noqa: E402
from w7tp_adaptive_network.failover import evaluate_binding_failover  # noqa: E402
from w7tp_adaptive_network.healing import plan_low_risk_healing  # noqa: E402
from w7tp_adaptive_network.path_evaluator import IPV6_GATES, qualify_ipv6  # noqa: E402
from w7tp_adaptive_network.policy_engine import evaluate_policy  # noqa: E402


TEST_CONTRACT_CORRECTION = (
    "GLOBAL_FIXED_PRIORITY_REMOVED_PER_INTENT_BINDING_AND_ZONE_POLICY_ARE_AUTHORITATIVE_CANDIDATES"
)


def _intent(
    *permitted: str,
    intent_id: str = "TEST",
    source_zone: str = "ZONE_CORE",
    target_zone: str = "ZONE_CORE",
    service_identity: str = "TEST_SERVICE",
    service_class: str = "INTERNAL_APPLICATION",
    published_gateway_bound: bool = False,
    path_preference: list[str] | None = None,
    allow_concurrent_paths: bool = False,
) -> dict:
    return {
        "intent_id": intent_id,
        "source_node": "source",
        "source_zone": source_zone,
        "target_node": "target",
        "target_zone": target_zone,
        "service_identity": service_identity,
        "service_class": service_class,
        "published_gateway_bound": published_gateway_bound,
        "target_identity_state": "OBSERVED_PARTIAL",
        "permitted_paths": list(permitted) if permitted else None,
        "path_preference": path_preference,
        "allow_concurrent_paths": allow_concurrent_paths,
    }


def _path(
    path_type: str,
    *,
    path_id: str | None = None,
    available: bool = True,
    host: bool = True,
    service: bool = True,
    qualified: bool = True,
    score: float = 1.0,
    remote_agent_online: bool | None = None,
    target: str = "candidate-target",
    service_identity: str | None = None,
    expires_at: str | None = None,
) -> dict:
    row = {
        "path_id": path_id or path_type,
        "path_type": path_type,
        "available": available,
        "host_reachable": host,
        "service_reachable": service,
        "qualified": qualified,
        "candidate_score": score,
        "remote_agent_online": remote_agent_online,
        "identity_state": "OBSERVED_PARTIAL",
        "interface": "test0",
        "target": target,
    }
    if service_identity:
        row["service_identity"] = service_identity
    if expires_at:
        row["expires_at"] = expires_at
    return row


def _all_ipv6_gates(value: bool = True) -> dict[str, bool]:
    return {gate: value for gate in IPV6_GATES}


def _verification(*path_ids: str, value: bool = True) -> dict[str, dict[str, bool]]:
    return {
        path_id: {
            "SOURCE_BOUND": value,
            "SOURCE_ZONE_BOUND": value,
            "INTERFACE_BOUND": value,
            "ROUTE_BOUND": value,
            "TARGET_BOUND": value,
            "TARGET_ZONE_BOUND": value,
            "SERVICE_PASS": value,
            "APPLICATION_PASS": value,
            "RESPONSE_VERIFIED": value,
        }
        for path_id in path_ids
    }


def _resolve(
    intent_id: str,
    paths: list[dict],
    verification: dict,
    *,
    source_zone: str = "ZONE_CORE",
    target_zone: str = "ZONE_CORE",
    service_identity: str = "TEST_SERVICE",
    service_class: str = "INTERNAL_APPLICATION",
    published_gateway_bound: bool = False,
    permitted_paths: list[str] | None = None,
    allow_concurrent_paths: bool = False,
    observed_at: str = "2026-09-24T00:00:00Z",
    now: str = "2026-09-24T00:00:00Z",
) -> dict:
    return resolve_service(
        intent_id,
        "source",
        "target",
        service_identity,
        source_zone=source_zone,
        target_zone=target_zone,
        service_class=service_class,
        published_gateway_bound=published_gateway_bound,
        paths=paths,
        verification=verification,
        permitted_paths=permitted_paths,
        allow_concurrent_paths=allow_concurrent_paths,
        observed_at=observed_at,
        now=now,
    )


def test_t1_lan_candidate_selected_for_this_intent() -> None:
    decision = evaluate_policy(_intent(), [_path("LAN_IPV4")])
    assert decision["candidate_decision"] == "CANDIDATE_PATH_SELECTED"
    assert decision["selected_path"] == "LAN_IPV4"


def test_t2_binding_local_fallback_to_tailscale() -> None:
    decision = evaluate_policy(
        _intent(),
        [_path("LAN_IPV4", available=False), _path("TAILSCALE_IPV4")],
    )
    assert decision["selected_path"] == "TAILSCALE_IPV4"


def test_t3_test_contract_correction_uses_per_intent_preference() -> None:
    intent = _intent(path_preference=["TAILSCALE_IPV4", "LAN_IPV4"])
    decision = evaluate_policy(
        intent,
        [_path("LAN_IPV4", score=100.0), _path("TAILSCALE_IPV4", score=1.0)],
    )
    assert TEST_CONTRACT_CORRECTION.startswith("GLOBAL_FIXED_PRIORITY_REMOVED")
    assert decision["selected_path"] == "TAILSCALE_IPV4"
    assert decision["score_used_as_authority"] is False


def test_t4_ipv6_address_exists_but_route_fails_hold() -> None:
    gates = _all_ipv6_gates()
    gates["DEFAULT_ROUTE_PRESENT"] = False
    qualification = qualify_ipv6(gates)
    decision = evaluate_policy(
        _intent("NATIVE_IPV6"),
        [_path("NATIVE_IPV6", qualified=qualification["qualified"])],
    )
    assert qualification["qualified"] is False
    assert decision["decision"] == "HOLD"


def test_t5_ipv6_route_exists_but_tcp_fails_hold() -> None:
    gates = _all_ipv6_gates()
    gates["TCP_SERVICE_REACHABLE"] = False
    qualification = qualify_ipv6(gates)
    decision = evaluate_policy(
        _intent("NATIVE_IPV6"),
        [_path("NATIVE_IPV6", service=False, qualified=qualification["qualified"])],
    )
    assert "TCP_SERVICE_REACHABLE" in qualification["missing_gates"]
    assert decision["decision"] == "HOLD"


def test_t6_remote_agent_offline_does_not_override_service_evidence() -> None:
    decision = evaluate_policy(
        _intent(),
        [
            _path("LAN_IPV4", available=False),
            _path("TAILSCALE_IPV4", remote_agent_online=False),
        ],
    )
    assert decision["selected_path"] == "TAILSCALE_IPV4"


def test_t7_host_reachable_but_service_localhost_only() -> None:
    decision = evaluate_policy(_intent(), [_path("LAN_IPV4", host=True, service=False)])
    findings = detect_service_localhost_only(
        {"service": "candidate-service", "port": 8080, "bind_address": "127.0.0.1", "loopback": True},
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
        ["100.64.0.10"], ["100.64.0.10", "fd7a:115c:a1e0::1"], "node.example.ts.net"
    )
    assert findings == []


def test_t9_unqualified_ipv6_cannot_displace_qualified_lan() -> None:
    decision = evaluate_policy(
        _intent(),
        [_path("LAN_IPV4"), _path("NATIVE_IPV6", qualified=False, score=100.0)],
    )
    assert decision["selected_path"] == "LAN_IPV4"


def test_t10_container_reachable_internally_but_host_binding_absent() -> None:
    findings = detect_container_binding(
        container_reachable=True, host_binding_present=False, service="container-api"
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
        {"transport": "tcp", "bind_address": "0.0.0.0", "port": 8080, "service": "service-a"},
        {"transport": "tcp", "bind_address": "0.0.0.0", "port": 8080, "service": "service-b"},
    ]
    findings = detect_port_collisions(bindings)
    assert findings[0]["risk_id"] == "PORT_COLLISION"


def test_t14_all_paths_fail_holds_only_this_intent() -> None:
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
    assert decision["routing_unit"] == "PER_INTENT_BINDING"


def test_wan_publication_rules_without_application_verification_are_drift() -> None:
    findings = detect_wan_publication_drift(
        port_forwarding_enabled=True,
        forwarding_rule_count=3,
        application_verified=False,
    )
    assert findings[0]["risk_id"] == "WAN_PUBLICATION_DRIFT"


def test_secondary_private_default_is_double_nat_candidate() -> None:
    findings = detect_secondary_double_nat(
        ["default via 168.95.98.254 dev ppp0", "default via 192.168.1.1 dev eth1 metric 2"],
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
        write_bundle(output, first, timestamp="2026-09-23T00:00:00Z", source_node="test-node")
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


def test_learning_signal_cannot_override_intent_or_zone_policy() -> None:
    learning = build_learning_candidate(
        [_path("LAN_IPV4", score=5.0), _path("TAILSCALE_IPV4", score=99.0)]
    )
    assert learning["observed_performance_order"][0] == "TAILSCALE_IPV4"
    assert learning["can_override_intent_policy"] is False
    assert learning["can_override_zone_policy"] is False


def test_healing_plan_is_low_risk_and_not_executed() -> None:
    plan = plan_low_risk_healing([{"risk_id": "IPV6_DRIFT"}, {"risk_id": "SERVICE_BIND_DRIFT"}])
    assert plan["execution_performed"] is False
    assert plan["router_mutation"] is False
    assert {item["decision"] for item in plan["plans"]} == {"ALLOW_CANDIDATE_ONLY"}


def test_t31_different_intents_can_use_different_active_paths() -> None:
    paths = [_path("LAN_IPV4"), _path("TAILSCALE_IPV4")]
    verification = _verification("LAN_IPV4", "TAILSCALE_IPV4")
    local = _resolve("LOCAL_SERVICE", paths, verification)
    remote = _resolve(
        "REMOTE_MANAGEMENT",
        paths,
        verification,
        source_zone="ZONE_TAILSCALE",
        target_zone="ZONE_MANAGEMENT",
    )
    assert local["selected_path"] == "LAN_IPV4"
    assert remote["selected_path"] == "TAILSCALE_IPV4"
    assert local["authorized"] is True and remote["authorized"] is True


def test_t32_lan_failure_for_one_binding_does_not_disable_other_lan_bindings() -> None:
    healthy_paths = [_path("LAN_IPV4"), _path("TAILSCALE_IPV4")]
    verification = _verification("LAN_IPV4", "TAILSCALE_IPV4")
    first = _resolve("FIRST", healthy_paths, verification)
    second = _resolve("SECOND", healthy_paths, verification)
    degraded = [_path("LAN_IPV4", available=False), _path("TAILSCALE_IPV4")]
    switched = evaluate_binding_failover(first, degraded, verification, now="2026-09-24T00:00:00Z")
    assert switched["selected_path"] == "TAILSCALE_IPV4"
    assert switched["binding_state"] == "ALTERNATE_ACTIVE"
    assert switched["other_bindings_modified"] is False
    assert second["selected_path"] == "LAN_IPV4"


def test_healthy_binding_does_not_switch_to_an_alternate() -> None:
    paths = [_path("LAN_IPV4"), _path("TAILSCALE_IPV4")]
    verification = _verification("LAN_IPV4", "TAILSCALE_IPV4")
    binding = _resolve("STABLE", paths, verification)
    reevaluated = evaluate_binding_failover(
        binding, paths, verification, now="2026-09-24T00:00:00Z"
    )
    assert reevaluated["selected_path"] == "LAN_IPV4"
    assert reevaluated["binding_state"] == "HEALTHY"


def test_t33_ipv6_active_for_one_intent_does_not_authorize_another() -> None:
    paths = [_path("NATIVE_IPV6", path_id="NATIVE_IPV6@2001:db8::1")]
    allowed = _resolve(
        "IPV6_ALLOWED",
        paths,
        _verification("NATIVE_IPV6@2001:db8::1"),
        permitted_paths=["NATIVE_IPV6"],
    )
    blocked = _resolve(
        "IPV6_BLOCKED",
        paths,
        _verification("NATIVE_IPV6@2001:db8::1", value=False),
        permitted_paths=["NATIVE_IPV6"],
    )
    assert allowed["authorized"] is True
    assert blocked["authorized"] is False
    assert blocked["decision"] == "HOLD"


def test_t34_guest_service_path_is_not_global_fallback() -> None:
    paths = [
        _path("LAN_IPV4", available=False),
        _path("GUEST_SERVICE_PATH", path_id="GUEST_SERVICE_PATH@guest"),
    ]
    verification = _verification("GUEST_SERVICE_PATH@guest")
    core = _resolve("CORE", paths, verification)
    guest = _resolve(
        "GUEST",
        paths,
        verification,
        source_zone="ZONE_GUEST_SERVICE",
        target_zone="ZONE_GUEST_SERVICE",
        permitted_paths=["GUEST_SERVICE_PATH"],
    )
    assert core["authorized"] is False
    assert guest["selected_path"] == "GUEST_SERVICE_PATH@guest"
    assert guest["authorized"] is True


def test_t35_wan_publication_path_is_not_global_fallback() -> None:
    paths = [
        _path("LAN_IPV4", available=False),
        _path("WAN_PUBLICATION_PATH", path_id="WAN_PUBLICATION_PATH@edge"),
    ]
    verification = _verification("WAN_PUBLICATION_PATH@edge")
    core = _resolve("CORE", paths, verification)
    external = _resolve(
        "PUBLIC_MEMBER_SERVICE",
        paths,
        verification,
        source_zone="ZONE_WAN",
        target_zone="ZONE_FUTURE_PUBLIC_SERVICE",
        service_class="PUBLIC_APPLICATION",
        published_gateway_bound=True,
        permitted_paths=["WAN_PUBLICATION_PATH"],
    )
    assert core["authorized"] is False
    assert external["selected_path"] == "WAN_PUBLICATION_PATH@edge"
    assert external["authorized"] is True


def test_t36_tailscale_management_and_application_paths_are_independent() -> None:
    paths = [
        _path(
            "TAILSCALE_IPV4",
            path_id="TAILSCALE_IPV4@management",
            service_identity="MANAGEMENT_SERVICE",
        ),
        _path(
            "TAILSCALE_IPV4",
            path_id="TAILSCALE_IPV4@application",
            service_identity="APPLICATION_SERVICE",
        ),
    ]
    verification = _verification("TAILSCALE_IPV4@management", "TAILSCALE_IPV4@application")
    management = _resolve(
        "MANAGEMENT",
        paths,
        verification,
        source_zone="ZONE_TAILSCALE",
        target_zone="ZONE_MANAGEMENT",
        service_identity="MANAGEMENT_SERVICE",
    )
    application = _resolve(
        "APPLICATION",
        paths,
        verification,
        source_zone="ZONE_TAILSCALE",
        target_zone="ZONE_CORE",
        service_identity="APPLICATION_SERVICE",
    )
    assert management["selected_path"] == "TAILSCALE_IPV4@management"
    assert application["selected_path"] == "TAILSCALE_IPV4@application"


def test_t37_multiple_qualified_paths_can_coexist() -> None:
    paths = [_path("LAN_IPV4"), _path("TAILSCALE_IPV4")]
    binding = _resolve(
        "CONCURRENT",
        paths,
        _verification("LAN_IPV4", "TAILSCALE_IPV4"),
        allow_concurrent_paths=True,
    )
    assert set(binding["qualified_path_set"]) == {"LAN_IPV4", "TAILSCALE_IPV4"}
    assert set(binding["concurrent_paths"]) == {"LAN_IPV4", "TAILSCALE_IPV4"}
    assert set(binding["active_path_set"]) == {"LAN_IPV4", "TAILSCALE_IPV4"}


def test_t38_one_binding_hold_does_not_force_global_network_hold() -> None:
    path = _path("LAN_IPV4")
    held = _resolve("HELD", [path], _verification("LAN_IPV4", value=False))
    healthy = _resolve("HEALTHY", [path], _verification("LAN_IPV4"))
    assert held["decision"] == "HOLD"
    assert healthy["decision"] == "D8_ALLOW_FOR_THIS_INTENT"


def test_t39_concurrent_path_schema_supported() -> None:
    schema = json.loads((SKILL_ROOT / "schemas/network_state.schema.json").read_text(encoding="utf-8"))
    binding = schema["$defs"]["intentPathBinding"]
    assert "concurrent_paths" in binding["required"]
    assert binding["properties"]["concurrent_paths"]["type"] == "array"


def test_t40_per_intent_d8_decisions_are_deterministic() -> None:
    path = _path("LAN_IPV4")
    first = _resolve("DETERMINISTIC", [path], _verification("LAN_IPV4"))
    second = _resolve(
        "DETERMINISTIC",
        [path],
        _verification("LAN_IPV4"),
        observed_at="2026-09-24T00:01:00Z",
    )
    assert first["decision_id"] == second["decision_id"]


def test_t41_iot_service_path_is_isolated_and_not_global_fallback() -> None:
    paths = [
        _path("LAN_IPV4", available=False),
        _path("IOT_SERVICE_PATH", path_id="IOT_SERVICE_PATH@broker"),
    ]
    verification = _verification("IOT_SERVICE_PATH@broker")
    core = _resolve("CORE_WITH_IOT_PRESENT", paths, verification)
    iot = _resolve(
        "IOT_BROKER",
        paths,
        verification,
        source_zone="ZONE_IOT",
        target_zone="ZONE_IOT_SERVICE",
        permitted_paths=["IOT_SERVICE_PATH"],
    )
    assert core["authorized"] is False
    assert iot["selected_path"] == "IOT_SERVICE_PATH@broker"
    assert iot["authorized"] is True


def test_d8_two_phase_requires_every_gate() -> None:
    verification = _verification("LAN_IPV4")
    verification["LAN_IPV4"]["APPLICATION_PASS"] = False
    binding = _resolve("TWO_PHASE", [_path("LAN_IPV4")], verification)
    assert binding["candidate_selection_state"] == "CANDIDATE_PATH_SELECTED"
    assert binding["authorized"] is False
    assert binding["d8_two_phase_decision"] == "HOLD"


def test_stale_evidence_is_removed_from_qualified_set() -> None:
    path = _path("LAN_IPV4", expires_at="2026-09-24T00:00:30Z")
    binding = _resolve(
        "STALE",
        [path],
        _verification("LAN_IPV4"),
        now="2026-09-24T00:01:00Z",
    )
    assert binding["stale_path_set"] == ["LAN_IPV4"]
    assert binding["authorized"] is False


def test_external_user_cannot_target_core_directly() -> None:
    binding = _resolve(
        "PUBLIC_TO_CORE",
        [_path("WAN_PUBLICATION_PATH")],
        _verification("WAN_PUBLICATION_PATH"),
        source_zone="ZONE_WAN",
        target_zone="ZONE_CORE",
        permitted_paths=["WAN_PUBLICATION_PATH"],
    )
    assert binding["authorized"] is False
    assert binding["zone_policy"]["reason"] == "WAN_DIRECT_TO_PROTECTED_ZONE_DENIED"


def test_external_public_service_requires_explicit_published_gateway_binding() -> None:
    binding = _resolve(
        "PUBLIC_WITHOUT_GATEWAY",
        [_path("WAN_PUBLICATION_PATH")],
        _verification("WAN_PUBLICATION_PATH"),
        source_zone="ZONE_WAN",
        target_zone="ZONE_FUTURE_PUBLIC_SERVICE",
        service_class="PUBLIC_APPLICATION",
        published_gateway_bound=False,
        permitted_paths=["WAN_PUBLICATION_PATH"],
    )
    assert binding["authorized"] is False
    assert binding["zone_policy"]["reason"] == "WAN_PUBLISHED_GATEWAY_NOT_BOUND"


def test_multi_aaaa_candidates_are_qualified_independently() -> None:
    originals = {
        "dns_resolution": health_probe.dns_resolution,
        "route_lookup": health_probe.route_lookup,
        "ping_target": health_probe.ping_target,
        "tcp_connect": health_probe.tcp_connect,
        "http_probe": health_probe.http_probe,
    }
    routed: list[str] = []
    try:
        health_probe.dns_resolution = lambda host: {
            "passed": True,
            "addresses": ["2001:4860:4860::1", "2001:4860:4860::2"],
        }

        def fake_route(target: str, family: int) -> dict:
            routed.append(target)
            return {
                "passed": True,
                "route": {"dev": "eth0", "prefsrc": "2001:4860:1::10", "gateway": "fe80::1"},
            }

        health_probe.route_lookup = fake_route
        health_probe.ping_target = lambda target, family, interface=None: {"passed": True}
        health_probe.tcp_connect = lambda host, port, family: {"passed": True}
        health_probe.http_probe = lambda url, family=0, resolve_address=None, **kwargs: {
            "passed": True,
            "formal_tls_verified": True,
            "remote": resolve_address,
        }
        local = {
            "addresses": [
                {
                    "ifname": "eth0",
                    "addr_info": [{"family": "inet6", "local": "2001:4860:1::10"}],
                }
            ],
            "routes_v6": [{"dst": "default", "dev": "eth0", "gateway": "fe80::1"}],
        }
        result = health_probe.ipv6_qualification_probe(local, "example.com", 443, "https://example.com/")
        assert result["candidate_count"] == 2
        assert len(result["qualified_candidate_ids"]) == 2
        assert set(routed) == {"2001:4860:4860::1", "2001:4860:4860::2"}
        assert result["global_ipv6_pass"] is False
    finally:
        for name, value in originals.items():
            setattr(health_probe, name, value)


def test_formal_tls_default_has_no_insecure_flag_and_diagnostic_never_passes() -> None:
    original = health_probe.run_command
    calls: list[list[str]] = []
    try:
        def fake_run(argv: list[str], timeout: float = 8.0) -> dict:
            calls.append(argv)
            return {
                "returncode": 0,
                "stdout": "200|2001:4860:4860::1|0.01",
                "stderr": "",
                "status": "PASS",
            }

        health_probe.run_command = fake_run
        formal = health_probe.http_probe("https://example.com/")
        diagnostic = health_probe.http_probe("https://example.com/", insecure_diagnostic=True)
        assert "-k" not in calls[0]
        assert formal["passed"] is True
        assert formal["tls_verification"] == "SYSTEM_CA"
        assert "-k" in calls[1]
        assert diagnostic["passed"] is False
        assert diagnostic["tls_verification"] == "TLS_UNVERIFIED_DIAGNOSTIC"
    finally:
        health_probe.run_command = original

# System-level runtime integration checks (no router or WAN activity).
from w7tp_adaptive_network.runtime_adapter import AdaptiveRuntime, load_contract, INTENT


def _runtime_observer():
    return {
        "links": [{"ifname": "lo", "flags": ["UP"]}],
        "dns_summary": "local",
        "command_evidence": {key: {"returncode": 0}
                             for key in ("links", "addresses", "routes_v4")},
    }


def test_system_runtime_contract_loads():
    manifest = load_contract()
    assert manifest["version"] == "0.2.0-candidate.1"
    assert manifest["capability_scope"] == "TAIJI_HUB_SYSTEM_LEVEL"


def test_system_network_provider_not_forced_into_xiaoj_registry():
    manifest = load_contract()
    assert manifest["xiaoj_exclusive"] is False
    assert manifest["force_bind_xiaoj_registry"] is False
    assert manifest["runtime_contract"] == "MINIMAL_TAIJI_HUB_SYSTEM_CAPABILITY_RUNTIME_ADAPTER"


def test_real_consumer_uses_resolve_service():
    consumer = (SKILL_ROOT / "scripts/native_adi_health_consumer.py").read_text()
    assert 'resolve("READ_ONLY_NATIVE_ADI_HEALTH")' in consumer
    runtime = AdaptiveRuntime(observer=_runtime_observer, application_probe=lambda: True)
    assert runtime.refresh()
    assert runtime.resolve(INTENT)["authorized"] is True


def test_continuous_observer_refreshes_evidence():
    stamps = iter([1, 2, 3])
    runtime = AdaptiveRuntime(observer=_runtime_observer, application_probe=lambda: True,
                              clock=lambda: next(stamps))
    assert runtime.refresh()
    assert runtime.refresh()
    assert runtime.status()["observation_count"] == 2


def test_one_binding_failure_does_not_global_hold():
    first = _resolve("FIRST", [_path("LAN_IPV4", path_id="A")], _verification("A"))
    second = _resolve("SECOND", [_path("TAILSCALE_IPV4", path_id="B")], _verification("B"))
    failed = evaluate_binding_failover(first, [_path("LAN_IPV4", path_id="A", available=False)],
                                       _verification("A"), now="2026-09-24T00:00:00Z")
    assert failed["binding_state"] in ("PRIMARY_PATH_FAILED", "HOLD")
    assert second["authorized"] is True
    assert failed["other_bindings_modified"] is False


def test_runtime_restart_invalidates_transient_decisions():
    runtime = AdaptiveRuntime(observer=_runtime_observer, application_probe=lambda: True)
    assert runtime.refresh()
    restarted = AdaptiveRuntime(observer=_runtime_observer, application_probe=lambda: True)
    assert restarted.resolve(INTENT)["decision"] == "HOLD"
    assert restarted.status()["qualified_path_set"] == []


def test_runtime_restart_rebuilds_bindings():
    restarted = AdaptiveRuntime(observer=_runtime_observer, application_probe=lambda: True)
    assert restarted.status()["health"] == "HOLD"
    assert restarted.refresh()
    assert restarted.resolve(INTENT)["authorized"]


def test_runtime_active_does_not_promote_canonical():
    runtime = AdaptiveRuntime(observer=_runtime_observer, application_probe=lambda: True)
    assert runtime.refresh()
    state = runtime.status()
    assert state["canonical_status"] == "CANDIDATE_ONLY"
    assert state["runtime_state"] != "ACTIVE"


def test_port_9002_not_assumed_d8():
    manifest = load_contract()
    assert manifest["port_9002_is_d8"] is False
    assert "9002" not in (SKILL_ROOT / "scripts/network_runtime.py").read_text()
    assert manifest["runtime_transport"] == "UNIX_SOCKET_NO_PORT_ALLOCATION"


def test_port_forward_rules_do_not_imply_public_application_active():
    runtime = AdaptiveRuntime(observer=_runtime_observer, application_probe=lambda: True)
    assert runtime.refresh()
    assert "WAN_PUBLICATION_PATH" not in runtime.status()["available_path_set"]


def test_observer_failed_refresh_fails_closed():
    healthy = [True]
    runtime = AdaptiveRuntime(observer=_runtime_observer,
                              application_probe=lambda: healthy[0])
    assert runtime.refresh()
    healthy[0] = False
    assert not runtime.refresh()
    assert runtime.resolve(INTENT)["decision"] == "HOLD"
    assert runtime.status()["active_path_set"] == []


def test_unallocated_tcp_port_is_absent():
    source = (SKILL_ROOT / "scripts/w7tp_adaptive_network/runtime_adapter.py").read_text()
    assert "ThreadingHTTPServer" not in source
    assert "UnixHTTPServer" in source

def test_msi_two_carriers_and_per_binding_failover():
    from w7tp_adaptive_network import runtime_adapter as adapter
    import time
    with tempfile.TemporaryDirectory() as tmp:
        old = adapter.REMOTE_EVIDENCE
        adapter.REMOTE_EVIDENCE = Path(tmp) / "msi.json"
        try:
            runtime = adapter.AdaptiveRuntime(observer=_runtime_observer,
                                              application_probe=lambda: True)
            packet = {
                "schema": "MSI_TWO_PATH_HEALTH_OBSERVATION/1",
                "source_node": "MSI",
                "observed_at_epoch": time.time(),
                "paths": {
                    "LAN_IPV4": {"interface": "eth2", "source_ipv4": "192.168.50.84", "route_bound": True,
                                 "application_pass": True},
                    "TAILSCALE_IPV4": {"interface": "tailscale0", "source_ipv4": "100.84.204.114", "route_bound": True,
                                       "application_pass": True},
                },
            }
            adapter.REMOTE_EVIDENCE.write_text(json.dumps(packet))
            assert runtime.refresh()
            remote = runtime.resolve(adapter.REMOTE_INTENT)
            assert remote["selected_path"] == "MSI_ADI_LAN"
            assert set(remote["qualified_path_set"]) == {"MSI_ADI_LAN", "MSI_ADI_TAILSCALE"}
            packet["paths"]["LAN_IPV4"]["application_pass"] = False
            adapter.REMOTE_EVIDENCE.write_text(json.dumps(packet))
            assert runtime.refresh()
            assert runtime.resolve(adapter.REMOTE_INTENT)["selected_path"] == "MSI_ADI_TAILSCALE"
            assert runtime.resolve(adapter.INTENT)["authorized"]
            assert runtime.status()["failover_bindings"][adapter.REMOTE_INTENT]["other_bindings_modified"] is False
            packet["paths"]["LAN_IPV4"]["application_pass"] = True
            adapter.REMOTE_EVIDENCE.write_text(json.dumps(packet))
            assert runtime.refresh()
            assert "MSI_ADI_LAN" in runtime.resolve(adapter.REMOTE_INTENT)["qualified_path_set"]
        finally:
            adapter.REMOTE_EVIDENCE = old


def test_remote_evidence_stale_holds_only_remote():
    from w7tp_adaptive_network import runtime_adapter as adapter
    with tempfile.TemporaryDirectory() as tmp:
        old = adapter.REMOTE_EVIDENCE
        adapter.REMOTE_EVIDENCE = Path(tmp) / "msi.json"
        try:
            packet = {"schema": "MSI_TWO_PATH_HEALTH_OBSERVATION/1",
                      "source_node": "MSI", "observed_at_epoch": 0,
                      "paths": {"LAN_IPV4": {}, "TAILSCALE_IPV4": {}}}
            adapter.REMOTE_EVIDENCE.write_text(json.dumps(packet))
            runtime = adapter.AdaptiveRuntime(observer=_runtime_observer,
                                              application_probe=lambda: True)
            assert runtime.refresh()
            assert runtime.resolve(adapter.REMOTE_INTENT)["decision"] == "HOLD"
            assert runtime.resolve(adapter.INTENT)["authorized"]
        finally:
            adapter.REMOTE_EVIDENCE = old

def test_remote_ttl_expires_at_consumer_lookup():
    from w7tp_adaptive_network import runtime_adapter as adapter
    import time
    with tempfile.TemporaryDirectory() as tmp:
        old = adapter.REMOTE_EVIDENCE
        adapter.REMOTE_EVIDENCE = Path(tmp) / "msi.json"
        try:
            packet = {"schema": "MSI_TWO_PATH_HEALTH_OBSERVATION/1",
                      "source_node": "MSI", "observed_at_epoch": time.time(),
                      "paths": {
                          "LAN_IPV4": {"interface": "eth2", "source_ipv4": "192.168.50.84", "route_bound": True,
                                       "application_pass": True},
                          "TAILSCALE_IPV4": {"interface": "tailscale0",
                                            "source_ipv4": "100.84.204.114", "route_bound": True, "application_pass": True},
                      }}
            adapter.REMOTE_EVIDENCE.write_text(json.dumps(packet))
            runtime = adapter.AdaptiveRuntime(observer=_runtime_observer,
                                              application_probe=lambda: True)
            assert runtime.refresh()
            assert runtime.resolve(adapter.REMOTE_INTENT)["authorized"]
            runtime.remote_valid_until_epoch = 0
            assert runtime.resolve(adapter.REMOTE_INTENT)["decision"] == "HOLD"
            assert runtime.resolve(adapter.INTENT)["authorized"]
        finally:
            adapter.REMOTE_EVIDENCE = old

def test_msi_consumer_resolves_selected_service_before_use():
    import importlib.util
    candidate = SKILL_ROOT / "scripts/msi_network_consumer.py"
    source = candidate.read_text()
    assert "/resolve_service?intent_id=MSI_READ_ONLY_NATIVE_ADI_HEALTH" in source
    assert "selected_application_pass" in source
    spec = importlib.util.spec_from_file_location("msi_network_consumer", candidate)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    compile(module.REMOTE_QUERY, "remote_query", "exec")


def test_route_dns_drift_detected_from_new_observation():
    counter = [0]
    def observer():
        counter[0] += 1
        local = _runtime_observer()
        local["routes_v4"] = [{"gateway": str(counter[0])}]
        local["dns_summary"] = str(counter[0])
        return local
    runtime = AdaptiveRuntime(observer=observer, application_probe=lambda: True)
    assert runtime.refresh()
    assert runtime.status()["dns_drift"] == "FIRST_OBSERVATION"
    assert runtime.refresh()
    assert runtime.status()["dns_drift"] == "CHANGED"
    assert runtime.status()["route_drift"] == "CHANGED"


def test_route_expiry_telemetry_does_not_create_false_drift():
    counter = [600]
    def observer():
        counter[0] -= 1
        local = _runtime_observer()
        local["routes_v6"] = [{
            "dst": "default", "gateway": "fe80::1", "dev": "eth0",
            "protocol": "ra", "expires": counter[0],
        }]
        return local
    runtime = AdaptiveRuntime(observer=observer, application_probe=lambda: True)
    assert runtime.refresh()
    assert runtime.status()["route_drift"] == "FIRST_OBSERVATION"
    assert runtime.refresh()
    assert runtime.status()["route_drift"] == "UNCHANGED"


def test_refresh_keeps_fresh_snapshot_until_new_observation_completes():
    import threading
    entered = threading.Event()
    release = threading.Event()
    calls = [0]
    def observer():
        calls[0] += 1
        if calls[0] == 2:
            entered.set()
            assert release.wait(2)
        return _runtime_observer()
    runtime = AdaptiveRuntime(observer=observer, application_probe=lambda: True)
    assert runtime.refresh()
    worker = threading.Thread(target=runtime.refresh)
    worker.start()
    assert entered.wait(2)
    assert runtime.status()["health"].startswith("PASS_")
    assert runtime.resolve(INTENT)["authorized"] is True
    release.set()
    worker.join(2)
    assert not worker.is_alive()

def test_operational_gates_do_not_bypass_total_field_runtime_decision():
    from w7tp_adaptive_network import runtime_adapter as adapter
    import hashlib
    import time
    with tempfile.TemporaryDirectory() as tmp:
        old_marker, old_remote = adapter.ACTIVATION_MARKER, adapter.REMOTE_EVIDENCE
        adapter.ACTIVATION_MARKER = Path(tmp) / "activation-gates.json"
        adapter.REMOTE_EVIDENCE = Path(tmp) / "msi.json"
        try:
            evidence = Path(tmp) / "evidence.json"
            evidence.write_text('{"result":"PASS"}')
            digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
            gates = {
                key: "PASS" for key in (
                    "SYSTEM_RUNTIME_CONTRACT", "INSTALLATION", "RUNTIME_ENTRYPOINT",
                    "CONTINUOUS_OBSERVER", "REAL_CONSUMER_BINDING",
                    "PER_INTENT_BINDING", "PER_BINDING_FAILOVER",
                    "RESTART_RECOVERY", "FAIL_CLOSED")
            }
            marker = {
                "schema": "SYSTEM_ADAPTIVE_NETWORK_RUNTIME_GATE/1",
                "gates": gates, "canonical_status": "CANDIDATE_ONLY",
                "source_sha256sum_sha256": hashlib.sha256(
                    (SKILL_ROOT / "SOURCE_SHA256SUMS").read_bytes()).hexdigest(),
                "runtime_contract_sha256": hashlib.sha256(
                    (SKILL_ROOT / "deploy/w7tp-adaptive-network.service").read_bytes()).hexdigest(),
                "failover_evidence": {"filename": evidence.name, "sha256": digest},
                "restart_evidence": {"filename": evidence.name, "sha256": digest},
            }
            adapter.ACTIVATION_MARKER.write_text(json.dumps(marker))
            packet = {
                "schema": "MSI_TWO_PATH_HEALTH_OBSERVATION/1",
                "source_node": "MSI", "observed_at_epoch": time.time(),
                "paths": {
                    "LAN_IPV4": {"interface": "eth2", "source_ipv4": "192.168.50.84", "route_bound": True,
                                 "application_pass": True},
                    "TAILSCALE_IPV4": {"interface": "tailscale0",
                                       "source_ipv4": "100.84.204.114", "route_bound": True, "application_pass": True},
                },
            }
            adapter.REMOTE_EVIDENCE.write_text(json.dumps(packet))
            runtime = adapter.AdaptiveRuntime(observer=_runtime_observer,
                                              application_probe=lambda: True)
            assert runtime.refresh()
            state = runtime.status()
            assert state["runtime_state"] == "OBSERVER_RUNNING_LIMITED"
            assert state["total_field_decision"] == "NOT_RUN"
            assert state["canonical_status"] == "CANDIDATE_ONLY"
            evidence.write_text('{"result":"TAMPERED"}')
            assert runtime.status()["runtime_state"] != "ACTIVE"
        finally:
            adapter.ACTIVATION_MARKER, adapter.REMOTE_EVIDENCE = old_marker, old_remote


def test_hash_bound_closed_total_field_decision_activates_runtime():
    from datetime import datetime, timezone
    from w7tp_adaptive_network import runtime_adapter as adapter
    import hashlib
    import os
    import time

    with tempfile.TemporaryDirectory() as tmp:
        old_paths = (
            adapter.ACTIVATION_MARKER,
            adapter.REMOTE_EVIDENCE,
            adapter.TOTAL_FIELD_RUNTIME_DECISION,
            adapter.TOTAL_FIELD_AUTHORITY_POINTER,
        )
        adapter.ACTIVATION_MARKER = Path(tmp) / "activation-gates.json"
        adapter.REMOTE_EVIDENCE = Path(tmp) / "msi.json"
        adapter.TOTAL_FIELD_RUNTIME_DECISION = Path(tmp) / "total-field-runtime-decision.json"
        adapter.TOTAL_FIELD_AUTHORITY_POINTER = Path(tmp) / "ACTIVE_TOTAL_FIELD_AUTHORITY.json"
        try:
            evidence = Path(tmp) / "evidence.json"
            evidence.write_text('{"result":"PASS"}')
            evidence_sha = hashlib.sha256(evidence.read_bytes()).hexdigest()
            marker = {
                "schema": "SYSTEM_ADAPTIVE_NETWORK_RUNTIME_GATE/1",
                "gates": {key: "PASS" for key in (
                    "SYSTEM_RUNTIME_CONTRACT", "INSTALLATION", "RUNTIME_ENTRYPOINT",
                    "CONTINUOUS_OBSERVER", "REAL_CONSUMER_BINDING",
                    "PER_INTENT_BINDING", "PER_BINDING_FAILOVER",
                    "RESTART_RECOVERY", "FAIL_CLOSED")},
                "canonical_status": "CANDIDATE_ONLY",
                "source_sha256sum_sha256": hashlib.sha256(
                    (SKILL_ROOT / "SOURCE_SHA256SUMS").read_bytes()).hexdigest(),
                "runtime_contract_sha256": hashlib.sha256(
                    (SKILL_ROOT / "deploy/w7tp-adaptive-network.service").read_bytes()).hexdigest(),
                "failover_evidence": {"filename": evidence.name, "sha256": evidence_sha},
                "restart_evidence": {"filename": evidence.name, "sha256": evidence_sha},
            }
            adapter.ACTIVATION_MARKER.write_text(json.dumps(marker))
            authority = {
                "allowed_effects": [adapter.TOTAL_FIELD_RUNTIME_EFFECT],
                "contract_state": "ACTIVE_FORMAL",
                "formal_decision_authority": True,
                "formal_seal_authority": True,
                "node_id": "taiji01",
                "prohibited_effects": [],
                "state": "ACTIVE_TOTAL_FIELD_AUTHORITY",
            }
            adapter.TOTAL_FIELD_AUTHORITY_POINTER.write_text(json.dumps(authority))
            os.chmod(adapter.TOTAL_FIELD_AUTHORITY_POINTER, 0o644)
            decision = {
                "schema_version": "W7TP-ADAPTIVE-NETWORK-RUNTIME-DECISION/1.0",
                "packet_type": "TOTAL_FIELD_ADAPTIVE_NETWORK_RUNTIME_DECISION",
                "decision_id": "TEST_ADAPTIVE_NETWORK_RUNTIME_ACTIVATION",
                "state": "PASS_ADAPTIVE_NETWORK_RUNTIME_ACTIVATION",
                "final_decision": "PASS",
                "decision_scope": "ADAPTIVE_NETWORK_READ_ONLY_OBSERVER_RUNTIME_ONLY",
                "capability_id": "w7tp-8d-adi-adaptive-network",
                "capability_version": "v0.2.0-candidate.1",
                "node_id": "taiji01",
                "authority_pointer_ref": "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json",
                "authority_pointer_sha256": adapter.file_sha256(
                    adapter.TOTAL_FIELD_AUTHORITY_POINTER),
                "founder_command": "USE_EXISTING_CLOSED_8D_ADI_TOTAL_FIELD_FOR_LIVE_DEPLOYMENT",
                "source_sha256sum_sha256": adapter.file_sha256(
                    SKILL_ROOT / "SOURCE_SHA256SUMS"),
                "runtime_contract_sha256": adapter.file_sha256(
                    SKILL_ROOT / "deploy/w7tp-adaptive-network.service"),
                "activation_marker_sha256": adapter.file_sha256(adapter.ACTIVATION_MARKER),
                "canonical_status": "CANDIDATE_ONLY",
                "allowed_effects": list(adapter.TOTAL_FIELD_ALLOWED_EFFECTS),
                "forbidden_effects": list(adapter.TOTAL_FIELD_FORBIDDEN_EFFECTS),
                "decided_at": datetime.now(timezone.utc).isoformat(),
                "revocation_operation": "REMOVE_EXACT_RUNTIME_DECISION_AND_RESTART_SELF_ONLY",
            }
            decision["decision_self_sha256"] = hashlib.sha256(
                adapter.canonical_json_bytes(decision)).hexdigest()
            adapter.TOTAL_FIELD_RUNTIME_DECISION.write_text(json.dumps(decision))
            os.chmod(adapter.TOTAL_FIELD_RUNTIME_DECISION, 0o600)
            packet = {
                "schema": "MSI_TWO_PATH_HEALTH_OBSERVATION/1",
                "source_node": "MSI", "observed_at_epoch": time.time(),
                "paths": {
                    "LAN_IPV4": {"interface": "eth2", "source_ipv4": "192.168.50.84",
                                 "route_bound": True, "application_pass": True},
                    "TAILSCALE_IPV4": {"interface": "tailscale0",
                                       "source_ipv4": "100.84.204.114",
                                       "route_bound": True, "application_pass": True},
                },
            }
            adapter.REMOTE_EVIDENCE.write_text(json.dumps(packet))
            runtime = adapter.AdaptiveRuntime(observer=_runtime_observer,
                                              application_probe=lambda: True)
            assert runtime.refresh()
            state = runtime.status()
            assert state["runtime_state"] == "ACTIVE", state
            assert state["total_field_decision"] == "PASS"
            assert state["canonical_status"] == "CANDIDATE_ONLY"
            assert state["intent_path_bindings"][adapter.INTENT]["total_field_decision"] == "PASS"
            assert state["intent_path_bindings"][adapter.REMOTE_INTENT]["total_field_decision"] == "PASS"
            assert runtime.resolve(adapter.REMOTE_INTENT)["total_field_decision"] == "PASS"
            authority["allowed_effects"].append("AUTHORIZE_ANOTHER_8D_ADI_RUNTIME_EFFECT")
            adapter.TOTAL_FIELD_AUTHORITY_POINTER.write_text(json.dumps(authority))
            assert runtime.status()["runtime_state"] == "ACTIVE"
            authority["allowed_effects"].remove(adapter.TOTAL_FIELD_RUNTIME_EFFECT)
            adapter.TOTAL_FIELD_AUTHORITY_POINTER.write_text(json.dumps(authority))
            assert runtime.status()["runtime_state"] == "OBSERVER_RUNNING_LIMITED"
            authority["allowed_effects"].append(adapter.TOTAL_FIELD_RUNTIME_EFFECT)
            adapter.TOTAL_FIELD_AUTHORITY_POINTER.write_text(json.dumps(authority))
            decision["allowed_effects"] = []
            adapter.TOTAL_FIELD_RUNTIME_DECISION.write_text(json.dumps(decision))
            assert runtime.status()["runtime_state"] == "OBSERVER_RUNNING_LIMITED"
        finally:
            (adapter.ACTIVATION_MARKER, adapter.REMOTE_EVIDENCE,
             adapter.TOTAL_FIELD_RUNTIME_DECISION,
             adapter.TOTAL_FIELD_AUTHORITY_POINTER) = old_paths


def test_msi_lan_nic_renumber_uses_current_route():
    from w7tp_adaptive_network import runtime_adapter as adapter
    import time
    with tempfile.TemporaryDirectory() as tmp:
        old = adapter.REMOTE_EVIDENCE
        adapter.REMOTE_EVIDENCE = Path(tmp) / "msi.json"
        try:
            packet = {
                "schema": "MSI_TWO_PATH_HEALTH_OBSERVATION/1",
                "source_node": "MSI", "observed_at_epoch": time.time(),
                "paths": {
                    "LAN_IPV4": {"interface": "eth1", "source_ipv4": "192.168.50.82",
                                 "route_bound": True, "application_pass": True},
                    "TAILSCALE_IPV4": {"interface": "tailscale0",
                                       "source_ipv4": "100.84.204.114",
                                       "route_bound": True, "application_pass": True},
                },
            }
            adapter.REMOTE_EVIDENCE.write_text(json.dumps(packet))
            runtime = adapter.AdaptiveRuntime(observer=_runtime_observer,
                                              application_probe=lambda: True)
            assert runtime.refresh()
            resolved = runtime.resolve(adapter.REMOTE_INTENT)
            assert resolved["selected_path"] == "MSI_ADI_LAN"
            assert resolved["selected_interface"] == "eth1"
            packet["paths"]["LAN_IPV4"]["interface"] = "tailscale0"
            adapter.REMOTE_EVIDENCE.write_text(json.dumps(packet))
            assert runtime.refresh()
            assert runtime.resolve(adapter.REMOTE_INTENT)["selected_path"] == "MSI_ADI_TAILSCALE"
            assert runtime.resolve(adapter.INTENT)["authorized"]
        finally:
            adapter.REMOTE_EVIDENCE = old
