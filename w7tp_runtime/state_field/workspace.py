"""Bounded workspace observation and confined candidate file creation."""

from __future__ import annotations

import errno
import hashlib
import os
import stat
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from .models import EntryKind, WorkspaceObservation
from .object_packet_store import CHUNK_BYTES


DEFAULT_MAX_OBSERVATION_BYTES = 1024 * 1024 * 1024


class WorkspaceError(ValueError):
    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class WorkspaceHold(WorkspaceError):
    pass


class WorkspaceConfinementError(WorkspaceError):
    pass


@dataclass(frozen=True, slots=True)
class FileHashObservation:
    workspace_id: str
    logical_path: str
    size_bytes: int
    sha256: str
    observed_version_ref: str


def validated_relative_parts(logical_path: str) -> tuple[str, ...]:
    if (
        not isinstance(logical_path, str)
        or not logical_path
        or logical_path != logical_path.strip()
        or "\\" in logical_path
        or "\x00" in logical_path
        or unicodedata.normalize("NFC", logical_path) != logical_path
    ):
        raise WorkspaceConfinementError("WORKSPACE_PATH_INVALID")
    posix = PurePosixPath(logical_path)
    windows = PureWindowsPath(logical_path)
    raw_parts = logical_path.split("/")
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or bool(windows.drive)
        or any(part in {"", ".", ".."} for part in raw_parts)
        or posix.as_posix() != logical_path
    ):
        raise WorkspaceConfinementError("WORKSPACE_PATH_UNCONFINED")
    return tuple(raw_parts)


def _resolved_root(root: str | os.PathLike[str]) -> Path:
    candidate = Path(root)
    try:
        metadata = candidate.lstat()
    except OSError as error:
        raise WorkspaceHold("HOLD_WORKSPACE_ROOT_UNAVAILABLE") from error
    if candidate.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise WorkspaceConfinementError("WORKSPACE_ROOT_UNSAFE")
    return candidate.resolve(strict=True)


def confined_candidate(
    root: str | os.PathLike[str], logical_path: str
) -> Path:
    resolved_root = _resolved_root(root)
    return resolved_root.joinpath(*validated_relative_parts(logical_path))


def require_resolved_beneath(
    root: str | os.PathLike[str],
    candidate: str | os.PathLike[str],
    *,
    strict: bool,
) -> Path:
    resolved_root = _resolved_root(root)
    try:
        resolved = Path(candidate).resolve(strict=strict)
    except OSError as error:
        raise WorkspaceHold("HOLD_WORKSPACE_PATH_UNRESOLVED") from error
    if resolved == resolved_root or resolved_root not in resolved.parents:
        raise WorkspaceConfinementError("WORKSPACE_PATH_ESCAPES_ROOT")
    return resolved


def stat_read_only(
    root: str | os.PathLike[str],
    workspace_id: str,
    logical_path: str,
) -> WorkspaceObservation:
    candidate = confined_candidate(root, logical_path)
    try:
        metadata = candidate.lstat()
    except FileNotFoundError:
        require_resolved_beneath(root, candidate, strict=False)
        return WorkspaceObservation(
            workspace_id=workspace_id,
            logical_path=logical_path,
            exists=False,
            entry_kind=EntryKind.UNKNOWN,
            mode=None,
            size_bytes=None,
            observed_version_ref=None,
        )
    except OSError as error:
        raise WorkspaceHold("HOLD_WORKSPACE_LSTAT_FAILED") from error

    require_resolved_beneath(root, candidate, strict=True)
    if stat.S_ISREG(metadata.st_mode):
        entry_kind = EntryKind.FILE
        size_bytes: int | None = metadata.st_size
    elif stat.S_ISDIR(metadata.st_mode):
        entry_kind = EntryKind.DIRECTORY
        size_bytes = None
    else:
        entry_kind = EntryKind.OTHER
        size_bytes = None

    return WorkspaceObservation(
        workspace_id=workspace_id,
        logical_path=logical_path,
        exists=True,
        entry_kind=entry_kind,
        mode=stat.S_IMODE(metadata.st_mode),
        size_bytes=size_bytes,
        observed_version_ref=(
            f"local-stat:{metadata.st_dev}:{metadata.st_ino}:"
            f"{metadata.st_mtime_ns}"
        ),
    )


def _require_secure_dir_fd_support() -> None:
    required_flags = ("O_NOFOLLOW", "O_DIRECTORY")
    if (
        any(not hasattr(os, name) for name in required_flags)
        or os.open not in os.supports_dir_fd
    ):
        raise WorkspaceHold("HOLD_SECURE_WRITE_ADAPTER_UNAVAILABLE")


