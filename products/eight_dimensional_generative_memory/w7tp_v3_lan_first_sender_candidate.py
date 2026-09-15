#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W7TP V3 LAN-first sender projection.

This is an append-only, implementation-compatible successor carrier for the
observed W7G3 /generative receiver contract.  It never promotes itself to
canonical authority.  LAN is attempted first; VPN is eligible only when the
LAN connection itself is unavailable.  Protocol, reconstruction, or hash
failures HOLD and never trigger a route downgrade.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import struct
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, Tuple


MAGIC = b"W7G3"
HEADER = struct.Struct("!4sIIII")
KNOWN = struct.Struct("!HB")
NOVEL_INDEX = struct.Struct("!H")
BASE_PATTERN = b"W7TP-8D-ADI-BASE-V3|"
TOKEN_TABLE = {
    0: b"W7TP-KNOWN-A|",
    1: b"W7TP-KNOWN-B|",
    2: b"W7TP-KNOWN-C|",
    3: b"W7TP-KNOWN-D|",
}
MAX_SIZE = 8 * 1024 * 1024
SOURCE_CONTRACT_SHA256 = "d9ce00a7656926a57ecbfc1c639c0c53ac12790dba2eec2802e23dd8477d8913"


class ProtocolHold(RuntimeError):
    pass


def repeat_to_size(pattern: bytes, size: int) -> bytes:
    return (pattern * ((size + len(pattern) - 1) // len(pattern)))[:size]


def novel_payload(seed: str, block: int, size: int) -> bytes:
    material = f"{seed}|W7G3|{block}".encode("utf-8")
    return hashlib.shake_256(material).digest(size)


def build_packet(
    *, size: int, block_size: int, known_percent: int, seed: str
) -> Tuple[bytes, str, int, int]:
    if size <= 0 or size > MAX_SIZE:
        raise ProtocolHold("HOLD_SIZE_OUTSIDE_OBSERVED_V3_CONTRACT")
    if block_size <= 0 or size % block_size:
        raise ProtocolHold("HOLD_BLOCK_SIZE_INVALID")
    total_blocks = size // block_size
    if total_blocks > 65535:
        raise ProtocolHold("HOLD_BLOCK_COUNT_TOO_LARGE")
    if not 0 <= known_percent <= 100:
        raise ProtocolHold("HOLD_KNOWN_PERCENT_INVALID")

    known_count = total_blocks * known_percent // 100
    novel_count = total_blocks - known_count
    body = bytearray(HEADER.pack(MAGIC, size, block_size, known_count, novel_count))
    state = bytearray(repeat_to_size(BASE_PATTERN, size))

    for block in range(known_count):
        token_id = block % len(TOKEN_TABLE)
        body.extend(KNOWN.pack(block, token_id))
        start = block * block_size
        state[start : start + block_size] = repeat_to_size(TOKEN_TABLE[token_id], block_size)

    for block in range(known_count, total_blocks):
        payload = novel_payload(seed, block, block_size)
        body.extend(NOVEL_INDEX.pack(block))
        body.extend(payload)
        start = block * block_size
        state[start : start + block_size] = payload

    return bytes(body), hashlib.sha256(state).hexdigest(), known_count, novel_count


def post_packet(base_url: str, packet: bytes, timeout: float) -> Dict[str, object]:
    url = base_url.rstrip("/") + "/generative"
    request = urllib.request.Request(
        url,
        data=packet,
        method="POST",
        headers={"Content-Type": "application/octet-stream"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise ProtocolHold(f"HOLD_RECEIVER_HTTP_{exc.code}") from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolHold("HOLD_RECEIVER_RESPONSE_INVALID") from exc


def send_lan_first(
    *, lan_url: str, vpn_url: str, packet: bytes, timeout: float
) -> Tuple[Dict[str, object], str, str]:
    try:
        return post_packet(lan_url, packet, timeout), lan_url, "LAN_PRIMARY"
    except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError):
        pass

    try:
        return (
            post_packet(vpn_url, packet, timeout),
            vpn_url,
            "VPN_FALLBACK_AFTER_LAN_UNREACHABLE",
        )
    except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError) as exc:
        raise ProtocolHold("HOLD_LAN_AND_VPN_UNREACHABLE") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="W7TP V3 LAN-first exact sender candidate")
    parser.add_argument("--lan-url", default="http://192.168.50.249:8082")
    parser.add_argument("--vpn-fallback-url", default="http://100.71.224.18:8082")
    parser.add_argument("--size", type=int, default=8 * 1024 * 1024)
    parser.add_argument("--block-size", type=int, default=65536)
    parser.add_argument("--known-percent", type=int, default=95)
    parser.add_argument("--seed", default="W7TP_V3_LAN_FIRST_2.3")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--report")
    args = parser.parse_args()

    packet, expected_sha256, known_count, novel_count = build_packet(
        size=args.size,
        block_size=args.block_size,
        known_percent=args.known_percent,
        seed=args.seed,
    )
    started = time.perf_counter_ns()
    response, selected_url, selected_route = send_lan_first(
        lan_url=args.lan_url,
        vpn_url=args.vpn_fallback_url,
        packet=packet,
        timeout=args.timeout,
    )
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000

    if response.get("STATE_SHA256") != expected_sha256:
        raise ProtocolHold("HOLD_EXACT_RECONSTRUCTION_HASH_MISMATCH")
    if int(response.get("RECONSTRUCTED_BYTES", -1)) != args.size:
        raise ProtocolHold("HOLD_RECONSTRUCTED_SIZE_MISMATCH")

    receipt = {
        "schema": "W7TP-V3-LAN-FIRST-SEND-RECEIPT/1.0",
        "state": "PASS_CANDIDATE_EXACT_RECONSTRUCTION",
        "canonical": False,
        "target_system_version": "2.3",
        "source_contract_sha256": SOURCE_CONTRACT_SHA256,
        "route_policy": "LAN_PRIMARY_VPN_ONLY_AFTER_LAN_UNREACHABLE",
        "selected_route": selected_route,
        "selected_url": selected_url,
        "lan_url": args.lan_url,
        "vpn_fallback_url": args.vpn_fallback_url,
        "packet_bytes": len(packet),
        "reconstructed_bytes": args.size,
        "known_count": known_count,
        "novel_count": novel_count,
        "expected_state_sha256": expected_sha256,
        "receiver_state_sha256": response.get("STATE_SHA256"),
        "elapsed_ms": elapsed_ms,
        "D8": "FOUNDER_AUTHORIZED_CANDIDATE_EFFECT_NOT_SELF_PROMOTED",
    }
    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
