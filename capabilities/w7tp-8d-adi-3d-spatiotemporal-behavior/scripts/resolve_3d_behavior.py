#!/usr/bin/env python3
"""Read-only 3D behavior projection resolver: exact model digest, creator labels.

This is a D3 application index projection under W7TP/8D ADI V2.3.
It cannot grant D8, perform authoring, create a new 3D character or
replace the 8-in-1 Total Field.
"""
import json
import re
from pathlib import Path

MAP=Path(__file__).resolve().parent.parent/"references/CROSS_MODEL_BEHAVIOR_MAPPING.json"
HEX64=re.compile(r"^[0-9a-f]{64}$")

class ModelRouteHold(ValueError):
    pass

def resolve(source_sha256:str, behavior:str, *, require_anatomical_landmark=False, registry_path=MAP):
    """Map a human action to verified source-level controls, not bone indices."""
    if not isinstance(source_sha256,str) or HEX64.fullmatch(source_sha256) is None:
        raise ModelRouteHold("HOLD_MODEL_SOURCE_SHA_INVALID")
    if not isinstance(behavior,str) or behavior not in ("smile","微笑"):
        raise ModelRouteHold("HOLD_BEHAVIOR_NOT_SUPPORTED")
    data=json.loads(Path(registry_path).read_text(encoding="utf-8"))
    if data.get("authority")!="CANDIDATE_ONLY" or data.get("runtime_authority") is not False:
        raise ModelRouteHold("HOLD_MAPPING_AUTHORITY_DRIFT")
    variants=[m for m in data.get("model_variants",[]) if m.get("model_sha256")==source_sha256]
    if len(variants)!=1:
        raise ModelRouteHold("HOLD_MODEL_IDENTITY_NOT_UNIQUELY_BOUND")
    variant=variants[0]
    spec=variant.get("semantics",{}).get("smile")
    if not isinstance(spec,dict) or not spec.get("control_targets"):
        raise ModelRouteHold("HOLD_MODEL_MORPH_TARGET_UNMAPPED")
    if not isinstance(variant.get("bone_count"),int) or variant["bone_count"]<1:
        raise ModelRouteHold("HOLD_MODEL_BONE_PROVENANCE_MISSING")
    if require_anatomical_landmark:
        raise ModelRouteHold("HOLD_MOUTH_ANATOMICAL_POINT_NOT_INDEPENDENTLY_VERIFIED")
    return {
      "schema":"W7TP_MODEL_SPECIFIC_3D_BEHAVIOR_PROJECTION/1.0-CANDIDATE",
      "task_ref":data["task_ref"],
      "model_id":variant["model_id"],
      "model_sha256":source_sha256,
      "human_intent":"微笑",
      "behavior_ref":"smile",
      "source_semantic_control":spec["source"],
      "control_targets":spec["control_targets"],
      "source_semantic_provenance":spec["semantic_channel_provenance"],
      "control_point_status":spec["control_point_provenance"],
      "time_duration_ms":data["timeline_default_ms"],
      "easing_rule_ref":data["interpolation_ref"],
      "position_basis":data["positions"],
      "distance_method":data["distance_metric"],
      "unit_state":data["units"],
      "source_assets_required":True,
      "byte_reconstruction_claimed":False,
      "effect_execution_granted":False,
      "d8_authority":False,
      "canonical":False
    }
