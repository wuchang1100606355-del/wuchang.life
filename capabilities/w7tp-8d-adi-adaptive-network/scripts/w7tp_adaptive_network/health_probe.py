from __future__ import annotations

import ipaddress
import hashlib
import socket
import ssl
import time
from typing import Any
from urllib.parse import urlsplit

from .common import parse_json_result, run_command


def dns_resolution(host: str) -> dict[str, Any]:
    started = time.monotonic()
    try:
        rows = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        return {
            "probe": "DNS_RESOLUTION",
            "passed": False,
            "addresses": [],
            "error": exc.__class__.__name__,
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
        }
    addresses: list[str] = []
    for row in rows:
        address = row[4][0]
        if address not in addresses:
            addresses.append(address)
    return {
        "probe": "DNS_RESOLUTION",
        "passed": bool(addresses),
        "addresses": addresses,
        "duration_ms": round((time.monotonic() - started) * 1000, 3),
    }


def tcp_connect(host: str, port: int, family: int = socket.AF_UNSPEC, timeout: float = 3.0) -> dict[str, Any]:
    started = time.monotonic()
    try:
        candidates = socket.getaddrinfo(host, port, family, socket.SOCK_STREAM)
    except socket.gaierror as exc:
        return {
            "probe": "TCP_CONNECT",
            "passed": False,
            "host": host,
            "port": port,
            "error": exc.__class__.__name__,
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
        }
    errors: list[str] = []
    for af, socktype, proto, _, sockaddr in candidates:
        sock = socket.socket(af, socktype, proto)
        sock.settimeout(timeout)
        try:
            sock.connect(sockaddr)
            return {
                "probe": "TCP_CONNECT",
                "passed": True,
                "host": host,
                "port": port,
                "remote": sockaddr[0],
                "address_family": "IPV6" if af == socket.AF_INET6 else "IPV4",
                "duration_ms": round((time.monotonic() - started) * 1000, 3),
            }
        except OSError as exc:
            errors.append(exc.__class__.__name__)
        finally:
            sock.close()
    return {
        "probe": "TCP_CONNECT",
        "passed": False,
        "host": host,
        "port": port,
        "errors": sorted(set(errors)),
        "duration_ms": round((time.monotonic() - started) * 1000, 3),
    }


def ssh_handshake(host: str, port: int = 22, family: int = socket.AF_UNSPEC) -> dict[str, Any]:
    started = time.monotonic()
    try:
        candidates = socket.getaddrinfo(host, port, family, socket.SOCK_STREAM)
    except socket.gaierror as exc:
        return {"probe": "SSH_HANDSHAKE", "passed": False, "error": exc.__class__.__name__}
    for af, socktype, proto, _, sockaddr in candidates:
        sock = socket.socket(af, socktype, proto)
        sock.settimeout(3.0)
        try:
            sock.connect(sockaddr)
            banner = sock.recv(255).decode("ascii", errors="replace").strip()
            return {
                "probe": "SSH_HANDSHAKE",
                "passed": banner.startswith("SSH-"),
                "banner_class": banner.split("-", 2)[:2],
                "remote": sockaddr[0],
                "duration_ms": round((time.monotonic() - started) * 1000, 3),
            }
        except OSError:
            continue
        finally:
            sock.close()
    return {
        "probe": "SSH_HANDSHAKE",
        "passed": False,
        "duration_ms": round((time.monotonic() - started) * 1000, 3),
    }


