from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from w7tp_runtime.state_field.models import EntryKind, ManifestChunk, ManifestEntry
from w7tp_runtime.state_field.mrs_resolver import (
    DependencyDecision,
    MappingDependencyCatalog,
    Resolution,
    close_mrs,
)
from w7tp_runtime.state_field.object_packet_store import (
    CHUNK_BYTES,
    ManifestValidationError,
    ObjectPacketStore,
    ObjectStoreConflict,
    load_sealed_manifest,
    reconstruct_manifest,
    seal_manifest,
    validate_manifest_entries,
)
from w7tp_runtime.state_field.workspace import (
    WorkspaceConfinementError,
    WorkspaceHold,
    hash_file_read_only,
    open_new_file_beneath,
    stat_read_only,
)


class ObjectPacketStoreTests(unittest.TestCase):
    def test_exact_round_trip_packet_install_and_idempotent_publication(self) -> None:
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = ObjectPacketStore(first_dir)
            second = ObjectPacketStore(second_dir)
            data = b"state-field-object\x00bytes"

            object_ref = first.put_bytes(data)
            self.assertEqual(object_ref, f"sha256:{hashlib.sha256(data).hexdigest()}")
            self.assertEqual(first.put_bytes(data), object_ref)
            self.assertTrue(first.has(object_ref))
            self.assertEqual(first.get_bytes(object_ref), data)

            packet = first.export_packet(object_ref)
            installed_ref = second.install_packet(packet)
            self.assertEqual(installed_ref, object_ref)
            self.assertEqual(second.get_exact(installed_ref), data)

    def test_existing_conflicting_object_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ObjectPacketStore(directory)
            intended = b"intended immutable bytes"
            object_ref = f"sha256:{hashlib.sha256(intended).hexdigest()}"
            target = store.object_path(object_ref)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"conflicting pre-existing bytes")

            with self.assertRaisesRegex(
                ObjectStoreConflict,
                "OBJECT_BYTES_HASH_CONFLICT",
            ):
                store.put_exact(object_ref, intended)
            self.assertEqual(target.read_bytes(), b"conflicting pre-existing bytes")

    def test_nested_object_store_symlink_is_rejected_without_escape(self) -> None:
        with tempfile.TemporaryDirectory() as root_dir, tempfile.TemporaryDirectory() as outside_dir:
            root = Path(root_dir)
            outside = Path(outside_dir)
            (root / "objects").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(
                ObjectStoreConflict,
                "OBJECT_STORE_DIRECTORY_CONFLICT",
            ):
                ObjectPacketStore(root)
            self.assertEqual(tuple(outside.iterdir()), ())

    def test_fixed_four_mib_chunks_and_manifest_validate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ObjectPacketStore(directory)
            data = b"A" * CHUNK_BYTES + b"tail"
            chunked = store.put_chunks(data)
            self.assertEqual(
                [chunk.byte_length for chunk in chunked.chunks],
                [CHUNK_BYTES, 4],
            )
            entries = (
                ManifestEntry(
                    entry_ordinal=0,
                    logical_path="payload",
                    entry_kind=EntryKind.DIRECTORY,
                    mode=0o755,
                    size_bytes=0,
                    file_sha256=None,
                ),
                ManifestEntry(
                    entry_ordinal=1,
                    logical_path="payload/data.bin",
                    entry_kind=EntryKind.FILE,
                    mode=0o640,
                    size_bytes=chunked.size_bytes,
                    file_sha256=chunked.file_sha256,
                    chunks=tuple(
                        ManifestChunk(
                            object_id=chunk.object_id,
                            chunk_ordinal=chunk.chunk_ordinal,
                            byte_offset=chunk.byte_offset,
                            byte_length=chunk.byte_length,
                        )
                        for chunk in chunked.chunks
                    ),
                ),
            )
            validate_manifest_entries(entries, store)
            sealed = seal_manifest(entries, store)
            loaded = load_sealed_manifest(sealed.manifest_ref, store)
            self.assertEqual(loaded, sealed)
            self.assertEqual(
                loaded.unique_chunks_in_order(),
                tuple(chunk.object_id for chunk in chunked.chunks),
            )
            rebuilt = reconstruct_manifest(loaded, store)
            self.assertEqual(
                tuple(
                    (
                        item.logical_path,
                        item.entry_kind,
                        item.mode,
                        item.size_bytes,
                        item.file_sha256,
                        item.data,
                    )
                    for item in rebuilt
                ),
                (
                    ("payload", "DIRECTORY", 0o755, 0, None, None),
                    (
                        "payload/data.bin",
                        "FILE",
                        0o640,
                        len(data),
                        hashlib.sha256(data).hexdigest(),
                        data,
                    ),
                ),
            )

    def test_manifest_rejects_ordinal_gap_hash_conflict_and_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ObjectPacketStore(directory)
            chunk = store.put_chunks(b"verified")
            correct_chunk = chunk.chunks[0]

            gap = ManifestEntry(
                entry_ordinal=0,
                logical_path="gap.bin",
                entry_kind=EntryKind.FILE,
                mode=0o600,
                size_bytes=chunk.size_bytes,
                file_sha256=chunk.file_sha256,
                chunks=(
                    ManifestChunk(
                        object_id=correct_chunk.object_id,
                        chunk_ordinal=1,
                        byte_offset=0,
                        byte_length=correct_chunk.byte_length,
                    ),
                ),
            )
            with self.assertRaisesRegex(
                ManifestValidationError,
                "CHUNK_ORDINAL_GAP",
            ):
                validate_manifest_entries((gap,), store)

            bad_hash = ManifestEntry(
                entry_ordinal=0,
                logical_path="hash.bin",
                entry_kind=EntryKind.FILE,
                mode=0o600,
                size_bytes=chunk.size_bytes,
                file_sha256="0" * 64,
                chunks=(
                    ManifestChunk(
                        object_id=correct_chunk.object_id,
                        chunk_ordinal=0,
                        byte_offset=0,
                        byte_length=correct_chunk.byte_length,
                    ),
                ),
            )
            with self.assertRaisesRegex(
                ManifestValidationError,
                "FILE_HASH_CONFLICT",
            ):
                validate_manifest_entries((bad_hash,), store)

            traversal = ManifestEntry(
                entry_ordinal=0,
                logical_path="../escape.bin",
                entry_kind=EntryKind.FILE,
                mode=0o600,
                size_bytes=0,
                file_sha256=hashlib.sha256(b"").hexdigest(),
            )
            with self.assertRaisesRegex(
                ManifestValidationError,
                "MANIFEST_LOGICAL_PATH_UNCONFINED",
            ):
                validate_manifest_entries((traversal,), store)


