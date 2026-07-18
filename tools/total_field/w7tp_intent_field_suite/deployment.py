"""Content-addressed release and rollback evidence without service mutation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from tools.deploy_w7tp_small_agent_all_nodes import (
    DeploymentError,
    _atomic_symlink,
)
from tools.total_field.w7tp_field_application_runtime import FieldApplicationError

from .canonical_hash import canonical_sha256


ROOT = Path(__file__).resolve().parents[3]
BOOTSTRAP_INSTALLER = ROOT / "tools/total_field/w7tp_bundle_installer.py"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_deployment_manifest(files: Iterable[Path], run_id: str) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for path in sorted({Path(item).resolve() for item in files}, key=str):
        try:
            relative = path.relative_to(ROOT)
        except ValueError as exc:
            raise FieldApplicationError("RELEASE_FILE_OUTSIDE_REPO") from exc
        if not path.is_file():
            raise FieldApplicationError("RELEASE_FILE_NOT_FOUND", str(relative))
        entries.append(
            {
                "path": relative.as_posix(),
                "sha256": file_sha256(path),
                "size": path.stat().st_size,
            }
        )
    manifest: dict[str, Any] = {
        "schema_version": "W7TP-DEPLOYMENT-MANIFEST/1.0",
        "run_id": run_id,
        "artifact_transport": "BYTE_EXACT_SHA256",
        "w7tp_generative_transmission": "PROTOCOL_NATIVE_8D_INTENT_FIELD_PACKET",
        "files": entries,
        "entrypoint": "tools/total_field/w7tp_field_application_runtime.py",
        "deployment_scope": "SHARED_RUNTIME_ONLY",
        "cpu_baseline_required": True,
        "cloud_fallback": False,
        "db_write": False,
        "dns_write": False,
        "router_write": False,
        "tailnet_policy_write": False,
        "formal_transaction": False,
        "rollback": {
            "mode": "ATOMIC_RELEASE_POINTER_RESTORE",
            "health_failure_action": "RESTORE_PREVIOUS_RELEASE",
            "caddy_failure_action": "RESTORE_BACKUP_VALIDATE_THEN_RELOAD",
            "node_failure_isolation": True,
        },
    }
    manifest["content_sha256"] = canonical_sha256(manifest)
    return manifest


def build_release_bundle(files: Iterable[Path], output_dir: Path, run_id: str) -> dict[str, Any]:
    manifest = build_deployment_manifest(files, run_id)
    release_id = manifest["content_sha256"][:16]
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / f"w7tp-intent-field-{release_id}.tar"
    manifest_path = output_dir / f"w7tp-intent-field-{release_id}.manifest.json"
    with tempfile.TemporaryDirectory(dir=output_dir) as directory:
        temporary_artifact = Path(directory) / artifact_path.name
        with tarfile.open(temporary_artifact, "w", format=tarfile.PAX_FORMAT) as archive:
            for entry in manifest["files"]:
                source = ROOT / entry["path"]
                info = archive.gettarinfo(str(source), arcname=entry["path"])
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mtime = 0
                with source.open("rb") as handle:
                    archive.addfile(info, handle)
            payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
            info = tarfile.TarInfo("SHA256_MANIFEST.json")
            info.size = len(payload)
            info.uid = info.gid = 0
            info.mtime = 0
            archive.addfile(info, __import__("io").BytesIO(payload))
        os.replace(temporary_artifact, artifact_path)
    manifest["artifact"] = {
        "path": artifact_path.name,
        "sha256": file_sha256(artifact_path),
        "size": artifact_path.stat().st_size,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    bootstrap_path = output_dir / f"install-w7tp-intent-field-{release_id}.py"
    shutil.copyfile(BOOTSTRAP_INSTALLER, bootstrap_path)
    bootstrap = {
        "path": str(bootstrap_path),
        "sha256": file_sha256(bootstrap_path),
        "size": bootstrap_path.stat().st_size,
    }
    return {
        "manifest": manifest,
        "manifest_path": str(manifest_path),
        "artifact_path": str(artifact_path),
        "bootstrap_installer": bootstrap,
        "exact_install_command": (
            f"python3 {bootstrap_path.name} "
            f"--artifact {artifact_path.name} --manifest {manifest_path.name} "
            "--install-root ~/.local/share/w7tp-intent-field"
        ),
    }


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise FieldApplicationError("DEPLOYMENT_MANIFEST_INVALID") from exc
    if not isinstance(value, dict):
        raise FieldApplicationError("DEPLOYMENT_MANIFEST_INVALID")
    return value


def _verify_bundle(artifact_path: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = _load_manifest(manifest_path)
    artifact = manifest.get("artifact")
    if not isinstance(artifact, Mapping):
        raise FieldApplicationError("DEPLOYMENT_ARTIFACT_RECORD_MISSING")
    if (
        artifact.get("path") != artifact_path.name
        or artifact.get("sha256") != file_sha256(artifact_path)
        or artifact.get("size") != artifact_path.stat().st_size
    ):
        raise FieldApplicationError("DEPLOYMENT_ARTIFACT_SHA256_MISMATCH")
    unsigned = dict(manifest)
    supplied_content_hash = unsigned.pop("content_sha256", None)
    unsigned.pop("artifact", None)
    if supplied_content_hash != canonical_sha256(unsigned):
        raise FieldApplicationError("DEPLOYMENT_MANIFEST_SHA256_MISMATCH")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise FieldApplicationError("DEPLOYMENT_MANIFEST_FILES_INVALID")
    expected_paths = [entry.get("path") for entry in files if isinstance(entry, dict)]
    if (
        len(expected_paths) != len(files)
        or any(not isinstance(path, str) or not path for path in expected_paths)
        or len(set(expected_paths)) != len(expected_paths)
    ):
        raise FieldApplicationError("DEPLOYMENT_MANIFEST_FILES_INVALID")
    return manifest


def _extract_verified_bundle(
    artifact_path: Path,
    manifest: Mapping[str, Any],
    stage: Path,
) -> None:
    expected = {
        entry["path"]: (entry["sha256"], entry["size"])
        for entry in manifest["files"]
    }
    seen: set[str] = set()
    embedded_manifest: dict[str, Any] | None = None
    try:
        archive = tarfile.open(artifact_path, "r")
    except (OSError, tarfile.TarError) as exc:
        raise FieldApplicationError("DEPLOYMENT_ARTIFACT_INVALID") from exc
    with archive:
        for member in archive.getmembers():
            name = member.name
            path = Path(name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or not member.isfile()
                or name in seen
                or (name not in expected and name != "SHA256_MANIFEST.json")
            ):
                raise FieldApplicationError("DEPLOYMENT_ARTIFACT_MEMBER_BLOCKED")
            seen.add(name)
            extracted = archive.extractfile(member)
            if extracted is None:
                raise FieldApplicationError("DEPLOYMENT_ARTIFACT_INVALID")
            content = extracted.read()
            if name == "SHA256_MANIFEST.json":
                try:
                    value = json.loads(content.decode("utf-8"))
                except (UnicodeError, json.JSONDecodeError) as exc:
                    raise FieldApplicationError(
                        "DEPLOYMENT_EMBEDDED_MANIFEST_INVALID"
                    ) from exc
                if not isinstance(value, dict):
                    raise FieldApplicationError("DEPLOYMENT_EMBEDDED_MANIFEST_INVALID")
                embedded_manifest = value
                continue
            expected_hash, expected_size = expected[name]
            if (
                len(content) != expected_size
                or hashlib.sha256(content).hexdigest() != expected_hash
            ):
                raise FieldApplicationError("DEPLOYMENT_RELEASE_FILE_SHA256_MISMATCH")
            destination = stage / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
    if seen != set(expected).union({"SHA256_MANIFEST.json"}):
        raise FieldApplicationError("DEPLOYMENT_ARTIFACT_INVENTORY_MISMATCH")
    expected_embedded = dict(manifest)
    expected_embedded.pop("artifact", None)
    if embedded_manifest != expected_embedded:
        raise FieldApplicationError("DEPLOYMENT_EMBEDDED_MANIFEST_MISMATCH")


def _default_release_health(release_root: Path) -> bool:
    runtime = release_root / "tools/total_field/w7tp_field_application_runtime.py"
    if not runtime.is_file():
        return False
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, str(runtime), "suite", "policy"],
        cwd=release_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    return completed.returncode == 0 and '"policy_hash"' in completed.stdout


def _verify_installed_files(
    release_root: Path, manifest: Mapping[str, Any]
) -> bool:
    return all(
        (release_root / entry["path"]).is_file()
        and (release_root / entry["path"]).stat().st_size == entry["size"]
        and file_sha256(release_root / entry["path"]) == entry["sha256"]
        for entry in manifest["files"]
    )


def install_release_bundle(
    artifact_path: Path,
    manifest_path: Path,
    install_root: Path,
    *,
    health_check: Callable[[Path], bool] | None = None,
) -> dict[str, Any]:
    """Install one immutable release and atomically switch or roll back current."""

    artifact_path = Path(artifact_path).resolve()
    manifest_path = Path(manifest_path).resolve()
    install_root = Path(install_root).expanduser().resolve()
    manifest = _verify_bundle(artifact_path, manifest_path)
    release_id = manifest["content_sha256"][:16]
    releases = install_root / "releases"
    target = releases / release_id
    stage = releases / f".{release_id}.stage"
    current = install_root / "current"
    check = health_check or _default_release_health
    releases.mkdir(parents=True, exist_ok=True)
    previous_target = os.readlink(current) if current.is_symlink() else None
    if current.exists() and not current.is_symlink():
        raise FieldApplicationError("DEPLOYMENT_CURRENT_POINTER_CONFLICT")
    if stage.exists():
        raise FieldApplicationError("DEPLOYMENT_STALE_STAGE")
    if target.exists():
        if not target.is_dir() or not _verify_installed_files(target, manifest):
            raise FieldApplicationError("DEPLOYMENT_EXISTING_RELEASE_CONFLICT")
    else:
        stage.mkdir()
        try:
            _extract_verified_bundle(artifact_path, manifest, stage)
            if not _verify_installed_files(stage, manifest) or not check(stage):
                raise FieldApplicationError("DEPLOYMENT_STAGE_HEALTH_FAILED")
            os.replace(stage, target)
        except Exception:
            if stage.exists():
                shutil.rmtree(stage)
            raise
    if current.is_symlink() and current.resolve() == target.resolve() and check(target):
        return {
            "state": "ALREADY_PASS",
            "release_id": release_id,
            "release_content_sha256": manifest["content_sha256"],
            "current": str(target),
            "health": "PASS",
            "rollback_status": "NOT_REQUIRED",
            "reloads_or_restarts": [],
        }
    try:
        _atomic_symlink(target, current)
    except DeploymentError as exc:
        raise FieldApplicationError(exc.reason_code) from exc
    if not current.is_symlink() or current.resolve() != target.resolve() or not check(target):
        try:
            if previous_target is None:
                if current.is_symlink():
                    current.unlink()
            else:
                _atomic_symlink(Path(previous_target), current)
        except (OSError, DeploymentError) as exc:
            raise FieldApplicationError(
                "DEPLOYMENT_HEALTH_FAILED_ROLLBACK_FAILED"
            ) from exc
        if previous_target is not None:
            previous_release = (current.parent / previous_target).resolve()
            if not current.is_symlink() or current.resolve() != previous_release or not check(previous_release):
                raise FieldApplicationError(
                    "DEPLOYMENT_HEALTH_FAILED_ROLLBACK_HEALTH_FAILED"
                )
        raise FieldApplicationError("DEPLOYMENT_HEALTH_FAILED_ROLLED_BACK")
    return {
        "state": "PASS",
        "release_id": release_id,
        "release_content_sha256": manifest["content_sha256"],
        "current": str(target),
        "health": "PASS",
        "rollback_status": "ARMED_PREVIOUS_POINTER_RECORDED",
        "previous_current": previous_target,
        "reloads_or_restarts": [],
        "db_write": False,
        "dns_write": False,
        "router_write": False,
        "tailnet_policy_write": False,
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def build_evidence_seal(
    files: Iterable[Path],
    output_root: Path,
    run_id: str,
    *,
    node_matrix: dict[str, Any],
    health_checks: dict[str, Any],
    tests: dict[str, Any],
    deployment_status: dict[str, Any],
) -> dict[str, Any]:
    """Seal source, tests, inventory, health, and deployment truth under one run."""

    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    release = build_release_bundle(files, run_dir / "release", run_id)
    evidence = {
        "NODE_MATRIX.json": node_matrix,
        "HEALTH_CHECKS.json": health_checks,
        "TEST_RESULTS.json": tests,
        "DEPLOYMENT_STATUS.json": deployment_status,
    }
    for name, value in evidence.items():
        _write_json(run_dir / name, value)

    entries: list[dict[str, Any]] = []
    for path in sorted(run_dir.rglob("*"), key=str):
        if path.is_file() and path.name != "SHA256_MANIFEST.json":
            entries.append(
                {
                    "path": path.relative_to(run_dir).as_posix(),
                    "sha256": file_sha256(path),
                    "size": path.stat().st_size,
                }
            )
    seal: dict[str, Any] = {
        "schema_version": "W7TP-SHARED-INTENT-FIELD-EVIDENCE/1.0",
        "run_id": run_id,
        "state": deployment_status.get("state"),
        "files": entries,
        "release_content_sha256": release["manifest"]["content_sha256"],
        "db_write": False,
        "dns_write": False,
        "router_write": False,
        "tailnet_policy_write": False,
        "git_commit": False,
        "git_push": False,
    }
    seal["content_sha256"] = canonical_sha256(seal)
    seal_path = run_dir / "SHA256_MANIFEST.json"
    _write_json(seal_path, seal)
    return {"run_dir": str(run_dir), "seal_path": str(seal_path), "seal": seal}
