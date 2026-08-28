"""Receiver-side object installation, deterministic reconstruction, and receipt."""

from __future__ import annotations

import datetime as dt
from typing import Mapping

from .core import (
    CARRIER_SCHEMA,
    PACKET_RECEIPT_SCHEMA,
    PRIMARY_DECISION_ENGINE,
    SNAPSHOT_SCHEMA,
    TOTAL_FIELD_AUTHORITY_REF,
    MeshConflict,
    MeshHold,
    epoch_seconds,
    require_core,
    utc_now,
    utc_text,
)
from .journal import MeshStorage
from .known_novel_v3 import KnownNovelV3Error, reconstruct_v3_artifact
from .packet import validate_packet, validate_packet_profile_binding
from .control import validate_capability_inventory, validate_control_plane_contract


class MeshReceiver:
    def __init__(self, storage: MeshStorage, *, receiver_node_ref: str) -> None:
        if not isinstance(receiver_node_ref, str) or not receiver_node_ref.startswith("node:"):
            raise MeshHold("HOLD_RECEIVER_NODE_REF_INVALID")
        self.storage = storage
        self.receiver_node_ref = receiver_node_ref

    @staticmethod
    def _carrier_shape(carrier: Mapping[str, object]) -> None:
        if set(carrier) != {
            "schema_id",
            "carrier",
            "carrier_authority",
            "packet_ref",
            "packet",
            "object_packets",
            "created_at",
        }:
            raise MeshHold("HOLD_CARRIER_SHAPE")
        if carrier.get("schema_id") != CARRIER_SCHEMA:
            raise MeshHold("HOLD_CARRIER_SCHEMA")
        if carrier.get("carrier") != "HTTP_OVER_TAILSCALE_OR_LOCAL_NETWORK" or carrier.get("carrier_authority") != "NONE":
            raise MeshConflict("CONFLICT_CARRIER_AUTHORITY_ESCALATION")
        if not isinstance(carrier.get("packet"), Mapping) or not isinstance(carrier.get("object_packets"), list):
            raise MeshHold("HOLD_CARRIER_CONTENT_INVALID")

    def _install_carrier_objects(
        self, carrier: Mapping[str, object]
    ) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
        core = require_core()
        packet = dict(carrier["packet"])
        packet_raw = core.canonical_json_bytes(packet)
        packet_ref = carrier.get("packet_ref")
        if packet_ref != core.sha256_ref(packet_raw):
            raise MeshConflict("CONFLICT_CARRIER_PACKET_REF")
        self.storage.put_exact_bytes(str(packet_ref), packet_raw)
        installed: dict[str, dict[str, object]] = {}
        for item in carrier["object_packets"]:
            if not isinstance(item, Mapping) or set(item) != {"object_ref", "artifact"}:
                raise MeshHold("HOLD_CARRIER_OBJECT_PACKET_SHAPE")
            object_ref = item.get("object_ref")
            artifact = item.get("artifact")
            if not isinstance(object_ref, str) or not isinstance(artifact, Mapping):
                raise MeshHold("HOLD_CARRIER_OBJECT_PACKET_INVALID")
            raw = core.canonical_json_bytes(artifact)
            if object_ref != core.sha256_ref(raw):
                raise MeshConflict("CONFLICT_CARRIER_OBJECT_HASH")
            self.storage.put_exact_bytes(object_ref, raw)
            installed[object_ref] = dict(artifact)
        return packet, installed

    def receive(
        self,
        carrier: Mapping[str, object],
        *,
        now: dt.datetime | None = None,
    ) -> dict[str, object]:
        core = require_core()
        self._carrier_shape(carrier)
        packet, installed = self._install_carrier_objects(carrier)
        validate_packet(packet)
        packet_ref = str(carrier["packet_ref"])
        envelope = packet["envelope"]
        adi = packet["adi"]
        replay = adi["replay_protection"]
        replay_tuple = replay["tuple"]
        profile_candidates = [
            artifact
            for artifact in installed.values()
            if artifact.get("schema_id") == "W7TP_GT_MESH_DOMAIN_PROFILE_V21"
        ]
        if len(profile_candidates) != 1:
            raise MeshHold("HOLD_DOMAIN_PROFILE_CARDINALITY")
        profile = profile_candidates[0]
        validate_packet_profile_binding(packet, profile)
        control_plane = profile["control_plane"]
        capability_ref = control_plane["capability_inventory_ref"]
        task_contract_ref = control_plane["task_envelope_contract_ref"]
        capability_inventory = installed.get(capability_ref)
        task_contract = installed.get(task_contract_ref)
        if capability_inventory is None or task_contract is None:
            raise MeshHold("HOLD_CONTROL_PLANE_OBJECT_NOT_CARRIED")
        validate_capability_inventory(capability_inventory)
        validate_control_plane_contract(task_contract)
        if (
            capability_inventory.get("source_node_ref") != profile.get("source_node_ref")
            or capability_inventory.get("logical_time") != profile.get("logical_time")
        ):
            raise MeshConflict("CONFLICT_CAPABILITY_INVENTORY_COORDINATE")
        if envelope.get("nonce") != replay_tuple.get("nonce") or envelope.get("authority_ref") != replay_tuple.get("authority_ref"):
            raise MeshConflict("CONFLICT_REPLAY_ENVELOPE_BINDING")
        computed_tuple_sha = core.sha256_hex(core.canonical_json_bytes(replay_tuple))
        if computed_tuple_sha != replay.get("tuple_sha256") or computed_tuple_sha != adi["packet_layer"].get("decision_index"):
            raise MeshConflict("CONFLICT_REPLAY_TUPLE_HASH")
        observed_now = now or utc_now()
        issued_epoch = profile.get("issued_at_epoch_seconds")
        expires_epoch = profile.get("expires_at_epoch_seconds")
        ttl_seconds = envelope.get("ttl_seconds")
        if (
            isinstance(issued_epoch, bool)
            or not isinstance(issued_epoch, int)
            or isinstance(expires_epoch, bool)
            or not isinstance(expires_epoch, int)
            or isinstance(ttl_seconds, bool)
            or not isinstance(ttl_seconds, int)
            or expires_epoch != issued_epoch + ttl_seconds
        ):
            raise MeshHold("HOLD_TTL_CONTRACT_INVALID")
        now_epoch = epoch_seconds(observed_now)
        if now_epoch < issued_epoch - 30:
            raise MeshHold("HOLD_PACKET_ISSUED_IN_FUTURE")
        if now_epoch > expires_epoch:
            raise MeshHold("HOLD_PACKET_TTL_EXPIRED")
        transfer = profile["transfer"]
        payload_ref = transfer["payload_object_ref"]
        payload = installed.get(payload_ref)
        if payload is None:
            raise MeshHold("HOLD_PAYLOAD_OBJECT_NOT_CARRIED")
        payload_raw = core.canonical_json_bytes(payload)
        if envelope.get("payload_sha256") != core.sha256_hex(payload_raw):
            raise MeshConflict("CONFLICT_PACKET_PAYLOAD_HASH")
        transfer_mode = transfer["mode"]
        if transfer_mode == "DIRECT_TRANSFER_BASELINE":
            reconstructed = payload_raw
        elif transfer_mode == "W7TP_GENERATIVE_DELTA":
            base_ref = transfer.get("base_snapshot_ref")
            if not isinstance(base_ref, str) or not self.storage.has(base_ref):
                raise MeshHold("HOLD_DELTA_BASE_OBJECT_MISSING")
            base_raw = self.storage.get_bytes(base_ref)
            try:
                reconstructed = core.apply_delta(base_raw, payload)
            except Exception as exc:
                code = getattr(exc, "args", ["HOLD_DELTA_RECONSTRUCTION_FAILED"])[0]
                raise MeshHold(str(code)) from exc
        elif transfer_mode == "W7TP_ADI_KNOWN_NOVEL_V3":
            lookup_object_ref = transfer.get("lookup_object_ref")
            carried_lookup = installed.get(lookup_object_ref) if isinstance(lookup_object_ref, str) else None
            if carried_lookup is None:
                raise MeshHold("HOLD_V3_LOOKUP_OBJECT_NOT_CARRIED")
            try:
                reconstructed = reconstruct_v3_artifact(
                    payload,
                    carried_lookup_profile=carried_lookup,
                )
            except KnownNovelV3Error as exc:
                code = str(exc) or "HOLD_V3_RECONSTRUCTION_FAILED"
                raise MeshHold(code) from exc
        else:
            raise MeshHold("HOLD_TRANSFER_MODE_INVALID")
        target_ref = transfer["target_snapshot_ref"]
        if target_ref != core.sha256_ref(reconstructed):
            raise MeshConflict("CONFLICT_RECONSTRUCTED_TARGET_HASH")
        snapshot = core.canonical_json_loads(reconstructed, require_canonical=True)
        if not isinstance(snapshot, dict) or snapshot.get("schema_id") != SNAPSHOT_SCHEMA:
            raise MeshHold("HOLD_RECONSTRUCTED_SNAPSHOT_SCHEMA")
        if snapshot.get("source_node_ref") != profile.get("source_node_ref") or snapshot.get("logical_time") != profile.get("logical_time"):
            raise MeshConflict("CONFLICT_RECONSTRUCTED_COORDINATE")
        self.storage.put_exact_bytes(target_ref, reconstructed)
        existing_receipt = self.storage.journal.find_receipt(packet_ref)
        if existing_receipt is not None:
            return {**existing_receipt, "delivery_state": "PASS_IDEMPOTENT_ALREADY_RECEIVED"}
        claimed = self.storage.journal.claim_replay(
            authority_ref=str(replay_tuple["authority_ref"]),
            namespace=str(replay_tuple["namespace"]),
            nonce=str(replay_tuple["nonce"]),
            logical_time=int(replay_tuple["logical_time"]),
            tuple_sha256=computed_tuple_sha,
            packet_ref=packet_ref,
            claimed_at=utc_text(observed_now),
        )
        if not claimed:
            existing_receipt = self.storage.journal.find_receipt(packet_ref)
            if existing_receipt is not None:
                return {**existing_receipt, "delivery_state": "PASS_IDEMPOTENT_ALREADY_RECEIVED"}
        packet_digest = packet_ref.removeprefix("sha256:")
        logical_time = int(profile["logical_time"])
        source_node_ref = str(profile["source_node_ref"])
        lineage = {
            "schema_id": "W7TP_GT_MESH_RECEIVER_LINEAGE_V21",
            "append_only": True,
            "packet_ref": packet_ref,
            "parent_packet_ref": None if packet["lineage"]["parent_ref"] == "packet:GENESIS" else packet["lineage"]["parent_ref"],
            "base_snapshot_ref": transfer.get("base_snapshot_ref"),
            "target_snapshot_ref": target_ref,
            "source_node_ref": source_node_ref,
            "receiver_node_ref": self.receiver_node_ref,
            "logical_time": logical_time,
            "reconstructed_at": utc_text(observed_now),
            "verification_state": "PASS_EXACT_CANONICAL_JSON_HASH",
            "authority_state": "CANDIDATE_EVIDENCE_ONLY",
        }
        state = {
            "schema_id": "W7TP_GT_MESH_LOCAL_STATE_V21",
            "state_role": "RECEIVER_RECONSTRUCTED",
            "source_node_ref": source_node_ref,
            "receiver_node_ref": self.receiver_node_ref,
            "logical_time": logical_time,
            "snapshot_ref": target_ref,
            "packet_ref": packet_ref,
            "observed_at": snapshot.get("observed_at"),
            "reconstructed_at": utc_text(observed_now),
            "authority_state": "CANDIDATE_EVIDENCE_ONLY",
            "live_effect_state": "RECONSTRUCTED_METADATA_STATE_ONLY",
        }
        receipt: dict[str, object] = {
            "schema_id": PACKET_RECEIPT_SCHEMA,
            "packet_ref": packet_ref,
            "packet_id": envelope["packet_id"],
            "source_node_ref": source_node_ref,
            "receiver_node_ref": self.receiver_node_ref,
            "logical_time": logical_time,
            "payload_ref": payload_ref,
            "target_snapshot_ref": target_ref,
            "transfer_mode": transfer_mode,
            "received_at": utc_text(observed_now),
            "delivery_state": "PASS_RECEIVED",
            "reconstruction_state": "PASS_EXACT_CANONICAL_JSON_HASH",
            "verification_state": "PASS_STRUCTURAL_CANDIDATE_ONLY",
            "carrier_authority": "NONE",
            "authority_ref": TOTAL_FIELD_AUTHORITY_REF,
            "primary_decision_engine": PRIMARY_DECISION_ENGINE,
            "decision_engine_authority_state": "NOT_AUTHORITY",
            "authority_state": "CANDIDATE_EVIDENCE_ONLY",
            "live_effect_state": "NOT_ESTABLISHED_AS_RUNTIME_EFFECT",
            "final_authority_granted": False,
            "final_seal_state": "NOT_GRANTED",
            "performance_claim_scope": "RECONSTRUCTION_INTEGRITY_ONLY_NO_THROUGHPUT_CLAIM",
            "w7g3_fixed_vector_relation": "CODEC_COMPATIBILITY_ONLY_NOT_MESH_END_TO_END_BENCHMARK",
        }
        # ``receipt_ref`` is the hash of the exact receipt body excluding the
        # response-only reference field, avoiding a circular self-hash.
        receipt_ref = self.storage.put_artifact(receipt)
        receipt_with_ref = {**receipt, "receipt_ref": receipt_ref}
        self.storage.journal.append("packets", packet_digest, packet)
        self.storage.journal.append("lineage", f"{logical_time:020d}-{packet_digest}", lineage)
        self.storage.journal.append("states", f"{logical_time:020d}-{packet_digest}", state)
        self.storage.journal.append("receipts", packet_digest, receipt_with_ref)
        return receipt_with_ref