def http_probe(
    url: str,
    family: int = 0,
    timeout: float = 7.0,
    *,
    ca_file: str | None = None,
    certificate_fingerprint_sha256: str | None = None,
    insecure_diagnostic: bool = False,
    resolve_address: str | None = None,
) -> dict[str, Any]:
    parsed = urlsplit(url)
    is_tls = parsed.scheme.lower() == "https"
    argv = ["curl", "-sS", "-o", "/dev/null"]
    if family == 4:
        argv.append("-4")
    elif family == 6:
        argv.append("-6")
    if is_tls and insecure_diagnostic:
        argv.append("-k")
    elif is_tls and ca_file:
        argv.extend(["--cacert", ca_file])
    if resolve_address and parsed.hostname:
        port = parsed.port or (443 if is_tls else 80)
        resolved = f"[{resolve_address}]" if ":" in resolve_address else resolve_address
        argv.extend(["--resolve", f"{parsed.hostname}:{port}:{resolved}"])
    argv.extend(
        [
            "--connect-timeout",
            "3",
            "--max-time",
            str(int(timeout)),
            "-w",
            "%{http_code}|%{remote_ip}|%{time_total}",
            url,
        ]
    )
    result = run_command(argv, timeout=timeout + 2)
    status, remote, elapsed = "000", "", ""
    fields = result.get("stdout", "").strip().split("|", 2)
    if len(fields) == 3:
        status, remote, elapsed = fields
    transport_passed = (
        result.get("returncode") == 0 and status.isdigit() and 200 <= int(status) < 400
    )
    fingerprint_result = {
        "requested": False,
        "matched": None,
        "error": None,
    }
    if is_tls and certificate_fingerprint_sha256 and not insecure_diagnostic:
        fingerprint_result = _verify_certificate_fingerprint(
            host=parsed.hostname or "",
            port=parsed.port or 443,
            expected=certificate_fingerprint_sha256,
            connect_host=resolve_address,
            ca_file=ca_file,
            timeout=min(timeout, 5.0),
        )
    formal_tls = bool(
        not is_tls
        or (
            transport_passed
            and not insecure_diagnostic
            and (not certificate_fingerprint_sha256 or fingerprint_result["matched"] is True)
        )
    )
    passed = bool(transport_passed and formal_tls and not insecure_diagnostic)
    return {
        "probe": "HTTP_APPLICATION",
        "passed": passed,
        "application_pass": passed,
        "diagnostic_transport_reachable": transport_passed,
        "url": url,
        "http_status": int(status) if status.isdigit() else 0,
        "remote": remote,
        "time_total": elapsed,
        "address_family": "IPV6" if ":" in remote else ("IPV4" if remote else "UNKNOWN"),
        "error_class": "NONE" if result.get("returncode") == 0 else result.get("status"),
        "tls_verification": (
            "NOT_APPLICABLE"
            if not is_tls
            else (
                "TLS_UNVERIFIED_DIAGNOSTIC"
                if insecure_diagnostic
                else (
                    "SYSTEM_OR_EXPLICIT_CA_PLUS_CERTIFICATE_FINGERPRINT"
                    if certificate_fingerprint_sha256
                    else ("EXPLICIT_CA" if ca_file else "SYSTEM_CA")
                )
            )
        ),
        "formal_tls_verified": formal_tls,
        "certificate_fingerprint": fingerprint_result,
    }


def route_lookup(target: str, family: int) -> dict[str, Any]:
    flag = "-6" if family == 6 else "-4"
    result = run_command(["ip", "-j", flag, "route", "get", target], timeout=5.0)
    routes = parse_json_result(result, [])
    route = routes[0] if isinstance(routes, list) and routes else {}
    return {
        "probe": "ROUTE_LOOKUP",
        "passed": result.get("returncode") == 0 and bool(route),
        "target": target,
        "route": route,
    }


def ping_target(target: str, family: int, interface: str | None = None) -> dict[str, Any]:
    flag = "-6" if family == 6 else "-4"
    destination = f"{target}%{interface}" if family == 6 and interface and target.lower().startswith("fe80:") else target
    result = run_command(["ping", flag, "-c", "1", "-W", "2", destination], timeout=4.0)
    return {
        "probe": "ICMP_REACHABILITY",
        "passed": result.get("returncode") == 0,
        "target": target,
        "interface": interface,
        "duration_ms": result.get("duration_ms"),
    }


def tailscale_ping(target: str) -> dict[str, Any]:
    result = run_command(
        ["tailscale", "ping", "--timeout=3s", "--c", "1", target], timeout=5.0
    )
    output = f"{result.get('stdout', '')}\n{result.get('stderr', '')}".strip()
    return {
        "probe": "TAILSCALE_PING",
        "passed": result.get("returncode") == 0 and "pong from" in output,
        "target": target,
        "path_class": (
            "DIRECT" if "via DERP(" not in output and "pong from" in output else "DERP_OR_UNKNOWN"
        ),
        "duration_ms": result.get("duration_ms"),
    }


