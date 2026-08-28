"""Immutable object storage plus append-only packet/receipt/lineage journals."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Iterable

from .core import MeshConflict, MeshHold, require_core, safe_component


class AppendOnlyJournal:
    """One canonical JSON object per immutable event file."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        requested = Path(root)
        requested.mkdir(parents=True, exist_ok=True)
        if requested.is_symlink() or not requested.is_dir():
            raise MeshHold("HOLD_JOURNAL_ROOT_UNSAFE")
        self.root = requested.resolve(strict=True)

    def _category(self, category: str) -> Path:
        safe_component(category, code="HOLD_JOURNAL_CATEGORY_INVALID")
        path = self.root / category
        path.mkdir(parents=True, exist_ok=True)
        if path.is_symlink() or not path.is_dir():
            raise MeshHold("HOLD_JOURNAL_CATEGORY_UNSAFE")
        return path

    def append(self, category: str, key: str, value: Any) -> Path:
        safe_component(key, code="HOLD_JOURNAL_KEY_INVALID")
        core = require_core()
        raw = core.canonical_json_bytes(value)
        path = self._category(category) / f"{key}.json"
        try:
            with path.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            try:
                existing = path.read_bytes()
            except OSError as exc:
                raise MeshHold("HOLD_JOURNAL_EXISTING_READ_FAILED") from exc
            if existing != raw:
                raise MeshConflict("CONFLICT_APPEND_ONLY_RECORD_EXISTS")
        return path

    def records(self, category: str) -> Iterable[dict[str, object]]:
        core = require_core()
        path = self._category(category)
        for item in sorted(path.glob("*.json"), key=lambda candidate: candidate.name):
            if item.is_symlink() or not item.is_file():
                raise MeshConflict("CONFLICT_JOURNAL_ENTRY_UNSAFE")
            parsed = core.canonical_json_loads(item.read_bytes(), require_canonical=True)
            if not isinstance(parsed, dict):
                raise MeshConflict("CONFLICT_JOURNAL_ENTRY_NOT_OBJECT")
            yield parsed

    def find_receipt(self, packet_ref: str) -> dict[str, object] | None:
        for receipt in self.records("receipts"):
            if receipt.get("packet_ref") == packet_ref:
                return receipt
        return None

    def latest_state(self, source_node_ref: str) -> dict[str, object] | None:
        latest: dict[str, object] | None = None
        for state in self.records("states"):
            if state.get("source_node_ref") != source_node_ref:
                continue
            logical_time = state.get("logical_time")
            if isinstance(logical_time, bool) or not isinstance(logical_time, int):
                raise MeshConflict("CONFLICT_STATE_LOGICAL_TIME_INVALID")
            if latest is None or logical_time > int(latest["logical_time"]):
                latest = state
        return latest

    def next_logical_time(self, source_node_ref: str) -> int:
        latest = self.latest_state(source_node_ref)
        return 1 if latest is None else int(latest["logical_time"]) + 1

    def _acquire_replay_lock(self) -> Path:
        lock = self.root / ".replay.lock"
        deadline = time.monotonic_ns() + 5_000_000_000
        while True:
            try:
                lock.mkdir()
                return lock
            except FileExistsError:
                if time.monotonic_ns() >= deadline:
                    raise MeshHold("HOLD_REPLAY_LEDGER_LOCKED")
                time.sleep(0.01)

    @staticmethod
    def _release_replay_lock(lock: Path) -> None:
        try:
            lock.rmdir()
        except OSError:
            pass

    def claim_replay(
        self,
        *,
        authority_ref: str,
        namespace: str,
        nonce: str,
        logical_time: int,
        tuple_sha256: str,
        packet_ref: str,
        claimed_at: str,
    ) -> bool:
        """Atomically claim nonce/time; return False for exact idempotence."""

        core = require_core()
        nonce_scope = {
            "authority_ref": authority_ref,
            "namespace": namespace,
            "nonce": nonce,
        }
        nonce_key = core.sha256_hex(core.canonical_json_bytes(nonce_scope))
        claim = {
            "schema_id": "W7TP_GT_MESH_REPLAY_CLAIM_V21",
            **nonce_scope,
            "logical_time": logical_time,
            "tuple_sha256": tuple_sha256,
            "packet_ref": packet_ref,
            "claimed_at": claimed_at,
        }
        lock = self._acquire_replay_lock()
        try:
            claims = list(self.records("replay_claims"))
            for existing in claims:
                if (
                    existing.get("authority_ref") == authority_ref
                    and existing.get("namespace") == namespace
                    and existing.get("nonce") == nonce
                ):
                    if (
                        existing.get("tuple_sha256") == tuple_sha256
                        and existing.get("packet_ref") == packet_ref
                    ):
                        return False
                    raise MeshConflict("CONFLICT_NONCE_REUSE")
            prior_times = [
                int(item["logical_time"])
                for item in claims
                if item.get("authority_ref") == authority_ref
                and item.get("namespace") == namespace
                and isinstance(item.get("logical_time"), int)
                and not isinstance(item.get("logical_time"), bool)
            ]
            if prior_times and logical_time <= max(prior_times):
                raise MeshConflict("CONFLICT_LOGICAL_TIME_REPLAY")
            self.append("replay_claims", nonce_key, claim)
            return True
        finally:
            self._release_replay_lock(lock)


