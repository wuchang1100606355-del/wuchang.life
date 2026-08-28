from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

from .canonical import canonical_hash, validate_sha256_hex, validate_sha256_ref
from .journal_recovery import validate_effect_transition
from .models import JournalEventType, Quarantine


EXPECTED_USER_VERSION = 1
DEFAULT_BUSY_TIMEOUT_MS = 5000
DEFAULT_SCHEMA_PATH = Path(__file__).with_name("schema.sql")
ARTIFACT_BINDING_SCHEMA_ID = "W7TP_ARTIFACT_BINDING_V1"
REQUIRED_V1_SCHEMA_OBJECTS = frozenset(
    {
        "artifact_bindings",
        "artifact_bindings_no_delete",
        "artifact_bindings_no_update",
        "artifact_bindings_verify_sealed_verified",
        "current_pointer",
        "effect_attempt_claims",
        "effect_attempt_claims_no_delete",
        "effect_attempt_claims_no_update",
        "effect_operation_claims",
        "effect_operation_claims_no_delete",
        "effect_operation_claims_no_update",
        "operation_journal",
        "receipts",
        "resources",
        "transitions",
        "workspaces",
    }
)


class SchemaHold(RuntimeError):
    """The database schema cannot be used without an explicit migration."""


class StoreHold(RuntimeError):
    """Required state is absent or cannot safely advance."""


class StoreConflict(RuntimeError):
    """Observed state conflicts with the sealed operation."""


class CASConflict(StoreConflict):
    """The current pointer no longer matches both expected coordinates."""


class JournalHold(StoreHold):
    """The append-only journal sequence or hash chain is incomplete."""


def _artifact_binding_body(
    *,
    node_id: str,
    workspace_id: str,
    artifact_ref: str,
    manifest_ref: str,
    artifact_hash: str,
    capability_id: str,
    version: str,
    adapter_ref: str,
    binding_state: str,
    evidence_ref: str,
    observed_at: str,
) -> dict[str, str]:
    return {
        "schema_id": ARTIFACT_BINDING_SCHEMA_ID,
        "node_id": node_id,
        "workspace_id": workspace_id,
        "artifact_ref": artifact_ref,
        "manifest_ref": manifest_ref,
        "artifact_hash": artifact_hash,
        "capability_id": capability_id,
        "version": version,
        "adapter_ref": adapter_ref,
        "binding_state": binding_state,
        "evidence_ref": evidence_ref,
        "observed_at": observed_at,
    }


def _sqlite_artifact_binding_hash(*values: object) -> str:
    if len(values) != 11 or any(
        not isinstance(value, str) or not value for value in values
    ):
        return ""
    return canonical_hash(
        _artifact_binding_body(
            node_id=values[0],
            workspace_id=values[1],
            artifact_ref=values[2],
            manifest_ref=values[3],
            artifact_hash=values[4],
            capability_id=values[5],
            version=values[6],
            adapter_ref=values[7],
            binding_state=values[8],
            evidence_ref=values[9],
            observed_at=values[10],
        )
    )


def iter_sql_statements(source: str) -> Iterator[str]:
    pending: list[str] = []
    for line in source.splitlines(keepends=True):
        pending.append(line)
        candidate = "".join(pending)
        if sqlite3.complete_statement(candidate):
            statement = candidate.strip()
            pending.clear()
            if statement:
                yield statement
    if "".join(pending).strip():
        raise SchemaHold("HOLD_INCOMPLETE_SCHEMA_SQL")


def _configure_connection(
    conn: sqlite3.Connection,
    *,
    busy_timeout_ms: int,
) -> None:
    if conn.in_transaction:
        raise SchemaHold("HOLD_CONNECTION_ALREADY_IN_TRANSACTION")
    if isinstance(busy_timeout_ms, bool) or busy_timeout_ms < 1:
        raise ValueError("busy_timeout_ms must be a positive integer")
    conn.create_function(
        "w7tp_artifact_binding_hash",
        11,
        _sqlite_artifact_binding_hash,
        deterministic=True,
    )
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = FULL")
    conn.execute(f"PRAGMA busy_timeout = {int(busy_timeout_ms)}")


