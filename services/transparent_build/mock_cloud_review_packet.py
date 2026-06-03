"""Advice-only cloud review packet assembly for transparent-build mock data."""

from __future__ import annotations

import json
import sys
from typing import Any

from mock_observation_collector import BLOCKED_SENSITIVE_PATHS, collect_mock_observation
from mock_redactor import redact_observation_pack


SCHEMA_ID = "sister_j.transparent_observation_pack.v0.1"


def _review_priority(pack: dict[str, Any]) -> str:
    severities = {item["severity"] for item in pack.get("known_errors", [])}
    if "blocked" in severities:
        return "blocked"
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    return "low"


def create_cloud_review_packet(scenario: str = "design_baseline") -> dict[str, Any]:
    """Produce a redacted observation pack suitable only for advice/review."""
    raw_pack = collect_mock_observation(scenario)
    packet, redaction_summary = redact_observation_pack(raw_pack)
    packet["schema"] = SCHEMA_ID
    priority = _review_priority(packet)
    packet["cloud_review"] = {
        "review_priority": priority,
        "review_focus": [
            "Distinguish design evidence from live status.",
            "Review known gaps without requesting sensitive source data.",
            "Keep next actions review_or_plan_only.",
        ],
        "decision_requests": [
            "Confirm whether the proposed candidate files may proceed to human design review.",
            "Confirm that blocked sensitive paths remain local-only.",
        ],
        "cloud_action_boundary": "advice_only_no_execution",
        "redaction_summary": redaction_summary,
    }
    return packet


DEMO_EXPECTATIONS = {
    "design_baseline": {"stage": "design", "priority": "medium", "replacement_count": 0},
    "prototype_gap": {"stage": "prototype", "priority": "high", "replacement_count": 0},
    "audit_blocked": {"stage": "audit", "priority": "blocked", "replacement_count": 3},
}


def run_self_test() -> list[dict[str, Any]]:
    results = []
    for scenario, expected in DEMO_EXPECTATIONS.items():
        packet = create_cloud_review_packet(scenario)
        review = packet["cloud_review"]
        serialized = json.dumps(packet, ensure_ascii=False)
        assert packet["current_stage"] == expected["stage"]
        assert packet["observation_mode"] == "mock_static_input_only"
        assert packet["blocked_sensitive_paths"] == BLOCKED_SENSITIVE_PATHS
        assert review["review_priority"] == expected["priority"]
        assert review["cloud_action_boundary"] == "advice_only_no_execution"
        assert review["redaction_summary"]["replacement_count"] == expected["replacement_count"]
        assert "DEMO_VALUE" not in serialized
        assert "DEMO_TOKEN_VALUE" not in serialized
        assert "sample.person@example.invalid" not in serialized
        results.append(
            {
                "scenario": scenario,
                "current_stage": packet["current_stage"],
                "review_priority": review["review_priority"],
                "redaction_summary": review["redaction_summary"],
                "status": "passed",
            }
        )
    return results


def main(argv: list[str]) -> int:
    if argv == ["--self-test"]:
        print(json.dumps(run_self_test(), ensure_ascii=False, indent=2))
        return 0

    scenario = argv[0] if argv else "design_baseline"
    print(json.dumps(create_cloud_review_packet(scenario), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
