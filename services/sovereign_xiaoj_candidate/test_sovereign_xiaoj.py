from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("sovereign_xiaoj", ROOT / "sovereign_xiaoj.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def load_pack():
    return MODULE.load_scene_pack(ROOT / "sovereign_xiaoj_scene_pack.json")


def bindings():
    return [
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
            "binding_ref": "compute:local-vlm",
            "provider_kind": "local_model",
            "priority": 2,
            "modality_allowlist": ["image", "text"],
            "model_allowlist": ["local-vision-translator"],
            "daily_budget_units": 0,
            "used_units": 0,
            "state": "bound",
        },
        {
            "binding_ref": "compute:gemini-member",
            "provider_kind": "gemini",
            "priority": 10,
            "modality_allowlist": ["text", "audio", "image"],
            "model_allowlist": ["gemini-custom"],
            "daily_budget_units": 100,
            "used_units": 4,
            "state": "bound",
        },
        {
            "binding_ref": "compute:openai-member",
            "provider_kind": "openai",
            "priority": 20,
            "modality_allowlist": ["text", "audio", "image"],
            "model_allowlist": ["gpt-custom"],
            "daily_budget_units": 100,
            "used_units": 5,
            "state": "bound",
        },
    ]


def simulation_event():
    material = "2026 competition earthquake simulation fixture"
    return {
        "schema_id": "W7TP_VERIFIED_ALERT_EVENT_CANDIDATE_V1",
        "event_id": "simulation:earthquake:cafe:001",
        "source_class": "ISOLATED_SIMULATION",
        "alert_type": "earthquake",
        "area_refs": ["demo-area:cafe"],
        "sent_at": "2026-09-09T12:00:00+08:00",
        "severity": "Severe",
        "status": "Exercise",
        "evidence_ref": "fixture:earthquake:cafe:001",
        "evidence_sha256": hashlib.sha256(material.encode()).hexdigest(),
        "verified": True,
        "official_alert": False,
        "simulation": True,
    }


def multimodal_observations():
    values = []
    for modality, ref, features in (
        ("image", "fixture:image:cafe-counter", ["counter", "cup", "no_face_inference"]),
        ("audio", "fixture:audio:customer-intent", ["speech_segment", "transcript_candidate"]),
        ("network_state", "fixture:network:lan", ["lan_reachable", "vpn_standby"]),
        ("device_capability", "fixture:device:kiosk", ["display", "speaker", "microphone"]),
    ):
        values.append(
            {
                "schema_id": MODULE.OBSERVATION_SCHEMA,
                "modality": modality,
                "observation_ref": ref,
                "evidence_sha256": hashlib.sha256(ref.encode()).hexdigest(),
                "source_class": "ISOLATED_TEST_FIXTURE",
                "features": features,
            }
        )
    return values


def high_dimensional_inference():
    return {
        "schema_id": MODULE.FLOATING_INFERENCE_SCHEMA,
        "vector_ref": "fixture:vector:cafe-intent:001",
        "dimensions": 768,
        "source_model_ref": "model:replaceable:test-only",
        "hypotheses": [
            {"label": "需要菜單說明", "score": 0.94},
            {"label": "準備點餐", "score": 0.82},
        ],
        "proposed_capability_ids": ["cafe.menu.explain", "cafe.order.proposal"],
        "authority": False,
    }


def lan_network_state():
    ref = "fixture:network-state:lan-ready"
    return {
        "schema_id": MODULE.NETWORK_STATE_SCHEMA,
        "state": "LAN_READY",
        "available_paths": ["LAN", "VPN", "OFFLINE"],
        "observation_ref": ref,
        "evidence_sha256": hashlib.sha256(ref.encode()).hexdigest(),
        "verified": True,
        "source_class": "ISOLATED_TEST_FIXTURE",
    }


def build(**overrides):
    args = {
        "scene_pack": load_pack(),
        "intent_id": "founder-intent:competition:001",
        "intent_zh_tw": "以咖啡館影音小J展示完整8D ADI人工智慧應用系統與地震韌性",
        "scene_id": "cafe",
        "requested_capability_ids": [
            "cafe.audiovisual.guide",
            "cafe.menu.explain",
            "cafe.order.proposal",
        ],
        "provider_bindings": bindings(),
    }
    args.update(overrides)
    return MODULE.build_sovereign_xiaoj_plan(**args)


