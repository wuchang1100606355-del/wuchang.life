#!/usr/bin/env python3
"""8DADI 2.3 Google Drive material field resolver.

Google Drive is an untrusted material field.  Only files named by a validated
manifest are materialized into the local read-only container projection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tempfile
from datetime import datetime, timezone


SCHEMA = "w7tp.8dadi.generative-material-manifest/2.3"
DEFAULT_REMOTE = (
    "wuchang_gdrive,team_drive=0ABYhFR44_jiNUk9PVA:"
    "W7TP_MODEL_STATIC_FIELD/models"
)
DEFAULT_LOCAL_ROOT = Path(
    "/home/taiji_admin/Taiji_Hub/runtime/materialized/xiaoj_voice_23"
)
DEFAULT_RECEIPT_ROOT = Path(
    "/home/taiji_admin/Taiji_Hub/reports/voice_materializer_23"
)


def now_token() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"不安全的材料座標: {value!r}")
    return path


def run_rclone(*args: str, capture: bool = False) -> str:
    command = ["rclone", *args]
    completed = subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    return completed.stdout if capture else ""


def load_remote_manifest(remote_root: str, package_id: str) -> dict:
    manifest_path = f"{remote_root}/manifests/{package_id}/manifest.8dadi.json"
    raw = run_rclone("cat", manifest_path, capture=True)
    manifest = json.loads(raw)
    if manifest.get("schema") != SCHEMA:
        raise ValueError("清單 schema 不是正典 2.3")
    if manifest.get("package_id") != package_id:
        raise ValueError("清單 package_id 與要求座標不一致")
    authority = manifest.get("D8_authority", {})
    if authority.get("cloud_role") != "MATERIAL_ONLY":
        raise ValueError("雲端材料錯誤宣稱權威")
    if authority.get("runtime_decider") != "TOTAL_FIELD":
        raise ValueError("缺少總場執行裁決界線")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("清單沒有可實體化材料")
    return manifest


def materialize(remote_root: str, package_id: str, local_root: Path, receipt_root: Path) -> dict:
    manifest = load_remote_manifest(remote_root, package_id)
    package_root = local_root / package_id
    package_root.mkdir(parents=True, exist_ok=True)
    receipt_root.mkdir(parents=True, exist_ok=True)
    changed: list[dict] = []
    reused: list[dict] = []
    expected: set[str] = set()

    for item in manifest["files"]:
        relative = safe_relative(str(item["path"]))
        expected_hash = str(item["sha256"]).lower()
        expected_size = int(item["size"])
        expected.add(relative.as_posix())
        destination = package_root.joinpath(*relative.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.is_file() and destination.stat().st_size == expected_size:
            actual_hash = sha256_file(destination)
            if actual_hash == expected_hash:
                reused.append({"path": relative.as_posix(), "sha256": actual_hash})
                continue

        with tempfile.NamedTemporaryFile(
            prefix=f".{destination.name}.", dir=destination.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
        try:
            chunks = item.get("chunks")
            if chunks:
                with temporary.open("wb") as assembled:
                    for chunk in chunks:
                        chunk_relative = safe_relative(str(chunk["path"]))
                        with tempfile.NamedTemporaryFile(
                            prefix=".8dadi-chunk.", dir=destination.parent, delete=False
                        ) as chunk_handle:
                            chunk_temporary = Path(chunk_handle.name)
                        try:
                            source = (
                                f"{remote_root}/raw/{package_id}/{chunk_relative.as_posix()}"
                            )
                            run_rclone("copyto", source, str(chunk_temporary), "--immutable")
                            chunk_size = chunk_temporary.stat().st_size
                            chunk_hash = sha256_file(chunk_temporary)
                            if chunk_size != int(chunk["size"]) or chunk_hash != str(chunk["sha256"]).lower():
                                raise ValueError(f"材料分片驗證失敗: {chunk_relative.as_posix()}")
                            with chunk_temporary.open("rb") as chunk_source:
                                for block in iter(lambda: chunk_source.read(1024 * 1024), b""):
                                    assembled.write(block)
                        finally:
                            chunk_temporary.unlink(missing_ok=True)
            else:
                source = f"{remote_root}/raw/{package_id}/{relative.as_posix()}"
                run_rclone("copyto", source, str(temporary), "--immutable")
            actual_size = temporary.stat().st_size
            actual_hash = sha256_file(temporary)
            if actual_size != expected_size or actual_hash != expected_hash:
                raise ValueError(f"材料驗證失敗: {relative.as_posix()}")
            os.replace(temporary, destination)
            changed.append({"path": relative.as_posix(), "sha256": actual_hash})
        finally:
            temporary.unlink(missing_ok=True)

    expected.add("manifest.8dadi.json")
    unreferenced = sorted(
        path.relative_to(package_root).as_posix()
        for path in package_root.rglob("*")
        if path.is_file() and path.relative_to(package_root).as_posix() not in expected
    )
    local_manifest = package_root / "manifest.8dadi.json"
    local_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    receipt = {
        "schema": "w7tp.8dadi.materialization-receipt/2.3",
        "timestamp": now_token(),
        "package_id": package_id,
        "decision": "PASS_MATERIALIZED" if not unreferenced else "HOLD_UNREFERENCED_LOCAL_FILES",
        "changed": changed,
        "reused": reused,
        "unreferenced_not_deleted": unreferenced,
        "D6_transfer": "MANIFEST_DRIVEN_MISSING_OR_MISMATCHED_ONLY",
        "D8_authority": "TOTAL_FIELD_REOBSERVATION_REQUIRED",
    }
    receipt_path = receipt_root / f"{receipt['timestamp']}_{package_id}.json"
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        run_rclone(
            "copyto",
            str(receipt_path),
            f"{remote_root}/reports/{package_id}/{receipt_path.name}",
            "--immutable",
        )
        receipt["cloud_receipt_state"] = "PASS_RCLONE_WRITTEN"
    except subprocess.CalledProcessError:
        receipt["cloud_receipt_state"] = "HOLD_EXTERNAL_CONNECTOR_WRITE_REQUIRED"
        receipt_path.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="8DADI 2.3 雲端材料實體化器")
    parser.add_argument("package_id")
    parser.add_argument("--remote-root", default=DEFAULT_REMOTE)
    parser.add_argument("--local-root", type=Path, default=DEFAULT_LOCAL_ROOT)
    parser.add_argument("--receipt-root", type=Path, default=DEFAULT_RECEIPT_ROOT)
    args = parser.parse_args()
    receipt = materialize(args.remote_root, args.package_id, args.local_root, args.receipt_root)
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if receipt["decision"] == "PASS_MATERIALIZED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
