"""Total Field control-plane contracts without an active executor.

The mesh transports observed capability metadata and validates task envelopes.
It deliberately does not start, stop, schedule, or mutate a node/container.
Execution remains closed until a separate Total Field seal verifier and executor
are explicitly wired by deployment governance.
"""

from __future__ import annotations

import copy
from typing import Mapping

from .core import (
    CAPABILITY_INVENTORY_SCHEMA,
    CONTROL_PLANE_CONTRACT_SCHEMA,
    CONTROL_TASK_ENVELOPE_SCHEMA,
    PRIMARY_DECISION_ENGINE,
    PRIMARY_DECISION_ENGINE_REF,
    TOTAL_FIELD_AUTHORITY_REF,
    TOTAL_FIELD_AUTHORITY_NODE_REF,
    MeshHold,
    require_core,
)


AUTHORITY_CONTRACT: dict[str, object] = {
    "unique_authority": "TOTAL_FIELD",
    "authority_ref": TOTAL_FIELD_AUTHORITY_REF,
    "authority_node_ref": TOTAL_FIELD_AUTHORITY_NODE_REF,
    "authority_node_roles": [
        "TOTAL_FIELD_VERIFIER",
        "NATIVE_ADI_PRIMARY",
        "STATE_SEALER",
        "RECEIPT_ISSUER",
    ],
    "physical_control_endpoint_state": "CANDIDATE_BINDING_NOT_ACTIVATED_BY_MESH",
    "decision_engine": PRIMARY_DECISION_ENGINE,
    "decision_engine_ref": PRIMARY_DECISION_ENGINE_REF,
    "decision_engine_role": "PRIMARY_DECISION_ENGINE",
    "decision_engine_authority_state": "NOT_AUTHORITY",
}


def _typed_ref(value: object) -> bool:
    return (
        isinstance(value, str)
        and ":" in value
        and not any(character.isspace() for character in value)
        and bool(value.split(":", 1)[0])
        and bool(value.split(":", 1)[1])
    )


def authority_contract() -> dict[str, object]:
    """Return an isolated copy of the one-authority/one-engine contract."""

    return copy.deepcopy(AUTHORITY_CONTRACT)


def control_plane_contract() -> dict[str, object]:
    """Describe the extensible scheduler ingress while keeping execution off."""

    return {
        "schema_id": CONTROL_PLANE_CONTRACT_SCHEMA,
        "version": "2.1",
        "authority": authority_contract(),
        "task_envelope_schema_id": CONTROL_TASK_ENVELOPE_SCHEMA,
        "target_kinds": ["NODE", "CONTAINER"],
        "resource_dimensions": ["CPU", "GPU", "RAM", "CONTAINER_RUNTIME"],
        "action_reference_contract": "TYPED_REFERENCE_ONLY",
        "capability_reference_contract": "IMMUTABLE_SHA256_CAS_OBJECT",
        "ingress_state": "TASK_ENVELOPE_VALIDATION_AVAILABLE",
        "execution_state": "NOT_WIRED_NO_SIDE_EFFECT",
    }


def validate_control_plane_contract(contract: Mapping[str, object]) -> None:
    expected = control_plane_contract()
    if dict(contract) != expected:
        raise MeshHold("HOLD_CONTROL_PLANE_CONTRACT_DRIFT")


def build_capability_inventory(snapshot: Mapping[str, object]) -> dict[str, object]:
    """Create scheduler-readable, metadata-only CPU/GPU/RAM/runtime inventory."""

    source_node_ref = snapshot.get("source_node_ref")
    logical_time = snapshot.get("logical_time")
    if not _typed_ref(source_node_ref):
        raise MeshHold("HOLD_CAPABILITY_SOURCE_NODE_REF")
    if isinstance(logical_time, bool) or not isinstance(logical_time, int) or logical_time < 1:
        raise MeshHold("HOLD_CAPABILITY_LOGICAL_TIME")
    resources = snapshot.get("resources")
    resource_view = dict(resources) if isinstance(resources, Mapping) else {
        "cpu": {"observation_state": "UNKNOWN"},
        "ram": {"observation_state": "UNKNOWN"},
        "disks": [],
        "gpus": [],
        "gpu_observation_state": "UNKNOWN",
        "network": {"observation_state": "UNKNOWN"},
        "virtualization_evidence": [],
        "virtualization_observation_state": "UNKNOWN",
    }
    containers = snapshot.get("containers")
    images = snapshot.get("container_images")
    volumes = snapshot.get("container_volumes")
    networks = snapshot.get("container_networks")
    container_probe: Mapping[str, object] | None = None
    probes = snapshot.get("probe_evidence")
    if isinstance(probes, list):
        for item in probes:
            if isinstance(item, Mapping) and item.get("probe") == "container_metadata":
                container_probe = item
                break
    runtime_state = str(container_probe.get("state")) if container_probe is not None else "UNKNOWN"
    runtime_engine = container_probe.get("engine") if container_probe is not None else None
    core = require_core()
    container_refs = sorted(
        {
            f"container:{core.sha256_hex(core.canonical_json_bytes(item))}"
            for item in containers
            if isinstance(containers, list) and isinstance(item, Mapping)
        }
    ) if isinstance(containers, list) else []
    inventory: dict[str, object] = {
        "schema_id": CAPABILITY_INVENTORY_SCHEMA,
        "version": "2.1",
        "source_node_ref": source_node_ref,
        "logical_time": logical_time,
        "authority": authority_contract(),
        "capability_scope": ["NODE", "CONTAINER", "CPU", "GPU", "RAM", "CONTAINER_RUNTIME"],
        "targets": {"node_refs": [source_node_ref], "container_refs": container_refs},
        "resources": resource_view,
        "container_runtime": {
            "engine": runtime_engine if isinstance(runtime_engine, str) and runtime_engine else "UNKNOWN",
            "observation_state": runtime_state,
            "container_count": len(containers) if isinstance(containers, list) else 0,
            "image_count": len(images) if isinstance(images, list) else 0,
            "volume_count": len(volumes) if isinstance(volumes, list) else 0,
            "network_count": len(networks) if isinstance(networks, list) else 0,
        },
        "scheduler_interface_state": "OBSERVED_CAPABILITIES_AVAILABLE",
        "control_execution_state": "NOT_WIRED_NO_SIDE_EFFECT",
    }
    validate_capability_inventory(inventory)
    require_core().canonical_json_bytes(inventory)
    return inventory


