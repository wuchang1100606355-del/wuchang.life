from tools.total_field.w7tp_multimodel_multifunction_route_candidate import build_candidate

REFS = {
    "task_ref": "current-intent:multimodel-20261017",
    "context_receipt_ref": "context-pull:example-only",
    "d8_envelope_ref": "d8-envelope:example-only",
}
OBSERVED = {
    "dynamic_context_receipt_verified": True,
    "d8_envelope_verified": True,
    "local_llm_live": True,
}

def make(surface, **kwargs):
    return build_candidate(surface=surface, observed=OBSERVED, **REFS, **kwargs)

def get_route(result, capability):
    return next(item for item in result["routes"] if item["capability"] == capability)

def test_local_routine_never_calls_external_or_executes():
    result = make("routine")
    assert result["state"] == "READY_FOR_TOTAL_FIELD_REVIEW"
    assert len(result["routes"]) == 1
    assert result["model_call_performed"] is False
    assert result["execution_authorized"] is False
    assert result["cloud_call_performed"] is False

def test_code_reuses_existing_cloud_and_remote_organs_as_candidates():
    result = build_candidate(
        surface="code", **REFS,
        observed={**OBSERVED, "code_assist_live": True,
                  "vertex_model_live": True, "native_claw_executor_verified": True},
        cloud_candidate_allowed=True,
    )
    assert get_route(result, "code_assistance")["state"] == "CANDIDATE_CLOUD"
    assert get_route(result, "complex_reasoning")["state"] == "CANDIDATE_CLOUD"
    assert get_route(result, "remote_code_execution")["state"] == "READY_FOR_D8_EXECUTION_REVIEW"
    assert result["remote_action_performed"] is False

def test_workspace_requires_bound_flow_not_generic_model_api():
    held = make("workspace", cloud_candidate_allowed=True)
    assert get_route(held, "workspace_automation")["state"].startswith("HOLD_")
    good = build_candidate(surface="workspace", **REFS, cloud_candidate_allowed=True,
                           observed={**OBSERVED, "workspace_studio_trigger_bound": True})
    assert get_route(good, "workspace_automation")["state"] == "CANDIDATE_WORKSPACE_FLOW"
    assert good["cloud_call_performed"] is False

def test_taiji04_voice_remains_held_even_if_caller_claims_license():
    result = build_candidate(surface="voice", **REFS,
        observed={**OBSERVED,
                  "taiji04_google_voice_commercial_grant_verified": True,
                  "taiji04_google_tts_interface_verified": True,
                  "taiji04_google_tts_license_type": "ANDROID_ENGINE"})
    route = get_route(result, "text_to_speech")
    assert route["state"] == "HOLD_D3_DEVICE_IDENTITY_MISMATCH"
    assert result["tts_performed"] is False
    assert result["state"] == "HOLD_REQUIRED_CAPABILITY"

def test_no_d8_context_does_not_grant_effects():
    result = build_candidate(task_ref="t1", surface="code",
        observed={"local_llm_live": True,
                  "code_assist_live": True, "vertex_model_live": True,
                  "native_claw_executor_verified": True},
        cloud_candidate_allowed=True)
    assert get_route(result, "code_assistance")["state"].startswith("HOLD_")
    assert get_route(result, "remote_code_execution")["state"].startswith("HOLD_")
    assert result["execution_authorized"] is False

def test_total_field_is_only_authority_and_native_claw_is_controlled():
    result = build_candidate(
        surface="code", **REFS, cloud_candidate_allowed=True,
        observed={
            **OBSERVED, "code_assist_live": True, "vertex_model_live": True,
            "native_claw_executor_verified": True,
        },
    )
    control = result["control_plane"]
    assert control["authority"] == "TAIJI01_TOTAL_FIELD_ONLY"
    assert control["native_claw"] == "TOTAL_FIELD_CONTROLLED_EXECUTION_ORGAN"
    assert control["local_llm"] == "COMPUTE_ONLY_NO_EFFECT_AUTHORITY"
    assert control["cloud_llm"] == "COMPUTE_ONLY_NO_EFFECT_AUTHORITY"
    assert control["sealed_execution_granted"] is False
    assert control["no_model_generated_authority"] is True
    assert control["no_cross_task_envelope_reuse"] is True
    assert result["execution_authorized"] is False
    assert all(not route["execution_authorized"] for route in result["routes"])


def test_missing_seal_ref_holds_even_when_models_report_ready():
    result = build_candidate(
        task_ref="current-intent",
        surface="code",
        context_receipt_ref="context:unverified",
        observed={
            "dynamic_context_receipt_verified": True,
            "d8_envelope_verified": True,
            "local_llm_live": True,
            "code_assist_live": True,
            "vertex_model_live": True,
            "native_claw_executor_verified": True,
        },
        cloud_candidate_allowed=True,
    )
    assert result["state"] == "HOLD_REQUIRED_CAPABILITY"
    assert "HOLD_CONTEXT_RECEIPT_OR_D8_ENVELOPE_UNVERIFIED" in result["held_route_states"]
    assert result["control_plane"]["sealed_execution_granted"] is False


