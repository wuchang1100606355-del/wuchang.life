#!/usr/bin/env python3
"""Fail-closed Total Field successor-rebind review contract candidate.

Until an active, hash-bound Total Field authority pointer approves this
contract, this module may emit test-only decisions and receipts or HOLD.  It
never modifies the reviewed candidate, source, Canonical, Pointer, Git, DB, or
runtime state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator


REVIEWER_VERSION = "w7tp-successor-rebind-reviewer/1.0-candidate"
REQUEST_SCHEMA_VERSION = "W7TP-TOTAL-FIELD-SUCCESSOR-REBIND-REVIEW-REQUEST/1.0"
DECISION_SCHEMA_VERSION = "W7TP-TOTAL-FIELD-SUCCESSOR-REBIND-DECISION/1.0"
RECEIPT_SCHEMA_VERSION = "W7TP-TOTAL-FIELD-SUCCESSOR-REBIND-RECEIPT/1.0"
REQUEST_SELF_HASH_ALGORITHM = "SHA256_CANONICAL_JSON_EXCLUDING_REQUEST_SELF_SHA256/1.0"
DECISION_SELF_HASH_ALGORITHM = "SHA256_CANONICAL_JSON_EXCLUDING_DECISION_SHA256/1.0"
RECEIPT_SELF_HASH_ALGORITHM = "SHA256_CANONICAL_JSON_EXCLUDING_RECEIPT_SHA256/1.0"
DECISION_APPROVED = "SUCCESSOR_REBIND_APPROVED"
DECISION_REJECTED = "SUCCESSOR_REBIND_REJECTED"
DECISION_HOLD = "HOLD_SUCCESSOR_REBIND_REVIEW"
CORE_LANDING = "HOLD_PENDING_SEPARATE_AUTHORIZATION"
MAX_REQUEST_TTL_SECONDS = 3600
MAX_CLOCK_SKEW_SECONDS = 60
FORMAL_FOUNDER_EFFECT = "AUTHORIZE_FORMAL_SUCCESSOR_REBIND_REVIEW"
NON_EXECUTION_FIELDS = frozenset(
    {
        "core_write",
        "canonical_change",
        "pointer_change",
        "git_write",
        "db_write",
        "deploy",
        "restart",
        "network_change",
        "formal_decision_creation",
        "formal_seal_creation",
    }
)
FORBIDDEN_FORMAL_ARTIFACTS = frozenset(
    {
        "FORMAL_TOTAL_FIELD_DECISION.json",
        "TOTAL_FIELD_REVIEW_RECEIPT.json",
        "FORMAL_SEAL.json",
        "ACTIVE_AUTHORITY_POINTER.json",
    }
)
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
NONCE = re.compile(r"^nonce:sha256:[0-9a-f]{64}$")


class SuccessorRebindReviewError(ValueError):
    """Stable fail-closed result with a decision and reason code."""

    def __init__(self, decision: str, reason_code: str, path: str = "$") -> None:
        self.decision = decision
        self.reason_code = reason_code
        self.path = path
        super().__init__(f"{decision}:{reason_code}:{path}")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: Any, path: str) -> datetime:
    if not isinstance(value, str):
        raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_DATETIME_REQUIRED", path)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_DATETIME_INVALID", path) from exc
    if parsed.tzinfo is None:
        raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_DATETIME_TIMEZONE_REQUIRED", path)
    return parsed.astimezone(timezone.utc)


def load_object(path: Path, reason: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SuccessorRebindReviewError(DECISION_REJECTED, f"REJECT_{reason}_JSON_INVALID", str(path)) from exc
    if not isinstance(value, dict):
        raise SuccessorRebindReviewError(DECISION_REJECTED, f"REJECT_{reason}_OBJECT_REQUIRED", str(path))
    return value


def safe_repo_path(repo_root: Path, raw_path: Any, path: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_PATH_REQUIRED", path)
    relative = Path(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_PATH_ESCAPE", path)
    resolved_root = repo_root.resolve()
    current = resolved_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_SYMBOLIC_LINK", path)
    resolved = (resolved_root / relative).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_PATH_ESCAPE", path) from exc
    return resolved


def validate_schema(value: dict[str, Any], schema_path: Path, reason: str) -> None:
    schema = load_object(schema_path, f"{reason}_SCHEMA")
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise SuccessorRebindReviewError(DECISION_REJECTED, f"REJECT_{reason}_SCHEMA_INVALID", str(schema_path)) from exc
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda error: list(error.absolute_path))
    if errors:
        location = "$" + "".join(f"[{item}]" if isinstance(item, int) else f".{item}" for item in errors[0].absolute_path)
        raise SuccessorRebindReviewError(DECISION_REJECTED, f"REJECT_{reason}_SCHEMA", location)


def validate_self_hash(value: dict[str, Any], field: str, algorithm_field: str, algorithm: str) -> None:
    expected = value.get(field)
    if value.get(algorithm_field) != algorithm or not isinstance(expected, str) or HEX64.fullmatch(expected) is None:
        raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_SELF_HASH_SCHEMA", f"$.{field}")
    material = dict(value)
    material.pop(field)
    if sha256_bytes(canonical_json_bytes(material)) != expected:
        raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_SELF_HASH_MISMATCH", f"$.{field}")


def git_tracked(repo_root: Path, path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return False
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def git_blob(repo_root: Path, commit: str, path_ref: str) -> bytes:
    if HEX40.fullmatch(commit) is None:
        raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_COMMIT_SCHEMA", "$.commit")
    result = subprocess.run(
        ["git", "show", f"{commit}:{path_ref}"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        raise SuccessorRebindReviewError(DECISION_HOLD, "HOLD_COMMIT_OR_PATH_NOT_EVIDENCED", f"{commit}:{path_ref}")
    return result.stdout


def git_subject(repo_root: Path, commit: str) -> str:
    result = subprocess.run(
        ["git", "show", "-s", "--format=%s", commit],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise SuccessorRebindReviewError(DECISION_HOLD, "HOLD_COMMIT_SUBJECT_NOT_EVIDENCED", commit)
    return result.stdout.rstrip("\n")


def _schema_path(repo_root: Path, filename: str) -> Path:
    return repo_root / "schemas" / "field" / filename


def _check_freshness(request: dict[str, Any], reviewed_at: datetime) -> None:
    created = parse_utc(request["created_at"], "$.created_at")
    expires = parse_utc(request["expires_at"], "$.expires_at")
    if expires <= created or (expires - created).total_seconds() > MAX_REQUEST_TTL_SECONDS:
        raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_REQUEST_TTL", "$.expires_at")
    if created > reviewed_at + timedelta(seconds=MAX_CLOCK_SKEW_SECONDS):
        raise SuccessorRebindReviewError(DECISION_HOLD, "HOLD_REQUEST_NOT_YET_FRESH", "$.created_at")
    if reviewed_at >= expires:
        raise SuccessorRebindReviewError(DECISION_HOLD, "HOLD_REQUEST_EXPIRED", "$.expires_at")


def _validate_authority(pointer: dict[str, Any], *, test_mode: bool) -> bool:
    if pointer.get("node_id") != "taiji01":
        raise SuccessorRebindReviewError(DECISION_HOLD, "HOLD_AUTHORITY_NODE_MISMATCH", "$.authority_pointer.node_id")
    if test_mode:
        if pointer.get("state") not in {"TEST_ONLY", "ACTIVE_TOTAL_FIELD_AUTHORITY"}:
            raise SuccessorRebindReviewError(DECISION_HOLD, "HOLD_AUTHORITY_POINTER_REQUEST_ONLY", "$.authority_pointer.state")
        return False
    required = {
        "state": "ACTIVE_TOTAL_FIELD_AUTHORITY",
        "contract_state": "ACTIVE_FORMAL",
        "formal_decision_authority": True,
        "formal_seal_authority": True,
    }
    for key, expected in required.items():
        if pointer.get(key) != expected:
            raise SuccessorRebindReviewError(DECISION_HOLD, "HOLD_FORMAL_AUTHORITY_POINTER_MISSING", f"$.authority_pointer.{key}")
    return True


def _validate_founder_authorization(authorization: dict[str, Any], *, test_mode: bool) -> None:
    if authorization.get("founder") != "江政隆":
        raise SuccessorRebindReviewError(DECISION_HOLD, "HOLD_FOUNDER_IDENTITY_MISMATCH", "$.founder_authorization.founder")
    if test_mode and authorization.get("state") == "TEST_ONLY":
        return
    if authorization.get("state") != "FOUNDER_AUTHORIZATION_APPROVED" or authorization.get("authorized_effect") != FORMAL_FOUNDER_EFFECT:
        raise SuccessorRebindReviewError(DECISION_HOLD, "HOLD_FOUNDER_FORMAL_REVIEW_AUTHORIZATION_MISSING", "$.founder_authorization")


def _replay_seen(replay_root: Path | None, request: dict[str, Any]) -> bool:
    if replay_root is None or not replay_root.is_dir():
        return False
    domain = request["replay_guard"]["domain"]
    for path in replay_root.rglob("*SUCCESSOR_REBIND_RECEIPT.json"):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if receipt.get("nonce") == request["nonce"] and receipt.get("replay_guard", {}).get("domain") == domain:
            return True
    return False


def _decision_state(decision: str) -> str:
    if decision == DECISION_APPROVED:
        return "PASS_SUCCESSOR_REBIND_REVIEW"
    if decision == DECISION_REJECTED:
        return "REJECT_SUCCESSOR_REBIND_REVIEW"
    return "HOLD_SUCCESSOR_REBIND_REVIEW"


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fail_result(error: SuccessorRebindReviewError) -> dict[str, Any]:
    return {
        "state": _decision_state(error.decision),
        "decision": error.decision,
        "reason_codes": [error.reason_code],
        "error_path": error.path,
        "formal": False,
        "decision_document": None,
        "receipt_document": None,
    }


def review_once(
    *,
    request_path: Path,
    repo_root: Path,
    output_dir: Path | None = None,
    replay_root: Path | None = None,
    now: datetime | None = None,
    test_mode: bool = False,
    source_loader: Callable[[str, str], bytes] | None = None,
    subject_loader: Callable[[str], str] | None = None,
    tracked_checker: Callable[[Path], bool] | None = None,
) -> dict[str, Any]:
    """Review one hash-bound request and emit only test artifacts until approved."""

    repo_root = repo_root.resolve()
    reviewed_at = (now or utc_now()).astimezone(timezone.utc)
    if not test_mode and any(value is not None for value in (source_loader, subject_loader, tracked_checker)):
        return _fail_result(SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_FORMAL_DEPENDENCY_INJECTION"))
    source_loader = source_loader or (lambda commit, path: git_blob(repo_root, commit, path))
    subject_loader = subject_loader or (lambda commit: git_subject(repo_root, commit))
    tracked_checker = tracked_checker or (lambda path: git_tracked(repo_root, path))
    checks = {
        "schema": "NOT_REACHED",
        "self_hash": "NOT_REACHED",
        "freshness": "NOT_REACHED",
        "manifest": "NOT_REACHED",
        "commit_and_file_hash": "NOT_REACHED",
        "breakpoint_contract": "NOT_REACHED",
        "founder_authorization": "NOT_REACHED",
        "authority_pointer": "NOT_REACHED",
        "replay": "NOT_REACHED",
        "candidate_only": "NOT_REACHED",
        "tracked_inputs": "NOT_REACHED",
    }
    try:
        request_path = request_path.resolve()
        request = load_object(request_path, "REQUEST")
        request_sha256 = sha256_file(request_path)
        validate_schema(
            request,
            _schema_path(repo_root, "w7tp_total_field_successor_rebind_review_request_v1.schema.json"),
            "REQUEST",
        )
        checks["schema"] = "PASS"
        validate_self_hash(
            request,
            "request_self_sha256",
            "request_self_hash_algorithm",
            REQUEST_SELF_HASH_ALGORITHM,
        )
        checks["self_hash"] = "PASS"
        _check_freshness(request, reviewed_at)
        checks["freshness"] = "PASS"
        if NONCE.fullmatch(request["nonce"]) is None or request["replay_guard"]["single_use"] is not True:
            raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_NONCE_OR_REPLAY_SCHEMA", "$.nonce")

        canonical = safe_repo_path(repo_root, request["canonical_ref"], "$.canonical_ref")
        candidate_root = safe_repo_path(repo_root, request["candidate_root"], "$.candidate_root")
        manifest_path = candidate_root / "SHA256_MANIFEST.json"
        authority_path = safe_repo_path(repo_root, request["authority_pointer_ref"], "$.authority_pointer_ref")
        founder_path = safe_repo_path(repo_root, request["founder_authorization_ref"], "$.founder_authorization_ref")
        if not canonical.is_file():
            raise SuccessorRebindReviewError(DECISION_HOLD, "HOLD_CANONICAL_POINTER_MISSING", "$.canonical_ref")
        canonical_pointer = load_object(canonical, "CANONICAL_POINTER")
        if canonical_pointer.get("state") != "ACTIVE_CANONICAL" or canonical_pointer.get("version") != "2.1":
            raise SuccessorRebindReviewError(DECISION_HOLD, "HOLD_CANONICAL_V2_1_NOT_ACTIVE", "$.canonical_ref")
        if not candidate_root.is_dir() or not manifest_path.is_file():
            raise SuccessorRebindReviewError(DECISION_HOLD, "HOLD_CANDIDATE_OR_MANIFEST_MISSING", "$.candidate_root")
        if sha256_file(manifest_path) != request["manifest_sha256"]:
            raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_MANIFEST_HASH_DRIFT", "$.manifest_sha256")
        checks["manifest"] = "PASS"

        predecessor = source_loader(request["predecessor_commit"], request["source_path_ref"])
        current = source_loader(request["current_commit"], request["source_path_ref"])
        if sha256_bytes(predecessor) != request["predecessor_sha256"] or sha256_bytes(current) != request["current_sha256"]:
            raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_SOURCE_BINDING_HASH_DRIFT", "$.current_sha256")
        symbol_marker = f"def {request['symbol_ref']}".encode("utf-8")
        if symbol_marker not in predecessor or symbol_marker not in current:
            raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_SOURCE_SYMBOL_MISSING", "$.symbol_ref")
        checks["commit_and_file_hash"] = "PASS"
        if subject_loader(request["current_commit"]) != request["change_provenance"]:
            raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_CHANGE_PROVENANCE_MISMATCH", "$.change_provenance")
        if b"BreakpointReachabilityDenied" not in current or b"breakpoint_segment_ref" not in current:
            raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_BREAKPOINT_REACHABILITY_CONTRACT_MISSING", "$.breakpoint_reachability_contract")
        checks["breakpoint_contract"] = "PASS"

        if not authority_path.is_file() or sha256_file(authority_path) != request["authority_pointer_sha256"]:
            raise SuccessorRebindReviewError(DECISION_HOLD, "HOLD_AUTHORITY_POINTER_HASH_OR_PATH", "$.authority_pointer_ref")
        authority = load_object(authority_path, "AUTHORITY_POINTER")
        formal_authority = _validate_authority(authority, test_mode=test_mode)
        checks["authority_pointer"] = "PASS"
        if not founder_path.is_file() or sha256_file(founder_path) != request["founder_authorization_sha256"]:
            raise SuccessorRebindReviewError(DECISION_HOLD, "HOLD_FOUNDER_AUTHORIZATION_HASH_OR_PATH", "$.founder_authorization_ref")
        _validate_founder_authorization(load_object(founder_path, "FOUNDER_AUTHORIZATION"), test_mode=test_mode)
        checks["founder_authorization"] = "PASS"

        if any((candidate_root / name).exists() for name in FORBIDDEN_FORMAL_ARTIFACTS):
            raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_CANDIDATE_SELF_FORMAL_AUTHORITY", "$.candidate_root")
        if request["contract_mode"] == "FORMAL_REVIEW" and test_mode:
            raise SuccessorRebindReviewError(DECISION_REJECTED, "REJECT_TEST_MODE_FORMAL_REQUEST", "$.contract_mode")
        if request["contract_mode"] != "FORMAL_REVIEW" and not test_mode:
            raise SuccessorRebindReviewError(DECISION_HOLD, "HOLD_CONTRACT_NOT_FORMALLY_ACTIVE", "$.contract_mode")
        checks["candidate_only"] = "PASS"

        if _replay_seen(replay_root, request):
            checks["replay"] = "HOLD"
            raise SuccessorRebindReviewError(DECISION_HOLD, "HOLD_NONCE_REPLAY", "$.nonce")
        if not test_mode and replay_root is None:
            raise SuccessorRebindReviewError(DECISION_HOLD, "HOLD_REPLAY_LEDGER_NOT_BOUND", "$.replay_guard.ledger_ref")
        checks["replay"] = "PASS"

        tracked_inputs = [request_path, canonical, manifest_path, authority_path, founder_path]
        if not test_mode and not all(tracked_checker(path) for path in tracked_inputs):
            raise SuccessorRebindReviewError(DECISION_HOLD, "HOLD_UNTRACKED_FORMAL_INPUT", "$.tracked_inputs")
        checks["tracked_inputs"] = "PASS"

        formal = bool(formal_authority and not test_mode)
        decision = {
            "schema_version": DECISION_SCHEMA_VERSION,
            "packet_type": "TOTAL_FIELD_SUCCESSOR_REBIND_DECISION",
            "decision_id": f"decision:{request['run_id']}:{request_sha256[:16]}",
            "request_id": request["request_id"],
            "run_id": request["run_id"],
            "reviewed_at": utc_text(reviewed_at),
            "state": _decision_state(DECISION_APPROVED),
            "decision": DECISION_APPROVED,
            "reason_codes": ["PASS_TEST_VECTOR_ONLY" if test_mode else "PASS_FORMAL_SUCCESSOR_REBIND_REVIEW"],
            "request_sha256": request_sha256,
            "manifest_sha256": request["manifest_sha256"],
            "predecessor_commit": request["predecessor_commit"],
            "predecessor_sha256": request["predecessor_sha256"],
            "current_commit": request["current_commit"],
            "current_sha256": request["current_sha256"],
            "authority_pointer_ref": request["authority_pointer_ref"],
            "authority_pointer_sha256": request["authority_pointer_sha256"],
            "formal": formal,
            "seal_eligible": True,
            "core_landing": CORE_LANDING,
            "decision_self_hash_algorithm": DECISION_SELF_HASH_ALGORITHM,
        }
        decision["decision_sha256"] = sha256_bytes(canonical_json_bytes(decision))
        receipt = {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "packet_type": "TOTAL_FIELD_SUCCESSOR_REBIND_REVIEW_RECEIPT",
            "receipt_id": f"receipt:{request['run_id']}:{decision['decision_sha256'][:16]}",
            "decision_id": decision["decision_id"],
            "request_id": request["request_id"],
            "run_id": request["run_id"],
            "received_at": utc_text(reviewed_at),
            "request_expires_at": request["expires_at"],
            "nonce": request["nonce"],
            "replay_guard": {
                "single_use": True,
                "domain": request["replay_guard"]["domain"],
                "disposition": "CONSUMED",
            },
            "request_sha256": request_sha256,
            "manifest_sha256": request["manifest_sha256"],
            "decision_sha256": decision["decision_sha256"],
            "authority_pointer_ref": request["authority_pointer_ref"],
            "authority_pointer_sha256": request["authority_pointer_sha256"],
            "final_decision": DECISION_APPROVED,
            "checks": checks,
            "formal": formal,
            "core_landing": CORE_LANDING,
            "receipt_self_hash_algorithm": RECEIPT_SELF_HASH_ALGORITHM,
        }
        receipt["receipt_sha256"] = sha256_bytes(canonical_json_bytes(receipt))
        validate_schema(decision, _schema_path(repo_root, "w7tp_total_field_successor_rebind_decision_v1.schema.json"), "DECISION")
        validate_schema(receipt, _schema_path(repo_root, "w7tp_total_field_successor_rebind_receipt_v1.schema.json"), "RECEIPT")
        result = {
            "state": decision["state"],
            "decision": decision["decision"],
            "reason_codes": decision["reason_codes"],
            "formal": formal,
            "decision_document": decision,
            "receipt_document": receipt,
        }
        if output_dir is not None:
            output_dir = output_dir.resolve()
            if output_dir.exists() and any(output_dir.iterdir()):
                raise FileExistsError(f"refusing to overwrite non-empty output directory: {output_dir}")
            output_dir.mkdir(parents=True, exist_ok=True)
            prefix = "FORMAL" if formal else "TEST"
            _write_json(output_dir / f"{prefix}_TOTAL_FIELD_SUCCESSOR_REBIND_DECISION.json", decision)
            _write_json(output_dir / f"{prefix}_TOTAL_FIELD_SUCCESSOR_REBIND_RECEIPT.json", receipt)
        return result
    except SuccessorRebindReviewError as error:
        return _fail_result(error)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--replay-root", type=Path)
    parser.add_argument("--test-mode", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = review_once(
        request_path=args.request,
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        replay_root=args.replay_root,
        test_mode=args.test_mode,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["decision"] == DECISION_APPROVED else 2


if __name__ == "__main__":
    raise SystemExit(main())
