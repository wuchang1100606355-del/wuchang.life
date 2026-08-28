from __future__ import annotations

import hashlib
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from w7tp_runtime.state_field.canonical import canonical_hash
from w7tp_runtime.state_field.models import ArtifactBinding, BindingState
from w7tp_runtime.state_field.store import (
    CASConflict,
    DEFAULT_SCHEMA_PATH,
    JournalEventWrite,
    JournalHold,
    ReceiptWrite,
    SchemaHold,
    StateCommitWrite,
    StateFieldStore,
    StoreConflict,
    StoreHold,
    TransitionWrite,
    initialize_or_continue,
)


NOW = "2026-08-23T00:00:00+00:00"
EFFECT_HASH = hashlib.sha256(b"effect-contract").hexdigest()
EFFECT_REF = f"sha256:{EFFECT_HASH}"


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def sha_ref(label: str) -> tuple[str, str]:
    value = digest(label)
    return f"sha256:{value}", value


def journal_event(
    *,
    operation_id: str,
    sequence_no: int,
    event_type: str,
    previous_event_hash: str | None,
    attempt_no: int = 1,
) -> JournalEventWrite:
    fields = {
        "operation_id": operation_id,
        "attempt_no": attempt_no,
        "sequence_no": sequence_no,
        "effect_contract_ref": EFFECT_REF,
        "effect_contract_hash": EFFECT_HASH,
        "event_type": event_type,
        "payload_ref": f"payload:{operation_id}:{sequence_no}",
        "previous_event_hash": previous_event_hash,
        "occurred_at": NOW,
    }
    return JournalEventWrite(
        operation_id=operation_id,
        attempt_no=attempt_no,
        sequence_no=sequence_no,
        effect_contract_ref=EFFECT_REF,
        effect_contract_hash=EFFECT_HASH,
        event_type=event_type,
        payload_ref=f"payload:{operation_id}:{sequence_no}",
        previous_event_hash=previous_event_hash,
        event_hash=canonical_hash(fields),
        occurred_at=NOW,
    )


