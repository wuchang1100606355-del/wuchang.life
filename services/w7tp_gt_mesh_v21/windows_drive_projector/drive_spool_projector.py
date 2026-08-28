#!/usr/bin/env python3
"""Project immutable W7TP v2.1 JSON artifacts from a local spool to Drive.

This module intentionally uses only the Python standard library.  It does not
inspect a version-control repository and it never treats the Drive projection
as authority or live-effect evidence.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import stat
import sys
import time
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


ENVELOPE_SCHEMA_ID = "W7TP_DRIVE_PROJECTION_ENVELOPE_V21"
RECEIPT_SCHEMA_ID = "W7TP_CLOUD_WRITE_RECEIPT_V21"
CANONICALIZATION_ID = "UTF8_NFC_SORTED_KEYS_COMPACT_JSON_V1"

ALLOWED_PARTITIONS = frozenset(
    {
        "00_CONTROL",
        "01_NODE_INDEX",
        "02_FILE_INDEX",
        "03_LINEAGE",
        "04_EVIDENCE",
        "05_CONFLICT",
        "06_RECONSTRUCTION",
        "07_GITHUB",
        "08_RECEIPTS",
        "99_QUARANTINE",
    }
)

ENVELOPE_FIELDS = frozenset(
    {
        "schema_id",
        "projection_relative_path",
        "artifact_sha256",
        "artifact",
        "source_node_ref",
        "packet_id",
        "logical_time",
        "created_at",
        "envelope_sha256",
    }
)

HEX_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RESERVED_WINDOWS_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)
RECEIPT_PREFIX = "CLOUD_WRITE_RECEIPT_"
DEFAULT_MAX_ENVELOPE_BYTES = 16 * 1024 * 1024


class ProjectorError(Exception):
    """Base error with a stable non-secret code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class SetupHold(ProjectorError):
    """The projector cannot safely start with the supplied coordinates."""


class EnvelopeRejected(ProjectorError):
    """An envelope fails the bounded v2.1 input contract."""


class ProjectionHold(ProjectorError):
    """A projection cannot continue without overwrite or ambiguity."""


@dataclasses.dataclass(frozen=True)
class ValidEnvelope:
    envelope_path: Path
    envelope_spool_relative_path: str
    envelope_file_sha256: str
    envelope_sha256: str
    projection_relative_path: PurePosixPath
    artifact_sha256: str
    artifact_bytes: bytes
    source_node_ref: str
    packet_id: str
    logical_time: Any
    created_at: str


@dataclasses.dataclass(frozen=True)
class WriteResult:
    state: str
    byte_count: int


@dataclasses.dataclass(frozen=True)
class EnvelopeResult:
    envelope_file: str
    state: str
    code: str
    artifact_write_state: Optional[str] = None
    local_receipt_state: Optional[str] = None
    drive_receipt_state: Optional[str] = None
    projection_relative_path: Optional[str] = None
    receipt_id: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class RunSummary:
    state: str
    processed: int
    passed: int
    held: int
    results: Tuple[EnvelopeResult, ...]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "processed": self.processed,
            "passed": self.passed,
            "held": self.held,
            "authority": "NOT_ESTABLISHED",
            "live_effect": "NOT_ESTABLISHED",
            "drive_role": "PROJECTION_SINK_ONLY",
            "results": [dataclasses.asdict(item) for item in self.results],
        }


def _reject_json_constant(_value: str) -> None:
    raise ValueError("NON_FINITE_JSON_NUMBER")


