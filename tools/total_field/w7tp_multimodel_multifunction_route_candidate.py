#!/usr/bin/env python3
"""Read-only multi-model/function routing projection for W7TP/8D ADI V2.3.

A bounded capability selector, NOT a separate 8D core, authorization engine, or
runtime executor. It reuses current audio topology and refers to established
model, context and task execution organs. No provider invocation or state write.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.total_field.w7tp_all_node_audio_topology import resolve_audio_target

SURFACES = {"routine", "code", "research", "workspace", "voice", "3d"}
SOURCES = {
    "local": "core/msi_local_llm_route.py",
    "code_assist": "tools/gemini_code_assist_a2a_candidate.py",
    "vertex": "tools/total_field/w7tp_vertex_candidate_gateway.py",
    "workspace": "Google Workspace Studio triggers.fire (requires a bound trigger and OAuth)",
    "claw": "legacy_core/taiji_native_claw.py + authorized remote execution organs",
    "audio": "tools/total_field/w7tp_all_node_audio_topology.py",
    "context": "tools/total_field_dynamic_context_pull.py",
}

def _bool(observed: Mapping[str, Any], key: str) -> bool:
    return observed.get(key) is True

def build_candidate(
    *,
    task_ref: str,
    surface: str,
    context_receipt_ref: str = "",
    d8_envelope_ref: str = "",
    observed: Mapping[str, Any] | None = None,
    cloud_candidate_allowed: bool = False,
    voice_requested: bool = False,
) -> dict[str, Any]:
    """Build capability routing evidence without executing provider calls.

    Observed readiness is supplied by external live observation, not inferred
    from file existence. Receipts/refs are routing inputs, not self-authorization.
    """
    observed = observed or {}
    if surface not in SURFACES or not task_ref.strip():
        return {
            "schema": "W7TP_8D_ADI_MULTIFUNCTION_ROUTE_CANDIDATE_V1",
            "state": "HOLD_TASK_COORDINATE_OR_SURFACE_INVALID",
            "execution_authorized": False,
            "routes": [],
        }
    context_bounded = bool(context_receipt_ref and d8_envelope_ref
                           and _bool(observed, "dynamic_context_receipt_verified")
                           and _bool(observed, "d8_envelope_verified"))
    routes: list[dict[str, Any]] = []

    def add(capability: str, provider: str, state: str, purpose: str) -> None:
        routes.append({
            "capability": capability,
            "provider": provider,
            "state": state,
            "purpose": purpose,
            "execution_authorized": False,
        })

    local_ready = _bool(observed, "local_llm_live")
    add("language_inference", "MSI_OLLAMA_LOCAL",
        "CANDIDATE_LOCAL" if local_ready else "HOLD_LOCAL_MODEL_NOT_OBSERVED",
        "local-first language understanding and bounded code candidate")

    if surface == "code":
        add("code_assistance", "GEMINI_CODE_ASSIST_A2A",
            ("CANDIDATE_CLOUD" if cloud_candidate_allowed
             and _bool(observed, "code_assist_live") and context_bounded
             else "HOLD_CODE_ASSIST_BINDING_OR_POLICY"),
            "code review/generation through existing A2A candidate organ")
        add("remote_code_execution", "NATIVE_CLAW_AND_REMOTE_EXECUTOR",
            ("READY_FOR_D8_EXECUTION_REVIEW" if context_bounded
             and _bool(observed, "native_claw_executor_verified")
             else "HOLD_EXECUTOR_OR_D8_EVIDENCE"),
            "existing authorized device executor; not a model tool-call permission")

    if surface in {"code", "research", "3d"}:
        add("complex_reasoning", "GOOGLE_VERTEX_AI",
            ("CANDIDATE_CLOUD" if cloud_candidate_allowed
             and context_bounded and _bool(observed, "vertex_model_live")
             else "HOLD_VERTEX_BINDING_OR_POLICY"),
            "Google Cloud model candidate, never final authority")

    if surface == "workspace":
        add("workspace_automation", "GEMINI_FOR_GOOGLE_WORKSPACE_STUDIO",
            ("CANDIDATE_WORKSPACE_FLOW" if cloud_candidate_allowed
             and context_bounded and _bool(observed, "workspace_studio_trigger_bound")
             else "HOLD_WORKSPACE_TRIGGER_OR_POLICY"),
            "Workspace workflow trigger, NOT a generic Gemini inference API")

    if surface == "3d":
        add("spatial_action", "EXISTING_3D_CONTROL_ORGAN",
            ("CANDIDATE_3D" if context_bounded
             and _bool(observed, "spatial_control_live")
             else "HOLD_SPATIAL_CONTROL_EVIDENCE"),
            "coordinate/time/semantic control under existing 8D governance")

    if surface == "voice" or voice_requested:
        # Do not silently reroute node 04's voice permission to another device.
        target = resolve_audio_target("taiji04")
        topology_state = target["state"]
        license_verified = _bool(observed, "taiji04_google_voice_commercial_grant_verified")
        voice_interface_verified = _bool(observed, "taiji04_google_tts_interface_verified")
        voice_state = (
            "READY_FOR_D8_VOICE_REVIEW"
            if topology_state == "PASS_AUDIO_TARGET"
            and license_verified and voice_interface_verified and context_bounded
            else topology_state if topology_state.startswith("HOLD_")
            else "HOLD_TAIJI04_TTS_LICENSE_INTERFACE_OR_CONTEXT"
        )
        add("text_to_speech", "TAIJI04_GOOGLE_AUTHORIZED_VOICE",
            voice_state,
            "TTS synthesis/playback on identity-verified authorized node only")
        # Keep Android installed TTS engine separate from Cloud Text-to-Speech entitlement.
        routes[-1]["license_type"] = (
            str(observed.get("taiji04_google_tts_license_type"))
            if license_verified and observed.get("taiji04_google_tts_license_type") in
            {"ANDROID_ENGINE", "GOOGLE_CLOUD_TTS"} else "UNKNOWN"
        )

    held = [r["state"] for r in routes if r["state"].startswith("HOLD_")]
    if not context_bounded:
        held.append("HOLD_CONTEXT_RECEIPT_OR_D8_ENVELOPE_UNVERIFIED")
    return {
        "schema": "W7TP_8D_ADI_MULTIFUNCTION_ROUTE_CANDIDATE_V1",
        "task_ref_sha256": hashlib.sha256(task_ref.encode("utf-8")).hexdigest(),
        "surface": surface,
        "state": "HOLD_REQUIRED_CAPABILITY" if held else "READY_FOR_TOTAL_FIELD_REVIEW",
        "context_receipt_provided": bool(context_receipt_ref),
        "context_bounded_and_verified": context_bounded,
        "cloud_candidate_allowed": cloud_candidate_allowed,
        "routes": routes,
        "held_route_states": held,
        "existing_sources": SOURCES,
        "control_plane": {
            "authority": "TAIJI01_TOTAL_FIELD_ONLY",
            "dynamic_state_field": "W7TP_8D_ADI_V2_3_SINGLE_COUPLED_FIELD",
            "context_binding": "TASK_AND_MODEL_BOUNDED_VERIFIED_DYNAMIC_CONTEXT",
            "model_output_role": "NON_AUTHORITATIVE_COMPUTATION_CANDIDATE",
            "local_llm": "COMPUTE_ONLY_NO_EFFECT_AUTHORITY",
            "cloud_llm": "COMPUTE_ONLY_NO_EFFECT_AUTHORITY",
            "native_claw": "TOTAL_FIELD_CONTROLLED_EXECUTION_ORGAN",
            "execution_condition": "EXISTING_D8_SEALED_ENVELOPE_AND_LIVE_TASK_EFFECT_GATE",
            "d8_verifier_source": "tools/total_field/w7tp_d8_reviewer_entrypoint.py",
            "d8_envelope_reference": d8_envelope_ref or None,
            "sealed_execution_granted": False,
            "no_model_generated_authority": True,
            "no_node_self_authority": True,
            "no_cross_task_envelope_reuse": True,
            "no_automatic_canonical_promotion": True,
        },
        "model_call_performed": False,
        "remote_action_performed": False,
        "cloud_call_performed": False,
        "tts_performed": False,
        "execution_authorized": False,
        "canonical_promotion": False,
        "note": "Only live evidence and D8 control may activate route effects; this output is not authority.",
    }

def build_adi_distribution_candidate(
    *,
    task_ref: str,
    semantic_candidate: Mapping[str, Any],
    resource_arbitration: Mapping[str, Any],
    recipient_contexts: Mapping[str, Any],
    requested_resource_ids: list[str],
    d6_required: bool = False,
    d6_state_packet: Mapping[str, Any] | None = None,
    cloud_model_origin_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Taiji01-only read-only dispatch projection from existing ADI/broker results.

    Does not itself classify the founder's intent, issue a context pull, transfer a
    cell, contact a model/node, or grant a D8 envelope. ADI arbitration and actual
    pointer-first model context pull remain owned by existing Total Field organs.
    """
    from tools.total_field_dynamic_context_pull import (
        RESULT_SCHEMA, canonical_sha256, validate_model_visible_context,
    )

    holds: list[str] = []
    recipients: list[dict[str, Any]] = []
    task = str(task_ref).strip()
    semantic = dict(semantic_candidate) if isinstance(semantic_candidate, Mapping) else {}
    arbitration = dict(resource_arbitration) if isinstance(resource_arbitration, Mapping) else {}
    source_valid = bool(
        task and semantic.get("task_ref") == task
        and semantic.get("producer") == "MSI_LOCAL_LLM"
        and semantic.get("authority") == "CANDIDATE_ONLY"
    )
    if not source_valid:
        holds.append("HOLD_LOCAL_SEMANTIC_CANDIDATE_TASK_OR_ORIGIN")
    if (
        arbitration.get("STATE") != "PASS_RESOURCE_ARBITRATION"
        or (arbitration.get("RESOURCE_ROUTER") or {}).get("FORMAL_EFFECT_BOUNDARY")
        != "TAIJI01_TOTAL_FIELD"
    ):
        holds.append("HOLD_TOTAL_FIELD_ADI_ARBITRATION_EVIDENCE")

    resources = {
        r.get("RESOURCE_ID"): r for r in arbitration.get("RESOURCE_COORDINATES", [])
        if isinstance(r, dict) and isinstance(r.get("RESOURCE_ID"), str)
    }
    available = set(arbitration.get("AVAILABLE_SET", []))
    qualified = set(arbitration.get("QUALIFIED_SET", []))
    preferred = set(arbitration.get("PREFERRED_SET", []))
    if not requested_resource_ids:
        holds.append("HOLD_NO_RESOURCE_SELECTED_BY_TOTAL_FIELD")
    if len(requested_resource_ids) != len(set(requested_resource_ids)):
        holds.append("HOLD_DUPLICATE_RESOURCE_SELECTION")

    for rid in dict.fromkeys(requested_resource_ids):
        r = resources.get(rid, {})
        node = r.get("NODE", "UNKNOWN")
        state = str(r.get("CURRENT_STATE", "UNKNOWN"))
        entry = {
            "resource_id": rid,
            "node_coordinate": node,
            "context_location": r.get("CONTEXT_LOCATION", "UNKNOWN"),
            "model_or_service": r.get("MODEL_OR_SERVICE", "UNKNOWN"),
            "preferred_by_adi": rid in preferred,
            "context_ref": None,
            "packet_ref": None,
            "pull_result_sha256": None,
            "context_delivery": "HOLD",
            "authority": "NONE",
        }
        # Registered resources are not necessarily live and callable.
        if rid not in available or rid not in qualified or not state.startswith("AVAILABLE"):
            entry["hold"] = "HOLD_RESOURCE_NOT_LIVE_QUALIFIED"
        else:
            binding = recipient_contexts.get(rid, {})
            result = binding.get("pull_result", {}) if isinstance(binding, Mapping) else {}
            if not isinstance(result, Mapping) or result.get("schema_version") != RESULT_SCHEMA:
                entry["hold"] = "HOLD_TARGET_CONTEXT_PULL_MISSING"
            elif (
                binding.get("task_ref") != task
                or binding.get("resource_id") != rid
                or result.get("task_ref") != task
                or binding.get("provider_ref") is None
                or binding.get("model_ref") is None
                or result.get("authority", {}).get("candidate_only") is not True
                or result.get("authority", {}).get("model_authority") is not False
                or result.get("persistence_policy", {}).get("full_state_persistence_allowed") is not False
                or result.get("persistence_policy", {}).get("credential_persistence_allowed") is not False
            ):
                entry["hold"] = "HOLD_CONTEXT_BINDING_OR_AUTHORITY_MISMATCH"
            else:
                try:
                    context = validate_model_visible_context(result["model_visible_context"])
                    transmitted_hash = result["pull_result_sha256"]
                    hash_basis = {k: v for k, v in result.items() if k != "pull_result_sha256"}
                    if canonical_sha256(hash_basis) != transmitted_hash:
                        raise ValueError("PULL_RESULT_HASH_MISMATCH")
                    if context.get("context_ref") != result["persistent_refs"]["context_ref"]:
                        raise ValueError("CONTEXT_REF_MISMATCH")
                    entry.update({
                        "context_ref": context["context_ref"],
                        "packet_ref": result["persistent_refs"]["packet_ref"],
                        "pull_result_sha256": transmitted_hash,
                        "context_delivery": "BOUND_REFERENCE_CANDIDATE",
                        "authority": "CANDIDATE_ONLY",
                        "needs_total_field_runtime_reverification": True,
                    })
                except (KeyError, TypeError, ValueError):
                    entry["hold"] = "HOLD_CONTEXT_PULL_RECEIPT_INVALID"
        if "hold" in entry:
            holds.append(f"{rid}:{entry['hold']}")
        recipients.append(entry)

    d6 = {"mode": "NOT_REQUIRED", "packet_ref": None,
          "transmitted": False, "reconstructed": False,
          "full_effect_cost_verified": False}
    if d6_required:
        packet = dict(d6_state_packet) if isinstance(d6_state_packet, Mapping) else {}
        packet_ref = packet.get("packet_ref")
        packet_sha = packet.get("packet_sha256")
        deps = packet.get("dependency_refs")
        target = packet.get("target_resource_id")
        # A proposed rule packet is not a completed transfer or reconstruction.
        if (not isinstance(packet_ref, str) or not packet_ref
                or not isinstance(packet_sha, str) or len(packet_sha) != 64
                or not isinstance(deps, list) or not deps
                or target not in requested_resource_ids):
            holds.append("HOLD_D6_PACKET_OR_RECONSTRUCTION_DEPENDENCIES")
        d6 = {
            "mode": "D6_ORIGIN_STATE_RECONSTRUCTION_CANDIDATE",
            "packet_ref": packet_ref if isinstance(packet_ref, str) else None,
            "target_resource_id": target,
            "dependency_refs": deps if isinstance(deps, list) else [],
            "transmitted": False,
            "reconstructed": False,
            "full_effect_cost_verified": False,
            "local_rule_and_prior_costs_required": True,
        }

    cloud_origin = {
        "mode": "NOT_REQUESTED",
        "owner": "TAIJI01_TOTAL_FIELD",
        "model_internal_state_access": False,
        "packet_pulled": False,
        "reconstruction_verified": False,
    }
    if cloud_model_origin_packet is not None:
        cloud_packet = (dict(cloud_model_origin_packet)
                        if isinstance(cloud_model_origin_packet, Mapping) else {})
        source = cloud_packet.get("source_resource_id")
        ref = cloud_packet.get("packet_ref")
        sha = cloud_packet.get("packet_sha256")
        deps = cloud_packet.get("dependency_refs")
        contract = cloud_packet.get("origin_state_contract_ref")
        valid = bool(
            cloud_packet.get("semantic_class") == "CLOUD_MODEL_OUTPUT_ORIGIN_STATE_CANDIDATE"
            and cloud_packet.get("task_ref") == task
            and source in requested_resource_ids
            and source in qualified
            and source in {"GOOGLE_VERTEX_GEMINI", "GEMINI_CODE_ASSIST", "OLLAMA_CLOUD"}
            and isinstance(ref, str) and ref
            and isinstance(sha, str) and len(sha) == 64
            and isinstance(deps, list) and deps
            and isinstance(contract, str) and contract
            and cloud_packet.get("model_internal_state_access") is False
        )
        if not valid:
            holds.append("HOLD_CLOUD_ORIGIN_PACKET_SCOPE_OR_DEPENDENCIES")
        cloud_origin = {
            "mode": ("CANDIDATE_CLOUD_ORIGIN_PACKET_FOR_TOTAL_FIELD_PULL"
                     if valid else "HOLD_CLOUD_ORIGIN_PACKET_SCOPE_OR_DEPENDENCIES"),
            "owner": "TAIJI01_TOTAL_FIELD",
            "source_resource_id": source,
            "packet_ref": ref if isinstance(ref, str) else None,
            "origin_state_contract_ref": contract if isinstance(contract, str) else None,
            "model_internal_state_access": False,
            "packet_pulled": False,
            "reconstruction_verified": False,
        }

    return {
        "schema": "W7TP_8D_ADI_ADI_RESOURCE_CONTEXT_DISTRIBUTION_CANDIDATE_V1",
        "task_ref": task,
        "semantic_stage": "MSI_LOCAL_LLM_TO_TOTAL_FIELD_INSTRUCTION_CANDIDATE",
        "semantic_candidate_authority": False,
        "decision_owner": "TAIJI01_8D_ADI_TOTAL_FIELD",
        "resource_mapping_source": "core/resource_arbitration.py",
        "context_pull_source": "tools/total_field_dynamic_context_pull.py",
        "d6_transport_source": "services/w7tp_gst_v23_runtime.py",
        "model_internal_state_pulled": False,
        "routine_model_inference_is_d6": False,
        "recipients": recipients,
        "d6": d6,
        "cloud_origin_packet_pull": cloud_origin,
        "holds": holds,
        "state": "HOLD_CONTEXT_OR_RESOURCE" if holds else "READY_FOR_D8_REVIEW_CANDIDATE_ONLY",
        "remote_dispatch_executed": False,
        "cloud_inference_executed": False,
        "execution_authorized": False,
        "canonical_promotion": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="8D ADI read-only multi-capability route candidate")
    parser.add_argument("--task-ref", required=True)
    parser.add_argument("--surface", required=True, choices=sorted(SURFACES))
    parser.add_argument("--observed-json", help="Existing live-evidence flags as JSON, no secrets")
    parser.add_argument("--context-receipt-ref", default="")
    parser.add_argument("--d8-envelope-ref", default="")
    parser.add_argument("--cloud-candidate-allowed", action="store_true")
    parser.add_argument("--voice-requested", action="store_true")
    args = parser.parse_args()
    observed = json.loads(Path(args.observed_json).read_text("utf-8")) if args.observed_json else {}
    result = build_candidate(
        task_ref=args.task_ref, surface=args.surface, observed=observed,
        context_receipt_ref=args.context_receipt_ref,
        d8_envelope_ref=args.d8_envelope_ref,
        cloud_candidate_allowed=args.cloud_candidate_allowed,
        voice_requested=args.voice_requested,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["state"] == "READY_FOR_TOTAL_FIELD_REVIEW" else 2

if __name__ == "__main__":
    raise SystemExit(main())
