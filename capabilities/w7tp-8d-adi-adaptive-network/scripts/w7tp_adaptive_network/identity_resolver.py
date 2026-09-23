from __future__ import annotations

import hashlib
import ipaddress
from collections import defaultdict
from typing import Any


def _stable_candidate_id(*parts: str) -> str:
    material = "|".join(part for part in parts if part and part != "LOCALIZED_UNKNOWN")
    if not material:
        return "LOCALIZED_UNKNOWN"
    return f"candidate-node:{hashlib.sha256(material.encode('utf-8')).hexdigest()[:20]}"


def _address_sets(addresses: list[dict[str, Any]]) -> dict[str, list[str]]:
    result = {
        "lan_ipv4": [],
        "tailscale_ipv4": [],
        "tailscale_ipv6": [],
        "native_ipv6": [],
        "container": [],
    }
    for interface in addresses:
        name = interface.get("ifname", "")
        for entry in interface.get("addr_info", []):
            local = entry.get("local")
            if not local:
                continue
            try:
                ip = ipaddress.ip_address(local)
            except ValueError:
                continue
            if name == "tailscale0":
                result["tailscale_ipv6" if ip.version == 6 else "tailscale_ipv4"].append(local)
            elif name.startswith(("docker", "br-", "veth")):
                result["container"].append(local)
            elif ip.version == 4 and ip.is_private and not ip.is_loopback:
                result["lan_ipv4"].append(local)
            elif ip.version == 6 and not (ip.is_loopback or ip.is_link_local):
                result["native_ipv6"].append(local)
    return result


def _primary_mac(links: list[dict[str, Any]], addresses: dict[str, list[str]]) -> str:
    lan_interfaces: set[str] = set()
    for link in links:
        if link.get("ifname") == "lo" or link.get("ifname", "").startswith(
            ("tailscale", "docker", "br-", "veth")
        ):
            continue
        if link.get("address"):
            lan_interfaces.add(link["ifname"])
    for link in links:
        if link.get("ifname") in lan_interfaces:
            return link.get("address", "LOCALIZED_UNKNOWN")
    return "LOCALIZED_UNKNOWN"


def _peer_list(tailscale: dict[str, Any]) -> list[dict[str, Any]]:
    peers = tailscale.get("Peer", {})
    if isinstance(peers, dict):
        return [value for value in peers.values() if isinstance(value, dict)]
    if isinstance(peers, list):
        return [value for value in peers if isinstance(value, dict)]
    return []


