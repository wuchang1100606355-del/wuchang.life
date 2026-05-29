"""Synthetic phase-delta shard allocator for W7TP Lite.

This module hashes caller-provided mock fragments only. It never reads or
synchronizes real files and never examines live node load.
"""

from __future__ import annotations

import hashlib
import json
import sys
from typing import Any

from mock_semantic_lane_router import route_text


SCHEMA_ID = "w7tp.phase_delta_manifest.v0.1"


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _shard_id(lane: str, content: str) -> str:
    digest = hashlib.sha256(f"{lane}:{content}".encode("utf-8")).hexdigest()[:12]
    return f"shard_{digest}"


def _content_class(intent_class: str) -> str:
    return {
        "health_check": "health_plan",
        "document_spec_review": "document_spec",
        "blocked_write": "blocked_write",
        "manual_review": "document_spec",
    }[intent_class]


def _node_label(lane: str) -> str:
    return {
        "local_lane": "local_design_workspace",
        "google_lane": "cloud_review_advice_only",
        "open_lane": "cloud_review_advice_only",
        "blocked": "router_dlq",
    }[lane]


def allocate_phase_delta(
    decision: dict[str, Any],
    mock_fragments: dict[str, str],
    baseline_hashes: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create a no-sync manifest for changed synthetic fragments only."""
    if decision.get("plan_only") is not True:
        raise ValueError("phase delta allocator only accepts plan-only decisions")

    baseline_hashes = baseline_hashes or {}
    allocated: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    content_class = _content_class(decision["intent_class"])

    for lane in decision["selected_lanes"]:
        content = mock_fragments.get(lane, f"mock:{decision['intent_class']}:{lane}")
        block_hash = _sha256(content)
        shard = {
            "shard_id": _shard_id(lane, content),
            "content_class": content_class,
            "block_hash": block_hash,
            "delta_required": baseline_hashes.get(lane) != block_hash,
            "preferred_node_label": _node_label(lane),
            "lane": lane,
            "execution_status": "not_executed",
        }
        if lane == "blocked":
            blocked.append(shard)
        elif shard["delta_required"]:
            allocated.append(shard)
        else:
            unchanged.append(shard)

    phase = "blocked" if decision["route_to_dlq"] else "review_allocation"
    phase_material = json.dumps(
        {"decision_id": decision["decision_id"], "allocated": allocated, "blocked": blocked},
        ensure_ascii=False,
        sort_keys=True,
    )
    manifest_digest = hashlib.sha256(phase_material.encode("utf-8")).hexdigest()[:12]
    return {
        "schema": SCHEMA_ID,
        "manifest_id": f"phase_manifest_{manifest_digest}",
        "intent_id": decision["intent_id"],
        "decision_id": decision["decision_id"],
        "phase": phase,
        "delta_only": True,
        "phase_hash": _sha256(phase_material),
        "allocation_mode": "mock_shards_only_no_sync",
        "load_policy": "mock_no_live_load_observation",
        "allocated_shards": allocated,
        "skipped_unchanged_shards": unchanged,
        "blocked_shards": blocked,
        "plan_only": True,
    }


def main(argv: list[str]) -> int:
    text = " ".join(argv).strip() or "檢查目前 Gateway、Ollama、Odoo 是否在線"
    decision = route_text(text)
    fragments = {lane: f"mock fragment for {lane}: {decision['intent_class']}" for lane in decision["selected_lanes"]}
    print(json.dumps(allocate_phase_delta(decision, fragments), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
