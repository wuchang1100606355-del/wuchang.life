from __future__ import annotations

from typing import Any

from .route_selector import select_route


def resolve_service(
    intent_id: str,
    source_node: str,
    target_node: str,
    service_identity: str,
    *,
    source_zone: str,
    target_zone: str,
    service_class: str = "INTERNAL_APPLICATION",
    published_gateway_bound: bool = False,
    paths: list[dict[str, Any]],
    verification: dict[str, Any] | None = None,
    permitted_paths: list[str] | None = None,
    concurrent_paths: list[str] | None = None,
    allow_concurrent_paths: bool = False,
    path_preference: list[str] | None = None,
    target_identity_state: str = "OBSERVED_PARTIAL",
    observed_at: str | None = None,
    ttl_seconds: int = 300,
    policy_version: str = "PER_INTENT_MULTIPATH_V1",
    now: str | None = None,
) -> dict[str, Any]:
    """Consumer API: applications express a service intent, not a carrier."""

    intent = {
        "intent_id": intent_id,
        "source_node": source_node,
        "source_zone": source_zone,
        "target_node": target_node,
        "target_zone": target_zone,
        "service_identity": service_identity,
        "service_class": service_class,
        "published_gateway_bound": published_gateway_bound,
        "permitted_paths": permitted_paths,
        "concurrent_paths": concurrent_paths or [],
        "allow_concurrent_paths": allow_concurrent_paths,
        "path_preference": path_preference,
        "target_identity_state": target_identity_state,
    }
    return select_route(
        intent,
        paths,
        verification,
        observed_at=observed_at,
        ttl_seconds=ttl_seconds,
        policy_version=policy_version,
        now=now,
    )
