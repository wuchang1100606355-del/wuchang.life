"""Read-only, privacy-minimized Tailscale node inventory."""

from __future__ import annotations

import json
import hashlib
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping

from tools.total_field.w7tp_field_application_runtime import FieldApplicationError

from .canonical_hash import canonical_sha256


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_AUTHORITY_REGISTRY = (
    ROOT
    / "manifests/w7tp_small_agent_node_authority_v0_1/node_authority_registry_runtime_minimized.json"
)
DEFAULT_CONTAINER_MANIFEST = (
    ROOT
    / "runtime/total_field/node_container_scope/TOTAL_FIELD_NODE_CONTAINER_MANIFEST_20260624.json"
)
BASE_ENTRYPOINT = ROOT / "tools/total_field/w7tp_field_application_runtime.py"
VALID_STATES = frozenset(
    {
        "INSTALLED_USABLE",
        "INSTALLED_UNUSABLE",
        "REACHABLE_NOT_INSTALLED",
        "REACHABLE_PROBE_UNAVAILABLE",
        "OFFLINE",
        "CLIENT_ONLY",
        "UNVERIFIED",
    }
)
TOTAL_FIELD_CONTAINER_AUTHORITY = "OBSERVE_INDEX_CLASSIFY_ROUTE_WARN_SEAL"


def _local_runtime_health() -> dict[str, Any]:
    health: dict[str, Any] = {
        "installed": BASE_ENTRYPOINT.is_file(),
        "self_test": False,
        "protocol_version": None,
        "manifest_sha256": None,
        "validator_compatible": False,
        "cpu": platform.machine() or "UNKNOWN",
        "gpu": "NOT_REQUIRED_FOR_COMPLETE_FUNCTION",
    }
    if not health["installed"]:
        return health
    digest = hashlib.sha256(BASE_ENTRYPOINT.read_bytes()).hexdigest()
    health["manifest_sha256"] = digest
    try:
        from .packet_builder import process_intent

        packet = process_intent(
            "GENERIC",
            {
                "requested_result": "LOCAL_RUNTIME_SELF_TEST",
                "constraints": "READ_ONLY",
                "evidence_refs": ["local:self-test"],
            },
        )
        health["self_test"] = packet.get("D8", {}).get("decision") == "PENDING_TOTAL_FIELD_REVIEW"
        health["validator_compatible"] = health["self_test"]
        health["protocol_version"] = packet.get("schema_version")
    except (FieldApplicationError, OSError):
        health["self_test"] = False
    return health


