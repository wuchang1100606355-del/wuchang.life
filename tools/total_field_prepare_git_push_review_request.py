#!/usr/bin/env python3
"""Register one immutable Git-push review request from exact Git evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field_mandatory_application_gate import PASS_STATE, scan_operation

CONFIG_REL = Path("configs/total_field/git_push_review_gate_v1.json")
REQUEST_SCHEMA = "W7TP_TOTAL_FIELD_GIT_PUSH_REVIEW_REQUEST_V1"
POINTER_SCHEMA = "W7TP_TOTAL_FIELD_ACTIVE_REVIEW_REQUEST_V1"
PASS_REQUEST = "PASS_TOTAL_FIELD_GIT_PUSH_REVIEW_REQUEST_REGISTERED"
HOLD_REQUEST = "HOLD_TOTAL_FIELD_GIT_PUSH_REVIEW_REQUEST"
OID = re.compile(r"^[0-9a-f]{40,64}$")


class ReviewRequestRejected(RuntimeError):
    pass


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git(root: Path, *args: str, binary: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=not binary,
    )
    if result.returncode != 0:
        raise ReviewRequestRejected("GIT_EVIDENCE_UNAVAILABLE")
    return result.stdout if binary else result.stdout.strip()


def _safe_request_path(root: Path, value: Any) -> Path:
    if not isinstance(value, str):
        raise ReviewRequestRejected("REVIEW_REQUEST_REF_MISSING")
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or tuple(relative.parts[:3]) != ("runtime", "total_field", "review_requests")
        or relative.name != "REQUEST.json"
    ):
        raise ReviewRequestRejected("REVIEW_REQUEST_REF_INVALID")
    path = root.joinpath(*relative.parts)
    try:
        path.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise ReviewRequestRejected("REVIEW_REQUEST_REF_OUTSIDE_ROOT") from exc
    return path


def _active_pointer_path(root: Path, value: Any) -> Path:
    if not isinstance(value, str):
        raise ReviewRequestRejected("ACTIVE_REVIEW_REQUEST_POINTER_REF_MISSING")
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or tuple(relative.parts[:2]) != ("runtime", "total_field")
        or relative.name != "ACTIVE_REVIEW_REQUEST.json"
    ):
        raise ReviewRequestRejected("ACTIVE_REVIEW_REQUEST_POINTER_REF_INVALID")
    return root.joinpath(*relative.parts)


def active_review_request_pointer_path(repo_root: str | Path) -> Path:
    root = Path(repo_root).resolve()
    config = _load_config(root)
    return _active_pointer_path(
        root,
        config["passkey_verifier"].get("active_review_request_pointer_ref"),
    )


def _load_config(root: Path) -> dict[str, Any]:
    try:
        value = json.loads((root / CONFIG_REL).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewRequestRejected("GIT_PUSH_GATE_CONFIG_INVALID") from exc
    passkey = value.get("passkey_verifier") if isinstance(value, Mapping) else None
    if value.get("state") != "ACTIVE_FAIL_CLOSED" or not isinstance(passkey, Mapping):
        raise ReviewRequestRejected("GIT_PUSH_GATE_NOT_ACTIVE")
    return value


def build_review_request(
    *,
    repo_root: str | Path,
    base_commit: str,
    target_commit: str,
    target_branch: str,
    remote_name: str,
    deployment_id: str | None = None,
    canonical_repository_root: str = "/home/taiji_admin/Taiji_Hub",
    created_at: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    root = Path(repo_root).resolve()
    config = _load_config(root)
    if not OID.fullmatch(base_commit) or not OID.fullmatch(target_commit):
        raise ReviewRequestRejected("COMMIT_COORDINATE_INVALID")
    if not target_branch or target_branch.startswith("-") or any(char.isspace() for char in target_branch):
        raise ReviewRequestRejected("TARGET_BRANCH_INVALID")
    _git(root, "check-ref-format", f"refs/heads/{target_branch}")
    if _git(root, "status", "--porcelain", "--untracked-files=all"):
        raise ReviewRequestRejected("DIRTY_WORKTREE_BLOCKED")
    resolved_target = str(_git(root, "rev-parse", target_commit))
    resolved_base = str(_git(root, "rev-parse", base_commit))
    if resolved_target != target_commit or resolved_base != base_commit:
        raise ReviewRequestRejected("COMMIT_COORDINATE_NOT_EXACT")
    if _git(root, "rev-parse", f"{target_commit}^") != base_commit:
        raise ReviewRequestRejected("SINGLE_COMMIT_BASE_MISMATCH")
    remote_url = str(_git(root, "remote", "get-url", remote_name))
    remote_base = str(_git(root, "rev-parse", f"refs/remotes/{remote_name}/{target_branch}"))
    if remote_base != base_commit:
        raise ReviewRequestRejected("REMOTE_BASE_DRIFT")
    target_tree = str(_git(root, "rev-parse", f"{target_commit}^{{tree}}"))
    changed_paths = sorted(
        line
        for line in str(
            _git(root, "diff", "--name-only", "--no-renames", base_commit, target_commit, "--")
        ).splitlines()
        if line
    )
    if not changed_paths:
        raise ReviewRequestRejected("EMPTY_CHANGE_SET")
    changed_paths_sha256 = _sha256(("\n".join(changed_paths) + "\n").encode("utf-8"))
    patch = _git(root, "diff", "--binary", "--no-renames", base_commit, target_commit, "--", binary=True)
    passkey = config["passkey_verifier"]
    deployment = None
    if deployment_id:
        admitted = passkey.get("admitted_deployments")
        if not isinstance(admitted, list):
            raise ReviewRequestRejected("DEPLOYMENT_REGISTRY_MISSING")
        matches = [
            item
            for item in admitted
            if isinstance(item, Mapping) and item.get("deployment_id") == deployment_id
        ]
        if len(matches) != 1:
            raise ReviewRequestRejected("DEPLOYMENT_NOT_ADMITTED")
        deployment = dict(matches[0])
    requested_scopes = ["AUTHORIZE_GIT_PUSH"]
    if deployment is not None:
        requested_scopes.append("AUTHORIZE_EXACT_DEPLOY_RESTART")
    timestamp = created_at or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    packet: dict[str, Any] = {
        "schema_id": REQUEST_SCHEMA,
        "state": "REGISTERED_PENDING_TOTAL_FIELD_REVIEW",
        "registration_state": "REGISTERED_FOR_REVIEW",
        "created_at": timestamp,
        "D1_INTENT": {
            "founder_intent_zh_TW": "將總場強制套用模組的精確已審提交送交人類 Passkey 核可後推送。",
            "target_outcome": (
                "只推送核定提交並部署重啟已登記的本機閘道與每小時排程；不改 canonical 或 active pointer。"
                if deployment is not None
                else "只推送核定提交；不改 canonical 或 active pointer；不授權部署或重啟。"
            ),
        },
        "D2_STATE": {
            "repository_state": "CANDIDATE_COMMITTED_LOCAL_ONLY",
            "candidate_commit": target_commit,
            "runtime_effect_state": "NOT_DEPLOYED_NOT_RESTARTED",
        },
        "D3_COORDINATE": {
            "repository_root": canonical_repository_root,
            "branch": target_branch,
            "base_commit": base_commit,
            "target_tree": target_tree,
            "remote_name": remote_name,
            "remote_url_sha256": _sha256(remote_url.encode("utf-8")),
            "target_ref": f"refs/heads/{target_branch}",
            "changed_paths": changed_paths,
        },
        "D4_EVIDENCE": {
            "changed_paths_sha256": changed_paths_sha256,
            "candidate_patch_sha256": _sha256(bytes(patch)),
            "candidate_tests": "SEPARATE_VERIFIED_D4_EVIDENCE",
            "remote_candidate_received": False,
        },
        "D5_EXECUTION_POLICY": {
            "requested_action": (
                "REVIEW_AUTHORIZE_EXACT_GIT_PUSH_DEPLOY_RESTART"
                if deployment is not None
                else "REVIEW_AUTHORIZE_EXACT_GIT_PUSH"
            ),
            "required_sequence": (
                ["TOTAL_FIELD_REVIEW", "D8_PASSKEY", "GIT_PUSH", "CANARY", "DEPLOY", "RESTART", "REOBSERVE"]
                if deployment is not None
                else ["TOTAL_FIELD_REVIEW", "D8_PASSKEY", "GIT_PUSH", "REOBSERVE"]
            ),
            "canonical_pointer_write": False,
            "active_pointer_write": False,
            "deployment": deployment,
        },
        "D6_GENERATIVE_TRANSMISSION": {
            "used": False,
            "git_push_is_not_generative_transmission": True,
        },
        "D7_RISK_QUARANTINE": {
            "wrong_branch_tree_or_path_set": "HOLD",
            "expired_or_replayed_passkey": "HOLD",
            "deploy_or_restart": "ALLOW_ONLY_EXACT_REGISTERED_DEPLOYMENT" if deployment is not None else "DENY",
        },
        "D8_ENVELOPE_AUTHORITY": {
            "requested_scopes": requested_scopes,
            "maximum_ttl_seconds": int(passkey["maximum_ttl_seconds"]),
            "single_use_authorization_required": True,
            "founder_enrolled_user_verified_passkey_required": True,
            "candidate_authority": False,
            "model_authority": False,
            "execution_authorized": False,
        },
        "requested_review_registration_ref": "runtime/total_field/authority_artifacts/TO_BE_ISSUED/GIT_PUSH_REVIEW_REGISTRATION.json",
    }
    packet["packet_sha256"] = _sha256(_canonical_json(packet))
    request_path = _safe_request_path(
        root,
        f"runtime/total_field/review_requests/by_packet/{packet['packet_sha256']}/REQUEST.json",
    )
    return request_path, packet


def register_review_request(
    path: Path,
    packet: Mapping[str, Any],
    *,
    active_pointer_path: Path | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    if path.exists():
        if path.is_symlink() or path.read_bytes() != payload:
            raise ReviewRequestRejected("REVIEW_REQUEST_APPEND_ONLY_COLLISION")
    else:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            try:
                path.unlink(missing_ok=True)
            finally:
                raise
    if active_pointer_path is None:
        return
    pointer = {
        "schema_id": POINTER_SCHEMA,
        "state": "ACTIVE_REVIEW_REQUEST",
        "review_request_ref": path.relative_to(path.parents[5]).as_posix(),
        "request_packet_sha256": packet["packet_sha256"],
        "request_source_sha256": _sha256(path.read_bytes()),
        "updated_at": packet["created_at"],
    }
    active_pointer_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = active_pointer_path.with_name(
        f".{active_pointer_path.name}.{os.getpid()}.tmp"
    )
    payload = json.dumps(pointer, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, active_pointer_path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Register exact Total Field Git-push review request.")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--base-commit", required=True)
    parser.add_argument("--target-commit", required=True)
    parser.add_argument("--target-branch", required=True)
    parser.add_argument("--remote-name", default="origin")
    parser.add_argument("--deployment-id")
    parser.add_argument("--canonical-repository-root", default="/home/taiji_admin/Taiji_Hub")
    args = parser.parse_args()
    try:
        mandatory = scan_operation(
            repo_root=args.repo_root,
            operation="PREFLIGHT",
            actor_class="SYSTEM",
            query="登記總場核定的精確 Git push 審查請求",
        )
        if mandatory.get("state") != PASS_STATE:
            raise ReviewRequestRejected(str(mandatory.get("reason") or mandatory.get("state")))
        path, packet = build_review_request(
            repo_root=args.repo_root,
            base_commit=args.base_commit,
            target_commit=args.target_commit,
            target_branch=args.target_branch,
            remote_name=args.remote_name,
            deployment_id=args.deployment_id,
            canonical_repository_root=args.canonical_repository_root,
        )
        register_review_request(
            path,
            packet,
            active_pointer_path=active_review_request_pointer_path(args.repo_root),
        )
        result = {
            "state": PASS_REQUEST,
            "review_request_ref": path.relative_to(Path(args.repo_root).resolve()).as_posix(),
            "packet_sha256": packet["packet_sha256"],
            "base_commit": args.base_commit,
            "target_commit": args.target_commit,
            "target_tree": packet["D3_COORDINATE"]["target_tree"],
            "branch": args.target_branch,
            "changed_paths_sha256": packet["D4_EVIDENCE"]["changed_paths_sha256"],
            "push_authorized": False,
            "deploy_authorized": False,
        }
    except (ReviewRequestRejected, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        result = {
            "state": HOLD_REQUEST,
            "reason": str(exc),
            "push_authorized": False,
            "deploy_authorized": False,
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("state") == PASS_REQUEST else 1


if __name__ == "__main__":
    raise SystemExit(main())
