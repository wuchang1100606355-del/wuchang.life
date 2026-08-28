"""Fail-closed canary-only container and system-service action adapters."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from w7tp_gt_mesh.core import MeshHold, require_core


_CANARY_NAME = re.compile(r"^w7tp-canary-[a-z0-9][a-z0-9_.-]{0,62}$")
_CANARY_UNIT = re.compile(r"^w7tp-canary-[a-z0-9][a-z0-9_.-]{0,62}\.service$")
_IMMUTABLE_IMAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:~-]{0,255}@sha256:[0-9a-f]{64}$")
_EXACT_CONTAINER_ID = re.compile(r"^[0-9a-f]{64}$")
_STATE_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SENSITIVE_PARAMETER = re.compile(r"(?:secret|password|credential|private[_-]?key|token)", re.IGNORECASE)

CONTAINER_OPERATIONS = {
    "container_inspect_canary",
    "container_start_canary",
    "container_stop_canary",
    "container_run_canary",
    "container_remove_canary",
}
SERVICE_OPERATIONS = {
    "service_inspect_canary",
    "service_start_canary",
    "service_stop_canary",
}
EXISTING_CONTAINER_OPERATIONS = {
    "container_inspect_existing",
    "container_start_existing",
    "container_stop_existing",
    "container_remove_existing",
}
ALL_OPERATIONS = CONTAINER_OPERATIONS | EXISTING_CONTAINER_OPERATIONS | SERVICE_OPERATIONS


@dataclass(frozen=True, slots=True)
class RunnerResult:
    returncode: int
    stdout: str
    stderr: str = ""


Runner = Callable[[Sequence[str], int], RunnerResult]


def subprocess_runner(argv: Sequence[str], timeout_seconds: int) -> RunnerResult:
    try:
        result = subprocess.run(
            list(argv),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            shell=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        del exc
        return RunnerResult(127, "", "ADAPTER_EXECUTION_UNAVAILABLE")
    return RunnerResult(result.returncode, result.stdout[:65536], result.stderr[:4096])


def _assert_no_sensitive_keys(value: object) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str) or _SENSITIVE_PARAMETER.search(key):
                raise MeshHold("HOLD_CONTROL_SENSITIVE_PARAMETER_FORBIDDEN")
            _assert_no_sensitive_keys(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_sensitive_keys(child)


class CanaryPolicy:
    """Default-deny policy that can mutate only explicitly dedicated canaries."""

    def __init__(
        self,
        *,
        allowed_image_refs: Sequence[str] = (),
        allowed_existing_container_ids: Sequence[str] = (),
        manage_existing_scope_authorized: bool = False,
    ) -> None:
        self.allowed_image_refs = frozenset(allowed_image_refs)
        self.allowed_existing_container_ids = frozenset(allowed_existing_container_ids)
        self.manage_existing_scope_authorized = manage_existing_scope_authorized is True
        if any(not _IMMUTABLE_IMAGE.fullmatch(item) for item in self.allowed_image_refs):
            raise MeshHold("HOLD_CANARY_IMAGE_ALLOWLIST_INVALID")
        if any(not _EXACT_CONTAINER_ID.fullmatch(item) for item in self.allowed_existing_container_ids):
            raise MeshHold("HOLD_EXISTING_CONTAINER_ALLOWLIST_INVALID")

    def validate(self, operation: object, parameters: object) -> None:
        if operation not in ALL_OPERATIONS or not isinstance(parameters, Mapping):
            raise MeshHold("HOLD_CONTROL_OPERATION_NOT_ALLOWED")
        _assert_no_sensitive_keys(parameters)
        if operation in EXISTING_CONTAINER_OPERATIONS:
            engine = parameters.get("engine")
            container_id = parameters.get("container_id")
            state_hash = parameters.get("current_state_sha256")
            if engine not in {"docker", "podman"}:
                raise MeshHold("HOLD_CONTAINER_ENGINE_INVALID")
            if not isinstance(container_id, str) or not _EXACT_CONTAINER_ID.fullmatch(container_id):
                raise MeshHold("HOLD_EXACT_CONTAINER_ID_REQUIRED")
            if not isinstance(state_hash, str) or not _STATE_SHA256.fullmatch(state_hash):
                raise MeshHold("HOLD_CONTAINER_CURRENT_STATE_HASH_REQUIRED")
            if not self.manage_existing_scope_authorized:
                raise MeshHold("HOLD_MANAGE_EXISTING_CONTAINER_NOT_AUTHORIZED")
            if container_id not in self.allowed_existing_container_ids:
                raise MeshHold("HOLD_EXISTING_CONTAINER_NOT_ALLOWLISTED")
        elif operation in CONTAINER_OPERATIONS:
            name = parameters.get("name")
            engine = parameters.get("engine")
            if not isinstance(name, str) or not _CANARY_NAME.fullmatch(name):
                raise MeshHold("HOLD_CANARY_CONTAINER_NAME_REQUIRED")
            if engine not in {"docker", "podman"}:
                raise MeshHold("HOLD_CONTAINER_ENGINE_INVALID")
            if operation == "container_run_canary":
                image_ref = parameters.get("image_ref")
                if (
                    not isinstance(image_ref, str)
                    or not _IMMUTABLE_IMAGE.fullmatch(image_ref)
                    or image_ref not in self.allowed_image_refs
                ):
                    raise MeshHold("HOLD_CANARY_IMAGE_NOT_ALLOWLISTED")
                command = parameters.get("command", [])
                if (
                    not isinstance(command, list)
                    or len(command) > 32
                    or not all(isinstance(item, str) and 0 < len(item) <= 1024 for item in command)
                ):
                    raise MeshHold("HOLD_CANARY_COMMAND_INVALID")
                limits = parameters.get("resource_limits")
                if not isinstance(limits, Mapping):
                    raise MeshHold("HOLD_CONTAINER_RESOURCE_LIMITS_REQUIRED")
                required_integer_limits = {
                    "cpu_count": (1, 65536),
                    "ram_bytes": (1, 2**63 - 1),
                    "gpu_count": (0, 1024),
                    "gpu_memory_mib": (0, 2**31 - 1),
                    "pids_limit": (1, 4096),
                }
                for key, (minimum, maximum) in required_integer_limits.items():
                    value = limits.get(key)
                    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
                        raise MeshHold("HOLD_CONTAINER_RESOURCE_LIMITS_INVALID")
                if limits.get("container_engine") != engine:
                    raise MeshHold("HOLD_CONTAINER_RESOURCE_ENGINE_MISMATCH")
        else:
            unit = parameters.get("unit")
            scope = parameters.get("scope", "system")
            if not isinstance(unit, str) or not _CANARY_UNIT.fullmatch(unit):
                raise MeshHold("HOLD_CANARY_SERVICE_NAME_REQUIRED")
            if scope not in {"system", "user"}:
                raise MeshHold("HOLD_SERVICE_SCOPE_INVALID")


class ContainerCanaryAdapter:
    _INSPECT_FORMAT = (
        '{"id":{{json .Id}},"name":{{json .Name}},"image":{{json .Config.Image}},'
        '"state":{{json .State.Status}},"canary":{{json (index .Config.Labels "w7tp.role")}},'
        '"control":{{json (index .Config.Labels "w7tp.total_field_control")}}}'
    )

    def __init__(self, policy: CanaryPolicy, *, runner: Runner = subprocess_runner) -> None:
        self.policy = policy
        self.runner = runner

    def _run(self, argv: Sequence[str], *, allow_absent: bool = False) -> RunnerResult:
        result = self.runner(tuple(argv), 60)
        if result.returncode != 0 and not allow_absent:
            raise MeshHold("HOLD_CONTAINER_ADAPTER_COMMAND_FAILED")
        return result

    def inspect(self, engine: str, name: str, *, allow_absent: bool = False) -> dict[str, object] | None:
        result = self._run([engine, "inspect", "--format", self._INSPECT_FORMAT, name], allow_absent=allow_absent)
        if result.returncode != 0:
            return None
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise MeshHold("HOLD_CONTAINER_INSPECT_INVALID") from exc
        if not isinstance(parsed, dict):
            raise MeshHold("HOLD_CONTAINER_INSPECT_INVALID")
        if parsed.get("canary") != "canary" or parsed.get("control") != "true":
            raise MeshHold("HOLD_CONTAINER_CANARY_LABELS_REQUIRED")
        return {
            "container_id": str(parsed.get("id") or "UNKNOWN"),
            "name": str(parsed.get("name") or name).lstrip("/"),
            "image_ref": str(parsed.get("image") or "UNKNOWN"),
            "state": str(parsed.get("state") or "UNKNOWN"),
            "canary_labels_verified": True,
        }

    def execute(self, operation: str, parameters: Mapping[str, object]) -> dict[str, object]:
        self.policy.validate(operation, parameters)
        engine = str(parameters["engine"])
        name = str(parameters["name"])
        if operation == "container_inspect_canary":
            inspected = self.inspect(engine, name)
            return {"operation": operation, "state": "OBSERVED", "container": inspected}
        if operation == "container_run_canary":
            image_ref = str(parameters["image_ref"])
            command = [str(item) for item in parameters.get("command", [])]
            limits = parameters["resource_limits"]
            assert isinstance(limits, Mapping)
            argv = [
                engine,
                "run",
                "--detach",
                "--name",
                name,
                "--label",
                "w7tp.role=canary",
                "--label",
                "w7tp.total_field_control=true",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--network",
                "none",
                "--cpus",
                str(limits["cpu_count"]),
                "--memory",
                str(limits["ram_bytes"]),
                "--memory-swap",
                str(limits["ram_bytes"]),
                "--pids-limit",
                str(limits["pids_limit"]),
                "--label",
                f"w7tp.resource.gpu_memory_mib={limits['gpu_memory_mib']}",
            ]
            if int(limits["gpu_count"]) > 0:
                argv.extend(["--gpus", str(limits["gpu_count"])])
            argv.extend(
                [
                image_ref,
                *command,
                ]
            )
            result = self._run(argv)
            return {"operation": operation, "state": "EXECUTED", "result_id": result.stdout.strip()[:128]}
        inspected = self.inspect(engine, name)
        if inspected is None:
            raise MeshHold("HOLD_CANARY_CONTAINER_NOT_FOUND")
        if operation == "container_start_canary":
            self._run([engine, "start", name])
        elif operation == "container_stop_canary":
            self._run([engine, "stop", "--time", "10", name])
        elif operation == "container_remove_canary":
            if inspected.get("state") == "running":
                raise MeshHold("HOLD_CANARY_REMOVE_REQUIRES_STOPPED")
            self._run([engine, "rm", name])
        else:
            raise MeshHold("HOLD_CONTROL_OPERATION_NOT_ALLOWED")
        return {"operation": operation, "state": "EXECUTED", "container": inspected}

    def verify(self, operation: str, parameters: Mapping[str, object]) -> dict[str, object]:
        self.policy.validate(operation, parameters)
        engine = str(parameters["engine"])
        name = str(parameters["name"])
        inspected = self.inspect(engine, name, allow_absent=operation == "container_remove_canary")
        if operation == "container_remove_canary":
            if inspected is not None:
                raise MeshHold("HOLD_CANARY_REMOVE_VERIFY_FAILED")
            return {"verification_state": "PASS_ABSENT", "name": name}
        if inspected is None:
            raise MeshHold("HOLD_CANARY_VERIFY_NOT_FOUND")
        state = inspected.get("state")
        if operation in {"container_run_canary", "container_start_canary"} and state != "running":
            raise MeshHold("HOLD_CANARY_RUNNING_VERIFY_FAILED")
        if operation == "container_stop_canary" and state == "running":
            raise MeshHold("HOLD_CANARY_STOP_VERIFY_FAILED")
        return {"verification_state": "PASS", "container": inspected}


class ExistingContainerAdapter:
    """Generic capability, disabled until D8 scope and exact-ID allowlist exist."""

    _INSPECT_FORMAT = ContainerCanaryAdapter._INSPECT_FORMAT

    def __init__(self, policy: CanaryPolicy, *, runner: Runner = subprocess_runner) -> None:
        self.policy = policy
        self.runner = runner

    def inspect(self, engine: str, container_id: str, *, allow_absent: bool = False) -> dict[str, object] | None:
        result = self.runner((engine, "inspect", "--format", self._INSPECT_FORMAT, container_id), 60)
        if result.returncode != 0:
            if allow_absent:
                return None
            raise MeshHold("HOLD_CONTAINER_ADAPTER_COMMAND_FAILED")
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise MeshHold("HOLD_CONTAINER_INSPECT_INVALID") from exc
        if not isinstance(parsed, dict) or parsed.get("id") != container_id:
            raise MeshHold("HOLD_EXACT_CONTAINER_ID_MISMATCH")
        record: dict[str, object] = {
            "container_id": container_id,
            "name": str(parsed.get("name") or "UNKNOWN").lstrip("/"),
            "image_ref": str(parsed.get("image") or "UNKNOWN"),
            "state": str(parsed.get("state") or "UNKNOWN"),
            "canary_label": parsed.get("canary"),
            "total_field_control_label": parsed.get("control"),
        }
        record["current_state_sha256"] = require_core().sha256_hex(
            require_core().canonical_json_bytes(record)
        )
        return record

    def _bound_current(self, parameters: Mapping[str, object]) -> tuple[str, str, dict[str, object]]:
        engine = str(parameters["engine"])
        container_id = str(parameters["container_id"])
        inspected = self.inspect(engine, container_id)
        assert inspected is not None
        if inspected.get("current_state_sha256") != parameters.get("current_state_sha256"):
            raise MeshHold("HOLD_CONTAINER_CURRENT_STATE_DRIFT")
        return engine, container_id, inspected

    def execute(self, operation: str, parameters: Mapping[str, object]) -> dict[str, object]:
        self.policy.validate(operation, parameters)
        engine, container_id, before = self._bound_current(parameters)
        if operation == "container_inspect_existing":
            return {"operation": operation, "state": "OBSERVED", "container": before}
        if operation == "container_remove_existing" and before.get("state") == "running":
            raise MeshHold("HOLD_EXISTING_CONTAINER_REMOVE_REQUIRES_STOPPED")
        verb = {
            "container_start_existing": "start",
            "container_stop_existing": "stop",
            "container_remove_existing": "rm",
        }.get(operation)
        if verb is None:
            raise MeshHold("HOLD_CONTROL_OPERATION_NOT_ALLOWED")
        argv = [engine, verb]
        if verb == "stop":
            argv.extend(["--time", "10"])
        argv.append(container_id)
        result = self.runner(tuple(argv), 60)
        if result.returncode != 0:
            raise MeshHold("HOLD_CONTAINER_ADAPTER_COMMAND_FAILED")
        return {"operation": operation, "state": "EXECUTED", "container_before": before}

    def verify(self, operation: str, parameters: Mapping[str, object]) -> dict[str, object]:
        self.policy.validate(operation, parameters)
        engine = str(parameters["engine"])
        container_id = str(parameters["container_id"])
        after = self.inspect(engine, container_id, allow_absent=operation == "container_remove_existing")
        if operation == "container_remove_existing":
            if after is not None:
                raise MeshHold("HOLD_EXISTING_CONTAINER_REMOVE_VERIFY_FAILED")
            return {"verification_state": "PASS_ABSENT", "container_id": container_id}
        if after is None:
            raise MeshHold("HOLD_EXISTING_CONTAINER_VERIFY_NOT_FOUND")
        if operation == "container_start_existing" and after.get("state") != "running":
            raise MeshHold("HOLD_EXISTING_CONTAINER_START_VERIFY_FAILED")
        if operation == "container_stop_existing" and after.get("state") == "running":
            raise MeshHold("HOLD_EXISTING_CONTAINER_STOP_VERIFY_FAILED")
        return {"verification_state": "PASS", "container": after}


class SystemCanaryServiceAdapter:
    def __init__(self, policy: CanaryPolicy, *, runner: Runner = subprocess_runner) -> None:
        self.policy = policy
        self.runner = runner

    @staticmethod
    def _prefix(scope: str) -> list[str]:
        return ["systemctl", "--user"] if scope == "user" else ["systemctl"]

    def inspect(self, unit: str, scope: str) -> dict[str, object]:
        result = self.runner(
            (*self._prefix(scope), "show", unit, "--no-pager", "--property=Id,LoadState,ActiveState,SubState,UnitFileState,MainPID"),
            30,
        )
        if result.returncode != 0:
            raise MeshHold("HOLD_SERVICE_ADAPTER_COMMAND_FAILED")
        values: dict[str, str] = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value
        if values.get("Id") != unit or values.get("LoadState") != "loaded":
            raise MeshHold("HOLD_CANARY_SERVICE_NOT_LOADED")
        return {
            "unit": unit,
            "scope": scope,
            "load_state": values.get("LoadState", "UNKNOWN"),
            "active_state": values.get("ActiveState", "UNKNOWN"),
            "sub_state": values.get("SubState", "UNKNOWN"),
            "unit_file_state": values.get("UnitFileState", "UNKNOWN"),
            "main_pid": int(values["MainPID"]) if values.get("MainPID", "").isdigit() else None,
        }

    def execute(self, operation: str, parameters: Mapping[str, object]) -> dict[str, object]:
        self.policy.validate(operation, parameters)
        unit = str(parameters["unit"])
        scope = str(parameters.get("scope", "system"))
        before = self.inspect(unit, scope)
        if operation == "service_inspect_canary":
            return {"operation": operation, "state": "OBSERVED", "service": before}
        verb = "start" if operation == "service_start_canary" else "stop" if operation == "service_stop_canary" else None
        if verb is None:
            raise MeshHold("HOLD_CONTROL_OPERATION_NOT_ALLOWED")
        result = self.runner((*self._prefix(scope), verb, unit), 60)
        if result.returncode != 0:
            raise MeshHold("HOLD_SERVICE_ADAPTER_COMMAND_FAILED")
        return {"operation": operation, "state": "EXECUTED", "service_before": before}

    def verify(self, operation: str, parameters: Mapping[str, object]) -> dict[str, object]:
        self.policy.validate(operation, parameters)
        unit = str(parameters["unit"])
        scope = str(parameters.get("scope", "system"))
        after = self.inspect(unit, scope)
        if operation == "service_start_canary" and after.get("active_state") != "active":
            raise MeshHold("HOLD_CANARY_SERVICE_START_VERIFY_FAILED")
        if operation == "service_stop_canary" and after.get("active_state") == "active":
            raise MeshHold("HOLD_CANARY_SERVICE_STOP_VERIFY_FAILED")
        return {"verification_state": "PASS", "service": after}


class CanaryActionDispatcher:
    """One bounded dispatcher; it does not provide a transport or authority path."""

    def __init__(
        self,
        *,
        allowed_image_refs: Sequence[str] = (),
        allowed_existing_container_ids: Sequence[str] = (),
        manage_existing_scope_authorized: bool = False,
        runner: Runner = subprocess_runner,
    ) -> None:
        self.policy = CanaryPolicy(
            allowed_image_refs=allowed_image_refs,
            allowed_existing_container_ids=allowed_existing_container_ids,
            manage_existing_scope_authorized=manage_existing_scope_authorized,
        )
        self.containers = ContainerCanaryAdapter(self.policy, runner=runner)
        self.existing_containers = ExistingContainerAdapter(self.policy, runner=runner)
        self.services = SystemCanaryServiceAdapter(self.policy, runner=runner)

    def validate(self, operation: str, parameters: Mapping[str, object]) -> None:
        self.policy.validate(operation, parameters)

    def execute(self, operation: str, parameters: Mapping[str, object]) -> dict[str, object]:
        if operation in CONTAINER_OPERATIONS:
            return self.containers.execute(operation, parameters)
        if operation in EXISTING_CONTAINER_OPERATIONS:
            return self.existing_containers.execute(operation, parameters)
        return self.services.execute(operation, parameters)

    def verify(self, operation: str, parameters: Mapping[str, object]) -> dict[str, object]:
        if operation in CONTAINER_OPERATIONS:
            return self.containers.verify(operation, parameters)
        if operation in EXISTING_CONTAINER_OPERATIONS:
            return self.existing_containers.verify(operation, parameters)
        return self.services.verify(operation, parameters)