def ipv6_qualification_probe(
    local: dict[str, Any], host: str, port: int, application_url: str
) -> dict[str, Any]:
    dns = dns_resolution(host)
    targets = [address for address in dns.get("addresses", []) if _is_ipv6(address)]
    global_addresses = _global_native_ipv6(local.get("addresses", []))
    defaults = [route for route in local.get("routes_v6", []) if route.get("dst") == "default"]
    candidates = [
        _probe_ipv6_candidate(
            target=target,
            host=host,
            port=port,
            application_url=application_url,
            global_addresses=global_addresses,
            defaults=defaults,
        )
        for target in targets
    ]
    return {
        "target_host": host,
        "target_port": port,
        "application_url": application_url,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "qualified_candidate_ids": [
            candidate["path_id"] for candidate in candidates if candidate["qualified"]
        ],
        "global_ipv6_pass": False,
        "qualification_scope": "PER_AAAA_CANDIDATE",
        "dns": dns,
        "native_source_addresses": global_addresses,
    }


def _probe_ipv6_candidate(
    *,
    target: str,
    host: str,
    port: int,
    application_url: str,
    global_addresses: list[str],
    defaults: list[dict[str, Any]],
) -> dict[str, Any]:
    route = route_lookup(target, 6) if target else {"passed": False, "route": {}}
    route_data = route.get("route", {})
    interface = route_data.get("dev") or (defaults[0].get("dev") if defaults else None)
    source = route_data.get("prefsrc") or route_data.get("src")
    gateway = route_data.get("gateway") or (defaults[0].get("gateway") if defaults else None)
    next_hop = (
        ping_target(gateway, 6, interface)
        if gateway
        else {"probe": "ICMP_REACHABILITY", "passed": False, "target": "UNKNOWN"}
    )
    target_ping = (
        ping_target(target, 6, interface)
        if target
        else {"probe": "ICMP_REACHABILITY", "passed": False, "target": "UNKNOWN"}
    )
    tcp = tcp_connect(target, port, socket.AF_INET6) if target else {"passed": False}
    application = http_probe(application_url, family=6, resolve_address=target)
    response_matches_target = _same_ip(application.get("remote", ""), target)
    gates = {
        "ADDRESS_PRESENT": bool(global_addresses),
        "DEFAULT_ROUTE_PRESENT": bool(defaults),
        "SOURCE_SELECTION_VALID": bool(route.get("passed") and source and source in global_addresses),
        "NEXT_HOP_REACHABLE": bool(next_hop.get("passed")),
        "TARGET_REACHABLE": bool(target_ping.get("passed") or tcp.get("passed")),
        "TCP_SERVICE_REACHABLE": bool(tcp.get("passed")),
        "RETURN_PATH_VALID": bool(tcp.get("passed") and response_matches_target),
        "APPLICATION_PASS": bool(
            application.get("passed") and application.get("formal_tls_verified")
        ),
    }
    return {
        "path_id": f"NATIVE_IPV6@{target}",
        "target_host": host,
        "target_ipv6": target,
        "target_port": port,
        "application_url": application_url,
        "gates": gates,
        "qualified": all(gates.values()),
        "evidence": {
            "route": route,
            "next_hop": next_hop,
            "target_reachability": target_ping,
            "tcp": tcp,
            "application": application,
            "native_source_addresses": global_addresses,
        },
    }


def _verify_certificate_fingerprint(
    *,
    host: str,
    port: int,
    expected: str,
    connect_host: str | None,
    ca_file: str | None,
    timeout: float,
) -> dict[str, Any]:
    normalized = expected.lower().replace("sha256:", "").replace(":", "")
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        return {"requested": True, "matched": False, "error": "INVALID_SHA256_FINGERPRINT"}
    try:
        context = ssl.create_default_context(cafile=ca_file)
        with socket.create_connection((connect_host or host, port), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=host) as wrapped:
                measured = hashlib.sha256(wrapped.getpeercert(binary_form=True)).hexdigest()
    except (OSError, ssl.SSLError, ValueError):
        return {"requested": True, "matched": False, "error": "TLS_FINGERPRINT_PROBE_FAILED"}
    return {"requested": True, "matched": measured == normalized, "error": None}


def _global_native_ipv6(addresses: list[dict[str, Any]]) -> list[str]:
    found: list[str] = []
    for interface in addresses:
        if interface.get("ifname") == "tailscale0":
            continue
        for entry in interface.get("addr_info", []):
            if entry.get("family") != "inet6" or not entry.get("local"):
                continue
            value = entry["local"]
            try:
                address = ipaddress.ip_address(value)
            except ValueError:
                continue
            if not address.is_loopback and not address.is_link_local and not address.is_private:
                found.append(value)
    return found


def _is_ipv6(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).version == 6
    except ValueError:
        return False


def _same_ip(left: str, right: str) -> bool:
    try:
        return ipaddress.ip_address(left) == ipaddress.ip_address(right)
    except ValueError:
        return False
