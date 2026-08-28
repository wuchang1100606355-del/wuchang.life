"""V2.1 interactive 8D Domain Profile and incremental packet construction."""

from __future__ import annotations

import dataclasses
import datetime as dt
import secrets
from typing import Any, Mapping

from .core import (
    CANONICAL_ID,
    CANONICAL_VERSION,
    DIMENSIONS,
    MESH_PROFILE_SCHEMA,
    MIGRATION_MODE,
    PACKET_CORE,
    PARENT_PATH,
    PARENT_SHA256,
    PARENT_VERSION,
    STATE_FIELD_KIND,
    TOTAL_FIELD_AUTHORITY_REF,
    TRANSITION_FUNCTION,
    CARRIER_SCHEMA,
    MeshConflict,
    MeshHold,
    canonical_binding,
    epoch_seconds,
    object_typed_ref,
    require_core,
    self_hash_excluding,
    utc_now,
    utc_text,
)
from .control import (
    authority_contract,
    build_capability_inventory,
    control_plane_contract,
    validate_capability_inventory,
    validate_control_plane_contract,
)
from .journal import MeshStorage
from .known_novel_v3 import LOOKUP_VERSION, V3_CAPABILITY_REF, build_v3_artifact, lookup_profile


COUPLING_EDGES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("D1_INTENT", ("D2_STATE", "D5_EXECUTION", "D6_GENERATIVE_TRANSMISSION", "D8_ENVELOPE_VERIFICATION")),
    ("D2_STATE", ("D3_COORDINATE", "D4_EVIDENCE", "D6_GENERATIVE_TRANSMISSION", "D7_RISK_QUARANTINE")),
    ("D3_COORDINATE", ("D2_STATE", "D4_EVIDENCE", "D6_GENERATIVE_TRANSMISSION")),
    ("D4_EVIDENCE", ("D2_STATE", "D5_EXECUTION", "D7_RISK_QUARANTINE", "D8_ENVELOPE_VERIFICATION")),
    ("D5_EXECUTION", ("D2_STATE", "D4_EVIDENCE", "D6_GENERATIVE_TRANSMISSION", "D7_RISK_QUARANTINE")),
    ("D6_GENERATIVE_TRANSMISSION", ("D2_STATE", "D3_COORDINATE", "D4_EVIDENCE", "D8_ENVELOPE_VERIFICATION")),
    ("D7_RISK_QUARANTINE", ("D5_EXECUTION", "D6_GENERATIVE_TRANSMISSION", "D8_ENVELOPE_VERIFICATION")),
    ("D8_ENVELOPE_VERIFICATION", ("D1_INTENT", "D2_STATE", "D4_EVIDENCE", "D7_RISK_QUARANTINE")),
)


@dataclasses.dataclass(frozen=True, slots=True)
class BuiltTransfer:
    packet_ref: str
    profile_ref: str
    payload_ref: str
    target_snapshot_ref: str
    carrier_ref: str
    capability_inventory_ref: str
    control_plane_contract_ref: str
    logical_time: int
    transfer_mode: str
    packet: dict[str, object]
    profile: dict[str, object]
    carrier: dict[str, object]
    capability_inventory: dict[str, object]
    control_plane_contract: dict[str, object]


def _is_typed_ref(value: object) -> bool:
    if not isinstance(value, str) or ":" not in value or any(char.isspace() for char in value):
        return False
    prefix, suffix = value.split(":", 1)
    return bool(prefix) and prefix[0].isalpha() and bool(suffix)


def _strongly_connected(edges: Mapping[str, list[str]]) -> bool:
    nodes = set(DIMENSIONS)
    if set(edges) != nodes or any(not set(targets) <= nodes for targets in edges.values()):
        return False

    def visit(graph: Mapping[str, list[str]], start: str) -> set[str]:
        seen: set[str] = set()
        stack = [start]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(graph[node])
        return seen

    if visit(edges, DIMENSIONS[0]) != nodes:
        return False
    reverse = {node: [] for node in nodes}
    for source, targets in edges.items():
        for target in targets:
            reverse[target].append(source)
    return visit(reverse, DIMENSIONS[0]) == nodes


def validate_domain_profile(profile: Mapping[str, object]) -> None:
    if profile.get("schema_id") != MESH_PROFILE_SCHEMA:
        raise MeshHold("HOLD_DOMAIN_PROFILE_SCHEMA")
    if profile.get("canonical_id") != CANONICAL_ID or profile.get("version") != CANONICAL_VERSION:
        raise MeshHold("HOLD_CANONICAL_BINDING_MISMATCH")
    if profile.get("canonical_binding") != canonical_binding():
        raise MeshHold("HOLD_CANONICAL_HASH_BINDING_MISMATCH")
    if profile.get("authority_contract") != authority_contract():
        raise MeshHold("HOLD_TOTAL_FIELD_AUTHORITY_CONTRACT")
    if profile.get("authority_ref") != TOTAL_FIELD_AUTHORITY_REF:
        raise MeshHold("HOLD_TOTAL_FIELD_PROFILE_AUTHORITY_REF")
    if not isinstance(profile.get("packet_id"), str) or not profile.get("packet_id"):
        raise MeshHold("HOLD_PROFILE_PACKET_ID")
    if not isinstance(profile.get("nonce"), str) or len(str(profile.get("nonce"))) < 16:
        raise MeshHold("HOLD_PROFILE_NONCE")
    if not isinstance(profile.get("namespace"), str) or not profile.get("namespace"):
        raise MeshHold("HOLD_PROFILE_NAMESPACE")
    profile_logical_time = profile.get("logical_time")
    if isinstance(profile_logical_time, bool) or not isinstance(profile_logical_time, int) or profile_logical_time < 1:
        raise MeshHold("HOLD_PROFILE_LOGICAL_TIME")
    control_plane = profile.get("control_plane")
    if not isinstance(control_plane, Mapping) or set(control_plane) != {
        "capability_inventory_ref",
        "task_envelope_contract_ref",
        "task_envelope_schema_id",
        "scheduler_interface_state",
        "runtime_execution_state",
    }:
        raise MeshHold("HOLD_CONTROL_PLANE_PROFILE_SHAPE")
    for key in ("capability_inventory_ref", "task_envelope_contract_ref"):
        value = control_plane.get(key)
        if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
            raise MeshHold("HOLD_CONTROL_PLANE_PROFILE_REF")
    if (
        control_plane.get("task_envelope_schema_id") != "W7TP_GT_MESH_CONTROL_TASK_ENVELOPE_V21"
        or control_plane.get("scheduler_interface_state") != "CAPABILITY_DISCOVERY_AND_TASK_VALIDATION_ONLY"
        or control_plane.get("runtime_execution_state") != "NOT_WIRED_NO_SIDE_EFFECT"
    ):
        raise MeshHold("HOLD_CONTROL_PLANE_PROFILE_CONTRACT")
    dimensions = profile.get("dimensions")
    if not isinstance(dimensions, Mapping) or set(dimensions) != set(DIMENSIONS):
        raise MeshHold("HOLD_8D_DIMENSIONS_INCOMPLETE")
    coupling = profile.get("coupling")
    if not isinstance(coupling, Mapping):
        raise MeshHold("HOLD_8D_COUPLING_MISSING")
    if coupling.get("model") != "INTERACTIVE_CLOSED_STATE_FIELD" or coupling.get("flat_field_model") is not False:
        raise MeshHold("HOLD_FLAT_8D_MODEL_FORBIDDEN")
    if coupling.get("transition_function") != TRANSITION_FUNCTION or coupling.get("all_dimensions_required") is not True:
        raise MeshHold("HOLD_8D_TRANSITION_CONTRACT")
    raw_edges = coupling.get("closure_edges")
    if not isinstance(raw_edges, list):
        raise MeshHold("HOLD_8D_CLOSURE_EDGES_MISSING")
    edges: dict[str, list[str]] = {}
    for item in raw_edges:
        if not isinstance(item, Mapping) or not isinstance(item.get("from"), str) or not isinstance(item.get("to"), list):
            raise MeshHold("HOLD_8D_CLOSURE_EDGE_INVALID")
        source = str(item["from"])
        targets = item["to"]
        if not all(isinstance(target, str) for target in targets):
            raise MeshHold("HOLD_8D_CLOSURE_EDGE_INVALID")
        if source in edges:
            raise MeshHold("HOLD_8D_CLOSURE_EDGE_DUPLICATE")
        edges[source] = list(targets)
    if not _strongly_connected(edges):
        raise MeshHold("HOLD_8D_INTERACTION_NOT_CLOSED")
    transfer = profile.get("transfer")
    if not isinstance(transfer, Mapping) or transfer.get("mode") not in {
        "DIRECT_TRANSFER_BASELINE",
        "W7TP_GENERATIVE_DELTA",
        "W7TP_ADI_KNOWN_NOVEL_V3",
    }:
        raise MeshHold("HOLD_TRANSFER_MODE_INVALID")
    for key in ("payload_object_ref", "target_snapshot_ref"):
        value = transfer.get(key)
        if not isinstance(value, str) or not value.startswith("sha256:"):
            raise MeshHold("HOLD_TRANSFER_OBJECT_REF_INVALID")
    if transfer.get("mode") == "W7TP_ADI_KNOWN_NOVEL_V3":
        lookup_object_ref = transfer.get("lookup_object_ref")
        if (
            not isinstance(lookup_object_ref, str)
            or not lookup_object_ref.startswith("sha256:")
            or transfer.get("lookup_version") != LOOKUP_VERSION
        ):
            raise MeshHold("HOLD_V3_LOOKUP_OBJECT_REF")


