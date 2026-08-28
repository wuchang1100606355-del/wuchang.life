"""Closed contracts and metadata-only resource probes for the experiment."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence


PACKET_SCHEMA = "W7TP_8D_CANDIDATE_PACKET_V1"
RESOURCE_SCHEMA = "W7TP_CANDIDATE_RESOURCE_CATALOG_V1"
RECEIPT_SCHEMA = "W7TP_CONTROLLED_EXPERIMENT_RECEIPT_V1"
ALGORITHM_VERSION = "w7tp-controlled-experiment-v1.0.0"
CANDIDATE_AUTHORITY = "AUTHORIZED_CANDIDATE_ONLY"
UNKNOWN_REF = "UNKNOWN_UNVERIFIED"


class ContractError(ValueError):
    """A stable fail-closed contract error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        raise ContractError("TIMEZONE_REQUIRED")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise ContractError("TIME_REQUIRED")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("TIME_INVALID") from exc
    if parsed.tzinfo is None:
        raise ContractError("TIMEZONE_REQUIRED")
    return parsed.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class ResourceRecord:
    resource_id: str
    node: str
    kind: str
    capacity: Mapping[str, int | str | None]
    observed_at: str
    evidence_state: str
    authority_state: str
    lease: Mapping[str, object]
    revoke: Mapping[str, object]
    source: Mapping[str, object]
    limits: Mapping[str, object]
    backend: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _lease(now: datetime, seconds: int) -> dict[str, object]:
    return {
        "lease_id": f"candidate-local-{int(now.timestamp())}",
        "issued_at": utc_text(now),
        "expires_at": utc_text(now + timedelta(seconds=seconds)),
        "scope": "LOCAL_SYNTHETIC_EXPERIMENT_ONLY",
        "state": "ACTIVE",
    }


def _revoke() -> dict[str, object]:
    return {
        "revoked": False,
        "revocation_ref": None,
        "check": "PER_PLACEMENT",
    }


