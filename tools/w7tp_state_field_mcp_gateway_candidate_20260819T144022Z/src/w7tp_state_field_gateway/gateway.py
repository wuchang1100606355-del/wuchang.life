"""Eight focused MCP tool handlers over a fixed local evidence allowlist."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any

from .errors import PolicyDenied
from .inventory import EvidenceInventory
from .policy import (
    AUTH_TTL_MAX_SECONDS,
    AUTH_TTL_MIN_SECONDS,
    MAX_LOG_AGE_SECONDS,
    MAX_LOG_LINES,
    MAX_TASK_CANDIDATES,
    TOOL_NAMES,
    require_enum,
    validate_exact_keys,
    validate_identifier,
    validate_integer,
    validate_sha256,
)
from .state_field import StateFieldRuntime

Clock = Callable[[], datetime]


@dataclass(frozen=True)
class TaskCandidateRecord:
    candidate_id: str
    task_hash: str
    task_basis: dict[str, Any]
    issued_at: datetime
    expires_at: datetime

TASK_KINDS = {
    "observe_node_health": "get_node_health",
    "observe_compute_capability": "get_compute_capability",
    "observe_service_status": "get_service_status",
    "observe_bounded_logs": "read_bounded_logs",
    "snapshot_state_field_topology": "get_state_field_topology",
}
ROLLBACK_CONDITIONS = {
    "discard_candidate",
    "no_state_change_expected",
    "restore_pre_task_snapshot",
}
STOP_CONDITIONS = {
    "first_policy_denial",
    "output_policy_blocked",
    "target_health_degraded",
    "ttl_expired",
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _closed_object(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required,
    }


_OUTPUT_SCHEMA = _closed_object(
    {
        "status": {"type": "string"},
        "state_field_status": {"type": "string"},
        "adi_index_status": {"type": "string"},
        "packet_ref": {"type": "string"},
        "content_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        "result_json": {"type": "string", "maxLength": 65536},
    },
    [
        "status",
        "state_field_status",
        "adi_index_status",
        "packet_ref",
        "content_sha256",
        "result_json",
    ],
)


class StateFieldGateway:
    """A local, non-executing facade used by the MCP transport."""

    def __init__(self, candidate_root: Path | None = None, clock: Clock = _utc_now) -> None:
        root = candidate_root or Path(__file__).resolve().parents[2]
        self._clock = clock
        self.inventory = EvidenceInventory(root)
        self.runtime = StateFieldRuntime(clock=clock)
        self._registry_lock = Lock()
        self._candidate_sequence = 0
        self._task_candidates: dict[str, TaskCandidateRecord] = {}
        self._authorization_prepared: set[str] = set()

    def list_tool_definitions(self) -> list[dict[str, Any]]:
        node_ids = sorted(node["id"] for node in self.inventory.config["nodes"])
        service_ids = sorted(service["id"] for service in self.inventory.config["services"])
        log_service_ids = sorted(
            service["id"]
            for service in self.inventory.config["services"]
            if service.get("log_file") is not None
        )
        node_property = {"type": "string", "enum": node_ids}
        service_property = {"type": "string", "enum": service_ids}
        annotations = {
            "readOnlyHint": True,
            "destructiveHint": False,
            "openWorldHint": False,
        }
        task_parameters_schema = _closed_object(
            {
                "lines": {"type": "integer", "minimum": 1, "maximum": MAX_LOG_LINES},
                "since_seconds": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_LOG_AGE_SECONDS,
                },
            },
            [],
        )
        definitions = [
            (
                "list_nodes",
                "List allowlisted nodes",
                "List only sanitized evidence-bound logical nodes; never returns addresses or login identities.",
                _closed_object({}, []),
            ),
            (
                "get_node_health",
                "Get bounded node health",
                "Read safe local metrics for MSI WSL or return a no-remote-probe evidence state.",
                _closed_object({"node_id": node_property}, ["node_id"]),
            ),
            (
                "get_compute_capability",
                "Get compute capability",
                "Return evidence-bound capabilities and disabled agent candidates; it never exposes shell.",
                _closed_object({"node_id": node_property}, ["node_id"]),
            ),
            (
                "get_service_status",
                "Get service status",
                "Probe only a fixed node/service allowlist; local probes are TCP loopback observations only.",
                _closed_object(
                    {"node_id": node_property, "service_id": service_property},
                    ["node_id", "service_id"],
                ),
            ),
            (
                "read_bounded_logs",
                "Read bounded masked logs",
                "Read only an allowlisted synthetic source with line, time, byte, and redaction limits.",
                _closed_object(
                    {
                        "node_id": node_property,
                        "service_id": {"type": "string", "enum": log_service_ids},
                        "lines": {"type": "integer", "minimum": 1, "maximum": MAX_LOG_LINES},
                        "since_seconds": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": MAX_LOG_AGE_SECONDS,
                        },
                    },
                    ["node_id", "service_id", "lines", "since_seconds"],
                ),
            ),
            (
                "get_state_field_topology",
                "Get sanitized state-field topology",
                "Return logical planes, evidenced fault-domain grouping, and carriers without credentials.",
                _closed_object({}, []),
            ),
            (
                "prepare_task_candidate",
                "Prepare a non-executing task candidate",
                "Create an in-memory, hash-bound candidate for one allowlisted observation; execution is false.",
                _closed_object(
                    {
                        "node_id": node_property,
                        "task_kind": {"type": "string", "enum": sorted(TASK_KINDS)},
                        "target_ref": {
                            "type": "string",
                            "enum": sorted(set(node_ids + service_ids + ["sanitized_topology"])),
                        },
                        "parameters": task_parameters_schema,
                    },
                    ["node_id", "task_kind", "target_ref", "parameters"],
                ),
            ),
            (
                "prepare_authorization_request",
                "Prepare a non-authoritative authorization request",
                "Create an in-memory, single-use/TTL contract candidate with rollback and stop conditions; no credential or authority is issued.",
                _closed_object(
                    {
                        "task_candidate_id": {
                            "type": "string",
                            "pattern": "^taskcand-[a-z0-9-]{1,54}$",
                        },
                        "task_hash": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                        "ttl_seconds": {
                            "type": "integer",
                            "minimum": AUTH_TTL_MIN_SECONDS,
                            "maximum": AUTH_TTL_MAX_SECONDS,
                        },
                        "rollback_condition_id": {
                            "type": "string",
                            "enum": sorted(ROLLBACK_CONDITIONS),
                        },
                        "stop_condition_id": {
                            "type": "string",
                            "enum": sorted(STOP_CONDITIONS),
                        },
                    },
                    [
                        "task_candidate_id",
                        "task_hash",
                        "ttl_seconds",
                        "rollback_condition_id",
                        "stop_condition_id",
                    ],
                ),
            ),
        ]
        return [
            {
                "name": name,
                "title": title,
                "description": description,
                "inputSchema": input_schema,
                "outputSchema": _OUTPUT_SCHEMA,
                "annotations": {
                    **annotations,
                    "readOnlyHint": not name.startswith("prepare_"),
                },
            }
            for name, title, description, input_schema in definitions
        ]

    def call_tool(self, name: Any, arguments: Any) -> dict[str, Any]:
        if not isinstance(name, str) or name not in TOOL_NAMES:
            raise PolicyDenied("DENY_UNKNOWN_TOOL", "The tool is not allowlisted.")
        if not isinstance(arguments, Mapping):
            raise PolicyDenied("DENY_SCHEMA", "Tool arguments must be an object.")
        clean_arguments = dict(arguments)
        return self.runtime.execute(
            name,
            clean_arguments,
            lambda: self._validated_handler(name, clean_arguments),
        )

    def to_mcp_structured_content(self, envelope: Mapping[str, Any]) -> dict[str, Any]:
        result_json = _canonical(envelope["result"]).decode("utf-8")
        return {
            "status": str(envelope["status"]),
            "state_field_status": str(envelope["state"]["fusion"]["status"]),
            "adi_index_status": "NON_EXECUTABLE",
            "packet_ref": str(envelope["packet"]["packet_ref"]),
            "content_sha256": str(envelope["hash"]),
            "result_json": result_json,
        }

    def _validated_handler(self, name: str, arguments: dict[str, Any]) -> Callable[[], dict[str, Any]]:
        if name == "list_nodes":
            validate_exact_keys(arguments, set())
            return lambda: {"nodes": self.inventory.list_nodes()}
        if name == "get_state_field_topology":
            validate_exact_keys(arguments, set())
            return self.inventory.topology
        if name in {"get_node_health", "get_compute_capability"}:
            validate_exact_keys(arguments, {"node_id"})
            node_id = validate_identifier(arguments["node_id"], "node_id")
            self.inventory.node(node_id)
            if name == "get_node_health":
                return lambda: self.inventory.get_node_health(node_id)
            return lambda: self.inventory.get_compute_capability(node_id)
        if name == "get_service_status":
            validate_exact_keys(arguments, {"node_id", "service_id"})
            node_id = validate_identifier(arguments["node_id"], "node_id")
            service_id = validate_identifier(arguments["service_id"], "service_id")
            self.inventory.service(node_id, service_id)
            return lambda: self.inventory.get_service_status(node_id, service_id)
        if name == "read_bounded_logs":
            validate_exact_keys(arguments, {"node_id", "service_id", "lines", "since_seconds"})
            node_id = validate_identifier(arguments["node_id"], "node_id")
            service_id = validate_identifier(arguments["service_id"], "service_id")
            lines = validate_integer(arguments["lines"], "lines", 1, MAX_LOG_LINES)
            since_seconds = validate_integer(
                arguments["since_seconds"], "since_seconds", 1, MAX_LOG_AGE_SECONDS
            )
            self.inventory.service(node_id, service_id)
            return lambda: self.inventory.read_bounded_logs(
                node_id, service_id, lines, since_seconds
            )
        if name == "prepare_task_candidate":
            validate_exact_keys(
                arguments, {"node_id", "task_kind", "target_ref", "parameters"}
            )
            node_id, task_kind, target_ref, parameters = self._validate_task_basis(arguments)
            self._require_task_capacity()
            return lambda: self._prepare_task_candidate(
                node_id, task_kind, target_ref, parameters
            )
        validate_exact_keys(
            arguments,
            {
                "task_candidate_id",
                "task_hash",
                "ttl_seconds",
                "rollback_condition_id",
                "stop_condition_id",
            },
        )
        candidate_id = validate_identifier(
            arguments["task_candidate_id"], "task_candidate_id"
        )
        task_hash = validate_sha256(arguments["task_hash"], "task_hash")
        ttl = validate_integer(
            arguments["ttl_seconds"],
            "ttl_seconds",
            AUTH_TTL_MIN_SECONDS,
            AUTH_TTL_MAX_SECONDS,
        )
        rollback = require_enum(
            arguments["rollback_condition_id"],
            "rollback_condition_id",
            ROLLBACK_CONDITIONS,
        )
        stop = require_enum(
            arguments["stop_condition_id"], "stop_condition_id", STOP_CONDITIONS
        )
        record = self._require_live_task_candidate(candidate_id, task_hash, ttl)
        return lambda: self._prepare_authorization_request(
            record, ttl, rollback, stop
        )

    def _validate_task_basis(
        self, arguments: Mapping[str, Any]
    ) -> tuple[str, str, str, dict[str, int]]:
        node_id = validate_identifier(arguments["node_id"], "node_id")
        self.inventory.node(node_id)
        task_kind = require_enum(arguments["task_kind"], "task_kind", set(TASK_KINDS))
        target_ref = validate_identifier(arguments["target_ref"], "target_ref")
        raw_parameters = arguments["parameters"]
        if not isinstance(raw_parameters, Mapping):
            raise PolicyDenied("DENY_SCHEMA", "parameters must be a closed object.")
        parameters: dict[str, int] = {}
        if task_kind in {"observe_node_health", "observe_compute_capability"}:
            if target_ref != node_id:
                raise PolicyDenied("DENY_TASK_BINDING", "The task target does not match the node.")
            validate_exact_keys(raw_parameters, set())
        elif task_kind in {"observe_service_status", "observe_bounded_logs"}:
            service = self.inventory.service(node_id, target_ref)
            if task_kind == "observe_bounded_logs" and service.get("log_file") is None:
                raise PolicyDenied("DENY_PROTECTED_RESOURCE", "The task targets a protected log source.")
            if task_kind == "observe_bounded_logs":
                validate_exact_keys(raw_parameters, {"lines", "since_seconds"})
                parameters = {
                    "lines": validate_integer(
                        raw_parameters["lines"], "lines", 1, MAX_LOG_LINES
                    ),
                    "since_seconds": validate_integer(
                        raw_parameters["since_seconds"],
                        "since_seconds",
                        1,
                        MAX_LOG_AGE_SECONDS,
                    ),
                }
            else:
                validate_exact_keys(raw_parameters, set())
        elif target_ref != "sanitized_topology":
            raise PolicyDenied("DENY_TASK_BINDING", "The topology target is not allowlisted.")
        else:
            validate_exact_keys(raw_parameters, set())
        return node_id, task_kind, target_ref, parameters

    def _task_basis(
        self, node_id: str, task_kind: str, target_ref: str, parameters: Mapping[str, int]
    ) -> dict[str, Any]:
        return {
            "node_id": node_id,
            "task_kind": task_kind,
            "target_ref": target_ref,
            "parameters": dict(parameters),
            "capability_tool": TASK_KINDS[task_kind],
            "execution_mode": "CANDIDATE_ONLY_NO_EXECUTION",
        }

    def _prepare_task_candidate(
        self,
        node_id: str,
        task_kind: str,
        target_ref: str,
        parameters: Mapping[str, int],
    ) -> dict[str, Any]:
        issued_at = self._clock().astimezone(UTC)
        expires_at = issued_at + timedelta(seconds=AUTH_TTL_MAX_SECONDS)
        with self._registry_lock:
            self._prune_expired_candidates_locked(issued_at)
            if len(self._task_candidates) >= MAX_TASK_CANDIDATES:
                raise PolicyDenied(
                    "DENY_RESOURCE_LIMIT", "The in-memory candidate registry is full."
                )
            self._candidate_sequence += 1
            candidate_id = (
                f"taskcand-{issued_at.strftime('%Y%m%dt%H%M%Sz').lower()}-"
                f"{self._candidate_sequence:08x}"
            )
            basis = self._task_basis(node_id, task_kind, target_ref, parameters)
            hash_basis = {
                "candidate_id": candidate_id,
                "task_basis": basis,
                "issued_at": issued_at.isoformat().replace("+00:00", "Z"),
                "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
            }
            task_hash = hashlib.sha256(_canonical(hash_basis)).hexdigest()
            self._task_candidates[candidate_id] = TaskCandidateRecord(
                candidate_id=candidate_id,
                task_hash=task_hash,
                task_basis=basis,
                issued_at=issued_at,
                expires_at=expires_at,
            )
        return {
            "status": "CANDIDATE_ONLY",
            "candidate_id": candidate_id,
            "task_basis": basis,
            "task_hash": task_hash,
            "issued_at": issued_at.isoformat().replace("+00:00", "Z"),
            "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
            "execution_allowed": False,
            "remote_connection_attempted": False,
            "persistence": "PROCESS_MEMORY_ONLY_NO_EXTERNAL_WRITE",
        }

    def _prune_expired_candidates_locked(self, now: datetime) -> None:
        expired = [
            candidate_id
            for candidate_id, record in self._task_candidates.items()
            if now >= record.expires_at
        ]
        for candidate_id in expired:
            self._task_candidates.pop(candidate_id, None)
            self._authorization_prepared.discard(candidate_id)

    def _require_task_capacity(self) -> None:
        now = self._clock().astimezone(UTC)
        with self._registry_lock:
            self._prune_expired_candidates_locked(now)
            if len(self._task_candidates) >= MAX_TASK_CANDIDATES:
                raise PolicyDenied(
                    "DENY_RESOURCE_LIMIT", "The in-memory candidate registry is full."
                )

    def _require_live_task_candidate(
        self, candidate_id: str, task_hash: str, ttl_seconds: int
    ) -> TaskCandidateRecord:
        now = self._clock().astimezone(UTC)
        with self._registry_lock:
            record = self._task_candidates.get(candidate_id)
            if record is None or record.task_hash != task_hash:
                raise PolicyDenied(
                    "DENY_TASK_BINDING",
                    "The authorization candidate is not bound to a live task candidate.",
                )
            if candidate_id in self._authorization_prepared:
                raise PolicyDenied(
                    "DENY_REPLAY", "The task candidate already produced an authorization request."
                )
            if now >= record.expires_at:
                raise PolicyDenied("DENY_TASK_EXPIRED", "The task candidate has expired.")
            if now + timedelta(seconds=ttl_seconds) > record.expires_at:
                raise PolicyDenied(
                    "DENY_TTL_EXCEEDS_TASK",
                    "The authorization TTL exceeds the task candidate lifetime.",
                )
            return record

    def _prepare_authorization_request(
        self,
        record: TaskCandidateRecord,
        ttl_seconds: int,
        rollback: str,
        stop: str,
    ) -> dict[str, Any]:
        issued_at = self._clock().astimezone(UTC)
        expires_at = issued_at + timedelta(seconds=ttl_seconds)
        target = {
            "node_id": record.task_basis["node_id"],
            "task_kind": record.task_basis["task_kind"],
            "target_ref": record.task_basis["target_ref"],
            "parameters": record.task_basis["parameters"],
        }
        request_basis = {
            "task_candidate_id": record.candidate_id,
            "task_hash": record.task_hash,
            "target": target,
            "issued_at": issued_at.isoformat().replace("+00:00", "Z"),
            "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
            "rollback_condition_id": rollback,
            "stop_condition_id": stop,
        }
        request_hash = hashlib.sha256(_canonical(request_basis)).hexdigest()
        with self._registry_lock:
            current = self._task_candidates.get(record.candidate_id)
            if (
                current != record
                or record.candidate_id in self._authorization_prepared
                or issued_at >= record.expires_at
                or expires_at > record.expires_at
            ):
                raise PolicyDenied(
                    "DENY_REPLAY", "The task candidate is no longer usable for authorization."
                )
            self._authorization_prepared.add(record.candidate_id)
        return {
            "status": "CANDIDATE_NOT_AUTHORITY",
            "authorization_request_id": f"authcand-{request_hash[:20]}",
            "request_hash": request_hash,
            "task_candidate_id": record.candidate_id,
            "task_hash": record.task_hash,
            "target": target,
            "issued_at": request_basis["issued_at"],
            "expires_at": request_basis["expires_at"],
            "ttl_seconds": ttl_seconds,
            "rollback_condition_id": rollback,
            "stop_condition_id": stop,
            "single_use": True,
            "max_uses": 1,
            "single_use_enforced_scope": "PROCESS_MEMORY_CANDIDATE_ONLY",
            "exactly_once_enforced": False,
            "consumer_present": False,
            "authority_effect": "NONE",
            "execution_allowed": False,
            "credential_issued": False,
            "persistence": "PROCESS_MEMORY_ONLY_NO_EXTERNAL_WRITE",
        }