def _dimension_profile(
    snapshot_ref: str,
    *,
    transfer_mode: str,
    base_snapshot_ref: str | None,
    target_snapshot_ref: str,
) -> dict[str, object]:
    generation_rule = {
        "DIRECT_TRANSFER_BASELINE": "DIRECT_CANONICAL_JSON",
        "W7TP_GENERATIVE_DELTA": "ESTABLISHED_COMMON_PREFIX_SUFFIX_SINGLE_PATCH",
        "W7TP_ADI_KNOWN_NOVEL_V3": "ADI_KNOWN_NOVEL_V3_BLOCK_TOKEN_COORDINATES",
    }[transfer_mode]
    return {
        "D1_INTENT": {
            "intent": "INCREMENTAL_NODE_STATE_OBSERVATION_AND_VERIFIABLE_RECONSTRUCTION",
            "target_equivalence": "L1_EXACT_CANONICAL_JSON_BYTES",
            "authority_effect": "NONE_CANDIDATE_EVIDENCE_ONLY",
        },
        "D2_STATE": {
            "source_state_ref": base_snapshot_ref or "state:GENESIS",
            "candidate_state_ref": target_snapshot_ref,
            "transition": transfer_mode,
        },
        "D3_COORDINATE": {
            "coordinate_profile": "NODE_CONTAINER_SERVICE_LISTENER_CURATED_FILE_METADATA",
            "snapshot_ref": snapshot_ref,
            "git_coordinate_role": "OPTIONAL_D4_EVIDENCE_ONLY_NOT_AUTHORITY",
        },
        "D4_EVIDENCE": {
            "evidence_refs": [target_snapshot_ref],
            "git_evidence_authority_state": "EVIDENCE_ONLY",
            "git_live_effect_state": "NOT_ESTABLISHED_BY_GIT",
        },
        "D5_EXECUTION": {
            "execution": "COLLECT_BUILD_SEND_RECEIVE_RECONSTRUCT_VERIFY_APPEND",
            "write_scope": "ADAPTER_RUNTIME_ROOT_ONLY",
            "activation": False,
        },
        "D6_GENERATIVE_TRANSMISSION": {
            "protocol": "W7TP_GT_MESH_V21",
            "routing": "HTTP_OVER_TAILSCALE_OR_LOCAL_CARRIER",
            "segmentation": "SINGLE_CANONICAL_JSON_ARTIFACT",
            "merge_conditions": ["BASE_HASH_MATCH", "TARGET_HASH_MATCH", "CANONICAL_JSON_VALID"],
            "lookup": "ESTABLISHED_OBJECT_PACKET_STORE",
            "references": [snapshot_ref],
            "generation_rules": [generation_rule],
            "reconstruction_contract": "APPLY_ESTABLISHED_DELTA_THEN_EXACT_HASH_VERIFY",
            "verification_contract": "L1_EXACT_CANONICAL_JSON_BYTES",
            "residual": "DELTA_REPLACEMENT_HEX_OR_BASELINE_CANONICAL_JSON",
            "refill_policy": "HOLD_IF_BASE_OBJECT_MISSING",
            "on_demand_materialization": False,
        },
        "D7_RISK_QUARANTINE": {
            "hard_risks": [],
            "protected_scope": ["TECHNICAL_CONTENT", "PRIVATE_LOOKUP_TABLES", "KEYS", "RUNTIME_INTEGRITY"],
            "decision": "PASS_METADATA_ONLY",
        },
        "D8_ENVELOPE_VERIFICATION": {
            "verification": ["CANONICAL_HASH", "TTL", "NONCE", "REPLAY", "LOGICAL_TIME"],
            "seal_state": "UNSEALED_CANDIDATE",
            "final_authority_granted": False,
        },
    }


