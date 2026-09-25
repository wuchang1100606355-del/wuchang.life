#!/usr/bin/env python3
"""Fail-closed validator for the Total Field authority-binding schema candidate.

This module validates a candidate authority-binding object and its exact file
SHA-256.  It creates no authority instance, pointer, decision, receipt, seal,
canonical mutation, deployment, or runtime effect.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


VALIDATOR_VERSION = "w7tp-total-field-authority-binding-validator/1.0-candidate"
SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "field"
    / "w7tp_total_field_authority_binding_v1.schema.candidate.json"
)


class AuthorityBindingValidationError(ValueError):
    """Stable fail-closed authority-binding validation result."""

    def __init__(self, reason_code: str, path: str = "$") -> None:
        self.reason_code = reason_code
        self.path = path
        super().__init__(f"{reason_code}:{path}")


def _json_path(items: Any) -> str:
    return "$" + "".join(
        f"[{item}]" if isinstance(item, int) else f".{item}" for item in items
    )


def _load_json_object_bytes(raw: bytes, *, reason: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuthorityBindingValidationError(f"REJECT_{reason}_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise AuthorityBindingValidationError(f"REJECT_{reason}_OBJECT_REQUIRED")
    return value


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_schema(schema_path: Path = SCHEMA_PATH) -> dict[str, Any]:
    try:
        raw = schema_path.read_bytes()
    except OSError as exc:
        raise AuthorityBindingValidationError(
            "HOLD_AUTHORITY_BINDING_SCHEMA_MISSING", str(schema_path)
        ) from exc
    schema = _load_json_object_bytes(raw, reason="AUTHORITY_BINDING_SCHEMA")
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise AuthorityBindingValidationError(
            "REJECT_AUTHORITY_BINDING_SCHEMA_INVALID", str(schema_path)
        ) from exc
    return schema


def validate_authority_binding(
    value: dict[str, Any],
    *,
    required_effect: str | None = None,
    schema_path: Path = SCHEMA_PATH,
) -> dict[str, Any]:
    """Validate one candidate object against the shared P0 contract."""

    if not isinstance(value, dict):
        raise AuthorityBindingValidationError(
            "REJECT_AUTHORITY_BINDING_OBJECT_REQUIRED"
        )
    schema = load_schema(schema_path)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        raise AuthorityBindingValidationError(
            "REJECT_AUTHORITY_BINDING_SCHEMA",
            _json_path(errors[0].absolute_path),
        )
    if required_effect is not None:
        if not isinstance(required_effect, str) or not required_effect:
            raise AuthorityBindingValidationError(
                "REJECT_REQUIRED_EFFECT_INVALID", "$.required_effect"
            )
        prohibited_effects = value.get("prohibited_effects", [])
        if isinstance(prohibited_effects, dict):
            raise AuthorityBindingValidationError(
                "HOLD_AUTHORITY_PROHIBITED_EFFECTS_UNRESOLVED",
                "$.prohibited_effects",
            )
        if required_effect in prohibited_effects:
            raise AuthorityBindingValidationError(
                "HOLD_AUTHORITY_EFFECT_PROHIBITED", "$.prohibited_effects"
            )
        if required_effect not in value["allowed_effects"]:
            raise AuthorityBindingValidationError(
                "HOLD_AUTHORITY_EFFECT_NOT_ALLOWED", "$.allowed_effects"
            )
    return value


def validate_authority_binding_file(
    path: Path,
    *,
    expected_sha256: str | None = None,
    required_effect: str | None = None,
    schema_path: Path = SCHEMA_PATH,
) -> dict[str, Any]:
    """Validate exact file bytes and return a candidate-only verification record."""

    if path.is_symlink() or not path.is_file():
        raise AuthorityBindingValidationError(
            "HOLD_AUTHORITY_BINDING_FILE_MISSING_OR_SYMLINK", str(path)
        )
    raw = path.read_bytes()
    actual_sha256 = sha256_bytes(raw)
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise AuthorityBindingValidationError(
            "REJECT_AUTHORITY_BINDING_FILE_HASH_MISMATCH", str(path)
        )
    value = _load_json_object_bytes(raw, reason="AUTHORITY_BINDING")
    validate_authority_binding(
        value,
        required_effect=required_effect,
        schema_path=schema_path,
    )
    return {
        "state": "AUTHORITY_BINDING_CANDIDATE_VALID",
        "validator_version": VALIDATOR_VERSION,
        "authority_binding_ref": str(path),
        "authority_binding_sha256": actual_sha256,
        "required_effect": required_effect,
        "authority_effect": "NONE",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority-binding", type=Path, required=True)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--required-effect")
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = validate_authority_binding_file(
            args.authority_binding,
            expected_sha256=args.expected_sha256,
            required_effect=args.required_effect,
            schema_path=args.schema,
        )
    except AuthorityBindingValidationError as exc:
        print(
            json.dumps(
                {
                    "state": "HOLD_AUTHORITY_BINDING_INVALID",
                    "reason_code": exc.reason_code,
                    "path": exc.path,
                    "authority_effect": "NONE",
                },
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