def _object_without_duplicate_keys(pairs: Iterable[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def strict_json_loads(raw: bytes) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EnvelopeRejected("ENVELOPE_NOT_UTF8") from exc
    try:
        return json.loads(
            text,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_object_without_duplicate_keys,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        code = str(exc) if str(exc) in {"NON_FINITE_JSON_NUMBER", "DUPLICATE_JSON_KEY"} else "ENVELOPE_INVALID_JSON"
        raise EnvelopeRejected(code) from exc


def canonical_json_bytes(value: Any) -> bytes:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EnvelopeRejected("VALUE_NOT_CANONICAL_JSON") from exc
    if unicodedata.normalize("NFC", encoded.decode("utf-8")) != encoded.decode("utf-8"):
        raise EnvelopeRejected("JSON_TEXT_NOT_NFC")
    return encoded


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_plain_string(document: Mapping[str, Any], key: str, maximum: int = 512) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise EnvelopeRejected(f"INVALID_{key.upper()}")
    if any(ord(char) < 0x20 for char in value):
        raise EnvelopeRejected(f"INVALID_{key.upper()}")
    if unicodedata.normalize("NFC", value) != value:
        raise EnvelopeRejected(f"NON_NFC_{key.upper()}")
    return value


def _validate_created_at(value: str) -> None:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EnvelopeRejected("INVALID_CREATED_AT") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EnvelopeRejected("CREATED_AT_MISSING_TIMEZONE")


def validate_projection_path(raw_path: Any) -> PurePosixPath:
    if not isinstance(raw_path, str) or not raw_path or len(raw_path) > 1024:
        raise EnvelopeRejected("INVALID_PROJECTION_RELATIVE_PATH")
    if unicodedata.normalize("NFC", raw_path) != raw_path:
        raise EnvelopeRejected("PROJECTION_PATH_NOT_NFC")
    if "\\" in raw_path or "\x00" in raw_path or raw_path.startswith("/") or raw_path.endswith("/"):
        raise EnvelopeRejected("PROJECTION_PATH_NOT_CANONICAL_POSIX_RELATIVE")
    raw_parts = raw_path.split("/")
    if not raw_parts or any(part in {"", ".", ".."} for part in raw_parts):
        raise EnvelopeRejected("PROJECTION_PATH_TRAVERSAL_OR_EMPTY_SEGMENT")
    for part in raw_parts:
        if part.endswith((" ", ".")) or ":" in part or any(ord(char) < 0x20 for char in part):
            raise EnvelopeRejected("PROJECTION_PATH_WINDOWS_UNSAFE_SEGMENT")
        device_stem = part.split(".", 1)[0].upper()
        if device_stem in RESERVED_WINDOWS_NAMES:
            raise EnvelopeRejected("PROJECTION_PATH_WINDOWS_RESERVED_NAME")
    if raw_parts[0] not in ALLOWED_PARTITIONS:
        raise EnvelopeRejected("PROJECTION_PARTITION_NOT_ALLOWLISTED")
    if raw_parts[0] == "08_RECEIPTS" and raw_parts[-1].casefold().startswith(RECEIPT_PREFIX.casefold()):
        raise EnvelopeRejected("PROJECTOR_RECEIPT_TARGET_RESERVED")
    return PurePosixPath(*raw_parts)


def _validate_github_gate(path: PurePosixPath, artifact: Any) -> None:
    if path.parts[0] != "07_GITHUB":
        return
    if not isinstance(artifact, dict):
        raise EnvelopeRejected("GITHUB_D4_ARTIFACT_NOT_OBJECT")
    if artifact.get("dimension") != "D4_EVIDENCE":
        raise EnvelopeRejected("GITHUB_PROJECTION_NOT_D4_EVIDENCE")
    if artifact.get("authority_state") != "EVIDENCE_ONLY":
        raise EnvelopeRejected("GITHUB_PROJECTION_AUTHORITY_GATE_FAILED")
    if artifact.get("live_effect_state") != "NOT_ESTABLISHED_BY_GIT":
        raise EnvelopeRejected("GITHUB_PROJECTION_LIVE_EFFECT_GATE_FAILED")


def validate_envelope(
    envelope_path: Path,
    raw: bytes,
    envelope_spool_relative_path: Optional[str] = None,
) -> ValidEnvelope:
    document = strict_json_loads(raw)
    if not isinstance(document, dict):
        raise EnvelopeRejected("ENVELOPE_NOT_OBJECT")
    keys = frozenset(document.keys())
    if keys != ENVELOPE_FIELDS:
        raise EnvelopeRejected("ENVELOPE_FIELDS_NOT_EXACT_V21")
    if document.get("schema_id") != ENVELOPE_SCHEMA_ID:
        raise EnvelopeRejected("ENVELOPE_SCHEMA_ID_MISMATCH")

    supplied_envelope_sha256 = document.get("envelope_sha256")
    supplied_artifact_sha256 = document.get("artifact_sha256")
    if not isinstance(supplied_envelope_sha256, str) or not HEX_SHA256_RE.fullmatch(supplied_envelope_sha256):
        raise EnvelopeRejected("INVALID_ENVELOPE_SHA256")
    if not isinstance(supplied_artifact_sha256, str) or not HEX_SHA256_RE.fullmatch(supplied_artifact_sha256):
        raise EnvelopeRejected("INVALID_ARTIFACT_SHA256")

    artifact = document["artifact"]
    artifact_bytes = canonical_json_bytes(artifact)
    if sha256_hex(artifact_bytes) != supplied_artifact_sha256:
        raise EnvelopeRejected("ARTIFACT_SHA256_MISMATCH")

    envelope_without_hash = dict(document)
    del envelope_without_hash["envelope_sha256"]
    computed_envelope_sha256 = sha256_hex(canonical_json_bytes(envelope_without_hash))
    if computed_envelope_sha256 != supplied_envelope_sha256:
        raise EnvelopeRejected("ENVELOPE_SHA256_MISMATCH")

    projection_path = validate_projection_path(document["projection_relative_path"])
    _validate_github_gate(projection_path, artifact)
    source_node_ref = _require_plain_string(document, "source_node_ref")
    packet_id = _require_plain_string(document, "packet_id")
    created_at = _require_plain_string(document, "created_at", maximum=128)
    _validate_created_at(created_at)

    logical_time = document.get("logical_time")
    if isinstance(logical_time, bool) or not isinstance(logical_time, (str, int)):
        raise EnvelopeRejected("INVALID_LOGICAL_TIME")
    if isinstance(logical_time, int) and logical_time < 0:
        raise EnvelopeRejected("INVALID_LOGICAL_TIME")
    if isinstance(logical_time, str):
        if not logical_time or len(logical_time) > 256 or any(ord(char) < 0x20 for char in logical_time):
            raise EnvelopeRejected("INVALID_LOGICAL_TIME")
        if unicodedata.normalize("NFC", logical_time) != logical_time:
            raise EnvelopeRejected("NON_NFC_LOGICAL_TIME")

    return ValidEnvelope(
        envelope_path=envelope_path,
        envelope_spool_relative_path=envelope_spool_relative_path or envelope_path.name,
        envelope_file_sha256=sha256_hex(raw),
        envelope_sha256=supplied_envelope_sha256,
        projection_relative_path=projection_path,
        artifact_sha256=supplied_artifact_sha256,
        artifact_bytes=artifact_bytes,
        source_node_ref=source_node_ref,
        packet_id=packet_id,
        logical_time=logical_time,
        created_at=created_at,
    )


def _is_reparse_or_symlink(path: Path) -> bool:
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode):
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _resolved(path: Path, strict: bool) -> Path:
    try:
        return path.resolve(strict=strict)
    except (OSError, RuntimeError) as exc:
        raise SetupHold("PATH_RESOLUTION_FAILED") from exc


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _validate_root_directory(path: Path, code_prefix: str) -> Path:
    if not path.exists():
        raise SetupHold(f"{code_prefix}_MISSING")
    if _is_reparse_or_symlink(path):
        raise SetupHold(f"{code_prefix}_REPARSE_POINT_REJECTED")
    if not path.is_dir():
        raise SetupHold(f"{code_prefix}_NOT_DIRECTORY")
    return _resolved(path, strict=True)


def _validate_local_coordinates(spool_dir: Path, receipt_dir: Path, drive_root: Path) -> Tuple[Path, Path, Path]:
    spool_root = _validate_root_directory(spool_dir, "SPOOL_DIR")
    drive_root_resolved = _validate_root_directory(drive_root, "DRIVE_ROOT")
    if _is_within(spool_root, drive_root_resolved):
        raise SetupHold("SPOOL_MUST_BE_LOCAL_OUTSIDE_DRIVE_ROOT")

    receipt_candidate = _resolved(receipt_dir, strict=False)
    if _is_within(receipt_candidate, drive_root_resolved):
        raise SetupHold("RECEIPT_DIR_MUST_BE_LOCAL_OUTSIDE_DRIVE_ROOT")
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_root = _validate_root_directory(receipt_dir, "RECEIPT_DIR")
    if _is_within(receipt_root, drive_root_resolved):
        raise SetupHold("RECEIPT_DIR_MUST_BE_LOCAL_OUTSIDE_DRIVE_ROOT")
    if _is_within(receipt_root, spool_root) or _is_within(spool_root, receipt_root):
        raise SetupHold("RECEIPT_DIR_MUST_BE_SEPARATE_FROM_SPOOL")
    return spool_root, receipt_root, drive_root_resolved


def _read_stable_envelope(path: Path, maximum_bytes: int) -> bytes:
    if _is_reparse_or_symlink(path):
        raise EnvelopeRejected("ENVELOPE_REPARSE_POINT_REJECTED")
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise EnvelopeRejected("ENVELOPE_NOT_REGULAR_FILE")
    if before.st_size > maximum_bytes:
        raise EnvelopeRejected("ENVELOPE_SIZE_LIMIT_EXCEEDED")
    with path.open("rb") as stream:
        raw = stream.read(maximum_bytes + 1)
    if len(raw) > maximum_bytes:
        raise EnvelopeRejected("ENVELOPE_SIZE_LIMIT_EXCEEDED")
    after = path.stat()
    before_coordinate = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_coordinate = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_coordinate != after_coordinate:
        raise EnvelopeRejected("ENVELOPE_CHANGED_DURING_READ")
    return raw


def _spool_relative_path(spool_root: Path, envelope_path: Path) -> str:
    try:
        relative = envelope_path.relative_to(spool_root)
    except ValueError as exc:
        raise EnvelopeRejected("ENVELOPE_PATH_OUTSIDE_SPOOL") from exc
    current = spool_root
    for part in relative.parts:
        if unicodedata.normalize("NFC", part) != part:
            raise EnvelopeRejected("ENVELOPE_SPOOL_PATH_NOT_NFC")
        current = current / part
        if _is_reparse_or_symlink(current):
            raise EnvelopeRejected("ENVELOPE_SPOOL_PATH_REPARSE_POINT_REJECTED")
    resolved_envelope = _resolved(envelope_path, strict=True)
    if not _is_within(resolved_envelope, spool_root):
        raise EnvelopeRejected("ENVELOPE_PATH_ESCAPED_SPOOL")
    return PurePosixPath(*relative.parts).as_posix()


def _enumerate_envelopes(spool_root: Path) -> List[Path]:
    envelope_paths: List[Path] = []
    for current_text, directory_names, file_names in os.walk(spool_root, followlinks=False):
        current = Path(current_text)
        safe_directories: List[str] = []
        for directory_name in directory_names:
            candidate = current / directory_name
            if _is_reparse_or_symlink(candidate):
                raise SetupHold("SPOOL_SUBDIRECTORY_REPARSE_POINT_REJECTED")
            safe_directories.append(directory_name)
        directory_names[:] = safe_directories
        for file_name in file_names:
            if file_name.lower().endswith(".json"):
                envelope_paths.append(current / file_name)
    return sorted(
        envelope_paths,
        key=lambda entry: _spool_relative_path(spool_root, entry).casefold(),
    )


def _ensure_drive_parent(drive_root: Path, relative_path: PurePosixPath) -> Path:
    current = drive_root
    parent_parts = relative_path.parts[:-1]
    for index, part in enumerate(parent_parts):
        current = current / part
        if current.exists():
            if _is_reparse_or_symlink(current):
                raise ProjectionHold("DRIVE_PARENT_REPARSE_POINT_REJECTED")
            if not current.is_dir():
                raise ProjectionHold("DRIVE_PARENT_NOT_DIRECTORY")
        elif index == 0:
            raise ProjectionHold("DRIVE_ALLOWLIST_PARTITION_MISSING")
        else:
            try:
                current.mkdir()
            except FileExistsError:
                pass
            except OSError as exc:
                raise ProjectionHold("DRIVE_PARENT_CREATE_FAILED") from exc
            if _is_reparse_or_symlink(current) or not current.is_dir():
                raise ProjectionHold("DRIVE_PARENT_UNSAFE_AFTER_CREATE")
        resolved_current = _resolved(current, strict=True)
        if not _is_within(resolved_current, drive_root):
            raise ProjectionHold("DRIVE_PARENT_ESCAPED_ROOT")
    target = current / relative_path.name
    resolved_candidate = _resolved(target, strict=False)
    if not _is_within(resolved_candidate, drive_root):
        raise ProjectionHold("DRIVE_TARGET_ESCAPED_ROOT")
    return target


def _existing_file_equals(path: Path, expected: bytes) -> bool:
    if _is_reparse_or_symlink(path):
        raise ProjectionHold("EXISTING_TARGET_REPARSE_POINT_REJECTED")
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ProjectionHold("EXISTING_TARGET_NOT_REGULAR_FILE")
    if metadata.st_size != len(expected):
        return False
    view = memoryview(expected)
    offset = 0
    with path.open("rb") as stream:
        while offset < len(expected):
            chunk = stream.read(min(1024 * 1024, len(expected) - offset))
            if not chunk or chunk != view[offset : offset + len(chunk)].tobytes():
                return False
            offset += len(chunk)
        return stream.read(1) == b""


def _exclusive_create_or_identical(path: Path, data: bytes) -> WriteResult:
    binary_flag = getattr(os, "O_BINARY", 0)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | binary_flag
    try:
        descriptor = os.open(str(path), flags, 0o600)
    except FileExistsError:
        if _existing_file_equals(path, data):
            return WriteResult("ALREADY_PRESENT_IDENTICAL", len(data))
        raise ProjectionHold("EXISTING_TARGET_BYTES_CONFLICT")
    except OSError as exc:
        raise ProjectionHold("EXCLUSIVE_CREATE_FAILED") from exc

    write_failed = False
    try:
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                raise OSError("zero-byte write")
            offset += written
        os.fsync(descriptor)
    except OSError as exc:
        write_failed = True
        raise ProjectionHold("WRITE_INCOMPLETE_NO_CLEANUP_PERFORMED") from exc
    finally:
        os.close(descriptor)

    if not write_failed and not _existing_file_equals(path, data):
        raise ProjectionHold("POST_WRITE_BYTE_VERIFICATION_FAILED")
    return WriteResult("CREATED", len(data))


def _project_drive_bytes(drive_root: Path, relative_path: PurePosixPath, data: bytes) -> WriteResult:
    target = _ensure_drive_parent(drive_root, relative_path)
    return _exclusive_create_or_identical(target, data)


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _receipt_id(envelope_sha256: str) -> str:
    basis = (RECEIPT_SCHEMA_ID + "\x00" + envelope_sha256).encode("ascii")
    return sha256_hex(basis)


def _build_receipt(envelope: ValidEnvelope, artifact_write_state: str) -> Tuple[str, bytes]:
    receipt_id = _receipt_id(envelope.envelope_sha256)
    drive_receipt_relative_path = f"08_RECEIPTS/{RECEIPT_PREFIX}{receipt_id}.json"
    receipt: Dict[str, Any] = {
        "schema_id": RECEIPT_SCHEMA_ID,
        "canonicalization": CANONICALIZATION_ID,
        "receipt_id": receipt_id,
        "observed_at": _utc_now(),
        "source_node_ref": envelope.source_node_ref,
        "packet_id": envelope.packet_id,
        "logical_time": envelope.logical_time,
        "envelope_sha256": envelope.envelope_sha256,
        "envelope_spool_relative_path": envelope.envelope_spool_relative_path,
        "envelope_file_sha256": envelope.envelope_file_sha256,
        "artifact_sha256": envelope.artifact_sha256,
        "artifact_byte_count": len(envelope.artifact_bytes),
        "projection_relative_path": envelope.projection_relative_path.as_posix(),
        "artifact_write_state": artifact_write_state,
        "drive_receipt_relative_path": drive_receipt_relative_path,
        "write_semantics": "EXCLUSIVE_CREATE_OR_IDENTICAL_BYTES",
        "spool_state": "PRESERVED_APPEND_ONLY_SOURCE",
        "drive_role": "PROJECTION_SINK_ONLY",
        "authority_state": "NOT_AUTHORITY",
        "live_effect_state": "NOT_ESTABLISHED",
    }
    receipt["receipt_sha256"] = sha256_hex(canonical_json_bytes(receipt))
    return receipt_id, canonical_json_bytes(receipt)


def _validated_receipt_document(raw: bytes) -> Dict[str, Any]:
    try:
        document = strict_json_loads(raw)
    except EnvelopeRejected as exc:
        raise ProjectionHold(f"LOCAL_RECEIPT_{exc.code}") from exc
    if not isinstance(document, dict):
        raise ProjectionHold("LOCAL_RECEIPT_NOT_OBJECT")
    supplied_hash = document.get("receipt_sha256")
    if not isinstance(supplied_hash, str) or not HEX_SHA256_RE.fullmatch(supplied_hash):
        raise ProjectionHold("LOCAL_RECEIPT_SHA256_INVALID")
    without_hash = dict(document)
    del without_hash["receipt_sha256"]
    try:
        computed_hash = sha256_hex(canonical_json_bytes(without_hash))
        canonical_raw = canonical_json_bytes(document)
    except EnvelopeRejected as exc:
        raise ProjectionHold(f"LOCAL_RECEIPT_{exc.code}") from exc
    if computed_hash != supplied_hash:
        raise ProjectionHold("LOCAL_RECEIPT_SHA256_MISMATCH")
    if canonical_raw != raw:
        raise ProjectionHold("LOCAL_RECEIPT_NOT_CANONICAL_BYTES")
    return document


def _validate_existing_receipt(raw: bytes, envelope: ValidEnvelope, receipt_id: str) -> None:
    document = _validated_receipt_document(raw)
    expected_bindings = {
        "schema_id": RECEIPT_SCHEMA_ID,
        "receipt_id": receipt_id,
        "envelope_sha256": envelope.envelope_sha256,
        "envelope_spool_relative_path": envelope.envelope_spool_relative_path,
        "envelope_file_sha256": envelope.envelope_file_sha256,
        "artifact_sha256": envelope.artifact_sha256,
        "projection_relative_path": envelope.projection_relative_path.as_posix(),
        "drive_role": "PROJECTION_SINK_ONLY",
        "authority_state": "NOT_AUTHORITY",
        "live_effect_state": "NOT_ESTABLISHED",
    }
    if any(document.get(key) != value for key, value in expected_bindings.items()):
        raise ProjectionHold("LOCAL_RECEIPT_BINDING_MISMATCH")


def _assert_spool_path_append_only(receipt_root: Path, envelope: ValidEnvelope) -> None:
    """Reject a successful spool relative path that later presents different bytes."""

    for receipt_path in receipt_root.glob("*.json"):
        if _is_reparse_or_symlink(receipt_path) or not receipt_path.is_file():
            raise ProjectionHold("LOCAL_RECEIPT_ENTRY_UNSAFE")
        try:
            raw = receipt_path.read_bytes()
        except OSError as exc:
            raise ProjectionHold("LOCAL_RECEIPT_READ_FAILED") from exc
        document = _validated_receipt_document(raw)
        receipt_id = document.get("receipt_id")
        if not isinstance(receipt_id, str) or not HEX_SHA256_RE.fullmatch(receipt_id):
            raise ProjectionHold("LOCAL_RECEIPT_ID_INVALID")
        if receipt_path.name != f"{receipt_id}.json":
            raise ProjectionHold("LOCAL_RECEIPT_FILENAME_BINDING_MISMATCH")
        if document.get("envelope_spool_relative_path") != envelope.envelope_spool_relative_path:
            continue
        if document.get("envelope_file_sha256") != envelope.envelope_file_sha256:
            raise ProjectionHold("SPOOL_ENVELOPE_PATH_REBOUND")


def _load_or_create_local_receipt(
    receipt_root: Path,
    envelope: ValidEnvelope,
    artifact_write_state: str,
) -> Tuple[str, bytes, WriteResult]:
    receipt_id = _receipt_id(envelope.envelope_sha256)
    local_path = receipt_root / f"{receipt_id}.json"
    if local_path.exists():
        if _is_reparse_or_symlink(local_path):
            raise ProjectionHold("LOCAL_RECEIPT_REPARSE_POINT_REJECTED")
        raw = local_path.read_bytes()
        _validate_existing_receipt(raw, envelope, receipt_id)
        return receipt_id, raw, WriteResult("ALREADY_PRESENT_IDENTICAL", len(raw))

    built_receipt_id, receipt_bytes = _build_receipt(envelope, artifact_write_state)
    try:
        result = _exclusive_create_or_identical(local_path, receipt_bytes)
        return built_receipt_id, receipt_bytes, result
    except ProjectionHold as exc:
        if exc.code != "EXISTING_TARGET_BYTES_CONFLICT" or not local_path.exists():
            raise
        # A concurrent projector may have created a valid receipt with a
        # different observed_at.  Its immutable bytes become the one receipt.
        raw = local_path.read_bytes()
        _validate_existing_receipt(raw, envelope, receipt_id)
        return receipt_id, raw, WriteResult("ALREADY_PRESENT_IDENTICAL", len(raw))


def process_envelope(
    envelope_path: Path,
    spool_root: Path,
    drive_root: Path,
    receipt_root: Path,
    maximum_bytes: int,
) -> EnvelopeResult:
    stage = "ENVELOPE"
    envelope_display = envelope_path.name
    try:
        envelope_display = _spool_relative_path(spool_root, envelope_path)
        raw = _read_stable_envelope(envelope_path, maximum_bytes)
        envelope = validate_envelope(envelope_path, raw, envelope_display)
        _assert_spool_path_append_only(receipt_root, envelope)
        stage = "ARTIFACT"
        artifact_result = _project_drive_bytes(
            drive_root,
            envelope.projection_relative_path,
            envelope.artifact_bytes,
        )
        stage = "LOCAL_RECEIPT"
        receipt_id, receipt_bytes, local_receipt_result = _load_or_create_local_receipt(
            receipt_root,
            envelope,
            artifact_result.state,
        )
        receipt_relative_path = PurePosixPath(
            "08_RECEIPTS",
            f"{RECEIPT_PREFIX}{receipt_id}.json",
        )
        stage = "DRIVE_RECEIPT"
        drive_receipt_result = _project_drive_bytes(drive_root, receipt_relative_path, receipt_bytes)
        return EnvelopeResult(
            envelope_file=envelope_display,
            state="PASS_BYTES_PROJECTED",
            code="PROJECTED_EXCLUSIVE_OR_IDENTICAL",
            artifact_write_state=artifact_result.state,
            local_receipt_state=local_receipt_result.state,
            drive_receipt_state=drive_receipt_result.state,
            projection_relative_path=envelope.projection_relative_path.as_posix(),
            receipt_id=receipt_id,
        )
    except EnvelopeRejected as exc:
        return EnvelopeResult(
            envelope_file=envelope_display,
            state="HOLD_ENVELOPE_REJECTED",
            code=exc.code,
        )
    except ProjectionHold as exc:
        return EnvelopeResult(
            envelope_file=envelope_display,
            state="HOLD_PROJECTION",
            code=f"{stage}_{exc.code}",
        )
    except OSError:
        return EnvelopeResult(
            envelope_file=envelope_display,
            state="HOLD_IO",
            code="UNCLASSIFIED_IO_ERROR",
        )


def run_once(
    spool_dir: Path,
    drive_root: Path,
    receipt_dir: Path,
    maximum_bytes: int = DEFAULT_MAX_ENVELOPE_BYTES,
) -> RunSummary:
    if maximum_bytes < 1:
        raise SetupHold("MAX_ENVELOPE_BYTES_INVALID")
    spool_root, receipt_root, drive_root_resolved = _validate_local_coordinates(
        Path(spool_dir), Path(receipt_dir), Path(drive_root)
    )
    envelope_paths = _enumerate_envelopes(spool_root)
    results = tuple(
        process_envelope(path, spool_root, drive_root_resolved, receipt_root, maximum_bytes)
        for path in envelope_paths
    )
    passed = sum(item.state == "PASS_BYTES_PROJECTED" for item in results)
    held = len(results) - passed
    state = "IDLE_NO_ENVELOPES" if not results else ("PASS_BYTES_PROJECTED" if held == 0 else "HOLD")
    return RunSummary(
        state=state,
        processed=len(results),
        passed=passed,
        held=held,
        results=results,
    )


def _default_local_base() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "W7TP" / "gt_mesh_v21"
    return Path.home() / "AppData" / "Local" / "W7TP" / "gt_mesh_v21"


def _parser() -> argparse.ArgumentParser:
    local_base = _default_local_base()
    parser = argparse.ArgumentParser(
        description="Project W7TP v2.1 local spool envelopes to an existing Drive 8D_ADI_INDEX root.",
    )
    parser.add_argument(
        "--spool-dir",
        type=Path,
        default=local_base / "drive_spool",
        help="Local append-only envelope directory (default: LocalAppData/W7TP/gt_mesh_v21/drive_spool).",
    )
    parser.add_argument(
        "--receipt-dir",
        type=Path,
        default=local_base / "receipts",
        help="Local immutable one-file-per-envelope receipt directory.",
    )
    parser.add_argument(
        "--drive-root",
        type=Path,
        default=os.environ.get("W7TP_DRIVE_INDEX_ROOT"),
        required=os.environ.get("W7TP_DRIVE_INDEX_ROOT") is None,
        help="Existing J:\\...\\8D_ADI_INDEX root; may also use W7TP_DRIVE_INDEX_ROOT.",
    )
    parser.add_argument(
        "--max-envelope-bytes",
        type=int,
        default=DEFAULT_MAX_ENVELOPE_BYTES,
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Remain running and rescan the append-only spool.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=5.0,
        help="Watch-mode delay; must be at least 1 second.",
    )
    return parser


def _emit_summary(summary: RunSummary) -> None:
    sys.stdout.buffer.write(canonical_json_bytes(summary.as_dict()) + b"\n")
    sys.stdout.buffer.flush()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.watch and args.poll_seconds < 1:
        parser.error("--poll-seconds must be at least 1")
    exit_code = 0
    try:
        while True:
            summary = run_once(
                spool_dir=args.spool_dir,
                drive_root=args.drive_root,
                receipt_dir=args.receipt_dir,
                maximum_bytes=args.max_envelope_bytes,
            )
            _emit_summary(summary)
            if summary.held:
                exit_code = 2
            if not args.watch:
                return exit_code
            time.sleep(args.poll_seconds)
    except SetupHold as exc:
        error = {
            "state": "HOLD_SETUP",
            "code": exc.code,
            "authority": "NOT_ESTABLISHED",
            "live_effect": "NOT_ESTABLISHED",
            "drive_role": "PROJECTION_SINK_ONLY",
        }
        sys.stderr.buffer.write(canonical_json_bytes(error) + b"\n")
        return 3
    except KeyboardInterrupt:
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
