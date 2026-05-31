#!/usr/bin/env python3
"""Local-only XiaoJ front/back-brain router.

This module keeps XiaoJ as one visible AI identity. Front-brain and the dynamic
engineering sensory brain are treated as internal state windows, not as two
separate AI beings. The engineering sensory brain decides which minimal sensory
state bundle the front-brain may see. They exchange only coordinate-like
MetricPacket/SensoryPacket data, never raw full context.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import subprocess
import sys
from typing import Any


FRONT_BRAIN_MODEL_CANDIDATES = ("gemma:2b", "qwen:0.5b")
BACK_BRAIN_MODEL_CANDIDATES = (
    "gemma4:e4b",
    "metric-language-gateway-ai:latest",
    "sister-j-brain:latest",
    "llama3.1:latest",
    "deepseek-r1:8b",
)


@dataclasses.dataclass(frozen=True)
class MetricPacket:
    intent: str
    node: str
    auth: str
    hazard: str
    memory_ref: str
    event_ref: str
    output_contract: str
    curvature: float
    identity: str = "XiaoJ"
    raw_context_included: bool = False

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def discover_ollama_models() -> list[str]:
    try:
        result = subprocess.run(
            ["ollama", "list"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    models: list[str] = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split()
        if parts:
            models.append(parts[0])
    return models


def choose_model(candidates: tuple[str, ...], available: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in available:
            return candidate
    return None


def classify_curvature(intent: str) -> float:
    lowered = intent.lower()
    high_terms = (
        "deploy",
        "docker",
        "odoo",
        "payment",
        "secret",
        "token",
        "ssh",
        "production",
        "容器",
        "部署",
        "金流",
        "憑證",
        "主權",
        "會計",
    )
    score = 0.22
    score += min(len(intent) / 800, 0.32)
    score += 0.42 if any(term in lowered for term in high_terms) else 0.0
    return round(min(score, 1.0), 3)


def build_metric_packet(intent: str, node: str, output_contract: str) -> MetricPacket:
    curvature = classify_curvature(intent)
    hazard = "L2_review" if curvature >= 0.65 else "L1_audit"
    if any(term in intent.lower() for term in ("payment", "secret", "token", "private key", "金流", "憑證")):
        hazard = "L3_metric_hazard"
    return MetricPacket(
        intent="metric_coordinate_intent",
        node=node,
        auth="gateway_required_human_boundary_preserved",
        hazard=hazard,
        memory_ref=sha256_text(intent),
        event_ref="event:" + dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        output_contract=output_contract,
        curvature=curvature,
    )


def route(packet: MetricPacket, available: list[str]) -> dict[str, Any]:
    front_brain_model = choose_model(FRONT_BRAIN_MODEL_CANDIDATES, available)
    back_brain_model = choose_model(BACK_BRAIN_MODEL_CANDIDATES, available)
    selected_state = "back_brain_routing" if packet.curvature >= 0.65 else "front_brain_operational"
    selected_model = back_brain_model if selected_state == "back_brain_routing" else front_brain_model
    if packet.hazard == "L3_metric_hazard":
        selected_state = "deadbox_review"
        selected_model = None
    return {
        "identity": "XiaoJ",
        "visible_ai_count": 1,
        "state_windows": {
            "front_brain_operational": front_brain_model,
            "dynamic_engineering_sensory_brain": back_brain_model,
            "metric_state": "Five Metric Gate",
            "memory_state": "hash_or_metric_ref_only",
        },
        "selected_state": selected_state,
        "selected_model": selected_model,
        "front_brain_visibility": "minimal_sensory_state_bundle_selected_by_engineering_brain",
        "engineering_brain_scope": (
            "vector_tensor_topology_gateway_response_memory_knowledge_environment_voice_auditory_collection"
        ),
        "dedicated_internal_line": "engineering_sensory_brain_to_2b_front_brain_point_to_point",
        "sensory_sources": [
            "memory_recall",
            "knowledge_retrieval",
            "environment_state",
            "voice_signal",
            "auditory_event",
            "topology_vector",
            "gateway_response",
        ],
        "direction_law": "SensoryPacket flows engineering_sensory_brain_to_front_brain_only",
        "exchange_format": "MetricPacket_or_SensoryPacket_coordinate_tensor_field_no_plaintext_context",
        "raw_context_exchange": False,
        "packet": packet.as_dict(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="XiaoJ one-identity dual-state local router")
    parser.add_argument("--intent", required=True, help="Intent text used only to derive hash and routing metrics.")
    parser.add_argument("--node", default="MSI")
    parser.add_argument("--output-contract", default="unified_xiaoj_answer")
    args = parser.parse_args()

    packet = build_metric_packet(args.intent, args.node, args.output_contract)
    decision = route(packet, discover_ollama_models())
    json.dump(decision, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
