#!/usr/bin/env python3
"""Verifier for the association digital resident identity code packet."""

from __future__ import annotations

import json
import py_compile
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/total_field/W7TP_ASSOCIATION_DIGITAL_RESIDENT_IDENTITY_CODE_SPEC.md"
SCHEMA = ROOT / "schemas/field/w7tp_association_digital_resident_identity_code.schema.json"
SAMPLE = ROOT / "schemas/field/examples/association_digital_resident_identity_code/sample_role_stacked_resident_identity.json"
VERIFY_SCRIPT = ROOT / "scripts/verify/verify_association_digital_resident_identity_code.py"

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
    "no_raw_voice",
    "no_raw_credentials",
    "no_db_write",
    "no_deploy",
    "no_restart",
    "no_router_write",
]

FORBIDDEN_JSON_KEYS = {
    "raw_api_key",
    "raw_token",
    "password",
    "plaintext_member_data",
    "resident_plaintext",
    "raw_image_export",
    "raw_voice_export",
}

FORBIDDEN_TEXT = [
    "8欄位",
    "八欄位",
    "ADI裝8D",
    "雲端同步個資",
    "檔案搬運",
    "備份下載",
    "明文傳輸",
]

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|token|password|client_secret)\s*[:=]\s*[A-Za-z0-9._-]{12,}"),
]


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def fail(reason: str) -> int:
    print("STATE=HOLD_ASSOCIATION_DIGITAL_RESIDENT_IDENTITY_CODE_VERIFY")
    print(f"REASON={reason}")
    return 1


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        raise ValueError(f"json_parse_failed:{rel(path)}:{exc}") from exc


