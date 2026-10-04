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

from tools.total_field.w7tp_total_field_authority_binding_v1 import (
    AuthorityBindingValidationError,
    validate_authority_binding,
)
from tools.total_field.w7tp_founder_passkey_v1 import (
    PasskeyVerificationError,
    verify_authorization_passkey,
)


REVIEWER_VERSION = "w7tp-successor-rebind-reviewer/1.3-t007-task-state-d6-hardening"
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
GLOBAL_REQUEST_SCHEMA_VERSION = "W7TP-TOTAL-FIELD-SUCCESSOR-REBIND-REVIEW-REQUEST/2.0"
GLOBAL_DECISION_SCHEMA_VERSION = "W7TP-TOTAL-FIELD-SUCCESSOR-REBIND-DECISION/2.0"
GLOBAL_RECEIPT_SCHEMA_VERSION = "W7TP-TOTAL-FIELD-SUCCESSOR-REBIND-RECEIPT/2.0"
GLOBAL_REVIEW_SCOPE = "GLOBAL_CANONICAL_SUCCESSOR"
GLOBAL_REVIEW_COMPLETION_DIR = "review_completion_20261002T184158Z"
GLOBAL_REQUIRED_PACKAGE_FILES = {
    "founder_directive": "00_FOUNDER_DIRECTIVE.json",
    "successor_contract": f"{GLOBAL_REVIEW_COMPLETION_DIR}/GLOBAL_SUCCESSOR_CONTRACT.json",
    "current_field_successor": f"{GLOBAL_REVIEW_COMPLETION_DIR}/CURRENT_8D_FIELD_SUCCESSOR.json",
    "consumer_rebind_matrix": "03_ACTIVE_CONSUMER_REBIND_MATRIX.json",
    "authority_successor_receipt": f"{GLOBAL_REVIEW_COMPLETION_DIR}/AUTHORITY_SUCCESSOR_RECEIPT_CANDIDATE.json",
}
GLOBAL_COMPLETION_MANIFEST_FILES = frozenset(
    {
        "AUTHORITY_SUCCESSOR_RECEIPT_CANDIDATE.json",
        "CURRENT_8D_FIELD_SUCCESSOR.json",
        "GLOBAL_SUCCESSOR_CONTRACT.json",
        "REGRESSION_SPEC.md",
        "REOBSERVATION.json",
        "REOBSERVATION_REVIEWER_EXTENSION_20261003.json",
        "validate_candidate.py",
    }
)
GLOBAL_REQUIRED_ACTIVE_CONSUMERS = frozenset(
    {
        "tools/d8_guard_eval.py",
        "tools/total_field/w7tp_intent_field_suite/edge_queue.py",
        "tools/total_field/w7tp_intent_field_suite/adaptive_cognition.py",
        "tools/total_field/w7tp_intent_field_suite/cli.py",
        "tools/total_field/w7tp_true8d_contract_sandbox.py",
        "tools/total_field/wuchang_three_org_container_scene_bridge.py",
        "tools/total_field/w7tp_review_candidate_v2_3_adapter_v2_1.py",
        "manifests/total_field/w7tp_five_skill_id_binding_matrix_v2_1/BINDING_MATRIX.json",
        "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_CANONICAL.json",
        "runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json",
    }
)
GLOBAL_POSTIMAGE_CONSUMER_PREIMAGES = {
    "tools/d8_guard_eval.py": "ba7fedc7cae1eb447fab2fd34d4018a01efb476a3b61017fb0ef30807c9e5b8b",
    "tools/total_field/w7tp_intent_field_suite/edge_queue.py": "247ba4d139603c11091cd2abeb6fd737a5d09914fc9c1eda7d48e164569ec1a9",
    "tools/total_field/w7tp_intent_field_suite/adaptive_cognition.py": "ee65b21510eeec7bd523d4be35f005712b97baed603247fc4fd51994235c046e",
    "tools/total_field/w7tp_intent_field_suite/cli.py": "2ae1efc1106af00b1c7f15b55a70ae3c9341f64410ca45d272c848a0fdbd4177",
    "tools/total_field/w7tp_true8d_contract_sandbox.py": "3d43d1a6815cee0f5a6cadfd660b4d319731028a1d88ea4ee175317c7829d20e",
    "tools/total_field/wuchang_three_org_container_scene_bridge.py": "dbd44de14f3a072b898ee8b9588371bc1c32bd041487c09006e33999d949eec2",
    "tools/total_field/w7tp_review_candidate_v2_3_adapter_v2_1.py": "2aa249f39d452bbc6791db73c38001925eeeac695114a88edbcbbf66780fa9b5",
    "manifests/total_field/w7tp_five_skill_id_binding_matrix_v2_1/BINDING_MATRIX.json": "f7009c496f6d96b73298457b5d5bf055d5e0d9fae20afe069042a89f9c39b130",
}
GLOBAL_RETIRED_ADAPTER = "tools/total_field/w7tp_review_candidate_v2_3_adapter_v2_1.py"
GLOBAL_SKILL_MATRIX_PREDECESSOR = (
    "manifests/total_field/w7tp_five_skill_id_binding_matrix_v2_1/BINDING_MATRIX.json"
)
GLOBAL_SUCCESSOR_ID = "W7TP_8D_ADI_V2_3"
GLOBAL_ACTIVE_BINDING_LITERAL = "active_canonical_binding"
GLOBAL_OLD_ACTIVE_DIMENSION_LITERALS = frozenset(
    {
        "D6 Sovereign Privacy Field",
        "D7 Generative Transmission & Resource Routing Field",
    }
)
GLOBAL_SKILL_SCOPE_SCHEMA = "W7TP-SKILL-BINDING-MATRIX/2.3/1.0"
GLOBAL_SKILL_SCOPE_ROOTS = (".skill-build", "capabilities")
GLOBAL_NATIVE_SKILL_INDEX_REF = "capabilities/W7TP_NATIVE_SKILLS_INDEX.json"
GLOBAL_SKILL_BINDING_STATES = frozenset(
    {
        "ACTIVE_EXECUTABLE",
        "REGISTERED_NATIVE",
        "REFERENCED_BY_ACTIVE_RUNTIME",
        "SOURCE_PRESENT",
    }
)
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
    try:
        validate_authority_binding(pointer)
    except AuthorityBindingValidationError as exc:
        suffix = exc.path[1:] if exc.path.startswith("$") else f".{exc.path}"
        raise SuccessorRebindReviewError(
            DECISION_HOLD,
            "HOLD_FORMAL_AUTHORITY_BINDING_SCHEMA",
            f"$.authority_pointer{suffix}",
        ) from exc
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



def _load_native_adi_atom(record_id: str) -> dict[str, Any]:
    """Resolve one task-bound Native ADI state atom from the existing local service."""

    try:
        from tools.w7tp_task_state_minimum_packet import _post_json

        packet = _post_json("/v1/adi/packet", {"ids": [record_id]})
    except Exception as exc:
        raise SuccessorRebindReviewError(
            DECISION_HOLD,
            "HOLD_NATIVE_ADI_DYNAMIC_CONTEXT_LOOKUP_FAILED",
            "$.dynamic_context.adi_record_id",
        ) from exc
    atoms = packet.get("delta", {}).get("state_atoms", [])
    if not isinstance(atoms, list) or len(atoms) != 1 or atoms[0].get("id") != record_id:
        raise SuccessorRebindReviewError(
            DECISION_HOLD,
            "HOLD_NATIVE_ADI_DYNAMIC_CONTEXT_NOT_EXACT",
            "$.dynamic_context.adi_record_id",
        )
    return atoms[0]


