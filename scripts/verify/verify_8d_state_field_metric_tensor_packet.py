#!/usr/bin/env python3
"""Read-only verifier for W7TP 8D state field metric tensor packet artifacts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/total_field/W7TP_8D_STATE_FIELD_METRIC_TENSOR_PACKET_SPEC.md"
SCHEMA = ROOT / "schemas/field/w7tp_8d_state_field_metric_tensor_packet.schema.json"
SAMPLES = [
    ROOT / "schemas/field/examples/8d_state_field_metric_tensor_packet/sample_internal_member_to_merchant_gt.json",
    ROOT / "schemas/field/examples/8d_state_field_metric_tensor_packet/sample_xiaoj_block_unauthorized_door.json"
]

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

FORBIDDEN_KEYS = {
    "raw_api_key",
    "raw_token",
    "password",
    "plaintext_member_data",
    "resident_plaintext",
    "raw_image_export",
}

FORBIDDEN_DEFINITION_TERMS = [
    "8欄位",
    "八欄位",
    "ADI裝8D",
    "雲端同步個資",
    "備份下載",
    "明文傳輸",
]

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|token|password|client_secret)\s*[:=]\s*[A-Za-z0-9._-]{12,}"),
]

EXECUTION_PATTERNS = [
    re.compile(r"docker\s+compose\s+restart", re.IGNORECASE),
    re.compile(r"systemctl\s+restart", re.IGNORECASE),
    re.compile(r"kubectl\s+apply", re.IGNORECASE),
    re.compile(r"router\s+write", re.IGNORECASE),
    re.compile(r"psql\b.*\b(INSERT|UPDATE|DELETE)\b", re.IGNORECASE),
]


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def fail(reason: str) -> int:
    print("STATE=HOLD_8D_STATE_FIELD_METRIC_TENSOR_PACKET_VERIFY")
    print(f"REASON={reason}")
    return 1


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        raise ValueError(f"json_parse_failed:{rel(path)}:{exc}") from exc


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


def is_allowed_negative_definition(line: str, term: str) -> bool:
    if term == "檔案搬運":
        return "不是" in line or "not=" in line
    return False


def is_allowed_risk_boundary_line(line: str) -> bool:
    stripped = line.strip()
    return (
        stripped.startswith("- router write")
        or stripped.startswith("- deploy/restart/reboot")
        or "NO_ROUTER_WRITE" in stripped
        or "NO_DEPLOY" in stripped
        or "NO_RESTART" in stripped
    )


def scan_text(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            return f"raw_secret_pattern:{rel(path)}"
    for line_no, line in enumerate(text.splitlines(), start=1):
        for term in FORBIDDEN_DEFINITION_TERMS + ["檔案搬運"]:
            if term in line and not is_allowed_negative_definition(line, term):
                return f"forbidden_definition_term:{rel(path)}:{line_no}:{term}"
        for pattern in EXECUTION_PATTERNS:
            if pattern.search(line) and not is_allowed_risk_boundary_line(line):
                return f"execution_command_pattern:{rel(path)}:{line_no}:{pattern.pattern}"
    return None


def required_const(schema: dict[str, Any], key: str) -> Any:
    props = schema.get("properties", {})
    if not isinstance(props, dict):
        return None
    node = props.get(key, {})
    if not isinstance(node, dict):
        return None
    return node.get("const")


def nested_required_const(schema: dict[str, Any], object_key: str, key: str) -> Any:
    props = schema.get("properties", {})
    if not isinstance(props, dict):
        return None
    node = props.get(object_key, {})
    if not isinstance(node, dict):
        return None
    nested_props = node.get("properties", {})
    if not isinstance(nested_props, dict):
        return None
    nested = nested_props.get(key, {})
    if not isinstance(nested, dict):
        return None
    return nested.get("const")


def check_schema(schema: dict[str, Any]) -> str | None:
    if walk_keys(schema) & FORBIDDEN_KEYS:
        return "forbidden_schema_key"
    if required_const(schema, "primary_technology") != "8D_STATE_FIELD_PACKET":
        return "schema_primary_technology_mismatch"
    if required_const(schema, "final_authority") != "total_field_verifier":
        return "schema_final_authority_mismatch"
    if nested_required_const(schema, "generative_transport", "mode") != "incomplete_information_equivalent_state_transmission":
        return "schema_gt_mode_mismatch"
    if nested_required_const(schema, "generative_transport", "full_data_required") is not False:
        return "schema_gt_full_data_required_not_false"
    if nested_required_const(schema, "generative_transport", "plaintext_required") is not False:
        return "schema_gt_plaintext_required_not_false"
    if required_const(schema, "cloud_candidate_policy") != "CANDIDATE_ONLY_NO_AUTHORITY":
        return "schema_cloud_candidate_policy_mismatch"
    if required_const(schema, "adi_policy") != "ADI_5D_METRIC_INDEX_ONLY_NOT_8D_TABLE":
        return "schema_adi_policy_mismatch"
    return None


def check_state_field_node(path: Path, sample: dict[str, Any], key: str) -> str | None:
    packet_vector = sample.get("packet_vector", {})
    if not isinstance(packet_vector, dict):
        return f"sample_packet_vector_missing:{rel(path)}"
    node = packet_vector.get(key)
    if not isinstance(node, dict):
        return f"sample_missing_8_state_field:{rel(path)}:{key}"
    missing = [field for field in BASE_FIELD_KEYS if field not in node]
    if missing:
        return f"sample_state_field_missing_base:{rel(path)}:{key}:{','.join(missing)}"
    return None


def check_sample(path: Path, sample: dict[str, Any]) -> str | None:
    if walk_keys(sample) & FORBIDDEN_KEYS:
        return f"forbidden_sample_key:{rel(path)}"
    if sample.get("primary_technology") != "8D_STATE_FIELD_PACKET":
        return f"sample_primary_technology_mismatch:{rel(path)}"
    if sample.get("final_authority") != "total_field_verifier":
        return f"sample_final_authority_mismatch:{rel(path)}"
    if sample.get("cloud_candidate_policy") != "CANDIDATE_ONLY_NO_AUTHORITY":
        return f"sample_cloud_candidate_policy_mismatch:{rel(path)}"
    if sample.get("adi_policy") != "ADI_5D_METRIC_INDEX_ONLY_NOT_8D_TABLE":
        return f"sample_adi_policy_mismatch:{rel(path)}"

    gt = sample.get("generative_transport", {})
    if not isinstance(gt, dict):
        return f"sample_gt_missing:{rel(path)}"
    if gt.get("mode") != "incomplete_information_equivalent_state_transmission":
        return f"sample_gt_mode_mismatch:{rel(path)}"
    if gt.get("full_data_required") is not False:
        return f"sample_gt_full_data_required_not_false:{rel(path)}"
    if gt.get("plaintext_required") is not False:
        return f"sample_gt_plaintext_required_not_false:{rel(path)}"

    for key in STATE_FIELD_KEYS:
        field_error = check_state_field_node(path, sample, key)
        if field_error:
            return field_error

    if path.name == "sample_xiaoj_block_unauthorized_door.json":
        if sample.get("total_field_decision") != "BLOCK":
            return "door_sample_not_block"
        expected = "小J問了總場小J前輩，他說沒有對方同意不能打開人家的門。需要小J幫您按電鈴或傳訊息嗎？"
        if expected not in str(sample.get("humanized_response", "")):
            return "door_sample_humanized_response_missing"
    return None


def main() -> int:
    targets = [DOC, SCHEMA, *SAMPLES]
    for path in targets:
        if not path.is_file():
            return fail(f"target_missing:{rel(path)}")
        scan_error = scan_text(path)
        if scan_error:
            return fail(scan_error)

    try:
        schema = read_json(SCHEMA)
        samples = {path: read_json(path) for path in SAMPLES}
    except ValueError as exc:
        return fail(str(exc))

    schema_error = check_schema(schema)
    if schema_error:
        return fail(schema_error)
    for path, sample in samples.items():
        if not isinstance(sample, dict):
            return fail(f"sample_not_object:{rel(path)}")
        sample_error = check_sample(path, sample)
        if sample_error:
            return fail(sample_error)

    print("STATE=PASS_8D_STATE_FIELD_METRIC_TENSOR_PACKET_VERIFY")
    print("JSON_PARSE=PASS")
    print("REDTEAM_CHECK=PASS")
    print(f"DOC={rel(DOC)}")
    print(f"SCHEMA={rel(SCHEMA)}")
    print("SAMPLES=" + ",".join(rel(path) for path in SAMPLES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