def test_unknown_surface_fails_closed():
    result = make("unknown")
    assert result["state"] == "HOLD_TASK_COORDINATE_OR_SURFACE_INVALID"
    assert result["routes"] == []

def test_no_license_claim_may_be_inferred_from_device_model():
    result = make("3d", voice_requested=True)
    assert get_route(result, "text_to_speech")["license_type"] == "UNKNOWN"
    assert get_route(result, "text_to_speech")["state"].startswith("HOLD_")


# ADI distribution projection tests; no model calls, network or live D8 effects.
from tools.total_field.w7tp_multimodel_multifunction_route_candidate import (
    build_adi_distribution_candidate,
)
from tools.total_field_dynamic_context_pull import RESULT_SCHEMA, canonical_sha256

TASK = "task:WUC-NEW-INTENT"

def arbitration_snapshot(live=True):
    rid = "MSI_OLLAMA_LOCAL"
    return {
        "STATE": "PASS_RESOURCE_ARBITRATION",
        "RESOURCE_ROUTER": {"FORMAL_EFFECT_BOUNDARY": "TAIJI01_TOTAL_FIELD"},
        "RESOURCE_COORDINATES": [{
            "RESOURCE_ID": rid, "NODE": "MSI",
            "CURRENT_STATE": "AVAILABLE_CONNECTED" if live else "REGISTERED_AVAILABLE_RESOURCE",
            "CONTEXT_LOCATION": "MSI:ollama",
            "MODEL_OR_SERVICE": "xiaoj:latest",
        }],
        "AVAILABLE_SET": [rid],
        "QUALIFIED_SET": [rid],
        "PREFERRED_SET": [rid],
    }

def semantic_snapshot(task=TASK):
    return {"task_ref": task, "producer": "MSI_LOCAL_LLM", "authority": "CANDIDATE_ONLY"}

def context_snapshot(task=TASK):
    context = {
        "context_ref": "tfctx:example",
        "state_projection": {},
        "evidence_refs": [], "capability_refs": [], "acceptance_conditions": [],
        "schema_refs": [], "interface_refs": [], "non_core_rule_capsule_refs": [],
    }
    result = {
        "schema_version": RESULT_SCHEMA,
        "task_ref": task,
        "model_visible_context": context,
        "persistent_refs": {"context_ref": context["context_ref"], "packet_ref": "packet:example"},
        "authority": {"candidate_only": True, "model_authority": False},
        "persistence_policy": {
            "full_state_persistence_allowed": False,
            "credential_persistence_allowed": False,
        },
    }
    result["pull_result_sha256"] = canonical_sha256(result)
    return {"MSI_OLLAMA_LOCAL": {
        "task_ref": task, "resource_id": "MSI_OLLAMA_LOCAL",
        "provider_ref": "provider:MSI", "model_ref": "model:xiaoj",
        "pull_result": result,
    }}

def distribution(**overrides):
    args = {
        "task_ref": TASK,
        "semantic_candidate": semantic_snapshot(),
        "resource_arbitration": arbitration_snapshot(),
        "recipient_contexts": context_snapshot(),
        "requested_resource_ids": ["MSI_OLLAMA_LOCAL"],
    }
    args.update(overrides)
    return build_adi_distribution_candidate(**args)

def test_adi_distribution_uses_resource_index_and_minimum_context_refs():
    result = distribution()
    assert result["state"] == "READY_FOR_D8_REVIEW_CANDIDATE_ONLY"
    recipient = result["recipients"][0]
    assert recipient["node_coordinate"] == "MSI"
    assert recipient["context_ref"] == "tfctx:example"
    assert recipient["context_delivery"] == "BOUND_REFERENCE_CANDIDATE"
    assert result["remote_dispatch_executed"] is False
    assert result["execution_authorized"] is False
    assert result["d6"]["mode"] == "NOT_REQUIRED"
    assert result["model_internal_state_pulled"] is False

def test_adi_distribution_holds_registered_not_live_resource():
    result = distribution(resource_arbitration=arbitration_snapshot(live=False))
    assert result["state"] == "HOLD_CONTEXT_OR_RESOURCE"
    assert result["recipients"][0]["hold"] == "HOLD_RESOURCE_NOT_LIVE_QUALIFIED"

def test_adi_distribution_holds_mismatched_task_and_model_context():
    result = distribution(recipient_contexts=context_snapshot("task:OTHER"))
    assert result["state"] == "HOLD_CONTEXT_OR_RESOURCE"
    assert result["recipients"][0]["hold"] == "HOLD_CONTEXT_BINDING_OR_AUTHORITY_MISMATCH"
    result2 = distribution(semantic_candidate=semantic_snapshot("task:OTHER"))
    assert "HOLD_LOCAL_SEMANTIC_CANDIDATE_TASK_OR_ORIGIN" in result2["holds"]

