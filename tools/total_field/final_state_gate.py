#!/usr/bin/env python3
"""Final-state Total Field gate for natural-language candidate requests.

This module is a local verifier composition layer. It does not call cloud
services, write databases, deploy, restart services, submit formal filings, or
reveal ADI/H64/TD internals.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.intent_field.adi_5d_absolute_index_verifier import (
    base_pass_packet as base_adi_5d_absolute_index_packet,
    verify_packet as verify_adi_5d_absolute_index_packet,
)
from tools.taiji_8d_canonical_verifier import (
    ALLOW,
    BLOCK,
    HOLD,
    Canonical8DVerifier,
    VerifierConfig,
    VerifierSecrets,
    sign_d7_packet,
)


PASS = "PASS"
STATE = "TOTAL_FIELD_FINAL_STATE_GATE_RESULT"

ALLOWED_7D_FUNCTIONAL_STATES = {
    "NATURAL_LANGUAGE_RESPONSE",
    "INFORMATION_LOOKUP",
    "MENU_EXPLANATION",
    "MEMBER_SUPPORT_CANDIDATE",
    "LINE_CANDIDATE_REPLY",
    "WEB_CANDIDATE_REPLY",
    "ODOO_CANDIDATE_REPLY",
}

GT_FORBIDDEN_CORE_TERMS = (
    "cloud encrypted sync",
    "encrypted cloud sync",
    "cloud sync",
    "file transfer",
    "backup",
    "download-decrypt restore",
    "download and decrypt restore",
    "decrypt restore",
    "檔案搬運",
    "雲端密文同步",
    "雲端同步",
    "備份",
    "下載解密",
)
GT_CORE_MARKERS = (
    "generative transmission",
    "generative_transmission",
    "gt core",
    "gt_core",
    "生成式傳輸",
    "核心",
)
ADI_DRIFT_TERMS = (
    "adi neural network",
    "5d neural network",
    "ordinary json five fields",
    "generic 5d schema",
    "external tensor network",
    "extra tensor network",
    "普通 json 五欄位",
    "神經網路",
    "外掛張量網",
)
HARD_RISK_TERMS = (
    "db write",
    "database write",
    "odoo write",
    "write_to_pos",
    "pos order create",
    "payment capture",
    "deploy",
    "restart",
    "reboot",
    "router write",
    "formal submit",
    "production activation",
    "寫入資料庫",
    "寫入 odoo",
    "寫入 pos",
    "付款扣款",
    "正式送件",
    "部署",
    "重啟",
    "重開",
)
HARD_RISK_FLAGS = (
    "db_write",
    "odoo_write",
    "write_to_pos",
    "payment_capture",
    "deploy",
    "restart",
    "reboot",
    "router_write",
    "formal_submit",
    "production_activation",
)


@dataclass
class InMemoryNonceLedger:
    """Nonce ledger compatible with Canonical8DVerifier without SQLite writes."""

    used: set[str] = field(default_factory=set)

    def cleanup(self, _now: float) -> None:
        return None

    def mark_used_or_replay(self, nonce: str, _packet_hash: str, _now: float, _ttl_seconds: int) -> bool:
        if nonce in self.used:
            return False
        self.used.add(nonce)
        return True


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def hash_ref(value: Any) -> str:
    return "hash:" + stable_hash(value)


def _payload_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).lower()


def _bool_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _extract_text(request: dict[str, Any]) -> str:
    for key in ("text", "utterance", "message", "intent_text", "natural_language", "query"):
        value = request.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())[:700]

    line_candidate = request.get("line_candidate")
    if isinstance(line_candidate, dict):
        events = line_candidate.get("event_candidates")
        if isinstance(events, list):
            for event in events:
                if isinstance(event, dict):
                    value = event.get("message_text_candidate")
                    if isinstance(value, str) and value.strip():
                        return " ".join(value.split())[:700]
    return ""


def default_7d_functional_state(source_channel: str) -> dict[str, Any]:
    channel = source_channel.upper()
    if channel == "LINE":
        functional_type = "LINE_CANDIDATE_REPLY"
    elif channel == "ODOO":
        functional_type = "ODOO_CANDIDATE_REPLY"
    elif channel == "WEB":
        functional_type = "WEB_CANDIDATE_REPLY"
    else:
        functional_type = "NATURAL_LANGUAGE_RESPONSE"
    return {
        "layer": "7D_FUNCTIONAL_STATE_LAYER",
        "functional_state_type": functional_type,
        "state_generation_mode": "EQUIVALENT_STATE_EFFECT",
        "equivalent_state_or_effect_generation": True,
        "executable_state": False,
        "candidate_only": True,
        "db_write": False,
        "odoo_write": False,
        "deploy": False,
        "restart": False,
        "formal_submit": False,
    }


def normalize_candidate_request(request: str | dict[str, Any] | None) -> dict[str, Any]:
    source: dict[str, Any]
    if isinstance(request, str):
        source = {"text": request}
    elif isinstance(request, dict):
        source = dict(request)
    else:
        source = {}

    source_channel = str(source.get("source_channel") or source.get("channel") or "web").upper()
    text = _extract_text(source)
    functional_state = source.get("functional_state_7d")
    if not isinstance(functional_state, dict):
        functional_state = default_7d_functional_state(source_channel)

    include_adi = source.get("include_adi_5d", True) is not False
    if "adi_5d_absolute_index" in source:
        adi_packet = source.get("adi_5d_absolute_index")
    elif include_adi:
        adi_packet = base_adi_5d_absolute_index_packet()
    else:
        adi_packet = None

    candidate_packet = {
        "packet_type": "natural_language_candidate_request",
        "candidate_only": True,
        "source_channel": source_channel,
        "natural_language_hash": hash_ref(text or "empty-natural-language"),
        "natural_language_excerpt": text,
        "ai_candidate_lane": {
            "candidate_generator_only": True,
            "final_authority": False,
            "formal_action_allowed": False,
        },
        "state_field_packet": {
            "packet_type": "8D_7D_STATE_FIELD_PACKET",
            "contains_7d_functional_state": True,
            "contains_8d_authority_envelope": True,
            "contains_adi_5d_absolute_index": isinstance(adi_packet, dict),
        },
        "lookup_reference_reconstruction_conditions": {
            "lookup_refs": ["lookup_ref:total_field_safe_natural_reply"],
            "reference_refs": ["reference_ref:clean_authority_index"],
            "reconstruction_condition_refs": ["reconstruction_condition_ref:equivalent_state_or_effect"],
            "actual_h64_td_rules_disclosed": False,
        },
        "functional_state_7d": functional_state,
        "authority_envelope_8d": {
            "authority": "LOCAL_TOTAL_FIELD",
            "ttl_seconds": 30,
            "nonce_required": True,
            "seal_required": True,
            "final_authority": True,
        },
        "requested_flags": {
            key: _bool_flag(source.get(key)) for key in HARD_RISK_FLAGS
        },
        "safety_boundary": {
            "db_write": False,
            "odoo_write": False,
            "deploy": False,
            "restart": False,
            "router_write": False,
            "formal_submit": False,
            "line_reply_sent": False,
            "external_api_call": False,
        },
    }
    line_candidate = source.get("line_candidate")
    if isinstance(line_candidate, dict):
        local = line_candidate.get("local_verifier") if isinstance(line_candidate.get("local_verifier"), dict) else {}
        candidate_packet["channel_candidate_verifier"] = {
            "channel": "LINE",
            "decision": local.get("decision", ""),
            "line_reply_allowed": False,
            "formal_line_send": False,
        }
    if isinstance(adi_packet, dict):
        candidate_packet["adi_5d_absolute_index"] = adi_packet
    return candidate_packet


def check_gt_definition_drift(candidate_packet: dict[str, Any]) -> list[str]:
    text = str(candidate_packet.get("natural_language_excerpt") or "").lower()
    errors: list[str] = []
    if any(marker in text for marker in GT_CORE_MARKERS) and any(term in text for term in GT_FORBIDDEN_CORE_TERMS):
        errors.append("GT_CORE_DEFINITION_DRIFT_FILE_TRANSFER_OR_CLOUD_SYNC")
    if any(term in text for term in ADI_DRIFT_TERMS):
        errors.append("ADI_5D_DEFINITION_DRIFT")
    return errors


def check_hard_risk(candidate_packet: dict[str, Any]) -> list[str]:
    text = str(candidate_packet.get("natural_language_excerpt") or "").lower()
    errors = [f"HARD_RISK_TERM:{term}" for term in HARD_RISK_TERMS if term in text]
    flags = candidate_packet.get("requested_flags", {})
    if isinstance(flags, dict):
        errors.extend(f"HARD_RISK_FLAG:{key}" for key, value in sorted(flags.items()) if value is True)
    return sorted(set(errors))


def check_7d_functional_state(candidate_packet: dict[str, Any]) -> list[str]:
    state = candidate_packet.get("functional_state_7d")
    if not isinstance(state, dict):
        return ["7D_FUNCTIONAL_STATE_MISSING"]
    errors: list[str] = []
    if state.get("layer") != "7D_FUNCTIONAL_STATE_LAYER":
        errors.append("7D_FUNCTIONAL_STATE_LAYER_INVALID")
    functional_type = state.get("functional_state_type")
    if functional_type not in ALLOWED_7D_FUNCTIONAL_STATES:
        errors.append("7D_FUNCTIONAL_STATE_TYPE_INVALID")
    if state.get("state_generation_mode") != "EQUIVALENT_STATE_EFFECT":
        errors.append("7D_FUNCTIONAL_STATE_GENERATION_MODE_INVALID")
    for key in ("db_write", "odoo_write", "deploy", "restart", "formal_submit"):
        if state.get(key) is not False:
            errors.append(f"7D_FUNCTIONAL_STATE_FORBIDDEN_SIDE_EFFECT:{key}")
    if state.get("candidate_only") is not True:
        errors.append("7D_FUNCTIONAL_STATE_NOT_CANDIDATE_ONLY")
    return errors


def check_channel_candidate(candidate_packet: dict[str, Any]) -> list[str]:
    if candidate_packet.get("source_channel") != "LINE":
        return []
    verifier = candidate_packet.get("channel_candidate_verifier")
    if not isinstance(verifier, dict):
        return ["LINE_CANDIDATE_VERIFIER_MISSING"]
    if verifier.get("decision") != "READY_FOR_LOCAL_INTENT_CANDIDATE":
        return ["LINE_CANDIDATE_VERIFIER_HOLD"]
    return []


def _make_verifier(run_id: str) -> Canonical8DVerifier:
    seed = stable_hash({"run_id": run_id, "purpose": "final_state_gate_ephemeral_verifier"})
    secrets = VerifierSecrets(
        d7_secret=hashlib.sha256((seed + ":d7").encode("utf-8")).digest(),
        trajectory_secret=hashlib.sha256((seed + ":trajectory").encode("utf-8")).digest(),
        audit_secret=hashlib.sha256((seed + ":audit").encode("utf-8")).digest(),
        key_version="ephemeral-final-state-gate-v1",
    )
    return Canonical8DVerifier(
        secrets=secrets,
        nonce_ledger=InMemoryNonceLedger(),
        config=VerifierConfig(ttl_seconds=30, verifier_version="final-state-gate-canonical-8d-v1"),
    )


def build_canonical_payload(candidate_packet: dict[str, Any], now: float, run_id: str) -> dict[str, Any]:
    payload = {
        "delta_D1": "user1",
        "ref_D2": "intent_order_latte",
        "delta_D4": "route_local",
        "env_D8": {
            "nonce": "nonce:" + stable_hash({"run_id": run_id, "candidate": candidate_packet})[:32],
            "timestamp": now,
        },
        "candidate_packet_ref": hash_ref(candidate_packet),
        "functional_state_7d": candidate_packet.get("functional_state_7d"),
        "lookup_reference_reconstruction_conditions": candidate_packet.get("lookup_reference_reconstruction_conditions"),
        "authority_envelope_8d": candidate_packet.get("authority_envelope_8d"),
        "generative_transmission_definition_lock": {
            "state_field_packet": True,
            "lookup_reference_reconstruction_conditions": True,
            "equivalent_state_generation": True,
            "total_field_verification": True,
            "file_transfer_core": False,
            "cloud_sync_core": False,
            "backup_core": False,
            "download_decrypt_restore_core": False,
        },
    }
    if isinstance(candidate_packet.get("adi_5d_absolute_index"), dict):
        payload["adi_5d_absolute_index"] = candidate_packet["adi_5d_absolute_index"]
    text = candidate_packet.get("natural_language_excerpt")
    if isinstance(text, str) and text:
        payload["natural_language_candidate_hash"] = hash_ref(text)
        payload["natural_language_candidate_excerpt"] = text
    return payload


def _sign_canonical_payload(payload: dict[str, Any], verifier: Canonical8DVerifier) -> None:
    payload["proof_D7"] = sign_d7_packet(payload, verifier.secrets.d7_secret)


def _reply_candidate(candidate_packet: dict[str, Any]) -> dict[str, Any]:
    text = str(candidate_packet.get("natural_language_excerpt") or "").strip()
    if not text:
        summary = "我可以先整理成安全候選回覆。"
    elif "菜單" in text or "menu" in text.lower():
        summary = "可以，我先整理菜單或服務資訊的候選回覆，正式下單或付款仍需人工確認。"
    else:
        summary = "可以，我先提供候選說明，所有正式操作都保持暫停。"
    return {
        "reply_type": "candidate_natural_language",
        "text": summary,
        "formal_action_executed": False,
    }


def run_total_field_gate(request: str | dict[str, Any] | None, now: float | None = None) -> dict[str, Any]:
    current_time = time.time() if now is None else float(now)
    candidate_packet = normalize_candidate_request(request)
    run_id = "TOTAL_FIELD_GATE_" + stable_hash({"candidate": candidate_packet, "now": current_time})[:16]

    adi_packet = candidate_packet.get("adi_5d_absolute_index")
    if isinstance(adi_packet, dict):
        adi_result = verify_adi_5d_absolute_index_packet(adi_packet)
        adi_errors = list(adi_result.get("ERRORS", []))
    else:
        adi_result = {
            "DRY_RUN": "FAIL",
            "CHECKS": {},
            "ERRORS": ["ADI_5D_ABSOLUTE_INDEX_MISSING"],
        }
        adi_errors = ["ADI_5D_ABSOLUTE_INDEX_MISSING"]

    gt_drift_errors = check_gt_definition_drift(candidate_packet)
    hard_risk_errors = check_hard_risk(candidate_packet)
    functional_errors = check_7d_functional_state(candidate_packet)
    channel_errors = check_channel_candidate(candidate_packet)

    verifier = _make_verifier(run_id)
    canonical_payload = build_canonical_payload(candidate_packet, current_time, run_id)
    _sign_canonical_payload(canonical_payload, verifier)
    canonical_decision, canonical_log = verifier.process_transmission(canonical_payload, now=current_time)
    canonical_adi = canonical_log.get("adi_5d_gate_result", {})

    errors = []
    errors.extend(gt_drift_errors)
    errors.extend(adi_errors)
    errors.extend(functional_errors)
    errors.extend(channel_errors)
    errors.extend(hard_risk_errors)
    if isinstance(canonical_adi, dict):
        errors.extend(error for error in canonical_adi.get("errors", []) if error not in errors)

    if gt_drift_errors:
        decision = HOLD
        gate_code = "HOLD_GT_DEFINITION_DRIFT"
        risk_level = "HIGH"
    elif hard_risk_errors:
        decision = HOLD
        gate_code = "HOLD_HARD_RISK_SIDE_EFFECT"
        risk_level = "HIGH"
    elif adi_errors:
        decision = HOLD
        gate_code = "HOLD_ADI_5D_ABSOLUTE_INDEX"
        risk_level = "MEDIUM"
    elif functional_errors:
        decision = HOLD
        gate_code = "HOLD_7D_FUNCTIONAL_STATE"
        risk_level = "MEDIUM"
    elif channel_errors:
        decision = HOLD
        gate_code = "HOLD_CHANNEL_CANDIDATE_VERIFIER"
        risk_level = "MEDIUM"
    elif canonical_decision == ALLOW:
        decision = PASS
        gate_code = "PASS_TOTAL_FIELD_GATE"
        risk_level = "LOW"
    elif canonical_decision == BLOCK:
        decision = BLOCK
        gate_code = "BLOCK_CANONICAL_8D_VERIFIER"
        risk_level = "HIGH"
    else:
        decision = HOLD
        gate_code = "HOLD_CANONICAL_8D_VERIFIER"
        risk_level = "MEDIUM"

    return {
        "state": STATE,
        "run_id": run_id,
        "decision": decision,
        "gate_code": gate_code,
        "risk_level": risk_level,
        "source_channel": candidate_packet.get("source_channel"),
        "candidate_packet_hash": hash_ref(candidate_packet),
        "reply_candidate": _reply_candidate(candidate_packet) if decision == PASS else {},
        "checks": {
            "candidate_normalized": "PASS",
            "adi_5d_absolute_index": "PASS" if not adi_errors else "FAIL",
            "canonical_8d_verifier": "PASS" if canonical_decision == ALLOW else canonical_decision,
            "functional_state_7d": "PASS" if not functional_errors else "FAIL",
            "channel_candidate": "PASS" if not channel_errors else "FAIL",
            "hard_risk": "PASS" if not hard_risk_errors else "FAIL",
            "gt_definition_drift": "PASS" if not gt_drift_errors else "FAIL",
            "lookup_reference_reconstruction_conditions": "PASS",
            "no_side_effects": "PASS",
        },
        "canonical_verifier": {
            "decision": canonical_decision,
            "gate_stage": canonical_log.get("gate_stage"),
            "adi_5d_gate_result_code": canonical_adi.get("result_code") if isinstance(canonical_adi, dict) else "",
        },
        "adi_5d_verifier": {
            "dry_run": adi_result.get("DRY_RUN"),
            "checks": adi_result.get("CHECKS", {}),
        },
        "functional_state_7d": {
            "type": (candidate_packet.get("functional_state_7d") or {}).get("functional_state_type")
            if isinstance(candidate_packet.get("functional_state_7d"), dict)
            else "",
            "layer": "7D_FUNCTIONAL_STATE_LAYER",
        },
        "authority": {
            "total_field_final_authority": True,
            "ai_candidate_lane_final_authority": False,
            "channel_final_authority": False,
        },
        "side_effects": {
            "db_write": False,
            "odoo_write": False,
            "deploy": False,
            "restart": False,
            "router_write": False,
            "formal_submit": False,
            "external_api_call": False,
            "line_reply_sent": False,
        },
        "errors": sorted(set(errors)),
    }


def run_line_candidate_gate(line_candidate: dict[str, Any] | None, now: float | None = None) -> dict[str, Any]:
    candidate = line_candidate if isinstance(line_candidate, dict) else {}
    return run_total_field_gate(
        {
            "source_channel": "LINE",
            "line_candidate": candidate,
            "text": _extract_text({"line_candidate": candidate}),
        },
        now=now,
    )


def main() -> int:
    result = run_total_field_gate({"text": "請用自然語言回覆菜單資訊", "source_channel": "web"})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["decision"] == PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
