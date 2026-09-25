from __future__ import annotations

from typing import Any

from .rollback_guard import guard_action


ACTION_BY_RISK = {
    "DNS_DRIFT": "refresh_dns_state",
    "STALE_DNS": "refresh_dns_state",
    "STALE_TAILSCALE_IP": "refresh_peer_state",
    "TUNNEL_DRIFT": "refresh_peer_state",
    "IPV6_DRIFT": "reprobe_alternate_path",
    "ROUTE_DRIFT": "reprobe_alternate_path",
    "ASYMMETRIC_ROUTE": "reprobe_alternate_path",
}


def plan_low_risk_healing(risks: list[dict[str, Any]]) -> dict[str, Any]:
    plans: list[dict[str, Any]] = []
    seen: set[str] = set()
    for finding in risks:
        action = ACTION_BY_RISK.get(finding.get("risk_id"), "refresh_observation")
        if action in seen:
            continue
        seen.add(action)
        plans.append(
            {
                "risk_ids": sorted(
                    {
                        item.get("risk_id")
                        for item in risks
                        if ACTION_BY_RISK.get(item.get("risk_id"), "refresh_observation") == action
                    }
                ),
                **guard_action(action),
                "execution_performed": False,
            }
        )
    return {
        "state": "PLAN_ONLY_NO_NETWORK_EFFECT",
        "plans": plans,
        "execution_performed": False,
        "router_mutation": False,
        "service_restart": False,
    }

