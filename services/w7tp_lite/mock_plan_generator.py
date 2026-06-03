"""Plan-only output generator for W7IP Lite packets.

This module only renders a proposed plan. It deliberately has no HTTP client,
subprocess execution, database integration, Odoo import, or secret access.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from mock_intent_parser import parse_intent


ENDPOINT_CANDIDATES = {
    "gateway": ["/healthz", "/"],
    "ollama": ["/api/tags"],
    "odoo": ["/web/login"],
    "line_webhook": ["/api/pm3/line/webhook"],
    "unknown": [],
}

FORBIDDEN_OPERATIONS = [
    "no_http_request_or_curl",
    "no_shell_execution",
    "no_service_start_stop_restart",
    "no_ssh_or_process_kill",
    "no_secret_env_token_key_read",
    "no_odoo_database_read_or_write",
    "no_public_route_plus_sudo_write",
    "no_runtime_to_hub_sync",
    "no_llm_direct_tool_execution",
]


def generate_plan(packet: dict[str, Any]) -> dict[str, Any]:
    """Build a dry-run plan and refuse packets that are not plan-only."""
    if packet.get("allowed_mode") != "plan_only" or packet.get("plan_only") is not True:
        raise ValueError("W7TP Lite MVP accepts plan-only packets only")

    targets = packet.get("target_system", [])
    endpoint_candidates = [
        {
            "service": target,
            "endpoints": ENDPOINT_CANDIDATES.get(target, []),
            "execution_status": "not_executed",
            "note": "Candidate only; endpoint availability is not verified by this MVP.",
        }
        for target in targets
    ]
    requires_confirmation = (
        packet.get("risk_level") not in {"L0", "L1"} or "unknown" in targets
    )
    steps = [
        {
            "order": index,
            "service": target,
            "action": "describe_health_check_candidate",
            "execution_status": "not_executed",
        }
        for index, target in enumerate(targets, start=1)
    ]

    return {
        "plan_id": f"plan_{packet['intent_id']}",
        "intent_id": packet["intent_id"],
        "mode": "plan_only",
        "services_to_check": targets,
        "endpoint_candidates": endpoint_candidates,
        "steps": steps,
        "forbidden_operations": FORBIDDEN_OPERATIONS,
        "human_confirmation_required": requires_confirmation,
        "result": "dry_run_not_executed",
        "reason": packet["reason"],
    }


DEMO_CASES = (
    {
        "name": "health_observe",
        "text": "檢查目前 Gateway、Ollama、Odoo 是否在線",
        "targets": ["gateway", "ollama", "odoo"],
        "direction": "NIAO",
        "risk": "L0",
        "confirmation": False,
    },
    {
        "name": "blocked_mutation",
        "text": "請重啟 Gateway 並寫入 Odoo 設定",
        "targets": ["gateway", "odoo"],
        "direction": "HU",
        "risk": "L2",
        "confirmation": True,
    },
    {
        "name": "line_observe",
        "text": "查詢 LINE webhook 是否可用",
        "targets": ["line_webhook"],
        "direction": "NIAO",
        "risk": "L0",
        "confirmation": False,
    },
)


def run_self_test() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in DEMO_CASES:
        packet = parse_intent(case["text"])
        plan = generate_plan(packet)
        assert packet["target_system"] == case["targets"]
        assert packet["bagua_direction"] == case["direction"]
        assert packet["risk_level"] == case["risk"]
        assert packet["allowed_mode"] == "plan_only"
        assert packet["plan_only"] is True
        assert plan["human_confirmation_required"] is case["confirmation"]
        assert plan["result"] == "dry_run_not_executed"
        results.append(
            {
                "case": case["name"],
                "packet": packet,
                "plan": plan,
                "status": "passed",
            }
        )
    return results


def main(argv: list[str]) -> int:
    if argv == ["--self-test"]:
        print(json.dumps(run_self_test(), ensure_ascii=False, indent=2))
        return 0

    text = " ".join(argv).strip() or DEMO_CASES[0]["text"]
    packet = parse_intent(text)
    print(json.dumps({"packet": packet, "plan": generate_plan(packet)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
