from __future__ import annotations

from typing import Any


LOW_RISK_ACTIONS = {
    "refresh_observation",
    "refresh_dns_state",
    "refresh_peer_state",
    "reprobe_alternate_path",
    "switch_application_candidate_path",
    "restart_skill_local_observer",
}

FORBIDDEN_ACTIONS = {
    "restart_host",
    "restart_router",
    "change_wan",
    "flush_firewall",
    "disable_ipv6_globally",
    "change_dhcp_globally",
    "delete_routes",
    "reset_tailscale",
    "nvram_set",
    "nvram_commit",
}


def guard_action(action: str, preimage_ref: str | None = None) -> dict[str, Any]:
    if action in FORBIDDEN_ACTIONS:
        return {
            "decision": "DENY",
            "action": action,
            "reason": "FIRST_ROUND_FORBIDDEN_NETWORK_EFFECT",
            "rollback": "NOT_APPLICABLE_NO_EFFECT_ALLOWED",
        }
    if action not in LOW_RISK_ACTIONS:
        return {
            "decision": "HOLD",
            "action": action,
            "reason": "ACTION_NOT_IN_SKILL_LOCAL_ALLOWLIST",
            "rollback": "NOT_PROVEN",
        }
    if action in {"switch_application_candidate_path", "restart_skill_local_observer"} and not preimage_ref:
        return {
            "decision": "HOLD",
            "action": action,
            "reason": "ROLLBACK_PREIMAGE_REQUIRED",
            "rollback": "NOT_PROVEN",
        }
    return {
        "decision": "ALLOW_CANDIDATE_ONLY",
        "action": action,
        "reason": "LOW_RISK_SKILL_LOCAL_ACTION",
        "rollback": f"restore_or_reselect:{preimage_ref}" if preimage_ref else "discard_refreshed_evidence",
        "network_mutation": False,
        "authority_scope": "CANDIDATE_ONLY",
    }