def _validate_global_founder_authorization(
    authorization: dict[str, Any],
    request: dict[str, Any],
    reviewed_at: datetime,
    *,
    repo_root: Path,
    test_mode: bool,
) -> list[Path]:
    if authorization.get("founder") != "江政隆":
        raise SuccessorRebindReviewError(
            DECISION_HOLD,
            "HOLD_FOUNDER_IDENTITY_MISMATCH",
            "$.founder_authorization.founder",
        )
    if test_mode and authorization.get("state") == "TEST_ONLY":
        return []
    required = {
        "state": "FOUNDER_AUTHORIZATION_APPROVED",
        "authorized_effect": FORMAL_FOUNDER_EFFECT,
        "task_id": "T-007",
        "review_scope": GLOBAL_REVIEW_SCOPE,
        "candidate_root": request["candidate_root"],
        "manifest_sha256": request["manifest_sha256"],
        "canonical_preimage_sha256": request["predecessor_pointer_sha256"],
        "authority_preimage_sha256": request["authority_pointer_sha256"],
        "current_field_preimage_sha256": request["live_bindings"]["current_field"]["sha256"],
        "single_use": True,
        "g4_authorized": False,
    }
    for key, expected in required.items():
        if authorization.get(key) != expected:
            raise SuccessorRebindReviewError(
                DECISION_HOLD,
                "HOLD_FOUNDER_GLOBAL_REVIEW_SCOPE_MISMATCH",
                f"$.founder_authorization.{key}",
            )
    if authorization.get("gates") != ["G1", "G2", "G3"]:
        raise SuccessorRebindReviewError(
            DECISION_HOLD,
            "HOLD_FOUNDER_GLOBAL_REVIEW_SCOPE_MISMATCH",
            "$.founder_authorization.gates",
        )
    if authorization.get("passkey_assertion_verified") is not True:
        raise SuccessorRebindReviewError(
            DECISION_HOLD,
            "HOLD_FOUNDER_PASSKEY_ASSERTION_NOT_VERIFIED",
            "$.founder_authorization.passkey_assertion_verified",
        )
    created = parse_utc(authorization.get("created_at"), "$.founder_authorization.created_at")
    expires = parse_utc(authorization.get("expires_at"), "$.founder_authorization.expires_at")
    if expires <= created or (expires - created).total_seconds() > MAX_REQUEST_TTL_SECONDS:
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_FOUNDER_AUTHORIZATION_TTL",
            "$.founder_authorization.expires_at",
        )
    if reviewed_at < created - timedelta(seconds=MAX_CLOCK_SKEW_SECONDS) or reviewed_at >= expires:
        raise SuccessorRebindReviewError(
            DECISION_HOLD,
            "HOLD_FOUNDER_AUTHORIZATION_NOT_FRESH",
            "$.founder_authorization.expires_at",
        )
    scope_keys = (
        "founder",
        "authorized_effect",
        "task_id",
        "review_scope",
        "candidate_root",
        "manifest_sha256",
        "canonical_preimage_sha256",
        "authority_preimage_sha256",
        "current_field_preimage_sha256",
        "gates",
        "g4_authorized",
        "single_use",
        "created_at",
        "expires_at",
    )
    scope = {key: authorization.get(key) for key in scope_keys}
    try:
        verified = verify_authorization_passkey(
            repo_root,
            authorization,
            scope=scope,
        )
    except PasskeyVerificationError as exc:
        raise SuccessorRebindReviewError(
            DECISION_HOLD,
            f"HOLD_FOUNDER_{exc.code}",
            f"$.founder_authorization{exc.path[1:] if exc.path.startswith('$') else '.' + exc.path}",
        ) from exc
    return [verified.credential_path, verified.assertion_path]


def _validate_global_dynamic_context(
    request: dict[str, Any],
    atom: dict[str, Any],
    reviewed_at: datetime,
) -> None:
    """Validate either the existing task-state Dynamic Context atom or the legacy bootstrap atom."""

    binding = request["dynamic_context"]
    if atom.get("record_sha256") != binding["record_sha256"]:
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_NATIVE_ADI_RECORD_HASH_DRIFT",
            "$.dynamic_context.record_sha256",
        )
    try:
        atom_time = datetime.fromtimestamp(int(atom["time_slot"]), tz=timezone.utc)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_NATIVE_ADI_TIME_SLOT_INVALID",
            "$.dynamic_context",
        ) from exc
    record_id = binding["adi_record_id"]
    if record_id.startswith("task-state:T-007:"):
        pulled_at = parse_utc(
            binding.get("pulled_at"),
            "$.dynamic_context.pulled_at",
        )
        pull_age = (reviewed_at - pulled_at).total_seconds()
        if (
            pull_age < -MAX_CLOCK_SKEW_SECONDS
            or pull_age > binding["maximum_age_seconds"]
            or atom_time > pulled_at + timedelta(seconds=MAX_CLOCK_SKEW_SECONDS)
        ):
            raise SuccessorRebindReviewError(
                DECISION_HOLD,
                "HOLD_NATIVE_ADI_DYNAMIC_CONTEXT_NOT_FRESH",
                "$.dynamic_context.pulled_at",
            )
        packet_sha = binding.get("packet_sha256")
        context_ref = binding.get("context_ref")
        if (
            HEX64.fullmatch(str(packet_sha or "")) is None
            or context_ref != f"context:task-state:T-007:{packet_sha[:16]}"
        ):
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_NATIVE_ADI_DYNAMIC_CONTEXT_PULL_BINDING",
                "$.dynamic_context.context_ref",
            )
    else:
        age = (reviewed_at - atom_time).total_seconds()
        if age < -MAX_CLOCK_SKEW_SECONDS or age > binding["maximum_age_seconds"]:
            raise SuccessorRebindReviewError(
                DECISION_HOLD,
                "HOLD_NATIVE_ADI_DYNAMIC_CONTEXT_NOT_FRESH",
                "$.dynamic_context.maximum_age_seconds",
            )

    payload = atom.get("payload")
    if not isinstance(payload, dict):
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_NATIVE_ADI_PAYLOAD_INVALID",
            "$.dynamic_context",
        )

    def require_exact(exact: dict[tuple[str, ...], Any]) -> None:
        for path, expected in exact.items():
            current: Any = payload
            for key in path:
                if not isinstance(current, dict) or key not in current:
                    raise SuccessorRebindReviewError(
                        DECISION_REJECTED,
                        "REJECT_NATIVE_ADI_DYNAMIC_CONTEXT_SCOPE",
                        "$.dynamic_context." + ".".join(path),
                    )
                current = current[key]
            if current != expected:
                raise SuccessorRebindReviewError(
                    DECISION_REJECTED,
                    "REJECT_NATIVE_ADI_DYNAMIC_CONTEXT_SCOPE",
                    "$.dynamic_context." + ".".join(path),
                )

    record_id = binding["adi_record_id"]
    if record_id.startswith("task-state:T-007:"):
        require_exact(
            {
                ("knowledge_type",): "OBSERVED_TASK_STATE_COORDINATE",
                ("state",): "TASK_STATE_SNAPSHOT_INDEXED",
                ("D1_INTENT", "task_ref"): "task:T-007",
                ("D2_STATE", "current"): "DOING",
                ("D3_COORDINATE", "git_branch"): "codex/current-live-state-consolidation-20260915",
                ("D5_EXECUTION", "reconstruction_scope"): "LOCAL_TASK_STATE_ONLY",
                ("D5_EXECUTION", "task_dirty_zero_required"): True,
                ("D6_GST", "packet_contract"): "ORIGIN_STATE_MINIMUM_PACKET",
                ("D6_GST", "reconstruction"): "LOCAL_VOLATILE_ON_PULL",
                ("D6_GST", "rule_body_location"): "LOCAL_ONLY",
                ("D6_GST", "rule_ref"): "local-rule:w7tp-task-state-ledger-reconstruction/v1",
                ("D6_GST", "compression"): False,
                ("D6_GST", "differential"): False,
                ("D7_RISK", "source_hash_drift"): "FAIL_CLOSED",
                ("D7_RISK", "missing_action_ref"): "FAIL_CLOSED",
                ("D7_RISK", "missing_adi_record"): "FAIL_CLOSED",
                ("D8_AUTHORITY", "candidate_only"): True,
                ("D8_AUTHORITY", "canonical"): False,
                ("D8_AUTHORITY", "formal_effect_authority"): "LOCAL_TOTAL_FIELD",
                ("D8_AUTHORITY", "model_authority"): False,
                ("D8_AUTHORITY", "provider_authority"): False,
            }
        )
        for path in (
            ("D2_STATE", "snapshot_sha256"),
            ("D3_COORDINATE", "support_native_adi_packet_sha256"),
            ("D4_EVIDENCE", "task_state_sha256"),
            ("D4_EVIDENCE", "selected_actions_sha256"),
            ("D4_EVIDENCE", "checkpoint_sha256"),
        ):
            current: Any = payload
            for key in path:
                current = current.get(key) if isinstance(current, dict) else None
            if HEX64.fullmatch(str(current or "")) is None:
                raise SuccessorRebindReviewError(
                    DECISION_REJECTED,
                    "REJECT_NATIVE_ADI_DYNAMIC_CONTEXT_SCOPE",
                    "$.dynamic_context." + ".".join(path),
                )
        selected_actions = payload.get("D4_EVIDENCE", {}).get("selected_action_refs")
        if (
            not isinstance(selected_actions, list)
            or not selected_actions
            or any(not isinstance(value, str) or not value for value in selected_actions)
        ):
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_NATIVE_ADI_DYNAMIC_CONTEXT_SCOPE",
                "$.dynamic_context.D4_EVIDENCE.selected_action_refs",
            )
        return

    require_exact(
        {
            ("CURRENT_CONTEXT_ELIGIBLE",): True,
            ("DYNAMIC_CONTEXT_ELIGIBLE",): True,
            ("RUNTIME_DECISION_ELIGIBLE",): True,
            ("D1_INTENT", "task_ref"): "task:T-007",
            ("D2_STATE", "active_machine_pointer_version"): "2.1",
            ("D3_COORDINATE", "node"): "taiji01",
            ("D3_COORDINATE", "candidate_root"): request["candidate_root"],
            ("D3_COORDINATE", "canonical_pointer_ref"): request["canonical_ref"],
            ("D4_EVIDENCE", "candidate_manifest_sha256"): request["manifest_sha256"],
            ("D4_EVIDENCE", "canonical_pointer_sha256"): request["predecessor_pointer_sha256"],
            ("D4_EVIDENCE", "current_field_sha256"): request["live_bindings"]["current_field"]["sha256"],
            ("D4_EVIDENCE", "current_field_router_sha256"): request["live_bindings"]["current_field_router"]["sha256"],
            ("D4_EVIDENCE", "total_field_authority_sha256"): request["authority_pointer_sha256"],
            ("D5_EXECUTION", "canonical_pointer_change"): False,
            ("D6_GST", "compression_payload"): False,
            ("D6_GST", "differential_payload"): False,
            ("D6_GST", "dynamic_context_required"): True,
            ("D6_GST", "task_state_origin_cell_required"): True,
            ("D7_RISK", "fail_closed_on_source_hash_drift"): True,
            ("D8_AUTHORITY", "candidate_only"): True,
            ("D8_AUTHORITY", "canonical"): False,
            ("D8_AUTHORITY", "promotion_authorized_by_this_record"): False,
        }
    )


