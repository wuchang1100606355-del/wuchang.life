from __future__ import annotations

import json
import platform
import socket
from pathlib import Path
from typing import Any

from .common import parse_json_result, run_command, sha256_bytes


def _machine_id_hash() -> str:
    path = Path("/etc/machine-id")
    try:
        raw = path.read_bytes().strip()
    except OSError:
        return "LOCALIZED_UNKNOWN"
    return f"sha256:{sha256_bytes(raw)}"


def _command_json(argv: list[str], timeout: float = 8.0) -> tuple[Any, dict[str, Any]]:
    result = run_command(argv, timeout=timeout)
    return parse_json_result(result, []), result


def observe_local() -> dict[str, Any]:
    links, links_result = _command_json(["ip", "-j", "link", "show"])
    addresses, addresses_result = _command_json(["ip", "-j", "address", "show"])
    routes_v4, routes_v4_result = _command_json(
        ["ip", "-j", "-4", "route", "show", "table", "main"]
    )
    routes_v6, routes_v6_result = _command_json(
        ["ip", "-j", "-6", "route", "show", "table", "main"]
    )
    neighbors, neighbors_result = _command_json(["ip", "-j", "neigh", "show"])
    tailscale_result = run_command(["tailscale", "status", "--json"], timeout=10.0)
    tailscale = parse_json_result(tailscale_result, {})
    listeners_result = run_command(["ss", "-H", "-lntup"], timeout=8.0)
    dns_result = run_command(["resolvectl", "dns"], timeout=5.0)
    virtualization_result = run_command(["systemd-detect-virt"], timeout=5.0)
    docker_result = run_command(
        ["docker", "ps", "--format", "{{json .}}"], timeout=10.0
    )
    docker_rows: list[dict[str, Any]] = []
    if docker_result.get("returncode") == 0:
        for line in docker_result.get("stdout", "").splitlines():
            try:
                docker_rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return {
        "hostname": socket.gethostname(),
        "machine_id": _machine_id_hash(),
        "platform": platform.platform(),
        "virtualization": virtualization_result.get("stdout", "").strip()
        or "none_or_unknown",
        "links": links,
        "addresses": addresses,
        "routes_v4": routes_v4,
        "routes_v6": routes_v6,
        "neighbors": neighbors,
        "tailscale": tailscale,
        "listeners_raw": listeners_result.get("stdout", ""),
        "dns_summary": dns_result.get("stdout", "").strip(),
        "docker_containers": docker_rows,
        "command_evidence": {
            "links": _result_summary(links_result),
            "addresses": _result_summary(addresses_result),
            "routes_v4": _result_summary(routes_v4_result),
            "routes_v6": _result_summary(routes_v6_result),
            "neighbors": _result_summary(neighbors_result),
            "tailscale": _result_summary(tailscale_result),
            "listeners": _result_summary(listeners_result),
            "dns": _result_summary(dns_result),
            "docker": _result_summary(docker_result),
        },
    }


def _result_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "executed": result.get("executed"),
        "returncode": result.get("returncode"),
        "status": result.get("status"),
        "duration_ms": result.get("duration_ms"),
        "stdout_sha256": sha256_bytes(result.get("stdout", "").encode("utf-8")),
        "stderr_class": (
            "NONE" if not result.get("stderr", "").strip() else "COMMAND_REPORTED_STDERR"
        ),
    }

