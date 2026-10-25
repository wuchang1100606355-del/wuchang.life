#!/usr/bin/env python3
"""Validate a candidate W7TP 8D Git sidecar index packet read-only."""

from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
OID_RE = {"sha1": re.compile(r"^[0-9a-f]{40}$"), "sha256": SHA256_RE}
OBJECT_TYPES = {"blob", "tree", "commit", "tag"}
OPERATIONS = {"LOOKUP", "PROJECT", "MATERIALIZE_CANDIDATE", "PACK_HINT"}
POLICIES = {"READ_ONLY_LOOKUP", "BUILD_SIDECAR_CANDIDATE", "ISOLATED_MATERIALIZE"}
FILE_MODES = {"100644", "100755", "120000", "160000"}
MAX_PACKET_BYTES = 1_048_576
MAX_SAFE_INTEGER = 9_007_199_254_740_991
CANONICAL_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
TOP_LEVEL_KEYS = {
    "schema_version",
    "packet_id",
    "packet_decision_index",
    "identity_root_ref",
    "seat_binding_ref",
    "receiver",
    "event",
    "D1",
    "D2",
    "D3",
    "D4",
    "D5",
    "D6",
    "D7",
    "D8",
}
OBJECT_KEYS = {
    "receiver": {"id", "version"},
    "event": {
        "logical_time",
        "prev_event_hash",
        "event_hash",
        "hash_contract",
        "nonce",
        "replay_guard_ref",
        "expiry",
    },
    "D1": {"intent_ref", "operation"},
    "D2": {
        "repo_namespace",
        "object_format",
        "object_type",
        "expected_size",
        "expected_git_oid",
        "acceptance",
    },
    "D3": {
        "base_commit_oid",
        "base_tree_oid",
        "path_bytes_b64",
        "file_mode",
        "lineage_event_ref",
    },
    "D4": {"source_object_oids", "source_manifest_sha256", "reconstruction_receipt_ref"},
    "D5": {"policy", "abort_conditions"},
    "D6": {"rule_refs", "lookup_closure", "acceptance", "verification_instruction"},
    "D7": {"missing_prerequisite", "max_reconstruction_depth", "max_output_bytes"},
    "D8": {"authority", "allowed_ref_prefix", "canonical_write", "promotion_receipt_required"},
}
D6_ENTRY_KEYS = {"ref", "sha256"}


class _DuplicateKey(ValueError):
    pass


class _NonJsonConstant(ValueError):
    pass


def _string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _closed_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateKey(key)
        value[key] = item
    return value


def _reject_json_constant(value: str) -> None:
    raise _NonJsonConstant(value)


def _decode_json(raw: bytes) -> Any:
    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_closed_object_pairs,
        parse_constant=_reject_json_constant,
    )


