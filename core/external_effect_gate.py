"""Fail-closed gate for effects performed through external execution tools.

This does not grant authority. Read-only observation may pass without an effect
permit. Any mutation requires an exact, unexpired permit and a matching effect
already allowed by the active Total Field authority pointer.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_POINTER = PROJECT_ROOT / "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json"

READ_ONLY_OPERATIONS = frozenset({
    "observe", "read", "list", "search", "inspect", "status", "health", "screenshot",
})

class ExternalEffectHold(RuntimeError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ExternalEffectHold("HOLD_EFFECT_PERMIT_TTL_TIMEZONE_REQUIRED")
    return parsed.astimezone(timezone.utc)


def load_active_authority(path: Path = AUTHORITY_POINTER) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExternalEffectHold("HOLD_ACTIVE_TOTAL_FIELD_AUTHORITY_UNREADABLE") from exc
    if not isinstance(value, dict) or value.get("state") != "ACTIVE_TOTAL_FIELD_AUTHORITY":
        raise ExternalEffectHold("HOLD_ACTIVE_TOTAL_FIELD_AUTHORITY_INVALID")
    return value


def authorize_external_effect(
    *,
    task_id: str,
    node: str,
    object_ref: str,
    operation: str,
    permit: dict[str, Any] | None = None,
    authority_path: Path = AUTHORITY_POINTER,
    now: datetime | None = None,
) -> dict[str, Any]:
    op = operation.strip().lower()
    if op in READ_ONLY_OPERATIONS:
        return {
            "state": "ALLOW_READ_ONLY_EXTERNAL_OBSERVATION",
            "effect_authority": False,
            "mutation": False,
        }

    if not isinstance(permit, dict):
        raise ExternalEffectHold("HOLD_EXTERNAL_MUTATION_EFFECT_PERMIT_REQUIRED")

    required = {
        "task_id", "node", "object_ref", "operation", "preimage_ref",
        "rollback_ref", "expires_at", "authority_ref", "authorized_effect",
    }
    if set(permit) != required:
        raise ExternalEffectHold("HOLD_EFFECT_PERMIT_SHAPE_INVALID")
    expected = {
        "task_id": task_id,
        "node": node,
        "object_ref": object_ref,
        "operation": operation,
    }
    if any(permit.get(key) != value for key, value in expected.items()):
        raise ExternalEffectHold("HOLD_EFFECT_PERMIT_COORDINATE_MISMATCH")
    if not permit["preimage_ref"] or not permit["rollback_ref"]:
        raise ExternalEffectHold("HOLD_EFFECT_PERMIT_RECOVERY_COORDINATE_MISSING")

    authority = load_active_authority(authority_path)
    if permit["authority_ref"] != str(authority_path):
        raise ExternalEffectHold("HOLD_EFFECT_PERMIT_AUTHORITY_REF_MISMATCH")
    effect = permit["authorized_effect"]
    if effect in authority.get("prohibited_effects", []):
        raise ExternalEffectHold("HOLD_EXTERNAL_EFFECT_PROHIBITED")
    if effect not in authority.get("allowed_effects", []):
        raise ExternalEffectHold("HOLD_EXTERNAL_EFFECT_NOT_ALLOWED_BY_TOTAL_FIELD")

    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if _utc(str(permit["expires_at"])) <= current:
        raise ExternalEffectHold("HOLD_EFFECT_PERMIT_EXPIRED")

    return {
        "state": "ALLOW_EXACT_EXTERNAL_EFFECT",
        "effect_authority": True,
        "mutation": True,
        "authorized_effect": effect,
        "task_id": task_id,
        "node": node,
        "object_ref": object_ref,
        "operation": operation,
    }
