from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path
from typing import Any

from .candidate_learning import build_learning_candidate
from .common import evidence_envelope, utc_now
from .drift_detector import detect_risks, detect_stale_tailscale_ip
from .evidence_writer import write_bundle
from .health_probe import (
    dns_resolution,
    http_probe,
    ipv6_qualification_probe,
    ssh_handshake,
    tailscale_ping,
    tcp_connect,
)
from .healing import plan_low_risk_healing
from .identity_resolver import resolve_identities
from .merlin_adapter import observe_merlin, to_redacted_inventory
from .observer import observe_local
from .path_evaluator import qualify_ipv6, score_path
from .route_selector import select_route
from .service_binding import binding_summary, enrich_container_services, parse_listeners


def discover(args: argparse.Namespace) -> dict[str, Any]:
    timestamp = utc_now()
    historical_path_matrices = _load_historical_path_matrices(Path(args.output_dir))
    local = observe_local()
    source_node = local.get("hostname", "LOCALIZED_UNKNOWN")
    merlin = observe_merlin(args.router_alias) if args.router_alias else _no_router_observation()
    role_hints = _parse_role_hints(args.role_hint)
    identities = resolve_identities(local, merlin, role_hints)

    lan_addresses, tailscale_addresses = _local_address_sets(local)
    health_by_port = _local_health_probes(local, lan_addresses)
    bindings = parse_listeners(
        local.get("listeners_raw", ""),
        lan_addresses=lan_addresses,
        tailscale_addresses=tailscale_addresses,
        health_by_port=health_by_port,
    )
    bindings = enrich_container_services(bindings, local.get("docker_containers", []))
    service_matrix = binding_summary(bindings)

    paths, verification, default_application = _build_paths(local, merlin, args)
    intent = {
        "intent_id": args.intent_id,
        "source_node": source_node,
        "target_node": merlin.get("hostname", "MERLIN_ROUTER"),
        "service_identity": "MERLIN_READ_ONLY_SSH_OBSERVER",
        "cross_network_required": False,
        "permitted_paths": ["LAN_IPV4", "TAILSCALE_IPV4", "NATIVE_IPV6", "TAILSCALE_IPV6"],
        "target_identity_state": "OBSERVED_PARTIAL" if merlin.get("reachable") else "LOCALIZED_UNKNOWN",
    }
    route_decision = select_route(intent, paths, verification)

    risks = detect_risks(
        {
            "identity_conflicts": identities.get("conflicts", []),
            "identity_nodes": identities.get("nodes", []),
            "bindings": bindings,
            "default_application_family": default_application.get("address_family", "UNKNOWN"),
            "generic_ipv6_policy_gate_present": False,
            "router_tailscale_interface_present": bool(merlin.get("tailscale_ipv4")),
            "router_tailscale_cli_observed": merlin.get("tailscale_cli") == "present",
            "router_routes_v4": merlin.get("routes_v4", []),
            "router_wan_scope": merlin.get("wan_ipv4_scope", "LOCALIZED_UNKNOWN"),
        }
    )
    dns_findings = _tailscale_dns_findings(local)
    risks.extend(dns_findings)
    risks = _dedupe_risks(risks)
    healing_plan = plan_low_risk_healing(risks)
    learning_candidate = build_learning_candidate(paths, historical_path_matrices)

    route_findings = [
        item for item in risks if item["risk_id"] in {"ROUTE_DRIFT", "IPV6_DRIFT", "ASYMMETRIC_ROUTE"}
    ]
    dns_risks = [item for item in risks if item["risk_id"] in {"DNS_DRIFT", "STALE_DNS", "STALE_TAILSCALE_IP"}]
    reconstruction_states = _reconstruction_states(
        merlin=merlin,
        local=local,
        bindings=bindings,
        paths=paths,
    )

    network_state_field = {
        "semantics": "8_IN_1_SINGLE_STATE_FIELD",
        "D1": intent,
        "D2": {
            "identity_rule": "IP_IS_COORDINATE_NOT_PERMANENT_IDENTITY",
            "node_count": len(identities.get("nodes", [])),
            "conflict_count": len(identities.get("conflicts", [])),
            "identity_map_ref": "node_identity_map.json",
        },
        "D3": {
            "layers": [
                "HOST_NETWORK",
                "WSL_NETWORK",
                "CONTAINER_NETWORK",
                "TAILSCALE_NETWORK",
                "LAN_NETWORK",
                "NATIVE_IPV6_NETWORK",
                "APPLICATION_NETWORK",
                "MERLIN_ROUTER",
            ],
            "interfaces_observed": len(local.get("links", [])),
            "routes_v4_observed": len(local.get("routes_v4", [])),
            "routes_v6_observed": len(local.get("routes_v6", [])),
            "listeners_observed": len(bindings),
        },
        "D4": {
            "evidence_refs": [
                "node_identity_map.json",
                "path_matrix.json",
                "service_binding_matrix.json",
                "network_risks.json",
                "merlin_observation.json",
            ],
            "single_probe_is_authority": False,
        },
        "D5": {
            "priority": [
                "LAN_IPV4",
                "TAILSCALE_IPV4",
                "QUALIFIED_NATIVE_IPV6",
                "QUALIFIED_TAILSCALE_IPV6",
                "HOLD",
            ],
            "score_is_authority": False,
            "unqualified_ipv6_selectable": False,
        },
        "D6": {
            "network_state_field": reconstruction_states,
            "reconstruction_rule": "TARGET_NATIVE_SERVICE_AND_APPLICATION_RESPONSE_REQUIRED",
            "learning_state": learning_candidate["state"],
            "learning_can_override_policy": learning_candidate["can_override_policy_priority"],
        },
        "D7": {
            "risk_count": len(risks),
            "risk_ids": sorted({item["risk_id"] for item in risks}),
            "risk_ref": "network_risks.json",
        },
        "D8": {
            "decision": route_decision["decision"],
            "decision_scope": "CURRENT_INTENT_ONLY",
            "decision_state": route_decision["decision_state"],
            "total_field_decision": "NOT_RUN",
            "canonical": False,
        },
        "coupling": {
            "joint_state_representation": True,
            "coupling_rule": "D1-D7 jointly constrain D8",
            "cross_dimension_constraint": "identity + service + path + application + risk closure",
            "joint_state_transition": "OBSERVED_TO_VERIFIED_CANDIDATE_OR_FAIL_CLOSED",
            "closure_rule": "selected path end-to-end chain must be complete",
            "fail_closed_rule": "conflict, missing evidence, or unqualified IPv6 is not selectable",
        },
    }

    documents = {
        "network_state.json": {
            **evidence_envelope(
                schema_id="W7TP_8D_ADI_NETWORK_STATE_V1",
                timestamp=timestamp,
                source_node=source_node,
                confidence="HIGH" if route_decision.get("end_to_end_verified") else "MEDIUM",
            ),
            "network_state_field": network_state_field,
        },
        "node_identity_map.json": {
            **evidence_envelope(
                schema_id="W7TP_8D_ADI_NODE_IDENTITY_MAP_V1",
                timestamp=timestamp,
                source_node=source_node,
            ),
            **identities,
        },
        "path_matrix.json": {
            **evidence_envelope(
                schema_id="W7TP_8D_ADI_PATH_MATRIX_V1",
                timestamp=timestamp,
                source_node=source_node,
            ),
            "paths": paths,
            "default_application_probe": default_application,
            "learning_candidate": learning_candidate,
            "score_is_authority": False,
        },
        "service_binding_matrix.json": {
            **evidence_envelope(
                schema_id="W7TP_8D_ADI_SERVICE_BINDING_MATRIX_V1",
                timestamp=timestamp,
                source_node=source_node,
            ),
            **service_matrix,
        },
        "route_decision.json": {
            **evidence_envelope(
                schema_id="W7TP_8D_ADI_ROUTE_DECISION_V1",
                timestamp=timestamp,
                source_node=source_node,
                confidence="HIGH" if route_decision.get("end_to_end_verified") else "MEDIUM",
                authority_scope="CANDIDATE_D8_DECISION_ONLY",
            ),
            **route_decision,
        },
        "network_risks.json": {
            **evidence_envelope(
                schema_id="W7TP_8D_ADI_NETWORK_RISKS_V1",
                timestamp=timestamp,
                source_node=source_node,
            ),
            "risks": risks,
            "route_drift_findings": route_findings,
            "dns_drift_findings": dns_risks,
            "healing_plan": healing_plan,
            "no_finding_means_no_bounded_evidence_not_global_absence": True,
        },
        "merlin_observation.json": {
            **evidence_envelope(
                schema_id="W7TP_8D_ADI_MERLIN_OBSERVATION_V1",
                timestamp=timestamp,
                source_node=source_node,
                confidence="HIGH" if merlin.get("reachable") else "LOW",
            ),
            "observation": merlin,
            "redacted_inventory_projection": to_redacted_inventory(merlin),
            "router_role": "EDGE_NETWORK_OBSERVER_AND_POLICY_EXECUTION_POINT_CANDIDATE",
            "router_is_d8_authority": False,
        },
    }
    written = write_bundle(
        Path(args.output_dir),
        documents,
        timestamp=timestamp,
        source_node=source_node,
        supersede_existing=args.supersede_existing,
    )
    return {
        "state": "PASS_CANDIDATE_EVIDENCE_CREATED",
        "source_node": source_node,
        "decision": route_decision["decision"],
        "selected_path": route_decision.get("selected_path"),
        "ipv6_qualified": next(
            (path.get("qualified") for path in paths if path.get("path_type") == "NATIVE_IPV6"),
            False,
        ),
        "merlin_state": merlin.get("state"),
        "risk_count": len(risks),
        "written": written,
        "network_mutation": False,
        "router_mutation": False,
        "service_restart": False,
        "total_field_decision": "NOT_RUN",
    }


