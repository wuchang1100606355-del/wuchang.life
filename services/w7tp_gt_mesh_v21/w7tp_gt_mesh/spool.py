"""Low-cost Drive spool producer; projection is evidence, never authority."""

from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

from .core import (
    DRIVE_ENVELOPE_SCHEMA,
    MeshConflict,
    MeshHold,
    require_core,
    safe_component,
    utc_now,
    utc_text,
)


def _slug(value: object) -> str:
    text = str(value or "unknown")
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", text).strip("-.")[:80]
    return cleaned or "unknown"


class DriveSpoolProducer:
    """Emit one canonical envelope JSON per projected artifact."""

    def __init__(self, spool_root: str | os.PathLike[str]) -> None:
        root = Path(spool_root)
        root.mkdir(parents=True, exist_ok=True)
        if root.is_symlink() or not root.is_dir():
            raise MeshHold("HOLD_DRIVE_SPOOL_ROOT_UNSAFE")
        self.root = root.resolve(strict=True)

    def emit(
        self,
        projection_relative_path: str,
        artifact: Mapping[str, object],
        *,
        source_node_ref: str,
        packet_id: str,
        logical_time: int,
        created_at: str | None = None,
    ) -> Path:
        core = require_core()
        relative = PurePosixPath(projection_relative_path)
        if (
            relative.is_absolute()
            or any(part in {"", ".", ".."} for part in relative.parts)
            or relative.suffix != ".json"
        ):
            raise MeshHold("HOLD_DRIVE_PROJECTION_PATH_INVALID")
        artifact_dict = dict(artifact)
        if "07_GITHUB" in relative.parts and not (
            artifact_dict.get("dimension") == "D4_EVIDENCE"
            and artifact_dict.get("authority_state") == "EVIDENCE_ONLY"
            and artifact_dict.get("live_effect_state") == "NOT_ESTABLISHED_BY_GIT"
        ):
            raise MeshHold("HOLD_GITHUB_PROJECTION_D4_GATE")
        artifact_raw = core.canonical_json_bytes(artifact_dict)
        body: dict[str, object] = {
            "schema_id": DRIVE_ENVELOPE_SCHEMA,
            "projection_relative_path": relative.as_posix(),
            "artifact_sha256": core.sha256_hex(artifact_raw),
            "artifact": artifact_dict,
            "source_node_ref": source_node_ref,
            "packet_id": packet_id,
            "logical_time": logical_time,
            "created_at": created_at or utc_text(utc_now()),
        }
        body["envelope_sha256"] = core.sha256_hex(core.canonical_json_bytes(body))
        raw = core.canonical_json_bytes(body)
        destination = self.root.joinpath(*relative.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        resolved_parent = destination.parent.resolve(strict=True)
        if self.root != resolved_parent and self.root not in resolved_parent.parents:
            raise MeshHold("HOLD_DRIVE_PROJECTION_PATH_ESCAPE")
        try:
            with destination.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            if destination.read_bytes() != raw:
                raise MeshConflict("CONFLICT_DRIVE_PROJECTION_EXISTS")
        return destination


def produce_drive_projection_envelopes(
    spool_root: str | os.PathLike[str],
    *,
    snapshot: Mapping[str, object],
    packet: Mapping[str, object],
    profile: Mapping[str, object],
    lineage: Mapping[str, object],
    capability_inventory: Mapping[str, object] | None = None,
    receipts: Sequence[Mapping[str, object]] = (),
) -> tuple[Path, ...]:
    """Split a transfer into the governed low-cost projection topology."""

    core = require_core()
    producer = DriveSpoolProducer(spool_root)
    node_ref = snapshot.get("source_node_ref")
    logical_time = snapshot.get("logical_time")
    envelope = packet.get("envelope")
    if (
        not isinstance(node_ref, str)
        or ":" not in node_ref
        or isinstance(logical_time, bool)
        or not isinstance(logical_time, int)
        or not isinstance(envelope, Mapping)
        or not isinstance(envelope.get("packet_id"), str)
    ):
        raise MeshHold("HOLD_DRIVE_PROJECTION_COORDINATE")
    node_id = safe_component(node_ref.split(":", 1)[1], code="HOLD_NODE_ID_INVALID")
    packet_id = str(envelope["packet_id"])
    created_at = str(profile.get("issued_at") or utc_text(utc_now()))
    emitted: list[Path] = []

    def project(prefix: str, artifact: Mapping[str, object]) -> None:
        digest = core.sha256_hex(core.canonical_json_bytes(artifact))
        emitted.append(
            producer.emit(
                f"{prefix}/{logical_time:020d}-{digest}.json",
                artifact,
                source_node_ref=node_ref,
                packet_id=packet_id,
                logical_time=logical_time,
                created_at=created_at,
            )
        )

    node = snapshot.get("node")
    if isinstance(node, Mapping):
        project(f"01_NODE_INDEX/{node_id}/node", {"schema_id": "W7TP_GT_MESH_NODE_INDEX_V21", **dict(node)})
    resources = snapshot.get("resources")
    if isinstance(resources, Mapping):
        project(f"01_NODE_INDEX/{node_id}/resources", {"schema_id": "W7TP_GT_MESH_NODE_RESOURCE_INDEX_V21", **dict(resources)})
    if capability_inventory is not None:
        project(f"01_NODE_INDEX/{node_id}/capabilities", capability_inventory)
    for discovered in snapshot.get("discovered_nodes", []):
        if isinstance(discovered, Mapping):
            safe_id = _slug(
                discovered.get("node_id")
                if discovered.get("node_id") not in {None, "", "UNKNOWN"}
                else discovered.get("dns_name") or discovered.get("node_name")
            )
            project(
                f"01_NODE_INDEX/discovered/{safe_id}/observers/{node_id}/topology",
                {"schema_id": "W7TP_GT_MESH_DISCOVERED_NODE_EVIDENCE_V21", **dict(discovered)},
            )
    for service in snapshot.get("services", []):
        if isinstance(service, Mapping):
            project(
                f"01_NODE_INDEX/{node_id}/services/{_slug(service.get('service_id'))}",
                {"schema_id": "W7TP_GT_MESH_SERVICE_INDEX_V21", **dict(service)},
            )
    for container in snapshot.get("containers", []):
        if isinstance(container, Mapping):
            project(
                f"01_NODE_INDEX/{node_id}/containers/{_slug(container.get('name') or container.get('container_id'))}",
                {"schema_id": "W7TP_GT_MESH_CONTAINER_INDEX_V21", **dict(container)},
            )
    for image in snapshot.get("container_images", []):
        if isinstance(image, Mapping):
            project(
                f"01_NODE_INDEX/{node_id}/images/{_slug(image.get('image_id'))}",
                {"schema_id": "W7TP_GT_MESH_CONTAINER_IMAGE_INDEX_V21", **dict(image)},
            )
    for volume in snapshot.get("container_volumes", []):
        if isinstance(volume, Mapping):
            project(
                f"01_NODE_INDEX/{node_id}/volumes/{_slug(volume.get('volume_name'))}",
                {"schema_id": "W7TP_GT_MESH_CONTAINER_VOLUME_INDEX_V21", **dict(volume)},
            )
    for network in snapshot.get("container_networks", []):
        if isinstance(network, Mapping):
            project(
                f"01_NODE_INDEX/{node_id}/networks/{_slug(network.get('network_id') or network.get('network_name'))}",
                {"schema_id": "W7TP_GT_MESH_CONTAINER_NETWORK_INDEX_V21", **dict(network)},
            )
    for file_item in snapshot.get("curated_files", []):
        if isinstance(file_item, Mapping):
            project(
                f"02_FILE_INDEX/{node_id}/{_slug(file_item.get('logical_path'))}",
                {"schema_id": "W7TP_GT_MESH_FILE_INDEX_V21", **dict(file_item)},
            )
    project("03_LINEAGE", lineage)
    for listener in snapshot.get("listeners", []):
        if isinstance(listener, Mapping):
            project(f"04_EVIDENCE/listeners/{node_id}", {"schema_id": "W7TP_GT_MESH_LISTENER_EVIDENCE_V21", **dict(listener)})
    for git_item in snapshot.get("git_evidence", []):
        if isinstance(git_item, Mapping):
            if (
                git_item.get("dimension") != "D4_EVIDENCE"
                or git_item.get("authority_state") != "EVIDENCE_ONLY"
                or git_item.get("live_effect_state") != "NOT_ESTABLISHED_BY_GIT"
            ):
                raise MeshHold("HOLD_GIT_EVIDENCE_PROJECTION_GATE")
            project(f"07_GITHUB/{node_id}", {"schema_id": "W7TP_GT_MESH_GIT_D4_EVIDENCE_V21", **dict(git_item)})
    for probe in snapshot.get("probe_evidence", []):
        if isinstance(probe, Mapping):
            project(f"04_EVIDENCE/probes/{node_id}", {"schema_id": "W7TP_GT_MESH_PROBE_EVIDENCE_V21", **dict(probe)})
    project("06_RECONSTRUCTION/packets", packet)
    project("06_RECONSTRUCTION/profiles", profile)
    for receipt in receipts:
        project("08_RECEIPTS", receipt)
    return tuple(emitted)
