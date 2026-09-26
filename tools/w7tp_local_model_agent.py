#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.msi_local_llm_route import resolve_msi_ollama_url

DEFAULT_OLLAMA_URL_OVERRIDE = os.getenv("TAIJI_LOCAL_OLLAMA_URL", "").strip()
DEFAULT_MODEL = os.getenv("TAIJI_LOCAL_MODEL", "taiji-qwen2.5-coder-7b:ctx16k")
MAX_STEPS = int(os.getenv("TAIJI_LOCAL_AGENT_MAX_STEPS", "32"))
MAX_READ_LINES = 400
MAX_SEARCH_HITS = 80
MAX_WRITE_BYTES = 2 * 1024 * 1024
SOURCE_ROOTS = {
    "core", "services", "tools", "capabilities", "configs", "schemas",
    "scripts", "tests", "docs", "web", "products", "deploy", "legacy_core",
    "runtime_adapters", "models", "prompts", ".skill-build",
}
def _safe_rel(value: str) -> str:
    raw = str(value or "").strip().replace("\\", "/")
    if not raw or raw.startswith("/") or raw.startswith("../") or "/../" in raw:
        raise ValueError("PATH_INVALID")
    return Path(raw).as_posix()


def _safe_path(root: Path, rel: str) -> Path:
    rel = _safe_rel(rel)
    target = (root / rel).resolve()
    root_resolved = root.resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise ValueError("PATH_ESCAPE")
    return target


def _source_allowed(rel: str) -> bool:
    parts = Path(_safe_rel(rel)).parts
    return bool(parts) and parts[0] in SOURCE_ROOTS


def _text(path: Path) -> str:
    if path.stat().st_size > MAX_WRITE_BYTES:
        raise ValueError("FILE_TOO_LARGE")
    return path.read_text(encoding="utf-8", errors="replace")
