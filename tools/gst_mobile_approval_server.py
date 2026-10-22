#!/usr/bin/env python3
"""Serve the existing phone credential's exact GST intent capture on loopback.

The existing authenticated HTTPS proxy supplies the browser origin. This service
only captures and verifies a real signature. It cannot repair, promote, or issue
authority. Request bodies and authentication data are never logged.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gst_mobile_approval_first as capture

HOSTS = {"127.0.0.1:9122", "localhost:9122", "taiji01.tailea1eef.ts.net:8444"}
MAX_BODY = 96 * 1024
fido = capture.make_server()


class Handler(BaseHTTPRequestHandler):
    server_version = "W7TPPhoneApproval/1"

    def log_message(self, *_args):
        pass

    def _route(self):
        if self.headers.get("Host", "").lower() not in HOSTS:
            raise PermissionError("EXACT_HOST_REQUIRED")
        route = urlsplit(self.path).path
        prefix = "/proxy/9122"
        if route.startswith(prefix + "/"):
            route = route[len(prefix):]
        return route

    def _reply(self, code, data, content_type="application/json; charset=utf-8"):
        raw = data if isinstance(data, bytes) else json.dumps(
            data, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(raw)

    def _failure(self, exc):
        reason = str(exc) if isinstance(exc, PermissionError) else "REQUEST_OR_PROOF_INVALID"
        self._reply(400, {"state": "PHONE_APPROVAL_NOT_COMPLETED",
                          "reason_code": reason,
                          "signature_verified": False,
                          "formal_effect_authorized": False})

    def do_GET(self):
        try:
            route = self._route()
            if route in ("/gst-v21", "/gst-v21/"):
                self._reply(200, capture.PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif route == "/gst-v21/status":
                self._reply(200, capture.status(fido))
            elif route == "/gst-v21/phone-link.svg":
                self._reply(200, Path(__file__).with_name("gst_mobile_phone_link.svg").read_bytes(), "image/svg+xml")
            elif route == "/health":
                self._reply(200, {"state": "PHONE_APPROVAL_CAPTURE_AVAILABLE",
                                  "rp_id": capture.RP_ID, "origin": capture.ORIGIN,
                                  "formal_effect_authorized": False})
            else:
                self._reply(404, {"state": "NOT_FOUND"})
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self._failure(exc)

    def do_POST(self):
        try:
            route = self._route()
            if self.headers.get("Origin") != capture.ORIGIN:
                raise PermissionError("EXACT_SAME_ORIGIN_REQUIRED")
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip() != "application/json":
                raise PermissionError("JSON_REQUIRED")
            if self.headers.get("Transfer-Encoding") is not None:
                raise PermissionError("CONTENT_LENGTH_REQUIRED")
            length = int(self.headers.get("Content-Length", "-1"))
            if not 0 < length <= MAX_BODY:
                raise PermissionError("BOUNDED_BODY_REQUIRED")
            self.connection.settimeout(5)
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise PermissionError("INCOMPLETE_BODY")
            body = json.loads(raw)
            if not isinstance(body, dict):
                raise PermissionError("OBJECT_REQUIRED")
            if route == "/gst-v21/options" and body == {}:
                result = capture.begin(fido)
            elif route == "/gst-v21/complete":
                result = capture.complete(fido, body)
            else:
                raise PermissionError("EXACT_ROUTE_AND_BODY_REQUIRED")
            self._reply(200, result)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self._failure(exc)


def main():
    capture.initialize_state()
    server = ThreadingHTTPServer(("127.0.0.1", 9122), Handler)
    server.daemon_threads = True
    server.serve_forever()


if __name__ == "__main__":
    main()
