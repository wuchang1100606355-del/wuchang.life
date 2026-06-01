#!/usr/bin/env python3
"""Taiji formal tensor runtime package v0.1.

Standard-library-only HTTP runtime:
- GET /health
- POST /tensor/validate
- POST /tensor/route

Default bind is 127.0.0.1. No production service is started by this file unless
an operator explicitly runs it.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_adapters.formal_tensor_runtime_adapter_v0_1 import validate  # noqa: E402


RUNTIME_NAME = "taiji_formal_tensor_runtime_pkg_v0_1"
BIND_HOST = os.environ.get("TAIJI_BIND_HOST", "127.0.0.1")
PORT = int(os.environ.get("TAIJI_PORT", "8125"))
STATE_DIR = pathlib.Path(os.environ.get("TAIJI_STATE_DIR", str(ROOT / ".taiji_runtime_pkg_v0_1")))
AUDIT_PATH = pathlib.Path(os.environ.get("TAIJI_AUDIT_PATH", str(STATE_DIR / "audit/runtime_audit.jsonl")))
DEADBOX_DIR = pathlib.Path(os.environ.get("TAIJI_DEADBOX_DIR", str(STATE_DIR / "deadbox")))
REPLAY_DIR = pathlib.Path(os.environ.get("TAIJI_REPLAY_DIR", str(STATE_DIR / "replay")))
CACHE_DIR = pathlib.Path(os.environ.get("TAIJI_CACHE_DIR", str(STATE_DIR / "cache")))


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def ensure_dirs() -> None:
    for path in (AUDIT_PATH.parent, DEADBOX_DIR, REPLAY_DIR, CACHE_DIR):
        path.mkdir(parents=True, exist_ok=True)


def packet_hash(packet: Any) -> str:
    raw = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def audit(event: dict[str, Any]) -> None:
    ensure_dirs()
    record = {
        "ts": now(),
        "runtime": RUNTIME_NAME,
        "external_api_called": False,
        "production_started_automatically": False,
        "secret_material_printed": False,
        **event,
    }
    with AUDIT_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def route(packet: dict[str, Any]) -> dict[str, Any]:
    result = validate(packet)
    target = "deadbox" if not result.get("allowed") or result.get("route") == "deadbox" else "gateway"
    response = {
        "ok": target != "deadbox",
        "runtime": RUNTIME_NAME,
        "target": target,
        "packet_hash": packet_hash(packet),
        "validation": result,
    }
    audit({"event": "tensor_route", "target": target, "packet_hash": response["packet_hash"]})
    return response


def health() -> dict[str, Any]:
    ensure_dirs()
    return {
        "ok": True,
        "runtime": "taiji_formal_tensor_runtime",
        "package": RUNTIME_NAME,
        "bind_host": BIND_HOST,
        "validator": "ok_or_fail_closed_adapter",
        "replay_runtime": "ok",
        "deadbox_runtime": "ok",
        "audit_runtime": "ok",
        "continuity_cache": "ok",
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "TaijiFormalRuntimePkg/0.1"

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict[str, Any] | None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            value = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, dict) else None

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self.send_json(200, health())
            return
        self.send_json(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        body = self.read_json()
        if body is None:
            self.send_json(400, {"ok": False, "error": "invalid_json"})
            return
        if self.path == "/tensor/validate":
            result = validate(body)
            audit({"event": "tensor_validate", "allowed": result.get("allowed"), "packet_hash": packet_hash(body)})
            self.send_json(200 if result.get("allowed") else 423, result)
            return
        if self.path == "/tensor/route":
            result = route(body)
            self.send_json(200 if result.get("ok") else 423, result)
            return
        self.send_json(404, {"ok": False, "error": "not_found"})

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write(f"{now()} {fmt % args}\n")


def main() -> int:
    if BIND_HOST == "0.0.0.0" and os.environ.get("TAIJI_ALLOW_UNRESTRICTED_BIND", "false").lower() != "true":
        raise SystemExit("0.0.0.0 bind requires TAIJI_ALLOW_UNRESTRICTED_BIND=true")
    ensure_dirs()
    audit({"event": "runtime_manual_start", "bind_host": BIND_HOST, "port": PORT})
    server = ThreadingHTTPServer((BIND_HOST, PORT), Handler)
    print(json.dumps({"ok": True, "runtime": RUNTIME_NAME, "bind_host": BIND_HOST, "port": PORT}, ensure_ascii=False), flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