def _manifest_entry_sha256(files: dict[str, Any], name: str) -> str | None:
    entry = files.get(name)
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        value = entry.get("sha256")
        return value if isinstance(value, str) else None
    return None


def _validate_completion_manifest(
    *,
    repo_root: Path,
    candidate_root_ref: str,
) -> tuple[Path, dict[str, Any], list[Path]]:
    manifest_ref = (
        Path(candidate_root_ref) / GLOBAL_REVIEW_COMPLETION_DIR / "SHA256_MANIFEST.json"
    ).as_posix()
    manifest_path = safe_repo_path(repo_root, manifest_ref, "$.completion_manifest")
    if not manifest_path.is_file():
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_G2_COMPLETION_MANIFEST_MISSING",
            "$.completion_manifest",
        )
    manifest = load_object(manifest_path, "G2_COMPLETION_MANIFEST")
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != set(GLOBAL_COMPLETION_MANIFEST_FILES):
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_G2_COMPLETION_MANIFEST_FILE_SET",
            "$.completion_manifest.files",
        )
    paths = [manifest_path]
    for name in sorted(GLOBAL_COMPLETION_MANIFEST_FILES):
        leaf_ref = (
            Path(candidate_root_ref) / GLOBAL_REVIEW_COMPLETION_DIR / name
        ).as_posix()
        leaf = safe_repo_path(repo_root, leaf_ref, f"$.completion_manifest.files.{name}")
        expected = _manifest_entry_sha256(files, name)
        if not leaf.is_file() or expected is None or sha256_file(leaf) != expected:
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_G2_COMPLETION_MANIFEST_HASH_DRIFT",
                f"$.completion_manifest.files.{name}",
            )
        paths.append(leaf)
    return manifest_path, manifest, paths


def _validate_completion_contract(
    contract: dict[str, Any],
    *,
    request: dict[str, Any],
    root_contract_ref: str,
    root_contract_sha256: str,
    field_binding: dict[str, Any],
    authority_binding: dict[str, Any],
) -> None:
    expected_dims = {
        "D1": "Intent",
        "D2": "State",
        "D3": "Coordinate",
        "D4": "Evidence",
        "D5": "Execution/Policy",
        "D6": "Generative State Transmission",
        "D7": "Risk/Isolation",
        "D8": "Envelope/Authority",
    }
    dims = contract.get("dimension_contract", {})
    closure = contract.get("closure", {})
    non_effects = contract.get("non_effects", {})
    transition = contract.get("version_transition", {})
    dynamic = contract.get("dynamic_context", {})
    expected_source_bindings = {
        request["canonical_ref"]: request["predecessor_pointer_sha256"],
        request["live_bindings"]["current_field"]["ref"]: request["live_bindings"]["current_field"]["sha256"],
        request["live_bindings"]["current_field_router"]["ref"]: request["live_bindings"]["current_field_router"]["sha256"],
        request["authority_pointer_ref"]: request["authority_pointer_sha256"],
        (Path(request["candidate_root"]) / "SHA256_MANIFEST.json").as_posix(): request["manifest_sha256"],
    }
    source_bindings = contract.get("source_bindings")
    source_map = {
        item.get("ref"): item.get("sha256")
        for item in source_bindings
        if isinstance(source_bindings, list) and isinstance(item, dict)
    } if isinstance(source_bindings, list) else {}
    if (
        contract.get("schema_id") != "W7TP_V21_TO_V23_GLOBAL_SUCCESSOR_REVIEW_COMPLETION_V1"
        or contract.get("state") != "CANDIDATE_ONLY"
        or contract.get("task_id") != "T-007"
        or transition != {"from": "2.1", "mode": "APPEND_ONLY_SUCCESSOR", "to": "2.3"}
        or contract.get("extends") != {"ref": root_contract_ref, "sha256": root_contract_sha256}
        or contract.get("field_successor") != field_binding
        or contract.get("authority_successor_receipt") != authority_binding
        or contract.get("predecessor_pointer")
        != {"ref": request["canonical_ref"], "sha256": request["predecessor_pointer_sha256"]}
        or any(dims.get(key) != value for key, value in expected_dims.items())
        or dims.get("mode") != "8_IN_1_SINGLE_DYNAMIC_STATE_FIELD"
        or dims.get("sequential_pipeline_definition_forbidden") is not True
        or closure.get("G1") != "CANDIDATE_REQUIRES_FORMAL_REVIEW"
        or closure.get("G2") != "CANDIDATE_REQUIRES_CONSUMER_VALIDATION_AND_ACCEPTANCE"
        or closure.get("G3") != "CANDIDATE_REQUIRES_APPEND_ONLY_FORMAL_ACCEPTANCE"
        or closure.get("G4") != "NOT_RUN"
        or any(non_effects.get(key) is not False for key in ("deployed", "formal_decision_created", "pointer_changed", "runtime_changed"))
        or contract.get("promotion_plan", {}).get("enabled") is not False
        or dynamic.get("adi_record_id") != request["dynamic_context"]["adi_record_id"]
        or dynamic.get("record_sha256") != request["dynamic_context"]["record_sha256"]
        or dynamic.get("promotion_authorized_by_dynamic_context") is not False
        or any(source_map.get(ref) != digest for ref, digest in expected_source_bindings.items())
    ):
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_G2_COMPLETION_CONTRACT_BINDING",
            "$.package_bindings.successor_contract",
        )


