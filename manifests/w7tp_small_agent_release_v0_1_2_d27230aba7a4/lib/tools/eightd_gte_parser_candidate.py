"""Deterministic parser for the candidate 8D-GTE representation contract.

The parser treats every document as data.  It validates a caller-owned mapping
or a UTF-8 JSON document, produces a canonical representation, and derives a
SHA-256 candidate identifier without interpreting document content.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn, TypeAlias, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError


JSONScalar: TypeAlias = None | bool | int | float | str
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]

DEFAULT_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "schemas"
    / "field"
    / "8d_governance_tensor_expression_candidate.schema.json"
)
_DIMENSION_KEYS = tuple(f"D{index}_ref" for index in range(1, 9))


class GTECandidateParseError(ValueError):
    """Report one stable parser failure without retaining caller content."""

    def __init__(self, reason_code: str, path: str, detail: str) -> None:
        """Create an error with a stable code, data path, and safe detail."""

        self.reason_code = reason_code
        self.path = path
        self.detail = detail
        super().__init__(f"{reason_code}:{path}:{detail}")


class _DuplicateKeyError(ValueError):
    """Carry a duplicate key from the strict JSON object hook."""

    def __init__(self, key: str) -> None:
        """Record the repeated member name without retaining its value."""

        self.key = key
        super().__init__(key)


@dataclass(frozen=True, slots=True)
class Parsed8DGTECandidate:
    """Immutable parse result backed by canonical JSON text."""

    canonical_payload: str
    candidate_hash: str
    schema_version: str
    lifecycle: str

    @property
    def payload(self) -> dict[str, JSONValue]:
        """Return a fresh document so consumers cannot alter parser state."""

        value = cast(JSONValue, json.loads(self.canonical_payload))
        if not isinstance(value, dict):
            raise GTECandidateParseError(
                "GTE_INTERNAL_CANONICAL_TYPE",
                "$",
                "canonical document is not an object",
            )
        return value

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a fresh validated document."""

        return self.payload


def _strict_object(pairs: list[tuple[str, JSONValue]]) -> dict[str, JSONValue]:
    """Build one JSON object while rejecting duplicate member names."""

    result: dict[str, JSONValue] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(key)
        result[key] = value
    return result


def _reject_non_finite_token(token: str) -> NoReturn:
    """Reject the non-standard numeric constants accepted by default."""

    raise GTECandidateParseError(
        "GTE_NON_FINITE_NUMBER",
        "$",
        f"non-finite numeric token {token!r} is forbidden",
    )


def _data_path(parts: list[str | int]) -> str:
    """Render a deterministic JSON-style path."""

    rendered = "$"
    for part in parts:
        if isinstance(part, int):
            rendered += f"[{part}]"
        else:
            rendered += f"[{json.dumps(part, ensure_ascii=False)}]"
    return rendered


