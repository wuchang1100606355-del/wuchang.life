#!/usr/bin/env python3
"""Hash-bound successor-rebind seal tool contract candidate.

The current unapproved contract can create only `TEST_SEAL_ONLY` artifacts.
A formal seal additionally requires tracked inputs and an active, hash-bound
Total Field authority pointer whose contract state is `ACTIVE_FORMAL`.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from tools.total_field import w7tp_successor_rebind_reviewer_v1 as reviewer


SEAL_TOOL_VERSION = "w7tp-successor-rebind-seal/1.0-candidate"
SEAL_SCHEMA_VERSION = "W7TP-TOTAL-FIELD-SUCCESSOR-REBIND-SEAL/1.0"
SEAL_SELF_HASH_ALGORITHM = "SHA256_CANONICAL_JSON_EXCLUDING_SEAL_SHA256/1.0"
MAX_SEAL_TTL_SECONDS = 300


class SuccessorRebindSealError(ValueError):
    """Stable fail-closed seal error."""

    def __init__(self, reason_code: str, path: str = "$") -> None:
        self.reason_code = reason_code
        self.path = path
        super().__init__(f"{reason_code}:{path}")


def _load(path: Path, reason: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SuccessorRebindSealError(f"REJECT_{reason}_JSON_INVALID", str(path)) from exc
    if not isinstance(value, dict):
        raise SuccessorRebindSealError(f"REJECT_{reason}_OBJECT_REQUIRED", str(path))
    return value


def _validate_self_hash(value: dict[str, Any], field: str, algorithm_field: str, algorithm: str) -> None:
    expected = value.get(field)
    if not isinstance(expected, str) or reviewer.HEX64.fullmatch(expected) is None or value.get(algorithm_field) != algorithm:
        raise SuccessorRebindSealError("REJECT_SEGMENT_SELF_HASH_SCHEMA", f"$.{field}")
    material = dict(value)
    material.pop(field)
    if reviewer.sha256_bytes(reviewer.canonical_json_bytes(material)) != expected:
        raise SuccessorRebindSealError("REJECT_SEGMENT_SELF_HASH_MISMATCH", f"$.{field}")


def _seal_replay_seen(replay_root: Path | None, nonce: str, domain: str) -> bool:
    if replay_root is None or not replay_root.is_dir():
        return False
    for path in replay_root.rglob("*SUCCESSOR_REBIND_SEAL.json"):
        try:
            seal = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if seal.get("nonce") == nonce and seal.get("replay_guard", {}).get("domain") == domain:
            return True
    return False


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def create_seal(
    *,
    manifest_path: Path,
    manifest_sha256: str | None,
    decision_path: Path,
    receipt_path: Path,
    authority_pointer_path: Path,
    authority_pointer_sha256: str,
    repo_root: Path,
    output_path: Path | None = None,
    replay_root: Path | None = None,
    now: datetime | None = None,
    test_mode: bool = False,
    tracked_checker: Callable[[Path], bool] | None = None,
) -> dict[str, Any]:
    """Create a test seal, or a formal seal only after contract activation."""

    repo_root = repo_root.resolve()
    issued_at = (now or reviewer.utc_now()).astimezone(timezone.utc)
    if manifest_sha256 is None or reviewer.HEX64.fullmatch(manifest_sha256) is None:
        raise SuccessorRebindSealError("REJECT_MANIFEST_SHA256_NULL_OR_INVALID", "$.manifest_sha256")
    if not test_mode and tracked_checker is not None:
        raise SuccessorRebindSealError("REJECT_FORMAL_TRACKING_CHECKER_INJECTION")
    tracked_checker = tracked_checker or (lambda path: reviewer.git_tracked(repo_root, path))
    paths = [manifest_path.resolve(), decision_path.resolve(), receipt_path.resolve(), authority_pointer_path.resolve()]
    if any(not path.is_file() or path.is_symlink() for path in paths):
        raise SuccessorRebindSealError("REJECT_SEAL_INPUT_MISSING_OR_SYMLINK")

    decision = _load(decision_path, "DECISION")
    receipt = _load(receipt_path, "RECEIPT")
    authority = _load(authority_pointer_path, "AUTHORITY_POINTER")
    reviewer.validate_schema(
        decision,
        repo_root / "schemas/field/w7tp_total_field_successor_rebind_decision_v1.schema.json",
        "DECISION",
    )
    reviewer.validate_schema(
        receipt,
        repo_root / "schemas/field/w7tp_total_field_successor_rebind_receipt_v1.schema.json",
        "RECEIPT",
    )
    _validate_self_hash(
        decision,
        "decision_sha256",
        "decision_self_hash_algorithm",
        reviewer.DECISION_SELF_HASH_ALGORITHM,
    )
    _validate_self_hash(
        receipt,
        "receipt_sha256",
        "receipt_self_hash_algorithm",
        reviewer.RECEIPT_SELF_HASH_ALGORITHM,
    )
    if decision["decision"] != reviewer.DECISION_APPROVED or decision["seal_eligible"] is not True:
        raise SuccessorRebindSealError("REJECT_DECISION_NOT_APPROVED_OR_SEAL_ELIGIBLE", "$.decision")
    if receipt["final_decision"] != reviewer.DECISION_APPROVED:
        raise SuccessorRebindSealError("REJECT_RECEIPT_DECISION_NOT_APPROVED", "$.receipt.final_decision")
    if reviewer.sha256_file(manifest_path) != manifest_sha256:
        raise SuccessorRebindSealError("REJECT_SOURCE_MANIFEST_HASH_DRIFT", "$.manifest_sha256")
    if decision["manifest_sha256"] != manifest_sha256 or receipt["manifest_sha256"] != manifest_sha256:
        raise SuccessorRebindSealError("REJECT_MANIFEST_SEGMENT_BINDING_MISMATCH", "$.manifest_sha256")
    if receipt["decision_id"] != decision["decision_id"] or receipt["decision_sha256"] != decision["decision_sha256"]:
        raise SuccessorRebindSealError("REJECT_DECISION_RECEIPT_HASH_BINDING", "$.receipt.decision_sha256")
    if receipt["request_sha256"] != decision["request_sha256"] or receipt["run_id"] != decision["run_id"]:
        raise SuccessorRebindSealError("REJECT_REQUEST_OR_RUN_BINDING", "$.receipt")
    if reviewer.sha256_file(authority_pointer_path) != authority_pointer_sha256:
        raise SuccessorRebindSealError("REJECT_AUTHORITY_POINTER_HASH_DRIFT", "$.authority_pointer_sha256")
    if decision["authority_pointer_sha256"] != authority_pointer_sha256 or receipt["authority_pointer_sha256"] != authority_pointer_sha256:
        raise SuccessorRebindSealError("REJECT_AUTHORITY_SEGMENT_BINDING", "$.authority_pointer_sha256")
    if decision["authority_pointer_ref"] != receipt["authority_pointer_ref"]:
        raise SuccessorRebindSealError("REJECT_AUTHORITY_REFERENCE_BINDING", "$.authority_pointer_ref")

    request_expires_at = reviewer.parse_utc(receipt["request_expires_at"], "$.receipt.request_expires_at")
    if issued_at >= request_expires_at:
        raise SuccessorRebindSealError("REJECT_EXPIRED_REVIEW_RECEIPT", "$.receipt.request_expires_at")
    domain = receipt["replay_guard"]["domain"]
    if _seal_replay_seen(replay_root, receipt["nonce"], domain):
        raise SuccessorRebindSealError("REJECT_SEAL_REPLAY", "$.receipt.nonce")
    if not test_mode and replay_root is None:
        raise SuccessorRebindSealError("REJECT_FORMAL_REPLAY_LEDGER_NOT_BOUND", "$.replay_guard")

    if test_mode:
        if decision["formal"] is not False or receipt["formal"] is not False:
            raise SuccessorRebindSealError("REJECT_TEST_MODE_FORMAL_INPUT")
        formal = False
        contract_approved = False
        seal_state = "TEST_SEAL_ONLY"
    else:
        required_authority = {
            "state": "ACTIVE_TOTAL_FIELD_AUTHORITY",
            "contract_state": "ACTIVE_FORMAL",
            "formal_decision_authority": True,
            "formal_seal_authority": True,
        }
        for key, expected in required_authority.items():
            if authority.get(key) != expected:
                raise SuccessorRebindSealError("REJECT_FORMAL_AUTHORITY_NOT_ACTIVE", f"$.authority_pointer.{key}")
        if decision["formal"] is not True or receipt["formal"] is not True:
            raise SuccessorRebindSealError("REJECT_NONFORMAL_DECISION_OR_RECEIPT")
        if not all(tracked_checker(path) for path in paths):
            raise SuccessorRebindSealError("REJECT_UNTRACKED_FORMAL_INPUT")
        formal = True
        contract_approved = True
        seal_state = "FORMAL_SEAL"

    expires_at = min(request_expires_at, issued_at + timedelta(seconds=MAX_SEAL_TTL_SECONDS))
    seal = {
        "schema_version": SEAL_SCHEMA_VERSION,
        "packet_type": "TOTAL_FIELD_SUCCESSOR_REBIND_SEAL",
        "seal_id": f"seal:{decision['run_id']}:{receipt['receipt_sha256'][:16]}",
        "run_id": decision["run_id"],
        "issued_at": reviewer.utc_text(issued_at),
        "expires_at": reviewer.utc_text(expires_at),
        "source_manifest_sha256": manifest_sha256,
        "decision_sha256": decision["decision_sha256"],
        "receipt_sha256": receipt["receipt_sha256"],
        "authority_pointer_ref": decision["authority_pointer_ref"],
        "authority_pointer_sha256": authority_pointer_sha256,
        "nonce": receipt["nonce"],
        "replay_guard": {"single_use": True, "domain": domain, "disposition": "CONSUMED"},
        "seal_state": seal_state,
        "formal": formal,
        "contract_approved": contract_approved,
        "core_landing": reviewer.CORE_LANDING,
        "seal_self_hash_algorithm": SEAL_SELF_HASH_ALGORITHM,
    }
    seal["seal_sha256"] = reviewer.sha256_bytes(reviewer.canonical_json_bytes(seal))
    reviewer.validate_schema(
        seal,
        repo_root / "schemas/field/w7tp_total_field_successor_rebind_seal_v1.schema.json",
        "SEAL",
    )
    if output_path is not None:
        if output_path.exists():
            raise FileExistsError(f"refusing to overwrite existing seal: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(output_path, seal)
    return seal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--authority-pointer", type=Path, required=True)
    parser.add_argument("--authority-pointer-sha256", required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--replay-root", type=Path)
    parser.add_argument("--test-mode", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        seal = create_seal(
            manifest_path=args.manifest,
            manifest_sha256=args.manifest_sha256,
            decision_path=args.decision,
            receipt_path=args.receipt,
            authority_pointer_path=args.authority_pointer,
            authority_pointer_sha256=args.authority_pointer_sha256,
            repo_root=args.repo_root,
            output_path=args.output,
            replay_root=args.replay_root,
            test_mode=args.test_mode,
        )
    except SuccessorRebindSealError as error:
        print(json.dumps({"state": "HOLD", "reason_code": error.reason_code, "path": error.path}, sort_keys=True))
        return 2
    print(json.dumps(seal, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