class WorkspaceTests(unittest.TestCase):
    def test_stat_separates_exists_from_entry_kind_and_hashes_by_fd(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "folder").mkdir()
            data = b"bounded observation"
            (root / "folder" / "data.bin").write_bytes(data)

            folder = stat_read_only(root, "workspace:test", "folder")
            self.assertTrue(folder.exists)
            self.assertEqual(folder.entry_kind, EntryKind.DIRECTORY)
            self.assertIsNone(folder.size_bytes)

            missing = stat_read_only(root, "workspace:test", "missing")
            self.assertFalse(missing.exists)
            self.assertEqual(missing.entry_kind, EntryKind.UNKNOWN)

            observed = hash_file_read_only(
                root,
                "workspace:test",
                "folder/data.bin",
                max_bytes=len(data),
            )
            self.assertEqual(observed.size_bytes, len(data))
            self.assertEqual(observed.sha256, hashlib.sha256(data).hexdigest())

    def test_traversal_and_escape_symlink_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as root_dir, tempfile.TemporaryDirectory() as outside_dir:
            root = Path(root_dir)
            outside = Path(outside_dir) / "outside.bin"
            outside.write_bytes(b"outside")

            with self.assertRaises(WorkspaceConfinementError):
                stat_read_only(root, "workspace:test", "../outside.bin")

            link = root / "escape"
            try:
                link.symlink_to(outside)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlink unavailable: {error}")

            with self.assertRaisesRegex(
                WorkspaceConfinementError,
                "WORKSPACE_PATH_ESCAPES_ROOT",
            ):
                stat_read_only(root, "workspace:test", "escape")
            with self.assertRaises(WorkspaceConfinementError):
                hash_file_read_only(root, "workspace:test", "escape")

    def test_open_new_file_uses_no_follow_and_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as root_dir, tempfile.TemporaryDirectory() as outside_dir:
            root = Path(root_dir)
            (root / "safe").mkdir()
            try:
                descriptor = open_new_file_beneath(root, "safe/new.bin")
            except WorkspaceHold as error:
                if error.reason_code == "HOLD_SECURE_WRITE_ADAPTER_UNAVAILABLE":
                    self.skipTest(error.reason_code)
                raise
            try:
                os.write(descriptor, b"created once")
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

            with self.assertRaisesRegex(
                WorkspaceHold,
                "HOLD_TARGET_ALREADY_EXISTS",
            ):
                open_new_file_beneath(root, "safe/new.bin")
            self.assertEqual((root / "safe" / "new.bin").read_bytes(), b"created once")

            outside = Path(outside_dir)
            linked_parent = root / "linked"
            try:
                linked_parent.symlink_to(outside, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlink unavailable: {error}")
            with self.assertRaises(WorkspaceConfinementError):
                open_new_file_beneath(root, "linked/escape.bin")
            self.assertFalse((outside / "escape.bin").exists())

    def test_missing_paths_hold_while_non_directory_parent_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "safe").mkdir()
            (root / "plain-file").write_bytes(b"not a directory")

            with self.assertRaisesRegex(
                WorkspaceHold,
                "HOLD_WORKSPACE_PARENT_UNAVAILABLE",
            ):
                hash_file_read_only(
                    root, "workspace:test", "missing-parent/data.bin"
                )
            with self.assertRaisesRegex(
                WorkspaceHold,
                "HOLD_WORKSPACE_FILE_UNAVAILABLE",
            ):
                hash_file_read_only(root, "workspace:test", "safe/missing.bin")
            with self.assertRaisesRegex(
                WorkspaceHold,
                "HOLD_WORKSPACE_PARENT_UNAVAILABLE",
            ):
                open_new_file_beneath(root, "missing-parent/new.bin")

            with self.assertRaisesRegex(
                WorkspaceConfinementError,
                "WORKSPACE_PARENT_SYMLINK_OR_NON_DIRECTORY",
            ):
                hash_file_read_only(
                    root, "workspace:test", "plain-file/child.bin"
                )