def _packet_without_self_hash(
    *,
    packet_id: str,
    nonce: str,
    ttl_seconds: int,
    logical_time: int,
    authority_ref: str,
    namespace: str,
    source_node_ref: str,
    payload_ref: str,
    payload_sha256: str,
    profile_ref: str,
    target_snapshot_ref: str,
    transfer_mode: str,
    lookup_object_ref: str | None,
    parent_packet_ref: str | None,
    parent_snapshot_ref: str | None,
) -> dict[str, object]:
    core = require_core()
    profile_typed = object_typed_ref(profile_ref, "DOMAIN_PROFILE")
    payload_typed = object_typed_ref(payload_ref, "PAYLOAD")
    target_typed = object_typed_ref(target_snapshot_ref, "TARGET_STATE")
    replay_tuple = {
        "authority_ref": authority_ref,
        "namespace": namespace,
        "packet_id": packet_id,
        "nonce": nonce,
        "logical_time": logical_time,
    }
    replay_sha = core.sha256_hex(core.canonical_json_bytes(replay_tuple))
    parent_ref = object_typed_ref(parent_packet_ref, "PACKET") if parent_packet_ref else "packet:GENESIS"
    parent_sha = parent_packet_ref.removeprefix("sha256:") if parent_packet_ref else core.sha256_hex(b"")
    previous_seal = object_typed_ref(parent_snapshot_ref, "PREVIOUS_STATE") if parent_snapshot_ref else "seal:GENESIS"
    changed = list(DIMENSIONS) if parent_snapshot_ref is None else [
        "D2_STATE",
        "D3_COORDINATE",
        "D4_EVIDENCE",
        "D5_EXECUTION",
        "D6_GENERATIVE_TRANSMISSION",
        "D7_RISK_QUARANTINE",
        "D8_ENVELOPE_VERIFICATION",
    ]
    generation_rule_ref = {
        "DIRECT_TRANSFER_BASELINE": "capability:DIRECT_CANONICAL_JSON_V21",
        "W7TP_GENERATIVE_DELTA": "capability:W7TP_BYTE_DELTA_INDEX_V1",
        "W7TP_ADI_KNOWN_NOVEL_V3": V3_CAPABILITY_REF,
    }[transfer_mode]
    lookup_refs = (
        [object_typed_ref(lookup_object_ref, "LOOKUP_PROFILE")]
        if lookup_object_ref is not None
        else ["capability:W7TP_OBJECT_PACKET_STORE_V1"]
    )
    dimension_refs = {
        name: {"profile_ref": f"{profile_typed}.{name}"}
        for name in DIMENSIONS
    }
    dimension_refs["D4_EVIDENCE"] = {
        "profile_ref": f"{profile_typed}.D4_EVIDENCE",
        "evidence_refs": [target_typed],
    }
    dimension_refs["D6_GENERATIVE_TRANSMISSION"] = {
        "protocol_ref": f"{profile_typed}.D6_PROTOCOL",
        "routing_ref": f"{profile_typed}.D6_ROUTING",
        "lookup_refs": lookup_refs,
        "reference_refs": [payload_typed, target_typed],
        "generation_rule_refs": [generation_rule_ref],
        "reconstruction_condition_refs": [f"{profile_typed}.RECONSTRUCTION_CONDITIONS"],
        "equivalent_state_rule_refs": [f"{profile_typed}.L1_EXACT_CANONICAL_JSON_BYTES"],
        "total_field_verifier_ref": "verifier:TOTAL_FIELD_REQUIRED_FOR_FINAL_DECISION",
    }
    dimension_refs["D7_RISK_QUARANTINE"] = {
        "hard_risks": [],
        "quarantine_refs": [f"quarantine:none:{packet_id}"],
        "decision": "PASS",
    }
    dimension_refs["D8_ENVELOPE_VERIFICATION"] = {
        "envelope_ref": f"{profile_typed}.D8_ENVELOPE",
        "verifier_ref": "verifier:SHA256_TTL_NONCE_REPLAY_V21",
        "seal_policy_ref": "seal_policy:TOTAL_FIELD_ONLY",
    }
    packet: dict[str, object] = {
        "canonical_id": CANONICAL_ID,
        "version": CANONICAL_VERSION,
        "canonical_binding": canonical_binding(),
        "packet_core": PACKET_CORE,
        "communication_contract": {
            "primary": "INTENT_COMMUNICATION",
            "secondary": "STATE_FIELD_PACKET_COMMUNICATION",
            "semantic_communication": False,
            "semantic_model_role": "CANDIDATE_EVIDENCE_ONLY",
            "floating_point_required": False,
        },
        "authority_boundary": {
            "cloud_authority": ["CANDIDATE", "EVIDENCE"],
            "llm_authority": ["CANDIDATE", "EVIDENCE"],
            "final_decision_authority": "LOCAL_TOTAL_FIELD",
            "final_seal_authority": "LOCAL_TOTAL_FIELD",
        },
        "state_field": {
            "kind": STATE_FIELD_KIND,
            "dimensions": dimension_refs,
            "coupling": {
                "transition_function": TRANSITION_FUNCTION,
                "current_state_ref": object_typed_ref(parent_snapshot_ref, "CURRENT_STATE") if parent_snapshot_ref else "state:GENESIS",
                "intent_ref": f"{profile_typed}.D1_INTENT",
                "coordinate_ref": f"{profile_typed}.D3_COORDINATE",
                "evidence_refs": [target_typed],
                "execution_ref": f"{profile_typed}.D5_EXECUTION",
                "generation_ref": f"{profile_typed}.D6_GENERATIVE_TRANSMISSION",
                "risk_ref": f"{profile_typed}.D7_RISK_QUARANTINE",
                "verification_ref": f"{profile_typed}.D8_ENVELOPE_VERIFICATION",
                "target_state_ref": target_typed,
                "non_float_execution": True,
            },
        },
        "adi": {
            "packet_layer": {
                "index_kind": "OPAQUE_IRREVERSIBLE_PACKET_DECISION_INDEX",
                "namespace": namespace,
                "decision_index": replay_sha,
                "nonce": nonce,
                "key_version_ref": "key_version:CANDIDATE_STRUCTURAL_HASH_V21",
                "authority_ref": authority_ref,
                "evidence_refs": [target_typed],
                "derivation_ref": "derivation:SHA256_CANONICAL_REPLAY_TUPLE_V21",
                "verifier_ref": "verifier:SHA256_TTL_NONCE_REPLAY_V21",
                "irreversible": True,
                "reversible_identity": False,
                "database_primary_key": False,
                "floating_embedding": False,
            },
            "system_layer": {
                "index_kind": "USER_OWNED_SPATIOTEMPORAL_STATE_INDEX_NETWORK",
                "owner_authority_ref": authority_ref,
                "namespace": namespace,
                "logical_time": logical_time,
                "packet_lineage_refs": [parent_ref],
                "state_transition_ref": f"{profile_typed}.STATE_TRANSITION",
                "evidence_refs": [target_typed],
            },
            "replay_protection": {
                "tuple": replay_tuple,
                "tuple_sha256": replay_sha,
                "logical_time_monotonic": True,
            },
        },
        "lineage": {
            "append_only": True,
            "parent_ref": parent_ref,
            "parent_sha256": parent_sha,
            "previous_seal_ref": previous_seal,
            "logical_time": logical_time,
            "changed_dimensions": changed,
            "transition_evidence_refs": [target_typed],
        },
        "generation": {
            "protocol_native": True,
            "state_ref": target_typed,
            "coordinate_ref": f"{profile_typed}.D3_COORDINATE",
            "lookup_refs": lookup_refs,
            "generation_rule_refs": [generation_rule_ref],
            "reconstruction_condition_refs": [f"{profile_typed}.RECONSTRUCTION_CONDITIONS"],
            "target_state_ref": target_typed,
            "file_movement": False,
        },
        "reconstruction": {
            "local_state_field_ref": f"state_field:{source_node_ref}",
            "lookup_refs": lookup_refs,
            "condition_refs": [f"{profile_typed}.RECONSTRUCTION_CONDITIONS"],
            "equivalent_state_rule_refs": [f"{profile_typed}.L1_EXACT_CANONICAL_JSON_BYTES"],
            "target_state_ref": target_typed,
            "total_field_verifier_ref": "verifier:TOTAL_FIELD_REQUIRED_FOR_FINAL_DECISION",
            "deterministic_operations": [
                "INTEGER",
                "BOOLEAN",
                "SYMBOLIC",
                "LOOKUP",
                "REFERENCE_RESOLUTION",
                "STATE_TRANSITION",
            ],
            "model_output_role": "CANDIDATE_EVIDENCE_ONLY",
        },
        "verification": {
            "mode": "L3_CANDIDATE",
            "method_ref": "method:SHA256_CANONICAL_RECONSTRUCTION_V21",
            "contract_ref": f"{profile_typed}.VERIFICATION_CONTRACT",
            "decision": "HOLD",
            "candidate_refs": [target_typed],
            "local_decision_authority_ref": authority_ref,
            "final_authority_granted": False,
        },
        "protected_refs": {"materials": []},
        "envelope": {
            "packet_id": packet_id,
            "authority_ref": authority_ref,
            "version": CANONICAL_VERSION,
            "ttl_seconds": ttl_seconds,
            "nonce": nonce,
            "payload_sha256": payload_sha256,
            "canonical_json_sha256": "",
            "verifier_ref": "verifier:SHA256_TTL_NONCE_REPLAY_V21",
            "seal_policy_ref": "seal_policy:TOTAL_FIELD_ONLY",
            "seal_state": "UNSEALED_CANDIDATE",
            "final_seal_authority": "LOCAL_TOTAL_FIELD",
        },
    }
    packet["envelope"]["canonical_json_sha256"] = self_hash_excluding(
        packet, container_key="envelope", hash_key="canonical_json_sha256"
    )
    return packet