def _validate_current_field_sidecar(
    field_successor: dict[str, Any],
    *,
    request: dict[str, Any],
    candidate_root_ref: str,
    founder_sha256: str,
    root_field_sha256: str,
) -> dict[str, Any]:
    expected_predecessors = {
        (request["live_bindings"]["current_field"]["ref"], request["live_bindings"]["current_field"]["sha256"]),
        (request["live_bindings"]["current_field_router"]["ref"], request["live_bindings"]["current_field_router"]["sha256"]),
    }
    predecessors = field_successor.get("predecessors")
    observed_predecessors = {
        (item.get("ref"), item.get("sha256"))
        for item in predecessors
        if isinstance(predecessors, list) and isinstance(item, dict)
    } if isinstance(predecessors, list) else set()
    expected_dims = {
        "D1": "Intent",
        "D2": "State",
        "D3": "Coordinate",
        "D4": "Evidence",
        "D5": "Execution/Policy",
        "D6": "Generative State Transmission",
        "D7": "Risk/Isolation",
        "D8": "Envelope/Authority",
    }
    dimensions = field_successor.get("dimensions")
    dimension_map = {
        item.get("id"): item.get("field_en")
        for item in dimensions
        if isinstance(dimensions, list) and isinstance(item, dict)
    } if isinstance(dimensions, list) else {}
    flags = field_successor.get("safety_flags", {})
    required_false = (
        "FILE_CONTENT_READ",
        "CONFIG_READ",
        "NVRAM_WRITE",
        "FIREWALL_WRITE",
        "ROUTER_REBOOT",
        "SECRET_READ",
        "MEMBER_PLAINTEXT_READ",
        "DB_WRITE",
        "SERVICE_RESTART",
        "DEPLOY",
        "PRODUCTION_RELEASE",
    )
    coupled = field_successor.get("coupled_constraints")
    router_nodes = [
        item
        for item in field_successor.get("nodes", [])
        if isinstance(item, dict) and item.get("role") == "physical_network_boundary"
    ]
    if (
        field_successor.get("schema_id") != "W7TP_CURRENT_8D_FIELD_V23_SUCCESSOR_CANDIDATE_V2"
        or field_successor.get("state") != "CANDIDATE_NOT_ACTIVE"
        or field_successor.get("activation") is not False
        or field_successor.get("semantics") != "8_IN_1_SINGLE_DYNAMIC_STATE_FIELD"
        or field_successor.get("representation") != "TASK_PROJECTION_NOT_EIGHT_FIXED_FIELDS_OR_EIGHT_STEPS"
        or observed_predecessors != expected_predecessors
        or field_successor.get("supersedes_candidate")
        != {
            "ref": (Path(candidate_root_ref) / "02_CURRENT_8D_FIELD_V23_SUCCESSOR_CANDIDATE.json").as_posix(),
            "sha256": root_field_sha256,
        }
        or field_successor.get("definition_source")
        != {
            "ref": (Path(candidate_root_ref) / "00_FOUNDER_DIRECTIVE.json").as_posix(),
            "sha256": founder_sha256,
        }
        or field_successor.get("scope", {}).get("router_boundary") != "INCLUDED"
        or field_successor.get("scope", {}).get("dimensions") != "TRUE_8D_ALL"
        or not router_nodes
        or flags.get("PATH_METADATA_ONLY") is not True
        or any(flags.get(key) is not False for key in required_false)
        or dimension_map != expected_dims
        or not isinstance(coupled, dict)
        or coupled.get("difference_analysis") != "差異分析能力，不等於生成式狀態傳輸。"
        or any(not isinstance(coupled.get(key), str) or not coupled.get(key) for key in ("privacy", "routing", "authority"))
        or field_successor.get("formal_total_field_decision_ref") is not None
    ):
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_G2_CURRENT_FIELD_SIDECAR_SEMANTICS",
            "$.package_bindings.current_field_successor",
        )
    downstream = field_successor.get("downstream_validation")
    expected_receipt_ref = (
        Path(candidate_root_ref)
        / GLOBAL_REVIEW_COMPLETION_DIR
        / "REOBSERVATION_REVIEWER_EXTENSION_20261003.json"
    ).as_posix()
    if (
        not isinstance(downstream, dict)
        or downstream.get("state") != "PASS"
        or downstream.get("scope") != GLOBAL_REVIEW_SCOPE
        or downstream.get("receipt_ref") != expected_receipt_ref
        or HEX64.fullmatch(str(downstream.get("receipt_sha256", ""))) is None
    ):
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_G2_DOWNSTREAM_VALIDATION_MISSING",
            "$.package_bindings.current_field_successor.downstream_validation",
        )
    return downstream


def _validate_content_constraints(
    item: dict[str, Any],
    content: bytes,
    *,
    path: str,
) -> None:
    constraints = item.get("content_constraints")
    if not isinstance(constraints, dict) or set(constraints) != {"required_literals", "forbidden_literals"}:
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_CONSUMER_CONTENT_CONSTRAINTS_MISSING",
            path,
        )
    required = constraints.get("required_literals")
    forbidden = constraints.get("forbidden_literals")
    if (
        not isinstance(required, list)
        or not required
        or len(required) != len(set(required))
        or not isinstance(forbidden, list)
        or len(forbidden) != len(set(forbidden))
        or any(not isinstance(value, str) or not value for value in [*required, *forbidden])
    ):
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_CONSUMER_CONTENT_CONSTRAINTS_INVALID",
            path,
        )
    if any(value.encode("utf-8") not in content for value in required):
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_CONSUMER_REQUIRED_CONTENT_MISSING",
            path,
        )
    if any(value.encode("utf-8") in content for value in forbidden):
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_CONSUMER_FORBIDDEN_CONTENT_PRESENT",
            path,
        )


def _skill_source_name(path: Path) -> str | None:
    try:
        head = path.read_text(encoding="utf-8")[:8192]
    except (OSError, UnicodeError):
        return None
    match = re.search(r"(?m)^name:\s*['\"]?([A-Za-z0-9._-]+)['\"]?\s*$", head)
    if match is None:
        return None
    name = match.group(1)
    return name if name.startswith("w7tp-") else None


def _discover_repo_w7tp_skill_sources(repo_root: Path) -> dict[str, Path]:
    discovered: dict[str, Path] = {}
    for root_ref in GLOBAL_SKILL_SCOPE_ROOTS:
        base = repo_root / root_ref
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("SKILL.md")):
            if not path.is_file():
                continue
            skill_id = _skill_source_name(path)
            if skill_id is None:
                continue
            if skill_id in discovered and discovered[skill_id] != path:
                raise SuccessorRebindReviewError(
                    DECISION_REJECTED,
                    "REJECT_G2_DUPLICATE_SKILL_ID",
                    f"$.skill_bindings.{skill_id}",
                )
            discovered[skill_id] = path
    return discovered


