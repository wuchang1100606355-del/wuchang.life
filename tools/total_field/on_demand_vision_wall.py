#!/usr/bin/env python3
"""Total Field on-demand vision wall capability.

This module converts a short Traditional-Chinese viewing intent into a deterministic,
credential-free launch plan. It does not store credentials, open RTSP streams, or
start a persistent service. A local UI executor may consume the returned plan only
when the Founder explicitly requests viewing.
"""

from __future__ import annotations

import argparse
import json
import re
import socket
from dataclasses import asdict, dataclass
from typing import Iterable

LOCAL_HOST = "192.168.50.34"
REMOTE_HOST = "p1430563.ds1.nxt.net.tw"
RTSP_PORT = 554
SERVICE_PORT = 30080
CHANNEL_COUNT = 8
STREAM_PRIMARY = 0
STREAM_SECONDARY = 1


@dataclass(frozen=True)
class VisionWallPlan:
    capability: str
    mode: str
    host: str
    route: str
    channels: list[int]
    layout: str
    stream: int
    rtsp_port: int
    service_port: int
    credential_policy: str
    persistent_stream: bool
    urls: list[str]


def _unique(values: Iterable[int]) -> list[int]:
    return sorted(set(values))


def parse_channels(text: str) -> list[int]:
    value = str(text or "").strip().lower()
    if not value:
        raise ValueError("VISION_INTENT_REQUIRED")

    if any(token in value for token in ("全部", "全開", "所有", "八路", "8路")):
        return list(range(CHANNEL_COUNT))

    ranges = re.findall(r"([1-8])\s*(?:到|至|[-~～])\s*([1-8])", value)
    channels: list[int] = []
    for start, end in ranges:
        a, b = int(start), int(end)
        lo, hi = sorted((a, b))
        channels.extend(range(lo - 1, hi))

    chinese = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8}
    for token, number in chinese.items():
        if re.search(rf"(?:看|開|顯示)?\s*{token}\s*(?:號|路|台)?", value):
            channels.append(number - 1)

    for number in re.findall(r"(?<!\d)([1-8])(?!\d)", value):
        channels.append(int(number) - 1)

    result = _unique(channels)
    if not result:
        raise ValueError("VISION_CHANNEL_NOT_RESOLVED")
    return result


def choose_layout(channel_count: int) -> str:
    if channel_count <= 1:
        return "1x1"
    if channel_count <= 4:
        return "2x2"
    return "3x3"


def _tcp_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def choose_host(*, probe_local: bool = False) -> tuple[str, str]:
    if probe_local and _tcp_open(LOCAL_HOST, RTSP_PORT):
        return LOCAL_HOST, "LOCAL_LAN"
    return REMOTE_HOST, "REMOTE_DDNS"


def build_plan(text: str, *, probe_local: bool = False, stream: int = STREAM_SECONDARY) -> VisionWallPlan:
    if stream not in (STREAM_PRIMARY, STREAM_SECONDARY):
        raise ValueError("VISION_STREAM_INVALID")
    channels = parse_channels(text)
    host, route = choose_host(probe_local=probe_local)
    urls = [
        f"rtsp://{host}:{RTSP_PORT}/rtspstream?channel={channel}&stream={stream}"
        for channel in channels
    ]
    return VisionWallPlan(
        capability="CAP_ON_DEMAND_VISION_WALL_V1",
        mode="ON_DEMAND",
        host=host,
        route=route,
        channels=channels,
        layout=choose_layout(len(channels)),
        stream=stream,
        rtsp_port=RTSP_PORT,
        service_port=SERVICE_PORT,
        credential_policy="EXTERNAL_LOCAL_SECRET_STORE_ONLY",
        persistent_stream=False,
        urls=urls,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Total Field on-demand multi-camera vision wall planner")
    parser.add_argument("intent", help="例如：開全部監視器、看一號、看一到四號")
    parser.add_argument("--probe-local", action="store_true", help="只探測本地 554 是否可達；不可達則使用 DDNS")
    parser.add_argument("--primary", action="store_true", help="使用主串流；預設使用較節能的副串流")
    args = parser.parse_args(argv)
    try:
        plan = build_plan(
            args.intent,
            probe_local=args.probe_local,
            stream=STREAM_PRIMARY if args.primary else STREAM_SECONDARY,
        )
    except ValueError as exc:
        print(json.dumps({"state": "BLOCK", "reason_code": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({"state": "PASS_PLAN", **asdict(plan)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
