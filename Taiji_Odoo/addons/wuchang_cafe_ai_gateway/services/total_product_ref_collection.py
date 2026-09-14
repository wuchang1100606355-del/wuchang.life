"""Total product ref collection helpers.

This service normalizes human-filled refs for the XiaoJ total product handoff.
It accepts refs only and performs no external API calls, no DB writes, no
message sends, no POS writes, no payment captures, no secret reads, and no
member or resident plaintext reads.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from .line_official_account_config import REQUIRED_LINE_OFFICIAL_REFS
from .line_official_account_refs import build_line_official_account_refs_draft
from .lineworks_release_refs import (
    REQUIRED_CONNECTOR_REFS,
    REQUIRED_RELEASE_REFS,
    build_lineworks_release_refs_draft,
)
from .p1_intent_engine import FORMAL_RELEASE_GATES, RELEASE_REF_VERIFIER_ALLOWLIST


MERCHANT_FORMAL_GATES = ["member_registration", "pos_order", "payment"]
ASSOCIATION_SOVEREIGN_MEMBER_REFS = [
    "member_identity_ref",
    "member_consent_ref",
    "sovereign_xiaoj_claim_ref",
    "delegate_rotation_ref",
    "gemini_key_ref_vault_binding",
    "member_llm_release_ref",
]
RESIDENT_PROPERTY_REFS = [
    "resident_ref",
    "unit_ref",
    "role_ref",
    "facility_ref",
    "repair_or_service_case_ref",
    "resident_unit_role_policy_ref",
    "property_action_approval_ref",
    "resident_plaintext_redaction_verifier_ref",
]
SAFE_REF_PATTERN = re.compile(r"[A-Z0-9_:-]{6,180}")
HEX64_PATTERN = re.compile(r"[a-f0-9]{64}")
JWT_SHAPE_PATTERN = re.compile(r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}")
LONG_TOKEN_SHAPE_PATTERN = re.compile(r"(?=.*[A-Za-z])(?=.*[0-9])[A-Za-z0-9_~+/=-]{40,}")


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def has_secret_or_plaintext_shape(value: Any) -> bool:
    text = str(value or "")
    return bool(
        re.search(r"sk-[A-Za-z0-9_-]{12,}", text)
        or re.search(r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+", text)
        or re.search(r"(?i)channel_secret\s*[:=]\s*\S+", text)
        or re.search(r"(?i)client_secret\s*[:=]\s*\S+", text)
        or re.search(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----", text)
        or re.search(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}", text)
        or re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
        or re.search(r"09\d{2}[- ]?\d{3}[- ]?\d{3}", text)
        or re.search(r"\b[A-Z][12]\d{8}\b", text)
        or JWT_SHAPE_PATTERN.search(text)
        or LONG_TOKEN_SHAPE_PATTERN.search(text)
    )


def is_placeholder_ref(value: Any) -> bool:
    text = str(value or "")
    return (
        not text
        or text.startswith("REF_")
        or text.endswith("_TO_FILL")
        or text.endswith("_NO_SECRET")
        or text.endswith("_NO_MEMBER_PLAINTEXT")
        or text.endswith("_NO_TOKEN_VALUE")
        or "PLACEHOLDER" in text
        or text == "0" * 64
    )


def is_safe_ref(value: Any) -> bool:
    text = str(value or "").strip()
    return (
        (HEX64_PATTERN.fullmatch(text.lower()) is not None or ("REF" in text and SAFE_REF_PATTERN.fullmatch(text) is not None))
        and text == str(value or "")
        and not has_secret_or_plaintext_shape(text)
    )


def is_safe_packet_hash(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return bool(HEX64_PATTERN.fullmatch(text)) and text != "0" * 64


def _assert_no_secret_leaf_values(value: Any, path: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"schema", "state", "usage"}:
                continue
            _assert_no_secret_leaf_values(child, f"{path}.{key}" if path else str(key))
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_secret_leaf_values(child, f"{path}[{index}]")
        return
    if isinstance(value, (bool, int, float)) or value is None:
        return
    if has_secret_or_plaintext_shape(value):
        raise ValueError(f"secret-shaped or plaintext-shaped material is not allowed in total product ref collection:{path}")


def _side_effects_false() -> dict:
    return {
        "external_api_call": False,
        "formal_lineworks_send": False,
        "formal_line_message_send": False,
        "official_account_setting_changed": False,
        "formal_member_registration": False,
        "formal_db_write": False,
        "formal_pos_write": False,
        "payment_capture": False,
        "secret_read": False,
        "member_plaintext_read": False,
        "resident_plaintext_read": False,
        "raw_audio_saved": False,
        "raw_video_saved": False,
        "deploy": False,
        "service_restart": False,
    }


def _placeholder_name(prefix: str, key: str) -> str:
    stem = key.upper()
    if stem.endswith("_REF"):
        stem = stem[:-4]
    return f"REF_{prefix}_{stem}_TO_FILL" if prefix else f"REF_{stem}_TO_FILL"


def _release_ref_template(prefix: str, key: str) -> dict:
    return {
        "ref": _placeholder_name(prefix, key),
        "packet_hash": "0" * 64,
        "verifier": "total_field_release_registry",
        "verified": False,
    }


def build_total_product_ref_collection_input_template() -> dict:
    """Build a human-fillable refs-only template for Odoo/API/CLI operators."""

    return {
        "schema": "W7TP_XIAOJ_TOTAL_PRODUCT_REF_COLLECTION_INPUT_V1",
        "state": "TEMPLATE_REQUIRES_HUMAN_FILLED_REFS",
        "usage": (
            "Fill refs only. Do not paste LINE, LINE WORKS, Google, Odoo, POS, payment, router, "
            "member, resident, raw audio, or raw video plaintext/secrets."
        ),
        "lineworks": {
            "lineworks_send": {
                key: _release_ref_template("LINEWORKS", key)
                for key in REQUIRED_RELEASE_REFS
            },
            "connector_refs": {
                "lineworks_bot_ref": "REF_LINEWORKS_BOT_RUNTIME_TO_FILL",
                "lineworks_target_user_ref": "REF_LINEWORKS_TARGET_RUNTIME_TO_FILL",
                "lineworks_access_token_runtime_ref": "REF_LINEWORKS_ACCESS_TOKEN_RUNTIME_PROVIDER_TO_FILL",
            },
        },
        "line_official_account": {
            "refs": {
                key: _placeholder_name("", key)
                for key in REQUIRED_LINE_OFFICIAL_REFS
            }
        },
        "merchant_formal_release": {
            gate_id: {
                key: _release_ref_template(
                    {
                        "member_registration": "MEMBER",
                        "pos_order": "POS",
                        "payment": "PAYMENT",
                    }[gate_id],
                    key,
                )
                for key in FORMAL_RELEASE_GATES[gate_id]["required_refs"]
            }
            for gate_id in MERCHANT_FORMAL_GATES
        },
        "association_sovereign_member": {
            key: _placeholder_name("", key)
            for key in ASSOCIATION_SOVEREIGN_MEMBER_REFS
        },
        "resident_property_management": {
            key: _placeholder_name("", key)
            for key in RESIDENT_PROPERTY_REFS
        },
    }


def _release_ref(raw_refs: dict, key: str, allow_verified: bool) -> tuple[dict, list[str]]:
    raw_value = raw_refs.get(key) if isinstance(raw_refs, dict) else None
    if isinstance(raw_value, dict):
        ref = {
            "ref": str(raw_value.get("ref") or "").strip(),
            "packet_hash": str(raw_value.get("packet_hash") or "").strip().lower(),
            "verifier": str(raw_value.get("verifier") or "total_field_manual_release_packet").strip(),
            "verified": raw_value.get("verified") is True,
        }
    elif raw_value:
        ref = {
            "ref": str(raw_value).strip(),
            "packet_hash": "",
            "verifier": "total_field_manual_release_packet",
            "verified": False,
        }
    else:
        ref = {
            "ref": f"REF_{key.upper()}_TO_FILL",
            "packet_hash": "0" * 64,
            "verifier": "total_field_manual_release_packet",
            "verified": False,
        }
    warnings = []
    if not is_safe_ref(ref["ref"]) or is_placeholder_ref(ref["ref"]):
        warnings.append(f"unsafe_or_placeholder_release_ref:{key}")
        ref["verified"] = False
    if not is_safe_packet_hash(ref["packet_hash"]):
        warnings.append(f"missing_or_placeholder_packet_hash:{key}")
        ref["verified"] = False
    if ref["verifier"] not in RELEASE_REF_VERIFIER_ALLOWLIST:
        warnings.append(f"verifier_not_allowlisted:{key}")
        ref["verified"] = False
    if not allow_verified:
        ref["verified"] = False
        if is_safe_ref(ref["ref"]) and is_safe_packet_hash(ref["packet_hash"]):
            warnings.append(f"verified_flag_requires_allow_verified:{key}")
    return ref, warnings


def _normalize_formal_release_refs(raw: dict, allow_verified: bool) -> tuple[dict, list[str]]:
    raw = raw if isinstance(raw, dict) else {}
    normalized = {}
    warnings = []
    for gate_id in MERCHANT_FORMAL_GATES:
        gate_input = raw.get(gate_id) if isinstance(raw.get(gate_id), dict) else {}
        gate_refs = {}
        for key in FORMAL_RELEASE_GATES[gate_id]["required_refs"]:
            ref, ref_warnings = _release_ref(gate_input, key, allow_verified)
            gate_refs[key] = ref
            warnings.extend(f"{gate_id}:{warning}" for warning in ref_warnings)
        normalized[gate_id] = gate_refs
    return normalized, warnings


def _normalize_ref_group(raw: dict, required_keys: list[str], label: str) -> tuple[dict, list[str]]:
    raw = raw if isinstance(raw, dict) else {}
    normalized = {}
    warnings = []
    for key in required_keys:
        value = str(raw.get(key) or f"REF_{key.upper()}_TO_FILL").strip()
        normalized[key] = value
        if is_placeholder_ref(value):
            warnings.append(f"placeholder_ref:{label}:{key}")
        if not is_safe_ref(value):
            warnings.append(f"unsafe_ref:{label}:{key}")
        if has_secret_or_plaintext_shape(value):
            warnings.append(f"secret_or_plaintext_shape:{label}:{key}")
    return normalized, warnings


def _lineworks_input(raw: dict) -> tuple[dict, dict]:
    raw = raw if isinstance(raw, dict) else {}
    if isinstance(raw.get("lineworks"), dict):
        raw = raw["lineworks"]
    release_refs = raw.get("lineworks_send") if isinstance(raw.get("lineworks_send"), dict) else raw
    connector_refs = raw.get("connector_refs") if isinstance(raw.get("connector_refs"), dict) else {}
    return release_refs, connector_refs


def _release_ref_check(group: str, key: str, ref: dict) -> dict:
    blockers = []
    ref_value = str((ref or {}).get("ref") or "").strip()
    packet_hash = str((ref or {}).get("packet_hash") or "").strip().lower()
    verifier = str((ref or {}).get("verifier") or "").strip()
    if not is_safe_ref(ref_value) or is_placeholder_ref(ref_value):
        blockers.append("fill_safe_opaque_ref")
    if not is_safe_packet_hash(packet_hash):
        blockers.append("fill_verified_packet_hash")
    if verifier not in RELEASE_REF_VERIFIER_ALLOWLIST:
        blockers.append("use_allowlisted_verifier")
    if (ref or {}).get("verified") is not True:
        blockers.append("set_verified_true_after_human_review")
    return {
        "group": group,
        "field": key,
        "value_class": "release_ref",
        "required": True,
        "status": "READY" if not blockers else "NEEDS_HUMAN_FILL",
        "blockers": blockers,
        "next_action": "none" if not blockers else "fill_ref_packet_hash_verifier_and_verified_flag",
    }


def _plain_ref_check(group: str, key: str, value: Any) -> dict:
    text = str(value or "").strip()
    blockers = []
    if not is_safe_ref(text) or is_placeholder_ref(text):
        blockers.append("fill_safe_opaque_ref")
    return {
        "group": group,
        "field": key,
        "value_class": "safe_ref",
        "required": True,
        "status": "READY" if not blockers else "NEEDS_HUMAN_FILL",
        "blockers": blockers,
        "next_action": "none" if not blockers else "fill_safe_opaque_ref",
    }


def _build_human_fill_checklist(
    *,
    lineworks: dict,
    line_official: dict,
    formal_release_refs: dict,
    association_refs: dict,
    resident_refs: dict,
) -> list[dict]:
    checklist = []
    for key, ref in (lineworks.get("lineworks_send", {}) or {}).items():
        checklist.append(_release_ref_check("lineworks_send", key, ref if isinstance(ref, dict) else {}))
    for key in REQUIRED_CONNECTOR_REFS:
        checklist.append(
            _plain_ref_check(
                "lineworks_connector_refs",
                key,
                (lineworks.get("connector_refs", {}) or {}).get(key),
            )
        )
    for key in REQUIRED_LINE_OFFICIAL_REFS:
        checklist.append(
            _plain_ref_check(
                "line_official_account",
                key,
                (line_official.get("refs", {}) or {}).get(key),
            )
        )
    for gate_id in MERCHANT_FORMAL_GATES:
        gate_refs = formal_release_refs.get(gate_id, {}) if isinstance(formal_release_refs.get(gate_id), dict) else {}
        for key in FORMAL_RELEASE_GATES[gate_id]["required_refs"]:
            checklist.append(_release_ref_check(f"merchant_formal_release.{gate_id}", key, gate_refs.get(key, {})))
    for key in ASSOCIATION_SOVEREIGN_MEMBER_REFS:
        checklist.append(_plain_ref_check("association_sovereign_member", key, association_refs.get(key)))
    for key in RESIDENT_PROPERTY_REFS:
        checklist.append(_plain_ref_check("resident_property_management", key, resident_refs.get(key)))
    return checklist


def _operator_fill_summary(checklist: list[dict]) -> dict:
    by_group: dict[str, dict[str, int]] = {}
    for item in checklist:
        group = item.get("group", "unknown")
        group_summary = by_group.setdefault(group, {"required": 0, "ready": 0, "needs_human_fill": 0})
        group_summary["required"] += 1
        if item.get("status") == "READY":
            group_summary["ready"] += 1
        else:
            group_summary["needs_human_fill"] += 1
    needs = [item for item in checklist if item.get("status") != "READY"]
    return {
        "total_required": len(checklist),
        "ready_count": len(checklist) - len(needs),
        "needs_human_fill_count": len(needs),
        "all_ready": not needs,
        "groups": by_group,
        "next_required_groups": sorted({item.get("group", "unknown") for item in needs}),
    }


def _operator_fill_worksheet_md(checklist: list[dict], summary: dict) -> str:
    lines = [
        "# XiaoJ Total Product Ref Fill Worksheet",
        "",
        f"STATE: {'READY_FOR_HANDOFF_CANDIDATE' if summary.get('all_ready') else 'HOLD_NEEDS_HUMAN_FILL'}",
        f"TOTAL_REQUIRED: {summary.get('total_required', 0)}",
        f"READY_COUNT: {summary.get('ready_count', 0)}",
        f"NEEDS_HUMAN_FILL_COUNT: {summary.get('needs_human_fill_count', 0)}",
        "",
        "BOUNDARY: refs only. Do not paste passwords, token values, API keys, member plaintext, resident plaintext, payment card data, raw audio, or raw video.",
        "",
    ]
    groups = summary.get("groups", {}) if isinstance(summary.get("groups"), dict) else {}
    for group in sorted(groups):
        group_items = [item for item in checklist if item.get("group") == group]
        group_summary = groups[group]
        lines.extend(
            [
                f"## {group}",
                "",
                f"required={group_summary.get('required', 0)} ready={group_summary.get('ready', 0)} needs_human_fill={group_summary.get('needs_human_fill', 0)}",
                "",
                "| Field | Value class | Status | Required action |",
                "| --- | --- | --- | --- |",
            ]
        )
        for item in group_items:
            blockers = ",".join(item.get("blockers", [])) if item.get("blockers") else "none"
            action = item.get("next_action") or blockers
            lines.append(
                f"| {item.get('field', '')} | {item.get('value_class', '')} | {item.get('status', '')} | {action} |"
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_total_product_ref_collection_draft(refs: dict | None = None, allow_verified: bool = False) -> dict:
    refs = refs if isinstance(refs, dict) else {}
    _assert_no_secret_leaf_values(refs)

    lineworks_release_refs, lineworks_connector_refs = _lineworks_input(refs.get("lineworks") if isinstance(refs.get("lineworks"), dict) else {})
    lineworks = build_lineworks_release_refs_draft(
        release_refs=lineworks_release_refs,
        connector_refs=lineworks_connector_refs,
        allow_verified=allow_verified,
    )
    line_official_input = refs.get("line_official_account") if isinstance(refs.get("line_official_account"), dict) else {}
    line_official = build_line_official_account_refs_draft(
        line_official_input.get("refs") if isinstance(line_official_input.get("refs"), dict) else line_official_input
    )
    formal_release_refs, formal_warnings = _normalize_formal_release_refs(
        refs.get("merchant_formal_release") if isinstance(refs.get("merchant_formal_release"), dict) else {},
        allow_verified,
    )
    association_refs, association_warnings = _normalize_ref_group(
        refs.get("association_sovereign_member") if isinstance(refs.get("association_sovereign_member"), dict) else {},
        ASSOCIATION_SOVEREIGN_MEMBER_REFS,
        "association_sovereign_member",
    )
    resident_refs, resident_warnings = _normalize_ref_group(
        refs.get("resident_property_management") if isinstance(refs.get("resident_property_management"), dict) else {},
        RESIDENT_PROPERTY_REFS,
        "resident_property_management",
    )
    warnings = []
    warnings.extend(f"lineworks:{warning}" for warning in lineworks.get("draft_warnings", []))
    warnings.extend(f"line_official_account:{warning}" for warning in line_official.get("draft_warnings", []))
    warnings.extend(formal_warnings)
    warnings.extend(association_warnings)
    warnings.extend(resident_warnings)
    formal_ready = all(
        ref.get("verified") is True
        for gate_refs in formal_release_refs.values()
        for ref in gate_refs.values()
    )
    ready = (
        not warnings
        and lineworks.get("state") == "RELEASE_REFS_DRAFT_READY_FOR_READINESS_CHECK"
        and line_official.get("state") == "LINE_OFFICIAL_ACCOUNT_REFS_READY_FOR_CONFIG_CANDIDATE"
        and formal_ready
    )
    human_fill_checklist = _build_human_fill_checklist(
        lineworks=lineworks,
        line_official=line_official,
        formal_release_refs=formal_release_refs,
        association_refs=association_refs,
        resident_refs=resident_refs,
    )
    operator_fill_summary = _operator_fill_summary(human_fill_checklist)
    operator_fill_worksheet_md = _operator_fill_worksheet_md(human_fill_checklist, operator_fill_summary)
    handoff_inputs = {
        "formal_release_refs": formal_release_refs,
        "lineworks_refs": {
            "lineworks_send": lineworks.get("lineworks_send", {}),
            "connector_refs": lineworks.get("connector_refs", {}),
        },
        "line_official_account_refs": {"refs": line_official.get("refs", {})},
    }
    draft_seed = {
        "lineworks": lineworks.get("draft_hash", ""),
        "line_official": line_official.get("draft_hash", ""),
        "formal_release_refs": formal_release_refs,
        "association_refs": association_refs,
        "resident_refs": resident_refs,
        "warnings": warnings,
        "operator_fill_summary": operator_fill_summary,
    }
    return {
        "schema": "W7TP_XIAOJ_TOTAL_PRODUCT_REF_COLLECTION_DRAFT_V1",
        "state": "TOTAL_PRODUCT_REFS_READY_FOR_HANDOFF_CANDIDATE" if ready else "HOLD_TOTAL_PRODUCT_REF_COLLECTION_DRAFT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "usage": "Refs only. Do not paste tokens, passwords, API keys, member plaintext, resident plaintext, payment data, raw audio, or raw video.",
        "allow_verified_input": allow_verified,
        "lineworks": lineworks,
        "line_official_account": line_official,
        "merchant_formal_release": formal_release_refs,
        "association_sovereign_member": association_refs,
        "resident_property_management": resident_refs,
        "handoff_inputs": handoff_inputs,
        "human_fill_checklist": human_fill_checklist,
        "operator_fill_summary": operator_fill_summary,
        "operator_fill_worksheet_md": operator_fill_worksheet_md,
        "draft_warnings": warnings,
        "ready_for_handoff_candidate": ready,
        "draft_hash": stable_hash(draft_seed),
        "side_effects": _side_effects_false(),
    }
