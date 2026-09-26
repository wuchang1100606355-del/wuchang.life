from __future__ import annotations

import ipaddress
import re
from collections import defaultdict
from typing import Any


def risk(
    risk_id: str,
    scope: str,
    evidence: list[str],
    impact: str,
    confidence: str,
    safe_action_candidate: str,
    rollback: str,
) -> dict[str, Any]:
    return {
        "risk_id": risk_id,
        "scope": scope,
        "evidence": evidence,
        "impact": impact,
        "confidence": confidence,
        "safe_action_candidate": safe_action_candidate,
        "rollback": rollback,
        "authority": "CANDIDATE_RISK_ONLY",
    }


def detect_stale_tailscale_ip(dns_ips: list[str], status_ips: list[str], node: str) -> list[dict[str, Any]]:
    dns_v4 = {value for value in dns_ips if ":" not in value}
    dns_v6 = {value for value in dns_ips if ":" in value}
    status_v4 = {value for value in status_ips if ":" not in value}
    status_v6 = {value for value in status_ips if ":" in value}
    mismatches: list[str] = []
    if dns_v4 and dns_v4 != status_v4:
        mismatches.append(f"ipv4:dns={sorted(dns_v4)} status={sorted(status_v4)}")
    if dns_v6 and dns_v6 != status_v6:
        mismatches.append(f"ipv6:dns={sorted(dns_v6)} status={sorted(status_v6)}")
    if not mismatches:
        return []
    return [
        risk(
            "STALE_TAILSCALE_IP",
            node,
            mismatches,
            "name resolution may target a stale peer coordinate",
            "HIGH",
            "refresh DNS and peer observations, then re-probe without changing routes",
            "discard refreshed candidate evidence and retain the prior observation",
        )
    ]


def detect_service_localhost_only(binding: dict[str, Any], intended_scope: str) -> list[dict[str, Any]]:
    if not binding.get("loopback") or intended_scope not in {"LAN", "TAILSCALE", "REMOTE"}:
        return []
    return [
        risk(
            "SERVICE_BIND_DRIFT",
            f"{binding.get('service', 'UNKNOWN')}:{binding.get('port', 'UNKNOWN')}",
            [f"bind={binding.get('bind_address')}", f"intended_scope={intended_scope}"],
            "host can be online while the intended remote service remains unreachable",
            "HIGH",
            "verify the service binding contract and create a non-active binding change candidate",
            "retain the current binding and abandon the candidate",
        )
    ]


def detect_container_binding(
    *, container_reachable: bool, host_binding_present: bool, service: str
) -> list[dict[str, Any]]:
    if not container_reachable or host_binding_present:
        return []
    return [
        risk(
            "CONTAINER_NETWORK_DRIFT",
            service,
            ["container_internal_reachable=true", "host_binding_present=false"],
            "container health can be mistaken for host or LAN service availability",
            "HIGH",
            "inspect the declared publication contract; do not add a host bind automatically",
            "no live change was made; discard the publication candidate",
        )
    ]


def detect_router_internet(router_reachable: bool, internet_reachable: bool) -> list[dict[str, Any]]:
    if not router_reachable or internet_reachable:
        return []
    return [
        risk(
            "ROUTE_DRIFT",
            "MERLIN_WAN_PATH",
            ["router_reachable=true", "internet_reachable=false"],
            "local gateway availability can be mistaken for Internet availability",
            "HIGH",
            "re-probe WAN route, DNS, TCP, and application response read-only",
            "retain the previous candidate path and make no router change",
        )
    ]


def detect_wan_publication_drift(
    *,
    port_forwarding_enabled: bool,
    forwarding_rule_count: int,
    application_verified: bool,
) -> list[dict[str, Any]]:
    if not port_forwarding_enabled or forwarding_rule_count <= 0 or application_verified:
        return []
    return [
        risk(
            "WAN_PUBLICATION_DRIFT",
            "MERLIN_WAN_PUBLICATION_PATH",
            [
                "port_forwarding_enabled=true",
                f"forwarding_rule_count={forwarding_rule_count}",
                "application_verified=false",
            ],
            "WAN publication rules exist without an intent-bound end-to-end application decision",
            "HIGH",
            "keep each publication binding on HOLD until the explicit service, target zone, TLS, response, and rollback are verified",
            "make no router change; preserve the observed rules and disconnect the WAN carrier if immediate containment is required",
        )
    ]


def detect_asymmetric_route(forward_interface: str, return_interface: str) -> list[dict[str, Any]]:
    if not forward_interface or not return_interface or forward_interface == return_interface:
        return []
    return [
        risk(
            "ASYMMETRIC_ROUTE",
            "END_TO_END_PATH",
            [f"forward_interface={forward_interface}", f"return_interface={return_interface}"],
            "return traffic may bypass the selected policy and fail stateful validation",
            "HIGH",
            "hold selection and collect source and target route lookups",
            "return to the last symmetric candidate path",
        )
    ]


def detect_secondary_double_nat(routes_v4: list[str], wan_scope: str) -> list[dict[str, Any]]:
    private_defaults: list[str] = []
    for route in routes_v4:
        match = re.match(r"^default via (\S+) dev (\S+)(?:\s|$)", route)
        if not match:
            continue
        try:
            gateway = ipaddress.ip_address(match.group(1))
        except ValueError:
            continue
        if gateway.is_private:
            private_defaults.append(route)
    if not private_defaults:
        return []
    return [
        risk(
            "DOUBLE_NAT",
            "MERLIN_SECONDARY_IPV4_UPLINK",
            [f"wan_scope={wan_scope}", *private_defaults],
            "traffic using the private secondary default may traverse an additional NAT boundary",
            "MEDIUM",
            "confirm the active route table and failover intent before selecting the secondary uplink",
            "keep the current primary path and make no route change",
        )
    ]


