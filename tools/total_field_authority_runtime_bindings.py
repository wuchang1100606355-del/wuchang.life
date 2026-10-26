from __future__ import annotations

import hashlib
import math
import re
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Collection, Protocol

NONCE_REF = re.compile(r"^nonce_ref:sha256:[0-9a-f]{64}$")
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
VERIFIER_REF = re.compile(r"^verifier_ref:[A-Za-z0-9_.:-]{4,240}$")
MAX_SIGNATURE_LENGTH = 16384
MAX_TTL_SECONDS = 300


class DetachedSignatureBackend(Protocol):
    def verify_detached(
        self,
        *,
        verifier_ref: str,
        payload_sha256: str,
        signature: str,
    ) -> bool:
        """Return True only when the detached signature is valid."""


class SQLitePersistentNonceLedger:
    """
    Persistent, fail-closed, single-use nonce ledger.

    The ledger stores only opaque nonce references, packet hashes, and timestamps.
    It never reads member plaintext, tokens, passwords, private keys, or key files.
    Consumed nonces are not automatically deleted, preserving single-use semantics
    across process restarts.
    """

    persistent = True
    secret_material_access = False

    def __init__(
        self,
        db_path: str | Path,
        *,
        busy_timeout_ms: int = 5000,
    ) -> None:
        path = Path(db_path)
        if path.exists() and path.is_symlink():
            raise ValueError("nonce ledger path must not be a symlink")
        self.db_path = path.resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.db_path.parent.chmod(0o700)
        except OSError:
            pass

        self._lock = threading.RLock()
        self._closed = False
        self._conn = sqlite3.connect(
            str(self.db_path),
            timeout=max(1.0, busy_timeout_ms / 1000.0),
            isolation_level=None,
            check_same_thread=False,
        )
        self._conn.execute(f"PRAGMA busy_timeout={int(max(1, busy_timeout_ms))}")
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS authority_nonce_ledger (
                nonce TEXT PRIMARY KEY,
                packet_hash TEXT NOT NULL,
                used_at REAL NOT NULL,
                authority_expires_at REAL NOT NULL,
                CHECK(length(nonce) = 81),
                CHECK(length(packet_hash) = 64)
            )
            """
        )
        self._conn.execute(
            """
            CREATE INDEX IF NOT EXISTS authority_nonce_used_at_idx
            ON authority_nonce_ledger(used_at)
            """
        )
        try:
            self.db_path.chmod(0o600)
        except OSError:
            pass

    def _valid_input(
        self,
        nonce: object,
        packet_hash: object,
        now_epoch: object,
        ttl_seconds: object,
    ) -> bool:
        if not isinstance(nonce, str) or NONCE_REF.fullmatch(nonce) is None:
            return False
        if (
            not isinstance(packet_hash, str)
            or SHA256_HEX.fullmatch(packet_hash) is None
        ):
            return False
        if isinstance(now_epoch, bool) or not isinstance(now_epoch, (int, float)):
            return False
        if not math.isfinite(float(now_epoch)) or float(now_epoch) < 0:
            return False
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int):
            return False
        return 1 <= ttl_seconds <= MAX_TTL_SECONDS

    def mark_used_or_replay(
        self,
        nonce: str,
        packet_hash: str,
        now_epoch: float,
        ttl_seconds: int,
    ) -> bool:
        """
        Atomically record first use.

        Returns True only for a first valid use. Invalid input, replay, closed
        ledger, or SQLite failure returns False.
        """
        if not self._valid_input(nonce, packet_hash, now_epoch, ttl_seconds):
            return False

        with self._lock:
            if self._closed:
                return False
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                cursor = self._conn.execute(
                    """
                    INSERT OR IGNORE INTO authority_nonce_ledger(
                        nonce,
                        packet_hash,
                        used_at,
                        authority_expires_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        nonce,
                        packet_hash,
                        float(now_epoch),
                        float(now_epoch) + ttl_seconds,
                    ),
                )
                inserted = cursor.rowcount == 1
                self._conn.execute("COMMIT")
                return inserted
            except sqlite3.Error:
                try:
                    self._conn.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                return False

    def entry_count(self) -> int:
        with self._lock:
            if self._closed:
                return 0
            try:
                row = self._conn.execute(
                    "SELECT COUNT(*) FROM authority_nonce_ledger"
                ).fetchone()
            except sqlite3.Error:
                return 0
        return int(row[0]) if row is not None else 0

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            try:
                self._conn.execute("PRAGMA wal_checkpoint(FULL)")
            except sqlite3.Error:
                pass
            self._conn.close()
            self._closed = True

    def __enter__(self) -> "SQLitePersistentNonceLedger":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        del exc_type, exc, traceback
        self.close()


