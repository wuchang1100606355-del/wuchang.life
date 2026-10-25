#!/usr/bin/env python3
"""Bounded HTTP adapter for the native, fixed GST WebAuthn verifier.

This module never issues authority. Completion persists the native proof first,
then a factual receipt, flushes the response, and signals the one-shot operator.
"""
from __future__ import annotations
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gst_mobile_approval_first as capture

HOSTS = {"127.0.0.1:9122", "localhost:9122", "taiji01.tailea1eef.ts.net:9122"}
MAX_BODY = 96 * 1024


class ApprovalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, address, fido_instance, on_verified, stop_event):
        self.fido = fido_instance
        self.on_verified = on_verified
        self.stop_event = stop_event
        self.completion_lock = threading.Lock()
        self.closing = threading.Event()
        self.completion_error = None
        super().__init__(address, Handler)

    def finish_requests(self, timeout=5):
        self.closing.set()
        acquired = self.completion_lock.acquire(timeout=timeout)
        if acquired:
            self.completion_lock.release()
        return acquired

    def handle_error(self, request, client_address):
        # Request bodies and authenticator data must never reach traceback logs.
        pass


class Handler(BaseHTTPRequestHandler):
    server_version = "W7TPPhoneApproval/2"

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *_args):
        pass

    def _route(self):
        hosts = self.headers.get_all("Host", [])
        capture.require(len(hosts) == 1 and hosts[0] in HOSTS, "EXACT_HOST_REQUIRED")
        parts = urlsplit(self.path)
        capture.require(not parts.scheme and not parts.netloc and not parts.query and
                        not parts.fragment and len(self.path) <= 256, "EXACT_REQUEST_PATH_REQUIRED")
        return parts.path

    def _reply(self, code, data, content_type="application/json; charset=utf-8"):
        raw = data if isinstance(data, bytes) else capture.canon(data)
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(raw)
        self.wfile.flush()
        self.close_connection = True

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
                self._reply(200, capture.status(self.server.fido))
            elif route == "/gst-v21/phone-link.svg":
                try:
                    import qrcode
                    import qrcode.image.svg
                except ImportError:
                    self._reply(404, {"state": "USE_PHONE_LINK"})
                    return
                stream = io.BytesIO()
                qrcode.make(capture.ORIGIN + "/gst-v21/", image_factory=qrcode.image.svg.SvgPathImage).save(stream)
                self._reply(200, stream.getvalue(), "image/svg+xml")
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
            origins = self.headers.get_all("Origin", [])
            capture.require(len(origins) == 1 and origins[0] == capture.ORIGIN, "EXACT_SAME_ORIGIN_REQUIRED")
            capture.require(not self.server.closing.is_set(), "SIGNING_SERVICE_CLOSING")
            capture.require(self.headers.get("Content-Type", "").split(";", 1)[0].strip() == "application/json", "JSON_REQUIRED")
            capture.require(self.headers.get("Transfer-Encoding") is None, "CONTENT_LENGTH_REQUIRED")
            lengths = self.headers.get_all("Content-Length", [])
            capture.require(len(lengths) == 1 and lengths[0].isdigit(), "CONTENT_LENGTH_REQUIRED")
            length = int(lengths[0])
            capture.require(0 < length <= MAX_BODY, "BOUNDED_BODY_REQUIRED")
            raw = self.rfile.read(length)
            capture.require(len(raw) == length, "INCOMPLETE_BODY")
            body = json.loads(raw)
            capture.require(isinstance(body, dict), "OBJECT_REQUIRED")
            if route == "/gst-v21/options" and body == {}:
                self._reply(200, capture.begin(self.server.fido))
                return
            capture.require(route == "/gst-v21/complete", "EXACT_ROUTE_AND_BODY_REQUIRED")
            with self.server.completion_lock:
                capture.require(not self.server.closing.is_set(), "SIGNING_SERVICE_CLOSING")
                result = capture.complete(self.server.fido, body)
                capture.require(result.get("signature_verified") is True, "NATIVE_SIGNATURE_NOT_VERIFIED")
                # Stop after saved proof even if receipt publication or delivery fails.
                self.server.closing.set()
                try:
                    if self.server.on_verified is not None:
                        result = self.server.on_verified(result)
                    self._reply(200, result)
                except Exception as exc:
                    self.server.completion_error = type(exc).__name__
                    try:
                        self._reply(500, {"state": "SIGNATURE_SAVED_RECEIPT_OR_DELIVERY_PENDING",
                                          "signature_verified": True,
                                          "formal_effect_authorized": False,
                                          "reason_code": "RECEIPT_OR_DELIVERY_PENDING"})
                    except OSError:
                        pass
                finally:
                    self.server.stop_event.set()
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self._failure(exc)


def create_server(address, *, fido_instance, on_verified=None, stop_event=None):
    capture.require(address[0] == "127.0.0.1", "LOOPBACK_ONLY")
    return ApprovalServer(address, fido_instance, on_verified,
                          stop_event if stop_event is not None else threading.Event())


def main():
    # Both supported command entrypoints share one operator lifecycle.
    from w7tp_founder_sign import main as operator_main
    return operator_main()


if __name__ == "__main__":
    raise SystemExit(main())
