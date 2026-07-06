#!/usr/bin/env python3
"""Validate product intent dry-run JSON with local schema and safety checks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas" / "intent_field"
SECRET_PATTERN = re.compile(
    r"sk-[A-Za-z0-9_-]{20,}|xox[baprs]-|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(api[_-]?key|secret|token|password|db_password)\s*[:=]\s*['\"][^'\"]{8,}",
    re.IGNORECASE,
)
MEMBER_ID_PATTERN = re.compile(r"(?<![A-Za-z0-9])[A-Z][12][0-9]{8}(?![A-Za-z0-9])")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate product intent dry-run result JSON.")
    parser.add_argument("--input", required=True, help="P0 result JSON path.")
    parser.add_argument("--out", help="Optional validation report JSON path.")
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_schema(name: str) -> dict[str, Any]:
    return load_json(SCHEMA_DIR / name)


def type_ok(value: Any, expected: str) -> bool:
    checks = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "boolean": lambda item: isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
    }
    return checks.get(expected, lambda _item: True)(value)


def validate_basic_schema(data: dict[str, Any], schema: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    for key in schema.get("required", []):
        if key not in data:
            errors.append(f"{label}.{key}=MISSING")

    properties = schema.get("properties", {})
    for key, rules in properties.items():
        if key not in data:
            continue
        value = data[key]
        if "type" in rules and not type_ok(value, str(rules["type"])):
            errors.append(f"{label}.{key}=TYPE_FAIL")
        if "const" in rules and value != rules["const"]:
            errors.append(f"{label}.{key}=CONST_FAIL")
        if "enum" in rules and value not in rules["enum"]:
            errors.append(f"{label}.{key}=ENUM_FAIL")
        if "pattern" in rules and isinstance(value, str) and not re.search(str(rules["pattern"]), value):
            errors.append(f"{label}.{key}=PATTERN_FAIL")
        if "minLength" in rules and isinstance(value, str) and len(value) < int(rules["minLength"]):
            errors.append(f"{label}.{key}=MIN_LENGTH_FAIL")
        if "minItems" in rules and isinstance(value, list) and len(value) < int(rules["minItems"]):
            errors.append(f"{label}.{key}=MIN_ITEMS_FAIL")
    return errors


def iter_values(data: Any) -> list[Any]:
    values: list[Any] = [data]
    if isinstance(data, dict):
        for value in data.values():
            values.extend(iter_values(value))
    elif isinstance(data, list):
        for value in data:
            values.extend(iter_values(value))
    return values


def no_side_effect_flags(data: Any) -> bool:
    if isinstance(data, dict):
        for key, value in data.items():
            if key in {"db_write", "deploy", "restart"} and value is not False:
                return False
            if not no_side_effect_flags(value):
                return False
    elif isinstance(data, list):
        return all(no_side_effect_flags(item) for item in data)
    return True


def h64_td_ref_only(data: Any) -> bool:
    allowed = {"trade_secret_ref:h64_codebook", "trade_secret_ref:td_hash_runtime"}
    for value in iter_values(data):
        if not isinstance(value, str):
            continue
        lowered = value.lower()
        if "h64" not in lowered and "td_hash" not in lowered:
            continue
        if value not in allowed:
            return False
    return True


def run_validation(input_path: Path) -> dict[str, Any]:
    result = load_json(input_path)
    text = input_path.read_text(encoding="utf-8", errors="ignore")
    request_schema = load_schema("product_intent_dry_run_request.schema.json")
    packet_schema = load_schema("product_intent_state_packet.schema.json")
    result_schema = load_schema("product_intent_dry_run_result.schema.json")

    errors: list[str] = []
    if not isinstance(result, dict):
        errors.append("result=NOT_OBJECT")
        return {"input": str(input_path), "schema_validation": "FAIL", "errors": errors}

    request = result.get("request", {})
    packet = result.get("state_packet", {})
    errors.extend(validate_basic_schema(result, result_schema, "result"))
    errors.extend(validate_basic_schema(request, request_schema, "request") if isinstance(request, dict) else ["request=NOT_OBJECT"])
    errors.extend(validate_basic_schema(packet, packet_schema, "state_packet") if isinstance(packet, dict) else ["state_packet=NOT_OBJECT"])

    if SECRET_PATTERN.search(text):
        errors.append("secret_scan=FAIL")
    if MEMBER_ID_PATTERN.search(text):
        errors.append("member_plaintext_scan=FAIL")
    if not no_side_effect_flags(result):
        errors.append("side_effect_flags=FAIL")
    if not h64_td_ref_only(result):
        errors.append("h64_td_ref_only=FAIL")
    drift_terms = ["八" + "欄位", "政府" + r"\s*ADI"]
    if re.search("|".join(drift_terms), text):
        errors.append("field_or_adi_drift=FAIL")

    return {
        "input": str(input_path),
        "schema_validation": "PASS" if not errors else "FAIL",
        "request_schema": "PASS" if not any(error.startswith("request.") or error.startswith("request=") for error in errors) else "FAIL",
        "state_packet_schema": "PASS" if not any(error.startswith("state_packet.") or error.startswith("state_packet=") for error in errors) else "FAIL",
        "result_schema": "PASS" if not any(error.startswith("result.") or error.startswith("result=") for error in errors) else "FAIL",
        "no_secret": SECRET_PATTERN.search(text) is None,
        "no_member_plaintext": MEMBER_ID_PATTERN.search(text) is None,
        "h64_td_ref_only": h64_td_ref_only(result),
        "no_db_write": no_side_effect_flags(result),
        "no_deploy": no_side_effect_flags(result),
        "no_restart": no_side_effect_flags(result),
        "errors": errors,
    }


def main() -> int:
    args = parse_args()
    report = run_validation(Path(args.input))
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if report["schema_validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