def resolve_identities(
    local: dict[str, Any],
    merlin: dict[str, Any] | None = None,
    role_hints: dict[str, str] | None = None,
) -> dict[str, Any]:
    role_hints = {key.lower(): value for key, value in (role_hints or {}).items()}
    merlin = merlin or {}
    local_addresses = _address_sets(local.get("addresses", []))
    self_ts = local.get("tailscale", {}).get("Self", {}) or {}
    local_hostname = local.get("hostname", "LOCALIZED_UNKNOWN")
    local_node = {
        "node_id": _stable_candidate_id(
            local_hostname,
            local.get("machine_id", ""),
            self_ts.get("DNSName", ""),
        ),
        "hostname": local_hostname,
        "machine_id": local.get("machine_id", "LOCALIZED_UNKNOWN"),
        "tailscale_identity": self_ts.get("DNSName", "LOCALIZED_UNKNOWN"),
        "MAC": _primary_mac(local.get("links", []), local_addresses),
        "LAN_IP": local_addresses["lan_ipv4"],
        "TAILSCALE_IPV4": local_addresses["tailscale_ipv4"],
        "TAILSCALE_IPV6": local_addresses["tailscale_ipv6"],
        "NATIVE_IPV6": local_addresses["native_ipv6"],
        "service_identity": [],
        "role": role_hints.get(local_hostname.lower(), "UNVERIFIED_ROLE"),
        "owner": "UNKNOWN",
        "identity_state": "OBSERVED_PARTIAL",
        "evidence_basis": ["LOCAL_MACHINE_ID_HASH", "LOCAL_LINKS", "TAILSCALE_SELF"],
    }

    leases_by_name: dict[str, list[str]] = defaultdict(list)
    for lease in merlin.get("leases", []):
        name = str(lease.get("hostname", "")).strip().lower()
        address = str(lease.get("lan_ip", "")).strip()
        if name and name != "*" and address:
            leases_by_name[name].append(address)

    neighbors_by_ip: dict[str, str] = {}
    for neighbor in local.get("neighbors", []):
        destination = str(neighbor.get("dst", ""))
        lladdr = str(neighbor.get("lladdr", ""))
        if destination and lladdr:
            neighbors_by_ip[destination] = lladdr

    remote_nodes: list[dict[str, Any]] = []
    hostname_groups: dict[str, list[int]] = defaultdict(list)
    matched_lease_names: set[str] = set()
    for peer in _peer_list(local.get("tailscale", {})):
        dns_name = str(peer.get("DNSName", "")).rstrip(".")
        dns_label = dns_name.split(".", 1)[0].lower() if dns_name else ""
        hostname = str(peer.get("HostName", "LOCALIZED_UNKNOWN"))
        lookup_names = [dns_label, hostname.lower()]
        lan_ips: list[str] = []
        for name in lookup_names:
            matched = leases_by_name.get(name, [])
            if matched:
                matched_lease_names.add(name)
                lan_ips.extend(matched)
        lan_ips = sorted(set(lan_ips))
        macs = sorted({neighbors_by_ip[ip] for ip in lan_ips if ip in neighbors_by_ip})
        ips = peer.get("TailscaleIPs", []) or []
        node = {
            "node_id": _stable_candidate_id(dns_name, hostname, str(peer.get("NodeKey", ""))),
            "hostname": hostname,
            "machine_id": "UNKNOWN",
            "tailscale_identity": dns_name or "LOCALIZED_UNKNOWN",
            "MAC": macs or ["UNKNOWN"],
            "LAN_IP": lan_ips or ["UNKNOWN"],
            "TAILSCALE_IPV4": [ip for ip in ips if ":" not in ip],
            "TAILSCALE_IPV6": [ip for ip in ips if ":" in ip],
            "NATIVE_IPV6": ["UNKNOWN"],
            "service_identity": [],
            "role": role_hints.get(dns_label, role_hints.get(hostname.lower(), "UNVERIFIED_ROLE")),
            "owner": "UNKNOWN",
            "identity_state": "OBSERVED_PARTIAL",
            "online": peer.get("Online", False),
            "active": peer.get("Active", False),
            "os": peer.get("OS", "UNKNOWN"),
            "last_seen": peer.get("LastSeen", "UNKNOWN"),
            "evidence_basis": ["TAILSCALE_PEER", "MERLIN_DHCP_LEASE_IF_MATCHED", "LOCAL_NEIGHBOR_IF_MATCHED"],
        }
        hostname_groups[hostname.lower()].append(len(remote_nodes))
        remote_nodes.append(node)

    for hostname, lan_ips in sorted(leases_by_name.items()):
        if hostname in matched_lease_names:
            continue
        unique_ips = sorted(set(lan_ips))
        macs = sorted({neighbors_by_ip[ip] for ip in unique_ips if ip in neighbors_by_ip})
        hostname_groups[hostname].append(len(remote_nodes))
        remote_nodes.append(
            {
                "node_id": _stable_candidate_id(hostname, *(macs or [])),
                "hostname": hostname,
                "machine_id": "UNKNOWN",
                "tailscale_identity": "UNKNOWN",
                "MAC": macs or ["UNKNOWN"],
                "LAN_IP": unique_ips,
                "TAILSCALE_IPV4": ["UNKNOWN"],
                "TAILSCALE_IPV6": ["UNKNOWN"],
                "NATIVE_IPV6": ["UNKNOWN"],
                "service_identity": [],
                "role": role_hints.get(hostname, "UNVERIFIED_ROLE"),
                "owner": "UNKNOWN",
                "identity_state": "OBSERVED_PARTIAL",
                "online": "UNKNOWN",
                "active": "UNKNOWN",
                "os": "UNKNOWN",
                "last_seen": "UNKNOWN",
                "evidence_basis": ["MERLIN_DHCP_LEASE", "LOCAL_NEIGHBOR_IF_MATCHED"],
            }
        )

    conflicts: list[dict[str, Any]] = []
    for hostname, indexes in hostname_groups.items():
        identities = {
            remote_nodes[index]["tailscale_identity"]
            for index in indexes
            if remote_nodes[index]["tailscale_identity"] != "LOCALIZED_UNKNOWN"
        }
        if len(identities) <= 1:
            continue
        conflict = {
            "conflict_id": f"duplicate-hostname:{hostname}",
            "hostname": hostname,
            "tailscale_identities": sorted(identities),
            "state": "CONFLICT",
            "reason": "one hostname maps to multiple Tailscale identities; do not select by hostname alone",
        }
        conflicts.append(conflict)
        for index in indexes:
            remote_nodes[index]["identity_state"] = "CONFLICT"
            remote_nodes[index]["LAN_IP"] = ["UNKNOWN_DUE_TO_IDENTITY_CONFLICT"]
            remote_nodes[index]["MAC"] = ["UNKNOWN_DUE_TO_IDENTITY_CONFLICT"]

    return {
        "identity_semantics": "IP_IS_COORDINATE_NOT_PERMANENT_IDENTITY",
        "nodes": [local_node, *remote_nodes],
        "conflicts": conflicts,
        "unresolved_fields_fail_closed": True,
    }
