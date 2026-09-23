from __future__ import annotations

import ipaddress
import re
from collections import defaultdict
from typing import Any


_BRACKET_ENDPOINT = re.compile(r"^\[(.*)]:(\d+)$")
_PROCESS = re.compile(r'users:\(\(\"([^\"]+)\"')
_PUBLISHED_PORT = re.compile(r"(?:^|, )(?:(?:\[[^]]+]\)|[^:, ]+):)?(\d+)->\d+/(?:tcp|udp)")


def parse_listeners(
    raw: str,
    lan_addresses: set[str] | None = None,
    tailscale_addresses: set[str] | None = None,
    health_by_port: dict[int, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    lan_addresses = lan_addresses or set()
    tailscale_addresses = tailscale_addresses or set()
    health_by_port = health_by_port or {}
    listeners: list[dict[str, Any]] = []
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        protocol = parts[0]
        state = parts[1]
        endpoint = parts[4]
        address, port = _split_endpoint(endpoint)
        if port is None:
            continue
        process_match = _PROCESS.search(line)
        process = process_match.group(1) if process_match else "UNKNOWN"
        scope = _scope(address, lan_addresses, tailscale_addresses)
        health = health_by_port.get(port, {})
        listeners.append(
            {
                "service": process,
                "transport": protocol,
                "port": port,
                "bind_address": address,
                "socket_state": state,
                "loopback": scope["loopback"],
                "LAN": scope["LAN"],
                "Tailscale": scope["Tailscale"],
                "IPv6": scope["IPv6"],
                "container": scope["container"],
                "wildcard": scope["wildcard"],
                "health": "PASS" if health.get("passed") else ("FAIL" if health else "NOT_PROBED"),
                "health_probe": health or None,
            }
        )
    return listeners


def binding_summary(listeners: list[dict[str, Any]]) -> dict[str, Any]:
    scopes: dict[str, int] = defaultdict(int)
    for listener in listeners:
        for key in ("loopback", "LAN", "Tailscale", "IPv6", "container", "wildcard"):
            if listener.get(key):
                scopes[key] += 1
    return {
        "listener_count": len(listeners),
        "scope_counts": dict(sorted(scopes.items())),
        "matrix": listeners,
        "interpretation_rule": "HOST_REACHABLE_DOES_NOT_IMPLY_SERVICE_REACHABLE",
    }


def enrich_container_services(
    listeners: list[dict[str, Any]], docker_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_port: dict[int, set[str]] = defaultdict(set)
    for row in docker_rows:
        name = str(row.get("Names", "UNKNOWN"))
        for match in _PUBLISHED_PORT.finditer(str(row.get("Ports", ""))):
            by_port[int(match.group(1))].add(name)
    for listener in listeners:
        names = sorted(by_port.get(int(listener.get("port", 0)), set()))
        if names and listener.get("service") in {"UNKNOWN", "docker-proxy"}:
            listener["service"] = "container:" + ",".join(names)
            listener["container_service"] = True
    return listeners


def _split_endpoint(endpoint: str) -> tuple[str, int | None]:
    bracket = _BRACKET_ENDPOINT.match(endpoint)
    if bracket:
        return bracket.group(1), int(bracket.group(2))
    if ":" not in endpoint:
        return endpoint, None
    address, port_text = endpoint.rsplit(":", 1)
    if not port_text.isdigit():
        return address, None
    return address, int(port_text)


def _scope(address: str, lan: set[str], tailscale: set[str]) -> dict[str, bool]:
    wildcard = address in {"0.0.0.0", "::", "*", ""}
    loopback = address.startswith("127.") or address == "::1"
    container = address.startswith("172.")
    is_ipv6 = ":" in address or address in {"::", "*"}
    lan_match = address in lan
    tailscale_match = address in tailscale
    if wildcard:
        lan_match = True
        tailscale_match = True
    if not wildcard and not loopback:
        try:
            parsed = ipaddress.ip_address(address.split("%", 1)[0])
            if parsed.version == 4 and parsed.is_private and not address.startswith(("100.", "172.")):
                lan_match = lan_match or True
        except ValueError:
            pass
    return {
        "loopback": loopback,
        "LAN": lan_match,
        "Tailscale": tailscale_match,
        "IPv6": is_ipv6,
        "container": container,
        "wildcard": wildcard,
    }
