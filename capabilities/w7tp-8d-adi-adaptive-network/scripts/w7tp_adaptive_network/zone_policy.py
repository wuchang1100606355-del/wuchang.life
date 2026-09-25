from __future__ import annotations

from typing import Any


ALL_PATH_TYPES = {
    "LOOPBACK_SERVICE_PATH",
    "CONTAINER_LOCAL_PATH",
    "LAN_IPV4",
    "TAILSCALE_IPV4",
    "NATIVE_IPV6",
    "TAILSCALE_IPV6",
    "GUEST_SERVICE_PATH",
    "IOT_SERVICE_PATH",
    "WAN_PUBLICATION_PATH",
}

ZONE_PATH_RULES: dict[tuple[str, str], set[str]] = {
    ("ZONE_CORE", "ZONE_CORE"): {
        "LOOPBACK_SERVICE_PATH",
        "CONTAINER_LOCAL_PATH",
        "LAN_IPV4",
        "TAILSCALE_IPV4",
        "NATIVE_IPV6",
        "TAILSCALE_IPV6",
    },
    ("ZONE_MANAGEMENT", "ZONE_MANAGEMENT"): {
        "LAN_IPV4",
        "TAILSCALE_IPV4",
        "TAILSCALE_IPV6",
    },
    ("ZONE_TAILSCALE", "ZONE_MANAGEMENT"): {
        "TAILSCALE_IPV4",
        "TAILSCALE_IPV6",
    },
    ("ZONE_TAILSCALE", "ZONE_CORE"): {
        "TAILSCALE_IPV4",
        "TAILSCALE_IPV6",
    },
    ("ZONE_MANAGEMENT", "ZONE_CORE"): {
        "LAN_IPV4",
        "TAILSCALE_IPV4",
        "TAILSCALE_IPV6",
    },
    ("ZONE_GUEST_SERVICE", "ZONE_GUEST_SERVICE"): {"GUEST_SERVICE_PATH"},
    ("ZONE_IOT", "ZONE_IOT_SERVICE"): {"IOT_SERVICE_PATH"},
    ("ZONE_CORE", "ZONE_IOT_SERVICE"): {"IOT_SERVICE_PATH"},
    ("ZONE_WAN", "ZONE_FUTURE_PUBLIC_SERVICE"): {"WAN_PUBLICATION_PATH"},
}

PUBLIC_DIRECT_DENY_ZONES = {
    "ZONE_CORE",
    "ZONE_MANAGEMENT",
    "ZONE_TAILSCALE",
    "ZONE_GUEST_SERVICE",
    "ZONE_IOT",
    "ZONE_IOT_SERVICE",
    "ZONE_TOTAL_FIELD",
    "ZONE_DATABASE",
}


def evaluate_zone_policy(intent: dict[str, Any]) -> dict[str, Any]:
    source_zone = str(intent.get("source_zone") or "LOCALIZED_UNKNOWN")
    target_zone = str(intent.get("target_zone") or "LOCALIZED_UNKNOWN")

    if source_zone == "ZONE_WAN" and target_zone in PUBLIC_DIRECT_DENY_ZONES:
        return _decision(False, set(), "WAN_DIRECT_TO_PROTECTED_ZONE_DENIED", source_zone, target_zone)

    if source_zone == "ZONE_WAN" and target_zone == "ZONE_FUTURE_PUBLIC_SERVICE":
        if intent.get("service_class") != "PUBLIC_APPLICATION":
            return _decision(
                False,
                set(),
                "WAN_SERVICE_IS_NOT_EXPLICIT_PUBLIC_APPLICATION",
                source_zone,
                target_zone,
            )
        if intent.get("published_gateway_bound") is not True:
            return _decision(
                False,
                set(),
                "WAN_PUBLISHED_GATEWAY_NOT_BOUND",
                source_zone,
                target_zone,
            )

    allowed = ZONE_PATH_RULES.get((source_zone, target_zone))
    if allowed is None:
        return _decision(
            False,
            set(),
            "ZONE_RELATION_NOT_DECLARED_FOR_THIS_INTENT",
            source_zone,
            target_zone,
        )

    return _decision(True, allowed, "ZONE_RELATION_CANDIDATE_ALLOWED", source_zone, target_zone)


def _decision(
    allowed: bool,
    paths: set[str],
    reason: str,
    source_zone: str,
    target_zone: str,
) -> dict[str, Any]:
    return {
        "allowed": allowed,
        "source_zone": source_zone,
        "target_zone": target_zone,
        "allowed_path_types": sorted(paths),
        "reason": reason,
        "policy_scope": "CANDIDATE_ZONE_POLICY_ONLY",
        "public_entry_is_internal_authority": False,
    }