class MRSResolverTests(unittest.TestCase):
    def test_exact_resolution_domain_has_no_placeholder(self) -> None:
        self.assertEqual(
            {item.value for item in Resolution},
            {
                "PRESENT",
                "FETCH",
                "RECONSTRUCT",
                "GENERATE",
                "HOLD_UNKNOWN",
                "HOLD_UNAVAILABLE",
                "QUARANTINE_CONFLICT",
            },
        )
        self.assertNotIn("RESOLVE", {item.value for item in Resolution})

    def test_recursive_closure_is_dependency_first_and_deduplicated(self) -> None:
        catalog = MappingDependencyCatalog(
            {
                "req:a": DependencyDecision(
                    "req:a",
                    Resolution.RECONSTRUCT,
                    dependency_refs=("req:c", "req:b", "req:c"),
                    selected_artifact_ref="artifact:a",
                ),
                "req:b": DependencyDecision(
                    "req:b",
                    Resolution.FETCH,
                    dependency_refs=("req:c",),
                    selected_artifact_ref="artifact:shared",
                ),
                "req:c": DependencyDecision(
                    "req:c",
                    Resolution.PRESENT,
                    selected_artifact_ref="artifact:shared",
                ),
            },
            environment_ref="environment:test",
        )
        result = close_mrs(("req:a", "req:a"), catalog, "environment:test")

        self.assertEqual(result.state, "MRS_READY")
        self.assertIsNotNone(result.mrs)
        assert result.mrs is not None
        self.assertEqual(
            result.mrs.requirement_refs,
            ("req:c", "req:b", "req:a"),
        )
        self.assertEqual(
            result.mrs.artifact_refs,
            ("artifact:shared", "artifact:a"),
        )
        self.assertEqual(
            result.diagnostic_graph.edges,
            (("req:b", "req:a"), ("req:c", "req:a"), ("req:c", "req:b")),
        )

    def test_mapping_catalog_is_bound_to_exact_environment(self) -> None:
        catalog = MappingDependencyCatalog(
            {
                "req:a": DependencyDecision(
                    "req:a",
                    Resolution.PRESENT,
                    selected_artifact_ref="artifact:a",
                )
            },
            environment_ref="environment:sealed",
        )

        result = close_mrs(("req:a",), catalog, "environment:different")

        self.assertEqual(result.state, "QUARANTINED")
        self.assertEqual(result.reason, "HOLD_MRS_DEPENDENCY_CONFLICT")
        self.assertIsNone(result.mrs)

    def test_malformed_decisions_and_refs_quarantine_without_exception(
        self,
    ) -> None:
        malformed = {
            "decision": None,
            "dependency": DependencyDecision(
                "req:root",
                Resolution.PRESENT,
                dependency_refs=("req:valid", 7),
                selected_artifact_ref="artifact:root",
            ),
            "evidence": DependencyDecision(
                "req:root",
                Resolution.PRESENT,
                selected_artifact_ref="artifact:root",
                evidence_refs=(["not-hashable"],),
            ),
            "artifact": DependencyDecision(
                "req:root",
                Resolution.PRESENT,
                selected_artifact_ref=7,
            ),
            "scope": DependencyDecision(
                "req:root",
                Resolution.HOLD_UNAVAILABLE,
                sealed_resolution_scope_ref=object(),
            ),
        }
        for label, decision in malformed.items():
            with self.subTest(label=label):
                result = close_mrs(
                    ("req:root",),
                    MappingDependencyCatalog(
                        {"req:root": decision},
                        environment_ref="environment:test",
                    ),
                    "environment:test",
                )
                self.assertEqual(result.state, "QUARANTINED")
                self.assertEqual(
                    result.reason,
                    "HOLD_MRS_DEPENDENCY_CONFLICT",
                )
                self.assertIsNone(result.mrs)

    def test_unknown_unavailable_conflict_and_cycle_never_return_mrs(self) -> None:
        unknown = close_mrs(
            ("req:missing",),
            MappingDependencyCatalog(
                {},
                environment_ref="environment:test",
            ),
            "environment:test",
        )
        self.assertEqual(unknown.state, "HOLD")
        self.assertEqual(unknown.reason, "HOLD_MRS_DEPENDENCY_UNKNOWN")
        self.assertIsNone(unknown.mrs)

        unavailable_without_scope = close_mrs(
            ("req:u",),
            MappingDependencyCatalog(
                {
                    "req:u": DependencyDecision(
                        "req:u",
                        Resolution.HOLD_UNAVAILABLE,
                    )
                },
                environment_ref="environment:test",
            ),
            "environment:test",
        )
        self.assertEqual(
            unavailable_without_scope.reason,
            "HOLD_MRS_DEPENDENCY_UNKNOWN",
        )
        self.assertIsNone(unavailable_without_scope.mrs)

        conflict = close_mrs(
            ("req:no-artifact",),
            MappingDependencyCatalog(
                {
                    "req:no-artifact": DependencyDecision(
                        "req:no-artifact",
                        Resolution.GENERATE,
                    )
                },
                environment_ref="environment:test",
            ),
            "environment:test",
        )
        self.assertEqual(conflict.state, "QUARANTINED")
        self.assertEqual(conflict.reason, "HOLD_MRS_DEPENDENCY_CONFLICT")
        self.assertIsNone(conflict.mrs)

        cycle = close_mrs(
            ("req:a",),
            MappingDependencyCatalog(
                {
                    "req:a": DependencyDecision(
                        "req:a",
                        Resolution.PRESENT,
                        dependency_refs=("req:b",),
                        selected_artifact_ref="artifact:a",
                    ),
                    "req:b": DependencyDecision(
                        "req:b",
                        Resolution.PRESENT,
                        dependency_refs=("req:a",),
                        selected_artifact_ref="artifact:b",
                    ),
                },
                environment_ref="environment:test",
            ),
            "environment:test",
        )
        self.assertEqual(cycle.state, "QUARANTINED")
        self.assertEqual(cycle.reason, "HOLD_MRS_DEPENDENCY_CYCLE")
        self.assertIsNone(cycle.mrs)


if __name__ == "__main__":
    unittest.main()
