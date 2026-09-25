#!/usr/bin/env python3
"""Produce a read-only Git source coordinate for capability assimilation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def git(repo: Path, *args: str, binary: bool = False):
    cmd = ["git", "-C", str(repo), *args]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        return None
    return result.stdout if binary else result.stdout.decode("utf-8", "replace").strip()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def detect_license_files(repo: Path) -> list[str]:
    candidates = []
    for child in repo.iterdir():
        if not child.is_file():
            continue
        name = child.name.upper()
        if name.startswith(("LICENSE", "LICENCE", "COPYING", "NOTICE")):
            candidates.append(child.name)
    return sorted(candidates)


def build_manifest(repo: Path, archive_hash: bool = True) -> dict:
    if not repo.is_dir():
        raise ValueError(f"not a directory: {repo}")
    inside = git(repo, "rev-parse", "--is-inside-work-tree")
    if inside != "true":
        raise ValueError(f"not a Git working tree: {repo}")

    status = git(repo, "status", "--porcelain=v1") or ""
    commit = git(repo, "rev-parse", "HEAD")
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    branch = git(repo, "branch", "--show-current") or None
    remote = git(repo, "remote", "get-url", "origin")
    tag = git(repo, "describe", "--tags", "--exact-match", "HEAD")

    snapshot = None
    if archive_hash:
        archive = git(repo, "archive", "--format=tar", "HEAD", binary=True)
        if archive is not None:
            snapshot = sha256(archive)

    return {
        "source_repository": str(repo.resolve()),
        "source_remote": remote,
        "source_branch": branch,
        "source_tag": tag,
        "source_commit": commit,
        "source_tree": tree,
        "source_snapshot_sha256": snapshot,
        "snapshot_hash_method": "SHA256(git archive HEAD tar bytes)" if snapshot else None,
        "worktree_dirty": bool(status),
        "dirty_item_count": len(status.splitlines()) if status else 0,
        "status_sha256": sha256(status.encode("utf-8")),
        "license_files": detect_license_files(repo),
        "project_code_executed": False,
        "repository_mutated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Path to an existing Git checkout")
    parser.add_argument("--no-archive-hash", action="store_true", help="Skip git archive SHA-256")
    args = parser.parse_args()

    try:
        manifest = build_manifest(Path(args.repo), archive_hash=not args.no_archive_hash)
    except Exception as exc:  # concise CLI error boundary
        print(json.dumps({"state": "ERROR", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
