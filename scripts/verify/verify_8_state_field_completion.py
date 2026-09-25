#!/usr/bin/env python3
"""Verify 8 state field completion for current W7TP candidate docs and schemas."""

from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

DOCS = [
    ROOT / "docs/total_field/W7TP_PROPERTY_MODULE_SOVEREIGN_AI_AMPLIFICATION_SPEC.md",
    ROOT / "docs/total_field/W7TP_DUAL_MODULE_PROPERTY_MERCHANT_GOVERNANCE_DEMO_SPEC.md",
    ROOT / "docs/total_field/W7TP_SOVEREIGN_AI_MEMBER_XIAOJ_TRANSLATOR_SPEC.md",
]

SCHEMAS = [
    ROOT / "schemas/field/w7tp_property_sovereign_ai_amplification.schema.json",
    ROOT / "schemas/field/w7tp_dual_module_property_merchant_governance.schema.json",
    ROOT / "schemas/field/sovereign_ai_member_xiaoj_translator.schema.json",
]

SAMPLE_GLOB = ROOT / "schemas/field/examples/dual_module_governance/*.json"

STATE_FIELD_KEYS = [
    "intent_field",
    "state_field",
    "coordinate_field",
    "evidence_field",
    "execution_field",
    "generative_transport_field",
    "risk_field",
    "envelope_field",
]

BASE_FIELD_KEYS = ["summary", "refs", "status"]
RISK_FLAGS = [
    "no_secret",
    "no_member_plaintext",
    "no_resident_plaintext",
    "no_raw_image",
    "no_db_write",
    "no_deploy",
    "no_restart",
    "no_router_write",
]

FORBIDDEN_TEXT = [
    "8欄位",
    "八欄位",
    "ADI裝8D",
    "雲端同步個資",
    "檔案搬運",
    "備份下載",
    "明文傳輸",
]

FORBIDDEN_JSON_KEYS = {
    "raw_api_key",
    "raw_token",
    "password",
    "plaintext_member_data",
    "raw_image_export",
}

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|token|password|client_secret)\s*[:=]\s*[A-Za-z0-9._-]{12,}"),
]


def fail(reason: str) -> int:
    print("STATE=HOLD_8_STATE_FIELD_VERIFICATION_COMPLETION")
    print(f"REASON={reason}")
    return 1


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        raise ValueError(f"json_parse_failed:{rel(path)}:{exc}") from exc


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def all_json_paths() -> list[Path]:
    sample_paths = [Path(path) for path in sorted(glob.glob(str(SAMPLE_GLOB)))]
    return [*SCHEMAS, *sample_paths]


def scan_forbidden(paths: list[Path]) -> str | None:
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for term in FORBIDDEN_TEXT:
            if term in text:
                return f"forbidden_definition_term:{rel(path)}:{term}"
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                return f"raw_secret_pattern:{rel(path)}"
    return None


def walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key))
            keys.update(walk_keys(nested))
    elif isinstance(value, list):
        for item in value:
            keys.update(walk_keys(item))
    return keys