def _read_authority_registry(path: Path) -> dict[str, dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise FieldApplicationError("NODE_AUTHORITY_REGISTRY_READ_FAILED") from exc
    nodes = value.get("nodes") if isinstance(value, dict) else None
    if not isinstance(nodes, list):
        raise FieldApplicationError("NODE_AUTHORITY_REGISTRY_INVALID")
    return {
        str(node.get("hostname") or node.get("node_id")): node
        for node in nodes
        if isinstance(node, dict) and (node.get("hostname") or node.get("node_id"))
    }


def _peers(status: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    values: list[Mapping[str, Any]] = []
    own = status.get("Self") or status.get("self")
    if isinstance(own, Mapping):
        values.append(own)
    peer_value = status.get("Peer") or status.get("Peers") or status.get("peer") or []
    if isinstance(peer_value, Mapping):
        values.extend(item for item in peer_value.values() if isinstance(item, Mapping))
    elif isinstance(peer_value, list):
        values.extend(item for item in peer_value if isinstance(item, Mapping))
    return values


def _hostname(peer: Mapping[str, Any]) -> str:
    value = peer.get("HostName") or peer.get("Hostname") or peer.get("hostName")
    if value:
        return str(value).strip().rstrip(".")
    dns_name = peer.get("DNSName") or peer.get("dnsName") or "UNKNOWN"
    return str(dns_name).split(".", 1)[0] or "UNKNOWN"


def _container_port_scope(ports: str) -> str:
    if not ports:
        return "NONE_OBSERVED"
    if "0.0.0.0:" in ports or "[::]:" in ports:
        return "HOST_EXPOSED_REQUIRES_BOUNDARY_CHECK"
    if "127.0.0.1:" in ports:
        return "LOCAL_ONLY"
    return "CONTAINER_INTERNAL_OR_UNCLASSIFIED"


def _read_container_manifest(path: Path) -> dict[str, dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise FieldApplicationError("CONTAINER_MANIFEST_READ_FAILED") from exc
    scope = value.get("scope") if isinstance(value, dict) else None
    containers = value.get("observed_containers") if isinstance(value, dict) else None
    if not isinstance(scope, dict) or scope.get("total_field") != "ALL_NODES_AND_CONTAINERS":
        raise FieldApplicationError("CONTAINER_MANIFEST_SCOPE_INVALID")
    if not isinstance(containers, list):
        raise FieldApplicationError("CONTAINER_MANIFEST_INVALID")
    return {
        str(container.get("name")): container
        for container in containers
        if isinstance(container, dict) and container.get("name")
    }


def parse_docker_ps_json(
    output: str,
    *,
    manifest_path: Path = DEFAULT_CONTAINER_MANIFEST,
    live_probe_state: str = "LIVE_DOCKER_PS_READ_ONLY",
) -> dict[str, Any]:
    """Merge privacy-minimized docker ps rows with the sealed container scope."""

    manifest = _read_container_manifest(manifest_path)
    live: dict[str, Mapping[str, Any]] = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except (ValueError, json.JSONDecodeError) as exc:
            raise FieldApplicationError("DOCKER_PS_JSON_INVALID") from exc
        if not isinstance(row, Mapping) or not row.get("Names"):
            raise FieldApplicationError("DOCKER_PS_JSON_INVALID")
        live[str(row["Names"])] = row

    names = sorted(set(manifest) | set(live), key=str.casefold)
    containers: list[dict[str, Any]] = []
    for name in names:
        sealed = manifest.get(name, {})
        observed = live.get(name)
        runtime_state = (
            str(observed.get("State") or "UNKNOWN").upper()
            if observed is not None
            else "NOT_OBSERVED_CURRENTLY"
        )
        ports = str(observed.get("Ports") or "") if observed is not None else ""
        containers.append(
            {
                "container_ref": str(sealed.get("node_ref") or f"node.container.unclassified.{name}"),
                "name": name,
                "image": str((observed or {}).get("Image") or sealed.get("image") or "UNKNOWN"),
                "runtime_state": runtime_state,
                "observed_status": (
                    str(observed.get("Status") or runtime_state)
                    if observed is not None
                    else "SEALED_MANIFEST_ONLY"
                ),
                "port_scope": _container_port_scope(ports),
                "role": str(sealed.get("role") or "UNCLASSIFIED_CONTAINER"),
                "risk_level": str(sealed.get("risk_level") or "L2_UNKNOWN_REQUIRES_CLASSIFICATION"),
                "governance_state": "TOTAL_FIELD_GOVERNED_READ_ONLY",
                "total_field_authority": TOTAL_FIELD_CONTAINER_AUTHORITY,
                "runtime_mutation_authority": False,
                "allowed_default": list(sealed.get("allowed_default") or ["status_read", "governance_report"]),
                "forbidden_default": list(
                    sealed.get("forbidden_default")
                    or ["secret_read", "container_restart", "container_mutation", "production_write"]
                ),
                "observation_source": (
                    "LIVE_DOCKER_PS_READ_ONLY" if observed is not None else "SEALED_MANIFEST_ONLY"
                ),
            }
        )
    return {"probe_state": live_probe_state, "containers": containers}


def _collect_container_inventory(timeout_seconds: int) -> dict[str, Any]:
    executable = shutil.which("docker")
    if executable is None:
        return parse_docker_ps_json("", live_probe_state="DOCKER_CLI_UNAVAILABLE_SEALED_MANIFEST_ONLY")
    try:
        completed = subprocess.run(
            [executable, "ps", "-a", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            timeout=max(timeout_seconds, 1),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return parse_docker_ps_json("", live_probe_state="LIVE_PROBE_UNAVAILABLE_SEALED_MANIFEST_ONLY")
    if completed.returncode != 0:
        return parse_docker_ps_json("", live_probe_state="LIVE_PROBE_UNAVAILABLE_SEALED_MANIFEST_ONLY")
    return parse_docker_ps_json(completed.stdout)


def parse_tailscale_status(
    status: Mapping[str, Any],
    *,
    authority_registry_path: Path = DEFAULT_AUTHORITY_REGISTRY,
    ping_results: Mapping[str, bool | None] | None = None,
    remote_health: Mapping[str, Mapping[str, Any]] | None = None,
    container_inventory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert official status variants to a report without IPs or owner email."""

    authorized = _read_authority_registry(authority_registry_path)
    ping_results = ping_results or {}
    remote_health = remote_health or {}
    container_inventory = container_inventory or parse_docker_ps_json(
        "", live_probe_state="SEALED_MANIFEST_ONLY"
    )
    rows: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for peer in _peers(status):
        hostname = _hostname(peer)
        counts[hostname] = counts.get(hostname, 0) + 1
        node_id = hostname if counts[hostname] == 1 else f"{hostname}#{counts[hostname]}"
        authority = authorized.get(hostname)
        os_name = str(peer.get("OS") or peer.get("os") or "UNKNOWN")
        online = bool(peer.get("Online", peer.get("online", False)))
        is_self = bool(peer.get("Self", peer.get("self", False))) or hostname == platform.node()
        health = remote_health.get(hostname, {})
        if authority is None or authority.get("authority") != "OWNER_AUTHORIZED":
            state = "UNVERIFIED"
        elif os_name.casefold() in {"ios", "iphone", "ipad"}:
            state = "CLIENT_ONLY"
        elif not online:
            state = "OFFLINE"
        elif is_self:
            state = "INSTALLED_USABLE" if health.get("installed") is True and health.get("self_test") is True else "INSTALLED_UNUSABLE"
        elif health.get("installed") is True and health.get("self_test") is True:
            state = "INSTALLED_USABLE"
        elif health.get("installed") is True:
            state = "INSTALLED_UNUSABLE"
        elif health.get("installed") is False:
            state = "REACHABLE_NOT_INSTALLED"
        else:
            state = "REACHABLE_PROBE_UNAVAILABLE"
        row = {
            "node_id": node_id,
            "os": os_name,
            "online": online,
            "ownership": "VERIFIED" if authority is not None else "UNVERIFIED",
            "management_channel": (authority or {}).get("connection_method") or "NONE",
            "ping": (
                "REACHABLE"
                if ping_results.get(hostname) is True
                else "UNREACHABLE"
                if ping_results.get(hostname) is False
                else "NOT_RUN"
            ),
            "base_transport_state": state,
            "protocol_version": health.get("protocol_version"),
            "manifest_sha256": health.get("manifest_sha256"),
            "validator_compatible": health.get("validator_compatible"),
            "cpu": health.get("cpu", "NOT_YET_EVIDENCED"),
            "gpu": health.get("gpu", "NOT_YET_EVIDENCED"),
        }
        if row["base_transport_state"] not in VALID_STATES:
            raise FieldApplicationError("NODE_STATE_INVALID")
        rows.append(row)
    report: dict[str, Any] = {
        "schema_version": "W7TP-NODE-CAPABILITY/1.0",
        "state": "READ_ONLY_INVENTORY",
        "privacy": "NO_OWNER_EMAIL_NO_IP_NO_SECRET",
        "scope": "ALL_NODES_AND_CONTAINERS",
        "total_field_authority": TOTAL_FIELD_CONTAINER_AUTHORITY,
        "runtime_mutation_authority": False,
        "nodes": sorted(rows, key=lambda row: row["node_id"].casefold()),
        "containers": list(container_inventory.get("containers") or []),
        "container_probe": str(container_inventory.get("probe_state") or "UNKNOWN"),
        "single_node_failure_isolated": True,
    }
    report["content_sha256"] = canonical_sha256(report)
    return report


def collect_inventory(
    *,
    probe: bool = False,
    authority_registry_path: Path = DEFAULT_AUTHORITY_REGISTRY,
    timeout_seconds: int = 3,
) -> dict[str, Any]:
    executable = shutil.which("tailscale")
    if executable is None:
        raise FieldApplicationError("TAILSCALE_CLI_NOT_FOUND")
    completed = subprocess.run(
        [executable, "status", "--json"],
        capture_output=True,
        text=True,
        timeout=max(timeout_seconds, 1),
        check=False,
    )
    if completed.returncode != 0:
        raise FieldApplicationError("TAILSCALE_STATUS_FAILED")
    try:
        status = json.loads(completed.stdout)
    except (ValueError, json.JSONDecodeError) as exc:
        raise FieldApplicationError("TAILSCALE_STATUS_JSON_INVALID") from exc
    if not isinstance(status, dict):
        raise FieldApplicationError("TAILSCALE_STATUS_JSON_INVALID")

    ping_results: dict[str, bool | None] = {}
    if probe:
        authorized = _read_authority_registry(authority_registry_path)
        for peer in _peers(status):
            hostname = _hostname(peer)
            authority = authorized.get(hostname)
            os_name = str(peer.get("OS") or "").casefold()
            online = bool(peer.get("Online", False))
            if authority is None or not online or os_name == "ios" or hostname == platform.node():
                continue
            try:
                result = subprocess.run(
                    [
                        executable,
                        "ping",
                        "--c",
                        "1",
                        "--timeout",
                        f"{timeout_seconds}s",
                        "--until-direct=false",
                        hostname,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=timeout_seconds + 2,
                    check=False,
                )
                ping_results[hostname] = result.returncode == 0
            except subprocess.TimeoutExpired:
                ping_results[hostname] = False
    self_peer = status.get("Self") or status.get("self")
    own_hostnames = [_hostname(self_peer)] if isinstance(self_peer, Mapping) else []
    local_health = _local_runtime_health()
    remote_health = {hostname: local_health for hostname in own_hostnames}
    container_inventory = _collect_container_inventory(timeout_seconds)
    return parse_tailscale_status(
        status,
        authority_registry_path=authority_registry_path,
        ping_results=ping_results,
        remote_health=remote_health,
        container_inventory=container_inventory,
    )
