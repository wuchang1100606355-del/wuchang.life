#!/usr/bin/env python3
"""Fail-closed Git push projection of the existing Total Field authority chain."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field_authority_resolver import (
    ACTIVE_POINTER_REL,
    GIT_PUSH_SCOPE,
    resolve_active_total_field_authority,
)
from tools.total_field_authority_runtime_bindings import build_authority_runtime_bindings
from tools.total_field_ed25519_backend import Ed25519DetachedSignatureBackend

CONFIG_REL = Path("configs/total_field/git_push_review_gate_v1.json")
APPROVAL_SCHEMA = "W7TP_TOTAL_FIELD_GIT_PUSH_REVIEW_REGISTRATION_V1"
APPROVAL_STATE = "PASS_TOTAL_FIELD_REVIEW_REGISTERED"
ZERO_OID = frozenset({"0" * 40, "0" * 64})
DEPLOY_RESTART_SCOPE = "AUTHORIZE_EXACT_DEPLOY_RESTART"


class PushGateRejected(RuntimeError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise PushGateRejected("GIT_COORDINATE_UNAVAILABLE")
    return result.stdout.strip()


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", ancestor, descendant],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise PushGateRejected("GIT_ANCESTRY_UNAVAILABLE")


def _safe_ref(root: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value:
        raise PushGateRejected("REVIEW_REGISTRATION_REF_MISSING")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise PushGateRejected("REVIEW_REGISTRATION_REF_INVALID")
    if tuple(relative.parts[:3]) != ("runtime", "total_field", "authority_artifacts"):
        raise PushGateRejected("REVIEW_REGISTRATION_OUTSIDE_AUTHORITY_TREE")
    path = root.joinpath(*relative.parts)
    if not path.is_file() or path.is_symlink():
        raise PushGateRejected("REVIEW_REGISTRATION_MISSING")
    return path


def _load_config(root: Path) -> dict[str, Any]:
    path = root / CONFIG_REL
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PushGateRejected("PUSH_GATE_CONFIG_INVALID") from exc
    if not isinstance(value, dict) or value.get("state") != "ACTIVE_FAIL_CLOSED":
        raise PushGateRejected("PUSH_GATE_NOT_ACTIVE")
    return value


def _changed_paths(root: Path, base_commit: str, local_oid: str) -> list[str]:
    output = _git(root, "diff", "--name-only", "--no-renames", base_commit, local_oid)
    return sorted(line for line in output.splitlines() if line)


def _paths_sha256(paths: list[str]) -> str:
    return _sha256(("\n".join(paths) + "\n").encode("utf-8"))


def verify_push(
    *,
    repo_root: str | Path,
    remote_name: str,
    remote_url: str,
    updates: list[tuple[str, str, str, str]],
    authority_resolver: Callable[..., Mapping[str, Any]],
    nonce_ledger: Any,
    signature_verifier: Any,
    trusted_verifier_refs: tuple[str, ...],
    passkey_authority_resolver: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config = _load_config(root)
    no_effect = {
        "push_authorized": False,
        "deploy_authorized": False,
        "canonical_mutation_authorized": False,
        "active_pointer_mutation_authorized": False,
    }
    try:
        if len(updates) != 1:
            raise PushGateRejected("EXACTLY_ONE_REF_UPDATE_REQUIRED")
        local_ref, local_oid, remote_ref, remote_oid = updates[0]
        if local_oid in ZERO_OID:
            raise PushGateRejected("DELETE_PUSH_FORBIDDEN")
        authority = authority_resolver(
            ACTIVE_POINTER_REL.as_posix(),
            repo_root=root,
            nonce_ledger=nonce_ledger,
            signature_verifier=signature_verifier,
            trusted_verifier_refs=trusted_verifier_refs,
        )
        authority_source = "ED25519_ACTIVE_AUTHORITY"
        if (
            authority.get("state") != "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED"
            or authority.get("authority_verified") is not True
            or GIT_PUSH_SCOPE not in (authority.get("scope") or [])
        ):
            if passkey_authority_resolver is None:
                raise PushGateRejected(str(authority.get("state") or "AUTHORITY_NOT_VERIFIED"))
            authority = passkey_authority_resolver(
                repo_root=root,
                config=config.get("passkey_verifier") or {},
                consume=False,
                required_scope=GIT_PUSH_SCOPE,
            )
            authority_source = "USER_VERIFIED_DEVICE_PASSKEY"
            if (
                authority.get("state") != "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED"
                or authority.get("authority_verified") is not True
                or GIT_PUSH_SCOPE not in (authority.get("scope") or [])
            ):
                raise PushGateRejected(str(authority.get("reason") or authority.get("state") or "AUTHORITY_NOT_VERIFIED"))
        constraints = authority.get("authority_scope_constraints")
        if not isinstance(constraints, Mapping):
            raise PushGateRejected("GIT_PUSH_SCOPE_CONSTRAINTS_MISSING")
        review_path = _safe_ref(root, constraints.get("review_registration_ref"))
        review_bytes = review_path.read_bytes()
        if _sha256(review_bytes) != constraints.get("review_registration_sha256"):
            raise PushGateRejected("REVIEW_REGISTRATION_HASH_DRIFT")
        try:
            review = json.loads(review_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PushGateRejected("REVIEW_REGISTRATION_INVALID") from exc
        if (
            not isinstance(review, Mapping)
            or review.get("schema_id") != APPROVAL_SCHEMA
            or review.get("state") != APPROVAL_STATE
            or review.get("review_registered") is not True
            or review.get("total_field_decision") not in {
                "ALLOW_FORMAL_GIT_PUSH",
                "ALLOW_FORMAL_GIT_PUSH_AND_EXACT_DEPLOY_RESTART",
            }
        ):
            raise PushGateRejected("TOTAL_FIELD_REVIEW_NOT_PASSED")
        exact = {
            "base_commit": constraints.get("base_commit"),
            "target_tree": constraints.get("target_tree"),
            "branch": constraints.get("branch"),
            "remote_name": constraints.get("remote_name"),
            "remote_url_sha256": constraints.get("remote_url_sha256"),
            "allowed_paths_sha256": constraints.get("allowed_paths_sha256"),
        }
        if any(review.get(key) != value for key, value in exact.items()):
            raise PushGateRejected("REVIEW_AUTHORITY_BINDING_MISMATCH")
        branch = str(exact["branch"])
        if remote_name != exact["remote_name"] or _sha256(remote_url.encode("utf-8")) != exact["remote_url_sha256"]:
            raise PushGateRejected("REMOTE_BINDING_MISMATCH")
        if local_ref != f"refs/heads/{branch}" or remote_ref != f"refs/heads/{branch}":
            raise PushGateRejected("BRANCH_BINDING_MISMATCH")
        if (
            remote_oid not in ZERO_OID
            and remote_oid != exact["base_commit"]
            and not _is_ancestor(root, remote_oid, str(exact["base_commit"]))
        ):
            raise PushGateRejected("REMOTE_BASE_DRIFT")
        if _git(root, "rev-parse", f"{local_oid}^{{tree}}") != exact["target_tree"]:
            raise PushGateRejected("TARGET_TREE_DRIFT")
        if constraints.get("single_commit_only") is not True or _git(root, "rev-parse", f"{local_oid}^") != exact["base_commit"]:
            raise PushGateRejected("SINGLE_COMMIT_BINDING_MISMATCH")
        paths = _changed_paths(root, str(exact["base_commit"]), local_oid)
        if _paths_sha256(paths) != exact["allowed_paths_sha256"]:
            raise PushGateRejected("ALLOWED_PATH_SET_DRIFT")
        if constraints.get("formal_submission") is not True or constraints.get("git_push") is not True:
            raise PushGateRejected("FORMAL_GIT_PUSH_NOT_GRANTED")
        if authority_source == "USER_VERIFIED_DEVICE_PASSKEY":
            consumed = passkey_authority_resolver(
                repo_root=root,
                config=config.get("passkey_verifier") or {},
                consume=True,
                required_scope=GIT_PUSH_SCOPE,
            )
            if (
                consumed.get("authority_verified") is not True
                or consumed.get("authority_sha256") != authority.get("authority_sha256")
            ):
                raise PushGateRejected(str(consumed.get("reason") or "PASSKEY_CONSUMPTION_FAILED"))
        return {
            "state": "PASS_TOTAL_FIELD_GIT_PUSH_GATE",
            "push_authorized": True,
            "deploy_authorized": bool(
                DEPLOY_RESTART_SCOPE in (authority.get("scope") or [])
                and constraints.get("deploy") is True
                and constraints.get("restart") is True
            ),
            "canonical_mutation_authorized": False,
            "active_pointer_mutation_authorized": False,
            "review_registration_sha256": constraints["review_registration_sha256"],
            "authority_sha256": authority.get("authority_sha256"),
            "authority_source": authority_source,
            "target_tree": exact["target_tree"],
            "paths_sha256": exact["allowed_paths_sha256"],
        }
    except PushGateRejected as exc:
        return {"state": "HOLD_TOTAL_FIELD_GIT_PUSH_GATE", "reason": str(exc), **no_effect}


def _parse_updates(stream: Any) -> list[tuple[str, str, str, str]]:
    updates: list[tuple[str, str, str, str]] = []
    for line in stream:
        fields = line.strip().split()
        if fields:
            if len(fields) != 4:
                raise PushGateRejected("PRE_PUSH_INPUT_INVALID")
            updates.append(tuple(fields))
    return updates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--remote-name", required=True)
    parser.add_argument("--remote-url", required=True)
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    config = _load_config(root)
    verifier_config = config.get("signature_verifier") or {}
    trusted = tuple(verifier_config.get("trusted_verifier_refs") or [])
    public_key = root / str(verifier_config.get("public_key_ref") or "")
    backend = Ed25519DetachedSignatureBackend(public_key, trusted_verifier_refs=trusted)
    from tools.total_field_passkey_d8 import verify_passkey_authority
    ledger_ref = str(config.get("nonce_ledger_ref") or "")
    with build_authority_runtime_bindings(
        ledger_path=root / ledger_ref,
        signature_backend=backend,
        trusted_verifier_refs=trusted,
    ) as bindings:
        result = verify_push(
            repo_root=root,
            remote_name=args.remote_name,
            remote_url=args.remote_url,
            updates=_parse_updates(sys.stdin),
            authority_resolver=resolve_active_total_field_authority,
            nonce_ledger=bindings.nonce_ledger,
            signature_verifier=bindings.signature_verifier,
            trusted_verifier_refs=bindings.trusted_verifier_refs,
            passkey_authority_resolver=verify_passkey_authority,
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("push_authorized") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
