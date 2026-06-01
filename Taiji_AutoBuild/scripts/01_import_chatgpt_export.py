#!/usr/bin/env python3
"""Create a local manifest for a ChatGPT export without printing conversation text.

Default behavior is file-level inventory only. This script does not call any
external API and does not send data to cloud services.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SENSITIVE_HINTS = ("conversation", "message", "content", "mapping", "text")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_for_path(path: Path) -> dict[str, Any]:
    stat = path.stat()
    manifest: dict[str, Any] = {
        "path": str(path),
        "name": path.name,
        "size_bytes": stat.st_size,
        "sha256": sha256_file(path),
        "created_manifest_at": datetime.now(timezone.utc).isoformat(),
        "mode": "metadata_only_no_conversation_text",
    }
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            entries = []
            for info in archive.infolist():
                lower = info.filename.lower()
                entries.append(
                    {
                        "name": info.filename,
                        "size_bytes": info.file_size,
                        "sha256_available": False,
                        "sensitive_text_possible": any(hint in lower for hint in SENSITIVE_HINTS),
                    }
                )
            manifest["archive_type"] = "zip"
            manifest["entries"] = entries
            manifest["entry_count"] = len(entries)
    elif path.suffix.lower() == ".json":
        manifest["archive_type"] = "json"
        manifest["content_not_printed"] = True
    elif path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
        manifest["archive_type"] = "csv"
        manifest["header"] = header
    else:
        manifest["archive_type"] = "unknown"
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a safe local manifest for an export file.")
    parser.add_argument("source", type=Path, help="Path to the local export file.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("Taiji_Governance/baseline/chatgpt_export_manifest.json"),
        help="Manifest output path. Contains metadata only.",
    )
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    if not source.exists():
        print(f"missing source: {source}", file=sys.stderr)
        return 2

    manifest = manifest_for_path(source)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"metadata_manifest_written={output}")
    print("conversation_text_printed=false")
    print("external_api_called=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