class TrustedSignatureVerifierBinding:
    """
    Reference-only verifier binding.

    This class never opens key files or reads environment variables. A trusted
    runtime injects a backend that owns key access outside this module.
    """

    trusted_runtime_verifier = True
    secret_material_access = False
    key_material_source = "INJECTED_BACKEND_ONLY"

    def __init__(
        self,
        backend: DetachedSignatureBackend,
        *,
        trusted_verifier_refs: Collection[str],
    ) -> None:
        method = getattr(backend, "verify_detached", None)
        if not callable(method):
            raise TypeError("signature backend must implement verify_detached")

        refs = tuple(sorted({str(item) for item in trusted_verifier_refs}))
        if not refs:
            raise ValueError("at least one trusted verifier reference is required")
        if any(VERIFIER_REF.fullmatch(item) is None for item in refs):
            raise ValueError("trusted verifier reference is invalid")

        self._backend = backend
        self.trusted_verifier_refs = refs

    def verify(
        self,
        *,
        verifier_ref: str,
        payload_sha256: str,
        signature: str,
    ) -> bool:
        if verifier_ref not in self.trusted_verifier_refs:
            return False
        if SHA256_HEX.fullmatch(payload_sha256 or "") is None:
            return False
        if (
            not isinstance(signature, str)
            or not signature
            or len(signature) > MAX_SIGNATURE_LENGTH
        ):
            return False

        try:
            result = self._backend.verify_detached(
                verifier_ref=verifier_ref,
                payload_sha256=payload_sha256,
                signature=signature,
            )
        except Exception:
            return False
        return result is True


@dataclass
class AuthorityRuntimeBindings:
    nonce_ledger: SQLitePersistentNonceLedger
    signature_verifier: TrustedSignatureVerifierBinding
    trusted_verifier_refs: tuple[str, ...]
    secret_material_access: bool = False

    def close(self) -> None:
        self.nonce_ledger.close()

    def __enter__(self) -> "AuthorityRuntimeBindings":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        del exc_type, exc, traceback
        self.close()


def build_authority_runtime_bindings(
    *,
    ledger_path: str | Path,
    signature_backend: DetachedSignatureBackend,
    trusted_verifier_refs: Collection[str],
) -> AuthorityRuntimeBindings:
    """
    Build runtime dependencies without reading secrets or activating authority.

    The caller must provide an injected signature backend and an explicit ledger
    path. This function does not read environment variables, key files, the active
    authority pointer, or member data.
    """
    verifier = TrustedSignatureVerifierBinding(
        signature_backend,
        trusted_verifier_refs=trusted_verifier_refs,
    )
    ledger = SQLitePersistentNonceLedger(ledger_path)
    return AuthorityRuntimeBindings(
        nonce_ledger=ledger,
        signature_verifier=verifier,
        trusted_verifier_refs=verifier.trusted_verifier_refs,
    )


__all__ = [
    "AuthorityRuntimeBindings",
    "DetachedSignatureBackend",
    "MAX_TTL_SECONDS",
    "SQLitePersistentNonceLedger",
    "TrustedSignatureVerifierBinding",
    "build_authority_runtime_bindings",
]