def _parse_canonical_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not CANONICAL_TIME_RE.fullmatch(value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _invalid_result(errors: list[str], acceptance: Any = None) -> dict[str, Any]:
    return {
        "state": "HOLD_8D_ADI_GIT_INDEX_INVALID",
        "errors": sorted(set(errors)),
        "acceptance": acceptance,
        "git_object_identity": "NEW_CANDIDATE_OR_UNVERIFIED",
        "canonical_state": "UNCHANGED",
        "authority": "CANDIDATE_ONLY",
        "receiver_authorization": "UNVERIFIED_EXTERNAL",
    }


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def compute_event_hash(document: dict[str, Any]) -> str:
    """Hash canonical packet JSON with event.event_hash excluded."""
    clone = copy.deepcopy(document)
    event = clone.get("event")
    if isinstance(event, dict):
        event.pop("event_hash", None)
    return hashlib.sha256(_canonical_json(clone)).hexdigest()


def validate(document: Any, now: datetime | None = None) -> dict[str, Any]:
    errors: list[str] = []

    def require(condition: bool, code: str) -> None:
        if not condition:
            errors.append(code)

    if not isinstance(document, dict):
        return _invalid_result(["DOCUMENT_OBJECT_REQUIRED"])

    require(set(document) == TOP_LEVEL_KEYS, "TOP_LEVEL_CLOSED_SCHEMA_FIELDS_INVALID")

    def object_field(key: str) -> dict[str, Any]:
        value = document.get(key)
        if not isinstance(value, dict):
            errors.append(f"{key.upper()}_OBJECT_INVALID")
            return {}
        require(set(value) == OBJECT_KEYS[key], f"{key.upper()}_CLOSED_SCHEMA_FIELDS_INVALID")
        return value

    require(document.get("schema_version") == "w7tp-8d-git-index/1.0", "SCHEMA_VERSION_INVALID")
    for key in ("packet_id", "packet_decision_index", "identity_root_ref", "seat_binding_ref"):
        require(_string(document.get(key)), f"{key.upper()}_MISSING")
    receiver = object_field("receiver")
    require(_string(receiver.get("id")), "RECEIVER_ID_MISSING")
    require(_string(receiver.get("version")), "RECEIVER_VERSION_MISSING")
    event = object_field("event")
    require(
        _integer(event.get("logical_time"))
        and 0 <= event.get("logical_time", -1) <= MAX_SAFE_INTEGER,
        "LOGICAL_TIME_INVALID",
    )
    require(is_sha256(event.get("event_hash")), "EVENT_HASH_INVALID")
    require(event.get("hash_contract") == "SHA256_CANONICAL_JSON_EXCLUDING_EVENT_HASH_V1", "EVENT_HASH_CONTRACT_INVALID")
    if is_sha256(event.get("event_hash")):
        try:
            computed_event_hash = compute_event_hash(document)
        except (TypeError, ValueError, UnicodeError, RecursionError):
            errors.append("EVENT_CANONICAL_JSON_INVALID")
        else:
            require(event["event_hash"] == computed_event_hash, "EVENT_HASH_MISMATCH")
    previous = event.get("prev_event_hash")
    require(previous is None or is_sha256(previous), "PREV_EVENT_HASH_INVALID")
    require(_string(event.get("nonce")), "NONCE_MISSING")
    require(_string(event.get("replay_guard_ref")), "REPLAY_GUARD_REF_MISSING")
    expiry = event.get("expiry")
    if expiry in (None, ""):
        errors.append("EXPIRY_MISSING")
    else:
        expires_at = _parse_canonical_time(expiry)
        if expires_at is None:
            errors.append("EXPIRY_INVALID")
        else:
            current = now or datetime.now(timezone.utc)
            if not isinstance(current, datetime) or current.tzinfo is None:
                errors.append("VALIDATION_TIME_TIMEZONE_MISSING")
            else:
                require(expires_at > current.astimezone(timezone.utc), "PACKET_EXPIRED")

    expected_fields = {f"D{number}" for number in range(1, 9)}
    require(expected_fields <= set(document), "D1_D8_FIELDS_MISSING")
    d1 = object_field("D1")
    require(d1.get("operation") in OPERATIONS, "D1_OPERATION_INVALID")
    require(_string(d1.get("intent_ref")), "D1_INTENT_REF_MISSING")

    d2 = object_field("D2")
    object_format = d2.get("object_format")
    object_type = d2.get("object_type")
    acceptance = d2.get("acceptance")
    require(_string(d2.get("repo_namespace")), "D2_REPO_NAMESPACE_MISSING")
    require(object_format in OID_RE, "D2_OBJECT_FORMAT_INVALID")
    require(object_type in OBJECT_TYPES, "D2_OBJECT_TYPE_INVALID")
    require(
        _integer(d2.get("expected_size"))
        and 0 <= d2.get("expected_size", -1) <= MAX_SAFE_INTEGER,
        "D2_EXPECTED_SIZE_INVALID",
    )
    require(acceptance in {"EXACT_BYTES", "EQUIVALENT_STATE"}, "D2_ACCEPTANCE_INVALID")
    expected_oid = d2.get("expected_git_oid")
    if acceptance == "EXACT_BYTES" and object_format in OID_RE:
        require(isinstance(expected_oid, str) and bool(OID_RE[object_format].fullmatch(expected_oid)), "D2_EXPECTED_OID_INVALID")
    if acceptance == "EQUIVALENT_STATE":
        require(expected_oid in (None, ""), "EQUIVALENT_STATE_CANNOT_REUSE_EXPECTED_OID")

    d3 = object_field("D3")
    if object_format in OID_RE:
        for field in ("base_commit_oid", "base_tree_oid"):
            value = d3.get(field)
            require(isinstance(value, str) and bool(OID_RE[object_format].fullmatch(value)), f"D3_{field.upper()}_INVALID")
    path_b64 = d3.get("path_bytes_b64")
    try:
        path_bytes = base64.b64decode(path_b64, validate=True) if isinstance(path_b64, str) else b""
    except (binascii.Error, ValueError):
        path_bytes = b""
    path_parts = path_bytes.split(b"/")
    require(
        bool(path_bytes)
        and b"\0" not in path_bytes
        and not path_bytes.startswith(b"/")
        and all(part not in {b"", b".", b".."} for part in path_parts),
        "D3_PATH_BYTES_INVALID",
    )
    require(d3.get("file_mode") in FILE_MODES, "D3_FILE_MODE_INVALID")
    require(_string(d3.get("lineage_event_ref")), "D3_LINEAGE_REF_MISSING")
    d4 = object_field("D4")
    require(is_sha256(d4.get("source_manifest_sha256")), "D4_SOURCE_MANIFEST_HASH_INVALID")
    source_oids = d4.get("source_object_oids")
    require(isinstance(source_oids, list) and bool(source_oids), "D4_SOURCE_OIDS_EMPTY")
    if isinstance(source_oids, list) and object_format in OID_RE:
        require(all(isinstance(value, str) and OID_RE[object_format].fullmatch(value) for value in source_oids), "D4_SOURCE_OID_INVALID")
    require(d4.get("reconstruction_receipt_ref") is None, "D4_RECONSTRUCTION_RECEIPT_NOT_NULL")

    d5 = object_field("D5")
    require(d5.get("policy") in POLICIES, "D5_POLICY_INVALID")
    abort_conditions = d5.get("abort_conditions")
    require(isinstance(abort_conditions, list) and bool(abort_conditions), "D5_ABORT_CONDITIONS_EMPTY")
    if isinstance(abort_conditions, list):
        require(all(_string(value) for value in abort_conditions), "D5_ABORT_CONDITIONS_INVALID")
    d6 = object_field("D6")
    require(d6.get("acceptance") == acceptance, "D6_ACCEPTANCE_MISMATCH")
    require(d6.get("verification_instruction") == "GIT_NATIVE_OID_TYPE_SIZE_AND_CONNECTIVITY", "D6_VERIFICATION_INVALID")
    for field in ("rule_refs", "lookup_closure"):
        entries = d6.get(field)
        require(isinstance(entries, list) and bool(entries), f"D6_{field.upper()}_EMPTY")
        if isinstance(entries, list):
            for item in entries:
                if isinstance(item, dict):
                    require(
                        set(item) == D6_ENTRY_KEYS,
                        f"D6_{field.upper()}_ENTRY_CLOSED_SCHEMA_FIELDS_INVALID",
                    )
            require(
                all(isinstance(item, dict) and _string(item.get("ref")) and is_sha256(item.get("sha256")) for item in entries),
                f"D6_{field.upper()}_UNPINNED",
            )

    d7 = object_field("D7")
    require(d7.get("missing_prerequisite") == "QUARANTINE", "D7_MISSING_POLICY_INVALID")
    require(_integer(d7.get("max_reconstruction_depth")) and 0 < d7.get("max_reconstruction_depth", 0) <= 4095, "D7_DEPTH_INVALID")
    require(
        _integer(d7.get("max_output_bytes"))
        and 0 < d7.get("max_output_bytes", 0) <= MAX_SAFE_INTEGER,
        "D7_OUTPUT_LIMIT_INVALID",
    )
    d8 = object_field("D8")
    require(d8.get("authority") == "CANDIDATE_ONLY", "D8_AUTHORITY_INVALID")
    require(d8.get("allowed_ref_prefix") == "refs/adi/candidates/", "D8_REF_PREFIX_INVALID")
    require(d8.get("canonical_write") is False, "D8_CANONICAL_WRITE_NOT_DENIED")
    require(d8.get("promotion_receipt_required") is True, "D8_PROMOTION_RECEIPT_NOT_REQUIRED")

    errors = sorted(set(errors))
    return {
        "state": "PASS_8D_ADI_GIT_INDEX_CANDIDATE" if not errors else "HOLD_8D_ADI_GIT_INDEX_INVALID",
        "errors": errors,
        "acceptance": acceptance,
        "git_object_identity": "EXACT" if acceptance == "EXACT_BYTES" and not errors else "NEW_CANDIDATE_OR_UNVERIFIED",
        "canonical_state": "UNCHANGED",
        "authority": "CANDIDATE_ONLY",
        "receiver_authorization": "UNVERIFIED_EXTERNAL",
    }


def main() -> int:
    if len(sys.argv) != 2:
        result = _invalid_result(["ONE_JSON_PATH_REQUIRED"])
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 2
    try:
        raw = Path(sys.argv[1]).read_bytes()
    except OSError as exc:
        result = _invalid_result([f"INPUT_READ_FAILED:{type(exc).__name__}"])
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 2
    if len(raw) > MAX_PACKET_BYTES:
        result = _invalid_result(["INPUT_TOO_LARGE"])
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 2
    try:
        document = _decode_json(raw)
    except _DuplicateKey:
        result = _invalid_result(["INPUT_JSON_INVALID:DUPLICATE_KEY"])
    except _NonJsonConstant:
        result = _invalid_result(["INPUT_JSON_INVALID:NON_JSON_CONSTANT"])
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError):
        result = _invalid_result(["INPUT_JSON_INVALID"])
    else:
        try:
            canonical = _canonical_json(document) + b"\n"
        except (TypeError, ValueError, UnicodeError, RecursionError):
            result = _invalid_result(["INPUT_CANONICAL_JSON_INVALID"])
        else:
            result = (
                validate(document)
                if raw == canonical
                else _invalid_result(["INPUT_BYTES_NOT_CANONICAL_JSON"])
            )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0 if not result["errors"] else 2


if __name__ == "__main__":
    sys.exit(main())
