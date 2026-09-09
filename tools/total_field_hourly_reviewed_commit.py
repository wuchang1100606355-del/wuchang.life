#!/usr/bin/env python3
"""Commit only the exact dirty snapshot already reviewed by Total Field rules."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field_dynamic_context import build_dynamic_context
from tools.total_field_mandatory_application_gate import (
    PASS_STATE,
    REVIEW_SCHEMA,
    REVIEW_STATE,
    MandatoryApplicationRejected,
    _canonical_json,
    _coordinates,
    _git,
    _sha256,
    change_bindings,
    scan_operation,
)

PASS_COMMIT = "PASS_HOURLY_TOTAL_FIELD_REVIEWED_COMMIT"
PASS_NOOP = "PASS_HOURLY_TOTAL_FIELD_NOOP"
HOLD_COMMIT = "HOLD_HOURLY_TOTAL_FIELD_REVIEWED_COMMIT"
CONFLICT_COMMIT = "CONFLICT_HOURLY_COMMIT_CREATED_POSTCHECK_FAILED"


def _write_append_only(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_json(payload) + b"\n"
    if path.exists():
        if path.is_symlink() or path.read_bytes() != encoded:
            raise MandatoryApplicationRejected("HOURLY_RECEIPT_COLLISION")
        return
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink(missing_ok=True)
        finally:
            raise


def _read_review(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise MandatoryApplicationRejected("REVIEW_RECEIPT_INVALID")
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MandatoryApplicationRejected("REVIEW_RECEIPT_INVALID") from exc
    if (
        not isinstance(packet, dict)
        or packet.get("schema_id") != REVIEW_SCHEMA
        or packet.get("state") != REVIEW_STATE
        or packet.get("review_registered") is not True
        or packet.get("effect_authority") is not False
    ):
        raise MandatoryApplicationRejected("REVIEW_RECEIPT_NOT_PASSED")
    supplied = packet.get("review_sha256")
    without_sha = {key: value for key, value in packet.items() if key != "review_sha256"}
    if supplied != _sha256(_canonical_json(without_sha)) or path.stem != supplied:
        raise MandatoryApplicationRejected("REVIEW_RECEIPT_HASH_DRIFT")
    return packet


def _matching_review(root: Path, current: list[dict[str, Any]]) -> dict[str, Any]:
    receipt_root = root / "runtime/total_field/rule_application_reviews/pending"
    if not receipt_root.is_dir() or receipt_root.is_symlink():
        raise MandatoryApplicationRejected("REVIEW_RECEIPT_REQUIRED")
    coordinates = _coordinates(root)
    matches: list[dict[str, Any]] = []
    for path in sorted(receipt_root.glob("*.json")):
        try:
            packet = _read_review(path)
        except MandatoryApplicationRejected:
            continue
        if (
            packet.get("branch") == coordinates["branch"]
            and packet.get("base_head") == coordinates["head"]
            and packet.get("base_tree") == coordinates["tree"]
            and packet.get("change_bindings") == current
        ):
            matches.append(packet)
    if len(matches) != 1:
        raise MandatoryApplicationRejected(
            "REVIEW_RECEIPT_REQUIRED" if not matches else "MULTIPLE_REVIEW_RECEIPTS_MATCH"
        )
    return matches[0]


def _run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise MandatoryApplicationRejected("REVIEWED_COMMIT_GIT_EFFECT_FAILED")
    return result.stdout.strip()


def _commit_bindings(root: Path, commit: str, paths: list[str]) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    for relative in paths:
        tree = subprocess.run(
            ["git", "-C", str(root), "ls-tree", "-z", commit, "--", relative],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if tree.returncode != 0:
            raise MandatoryApplicationRejected("COMMITTED_OBJECT_UNAVAILABLE")
        if not tree.stdout:
            bindings.append({"path": relative, "state": "DELETED", "sha256": None, "mode": None})
            continue
        try:
            metadata, returned_path = tree.stdout.rstrip(b"\0").split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split(" ", 2)
            decoded_path = returned_path.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise MandatoryApplicationRejected("COMMITTED_OBJECT_INVALID") from exc
        if decoded_path != relative or object_type != "blob" or mode not in {"100644", "100755"}:
            raise MandatoryApplicationRejected("COMMITTED_OBJECT_TYPE_UNSUPPORTED")
        blob = subprocess.run(
            ["git", "-C", str(root), "cat-file", "blob", object_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if blob.returncode != 0:
            raise MandatoryApplicationRejected("COMMITTED_OBJECT_UNAVAILABLE")
        bindings.append(
            {
                "path": relative,
                "state": "PRESENT",
                "sha256": _sha256(blob.stdout),
                "mode": "0o755" if mode == "100755" else "0o644",
            }
        )
    return bindings


def hourly_reviewed_commit(
    repo_root: str | Path,
    *,
    context_builder: Callable[..., Mapping[str, Any]] = build_dynamic_context,
    now: datetime | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    observed_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    created_commit: str | None = None
    try:
        current = change_bindings(root)
        coordinates = _coordinates(root)
        if not current:
            hour = observed_at.strftime("%Y%m%dT%HZ")
            packet = {
                "schema_id": "W7TP_8DADI_HOURLY_COMMIT_NOOP_V1",
                "state": PASS_NOOP,
                "hour_utc": hour,
                "coordinates": coordinates,
                "changed_path_count": 0,
                "commit_created": False,
                "push_authorized": False,
                "deploy_authorized": False,
            }
            _write_append_only(
                root / f"runtime/total_field/rule_application_reviews/hourly_noop/{hour}.json",
                packet,
            )
            return packet
        review = _matching_review(root, current)
        authority = {
            "state": "PASS_TOTAL_FIELD_RULE_APPLICATION_REVIEW_RECEIPT",
            "authority_verified": True,
            "scope": ["REVIEWED_CHANGE_SET_ONLY"],
            "review_sha256": review["review_sha256"],
        }
        gate = scan_operation(
            repo_root=root,
            operation="HOURLY_REVIEWED_COMMIT",
            actor_class="SYSTEM",
            query=review["work_target_query"],
            expected_branch=review["branch"],
            expected_head=review["base_head"],
            expected_tree=review["base_tree"],
            expected_work_target_sha256=review["work_target_sha256"],
            context_builder=context_builder,
            effect_authority=authority,
        )
        if gate.get("state") != PASS_STATE or gate.get("operation_authorized") is not True:
            raise MandatoryApplicationRejected(str(gate.get("reason") or gate.get("state")))
        if (
            gate.get("change_bindings") != review.get("change_bindings")
            or gate.get("local_rules_sha256") != review.get("local_rules_sha256")
            or gate.get("dynamic_context_sha256") != review.get("dynamic_context_sha256")
        ):
            raise MandatoryApplicationRejected("REVIEW_BINDING_DRIFT")
        reviewed_paths = [item["path"] for item in current]
        _run_git(root, "add", "--", *reviewed_paths)
        if change_bindings(root) != current:
            raise MandatoryApplicationRejected("CHANGE_SET_DRIFT_DURING_STAGE")
        staged = [line for line in _git(root, "diff", "--cached", "--name-only", "--no-renames", "--").splitlines() if line]
        if sorted(staged) != reviewed_paths:
            raise MandatoryApplicationRejected("STAGED_PATH_SET_DRIFT")
        message = f"chore: hourly reviewed change {review['review_sha256'][:12]}"
        _run_git(root, "commit", "-m", message)
        commit = _git(root, "rev-parse", "HEAD")
        created_commit = commit
        if _git(root, "rev-parse", "HEAD^") != review["base_head"]:
            raise MandatoryApplicationRejected("COMMIT_PARENT_DRIFT")
        committed_paths = sorted(
            line
            for line in _git(root, "diff", "--name-only", "--no-renames", "HEAD^", "HEAD", "--").splitlines()
            if line
        )
        if committed_paths != reviewed_paths:
            raise MandatoryApplicationRejected("COMMITTED_PATH_SET_DRIFT")
        if _commit_bindings(root, commit, reviewed_paths) != current:
            raise MandatoryApplicationRejected("COMMITTED_CONTENT_BINDING_DRIFT")
        if change_bindings(root):
            raise MandatoryApplicationRejected("POST_COMMIT_WORKTREE_DRIFT")
        outcome = {
            "schema_id": "W7TP_8DADI_HOURLY_REVIEWED_COMMIT_RECEIPT_V1",
            "state": PASS_COMMIT,
            "review_sha256": review["review_sha256"],
            "base_head": review["base_head"],
            "commit": commit,
            "branch": review["branch"],
            "changed_paths_sha256": review["changed_paths_sha256"],
            "commit_created": True,
            "push_authorized": False,
            "deploy_authorized": False,
        }
        _write_append_only(
            root
            / "runtime/total_field/rule_application_reviews/commit_outcomes"
            / review["review_sha256"]
            / f"{commit}.json",
            outcome,
        )
        return outcome
    except (MandatoryApplicationRejected, OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "state": CONFLICT_COMMIT if created_commit else HOLD_COMMIT,
            "reason": str(exc),
            "commit_created": bool(created_commit),
            "commit": created_commit,
            "push_authorized": False,
            "deploy_authorized": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Commit only a Total Field reviewed exact change set.")
    parser.add_argument("--repo-root", required=True)
    args = parser.parse_args()
    result = hourly_reviewed_commit(args.repo_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("state") in {PASS_COMMIT, PASS_NOOP} else 1


if __name__ == "__main__":
    raise SystemExit(main())
