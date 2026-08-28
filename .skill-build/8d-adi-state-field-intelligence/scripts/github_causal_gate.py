#!/usr/bin/env python3
"""Validate one committed GitHub causal declaration without network or authority claims."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


DECLARATION_SCHEMA = "w7tp-github-causal-declaration/1.0"
RECEIPT_SCHEMA = "w7tp-github-causal-receipt/1.0"
SCHEMA_FILE = Path(__file__).resolve().parent.parent / "references/github-causal-manifest.schema.json"
TOP_LEVEL_KEYS = {
    "schema_version",
    "candidate_only",
    "intent",
    "coordinate",
    "scenarios",
    "groups",
    "risk",
    "github_contract",
    "authority",
}
CLOSURE_STAGES = (
    "definition",
    "implementation",
    "consumer",
    "test",
    "wiring",
    "effect",
    "rollback",
)
RELATIONS = {
    "requires",
    "provides",
    "imports",
    "calls",
    "verifies",
    "produces",
    "routes",
    "affects",
    "causes",
    "authorizes",
    "conflicts",
}
EVIDENCE_CLASSES = {
    "OBSERVED",
    "RECONSTRUCTED_EXPLICIT",
    "INFERRED",
    "CONFLICT",
    "UNKNOWN",
}
SENSITIVE_PARTS = {
    ".env",
    ".ssh",
    "secret",
    "secrets",
    "credential",
    "credentials",
    "member_plaintext",
    "why_it_runs",
}
SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".kdbx"}
REQUIRED_FORBIDDEN_CLAIMS = {
    "SAFE",
    "ALLOW",
    "TOTAL_FIELD_D8_SELF_AUTHORITY",
    "DEPLOYMENT_FROM_CHECK",
}
GITHUB_ENV_KEYS = (
    "GITHUB_EVENT_NAME",
    "GITHUB_REPOSITORY",
    "GITHUB_REF",
    "GITHUB_HEAD_REF",
    "GITHUB_BASE_REF",
    "GITHUB_RUN_ID",
    "GITHUB_RUN_ATTEMPT",
    "GITHUB_WORKFLOW",
    "GITHUB_JOB",
    "GITHUB_ACTOR_ID",
)


class GateError(RuntimeError):
    """A deterministic local precondition failure."""


def git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_CONFIG_COUNT"] = "2"
    env["GIT_CONFIG_KEY_0"] = "core.fsmonitor"
    env["GIT_CONFIG_VALUE_0"] = "false"
    env["GIT_CONFIG_KEY_1"] = "core.hooksPath"
    env["GIT_CONFIG_VALUE_1"] = os.devnull
    return env


def run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
            env=git_env(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GateError(f"GIT_COMMAND_UNAVAILABLE:{args[0] if args else 'git'}") from exc
    if check and result.returncode != 0:
        reason = result.stderr.decode("utf-8", "replace").strip()
        raise GateError(f"GIT_COMMAND_FAILED:{args[0] if args else 'git'}:{reason[:160]}")
    return result


def git_text(repo: Path, *args: str) -> str:
    return run_git(repo, *args).stdout.decode("utf-8", "replace").strip()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def add_reason(reasons: list[str], code: str) -> None:
    if code not in reasons:
        reasons.append(code)


def is_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def string_list(value: Any, *, nonempty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (not nonempty or bool(value))
        and all(is_string(item) for item in value)
        and len(value) == len(set(value))
    )


def valid_git_oid(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", value) is not None


def valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def valid_path(value: Any) -> bool:
    if not is_string(value) or "\x00" in value or "\\" in value:
        return False
    candidate = PurePosixPath(value)
    return not candidate.is_absolute() and candidate.as_posix() == value and ".." not in candidate.parts


def sensitive_path(path: str) -> bool:
    candidate = PurePosixPath(path)
    lowered = {part.casefold() for part in candidate.parts}
    return bool(lowered.intersection(SENSITIVE_PARTS)) or candidate.suffix.casefold() in SENSITIVE_SUFFIXES


def committed_blob(repo: Path, commit: str, path: str) -> tuple[str, bytes]:
    result = run_git(repo, "ls-tree", "-z", commit, "--", path)
    records = [item for item in result.stdout.split(b"\0") if item]
    if len(records) != 1:
        raise GateError(f"GIT_BLOB_NOT_UNIQUE:{path}")
    try:
        header, raw_path = records[0].split(b"\t", 1)
        mode, object_type, object_id = header.decode("ascii").split()
        decoded_path = raw_path.decode("utf-8", "surrogateescape")
    except (ValueError, UnicodeError) as exc:
        raise GateError(f"GIT_TREE_RECORD_INVALID:{path}") from exc
    if decoded_path != path or object_type != "blob":
        raise GateError(f"GIT_OBJECT_UNSUPPORTED:{path}:{mode}:{object_type}")
    return mode, run_git(repo, "cat-file", "blob", object_id).stdout


def diff_entries(repo: Path, base: str, head: str) -> dict[str, str]:
    raw = run_git(repo, "diff", "--name-status", "-z", "--no-renames", base, head).stdout
    parts = [item for item in raw.split(b"\0") if item]
    if len(parts) % 2:
        raise GateError("GIT_DIFF_RECORD_INVALID")
    mapping = {"A": "ADD", "M": "MODIFY", "D": "DELETE"}
    entries: dict[str, str] = {}
    for index in range(0, len(parts), 2):
        status = parts[index].decode("ascii", "replace")
        path = parts[index + 1].decode("utf-8", "surrogateescape")
        normalized = mapping.get(status[:1])
        if normalized is None or not valid_path(path):
            raise GateError(f"GIT_DIFF_CHANGE_UNSUPPORTED:{status}:{path}")
        entries[path] = normalized
    return entries


def status_fingerprint(repo: Path) -> str:
    raw = run_git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout
    return sha256_bytes(raw)


def topo_order(groups: dict[str, set[str]], reasons: list[str]) -> list[str]:
    indegree = {group_id: 0 for group_id in groups}
    outgoing: dict[str, set[str]] = defaultdict(set)
    for group_id, dependencies in groups.items():
        for dependency in dependencies:
            if dependency not in groups:
                add_reason(reasons, "HOLD_GROUP_DEPENDENCY_MISSING")
                continue
            outgoing[dependency].add(group_id)
            indegree[group_id] += 1
    queue = deque(sorted(group_id for group_id, degree in indegree.items() if degree == 0))
    order: list[str] = []
    while queue:
        current = queue.popleft()
        order.append(current)
        for target in sorted(outgoing[current]):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if len(order) != len(groups):
        add_reason(reasons, "HOLD_GROUP_DEPENDENCY_CYCLE")
    return order


def read_schema(reasons: list[str]) -> tuple[str | None, dict[str, Any] | None]:
    try:
        raw = SCHEMA_FILE.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        add_reason(reasons, "HOLD_DECLARATION_SCHEMA_UNAVAILABLE")
        return None, None
    if not isinstance(value, dict) or value.get("$id") != "urn:w7tp:github-causal-declaration:1.0":
        add_reason(reasons, "HOLD_DECLARATION_SCHEMA_INVALID")
    return sha256_bytes(raw), value


def validate(repo_arg: Path, manifest_arg: Path) -> dict[str, Any]:
    reasons: list[str] = []
    schema_sha256, _ = read_schema(reasons)
    repo = Path(git_text(repo_arg.resolve(), "rev-parse", "--show-toplevel")).resolve()
    manifest_path = manifest_arg.resolve()
    try:
        manifest_relative = manifest_path.relative_to(repo).as_posix()
    except ValueError:
        manifest_relative = "OUTSIDE_REPOSITORY"
        add_reason(reasons, "HOLD_MANIFEST_OUTSIDE_REPOSITORY")

    head_before = git_text(repo, "rev-parse", "HEAD")
    tree_before = git_text(repo, "rev-parse", "HEAD^{tree}")
    status_before = status_fingerprint(repo)
    try:
        raw_manifest = manifest_path.read_bytes()
    except OSError as exc:
        raise GateError("MANIFEST_UNREADABLE") from exc
    manifest_sha256 = sha256_bytes(raw_manifest)
    if len(raw_manifest) > 2_000_000:
        add_reason(reasons, "HOLD_MANIFEST_TOO_LARGE")
    try:
        declaration = json.loads(raw_manifest.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        declaration = {}
        add_reason(reasons, "HOLD_MANIFEST_JSON_INVALID")

    if manifest_relative != "OUTSIDE_REPOSITORY":
        try:
            _, head_manifest = committed_blob(repo, head_before, manifest_relative)
            if head_manifest != raw_manifest:
                add_reason(reasons, "HOLD_MANIFEST_NOT_BOUND_TO_HEAD")
        except GateError:
            add_reason(reasons, "HOLD_MANIFEST_NOT_COMMITTED_AT_HEAD")

    if not isinstance(declaration, dict) or set(declaration) != TOP_LEVEL_KEYS:
        add_reason(reasons, "HOLD_MANIFEST_TOP_LEVEL_CONTRACT")
        declaration = declaration if isinstance(declaration, dict) else {}
    if declaration.get("schema_version") != DECLARATION_SCHEMA:
        add_reason(reasons, "HOLD_MANIFEST_SCHEMA_VERSION")
    if declaration.get("candidate_only") is not True:
        add_reason(reasons, "HOLD_CANDIDATE_ONLY_REQUIRED")

    intent = declaration.get("intent")
    if not isinstance(intent, dict) or set(intent) != {"intent_ref", "product_effect"}:
        add_reason(reasons, "HOLD_INTENT_CONTRACT")
    elif not is_string(intent.get("intent_ref")) or not is_string(intent.get("product_effect")):
        add_reason(reasons, "HOLD_INTENT_VALUE")

    coordinate = declaration.get("coordinate")
    base_commit = None
    if not isinstance(coordinate, dict) or set(coordinate) != {"logical_root_id", "base_commit", "target_ref"}:
        add_reason(reasons, "HOLD_COORDINATE_CONTRACT")
    else:
        base_commit = coordinate.get("base_commit")
        if not is_string(coordinate.get("logical_root_id")) or not is_string(coordinate.get("target_ref")):
            add_reason(reasons, "HOLD_COORDINATE_VALUE")
        if not valid_git_oid(base_commit):
            add_reason(reasons, "HOLD_BASE_COMMIT_FORMAT")

    diff: dict[str, str] = {}
    if isinstance(base_commit, str) and valid_git_oid(base_commit):
        exists = run_git(repo, "cat-file", "-e", f"{base_commit}^{{commit}}", check=False)
        if exists.returncode != 0:
            add_reason(reasons, "HOLD_BASE_COMMIT_NOT_FOUND")
        elif run_git(repo, "merge-base", "--is-ancestor", base_commit, head_before, check=False).returncode != 0:
            add_reason(reasons, "HOLD_BASE_NOT_ANCESTOR")
        else:
            try:
                diff = diff_entries(repo, base_commit, head_before)
            except GateError:
                add_reason(reasons, "HOLD_DIFF_UNREADABLE")

    scenarios = declaration.get("scenarios")
    scenario_ids: set[str] = set()
    if not isinstance(scenarios, list) or not scenarios:
        add_reason(reasons, "HOLD_SCENARIO_MISSING")
        scenarios = []
    for scenario in scenarios:
        expected = {"scenario_id", "actor", "trigger", "preconditions", "expected_effect", "verifier_refs"}
        if not isinstance(scenario, dict) or set(scenario) != expected:
            add_reason(reasons, "HOLD_SCENARIO_CONTRACT")
            continue
        scenario_id = scenario.get("scenario_id")
        if not is_string(scenario_id) or scenario_id in scenario_ids:
            add_reason(reasons, "HOLD_SCENARIO_ID")
            continue
        scenario_ids.add(scenario_id)
        if not all(is_string(scenario.get(key)) for key in ("actor", "trigger", "expected_effect")):
            add_reason(reasons, "HOLD_SCENARIO_VALUE")
        if not string_list(scenario.get("preconditions"), nonempty=True):
            add_reason(reasons, "HOLD_SCENARIO_PRECONDITION")
        if not string_list(scenario.get("verifier_refs"), nonempty=True):
            add_reason(reasons, "HOLD_SCENARIO_VERIFIER")

    groups_value = declaration.get("groups")
    group_dependencies: dict[str, set[str]] = {}
    declared_files: dict[str, dict[str, Any]] = {}
    edge_ids: set[str] = set()
    if not isinstance(groups_value, list) or not groups_value:
        add_reason(reasons, "HOLD_GROUP_MISSING")
        groups_value = []
    for group in groups_value:
        expected_group = {"group_id", "purpose", "scenario_refs", "depends_on", "files", "causal_edges", "closure", "effects"}
        if not isinstance(group, dict) or set(group) != expected_group:
            add_reason(reasons, "HOLD_GROUP_CONTRACT")
            continue
        group_id = group.get("group_id")
        if not is_string(group_id) or group_id in group_dependencies:
            add_reason(reasons, "HOLD_GROUP_ID")
            continue
        if not is_string(group.get("purpose")):
            add_reason(reasons, "HOLD_GROUP_PURPOSE")
        scenario_refs = group.get("scenario_refs")
        if not string_list(scenario_refs, nonempty=True) or not set(scenario_refs).issubset(scenario_ids):
            add_reason(reasons, "HOLD_GROUP_SCENARIO_BINDING")
        depends_on = group.get("depends_on")
        if not string_list(depends_on):
            add_reason(reasons, "HOLD_GROUP_DEPENDENCY_CONTRACT")
            depends_on = []
        group_dependencies[group_id] = set(depends_on)

        files = group.get("files")
        if not isinstance(files, list) or not files:
            add_reason(reasons, "HOLD_GROUP_FILES_MISSING")
            files = []
        for entry in files:
            if not isinstance(entry, dict) or set(entry) != {"path", "change", "sha256", "base_sha256"}:
                add_reason(reasons, "HOLD_FILE_CONTRACT")
                continue
            path = entry.get("path")
            if not valid_path(path) or path in declared_files or path == manifest_relative:
                add_reason(reasons, "HOLD_FILE_PATH_OR_MEMBERSHIP")
                continue
            declared_files[path] = entry
            if sensitive_path(path):
                add_reason(reasons, "HOLD_PROTECTED_PATH_IN_GROUP")

        edges = group.get("causal_edges")
        if not isinstance(edges, list) or not edges:
            add_reason(reasons, "HOLD_CAUSAL_EDGE_MISSING")
            edges = []
        for edge in edges:
            expected_edge = {"edge_id", "source", "target", "relation", "mechanism", "evidence_class", "evidence_refs", "verifier_refs"}
            if not isinstance(edge, dict) or set(edge) != expected_edge:
                add_reason(reasons, "HOLD_CAUSAL_EDGE_CONTRACT")
                continue
            edge_id = edge.get("edge_id")
            if not is_string(edge_id) or edge_id in edge_ids:
                add_reason(reasons, "HOLD_CAUSAL_EDGE_ID")
            else:
                edge_ids.add(edge_id)
            if not is_string(edge.get("source")) or not is_string(edge.get("target")):
                add_reason(reasons, "HOLD_CAUSAL_EDGE_ENDPOINT")
            if edge.get("relation") not in RELATIONS or edge.get("evidence_class") not in EVIDENCE_CLASSES:
                add_reason(reasons, "HOLD_CAUSAL_EDGE_CLASS")
            if not string_list(edge.get("evidence_refs"), nonempty=True) or not string_list(edge.get("verifier_refs")):
                add_reason(reasons, "HOLD_CAUSAL_EDGE_EVIDENCE")
            if edge.get("relation") == "causes":
                if not is_string(edge.get("mechanism")):
                    add_reason(reasons, "HOLD_CAUSE_MECHANISM_MISSING")
                if edge.get("evidence_class") not in {"OBSERVED", "RECONSTRUCTED_EXPLICIT"}:
                    add_reason(reasons, "HOLD_CAUSE_EVIDENCE_INSUFFICIENT")
                if not string_list(edge.get("verifier_refs"), nonempty=True):
                    add_reason(reasons, "HOLD_CAUSE_VERIFIER_MISSING")

        closure = group.get("closure")
        if not isinstance(closure, dict) or set(closure) != set(CLOSURE_STAGES):
            add_reason(reasons, "HOLD_CLOSURE_CONTRACT")
        else:
            for stage in CLOSURE_STAGES:
                value = closure.get(stage)
                if not isinstance(value, dict) or set(value) != {"state", "evidence_refs"}:
                    add_reason(reasons, "HOLD_CLOSURE_STAGE_CONTRACT")
                    continue
                state = value.get("state")
                evidence_refs = value.get("evidence_refs")
                if state not in {"CLOSED", "OPEN", "UNKNOWN", "NOT_APPLICABLE"} or not string_list(evidence_refs):
                    add_reason(reasons, "HOLD_CLOSURE_STAGE_VALUE")
                elif state in {"OPEN", "UNKNOWN"}:
                    add_reason(reasons, "HOLD_CLOSURE_INCOMPLETE")
                elif not evidence_refs:
                    add_reason(reasons, "HOLD_CLOSURE_EVIDENCE_MISSING")

        effects = group.get("effects")
        effect_keys = {"direct", "first_order", "second_order", "reverse", "unknown_frontier"}
        if not isinstance(effects, dict) or set(effects) != effect_keys:
            add_reason(reasons, "HOLD_EFFECT_CONTRACT")
        else:
            for key in effect_keys:
                if not string_list(effects.get(key), nonempty=(key == "direct")):
                    add_reason(reasons, "HOLD_EFFECT_VALUE")
            if effects.get("unknown_frontier"):
                add_reason(reasons, "HOLD_EFFECT_UNKNOWN_FRONTIER")

    group_order = topo_order(group_dependencies, reasons)

    for path, entry in declared_files.items():
        actual_change = diff.get(path)
        if actual_change is None:
            add_reason(reasons, "HOLD_DECLARED_FILE_NOT_CHANGED")
            continue
        if entry.get("change") != actual_change:
            add_reason(reasons, "HOLD_CHANGE_KIND_MISMATCH")
        try:
            if actual_change == "ADD":
                _, content = committed_blob(repo, head_before, path)
                if entry.get("sha256") != sha256_bytes(content) or entry.get("base_sha256") is not None:
                    add_reason(reasons, "HOLD_ADDED_FILE_HASH_MISMATCH")
            elif actual_change == "DELETE":
                _, content = committed_blob(repo, str(base_commit), path)
                if entry.get("sha256") is not None or entry.get("base_sha256") != sha256_bytes(content):
                    add_reason(reasons, "HOLD_DELETED_FILE_HASH_MISMATCH")
            else:
                _, head_content = committed_blob(repo, head_before, path)
                _, base_content = committed_blob(repo, str(base_commit), path)
                if entry.get("sha256") != sha256_bytes(head_content):
                    add_reason(reasons, "HOLD_MODIFIED_FILE_HASH_MISMATCH")
                if entry.get("base_sha256") != sha256_bytes(base_content):
                    add_reason(reasons, "HOLD_MODIFIED_BASE_HASH_MISMATCH")
        except GateError:
            add_reason(reasons, "HOLD_FILE_BLOB_UNREADABLE")

    unaccounted = sorted(set(diff).difference(declared_files).difference({manifest_relative}))
    if unaccounted:
        add_reason(reasons, "HOLD_DIFF_UNACCOUNTED_PATH")
    if sorted(set(declared_files).difference(diff)):
        add_reason(reasons, "HOLD_DECLARATION_OUTSIDE_DIFF")
    if manifest_relative not in diff:
        add_reason(reasons, "HOLD_MANIFEST_NOT_IN_CANDIDATE_DIFF")

    risk = declaration.get("risk")
    if not isinstance(risk, dict) or set(risk) != {"holds", "unknown_boundaries", "network_hold_set"}:
        add_reason(reasons, "HOLD_RISK_CONTRACT")
    else:
        if not all(string_list(risk.get(key)) for key in ("holds", "unknown_boundaries", "network_hold_set")):
            add_reason(reasons, "HOLD_RISK_VALUE")
        elif not all(valid_path(path) for path in risk.get("network_hold_set", [])):
            add_reason(reasons, "HOLD_NETWORK_SET_PATH_INVALID")
        if risk.get("holds"):
            add_reason(reasons, "HOLD_DECLARED_RISK")
        if risk.get("unknown_boundaries"):
            add_reason(reasons, "HOLD_DECLARED_UNKNOWN_BOUNDARY")
        if risk.get("network_hold_set"):
            add_reason(reasons, "HOLD_NETWORK_SET_PRESENT")

    github_contract = declaration.get("github_contract")
    github_keys = {"candidate_branch_ref", "target_ref", "required_checks", "pr_required", "attestation_required", "total_field_check_required"}
    if not isinstance(github_contract, dict) or set(github_contract) != github_keys:
        add_reason(reasons, "HOLD_GITHUB_CONTRACT")
    else:
        checks = github_contract.get("required_checks")
        if not is_string(github_contract.get("candidate_branch_ref")) or not is_string(github_contract.get("target_ref")):
            add_reason(reasons, "HOLD_GITHUB_REF")
        if not string_list(checks, nonempty=True) or "causal-gate" not in checks or "total-field-d8" not in checks:
            add_reason(reasons, "HOLD_REQUIRED_CHECK_BINDING")
        if github_contract.get("pr_required") is not True or github_contract.get("total_field_check_required") is not True:
            add_reason(reasons, "HOLD_GITHUB_AUTHORITY_GATE")
        if not isinstance(github_contract.get("attestation_required"), bool):
            add_reason(reasons, "HOLD_ATTESTATION_CONTRACT")
        if isinstance(coordinate, dict) and github_contract.get("target_ref") != coordinate.get("target_ref"):
            add_reason(reasons, "HOLD_TARGET_REF_MISMATCH")

    authority = declaration.get("authority")
    total_field_ref = None
    if not isinstance(authority, dict) or set(authority) != {"lifecycle", "total_field_decision_ref", "forbidden_claims"}:
        add_reason(reasons, "HOLD_AUTHORITY_CONTRACT")
    else:
        total_field_ref = authority.get("total_field_decision_ref")
        if authority.get("lifecycle") != "CANDIDATE":
            add_reason(reasons, "HOLD_CANDIDATE_LIFECYCLE_REQUIRED")
        if total_field_ref is not None and not is_string(total_field_ref):
            add_reason(reasons, "HOLD_TOTAL_FIELD_REF_FORMAT")
        forbidden = authority.get("forbidden_claims")
        if not string_list(forbidden, nonempty=True) or not REQUIRED_FORBIDDEN_CLAIMS.issubset(set(forbidden)):
            add_reason(reasons, "HOLD_FORBIDDEN_CLAIMS_INCOMPLETE")

    head_after = git_text(repo, "rev-parse", "HEAD")
    tree_after = git_text(repo, "rev-parse", "HEAD^{tree}")
    status_after = status_fingerprint(repo)
    if (head_before, tree_before, status_before) != (head_after, tree_after, status_after):
        add_reason(reasons, "HOLD_STATE_CHANGED")

    state = "HOLD" if reasons else "REVIEW"
    return {
        "schema_version": RECEIPT_SCHEMA,
        "state": state,
        "candidate_only": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "declaration": {
            "path": manifest_relative,
            "sha256": manifest_sha256,
            "schema_sha256": schema_sha256,
        },
        "git_coordinate": {
            "repository_root": str(repo),
            "base_commit": base_commit,
            "head_commit": head_after,
            "head_tree": tree_after,
            "worktree_status_sha256": status_after,
            "network_consulted": False,
            "remote_state_verified": False,
        },
        "coverage": {
            "diff_path_count": len(diff),
            "declared_path_count": len(declared_files),
            "manifest_self_excluded": manifest_relative in diff,
            "unaccounted_paths": unaccounted,
        },
        "groups": {
            "count": len(group_dependencies),
            "topological_order": group_order,
            "scenario_count": len(scenario_ids),
            "causal_edge_count": len(edge_ids),
        },
        "github_observation": {
            key: os.environ[key]
            for key in GITHUB_ENV_KEYS
            if key in os.environ and os.environ[key]
        },
        "total_field": {
            "state": "REFERENCE_PRESENT_UNVERIFIED" if total_field_ref else "NOT_REVIEWED",
            "receipt_ref": total_field_ref,
            "self_authority": False,
        },
        "decision_reason_codes": sorted(reasons),
        "forbidden_claims_confirmed": sorted(REQUIRED_FORBIDDEN_CLAIMS),
        "writes_performed": False,
        "next": (
            "把雜湊綁定的 REVIEW 收據交給既有 Total Field D8 check。"
            if state == "REVIEW"
            else "只修正第一個 HOLD，並在同一精確提交重新驗證。"
        ),
    }


def write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    target = path.resolve()
    if target.exists():
        raise GateError("RECEIPT_OUTPUT_EXISTS")
    if not target.parent.is_dir():
        raise GateError("RECEIPT_OUTPUT_PARENT_MISSING")
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    payload = (json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def git_setup(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", str(repo)], check=True, stdout=subprocess.PIPE)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "selftest@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Causal Gate Self Test"], check=True)


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="w7tp-github-causal-gate-") as temporary:
        repo = Path(temporary) / "repo"
        repo.mkdir()
        git_setup(repo)
        base_content = b"base\n"
        deleted_content = b"remove in candidate\n"
        (repo / "base.txt").write_bytes(base_content)
        (repo / "delete_me.txt").write_bytes(deleted_content)
        subprocess.run(["git", "-C", str(repo), "add", "base.txt", "delete_me.txt"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "base"], check=True)
        base = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()

        contents = {
            "base.txt": b"base upgraded\n",
            "provider.py": b"def value():\n    return 8\n",
            "consumer.py": b"from provider import value\nRESULT = value()\n",
            "test_provider.py": b"from provider import value\nassert value() == 8\n",
        }
        for name, content in contents.items():
            (repo / name).write_bytes(content)
        (repo / "delete_me.txt").unlink()
        manifest_path = repo / ".github/causality/change.json"
        manifest_path.parent.mkdir(parents=True)
        closed = {stage: {"state": "CLOSED", "evidence_refs": [f"evidence:{stage}"]} for stage in CLOSURE_STAGES}
        declaration = {
            "schema_version": DECLARATION_SCHEMA,
            "candidate_only": True,
            "intent": {"intent_ref": "intent:self-test", "product_effect": "Verify causal delivery evidence"},
            "coordinate": {"logical_root_id": "root:self-test", "base_commit": base, "target_ref": "refs/heads/main"},
            "scenarios": [{
                "scenario_id": "scene:self-test",
                "actor": "authorized-reviewer",
                "trigger": "candidate change",
                "preconditions": ["base commit exists"],
                "expected_effect": "causal declaration is reviewable",
                "verifier_refs": ["test:test_provider.py"],
            }],
            "groups": [{
                "group_id": "group:core",
                "purpose": "Provide and consume one deterministic value",
                "scenario_refs": ["scene:self-test"],
                "depends_on": [],
                "files": [
                    *[
                        {
                            "path": name,
                            "change": "MODIFY" if name == "base.txt" else "ADD",
                            "sha256": sha256_bytes(content),
                            "base_sha256": sha256_bytes(base_content) if name == "base.txt" else None,
                        }
                        for name, content in sorted(contents.items())
                    ],
                    {
                        "path": "delete_me.txt",
                        "change": "DELETE",
                        "sha256": None,
                        "base_sha256": sha256_bytes(deleted_content),
                    },
                ],
                "causal_edges": [{
                    "edge_id": "edge:provider-test",
                    "source": "provider.py:value",
                    "target": "test_provider.py:assert",
                    "relation": "causes",
                    "mechanism": "the imported function return value is asserted",
                    "evidence_class": "RECONSTRUCTED_EXPLICIT",
                    "evidence_refs": ["import:test_provider.py:provider.value"],
                    "verifier_refs": ["test:test_provider.py"],
                }],
                "closure": closed,
                "effects": {
                    "direct": ["provider returns integer 8"],
                    "first_order": ["consumer imports provider"],
                    "second_order": ["test verifies consumer contract"],
                    "reverse": ["test expectation constrains provider"],
                    "unknown_frontier": [],
                },
            }],
            "risk": {"holds": [], "unknown_boundaries": [], "network_hold_set": []},
            "github_contract": {
                "candidate_branch_ref": "refs/heads/candidate/self-test",
                "target_ref": "refs/heads/main",
                "required_checks": ["causal-gate", "total-field-d8"],
                "pr_required": True,
                "attestation_required": False,
                "total_field_check_required": True,
            },
            "authority": {
                "lifecycle": "CANDIDATE",
                "total_field_decision_ref": None,
                "forbidden_claims": sorted(REQUIRED_FORBIDDEN_CLAIMS),
            },
        }
        manifest_path.write_text(json.dumps(declaration, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "add",
                "base.txt",
                "provider.py",
                "consumer.py",
                "test_provider.py",
                "delete_me.txt",
                ".github/causality/change.json",
            ],
            check=True,
        )
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "candidate"], check=True)
        valid = validate(repo, manifest_path)
        receipt_output = Path(temporary) / "CAUSAL_GITHUB_RECEIPT.json"
        cli_validation = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "validate",
                "--repo",
                str(repo),
                "--manifest",
                str(manifest_path),
                "--receipt-output",
                str(receipt_output),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        written_receipt = json.loads(receipt_output.read_text(encoding="utf-8"))

        declaration["groups"][0]["causal_edges"][0]["mechanism"] = None
        manifest_path.write_text(json.dumps(declaration, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", ".github/causality/change.json"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "--amend", "--no-edit"], check=True)
        invalid = validate(repo, manifest_path)

        passed = (
            valid["state"] == "REVIEW"
            and valid["coverage"]["unaccounted_paths"] == []
            and cli_validation.returncode == 0
            and written_receipt["state"] == "REVIEW"
            and written_receipt["writes_performed"] is True
            and invalid["state"] == "HOLD"
            and "HOLD_CAUSE_MECHANISM_MISSING" in invalid["decision_reason_codes"]
        )
        result = {
            "state": "PASS_SELF_TEST" if passed else "FAIL_SELF_TEST",
            "valid_case": valid["state"],
            "invalid_case": invalid["state"],
            "invalid_reason_observed": "HOLD_CAUSE_MECHANISM_MISSING" in invalid["decision_reason_codes"],
            "receipt_write_case": written_receipt["state"],
            "network_used": False,
            "source_repository_modified": False,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a committed W7TP GitHub causal declaration")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--repo", required=True)
    validate_parser.add_argument("--manifest", required=True)
    validate_parser.add_argument("--receipt-output")
    subparsers.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test":
        return self_test()
    try:
        receipt = validate(Path(args.repo), Path(args.manifest))
        if args.receipt_output:
            output_path = Path(args.receipt_output).resolve()
            repository_root = Path(receipt["git_coordinate"]["repository_root"]).resolve()
            if output_path == repository_root or repository_root in output_path.parents:
                raise GateError("RECEIPT_OUTPUT_INSIDE_SOURCE")
            receipt["writes_performed"] = True
            receipt["receipt_output"] = str(output_path)
            write_receipt(output_path, receipt)
        print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if receipt["state"] == "REVIEW" else 4
    except GateError as exc:
        print(json.dumps({
            "schema_version": RECEIPT_SCHEMA,
            "state": "HOLD",
            "candidate_only": True,
            "decision_reason_codes": [str(exc).split(":", 1)[0]],
            "detail": str(exc),
            "network_used": False,
            "writes_performed": False,
        }, ensure_ascii=False, indent=2, sort_keys=True))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
