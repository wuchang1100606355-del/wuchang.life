from __future__ import annotations

from typing import Any


PRIORITY = ("LAN_IPV4", "TAILSCALE_IPV4", "NATIVE_IPV6", "TAILSCALE_IPV6")


def evaluate_policy(intent: dict[str, Any], paths: list[dict[str, Any]]) -> dict[str, Any]:
    by_type = {path.get("path_type"): path for path in paths}
    permitted = set(intent.get("permitted_paths") or PRIORITY)
    identity_state = intent.get("target_identity_state", "OBSERVED_PARTIAL")
    if identity_state == "CONFLICT":
        return _decision("HOLD", None, "TARGET_IDENTITY_CONFLICT")

    for path_type in PRIORITY:
        if path_type not in permitted:
            continue
        path = by_type.get(path_type)
        if not path:
            continue
        if not _base_eligible(path):
            continue
        if path_type in {"NATIVE_IPV6", "TAILSCALE_IPV6"}:
            if not path.get("qualified", False):
                continue
            return _decision(
                "ALLOW_QUALIFIED_IPV6",
                path,
                f"{path_type}_EXPLICITLY_QUALIFIED_AFTER_HIGHER_PRIORITY_PATHS_UNAVAILABLE",
            )
        if path_type == "LAN_IPV4":
            return _decision("ALLOW_LAN_IPV4", path, "LAN_AVAILABLE_AND_SERVICE_VERIFIED")
        return _decision(
            "ALLOW_TAILSCALE_IPV4",
            path,
            "LAN_UNAVAILABLE_AND_TAILSCALE_SERVICE_VERIFIED",
        )

    only_ipv6 = bool(permitted) and permitted.issubset({"NATIVE_IPV6", "TAILSCALE_IPV6"})
    unqualified_ipv6_present = any(
        path.get("path_type") in permitted
        and path.get("available", False)
        and not path.get("qualified", False)
        for path in paths
        if path.get("path_type") in {"NATIVE_IPV6", "TAILSCALE_IPV6"}
    )
    if only_ipv6 and unqualified_ipv6_present:
        return _decision("DENY", None, "UNQUALIFIED_IPV6_NOT_SELECTABLE")

    if not paths:
        return _decision("LOCALIZED_UNKNOWN", None, "NO_CURRENT_PATH_EVIDENCE")
    return _decision("HOLD", None, "NO_VERIFIED_SERVICE_PATH")


def _base_eligible(path: dict[str, Any]) -> bool:
    return bool(
        path.get("available", False)
        and path.get("host_reachable", False)
        and path.get("service_reachable", False)
        and path.get("identity_state", "OBSERVED_PARTIAL") != "CONFLICT"
    )


def _decision(decision: str, path: dict[str, Any] | None, reason: str) -> dict[str, Any]:
    return {
        "decision": decision,
        "selected_path": path.get("path_type") if path else None,
        "selected_interface": path.get("interface") if path else None,
        "selected_target": path.get("target") if path else None,
        "reason": reason,
        "score_used_as_authority": False,
        "total_field_decision": "NOT_RUN",
        "canonical": False,
    }