def _schema_object_names(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type IN ('table', 'index', 'trigger')
              AND name NOT LIKE 'sqlite_%'
            """
        )
    }


def initialize_or_continue(
    conn: sqlite3.Connection,
    schema_v1_source: str,
    *,
    busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
) -> str:
    """Initialize pristine v0 transactionally or continue exact schema v1."""

    _configure_connection(conn, busy_timeout_ms=busy_timeout_ms)
    conn.execute("BEGIN IMMEDIATE")
    try:
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
        if version == EXPECTED_USER_VERSION:
            missing = REQUIRED_V1_SCHEMA_OBJECTS - _schema_object_names(conn)
            if missing:
                raise SchemaHold(
                    "HOLD_SCHEMA_V1_REQUIRED_OBJECTS_MISSING:"
                    + ",".join(sorted(missing))
                )
            conn.commit()
            return "CONTINUE_V1"

        if version != 0:
            raise SchemaHold(
                f"HOLD_UNSUPPORTED_SCHEMA_VERSION:{version}"
            )

        existing = _schema_object_names(conn)
        if existing:
            raise SchemaHold("HOLD_PARTIAL_OR_UNVERSIONED_SCHEMA")

        for statement in iter_sql_statements(schema_v1_source):
            conn.execute(statement)

        conn.execute(f"PRAGMA user_version = {EXPECTED_USER_VERSION}")
        actual = int(conn.execute("PRAGMA user_version").fetchone()[0])
        if actual != EXPECTED_USER_VERSION:
            raise SchemaHold("HOLD_SCHEMA_VERSION_WRITE_FAILED")

        conn.commit()
        return "INITIALIZED_V1"
    except BaseException:
        conn.rollback()
        raise


@dataclass(frozen=True, slots=True)
class CurrentPointerRow:
    resource_id: str
    version_ref: str | None
    generation: int
    transition_ref: str | None
    updated_at: str


@dataclass(frozen=True, slots=True)
class ArtifactBindingRow:
    binding_ref: str
    binding_hash: str
    node_id: str
    workspace_id: str
    artifact_ref: str
    manifest_ref: str
    artifact_hash: str
    capability_id: str
    version: str
    adapter_ref: str
    binding_state: str
    evidence_ref: str
    observed_at: str


@dataclass(frozen=True, slots=True)
class EffectOperationClaimRow:
    idempotency_key: str
    operation_id: str
    effect_contract_ref: str
    claimed_at: str


@dataclass(frozen=True, slots=True)
class EffectAttemptClaimRow:
    operation_id: str
    attempt_no: int
    idempotency_key: str
    effect_contract_ref: str
    claimed_at: str


@dataclass(frozen=True, slots=True)
class TransitionWrite:
    transition_ref: str
    transition_hash: str
    operation_id: str
    resource_id: str
    from_version_ref: str | None
    to_version_ref: str
    expected_generation: int
    receipt_ref: str
    created_at: str


@dataclass(frozen=True, slots=True)
class ReceiptWrite:
    receipt_ref: str
    receipt_hash: str
    operation_id: str
    idempotency_key: str
    transition_ref: str
    effect_contract_ref: str
    effect_contract_hash: str
    result_version_ref: str
    payload_ref: str
    created_at: str


@dataclass(frozen=True, slots=True)
class JournalEventWrite:
    operation_id: str
    attempt_no: int
    sequence_no: int
    effect_contract_ref: str
    effect_contract_hash: str
    event_type: str
    payload_ref: str
    previous_event_hash: str | None
    event_hash: str
    occurred_at: str


@dataclass(frozen=True, slots=True)
class JournalEventRow:
    operation_id: str
    attempt_no: int
    sequence_no: int
    effect_contract_ref: str
    effect_contract_hash: str
    event_type: str
    payload_ref: str
    previous_event_hash: str | None
    event_hash: str
    occurred_at: str


@dataclass(frozen=True, slots=True)
class CommittedReceiptRow:
    receipt_ref: str
    receipt_hash: str
    operation_id: str
    idempotency_key: str
    transition_ref: str
    effect_contract_ref: str
    effect_contract_hash: str
    result_version_ref: str
    payload_ref: str
    created_at: str
    resource_id: str
    from_version_ref: str | None
    to_version_ref: str
    expected_generation: int
    transition_hash: str
    transition_receipt_ref: str
    transition_created_at: str


@dataclass(frozen=True, slots=True)
class StateCommitWrite:
    transition: TransitionWrite
    receipt: ReceiptWrite
    journal: JournalEventWrite
    pointer_updated_at: str


@dataclass(frozen=True, slots=True)
class CommitResult:
    receipt: CommittedReceiptRow
    pointer: CurrentPointerRow
    replayed: bool


class StateFieldTransaction:
    """Operations scoped to one StateFieldStore BEGIN IMMEDIATE."""

    def __init__(self, store: "StateFieldStore") -> None:
        self._store = store

    def insert_transition(self, record: TransitionWrite) -> TransitionWrite:
        self._store._insert_transition(record)
        return record

    def insert_receipt(self, record: ReceiptWrite) -> ReceiptWrite:
        self._store._insert_receipt(record)
        return record

    def cas_current_pointer(
        self,
        *,
        resource_id: str,
        expected_generation: int,
        expected_version_ref: str | None,
        new_version_ref: str,
        transition_ref: str,
        updated_at: str,
    ) -> CurrentPointerRow:
        return self._store._cas_current_pointer(
            resource_id=resource_id,
            expected_generation=expected_generation,
            expected_version_ref=expected_version_ref,
            new_version_ref=new_version_ref,
            transition_ref=transition_ref,
            updated_at=updated_at,
        )

    def append_journal(self, event: JournalEventWrite) -> JournalEventRow:
        return self._store._insert_journal_event(event)


class StateFieldStore:
    """SQLite durability boundary for node-local candidate state."""

    def __init__(
        self,
        db_path: str | Path,
        *,
        schema_path: str | Path | None = None,
        busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
    ) -> None:
        path = Path(db_path)
        if path.exists() and path.is_symlink():
            raise StoreHold("HOLD_STORE_PATH_IS_SYMLINK")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = path.resolve()
        self._lock = threading.RLock()
        self._closed = False
        self._conn = sqlite3.connect(
            str(self.db_path),
            timeout=max(1.0, busy_timeout_ms / 1000.0),
            isolation_level=None,
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        source_path = (
            Path(schema_path) if schema_path is not None else DEFAULT_SCHEMA_PATH
        )
        try:
            source = source_path.read_text(encoding="utf-8")
            self.schema_state = initialize_or_continue(
                self._conn,
                source,
                busy_timeout_ms=busy_timeout_ms,
            )
        except BaseException:
            self._conn.close()
            self._closed = True
            raise

    @property
    def connection(self) -> sqlite3.Connection:
        if self._closed:
            raise StoreHold("HOLD_STORE_CLOSED")
        return self._conn

    @contextmanager
    def begin_immediate(self) -> Iterator[StateFieldTransaction]:
        with self._lock:
            if self._closed:
                raise StoreHold("HOLD_STORE_CLOSED")
            if self._conn.in_transaction:
                raise StoreHold("HOLD_NESTED_TRANSACTION_FORBIDDEN")
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield StateFieldTransaction(self)
                self._conn.commit()
            except BaseException:
                self._conn.rollback()
                raise

    def register_workspace(
        self,
        *,
        workspace_id: str,
        node_id: str,
        root_ref: str,
        created_at: str,
    ) -> None:
        with self.begin_immediate():
            self._conn.execute(
                """
                INSERT INTO workspaces(
                    workspace_id, node_id, root_ref, created_at
                ) VALUES (?, ?, ?, ?)
                """,
                (workspace_id, node_id, root_ref, created_at),
            )

    def register_verified_artifact_binding(
        self,
        *,
        node_id: str,
        workspace_id: str,
        artifact_ref: str,
        manifest_ref: str,
        artifact_hash: str,
        capability_id: str,
        version: str,
        adapter_ref: str,
        evidence_ref: str,
        observed_at: str,
    ) -> ArtifactBindingRow:
        """Seal and append one exact VERIFIED binding.

        Hash, reference, and state are deliberately not caller inputs.
        """

        fields = {
            "node_id": node_id,
            "workspace_id": workspace_id,
            "artifact_ref": artifact_ref,
            "manifest_ref": manifest_ref,
            "artifact_hash": artifact_hash,
            "capability_id": capability_id,
            "version": version,
            "adapter_ref": adapter_ref,
            "evidence_ref": evidence_ref,
            "observed_at": observed_at,
        }
        if any(
            not isinstance(value, str) or not value
            for value in fields.values()
        ):
            raise ValueError("artifact binding fields must be non-empty strings")
        try:
            validate_sha256_ref(manifest_ref)
            validate_sha256_hex(artifact_hash)
        except ValueError as exc:
            raise StoreConflict(
                "QUARANTINE_ARTIFACT_BINDING_COORDINATE_CONFLICT"
            ) from exc

        body = _artifact_binding_body(
            **fields,
            binding_state="VERIFIED",
        )
        binding_hash = canonical_hash(body)
        record = ArtifactBindingRow(
            binding_ref=f"sha256:{binding_hash}",
            binding_hash=binding_hash,
            binding_state="VERIFIED",
            **fields,
        )
        with self.begin_immediate():
            existing = self._conn.execute(
                """
                SELECT binding_ref, binding_hash, node_id,
                       workspace_id, artifact_ref, manifest_ref,
                       artifact_hash, capability_id, version,
                       adapter_ref, binding_state, evidence_ref, observed_at
                FROM artifact_bindings
                WHERE binding_ref = ?
                   OR binding_hash = ?
                   OR (
                        node_id = ?
                        AND workspace_id = ?
                        AND artifact_ref = ?
                        AND manifest_ref = ?
                        AND artifact_hash = ?
                        AND capability_id = ?
                        AND version = ?
                        AND adapter_ref = ?
                   )
                LIMIT 1
                """,
                (
                    record.binding_ref,
                    record.binding_hash,
                    record.node_id,
                    record.workspace_id,
                    record.artifact_ref,
                    record.manifest_ref,
                    record.artifact_hash,
                    record.capability_id,
                    record.version,
                    record.adapter_ref,
                ),
            ).fetchone()
            if existing is not None:
                observed = ArtifactBindingRow(**dict(existing))
                if observed != record:
                    raise StoreConflict(
                        "QUARANTINE_ARTIFACT_BINDING_SEAL_CONFLICT"
                    )
                return observed
            try:
                self._conn.execute(
                    """
                    INSERT INTO artifact_bindings(
                        binding_ref, binding_hash, node_id,
                        workspace_id, artifact_ref, manifest_ref,
                        artifact_hash, capability_id, version,
                        adapter_ref, binding_state, evidence_ref, observed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.binding_ref,
                        record.binding_hash,
                        record.node_id,
                        record.workspace_id,
                        record.artifact_ref,
                        record.manifest_ref,
                        record.artifact_hash,
                        record.capability_id,
                        record.version,
                        record.adapter_ref,
                        record.binding_state,
                        record.evidence_ref,
                        record.observed_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                if "FOREIGN KEY constraint failed" in str(exc):
                    raise StoreHold(
                        "HOLD_ARTIFACT_BINDING_PREREQUISITE_MISSING"
                    ) from exc
                raise StoreConflict(
                    "QUARANTINE_ARTIFACT_BINDING_INSERT_CONFLICT"
                ) from exc
            return record

    def register_resource(
        self,
        *,
        resource_id: str,
        workspace_id: str,
        resource_kind: str,
        version_ref: str | None,
        generation: int,
        created_at: str,
    ) -> None:
        with self.begin_immediate():
            self._conn.execute(
                """
                INSERT INTO resources(
                    resource_id, workspace_id, resource_kind, created_at
                ) VALUES (?, ?, ?, ?)
                """,
                (resource_id, workspace_id, resource_kind, created_at),
            )
            self._conn.execute(
                """
                INSERT INTO current_pointer(
                    resource_id, version_ref, generation,
                    transition_ref, updated_at
                ) VALUES (?, ?, ?, NULL, ?)
                """,
                (resource_id, version_ref, generation, created_at),
            )

    def load_current_pointer_fresh(
        self,
        resource_id: str,
        *,
        bypass_cache: bool = True,
    ) -> CurrentPointerRow:
        del bypass_cache
        with self._lock:
            if self._closed:
                raise StoreHold("HOLD_STORE_CLOSED")
            row = self._conn.execute(
                """
                SELECT resource_id, version_ref, generation,
                       transition_ref, updated_at
                FROM current_pointer
                WHERE resource_id = ?
                """,
                (resource_id,),
            ).fetchone()
        if row is None:
            raise StoreHold("HOLD_CURRENT_POINTER_MISSING")
        return self._pointer_from_row(row)

    def get_committed_by_idempotency(
        self,
        idempotency_key: str,
    ) -> CommittedReceiptRow | None:
        with self._lock:
            if self._closed:
                raise StoreHold("HOLD_STORE_CLOSED")
            return self._get_committed_by_idempotency(idempotency_key)

    def get_effect_operation_claim(
        self,
        idempotency_key: str,
    ) -> EffectOperationClaimRow | None:
        with self._lock:
            if self._closed:
                raise StoreHold("HOLD_STORE_CLOSED")
            return self._get_effect_operation_claim(idempotency_key)

    def get_effect_attempt_claim(
        self,
        operation_id: str,
        attempt_no: int,
    ) -> EffectAttemptClaimRow | None:
        with self._lock:
            if self._closed:
                raise StoreHold("HOLD_STORE_CLOSED")
            return self._get_effect_attempt_claim(operation_id, attempt_no)

    def claim_effect_operation(
        self,
        *,
        idempotency_key: str,
        operation_id: str,
        effect_contract_ref: str,
        attempt_no: int,
        claimed_at: str,
    ) -> Literal["CLAIMED"]:
        """Atomically claim one exact operation attempt before receiver effect.

        A retry attempt is accepted only after the immediately preceding
        attempt has a durable EFFECT_FAILED tail.  The executor must still
        verify the receiver-backed retry evidence before requesting it.
        """

        inputs = (
            idempotency_key,
            operation_id,
            effect_contract_ref,
            claimed_at,
        )
        if any(not isinstance(value, str) or not value for value in inputs):
            raise ValueError("effect operation claim fields must be non-empty")
        if (
            isinstance(attempt_no, bool)
            or not isinstance(attempt_no, int)
            or attempt_no < 1
        ):
            raise ValueError("attempt_no must be a positive integer")
        try:
            validate_sha256_ref(effect_contract_ref)
        except ValueError as exc:
            raise StoreConflict(
                "QUARANTINE_EFFECT_OPERATION_CLAIM_REF_CONFLICT"
            ) from exc

        with self.begin_immediate():
            existing = self._get_effect_operation_claim(idempotency_key)
            committed = self._get_committed_by_idempotency(idempotency_key)
            operation_claim = self._get_effect_operation_claim_by_operation(
                operation_id
            )
            inserted_operation = False
            if existing is not None:
                if (
                    existing.operation_id != operation_id
                    or existing.effect_contract_ref != effect_contract_ref
                ):
                    raise StoreConflict(
                        "QUARANTINE_IDEMPOTENCY_OPERATION_CLAIM_CONFLICT"
                    )
                if operation_claim != existing:
                    raise StoreConflict(
                        "QUARANTINE_IDEMPOTENCY_OPERATION_CLAIM_CONFLICT"
                    )
            else:
                if committed is not None:
                    raise StoreHold(
                        "HOLD_COMMITTED_RECEIPT_WITHOUT_OPERATION_CLAIM"
                    )
                if operation_claim is not None:
                    raise StoreConflict(
                        "QUARANTINE_IDEMPOTENCY_OPERATION_CLAIM_CONFLICT"
                    )
                if attempt_no != 1:
                    raise StoreHold(
                        "HOLD_INITIAL_EFFECT_ATTEMPT_MUST_BE_ONE"
                    )
                self._conn.execute(
                    """
                    INSERT INTO effect_operation_claims(
                        idempotency_key, operation_id,
                        effect_contract_ref, claimed_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        idempotency_key,
                        operation_id,
                        effect_contract_ref,
                        claimed_at,
                    ),
                )
                inserted_operation = True

            if committed is not None:
                raise StoreHold("HOLD_EFFECT_ALREADY_COMMITTED_REPLAY_REQUIRED")

            existing_attempt = self._get_effect_attempt_claim(
                operation_id,
                attempt_no,
            )
            if existing_attempt is not None:
                if (
                    existing_attempt.idempotency_key != idempotency_key
                    or existing_attempt.effect_contract_ref
                    != effect_contract_ref
                ):
                    raise StoreConflict(
                        "QUARANTINE_EFFECT_ATTEMPT_CLAIM_CONFLICT"
                    )
                raise StoreHold(
                    "HOLD_EFFECT_ATTEMPT_ALREADY_CLAIMED_RECOVERY_REQUIRED"
                )

            latest_attempt = self._conn.execute(
                """
                SELECT MAX(attempt_no)
                FROM effect_attempt_claims
                WHERE operation_id = ?
                """,
                (operation_id,),
            ).fetchone()[0]
            if inserted_operation:
                expected_attempt = 1
            elif latest_attempt is None:
                raise StoreHold(
                    "HOLD_ORPHANED_OPERATION_CLAIM_RECOVERY_REQUIRED"
                )
            else:
                expected_attempt = int(latest_attempt) + 1
            if attempt_no != expected_attempt:
                raise StoreHold("HOLD_EFFECT_ATTEMPT_SEQUENCE_GAP")

            if attempt_no > 1:
                previous_tail = self._conn.execute(
                    """
                    SELECT event_type
                    FROM operation_journal
                    WHERE operation_id = ? AND attempt_no = ?
                    ORDER BY sequence_no DESC
                    LIMIT 1
                    """,
                    (operation_id, attempt_no - 1),
                ).fetchone()
                if (
                    previous_tail is None
                    or str(previous_tail[0]) != "EFFECT_FAILED"
                ):
                    raise StoreHold(
                        "HOLD_RETRY_ATTEMPT_RECOVERY_EVIDENCE_REQUIRED"
                    )

            self._conn.execute(
                """
                INSERT INTO effect_attempt_claims(
                    operation_id, attempt_no, idempotency_key,
                    effect_contract_ref, claimed_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    operation_id,
                    attempt_no,
                    idempotency_key,
                    effect_contract_ref,
                    claimed_at,
                ),
            )
            return "CLAIMED"

    def append_journal_event(
        self,
        event: JournalEventWrite,
    ) -> JournalEventRow:
        with self.begin_immediate() as transaction:
            return transaction.append_journal(event)

    def journal_events(
        self,
        operation_id: str,
        *,
        attempt_no: int | None = None,
    ) -> tuple[JournalEventRow, ...]:
        sql = """
            SELECT operation_id, attempt_no, sequence_no,
                   effect_contract_ref, effect_contract_hash,
                   event_type, payload_ref, previous_event_hash,
                   event_hash, occurred_at
            FROM operation_journal
            WHERE operation_id = ?
        """
        parameters: tuple[object, ...] = (operation_id,)
        if attempt_no is not None:
            sql += " AND attempt_no = ?"
            parameters = (operation_id, attempt_no)
        sql += " ORDER BY attempt_no, sequence_no"
        with self._lock:
            rows = self._conn.execute(sql, parameters).fetchall()
        return tuple(self._journal_from_row(row) for row in rows)

    def commit_state(self, write: StateCommitWrite) -> CommitResult:
        self._validate_commit_bundle(write)
        with self.begin_immediate() as transaction:
            self._require_commit_claim_consistency(write)
            existing = self._get_committed_by_idempotency(
                write.receipt.idempotency_key
            )
            if existing is not None:
                self._require_exact_replay(existing, write)
                pointer = self._load_pointer_in_transaction(
                    write.transition.resource_id
                )
                return CommitResult(existing, pointer, True)

            transaction.insert_transition(write.transition)
            transaction.insert_receipt(write.receipt)
            pointer = transaction.cas_current_pointer(
                resource_id=write.transition.resource_id,
                expected_generation=write.transition.expected_generation,
                expected_version_ref=write.transition.from_version_ref,
                new_version_ref=write.transition.to_version_ref,
                transition_ref=write.transition.transition_ref,
                updated_at=write.pointer_updated_at,
            )
            transaction.append_journal(write.journal)
            receipt = self._get_committed_by_idempotency(
                write.receipt.idempotency_key
            )
            if receipt is None:
                raise StoreConflict("QUARANTINE_RECEIPT_NOT_OBSERVABLE")
            return CommitResult(receipt, pointer, False)

    def receipt_exists(self, receipt_ref: str) -> bool:
        return self._exists("receipts", "receipt_ref", receipt_ref)

    def transition_exists(self, transition_ref: str) -> bool:
        return self._exists("transitions", "transition_ref", transition_ref)

    def _exists(self, table: str, column: str, value: str) -> bool:
        allowed = {
            ("receipts", "receipt_ref"),
            ("transitions", "transition_ref"),
        }
        if (table, column) not in allowed:
            raise ValueError("unsupported existence lookup")
        with self._lock:
            row = self._conn.execute(
                f"SELECT 1 FROM {table} WHERE {column} = ?",
                (value,),
            ).fetchone()
        return row is not None

    def _insert_transition(self, record: TransitionWrite) -> None:
        self._validate_transition_identity(record)
        self._conn.execute(
            """
            INSERT INTO transitions(
                transition_ref, transition_hash, operation_id,
                resource_id, from_version_ref, to_version_ref,
                expected_generation, receipt_ref, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.transition_ref,
                record.transition_hash,
                record.operation_id,
                record.resource_id,
                record.from_version_ref,
                record.to_version_ref,
                record.expected_generation,
                record.receipt_ref,
                record.created_at,
            ),
        )

    def _insert_receipt(self, record: ReceiptWrite) -> None:
        self._validate_receipt_identity(record)
        self._conn.execute(
            """
            INSERT INTO receipts(
                receipt_ref, receipt_hash, operation_id,
                idempotency_key, transition_ref,
                effect_contract_ref, effect_contract_hash,
                result_version_ref, payload_ref, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.receipt_ref,
                record.receipt_hash,
                record.operation_id,
                record.idempotency_key,
                record.transition_ref,
                record.effect_contract_ref,
                record.effect_contract_hash,
                record.result_version_ref,
                record.payload_ref,
                record.created_at,
            ),
        )

    def _cas_current_pointer(
        self,
        *,
        resource_id: str,
        expected_generation: int,
        expected_version_ref: str | None,
        new_version_ref: str,
        transition_ref: str,
        updated_at: str,
    ) -> CurrentPointerRow:
        cursor = self._conn.execute(
            """
            UPDATE current_pointer
            SET version_ref = ?,
                generation = generation + 1,
                transition_ref = ?,
                updated_at = ?
            WHERE resource_id = ?
              AND generation = ?
              AND (
                    version_ref = ?
                    OR (version_ref IS NULL AND ? IS NULL)
              )
            """,
            (
                new_version_ref,
                transition_ref,
                updated_at,
                resource_id,
                expected_generation,
                expected_version_ref,
                expected_version_ref,
            ),
        )
        if cursor.rowcount != 1:
            raise CASConflict("STATE_DRIFT_RECOMPUTE_NEW_OPERATION")
        return self._load_pointer_in_transaction(resource_id)

    def _insert_journal_event(
        self,
        event: JournalEventWrite,
    ) -> JournalEventRow:
        self._validate_journal_identity(event)
        latest = self._conn.execute(
            """
            SELECT sequence_no, event_hash
            FROM operation_journal
            WHERE operation_id = ? AND attempt_no = ?
            ORDER BY sequence_no DESC
            LIMIT 1
            """,
            (event.operation_id, event.attempt_no),
        ).fetchone()
        expected_sequence = 0 if latest is None else int(latest[0]) + 1
        expected_previous = None if latest is None else str(latest[1])
        if event.sequence_no != expected_sequence:
            raise JournalHold("HOLD_JOURNAL_SEQUENCE_GAP")
        if event.previous_event_hash != expected_previous:
            raise JournalHold("HOLD_JOURNAL_PREVIOUS_HASH_MISMATCH")

        try:
            current_type = JournalEventType(event.event_type)
        except ValueError:
            current_type = None
        effect_types = {
            JournalEventType.EFFECT_PREPARED,
            JournalEventType.EFFECT_STARTED,
            JournalEventType.EFFECT_OBSERVED,
            JournalEventType.EFFECT_FAILED,
            JournalEventType.EFFECT_ACCEPTED,
            JournalEventType.STATE_COMMITTED,
        }
        if current_type in effect_types:
            previous_effect = self._conn.execute(
                """
                SELECT event_type
                FROM operation_journal
                WHERE operation_id = ? AND attempt_no = ?
                  AND event_type IN (
                    'EFFECT_PREPARED', 'EFFECT_STARTED',
                    'EFFECT_OBSERVED', 'EFFECT_FAILED',
                    'EFFECT_ACCEPTED', 'STATE_COMMITTED'
                  )
                ORDER BY sequence_no DESC
                LIMIT 1
                """,
                (event.operation_id, event.attempt_no),
            ).fetchone()
            previous_type = (
                None
                if previous_effect is None
                else JournalEventType(str(previous_effect[0]))
            )
            try:
                validate_effect_transition(previous_type, current_type)
            except Quarantine as exc:
                raise JournalHold(
                    "HOLD_EFFECT_JOURNAL_TRANSITION_CONFLICT"
                ) from exc

        self._conn.execute(
            """
            INSERT INTO operation_journal(
                operation_id, attempt_no, sequence_no,
                effect_contract_ref, effect_contract_hash,
                event_type, payload_ref, previous_event_hash,
                event_hash, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.operation_id,
                event.attempt_no,
                event.sequence_no,
                event.effect_contract_ref,
                event.effect_contract_hash,
                event.event_type,
                event.payload_ref,
                event.previous_event_hash,
                event.event_hash,
                event.occurred_at,
            ),
        )
        return JournalEventRow(
            operation_id=event.operation_id,
            attempt_no=event.attempt_no,
            sequence_no=event.sequence_no,
            effect_contract_ref=event.effect_contract_ref,
            effect_contract_hash=event.effect_contract_hash,
            event_type=event.event_type,
            payload_ref=event.payload_ref,
            previous_event_hash=event.previous_event_hash,
            event_hash=event.event_hash,
            occurred_at=event.occurred_at,
        )

    def _get_committed_by_idempotency(
        self,
        idempotency_key: str,
    ) -> CommittedReceiptRow | None:
        row = self._conn.execute(
            """
            SELECT
                r.receipt_ref,
                r.receipt_hash,
                r.operation_id,
                r.idempotency_key,
                r.transition_ref,
                r.effect_contract_ref,
                r.effect_contract_hash,
                r.result_version_ref,
                r.payload_ref,
                r.created_at,
                t.resource_id,
                t.from_version_ref,
                t.to_version_ref,
                t.expected_generation,
                t.transition_hash,
                t.receipt_ref AS transition_receipt_ref,
                t.created_at AS transition_created_at
            FROM receipts AS r
            JOIN transitions AS t
              ON t.transition_ref = r.transition_ref
            WHERE r.idempotency_key = ?
            """,
            (idempotency_key,),
        ).fetchone()
        if row is None:
            return None
        return CommittedReceiptRow(**dict(row))

    def _get_effect_operation_claim(
        self,
        idempotency_key: str,
    ) -> EffectOperationClaimRow | None:
        row = self._conn.execute(
            """
            SELECT idempotency_key, operation_id,
                   effect_contract_ref, claimed_at
            FROM effect_operation_claims
            WHERE idempotency_key = ?
            """,
            (idempotency_key,),
        ).fetchone()
        if row is None:
            return None
        return EffectOperationClaimRow(**dict(row))

    def _get_effect_operation_claim_by_operation(
        self,
        operation_id: str,
    ) -> EffectOperationClaimRow | None:
        row = self._conn.execute(
            """
            SELECT idempotency_key, operation_id,
                   effect_contract_ref, claimed_at
            FROM effect_operation_claims
            WHERE operation_id = ?
            """,
            (operation_id,),
        ).fetchone()
        if row is None:
            return None
        return EffectOperationClaimRow(**dict(row))

    def _get_effect_attempt_claim(
        self,
        operation_id: str,
        attempt_no: int,
    ) -> EffectAttemptClaimRow | None:
        row = self._conn.execute(
            """
            SELECT operation_id, attempt_no, idempotency_key,
                   effect_contract_ref, claimed_at
            FROM effect_attempt_claims
            WHERE operation_id = ? AND attempt_no = ?
            """,
            (operation_id, attempt_no),
        ).fetchone()
        if row is None:
            return None
        return EffectAttemptClaimRow(
            operation_id=str(row["operation_id"]),
            attempt_no=int(row["attempt_no"]),
            idempotency_key=str(row["idempotency_key"]),
            effect_contract_ref=str(row["effect_contract_ref"]),
            claimed_at=str(row["claimed_at"]),
        )

    def _require_commit_claim_consistency(
        self,
        write: StateCommitWrite,
    ) -> None:
        receipt = write.receipt
        claim_by_key = self._get_effect_operation_claim(
            receipt.idempotency_key
        )
        claim_by_operation = self._get_effect_operation_claim_by_operation(
            receipt.operation_id
        )
        if claim_by_key is None or claim_by_operation is None:
            raise StoreHold("HOLD_EFFECT_OPERATION_CLAIM_MISSING")
        if (
            claim_by_key != claim_by_operation
            or claim_by_key.idempotency_key != receipt.idempotency_key
            or claim_by_key.operation_id != receipt.operation_id
            or claim_by_key.effect_contract_ref
            != receipt.effect_contract_ref
        ):
            raise StoreConflict(
                "QUARANTINE_IDEMPOTENCY_OPERATION_CLAIM_CONFLICT"
            )

        attempt_claim = self._get_effect_attempt_claim(
            receipt.operation_id,
            write.journal.attempt_no,
        )
        if attempt_claim is None:
            raise StoreHold("HOLD_EFFECT_ATTEMPT_CLAIM_MISSING")
        if (
            attempt_claim.idempotency_key != receipt.idempotency_key
            or attempt_claim.effect_contract_ref
            != receipt.effect_contract_ref
        ):
            raise StoreConflict(
                "QUARANTINE_EFFECT_ATTEMPT_CLAIM_CONFLICT"
            )

    def _load_pointer_in_transaction(
        self,
        resource_id: str,
    ) -> CurrentPointerRow:
        row = self._conn.execute(
            """
            SELECT resource_id, version_ref, generation,
                   transition_ref, updated_at
            FROM current_pointer
            WHERE resource_id = ?
            """,
            (resource_id,),
        ).fetchone()
        if row is None:
            raise StoreHold("HOLD_CURRENT_POINTER_MISSING")
        return self._pointer_from_row(row)

    @staticmethod
    def _pointer_from_row(row: sqlite3.Row) -> CurrentPointerRow:
        return CurrentPointerRow(
            resource_id=str(row["resource_id"]),
            version_ref=row["version_ref"],
            generation=int(row["generation"]),
            transition_ref=row["transition_ref"],
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _journal_from_row(row: sqlite3.Row) -> JournalEventRow:
        return JournalEventRow(
            operation_id=str(row["operation_id"]),
            attempt_no=int(row["attempt_no"]),
            sequence_no=int(row["sequence_no"]),
            effect_contract_ref=str(row["effect_contract_ref"]),
            effect_contract_hash=str(row["effect_contract_hash"]),
            event_type=str(row["event_type"]),
            payload_ref=str(row["payload_ref"]),
            previous_event_hash=row["previous_event_hash"],
            event_hash=str(row["event_hash"]),
            occurred_at=str(row["occurred_at"]),
        )

    @staticmethod
    def _validate_commit_bundle(write: StateCommitWrite) -> None:
        transition = write.transition
        receipt = write.receipt
        journal = write.journal
        if journal.event_type != "STATE_COMMITTED":
            raise StoreConflict("QUARANTINE_COMMIT_EVENT_TYPE_CONFLICT")
        if not (
            transition.operation_id
            == receipt.operation_id
            == journal.operation_id
        ):
            raise StoreConflict("QUARANTINE_OPERATION_BINDING_CONFLICT")
        if transition.receipt_ref != receipt.receipt_ref:
            raise StoreConflict("QUARANTINE_RECEIPT_BINDING_CONFLICT")
        if receipt.transition_ref != transition.transition_ref:
            raise StoreConflict("QUARANTINE_TRANSITION_BINDING_CONFLICT")
        if receipt.result_version_ref != transition.to_version_ref:
            raise StoreConflict("QUARANTINE_RESULT_VERSION_CONFLICT")
        if (
            receipt.effect_contract_ref != journal.effect_contract_ref
            or receipt.effect_contract_hash != journal.effect_contract_hash
        ):
            raise StoreConflict("QUARANTINE_EFFECT_CONTRACT_BINDING_CONFLICT")

        StateFieldStore._validate_transition_identity(transition)
        StateFieldStore._validate_receipt_identity(receipt)
        StateFieldStore._validate_journal_identity(journal)

    @staticmethod
    def _validate_transition_identity(record: TransitionWrite) -> None:
        body = {
            "schema_id": "W7TP_STATE_TRANSITION_V1",
            "operation_id": record.operation_id,
            "resource_id": record.resource_id,
            "from_version_ref": record.from_version_ref,
            "to_version_ref": record.to_version_ref,
            "expected_generation": record.expected_generation,
            "receipt_ref": record.receipt_ref,
            "created_at": record.created_at,
        }
        expected = canonical_hash(body)
        if (
            record.transition_hash != expected
            or record.transition_ref != f"sha256:{expected}"
        ):
            raise StoreConflict("QUARANTINE_TRANSITION_HASH_CONFLICT")

    @staticmethod
    def _validate_receipt_identity(record: ReceiptWrite) -> None:
        try:
            validate_sha256_hex(record.receipt_hash)
            validate_sha256_ref(record.receipt_ref)
            validate_sha256_hex(record.effect_contract_hash)
            validate_sha256_ref(record.effect_contract_ref)
            validate_sha256_ref(record.payload_ref)
        except ValueError as exc:
            raise StoreConflict("QUARANTINE_RECEIPT_HASH_CONFLICT") from exc
        if (
            record.receipt_ref != f"sha256:{record.receipt_hash}"
            or record.effect_contract_ref
            != f"sha256:{record.effect_contract_hash}"
            or record.payload_ref != record.receipt_ref
        ):
            raise StoreConflict("QUARANTINE_RECEIPT_HASH_CONFLICT")

    @staticmethod
    def _validate_journal_identity(event: JournalEventWrite) -> None:
        body = {
            "operation_id": event.operation_id,
            "attempt_no": event.attempt_no,
            "sequence_no": event.sequence_no,
            "effect_contract_ref": event.effect_contract_ref,
            "effect_contract_hash": event.effect_contract_hash,
            "event_type": event.event_type,
            "payload_ref": event.payload_ref,
            "previous_event_hash": event.previous_event_hash,
            "occurred_at": event.occurred_at,
        }
        expected = canonical_hash(body)
        if event.event_hash != expected:
            raise JournalHold("HOLD_JOURNAL_EVENT_HASH_CONFLICT")

    def _require_exact_replay(
        self,
        existing: CommittedReceiptRow,
        write: StateCommitWrite,
    ) -> None:
        transition = write.transition
        receipt = write.receipt
        expected = (
            receipt.receipt_ref,
            receipt.receipt_hash,
            receipt.operation_id,
            receipt.idempotency_key,
            receipt.transition_ref,
            receipt.effect_contract_ref,
            receipt.effect_contract_hash,
            receipt.result_version_ref,
            receipt.payload_ref,
            receipt.created_at,
            transition.transition_ref,
            transition.transition_hash,
            transition.resource_id,
            transition.from_version_ref,
            transition.to_version_ref,
            transition.expected_generation,
            transition.receipt_ref,
            transition.created_at,
        )
        observed = (
            existing.receipt_ref,
            existing.receipt_hash,
            existing.operation_id,
            existing.idempotency_key,
            existing.transition_ref,
            existing.effect_contract_ref,
            existing.effect_contract_hash,
            existing.result_version_ref,
            existing.payload_ref,
            existing.created_at,
            existing.transition_ref,
            existing.transition_hash,
            existing.resource_id,
            existing.from_version_ref,
            existing.to_version_ref,
            existing.expected_generation,
            existing.transition_receipt_ref,
            existing.transition_created_at,
        )
        if observed != expected:
            raise StoreConflict("QUARANTINE_IDEMPOTENCY_CONFLICT")
        row = self._conn.execute(
            """
            SELECT operation_id, attempt_no, sequence_no,
                   effect_contract_ref, effect_contract_hash,
                   event_type, payload_ref, previous_event_hash,
                   event_hash, occurred_at
            FROM operation_journal
            WHERE operation_id = ? AND event_type = 'STATE_COMMITTED'
            ORDER BY attempt_no DESC, sequence_no DESC
            LIMIT 1
            """,
            (existing.operation_id,),
        ).fetchone()
        if row is None:
            raise StoreConflict("QUARANTINE_REPLAY_JOURNAL_MISSING")
        committed_event = JournalEventRow(**dict(row))
        if committed_event != JournalEventRow(
            operation_id=write.journal.operation_id,
            attempt_no=write.journal.attempt_no,
            sequence_no=write.journal.sequence_no,
            effect_contract_ref=write.journal.effect_contract_ref,
            effect_contract_hash=write.journal.effect_contract_hash,
            event_type=write.journal.event_type,
            payload_ref=write.journal.payload_ref,
            previous_event_hash=write.journal.previous_event_hash,
            event_hash=write.journal.event_hash,
            occurred_at=write.journal.occurred_at,
        ):
            raise StoreConflict("QUARANTINE_IDEMPOTENCY_JOURNAL_CONFLICT")

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

    def __enter__(self) -> "StateFieldStore":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        del exc_type, exc, traceback
        self.close()
