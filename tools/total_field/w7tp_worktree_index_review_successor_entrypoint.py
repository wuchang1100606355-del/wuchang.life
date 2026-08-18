#!/usr/bin/env python3
"""Candidate-only exact Git-index binding validator for native Total Field review.

This successor never emits a formal decision or receipt.  It validates an exact
request, verifies repository-native state twice, and delegates only candidate
analysis to the existing deterministic Total Field decision engine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field.w7tp_candidate_fine_grain_reviewer import analyze_candidate


VERSION = "w7tp-worktree-index-review-successor/1.0"
REQUEST_SCHEMA = ROOT / "schemas/field/w7tp_total_field_worktree_index_review_request_v1.schema.json"
RECEIPT_SCHEMA = ROOT / "schemas/field/w7tp_total_field_worktree_index_review_receipt_v1.schema.json"


class BindingError(ValueError):
    def __init__(self, code: str, path: str = "$") -> None:
        self.code = code
        self.path = path
        super().__init__(f"{code}:{path}")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BindingError("HOLD_JSON_INVALID", str(path)) from exc


def git(repo: Path, *args: str, binary: bool = False) -> bytes | str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True
    )
    return completed.stdout if binary else completed.stdout.decode("utf-8").strip()


def safe_ref(repo: Path, reference: str, expected: str, path: str) -> None:
    candidate = Path(reference)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise BindingError("HOLD_REFERENCE_PATH_INVALID", path)
    target = (repo / candidate).resolve()
    try:
        target.relative_to(repo.resolve())
    except ValueError as exc:
        raise BindingError("HOLD_REFERENCE_PATH_ESCAPE", path) from exc
    if not target.is_file() or digest_file(target) != expected:
        raise BindingError("HOLD_REFERENCE_HASH_MISMATCH", path)


def self_hash(value: dict[str, Any], field: str) -> str:
    candidate = dict(value)
    candidate.pop(field, None)
    return digest_bytes(canonical_bytes(candidate))


def manifest_hash(manifest: dict[str, Any]) -> str:
    return self_hash(manifest, "manifest_self_sha256")


def envelope_hash(request: dict[str, Any]) -> str:
    candidate = dict(request)
    candidate.pop("request_self_sha256", None)
    candidate.pop("envelope_self_sha256", None)
    return digest_bytes(canonical_bytes(candidate))


def validate_self_hashes(request: dict[str, Any]) -> None:
    manifest = request["index_manifest"]
    if manifest_hash(manifest) != manifest["manifest_self_sha256"]:
        raise BindingError("HOLD_INDEX_MANIFEST_SELF_HASH_MISMATCH", "$.index_manifest.manifest_self_sha256")
    if self_hash(request, "request_self_sha256") != request["request_self_sha256"]:
        raise BindingError("HOLD_REQUEST_SELF_HASH_MISMATCH", "$.request_self_sha256")
    if envelope_hash(request) != request["envelope_self_sha256"]:
        raise BindingError("HOLD_ENVELOPE_SELF_HASH_MISMATCH", "$.envelope_self_sha256")


def index_entries(repo: Path) -> list[dict[str, Any]]:
    raw = git(repo, "ls-files", "--stage", "-z", binary=True)
    assert isinstance(raw, bytes)
    entries: list[dict[str, Any]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        header, raw_path = record.split(b"\t", 1)
        mode, oid, stage_text = header.decode("ascii").split(" ")
        stage = int(stage_text)
        if stage != 0:
            raise BindingError("HOLD_UNMERGED_INDEX_ENTRY", raw_path.decode("utf-8", "surrogateescape"))
        blob = git(repo, "cat-file", "blob", oid, binary=True)
        assert isinstance(blob, bytes)
        entries.append(
            {
                "path": raw_path.decode("utf-8", "surrogateescape"),
                "mode": mode,
                "stage": stage,
                "blob_oid": oid,
                "staged_bytes_sha256": digest_bytes(blob),
            }
        )
    return entries


def staged_delta_entries(repo: Path) -> list[dict[str, Any]]:
    staged_paths = git(repo, "diff", "--cached", "--name-only", "-z", "--diff-filter=ACDMRTUXB", binary=True)
    assert isinstance(staged_paths, bytes)
    wanted = {item.decode("utf-8", "surrogateescape") for item in staged_paths.split(b"\0") if item}
    return [entry for entry in index_entries(repo) if entry["path"] in wanted]


def find_queue_entry(repo: Path, binding: dict[str, Any]) -> dict[str, Any]:
    queue_path = repo / binding["queue_path"]
    queue = load_json(queue_path)
    if not isinstance(queue, list):
        raise BindingError("HOLD_QUEUE_INVALID", "$.queue_binding.queue_path")
    matches = [item for item in queue if isinstance(item, dict) and item.get("entry_sha256") == binding["queue_entry_sha256"]]
    if len(matches) != 1:
        raise BindingError("HOLD_QUEUE_ENTRY_NOT_UNIQUE", "$.queue_binding.queue_entry_sha256")
    entry = matches[0]
    if entry.get("candidate_content_sha256") != binding["candidate_content_sha256"]:
        raise BindingError("HOLD_CANDIDATE_HASH_MISMATCH", "$.queue_binding.candidate_content_sha256")
    return entry


def verify_repository_state(request: dict[str, Any], repo: Path) -> list[dict[str, Any]]:
    repository = request["repository"]
    if repo.resolve().as_posix() != repository["path"]:
        raise BindingError("HOLD_REPOSITORY_PATH_MISMATCH", "$.repository.path")
    checks = {
        "object_format": git(repo, "rev-parse", "--show-object-format"),
        "branch": git(repo, "branch", "--show-current"),
        "base_head": git(repo, "rev-parse", "HEAD"),
        "upstream_sha": git(repo, "rev-parse", "@{upstream}"),
    }
    for key, actual in checks.items():
        if repository[key] != actual:
            raise BindingError(f"HOLD_REPOSITORY_{key.upper()}_MISMATCH", f"$.repository.{key}")
    safe_ref(repo, repository["identity_reference"], repository["identity_sha256"], "$.repository.identity_reference")
    actual_entries = staged_delta_entries(repo)
    manifest = request["index_manifest"]
    if manifest["staged_count"] != len(actual_entries) or manifest["entries"] != actual_entries:
        raise BindingError("HOLD_GIT_INDEX_MANIFEST_MISMATCH", "$.index_manifest")
    if any(path in {entry["path"] for entry in actual_entries} for path in manifest["excluded_files"]):
        raise BindingError("HOLD_EXCLUDED_FILE_STAGED", "$.index_manifest.excluded_files")
    return actual_entries


def validate_candidate(
    request_path: Path,
    repo: Path,
    now: datetime | None = None,
    replay_root: Path | None = None,
) -> dict[str, Any]:
    schema = load_json(REQUEST_SCHEMA)
    Draft202012Validator.check_schema(schema)
    request = load_json(request_path)
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(request), key=lambda item: list(item.absolute_path))
    if errors:
        raise BindingError("HOLD_REQUEST_SCHEMA_INVALID", "$" + "".join(f"[{part!r}]" for part in errors[0].absolute_path))
    validate_self_hashes(request)
    expires = datetime.fromisoformat(request["single_use"]["expires_at"].replace("Z", "+00:00"))
    if (now or datetime.now(timezone.utc)).astimezone(timezone.utc) >= expires:
        raise BindingError("HOLD_REQUEST_EXPIRED", "$.single_use.expires_at")
    before = verify_repository_state(request, repo)
    for group, binding in request["authority_binding"].items():
        safe_ref(repo, binding["reference"], binding["sha256"], f"$.authority_binding.{group}")
    logical = request["logical_time"]
    safe_ref(repo, logical["reference"], logical["reference_sha256"], "$.logical_time.reference")
    single = request["single_use"]
    safe_ref(repo, single["nonce_reference"], single["nonce_sha256"], "$.single_use.nonce_reference")
    if replay_root is not None and replay_root.is_dir():
        for receipt_path in replay_root.rglob("*.json"):
            try:
                receipt = load_json(receipt_path)
            except BindingError:
                continue
            if isinstance(receipt, dict) and receipt.get("single_use_nonce_sha256") == single["nonce_sha256"]:
                raise BindingError("HOLD_SINGLE_USE_NONCE_REPLAY", str(receipt_path))
    queue_entry = find_queue_entry(repo, request["queue_binding"])
    _parsed, units = analyze_candidate(queue_entry.get("candidate_packet"), "$.queue_entry.candidate_packet")
    after = verify_repository_state(request, repo)
    if before != after:
        raise BindingError("HOLD_INDEX_CHANGED_DURING_REVIEW", "$.index_manifest")
    return {
        "state": "CANDIDATE_VALIDATED_FOR_NATIVE_DECISION_ONLY",
        "reviewer_version": VERSION,
        "formal_decision": None,
        "receipt_created": False,
        "request_sha256": digest_file(request_path),
        "index_manifest_sha256": manifest_hash(request["index_manifest"]),
        "queue_entry_sha256": request["queue_binding"]["queue_entry_sha256"],
        "candidate_content_sha256": request["queue_binding"]["candidate_content_sha256"],
        "decision_engine_delegation": "CANDIDATE_ANALYSIS_ONLY_NO_AUTHORITY",
        "decision_engine_unit_count": len(units),
    }


def validate_schemas() -> dict[str, Any]:
    for path in (REQUEST_SCHEMA, RECEIPT_SCHEMA):
        Draft202012Validator.check_schema(load_json(path))
    return {"state": "CANDIDATE_SCHEMAS_VALID", "formal_decision": None, "receipt_created": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate-schemas")
    validate = commands.add_parser("validate-candidate")
    validate.add_argument("--request-path", type=Path, required=True)
    validate.add_argument("--repo-root", type=Path, required=True)
    validate.add_argument("--replay-root", type=Path)
    args = parser.parse_args(argv)
    try:
        result = validate_schemas() if args.command == "validate-schemas" else validate_candidate(
            args.request_path, args.repo_root, replay_root=args.replay_root
        )
    except (BindingError, subprocess.CalledProcessError) as exc:
        code = exc.code if isinstance(exc, BindingError) else "HOLD_GIT_COMMAND_FAILED"
        path = exc.path if isinstance(exc, BindingError) else "$"
        print(json.dumps({"state": "HOLD_NATIVE_WORKTREE_REVIEW_SUCCESSOR", "reason_code": code, "error_path": path, "formal_decision": None, "receipt_created": False}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
