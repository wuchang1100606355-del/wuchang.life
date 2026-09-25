from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .common import evidence_envelope, sha256_bytes


ALLOWED_FILES = {
    "network_state.json",
    "node_identity_map.json",
    "path_matrix.json",
    "service_binding_matrix.json",
    "route_decision.json",
    "intent_path_bindings.json",
    "failover_bindings.json",
    "concurrent_path_bindings.json",
    "zone_state.json",
    "network_risks.json",
    "merlin_observation.json",
}


def write_bundle(
    output_dir: Path,
    documents: dict[str, dict[str, Any]],
    *,
    timestamp: str,
    source_node: str,
    supersede_existing: bool = False,
) -> dict[str, Any]:
    unexpected = set(documents) - ALLOWED_FILES
    missing = ALLOWED_FILES - set(documents)
    if unexpected or missing:
        raise ValueError(
            f"evidence_file_set_mismatch unexpected={sorted(unexpected)} missing={sorted(missing)}"
        )
    if output_dir.exists() and output_dir.is_symlink():
        raise ValueError("output_directory_must_not_be_symlink")
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {name: output_dir / name for name in ALLOWED_FILES}
    existing = [str(path) for path in paths.values() if path.exists()]
    manifest_path = output_dir / "evidence_manifest.json"
    if manifest_path.exists():
        existing.append(str(manifest_path))
    previous_candidate_archive: str | None = None
    if existing and not supersede_existing:
        raise FileExistsError(f"candidate_evidence_already_exists:{sorted(existing)}")
    if existing:
        previous_candidate_archive = _archive_existing_bundle(output_dir, paths, manifest_path)

    hashes: dict[str, str] = {}
    for name in sorted(documents):
        payload = _serialize(documents[name])
        _atomic_write(paths[name], payload)
        hashes[name] = sha256_bytes(payload)

    manifest = {
        **evidence_envelope(
            schema_id="W7TP_8D_ADI_NETWORK_EVIDENCE_MANIFEST_V2",
            timestamp=timestamp,
            source_node=source_node,
            confidence="HIGH",
        ),
        "state": "CANDIDATE_EVIDENCE_WRITTEN",
        "files": [
            {"path": name, "sha256": digest, "bytes": paths[name].stat().st_size}
            for name, digest in sorted(hashes.items())
        ],
        "hash_algorithm": "SHA-256",
        "canonical": False,
        "total_field_decision": "NOT_RUN",
        "network_mutation": False,
        "router_mutation": False,
        "service_restart": False,
    }
    if previous_candidate_archive:
        manifest["previous_candidate_archive"] = previous_candidate_archive
    manifest_payload = _serialize(manifest)
    _atomic_write(manifest_path, manifest_payload)
    return {
        "output_dir": str(output_dir),
        "files": sorted([*documents, manifest_path.name]),
        "hashes": hashes,
        "manifest_sha256": sha256_bytes(manifest_payload),
        "previous_candidate_archive": previous_candidate_archive,
    }


def _serialize(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _atomic_write(path: Path, payload: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _archive_existing_bundle(
    output_dir: Path, paths: dict[str, Path], manifest_path: Path
) -> str:
    required = [*paths.values(), manifest_path]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ValueError(f"cannot_supersede_incomplete_candidate_bundle:{missing}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("cannot_supersede_invalid_manifest") from exc
    expected = {
        item.get("path"): item.get("sha256")
        for item in manifest.get("files", [])
        if isinstance(item, dict)
    }
    for name, path in paths.items():
        digest = sha256_bytes(path.read_bytes())
        if expected.get(name) != digest:
            raise ValueError(f"cannot_supersede_hash_mismatch:{name}")
    timestamp = str(manifest.get("timestamp", "UNKNOWN"))
    archive_id = re.sub(r"[^0-9A-Za-z_.-]", "_", timestamp)
    archive_dir = output_dir / "history" / archive_id
    if archive_dir.exists():
        raise FileExistsError(f"candidate_archive_already_exists:{archive_dir}")
    archive_dir.mkdir(parents=True)
    for source in required:
        _atomic_write(archive_dir / source.name, source.read_bytes())
    return str(archive_dir.relative_to(output_dir))
