#!/usr/bin/env python3
"""Build a versioned GT mesh release from the live repository without Git runtime dependency."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path


CANONICAL_REL = Path(
    "docs/total_field/"
    "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1.md"
)
CANONICAL_SHA256 = "e960d14254df083ffed711e2c44b76fc2075541716881bc3d1034cb26cffbaba"
SCHEMA_REL = Path(
    "schemas/versioned/"
    "w7tp_8d_multipurpose_packet_canonical_v2_1.schema."
    "cf3df7380e70d0b4bb21635ddc6f1f097713cf94fbf8428966713c949ff1d135.json"
)
SCHEMA_SHA256 = "cf3df7380e70d0b4bb21635ddc6f1f097713cf94fbf8428966713c949ff1d135"
CORE_FILES = (
    Path("w7tp_runtime/gt_packet_v2.py"),
    Path("w7tp_runtime/state_field/__init__.py"),
    Path("w7tp_runtime/state_field/canonical.py"),
    Path("w7tp_runtime/state_field/object_packet_store.py"),
)
SERVICE_ENTRIES = (
    "w7tp_gt_mesh",
    "total_field_control",
    "tests",
    "v3_candidate",
    "deploy",
    "windows_drive_projector",
    "README.md",
    "pyproject.toml",
    "config.example.json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def copy_entry(source: Path, target: Path) -> None:
    if source.is_dir():
        shutil.copytree(
            source,
            target,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
    elif source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    else:
        raise RuntimeError(f"HOLD_RELEASE_SOURCE_MISSING:{source}")


def verify_pinned(path: Path, expected: str, reason: str) -> None:
    if not path.is_file() or sha256_file(path) != expected:
        raise RuntimeError(reason)


def build(repo_root: Path, service_root: Path, output: Path, source_head: str) -> dict[str, object]:
    repo_root = repo_root.resolve()
    service_root = service_root.resolve()
    output = output.resolve()
    if output.exists():
        raise RuntimeError("HOLD_RELEASE_OUTPUT_ALREADY_EXISTS")
    if not service_root.is_dir() or not repo_root.is_dir():
        raise RuntimeError("HOLD_RELEASE_ROOT_MISSING")

    verify_pinned(repo_root / CANONICAL_REL, CANONICAL_SHA256, "HOLD_CANONICAL_SHA_MISMATCH")
    verify_pinned(repo_root / SCHEMA_REL, SCHEMA_SHA256, "HOLD_SCHEMA_SHA_MISMATCH")

    output.mkdir(parents=True)
    for name in SERVICE_ENTRIES:
        copy_entry(service_root / name, output / name)

    runtime_root = output / "w7tp_runtime"
    runtime_root.mkdir()
    (runtime_root / "__init__.py").write_text(
        '"""Exact deployment subset required by the W7TP V2.1 GT mesh."""\n',
        encoding="utf-8",
    )
    for relative in CORE_FILES:
        copy_entry(repo_root / relative, output / relative)
    copy_entry(
        repo_root / "w7tp_runtime/state_field/controlled_experiment_v1",
        output / "w7tp_runtime/state_field/controlled_experiment_v1",
    )
    copy_entry(repo_root / CANONICAL_REL, output / CANONICAL_REL)
    copy_entry(repo_root / SCHEMA_REL, output / SCHEMA_REL)

    summary = "\n".join(
        (
            "意圖：將已驗證的 W7TP V2.1 生成式傳輸、動態索引與總場控制候選封裝成可部署版本。",
            "總場理由：總場仍是唯一權威，8D ADI 只負責主要決策；版本包、Git、節點與傳輸均不會自行取得權威。",
            "節點與容器：此版本可供 MSI、taiji01、taiji02、taiji03 與已登錄雲端節點安裝，實際控制仍須逐節點驗證。",
            "結果：核心依賴、固定正典、機器 schema、服務設定與人類摘要已放入同一個不可混用的版本目錄。",
            "風險與未知：這是候選版本；未通過現場 authority、scope、節點快照與收據閉環前，不得宣稱正式控制已生效。",
        )
    )
    (output / "HUMAN_RELEASE_SUMMARY_ZH_TW.txt").write_text(summary + "\n", encoding="utf-8")

    files = {
        path.relative_to(output).as_posix(): sha256_file(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "RELEASE_MANIFEST.json"
    }
    manifest: dict[str, object] = {
        "schema_id": "W7TP_GT_MESH_RELEASE_BUNDLE_V21",
        "state": "VERIFIED_CANDIDATE_RELEASE_NOT_AUTHORITY",
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_head": source_head,
        "source_head_role": "D4_EVIDENCE_ONLY_NOT_AUTHORITY",
        "canonical_sha256": CANONICAL_SHA256,
        "schema_sha256": SCHEMA_SHA256,
        "authority_ref": "authority:TOTAL_FIELD",
        "authority_node_ref": "node:taiji01",
        "primary_decision_engine": "8D_ADI",
        "primary_decision_engine_role": "NOT_AUTHORITY",
        "file_sha256": files,
        "human_summary_zh_tw": summary,
    }
    (output / "RELEASE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--service-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-head", required=True)
    args = parser.parse_args(argv)
    try:
        manifest = build(args.repo_root, args.service_root, args.output, args.source_head)
    except (OSError, RuntimeError) as exc:
        print(json.dumps({"state": "HOLD", "reason": str(exc)}, ensure_ascii=False))
        print("結果：版本包未建立；已保留原始檔案，請先修正上列唯一缺失條件。")
        return 2
    print(json.dumps({"state": manifest["state"], "file_count": len(manifest["file_sha256"])}, ensure_ascii=False))
    print(manifest["human_summary_zh_tw"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
