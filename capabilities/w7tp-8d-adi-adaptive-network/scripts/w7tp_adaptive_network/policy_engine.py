from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .zone_policy import evaluate_zone_policy


DEFAULT_PATH_ORDER = (
    "LOOPBACK_SERVICE_PATH",
    "CONTAINER_LOCAL_PATH",
    "LAN_IPV4",
    "TAILSCALE_IPV4",
    "NATIVE_IPV6",
    "TAILSCALE_IPV6",
    "GUEST_SERVICE_PATH",
    "IOT_SERVICE_PATH",
    "WAN_PUBLICATION_PATH",
)
IPV6_PATH_TYPES = {"NATIVE_IPV6", "TAILSCALE_IPV6"}


def evaluate_policy(
    intent: dict[str, Any],
    paths: list[dict[str, Any]],
    *,
    now: str | datetime | None = None,
) -> dict[str, Any]:
    """Select one candidate for one intent without granting D8 authority.

    The returned path sets are scoped to this intent.  They never become a
    host-wide primary/secondary/tertiary route state.
    """

    zone_decision = evaluate_zone_policy(intent)
    path_rows = _with_path_ids(paths)
    permitted = set(intent.get("permitted_paths") or DEFAULT_PATH_ORDER)
    permitted &= set(zone_decision["allowed_path_types"])
    preference = _intent_path_order(intent)
    identity_state = intent.get("target_identity_state", "OBSERVED_PARTIAL")

    available: list[str] = []
    qualified: list[str] = []
    denied: list[str] = []
    stale: list[str] = []
    denial_reasons: dict[str, list[str]] = {}

    for path in path_rows:
        path_id = path["path_id"]
        path_type = path.get("path_type", "UNKNOWN")
        reasons: list[str] = []
        if path.get("available", False):
            available.append(path_id)
        if path_is_stale(path, now=now):
            stale.append(path_id)
            reasons.append("STALE_EVIDENCE")
        if path_type not in permitted:
            reasons.append("PATH_NOT_PERMITTED_FOR_INTENT_OR_ZONE")
        path_service = path.get("service_identity")
        if path_service and path_service != intent.get("service_identity"):
            reasons.append("SERVICE_IDENTITY_MISMATCH")
        path_intent = path.get("intent_id")
        if path_intent and path_intent != intent.get("intent_id"):
            reasons.append("INTENT_BINDING_MISMATCH")
        if path.get("identity_state", "OBSERVED_PARTIAL") == "CONFLICT":
            reasons.append("PATH_IDENTITY_CONFLICT")
        if path_type in IPV6_PATH_TYPES and not path.get("qualified", False):
            reasons.append("IPV6_CANDIDATE_NOT_QUALIFIED")
        if not _base_eligible(path):
            reasons.append("PATH_OR_SERVICE_NOT_REACHABLE")
        if reasons:
            denied.append(path_id)
            denial_reasons[path_id] = sorted(set(reasons))
        else:
            qualified.append(path_id)

    qualified = _sort_path_ids(qualified, path_rows, preference)
    requested_concurrent = set(intent.get("concurrent_paths") or [])
    if intent.get("allow_concurrent_paths", False) and not requested_concurrent:
        concurrent = list(qualified)
    else:
        concurrent = [path_id for path_id in qualified if path_id in requested_concurrent]

    selected_id = qualified[0] if qualified else None
    selected = next((row for row in path_rows if row["path_id"] == selected_id), None)
    alternates = [path_id for path_id in qualified if path_id != selected_id]

    if identity_state in {"CONFLICT", "UNKNOWN", "LOCALIZED_UNKNOWN"}:
        candidate_decision = "HOLD"
        reason = (
            "TARGET_IDENTITY_CONFLICT"
            if identity_state == "CONFLICT"
            else "TARGET_IDENTITY_NOT_BOUND"
        )
        selected = None
        selected_id = None
        concurrent = []
    elif not zone_decision["allowed"]:
        candidate_decision = "DENY"
        reason = zone_decision["reason"]
        selected = None
        selected_id = None
        concurrent = []
    elif selected:
        candidate_decision = "CANDIDATE_PATH_SELECTED"
        reason = "PER_INTENT_QUALIFIED_PATH_SELECTED"
    elif not paths:
        candidate_decision = "LOCALIZED_UNKNOWN"
        reason = "NO_CURRENT_PATH_EVIDENCE"
    else:
        candidate_decision = "HOLD"
        reason = "NO_QUALIFIED_PATH_FOR_THIS_INTENT"

    return {
        "network_model": "MULTI_PATH_CONCURRENT_FIELD",
        "routing_unit": "PER_INTENT_BINDING",
        "failover_scope": "PER_BINDING",
        "global_three_way_selection": False,
        "candidate_decision": candidate_decision,
        "decision": candidate_decision,
        "selected_path": selected_id,
        "selected_path_type": selected.get("path_type") if selected else None,
        "selected_interface": selected.get("interface") if selected else None,
        "selected_target": selected.get("target") if selected else None,
        "alternate_paths": alternates,
        "concurrent_paths": concurrent,
        "available_path_set": sorted(set(available)),
        "qualified_path_set": qualified,
        "active_path_set": [],
        "denied_path_set": sorted(set(denied)),
        "stale_path_set": sorted(set(stale)),
        "denial_reasons": denial_reasons,
        "zone_policy": zone_decision,
        "reason": reason,
        "score_used_as_authority": False,
        "authorized": False,
        "total_field_decision": "NOT_RUN",
        "canonical": False,
    }


