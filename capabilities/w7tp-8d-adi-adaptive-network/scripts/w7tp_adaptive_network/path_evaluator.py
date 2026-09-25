from __future__ import annotations

from typing import Any


IPV6_GATES = (
    "ADDRESS_PRESENT",
    "DEFAULT_ROUTE_PRESENT",
    "SOURCE_SELECTION_VALID",
    "NEXT_HOP_REACHABLE",
    "TARGET_REACHABLE",
    "TCP_SERVICE_REACHABLE",
    "RETURN_PATH_VALID",
    "APPLICATION_PASS",
)


def qualify_ipv6(gates: dict[str, bool]) -> dict[str, Any]:
    normalized = {gate: bool(gates.get(gate, False)) for gate in IPV6_GATES}
    missing = [gate for gate, passed in normalized.items() if not passed]
    return {
        "gates": normalized,
        "qualified": not missing,
        "missing_gates": missing,
        "selectable": not missing,
        "rule": "UNQUALIFIED_IPV6_NOT_SELECTABLE",
    }


def score_path(path: dict[str, Any]) -> dict[str, Any]:
    """Compute a candidate score that never grants route authority."""

    weights = {
        "availability": 28.0,
        "latency": 12.0,
        "packet_loss": 10.0,
        "locality": 18.0,
        "cost": 8.0,
        "privacy": 10.0,
        "route_stability": 8.0,
        "observability": 6.0,
    }
    components = path.get("score_components", {})
    total = 0.0
    normalized: dict[str, float] = {}
    for key, weight in weights.items():
        value = float(components.get(key, 0.0))
        value = min(1.0, max(0.0, value))
        normalized[key] = value
        total += value * weight
    return {
        **path,
        "score_components": normalized,
        "candidate_score": round(total, 3),
        "score_is_authority": False,
    }


def classify_path(address: str, interface: str = "") -> str:
    if address.startswith("127.") or address == "::1":
        return "LOOPBACK"
    if interface == "tailscale0" or address.startswith("100.") or address.startswith("fd7a:115c:a1e0:"):
        return "TAILSCALE"
    if interface.startswith(("docker", "br-", "veth")) or address.startswith("172."):
        return "CONTAINER"
    if address.startswith("192.168.") or address.startswith("10."):
        return "LOCAL_LAN"
    if ":" in address:
        return "NATIVE_IPV6"
    if address:
        return "NATIVE_IPV4"
    return "UNKNOWN"