def _validate_skill_successor_matrix(
    matrix_path: Path,
    *,
    repo_root: Path,
) -> list[Path]:
    matrix = load_object(matrix_path, "G2_SKILL_SUCCESSOR_MATRIX")
    bindings = matrix.get("bindings")
    discovered = _discover_repo_w7tp_skill_sources(repo_root)
    if (
        matrix.get("schema_version") != GLOBAL_SKILL_SCOPE_SCHEMA
        or matrix.get("canonical_target", {}).get("canonical_id") != GLOBAL_SUCCESSOR_ID
        or matrix.get("canonical_target", {}).get("version") != "2.3"
        or matrix.get("scope_roots") != list(GLOBAL_SKILL_SCOPE_ROOTS)
        or not isinstance(bindings, dict)
        or matrix.get("binding_count") != len(bindings)
        or set(bindings) != set(discovered)
    ):
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_G2_SKILL_SCOPE_MISMATCH",
            "$.package_bindings.consumer_rebind_matrix",
        )

    native_binding = matrix.get("native_skill_index")
    if (
        not isinstance(native_binding, dict)
        or native_binding.get("ref") != GLOBAL_NATIVE_SKILL_INDEX_REF
        or HEX64.fullmatch(str(native_binding.get("sha256", ""))) is None
    ):
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_G2_NATIVE_SKILL_INDEX_BINDING",
            "$.skill_bindings.native_skill_index",
        )
    native_path = safe_repo_path(
        repo_root,
        GLOBAL_NATIVE_SKILL_INDEX_REF,
        "$.skill_bindings.native_skill_index.ref",
    )
    if not native_path.is_file() or sha256_file(native_path) != native_binding["sha256"]:
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_G2_NATIVE_SKILL_INDEX_HASH_DRIFT",
            "$.skill_bindings.native_skill_index.sha256",
        )
    native_index = load_object(native_path, "W7TP_NATIVE_SKILLS_INDEX")
    native_ids = native_index.get("skills")
    if (
        not isinstance(native_ids, list)
        or len(native_ids) != len(set(native_ids))
        or any(not isinstance(value, str) or value not in discovered for value in native_ids)
        or matrix.get("registered_native_skill_ids") != native_ids
    ):
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_G2_NATIVE_SKILL_SCOPE_MISMATCH",
            "$.skill_bindings.registered_native_skill_ids",
        )

    active_ids = matrix.get("active_skill_ids")
    if (
        not isinstance(active_ids, list)
        or len(active_ids) != len(set(active_ids))
        or any(not isinstance(value, str) or value not in discovered for value in active_ids)
    ):
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_G2_ACTIVE_SKILL_SCOPE_INVALID",
            "$.skill_bindings.active_skill_ids",
        )

    tracked_paths: list[Path] = [native_path]
    for skill_id, source_path in discovered.items():
        rel = source_path.resolve().relative_to(repo_root.resolve()).as_posix()
        binding = bindings.get(skill_id)
        if (
            not isinstance(binding, dict)
            or binding.get("target_skill_id") != skill_id
            or binding.get("skill_ref") != rel
            or binding.get("skill_sha256") != sha256_file(source_path)
            or binding.get("binding_state") not in GLOBAL_SKILL_BINDING_STATES
        ):
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_G2_SKILL_BINDING_MISMATCH",
                f"$.skill_bindings.{skill_id}",
            )
        state = binding["binding_state"]
        if skill_id in active_ids and state != "ACTIVE_EXECUTABLE":
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_G2_ACTIVE_SKILL_STATE_MISMATCH",
                f"$.skill_bindings.{skill_id}.binding_state",
            )
        if skill_id in native_ids and state not in {
            "REGISTERED_NATIVE",
            "ACTIVE_EXECUTABLE",
        }:
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_G2_NATIVE_SKILL_STATE_MISMATCH",
                f"$.skill_bindings.{skill_id}.binding_state",
            )
        tracked_paths.append(source_path)

    legacy = matrix.get("legacy_v21_identity_lineage")
    if (
        not isinstance(legacy, dict)
        or legacy.get("ref") != GLOBAL_SKILL_MATRIX_PREDECESSOR
        or legacy.get("role") != "HISTORY_ONLY_NOT_CURRENT_SKILL_SCOPE"
        or HEX64.fullmatch(str(legacy.get("sha256", ""))) is None
    ):
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_G2_LEGACY_SKILL_LINEAGE_BINDING",
            "$.skill_bindings.legacy_v21_identity_lineage",
        )
    legacy_path = safe_repo_path(
        repo_root,
        GLOBAL_SKILL_MATRIX_PREDECESSOR,
        "$.skill_bindings.legacy_v21_identity_lineage.ref",
    )
    if not legacy_path.is_file() or sha256_file(legacy_path) != legacy["sha256"]:
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_G2_LEGACY_SKILL_LINEAGE_HASH_DRIFT",
            "$.skill_bindings.legacy_v21_identity_lineage.sha256",
        )
    tracked_paths.append(legacy_path)
    return tracked_paths


def _validate_consumer_postimages(
    matrix: dict[str, Any],
    *,
    repo_root: Path,
    request: dict[str, Any],
    downstream: dict[str, Any],
) -> list[Path]:
    consumers = matrix.get("consumers")
    if not isinstance(consumers, list):
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_CONSUMER_REBIND_MATRIX_INVALID",
            "$.package_bindings.consumer_rebind_matrix",
        )
    by_path = {item.get("path"): item for item in consumers if isinstance(item, dict)}
    if len(by_path) != len(consumers) or not GLOBAL_REQUIRED_ACTIVE_CONSUMERS.issubset(set(by_path)):
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_ACTIVE_CONSUMER_REBIND_COVERAGE",
            "$.package_bindings.consumer_rebind_matrix",
        )
    if matrix.get("state") != "CANDIDATE_REBIND_EVIDENCE":
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_OLD_G2_PLAN_ONLY_SEMANTICS",
            "$.package_bindings.consumer_rebind_matrix.state",
        )
    if (
        by_path[GLOBAL_RETIRED_ADAPTER].get("action")
        != "RETIRE_FROM_ACTIVE_PATH; retain historical compatibility only"
        or by_path["runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json"].get("action")
        != "G4_LAST_STEP_ONLY_AFTER_G1_G3_AND_PROMOTION_AUTHORITY"
        or matrix.get("history_policy")
        != "V2.1 strings in evidence, receipts, preimages, release archives, migration history, and legacy adapters are not rewritten merely to remove the version number."
    ):
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_ACTIVE_CONSUMER_REBIND_POLICY",
            "$.package_bindings.consumer_rebind_matrix",
        )

    postimage_paths: list[Path] = []
    postimage_hashes: dict[str, str] = {}
    skill_matrix_path: Path | None = None
    for consumer_ref, expected_preimage in GLOBAL_POSTIMAGE_CONSUMER_PREIMAGES.items():
        item = by_path[consumer_ref]
        base_path = f"$.package_bindings.consumer_rebind_matrix.consumers[{consumer_ref}]"
        if item.get("preimage_sha256") != expected_preimage:
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_CONSUMER_PREIMAGE_BINDING",
                f"{base_path}.preimage_sha256",
            )
        postimage_ref = item.get("postimage_ref")
        postimage_sha256 = item.get("postimage_sha256")
        if not isinstance(postimage_ref, str) or HEX64.fullmatch(str(postimage_sha256 or "")) is None:
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_CONSUMER_POSTIMAGE_EVIDENCE_MISSING",
                base_path,
            )
        if consumer_ref == GLOBAL_SKILL_MATRIX_PREDECESSOR:
            if (
                postimage_ref == consumer_ref
                or not postimage_ref.startswith("manifests/total_field/")
                or not postimage_ref.endswith("/BINDING_MATRIX.json")
            ):
                raise SuccessorRebindReviewError(
                    DECISION_REJECTED,
                    "REJECT_CONSUMER_POSTIMAGE_PATH_MISMATCH",
                    f"{base_path}.postimage_ref",
                )
        elif postimage_ref != consumer_ref:
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_CONSUMER_POSTIMAGE_PATH_MISMATCH",
                f"{base_path}.postimage_ref",
            )
        postimage = safe_repo_path(repo_root, postimage_ref, f"{base_path}.postimage_ref")
        if not postimage.is_file() or sha256_file(postimage) != postimage_sha256:
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_CONSUMER_POSTIMAGE_HASH_DRIFT",
                f"{base_path}.postimage_sha256",
            )
        if consumer_ref != GLOBAL_RETIRED_ADAPTER and postimage_sha256 == expected_preimage:
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_CONSUMER_POSTIMAGE_NOT_REBOUND",
                f"{base_path}.postimage_sha256",
            )
        if item.get("downstream_validation") != "PASS":
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_CONSUMER_DOWNSTREAM_VALIDATION_MISSING",
                f"{base_path}.downstream_validation",
            )
        _validate_content_constraints(item, postimage.read_bytes(), path=base_path)
        required_literals = item["content_constraints"]["required_literals"]
        if (
            consumer_ref not in {GLOBAL_RETIRED_ADAPTER, GLOBAL_SKILL_MATRIX_PREDECESSOR}
            and GLOBAL_ACTIVE_BINDING_LITERAL not in required_literals
        ):
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_CONSUMER_ACTIVE_POINTER_BINDING_CONSTRAINT_MISSING",
                f"{base_path}.content_constraints.required_literals",
            )
        if consumer_ref != GLOBAL_RETIRED_ADAPTER and not GLOBAL_OLD_ACTIVE_DIMENSION_LITERALS.issubset(
            set(item["content_constraints"]["forbidden_literals"])
        ):
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_OLD_ACTIVE_DIMENSION_CONSTRAINT_MISSING",
                f"{base_path}.content_constraints.forbidden_literals",
            )
        if consumer_ref == "tools/total_field/w7tp_intent_field_suite/cli.py":
            required_forbidden = {
                GLOBAL_RETIRED_ADAPTER,
                GLOBAL_SKILL_MATRIX_PREDECESSOR,
            }
            if not required_forbidden.issubset(set(item["content_constraints"]["forbidden_literals"])):
                raise SuccessorRebindReviewError(
                    DECISION_REJECTED,
                    "REJECT_CLI_ACTIVE_RELEASE_RETIREMENT_CONSTRAINT_MISSING",
                    f"{base_path}.content_constraints.forbidden_literals",
                )
        postimage_paths.append(postimage)
        postimage_hashes[consumer_ref] = postimage_sha256
        if consumer_ref == GLOBAL_SKILL_MATRIX_PREDECESSOR:
            skill_matrix_path = postimage

    if skill_matrix_path is None:
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_G2_FIVE_SKILL_SUCCESSOR_MATRIX",
            "$.package_bindings.consumer_rebind_matrix",
        )
    receipt_path = safe_repo_path(
        repo_root,
        downstream["receipt_ref"],
        "$.package_bindings.current_field_successor.downstream_validation.receipt_ref",
    )
    if not receipt_path.is_file() or sha256_file(receipt_path) != downstream["receipt_sha256"]:
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_G2_DOWNSTREAM_RECEIPT_HASH_DRIFT",
            "$.package_bindings.current_field_successor.downstream_validation.receipt_sha256",
        )
    receipt = load_object(receipt_path, "G2_DOWNSTREAM_RECEIPT")
    if (
        receipt.get("schema_id") != "W7TP_T007_GLOBAL_SUCCESSOR_REVIEWER_EXTENSION_REOBSERVATION_V1"
        or receipt.get("task_id") != "T-007"
        or receipt.get("node") != "taiji01"
        or receipt.get("scope") != GLOBAL_REVIEW_SCOPE
        or receipt.get("state") != "GLOBAL_CANONICAL_SUCCESSOR_MODE_IMPLEMENTED"
        or receipt.get("result") != "PASS"
    ):
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_G2_GLOBAL_DOWNSTREAM_RECEIPT_SCOPE",
            "$.package_bindings.current_field_successor.downstream_validation",
        )
    if (
        receipt.get("consumer_postimages") != postimage_hashes
        or receipt.get("current_field_preimages")
        != {
            "current_field": request["live_bindings"]["current_field"],
            "current_field_router": request["live_bindings"]["current_field_router"],
        }
        or receipt.get("dynamic_context") != request["dynamic_context"]
    ):
        raise SuccessorRebindReviewError(
            DECISION_REJECTED,
            "REJECT_G2_DOWNSTREAM_ARTIFACT_BINDING_MISMATCH",
            "$.package_bindings.current_field_successor.downstream_validation",
        )
    return [
        *postimage_paths,
        *_validate_skill_successor_matrix(skill_matrix_path, repo_root=repo_root),
        receipt_path,
    ]


