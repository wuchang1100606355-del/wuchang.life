#!/usr/bin/env python3
"""Build a unified XiaoJ merchant productization readiness report.

The report aggregates LINE WORKS, LINE Official Account, member registration,
POS order, and payment release gates. It does not read secrets, write Odoo DB
rows, deploy, restart services, send LINE/LINE WORKS messages, create POS
orders, or capture payments.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "packets/product_av_ordering_ai/xiaoj_merchant_productization_readiness_template.json"
DEFAULT_OUT_DIR = ROOT / "runtime/product_av_ordering_ai/merchant_productization"
ENGINE_PATH = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/p1_intent_engine.py"
LINEWORKS_CONNECTOR_PATH = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/lineworks_connector.py"
LINE_OFFICIAL_CONFIG_PATH = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/line_official_account_config.py"
LINE_OFFICIAL_REFS_PATH = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/line_official_account_refs.py"
MERCHANT_READINESS_SERVICE_PATH = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/merchant_productization_readiness.py"


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+"),
    re.compile(r"(?i)channel_secret\s*[:=]\s*\S+"),
    re.compile(r"(?i)client_secret\s*[:=]\s*\S+"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}"),
]


def ensure_package_stub(name: str, path: Path) -> None:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]  # type: ignore[attr-defined]
        sys.modules[name] = module
    elif not hasattr(module, "__path__"):
        module.__path__ = [str(path)]  # type: ignore[attr-defined]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_service_module(module_name: str, path: Path):
    ensure_package_stub("Taiji_Odoo", ROOT / "Taiji_Odoo")
    ensure_package_stub("Taiji_Odoo.addons", ROOT / "Taiji_Odoo/addons")
    ensure_package_stub("Taiji_Odoo.addons.wuchang_cafe_ai_gateway", ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway")
    ensure_package_stub(
        "Taiji_Odoo.addons.wuchang_cafe_ai_gateway.services",
        ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services",
    )
    return load_module(f"Taiji_Odoo.addons.wuchang_cafe_ai_gateway.services.{module_name}", path)


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def resolve_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path


def default_out_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_OUT_DIR / f"XIAOJ_MERCHANT_PRODUCTIZATION_READINESS_{stamp}.json"


def has_secret_shape(value: Any) -> bool:
    text = str(value or "")
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def reject_secret_shapes(value: Any, label: str) -> None:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True) if not isinstance(value, str) else value
    if has_secret_shape(serialized):
        raise ValueError(f"secret-shaped material is not allowed in {label}; use refs only")


def is_placeholder_ref(value: Any) -> bool:
    text = str(value or "")
    return (
        not text
        or text.startswith("REF_")
        or text.endswith("_NO_SECRET")
        or text.endswith("_NO_MEMBER_PLAINTEXT")
        or text.endswith("_NO_TOKEN_VALUE")
        or text.endswith("_TO_FILL")
        or "PLACEHOLDER" in text
        or text == "0" * 64
    )


def release_ref_readiness(refs: dict, required_refs: list[str]) -> dict:
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
        if is_placeholder_ref(value.get("ref")) or is_placeholder_ref(value.get("packet_hash")):
            placeholders.append(key)
    return {
        "missing_release_refs": missing,
        "unverified_release_refs": unverified,
        "placeholder_release_refs": placeholders,
    }


def connector_ref_readiness(refs: dict, required_connector_refs: list[str]) -> dict:
    connector_refs = refs.get("connector_refs") if isinstance(refs.get("connector_refs"), dict) else {}
    missing = [key for key in required_connector_refs if not connector_refs.get(key)]
    placeholders = [key for key in required_connector_refs if is_placeholder_ref(connector_refs.get(key))]
    return {
        "connector_refs": connector_refs,
        "missing_connector_refs": missing,
        "placeholder_connector_refs": placeholders,
    }


def formal_gate_summary(formal_status: dict) -> dict:
    gates = formal_status.get("formal_release_gates") if isinstance(formal_status.get("formal_release_gates"), dict) else {}
    summary = {}
    for gate_id, gate in gates.items():
        summary[gate_id] = {
            "title": gate.get("title", gate_id),
            "decision": gate.get("decision", ""),
            "release_ready": gate.get("release_ready") is True,
            "missing_refs": gate.get("missing_refs", []),
            "unverified_ref_keys": gate.get("unverified_ref_keys", []),
            "total_field_blocker": gate.get("total_field_blocker", ""),
            "release_packet_hash": gate.get("release_packet_hash", ""),
        }
    return summary


def lineworks_readiness(engine, connector, lineworks_refs: dict, probe: dict) -> dict:
    required_release_refs = list(engine.FORMAL_RELEASE_GATES["lineworks_send"]["required_refs"])
    release_readiness = release_ref_readiness(lineworks_refs, required_release_refs)
    connector_readiness = connector_ref_readiness(lineworks_refs, connector.REQUIRED_CONNECTOR_REFS)
    candidate = engine.lineworks_notify_payload(
        probe.get("message") or "XiaoJ merchant productization readiness probe",
        probe.get("target_ref") or "TARGET_REF_READINESS_CHECK",
        probe.get("channel") or "member_service",
        probe.get("actor_ref") or "ACTOR_REF_READINESS_CHECK",
    )
    release_status = engine.formal_release_status_payload({"lineworks_send": lineworks_refs.get("lineworks_send", {})})
    preflight = connector.build_lineworks_send_preflight(
        candidate,
        release_status,
        connector_readiness["connector_refs"],
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
    return {
        "state": "PASS_LINEWORKS_RELEASE_READINESS" if not blockers else "HOLD_LINEWORKS_RELEASE_READINESS",
        "ready_for_human_activation": not blockers,
        "blockers": blockers,
        **release_readiness,
        "missing_connector_refs": connector_readiness["missing_connector_refs"],
        "placeholder_connector_refs": connector_readiness["placeholder_connector_refs"],
        "preflight_state": preflight.get("state", ""),
        "preflight_send_allowed": preflight.get("send_allowed") is True,
        "release_gate_decision": release_status.get("formal_release_gates", {}).get("lineworks_send", {}).get("decision", ""),
        "candidate_packet_hash": candidate.get("authority_packet", {}).get("packet_hash", ""),
        "preflight_envelope_hash": preflight.get("request_envelope_hash", ""),
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


def line_official_account_readiness(config_service, refs_service, refs_payload: dict, intent: str) -> dict:
    refs_input = refs_payload.get("refs") if isinstance(refs_payload.get("refs"), dict) else refs_payload
    refs_draft = refs_service.build_line_official_account_refs_draft(refs_input)
    candidate = config_service.build_line_official_account_config_candidate(
        intent,
        refs=refs_draft.get("refs", {}),
        style_ref="STYLE_REF_XIAOJ_WARM_PRECISE",
        operator_ref="OPERATOR_REF_LINE_OFFICIAL_ACCOUNT_REVIEW",
    )
    blockers = []
    if refs_draft.get("state") != "LINE_OFFICIAL_ACCOUNT_REFS_READY_FOR_CONFIG_CANDIDATE":
        blockers.append("line_official_account_refs_not_ready")
    if candidate.get("state") != "READY_FOR_HUMAN_APPROVAL":
        blockers.append("line_official_account_config_candidate_not_ready")
    return {
        "state": "PASS_LINE_OFFICIAL_ACCOUNT_READY_FOR_HUMAN_APPROVAL" if not blockers else "HOLD_LINE_OFFICIAL_ACCOUNT_REFS_OR_CONFIG",
        "ready_for_human_approval": not blockers,
        "blockers": blockers,
        "refs_state": refs_draft.get("state", ""),
        "refs_warnings": refs_draft.get("draft_warnings", []),
        "candidate_state": candidate.get("state", ""),
        "candidate_failure_reasons": candidate.get("local_verifier", {}).get("failure_reasons", []),
        "candidate_packet_hash": candidate.get("authority_packet", {}).get("packet_hash", ""),
        "evidence_hash": candidate.get("authority_packet", {}).get("evidence_hash", ""),
        "side_effects": {
            "external_api_call": False,
            "formal_line_message_send": False,
            "official_account_setting_changed": False,
            "secret_read": False,
            "member_plaintext_read": False,
            "db_write": False,
            "deploy": False,
            "service_restart": False,
        },
    }


def operator_next_actions(formal_gates: dict, lineworks: dict, line_official: dict) -> list[str]:
    actions = []
    if not line_official.get("ready_for_human_approval"):
        actions.append("fill_line_official_account_safe_refs_and_rerun_config_candidate")
    if not lineworks.get("ready_for_human_activation"):
        actions.append("fill_verified_lineworks_release_refs_and_runtime_connector_refs")
    gate_labels = {
        "member_registration": "fill_verified_member_registration_release_refs",
        "pos_order": "fill_verified_pos_order_release_refs",
        "payment": "fill_verified_payment_release_refs",
        "lineworks_send": "fill_verified_lineworks_send_release_refs",
    }
    for gate_id, gate in formal_gates.items():
        if gate.get("release_ready") is not True:
            actions.append(gate_labels.get(gate_id, f"fill_verified_{gate_id}_release_refs"))
    if not actions:
        actions.append("human_owner_admin_review_then_create_runtime_activation_packet")
    return sorted(dict.fromkeys(actions))


def build_report(config: dict, args) -> dict:
    reject_secret_shapes(config, "merchant productization readiness input")
    service = load_service_module("merchant_productization_readiness", MERCHANT_READINESS_SERVICE_PATH)

    lineworks_refs_path = resolve_path(args.lineworks_refs or config.get("lineworks_refs_path", ""))
    line_official_refs_path = resolve_path(args.line_official_refs or config.get("line_official_account_refs_path", ""))
    lineworks_refs = read_json(lineworks_refs_path)
    line_official_refs_payload = read_json(line_official_refs_path)
    reject_secret_shapes(lineworks_refs, "lineworks refs")
    reject_secret_shapes(line_official_refs_payload, "line official account refs")

    formal_release_refs = config.get("formal_release_refs") if isinstance(config.get("formal_release_refs"), dict) else {}
    return service.build_merchant_productization_readiness(
        formal_release_refs=formal_release_refs,
        lineworks_refs=lineworks_refs,
        line_official_account_refs=line_official_refs_payload,
        line_official_account_intent=args.line_official_intent or config.get("line_official_account_intent", ""),
        lineworks_probe=config.get("lineworks_probe") if isinstance(config.get("lineworks_probe"), dict) else {},
        input_ref=str(resolve_path(args.config)),
        lineworks_refs_path=str(lineworks_refs_path),
        line_official_account_refs_path=str(line_official_refs_path),
    )


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build XiaoJ merchant productization readiness report")
    parser.add_argument("--config", default=str(DEFAULT_INPUT), help="Readiness input JSON")
    parser.add_argument("--lineworks-refs", default="", help="Override LINE WORKS refs JSON")
    parser.add_argument("--line-official-refs", default="", help="Override LINE Official Account refs JSON")
    parser.add_argument("--line-official-intent", default="", help="Override LINE Official Account natural-language intent")
    parser.add_argument("--out", default="", help="Output report path")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    config_path = resolve_path(args.config)
    config = read_json(config_path)
    report = build_report(config, args)
    out_path = Path(args.out).expanduser() if args.out else default_out_path()
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "schema": "W7TP_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS_CLI_REPORT_V1",
        "state": report["state"],
        "output_path": relative_path(out_path),
        "product_ready_for_human_activation": report["product_ready_for_human_activation"],
        "operator_next_actions": report["operator_next_actions"],
        "report_hash": report["report_hash"],
        "side_effects": report["side_effects"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if report["state"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
