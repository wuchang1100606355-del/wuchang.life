"""LINE WORKS operator handoff pack helper."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .lineworks_activation import build_lineworks_runtime_activation_packet
from .lineworks_connector import (
    REQUIRED_CONNECTOR_REFS,
    build_lineworks_execution_envelope_export,
    build_lineworks_send_preflight,
    execute_lineworks_send_envelope,
)
from .lineworks_release_refs import build_lineworks_release_refs_draft
from .p1_intent_engine import FORMAL_RELEASE_GATES, formal_release_status_payload, lineworks_notify_payload


def _is_placeholder_ref(value: Any) -> bool:
    text = str(value or "")
    return (
        not text
        or text.startswith("REF_")
        or text.endswith("_NO_SECRET")
        or text.endswith("_NO_MEMBER_PLAINTEXT")
        or text.endswith("_NO_TOKEN_VALUE")
        or text == "0" * 64
    )


def _release_ref_readiness(refs: dict, required_refs: list[str]) -> dict:
    gate_refs = refs.get("lineworks_send") if isinstance(refs.get("lineworks_send"), dict) else {}
    missing = [key for key in required_refs if key not in gate_refs]
    unverified = []
    placeholders = []
    for key in required_refs:
        value = gate_refs.get(key) if isinstance(gate_refs, dict) else None
        if not isinstance(value, dict):
            continue
        if value.get("verified") is not True:
            unverified.append(key)
        if _is_placeholder_ref(value.get("ref")) or _is_placeholder_ref(value.get("packet_hash")):
            placeholders.append(key)
    return {
        "missing_release_refs": missing,
        "unverified_release_refs": unverified,
        "placeholder_release_refs": placeholders,
    }


def _connector_ref_readiness(refs: dict, required_connector_refs: list[str]) -> dict:
    connector_refs = refs.get("connector_refs") if isinstance(refs.get("connector_refs"), dict) else {}
    missing = [key for key in required_connector_refs if not connector_refs.get(key)]
    placeholders = [key for key in required_connector_refs if _is_placeholder_ref(connector_refs.get(key))]
    return {
        "connector_refs": connector_refs,
        "missing_connector_refs": missing,
        "placeholder_connector_refs": placeholders,
    }


def _next_actions(readiness: dict, draft: dict, activation: dict, dry_run: dict) -> list[str]:
    actions = []
    if readiness.get("missing_release_refs"):
        actions.append("fill_missing_lineworks_release_refs")
    if readiness.get("unverified_release_refs") or readiness.get("placeholder_release_refs"):
        actions.append("replace_placeholder_refs_with_verified_objects_and_64hex_packet_hashes")
    if readiness.get("missing_connector_refs") or readiness.get("placeholder_connector_refs"):
        actions.append("prepare_safe_connector_refs_without_tokens_or_member_plaintext")
    if readiness.get("unsafe_connector_ref_keys") or readiness.get("unsafe_connector_ref_shape_keys"):
        actions.append("remove_secret_or_raw_connector_ref_values")
    if draft.get("draft_warnings"):
        actions.append("resolve_release_refs_draft_warnings")
    if activation.get("draft_warnings"):
        actions.append("provide_safe_operator_ref_and_non_placeholder_execution_envelope_hash")
    if dry_run.get("dry_run_ready") is not True:
        actions.append("rerun_runtime_dry_run_after_release_refs_and_activation_are_ready")
    if not actions:
        actions.append("handoff_pack_ready_for_human_activation_review")
    return actions


def build_lineworks_operator_handoff_pack(
    refs: dict | None = None,
    refs_path: str = "",
    message: Any = "LINE WORKS 操作交接包候選通知",
    target_ref: Any = "TARGET_REF_HANDOFF_CHECK",
    actor_ref: Any = "ACTOR_REF_HANDOFF_CHECK",
    operator_ref: Any = "OPERATOR_REF_HANDOFF_CHECK",
    channel: Any = "member_service",
    confirm_human_activation: bool = False,
) -> dict:
    refs = refs if isinstance(refs, dict) else {}
    draft = build_lineworks_release_refs_draft(
        release_refs=refs.get("lineworks_send", refs),
        connector_refs=refs.get("connector_refs", {}),
        allow_verified=True,
    )
    required_release_refs = list(FORMAL_RELEASE_GATES["lineworks_send"]["required_refs"])
    release_readiness = _release_ref_readiness(refs, required_release_refs)
    connector_readiness = _connector_ref_readiness(refs, REQUIRED_CONNECTOR_REFS)
    candidate = lineworks_notify_payload(message, target_ref, channel, actor_ref)
    release_status = formal_release_status_payload({"lineworks_send": refs.get("lineworks_send", {})})
    preflight = build_lineworks_send_preflight(candidate, release_status, connector_readiness["connector_refs"])
    envelope = build_lineworks_execution_envelope_export(
        candidate,
        release_status,
        connector_readiness["connector_refs"],
        refs_path=refs_path,
    )
    activation = build_lineworks_runtime_activation_packet(
        operator_ref=operator_ref,
        execution_envelope_hash=envelope.get("preflight_envelope_hash", ""),
        candidate_packet_hash=envelope.get("candidate_packet_hash", ""),
        release_packet_hash=envelope.get("preflight_envelope_hash", ""),
        confirm_human_activation=confirm_human_activation,
    )
    dry_run = execute_lineworks_send_envelope(
        envelope,
        runtime_activation=activation.get("runtime_activation", {}),
        enable_external_call=False,
    )
    blockers = []
    for key in ["missing_release_refs", "unverified_release_refs", "placeholder_release_refs"]:
        if release_readiness[key]:
            blockers.append(key)
    for key in ["missing_connector_refs", "placeholder_connector_refs"]:
        if connector_readiness[key]:
            blockers.append(key)
    if preflight.get("unsafe_connector_ref_keys"):
        blockers.append("unsafe_connector_ref_keys")
    if preflight.get("unsafe_connector_ref_shape_keys"):
        blockers.append("unsafe_connector_ref_shape_keys")
    if preflight.get("send_allowed") is not True:
        blockers.append("lineworks_preflight_not_ready")
    readiness = {
        "state": "PASS_LINEWORKS_RELEASE_READINESS" if not blockers else "HOLD_LINEWORKS_RELEASE_READINESS",
        "release_gate_decision": release_status.get("formal_release_gates", {}).get("lineworks_send", {}).get("decision"),
        "release_ready": release_status.get("formal_release_gates", {}).get("lineworks_send", {}).get("release_ready") is True,
        "preflight_state": preflight.get("state"),
        "preflight_send_allowed": preflight.get("send_allowed") is True,
        "blockers": blockers,
        **release_readiness,
        "missing_connector_refs": connector_readiness["missing_connector_refs"],
        "placeholder_connector_refs": connector_readiness["placeholder_connector_refs"],
        "unsafe_connector_ref_keys": preflight.get("unsafe_connector_ref_keys", []),
        "unsafe_connector_ref_shape_keys": preflight.get("unsafe_connector_ref_shape_keys", []),
    }
    actions = _next_actions(readiness, draft, activation, dry_run)
    state = (
        "PASS_LINEWORKS_OPERATOR_HANDOFF_READY_FOR_HUMAN_REVIEW"
        if readiness["state"] == "PASS_LINEWORKS_RELEASE_READINESS" and dry_run.get("dry_run_ready") is True
        else "HOLD_LINEWORKS_OPERATOR_HANDOFF_NEEDS_HUMAN_REFS"
    )
    return {
        "schema": "W7TP_XIAOJ_LINEWORKS_OPERATOR_HANDOFF_PACK_V1",
        "state": state,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "refs_path": str(refs_path or ""),
        "release_refs_draft": {
            "state": draft.get("state"),
            "draft_hash": draft.get("draft_hash"),
            "draft_warnings": draft.get("draft_warnings", []),
        },
        "readiness": readiness,
        "execution_envelope": {
            "state": envelope.get("state"),
            "preflight_envelope_hash": envelope.get("preflight_envelope_hash", ""),
            "candidate_packet_hash": envelope.get("candidate_packet_hash", ""),
            "runtime_send_enabled": envelope.get("runtime_send_enabled") is True,
        },
        "runtime_activation": {
            "state": activation.get("state"),
            "activation_packet_hash": activation.get("activation_packet_hash", ""),
            "draft_warnings": activation.get("draft_warnings", []),
        },
        "runtime_dry_run": {
            "state": dry_run.get("state"),
            "dry_run_ready": dry_run.get("dry_run_ready") is True,
            "external_api_call": dry_run.get("external_api_call") is True,
            "formal_lineworks_send": dry_run.get("formal_lineworks_send") is True,
            "failure_reasons": dry_run.get("failure_reasons", []),
        },
        "operator_next_actions": actions,
        "side_effects": {
            "external_api_call": False,
            "formal_lineworks_send": False,
            "secret_read": False,
            "member_plaintext_read": False,
            "db_write": False,
            "deploy": False,
            "service_restart": False,
        },
    }