def _build_paths(
    local: dict[str, Any], merlin: dict[str, Any], args: argparse.Namespace
) -> tuple[list[dict[str, Any]], dict[str, bool], dict[str, Any]]:
    default_v4 = next(
        (route for route in local.get("routes_v4", []) if route.get("dst") == "default"), {}
    )
    gateway = default_v4.get("gateway", "")
    interface = default_v4.get("dev", "")
    lan_ssh = ssh_handshake(gateway) if gateway else {"passed": False}
    lan_http = http_probe(f"http://{gateway}/", family=4) if gateway else {"passed": False}
    https_port = int(merlin.get("nvram", {}).get("https_lanport") or 8443)
    lan_https = (
        http_probe(f"https://{gateway}:{https_port}/", family=4)
        if gateway
        else {"passed": False}
    )
    lan_service = bool(merlin.get("reachable") and lan_ssh.get("passed"))
    lan = score_path(
        {
            "path_type": "LAN_IPV4",
            "interface": interface or "LOCALIZED_UNKNOWN",
            "target": gateway or "LOCALIZED_UNKNOWN",
            "available": bool(gateway and merlin.get("reachable")),
            "host_reachable": bool(merlin.get("reachable")),
            "service_reachable": lan_service,
            "qualified": True,
            "identity_state": "OBSERVED_PARTIAL",
            "remote_agent_online": "NOT_REQUIRED",
            "evidence": {"ssh_handshake": lan_ssh, "http": lan_http, "https": lan_https},
            "score_components": {
                "availability": 1.0 if merlin.get("reachable") else 0.0,
                "latency": 0.95,
                "packet_loss": 1.0,
                "locality": 1.0,
                "cost": 1.0,
                "privacy": 0.9,
                "route_stability": 0.9,
                "observability": 1.0,
            },
        }
    )

    router_ts4 = merlin.get("tailscale_ipv4", "")
    router_ts_name = merlin.get("hostname", "rt-be86u-7428")
    ts_ping = tailscale_ping(router_ts_name) if router_ts_name else {"passed": False}
    ts_tcp = tcp_connect(router_ts4, 22, socket.AF_INET) if router_ts4 else {"passed": False}
    ts_ssh = ssh_handshake(router_ts4, family=socket.AF_INET) if router_ts4 else {"passed": False}
    tailscale_v4 = score_path(
        {
            "path_type": "TAILSCALE_IPV4",
            "interface": "tailscale0",
            "target": router_ts4 or "LOCALIZED_UNKNOWN",
            "available": bool(ts_ping.get("passed")),
            "host_reachable": bool(ts_ping.get("passed")),
            "service_reachable": bool(ts_tcp.get("passed") and ts_ssh.get("passed")),
            "qualified": True,
            "identity_state": "OBSERVED_PARTIAL",
            "remote_agent_online": merlin.get("reachable", False),
            "evidence": {"tailscale_ping": ts_ping, "tcp": ts_tcp, "ssh_handshake": ts_ssh},
            "score_components": {
                "availability": 1.0 if ts_ping.get("passed") else 0.0,
                "latency": 0.8,
                "packet_loss": 0.9,
                "locality": 0.65,
                "cost": 0.9,
                "privacy": 0.95,
                "route_stability": 0.8,
                "observability": 0.9,
            },
        }
    )

    if args.probe_external_ipv6:
        ipv6_probe = ipv6_qualification_probe(
            local,
            args.ipv6_host,
            args.ipv6_port,
            f"https://{args.ipv6_host}/",
        )
    else:
        ipv6_probe = {
            "qualified": False,
            "gates": {},
            "evidence": {},
            "probe_state": "NOT_RUN",
        }
    ipv6_qualification = qualify_ipv6(ipv6_probe.get("gates", {}))
    native_ipv6 = score_path(
        {
            "path_type": "NATIVE_IPV6",
            "interface": _native_ipv6_interface(local),
            "target": ipv6_probe.get("target_ipv6", "LOCALIZED_UNKNOWN"),
            "available": bool(
                ipv6_qualification["gates"]["ADDRESS_PRESENT"]
                and ipv6_qualification["gates"]["DEFAULT_ROUTE_PRESENT"]
            ),
            "host_reachable": ipv6_qualification["gates"]["TARGET_REACHABLE"],
            "service_reachable": ipv6_qualification["gates"]["TCP_SERVICE_REACHABLE"],
            "qualified": ipv6_qualification["qualified"],
            "qualification": ipv6_qualification,
            "identity_state": "OBSERVED_PARTIAL",
            "evidence": ipv6_probe.get("evidence", {}),
            "score_components": {
                "availability": 1.0 if ipv6_qualification["qualified"] else 0.0,
                "latency": 0.75,
                "packet_loss": 0.9,
                "locality": 0.2,
                "cost": 0.8,
                "privacy": 0.55,
                "route_stability": 0.6,
                "observability": 0.8,
            },
        }
    )

    tailscale_v6 = score_path(
        {
            "path_type": "TAILSCALE_IPV6",
            "interface": "tailscale0",
            "target": merlin.get("tailscale_ipv6", "LOCALIZED_UNKNOWN"),
            "available": bool(merlin.get("tailscale_ipv6")),
            "host_reachable": False,
            "service_reachable": False,
            "qualified": False,
            "qualification": qualify_ipv6({}),
            "identity_state": "OBSERVED_PARTIAL",
            "evidence": {"state": "NOT_EXPLICITLY_QUALIFIED"},
            "score_components": {},
        }
    )
    default_application = (
        http_probe(f"https://{args.ipv6_host}/")
        if args.probe_external_ipv6
        else {"probe": "HTTP_APPLICATION", "passed": False, "state": "NOT_RUN"}
    )
    verification = {
        "source": True,
        "interface": bool(interface),
        "route": bool(gateway),
        "target": bool(merlin.get("reachable")),
        "service": bool(lan_ssh.get("passed")),
        "application": bool(lan_http.get("passed") or lan_https.get("passed")),
        "response": bool(merlin.get("reachable")),
    }
    return [lan, tailscale_v4, native_ipv6, tailscale_v6], verification, default_application


