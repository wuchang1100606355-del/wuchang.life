#!/usr/bin/env python3
"""Fail-closed 8DADI target lock and Total Field rule-application gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field_dynamic_context import build_dynamic_context

CONFIG_REL = Path("configs/total_field/mandatory_application_gate_v1.json")
PASSKEY_GATE_CONFIG_REL = Path("configs/total_field/git_push_review_gate_v1.json")
PASS_STATE = "PASS_TOTAL_FIELD_RULE_APPLICATION_REVIEW"
HOLD_STATE = "HOLD_TOTAL_FIELD_RULE_APPLICATION_REVIEW"
REVIEW_SCHEMA = "W7TP_8DADI_COMPLETED_CHANGE_REVIEW_V1"
REVIEW_STATE = "PASS_TOTAL_FIELD_COMPLETED_CHANGE_REVIEW"


class MandatoryApplicationRejected(RuntimeError):
    pass


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise MandatoryApplicationRejected("GIT_COORDINATE_UNAVAILABLE")
    return result.stdout.strip()


def _git_bytes(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise MandatoryApplicationRejected("GIT_CHANGE_SET_UNAVAILABLE")
    return result.stdout


def _safe_path(root: Path, relative_value: Any) -> Path:
    if not isinstance(relative_value, str) or not relative_value:
        raise MandatoryApplicationRejected("LOCAL_RULE_REF_INVALID")
    relative = PurePosixPath(relative_value)
    if relative.is_absolute() or ".." in relative.parts:
        raise MandatoryApplicationRejected("LOCAL_RULE_REF_INVALID")
    candidate = root.joinpath(*relative.parts)
    try:
        candidate.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise MandatoryApplicationRejected("LOCAL_RULE_REF_OUTSIDE_ROOT") from exc
    return candidate


def _load_config(root: Path) -> dict[str, Any]:
    path = root / CONFIG_REL
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MandatoryApplicationRejected("MANDATORY_GATE_CONFIG_INVALID") from exc
    if (
        not isinstance(config, dict)
        or config.get("schema_id") != "W7TP_8DADI_MANDATORY_APPLICATION_GATE_V1"
        or config.get("state") != "ACTIVE_FAIL_CLOSED"
        or config.get("authority") != "TOTAL_FIELD_RULE_APPLICATION_REVIEW"
    ):
        raise MandatoryApplicationRejected("MANDATORY_GATE_NOT_ACTIVE")
    return config


def _coordinates(root: Path) -> dict[str, str]:
    return {
        "repo_root": str(root),
        "branch": _git(root, "symbolic-ref", "--quiet", "--short", "HEAD"),
        "head": _git(root, "rev-parse", "HEAD"),
        "tree": _git(root, "rev-parse", "HEAD^{tree}"),
    }


def _nul_paths(payload: bytes) -> set[str]:
    paths: set[str] = set()
    for raw in payload.split(b"\0"):
        if not raw:
            continue
        try:
            value = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MandatoryApplicationRejected("CHANGE_PATH_NOT_UTF8") from exc
        relative = PurePosixPath(value)
        if relative.is_absolute() or ".." in relative.parts:
            raise MandatoryApplicationRejected("CHANGE_PATH_INVALID")
        paths.add(relative.as_posix())
    return paths


def changed_paths(root: Path) -> list[str]:
    paths = _nul_paths(
        _git_bytes(root, "diff", "--cached", "--name-only", "--no-renames", "-z", "--")
    )
    paths.update(_nul_paths(_git_bytes(root, "diff", "--name-only", "--no-renames", "-z", "--")))
    paths.update(_nul_paths(_git_bytes(root, "ls-files", "--others", "--exclude-standard", "-z", "--")))
    return sorted(paths)


def change_bindings(root: Path) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    for relative in changed_paths(root):
        path = _safe_path(root, relative)
        if path.is_symlink():
            raise MandatoryApplicationRejected("CHANGED_SYMLINK_BLOCKED")
        if not path.exists():
            bindings.append({"path": relative, "state": "DELETED", "sha256": None, "mode": None})
        elif path.is_file():
            bindings.append(
                {
                    "path": relative,
                    "state": "PRESENT",
                    "sha256": _sha256(path.read_bytes()),
                    "mode": oct(path.stat().st_mode & 0o777),
                }
            )
        elif path.is_dir():
            raise MandatoryApplicationRejected("CHANGED_DIRECTORY_UNSUPPORTED")
        else:
            raise MandatoryApplicationRejected("CHANGED_PATH_TYPE_UNSUPPORTED")
    return bindings


def _rule_bindings(root: Path, config: Mapping[str, Any]) -> tuple[list[dict[str, str]], str]:
    refs = config.get("required_local_rule_refs")
    if not isinstance(refs, list) or not refs:
        raise MandatoryApplicationRejected("LOCAL_RULE_REFS_MISSING")
    bindings: list[dict[str, str]] = []
    for ref in refs:
        path = _safe_path(root, ref)
        if not path.is_file() or path.is_symlink():
            raise MandatoryApplicationRejected("LOCAL_RULE_SOURCE_INVALID")
        payload = path.read_bytes()
        if not payload:
            raise MandatoryApplicationRejected("LOCAL_RULE_SOURCE_EMPTY")
        bindings.append({"ref": str(ref), "sha256": _sha256(payload)})
    return bindings, _sha256(_canonical_json({"bindings": bindings}))


def _context_projection(packet: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "founder_intent_projection",
        "intent_translation_application_rules",
        "work_target_lock_contract",
        "adi_discrete_integer_lookup_math_contract",
    )
    if any(key not in packet for key in required):
        raise MandatoryApplicationRejected("DYNAMIC_CONTEXT_REQUIRED_PROJECTION_MISSING")
    founder_intent = packet["founder_intent_projection"]
    if not isinstance(founder_intent, Mapping):
        raise MandatoryApplicationRejected("CURRENT_FOUNDER_INTENT_REQUIRED")
    if (founder_intent.get("target_lock") or {}).get("locked") is not True:
        raise MandatoryApplicationRejected("CURRENT_FOUNDER_TARGET_NOT_LOCKED")
    if (founder_intent.get("D8") or {}).get("this_target_lock_grants_external_effect") is not False:
        raise MandatoryApplicationRejected("FOUNDER_TARGET_LOCK_AUTHORITY_BOUNDARY_INVALID")
    target_lock = packet["work_target_lock_contract"]
    if (
        not isinstance(target_lock, Mapping)
        or target_lock.get("model_tool_cloud_or_historical_evidence_may_change_target") is not False
    ):
        raise MandatoryApplicationRejected("TOTAL_FIELD_WORK_TARGET_LOCK_INVALID")
    return {
        "schema_id": "W7TP_8DADI_AI_LOCAL_RULE_CONTEXT_V1",
        "state": "REVIEWED_IN_MEMORY_AI_CONTEXT",
        "authority": "TOTAL_FIELD_RULE_APPLICATION_REVIEW_NO_EFFECT_AUTHORITY",
        "ai_role": "REPLACEABLE_CANDIDATE_REASONING_ORGAN",
        "ai_output_state": "CANDIDATE_ONLY",
        "ai_may_self_authorize": False,
        "ai_may_write_deploy_activate_or_promote": False,
        "dynamic_context_provider": "TOTAL_FIELD",
        "founder_live_input_is_intent_input_not_rule_authority": True,
        "founder_intent_projection": founder_intent,
        "intent_translation_application_rules": packet["intent_translation_application_rules"],
        "work_target_lock_contract": target_lock,
        "adi_discrete_integer_lookup_math_contract": packet[
            "adi_discrete_integer_lookup_math_contract"
        ],
    }


def _review_dynamic_context(
    *,
    root: Path,
    config: Mapping[str, Any],
    query: str,
    context_builder: Callable[..., Mapping[str, Any]],
) -> tuple[dict[str, Any], str]:
    packet = context_builder(query, root=root, max_items=8, identity_class="founder")
    if not isinstance(packet, Mapping):
        raise MandatoryApplicationRejected("DYNAMIC_CONTEXT_INVALID")
    expected = config.get("required_dynamic_context")
    if not isinstance(expected, Mapping) or any(packet.get(key) != value for key, value in expected.items()):
        raise MandatoryApplicationRejected(str(packet.get("state") or "DYNAMIC_CONTEXT_REVIEW_FAILED"))
    projection = _context_projection(packet)
    return projection, _sha256(_canonical_json(projection))


def _work_target_binding(
    query: str,
    coordinates: Mapping[str, str],
    projection: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    if not query.strip():
        raise MandatoryApplicationRejected("WORK_TARGET_QUERY_MISSING")
    binding = {
        "schema_id": "W7TP_8DADI_WORK_TARGET_LOCK_V1",
        "query_sha256": _sha256(query.encode("utf-8")),
        "branch": coordinates["branch"],
        "base_head": coordinates["head"],
        "base_tree": coordinates["tree"],
        "founder_intent_projection": projection["founder_intent_projection"],
        "work_target_lock_contract": projection["work_target_lock_contract"],
    }
    return binding, _sha256(_canonical_json(binding))


def _resolve_passkey_effect_authority(
    root: Path,
    required_scope: str,
) -> Mapping[str, Any]:
    try:
        gate_config = json.loads((root / PASSKEY_GATE_CONFIG_REL).read_text(encoding="utf-8"))
        passkey_config = gate_config["passkey_verifier"]
        if not isinstance(passkey_config, Mapping):
            raise KeyError("passkey_verifier")
        python_runtime = passkey_config.get("python_runtime")
        if not isinstance(python_runtime, str) or not Path(python_runtime).is_absolute():
            raise ValueError("passkey python runtime")
        completed = subprocess.run(
            [
                python_runtime,
                str(root / "tools/total_field_passkey_d8.py"),
                "--repo-root",
                str(root),
                "--gate-config",
                PASSKEY_GATE_CONFIG_REL.as_posix(),
                "--required-scope",
                required_scope,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
        )
        result = json.loads(completed.stdout)
        if not isinstance(result, Mapping):
            raise TypeError("passkey result")
        return result
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return {
            "state": "HOLD_DEVICE_PASSKEY_D8_AUTHORITY",
            "authority_verified": False,
            "reason": "PASSKEY_EFFECT_AUTHORITY_UNAVAILABLE",
            "scope": [],
        }


def _validate_effect_authority(
    root: Path,
    operation: str,
    operation_policy: Mapping[str, Any],
    effect_authority: Mapping[str, Any] | None,
) -> None:
    required_scope = operation_policy.get("required_scope")
    if required_scope == "UNAVAILABLE_FAIL_CLOSED":
        raise MandatoryApplicationRejected("EFFECT_SCOPE_UNAVAILABLE_FAIL_CLOSED")
    if operation == "HOURLY_REVIEWED_COMMIT":
        resolved_authority = effect_authority
    else:
        if effect_authority is not None:
            raise MandatoryApplicationRejected("CALLER_SUPPLIED_EFFECT_AUTHORITY_FORBIDDEN")
        resolved_authority = _resolve_passkey_effect_authority(root, str(required_scope))
    required_state = operation_policy.get(
        "required_authority_state", "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED"
    )
    if (
        not isinstance(resolved_authority, Mapping)
        or resolved_authority.get("state") != required_state
        or resolved_authority.get("authority_verified") is not True
        or required_scope not in (resolved_authority.get("scope") or [])
    ):
        raise MandatoryApplicationRejected("TOTAL_FIELD_D8_REQUIRED")


def _completed_change_review(
    *,
    coordinates: Mapping[str, str],
    query: str,
    target_sha256: str,
    rules_sha256: str,
    dynamic_context_sha256: str,
    bindings: list[dict[str, Any]],
) -> dict[str, Any]:
    if not bindings:
        raise MandatoryApplicationRejected("NO_COMPLETED_CHANGE_TO_REVIEW")
    packet: dict[str, Any] = {
        "schema_id": REVIEW_SCHEMA,
        "state": REVIEW_STATE,
        "review_registered": True,
        "effect_authority": False,
        "push_authorized": False,
        "deploy_authorized": False,
        "canonical_mutation_authorized": False,
        "active_pointer_mutation_authorized": False,
        "branch": coordinates["branch"],
        "base_head": coordinates["head"],
        "base_tree": coordinates["tree"],
        "work_target_query": query,
        "work_target_sha256": target_sha256,
        "local_rules_sha256": rules_sha256,
        "dynamic_context_sha256": dynamic_context_sha256,
        "change_bindings": bindings,
        "changed_paths_sha256": _sha256(
            ("\n".join(item["path"] for item in bindings) + "\n").encode("utf-8")
        ),
    }
    packet["review_sha256"] = _sha256(_canonical_json(packet))
    return packet


def scan_operation(
    *,
    repo_root: str | Path,
    operation: str,
    actor_class: str,
    query: str,
    expected_branch: str | None = None,
    expected_head: str | None = None,
    expected_tree: str | None = None,
    expected_work_target_sha256: str | None = None,
    context_builder: Callable[..., Mapping[str, Any]] = build_dynamic_context,
    effect_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    denied = {
        "operation_authorized": False,
        "ai_effect_authorized": False,
        "git_push_authorized": False,
        "deploy_authorized": False,
        "restart_authorized": False,
        "db_write_authorized": False,
        "adi_write_authorized": False,
        "canonical_mutation_authorized": False,
        "active_pointer_mutation_authorized": False,
        "promotion_authorized": False,
        "activation_authorized": False,
        "delete_or_overwrite_authorized": False,
    }
    try:
        config = _load_config(root)
        operations = config.get("operations")
        if not isinstance(operations, Mapping) or operation not in operations:
            raise MandatoryApplicationRejected("OPERATION_NOT_REGISTERED")
        operation_policy = operations[operation]
        if not isinstance(operation_policy, Mapping):
            raise MandatoryApplicationRejected("OPERATION_POLICY_INVALID")
        before = _coordinates(root)
        bindings = change_bindings(root)
        if config.get("policy", {}).get("clean_worktree_required") is not True:
            raise MandatoryApplicationRejected("CLEAN_WORKTREE_POLICY_NOT_ACTIVE")
        if operation_policy.get("require_clean_worktree") is not False and bindings:
            raise MandatoryApplicationRejected("DIRTY_WORKTREE_BLOCKED")
        expected_values = {"branch": expected_branch, "head": expected_head, "tree": expected_tree}
        if any(value is not None and before[key] != value for key, value in expected_values.items()):
            raise MandatoryApplicationRejected("EXPECTED_COORDINATE_DRIFT")
        rules, rules_digest = _rule_bindings(root, config)
        projection, projection_digest = _review_dynamic_context(
            root=root, config=config, query=query, context_builder=context_builder
        )
        target_binding, target_digest = _work_target_binding(query, before, projection)
        if operation_policy.get("require_expected_work_target") is True:
            if not expected_work_target_sha256:
                raise MandatoryApplicationRejected("WORK_TARGET_LOCK_REQUIRED")
            if target_digest != expected_work_target_sha256:
                raise MandatoryApplicationRejected("WORK_TARGET_DRIFT")
        after = _coordinates(root)
        if after != before or change_bindings(root) != bindings:
            raise MandatoryApplicationRejected("COORDINATE_OR_CHANGE_DRIFT_DURING_SCAN")
        effect = operation_policy.get("effect") is True
        if effect and actor_class == "AI":
            raise MandatoryApplicationRejected("AI_MAY_NOT_AUTHORIZE_EFFECT")
        if effect:
            _validate_effect_authority(root, operation, operation_policy, effect_authority)
        result: dict[str, Any] = {
            "state": PASS_STATE,
            "review": "TOTAL_FIELD_RULE_APPLICATION_REVIEW",
            "operation": operation,
            "actor_class": actor_class,
            "operation_authorized": True,
            "effect": effect,
            "coordinates": before,
            "local_rule_bindings": rules,
            "local_rules_sha256": rules_digest,
            "dynamic_context_sha256": projection_digest,
            "dynamic_context_projection": projection,
            "work_target_binding": target_binding,
            "work_target_sha256": target_digest,
            "change_bindings": bindings,
            "ai_output_state": "CANDIDATE_ONLY",
            **{key: False for key in denied if key != "operation_authorized"},
        }
        if operation == "CHANGE_COMPLETION_REVIEW":
            result["change_review_packet"] = _completed_change_review(
                coordinates=before,
                query=query,
                target_sha256=target_digest,
                rules_sha256=rules_digest,
                dynamic_context_sha256=projection_digest,
                bindings=bindings,
            )
        if operation == "DEPLOY":
            result["deploy_authorized"] = True
        elif operation == "RESTART":
            result["restart_authorized"] = True
        elif operation == "GIT_PUSH":
            result["git_push_authorized"] = True
        elif operation == "PROMOTION":
            result["promotion_authorized"] = True
        return result
    except (MandatoryApplicationRejected, OSError, ValueError, json.JSONDecodeError) as exc:
        return {"state": HOLD_STATE, "reason": str(exc), "operation": operation, **denied}


def reviewed_prompt_text(result: Mapping[str, Any]) -> str:
    if result.get("state") != PASS_STATE:
        raise MandatoryApplicationRejected("MANDATORY_APPLICATION_REVIEW_NOT_PASSED")
    projection = result.get("dynamic_context_projection")
    if not isinstance(projection, Mapping):
        raise MandatoryApplicationRejected("DYNAMIC_CONTEXT_PROJECTION_MISSING")
    payload = _canonical_json(projection)
    if _sha256(payload) != result.get("dynamic_context_sha256"):
        raise MandatoryApplicationRejected("DYNAMIC_CONTEXT_PROJECTION_HASH_DRIFT")
    return payload.decode("utf-8")


def write_change_review_receipt(repo_root: str | Path, result: Mapping[str, Any]) -> Path:
    root = Path(repo_root).resolve()
    packet = result.get("change_review_packet")
    if result.get("state") != PASS_STATE or not isinstance(packet, Mapping):
        raise MandatoryApplicationRejected("COMPLETED_CHANGE_REVIEW_NOT_PASSED")
    packet_without_sha = {key: value for key, value in packet.items() if key != "review_sha256"}
    review_sha256 = packet.get("review_sha256")
    if review_sha256 != _sha256(_canonical_json(packet_without_sha)):
        raise MandatoryApplicationRejected("COMPLETED_CHANGE_REVIEW_HASH_DRIFT")
    receipt_root = root / "runtime/total_field/rule_application_reviews/pending"
    receipt_root.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_root / f"{review_sha256}.json"
    payload = _canonical_json(packet) + b"\n"
    if receipt_path.exists():
        if receipt_path.is_symlink() or receipt_path.read_bytes() != payload:
            raise MandatoryApplicationRejected("REVIEW_RECEIPT_COLLISION")
        return receipt_path
    descriptor = os.open(receipt_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            receipt_path.unlink(missing_ok=True)
        finally:
            raise
    return receipt_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run mandatory 8DADI scan and Total Field rule application review."
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--operation", required=True)
    parser.add_argument("--actor-class", choices=("AI", "HUMAN", "SYSTEM"), required=True)
    parser.add_argument("--query", default="current governed operation")
    parser.add_argument("--expected-branch")
    parser.add_argument("--expected-head")
    parser.add_argument("--expected-tree")
    parser.add_argument("--expected-work-target-sha256")
    parser.add_argument("--write-review-receipt", action="store_true")
    args = parser.parse_args()
    result = scan_operation(
        repo_root=args.repo_root,
        operation=args.operation,
        actor_class=args.actor_class,
        query=args.query,
        expected_branch=args.expected_branch,
        expected_head=args.expected_head,
        expected_tree=args.expected_tree,
        expected_work_target_sha256=args.expected_work_target_sha256,
    )
    if args.write_review_receipt and result.get("state") == PASS_STATE:
        try:
            result["review_receipt_ref"] = write_change_review_receipt(
                args.repo_root, result
            ).relative_to(Path(args.repo_root).resolve()).as_posix()
        except MandatoryApplicationRejected as exc:
            result = {
                "state": HOLD_STATE,
                "reason": str(exc),
                "operation": args.operation,
                "operation_authorized": False,
            }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("operation_authorized") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