def path_is_stale(path: dict[str, Any], *, now: str | datetime | None = None) -> bool:
    if path.get("stale", False):
        return True
    expires_at = path.get("expires_at")
    if not expires_at:
        return False
    expiry = _parse_time(expires_at)
    current = _parse_time(now) if now is not None else datetime.now(timezone.utc)
    return expiry is None or current is None or current >= expiry


def _base_eligible(path: dict[str, Any]) -> bool:
    return bool(
        path.get("available", False)
        and path.get("host_reachable", False)
        and path.get("service_reachable", False)
        and path.get("identity_state", "OBSERVED_PARTIAL") != "CONFLICT"
    )


def _intent_path_order(intent: dict[str, Any]) -> tuple[str, ...]:
    requested = intent.get("path_preference") or intent.get("permitted_paths")
    if not requested:
        return DEFAULT_PATH_ORDER
    ordered = [str(value) for value in requested]
    ordered.extend(value for value in DEFAULT_PATH_ORDER if value not in ordered)
    return tuple(ordered)


def _with_path_ids(paths: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for path in paths:
        path_type = str(path.get("path_type", "UNKNOWN"))
        counts[path_type] = counts.get(path_type, 0) + 1
    rows: list[dict[str, Any]] = []
    for index, path in enumerate(paths):
        row = dict(path)
        path_type = str(row.get("path_type", "UNKNOWN"))
        path_id = row.get("path_id")
        if not path_id and counts[path_type] == 1:
            path_id = path_type
        if not path_id:
            coordinate = row.get("target") or row.get("interface") or str(index)
            path_id = f"{path_type}@{coordinate}"
        row["path_id"] = str(path_id)
        rows.append(row)
    return rows


def _sort_path_ids(
    path_ids: list[str], paths: list[dict[str, Any]], preference: tuple[str, ...]
) -> list[str]:
    by_id = {path["path_id"]: path for path in paths}
    rank = {value: index for index, value in enumerate(preference)}
    return sorted(
        path_ids,
        key=lambda path_id: (
            rank.get(path_id, rank.get(str(by_id[path_id].get("path_type")), len(rank))),
            -float(by_id[path_id].get("candidate_score", 0.0)),
            path_id,
        ),
    )


def _parse_time(value: str | datetime | None) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
