#!/usr/bin/env python3
"""Readonly RTSP metadata probe for property-management video integration.

The probe never records media and never prints credentials or raw SDP. Optional
credentials are read from environment variables and passed to curl over stdin so
they do not appear in the process argument list.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from urllib.parse import urlsplit


USERNAME_ENV = "PROPERTY_RTSP_USERNAME"
PASSWORD_ENV = "PROPERTY_RTSP_PASSWORD"


@dataclass(frozen=True)
class Target:
    url: str
    hostname: str
    port: int

    @property
    def coordinate(self) -> str:
        return f"{self.hostname}:{self.port}"


def parse_target(url: str) -> Target:
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "rtsp":
        raise ValueError("RTSP URL must use the rtsp scheme")
    if not parsed.hostname:
        raise ValueError("RTSP URL must include a host")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(
            f"Do not place credentials in the URL; use {USERNAME_ENV} and {PASSWORD_ENV}"
        )
    port = parsed.port or 554
    return Target(url=url, hostname=parsed.hostname, port=port)


def curl_resolve_address(value: str) -> str:
    address = ipaddress.ip_address(value)
    return f"[{address.compressed}]" if address.version == 6 else address.compressed


def curl_quote(value: str) -> str:
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ValueError("RTSP configuration values cannot contain control lines")
    return value.replace("\\", "\\\\").replace('"', '\\"')


def curl_config(
    target: Target,
    method: str,
    timeout: float,
    username: str | None,
    password: str | None,
    resolve_ip: str | None = None,
) -> str:
    lines = [
        f'url = "{curl_quote(target.url)}"',
        f'request = "{method}"',
        'header = "Accept: application/sdp"',
        "include",
        "silent",
        "show-error",
        f"connect-timeout = {timeout}",
        f"max-time = {timeout}",
        'noproxy = "*"',
        'user-agent = "Taiji-Property-RTSP-Probe/1.0"',
    ]
    if resolve_ip is not None:
        address = curl_resolve_address(resolve_ip)
        lines.append(f'resolve = "{curl_quote(target.hostname)}:{target.port}:{address}"')
    if username is not None or password is not None:
        if not username or password is None:
            raise ValueError(f"Both {USERNAME_ENV} and {PASSWORD_ENV} are required")
        lines.extend(
            [
                "anyauth",
                f'user = "{curl_quote(username)}:{curl_quote(password)}"',
            ]
        )
    return "\n".join(lines) + "\n"


def final_rtsp_response(raw: str) -> tuple[int | None, dict[str, str], str]:
    starts = [match.start() for match in re.finditer(r"(?m)^RTSP/\d(?:\.\d)? \d{3}", raw)]
    if not starts:
        return None, {}, ""
    block = raw[starts[-1] :]
    head, separator, body = block.partition("\r\n\r\n")
    if not separator:
        head, separator, body = block.partition("\n\n")
    lines = head.replace("\r", "").splitlines()
    status_match = re.match(r"RTSP/\d(?:\.\d)? (\d{3})", lines[0])
    status = int(status_match.group(1)) if status_match else None
    headers: dict[str, str] = {}
    for line in lines[1:]:
        name, found, value = line.partition(":")
        if found:
            headers[name.strip().lower()] = value.strip()
    return status, headers, body


def authentication_scheme(header: str) -> str | None:
    match = re.match(r"\s*([A-Za-z]+)", header)
    return match.group(1).lower() if match else None


def sdp_summary(body: str) -> dict[str, object]:
    video_tracks = 0
    audio_tracks = 0
    codecs: set[str] = set()
    for raw_line in body.replace("\r", "").splitlines():
        line = raw_line.strip()
        if line.startswith("m=video "):
            video_tracks += 1
        elif line.startswith("m=audio "):
            audio_tracks += 1
        elif line.startswith("a=rtpmap:"):
            _, _, encoding = line.partition(" ")
            codec = encoding.partition("/")[0].strip()
            if re.fullmatch(r"[A-Za-z0-9_.+-]{1,32}", codec):
                codecs.add(codec.upper())
    return {
        "video_tracks": video_tracks,
        "audio_tracks": audio_tracks,
        "codecs": sorted(codecs),
    }


def probe(
    target: Target,
    method: str,
    timeout: float,
    username: str | None,
    password: str | None,
    resolve_ip: str | None = None,
) -> tuple[dict[str, object], int]:
    if shutil.which("curl") is None:
        return {
            "state": "HOLD",
            "decision": "curl_rtsp_support_unavailable",
            "target": target.coordinate,
        }, 2

    config = curl_config(target, method, timeout, username, password, resolve_ip)
    completed = subprocess.run(
        ["curl", "--config", "-"],
        input=config,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=timeout + 2,
        check=False,
    )
    status, headers, body = final_rtsp_response(completed.stdout)
    auth_header = headers.get("www-authenticate", "")
    auth_required = status == 401
    media = sdp_summary(body) if status == 200 else sdp_summary("")

    if status == 200 and (method == "OPTIONS" or media["video_tracks"]):
        state = "PASS"
        decision = "rtsp_video_metadata_available" if media["video_tracks"] else "rtsp_available"
        exit_code = 0
    elif auth_required:
        state = "HOLD"
        decision = "rtsp_authentication_required"
        exit_code = 3
    elif status is None and completed.returncode != 0:
        state = "HOLD"
        decision = "rtsp_transport_unavailable"
        exit_code = 4
    elif status is None:
        state = "HOLD"
        decision = "rtsp_no_protocol_response"
        exit_code = 4
    else:
        state = "HOLD"
        decision = "rtsp_video_metadata_unavailable"
        exit_code = 5

    result: dict[str, object] = {
        "state": state,
        "decision": decision,
        "target": target.coordinate,
        "method": method,
        "dns_override": resolve_ip is not None,
        "rtsp_status": status,
        "transport_available": status is not None,
        "client_exit_code": completed.returncode,
        "auth_required": auth_required,
        "auth_scheme": authentication_scheme(auth_header),
        **media,
        "raw_media_saved": False,
        "raw_sdp_output": False,
        "credentials_output": False,
    }
    return result, exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="RTSP URL without credentials")
    parser.add_argument(
        "--method",
        choices=("OPTIONS", "DESCRIBE"),
        default="DESCRIBE",
        help="Readonly RTSP request to send",
    )
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument(
        "--resolve-ip",
        help="Resolve the RTSP hostname to this IP for this request only",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not 0.2 <= args.timeout <= 30:
        raise SystemExit("--timeout must be between 0.2 and 30 seconds")
    try:
        target = parse_target(args.url)
        result, exit_code = probe(
            target=target,
            method=args.method,
            timeout=args.timeout,
            username=os.environ.get(USERNAME_ENV),
            password=os.environ.get(PASSWORD_ENV),
            resolve_ip=args.resolve_ip,
        )
    except (ValueError, subprocess.TimeoutExpired) as exc:
        result = {
            "state": "HOLD",
            "decision": type(exc).__name__,
            "raw_media_saved": False,
            "credentials_output": False,
        }
        exit_code = 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
