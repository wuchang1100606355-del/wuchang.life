"""執行零外部效果的咖啡館 8D ADI 候選模擬。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sovereign_xiaoj import (
    FLOATING_INFERENCE_SCHEMA,
    NETWORK_STATE_SCHEMA,
    OBSERVATION_SCHEMA,
    build_sovereign_xiaoj_plan,
    load_scene_pack,
)


ROOT = Path(__file__).resolve().parent


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    image_ref = "simulation:image:cafe-counter"
    audio_ref = "simulation:audio:customer-intent"
    network_ref = "simulation:network:lan-ready"
    observations = [
        {
            "schema_id": OBSERVATION_SCHEMA,
            "modality": "image",
            "observation_ref": image_ref,
            "evidence_sha256": digest(image_ref),
            "source_class": "ISOLATED_SIMULATION",
            "features": ["counter", "cup", "no_face_inference"],
        },
        {
            "schema_id": OBSERVATION_SCHEMA,
            "modality": "audio",
            "observation_ref": audio_ref,
            "evidence_sha256": digest(audio_ref),
            "source_class": "ISOLATED_SIMULATION",
            "features": ["speech_segment", "transcript_candidate"],
        },
        {
            "schema_id": OBSERVATION_SCHEMA,
            "modality": "network_state",
            "observation_ref": network_ref,
            "evidence_sha256": digest(network_ref),
            "source_class": "ISOLATED_SIMULATION",
            "features": ["lan_reachable", "vpn_standby"],
        },
    ]
    plan = build_sovereign_xiaoj_plan(
        scene_pack=load_scene_pack(ROOT / "sovereign_xiaoj_scene_pack.json"),
        intent_id="founder-intent:competition-demo:001",
        intent_zh_tw="以咖啡館影音小J把全面理解形成可治理的服務候選",
        scene_id="cafe",
        requested_capability_ids=[
            "cafe.audiovisual.guide",
            "cafe.image.context",
            "cafe.audio.intent",
            "cafe.menu.explain",
            "cafe.order.proposal",
            "cafe.network.observe",
            "cafe.generative.transmission.plan",
        ],
        provider_bindings=[
            {
                "binding_ref": "compute:browser-local",
                "provider_kind": "browser_local",
                "priority": 1,
                "modality_allowlist": ["text", "audio", "network_state"],
                "model_allowlist": ["local-translator"],
                "daily_budget_units": 0,
                "used_units": 0,
                "state": "bound",
            },
            {
                "binding_ref": "compute:replaceable-cloud",
                "provider_kind": "other",
                "priority": 10,
                "modality_allowlist": ["text", "audio", "image"],
                "model_allowlist": ["bound-model"],
                "daily_budget_units": 100,
                "used_units": 0,
                "state": "bound",
            },
        ],
        observations=observations,
        high_dimensional_inference={
            "schema_id": FLOATING_INFERENCE_SCHEMA,
            "vector_ref": "simulation:vector:cafe-intent",
            "dimensions": 768,
            "source_model_ref": "model:replaceable:simulation",
            "hypotheses": [
                {"label": "需要菜單說明", "score": 0.94},
                {"label": "準備點餐", "score": 0.82},
            ],
            "proposed_capability_ids": ["cafe.menu.explain", "cafe.order.proposal"],
            "authority": False,
        },
        network_state={
            "schema_id": NETWORK_STATE_SCHEMA,
            "state": "LAN_READY",
            "available_paths": ["LAN", "VPN", "OFFLINE"],
            "observation_ref": network_ref,
            "evidence_sha256": digest(network_ref),
            "verified": True,
            "source_class": "ISOLATED_SIMULATION",
        },
    )
    summary = {
        "狀態": plan["state"],
        "系統": plan.get("system_kind"),
        "場景": plan.get("scene", {}).get("label_zh_tw"),
        "數位腦細胞數": plan.get("cell_count"),
        "已觀測模態": plan.get("comprehensive_understanding", {}).get("present_modalities"),
        "傳輸路徑": plan.get("transmission_route", {}).get("selected_path"),
        "完整物件傳輸": plan.get("transmission_route", {}).get("complete_object_transfer"),
        "真實效果已執行": plan.get("external_effect_executed"),
        "總場為最終作用閘門": plan.get("total_field_is_final_effect_gate"),
        "封包雜湊": plan.get("packet_sha256"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if plan["state"] == "VIRTUAL_CANDIDATE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