def _ram_bytes() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def _gpu_observation() -> tuple[str, int | None, str]:
    command = shutil.which("nvidia-smi")
    if command is None:
        return "UNKNOWN_UNVERIFIED", None, "NVIDIA_SMI_NOT_FOUND"
    try:
        result = subprocess.run(
            [
                command,
                "--query-gpu=memory.total",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "UNKNOWN_UNVERIFIED", None, "NVIDIA_SMI_UNAVAILABLE_OR_TIMEOUT"
    if result.returncode != 0:
        return "UNKNOWN_UNVERIFIED", None, "NVIDIA_SMI_UNAVAILABLE_OR_BLOCKED"
    try:
        totals = [int(line.strip()) for line in result.stdout.splitlines() if line.strip()]
    except ValueError:
        return "UNKNOWN_UNVERIFIED", None, "NVIDIA_SMI_OUTPUT_INVALID"
    if not totals:
        return "UNKNOWN_UNVERIFIED", None, "NVIDIA_SMI_GPU_NOT_OBSERVED"
    return "OBSERVED_DIRECT", sum(totals) * 1024 * 1024, "NVIDIA_SMI_METADATA_ONLY"


def probe_resource_catalog(
    *,
    now: datetime,
    node: str = "MSI",
    lease_seconds: int = 1800,
) -> dict[str, object]:
    """Observe non-secret local metadata; real GPU remains unauthorized."""

    if lease_seconds < 1:
        raise ContractError("LEASE_INVALID")
    observed = utc_text(now)
    lease = _lease(now, lease_seconds)
    resources: list[ResourceRecord] = []
    resources.append(
        ResourceRecord(
            resource_id="msi-cpu-local",
            node=node,
            kind="CPU",
            capacity={"logical_cores": os.cpu_count()},
            observed_at=observed,
            evidence_state="OBSERVED_DIRECT",
            authority_state=CANDIDATE_AUTHORITY,
            lease=lease,
            revoke=_revoke(),
            source={"method": "os.cpu_count", "platform": platform.system()},
            limits={"workload": "SYNTHETIC_BYTES_ONLY"},
            backend="python-stdlib",
        )
    )
    resources.append(
        ResourceRecord(
            resource_id="msi-ram-local",
            node=node,
            kind="RAM",
            capacity={"bytes_total": _ram_bytes()},
            observed_at=observed,
            evidence_state="OBSERVED_DIRECT",
            authority_state=CANDIDATE_AUTHORITY,
            lease=lease,
            revoke=_revoke(),
            source={"method": "proc_meminfo_metadata"},
            limits={"max_demo_payload_bytes": 8 * 1024 * 1024},
            backend="python-bytes",
        )
    )
    usage = shutil.disk_usage("/tmp")
    resources.append(
        ResourceRecord(
            resource_id="msi-storage-tmp",
            node=node,
            kind="STORAGE",
            capacity={"bytes_total": usage.total, "bytes_free": usage.free},
            observed_at=observed,
            evidence_state="OBSERVED_DIRECT",
            authority_state=CANDIDATE_AUTHORITY,
            lease=lease,
            revoke=_revoke(),
            source={"method": "shutil.disk_usage", "coordinate": "/tmp"},
            limits={"write_boundary": "/tmp/w7tp_controlled_experiment_v1"},
            backend="local-filesystem",
        )
    )
    gpu_state, vram_bytes, gpu_method = _gpu_observation()
    resources.append(
        ResourceRecord(
            resource_id="msi-gpu-observation",
            node=node,
            kind="GPU_VRAM",
            capacity={"vram_bytes_total": vram_bytes},
            observed_at=observed,
            evidence_state=gpu_state,
            authority_state="NOT_AUTHORIZED",
            lease={**lease, "state": "NOT_GRANTED"},
            revoke=_revoke(),
            source={"method": gpu_method},
            limits={"execution": "FORBIDDEN_IN_PHASE_B"},
            backend="none",
        )
    )
    resources.append(
        ResourceRecord(
            resource_id="msi-vram-simulator",
            node=node,
            kind="VRAM_SIMULATOR",
            capacity={"bytes_total": 256 * 1024 * 1024},
            observed_at=observed,
            evidence_state="SIMULATED",
            authority_state=CANDIDATE_AUTHORITY,
            lease=lease,
            revoke=_revoke(),
            source={"method": "python-bytearray-explicit-simulator"},
            limits={"no_cuda": True, "no_gpu_claim": True, "max_payload_bytes": 8 * 1024 * 1024},
            backend="python-bytearray-simulator",
        )
    )
    body: dict[str, object] = {
        "schema_id": RESOURCE_SCHEMA,
        "candidate_only": True,
        "node": node,
        "observed_at": observed,
        "available_backends": [
            "FULL_COPY",
            "DELTA_PATCH",
            "RECONSTRUCT_GPU_SIMULATED",
            "PINNED_RAM_COPY_SIMULATED",
            "EVICT_REBUILD",
        ],
        "resources": [record.as_dict() for record in resources],
    }
    body["catalog_sha256"] = sha256_bytes(canonical_bytes(body))
    return body


def build_candidate_packet(
    *,
    run_id: str,
    task_id: str,
    scenario_id: str,
    sequence: int,
    source_version: str,
    base: bytes,
    target: bytes,
    delta: Mapping[str, object],
    resource_ids: Sequence[str],
    issued_at: datetime,
    ttl_seconds: int = 900,
) -> dict[str, object]:
    if sequence < 1 or ttl_seconds < 1 or ttl_seconds > 3600:
        raise ContractError("PACKET_SEQUENCE_OR_TTL_INVALID")
    if not resource_ids:
        raise ContractError("PACKET_AUTHORIZATION_SCOPE_EMPTY")
    packet: dict[str, object] = {
        "schema_id": PACKET_SCHEMA,
        "candidate_only": True,
        "total_field_decision": "NOT_REVIEWED",
        "run_id": run_id,
        "task_id": task_id,
        "scenario_id": scenario_id,
        "sequence": sequence,
        "identity_ref": UNKNOWN_REF,
        "member_ref": UNKNOWN_REF,
        "session_ref": UNKNOWN_REF,
        "xiaoj_ref": "XIAOJ_CANDIDATE_SYNTHETIC_ENTRY",
        "source": {
            "version": source_version,
            "base_sha256": sha256_bytes(base),
            "target_sha256": sha256_bytes(target),
            "base_bytes": len(base),
            "target_bytes": len(target),
        },
        "delta_index": dict(delta),
        "reconstruction_contract": {
            "equivalence": "BYTE_EXACT",
            "expected_sha256": sha256_bytes(target),
            "expected_bytes": len(target),
            "algorithm_version": ALGORITHM_VERSION,
        },
        "authorization_scope": {
            "authority_state": CANDIDATE_AUTHORITY,
            "scope": "LOCAL_SYNTHETIC_EXPERIMENT_ONLY",
            "resource_ids": list(resource_ids),
            "write_boundary": "/tmp/w7tp_controlled_experiment_v1",
            "forbidden": [
                "CANONICAL_MUTATION",
                "AUTHORITY_MUTATION",
                "NONCE_CONSUMPTION",
                "ODOO_OR_MEMBER_WRITE",
                "PRODUCTION_SESSION",
                "DEPLOY_OR_RESTART",
            ],
        },
        "issued_at": utc_text(issued_at),
        "expires_at": utc_text(issued_at + timedelta(seconds=ttl_seconds)),
        "fallback": "FULL_COPY",
        "failure_policy": "FAIL_CLOSED_OR_SAFE_FULL_COPY",
        "algorithm_version": ALGORITHM_VERSION,
    }
    packet["state_field_8d"] = {
        "D1_INTENT": {
            "intent": "SYNTHETIC_BYTE_EXACT_RECONSTRUCTION",
            "task_id": task_id,
            "candidate_only": True,
        },
        "D2_STATE": {
            "from": "BASE_HASH_BOUND",
            "to": "RECONSTRUCTED_HASH_VERIFIED",
            "base_sha256": sha256_bytes(base),
            "target_sha256": sha256_bytes(target),
        },
        "D3_COORDINATE": {
            "run_id": run_id,
            "scenario_id": scenario_id,
            "sequence": sequence,
            "node": "MSI_LOCAL_CANDIDATE",
        },
        "D4_EVIDENCE": {
            "source_version": source_version,
            "delta_index_sha256": sha256_bytes(canonical_bytes(delta)),
            "verification": "SHA256_BYTE_EXACT_REQUIRED",
        },
        "D5_EXECUTION_OR_POLICY": {
            "allowed_modes": [
                "FULL_COPY",
                "DELTA_PATCH",
                "RECONSTRUCT_GPU_SIMULATED",
                "PINNED_RAM_COPY_SIMULATED",
                "EVICT_REBUILD",
            ],
            "write_boundary": "/tmp/w7tp_controlled_experiment_v1",
            "canonical_mutation": False,
        },
        "D6_GENERATIVE_TRANSMISSION": {
            "algorithm_version": ALGORITHM_VERSION,
            "delta_algorithm": delta.get("algorithm"),
            "fallback": "FULL_COPY",
            "receiver_binding": "w7tp_runtime.gt_packet_v2.PacketV2.isolated_receive",
        },
        "D7_RISK_OR_QUARANTINE": {
            "failure_policy": "FAIL_CLOSED_OR_SAFE_FULL_COPY",
            "real_gpu": "NOT_AUTHORIZED",
            "member_plaintext": "EXCLUDED",
            "secrets": "EXCLUDED",
            "authority_escalation": "FORBIDDEN",
        },
        "D8_ENVELOPE_OR_AUTHORITY": {
            "identity_precondition": UNKNOWN_REF,
            "authority_state": CANDIDATE_AUTHORITY,
            "candidate_only": True,
            "issued_at": utc_text(issued_at),
            "expires_at": utc_text(issued_at + timedelta(seconds=ttl_seconds)),
            "total_field_decision": "NOT_REVIEWED",
        },
    }
    packet["packet_sha256"] = sha256_bytes(canonical_bytes(packet))
    return packet


def validate_candidate_packet(packet: Mapping[str, object], *, now: datetime) -> None:
    if packet.get("schema_id") != PACKET_SCHEMA:
        raise ContractError("PACKET_SCHEMA_HOLD")
    if packet.get("candidate_only") is not True or packet.get("total_field_decision") != "NOT_REVIEWED":
        raise ContractError("PACKET_AUTHORITY_HOLD")
    supplied = packet.get("packet_sha256")
    if not isinstance(supplied, str):
        raise ContractError("PACKET_HASH_HOLD")
    body = dict(packet)
    body.pop("packet_sha256", None)
    if sha256_bytes(canonical_bytes(body)) != supplied:
        raise ContractError("PACKET_HASH_HOLD")
    issued = parse_time(packet.get("issued_at"))
    expires = parse_time(packet.get("expires_at"))
    current = now.astimezone(UTC)
    if not issued <= current < expires or expires - issued > timedelta(hours=1):
        raise ContractError("PACKET_LEASE_HOLD")
    sequence = packet.get("sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise ContractError("PACKET_SEQUENCE_HOLD")
    scope = packet.get("authorization_scope")
    if not isinstance(scope, Mapping):
        raise ContractError("PACKET_AUTHORIZATION_HOLD")
    resources = scope.get("resource_ids")
    if (
        scope.get("authority_state") != CANDIDATE_AUTHORITY
        or scope.get("scope") != "LOCAL_SYNTHETIC_EXPERIMENT_ONLY"
        or not isinstance(resources, list)
        or not resources
        or scope.get("write_boundary") != "/tmp/w7tp_controlled_experiment_v1"
    ):
        raise ContractError("PACKET_AUTHORIZATION_HOLD")
    state_field = packet.get("state_field_8d")
    required_8d = {
        "D1_INTENT",
        "D2_STATE",
        "D3_COORDINATE",
        "D4_EVIDENCE",
        "D5_EXECUTION_OR_POLICY",
        "D6_GENERATIVE_TRANSMISSION",
        "D7_RISK_OR_QUARANTINE",
        "D8_ENVELOPE_OR_AUTHORITY",
    }
    if not isinstance(state_field, Mapping) or set(state_field) != required_8d:
        raise ContractError("PACKET_8D_CLOSURE_HOLD")
    d8 = state_field.get("D8_ENVELOPE_OR_AUTHORITY")
    if (
        not isinstance(d8, Mapping)
        or d8.get("candidate_only") is not True
        or d8.get("authority_state") != CANDIDATE_AUTHORITY
        or d8.get("total_field_decision") != "NOT_REVIEWED"
    ):
        raise ContractError("PACKET_D8_AUTHORITY_HOLD")
