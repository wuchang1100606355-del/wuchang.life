from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

CANDIDATE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = CANDIDATE_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from w7tp_state_field_gateway.gateway import StateFieldGateway  # noqa: E402


def fixed_clock() -> datetime:
    return datetime(2026, 8, 19, 14, 45, 0, tzinfo=UTC)


def gateway() -> StateFieldGateway:
    return StateFieldGateway(candidate_root=CANDIDATE_ROOT, clock=fixed_clock)


def task_arguments() -> dict[str, object]:
    return {
        "node_id": "msi-linux-wsl",
        "task_kind": "observe_node_health",
        "target_ref": "msi-linux-wsl",
        "parameters": {},
    }


def authorization_arguments(instance: StateFieldGateway) -> dict[str, object]:
    task = instance.call_tool("prepare_task_candidate", task_arguments())["result"]
    return {
        "task_candidate_id": task["candidate_id"],
        "task_hash": task["task_hash"],
        "ttl_seconds": 300,
        "rollback_condition_id": "discard_candidate",
        "stop_condition_id": "first_policy_denial",
    }