def _local_health_probes(
    local: dict[str, Any], lan_addresses: set[str]
) -> dict[int, dict[str, Any]]:
    lan_ip = sorted(lan_addresses)[0] if lan_addresses else "127.0.0.1"
    self_dns = str(local.get("tailscale", {}).get("Self", {}).get("DNSName", "")).rstrip(".")
    specs: list[tuple[int, str]] = [
        (8082, "http://127.0.0.1:8082/health"),
        (9002, "http://127.0.0.1:9002/health"),
        (8090, "http://127.0.0.1:8090/"),
        (8088, "http://127.0.0.1:8088/"),
        (8069, f"http://{lan_ip}:8069/web/health"),
    ]
    if self_dns:
        specs.extend(
            [
                (8444, f"https://{self_dns}:8444/"),
                (8443, f"https://{self_dns}:8443/"),
            ]
        )
    return {port: http_probe(url) for port, url in specs}


def _tailscale_dns_findings(local: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    tailscale = local.get("tailscale", {})
    peers = tailscale.get("Peer", {})
    values = peers.values() if isinstance(peers, dict) else (peers if isinstance(peers, list) else [])
    for peer in values:
        dns_name = str(peer.get("DNSName", "")).rstrip(".")
        status_ips = list(peer.get("TailscaleIPs", []) or [])
        if not dns_name or not status_ips:
            continue
        resolved = dns_resolution(dns_name)
        if resolved.get("passed"):
            findings.extend(
                detect_stale_tailscale_ip(resolved.get("addresses", []), status_ips, dns_name)
            )
    return findings


def _local_address_sets(local: dict[str, Any]) -> tuple[set[str], set[str]]:
    lan: set[str] = set()
    tailscale: set[str] = set()
    for interface in local.get("addresses", []):
        name = interface.get("ifname", "")
        for entry in interface.get("addr_info", []):
            address = entry.get("local")
            if not address:
                continue
            if name == "tailscale0":
                tailscale.add(address)
            elif entry.get("family") == "inet" and not address.startswith(("127.", "172.")):
                lan.add(address)
    return lan, tailscale


def _native_ipv6_interface(local: dict[str, Any]) -> str:
    for route in local.get("routes_v6", []):
        if route.get("dst") == "default":
            return route.get("dev", "LOCALIZED_UNKNOWN")
    return "LOCALIZED_UNKNOWN"


def _reconstruction_states(
    *,
    merlin: dict[str, Any],
    local: dict[str, Any],
    bindings: list[dict[str, Any]],
    paths: list[dict[str, Any]],
) -> list[str]:
    states = ["HOST_ONLINE"]
    states.append("MERLIN_LAN_PASS" if merlin.get("reachable") else "MERLIN_STATE_LOCALIZED_UNKNOWN")
    for path in paths:
        if path["path_type"] == "TAILSCALE_IPV4":
            states.append("TAILSCALE_PASS" if path.get("host_reachable") else "TAILSCALE_FAIL")
        if path["path_type"] == "NATIVE_IPV6":
            states.append("NATIVE_IPV6_QUALIFIED" if path.get("qualified") else "NATIVE_IPV6_UNQUALIFIED")
    if any(binding.get("loopback") for binding in bindings):
        states.append("SERVICE_LOCALHOST_ONLY_PRESENT")
    if local.get("docker_containers"):
        states.append("CONTAINER_NETWORK_PRESENT")
    return sorted(set(states))


def _parse_role_hints(values: list[str]) -> dict[str, str]:
    hints: dict[str, str] = {}
    for value in values:
        key, separator, role = value.partition("=")
        if separator and key and role:
            hints[key.strip()] = role.strip()
    return hints


def _no_router_observation() -> dict[str, Any]:
    return {
        "state": "LOCALIZED_UNKNOWN",
        "reachable": False,
        "router_modified": False,
        "reason": "router_alias_not_supplied",
        "nvram": {},
    }


def _dedupe_risks(risks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in risks:
        key = (item["risk_id"], item["scope"])
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _load_historical_path_matrices(output_dir: Path) -> list[dict[str, Any]]:
    candidates = [output_dir / "path_matrix.json"]
    history = output_dir / "history"
    if history.is_dir():
        candidates.extend(sorted(history.glob("*/path_matrix.json"))[-63:])
    matrices: list[dict[str, Any]] = []
    seen_timestamps: set[str] = set()
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        timestamp = str(data.get("timestamp", path))
        if timestamp in seen_timestamps:
            continue
        seen_timestamps.add(timestamp)
        matrices.append({"timestamp": timestamp, "paths": data.get("paths", [])})
    return matrices


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="W7TP 8D ADI adaptive network candidate")
    subparsers = parser.add_subparsers(dest="command", required=True)
    discover_parser = subparsers.add_parser("discover", help="run read-only discovery")
    discover_parser.add_argument("--output-dir", default="runtime/network")
    discover_parser.add_argument("--router-alias", default=None)
    discover_parser.add_argument("--intent-id", default="NETWORK_READ_ONLY_DISCOVERY")
    discover_parser.add_argument("--ipv6-host", default="example.com")
    discover_parser.add_argument("--ipv6-port", type=int, default=443)
    discover_parser.add_argument("--probe-external-ipv6", action="store_true")
    discover_parser.add_argument("--role-hint", action="append", default=[])
    discover_parser.add_argument(
        "--supersede-existing",
        action="store_true",
        help="archive a complete hash-valid prior candidate bundle before replacing current candidate files",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "discover":
        raise AssertionError("unreachable")
    try:
        result = discover(args)
    except (FileExistsError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "state": "HOLD_CANDIDATE_EVIDENCE_WRITE",
                    "error": str(exc),
                    "network_mutation": False,
                    "router_mutation": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