def detect_port_collisions(bindings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int], set[str]] = defaultdict(set)
    for binding in bindings:
        key = (
            str(binding.get("transport", "")),
            str(binding.get("bind_address", "")),
            int(binding.get("port", 0)),
        )
        grouped[key].add(str(binding.get("service", "UNKNOWN")))
    findings: list[dict[str, Any]] = []
    for (transport, address, port), services in grouped.items():
        if port and len(services) > 1:
            findings.append(
                risk(
                    "PORT_COLLISION",
                    f"{transport}:{address}:{port}",
                    [f"services={sorted(services)}"],
                    "multiple service owners claim the same socket coordinate",
                    "HIGH",
                    "identify the actual socket owner and expected service before any restart",
                    "make no live change and preserve both ownership observations",
                )
            )
    return findings


def detect_risks(context: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for conflict in context.get("identity_conflicts", []):
        findings.append(
            risk(
                "NODE_IDENTITY_DRIFT",
                conflict.get("hostname", "UNKNOWN"),
                [str(conflict.get("tailscale_identities", []))],
                "path selection could bind the wrong physical or virtual node",
                "HIGH",
                "require machine or service identity evidence before selecting that node",
                "retain all conflicting identities without rebinding",
            )
        )

    findings.extend(detect_port_collisions(context.get("bindings", [])))
    for binding in context.get("bindings", []):
        if binding.get("wildcard") and binding.get("port") in {5432, 15432, 3306, 6379, 27017}:
            findings.append(
                risk(
                    "SERVICE_BIND_DRIFT",
                    f"{binding.get('service')}:{binding.get('port')}",
                    [f"bind={binding.get('bind_address')}", "sensitive_service_wildcard=true"],
                    "a data service may be reachable from more network fields than intended",
                    "MEDIUM",
                    "compare the live bind with the service authority contract; propose only a bounded candidate",
                    "keep the existing bind unchanged",
                )
            )
        if binding.get("container_service") and binding.get("wildcard") and binding.get("IPv6"):
            findings.append(
                risk(
                    "CONTAINER_NETWORK_DRIFT",
                    f"{binding.get('service')}:{binding.get('port')}",
                    [f"host_bind={binding.get('bind_address')}", "container_service=true"],
                    "a container service is published on the host IPv6 wildcard and may exceed its intended field",
                    "MEDIUM",
                    "compare the container publication with the service binding contract",
                    "keep the current publication unchanged",
                )
            )

    identity_nodes = context.get("identity_nodes", [])
    msi_nodes = [
        node for node in identity_nodes if str(node.get("hostname", "")).lower() == "msi"
    ]
    msi_operating_systems = {str(node.get("os", "UNKNOWN")).lower() for node in msi_nodes}
    msi_online_states = {str(node.get("online", "UNKNOWN")).lower() for node in msi_nodes}
    if {"linux", "windows"}.issubset(msi_operating_systems) and len(msi_online_states) > 1:
        findings.append(
            risk(
                "WSL_NETWORK_DRIFT",
                "MSI_WINDOWS_WSL_IDENTITY_BOUNDARY",
                [
                    f"operating_systems={sorted(msi_operating_systems)}",
                    f"online_states={sorted(msi_online_states)}",
                ],
                "Windows agent state can be mistaken for WSL host and service state, or vice versa",
                "HIGH",
                "bind Windows and WSL service identities separately before path selection",
                "preserve both identities and do not rebind either address",
            )
        )

    if context.get("default_application_family") == "IPV6" and not context.get(
        "generic_ipv6_policy_gate_present", False
    ):
        findings.append(
            risk(
                "IPV6_DRIFT",
                "APPLICATION_DEFAULT_ROUTE_SELECTION",
                ["default_application_family=IPV6", "generic_ipv6_policy_gate_present=false"],
                "an application can select IPv6 before W7TP performs target-specific qualification",
                "HIGH",
                "route each governed request through target-specific IPv6 qualification",
                "fall back to the last verified LAN or Tailscale IPv4 candidate",
            )
        )

    if context.get("router_tailscale_interface_present") and not context.get(
        "router_tailscale_cli_observed", False
    ):
        findings.append(
            risk(
                "TUNNEL_DRIFT",
                "MERLIN_TAILSCALE_OBSERVABILITY",
                ["tailscale_interface_present=true", "tailscale_cli_observed=false"],
                "tunnel data plane and management observation may diverge",
                "MEDIUM",
                "recheck the fixed /opt/bin/tailscale coordinate read-only",
                "retain interface and peer evidence separately",
            )
        )
    findings.extend(
        detect_secondary_double_nat(
            context.get("router_routes_v4", []),
            context.get("router_wan_scope", "LOCALIZED_UNKNOWN"),
        )
    )
    findings.extend(
        detect_wan_publication_drift(
            port_forwarding_enabled=context.get("port_forwarding_enabled", False),
            forwarding_rule_count=int(context.get("forwarding_rule_count", 0)),
            application_verified=context.get("wan_publication_application_verified", False),
        )
    )
    return _deduplicate(findings)


def _deduplicate(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for finding in findings:
        key = (finding["risk_id"], finding["scope"])
        if key not in seen:
            seen.add(key)
            output.append(finding)
    return output
