"""Deterministic byte bridge and evidence-bound candidate placement."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

from .contracts import CANDIDATE_AUTHORITY, ContractError, parse_time, sha256_bytes


BRIDGE_MODES = (
    "FULL_COPY",
    "DELTA_PATCH",
    "RECONSTRUCT_GPU_SIMULATED",
    "PINNED_RAM_COPY_SIMULATED",
    "EVICT_REBUILD",
)


def build_delta(base: bytes, target: bytes) -> dict[str, object]:
    prefix = 0
    limit = min(len(base), len(target))
    while prefix < limit and base[prefix] == target[prefix]:
        prefix += 1
    suffix = 0
    while (
        suffix < len(base) - prefix
        and suffix < len(target) - prefix
        and base[len(base) - suffix - 1] == target[len(target) - suffix - 1]
    ):
        suffix += 1
    base_end = len(base) - suffix
    target_end = len(target) - suffix
    replacement = target[prefix:target_end]
    return {
        "schema_id": "W7TP_BYTE_DELTA_INDEX_V1",
        "algorithm": "COMMON_PREFIX_SUFFIX_SINGLE_PATCH",
        "base_sha256": sha256_bytes(base),
        "target_sha256": sha256_bytes(target),
        "base_bytes": len(base),
        "target_bytes": len(target),
        "offset": prefix,
        "remove_bytes": base_end - prefix,
        "replacement_hex": replacement.hex(),
        "replacement_bytes": len(replacement),
        "preserved_suffix_bytes": suffix,
    }


def apply_delta(base: bytes, delta: Mapping[str, object]) -> bytes:
    if delta.get("schema_id") != "W7TP_BYTE_DELTA_INDEX_V1":
        raise ContractError("DELTA_SCHEMA_HOLD")
    if delta.get("base_sha256") != sha256_bytes(base) or delta.get("base_bytes") != len(base):
        raise ContractError("DELTA_BASE_HASH_HOLD")
    offset = delta.get("offset")
    remove = delta.get("remove_bytes")
    replacement_hex = delta.get("replacement_hex")
    if (
        isinstance(offset, bool)
        or not isinstance(offset, int)
        or isinstance(remove, bool)
        or not isinstance(remove, int)
        or not isinstance(replacement_hex, str)
        or offset < 0
        or remove < 0
        or offset + remove > len(base)
    ):
        raise ContractError("DELTA_COORDINATE_HOLD")
    try:
        replacement = bytes.fromhex(replacement_hex)
    except ValueError as exc:
        raise ContractError("DELTA_BYTES_HOLD") from exc
    rebuilt = base[:offset] + replacement + base[offset + remove :]
    if (
        delta.get("replacement_bytes") != len(replacement)
        or delta.get("target_bytes") != len(rebuilt)
        or delta.get("target_sha256") != sha256_bytes(rebuilt)
    ):
        raise ContractError("DELTA_RECONSTRUCTION_HASH_HOLD")
    return rebuilt


@dataclass(frozen=True, slots=True)
class Placement:
    resource_id: str
    kind: str
    backend: str
    evidence_state: str
    authority_state: str
    planned_mode: str

    def as_dict(self) -> dict[str, str]:
        return {
            "resource_id": self.resource_id,
            "kind": self.kind,
            "backend": self.backend,
            "evidence_state": self.evidence_state,
            "authority_state": self.authority_state,
            "planned_mode": self.planned_mode,
        }


class PlacementPlanner:
    def __init__(self, resources: Sequence[Mapping[str, object]]) -> None:
        self._resources = tuple(resources)

    def choose(self, mode: str, *, now: datetime) -> Placement:
        if mode not in BRIDGE_MODES:
            raise ContractError("PLACEMENT_MODE_HOLD")
        wanted = "VRAM_SIMULATOR" if mode == "RECONSTRUCT_GPU_SIMULATED" else "RAM"
        for item in self._resources:
            if item.get("kind") != wanted:
                continue
            lease = item.get("lease")
            revoke = item.get("revoke")
            if not isinstance(lease, Mapping) or not isinstance(revoke, Mapping):
                continue
            if (
                item.get("evidence_state") not in {"OBSERVED_DIRECT", "SIMULATED"}
                or item.get("authority_state") != CANDIDATE_AUTHORITY
                or lease.get("state") != "ACTIVE"
                or revoke.get("revoked") is not False
            ):
                continue
            if not parse_time(lease.get("issued_at")) <= now < parse_time(lease.get("expires_at")):
                continue
            return Placement(
                resource_id=str(item["resource_id"]),
                kind=str(item["kind"]),
                backend=str(item["backend"]),
                evidence_state=str(item["evidence_state"]),
                authority_state=str(item["authority_state"]),
                planned_mode=mode,
            )
        raise ContractError("PLACEMENT_NO_AUTHORIZED_RESOURCE_HOLD")


@dataclass(frozen=True, slots=True)
class BridgeResult:
    mode: str
    output: bytes
    latency_ns: int
    logical_bytes: int
    bridge_input_bytes: int
    h2d_bytes: int
    d2h_bytes: int
    evidence_state: str
    fallback_used: bool


def execute_bridge(
    mode: str,
    *,
    base: bytes,
    target: bytes,
    delta: Mapping[str, object],
    placement: Placement,
) -> BridgeResult:
    started = time.perf_counter_ns()
    if placement.planned_mode != mode:
        raise ContractError("PLACEMENT_EXECUTION_MISMATCH_HOLD")
    if mode == "FULL_COPY":
        output = bytes(target)
        bridge_bytes = len(target)
        evidence = "OBSERVED_DIRECT"
    elif mode == "DELTA_PATCH":
        output = apply_delta(base, delta)
        bridge_bytes = int(delta["replacement_bytes"])
        evidence = "OBSERVED_DIRECT"
    elif mode == "RECONSTRUCT_GPU_SIMULATED":
        if placement.evidence_state != "SIMULATED":
            raise ContractError("GPU_SIMULATOR_EVIDENCE_HOLD")
        simulated_device = bytearray(apply_delta(base, delta))
        output = bytes(simulated_device)
        bridge_bytes = len(simulated_device)
        evidence = "SIMULATED"
    elif mode == "PINNED_RAM_COPY_SIMULATED":
        simulated_pinned = bytearray(target)
        output = bytes(simulated_pinned)
        bridge_bytes = len(simulated_pinned)
        evidence = "SIMULATED"
    elif mode == "EVICT_REBUILD":
        transient = apply_delta(base, delta)
        del transient
        output = apply_delta(base, delta)
        bridge_bytes = int(delta["replacement_bytes"])
        evidence = "OBSERVED_DIRECT"
    else:
        raise ContractError("BRIDGE_MODE_HOLD")
    if sha256_bytes(output) != sha256_bytes(target):
        raise ContractError("BRIDGE_OUTPUT_HASH_HOLD")
    return BridgeResult(
        mode=mode,
        output=output,
        latency_ns=time.perf_counter_ns() - started,
        logical_bytes=len(target),
        bridge_input_bytes=bridge_bytes,
        h2d_bytes=0,
        d2h_bytes=0,
        evidence_state=evidence,
        fallback_used=False,
    )
