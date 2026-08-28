#!/usr/bin/env python3
"""有界、只讀、不讀內容且保持指定範圍的 8D/ADI 基線。"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


RISK_NAMES = (
    ".env", "secret", "credential", "password", "token", "dead_letter",
    "member_plaintext", "private", "why_it_runs",
    "application_default_credentials",
)

GROUPS = {
    "結構候選": ("schema", "contract", "protocol", "manifest"),
    "權威候選": ("authority", "governance", "policy", "decision", "receipt"),
    "驗證候選": ("test", "verify", "validator", "check", "spec"),
    "入口候選": ("runtime", "service", "gateway", "entry", "main", "cli"),
    "證據候選": ("evidence", "seal", "audit", "report", "sha256"),
    "索引文件候選": ("readme", "docs", "guide", "index"),
}


def git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_CONFIG_COUNT"] = "2"
    env["GIT_CONFIG_KEY_0"] = "core.fsmonitor"
    env["GIT_CONFIG_VALUE_0"] = "false"
    env["GIT_CONFIG_KEY_1"] = "core.hooksPath"
    env["GIT_CONFIG_VALUE_1"] = os.devnull
    return env


def git_text(root: Path, *args: str, timeout: float = 10.0) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
            env=git_env(),
        )
    except subprocess.TimeoutExpired:
        return 124, "", "唯讀版本查詢逾時"
    except OSError as exc:
        return 127, "", str(exc)
    return (
        result.returncode,
        result.stdout.decode("utf-8", "replace"),
        result.stderr.decode("utf-8", "replace").strip(),
    )


def git_nul_bounded(
    root: Path, args: list[str], max_items: int, timeout: float
) -> tuple[list[str], bool, str | None]:
    command = ["git", "-C", str(root), *args]
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=git_env(),
        )
    except OSError as exc:
        return [], False, str(exc)
    assert process.stdout is not None
    started = time.monotonic()
    buffer = b""
    items: list[str] = []
    truncated = False
    try:
        while True:
            if time.monotonic() - started > timeout:
                process.kill()
                return items, True, "唯讀版本查詢超過時間預算"
            chunk = process.stdout.read(4096)
            if not chunk:
                break
            buffer += chunk
            parts = buffer.split(b"\0")
            buffer = parts.pop()
            items.extend(part.decode("utf-8", "replace") for part in parts if part)
            if len(items) > max_items:
                truncated = True
                process.terminate()
                break
        if buffer and len(items) <= max_items:
            items.append(buffer.decode("utf-8", "replace"))
        try:
            _, stderr = process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            _, stderr = process.communicate()
        error = stderr.decode("utf-8", "replace").strip() if stderr else None
        if process.returncode not in (0, -15) and not truncated:
            return items[:max_items], truncated, error or "唯讀版本查詢失敗"
        return items[:max_items], truncated, error
    finally:
        if process.poll() is None:
            process.kill()


def candidate_groups(path: str) -> list[str]:
    lowered = path.lower()
    result = [name for name, keys in GROUPS.items() if any(key in lowered for key in keys)]
    return result or ["未分類候選"]


def name_risk(path: str) -> str:
    lowered = path.lower()
    return (
        "僅名稱命中_未讀內容"
        if any(marker in lowered for marker in RISK_NAMES)
        else "未命中名稱標記"
    )


def file_record(base: Path, relative: str, tracking: str) -> dict[str, object]:
    target = base / relative
    try:
        stat = target.lstat()
        existence, size, modified, link = "存在", stat.st_size, stat.st_mtime_ns, target.is_symlink()
    except OSError:
        existence, size, modified, link = "不存在或中繼資料不可讀", None, None, False
    return {
        "path": relative.replace(os.sep, "/"),
        "existence": existence,
        "tracking": tracking,
        "size": size,
        "modified_ns": modified,
        "symlink": link,
        "candidate_groups": candidate_groups(relative),
        "risk": name_risk(relative),
        "content_read": False,
        "content_hash": None,
        "conclusion": "路徑推論",
    }


def index_marker(repo: Path) -> tuple[int | None, int | None]:
    rc, path, _ = git_text(repo, "rev-parse", "--git-path", "index")
    if rc:
        return None, None
    index = Path(path.strip())
    if not index.is_absolute():
        index = repo / index
    try:
        stat = index.stat()
        return stat.st_size, stat.st_mtime_ns
    except OSError:
        return None, None


def parse_status(items: list[str]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    index = 0
    while index < len(items):
        item = items[index]
        if len(item) >= 4:
            code, path = item[:2], item[3:]
            row = {"code": code, "path": path}
            if ("R" in code or "C" in code) and index + 1 < len(items):
                row["source_path"] = items[index + 1]
                index += 1
            output.append(row)
        index += 1
    return output


def git_inventory(requested: Path, limit: int, timeout: float) -> dict[str, object]:
    rc, top, error = git_text(requested, "rev-parse", "--show-toplevel", timeout=timeout)
    if rc:
        raise RuntimeError(error)
    repo = Path(top.strip()).resolve()
    try:
        scope = requested.relative_to(repo).as_posix() or "."
    except ValueError as exc:
        raise RuntimeError("HOLD_WRONG_SCOPE：指定範圍不在解析出的版本庫內") from exc
    pathspec = "." if scope == "." else scope

    rc_head, head_before, head_error = git_text(repo, "rev-parse", "HEAD", timeout=timeout)
    rc_branch, branch_before, _ = git_text(repo, "branch", "--show-current", timeout=timeout)
    branch_name = branch_before.strip() if rc_branch == 0 and branch_before.strip() else None
    rc_upstream, upstream_text, _ = git_text(
        repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}", timeout=timeout
    )
    upstream = upstream_text.strip() if rc_upstream == 0 and upstream_text.strip() else None
    rc_remotes, remotes_text, _ = git_text(repo, "remote", timeout=timeout)
    remote_names = sorted(set(remotes_text.splitlines()))[:32] if rc_remotes == 0 else []
    rc_defaults, defaults_text, _ = git_text(
        repo, "for-each-ref", "--format=%(refname:short)", "refs/remotes/*/HEAD", timeout=timeout
    )
    local_default_refs = sorted(set(defaults_text.splitlines()))[:32] if rc_defaults == 0 else []
    configured_remote = None
    configured_merge_ref = None
    branch_push_remote = None
    invalid_remote_config_fields: list[str] = []
    if branch_name:
        rc_remote, remote_text, _ = git_text(
            repo, "config", "--get", f"branch.{branch_name}.remote", timeout=timeout
        )
        remote_value = remote_text.strip() if rc_remote == 0 else ""
        if remote_value in remote_names or remote_value == ".":
            configured_remote = remote_value
        elif remote_value:
            invalid_remote_config_fields.append("branch.remote")
        rc_merge, merge_text, _ = git_text(
            repo, "config", "--get", f"branch.{branch_name}.merge", timeout=timeout
        )
        configured_merge_ref = merge_text.strip() if rc_merge == 0 and merge_text.strip() else None
        rc_push, push_text, _ = git_text(
            repo, "config", "--get", f"branch.{branch_name}.pushRemote", timeout=timeout
        )
        push_value = push_text.strip() if rc_push == 0 else ""
        if push_value in remote_names:
            branch_push_remote = push_value
        elif push_value:
            invalid_remote_config_fields.append("branch.pushRemote")
    rc_push_default, push_default_text, _ = git_text(
        repo, "config", "--get", "remote.pushDefault", timeout=timeout
    )
    push_default_value = push_default_text.strip() if rc_push_default == 0 else ""
    repository_push_default = push_default_value if push_default_value in remote_names else None
    if push_default_value and repository_push_default is None:
        invalid_remote_config_fields.append("remote.pushDefault")
    candidate_push_remote = branch_push_remote or repository_push_default or configured_remote
    ahead_behind = None
    if upstream:
        rc_counts, counts_text, _ = git_text(
            repo, "rev-list", "--left-right", "--count", f"{upstream}...HEAD", timeout=timeout
        )
        parts = counts_text.split()
        if rc_counts == 0 and len(parts) == 2 and all(part.isdigit() for part in parts):
            ahead_behind = {"behind_local_tracking_ref": int(parts[0]), "ahead_local_tracking_ref": int(parts[1])}
    index_before = index_marker(repo)
    status_items, status_cut, status_error = git_nul_bounded(
        repo,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all", "--", pathspec],
        limit + 1,
        timeout,
    )
    remaining = max(1, limit - min(len(status_items), limit))
    tracked_items, tracked_cut, tracked_error = git_nul_bounded(
        repo, ["ls-files", "-z", "--", pathspec], remaining + 1, timeout
    )
    status_rows = parse_status(status_items[:limit])
    seen: set[str] = set()
    records: list[dict[str, object]] = []
    for row in status_rows:
        path = row["path"]
        if path not in seen and len(records) < limit:
            tracking = "未追蹤" if row["code"] == "??" else "已追蹤變更"
            records.append(file_record(repo, path, tracking))
            seen.add(path)
    for path in tracked_items:
        if path not in seen and len(records) < limit:
            records.append(file_record(repo, path, "已追蹤"))
            seen.add(path)

    rc_after, head_after, _ = git_text(repo, "rev-parse", "HEAD", timeout=timeout)
    rc_branch_after, branch_after, _ = git_text(repo, "branch", "--show-current", timeout=timeout)
    index_after = index_marker(repo)
    state_changed = (
        rc_head != rc_after
        or head_before.strip() != head_after.strip()
        or rc_branch != rc_branch_after
        or branch_before.strip() != branch_after.strip()
        or index_before != index_after
    )
    truncated = status_cut or tracked_cut
    errors = [item for item in (status_error, tracked_error) if item]
    group_counts = Counter(
        group for item in records for group in item["candidate_groups"]  # type: ignore[index]
    )
    return {
        "mode": "GIT_作為有界證據",
        "requested_root": str(requested),
        "repository_root": str(repo),
        "scope_pathspec": pathspec,
        "scope_preserved": True,
        "head": head_after.strip() if rc_after == 0 else None,
        "branch": branch_after.strip() if rc_branch_after == 0 and branch_after.strip() else "DETACHED",
        "head_error": head_error if rc_head else None,
        "index_marker_before": index_before,
        "index_marker_after": index_after,
        "state_changed": state_changed,
        "coverage": "部分_預算截斷" if truncated else "聲明範圍內查詢完成",
        "scan_errors": errors,
        "visible_changes": status_rows,
        "artifacts": records,
        "candidate_group_counts": dict(group_counts.most_common()),
        "ignored": "未掃描_節省資源",
        "remote_confirmed": False,
        "remote_note": "未連線查證；本機追蹤參照不得證明遠端現況",
        "delivery_evidence": {
            "configured_upstream": upstream,
            "configured_branch_remote": configured_remote,
            "configured_merge_ref": configured_merge_ref,
            "candidate_push_remote": candidate_push_remote,
            "remote_names": remote_names,
            "local_default_branch_refs": local_default_refs,
            "ahead_behind_local_tracking_ref": ahead_behind,
            "remote_urls_read": False,
            "network_remote_state_read": False,
            "invalid_remote_config_fields": invalid_remote_config_fields,
            "route_authority": "候選設定_仍需治理或使用者授權",
        },
    }


def filesystem_inventory(root: Path, limit: int, max_depth: int, timeout: float) -> dict[str, object]:
    started = time.monotonic()
    records: list[dict[str, object]] = []
    truncated = False
    errors: list[str] = []

    def onerror(error: OSError) -> None:
        errors.append(str(error))

    for current, directories, files in os.walk(root, followlinks=False, onerror=onerror):
        depth = len(Path(current).relative_to(root).parts)
        if depth >= max_depth:
            if directories:
                truncated = True
            directories[:] = []
        else:
            directories[:] = [name for name in directories if name != ".git"]
        for name in sorted(files):
            if time.monotonic() - started > timeout or len(records) >= limit:
                truncated = True
                break
            relative = (Path(current) / name).relative_to(root).as_posix()
            records.append(file_record(root, relative, "無版本索引"))
        if truncated and (time.monotonic() - started > timeout or len(records) >= limit):
            break
    group_counts = Counter(
        group for item in records for group in item["candidate_groups"]  # type: ignore[index]
    )
    return {
        "mode": "有界檔案系統觀察",
        "requested_root": str(root),
        "scope_preserved": True,
        "coverage": "部分_預算截斷" if truncated else "聲明範圍內查詢完成",
        "scan_errors": errors,
        "max_depth": max_depth,
        "artifacts": records,
        "candidate_group_counts": dict(group_counts.most_common()),
        "persistence": "僅觀察_未建立不可變快照",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="建立有界且保持範圍的 8D/ADI 基線")
    parser.add_argument("--root", required=True)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--time-budget-seconds", type=float, default=5.0)
    args = parser.parse_args()
    if not 1 <= args.limit <= 10000 or not 1 <= args.max_depth <= 32:
        print("筆數或深度預算不合法", file=sys.stderr)
        return 2
    if not 0.5 <= args.time_budget_seconds <= 60:
        print("時間預算必須介於 0.5 與 60 秒", file=sys.stderr)
        return 2
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print("根目錄不存在或不是資料夾", file=sys.stderr)
        return 2
    rc, _, _ = git_text(root, "rev-parse", "--is-inside-work-tree")
    try:
        field = (
            git_inventory(root, args.limit, args.time_budget_seconds)
            if rc == 0
            else filesystem_inventory(root, args.limit, args.max_depth, args.time_budget_seconds)
        )
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 3

    state = "PASS_只讀有界觀察"
    if field.get("state_changed"):
        state = "HOLD_STATE_CHANGED"
    elif field.get("scan_errors"):
        state = "HOLD_SCAN_INCOMPLETE"
    elif field.get("coverage") == "部分_預算截斷":
        state = "HOLD_BUDGET_EXHAUSTED"

    output = {
        "state": state,
        "coordinate": {
            "node": socket.gethostname(),
            "root": str(root),
            "observed_at": datetime.now(timezone.utc).isoformat(),
        },
        "budget": {
            "max_items": args.limit,
            "max_depth": args.max_depth,
            "max_seconds": args.time_budget_seconds,
        },
        "evidence_level": "觀察",
        "authority_state": "未判定",
        "content_read": False,
        "content_hashing": False,
        "writes_performed": False,
        "field": field,
        "warnings": [
            "路徑群組只是候選，不是功能或依賴證據",
            "未讀內容，不能判定真實敏感內容",
            "未查證正式權威、遠端、部署或執行效果",
        ],
        "next_exact_action": "從目前範圍選最多八個安全樞紐建立 ADI 段落輪廓",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if state.startswith("PASS") else 4


if __name__ == "__main__":
    raise SystemExit(main())