def scan_text(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    for term in FORBIDDEN_TEXT:
        if term in text:
            return f"forbidden_definition_term:{rel(path)}:{term}"
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            return f"secret_pattern:{rel(path)}"
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


def property_const(schema: dict[str, Any], name: str) -> Any:
    props = schema.get("properties", {})
    if not isinstance(props, dict):
        return None
    node = props.get(name, {})
    if not isinstance(node, dict):
        return None
    return node.get("const")


def nested_const(schema: dict[str, Any], object_name: str, property_name: str) -> Any:
    props = schema.get("properties", {})
    if not isinstance(props, dict):
        return None
    node = props.get(object_name, {})
    if not isinstance(node, dict):
        return None
    nested_props = node.get("properties", {})
    if not isinstance(nested_props, dict):
        return None
    target = nested_props.get(property_name, {})
    if not isinstance(target, dict):
        return None
    return target.get("const")


def resolve_schema_node(schema: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    ref = node.get("$ref")
    if not isinstance(ref, str):
        return node
    prefix = "#/$defs/"
    if not ref.startswith(prefix):
        return node
    defs = schema.get("$defs", {})
    resolved = defs.get(ref.removeprefix(prefix), {})
    return resolved if isinstance(resolved, dict) else node


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


def check_schema(schema: dict[str, Any]) -> str | None:
    bad_keys = sorted(walk_keys(schema) & FORBIDDEN_JSON_KEYS)
    if bad_keys:
        return "schema_forbidden_keys:" + ",".join(bad_keys)

    if property_const(schema, "primary_technology") != "8D_STATE_FIELD_PACKET":
        return "schema_primary_technology_mismatch"
    if property_const(schema, "final_authority") != "total_field_verifier":
        return "schema_final_authority_mismatch"
    if nested_const(schema, "digital_resident_identity_code", "plaintext_policy") != "LOCAL_ONLY_NO_CLOUD_NO_TOTAL_FIELD":
        return "schema_plaintext_policy_mismatch"
    if property_const(schema, "privacy_boundary") != "ALL_IDENTIFIABLE_PLAINTEXT_LOCAL_ONLY":
        return "schema_privacy_boundary_mismatch"
    if property_const(schema, "cloud_candidate_policy") != "CANDIDATE_ONLY_NO_AUTHORITY_NO_PLAINTEXT":
        return "schema_cloud_candidate_policy_mismatch"

    props = schema.get("properties", {})
    required = schema.get("required", [])
    if not isinstance(props, dict) or not isinstance(required, list):
        return "schema_shape_invalid"
    for key in STATE_FIELD_KEYS:
        if key not in props or key not in required:
            return f"schema_missing_state_field:{key}"
        missing = [base for base in BASE_FIELD_KEYS if base not in schema_required_keys(schema, key)]
        if missing:
            return f"schema_state_field_missing_base:{key}:{','.join(missing)}"

    gt_required = schema_required_keys(schema, "generative_transport_field")
    for required_key in ["mode", "full_data_required", "plaintext_required"]:
        if required_key not in gt_required:
            return f"schema_gt_missing:{required_key}"
    return None


def check_sample(sample: dict[str, Any]) -> str | None:
    bad_keys = sorted(walk_keys(sample) & FORBIDDEN_JSON_KEYS)
    if bad_keys:
        return "sample_forbidden_keys:" + ",".join(bad_keys)

    if sample.get("primary_technology") != "8D_STATE_FIELD_PACKET":
        return "sample_primary_technology_mismatch"
    if sample.get("final_authority") != "total_field_verifier":
        return "sample_final_authority_mismatch"
    if sample.get("privacy_boundary") != "ALL_IDENTIFIABLE_PLAINTEXT_LOCAL_ONLY":
        return "sample_privacy_boundary_mismatch"
    if sample.get("cloud_candidate_policy") != "CANDIDATE_ONLY_NO_AUTHORITY_NO_PLAINTEXT":
        return "sample_cloud_candidate_policy_mismatch"

    for key in STATE_FIELD_KEYS:
        node = sample.get(key)
        if not isinstance(node, dict):
            return f"sample_missing_state_field:{key}"
        missing = [base for base in BASE_FIELD_KEYS if base not in node]
        if missing:
            return f"sample_state_field_missing_base:{key}:{','.join(missing)}"

    gt = sample.get("generative_transport_field", {})
    if not isinstance(gt, dict):
        return "sample_gt_not_object"
    if gt.get("mode") != "incomplete_information_equivalent_state_transmission":
        return "sample_gt_mode_mismatch"
    if gt.get("full_data_required") is not False:
        return "sample_gt_full_data_required_not_false"
    if gt.get("plaintext_required") is not False:
        return "sample_gt_plaintext_required_not_false"

    risk = sample.get("risk_field", {})
    if not isinstance(risk, dict):
        return "sample_risk_not_object"
    for flag in RISK_FLAGS:
        if risk.get(flag) is not True:
            return f"sample_risk_flag_mismatch:{flag}"

    role_types = {
        role.get("role_type")
        for role in sample.get("role_mounts", [])
        if isinstance(role, dict)
    }
    expected_roles = {
        "resident_role",
        "member_role",
        "merchant_responsible_person_role",
        "association_responsible_person_role",
        "consumer_role",
        "developer_role",
    }
    if role_types != expected_roles:
        return "sample_role_mounts_incomplete"
    return None


def main() -> int:
    for path in [DOC, SCHEMA, SAMPLE, VERIFY_SCRIPT]:
        if not path.is_file():
            return fail(f"target_missing:{rel(path)}")

    for path in [DOC, SCHEMA, SAMPLE]:
        scan_error = scan_text(path)
        if scan_error:
            return fail(scan_error)

    try:
        py_compile.compile(str(VERIFY_SCRIPT), doraise=True)
        schema = load_json(SCHEMA)
        sample = load_json(SAMPLE)
    except Exception as exc:  # pragma: no cover
        return fail(str(exc))

    schema_error = check_schema(schema)
    if schema_error:
        return fail(schema_error)
    if not isinstance(sample, dict):
        return fail("sample_not_object")
    sample_error = check_sample(sample)
    if sample_error:
        return fail(sample_error)

    print("STATE=PASS_ASSOCIATION_DIGITAL_RESIDENT_IDENTITY_CODE_VERIFY")
    print("JSON_PARSE=PASS")
    print("PY_COMPILE=PASS")
    print("REDTEAM_CHECK=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
