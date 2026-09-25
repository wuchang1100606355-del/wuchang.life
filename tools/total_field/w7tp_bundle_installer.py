#!/usr/bin/env python3
"""Install one verified W7TP release bundle without requiring the repository.

This bootstrap is intentionally standard-library-only. It verifies the
sidecar manifest, byte-exact artifact, archive members, and embedded manifest
before promoting an immutable content-addressed release. It never installs a
service or writes DNS, router, database, or tailnet state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


SHA256_HEX_LENGTH = 64
EMBEDDED_MANIFEST_MAX_BYTES = 5 * 1024 * 1024


class BundleInstallError(ValueError):
    """Stable rejection that never includes untrusted content."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise BundleInstallError("DEPLOYMENT_MANIFEST_INVALID") from exc


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise BundleInstallError("DEPLOYMENT_ARTIFACT_UNREADABLE") from exc
    return digest.hexdigest()


def _load_json_object(path: Path, reason_code: str) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise BundleInstallError(reason_code) from exc
    if not isinstance(value, dict):
        raise BundleInstallError(reason_code)
    return value


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == SHA256_HEX_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def _safe_relative_path(value: Any) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise BundleInstallError("DEPLOYMENT_MANIFEST_FILES_INVALID")
    posix = PurePosixPath(value)
    if posix.is_absolute() or any(part in {"", ".", ".."} for part in posix.parts):
        raise BundleInstallError("DEPLOYMENT_MANIFEST_FILES_INVALID")
    return Path(*posix.parts)