def validate_capability_inventory(inventory: Mapping[str, object]) -> None:
    expected_keys = {
        "schema_id",
        "version",
        "source_node_ref",
        "logical_time",
        "authority",
        "capability_scope",
        "targets",
        "resources",
        "container_runtime",
        "scheduler_interface_state",
        "control_execution_state",
    }
    if set(inventory) != expected_keys:
        raise MeshHold("HOLD_CAPABILITY_INVENTORY_SHAPE")
    if inventory.get("schema_id") != CAPABILITY_INVENTORY_SCHEMA or inventory.get("version") != "2.1":
        raise MeshHold("HOLD_CAPABILITY_INVENTORY_SCHEMA")
    if inventory.get("authority") != authority_contract():
        raise MeshHold("HOLD_CAPABILITY_AUTHORITY_CONTRACT")
    if not _typed_ref(inventory.get("source_node_ref")):
        raise MeshHold("HOLD_CAPABILITY_SOURCE_NODE_REF")
    logical_time = inventory.get("logical_time")
    if isinstance(logical_time, bool) or not isinstance(logical_time, int) or logical_time < 1:
        raise MeshHold("HOLD_CAPABILITY_LOGICAL_TIME")
    if inventory.get("capability_scope") != ["NODE", "CONTAINER", "CPU", "GPU", "RAM", "CONTAINER_RUNTIME"]:
        raise MeshHold("HOLD_CAPABILITY_SCOPE")
    targets = inventory.get("targets")
    if not isinstance(targets, Mapping) or set(targets) != {"node_refs", "container_refs"}:
        raise MeshHold("HOLD_CAPABILITY_TARGETS")
    for key in ("node_refs", "container_refs"):
        values = targets.get(key)
        if not isinstance(values, list) or any(not _typed_ref(value) for value in values):
            raise MeshHold("HOLD_CAPABILITY_TARGET_REF")
    if not isinstance(inventory.get("resources"), Mapping):
        raise MeshHold("HOLD_CAPABILITY_RESOURCES")
    runtime = inventory.get("container_runtime")
    runtime_keys = {"engine", "observation_state", "container_count", "image_count", "volume_count", "network_count"}
    if not isinstance(runtime, Mapping) or set(runtime) != runtime_keys:
        raise MeshHold("HOLD_CAPABILITY_CONTAINER_RUNTIME")
    for key in ("container_count", "image_count", "volume_count", "network_count"):
        value = runtime.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise MeshHold("HOLD_CAPABILITY_CONTAINER_COUNT")
    if inventory.get("scheduler_interface_state") != "OBSERVED_CAPABILITIES_AVAILABLE":
        raise MeshHold("HOLD_CAPABILITY_SCHEDULER_INTERFACE")
    if inventory.get("control_execution_state") != "NOT_WIRED_NO_SIDE_EFFECT":
        raise MeshHold("HOLD_CAPABILITY_EXECUTION_STATE")