def resolve_schema_node(schema: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    ref = node.get("$ref")
    if not isinstance(ref, str):
        return node
    prefix = "#/$defs/"
    if not ref.startswith(prefix):
        return node
    defs = schema.get("$defs", {})
    target = defs.get(ref.removeprefix(prefix), {})
    return target if isinstance(target, dict) else node


def schema_required_keys(schema: dict[str, Any], field_key: str) -> set[str]:
    props = schema.get("properties", {})
    if not isinstance(props, dict):
        return set()
    node = props.get(field_key)
    if not isinstance(node, dict):
        return set()
    resolved = resolve_schema_node(schema, node)
    required = resolved.get("required", [])
    return set(required) if isinstance(required, list) else set()


def schema_property_const(schema: dict[str, Any], field_key: str, property_key: str) -> Any:
    props = schema.get("properties", {})
    if not isinstance(props, dict):
        return None
    node = props.get(field_key)
    if not isinstance(node, dict):
        return None
    resolved = resolve_schema_node(schema, node)
    nested_props = resolved.get("properties", {})
    if not isinstance(nested_props, dict):
        return None
    target = nested_props.get(property_key, {})
    if not isinstance(target, dict):
        return None
    return target.get("const")


def check_schema(path: Path, schema: dict[str, Any]) -> str | None:
    keys = walk_keys(schema)
    bad_keys = sorted(keys & FORBIDDEN_JSON_KEYS)
    if bad_keys:
        return f"forbidden_schema_keys:{rel(path)}:{','.join(bad_keys)}"

    required = schema.get("required", [])
    properties = schema.get("properties", {})
    if not isinstance(required, list) or not isinstance(properties, dict):
        return f"schema_shape_invalid:{rel(path)}"
    for key in STATE_FIELD_KEYS:
        if key not in required or key not in properties:
            return f"schema_missing_state_field:{rel(path)}:{key}"
        missing = [base_key for base_key in BASE_FIELD_KEYS if base_key not in schema_required_keys(schema, key)]
        if missing:
            return f"schema_state_field_missing_base_keys:{rel(path)}:{key}:{','.join(missing)}"

    if schema_property_const(schema, "generative_transport_field", "mode") != "state_packet_ref_reconstruction_equivalent_state":
        return f"schema_gt_mode_mismatch:{rel(path)}"

    for flag in RISK_FLAGS:
        if flag not in schema_required_keys(schema, "risk_field"):
            return f"schema_risk_flag_missing:{rel(path)}:{flag}"

    if schema_property_const(schema, "envelope_field", "final_authority") != "total_field_verifier":
        return f"schema_envelope_authority_mismatch:{rel(path)}"
    if schema_property_const(schema, "envelope_field", "human_review_required") is not True:
        return f"schema_envelope_human_review_mismatch:{rel(path)}"
    if schema_property_const(schema, "envelope_field", "candidate_only") is not True:
        return f"schema_envelope_candidate_only_mismatch:{rel(path)}"

    final_authority = properties.get("final_authority", {})
    if isinstance(final_authority, dict) and final_authority.get("const") != "total_field_verifier":
        return f"schema_final_authority_mismatch:{rel(path)}"

    return None


def check_sample(path: Path, sample: dict[str, Any]) -> str | None:
    bad_keys = sorted(walk_keys(sample) & FORBIDDEN_JSON_KEYS)
    if bad_keys:
        return f"forbidden_sample_keys:{rel(path)}:{','.join(bad_keys)}"

    for key in STATE_FIELD_KEYS:
        node = sample.get(key)
        if not isinstance(node, dict):
            return f"sample_missing_state_field:{rel(path)}:{key}"
        missing = [base_key for base_key in BASE_FIELD_KEYS if base_key not in node]
        if missing:
            return f"sample_state_field_missing_base_keys:{rel(path)}:{key}:{','.join(missing)}"

    gt = sample.get("generative_transport_field", {})
    if gt.get("mode") != "state_packet_ref_reconstruction_equivalent_state":
        return f"sample_gt_mode_mismatch:{rel(path)}"

    risk = sample.get("risk_field", {})
    for flag in RISK_FLAGS:
        if risk.get(flag) is not True:
            return f"sample_risk_flag_mismatch:{rel(path)}:{flag}"

    envelope = sample.get("envelope_field", {})
    if envelope.get("final_authority") != "total_field_verifier":
        return f"sample_envelope_authority_mismatch:{rel(path)}"
    if envelope.get("human_review_required") is not True:
        return f"sample_envelope_human_review_mismatch:{rel(path)}"
    if envelope.get("candidate_only") is not True:
        return f"sample_envelope_candidate_only_mismatch:{rel(path)}"

    if sample.get("final_authority") != "total_field_verifier":
        return f"sample_final_authority_mismatch:{rel(path)}"

    return None


def check_doc(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    for key in STATE_FIELD_KEYS:
        if key not in text:
            return f"doc_missing_state_field_key:{rel(path)}:{key}"
    if "mode=state_packet_ref_reconstruction_equivalent_state" not in text:
        return f"doc_missing_gt_mode:{rel(path)}"
    if "final_authority=total_field_verifier" not in text:
        return f"doc_missing_final_authority:{rel(path)}"
    if "human_review_required=true" not in text:
        return f"doc_missing_human_review_required:{rel(path)}"
    if "candidate_only=true" not in text:
        return f"doc_missing_candidate_only:{rel(path)}"
    return None


def main() -> int:
    for path in DOCS + SCHEMAS:
        if not path.is_file():
            return fail(f"target_missing:{rel(path)}")

    sample_paths = [Path(path) for path in sorted(glob.glob(str(SAMPLE_GLOB)))]
    if not sample_paths:
        return fail("dual_module_sample_missing")

    forbidden = scan_forbidden([*DOCS, *SCHEMAS, *sample_paths])
    if forbidden:
        return fail(forbidden)

    for doc in DOCS:
        doc_error = check_doc(doc)
        if doc_error:
            return fail(doc_error)

    try:
        schema_payloads = {path: read_json(path) for path in SCHEMAS}
        sample_payloads = {path: read_json(path) for path in sample_paths}
    except ValueError as exc:
        return fail(str(exc))

    for path, schema in schema_payloads.items():
        schema_error = check_schema(path, schema)
        if schema_error:
            return fail(schema_error)

    for path, sample in sample_payloads.items():
        if not isinstance(sample, dict):
            return fail(f"sample_not_object:{rel(path)}")
        sample_error = check_sample(path, sample)
        if sample_error:
            return fail(sample_error)

    print("STATE=PASS_8_STATE_FIELD_VERIFICATION_COMPLETION_VERIFY")
    print("JSON_PARSE=PASS")
    print("REDTEAM_CHECK=PASS")
    print("DOCS_CHECKED=" + ",".join(rel(path) for path in DOCS))
    print("SCHEMAS_CHECKED=" + ",".join(rel(path) for path in SCHEMAS))
    print("SAMPLES_CHECKED=" + ",".join(rel(path) for path in sample_paths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
