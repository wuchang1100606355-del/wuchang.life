#!/usr/bin/env python3
"""Preview or atomically stage an exact, allowlisted Git path set.

The live index is never used as a scratch area. Staging is first built and
verified in a temporary index, then installed only if HEAD and the original
index are unchanged. This tool never commits or pushes.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "docs" / "project" / "git_stage_allowlist.txt"

BLOCK_PATTERNS = [
    ".env", ".env.*", "keys/*", "*/keys/*", "*.key", "*.pem", "*.db",
    "*.sqlite", "data/*", "logs/*", "runtime/reports/*", "runtime/proofs/*",
    "runtime/merlin_*/*", "runtime/router_guard_dryrun/*", "runtime/patches/*",
    "open_webui_data/*", "*.tar.gz", "*.bak_*", "*password*", "*secret*",
    "*token*", "*private_key*",
]


class StageSafetyError(ValueError):
    def __init__(self, code: str, path: str = "$") -> None:
        self.code = code
        self.path = path
        super().__init__(f"{code}:{path}")


def run_git(repo: Path, *args: str, env: dict[str, str] | None = None, binary: bool = False) -> bytes | str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, env=env
    )
    return completed.stdout if binary else completed.stdout.decode("utf-8", "strict").strip()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_allowlist(path: Path = ALLOWLIST) -> list[str]:
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def split_z(value: bytes) -> list[str]:
    return [item.decode("utf-8", "surrogateescape") for item in value.split(b"\0") if item]


def changed_files(repo: Path = ROOT) -> list[str]:
    tracked = split_z(run_git(repo, "diff", "HEAD", "--name-only", "-z", binary=True))
    untracked = split_z(run_git(repo, "ls-files", "--others", "--exclude-standard", "-z", binary=True))
    return sorted(set(tracked + untracked))


def staged_files(repo: Path = ROOT, env: dict[str, str] | None = None) -> list[str]:
    return sorted(set(split_z(run_git(repo, "diff", "--cached", "--name-only", "-z", binary=True, env=env))))


def is_blocked(path: str) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in BLOCK_PATTERNS)


def is_allowed(path: str, allow: Iterable[str]) -> bool:
    for pattern in allow:
        if pattern.endswith("/") and path.startswith(pattern):
            return True
        if fnmatch.fnmatchcase(path, pattern):
            return True
    return False


def validate_exact_path(repo: Path, raw_path: str) -> str:
    if not raw_path or raw_path == "." or raw_path.startswith(":("):
        raise StageSafetyError("HOLD_SCOPE_NOT_EXACT", raw_path or "$")
    if any(character in raw_path for character in "*?[") or any(character in raw_path for character in "\x00\n\r"):
        raise StageSafetyError("HOLD_SCOPE_NOT_EXACT", raw_path)
    candidate = PurePosixPath(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts or ".git" in candidate.parts or raw_path.endswith("/"):
        raise StageSafetyError("HOLD_SCOPE_NOT_EXACT", raw_path)
    normalized = candidate.as_posix()
    if normalized != raw_path or normalized in {"", "."}:
        raise StageSafetyError("HOLD_SCOPE_NOT_EXACT", raw_path)
    target = repo / normalized
    current = repo
    for part in candidate.parts:
        current = current / part
        if current.is_symlink():
            raise StageSafetyError("HOLD_SYMLINK_SCOPE", normalized)
    if target.is_dir():
        raise StageSafetyError("HOLD_DIRECTORY_SCOPE_NOT_ENUMERATED", normalized)
    return normalized


def repository_coordinate(repo: Path) -> dict[str, str]:
    return {
        "root": str(repo.resolve()),
        "branch": str(run_git(repo, "branch", "--show-current")),
        "head": str(run_git(repo, "rev-parse", "HEAD")),
        "tree": str(run_git(repo, "rev-parse", "HEAD^{tree}")),
        "object_format": str(run_git(repo, "rev-parse", "--show-object-format")),
    }


def path_manifest(repo: Path, paths: Iterable[str], allow_deletion: bool) -> list[dict[str, Any]]:
    changed = set(changed_files(repo))
    manifest: list[dict[str, Any]] = []
    for path in paths:
        if path not in changed:
            raise StageSafetyError("HOLD_PATH_NOT_CHANGED", path)
        target = repo / path
        tracked = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "--error-unmatch", "--", path], capture_output=True
        ).returncode == 0
        if target.is_file():
            manifest.append({"path": path, "state": "FILE", "worktree_sha256": digest_file(target)})
        elif not target.exists() and tracked:
            if not allow_deletion:
                raise StageSafetyError("HOLD_DELETE_AUTHORITY_MISSING", path)
            manifest.append({"path": path, "state": "DELETION", "worktree_sha256": None})
        else:
            raise StageSafetyError("HOLD_UNSUPPORTED_PATH_STATE", path)
    return manifest


def index_path(repo: Path) -> Path:
    raw = Path(str(run_git(repo, "rev-parse", "--git-path", "index")))
    return raw if raw.is_absolute() else repo / raw


def staged_blob(repo: Path, path: str, env: dict[str, str]) -> tuple[str, str]:
    output = split_z(run_git(repo, "ls-files", "--stage", "-z", "--", path, binary=True, env=env))
    if len(output) != 1 or "\t" not in output[0]:
        raise StageSafetyError("HOLD_STAGED_BLOB_MISSING", path)
    header, indexed_path = output[0].split("\t", 1)
    mode, oid, stage = header.split(" ")
    if indexed_path != path or stage != "0":
        raise StageSafetyError("HOLD_STAGED_BLOB_MISMATCH", path)
    blob = run_git(repo, "cat-file", "blob", oid, binary=True)
    assert isinstance(blob, bytes)
    return mode, digest_bytes(blob)


def verify_temporary_index(repo: Path, env: dict[str, str], manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    intended = [entry["path"] for entry in manifest]
    if staged_files(repo, env) != sorted(intended):
        raise StageSafetyError("HOLD_INDEX_PATH_SET_MISMATCH")
    verified: list[dict[str, Any]] = []
    for entry in manifest:
        if entry["state"] == "DELETION":
            if split_z(run_git(repo, "ls-files", "-z", "--", entry["path"], binary=True, env=env)):
                raise StageSafetyError("HOLD_DELETION_NOT_STAGED", entry["path"])
            verified.append({**entry, "index_mode": None, "staged_bytes_sha256": None})
            continue
        mode, staged_sha256 = staged_blob(repo, entry["path"], env)
        if staged_sha256 != entry["worktree_sha256"]:
            raise StageSafetyError("HOLD_WORKTREE_INDEX_CONTENT_MISMATCH", entry["path"])
        verified.append({**entry, "index_mode": mode, "staged_bytes_sha256": staged_sha256})
    return verified


def install_index_atomically(repo: Path, temporary_index: Path, original_index: Path, original_sha256: str, coordinate: dict[str, str]) -> None:
    lock = original_index.with_name(original_index.name + ".lock")
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise StageSafetyError("HOLD_INDEX_LOCKED", str(lock)) from exc
    installed = False
    try:
        if repository_coordinate(repo) != coordinate or digest_file(original_index) != original_sha256:
            raise StageSafetyError("HOLD_COORDINATE_OR_INDEX_DRIFT")
        owned_descriptor = descriptor
        descriptor = -1
        with temporary_index.open("rb") as source, os.fdopen(owned_descriptor, "wb", closefd=True) as destination:
            shutil.copyfileobj(source, destination)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(lock, original_index)
        installed = True
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if not installed:
            lock.unlink(missing_ok=True)


def stage_exact_paths(repo: Path, paths: list[str], allow: list[str], allow_deletion: bool = False) -> dict[str, Any]:
    if not paths:
        raise StageSafetyError("HOLD_EXPLICIT_PATHS_REQUIRED")
    normalized = [validate_exact_path(repo, path) for path in paths]
    if len(normalized) != len(set(normalized)):
        raise StageSafetyError("HOLD_DUPLICATE_PATH")
    for path in normalized:
        if is_blocked(path):
            raise StageSafetyError("HOLD_BLOCKED_PATH", path)
        if not is_allowed(path, allow):
            raise StageSafetyError("HOLD_PATH_NOT_ALLOWLISTED", path)
    if staged_files(repo):
        raise StageSafetyError("HOLD_PREEXISTING_INDEX_STATE")

    coordinate = repository_coordinate(repo)
    manifest = path_manifest(repo, normalized, allow_deletion)
    live_index = index_path(repo)
    if not live_index.is_file():
        raise StageSafetyError("HOLD_GIT_INDEX_MISSING", str(live_index))
    original_sha256 = digest_file(live_index)
    temporary_fd, temporary_name = tempfile.mkstemp(prefix="safe-stage-index-", dir=live_index.parent)
    os.close(temporary_fd)
    temporary_index = Path(temporary_name)
    try:
        shutil.copy2(live_index, temporary_index)
        environment = dict(os.environ)
        environment["GIT_INDEX_FILE"] = str(temporary_index)
        run_git(repo, "add", "--", *normalized, env=environment)
        verified = verify_temporary_index(repo, environment, manifest)
        if repository_coordinate(repo) != coordinate or digest_file(live_index) != original_sha256:
            raise StageSafetyError("HOLD_COORDINATE_OR_INDEX_DRIFT")
        install_index_atomically(repo, temporary_index, live_index, original_sha256, coordinate)
        final_verified = verify_temporary_index(repo, dict(os.environ), manifest)
        if final_verified != verified:
            raise StageSafetyError("HOLD_INSTALLED_INDEX_READBACK_MISMATCH")
        return {"state": "STAGED_EXACT_PATHS", "coordinate": coordinate, "entries": verified}
    finally:
        temporary_index.unlink(missing_ok=True)


def preview(repo: Path, paths: list[str], allow: list[str], allow_deletion: bool) -> dict[str, Any]:
    candidates = paths or changed_files(repo)
    allowed: list[str] = []
    blocked: list[str] = []
    rejected: list[str] = []
    invalid: list[dict[str, str]] = []
    for raw_path in candidates:
        try:
            path = validate_exact_path(repo, raw_path)
        except StageSafetyError as exc:
            invalid.append({"path": raw_path, "reason": exc.code})
            continue
        if is_blocked(path):
            blocked.append(path)
        elif is_allowed(path, allow):
            allowed.append(path)
        else:
            rejected.append(path)
    manifest = path_manifest(repo, allowed, allow_deletion) if allowed else []
    return {
        "state": "DRY_RUN_PREVIEW", "coordinate": repository_coordinate(repo),
        "allowed": allowed, "blocked": blocked, "rejected_not_allowlisted": rejected,
        "invalid_scope": invalid, "entries": manifest, "commit": False, "report_written": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--stage", action="store_true")
    parser.add_argument("--allow-deletion", action="store_true")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)
    allow = read_allowlist()
    try:
        result = stage_exact_paths(ROOT, args.paths, allow, args.allow_deletion) if args.stage else preview(ROOT, args.paths, allow, args.allow_deletion)
    except (StageSafetyError, subprocess.CalledProcessError, OSError) as exc:
        code = exc.code if isinstance(exc, StageSafetyError) else "HOLD_GIT_STAGE_COMMAND_FAILED"
        path = exc.path if isinstance(exc, StageSafetyError) else "$"
        print(json.dumps({"state": "HOLD_SAFE_GIT_STAGE", "reason_code": code, "error_path": path, "commit": False}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