class SchemaGateTests(unittest.TestCase):
    def test_pristine_v0_initializes_and_v1_continues(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "state.db"
            with StateFieldStore(database) as store:
                self.assertEqual(store.schema_state, "INITIALIZED_V1")
                self.assertEqual(
                    store.connection.execute(
                        "PRAGMA user_version"
                    ).fetchone()[0],
                    1,
                )
                self.assertEqual(
                    store.connection.execute(
                        "PRAGMA journal_mode"
                    ).fetchone()[0],
                    "wal",
                )
                self.assertEqual(
                    store.connection.execute(
                        "PRAGMA synchronous"
                    ).fetchone()[0],
                    2,
                )
                self.assertEqual(
                    store.connection.execute(
                        "PRAGMA foreign_keys"
                    ).fetchone()[0],
                    1,
                )
                self.assertEqual(
                    store.connection.execute(
                        "PRAGMA busy_timeout"
                    ).fetchone()[0],
                    5000,
                )
                result = initialize_or_continue(
                    store.connection,
                    DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8"),
                )
                self.assertEqual(result, "CONTINUE_V1")

    def test_unsupported_user_version_holds_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "unsupported.db"
            conn = sqlite3.connect(database, isolation_level=None)
            try:
                conn.execute("PRAGMA user_version = 2")
                with self.assertRaisesRegex(
                    SchemaHold,
                    "HOLD_UNSUPPORTED_SCHEMA_VERSION:2",
                ):
                    initialize_or_continue(
                        conn,
                        DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8"),
                    )
                self.assertEqual(
                    conn.execute("PRAGMA user_version").fetchone()[0],
                    2,
                )
                tables = {
                    row[0]
                    for row in conn.execute(
                        """
                        SELECT name FROM sqlite_master
                        WHERE type = 'table'
                        """
                    )
                }
                self.assertNotIn("workspaces", tables)
            finally:
                conn.close()

    def test_versioned_v1_missing_claim_schema_holds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "stale-v1.db"
            conn = sqlite3.connect(database, isolation_level=None)
            try:
                conn.execute("PRAGMA user_version = 1")
                with self.assertRaisesRegex(
                    SchemaHold,
                    "HOLD_SCHEMA_V1_REQUIRED_OBJECTS_MISSING",
                ):
                    initialize_or_continue(
                        conn,
                        DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8"),
                    )
                self.assertEqual(
                    conn.execute("PRAGMA user_version").fetchone()[0],
                    1,
                )
                self.assertNotIn(
                    "effect_operation_claims",
                    {
                        row[0]
                        for row in conn.execute(
                            "SELECT name FROM sqlite_master"
                        )
                    },
                )
            finally:
                conn.close()

    def test_partial_unversioned_v0_holds_and_preserves_residue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "partial.db"
            conn = sqlite3.connect(database, isolation_level=None)
            try:
                conn.execute("CREATE TABLE residue(value TEXT)")
                with self.assertRaisesRegex(
                    SchemaHold,
                    "HOLD_PARTIAL_OR_UNVERSIONED_SCHEMA",
                ):
                    initialize_or_continue(
                        conn,
                        DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8"),
                    )
                tables = {
                    row[0]
                    for row in conn.execute(
                        """
                        SELECT name FROM sqlite_master
                        WHERE type = 'table'
                        """
                    )
                }
                self.assertIn("residue", tables)
                self.assertNotIn("workspaces", tables)
                self.assertEqual(
                    conn.execute("PRAGMA user_version").fetchone()[0],
                    0,
                )
            finally:
                conn.close()


class StateFieldStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = StateFieldStore(
            Path(self.temporary.name) / "state.db"
        )
        self.store.register_workspace(
            workspace_id="workspace:msi",
            node_id="node:msi",
            root_ref="root:/home/taiji_admin/Taiji_Hub",
            created_at=NOW,
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def test_manifest_relations_preserve_entry_and_chunk_coordinates(
        self,
    ) -> None:
        manifest_ref, manifest_hash = sha_ref("manifest")
        object_a, object_a_hash = sha_ref("chunk-a")
        object_b, object_b_hash = sha_ref("chunk-b")
        file_hash = digest("complete-file")

        with self.store.begin_immediate():
            self.store.connection.executemany(
                """
                INSERT INTO objects(
                    object_id, object_sha256, size_bytes,
                    storage_ref, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    (object_a, object_a_hash, 3, "object:a", NOW),
                    (object_b, object_b_hash, 4, "object:b", NOW),
                ),
            )
            self.store.connection.execute(
                """
                INSERT INTO manifests(
                    manifest_ref, manifest_hash, entry_count, created_at
                ) VALUES (?, ?, 2, ?)
                """,
                (manifest_ref, manifest_hash, NOW),
            )
            self.store.connection.executemany(
                """
                INSERT INTO manifest_entry(
                    manifest_ref, entry_ordinal, logical_path,
                    entry_kind, mode, size_bytes, file_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        manifest_ref,
                        0,
                        "payload",
                        "DIRECTORY",
                        0o755,
                        0,
                        None,
                    ),
                    (
                        manifest_ref,
                        1,
                        "payload/data.bin",
                        "FILE",
                        0o640,
                        7,
                        file_hash,
                    ),
                ),
            )
            self.store.connection.executemany(
                """
                INSERT INTO manifest_entry_chunk(
                    manifest_ref, entry_ordinal, chunk_ordinal,
                    object_id, byte_offset, byte_length
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    (manifest_ref, 1, 0, object_a, 0, 3),
                    (manifest_ref, 1, 1, object_b, 3, 4),
                ),
            )

        entries = self.store.connection.execute(
            """
            SELECT entry_ordinal, logical_path, entry_kind,
                   mode, size_bytes, file_sha256
            FROM manifest_entry
            WHERE manifest_ref = ?
            ORDER BY entry_ordinal
            """,
            (manifest_ref,),
        ).fetchall()
        self.assertEqual(
            [tuple(row) for row in entries],
            [
                (0, "payload", "DIRECTORY", 0o755, 0, None),
                (
                    1,
                    "payload/data.bin",
                    "FILE",
                    0o640,
                    7,
                    file_hash,
                ),
            ],
        )

        chunks = self.store.connection.execute(
            """
            SELECT entry_ordinal, chunk_ordinal, object_id,
                   byte_offset, byte_length
            FROM manifest_entry_chunk
            WHERE manifest_ref = ?
            ORDER BY entry_ordinal, chunk_ordinal
            """,
            (manifest_ref,),
        ).fetchall()
        self.assertEqual(
            [tuple(row) for row in chunks],
            [
                (1, 0, object_a, 0, 3),
                (1, 1, object_b, 3, 4),
            ],
        )
        immutable_mutations = (
            (
                "UPDATE objects SET size_bytes = 9 WHERE object_id = ?",
                (object_a,),
                "objects append-only",
            ),
            (
                "UPDATE manifests SET entry_count = 7 WHERE manifest_ref = ?",
                (manifest_ref,),
                "manifests append-only",
            ),
            (
                "UPDATE manifest_entry SET mode = 384 WHERE manifest_ref = ? AND entry_ordinal = 1",
                (manifest_ref,),
                "manifest_entry append-only",
            ),
            (
                "DELETE FROM manifest_entry_chunk WHERE manifest_ref = ? AND entry_ordinal = 1 AND chunk_ordinal = 0",
                (manifest_ref,),
                "manifest_entry_chunk append-only",
            ),
        )
        for statement, parameters, reason in immutable_mutations:
            with self.subTest(reason=reason), self.assertRaisesRegex(
                sqlite3.IntegrityError, reason
            ):
                self.store.connection.execute(statement, parameters)

    def test_artifact_binding_is_hash_checked_and_append_only(self) -> None:
        manifest_ref, manifest_hash = sha_ref("binding-manifest")
        with self.store.begin_immediate():
            self.store.connection.execute(
                """
                INSERT INTO manifests(
                    manifest_ref, manifest_hash, entry_count, created_at
                ) VALUES (?, ?, 0, ?)
                """,
                (manifest_ref, manifest_hash, NOW),
            )

        binding = self.store.register_verified_artifact_binding(
            node_id="node:msi",
            workspace_id="workspace:msi",
            artifact_ref="artifact:opaque",
            manifest_ref=manifest_ref,
            artifact_hash=digest("artifact"),
            capability_id="w7tp-deterministic-effect-gate",
            version="1",
            adapter_ref="adapter:static:v1",
            evidence_ref="evidence:sealed",
            observed_at=NOW,
        )
        expected_model = ArtifactBinding(
            binding_ref=binding.binding_ref,
            binding_hash=binding.binding_hash,
            node_id=binding.node_id,
            workspace_id=binding.workspace_id,
            artifact_ref=binding.artifact_ref,
            manifest_ref=binding.manifest_ref,
            artifact_hash=binding.artifact_hash,
            capability_id=binding.capability_id,
            version=binding.version,
            adapter_ref=binding.adapter_ref,
            binding_state=BindingState.VERIFIED,
            evidence_ref=binding.evidence_ref,
            observed_at=binding.observed_at,
        )
        expected_hash = canonical_hash(expected_model.sealed_body())
        self.assertEqual(binding.binding_hash, expected_hash)
        self.assertEqual(binding.binding_ref, f"sha256:{expected_hash}")
        self.assertEqual(binding.binding_state, "VERIFIED")
        self.assertEqual(
            self.store.register_verified_artifact_binding(
                node_id="node:msi",
                workspace_id="workspace:msi",
                artifact_ref="artifact:opaque",
                manifest_ref=manifest_ref,
                artifact_hash=digest("artifact"),
                capability_id="w7tp-deterministic-effect-gate",
                version="1",
                adapter_ref="adapter:static:v1",
                evidence_ref="evidence:sealed",
                observed_at=NOW,
            ),
            binding,
        )

        forged_hash = canonical_hash(
            {
                "node_id": "node:msi",
                "workspace_id": "workspace:msi",
                "artifact_ref": "artifact:forged",
                "manifest_ref": manifest_ref,
                "artifact_hash": digest("artifact-forged"),
                "capability_id": "w7tp-deterministic-effect-gate",
                "version": "1",
                "adapter_ref": "adapter:static:v1",
            }
        )
        with self.assertRaisesRegex(
            sqlite3.IntegrityError,
            "artifact_bindings sealed hash conflict",
        ):
            self.store.connection.execute(
                """
                INSERT INTO artifact_bindings(
                    binding_ref, binding_hash, node_id,
                    workspace_id, artifact_ref, manifest_ref,
                    artifact_hash, capability_id, version,
                    adapter_ref, binding_state, evidence_ref, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"sha256:{forged_hash}",
                    forged_hash,
                    "node:msi",
                    "workspace:msi",
                    "artifact:forged",
                    manifest_ref,
                    digest("artifact-forged"),
                    "w7tp-deterministic-effect-gate",
                    "1",
                    "adapter:static:v1",
                    "VERIFIED",
                    "evidence:sealed",
                    NOW,
                ),
            )

        with self.assertRaisesRegex(
            sqlite3.IntegrityError,
            "artifact_bindings append-only",
        ):
            self.store.connection.execute(
                """
                UPDATE artifact_bindings
                SET binding_state = 'HOLD'
                WHERE binding_ref = ?
                """,
                (binding.binding_ref,),
            )
        with self.assertRaisesRegex(
            sqlite3.IntegrityError,
            "artifact_bindings append-only",
        ):
            self.store.connection.execute(
                "DELETE FROM artifact_bindings WHERE binding_ref = ?",
                (binding.binding_ref,),
            )

        candidate_hash = canonical_hash(
            {
                "schema_id": "W7TP_ARTIFACT_BINDING_V1",
                "node_id": "node:msi",
                "workspace_id": "workspace:msi",
                "artifact_ref": "artifact:candidate",
                "manifest_ref": manifest_ref,
                "artifact_hash": digest("artifact-candidate"),
                "capability_id": "w7tp-deterministic-effect-gate",
                "version": "1",
                "adapter_ref": "adapter:static:v1",
                "binding_state": "CANDIDATE",
                "evidence_ref": "evidence:unverified",
                "observed_at": NOW,
            }
        )
        with self.assertRaisesRegex(
            sqlite3.IntegrityError,
            "artifact_bindings VERIFIED required",
        ):
            self.store.connection.execute(
                """
                INSERT INTO artifact_bindings(
                    binding_ref, binding_hash, node_id,
                    workspace_id, artifact_ref, manifest_ref,
                    artifact_hash, capability_id, version,
                    adapter_ref, binding_state, evidence_ref, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"sha256:{candidate_hash}",
                    candidate_hash,
                    "node:msi",
                    "workspace:msi",
                    "artifact:candidate",
                    manifest_ref,
                    digest("artifact-candidate"),
                    "w7tp-deterministic-effect-gate",
                    "1",
                    "adapter:static:v1",
                    "CANDIDATE",
                    "evidence:unverified",
                    NOW,
                ),
            )

    def test_effect_operation_claim_is_append_only_and_orphan_safe(
        self,
    ) -> None:
        self.assertEqual(
            self.store.claim_effect_operation(
                idempotency_key="idempotency:claim",
                operation_id="operation:claim",
                effect_contract_ref=EFFECT_REF,
                attempt_no=1,
                claimed_at=NOW,
            ),
            "CLAIMED",
        )
        operation_claim = self.store.get_effect_operation_claim(
            "idempotency:claim"
        )
        attempt_claim = self.store.get_effect_attempt_claim(
            "operation:claim",
            1,
        )
        self.assertIsNotNone(operation_claim)
        self.assertIsNotNone(attempt_claim)
        self.assertEqual(operation_claim.operation_id, "operation:claim")
        self.assertEqual(attempt_claim.idempotency_key, "idempotency:claim")

        with self.assertRaisesRegex(
            StoreHold,
            "HOLD_EFFECT_ATTEMPT_ALREADY_CLAIMED_RECOVERY_REQUIRED",
        ):
            self.store.claim_effect_operation(
                idempotency_key="idempotency:claim",
                operation_id="operation:claim",
                effect_contract_ref=EFFECT_REF,
                attempt_no=1,
                claimed_at="2026-08-23T00:00:01+00:00",
            )

        other_effect_ref, _ = sha_ref("other-effect-contract")
        conflict_cases = (
            (
                "idempotency:claim",
                "operation:other",
                EFFECT_REF,
            ),
            (
                "idempotency:claim",
                "operation:claim",
                other_effect_ref,
            ),
            (
                "idempotency:other",
                "operation:claim",
                EFFECT_REF,
            ),
        )
        for key, operation, contract in conflict_cases:
            with self.subTest(
                key=key,
                operation=operation,
                contract=contract,
            ), self.assertRaisesRegex(
                StoreConflict,
                "QUARANTINE_IDEMPOTENCY_OPERATION_CLAIM_CONFLICT",
            ):
                self.store.claim_effect_operation(
                    idempotency_key=key,
                    operation_id=operation,
                    effect_contract_ref=contract,
                    attempt_no=1,
                    claimed_at=NOW,
                )

        immutable_mutations = (
            (
                """
                UPDATE effect_operation_claims
                SET claimed_at = ?
                WHERE idempotency_key = ?
                """,
                ("later", "idempotency:claim"),
                "effect_operation_claims append-only",
            ),
            (
                """
                DELETE FROM effect_attempt_claims
                WHERE operation_id = ? AND attempt_no = 1
                """,
                ("operation:claim",),
                "effect_attempt_claims append-only",
            ),
        )
        for statement, parameters, reason in immutable_mutations:
            with self.subTest(reason=reason), self.assertRaisesRegex(
                sqlite3.IntegrityError,
                reason,
            ):
                self.store.connection.execute(statement, parameters)

    def test_two_connections_compete_for_one_effect_claim(self) -> None:
        second = StateFieldStore(self.store.db_path)
        barrier = threading.Barrier(2)

        def attempt(
            store: StateFieldStore,
            operation_id: str,
            effect_contract_ref: str,
        ) -> str:
            barrier.wait(timeout=5)
            try:
                return store.claim_effect_operation(
                    idempotency_key="idempotency:race",
                    operation_id=operation_id,
                    effect_contract_ref=effect_contract_ref,
                    attempt_no=1,
                    claimed_at=NOW,
                )
            except StoreConflict as error:
                return f"CONFLICT:{error}"

        other_effect_ref, _ = sha_ref("race-other-contract")
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = (
                    pool.submit(
                        attempt,
                        self.store,
                        "operation:race:a",
                        EFFECT_REF,
                    ),
                    pool.submit(
                        attempt,
                        second,
                        "operation:race:b",
                        other_effect_ref,
                    ),
                )
                outcomes = tuple(future.result(timeout=10) for future in futures)
        finally:
            second.close()

        self.assertEqual(outcomes.count("CLAIMED"), 1)
        self.assertEqual(
            sum(
                outcome
                == (
                    "CONFLICT:"
                    "QUARANTINE_IDEMPOTENCY_OPERATION_CLAIM_CONFLICT"
                )
                for outcome in outcomes
            ),
            1,
        )
        self.assertEqual(
            self.store.connection.execute(
                "SELECT COUNT(*) FROM effect_operation_claims"
            ).fetchone()[0],
            1,
        )
        self.assertEqual(
            self.store.connection.execute(
                "SELECT COUNT(*) FROM effect_attempt_claims"
            ).fetchone()[0],
            1,
        )

    def test_retry_attempt_claim_requires_failed_previous_tail(self) -> None:
        operation = "operation:retry-claim"
        key = "idempotency:retry-claim"
        self.assertEqual(
            self.store.claim_effect_operation(
                idempotency_key=key,
                operation_id=operation,
                effect_contract_ref=EFFECT_REF,
                attempt_no=1,
                claimed_at=NOW,
            ),
            "CLAIMED",
        )
        prepared = journal_event(
            operation_id=operation,
            sequence_no=0,
            event_type="EFFECT_PREPARED",
            previous_event_hash=None,
            attempt_no=1,
        )
        self.store.append_journal_event(prepared)
        failed = journal_event(
            operation_id=operation,
            sequence_no=1,
            event_type="EFFECT_FAILED",
            previous_event_hash=prepared.event_hash,
            attempt_no=1,
        )
        self.store.append_journal_event(failed)
        self.assertEqual(
            self.store.claim_effect_operation(
                idempotency_key=key,
                operation_id=operation,
                effect_contract_ref=EFFECT_REF,
                attempt_no=2,
                claimed_at="2026-08-23T00:00:02+00:00",
            ),
            "CLAIMED",
        )
        with self.assertRaisesRegex(
            StoreHold,
            "HOLD_EFFECT_ATTEMPT_ALREADY_CLAIMED_RECOVERY_REQUIRED",
        ):
            self.store.claim_effect_operation(
                idempotency_key=key,
                operation_id=operation,
                effect_contract_ref=EFFECT_REF,
                attempt_no=2,
                claimed_at="2026-08-23T00:00:03+00:00",
            )

        unsafe_operation = "operation:started-tail"
        unsafe_key = "idempotency:started-tail"
        self.store.claim_effect_operation(
            idempotency_key=unsafe_key,
            operation_id=unsafe_operation,
            effect_contract_ref=EFFECT_REF,
            attempt_no=1,
            claimed_at=NOW,
        )
        unsafe_prepared = journal_event(
            operation_id=unsafe_operation,
            sequence_no=0,
            event_type="EFFECT_PREPARED",
            previous_event_hash=None,
            attempt_no=1,
        )
        self.store.append_journal_event(unsafe_prepared)
        self.store.append_journal_event(
            journal_event(
                operation_id=unsafe_operation,
                sequence_no=1,
                event_type="EFFECT_STARTED",
                previous_event_hash=unsafe_prepared.event_hash,
                attempt_no=1,
            )
        )
        with self.assertRaisesRegex(
            StoreHold,
            "HOLD_RETRY_ATTEMPT_RECOVERY_EVIDENCE_REQUIRED",
        ):
            self.store.claim_effect_operation(
                idempotency_key=unsafe_key,
                operation_id=unsafe_operation,
                effect_contract_ref=EFFECT_REF,
                attempt_no=2,
                claimed_at="2026-08-23T00:00:04+00:00",
            )

    def test_journal_preserves_effect_events_and_exact_hash_chain(
        self,
    ) -> None:
        operation = "operation:journal"
        event_types = (
            "EFFECT_PREPARED",
            "EFFECT_STARTED",
            "EFFECT_OBSERVED",
            "EFFECT_ACCEPTED",
        )
        previous = None
        for sequence, event_type in enumerate(event_types):
            event = journal_event(
                operation_id=operation,
                sequence_no=sequence,
                event_type=event_type,
                previous_event_hash=previous,
            )
            self.store.append_journal_event(event)
            previous = event.event_hash

        failed_operation = "operation:failed"
        prepared = journal_event(
            operation_id=failed_operation,
            sequence_no=0,
            event_type="EFFECT_PREPARED",
            previous_event_hash=None,
        )
        self.store.append_journal_event(prepared)
        failed = journal_event(
            operation_id=failed_operation,
            sequence_no=1,
            event_type="EFFECT_FAILED",
            previous_event_hash=prepared.event_hash,
        )
        self.store.append_journal_event(failed)

        observed = self.store.journal_events(operation)
        self.assertEqual(
            tuple(item.event_type for item in observed),
            event_types,
        )
        self.assertEqual(observed[-1].previous_event_hash, observed[-2].event_hash)

        bad = journal_event(
            operation_id=operation,
            sequence_no=5,
            event_type="EFFECT_FAILED",
            previous_event_hash=previous,
        )
        with self.assertRaisesRegex(
            JournalHold,
            "HOLD_JOURNAL_SEQUENCE_GAP",
        ):
            self.store.append_journal_event(bad)
        self.assertEqual(len(self.store.journal_events(operation)), 4)

        illegal = journal_event(
            operation_id="operation:illegal-tail",
            sequence_no=0,
            event_type="EFFECT_ACCEPTED",
            previous_event_hash=None,
        )
        with self.assertRaisesRegex(
            JournalHold,
            "HOLD_EFFECT_JOURNAL_TRANSITION_CONFLICT",
        ):
            self.store.append_journal_event(illegal)

    def test_atomic_commit_cas_and_exact_idempotency_replay(self) -> None:
        self.store.register_resource(
            resource_id="resource:one",
            workspace_id="workspace:msi",
            resource_kind="FILE",
            version_ref="version:base",
            generation=0,
            created_at=NOW,
        )
        self.assertEqual(
            self.store.claim_effect_operation(
                idempotency_key="idempotency:one",
                operation_id="operation:commit",
                effect_contract_ref=EFFECT_REF,
                attempt_no=1,
                claimed_at=NOW,
            ),
            "CLAIMED",
        )
        previous = None
        for sequence, event_type in enumerate(
            (
                "EFFECT_PREPARED",
                "EFFECT_STARTED",
                "EFFECT_OBSERVED",
                "EFFECT_ACCEPTED",
            )
        ):
            event = journal_event(
                operation_id="operation:commit",
                sequence_no=sequence,
                event_type=event_type,
                previous_event_hash=previous,
            )
            self.store.append_journal_event(event)
            previous = event.event_hash

        write = self._commit_write(
            operation_id="operation:commit",
            resource_id="resource:one",
            idempotency_key="idempotency:one",
            expected_generation=0,
            expected_version_ref="version:base",
            sequence_no=4,
            previous_event_hash=previous,
        )
        first = self.store.commit_state(write)
        self.assertFalse(first.replayed)
        self.assertEqual(first.pointer.generation, 1)
        self.assertEqual(first.pointer.version_ref, "version:result")
        self.assertTrue(
            self.store.transition_exists(write.transition.transition_ref)
        )
        self.assertTrue(self.store.receipt_exists(write.receipt.receipt_ref))

        replay = self.store.commit_state(write)
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.receipt.receipt_ref, first.receipt.receipt_ref)
        self.assertEqual(
            self.store.load_current_pointer_fresh(
                "resource:one"
            ).generation,
            1,
        )
        self.assertEqual(
            self.store.connection.execute(
                "SELECT COUNT(*) FROM transitions"
            ).fetchone()[0],
            1,
        )
        self.assertEqual(
            self.store.connection.execute(
                "SELECT COUNT(*) FROM receipts"
            ).fetchone()[0],
            1,
        )
        self.assertEqual(
            tuple(
                item.event_type
                for item in self.store.journal_events("operation:commit")
            ),
            (
                "EFFECT_PREPARED",
                "EFFECT_STARTED",
                "EFFECT_OBSERVED",
                "EFFECT_ACCEPTED",
                "STATE_COMMITTED",
            ),
        )
        lookup = self.store.get_committed_by_idempotency(
            "idempotency:one"
        )
        self.assertIsNotNone(lookup)
        self.assertEqual(lookup.result_version_ref, "version:result")

    def test_generation_or_version_cas_mismatch_rolls_back_bundle(self) -> None:
        self.store.register_resource(
            resource_id="resource:cas",
            workspace_id="workspace:msi",
            resource_kind="FILE",
            version_ref="version:base",
            generation=0,
            created_at=NOW,
        )

        cases = (
            ("operation:bad-generation", 1, "version:base"),
            ("operation:bad-version", 0, "version:wrong"),
        )
        for operation, generation, version in cases:
            with self.subTest(operation=operation):
                self.assertEqual(
                    self.store.claim_effect_operation(
                        idempotency_key=f"idempotency:{operation}",
                        operation_id=operation,
                        effect_contract_ref=EFFECT_REF,
                        attempt_no=1,
                        claimed_at=NOW,
                    ),
                    "CLAIMED",
                )
                previous = self._append_accepted_history(operation)
                write = self._commit_write(
                    operation_id=operation,
                    resource_id="resource:cas",
                    idempotency_key=f"idempotency:{operation}",
                    expected_generation=generation,
                    expected_version_ref=version,
                    sequence_no=4,
                    previous_event_hash=previous,
                )
                with self.assertRaisesRegex(
                    CASConflict,
                    "STATE_DRIFT_RECOMPUTE_NEW_OPERATION",
                ):
                    self.store.commit_state(write)
                self.assertFalse(
                    self.store.transition_exists(
                        write.transition.transition_ref
                    )
                )
                self.assertFalse(
                    self.store.receipt_exists(write.receipt.receipt_ref)
                )
                self.assertEqual(
                    tuple(
                        event.event_type
                        for event in self.store.journal_events(operation)
                    ),
                    (
                        "EFFECT_PREPARED",
                        "EFFECT_STARTED",
                        "EFFECT_OBSERVED",
                        "EFFECT_ACCEPTED",
                    ),
                )

        pointer = self.store.load_current_pointer_fresh("resource:cas")
        self.assertEqual(pointer.generation, 0)
        self.assertEqual(pointer.version_ref, "version:base")

    def test_commit_without_exact_claim_holds_before_bundle_write(self) -> None:
        self.store.register_resource(
            resource_id="resource:unclaimed",
            workspace_id="workspace:msi",
            resource_kind="FILE",
            version_ref="version:base",
            generation=0,
            created_at=NOW,
        )
        previous = self._append_accepted_history("operation:unclaimed")
        write = self._commit_write(
            operation_id="operation:unclaimed",
            resource_id="resource:unclaimed",
            idempotency_key="idempotency:unclaimed",
            expected_generation=0,
            expected_version_ref="version:base",
            sequence_no=4,
            previous_event_hash=previous,
        )
        with self.assertRaisesRegex(
            StoreHold,
            "HOLD_EFFECT_OPERATION_CLAIM_MISSING",
        ):
            self.store.commit_state(write)
        self.assertFalse(
            self.store.transition_exists(write.transition.transition_ref)
        )
        self.assertFalse(self.store.receipt_exists(write.receipt.receipt_ref))

    def _append_accepted_history(self, operation_id: str) -> str:
        previous = None
        for sequence, event_type in enumerate(
            (
                "EFFECT_PREPARED",
                "EFFECT_STARTED",
                "EFFECT_OBSERVED",
                "EFFECT_ACCEPTED",
            )
        ):
            event = journal_event(
                operation_id=operation_id,
                sequence_no=sequence,
                event_type=event_type,
                previous_event_hash=previous,
            )
            self.store.append_journal_event(event)
            previous = event.event_hash
        return previous

    @staticmethod
    def _commit_write(
        *,
        operation_id: str,
        resource_id: str,
        idempotency_key: str,
        expected_generation: int,
        expected_version_ref: str | None,
        sequence_no: int,
        previous_event_hash: str | None,
    ) -> StateCommitWrite:
        receipt_ref, receipt_hash = sha_ref(f"receipt:{operation_id}")
        transition_body = {
            "schema_id": "W7TP_STATE_TRANSITION_V1",
            "operation_id": operation_id,
            "resource_id": resource_id,
            "from_version_ref": expected_version_ref,
            "to_version_ref": "version:result",
            "expected_generation": expected_generation,
            "receipt_ref": receipt_ref,
            "created_at": NOW,
        }
        transition_hash = canonical_hash(transition_body)
        transition_ref = f"sha256:{transition_hash}"
        transition = TransitionWrite(
            transition_ref=transition_ref,
            transition_hash=transition_hash,
            operation_id=operation_id,
            resource_id=resource_id,
            from_version_ref=expected_version_ref,
            to_version_ref="version:result",
            expected_generation=expected_generation,
            receipt_ref=receipt_ref,
            created_at=NOW,
        )
        receipt = ReceiptWrite(
            receipt_ref=receipt_ref,
            receipt_hash=receipt_hash,
            operation_id=operation_id,
            idempotency_key=idempotency_key,
            transition_ref=transition_ref,
            effect_contract_ref=EFFECT_REF,
            effect_contract_hash=EFFECT_HASH,
            result_version_ref="version:result",
            payload_ref=receipt_ref,
            created_at=NOW,
        )
        journal = journal_event(
            operation_id=operation_id,
            sequence_no=sequence_no,
            event_type="STATE_COMMITTED",
            previous_event_hash=previous_event_hash,
        )
        return StateCommitWrite(
            transition=transition,
            receipt=receipt,
            journal=journal,
            pointer_updated_at=NOW,
        )


if __name__ == "__main__":
    unittest.main()