def _validate_json_value(
    value: object,
    *,
    parts: list[str | int],
    ancestors: set[int],
) -> None:
    """Validate the exact JSON-compatible value subset accepted by the parser."""

    if value is None or isinstance(value, (bool, str, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise GTECandidateParseError(
                "GTE_NON_FINITE_NUMBER",
                _data_path(parts),
                "non-finite numbers are forbidden",
            )
        return
    if isinstance(value, list):
        identity = id(value)
        if identity in ancestors:
            raise GTECandidateParseError(
                "GTE_CYCLIC_VALUE",
                _data_path(parts),
                "cyclic containers are not JSON-compatible",
            )
        ancestors.add(identity)
        for index, item in enumerate(value):
            _validate_json_value(
                item,
                parts=[*parts, index],
                ancestors=ancestors,
            )
        ancestors.remove(identity)
        return
    if isinstance(value, dict):
        identity = id(value)
        if identity in ancestors:
            raise GTECandidateParseError(
                "GTE_CYCLIC_VALUE",
                _data_path(parts),
                "cyclic containers are not JSON-compatible",
            )
        ancestors.add(identity)
        for key, item in value.items():
            if not isinstance(key, str):
                raise GTECandidateParseError(
                    "GTE_NON_STRING_KEY",
                    _data_path(parts),
                    "JSON object keys must be strings",
                )
            _validate_json_value(
                item,
                parts=[*parts, key],
                ancestors=ancestors,
            )
        ancestors.remove(identity)
        return
    raise GTECandidateParseError(
        "GTE_NON_JSON_VALUE",
        _data_path(parts),
        f"unsupported value type {type(value).__name__}",
    )


def canonical_json(value: JSONValue) -> str:
    """Serialize one validated JSON-compatible value deterministically."""

    _validate_json_value(value, parts=[], ancestors=set())
    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise GTECandidateParseError(
            "GTE_CANONICALIZATION_FAILED",
            "$",
            type(error).__name__,
        ) from error


def candidate_hash_for(payload: dict[str, JSONValue]) -> str:
    """Return the lowercase SHA-256 digest of a canonical candidate document."""

    canonical_payload = canonical_json(payload)
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def _load_json_document(text: str) -> JSONValue:
    """Decode strict JSON with duplicate and non-finite number rejection."""

    try:
        return cast(
            JSONValue,
            json.loads(
                text,
                object_pairs_hook=_strict_object,
                parse_constant=_reject_non_finite_token,
            ),
        )
    except _DuplicateKeyError as error:
        raise GTECandidateParseError(
            "GTE_DUPLICATE_KEY",
            "$",
            "duplicate member is forbidden",
        ) from error
    except json.JSONDecodeError as error:
        raise GTECandidateParseError(
            "GTE_INVALID_JSON",
            "$",
            f"line={error.lineno},column={error.colno}",
        ) from error


def _schema_error_path(error: ValidationError) -> str:
    """Return a stable path for one schema validation error."""

    return _data_path([cast(str | int, part) for part in error.absolute_path])


def _schema_error_sort_key(error: ValidationError) -> tuple[list[str], str, str]:
    """Provide deterministic ordering when a document has several errors."""

    path = [str(part) for part in error.absolute_path]
    return path, str(error.validator), error.message


def _schema_reason_code(error: ValidationError) -> str:
    """Map schema keywords to stable public parser reason codes."""

    if error.validator == "additionalProperties":
        return "GTE_EXTRA_FIELD"
    if error.validator == "required":
        if tuple(error.absolute_path) == ("dimensions",):
            return "GTE_MISSING_DIMENSION"
        return "GTE_REQUIRED_FIELD_MISSING"
    if error.validator == "const" and tuple(error.absolute_path) == (
        "schema_version",
    ):
        return "GTE_SCHEMA_VERSION_UNSUPPORTED"
    if error.validator == "enum" and tuple(error.absolute_path) == ("lifecycle",):
        return "GTE_LIFECYCLE_UNSUPPORTED"
    return "GTE_SCHEMA_VALIDATION_FAILED"


def _enforce_lifecycle_invariants(payload: dict[str, JSONValue]) -> None:
    """Enforce lifecycle rules with stable, domain-specific reason codes."""

    dimensions = payload.get("dimensions")
    if isinstance(dimensions, dict):
        missing = [key for key in _DIMENSION_KEYS if key not in dimensions]
        if missing:
            raise GTECandidateParseError(
                "GTE_MISSING_DIMENSION",
                '$["dimensions"]',
                f"missing {','.join(missing)}",
            )

    lifecycle = payload.get("lifecycle")
    verification = payload.get("verification")
    if lifecycle == "CANDIDATE" and isinstance(verification, dict):
        if verification.get("commit_applied") is True:
            raise GTECandidateParseError(
                "GTE_CANDIDATE_COMMIT_FORBIDDEN",
                '$["verification"]["commit_applied"]',
                "candidate lifecycle cannot commit",
            )
        if verification.get("final_decision") == "ALLOW":
            raise GTECandidateParseError(
                "GTE_CANDIDATE_ALLOW_FORBIDDEN",
                '$["verification"]["final_decision"]',
                "candidate lifecycle cannot claim ALLOW",
            )
        if payload.get("tfs_result") is not None:
            raise GTECandidateParseError(
                "GTE_CANDIDATE_TFS_FORBIDDEN",
                '$["tfs_result"]',
                "candidate lifecycle cannot provide a TFS result",
            )

    if lifecycle == "COMMITTED":
        if not isinstance(verification, dict):
            return
        if verification.get("final_decision") != "ALLOW":
            raise GTECandidateParseError(
                "GTE_COMMITTED_REQUIRES_ALLOW",
                '$["verification"]["final_decision"]',
                "committed lifecycle requires ALLOW",
            )
        if verification.get("commit_applied") is not True:
            raise GTECandidateParseError(
                "GTE_COMMITTED_REQUIRES_COMMIT",
                '$["verification"]["commit_applied"]',
                "committed lifecycle requires commit_applied=true",
            )
        if payload.get("fixed_point_status") != "REACHED":
            raise GTECandidateParseError(
                "GTE_COMMITTED_REQUIRES_FIXED_POINT",
                '$["fixed_point_status"]',
                "committed lifecycle requires REACHED",
            )
        if not isinstance(payload.get("tfs_result"), dict):
            raise GTECandidateParseError(
                "GTE_COMMITTED_REQUIRES_TFS",
                '$["tfs_result"]',
                "committed lifecycle requires a TFS result",
            )


class EightDGTEParserCandidate:
    """Parse and validate candidate 8D-GTE documents against Draft 2020-12."""

    def __init__(self, schema_path: str | Path | None = None) -> None:
        """Load and check one schema without installing global mutable state."""

        self.schema_path = Path(schema_path) if schema_path else DEFAULT_SCHEMA_PATH
        self._validator = self._load_validator(self.schema_path)

    @staticmethod
    def _load_validator(schema_path: Path) -> Draft202012Validator:
        """Load the configured schema and return a checked validator."""

        try:
            raw = schema_path.read_bytes()
        except FileNotFoundError as error:
            raise GTECandidateParseError(
                "GTE_SCHEMA_NOT_FOUND",
                "$",
                str(schema_path),
            ) from error
        except OSError as error:
            raise GTECandidateParseError(
                "GTE_SCHEMA_READ_FAILED",
                "$",
                type(error).__name__,
            ) from error
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise GTECandidateParseError(
                "GTE_SCHEMA_INVALID_UTF8",
                "$",
                str(schema_path),
            ) from error
        try:
            schema_value = _load_json_document(text)
        except GTECandidateParseError as error:
            raise GTECandidateParseError(
                "GTE_SCHEMA_INVALID_JSON",
                "$",
                error.reason_code,
            ) from error
        if not isinstance(schema_value, dict):
            raise GTECandidateParseError(
                "GTE_SCHEMA_NOT_OBJECT",
                "$",
                str(schema_path),
            )
        try:
            Draft202012Validator.check_schema(schema_value)
        except SchemaError as error:
            raise GTECandidateParseError(
                "GTE_SCHEMA_INVALID",
                "$",
                error.message,
            ) from error
        return Draft202012Validator(schema_value)

    def parse_dict(self, payload: dict[str, JSONValue]) -> Parsed8DGTECandidate:
        """Validate a mapping and return a detached deterministic parse result."""

        if not isinstance(payload, dict):
            raise GTECandidateParseError(
                "GTE_INPUT_NOT_OBJECT",
                "$",
                "input must be a dict",
            )
        _validate_json_value(payload, parts=[], ancestors=set())
        detached = cast(dict[str, JSONValue], copy.deepcopy(payload))
        _enforce_lifecycle_invariants(detached)
        errors = sorted(
            self._validator.iter_errors(detached),
            key=_schema_error_sort_key,
        )
        if errors:
            error = errors[0]
            raise GTECandidateParseError(
                _schema_reason_code(error),
                _schema_error_path(error),
                f"schema keyword {error.validator}",
            ) from error
        canonical_payload = canonical_json(detached)
        digest = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
        return Parsed8DGTECandidate(
            canonical_payload=canonical_payload,
            candidate_hash=digest,
            schema_version=cast(str, detached["schema_version"]),
            lifecycle=cast(str, detached["lifecycle"]),
        )

    def parse_file(self, path: str | Path) -> Parsed8DGTECandidate:
        """Decode one strict UTF-8 JSON file and validate its candidate document."""

        source = Path(path)
        try:
            raw = source.read_bytes()
        except FileNotFoundError as error:
            raise GTECandidateParseError(
                "GTE_FILE_NOT_FOUND",
                "$",
                str(source),
            ) from error
        except OSError as error:
            raise GTECandidateParseError(
                "GTE_FILE_READ_FAILED",
                "$",
                type(error).__name__,
            ) from error
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise GTECandidateParseError(
                "GTE_INVALID_UTF8",
                "$",
                str(source),
            ) from error
        value = _load_json_document(text)
        if not isinstance(value, dict):
            raise GTECandidateParseError(
                "GTE_INPUT_NOT_OBJECT",
                "$",
                "document root must be an object",
            )
        return self.parse_dict(value)


def parse_8d_gte_candidate(
    payload: dict[str, JSONValue],
    *,
    schema_path: str | Path | None = None,
) -> Parsed8DGTECandidate:
    """Validate one caller-owned candidate mapping with a fresh parser."""

    return EightDGTEParserCandidate(schema_path).parse_dict(payload)


def parse_8d_gte_candidate_file(
    path: str | Path,
    *,
    schema_path: str | Path | None = None,
) -> Parsed8DGTECandidate:
    """Validate one strict UTF-8 JSON candidate file with a fresh parser."""

    return EightDGTEParserCandidate(schema_path).parse_file(path)


__all__ = [
    "DEFAULT_SCHEMA_PATH",
    "EightDGTEParserCandidate",
    "GTECandidateParseError",
    "JSONValue",
    "Parsed8DGTECandidate",
    "candidate_hash_for",
    "canonical_json",
    "parse_8d_gte_candidate",
    "parse_8d_gte_candidate_file",
]