def _review_global_once(
    *,
    request: dict[str, Any],
    request_path: Path,
    request_sha256: str,
    repo_root: Path,
    reviewed_at: datetime,
    output_dir: Path | None,
    replay_root: Path | None,
    test_mode: bool,
    tracked_checker: Callable[[Path], bool],
    native_adi_loader: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    checks = {
        "schema": "NOT_REACHED",
        "self_hash": "NOT_REACHED",
        "freshness": "NOT_REACHED",
        "predecessor_pointer": "NOT_REACHED",
        "manifest": "NOT_REACHED",
        "completion_manifest": "NOT_REACHED",
        "package_bindings": "NOT_REACHED",
        "successor_contract": "NOT_REACHED",
        "current_field_successor": "NOT_REACHED",
        "consumer_rebind_matrix": "NOT_REACHED",
        "consumer_postimages": "NOT_REACHED",
        "skill_scope_bindings": "NOT_REACHED",
        "authority_successor_receipt": "NOT_REACHED",
        "dynamic_context": "NOT_REACHED",
        "founder_authorization": "NOT_REACHED",
        "authority_pointer": "NOT_REACHED",
        "replay": "NOT_REACHED",
        "candidate_only": "NOT_REACHED",
        "tracked_inputs": "NOT_REACHED",
    }
    try:
        validate_schema(
            request,
            _schema_path(repo_root, "w7tp_total_field_successor_rebind_review_request_v2.schema.json"),
            "GLOBAL_REQUEST",
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
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_NONCE_OR_REPLAY_SCHEMA",
                "$.nonce",
            )

        canonical = safe_repo_path(repo_root, request["canonical_ref"], "$.canonical_ref")
        if not canonical.is_file() or sha256_file(canonical) != request["predecessor_pointer_sha256"]:
            raise SuccessorRebindReviewError(
                DECISION_HOLD,
                "HOLD_CANONICAL_PREIMAGE_HASH_OR_PATH",
                "$.predecessor_pointer_sha256",
            )
        canonical_pointer = load_object(canonical, "CANONICAL_POINTER")
        if canonical_pointer.get("state") != "ACTIVE_CANONICAL" or canonical_pointer.get("version") != "2.1":
            raise SuccessorRebindReviewError(
                DECISION_HOLD,
                "HOLD_CANONICAL_V2_1_NOT_ACTIVE",
                "$.canonical_ref",
            )
        checks["predecessor_pointer"] = "PASS"

        candidate_root = safe_repo_path(repo_root, request["candidate_root"], "$.candidate_root")
        manifest_path = candidate_root / "SHA256_MANIFEST.json"
        if not candidate_root.is_dir() or not manifest_path.is_file():
            raise SuccessorRebindReviewError(
                DECISION_HOLD,
                "HOLD_CANDIDATE_OR_MANIFEST_MISSING",
                "$.candidate_root",
            )
        if sha256_file(manifest_path) != request["manifest_sha256"]:
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_MANIFEST_HASH_DRIFT",
                "$.manifest_sha256",
            )
        manifest = load_object(manifest_path, "MANIFEST")
        if manifest.get("run_id") != request["run_id"]:
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_GLOBAL_RUN_ID_MISMATCH",
                "$.run_id",
            )
        if any((candidate_root / name).exists() for name in FORBIDDEN_FORMAL_ARTIFACTS):
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_CANDIDATE_SELF_FORMAL_AUTHORITY",
                "$.candidate_root",
            )
        checks["manifest"] = "PASS"

        completion_manifest_path, completion_manifest, completion_paths = _validate_completion_manifest(
            repo_root=repo_root,
            candidate_root_ref=request["candidate_root"],
        )
        completion_manifest_sha256 = sha256_file(completion_manifest_path)
        completion_manifest_files = completion_manifest["files"]
        checks["completion_manifest"] = "PASS"

        package_docs: dict[str, dict[str, Any]] = {}
        tracked_package_paths: list[Path] = []
        manifest_files = manifest.get("files")
        if not isinstance(manifest_files, dict):
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_GLOBAL_MANIFEST_FILES_INVALID",
                "$.manifest.files",
            )
        for key, filename in GLOBAL_REQUIRED_PACKAGE_FILES.items():
            binding = request["package_bindings"][key]
            expected_ref = (Path(request["candidate_root"]) / filename).as_posix()
            if binding["ref"] != expected_ref:
                raise SuccessorRebindReviewError(
                    DECISION_REJECTED,
                    "REJECT_GLOBAL_PACKAGE_REF_MISMATCH",
                    f"$.package_bindings.{key}.ref",
                )
            path = safe_repo_path(repo_root, binding["ref"], f"$.package_bindings.{key}.ref")
            if not path.is_file() or sha256_file(path) != binding["sha256"]:
                raise SuccessorRebindReviewError(
                    DECISION_REJECTED,
                    "REJECT_GLOBAL_PACKAGE_HASH_DRIFT",
                    f"$.package_bindings.{key}.sha256",
                )
            if filename.startswith(GLOBAL_REVIEW_COMPLETION_DIR + "/"):
                manifest_binding = _manifest_entry_sha256(
                    completion_manifest_files,
                    Path(filename).name,
                )
            else:
                manifest_binding = _manifest_entry_sha256(manifest_files, filename)
            if manifest_binding != binding["sha256"]:
                raise SuccessorRebindReviewError(
                    DECISION_REJECTED,
                    "REJECT_GLOBAL_MANIFEST_BINDING_MISMATCH",
                    f"$.package_bindings.{key}",
                )
            package_docs[key] = load_object(path, f"GLOBAL_{key.upper()}")
            tracked_package_paths.append(path)
        checks["package_bindings"] = "PASS"

        directive = package_docs["founder_directive"]
        if (
            directive.get("founder") != "江政隆"
            or directive.get("run_id") != request["run_id"]
            or directive.get("state") != "USER_EXPLICIT_FOUNDER_DIRECTIVE"
            or directive.get("replacement_boundary", {}).get("replace_active_v21_authority_consumption") is not True
            or directive.get("replacement_boundary", {}).get("replace_active_v21_runtime_consumption") is not True
            or directive.get("replacement_boundary", {}).get("replace_active_v21_skill_binding") is not True
            or directive.get("replacement_boundary", {}).get("preserve_historical_v21_evidence") is not True
        ):
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_FOUNDER_DIRECTIVE_SCOPE_MISMATCH",
                "$.package_bindings.founder_directive",
            )

        root_contract_name = "01_V23_GLOBAL_SUCCESSOR_CONTRACT_CANDIDATE.json"
        root_contract_ref = (Path(request["candidate_root"]) / root_contract_name).as_posix()
        root_contract_sha256 = _manifest_entry_sha256(manifest_files, root_contract_name)
        root_contract_path = safe_repo_path(repo_root, root_contract_ref, "$.root_successor_contract")
        if (
            root_contract_sha256 is None
            or not root_contract_path.is_file()
            or sha256_file(root_contract_path) != root_contract_sha256
        ):
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_ROOT_SUCCESSOR_CONTRACT_HASH_DRIFT",
                "$.root_successor_contract",
            )
        contract = load_object(root_contract_path, "ROOT_SUCCESSOR_CONTRACT")
        predecessor = contract.get("predecessor", {})
        successor = contract.get("proposed_successor", {})
        dims = successor.get("dimension_contract", {})
        expected_dims = {
            "D1": "Intent",
            "D2": "State",
            "D3": "Coordinate",
            "D4": "Evidence",
            "D5": "Execution/Policy",
            "D6": "Generative State Transmission",
            "D7": "Risk/Isolation",
            "D8": "Envelope/Authority",
        }
        if (
            contract.get("state") != "CANDIDATE_FOR_FORMAL_TOTAL_FIELD_REVIEW"
            or contract.get("task_id") != "T-007"
            or contract.get("migration_mode") != "APPEND_ONLY_SUCCESSOR"
            or predecessor.get("pointer_ref") != request["canonical_ref"]
            or predecessor.get("pointer_sha256") != request["predecessor_pointer_sha256"]
            or predecessor.get("version") != "2.1"
            or successor.get("version") != "2.3"
            or successor.get("canonical_id") != GLOBAL_SUCCESSOR_ID
            or any(dims.get(k) != v for k, v in expected_dims.items())
            or dims.get("mode") != "8_IN_1_SINGLE_DYNAMIC_STATE_FIELD"
            or dims.get("sequential_pipeline_definition_forbidden") is not True
            or successor.get("d6_contract", {}).get("difference_analysis_is_transmission") is not False
        ):
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_GLOBAL_SUCCESSOR_CONTRACT_SEMANTICS",
                "$.package_bindings.successor_contract",
            )
        _validate_completion_contract(
            package_docs["successor_contract"],
            request=request,
            root_contract_ref=root_contract_ref,
            root_contract_sha256=root_contract_sha256,
            field_binding=request["package_bindings"]["current_field_successor"],
            authority_binding=request["package_bindings"]["authority_successor_receipt"],
        )
        tracked_package_paths.append(root_contract_path)
        checks["successor_contract"] = "PASS"

        live_paths: list[Path] = []
        for key, expected_ref in {
            "current_field": "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_CANONICAL.json",
            "current_field_router": "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json",
            "total_field_authority": "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json",
        }.items():
            binding = request["live_bindings"][key]
            if binding["ref"] != expected_ref:
                raise SuccessorRebindReviewError(
                    DECISION_REJECTED,
                    "REJECT_GLOBAL_LIVE_REF_MISMATCH",
                    f"$.live_bindings.{key}.ref",
                )
            path = safe_repo_path(repo_root, binding["ref"], f"$.live_bindings.{key}.ref")
            if not path.is_file() or sha256_file(path) != binding["sha256"]:
                raise SuccessorRebindReviewError(
                    DECISION_HOLD,
                    "HOLD_GLOBAL_LIVE_HASH_DRIFT",
                    f"$.live_bindings.{key}.sha256",
                )
            live_paths.append(path)

        root_field_name = "02_CURRENT_8D_FIELD_V23_SUCCESSOR_CANDIDATE.json"
        root_field_ref = (Path(request["candidate_root"]) / root_field_name).as_posix()
        root_field_sha256 = _manifest_entry_sha256(manifest_files, root_field_name)
        root_field_path = safe_repo_path(repo_root, root_field_ref, "$.root_current_field_successor")
        if (
            root_field_sha256 is None
            or not root_field_path.is_file()
            or sha256_file(root_field_path) != root_field_sha256
        ):
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_ROOT_CURRENT_FIELD_HASH_DRIFT",
                "$.root_current_field_successor",
            )
        downstream_validation = _validate_current_field_sidecar(
            package_docs["current_field_successor"],
            request=request,
            candidate_root_ref=request["candidate_root"],
            founder_sha256=request["package_bindings"]["founder_directive"]["sha256"],
            root_field_sha256=root_field_sha256,
        )
        tracked_package_paths.append(root_field_path)
        checks["current_field_successor"] = "PASS"

        matrix = package_docs["consumer_rebind_matrix"]
        consumer_evidence_paths = _validate_consumer_postimages(
            matrix,
            repo_root=repo_root,
            request=request,
            downstream=downstream_validation,
        )
        checks["consumer_rebind_matrix"] = "PASS"
        checks["consumer_postimages"] = "PASS"
        checks["skill_scope_bindings"] = "PASS"

        authority_path = safe_repo_path(repo_root, request["authority_pointer_ref"], "$.authority_pointer_ref")
        if not authority_path.is_file() or sha256_file(authority_path) != request["authority_pointer_sha256"]:
            raise SuccessorRebindReviewError(
                DECISION_HOLD,
                "HOLD_AUTHORITY_POINTER_HASH_OR_PATH",
                "$.authority_pointer_ref",
            )
        if request["live_bindings"]["total_field_authority"]["sha256"] != request["authority_pointer_sha256"]:
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_AUTHORITY_LIVE_BINDING_MISMATCH",
                "$.live_bindings.total_field_authority",
            )
        authority = load_object(authority_path, "AUTHORITY_POINTER")
        formal_authority = _validate_authority(authority, test_mode=test_mode)
        if not test_mode:
            try:
                validate_authority_binding(authority, required_effect=FORMAL_FOUNDER_EFFECT)
            except AuthorityBindingValidationError as exc:
                raise SuccessorRebindReviewError(
                    DECISION_HOLD,
                    "HOLD_FORMAL_AUTHORITY_EFFECT_NOT_BOUND",
                    "$.authority_pointer.allowed_effects",
                ) from exc
        checks["authority_pointer"] = "PASS"

        authority_receipt = package_docs["authority_successor_receipt"]
        equal_fields = authority_receipt.get("non_effect_fields_equal", {})
        append_only = authority_receipt.get("append_only_policy", {})
        if (
            authority_receipt.get("schema_id") != "W7TP_AUTHORITY_SUCCESSOR_EVIDENCE_CANDIDATE_V2"
            or authority_receipt.get("state") != "CANDIDATE_NOT_FORMAL"
            or authority_receipt.get("formal") is not False
            or authority_receipt.get("removed_effects") != []
            or authority_receipt.get("successor", {}).get("ref") != request["authority_pointer_ref"]
            or authority_receipt.get("successor", {}).get("sha256") != request["authority_pointer_sha256"]
            or any(
                equal_fields.get(key) is not True
                for key in (
                    "contract_state",
                    "formal_decision_authority",
                    "formal_seal_authority",
                    "node_id",
                    "prohibited_effects",
                    "state",
                )
            )
            or append_only.get("overwrite_predecessor") is not False
            or append_only.get("rewrite_gst_d8") is not False
            or append_only.get("grant_added_effects_by_this_receipt") is not False
            or authority_receipt.get("formal_acceptance_ref") is not None
            or authority_receipt.get("original_transition_event_ref") is not None
        ):
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_AUTHORITY_SUCCESSOR_RECEIPT_SCOPE",
                "$.package_bindings.authority_successor_receipt",
            )
        checks["authority_successor_receipt"] = "PASS"

        founder_path = safe_repo_path(
            repo_root,
            request["founder_authorization_ref"],
            "$.founder_authorization_ref",
        )
        if not founder_path.is_file() or sha256_file(founder_path) != request["founder_authorization_sha256"]:
            raise SuccessorRebindReviewError(
                DECISION_HOLD,
                "HOLD_FOUNDER_AUTHORIZATION_HASH_OR_PATH",
                "$.founder_authorization_ref",
            )
        founder_support_paths = _validate_global_founder_authorization(
            load_object(founder_path, "FOUNDER_AUTHORIZATION"),
            request,
            reviewed_at,
            repo_root=repo_root,
            test_mode=test_mode,
        )
        checks["founder_authorization"] = "PASS"

        atom = native_adi_loader(request["dynamic_context"]["adi_record_id"])
        _validate_global_dynamic_context(request, atom, reviewed_at)
        checks["dynamic_context"] = "PASS"

        if request["contract_mode"] == "FORMAL_REVIEW" and test_mode:
            raise SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_TEST_MODE_FORMAL_REQUEST",
                "$.contract_mode",
            )
        if request["contract_mode"] != "FORMAL_REVIEW" and not test_mode:
            raise SuccessorRebindReviewError(
                DECISION_HOLD,
                "HOLD_CONTRACT_NOT_FORMALLY_ACTIVE",
                "$.contract_mode",
            )
        checks["candidate_only"] = "PASS"

        if _replay_seen(replay_root, request):
            checks["replay"] = "HOLD"
            raise SuccessorRebindReviewError(
                DECISION_HOLD,
                "HOLD_NONCE_REPLAY",
                "$.nonce",
            )
        if not test_mode and replay_root is None:
            raise SuccessorRebindReviewError(
                DECISION_HOLD,
                "HOLD_REPLAY_LEDGER_NOT_BOUND",
                "$.replay_guard.ledger_ref",
            )
        checks["replay"] = "PASS"

        tracked_inputs = [
            request_path,
            canonical,
            manifest_path,
            authority_path,
            founder_path,
            *founder_support_paths,
            *tracked_package_paths,
            *completion_paths,
            *consumer_evidence_paths,
            *live_paths,
        ]
        if not test_mode and not all(tracked_checker(path) for path in tracked_inputs):
            raise SuccessorRebindReviewError(
                DECISION_HOLD,
                "HOLD_UNTRACKED_FORMAL_INPUT",
                "$.tracked_inputs",
            )
        checks["tracked_inputs"] = "PASS"

        formal = bool(formal_authority and not test_mode)
        package_binding_sha256 = sha256_bytes(
            canonical_json_bytes(
                {
                    "package_bindings": request["package_bindings"],
                    "completion_manifest": {
                        "ref": completion_manifest_path.resolve().relative_to(repo_root).as_posix(),
                        "sha256": completion_manifest_sha256,
                    },
                }
            )
        )
        decision = {
            "schema_version": GLOBAL_DECISION_SCHEMA_VERSION,
            "packet_type": "TOTAL_FIELD_SUCCESSOR_REBIND_DECISION",
            "review_scope": GLOBAL_REVIEW_SCOPE,
            "decision_id": f"decision:{request['run_id']}:{request_sha256[:16]}",
            "request_id": request["request_id"],
            "run_id": request["run_id"],
            "reviewed_at": utc_text(reviewed_at),
            "state": _decision_state(DECISION_APPROVED),
            "decision": DECISION_APPROVED,
            "reason_codes": [
                "PASS_TEST_GLOBAL_SUCCESSOR_VECTOR_ONLY"
                if test_mode
                else "PASS_FORMAL_GLOBAL_CANONICAL_SUCCESSOR_REVIEW"
            ],
            "request_sha256": request_sha256,
            "manifest_sha256": request["manifest_sha256"],
            "predecessor_pointer_sha256": request["predecessor_pointer_sha256"],
            "predecessor_version": "2.1",
            "successor_version": "2.3",
            "package_binding_sha256": package_binding_sha256,
            "dynamic_context_record_id": request["dynamic_context"]["adi_record_id"],
            "dynamic_context_record_sha256": request["dynamic_context"]["record_sha256"],
            "authority_pointer_ref": request["authority_pointer_ref"],
            "authority_pointer_sha256": request["authority_pointer_sha256"],
            "formal": formal,
            "seal_eligible": True,
            "core_landing": CORE_LANDING,
            "decision_self_hash_algorithm": DECISION_SELF_HASH_ALGORITHM,
        }
        decision["decision_sha256"] = sha256_bytes(canonical_json_bytes(decision))
        receipt = {
            "schema_version": GLOBAL_RECEIPT_SCHEMA_VERSION,
            "packet_type": "TOTAL_FIELD_SUCCESSOR_REBIND_REVIEW_RECEIPT",
            "review_scope": GLOBAL_REVIEW_SCOPE,
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
            "package_binding_sha256": package_binding_sha256,
            "dynamic_context_record_id": request["dynamic_context"]["adi_record_id"],
            "dynamic_context_record_sha256": request["dynamic_context"]["record_sha256"],
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
        validate_schema(
            decision,
            _schema_path(repo_root, "w7tp_total_field_successor_rebind_decision_v2.schema.json"),
            "GLOBAL_DECISION",
        )
        validate_schema(
            receipt,
            _schema_path(repo_root, "w7tp_total_field_successor_rebind_receipt_v2.schema.json"),
            "GLOBAL_RECEIPT",
        )
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
    native_adi_loader: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Review one hash-bound request and emit only test artifacts until approved."""

    repo_root = repo_root.resolve()
    reviewed_at = (now or utc_now()).astimezone(timezone.utc)
    if not test_mode and any(
        value is not None
        for value in (source_loader, subject_loader, tracked_checker, native_adi_loader)
    ):
        return _fail_result(
            SuccessorRebindReviewError(
                DECISION_REJECTED,
                "REJECT_FORMAL_DEPENDENCY_INJECTION",
            )
        )
    source_loader = source_loader or (lambda commit, path: git_blob(repo_root, commit, path))
    subject_loader = subject_loader or (lambda commit: git_subject(repo_root, commit))
    tracked_checker = tracked_checker or (lambda path: git_tracked(repo_root, path))
    native_adi_loader = native_adi_loader or _load_native_adi_atom
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
        if request.get("schema_version") == GLOBAL_REQUEST_SCHEMA_VERSION:
            return _review_global_once(
                request=request,
                request_path=request_path,
                request_sha256=request_sha256,
                repo_root=repo_root,
                reviewed_at=reviewed_at,
                output_dir=output_dir,
                replay_root=replay_root,
                test_mode=test_mode,
                tracked_checker=tracked_checker,
                native_adi_loader=native_adi_loader,
            )
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