def build_task_envelope(
    *,
    task_id: str,
    target_kind: str,
    target_ref: str,
    action_ref: str,
    intent_ref: str,
    capability_inventory_ref: str,
    authority_seal_ref: str,
    logical_time: int,
    nonce: str,
    ttl_seconds: int,
    cpu_threads: int | None = None,
    ram_bytes: int | None = None,
    gpu_memory_mib: int | None = None,
    container_runtime_ref: str | None = None,
) -> dict[str, object]:
    """Build a non-executable scheduler task envelope for a future executor."""

    envelope: dict[str, object] = {
        "schema_id": CONTROL_TASK_ENVELOPE_SCHEMA,
        "version": "2.1",
        "task_id": task_id,
        "authority": {
            **authority_contract(),
            "authority_seal_ref": authority_seal_ref,
            "authority_verification_state": "UNVERIFIED_EXTERNAL_PREREQUISITE",
        },
        "intent_ref": intent_ref,
        "target": {"target_kind": target_kind, "target_ref": target_ref},
        "action_ref": action_ref,
        "capability_inventory_ref": capability_inventory_ref,
        "resource_request": {
            "cpu_threads": cpu_threads,
            "ram_bytes": ram_bytes,
            "gpu_memory_mib": gpu_memory_mib,
            "container_runtime_ref": container_runtime_ref,
        },
        "logical_time": logical_time,
        "nonce": nonce,
        "ttl_seconds": ttl_seconds,
        "control_state": "HOLD_UNTIL_TOTAL_FIELD_AUTHORIZATION_VERIFIED",
        "execution_permitted": False,
    }
    validate_task_envelope(envelope)
    require_core().canonical_json_bytes(envelope)
    return envelope


def validate_task_envelope(envelope: Mapping[str, object]) -> None:
    expected_keys = {
        "schema_id",
        "version",
        "task_id",
        "authority",
        "intent_ref",
        "target",
        "action_ref",
        "capability_inventory_ref",
        "resource_request",
        "logical_time",
        "nonce",
        "ttl_seconds",
        "control_state",
        "execution_permitted",
    }
    if set(envelope) != expected_keys:
        raise MeshHold("HOLD_CONTROL_TASK_SHAPE")
    if envelope.get("schema_id") != CONTROL_TASK_ENVELOPE_SCHEMA or envelope.get("version") != "2.1":
        raise MeshHold("HOLD_CONTROL_TASK_SCHEMA")
    authority = envelope.get("authority")
    authority_keys = set(AUTHORITY_CONTRACT) | {"authority_seal_ref", "authority_verification_state"}
    if not isinstance(authority, Mapping) or set(authority) != authority_keys:
        raise MeshHold("HOLD_CONTROL_TASK_AUTHORITY_SHAPE")
    if any(authority.get(key) != value for key, value in AUTHORITY_CONTRACT.items()):
        raise MeshHold("HOLD_CONTROL_TASK_AUTHORITY_CONTRACT")
    if not _typed_ref(authority.get("authority_seal_ref")):
        raise MeshHold("HOLD_CONTROL_TASK_AUTHORITY_SEAL_REF")
    if authority.get("authority_verification_state") != "UNVERIFIED_EXTERNAL_PREREQUISITE":
        raise MeshHold("HOLD_CONTROL_TASK_AUTHORITY_STATE")
    target = envelope.get("target")
    if not isinstance(target, Mapping) or set(target) != {"target_kind", "target_ref"}:
        raise MeshHold("HOLD_CONTROL_TASK_TARGET_SHAPE")
    if target.get("target_kind") not in {"NODE", "CONTAINER"} or not _typed_ref(target.get("target_ref")):
        raise MeshHold("HOLD_CONTROL_TASK_TARGET")
    for key in ("intent_ref", "action_ref"):
        if not _typed_ref(envelope.get(key)):
            raise MeshHold("HOLD_CONTROL_TASK_REFERENCE")
    capability_ref = envelope.get("capability_inventory_ref")
    if not isinstance(capability_ref, str) or not capability_ref.startswith("sha256:") or len(capability_ref) != 71:
        raise MeshHold("HOLD_CONTROL_TASK_CAPABILITY_REF")
    request = envelope.get("resource_request")
    request_keys = {"cpu_threads", "ram_bytes", "gpu_memory_mib", "container_runtime_ref"}
    if not isinstance(request, Mapping) or set(request) != request_keys:
        raise MeshHold("HOLD_CONTROL_TASK_RESOURCE_REQUEST")
    for key in ("cpu_threads", "ram_bytes", "gpu_memory_mib"):
        value = request.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise MeshHold("HOLD_CONTROL_TASK_RESOURCE_VALUE")
    runtime_ref = request.get("container_runtime_ref")
    if runtime_ref is not None and not _typed_ref(runtime_ref):
        raise MeshHold("HOLD_CONTROL_TASK_RUNTIME_REF")
    for key in ("logical_time", "ttl_seconds"):
        value = envelope.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise MeshHold("HOLD_CONTROL_TASK_INTEGER")
    if not isinstance(envelope.get("task_id"), str) or not envelope.get("task_id"):
        raise MeshHold("HOLD_CONTROL_TASK_ID")
    if not isinstance(envelope.get("nonce"), str) or len(str(envelope.get("nonce"))) < 16:
        raise MeshHold("HOLD_CONTROL_TASK_NONCE")
    if envelope.get("control_state") != "HOLD_UNTIL_TOTAL_FIELD_AUTHORIZATION_VERIFIED":
        raise MeshHold("HOLD_CONTROL_TASK_STATE")
    if envelope.get("execution_permitted") is not False:
        raise MeshHold("HOLD_CONTROL_TASK_EXECUTION_FORBIDDEN")