def _directory_flags() -> int:
    return (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )


def _open_parent_beneath(
    root: str | os.PathLike[str], parts: tuple[str, ...]
) -> int:
    _require_secure_dir_fd_support()
    try:
        current_fd = os.open(Path(root), _directory_flags())
    except OSError as error:
        if error.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise WorkspaceConfinementError("WORKSPACE_ROOT_UNSAFE") from error
        raise WorkspaceHold("HOLD_WORKSPACE_ROOT_UNAVAILABLE") from error
    try:
        for component in parts[:-1]:
            try:
                next_fd = os.open(
                    component,
                    _directory_flags(),
                    dir_fd=current_fd,
                )
            except OSError as error:
                if error.errno in {errno.ELOOP, errno.ENOTDIR}:
                    raise WorkspaceConfinementError(
                        "WORKSPACE_PARENT_SYMLINK_OR_NON_DIRECTORY"
                    ) from error
                raise WorkspaceHold(
                    "HOLD_WORKSPACE_PARENT_UNAVAILABLE"
                ) from error
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except BaseException:
        os.close(current_fd)
        raise


def hash_file_read_only(
    root: str | os.PathLike[str],
    workspace_id: str,
    logical_path: str,
    *,
    max_bytes: int = DEFAULT_MAX_OBSERVATION_BYTES,
) -> FileHashObservation:
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 0:
        raise WorkspaceHold("HOLD_OBSERVATION_BOUND_INVALID")
    parts = validated_relative_parts(logical_path)
    parent_fd = _open_parent_beneath(root, parts)
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        try:
            descriptor = os.open(parts[-1], flags, dir_fd=parent_fd)
        except OSError as error:
            if error.errno in {errno.ELOOP, errno.ENOTDIR}:
                raise WorkspaceConfinementError(
                    "WORKSPACE_FILE_SYMLINK_OR_NON_DIRECTORY"
                ) from error
            raise WorkspaceHold("HOLD_WORKSPACE_FILE_UNAVAILABLE") from error
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise WorkspaceConfinementError("WORKSPACE_ENTRY_NOT_REGULAR_FILE")
        if before.st_size > max_bytes:
            raise WorkspaceHold("HOLD_OBSERVATION_BOUND_EXCEEDED")

        digest = hashlib.sha256()
        observed_size = 0
        while True:
            block = os.read(descriptor, CHUNK_BYTES)
            if not block:
                break
            observed_size += len(block)
            if observed_size > max_bytes:
                raise WorkspaceHold("HOLD_OBSERVATION_BOUND_EXCEEDED")
            digest.update(block)

        after = os.fstat(descriptor)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if identity_before != identity_after or observed_size != after.st_size:
            raise WorkspaceHold("HOLD_FILE_CHANGED_DURING_OBSERVATION")

        sha256 = digest.hexdigest()
        version = (
            f"local-file:{after.st_dev}:{after.st_ino}:"
            f"{after.st_mtime_ns}:{after.st_size}:sha256:{sha256}"
        )
        return FileHashObservation(
            workspace_id=workspace_id,
            logical_path=logical_path,
            size_bytes=observed_size,
            sha256=sha256,
            observed_version_ref=version,
        )
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_fd)


def open_new_file_beneath(
    root: str | os.PathLike[str],
    logical_path: str,
    mode: int = 0o600,
) -> int:
    """Open a new file without following any path component symlink.

    The returned descriptor is owned by the caller.  Parent directories must
    already exist; this function never falls back to path-based writes.
    """

    if (
        isinstance(mode, bool)
        or not isinstance(mode, int)
        or not 0 <= mode <= 0o777
    ):
        raise WorkspaceHold("HOLD_SECURE_WRITE_MODE_INVALID")
    parts = validated_relative_parts(logical_path)
    parent_fd = _open_parent_beneath(root, parts)
    try:
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_NOFOLLOW
            | getattr(os, "O_CLOEXEC", 0)
        )
        try:
            descriptor = os.open(
                parts[-1],
                flags,
                mode,
                dir_fd=parent_fd,
            )
        except FileExistsError as error:
            raise WorkspaceHold("HOLD_TARGET_ALREADY_EXISTS") from error
        except OSError as error:
            if error.errno in {errno.ELOOP, errno.ENOTDIR}:
                raise WorkspaceConfinementError(
                    "WORKSPACE_TARGET_SYMLINK_OR_NON_DIRECTORY"
                ) from error
            raise WorkspaceHold("HOLD_SECURE_WRITE_OPEN_FAILED") from error
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise WorkspaceConfinementError("WORKSPACE_TARGET_NOT_REGULAR")
        return descriptor
    finally:
        os.close(parent_fd)