def validate_packet(packet: Mapping[str, object]) -> None:
    """Exact stdlib structural validator for the pinned V2.1 root profile.

    It enforces every object key set used by the canonical schema, including
    ``additionalProperties=false`` semantics.  It is deliberately not a new
    schema dialect and does not replace the pinned machine-readable schema.
    """

    def obj(value: object, keys: set[str], code: str) -> Mapping[str, object]:
        if not isinstance(value, Mapping) or set(value) != keys:
            raise MeshHold(code)
        return value

    def sha(value: object, code: str) -> str:
        if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise MeshHold(code)
        return value

    def integer(value: object, code: str, minimum: int = 1) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise MeshHold(code)
        return value

    def typed(value: object, code: str) -> str:
        if not _is_typed_ref(value):
            raise MeshHold(code)
        return str(value)

    def refs(value: object, code: str) -> list[object]:
        if not isinstance(value, list) or not value or len({str(item) for item in value}) != len(value):
            raise MeshHold(code)
        for item in value:
            typed(item, code)
        return value

    required = {
        "canonical_id",
        "version",
        "canonical_binding",
        "packet_core",
        "communication_contract",
        "authority_boundary",
        "state_field",
        "adi",
        "lineage",
        "generation",
        "reconstruction",
        "verification",
        "protected_refs",
        "envelope",
    }
    if set(packet) != required:
        raise MeshHold("HOLD_PACKET_TOP_LEVEL_SHAPE")
    if packet.get("canonical_id") != CANONICAL_ID or packet.get("version") != CANONICAL_VERSION:
        raise MeshHold("HOLD_PACKET_CANONICAL_ID")
    binding = obj(packet.get("canonical_binding"), {"canonical_path", "canonical_sha256", "parent_version", "parent_path", "parent_sha256", "migration_mode"}, "HOLD_PACKET_CANONICAL_BINDING_SHAPE")
    if binding != canonical_binding() or packet.get("packet_core") != PACKET_CORE:
        raise MeshHold("HOLD_PACKET_CANONICAL_BINDING")
    communication = obj(packet.get("communication_contract"), {"primary", "secondary", "semantic_communication", "semantic_model_role", "floating_point_required"}, "HOLD_PACKET_COMMUNICATION_SHAPE")
    if communication != {
        "primary": "INTENT_COMMUNICATION",
        "secondary": "STATE_FIELD_PACKET_COMMUNICATION",
        "semantic_communication": False,
        "semantic_model_role": "CANDIDATE_EVIDENCE_ONLY",
        "floating_point_required": False,
    }:
        raise MeshHold("HOLD_PACKET_COMMUNICATION_DRIFT")
    authority = obj(packet.get("authority_boundary"), {"cloud_authority", "llm_authority", "final_decision_authority", "final_seal_authority"}, "HOLD_PACKET_AUTHORITY_SHAPE")
    if (
        authority.get("cloud_authority") != ["CANDIDATE", "EVIDENCE"]
        or authority.get("llm_authority") != ["CANDIDATE", "EVIDENCE"]
        or authority.get("final_decision_authority") != "LOCAL_TOTAL_FIELD"
        or authority.get("final_seal_authority") != "LOCAL_TOTAL_FIELD"
    ):
        raise MeshConflict("CONFLICT_PACKET_AUTHORITY_BOUNDARY")
    field = obj(packet.get("state_field"), {"kind", "dimensions", "coupling"}, "HOLD_PACKET_STATE_FIELD_SHAPE")
    if field.get("kind") != STATE_FIELD_KIND:
        raise MeshHold("HOLD_PACKET_STATE_FIELD_KIND")
    dimensions = field.get("dimensions")
    if not isinstance(dimensions, Mapping) or set(dimensions) != set(DIMENSIONS):
        raise MeshHold("HOLD_PACKET_8D_INCOMPLETE")
    for name in ("D1_INTENT", "D2_STATE", "D3_COORDINATE", "D5_EXECUTION"):
        item = obj(dimensions[name], {"profile_ref"}, "HOLD_PACKET_PROFILE_DIMENSION_SHAPE")
        typed(item.get("profile_ref"), "HOLD_PACKET_PROFILE_REF")
    d4 = obj(dimensions["D4_EVIDENCE"], {"profile_ref", "evidence_refs"}, "HOLD_PACKET_D4_SHAPE")
    typed(d4.get("profile_ref"), "HOLD_PACKET_D4_REF")
    refs(d4.get("evidence_refs"), "HOLD_PACKET_D4_EVIDENCE_REFS")
    d6 = obj(dimensions["D6_GENERATIVE_TRANSMISSION"], {"protocol_ref", "routing_ref", "lookup_refs", "reference_refs", "generation_rule_refs", "reconstruction_condition_refs", "equivalent_state_rule_refs", "total_field_verifier_ref"}, "HOLD_PACKET_D6_SHAPE")
    typed(d6.get("protocol_ref"), "HOLD_PACKET_D6_REF")
    typed(d6.get("routing_ref"), "HOLD_PACKET_D6_REF")
    typed(d6.get("total_field_verifier_ref"), "HOLD_PACKET_D6_REF")
    for key in ("lookup_refs", "reference_refs", "generation_rule_refs", "reconstruction_condition_refs", "equivalent_state_rule_refs"):
        refs(d6.get(key), "HOLD_PACKET_D6_REFS")
    d7 = obj(dimensions["D7_RISK_QUARANTINE"], {"hard_risks", "quarantine_refs", "decision"}, "HOLD_PACKET_D7_SHAPE")
    if not isinstance(d7.get("hard_risks"), list) or d7.get("decision") not in {"PASS", "HOLD", "BLOCK"}:
        raise MeshHold("HOLD_PACKET_D7_CONTRACT")
    refs(d7.get("quarantine_refs"), "HOLD_PACKET_D7_REFS")
    d8 = obj(dimensions["D8_ENVELOPE_VERIFICATION"], {"envelope_ref", "verifier_ref", "seal_policy_ref"}, "HOLD_PACKET_D8_SHAPE")
    for key in d8:
        typed(d8[key], "HOLD_PACKET_D8_REF")
    coupling = obj(field.get("coupling"), {"transition_function", "current_state_ref", "intent_ref", "coordinate_ref", "evidence_refs", "execution_ref", "generation_ref", "risk_ref", "verification_ref", "target_state_ref", "non_float_execution"}, "HOLD_PACKET_COUPLING_SHAPE")
    if coupling.get("transition_function") != TRANSITION_FUNCTION or coupling.get("non_float_execution") is not True:
        raise MeshHold("HOLD_PACKET_COUPLING_INVALID")
    for key in ("current_state_ref", "intent_ref", "coordinate_ref", "execution_ref", "generation_ref", "risk_ref", "verification_ref", "target_state_ref"):
        typed(coupling.get(key), "HOLD_PACKET_COUPLING_REF")
    refs(coupling.get("evidence_refs"), "HOLD_PACKET_COUPLING_EVIDENCE")
    adi = obj(packet.get("adi"), {"packet_layer", "system_layer", "replay_protection"}, "HOLD_PACKET_ADI_SHAPE")
    packet_layer = obj(adi.get("packet_layer"), {"index_kind", "namespace", "decision_index", "nonce", "key_version_ref", "authority_ref", "evidence_refs", "derivation_ref", "verifier_ref", "irreversible", "reversible_identity", "database_primary_key", "floating_embedding"}, "HOLD_PACKET_ADI_PACKET_SHAPE")
    if packet_layer.get("index_kind") != "OPAQUE_IRREVERSIBLE_PACKET_DECISION_INDEX" or packet_layer.get("irreversible") is not True or any(packet_layer.get(key) is not False for key in ("reversible_identity", "database_primary_key", "floating_embedding")):
        raise MeshHold("HOLD_PACKET_ADI_PACKET_CONTRACT")
    sha(packet_layer.get("decision_index"), "HOLD_PACKET_ADI_DECISION_INDEX")
    if not isinstance(packet_layer.get("namespace"), str) or not packet_layer.get("namespace"):
        raise MeshHold("HOLD_PACKET_ADI_NAMESPACE")
    if not isinstance(packet_layer.get("nonce"), str) or len(str(packet_layer.get("nonce"))) < 16:
        raise MeshHold("HOLD_PACKET_ADI_NONCE")
    for key in ("key_version_ref", "authority_ref", "derivation_ref", "verifier_ref"):
        typed(packet_layer.get(key), "HOLD_PACKET_ADI_PACKET_REF")
    if packet_layer.get("authority_ref") != TOTAL_FIELD_AUTHORITY_REF:
        raise MeshConflict("CONFLICT_TOTAL_FIELD_AUTHORITY_REF")
    refs(packet_layer.get("evidence_refs"), "HOLD_PACKET_ADI_EVIDENCE")
    system_layer = obj(adi.get("system_layer"), {"index_kind", "owner_authority_ref", "namespace", "logical_time", "packet_lineage_refs", "state_transition_ref", "evidence_refs"}, "HOLD_PACKET_ADI_SYSTEM_SHAPE")
    if system_layer.get("index_kind") != "USER_OWNED_SPATIOTEMPORAL_STATE_INDEX_NETWORK":
        raise MeshHold("HOLD_PACKET_ADI_SYSTEM_KIND")
    typed(system_layer.get("owner_authority_ref"), "HOLD_PACKET_ADI_SYSTEM_REF")
    if system_layer.get("owner_authority_ref") != TOTAL_FIELD_AUTHORITY_REF:
        raise MeshConflict("CONFLICT_TOTAL_FIELD_OWNER_AUTHORITY_REF")
    typed(system_layer.get("state_transition_ref"), "HOLD_PACKET_ADI_SYSTEM_REF")
    integer(system_layer.get("logical_time"), "HOLD_PACKET_ADI_LOGICAL_TIME")
    if not isinstance(system_layer.get("namespace"), str) or not system_layer.get("namespace"):
        raise MeshHold("HOLD_PACKET_ADI_SYSTEM_NAMESPACE")
    refs(system_layer.get("packet_lineage_refs"), "HOLD_PACKET_ADI_LINEAGE_REFS")
    refs(system_layer.get("evidence_refs"), "HOLD_PACKET_ADI_EVIDENCE")
    replay = obj(adi.get("replay_protection"), {"tuple", "tuple_sha256", "logical_time_monotonic"}, "HOLD_PACKET_REPLAY_SHAPE")
    replay_tuple = obj(replay.get("tuple"), {"authority_ref", "namespace", "packet_id", "nonce", "logical_time"}, "HOLD_PACKET_REPLAY_TUPLE_SHAPE")
    typed(replay_tuple.get("authority_ref"), "HOLD_PACKET_REPLAY_AUTHORITY_REF")
    if replay_tuple.get("authority_ref") != TOTAL_FIELD_AUTHORITY_REF:
        raise MeshConflict("CONFLICT_TOTAL_FIELD_REPLAY_AUTHORITY_REF")
    integer(replay_tuple.get("logical_time"), "HOLD_PACKET_REPLAY_LOGICAL_TIME")
    for key in ("namespace", "packet_id", "nonce"):
        if not isinstance(replay_tuple.get(key), str) or not replay_tuple.get(key):
            raise MeshHold("HOLD_PACKET_REPLAY_COORDINATE")
    sha(replay.get("tuple_sha256"), "HOLD_PACKET_REPLAY_SHA")
    if replay.get("logical_time_monotonic") is not True:
        raise MeshHold("HOLD_PACKET_REPLAY_MONOTONIC")
    computed_replay_sha = require_core().sha256_hex(require_core().canonical_json_bytes(replay_tuple))
    if replay.get("tuple_sha256") != computed_replay_sha or packet_layer.get("decision_index") != computed_replay_sha:
        raise MeshConflict("CONFLICT_PACKET_REPLAY_TUPLE_HASH")
    lineage = obj(packet.get("lineage"), {"append_only", "parent_ref", "parent_sha256", "previous_seal_ref", "logical_time", "changed_dimensions", "transition_evidence_refs"}, "HOLD_PACKET_LINEAGE_SHAPE")
    if lineage.get("append_only") is not True:
        raise MeshHold("HOLD_PACKET_LINEAGE_APPEND_ONLY")
    typed(lineage.get("parent_ref"), "HOLD_PACKET_LINEAGE_REF")
    typed(lineage.get("previous_seal_ref"), "HOLD_PACKET_LINEAGE_REF")
    sha(lineage.get("parent_sha256"), "HOLD_PACKET_LINEAGE_SHA")
    integer(lineage.get("logical_time"), "HOLD_PACKET_LINEAGE_TIME")
    if not (
        packet_layer.get("namespace") == system_layer.get("namespace") == replay_tuple.get("namespace")
        and packet_layer.get("nonce") == replay_tuple.get("nonce")
        and system_layer.get("logical_time") == replay_tuple.get("logical_time") == lineage.get("logical_time")
    ):
        raise MeshConflict("CONFLICT_PACKET_ADI_LINEAGE_BINDING")
    changed = lineage.get("changed_dimensions")
    if not isinstance(changed, list) or not changed or len(set(changed)) != len(changed) or not set(changed) <= set(DIMENSIONS):
        raise MeshHold("HOLD_PACKET_LINEAGE_CHANGED_DIMENSIONS")
    refs(lineage.get("transition_evidence_refs"), "HOLD_PACKET_LINEAGE_EVIDENCE")
    generation = obj(packet.get("generation"), {"protocol_native", "state_ref", "coordinate_ref", "lookup_refs", "generation_rule_refs", "reconstruction_condition_refs", "target_state_ref", "file_movement"}, "HOLD_PACKET_GENERATION_SHAPE")
    if generation.get("protocol_native") is not True or generation.get("file_movement") is not False:
        raise MeshHold("HOLD_PACKET_GENERATION_CONTRACT")
    for key in ("state_ref", "coordinate_ref", "target_state_ref"):
        typed(generation.get(key), "HOLD_PACKET_GENERATION_REF")
    for key in ("lookup_refs", "generation_rule_refs", "reconstruction_condition_refs"):
        refs(generation.get(key), "HOLD_PACKET_GENERATION_REFS")
    reconstruction = obj(packet.get("reconstruction"), {"local_state_field_ref", "lookup_refs", "condition_refs", "equivalent_state_rule_refs", "target_state_ref", "total_field_verifier_ref", "deterministic_operations", "model_output_role"}, "HOLD_PACKET_RECONSTRUCTION_SHAPE")
    for key in ("local_state_field_ref", "target_state_ref", "total_field_verifier_ref"):
        typed(reconstruction.get(key), "HOLD_PACKET_RECONSTRUCTION_REF")
    for key in ("lookup_refs", "condition_refs", "equivalent_state_rule_refs"):
        refs(reconstruction.get(key), "HOLD_PACKET_RECONSTRUCTION_REFS")
    if reconstruction.get("deterministic_operations") != ["INTEGER", "BOOLEAN", "SYMBOLIC", "LOOKUP", "REFERENCE_RESOLUTION", "STATE_TRANSITION"] or reconstruction.get("model_output_role") != "CANDIDATE_EVIDENCE_ONLY":
        raise MeshHold("HOLD_PACKET_RECONSTRUCTION_CONTRACT")
    verification = obj(packet.get("verification"), {"mode", "method_ref", "contract_ref", "decision", "candidate_refs", "local_decision_authority_ref", "final_authority_granted"}, "HOLD_PACKET_VERIFICATION_SHAPE")
    if verification.get("mode") != "L3_CANDIDATE" or verification.get("decision") not in {"HOLD", "BLOCK"} or verification.get("final_authority_granted") is not False:
        raise MeshConflict("CONFLICT_PACKET_AUTHORITY_ESCALATION")
    for key in ("method_ref", "contract_ref", "local_decision_authority_ref"):
        typed(verification.get(key), "HOLD_PACKET_VERIFICATION_REF")
    if verification.get("local_decision_authority_ref") != TOTAL_FIELD_AUTHORITY_REF:
        raise MeshConflict("CONFLICT_TOTAL_FIELD_VERIFICATION_AUTHORITY_REF")
    refs(verification.get("candidate_refs"), "HOLD_PACKET_VERIFICATION_REFS")
    protected = obj(packet.get("protected_refs"), {"materials"}, "HOLD_PACKET_PROTECTED_REFS_SHAPE")
    if not isinstance(protected.get("materials"), list):
        raise MeshHold("HOLD_PACKET_PROTECTED_REFS")
    for material in protected["materials"]:
        entry = obj(material, {"kind", "reference", "disclosure"}, "HOLD_PACKET_PROTECTED_ENTRY_SHAPE")
        if entry.get("kind") not in {"H64_TD", "CODEBOOK", "MAPPING_TABLE", "RECOVERY_MATERIAL"} or entry.get("disclosure") != "REFERENCE_ONLY":
            raise MeshHold("HOLD_PACKET_PROTECTED_ENTRY")
        typed(entry.get("reference"), "HOLD_PACKET_PROTECTED_REF")
    envelope = obj(packet.get("envelope"), {"packet_id", "authority_ref", "version", "ttl_seconds", "nonce", "payload_sha256", "canonical_json_sha256", "verifier_ref", "seal_policy_ref", "seal_state", "final_seal_authority"}, "HOLD_PACKET_ENVELOPE_SHAPE")
    typed(envelope.get("authority_ref"), "HOLD_PACKET_ENVELOPE_AUTHORITY_REF")
    if envelope.get("authority_ref") != TOTAL_FIELD_AUTHORITY_REF:
        raise MeshConflict("CONFLICT_TOTAL_FIELD_ENVELOPE_AUTHORITY_REF")
    typed(envelope.get("verifier_ref"), "HOLD_PACKET_ENVELOPE_VERIFIER_REF")
    typed(envelope.get("seal_policy_ref"), "HOLD_PACKET_ENVELOPE_SEAL_REF")
    if not isinstance(envelope.get("packet_id"), str) or not envelope.get("packet_id"):
        raise MeshHold("HOLD_PACKET_ENVELOPE_PACKET_ID")
    if not isinstance(envelope.get("nonce"), str) or len(str(envelope.get("nonce"))) < 16:
        raise MeshHold("HOLD_PACKET_ENVELOPE_NONCE")
    integer(envelope.get("ttl_seconds"), "HOLD_PACKET_TTL")
    sha(envelope.get("payload_sha256"), "HOLD_PACKET_PAYLOAD_SHA")
    sha(envelope.get("canonical_json_sha256"), "HOLD_PACKET_CANONICAL_SHA")
    claimed = envelope.get("canonical_json_sha256")
    if claimed != self_hash_excluding(dict(packet), container_key="envelope", hash_key="canonical_json_sha256"):
        raise MeshConflict("CONFLICT_PACKET_CANONICAL_SELF_HASH")
    if envelope.get("packet_id") != replay_tuple.get("packet_id") or envelope.get("nonce") != replay_tuple.get("nonce"):
        raise MeshConflict("CONFLICT_PACKET_ENVELOPE_REPLAY_BINDING")
    if envelope.get("version") != CANONICAL_VERSION or envelope.get("seal_state") != "UNSEALED_CANDIDATE" or envelope.get("final_seal_authority") != "LOCAL_TOTAL_FIELD":
        raise MeshHold("HOLD_PACKET_ENVELOPE_STATE")


