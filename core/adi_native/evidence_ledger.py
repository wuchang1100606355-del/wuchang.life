from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

from .errors import LedgerParseFailure

if os.name == "nt":  # pragma: no cover - exercised on Windows
    import msvcrt
else:  # pragma: no cover - branch selection is platform-dependent
    import fcntl


LEGACY_HASH_V1 = "LEGACY_HASH_V1"
W7TP_EVIDENCE_HASH_V2 = "W7TP_EVIDENCE_HASH_V2"
GENESIS_HASH = "0" * 64


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def calculate_legacy_hash_v1(record: Mapping[str, Any]) -> str:
    payload = "".join(
        str(record[field])
        for field in ("timestamp", "event_type", "content", "actor", "previous_hash")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def calculate_evidence_hash_v2(record: Mapping[str, Any]) -> str:
    bounded = {key: value for key, value in record.items() if key != "hash"}
    return hashlib.sha256(_canonical_bytes(bounded)).hexdigest()


def load_legacy_records(path: str | os.PathLike[str]) -> list[dict[str, Any]]:
    source = Path(path)
    try:
        parsed = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LedgerParseFailure(str(source), type(exc).__name__) from exc
    if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
        raise LedgerParseFailure(str(source), "EXPECTED_JSON_ARRAY")
    return parsed


def verify_legacy_chain(path: str | os.PathLike[str]) -> tuple[bool, str]:
    records = load_legacy_records(path)
    previous = GENESIS_HASH
    for expected_index, record in enumerate(records, start=1):
        if record.get("index") != expected_index:
            return False, "LEGACY_INDEX_DIVERGENCE"
        if record.get("previous_hash") != previous:
            return False, "LEGACY_PREVIOUS_HASH_DIVERGENCE"
        profile = record.get("hash_profile", LEGACY_HASH_V1)
        if profile != LEGACY_HASH_V1:
            return False, "LEGACY_HASH_PROFILE_UNSUPPORTED"
        if record.get("hash") != calculate_legacy_hash_v1(record):
            return False, "LEGACY_HASH_DIVERGENCE"
        previous = record["hash"]
    return True, "CHAIN_VALID"


@contextmanager
def _locked(stream) -> Iterator[None]:
    if os.name == "nt":  # pragma: no cover - exercised on Windows
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class VerifiableSpacetimeSystem:
    """Append-only V2 evidence ledger; it is not the native ADI core."""

    def __init__(
        self,
        ledger_path: str | os.PathLike[str],
        *,
        legacy_path: str | os.PathLike[str] | None = None,
        legacy_file_sha256: str | None = None,
        legacy_chain_head: str | None = None,
    ):
        self.ledger_path = Path(ledger_path)
        if legacy_path is not None:
            legacy = Path(legacy_path)
            valid, reason = verify_legacy_chain(legacy)
            if not valid:
                raise LedgerParseFailure(str(legacy), reason)
            records = load_legacy_records(legacy)
            self.legacy_file_sha256 = _sha256_file(legacy)
            self.legacy_chain_head = records[-1]["hash"] if records else GENESIS_HASH
        else:
            self.legacy_file_sha256 = legacy_file_sha256
            self.legacy_chain_head = legacy_chain_head
        if not self.legacy_file_sha256 or not self.legacy_chain_head:
            raise ValueError("legacy_file_sha256 and legacy_chain_head are required")
        if self.ledger_path.exists():
            self._load_v2_records()

    def _load_v2_records(self, stream=None) -> list[dict[str, Any]]:
        try:
            if stream is None:
                text = self.ledger_path.read_text(encoding="utf-8")
            else:
                stream.seek(0)
                text = stream.read()
            records = [json.loads(line) for line in text.splitlines() if line.strip()]
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise LedgerParseFailure(str(self.ledger_path), type(exc).__name__) from exc
        if not all(isinstance(record, dict) for record in records):
            raise LedgerParseFailure(str(self.ledger_path), "EXPECTED_JSONL_OBJECTS")
        return records

    def append_event(
        self,
        event_type: str,
        content: Mapping[str, Any],
        *,
        actor_ref: str,
        accountable_person_ref: str,
        logical_time: int | None = None,
        timestamp_utc: str | None = None,
    ) -> dict[str, Any]:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open("a+", encoding="utf-8", newline="") as stream:
            with _locked(stream):
                records = self._load_v2_records(stream)
                valid, reason = self._verify_records(records)
                if not valid:
                    raise LedgerParseFailure(str(self.ledger_path), reason)
                previous = records[-1]["hash"] if records else self.legacy_chain_head
                next_logical = records[-1]["logical_time"] + 1 if records else 1
                if logical_time is not None:
                    if logical_time < next_logical:
                        raise ValueError("logical_time must be monotonic")
                    next_logical = logical_time
                event = {
                    "index": len(records) + 1,
                    "timestamp_utc": timestamp_utc
                    or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "logical_time": next_logical,
                    "event_type": event_type,
                    "content": dict(content),
                    "actor_ref": actor_ref,
                    "accountable_person_ref": accountable_person_ref,
                    "previous_hash": previous,
                    "hash_profile": W7TP_EVIDENCE_HASH_V2,
                }
                if not records:
                    event["legacy_file_sha256"] = self.legacy_file_sha256
                    event["legacy_chain_head"] = self.legacy_chain_head
                event["hash"] = calculate_evidence_hash_v2(event)
                stream.seek(0, os.SEEK_END)
                stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
                return event

    def _verify_records(self, records: list[dict[str, Any]]) -> tuple[bool, str]:
        previous = self.legacy_chain_head
        logical_time = 0
        for expected_index, record in enumerate(records, start=1):
            if record.get("index") != expected_index:
                return False, "V2_INDEX_DIVERGENCE"
            if record.get("hash_profile") != W7TP_EVIDENCE_HASH_V2:
                return False, "V2_HASH_PROFILE_DIVERGENCE"
            if record.get("previous_hash") != previous:
                return False, "V2_PREVIOUS_HASH_DIVERGENCE"
            if not isinstance(record.get("logical_time"), int) or record["logical_time"] <= logical_time:
                return False, "V2_LOGICAL_TIME_DIVERGENCE"
            if not record.get("actor_ref") or not record.get("accountable_person_ref"):
                return False, "V2_ACCOUNTABILITY_FIELDS_MISSING"
            if expected_index == 1 and (
                record.get("legacy_file_sha256") != self.legacy_file_sha256
                or record.get("legacy_chain_head") != self.legacy_chain_head
            ):
                return False, "V2_LEGACY_ANCHOR_DIVERGENCE"
            if record.get("hash") != calculate_evidence_hash_v2(record):
                return False, "V2_HASH_DIVERGENCE"
            previous = record["hash"]
            logical_time = record["logical_time"]
        return True, "CHAIN_VALID"

    def verify_chain(self) -> tuple[bool, str]:
        records = self._load_v2_records() if self.ledger_path.exists() else []
        return self._verify_records(records)