def _verified_manifest(artifact_path: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = _load_json_object(manifest_path, "DEPLOYMENT_MANIFEST_INVALID")
    content_sha256 = manifest.get("content_sha256")
    if not _is_sha256(content_sha256):
        raise BundleInstallError("DEPLOYMENT_MANIFEST_SHA256_MISMATCH")
    unsigned = dict(manifest)
    unsigned.pop("content_sha256", None)
    artifact = unsigned.pop("artifact", None)
    if content_sha256 != _canonical_sha256(unsigned):
        raise BundleInstallError("DEPLOYMENT_MANIFEST_SHA256_MISMATCH")
    if not isinstance(artifact, Mapping):
        raise BundleInstallError("DEPLOYMENT_ARTIFACT_RECORD_MISSING")
    try:
        artifact_size = artifact_path.stat().st_size
    except OSError as exc:
        raise BundleInstallError("DEPLOYMENT_ARTIFACT_UNREADABLE") from exc
    if (
        artifact.get("path") != artifact_path.name
        or not _is_sha256(artifact.get("sha256"))
        or artifact.get("sha256") != _file_sha256(artifact_path)
        or isinstance(artifact.get("size"), bool)
        or artifact.get("size") != artifact_size
    ):
        raise BundleInstallError("DEPLOYMENT_ARTIFACT_SHA256_MISMATCH")

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise BundleInstallError("DEPLOYMENT_MANIFEST_FILES_INVALID")
    seen: set[str] = set()
    for entry in files:
        if not isinstance(entry, Mapping):
            raise BundleInstallError("DEPLOYMENT_MANIFEST_FILES_INVALID")
        path = _safe_relative_path(entry.get("path")).as_posix()
        size = entry.get("size")
        if (
            path in seen
            or not _is_sha256(entry.get("sha256"))
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
        ):
            raise BundleInstallError("DEPLOYMENT_MANIFEST_FILES_INVALID")
        seen.add(path)
    return manifest


def _expected_files(manifest: Mapping[str, Any]) -> dict[str, tuple[str, int]]:
    return {
        _safe_relative_path(entry["path"]).as_posix(): (
            entry["sha256"],
            entry["size"],
        )
        for entry in manifest["files"]
    }


def _extract_verified(artifact_path: Path, manifest: Mapping[str, Any], stage: Path) -> None:
    expected = _expected_files(manifest)
    seen: set[str] = set()
    embedded_manifest: dict[str, Any] | None = None
    try:
        archive = tarfile.open(artifact_path, "r")
    except (OSError, tarfile.TarError) as exc:
        raise BundleInstallError("DEPLOYMENT_ARTIFACT_INVALID") from exc
    with archive:
        for member in archive.getmembers():
            name = member.name
            if name in seen or not member.isfile():
                raise BundleInstallError("DEPLOYMENT_ARTIFACT_MEMBER_BLOCKED")
            seen.add(name)
            extracted = archive.extractfile(member)
            if extracted is None:
                raise BundleInstallError("DEPLOYMENT_ARTIFACT_INVALID")
            if name == "SHA256_MANIFEST.json":
                if member.size > EMBEDDED_MANIFEST_MAX_BYTES:
                    raise BundleInstallError("DEPLOYMENT_EMBEDDED_MANIFEST_INVALID")
                content = extracted.read(EMBEDDED_MANIFEST_MAX_BYTES + 1)
                try:
                    value = json.loads(
                        content.decode("utf-8"),
                        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
                    )
                except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
                    raise BundleInstallError("DEPLOYMENT_EMBEDDED_MANIFEST_INVALID") from exc
                if not isinstance(value, dict):
                    raise BundleInstallError("DEPLOYMENT_EMBEDDED_MANIFEST_INVALID")
                embedded_manifest = value
                continue
            relative = _safe_relative_path(name)
            if name not in expected:
                raise BundleInstallError("DEPLOYMENT_ARTIFACT_MEMBER_BLOCKED")
            expected_hash, expected_size = expected[name]
            if member.size != expected_size:
                raise BundleInstallError("DEPLOYMENT_RELEASE_FILE_SHA256_MISMATCH")
            content = extracted.read(expected_size + 1)
            if len(content) != expected_size or hashlib.sha256(content).hexdigest() != expected_hash:
                raise BundleInstallError("DEPLOYMENT_RELEASE_FILE_SHA256_MISMATCH")
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
    if seen != set(expected).union({"SHA256_MANIFEST.json"}):
        raise BundleInstallError("DEPLOYMENT_ARTIFACT_INVENTORY_MISMATCH")
    expected_embedded = dict(manifest)
    expected_embedded.pop("artifact", None)
    if embedded_manifest != expected_embedded:
        raise BundleInstallError("DEPLOYMENT_EMBEDDED_MANIFEST_MISMATCH")


def _installed_files_pass(release_root: Path, manifest: Mapping[str, Any]) -> bool:
    expected = _expected_files(manifest)
    actual: set[str] = set()
    try:
        for installed in release_root.rglob("*"):
            if installed.is_symlink():
                return False
            if installed.is_file():
                actual.add(installed.relative_to(release_root).as_posix())
    except OSError:
        return False
    if actual != set(expected):
        return False
    for path, (expected_hash, expected_size) in expected.items():
        installed = release_root / Path(*PurePosixPath(path).parts)
        try:
            if (
                not installed.is_file()
                or installed.stat().st_size != expected_size
                or _file_sha256(installed) != expected_hash
            ):
                return False
        except BundleInstallError:
            return False
    return True


def _health_pass(release_root: Path) -> bool:
    runtime = release_root / "tools/total_field/w7tp_field_application_runtime.py"
    if not runtime.is_file():
        return False
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        completed = subprocess.run(
            [sys.executable, str(runtime), "suite", "policy"],
            cwd=release_root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0 and '"policy_hash"' in completed.stdout


def _atomic_symlink(target: Path, link: Path) -> None:
    temporary = link.with_name(f".{link.name}.{os.getpid()}.tmp")
    if temporary.exists() or temporary.is_symlink():
        raise BundleInstallError("DEPLOYMENT_ATOMIC_POINTER_TEMP_CONFLICT")
    try:
        os.symlink(str(target), temporary)
        os.replace(temporary, link)
    except OSError as exc:
        raise BundleInstallError("DEPLOYMENT_ATOMIC_POINTER_FAILED") from exc
    finally:
        if temporary.is_symlink():
            temporary.unlink()


def install_bundle(artifact: Path, manifest_path: Path, install_root: Path) -> dict[str, Any]:
    artifact = artifact.resolve()
    manifest_path = manifest_path.resolve()
    install_root = install_root.expanduser().resolve()
    manifest = _verified_manifest(artifact, manifest_path)
    release_id = manifest["content_sha256"][:16]
    releases = install_root / "releases"
    target = releases / release_id
    stage = releases / f".{release_id}.stage"
    current = install_root / "current"
    releases.mkdir(parents=True, exist_ok=True)
    previous_target = os.readlink(current) if current.is_symlink() else None
    if current.exists() and not current.is_symlink():
        raise BundleInstallError("DEPLOYMENT_CURRENT_POINTER_CONFLICT")
    if stage.exists() or stage.is_symlink():
        raise BundleInstallError("DEPLOYMENT_STALE_STAGE")
    if target.exists():
        if not target.is_dir() or not _installed_files_pass(target, manifest) or not _health_pass(target):
            raise BundleInstallError("DEPLOYMENT_EXISTING_RELEASE_CONFLICT")
    else:
        stage.mkdir(mode=0o700)
        try:
            _extract_verified(artifact, manifest, stage)
            if not _installed_files_pass(stage, manifest) or not _health_pass(stage):
                raise BundleInstallError("DEPLOYMENT_STAGE_HEALTH_FAILED")
            os.replace(stage, target)
        except Exception:
            if stage.exists():
                shutil.rmtree(stage)
            raise
    if current.is_symlink() and current.resolve() == target.resolve():
        return {
            "state": "ALREADY_PASS",
            "release_id": release_id,
            "release_content_sha256": manifest["content_sha256"],
            "current": str(target),
            "health": "PASS",
            "rollback_status": "NOT_REQUIRED",
            "service_mutation": False,
        }
    _atomic_symlink(target, current)
    if not current.is_symlink() or current.resolve() != target.resolve() or not _health_pass(target):
        if previous_target is None:
            if current.is_symlink():
                current.unlink()
        else:
            _atomic_symlink(Path(previous_target), current)
            previous_release = (current.parent / previous_target).resolve()
            if not current.is_symlink() or current.resolve() != previous_release or not _health_pass(previous_release):
                raise BundleInstallError("DEPLOYMENT_HEALTH_FAILED_ROLLBACK_FAILED")
        raise BundleInstallError("DEPLOYMENT_HEALTH_FAILED_ROLLED_BACK")
    return {
        "state": "PASS",
        "release_id": release_id,
        "release_content_sha256": manifest["content_sha256"],
        "current": str(target),
        "previous_current": previous_target,
        "health": "PASS",
        "rollback_status": "ARMED_PREVIOUS_POINTER_RECORDED",
        "service_mutation": False,
        "db_write": False,
        "dns_write": False,
        "router_write": False,
        "tailnet_policy_write": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify and install one content-addressed W7TP release bundle."
    )
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--install-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = install_bundle(args.artifact, args.manifest, args.install_root)
    except BundleInstallError as exc:
        print(
            json.dumps(
                {"state": "HOLD", "reason_code": exc.reason_code},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