def validate_packet_profile_binding(
    packet: Mapping[str, object],
    profile: Mapping[str, object],
) -> None:
    """Cross-bind every shared packet/profile replay coordinate."""

    validate_packet(packet)
    validate_domain_profile(profile)
    packet_layer = packet["adi"]["packet_layer"]
    system_layer = packet["adi"]["system_layer"]
    replay_tuple = packet["adi"]["replay_protection"]["tuple"]
    lineage = packet["lineage"]
    verification = packet["verification"]
    envelope = packet["envelope"]
    if not (
        profile.get("packet_id") == replay_tuple.get("packet_id") == envelope.get("packet_id")
        and profile.get("namespace")
        == packet_layer.get("namespace")
        == system_layer.get("namespace")
        == replay_tuple.get("namespace")
        and profile.get("nonce") == packet_layer.get("nonce") == replay_tuple.get("nonce") == envelope.get("nonce")
        and profile.get("logical_time")
        == system_layer.get("logical_time")
        == replay_tuple.get("logical_time")
        == lineage.get("logical_time")
        and profile.get("authority_ref")
        == packet_layer.get("authority_ref")
        == system_layer.get("owner_authority_ref")
        == replay_tuple.get("authority_ref")
        == verification.get("local_decision_authority_ref")
        == envelope.get("authority_ref")
        == TOTAL_FIELD_AUTHORITY_REF
    ):
        raise MeshConflict("CONFLICT_PACKET_PROFILE_REPLAY_BINDING")


