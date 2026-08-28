#!/usr/bin/env python3
"""保存 8D/ADI 狀態快照、比較差異並產生生成式傳輸封包。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SNAPSHOT_PROTOCOL = "W7TP-8D-ADI-STATE-SNAPSHOT"
TRANSFER_PROTOCOL = "W7TP-8D-ADI-STATE-TRANSFER"
VERSION = "0.1.0"
BLOCKED = (
    ".env", "secret", "credential", "password", "token", "dead_letter",
    "member_plaintext", "private", "why_it_runs",
    "application_default_credentials",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def object_digest(value: dict[str, Any], self_key: str) -> str:
    reduced = dict(value)
    reduced.pop(self_key, None)
    return digest_bytes(canonical_bytes(reduced))


def atomic_new(path: Path, data: bytes) -> None:
    if path.exists():
        raise FileExistsError(f"拒絕覆寫既有檔案：{path}")
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def write_json(path: Path, value: Any) -> None:
    atomic_new(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")


def within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def output_location(root: Path, raw: str) -> Path:
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if not within(resolved, root) or resolved == root:
        raise ValueError("輸出根目錄必須位於掃描根目錄內，且不得等於掃描根目錄")
    return resolved


def git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_CONFIG_COUNT"] = "2"
    env["GIT_CONFIG_KEY_0"] = "core.fsmonitor"
    env["GIT_CONFIG_VALUE_0"] = "false"
    env["GIT_CONFIG_KEY_1"] = "core.hooksPath"
    env["GIT_CONFIG_VALUE_1"] = os.devnull
    return env


def git(root: Path, *args: str) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
            env=git_env(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)
    return (
        result.returncode,
        result.stdout.decode("utf-8", "replace").strip(),
        result.stderr.decode("utf-8", "replace").strip(),
    )


def git_marker(root: Path) -> dict[str, Any]:
    rc, top, _ = git(root, "rev-parse", "--show-toplevel")
    if rc:
        return {"present": False}
    repo = Path(top).resolve()
    rc_head, head, head_error = git(repo, "rev-parse", "HEAD")
    rc_branch, branch, _ = git(repo, "symbolic-ref", "--short", "-q", "HEAD")
    rc_index, index_text, _ = git(repo, "rev-parse", "--git-path", "index")
    index_marker: list[int] | None = None
    if rc_index == 0:
        index_path = Path(index_text)
        if not index_path.is_absolute():
            index_path = repo / index_path
        try:
            stat = index_path.stat()
            index_marker = [stat.st_size, stat.st_mtime_ns]
        except OSError:
            pass
    return {
        "present": True,
        "repository_root": str(repo),
        "head": head if rc_head == 0 else None,
        "head_error": head_error if rc_head else None,
        "branch": branch if rc_branch == 0 else "分離或未建立版本",
        "index_marker": index_marker,
    }


def blocked_name(relative: str) -> bool:
    lowered = relative.lower()
    return any(marker in lowered for marker in BLOCKED)


def hash_file(path: Path, max_bytes: int) -> tuple[str | None, str | None]:
    try:
        before = path.stat()
    except OSError as exc:
        return None, str(exc)
    if before.st_size > max_bytes:
        return None, "超過內容雜湊位元組預算"
    digest = hashlib.sha256()
    read = 0
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                read += len(chunk)
                if read > max_bytes:
                    return None, "超過內容雜湊位元組預算"
                digest.update(chunk)
        after = path.stat()
    except OSError as exc:
        return None, str(exc)
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        return None, "雜湊期間檔案改變"
    return digest.hexdigest(), None


def make_artifact(root: Path, path: Path) -> dict[str, Any]:
    relative = unicodedata.normalize("NFC", path.relative_to(root).as_posix())
    try:
        stat = path.lstat()
        return {
            "path": relative,
            "existence": "存在",
            "kind": "符號連結" if path.is_symlink() else "檔案",
            "size": stat.st_size,
            "modified_ns": stat.st_mtime_ns,
            "mode": stat.st_mode,
            "name_risk": "僅名稱命中_未讀內容" if blocked_name(relative) else "未命中名稱標記",
            "content_sha256": None,
            "content_evidence": "中繼資料",
        }
    except OSError as exc:
        return {
            "path": relative,
            "existence": "中繼資料錯誤",
            "error": str(exc),
            "content_sha256": None,
            "content_evidence": "無",
        }


def bounded_walk(
    root: Path,
    excluded_root: Path,
    max_files: int,
    max_depth: int,
    seconds: float,
) -> tuple[list[dict[str, Any]], bool, list[str]]:
    started = time.monotonic()
    artifacts: list[dict[str, Any]] = []
    errors: list[str] = []
    truncated = False

    def onerror(error: OSError) -> None:
        errors.append(str(error))

    for current, directories, files in os.walk(root, followlinks=False, onerror=onerror):
        current_path = Path(current).resolve()
        depth = len(current_path.relative_to(root).parts)
        kept: list[str] = []
        for name in directories:
            candidate = (current_path / name).resolve()
            if name == ".git" or candidate == excluded_root or within(candidate, excluded_root):
                continue
            kept.append(name)
        directories[:] = kept
        if depth >= max_depth:
            if directories:
                truncated = True
            directories[:] = []
        for name in sorted(files):
            if time.monotonic() - started > seconds or len(artifacts) >= max_files:
                truncated = True
                break
            candidate = current_path / name
            if within(candidate.resolve(), excluded_root):
                continue
            artifacts.append(make_artifact(root, candidate))
        if truncated and (time.monotonic() - started > seconds or len(artifacts) >= max_files):
            break
    return sorted(artifacts, key=lambda item: item["path"]), truncated, errors


def apply_hash_authorizations(
    root: Path,
    artifacts: list[dict[str, Any]],
    raw_paths: list[str],
    max_bytes: int,
) -> list[dict[str, str]]:
    by_path = {item["path"]: item for item in artifacts}
    holds: list[dict[str, str]] = []
    for raw in raw_paths:
        relative = Path(raw)
        normalized = relative.as_posix()
        if relative.is_absolute() or ".." in relative.parts:
            holds.append({"path": raw, "reason": "拒絕絕對路徑或父層跳脫"})
            continue
        if blocked_name(normalized):
            holds.append({"path": raw, "reason": "敏感名稱候選不得內容雜湊"})
            continue
        target = (root / relative).resolve()
        if not within(target, root) or not target.is_file() or target.is_symlink():
            holds.append({"path": raw, "reason": "路徑不存在、不是一般檔案或逃逸"})
            continue
        item = by_path.get(unicodedata.normalize("NFC", target.relative_to(root).as_posix()))
        if item is None:
            holds.append({"path": raw, "reason": "路徑不在本次有界掃描結果內"})
            continue
        digest, error = hash_file(target, max_bytes)
        if error:
            holds.append({"path": raw, "reason": error})
            continue
        item["content_sha256"] = digest
        item["content_evidence"] = "完整內容雜湊"
    return holds


def new_run_dir(output_root: Path, prefix: str) -> tuple[str, Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"{prefix}_{stamp}_{uuid.uuid4().hex[:8]}"
    run_dir = output_root / run_id
    run_dir.mkdir(exist_ok=False)
    return run_id, run_dir


def scan(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print("掃描根目錄不存在", file=sys.stderr)
        return 2
    try:
        output_root = output_location(root, args.output_root)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    git_before = git_marker(root)
    artifacts, truncated, errors = bounded_walk(
        root, output_root, args.max_files, args.max_depth, args.time_budget_seconds
    )
    for item in artifacts:
        path_key = item["path"].casefold() if args.path_case_mode == "fold" else item["path"]
        item["adi_path_key"] = path_key
    key_counts: dict[str, int] = {}
    for item in artifacts:
        key = item["adi_path_key"]
        key_counts[key] = key_counts.get(key, 0) + 1
    coordinate_collisions = sorted(key for key, count in key_counts.items() if count > 1)
    hash_holds = apply_hash_authorizations(
        root, artifacts, args.hash_path or [], args.max_hash_bytes
    )
    git_after = git_marker(root)
    state_changed = git_before != git_after
    holds: list[dict[str, Any]] = []
    if coordinate_collisions:
        holds.append({"code": "HOLD_COORDINATE_COLLISION", "adi_path_keys": coordinate_collisions})
    if truncated:
        holds.append({"code": "HOLD_BUDGET_EXHAUSTED"})
    if errors:
        holds.append({"code": "HOLD_SCAN_INCOMPLETE", "errors": errors})
    if state_changed:
        holds.append({"code": "HOLD_STATE_CHANGED"})
    if hash_holds:
        holds.append({"code": "HOLD_HASH_PATHS", "items": hash_holds})

    observed = utc_now().isoformat()
    snapshot: dict[str, Any] = {
        "protocol": SNAPSHOT_PROTOCOL,
        "protocol_version": VERSION,
        "hash_scope": "此物件排除 snapshot_sha256 欄位後的標準 JSON",
        "logical_root_id": args.logical_root_id,
        "coordinate": {
            "node": args.node_id or socket.gethostname(),
            "root": str(root),
            "platform": platform.system(),
            "platform_release": platform.release(),
            "observed_at": observed,
            "git_before": git_before,
            "git_after": git_after,
        },
        "scan_policy": {
            "max_files": args.max_files,
            "max_depth": args.max_depth,
            "time_budget_seconds": args.time_budget_seconds,
            "max_hash_bytes": args.max_hash_bytes,
            "hash_authorized_paths": sorted(args.hash_path or []),
            "output_root_excluded": output_root.relative_to(root).as_posix(),
            "path_case_mode": args.path_case_mode,
            "coordinate_normalization": "POSIX_SEPARATOR_UNICODE_NFC_V1",
            "content_read_default": False,
        },
        "coverage": "部分_預算截斷" if truncated else "聲明範圍內查詢完成",
        "artifacts": artifacts,
        "holds": holds,
        "source_content_embedded": False,
        "snapshot_sha256": None,
    }
    snapshot["snapshot_sha256"] = object_digest(snapshot, "snapshot_sha256")
    decision = "PASS_SNAPSHOT" if not holds else "HOLD_SNAPSHOT"
    run_id, run_dir = new_run_dir(output_root, "SCAN")
    validation = {
        "run_id": run_id,
        "decision": decision,
        "artifact_count": len(artifacts),
        "coverage": snapshot["coverage"],
        "state_changed": state_changed,
        "scan_errors": errors,
        "hash_holds": hash_holds,
        "source_content_embedded": False,
    }
    packet = {
        "protocol": TRANSFER_PROTOCOL,
        "protocol_version": VERSION,
        "mode": "STATE_SNAPSHOT",
        "run_id": run_id,
        "source_snapshot_sha256": snapshot["snapshot_sha256"],
        "reconstruction_target": "ANALYSIS_ARTIFACTS_ONLY",
        "source_content_embedded": False,
        "required_artifacts": [
            "ADI_STATE_SNAPSHOT.json", "SNAPSHOT_SHA256.txt",
            "SEAL.json",
        ],
        "recipe": [
            "驗證快照標準 SHA-256",
            "依 logical_root_id 與 ADI 相對路徑重建節點",
            "依證據強度重建狀態向量與待分析缺口索引",
            "套用當次記憶體驗證結果與封印，不提升未證明權威",
        ],
        "limitations": ["不含原始程式內容", "不能單獨重建來源檔或證明來源身分"],
    }
    seal = {
        "run_id": run_id,
        "decision": decision,
        "snapshot_sha256": snapshot["snapshot_sha256"],
        "output_root": str(output_root),
        "no_overwrite": True,
        "source_content_embedded": False,
        "holds": holds,
    }
    write_json(run_dir / "ADI_STATE_SNAPSHOT.json", snapshot)
    atomic_new(run_dir / "SNAPSHOT_SHA256.txt", f"{snapshot['snapshot_sha256']}\n".encode())
    write_json(run_dir / "ADI_GENERATIVE_TRANSFER_PACKET.json", packet)
    write_json(run_dir / "SEAL.json", seal)
    print(json.dumps({"state": decision, "run_id": run_id, "output": str(run_dir), "snapshot_sha256": snapshot["snapshot_sha256"], "validation": validation, "report_persistence": "MEMORY_ONLY"}, ensure_ascii=False))
    return 0 if not holds else 4


def load_snapshot(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(value, dict) or value.get("protocol") != SNAPSHOT_PROTOCOL:
        return None, "不是支援的 ADI 狀態快照"
    expected = value.get("snapshot_sha256")
    actual = object_digest(value, "snapshot_sha256")
    if not isinstance(expected, str) or expected != actual:
        return None, "快照 SHA-256 驗證失敗"
    return value, None


def metadata_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return item.get("existence"), item.get("kind"), item.get("size"), item.get("modified_ns"), item.get("mode")


def artifact_index(snapshot: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """建立不容許覆蓋的 ADI 座標索引，並回報重複或無效座標。"""
    index: dict[str, dict[str, Any]] = {}
    invalid_or_duplicate: list[str] = []
    artifacts = snapshot.get("artifacts")
    if not isinstance(artifacts, list):
        return {}, ["<artifacts_not_list>"]
    for position, item in enumerate(artifacts):
        if not isinstance(item, dict):
            invalid_or_duplicate.append(f"<invalid_artifact:{position}>")
            continue
        key = item.get("adi_path_key", item.get("path"))
        if not isinstance(key, str) or not key:
            invalid_or_duplicate.append(f"<invalid_coordinate:{position}>")
            continue
        if key in index:
            invalid_or_duplicate.append(key)
            continue
        index[key] = item
    return index, sorted(set(invalid_or_duplicate))


def compare(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace_root).expanduser().resolve()
    if not workspace.is_dir():
        print("工作根目錄不存在", file=sys.stderr)
        return 2
    try:
        output_root = output_location(workspace, args.output_root)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    before, before_error = load_snapshot(Path(args.before).expanduser().resolve())
    after, after_error = load_snapshot(Path(args.after).expanduser().resolve())
    if before_error or after_error or before is None or after is None:
        print(before_error or after_error, file=sys.stderr)
        return 3
    holds: list[dict[str, Any]] = []
    for side, snapshot in (("before", before), ("after", after)):
        source_holds = snapshot.get("holds")
        if not isinstance(source_holds, list):
            holds.append({"code": "HOLD_SOURCE_SNAPSHOT_HOLDS_INVALID", "side": side})
        elif source_holds:
            source_codes = sorted(
                {
                    item.get("code", "HOLD_UNSPECIFIED")
                    for item in source_holds
                    if isinstance(item, dict)
                }
            )
            holds.append(
                {
                    "code": "HOLD_SOURCE_SNAPSHOT_NOT_PASS",
                    "side": side,
                    "source_hold_codes": source_codes or ["HOLD_UNSPECIFIED"],
                }
            )
    if before.get("logical_root_id") != after.get("logical_root_id"):
        holds.append({"code": "HOLD_COORDINATE_MISMATCH", "field": "logical_root_id"})
    before_policy = before.get("scan_policy", {})
    after_policy = after.get("scan_policy", {})
    comparable_keys = ("max_depth", "output_root_excluded", "path_case_mode", "coordinate_normalization")
    if any(before_policy.get(key) != after_policy.get(key) for key in comparable_keys):
        holds.append({"code": "HOLD_SCAN_POLICY_MISMATCH"})

    before_map, before_collisions = artifact_index(before)
    after_map, after_collisions = artifact_index(after)
    if before_collisions:
        holds.append(
            {
                "code": "HOLD_COORDINATE_COLLISION",
                "side": "before",
                "coordinate_count": len(before_collisions),
                "coordinates": before_collisions,
            }
        )
    if after_collisions:
        holds.append(
            {
                "code": "HOLD_COORDINATE_COLLISION",
                "side": "after",
                "coordinate_count": len(after_collisions),
                "coordinates": after_collisions,
            }
        )
    added = sorted(set(after_map) - set(before_map))
    removed = sorted(set(before_map) - set(after_map))
    modified_content: list[str] = []
    modified_metadata: list[str] = []
    unchanged_strong: list[str] = []
    unchanged_weak: list[str] = []
    for path in sorted(set(before_map) & set(after_map)):
        left, right = before_map[path], after_map[path]
        left_hash, right_hash = left.get("content_sha256"), right.get("content_sha256")
        if left_hash and right_hash:
            if left_hash != right_hash:
                modified_content.append(path)
            elif metadata_key(left) != metadata_key(right):
                modified_metadata.append(path)
            else:
                unchanged_strong.append(path)
        elif metadata_key(left) != metadata_key(right):
            modified_metadata.append(path)
        else:
            unchanged_weak.append(path)

    added_by_hash: dict[str, list[str]] = {}
    for path in added:
        digest = after_map[path].get("content_sha256")
        if digest:
            added_by_hash.setdefault(digest, []).append(path)
    possible_moves: list[dict[str, Any]] = []
    for path in removed:
        digest = before_map[path].get("content_sha256")
        if digest and digest in added_by_hash:
            possible_moves.append({"from": path, "to_candidates": added_by_hash[digest], "evidence": "相同內容雜湊_僅可能移位"})

    delta: dict[str, Any] = {
        "protocol": "W7TP-8D-ADI-STATE-DELTA",
        "protocol_version": VERSION,
        "hash_scope": "此物件排除 delta_sha256 欄位後的標準 JSON",
        "logical_root_id": after.get("logical_root_id"),
        "comparison_mode": args.comparison_mode,
        "before_node": before.get("coordinate", {}).get("node"),
        "after_node": after.get("coordinate", {}).get("node"),
        "before_snapshot_sha256": before["snapshot_sha256"],
        "after_snapshot_sha256": after["snapshot_sha256"],
        "added": added,
        "removed": removed,
        "modified_content": modified_content,
        "modified_metadata": modified_metadata,
        "unchanged_strong": unchanged_strong,
        "unchanged_metadata_only": unchanged_weak,
        "possible_moves": possible_moves,
        "code_loop_gaps": {
            "state": "REQUIRES_8D_ADI_ANALYSIS",
            "changed_paths": sorted(set(added + removed + modified_content + modified_metadata)),
        },
        "holds": holds,
        "source_content_embedded": False,
        "delta_sha256": None,
    }
    delta["delta_sha256"] = object_digest(delta, "delta_sha256")
    decision = "PASS_DELTA" if not holds else "HOLD_DELTA"
    run_id, run_dir = new_run_dir(output_root, "COMPARE")
    summary = (
        "# 8D ADI 狀態差異摘要\n\n"
        f"- 新增：{len(added)}\n"
        f"- 消失：{len(removed)}\n"
        f"- 內容改變：{len(modified_content)}\n"
        f"- 中繼資料改變：{len(modified_metadata)}\n"
        f"- 強一致未變：{len(unchanged_strong)}\n"
        f"- 僅中繼資料未變：{len(unchanged_weak)}\n"
        f"- 可能移位：{len(possible_moves)}\n"
        "\n未經 8D／ADI 關係與閉環分析前，不得把路徑差異直接當成因果或功能影響。\n"
    )
    validation = {
        "run_id": run_id,
        "decision": decision,
        "before_snapshot_valid": True,
        "after_snapshot_valid": True,
        "coordinate_comparable": not any(item["code"] == "HOLD_COORDINATE_MISMATCH" for item in holds),
        "policy_comparable": not any(item["code"] == "HOLD_SCAN_POLICY_MISMATCH" for item in holds),
        "comparison_mode": args.comparison_mode,
        "holds": holds,
    }
    packet = {
        "protocol": TRANSFER_PROTOCOL,
        "protocol_version": VERSION,
        "mode": "CROSS_NODE_STATE_DELTA" if args.comparison_mode == "cross-node" else "STATE_DELTA",
        "run_id": run_id,
        "before_snapshot_sha256": before["snapshot_sha256"],
        "after_snapshot_sha256": after["snapshot_sha256"],
        "delta_sha256": delta["delta_sha256"],
        "reconstruction_target": "ANALYSIS_ARTIFACTS_ONLY",
        "source_content_embedded": False,
        "required_artifacts": ["ADI_STATE_DELTA.json", "DELTA_SHA256.txt", "SEAL.json"],
        "recipe": [
            "驗證前後快照與差異 SHA-256",
            "依 ADI 路徑座標重建新增、消失與改變集合",
            "將改變路徑送入程式碼閉環與影響傳播分析",
            "依證據強度區分內容差異與中繼資料差異",
            "套用當次記憶體驗證結果與封印，不提升未證明權威",
        ],
        "limitations": ["不含原始程式內容", "可能移位不是身分延續證明"],
    }
    seal = {
        "run_id": run_id,
        "decision": decision,
        "delta_sha256": delta["delta_sha256"],
        "no_overwrite": True,
        "source_content_embedded": False,
        "holds": holds,
    }
    write_json(run_dir / "ADI_STATE_DELTA.json", delta)
    atomic_new(run_dir / "DELTA_SHA256.txt", f"{delta['delta_sha256']}\n".encode())
    write_json(run_dir / "ADI_GENERATIVE_TRANSFER_PACKET.json", packet)
    write_json(run_dir / "SEAL.json", seal)
    print(json.dumps({"state": decision, "run_id": run_id, "output": str(run_dir), "delta_sha256": delta["delta_sha256"], "report": summary, "validation": validation, "report_persistence": "MEMORY_ONLY"}, ensure_ascii=False))
    return 0 if not holds else 4


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="8D/ADI 狀態快照與差異保存")
    commands = root.add_subparsers(dest="command", required=True)
    scan_parser = commands.add_parser("scan", help="建立不可覆寫快照")
    scan_parser.add_argument("--root", required=True)
    scan_parser.add_argument("--output-root", required=True)
    scan_parser.add_argument("--logical-root-id", required=True)
    scan_parser.add_argument("--node-id")
    scan_parser.add_argument("--path-case-mode", choices=("preserve", "fold"), default="preserve")
    scan_parser.add_argument("--max-files", type=int, default=5000)
    scan_parser.add_argument("--max-depth", type=int, default=16)
    scan_parser.add_argument("--time-budget-seconds", type=float, default=30.0)
    scan_parser.add_argument("--hash-path", action="append")
    scan_parser.add_argument("--max-hash-bytes", type=int, default=16 * 1024 * 1024)
    compare_parser = commands.add_parser("compare", help="比較兩個快照")
    compare_parser.add_argument("--workspace-root", required=True)
    compare_parser.add_argument("--before", required=True)
    compare_parser.add_argument("--after", required=True)
    compare_parser.add_argument("--output-root", required=True)
    compare_parser.add_argument("--comparison-mode", choices=("temporal", "cross-node"), default="temporal")
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "scan":
        if not 1 <= args.max_files <= 1_000_000 or not 1 <= args.max_depth <= 128:
            print("掃描筆數或深度預算不合法", file=sys.stderr)
            return 2
        if not 0.5 <= args.time_budget_seconds <= 3600 or args.max_hash_bytes < 1:
            print("時間或雜湊位元組預算不合法", file=sys.stderr)
            return 2
        return scan(args)
    return compare(args)


if __name__ == "__main__":
    raise SystemExit(main())
