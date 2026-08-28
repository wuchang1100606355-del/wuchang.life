#!/usr/bin/env python3
"""對精確安全路徑建立有界 ADI 段落座標，不輸出正文或值。"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BLOCKED = (
    ".env", "secret", "credential", "password", "token", "dead_letter",
    "member_plaintext", "private", "why_it_runs",
    "application_default_credentials",
)
ALLOWED = {
    ".md", ".json", ".yaml", ".yml", ".py", ".sh", ".ps1",
    ".js", ".jsx", ".ts", ".tsx", ".xml", ".html", ".toml",
}


def stable_id(kind: str, name: str, ordinal: int) -> str:
    value = f"{kind}\0{name}\0{ordinal}".encode("utf-8", "replace")
    return hashlib.sha256(value).hexdigest()[:24]


def segment(
    kind: str,
    name: str,
    line_start: int | None,
    line_end: int | None,
    ordinal: int,
    emit_identifiers: bool,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "kind": kind,
        "segment_id": stable_id(kind, name, ordinal),
        "line_start": line_start,
        "line_end": line_end,
    }
    if emit_identifiers:
        result["identifier"] = name[:240]
    return result


def safe_target(root: Path, raw: str) -> tuple[Path | None, str | None]:
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        return None, "拒絕絕對路徑或父層跳脫"
    lowered = relative.as_posix().lower()
    if any(marker in lowered for marker in BLOCKED):
        return None, "敏感名稱候選_僅保留路徑層"
    target = (root / relative).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None, "拒絕根目錄逃逸"
    if not target.is_file() or target.is_symlink():
        return None, "檔案不存在、不是一般檔案或為符號連結"
    if target.suffix.lower() not in ALLOWED:
        return None, "非允許的文字檔類型"
    return target, None


def markdown_segments(text: str, emit: bool) -> list[dict[str, Any]]:
    found: list[tuple[int, str, str]] = []
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            found.append((number, f"標題{len(match.group(1))}", match.group(2)))
    output: list[dict[str, Any]] = []
    for index, (line, kind, name) in enumerate(found):
        end = found[index + 1][0] - 1 if index + 1 < len(found) else len(text.splitlines())
        output.append(segment(kind, name, line, end, index, emit))
    return output[:200]


def mapping_segments(text: str, suffix: str, emit: bool, complete: bool) -> tuple[list[dict[str, Any]], str | None]:
    if suffix == ".json":
        if not complete:
            return [], "不推測截斷 JSON 的結構鍵"
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return [], "JSON 無法解析"
        if not isinstance(value, dict):
            return [], "JSON 頂層不是物件"
        return [segment("頂層結構鍵", str(key), None, None, index, emit) for index, key in enumerate(list(value)[:200])], None
    output: list[dict[str, Any]] = []
    ordinal = 0
    patterns = (
        re.compile(r"^([A-Za-z0-9_.-]+)\s*:\s*(?:#.*)?$"),
        re.compile(r"^\[([^\]]+)\]\s*$"),
    )
    for number, line in enumerate(text.splitlines(), 1):
        for pattern in patterns:
            match = pattern.match(line)
            if match:
                output.append(segment("頂層結構鍵", match.group(1), number, number, ordinal, emit))
                ordinal += 1
                break
    return output[:200], None if complete else "輪廓來自截斷內容"


def python_segments(text: str, emit: bool, complete: bool) -> tuple[list[dict[str, Any]], str | None]:
    if complete:
        try:
            tree = ast.parse(text)
            output: list[dict[str, Any]] = []
            ordinal = 0
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    output.append(segment("類別", node.name, node.lineno, getattr(node, "end_lineno", node.lineno), ordinal, emit))
                    ordinal += 1
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    output.append(segment("函式", node.name, node.lineno, getattr(node, "end_lineno", node.lineno), ordinal, emit))
                    ordinal += 1
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        output.append(segment("匯入", alias.name, node.lineno, node.lineno, ordinal, emit))
                        ordinal += 1
                elif isinstance(node, ast.ImportFrom):
                    output.append(segment("匯入", node.module or "相對模組", node.lineno, node.lineno, ordinal, emit))
                    ordinal += 1
            return sorted(output, key=lambda item: (item["line_start"] or 0, item["segment_id"]))[:200], None
        except SyntaxError:
            pass
    return generic_segments(text, emit), "使用有限文字輪廓"


def generic_segments(text: str, emit: bool) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    patterns = (
        ("函式", re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)")),
        ("函式", re.compile(r"^\s*function\s+([A-Za-z_$][\w$]*)")),
        ("類別", re.compile(r"^\s*class\s+([A-Za-z_]\w*)")),
        ("匯入", re.compile(r"^\s*(?:from|import)\s+([^\s;]+)")),
    )
    ordinal = 0
    for number, line in enumerate(text.splitlines(), 1):
        for kind, pattern in patterns:
            match = pattern.match(line)
            if match:
                output.append(segment(kind, match.group(1), number, number, ordinal, emit))
                ordinal += 1
                break
    return output[:200]


def outline(path: Path, text: str, complete: bool, emit: bool) -> tuple[list[dict[str, Any]], str | None]:
    suffix = path.suffix.lower()
    if suffix == ".md":
        return markdown_segments(text, emit), None if complete else "輪廓來自截斷內容"
    if suffix in {".json", ".yaml", ".yml", ".toml"}:
        return mapping_segments(text, suffix, emit, complete)
    if suffix == ".py":
        return python_segments(text, emit, complete)
    return generic_segments(text, emit), None if complete else "輪廓來自截斷內容"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="建立有界 ADI 段落座標")
    result.add_argument("--root", required=True)
    result.add_argument("--path", action="append", required=True, dest="paths")
    result.add_argument("--max-files", type=int, default=8)
    result.add_argument("--max-bytes-per-file", type=int, default=65536)
    result.add_argument("--max-total-bytes", type=int, default=524288)
    result.add_argument("--allow-content-read", action="store_true")
    result.add_argument("--emit-identifiers", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    if not args.allow_content_read:
        print("缺少明確內容讀取授權", file=sys.stderr)
        return 2
    if not 1 <= args.max_files <= 32:
        print("檔案預算不合法", file=sys.stderr)
        return 2
    if not 1024 <= args.max_bytes_per_file <= 1048576 or args.max_total_bytes < args.max_bytes_per_file:
        print("位元組預算不合法", file=sys.stderr)
        return 2
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print("根目錄不存在", file=sys.stderr)
        return 2

    requested_over_budget = len(args.paths) > args.max_files
    results: list[dict[str, Any]] = []
    total_read = 0
    state_changed = False
    truncated = requested_over_budget
    for raw in args.paths[: args.max_files]:
        target, hold = safe_target(root, raw)
        if hold:
            results.append({"path": raw, "state": "保留", "reason": hold})
            continue
        assert target is not None
        before = target.stat()
        remaining = args.max_total_bytes - total_read
        budget = min(args.max_bytes_per_file, remaining)
        if budget < 1:
            truncated = True
            results.append({"path": raw, "state": "保留", "reason": "總讀取預算用盡"})
            continue
        with target.open("rb") as handle:
            data = handle.read(budget + 1)
        after = target.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            state_changed = True
            results.append({"path": raw, "state": "保留", "reason": "讀取期間檔案改變"})
            continue
        visible_data = data[:budget]
        total_read += len(visible_data)
        if b"\0" in visible_data:
            results.append({"path": raw, "state": "保留", "reason": "疑似二進位內容"})
            continue
        complete = len(data) <= budget
        truncated = truncated or not complete
        text = visible_data.decode("utf-8", "replace")
        segments, note = outline(target, text, complete, args.emit_identifiers)
        results.append({
            "path": target.relative_to(root).as_posix(),
            "state": "輪廓完成" if complete else "輪廓截斷",
            "file_size": before.st_size,
            "bytes_read": len(visible_data),
            "content_complete": complete,
            "content_sha256": hashlib.sha256(visible_data).hexdigest() if complete else None,
            "segments": segments,
            "identifiers_emitted": args.emit_identifiers,
            "note": note,
            "body_text_emitted": False,
        })

    mapped = sum(item.get("state") in {"輪廓完成", "輪廓截斷"} for item in results)
    state = "PASS_BOUNDED_ADI_MAP"
    if state_changed:
        state = "HOLD_STATE_CHANGED"
    elif mapped == 0:
        state = "HOLD_ALL_PATHS_UNREAD"
    elif truncated:
        state = "HOLD_BUDGET_EXHAUSTED"
    output = {
        "state": state,
        "root": str(root),
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "read_level": "輪廓層",
        "files_requested": len(args.paths),
        "files_processed": len(results),
        "omitted_paths": max(0, len(args.paths) - args.max_files),
        "bytes_read": total_read,
        "budget": {
            "max_files": args.max_files,
            "max_bytes_per_file": args.max_bytes_per_file,
            "max_total_bytes": args.max_total_bytes,
        },
        "results": results,
        "unknown_frontier": ["未讀路徑", "截斷檔案", "動態或外部依賴"] if state != "PASS_BOUNDED_ADI_MAP" else ["動態或外部依賴"],
        "body_text_emitted": False,
        "writes_performed": False,
        "warning": "未讀或截斷範圍保持未知，不得推論為不存在",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if state == "PASS_BOUNDED_ADI_MAP" else 4


if __name__ == "__main__":
    raise SystemExit(main())
