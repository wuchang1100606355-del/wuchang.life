"""Executable 8D state-field runtime and non-executable ADI index.

The eight dimensions below are programs with activation conditions and evaluators.
ADI is produced afterwards as an index over coordinates and evidence; it never
contains a callable, handler, command, or activation authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from .errors import GatewayError, PolicyDenied
from .policy import validate_no_prohibited_input
from .redaction import redact_object

Clock = Callable[[], datetime]
Handler = Callable[[], dict[str, Any]]
PolicyGate = Callable[[], Handler]
Activation = Callable[[str, Mapping[str, Any]], bool]
Evaluator = Callable[[str, Mapping[str, Any]], dict[str, Any]]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def classify_8d_definition(value: Any) -> str:
    """Detect a fixed D1-D8 projection without changing the inspected value."""

    if not isinstance(value, Mapping):
        return "NOT_AN_8D_DEFINITION"
    normalized = {str(key).split("_", 1)[0].upper() for key in value}
    static_dimensions = {f"D{index}" for index in range(1, 9)}
    if static_dimensions.issubset(normalized):
        return "TECHNICAL_DEFINITION_DRIFT"
    if value.get("definition") == "EXECUTABLE_DYNAMIC_DIMENSION_PROGRAMS":
        return "RUNTIME_OS_DEFINITION"
    return "UNCLASSIFIED_8D_DEFINITION"


@dataclass(frozen=True)
class DimensionProgram:
    """One executable state-field dimension with a dynamic activation rule."""

    name: str
    capability: str
    activation: Activation
    evaluator: Evaluator


class StateFieldRuntime:
    """Execute, fuse, govern, and packetize a bounded tool state transition."""

    def __init__(self, clock: Clock = _utc_now) -> None:
        self._clock = clock
        self._programs = self._build_programs()
        self._decision_lock = Lock()
        self._last_decision: dict[str, Any] = {
            "decision": "NOT_RUN",
            "adapter_invoked": False,
        }

    @property
    def dimension_names(self) -> tuple[str, ...]:
        return tuple(program.name for program in self._programs)

    @property
    def last_decision(self) -> dict[str, Any]:
        """Return a non-sensitive process-local audit projection for tests and diagnostics."""

        with self._decision_lock:
            return dict(self._last_decision)

    def _record_decision(
        self, tool: str, decision: str, adapter_invoked: bool, policy_code: str | None
    ) -> None:
        with self._decision_lock:
            self._last_decision = {
                "tool": tool,
                "decision": decision,
                "adapter_invoked": adapter_invoked,
                "policy_code": policy_code,
            }

    def _build_programs(self) -> tuple[DimensionProgram, ...]:
        always: Activation = lambda _tool, _args: True
        target_bound: Activation = lambda _tool, args: any(
            key in args for key in ("node_id", "service_id", "target_ref")
        )
        resource_bound: Activation = lambda tool, _args: tool not in {
            "list_nodes",
            "get_state_field_topology",
        }
        time_bound: Activation = lambda tool, _args: tool in {
            "read_bounded_logs",
            "prepare_task_candidate",
            "prepare_authorization_request",
        }
        return (
            DimensionProgram("identity", "bind_local_principal", always, self._identity),
            DimensionProgram("intent", "classify_bounded_goal", always, self._intent),
            DimensionProgram("authority", "enforce_candidate_boundary", always, self._authority),
            DimensionProgram("relation", "bind_allowlisted_target", target_bound, self._relation),
            DimensionProgram("resource", "apply_compute_and_output_budget", resource_bound, self._resource),
            DimensionProgram("time", "apply_window_ttl_and_freshness", time_bound, self._time),
            DimensionProgram("risk", "reject_untrusted_input_shapes", always, self._risk),
            DimensionProgram("governance", "fuse_fail_closed_decision", always, self._governance),
        )

    def _identity(self, tool: str, _arguments: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "principal_class": "LOCAL_LOOPBACK_CANDIDATE_CLIENT",
            "identity_authority": "NOT_ESTABLISHED",
            "tool_scope": tool,
        }

    def _intent(self, tool: str, _arguments: Mapping[str, Any]) -> dict[str, Any]:
        kind = "CANDIDATE_PREPARATION" if tool.startswith("prepare_") else "READ_ONLY_OBSERVATION"
        return {"intent_class": kind, "arbitrary_execution": False}

    def _authority(self, tool: str, _arguments: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "decision_scope": "LOCAL_CANDIDATE_ONLY",
            "formal_authority_effect": "NONE",
            "execution_allowed": False if tool.startswith("prepare_") else None,
        }

    def _relation(self, _tool: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        refs = {
            key: arguments[key]
            for key in ("node_id", "service_id", "target_ref")
            if key in arguments
        }
        return {"target_refs": refs, "relation_source": "FIXED_ALLOWLIST"}

    def _resource(self, tool: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "backend_class": "LOCAL_SAFE_ADAPTER_OR_STATIC_EVIDENCE",
            "line_budget": arguments.get("lines"),
            "network_scope": "LOOPBACK_ONLY",
            "tool_scope": tool,
        }

    def _time(self, tool: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "window_seconds": arguments.get("since_seconds"),
            "ttl_seconds": arguments.get("ttl_seconds"),
            "clock": "UTC",
            "tool_scope": tool,
        }

    def _risk(self, _tool: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        validate_no_prohibited_input(arguments)
        return {
            "input_policy": "PASS",
            "shell_surface": "ABSENT",
            "protected_resource_access": "ABSENT",
        }

    def _governance(self, tool: str, _arguments: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "decision_rule": "ALL_ACTIVE_PROGRAMS_AND_AUTHORITY_GATE_MUST_PASS",
            "canonical_effect": "NONE",
            "land_effect": "NONE",
            "tool_scope": tool,
        }

    def execute(
        self, tool: str, arguments: Mapping[str, Any], policy_gate: PolicyGate
    ) -> dict[str, Any]:
        """Fuse active programs, require governance approval, then invoke one adapter."""

        activated_at = self._clock().astimezone(UTC)
        activation = {
            program.name: bool(program.activation(tool, arguments)) for program in self._programs
        }
        outputs: dict[str, dict[str, Any]] = {}
        transitions: dict[str, str] = {}
        denial: GatewayError | None = None

        # Evaluate every ordinary capability program first. Risk is therefore a
        # real pre-adapter gate even though canonical output ordering remains stable.
        for program in self._programs:
            if program.name in {"authority", "governance"}:
                continue
            if not activation[program.name]:
                outputs[program.name] = {"reason": "ACTIVATION_CONDITION_NOT_MET"}
                transitions[program.name] = "INACTIVE_STABLE"
                continue
            try:
                outputs[program.name] = program.evaluator(tool, arguments)
                transitions[program.name] = "ELIGIBLE_TO_ACTIVE"
            except GatewayError as exc:
                denial = denial or exc
                outputs[program.name] = {"decision": "DENY", "policy_code": exc.code}
                transitions[program.name] = "POLICY_DENIED"
            except Exception:
                denial = denial or PolicyDenied(
                    "DENY_STATE_PROGRAM_FAILURE",
                    "A state-field capability program failed closed.",
                )
                outputs[program.name] = {
                    "decision": "DENY",
                    "policy_code": "DENY_STATE_PROGRAM_FAILURE",
                }
                transitions[program.name] = "POLICY_DENIED"

        handler: Handler | None = None
        authority_program = next(
            program for program in self._programs if program.name == "authority"
        )
        if denial is not None:
            outputs["authority"] = {
                **authority_program.evaluator(tool, arguments),
                "policy_gate": "SKIPPED_PREREQUISITE_DENIAL",
            }
            transitions["authority"] = "POLICY_DENIED"
        else:
            try:
                # Closed-schema, allowlist, target, and candidate-binding checks
                # execute here, inside the Authority dimension.
                handler = policy_gate()
                outputs["authority"] = {
                    **authority_program.evaluator(tool, arguments),
                    "policy_gate": "PASS",
                }
                transitions["authority"] = "ELIGIBLE_TO_ACTIVE"
            except GatewayError as exc:
                denial = exc
                outputs["authority"] = {
                    **authority_program.evaluator(tool, arguments),
                    "policy_gate": "DENY",
                    "policy_code": exc.code,
                }
                transitions["authority"] = "POLICY_DENIED"
            except Exception:
                denial = PolicyDenied(
                    "DENY_POLICY_GATE_FAILURE", "The authority policy gate failed closed."
                )
                outputs["authority"] = {
                    **authority_program.evaluator(tool, arguments),
                    "policy_gate": "DENY",
                    "policy_code": "DENY_POLICY_GATE_FAILURE",
                }
                transitions["authority"] = "POLICY_DENIED"

        governance_program = next(
            program for program in self._programs if program.name == "governance"
        )
        governance_output = governance_program.evaluator(tool, arguments)
        if denial is None and handler is not None:
            governance_output.update(
                {
                    "decision": "ALLOW_BOUNDED_LOCAL_CALL",
                    "all_active_programs_passed": True,
                    "adapter_gate": "OPEN_ONCE",
                }
            )
            transitions["governance"] = "FUSED_ALLOW"
        else:
            if denial is None:
                denial = PolicyDenied(
                    "DENY_NO_BOUNDED_ADAPTER", "No bounded adapter passed governance."
                )
            governance_output.update(
                {
                    "decision": "DENY",
                    "all_active_programs_passed": False,
                    "adapter_gate": "CLOSED",
                    "policy_code": denial.code,
                }
            )
            transitions["governance"] = "FUSED_DENY"
        outputs["governance"] = governance_output

        dimension_states = [
            {
                "dimension": program.name,
                "program": program.capability,
                "state": "ACTIVE" if activation[program.name] else "INACTIVE",
                "transition": transitions[program.name],
                "output": outputs[program.name],
            }
            for program in self._programs
        ]
        active_names = [
            program.name for program in self._programs if activation[program.name]
        ]
        if denial is not None:
            self._record_decision(tool, "DENY", False, denial.code)
            raise denial
        if handler is None:
            self._record_decision(tool, "DENY", False, "DENY_NO_BOUNDED_ADAPTER")
            raise PolicyDenied(
                "DENY_NO_BOUNDED_ADAPTER", "No bounded adapter passed governance."
            )

        self._record_decision(tool, "ALLOW", False, None)
        try:
            raw_result = handler()
        except GatewayError as exc:
            self._record_decision(tool, "DENY_BACKEND", True, exc.code)
            raise
        except Exception as exc:
            self._record_decision(tool, "DENY_BACKEND", True, "BACKEND_NOT_OBSERVED")
            raise GatewayError(
                "BACKEND_NOT_OBSERVED", "The bounded backend failed safely."
            ) from exc
        self._record_decision(tool, "ALLOW", True, None)
        safe_result = redact_object(raw_result)
        completed_at = self._clock().astimezone(UTC)
        state = {
            "runtime": "W7TP_8D_STATE_FIELD_RUNTIME_OS_CANDIDATE",
            "definition": "EXECUTABLE_DYNAMIC_DIMENSION_PROGRAMS",
            "active_dimensions": active_names,
            "dimension_states": dimension_states,
            "fusion": {
                "status": "FUSED",
                "rule": "ALL_ACTIVE_PROGRAMS_AND_AUTHORITY_GATE_PASS_BEFORE_ADAPTER",
                "result_class": "CANDIDATE" if tool.startswith("prepare_") else "READ_ONLY",
            },
        }
        adi_index = {
            "definition": "NON_EXECUTABLE_COORDINATE_RELATION_DECISION_TRANSITION_TIME_SPACE_EVIDENCE_INDEX",
            "coordinate": {"tool": tool, "scope": "msi-wsl-loopback"},
            "relation": [
                {"kind": "targets", "ref": arguments[key]}
                for key in ("node_id", "service_id", "target_ref")
                if key in arguments
            ],
            "decision": ["ALLOW_BOUNDED_LOCAL_CALL", "NO_FORMAL_AUTHORITY_EFFECT"],
            "transition": [
                {"dimension": item["dimension"], "transition": item["transition"]}
                for item in dimension_states
            ],
            "time": {
                "activated_at": activated_at.isoformat().replace("+00:00", "Z"),
                "completed_at": completed_at.isoformat().replace("+00:00", "Z"),
            },
            "space": {"network_zone": "127.0.0.1", "remote_execution": False},
            "evidence": ["fixed_allowlist", "runtime_policy", "bounded_adapter_result"],
            "callable_present": False,
            "activation_authority": False,
        }
        hash_basis = {"state": state, "coordinate": adi_index, "result": safe_result}
        digest = hashlib.sha256(_canonical_json(hash_basis)).hexdigest()
        packet = {
            "packet_ref": f"candidate:{digest[:24]}",
            "manifest_index": "RUNTIME_RESPONSE_NOT_FORMAL_MANIFEST",
            "delta": "BOUNDED_OBSERVATION_OR_IN_MEMORY_CANDIDATE",
            "hash": {"algorithm": "SHA-256", "value": digest},
            "sandbox": "LOCAL_LOOPBACK_ONLY",
            "validate": "PASS",
            "land": "NOT_REQUESTED_CANDIDATE_ONLY",
            "sequence": "State->Coordinate->Hash->Packet",
        }
        return {
            "status": "PASS_CANDIDATE_ONLY",
            "state": state,
            "coordinate": adi_index,
            "hash": digest,
            "packet": packet,
            "result": safe_result,
        }
