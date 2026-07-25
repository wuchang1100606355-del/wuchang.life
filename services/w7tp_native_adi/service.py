"""HTTP product surface for the existing Total Field master."""

from __future__ import annotations

import argparse
import json
import os
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

from .core import ADIError, PROTOCOL_VERSION, SERVICE_NAME, SpacetimeADI


AUTHORITY = "TOTAL_FIELD_SERVER_MASTER"
MAX_HTTP_REQUEST_BYTES = 32 * 1024 * 1024
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9110
DEFAULT_STATE_DIR = Path("/home/taiji_admin/.local/state/w7tp-native-adi")


def health_payload(*, authority_receipt_wired: bool = False) -> dict[str, Any]:
    return {
        "state": "PASS",
        "service": SERVICE_NAME,
        "authority": AUTHORITY,
        "protocol": "W7TP_8D_GENERATIVE_TRANSMISSION",
        "production": True,
        "reconstruction_authority_receipt": (
            "CONFIRMED_PROTECTION" if authority_receipt_wired else "UNVERIFIED_LIVE_WIRING"
        ),
    }


class NativeADIHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], engine: SpacetimeADI) -> None:
        super().__init__(address, NativeADIHandler)
        self.engine = engine


class NativeADIHandler(BaseHTTPRequestHandler):
    server: NativeADIHTTPServer

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, status: int, payload: Any) -> None:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _request_json(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length", "")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ADIError("HTTP_CONTENT_LENGTH_INVALID") from exc
        if length < 2 or length > MAX_HTTP_REQUEST_BYTES:
            raise ADIError("HTTP_REQUEST_SIZE_INVALID")
        try:
            payload = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ADIError("HTTP_REQUEST_JSON_INVALID") from exc
        if not isinstance(payload, dict):
            raise ADIError("HTTP_REQUEST_OBJECT_REQUIRED")
        return payload

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/health":
            self._json(200, health_payload())
            return
        if path == "/metrics":
            self._json(200, self.server.engine.metrics())
            return
        self._json(404, {"state": "HOLD", "reason_code": "ROUTE_NOT_FOUND"})

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        try:
            payload = self._request_json()
            if path == "/v1/adi/insert":
                time_keys = {"time_slot", "logical_time_uint64"} & set(payload)
                if (
                    len(time_keys) != 1
                    or set(payload) - {"id", "time_slot", "logical_time_uint64", "payload"}
                    or not {"id", "payload"} <= set(payload)
                ):
                    raise ADIError("INSERT_REQUEST_SHAPE_INVALID")
                logical_time = payload[next(iter(time_keys))]
                result = self.server.engine.insert(
                    payload["id"], logical_time, payload["payload"]
                )
                self._json(200, {"state": "PASS", "record": result})
                return
            if path == "/v1/adi/search":
                if not {"start_slot", "end_slot"} <= set(payload) or set(payload) - {
                    "start_slot",
                    "end_slot",
                    "limit",
                    "query_budget",
                }:
                    raise ADIError("SEARCH_REQUEST_SHAPE_INVALID")
                result = self.server.engine.search(
                    payload["start_slot"],
                    payload["end_slot"],
                    payload.get("limit", 100),
                    payload.get("query_budget"),
                )
                self._json(200, {"state": "PASS", "results": result})
                return
            if path == "/v1/adi/packet":
                if set(payload) - {
                    "ids",
                    "receiver_lookup",
                    "parent_snapshot_ref",
                }:
                    raise ADIError("PACKET_REQUEST_SHAPE_INVALID")
                result = self.server.engine.packet(
                    payload.get("ids"),
                    payload.get("receiver_lookup"),
                    payload.get("parent_snapshot_ref"),
                )
                self._json(200, result)
                return
            if path == "/v1/adi/reconstruct":
                if set(payload) != {"packet", "authority_receipt_ref"}:
                    raise ADIError("RECONSTRUCT_REQUEST_SHAPE_INVALID")
                result = self.server.engine.reconstruct(
                    payload["packet"], payload["authority_receipt_ref"]
                )
                self._json(200, result)
                return
            self._json(404, {"state": "HOLD", "reason_code": "ROUTE_NOT_FOUND"})
        except ADIError as exc:
            if not exc.dead_lettered:
                self.server.engine.record_rejection(exc, f"HTTP:{path}")
            dead_letter = dict(exc.dead_letter_receipt or {})
            self._json(
                422,
                {
                    "state": "HOLD",
                    "reason_code": exc.reason_code,
                    "path": exc.path,
                    "dead_letter_state": dead_letter.get(
                        "state", "UNVERIFIED_LIVE_WIRING"
                    ),
                    "dead_letter_id": dead_letter.get("dead_letter_id"),
                },
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=SERVICE_NAME)
    parser.add_argument("--host", default=os.environ.get("W7TP_NATIVE_ADI_HOST", DEFAULT_HOST))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("W7TP_NATIVE_ADI_PORT", str(DEFAULT_PORT))),
    )
    parser.add_argument(
        "--state-dir",
        default=os.environ.get("W7TP_NATIVE_ADI_STATE_DIR", str(DEFAULT_STATE_DIR)),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    from runtime.dead_letter.dead_letter_24h_hash_writer import (
        append_24h_hash_dead_letter,
    )

    engine = SpacetimeADI(
        arguments.state_dir,
        dead_letter_writer=append_24h_hash_dead_letter,
    )
    server = NativeADIHTTPServer((arguments.host, arguments.port), engine)

    def stop(_signum: int, _frame: Any) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
    return 0


__all__ = [
    "AUTHORITY",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "NativeADIHTTPServer",
    "health_payload",
    "main",
]
