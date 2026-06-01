#!/usr/bin/env python3
import argparse
import json
import sys
import time
from pathlib import Path

TAIJI_ROOT = Path(__file__).resolve().parents[1]
CONNECTOR_DIR = TAIJI_ROOT / "connectors"
REGISTRY_PATH = TAIJI_ROOT / "config" / "action_registry.json"
AUDIT_LOG = TAIJI_ROOT / "logs" / "five_metric_audit.jsonl"

sys.path.insert(0, str(CONNECTOR_DIR))

from five_metric_gate import metric_gate


def append_audit(record):
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_registry():
    with REGISTRY_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_vector(raw):
    try:
        vec = json.loads(raw)
    except Exception as e:
        raise SystemExit(f"invalid_vector_json={e}")

    if not isinstance(vec, list) or len(vec) != 5:
        raise SystemExit("current_vector_must_be_json_list_of_5_numbers")

    return [float(x) for x in vec]


def same_vector(a, b):
    return [float(x) for x in a] == [float(x) for x in b]


def deny(code, reason, action_name, actor, extra=None):
    record = {
        "timestamp": time.time(),
        "gate": "taiji_metric_preflight",
        "actor": actor,
        "action_name": action_name,
        "decision": "deny",
        "reason": reason,
        "registry": extra or {}
    }
    append_audit(record)
    print(json.dumps({
        "allowed": False,
        "reason": reason,
        "audit_log": str(AUDIT_LOG),
        "audit": record
    }, ensure_ascii=False, indent=2))
    raise SystemExit(code)


def main():
    parser = argparse.ArgumentParser(description="Taiji Metric Preflight Gate")
    parser.add_argument("--action", required=True)
    parser.add_argument("--current", required=False)
    parser.add_argument("--actor", default="taiji_preflight")
    parser.add_argument("--strict", action="store_true")

    args = parser.parse_args()

    registry = load_registry()
    actions = registry.get("actions", {})

    if registry.get("locked") is not True:
        deny(47, "action_registry_not_locked", args.action, args.actor, {
            "registry_name": registry.get("registry_name"),
            "registry_version": registry.get("version")
        })

    if registry.get("default_policy") != "deny_unregistered":
        deny(48, "action_registry_default_policy_not_deny", args.action, args.actor, {
            "registry_name": registry.get("registry_name"),
            "registry_version": registry.get("version")
        })

    if args.action not in actions:
        deny(44, "unregistered_action_denied", args.action, args.actor, {
            "registry_name": registry.get("registry_name"),
            "registry_version": registry.get("version"),
            "registry_locked": registry.get("locked"),
            "known_actions": sorted(actions.keys())
        })

    action_def = actions[args.action]

    if action_def.get("enabled") is not True:
        deny(45, "disabled_action_denied", args.action, args.actor, {
            "registry_name": registry.get("registry_name"),
            "registry_version": registry.get("version"),
            "registered_action": args.action
        })

    registry_current = [float(x) for x in action_def["current"]]

    if args.current:
        supplied_current = parse_vector(args.current)
        if not same_vector(supplied_current, registry_current):
            deny(46, "action_current_mismatch_denied", args.action, args.actor, {
                "registry_name": registry.get("registry_name"),
                "registry_version": registry.get("version"),
                "registry_locked": registry.get("locked"),
                "registered_action": args.action,
                "registry_current": registry_current,
                "supplied_current": supplied_current
            })

    result = metric_gate(
        action_name=args.action,
        current=registry_current,
        actor=args.actor
    )

    result["registry"] = {
        "registry_name": registry.get("registry_name"),
        "registry_version": registry.get("version"),
        "registry_locked": registry.get("locked"),
        "registered_action": args.action,
        "default_policy": registry.get("default_policy")
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result.get("allowed"):
        raise SystemExit(40)

    if args.strict and result.get("reason") == "metric_warning_continue_with_audit":
        raise SystemExit(30)

    raise SystemExit(0)


if __name__ == "__main__":
    main()
