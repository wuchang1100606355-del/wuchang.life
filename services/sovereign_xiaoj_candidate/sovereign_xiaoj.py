"""主權 AI 小 J 的 8D ADI 完整 AI 應用系統候選核心。

這個模組把影像、聲音、文字、網路與設備狀態，經由離散精準索引及
高維浮點推理候選融合，組成可治理的數位腦細胞，再規劃既有場景能力、
算力與生成式傳輸。它不連線、不寫入 Odoo、不呼叫模型，也不授予真實效果權威。
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence


SCENE_PACK_SCHEMA = "W7TP_SOVEREIGN_XIAOJ_SCENE_PACK_CANDIDATE_V1"
PLAN_SCHEMA = "W7TP_SOVEREIGN_XIAOJ_PLAN_CANDIDATE_V1"
OBSERVATION_SCHEMA = "W7TP_MULTIMODAL_OBSERVATION_CANDIDATE_V1"
FLOATING_INFERENCE_SCHEMA = "W7TP_HIGH_DIMENSIONAL_INFERENCE_CANDIDATE_V1"
NETWORK_STATE_SCHEMA = "W7TP_NETWORK_STATE_OBSERVATION_CANDIDATE_V1"
SYSTEM_KIND = "8D_ADI_COMPLETE_AI_APPLICATION_SYSTEM"
STATE_CELL_SCHEMA_REF = (
    "tools.total_field_dynamic_context:W7TP_8DADI_STATE_CELL_PROJECTION_V1"
)
DIMENSIONS = ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8")
STATE_CELL_FIELDS = frozenset(
    {
        "cell_id",
        "cell_class",
        "node",
        "capability",
        "state",
        "dimensions",
        "evidence_ref",
        "evidence_sha256",
        "freshness",
        "relations",
        "source_class",
        "target_eligible",
        "authority_envelope_ref",
    }
)
TRANSMISSION_FIELDS = frozenset(
    {
        "TARGET_BASE_STATE",
        "MINIMUM_REQUIRED_DELTA",
        "REFERENCES",
        "COORDINATES",
        "RECONSTRUCTION_RULES",
        "VERIFICATION_RULES",
    }
)
ALLOWED_CAPABILITY_MODES = {"read_only", "candidate_only", "human_release"}
ALLOWED_PROVIDER_KINDS = {
    "browser_local",
    "local_model",
    "gemini",
    "openai",
    "other",
}
ALLOWED_ALERT_SOURCES = {"ISOLATED_SIMULATION", "NCDR_CAP", "CWA_PWS"}
ALLOWED_OBSERVATION_MODALITIES = {
    "text",
    "image",
    "audio",
    "network_state",
    "device_capability",
}
ALLOWED_NETWORK_STATES = {
    "UNKNOWN",
    "OFFLINE",
    "DEGRADED",
    "LAN_READY",
    "VPN_READY",
    "CLOUD_READY",
}
ALLOWED_NETWORK_PATHS = {"LAN", "VPN", "CLOUD", "OFFLINE"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SENSITIVE_KEY_PARTS = {
    "password",
    "token",
    "secret",
    "credential",
    "api_key",
    "raw_audio",
    "raw_video",
    "member_plaintext",
    "customer_plaintext",
}


class CandidateHold(ValueError):
    """可預期、可機器判斷的候選停止狀態。"""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_hex(value: object) -> str:
    if isinstance(value, bytes):
        material = value
    elif isinstance(value, str):
        material = value.encode("utf-8")
    else:
        material = canonical_json_bytes(value)
    return hashlib.sha256(material).hexdigest()


def _finalize(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(payload))
    result["packet_sha256"] = sha256_hex(result)
    return result


def _nonempty_text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CandidateHold(code, code)
    return value.strip()


def _string_list(value: object, code: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise CandidateHold(code, code)
    normalized: list[str] = []
    for item in value:
        normalized.append(_nonempty_text(item, code))
    if len(normalized) != len(set(normalized)):
        raise CandidateHold(code, f"{code}:DUPLICATED")
    return normalized


def _contains_sensitive_material(value: object, *, parent: str = "") -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            name = str(key).lower()
            if any(part in name for part in SENSITIVE_KEY_PARTS) and item not in (None, "", False, []):
                return True
            if _contains_sensitive_material(item, parent=name):
                return True
    elif isinstance(value, list):
        return any(_contains_sensitive_material(item, parent=parent) for item in value)
    return False


def load_scene_pack(path: str | Path) -> dict[str, Any]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CandidateHold("HOLD_SCENE_PACK_UNREADABLE", str(exc)) from exc
    return validate_scene_pack(raw)


def validate_scene_pack(raw: object) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CandidateHold("HOLD_SCENE_PACK_INVALID", "scene pack must be an object")
    pack = deepcopy(dict(raw))
    if pack.get("schema_id") != SCENE_PACK_SCHEMA or pack.get("state") != "CANDIDATE":
        raise CandidateHold("HOLD_SCENE_PACK_INVALID", "schema or state mismatch")
    for field in ("canonical", "active", "live_effect", "final_authority"):
        if pack.get(field) is not False:
            raise CandidateHold("HOLD_SCENE_PACK_AUTHORITY_INVERSION", field)
    if _contains_sensitive_material(pack):
        raise CandidateHold("HOLD_SCENE_PACK_SENSITIVE_MATERIAL", "sensitive material present")

    system = pack.get("system_definition")
    if not isinstance(system, Mapping) or system.get("system_kind") != SYSTEM_KIND:
        raise CandidateHold("HOLD_8D_ADI_SYSTEM_DEFINITION_MISSING", "system_definition")
    if system.get("complete_ai_application_system") is not True:
        raise CandidateHold("HOLD_8D_ADI_REDUCED_TO_COMPONENT", "complete_ai_application_system")
    planes = system.get("computation_planes")
    if not isinstance(planes, Mapping):
        raise CandidateHold("HOLD_COMPUTATION_PLANES_MISSING", "computation_planes")
    discrete_plane = planes.get("discrete_index")
    floating_plane = planes.get("high_dimensional_float")
    if not isinstance(discrete_plane, Mapping) or discrete_plane.get("decision_mode") != "EXACT_LOOKUP":
        raise CandidateHold("HOLD_DISCRETE_INDEX_CONTRACT_INVALID", "discrete_index")
    if not isinstance(floating_plane, Mapping) or floating_plane.get("output_authority") is not False:
        raise CandidateHold("HOLD_FLOATING_INFERENCE_AUTHORITY_INVERSION", "high_dimensional_float")
    if system.get("final_effect_adjudicator") != "TOTAL_FIELD":
        raise CandidateHold("HOLD_TOTAL_FIELD_BOUNDARY_MISSING", "final_effect_adjudicator")

    loop = pack.get("understanding_to_execution")
    if not isinstance(loop, Mapping):
        raise CandidateHold("HOLD_UNDERSTANDING_EXECUTION_LOOP_MISSING", "understanding_to_execution")
    required_steps = [
        "CAPTURE_INTENT_AND_MULTIMODAL_STATE",
        "BIND_EVIDENCE_AND_COORDINATES",
        "EXACT_DISCRETE_INDEX_LOOKUP",
        "HIGH_DIMENSIONAL_FLOATING_INFERENCE_CANDIDATE",
        "FUSE_WITHOUT_AUTHORITY_INVERSION",
        "BUILD_D1_D8_DIGITAL_BRAIN_CELLS",
        "SELECT_REPLACEABLE_COMPUTE",
        "GENERATE_MINIMUM_REQUIRED_TRANSMISSION",
        "RECONSTRUCT_AT_TARGET",
        "TOTAL_FIELD_ADJUDICATES_EFFECT",
        "REOBSERVE_AND_RECORD_STATE",
    ]
    if loop.get("steps") != required_steps:
        raise CandidateHold("HOLD_UNDERSTANDING_EXECUTION_LOOP_DRIFT", "steps")

    scenes = pack.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise CandidateHold("HOLD_SCENE_PACK_SCENES_MISSING", "scenes")
    seen_scenes: set[str] = set()
    seen_capabilities: set[str] = set()
    for scene in scenes:
        if not isinstance(scene, Mapping):
            raise CandidateHold("HOLD_SCENE_INVALID", "scene")
        scene_id = _nonempty_text(scene.get("scene_id"), "HOLD_SCENE_ID_INVALID")
        if scene_id in seen_scenes:
            raise CandidateHold("HOLD_SCENE_ID_DUPLICATED", scene_id)
        seen_scenes.add(scene_id)
        _nonempty_text(scene.get("label_zh_tw"), "HOLD_SCENE_LABEL_MISSING")
        _string_list(scene.get("odoo_coordinates"), "HOLD_SCENE_COORDINATE_MISSING")
        capabilities = scene.get("capabilities")
        if not isinstance(capabilities, list) or not capabilities:
            raise CandidateHold("HOLD_SCENE_CAPABILITY_MISSING", scene_id)
        for capability in capabilities:
            capability_id = _validate_capability(capability)
            if capability_id in seen_capabilities:
                raise CandidateHold("HOLD_CAPABILITY_ID_DUPLICATED", capability_id)
            seen_capabilities.add(capability_id)

    overlay = pack.get("earthquake_overlay")
    if not isinstance(overlay, Mapping):
        raise CandidateHold("HOLD_EARTHQUAKE_OVERLAY_MISSING", "earthquake_overlay")
    if overlay.get("trigger_schema") != "W7TP_VERIFIED_ALERT_EVENT_CANDIDATE_V1":
        raise CandidateHold("HOLD_ALERT_TRIGGER_SCHEMA_INVALID", "trigger_schema")
    if set(overlay.get("generative_transmission", {})) != TRANSMISSION_FIELDS:
        raise CandidateHold("HOLD_D6_CONTRACT_INCOMPLETE", "generative_transmission")
    for capability in overlay.get("capabilities", []):
        capability_id = _validate_capability(capability)
        if capability_id in seen_capabilities:
            raise CandidateHold("HOLD_CAPABILITY_ID_DUPLICATED", capability_id)
        seen_capabilities.add(capability_id)
    _string_list(overlay.get("official_reference_urls"), "HOLD_ALERT_REFERENCE_MISSING")
    return pack


def _validate_capability(raw: object) -> str:
    if not isinstance(raw, Mapping):
        raise CandidateHold("HOLD_CAPABILITY_INVALID", "capability")
    capability_id = _nonempty_text(raw.get("capability_id"), "HOLD_CAPABILITY_ID_INVALID")
    _nonempty_text(raw.get("label_zh_tw"), "HOLD_CAPABILITY_LABEL_MISSING")
    if raw.get("mode") not in ALLOWED_CAPABILITY_MODES:
        raise CandidateHold("HOLD_CAPABILITY_MODE_INVALID", capability_id)
    if not isinstance(raw.get("d8_required_for_effect"), bool):
        raise CandidateHold("HOLD_CAPABILITY_D8_BOUNDARY_MISSING", capability_id)
    if not isinstance(raw.get("local_safe"), bool):
        raise CandidateHold("HOLD_CAPABILITY_LOCAL_BOUNDARY_MISSING", capability_id)
    _string_list(raw.get("coordinates"), "HOLD_CAPABILITY_COORDINATE_MISSING")
    _string_list(raw.get("output_modalities"), "HOLD_CAPABILITY_OUTPUT_MISSING")
    return capability_id


def _capability_index(pack: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for scene in pack["scenes"]:
        for capability in scene["capabilities"]:
            item = deepcopy(dict(capability))
            item["scene_id"] = scene["scene_id"]
            index[item["capability_id"]] = item
    for capability in pack["earthquake_overlay"]["capabilities"]:
        item = deepcopy(dict(capability))
        item["scene_id"] = "earthquake_overlay"
        index[item["capability_id"]] = item
    return index


def _scene_index(pack: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["scene_id"]): deepcopy(dict(item)) for item in pack["scenes"]}


def _normalize_provider_binding(raw: object) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or _contains_sensitive_material(raw):
        raise CandidateHold("HOLD_PROVIDER_BINDING_SENSITIVE_OR_INVALID", "provider binding")
    binding = dict(raw)
    allowed_fields = {
        "binding_ref",
        "provider_kind",
        "priority",
        "modality_allowlist",
        "model_allowlist",
        "daily_budget_units",
        "used_units",
        "state",
    }
    if set(binding) != allowed_fields:
        raise CandidateHold("HOLD_PROVIDER_BINDING_SHAPE_INVALID", "provider binding")
    binding_ref = _nonempty_text(binding["binding_ref"], "HOLD_PROVIDER_REF_INVALID")
    kind = binding["provider_kind"]
    if kind not in ALLOWED_PROVIDER_KINDS:
        raise CandidateHold("HOLD_PROVIDER_KIND_INVALID", binding_ref)
    if binding["state"] != "bound":
        raise CandidateHold("HOLD_PROVIDER_NOT_BOUND", binding_ref)
    for field in ("priority", "daily_budget_units", "used_units"):
        value = binding[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise CandidateHold("HOLD_PROVIDER_BUDGET_INVALID", binding_ref)
    modalities = _string_list(binding["modality_allowlist"], "HOLD_PROVIDER_MODALITY_INVALID")
    models = _string_list(binding["model_allowlist"], "HOLD_PROVIDER_MODEL_INVALID")
    return {
        **binding,
        "binding_ref": binding_ref,
        "modality_allowlist": modalities,
        "model_allowlist": models,
    }


def select_compute_route(
    bindings: Sequence[Mapping[str, Any]],
    *,
    required_modality: str,
    cloud_required: bool,
    required_model: str | None = None,
    estimated_units: int = 1,
) -> dict[str, Any]:
    if not required_modality or estimated_units < 0:
        raise CandidateHold("HOLD_COMPUTE_REQUEST_INVALID", "compute request")
    normalized = [_normalize_provider_binding(item) for item in bindings]
    eligible: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for item in normalized:
        reason = None
        if required_modality not in item["modality_allowlist"]:
            reason = "MODALITY_NOT_ALLOWED"
        elif (
            required_model
            and item["provider_kind"] not in {"browser_local", "local_model"}
            and required_model not in item["model_allowlist"]
        ):
            reason = "MODEL_NOT_ALLOWED"
        elif item["daily_budget_units"] > 0 and (
            item["used_units"] + estimated_units > item["daily_budget_units"]
        ):
            reason = "DAILY_BUDGET_EXHAUSTED"
        if reason:
            rejected.append({"binding_ref": item["binding_ref"], "reason": reason})
        else:
            eligible.append(item)

    local = [item for item in eligible if item["provider_kind"] in {"browser_local", "local_model"}]
    cloud = [item for item in eligible if item["provider_kind"] not in {"browser_local", "local_model"}]
    local.sort(key=lambda item: (item["priority"], item["provider_kind"], item["binding_ref"]))
    cloud.sort(key=lambda item: (item["priority"], item["provider_kind"], item["binding_ref"]))
    if not local:
        raise CandidateHold("HOLD_LOCAL_TRANSLATOR_UNAVAILABLE", "local translator")
    route = [local[0]["binding_ref"]]
    selected_supplier = None
    if cloud_required:
        if not cloud:
            raise CandidateHold("HOLD_REPLACEABLE_CLOUD_COMPUTE_UNAVAILABLE", "cloud compute")
        selected_supplier = cloud[0]
        route.append(selected_supplier["binding_ref"])
    return {
        "state": "COMPUTE_ROUTE_CANDIDATE_READY",
        "route_binding_refs": route,
        "local_translation_binding_ref": local[0]["binding_ref"],
        "selected_compute_supplier_ref": (
            selected_supplier["binding_ref"] if selected_supplier else local[0]["binding_ref"]
        ),
        "selected_compute_supplier_kind": (
            selected_supplier["provider_kind"] if selected_supplier else local[0]["provider_kind"]
        ),
        "cloud_required": cloud_required,
        "minimum_delta_only": True,
        "provider_output_is_candidate": True,
        "provider_is_authority": False,
        "credential_material_present": False,
        "rejected_bindings": rejected,
    }


def _normalize_observation(raw: object) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or _contains_sensitive_material(raw):
        raise CandidateHold("HOLD_MULTIMODAL_OBSERVATION_INVALID", "observation")
    observation = deepcopy(dict(raw))
    required = {
        "schema_id",
        "modality",
        "observation_ref",
        "evidence_sha256",
        "source_class",
        "features",
    }
    if set(observation) != required or observation.get("schema_id") != OBSERVATION_SCHEMA:
        raise CandidateHold("HOLD_MULTIMODAL_OBSERVATION_SHAPE_INVALID", "observation")
    modality = observation.get("modality")
    if modality not in ALLOWED_OBSERVATION_MODALITIES:
        raise CandidateHold("HOLD_MULTIMODAL_MODALITY_UNSUPPORTED", str(modality))
    for field in ("observation_ref", "source_class"):
        _nonempty_text(observation.get(field), "HOLD_MULTIMODAL_OBSERVATION_FIELD_MISSING")
    if not SHA256_RE.fullmatch(str(observation.get("evidence_sha256") or "")):
        raise CandidateHold("HOLD_MULTIMODAL_EVIDENCE_INVALID", str(modality))
    observation["features"] = _string_list(
        observation.get("features"),
        "HOLD_MULTIMODAL_FEATURES_INVALID",
        allow_empty=True,
    )
    return observation


def _normalize_floating_inference(raw: object | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, Mapping) or _contains_sensitive_material(raw):
        raise CandidateHold("HOLD_FLOATING_INFERENCE_INVALID", "floating inference")
    item = deepcopy(dict(raw))
    required = {
        "schema_id",
        "vector_ref",
        "dimensions",
        "source_model_ref",
        "hypotheses",
        "proposed_capability_ids",
        "authority",
    }
    if set(item) != required or item.get("schema_id") != FLOATING_INFERENCE_SCHEMA:
        raise CandidateHold("HOLD_FLOATING_INFERENCE_SHAPE_INVALID", "floating inference")
    _nonempty_text(item.get("vector_ref"), "HOLD_FLOATING_VECTOR_REF_MISSING")
    _nonempty_text(item.get("source_model_ref"), "HOLD_FLOATING_MODEL_REF_MISSING")
    dimensions = item.get("dimensions")
    if isinstance(dimensions, bool) or not isinstance(dimensions, int) or dimensions <= 0:
        raise CandidateHold("HOLD_FLOATING_DIMENSIONS_INVALID", "dimensions")
    if item.get("authority") is not False:
        raise CandidateHold("HOLD_FLOATING_INFERENCE_AUTHORITY_INVERSION", "authority")
    hypotheses = item.get("hypotheses")
    if not isinstance(hypotheses, list):
        raise CandidateHold("HOLD_FLOATING_HYPOTHESES_INVALID", "hypotheses")
    normalized_hypotheses: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        if not isinstance(hypothesis, Mapping) or set(hypothesis) != {"label", "score"}:
            raise CandidateHold("HOLD_FLOATING_HYPOTHESIS_SHAPE_INVALID", "hypothesis")
        label = _nonempty_text(hypothesis.get("label"), "HOLD_FLOATING_HYPOTHESIS_LABEL_MISSING")
        score = hypothesis.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise CandidateHold("HOLD_FLOATING_SCORE_INVALID", label)
        score_float = float(score)
        if not math.isfinite(score_float) or not 0.0 <= score_float <= 1.0:
            raise CandidateHold("HOLD_FLOATING_SCORE_INVALID", label)
        normalized_hypotheses.append({"label": label, "score": score_float})
    item["hypotheses"] = normalized_hypotheses
    item["proposed_capability_ids"] = _string_list(
        item.get("proposed_capability_ids"),
        "HOLD_FLOATING_CAPABILITY_PROPOSAL_INVALID",
        allow_empty=True,
    )
    return item


def _normalize_network_state(raw: object | None) -> dict[str, Any]:
    if raw is None:
        return {
            "schema_id": NETWORK_STATE_SCHEMA,
            "state": "UNKNOWN",
            "available_paths": ["OFFLINE"],
            "observation_ref": "not-supplied",
            "evidence_sha256": None,
            "verified": False,
            "source_class": "UNKNOWN",
        }
    if not isinstance(raw, Mapping) or _contains_sensitive_material(raw):
        raise CandidateHold("HOLD_NETWORK_STATE_INVALID", "network state")
    item = deepcopy(dict(raw))
    required = {
        "schema_id",
        "state",
        "available_paths",
        "observation_ref",
        "evidence_sha256",
        "verified",
        "source_class",
    }
    if set(item) != required or item.get("schema_id") != NETWORK_STATE_SCHEMA:
        raise CandidateHold("HOLD_NETWORK_STATE_SHAPE_INVALID", "network state")
    if item.get("state") not in ALLOWED_NETWORK_STATES:
        raise CandidateHold("HOLD_NETWORK_STATE_UNSUPPORTED", str(item.get("state")))
    paths = _string_list(item.get("available_paths"), "HOLD_NETWORK_PATHS_INVALID")
    if any(path not in ALLOWED_NETWORK_PATHS for path in paths):
        raise CandidateHold("HOLD_NETWORK_PATH_UNSUPPORTED", ",".join(paths))
    if not isinstance(item.get("verified"), bool):
        raise CandidateHold("HOLD_NETWORK_VERIFICATION_INVALID", "verified")
    _nonempty_text(item.get("observation_ref"), "HOLD_NETWORK_OBSERVATION_REF_MISSING")
    _nonempty_text(item.get("source_class"), "HOLD_NETWORK_SOURCE_CLASS_MISSING")
    if not SHA256_RE.fullmatch(str(item.get("evidence_sha256") or "")):
        raise CandidateHold("HOLD_NETWORK_EVIDENCE_INVALID", "evidence_sha256")
    if item["verified"]:
        required_path = {
            "LAN_READY": "LAN",
            "VPN_READY": "VPN",
            "CLOUD_READY": "CLOUD",
            "OFFLINE": "OFFLINE",
        }.get(item["state"])
        if required_path is None or required_path not in paths:
            raise CandidateHold("HOLD_NETWORK_STATE_PATH_CONFLICT", item["state"])
    item["available_paths"] = paths
    return item


def _select_transmission_path(network_state: Mapping[str, Any]) -> dict[str, Any]:
    paths = set(network_state["available_paths"]) if network_state["verified"] else {"OFFLINE"}
    selected = next((path for path in ("LAN", "VPN", "CLOUD") if path in paths), "OFFLINE")
    return {
        "state": "TRANSMISSION_ROUTE_CANDIDATE_READY",
        "selected_path": selected,
        "priority": ["LAN", "VPN", "CLOUD", "OFFLINE"],
        "network_state": network_state["state"],
        "network_evidence_verified": network_state["verified"],
        "mode": "TARGET_RECONSTRUCTION_FROM_MINIMUM_REQUIRED_INFORMATION",
        "complete_object_transfer": False,
        "live_send_executed": False,
    }


def _build_understanding_field(
    *,
    observations: Sequence[Mapping[str, Any]],
    floating_inference: Mapping[str, Any] | None,
    requested_capability_ids: Sequence[str],
    resolved_capability_ids: Sequence[str],
) -> dict[str, Any]:
    normalized_observations = [_normalize_observation(item) for item in observations]
    floating = _normalize_floating_inference(floating_inference)
    requested = list(requested_capability_ids)
    resolved = list(resolved_capability_ids)
    if requested != resolved:
        raise CandidateHold("HOLD_DISCRETE_INDEX_LOOKUP_INCOMPLETE", "capability index")
    if floating:
        unknown = sorted(set(floating["proposed_capability_ids"]) - set(resolved))
        if unknown:
            raise CandidateHold("HOLD_FLOATING_PROPOSAL_OUTSIDE_EXACT_INDEX", ",".join(unknown))
    present = sorted({item["modality"] for item in normalized_observations})
    required_surfaces = ["image", "audio", "network_state", "device_capability"]
    return {
        "state": "COMPREHENSIVE_UNDERSTANDING_CANDIDATE_READY",
        "observations": normalized_observations,
        "present_modalities": present,
        "not_observed_modalities": [item for item in required_surfaces if item not in present],
        "discrete_index": {
            "mode": "EXACT_LOOKUP",
            "requested_capability_ids": requested,
            "resolved_capability_ids": resolved,
            "all_resolved": True,
            "lookup_sha256": sha256_hex(resolved),
        },
        "high_dimensional_float": floating,
        "fusion": {
            "mode": "EXACT_DISCRETE_INDEX_PLUS_HIGH_DIMENSIONAL_FLOAT_CANDIDATE",
            "exact_index_owns_coordinates_and_policy": True,
            "floating_inference_supplies_understanding_candidate": True,
            "floating_inference_may_create_coordinates": False,
            "floating_inference_may_grant_authority": False,
            "undefined_numeric_basis_inferred": False,
        },
    }


def _normalize_alert_event(raw: object) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or _contains_sensitive_material(raw):
        raise CandidateHold("HOLD_ALERT_EVENT_INVALID", "alert event")
    event = deepcopy(dict(raw))
    required = {
        "schema_id",
        "event_id",
        "source_class",
        "alert_type",
        "area_refs",
        "sent_at",
        "severity",
        "status",
        "evidence_ref",
        "evidence_sha256",
        "verified",
        "official_alert",
        "simulation",
    }
    if set(event) != required or event.get("schema_id") != "W7TP_VERIFIED_ALERT_EVENT_CANDIDATE_V1":
        raise CandidateHold("HOLD_ALERT_EVENT_SHAPE_INVALID", "alert event")
    for field in ("event_id", "alert_type", "sent_at", "severity", "status", "evidence_ref"):
        _nonempty_text(event.get(field), "HOLD_ALERT_EVENT_FIELD_MISSING")
    _string_list(event.get("area_refs"), "HOLD_ALERT_AREA_MISSING")
    if event.get("source_class") not in ALLOWED_ALERT_SOURCES:
        raise CandidateHold("HOLD_ALERT_SOURCE_UNTRUSTED", str(event.get("source_class")))
    if event.get("alert_type") != "earthquake":
        raise CandidateHold("HOLD_ALERT_TYPE_UNSUPPORTED", str(event.get("alert_type")))
    if not SHA256_RE.fullmatch(str(event.get("evidence_sha256") or "")):
        raise CandidateHold("HOLD_ALERT_EVIDENCE_INVALID", "evidence_sha256")
    if event["source_class"] == "ISOLATED_SIMULATION":
        if event.get("simulation") is not True or event.get("official_alert") is not False:
            raise CandidateHold("HOLD_SIMULATION_MISLABELED", "simulation")
    elif (
        event.get("verified") is not True
        or event.get("official_alert") is not True
        or event.get("simulation") is not False
    ):
        raise CandidateHold("HOLD_OFFICIAL_ALERT_NOT_VERIFIED", "official alert")
    return event


def _build_cell(
    *,
    cell_id: str,
    cell_class: str,
    capability: Mapping[str, Any],
    scene: Mapping[str, Any],
    intent_id: str,
    intent_zh_tw: str,
    evidence_ref: str,
    evidence_sha256: str,
    relations: list[str],
    alert_event: Mapping[str, Any] | None,
    modality_refs: list[str],
    network_state: Mapping[str, Any],
    transmission_route: Mapping[str, Any],
) -> dict[str, Any]:
    emergency = alert_event is not None
    d6_delta = {
        "capability_id": capability["capability_id"],
        "scene_id": scene["scene_id"],
        "emergency_overlay": emergency,
        "alert_event_id": alert_event.get("event_id") if emergency else None,
        "modality_refs": modality_refs,
        "network_state": network_state["state"],
    }
    dimensions = {
        "D1": {"intent_id": intent_id, "intent_zh_tw": intent_zh_tw},
        "D2": {
            "state": "EARTHQUAKE_SPECIAL_STATE" if emergency else f"{scene['scene_id'].upper()}_SERVICE_STATE",
            "candidate_only": True,
            "network_state": network_state["state"],
            "multimodal_observation_refs": modality_refs,
        },
        "D3": {
            "scene_id": scene["scene_id"],
            "coordinates": capability["coordinates"],
            "transmission_path": transmission_route["selected_path"],
        },
        "D4": {
            "evidence_ref": evidence_ref,
            "evidence_sha256": evidence_sha256,
            "multimodal_evidence_refs": modality_refs,
            "evidence_is_authority": False,
        },
        "D5": {
            "mode": capability["mode"],
            "external_effect_available_but_not_requested": capability["mode"] == "human_release",
            "external_effect_requested": False,
            "external_effect_executed": False,
        },
        "D6": {
            "TARGET_BASE_STATE": "SCENE_PACK_AND_LOCAL_SAFETY_ROUTINE_PRESENT",
            "MINIMUM_REQUIRED_DELTA": d6_delta,
            "REFERENCES": capability["coordinates"],
            "COORDINATES": scene["odoo_coordinates"],
            "RECONSTRUCTION_RULES": [
                "VERIFY_BASE_STATE",
                "APPLY_MINIMUM_DELTA",
                "RECONSTRUCT_AT_TARGET_NODE",
            ],
            "VERIFICATION_RULES": [
                "REOBSERVE_TARGET_STATE",
                "REJECT_UNKNOWN_EFFECT",
                "TOTAL_FIELD_DECIDES_ANY_EFFECT",
            ],
        },
        "D7": {
            "fail_closed": True,
            "local_safe": capability["local_safe"],
            "no_personal_plaintext": True,
            "no_unverified_alert_promotion": True,
        },
        "D8": {
            "authority": "NONE_IN_CANDIDATE",
            "total_field_required_for_effect": capability["d8_required_for_effect"],
            "model_is_authority": False,
        },
    }
    cell = {
        "cell_id": cell_id,
        "cell_class": cell_class,
        "node": "node:total-field-candidate",
        "capability": capability["capability_id"],
        "state": "CANDIDATE",
        "dimensions": dimensions,
        "evidence_ref": evidence_ref,
        "evidence_sha256": evidence_sha256,
        "freshness": "CURRENT_CANDIDATE_INPUT",
        "relations": relations,
        "source_class": "USER_DECLARED_CURRENT_INTENT",
        "target_eligible": True,
        "authority_envelope_ref": None,
    }
    if set(cell) != STATE_CELL_FIELDS or set(cell["dimensions"]) != set(DIMENSIONS):
        raise CandidateHold("HOLD_STATE_CELL_CONSTRUCTION_INVALID", cell_id)
    return cell


def _hold_packet(code: str, detail: str) -> dict[str, Any]:
    return _finalize(
        {
            "schema_id": PLAN_SCHEMA,
            "state": code,
            "detail_zh_tw": detail,
            "candidate": True,
            "tested": False,
            "canonical": False,
            "active": False,
            "deployed": False,
            "live_effect": False,
            "final_authority": False,
            "external_effect_executed": False,
            "next": "RESOLVE_ONLY_THIS_HOLD",
        }
    )


def build_sovereign_xiaoj_plan(
    *,
    scene_pack: Mapping[str, Any],
    intent_id: str,
    intent_zh_tw: str,
    scene_id: str,
    requested_capability_ids: Sequence[str],
    provider_bindings: Sequence[Mapping[str, Any]],
    input_modality: str = "text",
    cloud_required: bool = False,
    required_model: str | None = None,
    estimated_units: int = 1,
    alert_event: Mapping[str, Any] | None = None,
    observations: Sequence[Mapping[str, Any]] = (),
    high_dimensional_inference: Mapping[str, Any] | None = None,
    network_state: Mapping[str, Any] | None = None,
    expected_scene_pack_sha256: str | None = None,
    external_effect_requested: bool = False,
    d8_authority_envelope_ref: str | None = None,
) -> dict[str, Any]:
    """建立單一候選計畫；任何效果要求都停在既有總場閘門前。"""

    try:
        pack = validate_scene_pack(scene_pack)
        scene_pack_sha256 = sha256_hex(pack)
        if expected_scene_pack_sha256 is not None:
            if not SHA256_RE.fullmatch(expected_scene_pack_sha256):
                raise CandidateHold("HOLD_DRIFT_GUARD_HASH_INVALID", "expected_scene_pack_sha256")
            if expected_scene_pack_sha256 != scene_pack_sha256:
                raise CandidateHold("HOLD_SCENE_PACK_DRIFT_DETECTED", "scene pack hash mismatch")
        intent_id_text = _nonempty_text(intent_id, "HOLD_INTENT_ID_MISSING")
        intent_text = _nonempty_text(intent_zh_tw, "HOLD_INTENT_MISSING")
        scene_id_text = _nonempty_text(scene_id, "HOLD_SCENE_ID_MISSING")
        scenes = _scene_index(pack)
        if scene_id_text not in scenes:
            raise CandidateHold("HOLD_UNKNOWN_SCENE", scene_id_text)
        scene = scenes[scene_id_text]
        requested = list(requested_capability_ids)
        if not requested or any(not isinstance(item, str) or not item for item in requested):
            raise CandidateHold("HOLD_CAPABILITY_REQUEST_MISSING", "requested capabilities")
        if len(requested) != len(set(requested)):
            raise CandidateHold("HOLD_CAPABILITY_REQUEST_DUPLICATED", "requested capabilities")
        alert = _normalize_alert_event(alert_event) if alert_event is not None else None
        if alert:
            requested.extend(pack["earthquake_overlay"]["default_capability_ids"])
            requested = list(dict.fromkeys(requested))
        capabilities = _capability_index(pack)
        selected: list[dict[str, Any]] = []
        for capability_id in requested:
            capability = capabilities.get(capability_id)
            if capability is None:
                raise CandidateHold("HOLD_UNKNOWN_CAPABILITY", capability_id)
            if capability["scene_id"] not in {scene_id_text, "earthquake_overlay"}:
                raise CandidateHold("HOLD_CAPABILITY_SCENE_MISMATCH", capability_id)
            selected.append(capability)

        resolved_capability_ids = [item["capability_id"] for item in selected]
        understanding = _build_understanding_field(
            observations=observations,
            floating_inference=high_dimensional_inference,
            requested_capability_ids=requested,
            resolved_capability_ids=resolved_capability_ids,
        )
        normalized_network_state = _normalize_network_state(network_state)
        transmission_route = _select_transmission_path(normalized_network_state)
        if network_state is not None and cloud_required and transmission_route["selected_path"] == "OFFLINE":
            raise CandidateHold("HOLD_NETWORK_PATH_REQUIRED_FOR_CLOUD_COMPUTE", "offline")

        compute_route = select_compute_route(
            provider_bindings,
            required_modality=input_modality,
            cloud_required=cloud_required,
            required_model=required_model,
            estimated_units=estimated_units,
        )
        if external_effect_requested:
            code = "HOLD_D8_VERIFIER_REQUIRED" if d8_authority_envelope_ref else "HOLD_EFFECT_AUTHORITY_REQUIRED"
            raise CandidateHold(code, "候選規劃器不驗證或執行真實效果")

        evidence_ref = (
            alert["evidence_ref"]
            if alert
            else "founder-intent:sovereign-xiaoj-cafe-service-competition-2026"
        )
        evidence_sha256 = alert["evidence_sha256"] if alert else sha256_hex(intent_text)
        modality_refs = [item["observation_ref"] for item in understanding["observations"]]
        cell_ids = [f"cell:{scene_id_text}:{item['capability_id']}" for item in selected]
        cells = [
            _build_cell(
                cell_id=cell_id,
                cell_class="EARTHQUAKE_SERVICE_CAPABILITY" if alert else "STATIC_SCENE_CAPABILITY",
                capability=capability,
                scene=scene,
                intent_id=intent_id_text,
                intent_zh_tw=intent_text,
                evidence_ref=evidence_ref,
                evidence_sha256=evidence_sha256,
                relations=[other for other in cell_ids if other != cell_id],
                alert_event=alert,
                modality_refs=modality_refs,
                network_state=normalized_network_state,
                transmission_route=transmission_route,
            )
            for cell_id, capability in zip(cell_ids, selected)
        ]
        overlay = pack["earthquake_overlay"]
        transmission = deepcopy(overlay["generative_transmission"])
        transmission["MINIMUM_REQUIRED_DELTA"] = {
            "scene_id": scene_id_text,
            "capability_ids": requested,
            "multimodal_observation_refs": modality_refs,
            "discrete_lookup_sha256": understanding["discrete_index"]["lookup_sha256"],
            "floating_inference_ref": (
                understanding["high_dimensional_float"]["vector_ref"]
                if understanding["high_dimensional_float"]
                else None
            ),
            "selected_network_path": transmission_route["selected_path"],
            "alert_event": (
                {
                    "event_id": alert["event_id"],
                    "source_class": alert["source_class"],
                    "severity": alert["severity"],
                    "area_refs": alert["area_refs"],
                    "simulation": alert["simulation"],
                }
                if alert
                else None
            ),
        }
        if set(transmission) != TRANSMISSION_FIELDS:
            raise CandidateHold("HOLD_D6_CONTRACT_INCOMPLETE", "transmission")

        return _finalize(
            {
                "schema_id": PLAN_SCHEMA,
                "system_kind": SYSTEM_KIND,
                "state": "VIRTUAL_CANDIDATE_READY",
                "candidate": True,
                "tested": False,
                "canonical": False,
                "active": False,
                "deployed": False,
                "live_effect": False,
                "final_authority": False,
                "product": pack["product"],
                "scene": {
                    "scene_id": scene_id_text,
                    "label_zh_tw": scene["label_zh_tw"],
                    "entry_role": scene["entry_role"],
                },
                "special_state": "EARTHQUAKE_SIMULATION" if alert and alert["simulation"] else (
                    "EARTHQUAKE_VERIFIED_INPUT" if alert else "NORMAL_CAFE_SERVICE"
                ),
                "alert_event": alert,
                "comprehensive_understanding": understanding,
                "compute_route": compute_route,
                "network_state": normalized_network_state,
                "transmission_route": transmission_route,
                "understanding_to_execution": pack["understanding_to_execution"],
                "anti_drift": {
                    "scene_pack_sha256": scene_pack_sha256,
                    "expected_scene_pack_sha256": expected_scene_pack_sha256,
                    "drift_detected": False,
                    "historical_evidence_rebound": False,
                },
                "state_cell_schema_ref": STATE_CELL_SCHEMA_REF,
                "cells": cells,
                "cell_count": len(cells),
                "generative_transmission": transmission,
                "external_effect_requested": False,
                "external_effect_executed": False,
                "provider_output_is_candidate": True,
                "provider_is_authority": False,
                "total_field_is_final_effect_gate": True,
                "offline_minimum_service_ready": bool(
                    alert and all(item["local_safe"] for item in selected)
                ),
                "human_summary_zh_tw": (
                    "地震演練狀態已在本機重建；小J只做可驗證警報轉譯、避難引導與效果提案。"
                    if alert
                    else f"{scene['label_zh_tw']}的小J已把理解組成數位腦細胞與可執行候選；任何真實效果仍由人員與總場放行。"
                ),
                "next": "RENDER_CANDIDATE_WITHOUT_EXTERNAL_EFFECT",
            }
        )
    except CandidateHold as exc:
        return _hold_packet(exc.code, exc.detail)
