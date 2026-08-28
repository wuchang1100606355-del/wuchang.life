"""Deterministic best-fit placement from existing mesh inventory snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from w7tp_gt_mesh.core import MeshHold, require_core
from w7tp_runtime.state_field.controlled_experiment_v1.bridge import PlacementPlanner

from .human_view import render_execution_lease_zh_tw, render_placement_zh_tw


@dataclass(frozen=True, slots=True)
class ResourceRequest:
    cpu_count: int
    ram_bytes: int
    disk_bytes: int
    gpu_count: int = 0
    gpu_memory_mib: int = 0
    pids_limit: int = 128
    container_engine: str | None = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "ResourceRequest":
        values: dict[str, int] = {}
        for key in ("cpu_count", "ram_bytes", "disk_bytes", "gpu_count", "gpu_memory_mib", "pids_limit"):
            default = 0 if key.startswith("gpu_") else 128 if key == "pids_limit" else None
            value = raw.get(key, default)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise MeshHold("HOLD_RESOURCE_REQUEST_INVALID")
            values[key] = value
        if (
            values["cpu_count"] < 1
            or values["ram_bytes"] < 1
            or values["disk_bytes"] < 1
            or not 1 <= values["pids_limit"] <= 4096
        ):
            raise MeshHold("HOLD_RESOURCE_REQUEST_INVALID")
        engine = raw.get("container_engine")
        if engine is not None and engine not in {"docker", "podman"}:
            raise MeshHold("HOLD_RESOURCE_CONTAINER_ENGINE_INVALID")
        return cls(**values, container_engine=engine)

    def as_dict(self) -> dict[str, object]:
        decision: dict[str, object] = {
            "cpu_count": self.cpu_count,
            "ram_bytes": self.ram_bytes,
            "disk_bytes": self.disk_bytes,
            "gpu_count": self.gpu_count,
            "gpu_memory_mib": self.gpu_memory_mib,
            "pids_limit": self.pids_limit,
            "container_engine": self.container_engine,
        }
        return decision


@dataclass(frozen=True, slots=True)
class NodeCapability:
    node_id: str
    cpu_count: int
    ram_available_bytes: int
    disk_free_bytes: int
    gpu_count: int
    gpu_memory_mib: int
    container_engines: tuple[str, ...]
    snapshot_sha256: str

    def satisfies(self, request: ResourceRequest) -> bool:
        return (
            self.cpu_count >= request.cpu_count
            and self.ram_available_bytes >= request.ram_bytes
            and self.disk_free_bytes >= request.disk_bytes
            and self.gpu_count >= request.gpu_count
            and self.gpu_memory_mib >= request.gpu_memory_mib
            and (request.container_engine is None or request.container_engine in self.container_engines)
        )


def _positive_int(value: object, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MeshHold(code)
    return value


def capability_from_snapshot(snapshot: Mapping[str, object]) -> NodeCapability:
    node = snapshot.get("node")
    resources = snapshot.get("resources")
    if not isinstance(node, Mapping) or not isinstance(resources, Mapping):
        raise MeshHold("HOLD_NODE_CAPABILITY_MISSING")
    node_id = node.get("node_id")
    if not isinstance(node_id, str) or not node_id:
        raise MeshHold("HOLD_NODE_CAPABILITY_ID_INVALID")
    cpu = resources.get("cpu")
    ram = resources.get("ram")
    disks = resources.get("disks")
    gpus = resources.get("gpus")
    if not isinstance(cpu, Mapping) or not isinstance(ram, Mapping) or not isinstance(disks, list) or not isinstance(gpus, list):
        raise MeshHold("HOLD_NODE_CAPABILITY_RESOURCES_UNKNOWN")
    cpu_count = _positive_int(cpu.get("logical_count"), "HOLD_NODE_CPU_UNKNOWN")
    ram_available = _positive_int(ram.get("available_bytes"), "HOLD_NODE_RAM_UNKNOWN")
    free_values = [
        _positive_int(item.get("free_bytes"), "HOLD_NODE_DISK_UNKNOWN")
        for item in disks
        if isinstance(item, Mapping) and item.get("observation_state") == "OBSERVED_METADATA_ONLY"
    ]
    if not free_values:
        raise MeshHold("HOLD_NODE_DISK_UNKNOWN")
    gpu_memory: list[int] = []
    for item in gpus:
        if not isinstance(item, Mapping):
            raise MeshHold("HOLD_NODE_GPU_INVALID")
        gpu_memory.append(_positive_int(item.get("memory_total_mib"), "HOLD_NODE_GPU_UNKNOWN"))
    engines: set[str] = set()
    for record in snapshot.get("containers", []):
        if isinstance(record, Mapping) and record.get("engine") in {"docker", "podman"}:
            engines.add(str(record["engine"]))
    for probe in snapshot.get("probe_evidence", []):
        if (
            isinstance(probe, Mapping)
            and probe.get("probe") == "container_metadata"
            and probe.get("state") == "OBSERVED"
            and probe.get("engine") in {"docker", "podman"}
        ):
            engines.add(str(probe["engine"]))
    digest = require_core().sha256_hex(require_core().canonical_json_bytes(snapshot))
    return NodeCapability(
        node_id=node_id,
        cpu_count=cpu_count,
        ram_available_bytes=ram_available,
        disk_free_bytes=max(free_values),
        gpu_count=len(gpu_memory),
        gpu_memory_mib=sum(gpu_memory),
        container_engines=tuple(sorted(engines)),
        snapshot_sha256=digest,
    )


class TotalFieldPlacementPlanner(PlacementPlanner):
    """Narrow hardware-capability extension of the established planner.

    The inherited planner remains the implementation for its existing bridge
    modes. This candidate adds only a node-inventory view and does not introduce
    another transport, lease issuer, or canonical placement authority.
    """

    def __init__(self, snapshots: Sequence[Mapping[str, object]]) -> None:
        self._snapshots = tuple(snapshots)
        capabilities: list[NodeCapability] = []
        rejected: list[dict[str, str]] = []
        inherited_resources: list[dict[str, object]] = []
        for snapshot in self._snapshots:
            try:
                capability = capability_from_snapshot(snapshot)
            except MeshHold as exc:
                node = snapshot.get("node") if isinstance(snapshot, Mapping) else None
                node_id = node.get("node_id") if isinstance(node, Mapping) else "UNKNOWN"
                rejected.append({"node_id": str(node_id), "reason_code": exc.code})
                continue
            capabilities.append(capability)
            inherited_resources.append(
                {
                    "resource_id": f"node-capability:{capability.node_id}:{capability.snapshot_sha256}",
                    "kind": "NODE_CAPABILITY",
                    "backend": ",".join(capability.container_engines) or "NO_CONTAINER_ENGINE_OBSERVED",
                    "evidence_state": "OBSERVED_DIRECT",
                    "authority_state": "EVIDENCE_ONLY_NOT_AUTHORITY",
                    "node_capability": capability,
                }
            )
        super().__init__(inherited_resources)
        self._capabilities = tuple(capabilities)
        self._rejected = tuple(rejected)

    def choose_node(self, resource_request: Mapping[str, object]) -> dict[str, object]:
        request = ResourceRequest.from_mapping(resource_request)
        candidates: list[NodeCapability] = []
        rejected = list(self._rejected)
        for capability in self._capabilities:
            if capability.satisfies(request):
                candidates.append(capability)
            else:
                rejected.append({"node_id": capability.node_id, "reason_code": "RESOURCE_INSUFFICIENT"})
        if not candidates:
            raise MeshHold("HOLD_NO_CAPABLE_NODE")
        candidates.sort(
            key=lambda item: (
                item.gpu_count - request.gpu_count,
                item.gpu_memory_mib - request.gpu_memory_mib,
                item.ram_available_bytes - request.ram_bytes,
                item.cpu_count - request.cpu_count,
                item.disk_free_bytes - request.disk_bytes,
                item.node_id,
            )
        )
        selected = candidates[0]
        node_manifest = {
            "schema_id": "W7TP_NODE_MANIFEST_CANDIDATE_V1",
            "node_id": selected.node_id,
            "container_engines": list(selected.container_engines),
            "snapshot_sha256": selected.snapshot_sha256,
            "authority_state": "EVIDENCE_ONLY_NOT_AUTHORITY",
        }
        node_resource_state = {
            "schema_id": "W7TP_NODE_RESOURCE_STATE_CANDIDATE_V1",
            "node_id": selected.node_id,
            "cpu_count": selected.cpu_count,
            "ram_available_bytes": selected.ram_available_bytes,
            "disk_free_bytes": selected.disk_free_bytes,
            "gpu_count": selected.gpu_count,
            "gpu_memory_mib": selected.gpu_memory_mib,
            "snapshot_sha256": selected.snapshot_sha256,
            "observation_state": "OBSERVED_METADATA_ONLY",
        }
        lease_preimage = {
            "node_id": selected.node_id,
            "snapshot_sha256": selected.snapshot_sha256,
            "resource_request": request.as_dict(),
            "state": "ISSUED",
        }
        lease_sha256 = require_core().sha256_hex(require_core().canonical_json_bytes(lease_preimage))
        execution_lease = {
            "schema_id": "W7TP_EXECUTION_LEASE_CANDIDATE_V1",
            "lease_id": f"execution_lease:{lease_sha256}",
            **lease_preimage,
            "state_machine": [
                "ISSUED",
                "ACKNOWLEDGED",
                "RUNNING",
                "RESULT_CANDIDATE",
                "ACCEPTED",
                "EXPIRED",
                "REJECTED",
            ],
            "issuer_node_id": "taiji01",
            "authority_ref": "authority:TOTAL_FIELD",
        }
        execution_lease["human_summary_zh_tw"] = render_execution_lease_zh_tw(execution_lease)
        decision: dict[str, object] = {
            "schema_id": "W7TP_TOTAL_FIELD_PLACEMENT_DECISION_CANDIDATE_V1",
            "authority_ref": "authority:TOTAL_FIELD",
            "primary_decision_engine": "8D_ADI",
            "algorithm": "PLACEMENT_PLANNER_NODE_CAPABILITY_EXTENSION_V1",
            "base_planner": (
                "w7tp_runtime.state_field.controlled_experiment_v1.bridge:PlacementPlanner"
            ),
            "selected_node_id": selected.node_id,
            "selected_snapshot_sha256": selected.snapshot_sha256,
            "resource_request": request.as_dict(),
            "node_manifest": node_manifest,
            "node_resource_state": node_resource_state,
            "execution_lease": execution_lease,
            "eligible_node_ids": [item.node_id for item in candidates],
            "rejected_nodes": sorted(rejected, key=lambda item: (item["node_id"], item["reason_code"])),
            "candidate_state": "CANDIDATE_NOT_CANONICAL_NOT_PROMOTED",
        }
        decision["human_summary_zh_tw"] = render_placement_zh_tw(decision)
        return decision


def deterministic_place(
    snapshots: Sequence[Mapping[str, object]],
    resource_request: Mapping[str, object],
) -> dict[str, object]:
    return TotalFieldPlacementPlanner(snapshots).choose_node(resource_request)