def test_adi_distribution_holds_tampered_receipt():
    ctx = context_snapshot()
    ctx["MSI_OLLAMA_LOCAL"]["pull_result"]["persistent_refs"]["context_ref"] = "tfctx:altered"
    result = distribution(recipient_contexts=ctx)
    assert result["recipients"][0]["hold"] == "HOLD_CONTEXT_PULL_RECEIPT_INVALID"

def test_adi_d6_only_when_required_and_packet_dependency_bound():
    regular = distribution()
    assert regular["d6"]["mode"] == "NOT_REQUIRED"
    missing = distribution(d6_required=True)
    assert "HOLD_D6_PACKET_OR_RECONSTRUCTION_DEPENDENCIES" in missing["holds"]
    supplied = distribution(d6_required=True, d6_state_packet={
        "packet_ref": "cell:ref", "packet_sha256": "a"*64,
        "target_resource_id": "MSI_OLLAMA_LOCAL", "dependency_refs": ["rule:available"]
    })
    assert supplied["d6"]["mode"] == "D6_ORIGIN_STATE_RECONSTRUCTION_CANDIDATE"
    assert supplied["d6"]["transmitted"] is False
    assert supplied["d6"]["reconstructed"] is False
    assert supplied["d6"]["full_effect_cost_verified"] is False


def cloud_distribution(packet):
    from copy import deepcopy
    a = arbitration_snapshot()
    a["RESOURCE_COORDINATES"].append({
        "RESOURCE_ID": "GOOGLE_VERTEX_GEMINI", "NODE": "GOOGLE_CLOUD",
        "CURRENT_STATE": "AVAILABLE_CONNECTED",
        "CONTEXT_LOCATION": "cloud:vertex:bounded",
        "MODEL_OR_SERVICE": "gemini",
    })
    a["AVAILABLE_SET"].append("GOOGLE_VERTEX_GEMINI")
    a["QUALIFIED_SET"].append("GOOGLE_VERTEX_GEMINI")
    contexts = context_snapshot()
    cloud = deepcopy(contexts["MSI_OLLAMA_LOCAL"])
    cloud["resource_id"] = "GOOGLE_VERTEX_GEMINI"
    cloud["provider_ref"] = "provider:vertex"
    cloud["model_ref"] = "model:gemini"
    cloud["pull_result"]["model_visible_context"]["context_ref"] = "tfctx:cloud-example"
    cloud["pull_result"]["persistent_refs"]["context_ref"] = "tfctx:cloud-example"
    cloud["pull_result"]["pull_result_sha256"] = canonical_sha256({
        k: v for k, v in cloud["pull_result"].items()
        if k != "pull_result_sha256"
    })
    contexts["GOOGLE_VERTEX_GEMINI"] = cloud
    return distribution(
        resource_arbitration=a,
        recipient_contexts=contexts,
        requested_resource_ids=["MSI_OLLAMA_LOCAL", "GOOGLE_VERTEX_GEMINI"],
        cloud_model_origin_packet=packet,
    )

def test_cloud_origin_packet_only_candidate_not_internal_model_state():
    packet = {
        "semantic_class": "CLOUD_MODEL_OUTPUT_ORIGIN_STATE_CANDIDATE",
        "task_ref": TASK, "source_resource_id": "GOOGLE_VERTEX_GEMINI",
        "packet_ref": "packet:cloud-output-candidate", "packet_sha256": "b"*64,
        "dependency_refs": ["rule:ref"], "origin_state_contract_ref": "schema:gst:2.3",
        "model_internal_state_access": False,
    }
    result = cloud_distribution(packet)
    observed = result["cloud_origin_packet_pull"]
    assert observed["mode"] == "CANDIDATE_CLOUD_ORIGIN_PACKET_FOR_TOTAL_FIELD_PULL"
    assert observed["packet_pulled"] is False
    assert observed["reconstruction_verified"] is False
    assert result["execution_authorized"] is False

def test_cloud_origin_packet_bad_cross_task_or_internal_state_claim_holds():
    packet = {
        "semantic_class": "CLOUD_MODEL_OUTPUT_ORIGIN_STATE_CANDIDATE",
        "task_ref": "task:wrong", "source_resource_id": "GOOGLE_VERTEX_GEMINI",
        "packet_ref": "packet:cross-task", "packet_sha256": "b"*64,
        "dependency_refs": ["rule:ref"], "origin_state_contract_ref": "schema:gst:2.3",
        "model_internal_state_access": True,
    }
    result = cloud_distribution(packet)
    assert "HOLD_CLOUD_ORIGIN_PACKET_SCOPE_OR_DEPENDENCIES" in result["holds"]
    assert result["cloud_origin_packet_pull"]["packet_pulled"] is False
