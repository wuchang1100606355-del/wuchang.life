"""Loopback-only, read-only demo UI/API for completed candidate runs."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .pipeline import require_isolated_output


def handler_for(run_dir: Path) -> type[BaseHTTPRequestHandler]:
    root = require_isolated_output(run_dir)

    class DemoHandler(BaseHTTPRequestHandler):
        server_version = "W7TPCandidateDemo/1"

        def log_message(self, format: str, *args: object) -> None:
            del format, args

        def _send(self, status: int, content_type: str, data: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-W7TP-Authority", "CANDIDATE_ONLY")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
            route = urlparse(self.path).path
            if route == "/":
                self._send(200, "text/html; charset=utf-8", (root / "index.html").read_bytes())
                return
            if route == "/api/demo/v1/status":
                self._send(200, "application/json", (root / "demo_state.json").read_bytes())
                return
            prefix = "/api/demo/v1/receipts/"
            if route.startswith(prefix):
                name = unquote(route[len(prefix) :])
                if not name or Path(name).name != name or not name.endswith(".json"):
                    self._send(400, "application/json", b'{"error":"INVALID_RECEIPT_REF"}')
                    return
                path = root / "receipts" / name
                if not path.is_file() or path.is_symlink():
                    self._send(404, "application/json", b'{"error":"NOT_FOUND"}')
                    return
                self._send(200, "application/json", path.read_bytes())
                return
            self._send(404, "application/json", b'{"error":"NOT_FOUND"}')

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
            self._send(405, "application/json", b'{"error":"READ_ONLY_API"}')

    return DemoHandler


def serve_demo(run_dir: Path, *, host: str = "127.0.0.1", port: int = 9108) -> None:
    if host != "127.0.0.1":
        raise ValueError("LOOPBACK_ONLY")
    root = require_isolated_output(run_dir)
    state = json.loads((root / "demo_state.json").read_bytes())
    if state.get("candidate_only") is not True:
        raise ValueError("CANDIDATE_STATE_REQUIRED")
    with ThreadingHTTPServer((host, port), handler_for(root)) as server:
        server.serve_forever()
