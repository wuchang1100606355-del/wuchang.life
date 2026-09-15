#!/usr/bin/env python3
"""Verify the candidate manifest against exact local Git objects without mutation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


RUN_DIR = Path(__file__).resolve().parent
MANIFEST = RUN_DIR / "SOURCE_BINDING_MANIFEST.json"
ROOT = Path(__file__).resolve().parents[4]


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors: list[str] = []
    source = manifest["source_coordinate"]
    ref = source["remote_tracking_ref"]
    if git("rev-parse", ref).decode().strip() != source["commit"]:
        errors.append("SOURCE_REF_COMMIT_MISMATCH")
    if git("rev-parse", f"{ref}^{{tree}}").decode().strip() != source["tree"]:
        errors.append("SOURCE_REF_TREE_MISMATCH")

    for skill in manifest["skills"]:
        skill_id = skill["skill_id"]
        source_path = skill["source_path"]
        if git("rev-parse", f"{ref}:{source_path}").decode().strip() != skill["source_tree_git_oid"]:
            errors.append(f"SOURCE_TREE_MISMATCH:{skill_id}")
        raw = git("ls-tree", "-r", "-z", ref, "--", source_path)
        observed = []
        for record in raw.rstrip(b"\0").split(b"\0") if raw else []:
            meta, full_path = record.split(b"\t", 1)
            _, object_type, oid = meta.decode().split()
            if object_type != "blob":
                errors.append(f"NON_BLOB_SOURCE:{skill_id}:{full_path.decode()}")
                continue
            data = git("cat-file", "blob", oid)
            observed.append({
                "path": full_path.decode()[len(source_path) + 1:],
                "git_blob_oid": oid,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            })
        if observed != skill["files"]:
            errors.append(f"FILE_MANIFEST_MISMATCH:{skill_id}")
        archive = git("archive", "--format=tar", ref, source_path)
        if hashlib.sha256(archive).hexdigest() != skill["source_archive_sha256"]:
            errors.append(f"SOURCE_ARCHIVE_HASH_MISMATCH:{skill_id}")

    result = {
        "state": "PASS_SOURCE_HASH_BINDING" if not errors else "FAIL_SOURCE_HASH_BINDING",
        "errors": errors,
        "run_id": manifest["run_id"],
        "source_commit": source["commit"],
        "skill_count": len(manifest["skills"]),
        "v2_3_binding_state": "HOLD_V2_3_SOURCE_BINDING_UNESTABLISHED",
        "authority_granted": False,
        "mutation_performed": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
