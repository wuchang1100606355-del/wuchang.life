"""Immutable SHA-256 object packets and deterministic manifest validation.

This module is candidate infrastructure only.  It establishes byte identity and
durable local publication; it does not establish provenance, authority, or
runtime activation.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import stat
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import BinaryIO, Iterable, Protocol, Sequence

from .canonical import (
    canonical_json_bytes,
    canonical_json_loads,
    sha256_hex,
    sha256_ref,
    validate_sha256_ref,
)


CHUNK_BYTES = 4 * 1024 * 1024


class ObjectStoreError(ValueError):
    """Base error carrying a stable fail-closed reason code."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class ObjectStoreHold(ObjectStoreError):
    """The requested operation cannot be proven safe or complete."""


class ObjectStoreConflict(ObjectStoreError):
    """Observed bytes conflict with their claimed immutable identity."""


class ManifestValidationError(ObjectStoreConflict):
    """A manifest is structurally or byte-wise inconsistent."""


@dataclass(frozen=True, slots=True)
class StoredChunk:
    object_id: str
    chunk_ordinal: int
    byte_offset: int
    byte_length: int


@dataclass(frozen=True, slots=True)
class ChunkedFile:
    size_bytes: int
    file_sha256: str
    chunks: tuple[StoredChunk, ...]


@dataclass(frozen=True, slots=True)
class SealedManifestEntry:
    entry_ordinal: int
    logical_path: str
    entry_kind: str
    mode: int
    size_bytes: int
    file_sha256: str | None
    chunks: tuple[StoredChunk, ...] = ()


@dataclass(frozen=True, slots=True)
class SealedManifest:
    manifest_ref: str
    manifest_hash: str
    entries: tuple[SealedManifestEntry, ...]

    def unique_chunks_in_order(self) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for entry in self.entries:
            for chunk in entry.chunks:
                if chunk.object_id not in seen:
                    seen.add(chunk.object_id)
                    result.append(chunk.object_id)
        return tuple(result)


@dataclass(frozen=True, slots=True)
class ReconstructedManifestEntry:
    entry_ordinal: int
    logical_path: str
    entry_kind: str
    mode: int
    size_bytes: int
    file_sha256: str | None
    data: bytes | None


class ManifestChunkLike(Protocol):
    object_id: str
    chunk_ordinal: int
    byte_offset: int
    byte_length: int


class ManifestEntryLike(Protocol):
    entry_ordinal: int
    logical_path: str
    entry_kind: object
    mode: int
    size_bytes: int
    file_sha256: str | None
    chunks: Sequence[ManifestChunkLike]


def _ensure_plain_directory(path: Path) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        path.mkdir(parents=True, exist_ok=False)
        metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise ObjectStoreHold("HOLD_OBJECT_STORE_DIRECTORY_UNSAFE")


def _directory_flags() -> int:
    required = ("O_DIRECTORY", "O_NOFOLLOW")
    if (
        any(not hasattr(os, name) for name in required)
        or os.open not in os.supports_dir_fd
        or os.mkdir not in os.supports_dir_fd
        or os.link not in os.supports_dir_fd
    ):
        raise ObjectStoreHold("HOLD_SECURE_OBJECT_STORE_UNAVAILABLE")
    return (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )


def _open_or_create_directory_at(parent_fd: int, name: str) -> int:
    flags = _directory_flags()
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
    except FileExistsError:
        pass
    except OSError as exc:
        raise ObjectStoreConflict("OBJECT_STORE_DIRECTORY_CONFLICT") from exc
    else:
        os.fsync(parent_fd)
    try:
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except OSError as exc:
        raise ObjectStoreConflict("OBJECT_STORE_DIRECTORY_CONFLICT") from exc
    if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise ObjectStoreConflict("OBJECT_STORE_DIRECTORY_CONFLICT")
    return descriptor


def _kind_value(value: object) -> object:
    return getattr(value, "value", value)