def build_transfer(
    storage: MeshStorage,
    snapshot: dict[str, object],
    *,
    authority_ref: str,
    namespace: str,
    ttl_seconds: int = 300,
    now: dt.datetime | None = None,
) -> BuiltTransfer:
    """Build baseline or economic delta using only the established bridge."""

    if authority_ref != TOTAL_FIELD_AUTHORITY_REF or not isinstance(namespace, str) or len(namespace) < 3:
        raise MeshHold("HOLD_AUTHORITY_OR_NAMESPACE_REF_INVALID")
    if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or not 1 <= ttl_seconds <= 86_400:
        raise MeshHold("HOLD_TTL_INVALID")
    core = require_core()
    source_node_ref = snapshot.get("source_node_ref")
    logical_time = snapshot.get("logical_time")
    if not isinstance(source_node_ref, str) or not _is_typed_ref(source_node_ref):
        raise MeshHold("HOLD_SOURCE_NODE_REF_INVALID")
    if isinstance(logical_time, bool) or not isinstance(logical_time, int) or logical_time < 1:
        raise MeshHold("HOLD_LOGICAL_TIME_INVALID")
    target_bytes = core.canonical_json_bytes(snapshot)
    target_ref = storage.put_exact_bytes(core.sha256_ref(target_bytes), target_bytes)
    previous_state = storage.journal.latest_state(source_node_ref)
    base_ref: str | None = None
    parent_packet_ref: str | None = None
    def marginal_object_packets_bytes(
        artifact: dict[str, object],
        raw: bytes,
        *extra_artifacts: dict[str, object],
    ) -> int:
        objects: list[dict[str, object]] = [
            {"object_ref": core.sha256_ref(raw), "artifact": artifact}
        ]
        for extra in extra_artifacts:
            extra_raw = core.canonical_json_bytes(extra)
            objects.append({"object_ref": core.sha256_ref(extra_raw), "artifact": extra})
        # List brackets are common carrier bytes.  The remaining bytes are the
        # exact mode-specific object-packet interiors, including commas and the
        # complete lookup profile/object wrapper when a mode requires one.
        return len(core.canonical_json_bytes(objects)) - 2

    direct_marginal_bytes = marginal_object_packets_bytes(snapshot, target_bytes)
    candidates: list[tuple[str, dict[str, object], bytes, str | None, int]] = [
        ("DIRECT_TRANSFER_BASELINE", snapshot, target_bytes, target_ref, direct_marginal_bytes)
    ]
    delta_size: int | None = None
    delta_marginal_bytes: int | None = None
    delta_state = "NOT_APPLICABLE_NO_BASE"
    if previous_state is not None:
        base_ref_raw = previous_state.get("snapshot_ref")
        if not isinstance(base_ref_raw, str):
            raise MeshConflict("CONFLICT_PREVIOUS_STATE_SNAPSHOT_REF")
        base_ref = base_ref_raw
        parent_packet_raw = previous_state.get("packet_ref")
        parent_packet_ref = parent_packet_raw if isinstance(parent_packet_raw, str) else None
        base_bytes = storage.get_bytes(base_ref)
        try:
            delta = core.build_delta(base_bytes, target_bytes)
        except Exception:
            delta_state = "HOLD_ESTABLISHED_DELTA_BUILD_FAILED"
        else:
            delta_bytes = core.canonical_json_bytes(delta)
            delta_size = len(delta_bytes)
            delta_marginal_bytes = marginal_object_packets_bytes(delta, delta_bytes)
            delta_state = "CANDIDATE_AVAILABLE"
            candidates.append(("W7TP_GENERATIVE_DELTA", delta, delta_bytes, None, delta_marginal_bytes))
    v3_result = build_v3_artifact(target_bytes)
    v3_size: int | None = None
    v3_body_bytes: int | None = None
    v3_marginal_bytes: int | None = None
    v3_lookup = lookup_profile()
    v3_lookup_raw = core.canonical_json_bytes(v3_lookup)
    v3_lookup_object_packet_bytes = len(
        core.canonical_json_bytes(
            {"object_ref": core.sha256_ref(v3_lookup_raw), "artifact": v3_lookup}
        )
    )
    if v3_result is not None:
        v3_artifact, v3_bytes = v3_result
        v3_size = len(v3_bytes)
        v3_body_bytes = int(v3_artifact["body_bytes"])
        v3_marginal_bytes = marginal_object_packets_bytes(v3_artifact, v3_bytes, v3_lookup)
        candidates.append(("W7TP_ADI_KNOWN_NOVEL_V3", v3_artifact, v3_bytes, None, v3_marginal_bytes))
    transfer_mode, payload, payload_bytes, existing_payload_ref, selected_marginal_bytes = min(
        candidates,
        key=lambda item: (
            item[4],
            {
                "DIRECT_TRANSFER_BASELINE": 0,
                "W7TP_GENERATIVE_DELTA": 1,
                "W7TP_ADI_KNOWN_NOVEL_V3": 2,
            }[item[0]],
        ),
    )
    payload_ref = existing_payload_ref or storage.put_exact_bytes(core.sha256_ref(payload_bytes), payload_bytes)
    carried_lookup = v3_lookup if transfer_mode == "W7TP_ADI_KNOWN_NOVEL_V3" else None
    lookup_object_ref = storage.put_artifact(carried_lookup) if carried_lookup is not None else None
    economic = {
        "decision": {
            "DIRECT_TRANSFER_BASELINE": "DIRECT_TRANSFER",
            "W7TP_GENERATIVE_DELTA": "W7TP_GENERATIVE_SINGLE_DELTA",
            "W7TP_ADI_KNOWN_NOVEL_V3": "W7TP_GENERATIVE_V3_BLOCK_TOKEN",
        }[transfer_mode],
        "source_size_bytes": len(target_bytes),
        "direct_payload_bytes": len(target_bytes),
        "direct_marginal_carrier_bytes": direct_marginal_bytes,
        "single_delta_payload_bytes": delta_size,
        "single_delta_marginal_carrier_bytes": delta_marginal_bytes,
        "single_delta_state": delta_state,
        "v3_block_token_payload_bytes": v3_size,
        "v3_marginal_carrier_bytes": v3_marginal_bytes,
        "v3_binary_body_bytes": v3_body_bytes,
        "v3_lookup_profile_bytes": len(v3_lookup_raw),
        "v3_lookup_object_packet_bytes": v3_lookup_object_packet_bytes,
        "v3_canonical_wire_wrapper_overhead_bytes": (
            v3_size - v3_body_bytes if v3_size is not None and v3_body_bytes is not None else None
        ),
        "v3_state": "CANDIDATE_AVAILABLE" if v3_size is not None else "NOT_APPLICABLE",
        "selected_payload_bytes": len(payload_bytes),
        "selected_marginal_carrier_bytes": selected_marginal_bytes,
        "selection_rule": "MIN_EXACT_MODE_SPECIFIC_OBJECT_PACKET_BYTES_TIE_FEWEST_DEPENDENCIES",
        "synthetic_throughput_claim": False,
    }
    observed_now = now or utc_now()
    issued_epoch = epoch_seconds(observed_now)
    packet_id = f"w7tp-gt-v21-{source_node_ref.split(':', 1)[1]}-{logical_time}-{secrets.token_hex(8)}"
    nonce = secrets.token_hex(16)
    capability_inventory = build_capability_inventory(snapshot)
    validate_capability_inventory(capability_inventory)
    capability_inventory_ref = storage.put_artifact(capability_inventory)
    task_contract = control_plane_contract()
    validate_control_plane_contract(task_contract)
    task_contract_ref = storage.put_artifact(task_contract)
    profile: dict[str, object] = {
        "schema_id": MESH_PROFILE_SCHEMA,
        "canonical_id": CANONICAL_ID,
        "version": CANONICAL_VERSION,
        "canonical_binding": canonical_binding(),
        "authority_contract": authority_contract(),
        "control_plane": {
            "capability_inventory_ref": capability_inventory_ref,
            "task_envelope_contract_ref": task_contract_ref,
            "task_envelope_schema_id": "W7TP_GT_MESH_CONTROL_TASK_ENVELOPE_V21",
            "scheduler_interface_state": "CAPABILITY_DISCOVERY_AND_TASK_VALIDATION_ONLY",
            "runtime_execution_state": "NOT_WIRED_NO_SIDE_EFFECT",
        },
        "domain_profile": "NODE_CONTAINER_SERVICE_LISTENER_CURATED_FILE_METADATA",
        "packet_id": packet_id,
        "nonce": nonce,
        "authority_ref": authority_ref,
        "source_node_ref": source_node_ref,
        "namespace": namespace,
        "logical_time": logical_time,
        "issued_at": utc_text(observed_now),
        "issued_at_epoch_seconds": issued_epoch,
        "expires_at_epoch_seconds": issued_epoch + ttl_seconds,
        "authority_state": "TOTAL_FIELD_UNIQUE_AUTHORITY_PACKET_CANDIDATE",
        "carrier_authority": "NONE",
        "transfer": {
            "mode": transfer_mode,
            "payload_object_ref": payload_ref,
            "base_snapshot_ref": base_ref,
            "target_snapshot_ref": target_ref,
            "lookup_object_ref": lookup_object_ref,
            "lookup_version": LOOKUP_VERSION if lookup_object_ref is not None else None,
            "economic_gate": economic,
        },
        "dimensions": _dimension_profile(
            target_ref,
            transfer_mode=transfer_mode,
            base_snapshot_ref=base_ref,
            target_snapshot_ref=target_ref,
        ),
        "coupling": {
            "model": "INTERACTIVE_CLOSED_STATE_FIELD",
            "flat_field_model": False,
            "transition_function": TRANSITION_FUNCTION,
            "all_dimensions_required": True,
            "closure_edges": [
                {"from": source, "to": list(targets)}
                for source, targets in COUPLING_EDGES
            ],
        },
        "reconstruction_conditions": [
            "BASE_HASH_MATCH_IF_DELTA",
            "PAYLOAD_HASH_MATCH",
            "TARGET_HASH_MATCH",
            "CANONICAL_JSON_EXACT",
            "TTL_VALID",
            "NONCE_UNUSED_OR_EXACT_IDEMPOTENCE",
            "LOGICAL_TIME_MONOTONIC",
        ],
        "verification_contract": {
            "mode": "L1_EXACT_CANONICAL_JSON_BYTES",
            "structural_decision": "PASS_OR_HOLD_OR_BLOCK",
            "final_authority_granted": False,
        },
    }
    validate_domain_profile(profile)
    profile_ref = storage.put_artifact(profile)
    packet = _packet_without_self_hash(
        packet_id=packet_id,
        nonce=nonce,
        ttl_seconds=ttl_seconds,
        logical_time=logical_time,
        authority_ref=authority_ref,
        namespace=namespace,
        source_node_ref=source_node_ref,
        payload_ref=payload_ref,
        payload_sha256=core.sha256_hex(payload_bytes),
        profile_ref=profile_ref,
        target_snapshot_ref=target_ref,
        transfer_mode=transfer_mode,
        lookup_object_ref=lookup_object_ref,
        parent_packet_ref=parent_packet_ref,
        parent_snapshot_ref=base_ref,
    )
    validate_packet(packet)
    packet_ref = storage.put_artifact(packet)
    carrier: dict[str, object] = {
        "schema_id": CARRIER_SCHEMA,
        "carrier": "HTTP_OVER_TAILSCALE_OR_LOCAL_NETWORK",
        "carrier_authority": "NONE",
        "packet_ref": packet_ref,
        "packet": packet,
        "object_packets": [
            {"object_ref": profile_ref, "artifact": profile},
            {"object_ref": payload_ref, "artifact": payload},
            {"object_ref": capability_inventory_ref, "artifact": capability_inventory},
            {"object_ref": task_contract_ref, "artifact": task_contract},
        ]
        + ([{"object_ref": lookup_object_ref, "artifact": carried_lookup}] if carried_lookup is not None else []),
        "created_at": utc_text(observed_now),
    }
    carrier_ref = storage.put_artifact(carrier)
    digest = packet_ref.removeprefix("sha256:")
    lineage = {
        "schema_id": "W7TP_GT_MESH_LINEAGE_V21",
        "append_only": True,
        "packet_ref": packet_ref,
        "parent_packet_ref": parent_packet_ref,
        "base_snapshot_ref": base_ref,
        "target_snapshot_ref": target_ref,
        "source_node_ref": source_node_ref,
        "logical_time": logical_time,
        "created_at": utc_text(observed_now),
        "authority_state": "CANDIDATE_EVIDENCE_ONLY",
    }
    state = {
        "schema_id": "W7TP_GT_MESH_LOCAL_STATE_V21",
        "state_role": "SOURCE_OBSERVATION",
        "source_node_ref": source_node_ref,
        "logical_time": logical_time,
        "snapshot_ref": target_ref,
        "packet_ref": packet_ref,
        "observed_at": snapshot.get("observed_at"),
        "authority_state": "EVIDENCE_ONLY",
        "live_effect_state": "NOT_ESTABLISHED_BY_METADATA",
    }
    storage.journal.append("packets", digest, packet)
    storage.journal.append("lineage", f"{logical_time:020d}-{digest}", lineage)
    storage.journal.append("states", f"{logical_time:020d}-{digest}", state)
    storage.journal.append(
        "outbound",
        f"{logical_time:020d}-{digest}",
        {
            "schema_id": "W7TP_GT_MESH_OUTBOUND_V21",
            "packet_ref": packet_ref,
            "carrier_ref": carrier_ref,
            "source_node_ref": source_node_ref,
            "logical_time": logical_time,
            "transfer_mode": transfer_mode,
            "created_at": utc_text(observed_now),
        },
    )
    return BuiltTransfer(
        packet_ref=packet_ref,
        profile_ref=profile_ref,
        payload_ref=payload_ref,
        target_snapshot_ref=target_ref,
        carrier_ref=carrier_ref,
        capability_inventory_ref=capability_inventory_ref,
        control_plane_contract_ref=task_contract_ref,
        logical_time=logical_time,
        transfer_mode=transfer_mode,
        packet=packet,
        profile=profile,
        carrier=carrier,
        capability_inventory=capability_inventory,
        control_plane_contract=task_contract,
    )
