#!/usr/bin/env python3
"""Taiji01 metric identity gateway.

This is an Ollama-compatible local proxy for node taiji01.  It is intentionally
small and dependency-free so it can run in a container or directly on Linux.
It does not store prompts; audit records contain only hashes and routing facts.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

try:
    from runtime_adapters.w7tp_secondary_cloud_runtime import (
        RUNTIME_PATH as SECONDARY_CLOUD_RUNTIME_PATH,
        run_secondary_cloud_runtime,
    )
except ModuleNotFoundError:
    from w7tp_secondary_cloud_runtime import (
        RUNTIME_PATH as SECONDARY_CLOUD_RUNTIME_PATH,
        run_secondary_cloud_runtime,
    )


VERSION = "taiji01_metric_identity_gateway_v0_1"
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def env(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


ROOT = Path(env("TAIJI_ROOT", "/home/taiji_01/Taiji_Hub"))
TARGET = env("TAIJI_OLLAMA_TARGET", "http://127.0.0.1:11434").rstrip("/")
ALLOWED_MODELS = {
    item.strip()
    for item in env("TAIJI_ALLOWED_MODELS", "metric-language-gateway-ai:latest").split(",")
    if item.strip()
}
ALLOWLIST_PATH = Path(
    env(
        "TAIJI_IDENTITY_ALLOWLIST",
        str(ROOT / "deploy/packages/taiji01_metric_identity_gateway_v0_1/identity_allowlist.json"),
    )
)
AUDIT_PATH = Path(
    env(
        "TAIJI_GATEWAY_AUDIT_LOG",
        str(ROOT / "Taiji_Governance/logs/taiji01_metric_identity_gateway.jsonl"),
    )
)
REQUIRE_FIVE_CODE_HASH = env("TAIJI_REQUIRE_FIVE_CODE_HASH", "false").lower() in {
    "1",
    "true",
    "yes",
}
MEMORY_REFS = [
    ROOT / "data/f5_core_memory.db",
    ROOT / "data/wuchang_5d_knowledge_vault.db",
    ROOT / "data/ledger/metric_memory.sqlite3",
]


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_allowlist() -> dict[str, Any]:
    if not ALLOWLIST_PATH.exists():
        return {"nodes": []}
    try:
        return json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"nodes": []}


def ip_matches(client_ip: str, patterns: list[str]) -> bool:
    try:
        ip = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    for pattern in patterns:
        pattern = pattern.strip()
        if not pattern:
            continue
        try:
            if "/" in pattern:
                if ip in ipaddress.ip_network(pattern, strict=False):
                    return True
            elif ip == ipaddress.ip_address(pattern):
                return True
        except ValueError:
            continue
    return False


def authorize(client_ip: str, supplied_hash: str | None) -> tuple[bool, str, str | None]:
    allowlist = load_allowlist()
    nodes = allowlist.get("nodes") or []
    for node in nodes:
        allowed_ips = node.get("allowed_ips") or []
        if not ip_matches(client_ip, allowed_ips):
            continue
        node_id = str(node.get("node_id") or "unnamed_node")
        expected_hash = str(node.get("five_code_sha256") or "").replace("sha256:", "")
        if REQUIRE_FIVE_CODE_HASH and expected_hash:
            if supplied_hash and supplied_hash.replace("sha256:", "") == expected_hash:
                return True, "allow_ip_and_five_code_hash", node_id
            return False, "five_code_hash_required", node_id
        return True, "allow_device_mapped_identity", node_id
    return False, "client_not_allowlisted", None


def memory_ref_state() -> dict[str, Any]:
    refs = []
    for path in MEMORY_REFS:
        refs.append({"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path), "exists": path.exists()})
    return {"count": sum(1 for item in refs if item["exists"]), "refs": refs}


def audit(record: dict[str, Any]) -> None:
    record = {"ts": now_iso(), "gateway": VERSION, **record}
    try:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception:
        return


def parse_model(body: bytes) -> str | None:
    if not body:
        return None
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return None
    model = payload.get("model")
    return str(model) if model else None


def block_payload(body: bytes) -> str | None:
    if not body:
        return None
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return None
    text = json.dumps(payload, ensure_ascii=False).lower()
    if '"payment_allowed": true' in text:
        return "payment_allowed_true_blocked"
    if '"plaintext_context_stored": true' in text:
        return "plaintext_context_stored_true_blocked"
    return None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _client_ip(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        return forwarded or self.client_address[0]

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _authorize_or_reply(self) -> tuple[bool, str | None, str]:
        client_ip = self._client_ip()
        supplied = self.headers.get("X-Taiji-Five-Code-Sha256")
        ok, reason, node_id = authorize(client_ip, supplied)
        if not ok:
            audit({"client_ip": client_ip, "path": self.path, "allowed": False, "reason": reason, "node_id": node_id})
            self._json(403, {"ok": False, "risk_level": "L3", "action": "block", "reason": reason})
            return False, node_id, reason
        return True, node_id, reason

    def do_GET(self) -> None:
        if self.path == "/health":
            target_ok = False
            try:
                urllib.request.urlopen(f"{TARGET}/api/tags", timeout=1.5).read(1)
                target_ok = True
            except Exception:
                target_ok = False
            self._json(
                200,
                {
                    "ok": target_ok,
                    "runtime": VERSION,
                    "target": TARGET,
                    "allowed_models": sorted(ALLOWED_MODELS),
                    "memory": memory_ref_state(),
                    "identity_allowlist_exists": ALLOWLIST_PATH.exists(),
                    "audit_path": str(AUDIT_PATH),
                },
            )
            return
        if self.path.startswith("/api/"):
            allowed, node_id, reason = self._authorize_or_reply()
            if not allowed:
                return
            self._proxy("GET", b"", node_id, reason)
            return
        self._json(404, {"ok": False, "reason": "not_found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or "0")
        body = self.rfile.read(length) if length else b""
        allowed, node_id, reason = self._authorize_or_reply()
        if not allowed:
            return
        if self.path == SECONDARY_CLOUD_RUNTIME_PATH:
            try:
                request = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._json(400, {"state": "HOLD_REQUEST_REJECTED", "errors": ["INVALID_JSON"]})
                return
            result = run_secondary_cloud_runtime(request)
            audit(
                {
                    "client_ip": self._client_ip(),
                    "path": self.path,
                    "body_sha256": sha256_bytes(body),
                    "allowed": True,
                    "reason": reason,
                    "node_id": node_id,
                    "runtime_state": result["state"],
                    "external_network_called": False,
                }
            )
            self._json(200, result)
            return
        hazard = block_payload(body)
        model = parse_model(body)
        if hazard:
            audit(
                {
                    "client_ip": self._client_ip(),
                    "path": self.path,
                    "model": model,
                    "body_sha256": sha256_bytes(body),
                    "allowed": False,
                    "reason": hazard,
                    "node_id": node_id,
                }
            )
            self._json(403, {"ok": False, "risk_level": "L3", "action": "block", "reason": hazard})
            return
        if model and model not in ALLOWED_MODELS:
            audit(
                {
                    "client_ip": self._client_ip(),
                    "path": self.path,
                    "model": model,
                    "body_sha256": sha256_bytes(body),
                    "allowed": False,
                    "reason": "model_not_allowlisted",
                    "node_id": node_id,
                }
            )
            self._json(403, {"ok": False, "risk_level": "L2", "action": "warn_block", "reason": "model_not_allowlisted"})
            return
        self._proxy("POST", body, node_id, reason)

    def _proxy(self, method: str, body: bytes, node_id: str | None, auth_reason: str) -> None:
        target_url = f"{TARGET}{self.path}"
        headers = {"Content-Type": self.headers.get("Content-Type", "application/json")}
        request = urllib.request.Request(target_url, data=body if method == "POST" else None, headers=headers, method=method)
        body_hash = sha256_bytes(body) if body else None
        model = parse_model(body)
        audit(
            {
                "client_ip": self._client_ip(),
                "path": self.path,
                "model": model,
                "body_sha256": body_hash,
                "allowed": True,
                "reason": auth_reason,
                "node_id": node_id,
                "memory_ref_count": memory_ref_state()["count"],
            }
        )
        try:
            with urllib.request.urlopen(request, timeout=float(env("TAIJI_PROXY_TIMEOUT_SEC", "300"))) as response:
                self.send_response(response.status)
                for key, value in response.headers.items():
                    if key.lower() not in HOP_BY_HOP and key.lower() != "content-length":
                        self.send_header(key, value)
                self.end_headers()
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except urllib.error.HTTPError as exc:
            self._json(exc.code, {"ok": False, "reason": "target_http_error", "status": exc.code})
        except Exception as exc:
            self._json(502, {"ok": False, "reason": "target_not_reachable", "error_type": type(exc).__name__})


def main() -> int:
    bind = env("TAIJI_GATEWAY_BIND", "127.0.0.1")
    port = int(env("TAIJI_GATEWAY_PORT", "11435"))
    server = ThreadingHTTPServer((bind, port), Handler)
    print(json.dumps({"ok": True, "runtime": VERSION, "bind": bind, "port": port, "target": TARGET}, ensure_ascii=False), flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