class AgentTools:
    def __init__(self, live: Path, shadow: Path, initial: list[str]) -> None:
        self.live = live.resolve()
        self.shadow = shadow.resolve()
        self.allowed: set[str] = set()
        self.writable: set[str] = set()
        for item in initial:
            if item != "product_and_competitor_evidence":
                try:
                    rel = _safe_rel(item)
                    self.allowed.add(rel)
                    self.writable.add(rel)
                except ValueError:
                    pass

    def _read_allowed(self, rel: str) -> bool:
        rel = _safe_rel(rel)
        return any(rel == base or rel.startswith(base.rstrip("/") + "/") for base in self.allowed)

    def _write_allowed(self, rel: str) -> bool:
        rel = _safe_rel(rel)
        for base in self.writable:
            if rel == base or rel.startswith(base.rstrip("/") + "/"):
                return True
        return False

    def list_files(self, path: str = "", limit: int = 200) -> dict[str, Any]:
        max_items = min(max(limit, 1), 500)
        bases: list[Path] = []
        if path:
            rel = _safe_rel(path)
            if not self._read_allowed(rel):
                return {"state": "HOLD_OUTSIDE_AFFECTED_CLOSURE", "files": [], "path": rel}
            bases = [_safe_path(self.live, rel)]
        else:
            bases = [_safe_path(self.live, rel) for rel in sorted(self.allowed)]
        out: list[str] = []
        seen: set[str] = set()
        for base in bases:
            if not base.exists():
                continue
            items = [base] if base.is_file() else base.rglob("*")
            for item in items:
                if not item.is_file() or ".git" in item.parts:
                    continue
                rel = item.relative_to(self.live).as_posix()
                if rel in seen:
                    continue
                seen.add(rel)
                out.append(rel)
                if len(out) >= max_items:
                    return {"state": "PASS", "files": out}
        return {"state": "PASS", "files": out}
    def read_file(self, path: str, start_line: int = 1, end_line: int = 220, shadow: bool = False) -> dict[str, Any]:
        rel = _safe_rel(path)
        if not self._read_allowed(rel):
            return {"state": "HOLD_OUTSIDE_AFFECTED_CLOSURE", "path": rel}
        root = self.shadow if shadow else self.live
        target = _safe_path(root, rel)
        if not target.is_file():
            return {"state": "NOT_FOUND", "path": rel}
        lines = _text(target).splitlines()
        start = max(1, int(start_line))
        end = min(len(lines), max(start, int(end_line)), start + MAX_READ_LINES - 1)
        body = "\n".join(f"{i+1}: {lines[i]}" for i in range(start - 1, end))
        return {"state": "PASS", "path": path, "start": start, "end": end, "content": body}

    def search_text(self, query: str, path: str = "", limit: int = 40) -> dict[str, Any]:
        if not query:
            return {"state": "INVALID_QUERY", "hits": []}
        if path:
            rel = _safe_rel(path)
            if not self._read_allowed(rel):
                return {"state": "HOLD_OUTSIDE_AFFECTED_CLOSURE", "hits": [], "path": rel}
            bases = [_safe_path(self.live, rel)]
        else:
            bases = [_safe_path(self.live, rel) for rel in sorted(self.allowed)]
        hits: list[dict[str, Any]] = []
        seen: set[str] = set()
        needle = query.casefold()
        for base in bases:
            if not base.exists():
                continue
            items = [base] if base.is_file() else base.rglob("*")
            for item in items:
                if not item.is_file() or ".git" in item.parts or item.stat().st_size > MAX_WRITE_BYTES:
                    continue
                rel = item.relative_to(self.live).as_posix()
                if rel in seen:
                    continue
                seen.add(rel)
                try:
                    lines = item.read_text(encoding="utf-8", errors="replace").splitlines()
                except OSError:
                    continue
                for idx, line in enumerate(lines, 1):
                    if needle in line.casefold():
                        hits.append({"path": rel, "line": idx, "text": line[:500]})
                        if len(hits) >= min(max(limit, 1), MAX_SEARCH_HITS):
                            return {"state": "PASS", "hits": hits}
        return {"state": "PASS", "hits": hits}
    def stage_path(self, path: str) -> dict[str, Any]:
        rel = _safe_rel(path)
        if not _source_allowed(rel):
            return {"state": "HOLD_SOURCE_ROOT_NOT_ALLOWED", "path": rel}
        if not self._read_allowed(rel):
            return {"state": "HOLD_OUTSIDE_AFFECTED_CLOSURE", "path": rel}
        src = _safe_path(self.live, rel)
        dst = _safe_path(self.shadow, rel)
        if not src.exists():
            return {"state": "NOT_FOUND", "path": rel}
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            count = 1
        else:
            count = sum(1 for p in src.rglob("*") if p.is_file())
            if count > 500:
                return {"state": "HOLD_STAGE_TOO_LARGE", "path": rel, "file_count": count}
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
        self.writable.add(rel)
        return {"state": "PASS", "path": rel, "file_count": count}

    def replace_text(self, path: str, old: str, new: str, expected: int = 1) -> dict[str, Any]:
        rel = _safe_rel(path)
        if not self._write_allowed(rel):
            return {"state": "HOLD_PATH_NOT_STAGED", "path": rel}
        target = _safe_path(self.shadow, rel)
        if not target.is_file():
            return {"state": "NOT_FOUND", "path": rel}
        content = _text(target)
        count = content.count(old)
        if count != int(expected):
            return {"state": "HOLD_REPLACEMENT_COUNT", "path": rel, "found": count, "expected": expected}
        target.write_text(content.replace(old, new), encoding="utf-8")
        return {"state": "PASS", "path": rel, "replacements": count}
    def write_file(self, path: str, content: str) -> dict[str, Any]:
        rel = _safe_rel(path)
        if not self._write_allowed(rel):
            return {"state": "HOLD_PATH_NOT_STAGED", "path": rel}
        data = content.encode("utf-8")
        if len(data) > MAX_WRITE_BYTES:
            return {"state": "HOLD_WRITE_TOO_LARGE", "path": rel}
        target = _safe_path(self.shadow, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return {"state": "PASS", "path": rel, "bytes": len(data)}

    def run_check(self, kind: str, paths: list[str]) -> dict[str, Any]:
        safe = [_safe_rel(p) for p in paths]
        if kind == "py_compile":
            cmd = ["python3", "-m", "py_compile", *safe]
        elif kind == "pytest":
            cmd = ["python3", "-m", "pytest", "-q", *safe]
        elif kind == "node_check" and len(safe) == 1:
            cmd = ["node", "--check", safe[0]]
        else:
            return {"state": "HOLD_CHECK_NOT_ALLOWED", "kind": kind}
        proc = subprocess.run(cmd, cwd=self.shadow, text=True, capture_output=True, timeout=300)
        return {"state": "PASS" if proc.returncode == 0 else "HOLD_CHECK_FAILED", "rc": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}
TOOL_DEFS = [
    {"type":"function","function":{"name":"list_files","description":"List live repository files under an optional path.","parameters":{"type":"object","properties":{"path":{"type":"string"},"limit":{"type":"integer"}}}}},
    {"type":"function","function":{"name":"read_file","description":"Read a bounded line range from live or shadow source.","parameters":{"type":"object","required":["path"],"properties":{"path":{"type":"string"},"start_line":{"type":"integer"},"end_line":{"type":"integer"},"shadow":{"type":"boolean"}}}}},
    {"type":"function","function":{"name":"search_text","description":"Search live source text for a literal query.","parameters":{"type":"object","required":["query"],"properties":{"query":{"type":"string"},"path":{"type":"string"},"limit":{"type":"integer"}}}}},
    {"type":"function","function":{"name":"stage_path","description":"Copy a needed live source file or small directory into the isolated writable shadow and authorize writes only there.","parameters":{"type":"object","required":["path"],"properties":{"path":{"type":"string"}}}}},
    {"type":"function","function":{"name":"replace_text","description":"Perform an exact replacement in a staged shadow file.","parameters":{"type":"object","required":["path","old","new"],"properties":{"path":{"type":"string"},"old":{"type":"string"},"new":{"type":"string"},"expected":{"type":"integer"}}}}},
    {"type":"function","function":{"name":"write_file","description":"Create or overwrite a staged shadow file.","parameters":{"type":"object","required":["path","content"],"properties":{"path":{"type":"string"},"content":{"type":"string"}}}}},
    {"type":"function","function":{"name":"run_check","description":"Run only allowed deterministic checks in the shadow.","parameters":{"type":"object","required":["kind","paths"],"properties":{"kind":{"type":"string","enum":["py_compile","pytest","node_check"]},"paths":{"type":"array","items":{"type":"string"}}}}}},
]
def ollama_chat(url: str, model: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {"model": model, "messages": messages, "tools": TOOL_DEFS, "stream": False, "options": {"temperature": 0.1}}
    req = urllib.request.Request(
        url.rstrip("/") + "/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise RuntimeError("LOCAL_MODEL_CALL_FAILED") from exc


def execute_tool(tools: AgentTools, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    fn = getattr(tools, name, None)
    if fn is None or name.startswith("_"):
        return {"state": "HOLD_TOOL_NOT_ALLOWED", "tool": name}
    try:
        return fn(**arguments)
    except Exception as exc:
        return {"state": "HOLD_TOOL_ERROR", "tool": name, "error_type": type(exc).__name__}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-root", required=True)
    parser.add_argument("--shadow-root", required=True)
    parser.add_argument("--allowed-json", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default="")
    parser.add_argument("--max-steps", type=int, default=MAX_STEPS)
    args = parser.parse_args()
    if not args.ollama_url:
        route = resolve_msi_ollama_url(
            args.model,
            override_url=DEFAULT_OLLAMA_URL_OVERRIDE or None,
            timeout=1.5,
        )
        if not route.get("selected_url"):
            raise RuntimeError("LOCAL_MODEL_ENDPOINT_UNREACHABLE")
        args.ollama_url = str(route["selected_url"])
    if args.max_steps < 1 or args.max_steps > 128:
        raise RuntimeError("LOCAL_MODEL_STEP_BUDGET_INVALID")
    prompt = sys.stdin.read()
    if not prompt.strip():
        return 2
    live = Path(args.live_root)
    shadow = Path(args.shadow_root)
    initial = json.loads(args.allowed_json)
    tools = AgentTools(live, shadow, initial)
    system = (
        "You are the local coding model inside a controlled 8D ADI development cell. "
        "Facts require tool evidence. Hypotheses must stay labeled. "
        "Use search/read tools before edits, stage only the smallest needed paths, "
        "edit only the shadow, run deterministic checks, and never claim live deployment. "
        "Do not ask the human to run commands. Continue until the requested source delta is implemented "
        "or a specific tool-evidenced blocker remains."
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    final = ""
    for _ in range(args.max_steps):
        response = ollama_chat(args.ollama_url, args.model, messages)
        message = response.get("message") or {}
        tool_calls = message.get("tool_calls") or []
        content = str(message.get("content") or "").strip()
        if not tool_calls and content:
            candidate = content.strip()
            fenced = re.fullmatch(r"```(?:json)?\s*(\{.*\})\s*```", candidate, re.DOTALL | re.IGNORECASE)
            if fenced:
                candidate = fenced.group(1).strip()
            tagged = re.fullmatch(r"<tool_call>\s*(\{.*\})\s*</tool_call>", candidate, re.DOTALL | re.IGNORECASE)
            if tagged:
                candidate = tagged.group(1).strip()
            try:
                pseudo = json.loads(candidate)
            except json.JSONDecodeError:
                pseudo = None
            if (
                isinstance(pseudo, dict)
                and isinstance(pseudo.get("name"), str)
                and pseudo.get("name") in {item["function"]["name"] for item in TOOL_DEFS}
            ):
                tool_calls = [{
                    "function": {
                        "name": pseudo["name"],
                        "arguments": pseudo.get("arguments") or {},
                    }
                }]
        messages.append(message)
        if not tool_calls:
            final = content
            break
        for call in tool_calls:
            fn = (call.get("function") or {})
            name = str(fn.get("name") or "")
            arguments = fn.get("arguments") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            result = execute_tool(tools, name, arguments)
            messages.append({"role": "tool", "tool_name": name, "content": json.dumps(result, ensure_ascii=False)})
    else:
        raise RuntimeError("LOCAL_MODEL_STEP_LIMIT")
    print(final or "LOCAL_MODEL_COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