class MeshStorage:
    """Required established CAS plus adapter-owned append-only journals."""

    def __init__(self, runtime_root: str | os.PathLike[str]) -> None:
        core = require_core()
        root = Path(runtime_root)
        root.mkdir(parents=True, exist_ok=True)
        if root.is_symlink() or not root.is_dir():
            raise MeshHold("HOLD_RUNTIME_ROOT_UNSAFE")
        self.root = root.resolve(strict=True)
        try:
            self.objects = core.object_store_type(self.root / "object_store")
        except Exception as exc:
            code = getattr(exc, "reason_code", "HOLD_OBJECT_STORE_UNAVAILABLE")
            raise MeshHold(str(code)) from exc
        self.journal = AppendOnlyJournal(self.root / "journal")

    def put_artifact(self, value: Any) -> str:
        core = require_core()
        raw = core.canonical_json_bytes(value)
        try:
            return self.objects.put_bytes(raw)
        except Exception as exc:
            code = getattr(exc, "reason_code", "HOLD_OBJECT_STORE_WRITE_FAILED")
            raise MeshHold(str(code)) from exc

    def put_exact_bytes(self, object_ref: str, raw: bytes) -> str:
        try:
            return self.objects.put_exact(object_ref, raw)
        except Exception as exc:
            code = getattr(exc, "reason_code", "HOLD_OBJECT_STORE_WRITE_FAILED")
            raise MeshConflict(str(code)) from exc

    def get_bytes(self, object_ref: str) -> bytes:
        try:
            return self.objects.get_bytes(object_ref)
        except Exception as exc:
            code = getattr(exc, "reason_code", "HOLD_OBJECT_NOT_FOUND")
            raise MeshHold(str(code)) from exc

    def get_artifact(self, object_ref: str) -> dict[str, object]:
        core = require_core()
        parsed = core.canonical_json_loads(self.get_bytes(object_ref), require_canonical=True)
        if not isinstance(parsed, dict):
            raise MeshConflict("CONFLICT_OBJECT_ARTIFACT_NOT_OBJECT")
        return parsed

    def has(self, object_ref: str) -> bool:
        try:
            return bool(self.objects.has(object_ref))
        except Exception as exc:
            code = getattr(exc, "reason_code", "HOLD_OBJECT_STORE_READ_FAILED")
            raise MeshHold(str(code)) from exc

    def close(self) -> None:
        self.objects.close()

    def __enter__(self) -> "MeshStorage":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        del exc_type, exc, traceback
        self.close()
