"""Router DLQ mock policy for W7TP Lite blocked or failed shards.

The output is an in-memory design object only. It does not append to runtime
dead-letter storage, replay work, or carry raw input payloads.
"""

from __future__ import annotations

import hashlib
import json
import sys
from typing import Any

from mock_phase_delta_allocator import allocate_phase_delta
from mock_semantic_lane_router import route_text


SCHEMA_ID = "w7tp.router_dead_letter_record.v0.1"


def apply_dlq_policy(decision: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Return Router DLQ mock records for blocked shards only."""
    records: list[dict[str, Any]] = []
    if not decision.get("route_to_dlq"):
        return records

    for shard in manifest.get("blocked_shards", []):
        digest = hashlib.sha256(
            f"{decision['decision_id']}:{shard['shard_id']}".encode("utf-8")
        ).hexdigest()[:12]
        records.append(
            {
                "schema": SCHEMA_ID,
                "dlq_id": f"router_dlq_{digest}",
                "intent_id": decision["intent_id"],
                "decision_id": decision["decision_id"],
                "shard_id": shard["shard_id"],
                "shard_hash": shard["block_hash"],
                "route_reason": decision["reason"],
                "redacted_summary": "Blocked write-intent shard; raw payload intentionally omitted.",
                "action": "hold_for_human_review",
                "replay_allowed": False,
                "persistence_mode": "mock_in_memory_only",
            }
        )
    return records


DEMO_CASES = (
    {
        "name": "health_check_intent",
        "text": "檢查目前 Gateway、Ollama、Odoo 是否在線",
        "expected_lanes": ["local_lane", "open_lane"],
        "expected_dlq": 0,
    },
    {
        "name": "document_spec_intent",
        "text": "整理 W7TP schema 文件與規格差異供 review",
        "expected_lanes": ["google_lane", "open_lane"],
        "expected_dlq": 0,
    },
    {
        "name": "odoo_write_intent",
        "text": "請寫入 Odoo 正式資料並建立會員",
        "expected_lanes": ["blocked"],
        "expected_dlq": 1,
    },
)


def run_self_test() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in DEMO_CASES:
        decision = route_text(case["text"])
        fragments = {lane: f"synthetic:{case['name']}:{lane}" for lane in decision["selected_lanes"]}
        manifest = allocate_phase_delta(decision, fragments)
        dlq_records = apply_dlq_policy(decision, manifest)
        assert decision["selected_lanes"] == case["expected_lanes"]
        assert decision["plan_only"] is True
        assert manifest["delta_only"] is True
        assert manifest["allocation_mode"] == "mock_shards_only_no_sync"
        assert len(dlq_records) == case["expected_dlq"]
        if case["expected_dlq"]:
            assert manifest["allocated_shards"] == []
            assert dlq_records[0]["replay_allowed"] is False
            assert dlq_records[0]["persistence_mode"] == "mock_in_memory_only"
        results.append(
            {
                "case": case["name"],
                "decision": decision,
                "manifest": manifest,
                "router_dlq": dlq_records,
                "status": "passed",
            }
        )
    return results


def main(argv: list[str]) -> int:
    if argv == ["--self-test"]:
        print(json.dumps(run_self_test(), ensure_ascii=False, indent=2))
        return 0

    text = " ".join(argv).strip() or DEMO_CASES[0]["text"]
    decision = route_text(text)
    fragments = {lane: f"synthetic:cli:{lane}" for lane in decision["selected_lanes"]}
    manifest = allocate_phase_delta(decision, fragments)
    output = {"decision": decision, "manifest": manifest, "router_dlq": apply_dlq_policy(decision, manifest)}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
