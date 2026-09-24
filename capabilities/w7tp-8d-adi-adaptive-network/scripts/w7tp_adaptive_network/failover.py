from __future__ import annotations

from typing import Any

from .route_selector import select_route


def evaluate_binding_failover(
    binding: dict[str, Any],
    paths: list[dict[str, Any]],
    verification: dict[str, Any] | None = None,
    *,
    now: str | None = None,
) -> dict[str, Any]:
    """Evaluate only the supplied binding; no host-global path state exists."""

    intent = dict(binding.get("intent") or _intent_from_binding(binding))
    previous_path = binding.get("selected_path")
    preference = [
        previous_path,
        *binding.get("alternate_paths", []),
    ]
    preference = [value for value in preference if value]
    if preference:
        intent["path_preference"] = preference

    reevaluated = select_route(
        intent,
        paths,
        verification,
        observed_at=binding.get("observed_at"),
        ttl_seconds=int(binding.get("ttl_seconds", 300)),
        policy_version=str(binding.get("policy_version", "PER_INTENT_MULTIPATH_V1")),
        now=now,
    )
    next_path = reevaluated.get("selected_path")
    if next_path == previous_path and reevaluated.get("authorized"):
        state = "HEALTHY"
    elif next_path and next_path != previous_path and reevaluated.get("authorized"):
        state = "ALTERNATE_ACTIVE"
    elif next_path and next_path != previous_path:
        state = "ALTERNATE_VERIFYING"
    elif previous_path:
        state = "PRIMARY_PATH_FAILED"
    else:
        state = "HOLD"

    return {
        **reevaluated,
        "binding_state": state,
        "previous_selected_path": previous_path,
        "failover_scope": "PER_BINDING",
        "other_bindings_modified": False,
    }


def _intent_from_binding(binding: dict[str, Any]) -> dict[str, Any]:
    return {
        key: binding.get(key)
        for key in (
            "intent_id",
            "source_node",
            "source_zone",
            "target_node",
            "target_zone",
            "service_identity",
            "service_class",
            "published_gateway_bound",
        )
    }
