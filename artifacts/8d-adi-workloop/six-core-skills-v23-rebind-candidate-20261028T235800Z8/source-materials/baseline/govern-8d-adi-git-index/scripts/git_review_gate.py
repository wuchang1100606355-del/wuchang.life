#!/usr/bin/env python3
"""Deterministically route a hash-bound Git change set without mutating Git."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import stat
import struct
import sys
from pathlib import Path, PurePosixPath
from typing import Any


SAFE_OPERATIONS = {
    "ADD_CANDIDATE_SCHEMA",
    "ADD_REVIEW_EVIDENCE",
}
REVIEW_OPERATIONS = {
    "ADD_CANDIDATE_SKILL_INSTRUCTIONS",
    "ADD_CANDIDATE_MANIFEST",
    "ADD_READONLY_VALIDATOR",
    "ADD_TEST",
    "MODIFY_EXISTING_FILE",
    "ISOLATED_MATERIALIZE",
    "TEMP_PACK_BUILD",
    "CREATE_CANDIDATE_REF",
    "WORKTREE_RELOCATION_COMMIT",
    "DEPENDENCY_CHANGE",
}
REVIEW_CONTROL_FILES = {
    ".clinerules",
    ".cursorrules",
    ".roorules",
    ".windsurfrules",
    "agents.md",
    "claude.md",
    "codex.md",
    "copilot-instructions.md",
    "gemini.md",
    "skill.md",
    "openai.yaml",
    "total-field-skill-manifest.json",
}
REVIEW_CONTROL_PATH_PARTS = {
    ".claude",
    ".codex",
    ".continue",
    ".cursor",
    ".devcontainer",
    ".vscode",
    ".windsurf",
}
SAFE_DECLARATIVE_DIRS = {"evidence", "references", "reports", "schemas"}
HOLD_OPERATIONS = {
    "LIVE_OBJECT_DB_WRITE",
    "HAND_EDIT_PACK_OR_INDEX",
    "MOVE_LIVE_REF",
    "HISTORY_REWRITE",
    "FORCE_PUSH",
    "RESET_HARD",
    "GC_PRUNE_OR_EXPIRE",
    "DELETE_ORIGINAL",
    "CANONICAL_POINTER_WRITE",
    "IDENTITY_OR_SEAT_CHANGE",
    "SELF_ASSERT_TOTAL_FIELD_RECEIPT",
    "MANUAL_PROMISOR_MARK",
}
ALLOWED_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".py"}
MAX_FILE_BYTES = 1_048_576
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN_PATH_PARTS = {
    ".git",
    ".github",
    ".gitlab",
    ".circleci",
    ".buildkite",
    "objects",
    "refs",
    "logs",
    "hooks",
    "canonical",
    "active_pointer",
    "secrets",
    "credentials",
}
FORBIDDEN_AUTORUN_NAMES = {
    ".gitlab-ci.yml",
    "azure-pipelines.yml",
    "cloudbuild.yaml",
    "jenkinsfile",
    "package.json",
}
FORBIDDEN_PYTHON_IMPORTS = {
    "ctypes",
    "http",
    "importlib",
    "multiprocessing",
    "os",
    "pty",
    "requests",
    "runpy",
    "shutil",
    "socket",
    "subprocess",
    "urllib",
}
FORBIDDEN_PYTHON_CALLS = {
    "builtins.__import__",
    "builtins.compile",
    "builtins.eval",
    "builtins.exec",
    "os.popen",
    "os.remove",
    "os.rename",
    "os.replace",
    "os.rmdir",
    "os.unlink",
    "os.system",
    "pathlib.Path.rename",
    "pathlib.Path.replace",
    "pathlib.Path.rmdir",
    "pathlib.Path.unlink",
    "shutil.move",
    "shutil.rmtree",
}
SECRET_RE = re.compile(
    r"(?i)(-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"(?:api[_-]?key|password|client[_-]?secret|access[_-]?token)\s*[:=]\s*['\"][^'\"]{8,})"
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_git_dir(repo_root: Path) -> Path | None:
    marker = repo_root / ".git"
    if marker.is_dir():
        return marker
    if not marker.is_file() or marker.is_symlink():
        return None
    try:
        first_line = marker.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, UnicodeDecodeError, IndexError):
        return None
    if not first_line.startswith("gitdir: "):
        return None
    target = Path(first_line[8:])
    return target if target.is_absolute() else (repo_root / target).resolve()


def parse_git_index(data: bytes, oid_bytes: int) -> tuple[set[bytes], set[bytes], bool] | None:
    """Parse Git index v2/v3 without executing Git or reading repository objects."""
    if len(data) < 12 + oid_bytes or data[:4] != b"DIRC":
        return None
    version, count = struct.unpack(">II", data[4:12])
    if version not in {2, 3}:
        return None
    content, checksum = data[:-oid_bytes], data[-oid_bytes:]
    algorithm = hashlib.sha1 if oid_bytes == 20 else hashlib.sha256
    if algorithm(content).digest() != checksum:
        return None
    offset = 12
    paths: set[bytes] = set()
    sparse_prefixes: set[bytes] = set()
    try:
        for _ in range(count):
            start = offset
            fixed = 42 + oid_bytes
            if offset + fixed > len(content):
                return None
            mode = struct.unpack(">I", content[offset + 24:offset + 28])[0]
            flags = struct.unpack(">H", content[offset + 40 + oid_bytes:offset + 42 + oid_bytes])[0]
            offset += fixed
            if flags & 0x4000:
                if version < 3 or offset + 2 > len(content):
                    return None
                offset += 2
            declared_length = flags & 0x0FFF
            terminator = content.find(b"\0", offset)
            if terminator < 0:
                return None
            path = content[offset:terminator]
            if declared_length < 0x0FFF and len(path) != declared_length:
                return None
            paths.add(path)
            if mode == 0o040000:
                sparse_prefixes.add(path.rstrip(b"/") + b"/")
            offset = terminator + 1
            offset += (8 - ((offset - start) % 8)) % 8
            if offset > len(content):
                return None
        split_index = False
        while offset < len(content):
            if offset + 8 > len(content):
                return None
            signature = content[offset:offset + 4]
            size = struct.unpack(">I", content[offset + 4:offset + 8])[0]
            offset += 8
            if offset + size > len(content):
                return None
            split_index = split_index or signature == b"link"
            offset += size
        return paths, sparse_prefixes, split_index
    except (IndexError, struct.error):
        return None


def git_index_membership(repo_root: Path, path_text: str) -> str:
    """Return TRACKED, UNTRACKED, or UNKNOWN from a checksum-valid Git index."""
    git_dir = resolve_git_dir(repo_root)
    if git_dir is None:
        return "UNKNOWN"
    index = git_dir / "index"
    try:
        if index.is_symlink() or not index.is_file() or index.stat().st_size > 67_108_864:
            return "UNKNOWN"
        data = index.read_bytes()
    except OSError:
        return "UNKNOWN"
    parsed = [result for length in (20, 32) if (result := parse_git_index(data, length)) is not None]
    if len(parsed) != 1:
        return "UNKNOWN"
    paths, sparse_prefixes, split_index = parsed[0]
    if split_index:
        return "UNKNOWN"
    target = path_text.encode("utf-8", errors="surrogateescape")
    if target in paths:
        return "TRACKED"
    if any(target.startswith(prefix) for prefix in sparse_prefixes):
        return "UNKNOWN"
    return "UNTRACKED"


def dotted_name(node: ast.AST) -> str | None:
    """Return a static dotted name without evaluating Python source."""
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    return None


def inspect_python_source(text: str) -> tuple[list[str], list[str]]:
    """Find executable Python capabilities, not policy text or test fixtures."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return ["PYTHON_SYNTAX_INVALID"], []
    hold_findings: list[str] = []
    review_findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in FORBIDDEN_PYTHON_IMPORTS:
                    hold_findings.append(f"FORBIDDEN_PYTHON_IMPORT:{alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root in FORBIDDEN_PYTHON_IMPORTS:
                hold_findings.append(f"FORBIDDEN_PYTHON_IMPORT:{node.module}")
        elif isinstance(node, ast.Call):
            name = dotted_name(node.func)
            if name in FORBIDDEN_PYTHON_CALLS:
                hold_findings.append(f"FORBIDDEN_PYTHON_CALL:{name}")
            if isinstance(node.func, ast.Name) and node.func.id in {"__import__", "compile", "eval", "exec"}:
                hold_findings.append(f"FORBIDDEN_PYTHON_CALL:{node.func.id}")
            method = name.rsplit(".", 1)[-1] if name else None
            if method == "open" or name == "open":
                mode_node = node.args[1] if len(node.args) > 1 else None
                for keyword in node.keywords:
                    if keyword.arg == "mode":
                        mode_node = keyword.value
                if mode_node is not None:
                    mode = mode_node.value if isinstance(mode_node, ast.Constant) and isinstance(mode_node.value, str) else None
                    if mode is None or any(marker in mode for marker in "wax+"):
                        review_findings.append("FILE_OPEN_WRITE_REQUIRES_REVIEW")
    return sorted(set(hold_findings)), sorted(set(review_findings))


def safe_relative(path_text: str, candidate_root: PurePosixPath) -> tuple[bool, str]:
    path = PurePosixPath(path_text)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        return False, "PATH_NOT_BOUNDED"
    try:
        path.relative_to(candidate_root)
    except ValueError:
        return False, "PATH_OUTSIDE_CANDIDATE_ROOT"
    lowered = {part.lower() for part in path.parts}
    if lowered & FORBIDDEN_PATH_PARTS:
        return False, "PROTECTED_PATH_COMPONENT"
    if path.name.lower() in FORBIDDEN_AUTORUN_NAMES:
        return False, "AUTORUN_FILE_PROTECTED"
    if path.suffix.lower() not in ALLOWED_SUFFIXES:
        return False, "FILE_TYPE_NOT_ALLOWLISTED"
    return True, "OK"


def classify(document: Any, repo_root: Path) -> dict[str, Any]:
    reasons: list[str] = []
    review_reasons: list[str] = []
    if not isinstance(document, dict):
        reasons.append("DOCUMENT_OBJECT_REQUIRED")
        document = {}
    if document.get("schema_version") != "w7tp-git-change-review/1.0":
        reasons.append("SCHEMA_VERSION_INVALID")

    root_text = document.get("candidate_root")
    if not isinstance(root_text, str) or not root_text:
        reasons.append("CANDIDATE_ROOT_MISSING")
        candidate_root = PurePosixPath("INVALID")
    else:
        candidate_root = PurePosixPath(root_text)
        if not candidate_root.parts or candidate_root == PurePosixPath("."):
            reasons.append("CANDIDATE_ROOT_NOT_ISOLATED")
            candidate_root = PurePosixPath("INVALID")
        elif candidate_root.is_absolute() or ".." in candidate_root.parts:
            reasons.append("CANDIDATE_ROOT_NOT_BOUNDED")

    raw_operations = document.get("operations")
    if not isinstance(raw_operations, list) or not all(isinstance(item, str) for item in raw_operations):
        reasons.append("OPERATIONS_STRING_ARRAY_REQUIRED")
        operations: set[str] = set()
    else:
        operations = set(raw_operations)
    unknown_ops = operations - SAFE_OPERATIONS - REVIEW_OPERATIONS - HOLD_OPERATIONS
    reasons.extend(f"PROTECTED_OPERATION:{op}" for op in sorted(operations & HOLD_OPERATIONS))
    review_reasons.extend(f"REVIEW_OPERATION:{op}" for op in sorted(operations & REVIEW_OPERATIONS))
    review_reasons.extend(f"UNKNOWN_OPERATION:{op}" for op in sorted(unknown_ops))
    if not operations:
        review_reasons.append("OPERATIONS_EMPTY")

    changes = document.get("changes")
    if not isinstance(changes, list) or not changes:
        reasons.append("CHANGES_EMPTY")
        changes = []

    reviewed_hashes: dict[str, str] = {}
    for item in changes:
        if not isinstance(item, dict):
            reasons.append("CHANGE_ENTRY_INVALID")
            continue
        status = item.get("status")
        path_text = item.get("path")
        declared_hash = item.get("sha256")
        if status != "A":
            review_reasons.append(f"NON_ADDITION_STATUS:{status}:{path_text}")
        if not isinstance(path_text, str):
            reasons.append("CHANGE_PATH_INVALID")
            continue
        path_ok, path_reason = safe_relative(path_text, candidate_root)
        if not path_ok:
            reasons.append(f"{path_reason}:{path_text}")
            continue
        path = repo_root
        symlink_component = False
        for part in PurePosixPath(path_text).parts:
            path = path / part
            if path.is_symlink():
                reasons.append(f"SYMLINK_COMPONENT:{path_text}")
                symlink_component = True
                break
        if symlink_component:
            continue
        path = path.resolve()
        try:
            path.relative_to(repo_root.resolve())
        except ValueError:
            reasons.append(f"RESOLVED_PATH_ESCAPE:{path_text}")
            continue
        if not path.exists() or not path.is_file() or path.is_symlink():
            reasons.append(f"NOT_REGULAR_FILE:{path_text}")
            continue
        if status == "A":
            membership = git_index_membership(repo_root, path_text)
            if membership == "TRACKED":
                reasons.append(f"DECLARED_ADDITION_ALREADY_TRACKED:{path_text}")
            elif membership == "UNKNOWN":
                review_reasons.append(f"BASELINE_INDEX_UNVERIFIED:{path_text}")
        if path.name.lower() in REVIEW_CONTROL_FILES:
            review_reasons.append(f"CONTROL_FILE_REQUIRES_REVIEW:{path_text}")
        lowered_parts = {part.lower() for part in PurePosixPath(path_text).parts}
        if lowered_parts & REVIEW_CONTROL_PATH_PARTS:
            review_reasons.append(f"CONTROL_PATH_REQUIRES_REVIEW:{path_text}")
        try:
            candidate_relative = PurePosixPath(path_text).relative_to(candidate_root)
        except ValueError:
            candidate_relative = PurePosixPath()
        if len(candidate_relative.parts) < 2 or candidate_relative.parts[0].lower() not in SAFE_DECLARATIVE_DIRS:
            review_reasons.append(f"PLACEMENT_REQUIRES_REVIEW:{path_text}")
        mode = path.stat().st_mode
        if mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            review_reasons.append(f"EXECUTABLE_MODE:{path_text}")
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            review_reasons.append(f"FILE_TOO_LARGE:{path_text}:{size}")
        actual_hash = file_sha256(path)
        if not isinstance(declared_hash, str) or not SHA256_RE.fullmatch(declared_hash):
            reasons.append(f"DECLARED_HASH_INVALID:{path_text}")
        elif actual_hash != declared_hash:
            reasons.append(f"HASH_MISMATCH:{path_text}")
        reviewed_hashes[path_text] = actual_hash
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            review_reasons.append(f"NON_UTF8_FILE:{path_text}")
            continue
        if path.suffix.lower() == ".py":
            review_reasons.append(f"PYTHON_CODE_REQUIRES_REVIEW:{path_text}")
            hold_findings, python_review_findings = inspect_python_source(text)
            reasons.extend(f"{finding}:{path_text}" for finding in hold_findings)
            review_reasons.extend(f"{finding}:{path_text}" for finding in python_review_findings)
        if SECRET_RE.search(text):
            reasons.append(f"SECRET_PATTERN:{path_text}")
        if path.name == "total-field-skill-manifest.json":
            try:
                manifest = json.loads(text)
            except json.JSONDecodeError:
                reasons.append(f"MANIFEST_JSON_INVALID:{path_text}")
            else:
                if not isinstance(manifest, dict):
                    reasons.append(f"MANIFEST_OBJECT_REQUIRED:{path_text}")
                    continue
                if manifest.get("manifest_state") == "ACTIVE":
                    reasons.append(f"SELF_ASSERTED_ACTIVE_MANIFEST:{path_text}")
                lifecycle = manifest.get("lifecycle", {})
                if not isinstance(lifecycle, dict):
                    reasons.append(f"LIFECYCLE_OBJECT_REQUIRED:{path_text}")
                elif lifecycle.get("state") == "ACTIVE" or lifecycle.get("total_field_decision_ref"):
                    reasons.append(f"SELF_ASSERTED_TOTAL_FIELD_DECISION:{path_text}")

    if reasons:
        decision = "HOLD_PROTECTED_GIT_EFFECT"
        effect = "E5_OR_INVALID"
        next_action = "修正列出的保護邊界問題後，以相同 schema 重新送審。"
    elif review_reasons:
        decision = "REVIEW_REQUIRED"
        effect = "E3_OR_E4"
        next_action = "建立隔離、回滾與單次授權證據，再交總場審查。"
    else:
        decision = "SAFE_PUSH_CANDIDATE"
        effect = "E2"
        next_action = "若交付包含遠端更新，建立 hash-bound $complete-deferred-git-push handoff；此 E2 route 不得直接推送且不等於 activation。"

    return {
        "state": "PASS_GIT_CHANGE_ROUTE" if decision == "SAFE_PUSH_CANDIDATE" else decision,
        "decision": decision,
        "maximum_effect_class": effect,
        "reasons": sorted(set(reasons)),
        "review_reasons": sorted(set(review_reasons)),
        "reviewed_hashes": dict(sorted(reviewed_hashes.items())),
        "canonical_state": "UNCHANGED",
        "total_field_receipt": "NOT_ISSUED_BY_THIS_GATE",
        "executor_route": "$complete-deferred-git-push",
        "executor_handoff_required_for_remote_delivery": True,
        "direct_push_allowed": False,
        "next": next_action,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("change_set", type=Path)
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    document = json.loads(args.change_set.read_text(encoding="utf-8"))
    result = classify(document, args.repo_root.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["decision"] == "SAFE_PUSH_CANDIDATE" else 2


if __name__ == "__main__":
    sys.exit(main())
