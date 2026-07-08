#!/usr/bin/env python3
"""Read-only verifier for the W7TP property sovereign AI amplification packet."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/total_field/W7TP_PROPERTY_MODULE_SOVEREIGN_AI_AMPLIFICATION_SPEC.md"
SCHEMA = ROOT / "schemas/field/w7tp_property_sovereign_ai_amplification.schema.json"
RUN_ROOT = ROOT / "runtime/total_field/property_sovereign_ai_amplification"
VERIFY_SCRIPT = ROOT / "scripts/verify/verify_property_sovereign_ai_amplification.py"

SAMPLE_NAMES = [
    "sample_visitor_lobby_xiaoj.json",
    "sample_unauthorized_door_open.json",
    "sample_management_committee_hold.json",
]

FORBIDDEN_SCHEMA_KEYS = {
    "raw_api_key",
    "raw_token",
    "password",
    "plaintext_member_data",
    "resident_plaintext",
    "raw_image_export",
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

EXECUTION_PATTERNS = [
    re.compile(r"docker\s+compose\s+restart", re.IGNORECASE),
    re.compile(r"systemctl\s+restart", re.IGNORECASE),
    re.compile(r"kubectl\s+apply", re.IGNORECASE),
    re.compile(r"\bdeploy\b", re.IGNORECASE),
    re.compile(r"router\s+write", re.IGNORECASE),
    re.compile(r"psql\b.*\b(INSERT|UPDATE|DELETE)\b", re.IGNORECASE),
]


def fail(reason: str) -> int:
    print("STATE=HOLD_PROPERTY_SOVEREIGN_AI_AMPLIFICATION_VERIFY")
    print(f"REASON={reason}")
    return 1


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - exact message is environment-specific
        raise ValueError(f"json_parse_failed:{path}:{exc}") from exc


def latest_run_dir() -> Path:
    if not RUN_ROOT.is_dir():
        raise ValueError("run_root_missing")
    runs = sorted(path for path in RUN_ROOT.iterdir() if path.is_dir())
    if not runs:
        raise ValueError("run_dir_missing")
    return runs[-1]


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
    prop = props.get(name, {})
    if not isinstance(prop, dict):
        return None
    return prop.get("const")


def scan_text_files(paths: list[Path]) -> str | None:
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for term in FORBIDDEN_TEXT:
            if term in text:
                return f"forbidden_definition_term:{path}:{term}"
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                return f"secret_pattern:{path}"
        for pattern in EXECUTION_PATTERNS:
            if pattern.search(text) and "NO_DEPLOY" not in text:
                return f"execution_pattern:{path}:{pattern.pattern}"
    return None


def check_schema(schema: dict[str, Any]) -> str | None:
    keys = walk_keys(schema)
    bad_keys = sorted(keys & FORBIDDEN_SCHEMA_KEYS)
    if bad_keys:
        return "forbidden_schema_keys:" + ",".join(bad_keys)
    required_consts = {
        "final_authority": "total_field_verifier",
        "management_committee_authorization_status": "HOLD_UNTIL_AUTHORIZED",
        "raw_image_policy": "LOCAL_ONLY_NO_CLOUD_NO_TOTAL_FIELD",
        "cloud_candidate_policy": "CANDIDATE_ONLY_NO_AUTHORITY",
    }
    for key, expected in required_consts.items():
        if property_const(schema, key) != expected:
            return f"schema_const_mismatch:{key}"
    return None


def check_sample(sample: dict[str, Any], name: str) -> str | None:
    required_values = {
        "final_authority": "total_field_verifier",
        "management_committee_authorization_status": "HOLD_UNTIL_AUTHORIZED",
        "raw_image_policy": "LOCAL_ONLY_NO_CLOUD_NO_TOTAL_FIELD",
        "cloud_candidate_policy": "CANDIDATE_ONLY_NO_AUTHORITY",
    }
    for key, expected in required_values.items():
        if sample.get(key) != expected:
            return f"sample_const_mismatch:{name}:{key}"
    if name == "sample_unauthorized_door_open.json":
        if sample.get("total_field_decision") != "BLOCK":
            return "unauthorized_sample_not_block"
        expected = "小J問了總場小J前輩，他說沒有對方同意不能打開人家的門。需要小J幫您按電鈴或傳訊息嗎？"
        if expected not in str(sample.get("humanized_response", "")):
            return "unauthorized_sample_missing_humanized_response"
    if name == "sample_management_committee_hold.json":
        if sample.get("public_projection") != "STRUCTURE_ONLY":
            return "committee_sample_public_projection_not_structure_only"
    return None


def main() -> int:
    if not DOC.is_file():
        return fail("doc_missing")
    if not SCHEMA.is_file():
        return fail("schema_missing")
    if not VERIFY_SCRIPT.is_file():
        return fail("verify_script_missing")

    try:
        run_dir = latest_run_dir()
        sample_paths = [run_dir / "samples" / name for name in SAMPLE_NAMES]
        for path in sample_paths:
            if not path.is_file():
                return fail(f"sample_missing:{path.name}")

        schema = load_json(SCHEMA)
        samples = {path.name: load_json(path) for path in sample_paths}
    except ValueError as exc:
        return fail(str(exc))

    text_error = scan_text_files([DOC, SCHEMA, *sample_paths])
    if text_error:
        return fail(text_error)

    schema_error = check_schema(schema)
    if schema_error:
        return fail(schema_error)

    for name, sample in samples.items():
        sample_error = check_sample(sample, name)
        if sample_error:
            return fail(sample_error)

    print("STATE=PASS_PROPERTY_SOVEREIGN_AI_AMPLIFICATION_VERIFY")
    print(f"RUN_ID={run_dir.name}")
    print("JSON_PARSE=PASS")
    print("REDTEAM_CHECK=PASS")
    print("SAFETY=NO_SECRET_NO_MEMBER_PLAINTEXT_NO_RESIDENT_PLAINTEXT_NO_RAW_IMAGE_NO_DB_WRITE_NO_DEPLOY_NO_RESTART_NO_ROUTER_WRITE_NO_OVERWRITE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
