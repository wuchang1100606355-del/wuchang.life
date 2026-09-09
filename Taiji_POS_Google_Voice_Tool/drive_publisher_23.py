#!/usr/bin/env python3
"""Publish one immutable 8DADI 2.3 material package to the shared Drive field."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone


SCHEMA = "w7tp.8dadi.generative-material-manifest/2.3"
DEFAULT_REMOTE = (
    "wuchang_gdrive,team_drive=0ABYhFR44_jiNUk9PVA:"
    "W7TP_MODEL_STATIC_FIELD/models"
)
DEFAULT_RECEIPT_ROOT = Path(
    "/home/taiji_admin/Taiji_Hub/reports/voice_materializer_23"
)
MAX_DIRECT_BYTES = 512 * 1024 * 1024
# Codex Google Drive connector has a 100 MiB transport ceiling.
CHUNK_BYTES = 96 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now_token() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


def run_rclone(*args: str) -> None:
    subprocess.run(["rclone", *args], check=True)


def build_manifest(package_id: str, source_root: Path, chunk_root: Path | None = None) -> dict:
    if not source_root.is_dir():
        raise ValueError("來源材料目錄不存在")
    files = []
    for path in sorted(source_root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"材料包不接受符號連結: {path}")
        if path.is_file():
            relative = path.relative_to(source_root).as_posix()
            item = {
                "path": relative,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            if path.stat().st_size > MAX_DIRECT_BYTES:
                if chunk_root is None:
                    raise ValueError(f"大檔需要分片材料座標: {relative}")
                chunk_root.mkdir(parents=True, exist_ok=True)
                chunks = []
                with path.open("rb") as source:
                    part = 0
                    while True:
                        block = source.read(CHUNK_BYTES)
                        if not block:
                            break
                        chunk_name = f"{len(files):04d}.part{part:04d}"
                        chunk_path = chunk_root / chunk_name
                        chunk_path.write_bytes(block)
                        chunks.append({
                            "path": f"chunks/{chunk_name}",
                            "size": len(block),
                            "sha256": hashlib.sha256(block).hexdigest(),
                        })
                        part += 1
                item["storage"] = "CHUNKED_EXACT_RECONSTRUCTION"
                item["chunks"] = chunks
            else:
                item["storage"] = "DIRECT"
            files.append(item)
    if not files:
        raise ValueError("來源材料目錄是空的")
    return {
        "schema": SCHEMA,
        "package_id": package_id,
        "D1_intent": "供小J語音器官使用的可重建材料",
        "D2_state": "IMMUTABLE_MATERIAL_PACKAGE",
        "D3_coordinate": "W7TP_MODEL_STATIC_FIELD/models",
        "D4_evidence": "size_and_sha256_per_file",
        "D5_execution": "host_resolver_only_container_read_only",
        "D6_transfer": "manifest_driven_missing_or_mismatched_only",
        "D7_risk": "fail_closed_no_delete_no_credential_in_container",
        "D8_authority": {
            "cloud_role": "MATERIAL_ONLY",
            "runtime_decider": "TOTAL_FIELD",
            "canonical_version": "2.3",
        },
        "files": files,
    }


def publish(package_id: str, source_root: Path, remote_root: str, receipt_root: Path) -> dict:
    manifest = build_manifest(package_id, source_root)
    receipt_root.mkdir(parents=True, exist_ok=True)
    uploaded = []
    for item in manifest["files"]:
        local = source_root / item["path"]
        remote = f"{remote_root}/raw/{package_id}/{item['path']}"
        run_rclone("copyto", str(local), remote, "--immutable")
        uploaded.append(item)

    manifest_path = receipt_root / f"{package_id}.manifest.8dadi.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    run_rclone(
        "copyto",
        str(manifest_path),
        f"{remote_root}/manifests/{package_id}/manifest.8dadi.json",
        "--immutable",
    )
    receipt = {
        "schema": "w7tp.8dadi.material-publish-receipt/2.3",
        "timestamp": now_token(),
        "package_id": package_id,
        "decision": "PASS_PUBLISHED_IMMUTABLE_MATERIAL",
        "files": uploaded,
        "cloud_role": "MATERIAL_ONLY",
        "runtime_authority": "TOTAL_FIELD_REOBSERVATION_REQUIRED",
    }
    receipt_path = receipt_root / f"{receipt['timestamp']}_{package_id}.publish.json"
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    run_rclone(
        "copyto",
        str(receipt_path),
        f"{remote_root}/reports/{package_id}/{receipt_path.name}",
        "--immutable",
    )
    return receipt


def prepare_manifest(package_id: str, source_root: Path, receipt_root: Path) -> tuple[dict, Path]:
    receipt_root.mkdir(parents=True, exist_ok=True)
    chunk_root = receipt_root / "transport" / package_id / "chunks"
    manifest = build_manifest(package_id, source_root, chunk_root=chunk_root)
    manifest_path = receipt_root / f"{package_id}.manifest.8dadi.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest, manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description="8DADI 2.3 雲端材料發佈器")
    parser.add_argument("package_id")
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--remote-root", default=DEFAULT_REMOTE)
    parser.add_argument("--receipt-root", type=Path, default=DEFAULT_RECEIPT_ROOT)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if args.prepare_only:
        manifest, manifest_path = prepare_manifest(
            args.package_id, args.source_root, args.receipt_root
        )
        print(json.dumps({
            "decision": "PASS_LOCAL_MANIFEST_PREPARED",
            "package_id": args.package_id,
            "manifest_path": str(manifest_path),
            "file_count": len(manifest["files"]),
            "total_size": sum(item["size"] for item in manifest["files"]),
        }, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(json.dumps(
        publish(args.package_id, args.source_root, args.remote_root, args.receipt_root),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
