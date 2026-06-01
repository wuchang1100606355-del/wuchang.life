#!/usr/bin/env python3
import json
import sys
import time
from pathlib import Path

CONNECTOR_DIR = Path(__file__).resolve().parent
TAIJI_ROOT = CONNECTOR_DIR.parent
LOG_DIR = TAIJI_ROOT / "logs"
AUDIT_LOG = LOG_DIR / "five_metric_audit.jsonl"

sys.path.insert(0, str(CONNECTOR_DIR))

from five_metric_client import health, hazard_check


DEFAULT_MEMORY_POOL = [
    [0.0, 0.0, 0.0, 1.0, 1.0],
    [1.0, 1.0, 1.0, 5.0, 1.0],
    [2.0, 2.0, 2.0, 6.0, 1.0],
]


def append_audit(record):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def metric_gate(action_name, current, memory_pool=None, weights=None, actor="taiji_hub"):
    """
    Taiji execution pre-check gate.

    Decision:
    - allow
    - allow_with_audit
    - warn
    - block
    """
    if memory_pool is None:
        memory_pool = DEFAULT_MEMORY_POOL

    result = hazard_check(
        current=current,
        memory_pool=memory_pool,
        weights=weights
    )

    decision = result.get("action", "block")

    audit_record = {
        "timestamp": time.time(),
        "gate": "five_metric_gate",
        "actor": actor,
        "action_name": action_name,
        "current": current,
        "decision": decision,
        "metric_result": result
    }

    append_audit(audit_record)

    if decision == "block":
        return {
            "allowed": False,
            "reason": "metric_hazard_blocked",
            "audit_log": str(AUDIT_LOG),
            "audit": audit_record
        }

    if decision == "warn":
        return {
            "allowed": True,
            "reason": "metric_warning_continue_with_audit",
            "audit_log": str(AUDIT_LOG),
            "audit": audit_record
        }

    return {
        "allowed": True,
        "reason": decision,
        "audit_log": str(AUDIT_LOG),
        "audit": audit_record
    }


def require_metric_permission(action_name, current, memory_pool=None, weights=None, actor="taiji_hub"):
    """
    強制守門版本：
    block 時直接 raise RuntimeError。
    """
    result = metric_gate(
        action_name=action_name,
        current=current,
        memory_pool=memory_pool,
        weights=weights,
        actor=actor
    )

    if not result["allowed"]:
        raise RuntimeError(json.dumps(result, ensure_ascii=False, indent=2))

    return result


if __name__ == "__main__":
    print("=== FIVE METRIC GATE WITH AUDIT CHECK ===")
    print(json.dumps(health(), ensure_ascii=False, indent=2))

    print("\n=== SAFE ACTION ===")
    safe = metric_gate(
        action_name="safe_memory_lookup",
        current=[1.0, 1.0, 1.0, 5.0, 1.0],
        actor="gate_self_test"
    )
    print(json.dumps(safe, ensure_ascii=False, indent=2))

    print("\n=== HAZARD ACTION ===")
    hazard = metric_gate(
        action_name="dangerous_metric_drift",
        current=[10.0, 10.0, 10.0, 50.0, 1.0],
        actor="gate_self_test"
    )
    print(json.dumps(hazard, ensure_ascii=False, indent=2))

    if safe["allowed"] is not True:
        raise SystemExit("safe action should be allowed")

    if hazard["allowed"] is not False:
        raise SystemExit("hazard action should be blocked")

    print("\n✓ five metric gate audit ok")
    print(f"audit_log={AUDIT_LOG}")
