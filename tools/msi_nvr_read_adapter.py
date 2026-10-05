#!/usr/bin/env python3
"""MSI-side governed read adapter for the Wuchang AH55B08 NVR.

Credentials remain local to MSI environment variables. The adapter never prints
credentials, never changes NVR state, and only supports bounded read operations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from tools.property_rtsp_probe import parse_target, probe

DEFAULT_HOST = os.getenv("W7TP_NVR_HOST", "192.168.50.34")
DEFAULT_HTTP_PORT = int(os.getenv("W7TP_NVR_HTTP_PORT", "30080"))
DEFAULT_RTSP_PORT = int(os.getenv("W7TP_NVR_RTSP_PORT", "554"))
DEFAULT_RTSP_PATH = os.getenv(
    "W7TP_NVR_RTSP_PATH", "/rtspstream?channel=0&stream=0"
)
USERNAME_ENV = "PROPERTY_RTSP_USERNAME"
PASSWORD_ENV = "PROPERTY_RTSP_PASSWORD"
HTTP_AUTH_ENV = "W7TP_NVR_HTTP_AUTH_SCHEME"
MAX_JPEG_BYTES = 20 * 1024 * 1024


class NvrReadHold(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _channel(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 31:
        raise NvrReadHold("HOLD_NVR_CHANNEL_INVALID")
    return value


def _credentials() -> tuple[str, str]:
    username = os.getenv(USERNAME_ENV)
    password = os.getenv(PASSWORD_ENV)
    if not username or password is None:
        raise NvrReadHold("HOLD_NVR_CREDENTIAL_BINDING_REQUIRED")
    return username, password


def _http_auth(username: str, password: str):
    scheme = os.getenv(HTTP_AUTH_ENV, "digest").strip().lower()
    if scheme == "digest":
        return HTTPDigestAuth(username, password), scheme
    if scheme == "basic":
        return HTTPBasicAuth(username, password), scheme
    raise NvrReadHold("HOLD_NVR_HTTP_AUTH_SCHEME_INVALID")


def status(
    *,
    host: str = DEFAULT_HOST,
    rtsp_port: int = DEFAULT_RTSP_PORT,
    rtsp_path: str = DEFAULT_RTSP_PATH,
    timeout: float = 4.0,
) -> dict[str, Any]:
    target = parse_target(f"rtsp://{host}:{rtsp_port}{rtsp_path}")
    result, _ = probe(
        target=target,
        method="OPTIONS",
        timeout=timeout,
        username=None,
        password=None,
    )
    reachable = bool(result.get("transport_available"))
    auth_required = bool(result.get("auth_required"))
    return {
        "state": (
            "PASS_NVR_READ_ADAPTER_REACHABLE"
            if reachable
            else "HOLD_NVR_RTSP_TRANSPORT_UNAVAILABLE"
        ),
        "device_ref": "device:nvr:ah55b08:wuchang",
        "service_ref": "service:msi:nvr-read-adapter",
        "node_ref": "node:MSI",
        "observed_at": _now(),
        "rtsp": {
            "target": result.get("target"),
            "reachable": reachable,
            "status": result.get("rtsp_status"),
            "auth_required": auth_required,
            "auth_scheme": result.get("auth_scheme"),
            "raw_media_saved": False,
            "credentials_output": False,
        },
        "credential_binding": (
            "BOUND_LOCAL_ENV"
            if os.getenv(USERNAME_ENV) and os.getenv(PASSWORD_ENV) is not None
            else "UNBOUND"
        ),
        "mutation_performed": False,
    }


def snapshot(
    *,
    output: Path,
    channel: int,
    host: str = DEFAULT_HOST,
    http_port: int = DEFAULT_HTTP_PORT,
    timeout: float = 8.0,
) -> dict[str, Any]:
    channel = _channel(channel)
    username, password = _credentials()
    auth, auth_scheme = _http_auth(username, password)
    url = f"http://{host}:{http_port}/cgi-bin/net_jpeg.cgi?ch={channel}"
    try:
        response = requests.get(
            url,
            auth=auth,
            timeout=timeout,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        raise NvrReadHold("HOLD_NVR_SNAPSHOT_TRANSPORT_ERROR") from exc

    if response.status_code in (401, 403):
        raise NvrReadHold("HOLD_NVR_SNAPSHOT_AUTH_REJECTED")
    if response.status_code != 200:
        raise NvrReadHold(f"HOLD_NVR_SNAPSHOT_HTTP_{response.status_code}")

    body = response.content
    if not body or len(body) > MAX_JPEG_BYTES:
        raise NvrReadHold("HOLD_NVR_SNAPSHOT_SIZE_INVALID")
    if not (body.startswith(b"\xff\xd8") and body.endswith(b"\xff\xd9")):
        raise NvrReadHold("HOLD_NVR_SNAPSHOT_NOT_JPEG")

    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise NvrReadHold("HOLD_NVR_SNAPSHOT_OUTPUT_EXISTS")
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        output.unlink(missing_ok=True)
        raise

    return {
        "state": "PASS_NVR_SNAPSHOT_ACQUIRED",
        "device_ref": "device:nvr:ah55b08:wuchang",
        "service_ref": "service:msi:nvr-read-adapter",
        "node_ref": "node:MSI",
        "camera_ref": f"CAM{channel + 1:02d}",
        "channel_index": channel,
        "observed_at": _now(),
        "media_type": "image/jpeg",
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "output_path": str(output),
        "http_auth_scheme": auth_scheme,
        "credentials_output": False,
        "mutation_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status")
    p_status.add_argument("--host", default=DEFAULT_HOST)
    p_status.add_argument("--rtsp-port", type=int, default=DEFAULT_RTSP_PORT)
    p_status.add_argument("--rtsp-path", default=DEFAULT_RTSP_PATH)

    p_snapshot = sub.add_parser("snapshot")
    p_snapshot.add_argument("--host", default=DEFAULT_HOST)
    p_snapshot.add_argument("--http-port", type=int, default=DEFAULT_HTTP_PORT)
    p_snapshot.add_argument("--channel", type=int, required=True)
    p_snapshot.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    try:
        if args.command == "status":
            result = status(
                host=args.host,
                rtsp_port=args.rtsp_port,
                rtsp_path=args.rtsp_path,
            )
        else:
            result = snapshot(
                output=args.output,
                channel=args.channel,
                host=args.host,
                http_port=args.http_port,
            )
    except NvrReadHold as exc:
        result = {
            "state": "HOLD",
            "reason": exc.code,
            "credentials_output": False,
            "mutation_performed": False,
        }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