def test_pack_defines_complete_system_and_reuses_four_static_odoo_scenes():
    pack = load_pack()
    assert [scene["scene_id"] for scene in pack["scenes"]] == [
        "cafe",
        "property",
        "association",
        "personal",
    ]
    assert pack["system_definition"]["system_kind"] == MODULE.SYSTEM_KIND
    assert pack["system_definition"]["complete_ai_application_system"] is True
    assert pack["system_definition"]["final_effect_adjudicator"] == "TOTAL_FIELD"
    assert pack["compute_binding_source"]["odoo_model"] == "wuchang.ai.compute.binding"
    assert pack["earthquake_overlay"]["xiaoj_may_issue_national_alert"] is False


def test_normal_cafe_plan_is_candidate_only_and_has_complete_cells():
    plan = build()
    assert plan["state"] == "VIRTUAL_CANDIDATE_READY"
    assert plan["candidate"] is True
    assert plan["canonical"] is False
    assert plan["active"] is False
    assert plan["deployed"] is False
    assert plan["external_effect_executed"] is False
    assert plan["special_state"] == "NORMAL_CAFE_SERVICE"
    assert plan["cell_count"] == 3
    for cell in plan["cells"]:
        assert set(cell) == MODULE.STATE_CELL_FIELDS
        assert tuple(cell["dimensions"]) == MODULE.DIMENSIONS
        assert cell["dimensions"]["D8"]["model_is_authority"] is False


def test_earthquake_simulation_reconstructs_locally_without_claiming_official_alert():
    plan = build(alert_event=simulation_event())
    assert plan["state"] == "VIRTUAL_CANDIDATE_READY"
    assert plan["special_state"] == "EARTHQUAKE_SIMULATION"
    assert plan["alert_event"]["official_alert"] is False
    assert plan["alert_event"]["simulation"] is True
    assert plan["offline_minimum_service_ready"] is True
    assert "safety.drop_cover_hold" in [cell["capability"] for cell in plan["cells"]]
    assert set(plan["generative_transmission"]) == MODULE.TRANSMISSION_FIELDS
    assert plan["external_effect_executed"] is False


def test_unverified_live_alert_fails_closed():
    event = simulation_event()
    event.update(
        {
            "source_class": "NCDR_CAP",
            "simulation": False,
            "official_alert": True,
            "verified": False,
            "status": "Actual",
        }
    )
    plan = build(alert_event=event)
    assert plan["state"] == "HOLD_OFFICIAL_ALERT_NOT_VERIFIED"
    assert plan["live_effect"] is False


def test_unknown_alert_source_fails_closed():
    event = simulation_event()
    event["source_class"] = "SOCIAL_MEDIA_POST"
    plan = build(alert_event=event)
    assert plan["state"] == "HOLD_ALERT_SOURCE_UNTRUSTED"


def test_effect_request_never_crosses_total_field_gate():
    without_d8 = build(external_effect_requested=True)
    assert without_d8["state"] == "HOLD_EFFECT_AUTHORITY_REQUIRED"
    with_unverified_ref = build(
        external_effect_requested=True,
        d8_authority_envelope_ref="authority-envelope:unverified",
    )
    assert with_unverified_ref["state"] == "HOLD_D8_VERIFIER_REQUIRED"
    assert with_unverified_ref["external_effect_executed"] is False


def test_local_first_route_does_not_spend_cloud_units_for_safety_script():
    plan = build(alert_event=simulation_event(), cloud_required=False)
    route = plan["compute_route"]
    assert route["route_binding_refs"] == ["compute:browser-local"]
    assert route["cloud_required"] is False
    assert route["provider_is_authority"] is False


def test_cloud_gap_uses_replaceable_bound_provider_after_local_translation():
    plan = build(cloud_required=True, required_model="gemini-custom", estimated_units=2)
    route = plan["compute_route"]
    assert route["route_binding_refs"] == ["compute:browser-local", "compute:gemini-member"]
    assert route["minimum_delta_only"] is True
    assert route["provider_output_is_candidate"] is True


