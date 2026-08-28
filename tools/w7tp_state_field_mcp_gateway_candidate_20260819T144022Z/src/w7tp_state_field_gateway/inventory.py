"""Evidence-bound node, service, health, and bounded-log adapters."""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import socket
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .errors import GatewayError, PolicyDenied
from .policy import MAX_LOG_OUTPUT_BYTES, MAX_LOG_READ_BYTES
from .redaction import redact_text

_RELATIVE_SECONDS = re.compile(r"^\[relative_seconds=-(\d+)]")


def validate_and_summarize_nodes(
    nodes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate node safety invariants and project evidenced hardware domains."""

    identifiers: set[str] = set()
    fault_domains: dict[str, list[str]] = {}
    mobile_nodes: list[str] = []
    for node in nodes:
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id or node_id in identifiers:
            raise RuntimeError("Node IDs must be unique non-empty strings.")
        identifiers.add(node_id)
        node_class = node.get("node_class")
        if node_class == "mobile_sensing_light_compute_node":
            if node.get("shell_capable") is not False or node.get("execution_enabled") is not False:
                raise RuntimeError("Mobile nodes must remain non-shell, non-executing candidates.")
            mobile_nodes.append(node_id)
        fault_domain = node.get("physical_fault_domain_id")
        if fault_domain is not None:
            if not isinstance(fault_domain, str) or not fault_domain:
                raise RuntimeError("Physical fault-domain IDs must be strings or null.")
            fault_domains.setdefault(fault_domain, []).append(node_id)
    return {
        "logical_node_count": len(identifiers),
        "evidenced_physical_fault_domains": [
            {
                "id": fault_domain,
                "logical_node_ids": sorted(node_ids),
                "count_as_independent_hardware_domains": 1,
            }
            for fault_domain, node_ids in sorted(fault_domains.items())
        ],
        "mobile_node_ids": sorted(mobile_nodes),
        "mobile_shell_assumed": False,
    }


class EvidenceInventory:
    """Loads one fixed allowlist and never accepts a caller-supplied path or command."""

    def __init__(self, candidate_root: Path) -> None:
        self.candidate_root = candidate_root.resolve()
        config_path = self.candidate_root / "config" / "allowlist.json"
        self._config = json.loads(config_path.read_text(encoding="utf-8"))
        self._nodes = {node["id"]: node for node in self._config["nodes"]}
        self._services = {service["id"]: service for service in self._config["services"]}
        self._node_model_summary = validate_and_summarize_nodes(self._config["nodes"])
        self._validate_fixed_config()

    @property
    def config(self) -> dict[str, Any]:
        return self._config

    def _validate_fixed_config(self) -> None:
        if len(self._nodes) != len(self._config["nodes"]):
            raise RuntimeError("Duplicate node IDs in fixed allowlist.")
        if len(self._services) != len(self._config["services"]):
            raise RuntimeError("Duplicate service IDs in fixed allowlist.")
        expected_domains = self._node_model_summary["evidenced_physical_fault_domains"]
        configured_domains = sorted(
            self._config["physical_fault_domains"], key=lambda item: item["id"]
        )
        if expected_domains != configured_domains:
            raise RuntimeError("Physical fault-domain projection does not match node evidence.")
        for service in self._services.values():
            if service.get("probe_host") not in (None, "127.0.0.1"):
                raise RuntimeError("Non-loopback service probe in fixed allowlist.")
            if service["node_id"] not in self._nodes:
                raise RuntimeError("Service references an unknown node.")
            relative_log = service.get("log_file")
            if relative_log is not None:
                unresolved = self.candidate_root / relative_log
                path = unresolved.resolve()
                fixture_root = (self.candidate_root / "fixtures").resolve()
                if unresolved.is_symlink() or fixture_root not in path.parents:
                    raise RuntimeError("Log allowlist escapes the synthetic fixture boundary.")

    def list_nodes(self) -> list[dict[str, Any]]:
        fields = (
            "id",
            "display_name",
            "node_class",
            "os_family",
            "logical_plane",
            "physical_fault_domain_id",
            "fault_domain_evidence",
            "last_observed_online",
            "shell_capable",
            "execution_enabled",
        )
        return [{field: node.get(field) for field in fields} for node in self._nodes.values()]

    def node(self, node_id: str) -> dict[str, Any]:
        try:
            return self._nodes[node_id]
        except KeyError as exc:
            raise PolicyDenied("DENY_UNKNOWN_NODE", "The node ID is not allowlisted.") from exc

    def service(self, node_id: str, service_id: str) -> dict[str, Any]:
        self.node(node_id)
        try:
            service = self._services[service_id]
        except KeyError as exc:
            raise PolicyDenied("DENY_NODE_SERVICE_PAIR", "The node/service pair is not allowlisted.") from exc
        if service["node_id"] != node_id:
            raise PolicyDenied("DENY_NODE_SERVICE_PAIR", "The node/service pair is not allowlisted.")
        return service

    def get_node_health(self, node_id: str) -> dict[str, Any]:
        node = self.node(node_id)
        if node["health_mode"] != "local_safe_metrics":
            return {
                "node_id": node_id,
                "status": "NOT_OBSERVED_REMOTE_PROBE_FORBIDDEN",
                "last_observed_online": node["last_observed_online"],
                "remote_connection_attempted": False,
            }
        memory: dict[str, int] = {}
        with Path("/proc/meminfo").open("r", encoding="utf-8") as handle:
            for line in handle:
                key, _, remainder = line.partition(":")
                if key in {"MemTotal", "MemAvailable"}:
                    memory[key] = int(remainder.strip().split()[0]) * 1024
        uptime_seconds = int(float(Path("/proc/uptime").read_text(encoding="utf-8").split()[0]))
        disk = shutil.disk_usage("/")
        load_1m = os.getloadavg()[0]
        return {
            "node_id": node_id,
            "status": "OBSERVED_LOCAL_READ_ONLY",
            "os_family": platform.system().lower(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "uptime_seconds": uptime_seconds,
            "load_1m": round(load_1m, 3),
            "memory_total_bytes": memory.get("MemTotal"),
            "memory_available_bytes": memory.get("MemAvailable"),
            "disk_total_bytes": disk.total,
            "disk_free_bytes": disk.free,
        }

    def get_compute_capability(self, node_id: str) -> dict[str, Any]:
        node = self.node(node_id)
        return {
            "node_id": node_id,
            "node_class": node["node_class"],
            "observed_capabilities": list(node["observed_capabilities"]),
            "agent_candidates": list(node["agent_candidates"]),
            "shell_capable": node["shell_capable"],
            "execution_enabled": False,
            "evidence_status": node["capability_evidence_status"],
        }

    def get_service_status(self, node_id: str, service_id: str) -> dict[str, Any]:
        service = self.service(node_id, service_id)
        if service.get("probe_host") is None:
            return {
                "node_id": node_id,
                "service_id": service_id,
                "status": "NOT_OBSERVED_REMOTE_PROBE_FORBIDDEN",
                "probe_attempted": False,
            }
        reachable = False
        try:
            with socket.create_connection(
                (service["probe_host"], int(service["probe_port"])), timeout=0.25
            ):
                reachable = True
        except OSError:
            reachable = False
        return {
            "node_id": node_id,
            "service_id": service_id,
            "status": "LISTENING" if reachable else "NOT_LISTENING",
            "probe_scope": "LOOPBACK_TCP_ONLY",
            "configured_port": service["probe_port"],
            "exposure_baseline": service["exposure_baseline"],
            "mutation_attempted": False,
        }

    def read_bounded_logs(
        self, node_id: str, service_id: str, lines: int, since_seconds: int
    ) -> dict[str, Any]:
        service = self.service(node_id, service_id)
        relative_log = service.get("log_file")
        if relative_log is None:
            raise PolicyDenied(
                "DENY_PROTECTED_RESOURCE",
                "No model-readable log source is allowlisted for this service.",
            )
        unresolved = self.candidate_root / relative_log
        path = unresolved.resolve()
        fixture_root = (self.candidate_root / "fixtures").resolve()
        if unresolved.is_symlink() or fixture_root not in path.parents:
            raise PolicyDenied("DENY_PROTECTED_RESOURCE", "The log source failed containment policy.")
        try:
            with path.open("rb") as handle:
                handle.seek(0, 2)
                size = handle.tell()
                handle.seek(max(0, size - MAX_LOG_READ_BYTES))
                bounded_bytes = handle.read(MAX_LOG_READ_BYTES)
            raw_lines = bounded_bytes.decode("utf-8", errors="replace").splitlines()[-lines:]
        except OSError as exc:
            raise GatewayError("BACKEND_NOT_OBSERVED", "The allowlisted log source is unavailable.") from exc
        selected: list[str] = []
        for raw_line in raw_lines:
            match = _RELATIVE_SECONDS.match(raw_line)
            # A line without the fixture's explicit relative timestamp cannot
            # prove that it is inside the requested window, so omit it.
            if match is not None and int(match.group(1)) <= since_seconds:
                selected.append(redact_text(raw_line.rstrip()))
        bounded_lines: list[str] = []
        bounded_size = 0
        for line in selected:
            separator_size = 1 if bounded_lines else 0
            line_size = len(line.encode("utf-8"))
            if bounded_size + separator_size + line_size > MAX_LOG_OUTPUT_BYTES:
                break
            bounded_lines.append(line)
            bounded_size += separator_size + line_size
        bounded = "\n".join(bounded_lines)
        return {
            "node_id": node_id,
            "service_id": service_id,
            "source_class": "SYNTHETIC_FIXTURE_ONLY",
            "line_limit": lines,
            "time_limit_seconds": since_seconds,
            "returned_lines": len(bounded_lines),
            "masked": True,
            "text": bounded,
        }

    def topology(self) -> dict[str, Any]:
        return {
            "snapshot_status": "SANITIZED_CANDIDATE_EVIDENCE",
            "nodes": self.list_nodes(),
            "physical_fault_domains": self._config["physical_fault_domains"],
            "subnet_gateways": self._config["subnet_gateways"],
            "cloud_extension_nodes": self._config["cloud_extension_nodes"],
            "carriers": self._config["carriers"],
            "protected_opaque_nodes": self._config["protected_opaque_nodes"],
            "node_model_summary": self._node_model_summary,
        }