def validate_logical_path(value: str) -> str:
    """Require an exact NFC, portable, non-empty relative manifest path."""

    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\\" in value
        or "\x00" in value
        or unicodedata.normalize("NFC", value) != value
    ):
        raise ManifestValidationError("MANIFEST_LOGICAL_PATH_INVALID")
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    raw_parts = value.split("/")
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or bool(windows.drive)
        or any(part in {"", ".", ".."} for part in raw_parts)
        or posix.as_posix() != value
    ):
        raise ManifestValidationError("MANIFEST_LOGICAL_PATH_UNCONFINED")
    return value


class ObjectPacketStore:
    """A node-local immutable object store using no-overwrite hard links."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        requested_root = Path(root)
        _ensure_plain_directory(requested_root)
        self.root = requested_root.resolve(strict=True)
        self.objects_root = self.root / "objects" / "sha256"
        self.temporary_root = self.root / "tmp"
        flags = _directory_flags()
        try:
            self._root_fd = os.open(self.root, flags)
        except OSError as exc:
            raise ObjectStoreHold("HOLD_OBJECT_STORE_ROOT_UNSAFE") from exc
        opened: list[int] = []
        try:
            objects_fd = _open_or_create_directory_at(
                self._root_fd, "objects"
            )
            opened.append(objects_fd)
            self._objects_fd = _open_or_create_directory_at(
                objects_fd, "sha256"
            )
            opened.append(self._objects_fd)
            self._temporary_fd = _open_or_create_directory_at(
                self._root_fd, "tmp"
            )
            opened.append(self._temporary_fd)
        except BaseException:
            for descriptor in reversed(opened):
                os.close(descriptor)
            os.close(self._root_fd)
            raise
        os.close(objects_fd)

    @staticmethod
    def _digest_from_ref(object_ref: str) -> str:
        try:
            validate_sha256_ref(object_ref)
        except ValueError as error:
            raise ObjectStoreHold("HOLD_INVALID_OBJECT_REF") from error
        return object_ref.removeprefix("sha256:")

    def _object_path(self, object_ref: str) -> Path:
        digest = self._digest_from_ref(object_ref)
        return self.objects_root / digest[:2] / digest[2:]

    def object_path(self, object_ref: str) -> Path:
        """Return a diagnostic path; runtime reads/writes remain fd-relative."""

        return self._object_path(object_ref)

    def _open_prefix_fd(self, digest: str, *, create: bool) -> int:
        prefix = digest[:2]
        if create:
            return _open_or_create_directory_at(self._objects_fd, prefix)
        try:
            return os.open(prefix, _directory_flags(), dir_fd=self._objects_fd)
        except FileNotFoundError:
            raise
        except OSError as exc:
            raise ObjectStoreConflict("OBJECT_STORE_DIRECTORY_CONFLICT") from exc

    @staticmethod
    def _verify_open_descriptor(
        descriptor: int,
        object_ref: str,
    ) -> None:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ObjectStoreConflict("OBJECT_PATH_NOT_REGULAR")
        digest = hashlib.sha256()
        while True:
            block = os.read(descriptor, CHUNK_BYTES)
            if not block:
                break
            digest.update(block)
        if f"sha256:{digest.hexdigest()}" != object_ref:
            raise ObjectStoreConflict("OBJECT_BYTES_HASH_CONFLICT")

    def _verify_existing(self, object_ref: str) -> None:
        digest = self._digest_from_ref(object_ref)
        prefix_fd = self._open_prefix_fd(digest, create=False)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(
            os, "O_CLOEXEC", 0
        )
        try:
            descriptor = os.open(digest[2:], flags, dir_fd=prefix_fd)
        except FileNotFoundError:
            os.close(prefix_fd)
            raise
        except OSError as error:
            os.close(prefix_fd)
            raise ObjectStoreConflict("OBJECT_PATH_NOT_REGULAR") from error
        try:
            self._verify_open_descriptor(descriptor, object_ref)
        finally:
            os.close(descriptor)
            os.close(prefix_fd)

    def _create_temporary(self) -> tuple[int, str]:
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_NOFOLLOW
            | getattr(os, "O_CLOEXEC", 0)
        )
        for _ in range(64):
            name = f".object-{secrets.token_hex(16)}"
            try:
                return (
                    os.open(name, flags, 0o600, dir_fd=self._temporary_fd),
                    name,
                )
            except FileExistsError:
                continue
            except OSError as exc:
                raise ObjectStoreHold("HOLD_OBJECT_TEMP_CREATE_FAILED") from exc
        raise ObjectStoreHold("HOLD_OBJECT_TEMP_NAME_EXHAUSTED")

    def _publish_blocks(
        self,
        blocks: Iterable[bytes],
        *,
        expected_ref: str | None = None,
    ) -> str:
        if expected_ref is not None:
            self._digest_from_ref(expected_ref)
        descriptor, temporary_name = self._create_temporary()
        digest = hashlib.sha256()
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                for block in blocks:
                    if not isinstance(block, bytes):
                        raise ObjectStoreHold("HOLD_OBJECT_BLOCK_NOT_BYTES")
                    if not block:
                        continue
                    stream.write(block)
                    digest.update(block)
                stream.flush()
                os.fsync(stream.fileno())

            actual_ref = f"sha256:{digest.hexdigest()}"
            if expected_ref is not None and actual_ref != expected_ref:
                raise ObjectStoreConflict("OBJECT_PACKET_HASH_CONFLICT")

            digest_text = actual_ref.removeprefix("sha256:")
            prefix_fd = self._open_prefix_fd(digest_text, create=True)
            try:
                try:
                    os.link(
                        temporary_name,
                        digest_text[2:],
                        src_dir_fd=self._temporary_fd,
                        dst_dir_fd=prefix_fd,
                        follow_symlinks=False,
                    )
                except FileExistsError:
                    self._verify_existing(actual_ref)
                else:
                    os.chmod(
                        digest_text[2:],
                        0o444,
                        dir_fd=prefix_fd,
                        follow_symlinks=False,
                    )
                    os.fsync(prefix_fd)
            finally:
                os.close(prefix_fd)
            return actual_ref
        finally:
            try:
                os.unlink(temporary_name, dir_fd=self._temporary_fd)
                os.fsync(self._temporary_fd)
            except FileNotFoundError:
                pass

    def put_bytes(self, data: bytes) -> str:
        if not isinstance(data, bytes):
            raise ObjectStoreHold("HOLD_OBJECT_DATA_NOT_BYTES")
        return self._publish_blocks(
            data[offset : offset + CHUNK_BYTES]
            for offset in range(0, len(data), CHUNK_BYTES)
        )

    def put_exact(self, object_ref: str, data: bytes) -> str:
        if not isinstance(data, bytes):
            raise ObjectStoreHold("HOLD_OBJECT_DATA_NOT_BYTES")
        return self._publish_blocks(
            (
                data[offset : offset + CHUNK_BYTES]
                for offset in range(0, len(data), CHUNK_BYTES)
            ),
            expected_ref=object_ref,
        )

    def put_stream(self, stream: BinaryIO) -> str:
        def blocks() -> Iterable[bytes]:
            while True:
                block = stream.read(CHUNK_BYTES)
                if block == b"":
                    return
                if not isinstance(block, bytes):
                    raise ObjectStoreHold("HOLD_OBJECT_STREAM_NOT_BINARY")
                yield block

        return self._publish_blocks(blocks())

    def put_file(self, source: str | os.PathLike[str]) -> str:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(
            os, "O_CLOEXEC", 0
        )
        try:
            descriptor = os.open(Path(source), flags)
        except OSError as error:
            raise ObjectStoreHold("HOLD_OBJECT_SOURCE_OPEN_FAILED") from error
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ObjectStoreHold("HOLD_OBJECT_SOURCE_NOT_REGULAR")
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                return self.put_stream(stream)
        finally:
            os.close(descriptor)

    def put_file_chunks(
        self, source: str | os.PathLike[str]
    ) -> ChunkedFile:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(
            os, "O_CLOEXEC", 0
        )
        try:
            descriptor = os.open(Path(source), flags)
        except OSError as error:
            raise ObjectStoreHold("HOLD_OBJECT_SOURCE_OPEN_FAILED") from error
        file_digest = hashlib.sha256()
        chunks: list[StoredChunk] = []
        offset = 0
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ObjectStoreHold("HOLD_OBJECT_SOURCE_NOT_REGULAR")
            ordinal = 0
            while True:
                block = os.read(descriptor, CHUNK_BYTES)
                if not block:
                    break
                file_digest.update(block)
                object_id = self.put_bytes(block)
                chunks.append(
                    StoredChunk(
                        object_id=object_id,
                        chunk_ordinal=ordinal,
                        byte_offset=offset,
                        byte_length=len(block),
                    )
                )
                offset += len(block)
                ordinal += 1
        finally:
            os.close(descriptor)
        return ChunkedFile(offset, file_digest.hexdigest(), tuple(chunks))

    def put_chunks(self, data: bytes) -> ChunkedFile:
        if not isinstance(data, bytes):
            raise ObjectStoreHold("HOLD_OBJECT_DATA_NOT_BYTES")
        chunks: list[StoredChunk] = []
        for ordinal, offset in enumerate(range(0, len(data), CHUNK_BYTES)):
            block = data[offset : offset + CHUNK_BYTES]
            chunks.append(
                StoredChunk(
                    object_id=self.put_bytes(block),
                    chunk_ordinal=ordinal,
                    byte_offset=offset,
                    byte_length=len(block),
                )
            )
        return ChunkedFile(len(data), hashlib.sha256(data).hexdigest(), tuple(chunks))

    def has(self, object_ref: str) -> bool:
        try:
            self._verify_existing(object_ref)
        except FileNotFoundError:
            return False
        return True

    def get_bytes(self, object_ref: str) -> bytes:
        digest_text = self._digest_from_ref(object_ref)
        try:
            prefix_fd = self._open_prefix_fd(digest_text, create=False)
        except FileNotFoundError as error:
            raise ObjectStoreHold("HOLD_OBJECT_NOT_FOUND") from error
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(
            os, "O_CLOEXEC", 0
        )
        try:
            descriptor = os.open(
                digest_text[2:], flags, dir_fd=prefix_fd
            )
        except FileNotFoundError as error:
            os.close(prefix_fd)
            raise ObjectStoreHold("HOLD_OBJECT_NOT_FOUND") from error
        except OSError as error:
            os.close(prefix_fd)
            raise ObjectStoreConflict("OBJECT_PATH_NOT_REGULAR") from error
        result = bytearray()
        digest = hashlib.sha256()
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ObjectStoreConflict("OBJECT_PATH_NOT_REGULAR")
            while True:
                block = os.read(descriptor, CHUNK_BYTES)
                if not block:
                    break
                result.extend(block)
                digest.update(block)
        finally:
            os.close(descriptor)
            os.close(prefix_fd)
        if f"sha256:{digest.hexdigest()}" != object_ref:
            raise ObjectStoreConflict("OBJECT_BYTES_HASH_CONFLICT")
        return bytes(result)

    def get_exact(self, object_ref: str) -> bytes:
        return self.get_bytes(object_ref)

    def get_verified(self, object_ref: str) -> bytes:
        return self.get_bytes(object_ref)

    def export_packet(self, object_ref: str) -> bytes:
        """Export the exact object bytes; no authority metadata is invented."""

        return self.get_bytes(object_ref)

    def install_packet(self, packet: bytes) -> str:
        """Hash, verify, and immutably install exact packet bytes."""

        return self.put_bytes(packet)

    def close(self) -> None:
        for name in ("_temporary_fd", "_objects_fd", "_root_fd"):
            descriptor = getattr(self, name, None)
            if descriptor is not None:
                os.close(descriptor)
                setattr(self, name, None)

    def __enter__(self) -> "ObjectPacketStore":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        del exc_type, exc, traceback
        self.close()


def validate_manifest_entries(
    entries: Sequence[ManifestEntryLike],
    objects: ObjectPacketStore,
) -> None:
    """Validate complete ordered entry/chunk structure and every file hash."""

    ordinals = [entry.entry_ordinal for entry in entries]
    if ordinals != list(range(len(entries))):
        raise ManifestValidationError("MANIFEST_ENTRY_ORDINAL_GAP")

    paths: set[str] = set()
    for entry in entries:
        logical_path = validate_logical_path(entry.logical_path)
        if logical_path in paths:
            raise ManifestValidationError("MANIFEST_LOGICAL_PATH_DUPLICATE")
        paths.add(logical_path)

        if (
            isinstance(entry.mode, bool)
            or not isinstance(entry.mode, int)
            or not 0 <= entry.mode <= 65535
        ):
            raise ManifestValidationError("MANIFEST_MODE_INVALID")
        if (
            isinstance(entry.size_bytes, bool)
            or not isinstance(entry.size_bytes, int)
            or entry.size_bytes < 0
        ):
            raise ManifestValidationError("MANIFEST_SIZE_INVALID")

        entry_kind = _kind_value(entry.entry_kind)
        chunks = tuple(entry.chunks)
        if entry_kind == "DIRECTORY":
            if entry.size_bytes != 0 or entry.file_sha256 is not None or chunks:
                raise ManifestValidationError("DIRECTORY_CONTENT_CONFLICT")
            continue
        if entry_kind != "FILE":
            raise ManifestValidationError("MANIFEST_ENTRY_KIND_INVALID")
        if (
            not isinstance(entry.file_sha256, str)
            or len(entry.file_sha256) != 64
            or entry.file_sha256 != entry.file_sha256.lower()
            or any(character not in "0123456789abcdef" for character in entry.file_sha256)
        ):
            raise ManifestValidationError("FILE_HASH_INVALID")

        chunk_ordinals = [chunk.chunk_ordinal for chunk in chunks]
        if chunk_ordinals != list(range(len(chunks))):
            raise ManifestValidationError("CHUNK_ORDINAL_GAP")

        offset = 0
        digest = hashlib.sha256()
        for index, chunk in enumerate(chunks):
            if chunk.byte_offset != offset:
                raise ManifestValidationError("CHUNK_OFFSET_GAP")
            if (
                isinstance(chunk.byte_length, bool)
                or not isinstance(chunk.byte_length, int)
                or not 0 < chunk.byte_length <= CHUNK_BYTES
            ):
                raise ManifestValidationError("CHUNK_SIZE_CONFLICT")
            if index < len(chunks) - 1 and chunk.byte_length != CHUNK_BYTES:
                raise ManifestValidationError("NONFINAL_CHUNK_SIZE_CONFLICT")
            raw = objects.get_bytes(chunk.object_id)
            if len(raw) != chunk.byte_length:
                raise ManifestValidationError("CHUNK_SIZE_CONFLICT")
            digest.update(raw)
            offset += chunk.byte_length

        if offset != entry.size_bytes:
            raise ManifestValidationError("FILE_SIZE_CONFLICT")
        if digest.hexdigest() != entry.file_sha256:
            raise ManifestValidationError("FILE_HASH_CONFLICT")


def _manifest_body(entries: Sequence[ManifestEntryLike]) -> dict[str, object]:
    return {
        "schema_id": "W7TP_IMMUTABLE_MANIFEST_V1",
        "entries": [
            {
                "entry_ordinal": entry.entry_ordinal,
                "logical_path": entry.logical_path,
                "entry_kind": _kind_value(entry.entry_kind),
                "mode": entry.mode,
                "size_bytes": entry.size_bytes,
                "file_sha256": entry.file_sha256,
                "chunks": [
                    {
                        "object_id": chunk.object_id,
                        "chunk_ordinal": chunk.chunk_ordinal,
                        "byte_offset": chunk.byte_offset,
                        "byte_length": chunk.byte_length,
                    }
                    for chunk in entry.chunks
                ],
            }
            for entry in entries
        ],
    }


def seal_manifest(
    entries: Sequence[ManifestEntryLike],
    objects: ObjectPacketStore,
) -> SealedManifest:
    """Validate and immutably seal the complete ordered manifest body."""

    normalized = tuple(
        SealedManifestEntry(
            entry_ordinal=entry.entry_ordinal,
            logical_path=entry.logical_path,
            entry_kind=str(_kind_value(entry.entry_kind)),
            mode=entry.mode,
            size_bytes=entry.size_bytes,
            file_sha256=entry.file_sha256,
            chunks=tuple(
                StoredChunk(
                    object_id=chunk.object_id,
                    chunk_ordinal=chunk.chunk_ordinal,
                    byte_offset=chunk.byte_offset,
                    byte_length=chunk.byte_length,
                )
                for chunk in entry.chunks
            ),
        )
        for entry in entries
    )
    validate_manifest_entries(normalized, objects)
    raw = canonical_json_bytes(_manifest_body(normalized))
    manifest_ref = objects.put_bytes(raw)
    return SealedManifest(
        manifest_ref=manifest_ref,
        manifest_hash=sha256_hex(raw),
        entries=normalized,
    )


def load_sealed_manifest(
    manifest_ref: str,
    objects: ObjectPacketStore,
) -> SealedManifest:
    """Load exact canonical manifest bytes and revalidate full closure."""

    validate_sha256_ref(manifest_ref)
    raw = objects.get_bytes(manifest_ref)
    if sha256_ref(raw) != manifest_ref:
        raise ManifestValidationError("MANIFEST_REF_HASH_CONFLICT")
    packet = canonical_json_loads(raw)
    if (
        not isinstance(packet, dict)
        or set(packet) != {"schema_id", "entries"}
        or packet.get("schema_id") != "W7TP_IMMUTABLE_MANIFEST_V1"
        or not isinstance(packet.get("entries"), list)
    ):
        raise ManifestValidationError("MANIFEST_PACKET_SCHEMA_CONFLICT")
    try:
        entries = tuple(
            SealedManifestEntry(
                entry_ordinal=item["entry_ordinal"],
                logical_path=item["logical_path"],
                entry_kind=item["entry_kind"],
                mode=item["mode"],
                size_bytes=item["size_bytes"],
                file_sha256=item["file_sha256"],
                chunks=tuple(StoredChunk(**chunk) for chunk in item["chunks"]),
            )
            for item in packet["entries"]
        )
    except (KeyError, TypeError) as exc:
        raise ManifestValidationError("MANIFEST_PACKET_SHAPE_CONFLICT") from exc
    if canonical_json_bytes(_manifest_body(entries)) != raw:
        raise ManifestValidationError("MANIFEST_PACKET_CANONICAL_CONFLICT")
    validate_manifest_entries(entries, objects)
    return SealedManifest(
        manifest_ref=manifest_ref,
        manifest_hash=sha256_hex(raw),
        entries=entries,
    )


def reconstruct_manifest(
    manifest: SealedManifest,
    objects: ObjectPacketStore,
) -> tuple[ReconstructedManifestEntry, ...]:
    """Reconstruct ordered tree values in memory without guessing a path."""

    if manifest.manifest_ref != f"sha256:{manifest.manifest_hash}":
        raise ManifestValidationError("MANIFEST_IDENTITY_CONFLICT")
    validate_manifest_entries(manifest.entries, objects)
    reconstructed: list[ReconstructedManifestEntry] = []
    for entry in manifest.entries:
        data = None
        if entry.entry_kind == "FILE":
            data = b"".join(
                objects.get_bytes(chunk.object_id)
                for chunk in entry.chunks
            )
            if len(data) != entry.size_bytes:
                raise ManifestValidationError("FILE_SIZE_CONFLICT")
            if hashlib.sha256(data).hexdigest() != entry.file_sha256:
                raise ManifestValidationError("FILE_HASH_CONFLICT")
        reconstructed.append(
            ReconstructedManifestEntry(
                entry_ordinal=entry.entry_ordinal,
                logical_path=entry.logical_path,
                entry_kind=entry.entry_kind,
                mode=entry.mode,
                size_bytes=entry.size_bytes,
                file_sha256=entry.file_sha256,
                data=data,
            )
        )
    return tuple(reconstructed)