def test_multimodal_understanding_fuses_exact_lookup_and_floating_candidate():
    plan = build(
        observations=multimodal_observations(),
        high_dimensional_inference=high_dimensional_inference(),
        network_state=lan_network_state(),
    )
    understanding = plan["comprehensive_understanding"]
    assert plan["system_kind"] == MODULE.SYSTEM_KIND
    assert understanding["present_modalities"] == [
        "audio",
        "device_capability",
        "image",
        "network_state",
    ]
    assert understanding["discrete_index"]["all_resolved"] is True
    assert understanding["fusion"]["floating_inference_may_create_coordinates"] is False
    assert understanding["fusion"]["floating_inference_may_grant_authority"] is False
    assert plan["transmission_route"]["selected_path"] == "LAN"
    assert plan["transmission_route"]["complete_object_transfer"] is False
    assert plan["transmission_route"]["live_send_executed"] is False
    assert plan["anti_drift"]["drift_detected"] is False


def test_floating_inference_cannot_invent_capability_coordinate():
    inference = high_dimensional_inference()
    inference["proposed_capability_ids"].append("invented.unindexed.effect")
    plan = build(high_dimensional_inference=inference)
    assert plan["state"] == "HOLD_FLOATING_PROPOSAL_OUTSIDE_EXACT_INDEX"
    assert plan["external_effect_executed"] is False


def test_scene_pack_hash_drift_fails_closed_without_rebinding():
    plan = build(expected_scene_pack_sha256="0" * 64)
    assert plan["state"] == "HOLD_SCENE_PACK_DRIFT_DETECTED"
    assert plan["external_effect_executed"] is False


def test_known_offline_state_cannot_request_cloud_compute():
    state = lan_network_state()
    state.update({"state": "OFFLINE", "available_paths": ["OFFLINE"]})
    plan = build(
        network_state=state,
        cloud_required=True,
        required_model="gemini-custom",
    )
    assert plan["state"] == "HOLD_NETWORK_PATH_REQUIRED_FOR_CLOUD_COMPUTE"


def test_unverified_online_claim_uses_conservative_offline_path():
    state = lan_network_state()
    state["verified"] = False
    plan = build(network_state=state)
    assert plan["state"] == "VIRTUAL_CANDIDATE_READY"
    assert plan["network_state"]["state"] == "LAN_READY"
    assert plan["network_state"]["verified"] is False
    assert plan["transmission_route"]["selected_path"] == "OFFLINE"
    assert plan["transmission_route"]["network_evidence_verified"] is False


def test_effect_capability_is_only_available_until_explicit_effect_request():
    plan = build(requested_capability_ids=["cafe.order.release"])
    assert plan["state"] == "VIRTUAL_CANDIDATE_READY"
    d5 = plan["cells"][0]["dimensions"]["D5"]
    assert d5["external_effect_available_but_not_requested"] is True
    assert d5["external_effect_requested"] is False
    assert d5["external_effect_executed"] is False


def test_exhausted_provider_holds_instead_of_bypassing_model_allowlist():
    limited = bindings()
    gemini = next(item for item in limited if item["provider_kind"] == "gemini")
    gemini["daily_budget_units"] = 5
    gemini["used_units"] = 5
    plan = build(
        provider_bindings=limited,
        cloud_required=True,
        required_model="gemini-custom",
        estimated_units=1,
    )
    assert plan["state"] == "HOLD_REPLACEABLE_CLOUD_COMPUTE_UNAVAILABLE"


def test_sensitive_provider_material_is_rejected():
    unsafe = bindings()
    unsafe[0]["api_key"] = "must-never-enter-the-core"
    plan = build(provider_bindings=unsafe)
    assert plan["state"] == "HOLD_PROVIDER_BINDING_SENSITIVE_OR_INVALID"


def test_plan_is_deterministic_for_same_inputs():
    first = build(alert_event=simulation_event())
    second = build(alert_event=simulation_event())
    assert first == second
    unsigned = dict(first)
    supplied = unsigned.pop("packet_sha256")
    assert MODULE.sha256_hex(unsigned) == supplied


def test_scene_capability_cannot_leak_across_static_scene():
    plan = build(requested_capability_ids=["property.notice.read"])
    assert plan["state"] == "HOLD_CAPABILITY_SCENE_MISMATCH"


def test_static_scene_pack_contains_no_sensitive_material():
    pack = json.loads((ROOT / "sovereign_xiaoj_scene_pack.json").read_text(encoding="utf-8"))
    assert MODULE._contains_sensitive_material(pack) is False
