#!/usr/bin/env python3
"""Detached verifier for intent-field candidates and execution receipts."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import stat
import sys
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Mapping, Sequence, Tuple

import build_intent_field_candidate as producer
import intent_field_construct as structural


Hold = structural.ConstructionHold
PACKET_NAME = structural.PACKET_NAME
SHA_NAME = structural.SHA_NAME
SEAL_NAME = structural.SEAL_NAME
MAX_ARTIFACT_BYTES = 4 * 1024 * 1024
MAX_TTL_SECONDS = 15 * 60
RUNTIME_INITIAL_RESULTS = {"PASS", "EVIDENCE_GAP"}
TRANSFER_EVIDENCE_STAGES = (
    "PROGRAM_TRANSFER_RUBBING",
    "RECEIVER_RECONSTRUCTION",
    "EQUIVALENT_STATE_VERIFICATION",
)
STRUCTURE_RESULT = "STRUCTURE_AND_HASH_CHECK_PASS"
HASH_CHAIN_VALID = "HASH_CHAIN_VALID"
FINAL_STATES = [
    "CANDIDATE",
    "RUNTIME_EVIDENCE_UNVERIFIED",
    "USER_JOURNEY_EVIDENCE_UNVERIFIED",
    "CROSS_NODE_REPLAY_UNVERIFIED",
    "AUTHENTICITY_UNVERIFIED",
    "ACTIVATION_NOT_AUTHORIZED",
]
EQUIVALENCE_METHOD = "PUBLIC_CANONICAL_JSON_SHA256_EQUIVALENCE_V1"
SELF_CRYPTO_CLAIM_KEYS = (
    "public_key",
    "self_signature",
    "signature",
    "self_signed",
    "verification_receipt",
    "verification_receipt_ref",
    "verification_receipt_sha256",
)

DETACHED_CANDIDATE_RELATIONS = {
    "CONTINUE",
    "FUSE",
    "REPLACE",
    "PARALLEL_SHADOW",
    "ISOLATE",
    "HOLD",
}
DETACHED_CONTINUATION_AXES = (
    "semantic",
    "structure_contract",
    "dependency",
    "tests",
    "runtime_wiring",
    "data_migration",
    "governance_authority",
    "security",
    "cross_node",
    "recovery",
)
DETACHED_RELATION_HARD_GATES = {
    "CONTINUE": {"input_output_contract", "dependencies", "version"},
    "FUSE": {
        "overlapping_supply",
        "priority",
        "dual_execution_risk",
        "authority_conflict",
    },
    "REPLACE": {
        "all_consumers",
        "behavioral_equivalence",
        "data_migration",
        "exit_and_recovery",
    },
    "PARALLEL_SHADOW": {"isolation", "no_effect", "no_mainline_impact"},
    "ISOLATE": {"unrelated_or_risk_boundary"},
    "HOLD": set(),
}
DETACHED_SUPPLY_GAP_FIELDS = (
    "uncovered_demands",
    "extra_side_effects",
    "unknown_dynamic_consumers",
    "dependency_cycles",
    "authority_conflicts",
)
DETACHED_RECOVERY_STEPS = ("expand", "migrate", "deprecate")


def _relative_parts(ref: Any, path: str) -> Tuple[str, ...]:
    value = structural.require_str(ref, path, max_bytes=512)
    if "\\" in value or ":" in value:
        raise Hold("HOLD_NONLOCAL_PATH", path)
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or not parsed.parts or any(part in {".", ".."} for part in parsed.parts):
        raise Hold("HOLD_NONLOCAL_PATH", path)
    return tuple(parsed.parts)


def _root_path(value: Path) -> Path:
    if not value.is_absolute() or value.is_symlink() or not value.is_dir():
        raise Hold("HOLD_WORKTREE_ROOT", "$.worktree_root")
    return value.resolve()


def read_worktree_file(root: Path, ref: Any, path: str, limit: int = MAX_ARTIFACT_BYTES) -> bytes:
    parts = _relative_parts(ref, path)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    current_fd = os.open(root, os.O_RDONLY | directory | nofollow)
    try:
        for part in parts[:-1]:
            next_fd = os.open(part, os.O_RDONLY | directory | nofollow, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        file_fd = os.open(parts[-1], os.O_RDONLY | nofollow, dir_fd=current_fd)
        try:
            info = os.fstat(file_fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
                raise Hold("HOLD_ARTIFACT_TYPE_OR_SIZE", path)
            chunks = []
            remaining = limit + 1
            while remaining:
                chunk = os.read(file_fd, min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            value = b"".join(chunks)
            if len(value) > limit:
                raise Hold("HOLD_ARTIFACT_TYPE_OR_SIZE", path)
            return value
        finally:
            os.close(file_fd)
    except (FileNotFoundError, NotADirectoryError, OSError) as error:
        if isinstance(error, Hold):
            raise
        raise Hold("HOLD_ARTIFACT_PATH", path) from None
    finally:
        os.close(current_fd)


def read_json(root: Path, ref: Any, path: str) -> Tuple[Any, str]:
    raw = read_worktree_file(root, ref, path)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise Hold("HOLD_ARTIFACT_JSON", path) from None
    producer.sanitize_for_structure(value, path)
    return value, hashlib.sha256(raw).hexdigest()


def _json_artifact_ref(ref: Any, path: str) -> str:
    parts = _relative_parts(ref, path)
    if not parts[-1].endswith(".json"):
        raise Hold("HOLD_ARTIFACT_JSON_REF", path)
    return "/".join(parts)


def read_canonical_json(
    root: Path,
    ref: Any,
    path: str,
    *,
    source_zone: bool = False,
    expected_sha_raw: Any = None,
    hash_hold_code: str = "HOLD_ARTIFACT_HASH",
) -> Tuple[Dict[str, Any], str, str]:
    normalized_ref = _json_artifact_ref(ref, path)
    raw = read_worktree_file(root, normalized_ref, path)
    actual_sha = hashlib.sha256(raw).hexdigest()
    if expected_sha_raw is not None and actual_sha != structural.require_sha256(expected_sha_raw, f"{path}_sha256"):
        raise Hold(hash_hold_code, path)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise Hold("HOLD_ARTIFACT_JSON", path) from None
    if raw != structural.canonical_bytes(value) + b"\n":
        raise Hold("HOLD_NON_CANONICAL_JSON", path)
    producer.sanitize_for_structure(value, path, source_zone=source_zone)
    return structural.require_dict(value, f"{path}.artifact"), actual_sha, normalized_ref


def read_verified_json(
    root: Path,
    ref: Any,
    expected_sha_raw: Any,
    path: str,
    hash_hold_code: str,
) -> Tuple[Dict[str, Any], str, str]:
    normalized_ref = _json_artifact_ref(ref, path)
    artifact, actual_sha = read_json(root, normalized_ref, path)
    expected_sha = structural.require_sha256(expected_sha_raw, f"{path}_sha256")
    if actual_sha != expected_sha:
        raise Hold(hash_hold_code, path)
    return structural.require_dict(artifact, f"{path}.artifact"), actual_sha, normalized_ref


def _parse_time(value: Any, path: str) -> dt.datetime:
    text = structural.require_str(value, path, max_bytes=64)
    try:
        parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise Hold("HOLD_TIME_FORMAT", path) from None
    if parsed.tzinfo is None:
        raise Hold("HOLD_TIMEZONE_REQUIRED", path)
    return parsed.astimezone(dt.timezone.utc)


def _required_pass(value: Mapping[str, Any], name: str, path: str) -> None:
    if value.get(name) != "PASS":
        raise Hold("HOLD_RECEIPT_GATE", f"{path}.{name}")


def _runner_binding(value: Mapping[str, Any], path: str) -> Tuple[str, str]:
    runner = structural.require_str(value.get("runner"), f"{path}.runner", max_bytes=256)
    runner_version = structural.require_str(
        value.get("runner_version"), f"{path}.runner_version", max_bytes=128
    )
    if value.get("runner_verdict") != "UNVERIFIED":
        raise Hold("HOLD_RUNNER_VERDICT_SCOPE", f"{path}.runner_verdict")
    return runner, runner_version


def _str_list(value: Any, path: str, *, nonempty: bool = False) -> list[str]:
    return [
        structural.require_str(item, f"{path}[{index}]", max_bytes=512)
        for index, item in enumerate(structural.require_list(value, path, nonempty=nonempty))
    ]


def _hash_canonical(value: Any) -> str:
    return structural.sha256_bytes(structural.canonical_bytes(value))


def _detached_nonempty_refs(value: Any, path: str) -> list[str]:
    return _str_list(value, path, nonempty=True)


def verify_relational_contract(
    root: Path,
    spec: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> Dict[str, Any]:
    """Independently validate relational semantics and its content-addressed evidence."""
    main = structural.require_dict(spec.get("mainline_relation"), "$.mainline_relation")
    distance = structural.require_dict(spec.get("continuation_distance"), "$.continuation_distance")
    supply = structural.require_dict(spec.get("supply_demand_fit"), "$.supply_demand_fit")
    binding = structural.require_dict(spec.get("relational_evidence"), "$.relational_evidence")
    if (
        candidate.get("mainline_relation") != main
        or candidate.get("continuation_distance") != distance
        or candidate.get("supply_demand_fit") != supply
        or candidate.get("relational_evidence") != binding
    ):
        raise Hold("HOLD_RELATIONAL_CANDIDATE_TAMPER", "$.candidate")

    if set(main) != {
        "candidate_relation",
        "hard_gates",
        "missing_gates",
        "first_breakpoint",
        "shortest_continuation_route",
    }:
        raise Hold("HOLD_MAINLINE_RELATION_SHAPE", "$.mainline_relation")
    relation = structural.require_str(
        main.get("candidate_relation"), "$.mainline_relation.candidate_relation", max_bytes=32
    )
    if relation not in DETACHED_CANDIDATE_RELATIONS:
        raise Hold("HOLD_CANDIDATE_RELATION", "$.mainline_relation.candidate_relation")
    hard_gates = structural.require_dict(
        main.get("hard_gates"), "$.mainline_relation.hard_gates"
    )
    all_gate_names = set().union(*DETACHED_RELATION_HARD_GATES.values())
    if relation == "HOLD":
        valid_gate_set = set(hard_gates).issubset(all_gate_names)
    else:
        valid_gate_set = set(hard_gates) == DETACHED_RELATION_HARD_GATES[relation]
    if not valid_gate_set:
        raise Hold("HOLD_RELATION_GATE_SET", "$.mainline_relation.hard_gates")
    nonpass_gates: set[str] = set()
    for gate_name, raw in hard_gates.items():
        path = f"$.mainline_relation.hard_gates.{gate_name}"
        gate = structural.require_dict(raw, path)
        if set(gate) != {"state", "evidence_refs"}:
            raise Hold("HOLD_RELATION_GATE_SHAPE", path)
        state = structural.require_str(gate.get("state"), f"{path}.state", max_bytes=16)
        if state not in {"PASS", "FAIL", "UNKNOWN"}:
            raise Hold("HOLD_RELATION_GATE_STATE", f"{path}.state")
        _detached_nonempty_refs(gate.get("evidence_refs"), f"{path}.evidence_refs")
        if state != "PASS":
            nonpass_gates.add(gate_name)

    missing = _str_list(main.get("missing_gates"), "$.mainline_relation.missing_gates")
    if len(missing) != len(set(missing)):
        raise Hold("HOLD_DUPLICATE_VALUE", "$.mainline_relation.missing_gates")
    first = main.get("first_breakpoint")
    route = structural.require_list(
        main.get("shortest_continuation_route"),
        "$.mainline_relation.shortest_continuation_route",
        nonempty=False,
    )
    if missing:
        if first != missing[0] or not route:
            raise Hold("HOLD_RELATION_BREAKPOINT_ROUTE", "$.mainline_relation")
    elif first is not None or route:
        raise Hold("HOLD_RELATION_BREAKPOINT_ROUTE", "$.mainline_relation")
    for index, raw in enumerate(route):
        path = f"$.mainline_relation.shortest_continuation_route[{index}]"
        item = structural.require_dict(raw, path)
        if set(item) != {"step", "evidence_refs"}:
            raise Hold("HOLD_RELATION_ROUTE_SHAPE", path)
        structural.require_str(item.get("step"), f"{path}.step", max_bytes=256)
        _detached_nonempty_refs(item.get("evidence_refs"), f"{path}.evidence_refs")

    if set(distance) != set(DETACHED_CONTINUATION_AXES):
        raise Hold("HOLD_CONTINUATION_AXIS_SET", "$.continuation_distance")
    unknown_axes: set[str] = set()
    for axis in DETACHED_CONTINUATION_AXES:
        path = f"$.continuation_distance.{axis}"
        item = structural.require_dict(distance.get(axis), path)
        if set(item) != {"state", "evidence_refs"}:
            raise Hold("HOLD_CONTINUATION_AXIS_SHAPE", path)
        state = structural.require_str(item.get("state"), f"{path}.state", max_bytes=16)
        if state not in {"ALIGNED", "DELTA", "UNKNOWN"}:
            raise Hold("HOLD_CONTINUATION_AXIS_STATE", f"{path}.state")
        _detached_nonempty_refs(item.get("evidence_refs"), f"{path}.evidence_refs")
        if state == "UNKNOWN":
            unknown_axes.add(axis)

    expected_supply_keys = {
        "old_demand_set",
        "new_supply_mapping",
        "recovery_route",
        *DETACHED_SUPPLY_GAP_FIELDS,
    }
    if set(supply) != expected_supply_keys:
        raise Hold("HOLD_SUPPLY_DEMAND_SHAPE", "$.supply_demand_fit")
    old_demands = structural.require_list(
        supply.get("old_demand_set"), "$.supply_demand_fit.old_demand_set"
    )
    demand_ids: set[str] = set()
    for index, raw in enumerate(old_demands):
        path = f"$.supply_demand_fit.old_demand_set[{index}]"
        item = structural.require_dict(raw, path)
        if set(item) != {"id", "evidence_refs"}:
            raise Hold("HOLD_SUPPLY_DEMAND_ITEM_SHAPE", path)
        demand_id = structural.require_str(item.get("id"), f"{path}.id", max_bytes=128)
        if demand_id in demand_ids:
            raise Hold("HOLD_DUPLICATE_VALUE", f"{path}.id")
        demand_ids.add(demand_id)
        _detached_nonempty_refs(item.get("evidence_refs"), f"{path}.evidence_refs")
    mapped_ids: set[str] = set()
    for index, raw in enumerate(
        structural.require_list(
            supply.get("new_supply_mapping"),
            "$.supply_demand_fit.new_supply_mapping",
            nonempty=False,
        )
    ):
        path = f"$.supply_demand_fit.new_supply_mapping[{index}]"
        item = structural.require_dict(raw, path)
        if set(item) != {"demand_id", "supply_ids", "evidence_refs"}:
            raise Hold("HOLD_SUPPLY_MAPPING_SHAPE", path)
        demand_id = structural.require_str(
            item.get("demand_id"), f"{path}.demand_id", max_bytes=128
        )
        if demand_id not in demand_ids or demand_id in mapped_ids:
            raise Hold("HOLD_SUPPLY_MAPPING_DEMAND", f"{path}.demand_id")
        mapped_ids.add(demand_id)
        _str_list(item.get("supply_ids"), f"{path}.supply_ids", nonempty=True)
        _detached_nonempty_refs(item.get("evidence_refs"), f"{path}.evidence_refs")
    gap_ids: Dict[str, set[str]] = {}
    for name in DETACHED_SUPPLY_GAP_FIELDS:
        gap_ids[name] = set()
        for index, raw in enumerate(
            structural.require_list(
                supply.get(name), f"$.supply_demand_fit.{name}", nonempty=False
            )
        ):
            path = f"$.supply_demand_fit.{name}[{index}]"
            item = structural.require_dict(raw, path)
            if set(item) != {"id", "evidence_refs"}:
                raise Hold("HOLD_SUPPLY_DEMAND_ITEM_SHAPE", path)
            item_id = structural.require_str(item.get("id"), f"{path}.id", max_bytes=128)
            if item_id in gap_ids[name]:
                raise Hold("HOLD_DUPLICATE_VALUE", f"{path}.id")
            gap_ids[name].add(item_id)
            _detached_nonempty_refs(item.get("evidence_refs"), f"{path}.evidence_refs")
    uncovered = gap_ids["uncovered_demands"]
    if not uncovered.issubset(demand_ids) or mapped_ids | uncovered != demand_ids or mapped_ids & uncovered:
        raise Hold("HOLD_SUPPLY_DEMAND_COVERAGE", "$.supply_demand_fit")
    recovery = structural.require_list(
        supply.get("recovery_route"), "$.supply_demand_fit.recovery_route"
    )
    if len(recovery) != len(DETACHED_RECOVERY_STEPS):
        raise Hold("HOLD_RECOVERY_ROUTE", "$.supply_demand_fit.recovery_route")
    for index, step in enumerate(DETACHED_RECOVERY_STEPS):
        path = f"$.supply_demand_fit.recovery_route[{index}]"
        item = structural.require_dict(recovery[index], path)
        if set(item) != {"step", "evidence_refs", "rollback"} or item.get("step") != step:
            raise Hold("HOLD_RECOVERY_ROUTE", path)
        _detached_nonempty_refs(item.get("evidence_refs"), f"{path}.evidence_refs")
        rollback = structural.require_dict(item.get("rollback"), f"{path}.rollback")
        if set(rollback) != {"action", "evidence_refs"}:
            raise Hold("HOLD_RECOVERY_ROUTE", f"{path}.rollback")
        structural.require_str(rollback.get("action"), f"{path}.rollback.action", max_bytes=256)
        _detached_nonempty_refs(
            rollback.get("evidence_refs"), f"{path}.rollback.evidence_refs"
        )

    required_missing = {f"continuation_distance.{axis}" for axis in unknown_axes}
    required_missing.update(
        f"mainline_relation.hard_gates.{gate}" for gate in nonpass_gates
    )
    required_missing.update(
        f"supply_demand_fit.{name}"
        for name, values in gap_ids.items()
        if values
    )
    if not required_missing.issubset(set(missing)):
        raise Hold("HOLD_RELATION_MISSING_GATE_BINDING", "$.mainline_relation.missing_gates")
    if unknown_axes and relation != "HOLD":
        raise Hold("HOLD_RELATION_UNKNOWN_REQUIRES_HOLD", "$.mainline_relation")
    if required_missing and relation not in {"PARALLEL_SHADOW", "HOLD"}:
        raise Hold("HOLD_SUPPLY_DEMAND_RELATION_CONFLICT", "$.mainline_relation")
    if relation != "HOLD" and nonpass_gates:
        raise Hold("HOLD_RELATION_HARD_GATE_CONFLICT", "$.mainline_relation")
    if relation == "HOLD" and not missing:
        raise Hold("HOLD_RELATION_REQUIRES_BREAKPOINT", "$.mainline_relation")

    if set(binding) != {
        "evidence_class",
        "artifact_ref",
        "artifact_sha256",
        "stage_receipt_ref",
        "stage_receipt_sha256",
    } or binding.get("evidence_class") != "FIELD_EVIDENCE":
        raise Hold("HOLD_RELATIONAL_EVIDENCE_BINDING", "$.relational_evidence")
    artifact, artifact_sha, artifact_ref = read_canonical_json(
        root,
        binding.get("artifact_ref"),
        "$.relational_evidence.artifact_ref",
        expected_sha_raw=binding.get("artifact_sha256"),
        hash_hold_code="HOLD_RELATIONAL_EVIDENCE_HASH",
    )
    expected_artifact = {
        "schema_id": "IFGC_RELATIONAL_EVIDENCE_V1",
        "input_revision": spec.get("revision"),
        "evidence_class": "FIELD_EVIDENCE",
        "runner_verdict": "UNVERIFIED",
        "mainline_relation": main,
        "continuation_distance": distance,
        "supply_demand_fit": supply,
    }
    if artifact != expected_artifact:
        raise Hold("HOLD_RELATIONAL_EVIDENCE_CONFLICT", "$.relational_evidence.artifact_ref")
    stage, stage_sha, stage_ref = read_canonical_json(
        root,
        binding.get("stage_receipt_ref"),
        "$.relational_evidence.stage_receipt_ref",
        expected_sha_raw=binding.get("stage_receipt_sha256"),
        hash_hold_code="HOLD_RELATIONAL_STAGE_RECEIPT_HASH",
    )
    expected_stage = {
        "schema_id": "IFGC_RELATIONAL_STAGE_RECEIPT_V1",
        "input_revision": spec.get("revision"),
        "evidence_class": "FIELD_EVIDENCE",
        "artifact_ref": artifact_ref,
        "artifact_sha256": artifact_sha,
        "state": "STAGED",
        "runner_verdict": "UNVERIFIED",
        "grants_authority": False,
    }
    if stage != expected_stage or artifact_ref == stage_ref:
        raise Hold("HOLD_RELATIONAL_STAGE_RECEIPT_CONFLICT", "$.relational_evidence.stage_receipt_ref")
    relational_hash = _hash_canonical(
        {
            "mainline_relation": main,
            "continuation_distance": distance,
            "supply_demand_fit": supply,
            "relational_evidence": binding,
        }
    )
    if candidate.get("producer", {}).get("relational_contract_sha256") != relational_hash:
        raise Hold("HOLD_RELATIONAL_PRODUCER_BINDING", "$.candidate.producer")
    return {
        "state": "STRUCTURE_AND_HASH_CHECK_PASS",
        "candidate_relation": relation,
        "continuation_axis_states": {
            axis: distance[axis]["state"] for axis in DETACHED_CONTINUATION_AXES
        },
        "supply_gap_counts": {
            name: len(supply[name]) for name in DETACHED_SUPPLY_GAP_FIELDS
        },
        "artifact_ref": artifact_ref,
        "artifact_sha256": artifact_sha,
        "stage_receipt_ref": stage_ref,
        "stage_receipt_sha256": stage_sha,
        "grants_authority": False,
    }


def _expect_io(
    receipt: Mapping[str, Any],
    artifact: Mapping[str, Any],
    input_sha256: str,
    output_sha256: str,
    path: str,
    hold_code: str,
) -> None:
    if (
        structural.require_sha256(receipt.get("input_sha256"), f"{path}.input_sha256") != input_sha256
        or structural.require_sha256(receipt.get("output_sha256"), f"{path}.output_sha256") != output_sha256
        or artifact.get("input_sha256") != input_sha256
        or artifact.get("output_sha256") != output_sha256
    ):
        raise Hold(hold_code, path)


def _fallback_retrieval_output_sha(
    source_class: str,
    target_gap_refs: Sequence[str],
    input_revision: str,
    candidate_sha: str,
) -> str:
    return _hash_canonical(
        {
            "artifact_kind": "FALLBACK_RETRIEVAL",
            "source_class": source_class,
            "target_gap_refs": list(target_gap_refs),
            "input_revision": input_revision,
            "candidate_packet_sha256": candidate_sha,
        }
    )


def _verify_eight_d_runtime_artifact(
    candidate: Mapping[str, Any],
    artifact: Mapping[str, Any],
    path: str,
) -> None:
    eight_d = structural.require_dict(artifact.get("eight_d"), f"{path}.artifact.eight_d")
    if eight_d != candidate["eight_d"]:
        raise Hold("HOLD_RUNTIME_8D_ARTIFACT_BINDING", path)
    if eight_d.get("definition") != structural.HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD:
        raise Hold("HOLD_RUNTIME_8D_DEFINITION", path)
    if eight_d.get("not_ninth_dimension") is not True:
        raise Hold("HOLD_RUNTIME_8D_NOT_NINTH_DIMENSION", path)
    dimensions = structural.require_dict(eight_d.get("dimensions"), f"{path}.artifact.eight_d.dimensions")
    if set(dimensions) != set(structural.EIGHT_D_KEYS):
        raise Hold("HOLD_RUNTIME_8D_DIMENSION_SET", path)
    dynamic = structural.require_dict(eight_d.get("dynamic_depth"), f"{path}.artifact.eight_d.dynamic_depth")
    selected = dynamic.get("selected_depth")
    included = _str_list(dynamic.get("included_dimensions"), f"{path}.artifact.eight_d.dynamic_depth.included_dimensions")
    omitted = _str_list(dynamic.get("omitted_dimensions"), f"{path}.artifact.eight_d.dynamic_depth.omitted_dimensions")
    if (
        not isinstance(selected, int)
        or isinstance(selected, bool)
        or len(included) != selected
        or set(included) | set(omitted) != set(structural.EIGHT_D_KEYS)
        or set(included) & set(omitted)
    ):
        raise Hold("HOLD_RUNTIME_8D_SELECTED_DEPTH", path)
    if (
        dynamic.get("authority_effect") != "NONE"
        or dynamic.get("authority_granted") is not False
        or dynamic.get("resource_saving_only") is not False
        or dynamic.get("dynamic_arrangement_is_authority") is not False
    ):
        raise Hold("HOLD_RUNTIME_8D_AUTHORITY_SCOPE", path)


def core_function_subject_sha256(candidate: Mapping[str, Any], function_name: str) -> str:
    if function_name == "ANALYSIS":
        subject = {
            "eight_d": candidate["eight_d"],
            "runtime_completion_chain": candidate["runtime_completion_chain"],
            "architecture": candidate["architecture"],
            "mainline_relation": candidate["mainline_relation"],
            "continuation_distance": candidate["continuation_distance"],
            "supply_demand_fit": candidate["supply_demand_fit"],
        }
    elif function_name == "ADDRESSING":
        subject = {
            "adi_map": candidate["adi_map"],
            "mainline_relation": candidate["mainline_relation"],
            "continuation_distance": candidate["continuation_distance"],
            "supply_demand_fit": candidate["supply_demand_fit"],
        }
    elif function_name == "CONSTRUCTION":
        subject = {
            "code_reconstruction": candidate["code_reconstruction"],
            "closure": candidate["closure"],
        }
    elif function_name == "TRANSFER":
        subject = candidate["transfer"]
    else:
        raise Hold("HOLD_CORE_FUNCTION_RECEIPT_SET", "$.verification.core_function_receipts")
    return _hash_canonical(subject)


def transfer_packet_sha256(
    input_revision: str,
    candidate_sha: str,
    invariant_sha: str,
    recipe_manifest_sha: str,
) -> str:
    return _hash_canonical(
        {
            "protocol": structural.PROTOCOL,
            "version": structural.PROTOCOL_VERSION,
            "input_revision": input_revision,
            "candidate_sha256": candidate_sha,
            "invariant_sha256": invariant_sha,
            "recipe_manifest_sha256": recipe_manifest_sha,
        }
    )


def expected_cross_node_transfer_object(
    candidate: Mapping[str, Any],
    candidate_sha: str,
    transfer_result: Mapping[str, Any],
) -> Dict[str, Any]:
    invariant = dict(_candidate_transfer_invariant(candidate))
    return {
        "protocol": structural.PROTOCOL,
        "version": structural.PROTOCOL_VERSION,
        "revision": candidate["revision"],
        "candidate_sha256": candidate_sha,
        "TRANSFER_INVARIANT": invariant,
        "invariant_sha256": transfer_result["invariant_sha256"],
        "recipe_manifest_sha256": transfer_result["recipe_manifest_sha256"],
        "transfer_packet_sha256": transfer_result["transfer_packet_sha256"],
        "full_source_embedded": False,
        "semantic_reconstruction": True,
        "byte_identity_claim": False,
    }


def _candidate_transfer_invariant(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    invariant = structural.require_dict(candidate["transfer"]["invariant"], "$.candidate.transfer.invariant")
    if "value" in invariant:
        return structural.require_dict(invariant["value"], "$.candidate.transfer.invariant.value")
    return invariant


def _candidate_trade_secret_boundary(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    boundary = structural.require_dict(candidate["trade_secret_boundary"], "$.candidate.trade_secret_boundary")
    if "value" in boundary:
        return structural.require_dict(boundary["value"], "$.candidate.trade_secret_boundary.value")
    return boundary


def verify_journeys(
    root: Path, spec: Mapping[str, Any], bundle: Mapping[str, Any]
) -> Dict[str, Any]:
    expected = {item["id"]: item for item in spec["user_journeys"]}
    receipts_raw = structural.require_list(bundle.get("journey_receipts"), "$.verification.journey_receipts")
    receipts: Dict[str, Any] = {}
    result: Dict[str, Any] = {}
    scenarios: set[str] = set()
    surfaces: set[str] = set()
    not_applicable_with_evidence = False
    for index, raw in enumerate(receipts_raw):
        path = f"$.verification.journey_receipts[{index}]"
        receipt = structural.require_dict(raw, path)
        journey_id = structural.require_str(receipt.get("journey_id"), f"{path}.journey_id", max_bytes=128)
        if journey_id in receipts or journey_id not in expected:
            raise Hold("HOLD_JOURNEY_RECEIPT_SET", path)
        receipts[journey_id] = receipt
        journey = expected[journey_id]
        if receipt.get("executed") is not True or receipt.get("result") != "PASS":
            raise Hold("HOLD_JOURNEY_NOT_EXECUTED_PASS", path)
        if receipt.get("input_revision") != spec["revision"] or receipt.get("role") != journey["role"]:
            raise Hold("HOLD_JOURNEY_BINDING", path)
        if receipt.get("scenario") != journey["scenario"] or receipt.get("surface") != journey["surface"]:
            raise Hold("HOLD_JOURNEY_BINDING", path)
        if receipt.get("runner_verdict") != "UNVERIFIED":
            raise Hold("HOLD_RUNNER_VERDICT_SCOPE", f"{path}.runner_verdict")
        scenarios.add(journey["scenario"])
        surfaces.add(journey["surface"])
        if journey["surface"] == "NOT_APPLICABLE_WITH_EVIDENCE":
            not_applicable_with_evidence = bool(journey["evidence_refs"])
        entrypoint = structural.require_str(receipt.get("actual_entrypoint"), f"{path}.actual_entrypoint", max_bytes=512)
        runner = structural.require_str(receipt.get("runner"), f"{path}.runner", max_bytes=256)
        runner_version = structural.require_str(receipt.get("runner_version"), f"{path}.runner_version", max_bytes=128)
        artifact_ref = receipt.get("artifact_ref")
        trace, actual_sha = read_json(root, artifact_ref, f"{path}.artifact_ref")
        expected_sha = structural.require_sha256(receipt.get("artifact_sha256"), f"{path}.artifact_sha256")
        if actual_sha != expected_sha:
            raise Hold("HOLD_JOURNEY_ARTIFACT_HASH", path)
        trace = structural.require_dict(trace, f"{path}.artifact")
        if (
            trace.get("journey_id") != journey_id
            or trace.get("role") != journey["role"]
            or trace.get("scenario") != journey["scenario"]
            or trace.get("surface") != journey["surface"]
            or trace.get("input_revision") != spec["revision"]
            or trace.get("actual_entrypoint") != entrypoint
            or trace.get("runner") != runner
            or trace.get("runner_version") != runner_version
            or trace.get("runner_verdict") != "UNVERIFIED"
            or trace.get("executed") is not True
            or trace.get("result") != "PASS"
        ):
            raise Hold("HOLD_JOURNEY_ARTIFACT_BINDING", path)
        trace_steps = structural.require_list(trace.get("steps"), f"{path}.artifact.steps")
        if len(trace_steps) != len(journey["steps"]):
            raise Hold("HOLD_JOURNEY_STEP_COUNT", path)
        for step_index, step_raw in enumerate(trace_steps):
            step = structural.require_dict(step_raw, f"{path}.artifact.steps[{step_index}]")
            if step.get("executed") is not True or step.get("status") != "PASS":
                raise Hold("HOLD_JOURNEY_STEP", f"{path}.artifact.steps[{step_index}]")
        for flag in (
            "feedback_verified",
            "error_recovery_tested",
            "accessibility_tested",
            "authorization_boundary_tested",
            "exit_tested",
        ):
            if trace.get(flag) is not True:
                raise Hold("HOLD_JOURNEY_SCENARIO", f"{path}.artifact.{flag}")
        if journey["kind"] == "DENIAL_OR_RECOVERY" and trace.get("partial_effects") is not False:
            raise Hold("HOLD_JOURNEY_PARTIAL_EFFECT", path)
        result[journey_id] = {
            "verifier_result": STRUCTURE_RESULT,
            "evidence_state": "UNVERIFIED",
            "claimed_executed": receipt.get("executed"),
            "claimed_result": receipt.get("result"),
            "artifact_ref": "/".join(_relative_parts(artifact_ref, f"{path}.artifact_ref")),
            "artifact_sha256": actual_sha,
            "runner": runner,
            "runner_version": runner_version,
            "runner_verdict": "UNVERIFIED",
            "actual_entrypoint": entrypoint,
        }
    if set(receipts) != set(expected):
        raise Hold("HOLD_JOURNEY_RECEIPT_SET", "$.verification.journey_receipts")
    if scenarios != structural.JOURNEY_SCENARIOS:
        raise Hold("HOLD_JOURNEY_SCENARIO_SET_INCOMPLETE", "$.verification.journey_receipts")
    if not {"DESKTOP", "MOBILE"}.issubset(surfaces) and not not_applicable_with_evidence:
        raise Hold("HOLD_JOURNEY_SURFACE_SET_INCOMPLETE", "$.verification.journey_receipts")
    return result


def verify_redteam(
    root: Path, candidate_sha: str, bundle: Mapping[str, Any]
) -> Dict[str, Any]:
    receipts = structural.require_dict(bundle.get("redteam_receipts"), "$.verification.redteam_receipts")
    stage_names = list(structural.REDTEAM_CHECKS)
    if set(receipts) != set(stage_names):
        raise Hold("HOLD_REDTEAM_RECEIPT_SET", "$.verification.redteam_receipts")
    previous = structural.require_sha256(
        bundle.get("construction_input_sha256"), "$.verification.construction_input_sha256"
    )
    result: Dict[str, Any] = {}
    for stage_index, stage_name in enumerate(stage_names):
        path = f"$.verification.redteam_receipts.{stage_name}"
        stage = structural.require_dict(receipts[stage_name], path)
        rounds = structural.require_list(stage.get("rounds"), f"{path}.rounds")
        if len(rounds) > 3:
            raise Hold("HOLD_REDTEAM_ROUND_LIMIT", f"{path}.rounds")
        fixed_any = False
        artifact_hashes = []
        for round_index, round_raw in enumerate(rounds):
            round_path = f"{path}.rounds[{round_index}]"
            item = structural.require_dict(round_raw, round_path)
            if item.get("round") != round_index + 1 or item.get("executed") is not True:
                raise Hold("HOLD_REDTEAM_EXECUTION", round_path)
            input_sha = structural.require_sha256(item.get("input_sha256"), f"{round_path}.input_sha256")
            output_sha = structural.require_sha256(item.get("output_sha256"), f"{round_path}.output_sha256")
            if input_sha != previous:
                raise Hold("HOLD_REDTEAM_CHAIN", round_path)
            issues_found = item.get("issues_found")
            issues_fixed = item.get("issues_fixed")
            if (
                not isinstance(issues_found, int)
                or isinstance(issues_found, bool)
                or issues_found < 0
                or not isinstance(issues_fixed, int)
                or isinstance(issues_fixed, bool)
                or issues_fixed < 0
            ):
                raise Hold("HOLD_REDTEAM_COUNTS", round_path)
            if item.get("result") != "PASS":
                raise Hold("HOLD_REDTEAM_UNRESOLVED", round_path)
            if issues_found:
                fixed_any = True
                if (
                    issues_fixed < issues_found
                    or item.get("fix_applied") is not True
                    or item.get("rerun_executed") is not True
                    or input_sha == output_sha
                ):
                    raise Hold("HOLD_REDTEAM_FIX_RERUN", round_path)
                structural.require_str(item.get("fix_ref"), f"{round_path}.fix_ref", max_bytes=512)
            artifact_ref = item.get("artifact_ref")
            artifact, actual_sha = read_json(root, artifact_ref, f"{round_path}.artifact_ref")
            if actual_sha != structural.require_sha256(item.get("artifact_sha256"), f"{round_path}.artifact_sha256"):
                raise Hold("HOLD_REDTEAM_ARTIFACT_HASH", round_path)
            artifact = structural.require_dict(artifact, f"{round_path}.artifact")
            if (
                artifact.get("stage") != stage_name
                or artifact.get("round") != round_index + 1
                or artifact.get("input_sha256") != input_sha
                or artifact.get("output_sha256") != output_sha
                or artifact.get("executed") is not True
                or artifact.get("result") != "PASS"
            ):
                raise Hold("HOLD_REDTEAM_ARTIFACT_BINDING", round_path)
            structural.require_str(item.get("runner"), f"{round_path}.runner", max_bytes=256)
            artifact_hashes.append(actual_sha)
            previous = output_sha
        downstream = stage.get("downstream_revalidated", [])
        expected_downstream = stage_names[stage_index + 1 :] if fixed_any else []
        if downstream != expected_downstream:
            raise Hold("HOLD_REDTEAM_DOWNSTREAM_REVALIDATION", path)
        result[stage_name] = {
            "verifier_result": STRUCTURE_RESULT,
            "evidence_state": "UNVERIFIED",
            "rounds": len(rounds),
            "artifact_sha256": artifact_hashes,
            "downstream_revalidated": downstream,
        }
    if previous != candidate_sha:
        raise Hold("HOLD_REDTEAM_FINAL_CANDIDATE_BINDING", "$.verification.redteam_receipts")
    return result


def verify_runtime_receipts(
    root: Path,
    spec: Mapping[str, Any],
    candidate: Mapping[str, Any],
    candidate_sha: str,
    bundle: Mapping[str, Any],
) -> Dict[str, Any]:
    receipts = structural.require_dict(bundle.get("runtime_receipts"), "$.verification.runtime_receipts")
    segments_raw = structural.require_list(
        receipts.get("segments"), "$.verification.runtime_receipts.segments"
    )
    expected_stages = list(structural.TECHNICAL_CHAIN_STAGES)
    if len(segments_raw) != len(expected_stages):
        raise Hold("HOLD_RUNTIME_RECEIPT_STAGE_SET", "$.verification.runtime_receipts.segments")
    initial_gap_refs = list(candidate["runtime_completion_chain"]["initial_gap_refs"])
    initial_gap_set = set(initial_gap_refs)
    gap_union: set[str] = set()
    segments: list[Dict[str, Any]] = []
    artifact_refs: set[str] = set()
    previous_output = candidate["producer"]["input_spec_sha256"]
    for index, expected_stage in enumerate(expected_stages):
        path = f"$.verification.runtime_receipts.segments[{index}]"
        receipt = structural.require_dict(segments_raw[index], path)
        stage = structural.require_str(receipt.get("stage"), f"{path}.stage", max_bytes=96)
        if stage != expected_stage:
            if stage in expected_stages:
                raise Hold("HOLD_RUNTIME_RECEIPT_ORDER", f"{path}.stage")
            raise Hold("HOLD_RUNTIME_RECEIPT_STAGE_SET", f"{path}.stage")
        if receipt.get("sequence") != index + 1:
            raise Hold("HOLD_RUNTIME_RECEIPT_ORDER", f"{path}.sequence")
        if receipt.get("executed") is not True:
            raise Hold("HOLD_RUNTIME_RECEIPT_EXECUTION", path)
        initial_result = structural.require_str(
            receipt.get("initial_result"), f"{path}.initial_result", max_bytes=64
        )
        if initial_result not in RUNTIME_INITIAL_RESULTS:
            raise Hold("HOLD_RUNTIME_INITIAL_RESULT", f"{path}.initial_result")
        if receipt.get("evidence_class") != "FIELD_EVIDENCE":
            raise Hold("HOLD_RUNTIME_EVIDENCE_CLASS", f"{path}.evidence_class")
        if (
            receipt.get("input_revision") != spec["revision"]
            or receipt.get("candidate_packet_sha256") != candidate_sha
        ):
            raise Hold("HOLD_RUNTIME_RECEIPT_BINDING", path)
        input_sha = structural.require_sha256(receipt.get("input_sha256"), f"{path}.input_sha256")
        output_sha = structural.require_sha256(receipt.get("output_sha256"), f"{path}.output_sha256")
        if input_sha != previous_output:
            raise Hold("HOLD_RUNTIME_HASH_CHAIN", path)
        runner, runner_version = _runner_binding(receipt, path)
        artifact, actual_sha, artifact_ref = read_verified_json(
            root,
            receipt.get("artifact_ref"),
            receipt.get("artifact_sha256"),
            f"{path}.artifact",
            "HOLD_RUNTIME_ARTIFACT_HASH",
        )
        if artifact_ref in artifact_refs:
            raise Hold("HOLD_RUNTIME_ARTIFACT_INDEPENDENCE", f"{path}.artifact_ref")
        artifact_refs.add(artifact_ref)
        artifact_gaps = _str_list(
            artifact.get("gap_refs", []), f"{path}.artifact.gap_refs", nonempty=False
        )
        receipt_gaps = _str_list(receipt.get("gap_refs", []), f"{path}.gap_refs", nonempty=False)
        if (
            artifact.get("stage") != stage
            or artifact.get("sequence") != index + 1
            or artifact.get("executed") is not True
            or artifact.get("runner") != runner
            or artifact.get("runner_version") != runner_version
            or artifact.get("runner_verdict") != "UNVERIFIED"
            or artifact.get("evidence_class") != "FIELD_EVIDENCE"
            or artifact.get("input_revision") != spec["revision"]
            or artifact.get("candidate_packet_sha256") != candidate_sha
            or artifact.get("initial_result") != initial_result
            or artifact_gaps != receipt_gaps
        ):
            raise Hold("HOLD_RUNTIME_ARTIFACT_BINDING", path)
        _expect_io(receipt, artifact, input_sha, output_sha, path, "HOLD_RUNTIME_HASH_CHAIN")
        if stage == structural.HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD:
            _verify_eight_d_runtime_artifact(candidate, artifact, path)
        if initial_result == "EVIDENCE_GAP":
            if not artifact_gaps:
                raise Hold("HOLD_RUNTIME_GAP_REFS", path)
            gap_union.update(artifact_gaps)
        elif artifact_gaps:
            raise Hold("HOLD_RUNTIME_GAP_REFS", path)
        segments.append(
            {
                "stage": stage,
                "sequence": index + 1,
                "claimed_initial_result": initial_result,
                "input_sha256": input_sha,
                "output_sha256": output_sha,
                "verifier_result": HASH_CHAIN_VALID,
                "artifact_ref": artifact_ref,
                "artifact_sha256": actual_sha,
                "runner": runner,
                "runner_version": runner_version,
                "runner_verdict": "UNVERIFIED",
                "claimed_evidence_class": "FIELD_EVIDENCE",
                "gap_refs": artifact_gaps,
            }
        )
        previous_output = output_sha
    if previous_output != candidate_sha:
        raise Hold("HOLD_RUNTIME_HASH_CHAIN", "$.verification.runtime_receipts.segments")
    if initial_gap_set:
        if not gap_union or gap_union != initial_gap_set:
            raise Hold("HOLD_RUNTIME_INITIAL_GAP_REFS", "$.verification.runtime_receipts.segments")
    elif gap_union:
        raise Hold("HOLD_RUNTIME_INITIAL_GAP_REFS", "$.verification.runtime_receipts.segments")

    expected_fallbacks = list(candidate["runtime_completion_chain"]["fallbacks"])
    fallback_raw = structural.require_list(
        receipts.get("fallbacks", []),
        "$.verification.runtime_receipts.fallbacks",
        nonempty=False,
    )
    if not initial_gap_set and fallback_raw:
        raise Hold("HOLD_FALLBACK_INITIAL_GAP_REFS", "$.verification.runtime_receipts.fallbacks")
    if len(fallback_raw) != len(expected_fallbacks):
        raise Hold("HOLD_RUNTIME_FALLBACK_RECEIPT_SET", "$.verification.runtime_receipts.fallbacks")
    fallback_result: list[Dict[str, Any]] = []
    for index, expected in enumerate(expected_fallbacks):
        path = f"$.verification.runtime_receipts.fallbacks[{index}]"
        receipt = structural.require_dict(fallback_raw[index], path)
        source_class = structural.require_str(receipt.get("source_class"), f"{path}.source_class", max_bytes=96)
        if source_class not in structural.FALLBACK_CLASSES or source_class != expected["source_class"]:
            raise Hold("HOLD_FALLBACK_CLASS", f"{path}.source_class")
        if receipt.get("enabled_after_stage") != structural.TECHNICAL_CHAIN_STAGES[-1]:
            raise Hold("HOLD_FALLBACK_STAGE", f"{path}.enabled_after_stage")
        if receipt.get("grants_authority") is not False:
            raise Hold("HOLD_FALLBACK_AUTHORITY_ESCALATION", path)
        target_gap_refs = _str_list(receipt.get("target_gap_refs"), f"{path}.target_gap_refs", nonempty=True)
        if (
            target_gap_refs != expected["target_gap_refs"]
            or not set(target_gap_refs).issubset(initial_gap_set)
        ):
            raise Hold("HOLD_FALLBACK_TARGET_GAP_REFS", f"{path}.target_gap_refs")
        retrieval, retrieval_sha, retrieval_ref = read_verified_json(
            root,
            receipt.get("retrieval_artifact_ref"),
            receipt.get("retrieval_artifact_sha256"),
            f"{path}.retrieval_artifact",
            "HOLD_FALLBACK_RETRIEVAL_ARTIFACT_HASH",
        )
        retrieval_targets = _str_list(
            retrieval.get("target_gap_refs"), f"{path}.retrieval_artifact.target_gap_refs", nonempty=True
        )
        if (
            retrieval.get("artifact_kind") != "FALLBACK_RETRIEVAL"
            or retrieval.get("source_class") != source_class
            or retrieval.get("enabled_after_stage") != structural.TECHNICAL_CHAIN_STAGES[-1]
            or retrieval.get("grants_authority") is not False
            or retrieval.get("input_revision") != spec["revision"]
            or retrieval.get("candidate_packet_sha256") != candidate_sha
            or retrieval_targets != target_gap_refs
        ):
            raise Hold("HOLD_FALLBACK_RETRIEVAL_BINDING", path)
        if retrieval.get("evidence_class") == "FIELD_EVIDENCE" or retrieval.get("evidence_class") != source_class:
            raise Hold("HOLD_FALLBACK_RETRIEVAL_EVIDENCE_CLASS", f"{path}.retrieval_artifact.evidence_class")
        if retrieval.get("executed") is True or retrieval.get("result") == "PASS":
            raise Hold("HOLD_FALLBACK_RETRIEVAL_EXECUTION_CLAIM", f"{path}.retrieval_artifact")
        retrieval_input = candidate["producer"]["input_spec_sha256"]
        retrieval_output = _fallback_retrieval_output_sha(
            source_class,
            target_gap_refs,
            spec["revision"],
            candidate_sha,
        )
        if (
            retrieval.get("input_sha256") != retrieval_input
            or retrieval.get("output_sha256") != retrieval_output
        ):
            raise Hold("HOLD_FALLBACK_RETRIEVAL_HASH_CHAIN", path)
        rerun, rerun_sha, rerun_ref = read_verified_json(
            root,
            receipt.get("rerun_artifact_ref"),
            receipt.get("rerun_artifact_sha256"),
            f"{path}.rerun_artifact",
            "HOLD_FALLBACK_RERUN_ARTIFACT_HASH",
        )
        closed_gap_refs = _str_list(
            rerun.get("closed_gap_refs"), f"{path}.rerun_artifact.closed_gap_refs", nonempty=True
        )
        if (
            rerun_ref == retrieval_ref
            or rerun.get("artifact_kind") != "FALLBACK_RERUN"
            or rerun.get("source_class") != source_class
            or rerun.get("enabled_after_stage") != structural.TECHNICAL_CHAIN_STAGES[-1]
            or rerun.get("executed") is not True
            or rerun.get("result") != "PASS"
            or rerun.get("evidence_class") != "FIELD_EVIDENCE"
            or rerun.get("input_revision") != spec["revision"]
            or rerun.get("candidate_packet_sha256") != candidate_sha
            or rerun.get("runner_verdict") != "UNVERIFIED"
            or closed_gap_refs != target_gap_refs
        ):
            raise Hold("HOLD_FALLBACK_RERUN_BINDING", path)
        _expect_io(receipt, rerun, retrieval_sha, candidate_sha, path, "HOLD_FALLBACK_RERUN_HASH_CHAIN")
        structural.require_str(rerun.get("runner"), f"{path}.rerun_artifact.runner", max_bytes=256)
        structural.require_str(rerun.get("runner_version"), f"{path}.rerun_artifact.runner_version", max_bytes=128)
        fallback_result.append(
            {
                "source_class": source_class,
                "enabled_after_stage": structural.TECHNICAL_CHAIN_STAGES[-1],
                "target_gap_refs": target_gap_refs,
                "grants_authority": False,
                "input_sha256": retrieval_sha,
                "output_sha256": candidate_sha,
                "retrieval_artifact_ref": retrieval_ref,
                "retrieval_artifact_sha256": retrieval_sha,
                "rerun_artifact_ref": rerun_ref,
                "rerun_artifact_sha256": rerun_sha,
                "closed_gap_refs": closed_gap_refs,
                "runner_verdict": "UNVERIFIED",
            }
        )
    return {
        "verifier_result": STRUCTURE_RESULT,
        "hash_chain": HASH_CHAIN_VALID,
        "segments": segments,
        "initial_gap_refs": initial_gap_refs,
        "fallbacks": fallback_result,
    }


def verify_core_function_receipts(
    root: Path,
    spec: Mapping[str, Any],
    candidate: Mapping[str, Any],
    candidate_sha: str,
    bundle: Mapping[str, Any],
) -> Dict[str, Any]:
    receipts = structural.require_dict(
        bundle.get("core_function_receipts"), "$.verification.core_function_receipts"
    )
    if set(receipts) != set(structural.CORE_FUNCTIONS):
        raise Hold("HOLD_CORE_FUNCTION_RECEIPT_SET", "$.verification.core_function_receipts")
    result: Dict[str, Any] = {}
    artifact_refs: set[str] = set()
    for name in structural.CORE_FUNCTIONS:
        path = f"$.verification.core_function_receipts.{name}"
        receipt = structural.require_dict(receipts[name], path)
        if (
            receipt.get("function") != name
            or receipt.get("input_revision") != spec["revision"]
            or receipt.get("candidate_packet_sha256") != candidate_sha
        ):
            raise Hold("HOLD_CORE_FUNCTION_RECEIPT_BINDING", path)
        subject_sha = core_function_subject_sha256(candidate, name)
        if receipt.get("subject_sha256") != subject_sha:
            raise Hold("HOLD_CORE_FUNCTION_SUBJECT_HASH", path)
        runner, runner_version = _runner_binding(receipt, path)
        artifact, actual_sha, artifact_ref = read_verified_json(
            root,
            receipt.get("artifact_ref"),
            receipt.get("artifact_sha256"),
            f"{path}.artifact",
            "HOLD_CORE_FUNCTION_ARTIFACT_HASH",
        )
        if artifact_ref in artifact_refs:
            raise Hold("HOLD_CORE_FUNCTION_ARTIFACT_INDEPENDENCE", f"{path}.artifact_ref")
        artifact_refs.add(artifact_ref)
        if (
            artifact.get("function") != name
            or artifact.get("input_revision") != spec["revision"]
            or artifact.get("candidate_packet_sha256") != candidate_sha
            or artifact.get("subject_sha256") != subject_sha
            or artifact.get("runner") != runner
            or artifact.get("runner_version") != runner_version
            or artifact.get("runner_verdict") != "UNVERIFIED"
        ):
            raise Hold("HOLD_CORE_FUNCTION_ARTIFACT_BINDING", path)
        result[name] = {
            "verifier_result": STRUCTURE_RESULT,
            "subject_sha256": subject_sha,
            "artifact_ref": artifact_ref,
            "artifact_sha256": actual_sha,
            "runner": runner,
            "runner_version": runner_version,
            "runner_verdict": "UNVERIFIED",
            "claimed_result": receipt.get("result", receipt.get("claimed_result")),
            "claimed_evidence_class": receipt.get("evidence_class"),
        }
    return result


def verify_transfer_receipt(
    root: Path,
    spec: Mapping[str, Any],
    candidate: Mapping[str, Any],
    candidate_sha: str,
    bundle: Mapping[str, Any],
) -> Dict[str, Any]:
    receipt = structural.require_dict(bundle.get("transfer_receipt"), "$.verification.transfer_receipt")
    if (
        receipt.get("input_revision") != spec["revision"]
        or receipt.get("candidate_packet_sha256") != candidate_sha
    ):
        raise Hold("HOLD_TRANSFER_RECEIPT_BINDING", "$.verification.transfer_receipt")
    invariant = structural.require_dict(receipt.get("invariant"), "$.verification.transfer_receipt.invariant")
    if invariant != structural.TRANSFER_INVARIANT or invariant != _candidate_transfer_invariant(candidate):
        raise Hold("HOLD_TRANSFER_INVARIANT", "$.verification.transfer_receipt.invariant")
    invariant_sha = structural.sha256_bytes(structural.canonical_bytes(invariant))
    if invariant_sha != structural.require_sha256(
        receipt.get("invariant_sha256"), "$.verification.transfer_receipt.invariant_sha256"
    ):
        raise Hold("HOLD_TRANSFER_INVARIANT_HASH", "$.verification.transfer_receipt.invariant_sha256")
    recipe_manifest, recipe_manifest_sha, recipe_manifest_ref = read_verified_json(
        root,
        receipt.get("recipe_manifest_ref"),
        receipt.get("recipe_manifest_sha256"),
        "$.verification.transfer_receipt.recipe_manifest",
        "HOLD_TRANSFER_RECIPE_MANIFEST_HASH",
    )
    if (
        recipe_manifest.get("artifact_kind") != "TRANSFER_RECIPE_MANIFEST"
        or recipe_manifest.get("input_revision") != spec["revision"]
        or recipe_manifest.get("candidate_packet_sha256") != candidate_sha
        or recipe_manifest.get("recipes") != candidate["transfer"]["recipes"]
    ):
        raise Hold("HOLD_TRANSFER_RECIPE_MANIFEST_BINDING", "$.verification.transfer_receipt.recipe_manifest")
    packet_sha = transfer_packet_sha256(
        spec["revision"],
        candidate_sha,
        invariant_sha,
        recipe_manifest_sha,
    )
    if receipt.get("transfer_packet_sha256") != packet_sha:
        raise Hold("HOLD_TRANSFER_PACKET_HASH", "$.verification.transfer_receipt.transfer_packet_sha256")
    expected_state_sha = _hash_canonical(candidate["code_reconstruction"])
    stages_raw = structural.require_dict(
        receipt.get("stage_artifacts"), "$.verification.transfer_receipt.stage_artifacts"
    )
    if set(stages_raw) != set(TRANSFER_EVIDENCE_STAGES):
        raise Hold("HOLD_TRANSFER_ARTIFACT_SET", "$.verification.transfer_receipt.stage_artifacts")
    stages: Dict[str, Any] = {}
    artifact_refs = {recipe_manifest_ref}
    for stage_name in TRANSFER_EVIDENCE_STAGES:
        path = f"$.verification.transfer_receipt.stage_artifacts.{stage_name}"
        stage_receipt = structural.require_dict(stages_raw[stage_name], path)
        artifact, actual_sha, artifact_ref = read_verified_json(
            root,
            stage_receipt.get("artifact_ref"),
            stage_receipt.get("artifact_sha256"),
            f"{path}.artifact",
            "HOLD_TRANSFER_ARTIFACT_HASH",
        )
        if artifact_ref in artifact_refs:
            raise Hold("HOLD_TRANSFER_ARTIFACT_INDEPENDENCE", f"{path}.artifact_ref")
        artifact_refs.add(artifact_ref)
        if (
            artifact.get("stage") != stage_name
            or artifact.get("input_revision") != spec["revision"]
            or artifact.get("candidate_packet_sha256") != candidate_sha
            or artifact.get("runner_verdict") != "UNVERIFIED"
        ):
            raise Hold("HOLD_TRANSFER_ARTIFACT_BINDING", path)
        runner, runner_version = _runner_binding(artifact, f"{path}.artifact")
        if stage_name == "PROGRAM_TRANSFER_RUBBING":
            _expect_io(stage_receipt, artifact, recipe_manifest_sha, packet_sha, path, "HOLD_TRANSFER_HASH_CHAIN")
            if (
                artifact.get("transfer_mode") != "PROGRAM_TRANSFER_RUBBING"
                or artifact.get("recipe_manifest_sha256") != recipe_manifest_sha
                or artifact.get("transfer_packet_sha256") != packet_sha
            ):
                raise Hold("HOLD_TRANSFER_ARTIFACT_BINDING", path)
        elif stage_name == "RECEIVER_RECONSTRUCTION":
            _expect_io(stage_receipt, artifact, packet_sha, expected_state_sha, path, "HOLD_TRANSFER_HASH_CHAIN")
            if (
                artifact.get("input_packet_sha256") != packet_sha
                or artifact.get("actual_state_sha256") != expected_state_sha
            ):
                raise Hold("HOLD_TRANSFER_RECEIVER_STATE", path)
        elif stage_name == "EQUIVALENT_STATE_VERIFICATION":
            _expect_io(stage_receipt, artifact, expected_state_sha, candidate_sha, path, "HOLD_TRANSFER_HASH_CHAIN")
            if (
                artifact.get("expected_state_sha256") != expected_state_sha
                or artifact.get("actual_state_sha256") != expected_state_sha
                or artifact.get("equivalence_method") != EQUIVALENCE_METHOD
                or artifact.get("equivalent") is not True
            ):
                raise Hold("HOLD_TRANSFER_EQUIVALENCE", path)
        stages[stage_name] = {
            "artifact_ref": artifact_ref,
            "artifact_sha256": actual_sha,
            "input_sha256": structural.require_sha256(stage_receipt.get("input_sha256"), f"{path}.input_sha256"),
            "output_sha256": structural.require_sha256(stage_receipt.get("output_sha256"), f"{path}.output_sha256"),
            "runner": runner,
            "runner_version": runner_version,
            "runner_verdict": "UNVERIFIED",
            "claimed_result": artifact.get("result", artifact.get("claimed_result")),
        }
    return {
        "verifier_result": STRUCTURE_RESULT,
        "invariant_sha256": invariant_sha,
        "recipe_manifest_ref": recipe_manifest_ref,
        "recipe_manifest_sha256": recipe_manifest_sha,
        "transfer_packet_sha256": packet_sha,
        "expected_state_sha256": expected_state_sha,
        "stage_artifacts": stages,
    }


def verify_trade_secret_receipt(
    root: Path,
    spec: Mapping[str, Any],
    candidate: Mapping[str, Any],
    candidate_sha: str,
    bundle: Mapping[str, Any],
    transfer_result: Mapping[str, Any],
    cross_node_result: Mapping[str, Any],
) -> Dict[str, Any]:
    receipt = structural.require_dict(bundle.get("trade_secret_receipt"), "$.verification.trade_secret_receipt")
    if (
        receipt.get("input_revision") != spec["revision"]
        or receipt.get("candidate_packet_sha256") != candidate_sha
    ):
        raise Hold("HOLD_TRADE_SECRET_RECEIPT_BINDING", "$.verification.trade_secret_receipt")
    boundary = structural.require_dict(receipt.get("boundary"), "$.verification.trade_secret_receipt.boundary")
    if (
        boundary != structural.TRADE_SECRET_BOUNDARY
        or boundary != _candidate_trade_secret_boundary(candidate)
            or receipt.get("public_contract_only") is not True
    ):
        raise Hold("HOLD_TRADE_SECRET_BOUNDARY", "$.verification.trade_secret_receipt.boundary")
    expected: list[Dict[str, Any]] = [
        {
            "artifact_kind": "IN_MEMORY_CANDIDATE",
            "artifact_ref": "IN_MEMORY",
            "artifact_sha256": candidate_sha,
        },
        {
            "artifact_kind": "TRANSFER_RECIPE_MANIFEST",
            "artifact_ref": transfer_result["recipe_manifest_ref"],
            "artifact_sha256": transfer_result["recipe_manifest_sha256"],
        },
    ]
    for stage_name in TRANSFER_EVIDENCE_STAGES:
        stage = structural.require_dict(
            transfer_result["stage_artifacts"][stage_name],
            f"$.verification.transfer_receipt.stage_artifacts.{stage_name}",
        )
        expected.append(
            {
                "artifact_kind": stage_name,
                "artifact_ref": stage["artifact_ref"],
                "artifact_sha256": stage["artifact_sha256"],
            }
        )
    expected.append(
        {
            "artifact_kind": "CROSS_NODE_TRANSFER_OBJECT",
            "artifact_ref": cross_node_result["object_ref"],
            "artifact_sha256": cross_node_result["object_sha256"],
        }
    )
    scanned = structural.require_list(
        receipt.get("scanned_artifacts"),
        "$.verification.trade_secret_receipt.scanned_artifacts",
    )
    normalized: list[Dict[str, Any]] = []
    for index, raw in enumerate(scanned):
        path = f"$.verification.trade_secret_receipt.scanned_artifacts[{index}]"
        item = structural.require_dict(raw, path)
        normalized.append(
            {
                "artifact_kind": structural.require_str(item.get("artifact_kind"), f"{path}.artifact_kind", max_bytes=128),
                "artifact_ref": structural.require_str(item.get("artifact_ref"), f"{path}.artifact_ref", max_bytes=512),
                "artifact_sha256": structural.require_sha256(item.get("artifact_sha256"), f"{path}.artifact_sha256"),
            }
        )
    expected_sorted = sorted(expected, key=lambda item: (item["artifact_kind"], item["artifact_ref"]))
    normalized_sorted = sorted(normalized, key=lambda item: (item["artifact_kind"], item["artifact_ref"]))
    if normalized_sorted != expected_sorted:
        raise Hold("HOLD_TRADE_SECRET_SCANNED_SET", "$.verification.trade_secret_receipt.scanned_artifacts")
    return {
        "verifier_result": STRUCTURE_RESULT,
        "boundary": dict(structural.TRADE_SECRET_BOUNDARY),
        "public_contract_only": True,
        "scanned_artifacts": expected_sorted,
    }


def verify_cross_node(
    root: Path,
    spec: Mapping[str, Any],
    candidate: Mapping[str, Any],
    candidate_sha: str,
    bundle: Mapping[str, Any],
    transfer_result: Mapping[str, Any],
    now: dt.datetime,
) -> Dict[str, Any]:
    context = structural.require_dict(bundle.get("run_context"), "$.verification.run_context")
    receipt = structural.require_dict(bundle.get("cross_node_receipt"), "$.verification.cross_node_receipt")
    run_id = structural.require_str(context.get("run_id"), "$.verification.run_context.run_id", max_bytes=128)
    nonce = structural.require_str(context.get("nonce"), "$.verification.run_context.nonce", max_bytes=128)
    if re.fullmatch(r"[A-Za-z0-9_-]{16,128}", nonce) is None:
        raise Hold("HOLD_NONCE_FORMAT", "$.verification.run_context.nonce")
    issued = _parse_time(context.get("issued_at"), "$.verification.run_context.issued_at")
    expires = _parse_time(context.get("expires_at"), "$.verification.run_context.expires_at")
    if not issued <= now <= expires or (expires - issued).total_seconds() > MAX_TTL_SECONDS:
        raise Hold("HOLD_TTL", "$.verification.run_context")
    if receipt.get("protocol") != "IFGC-GTP" or receipt.get("protocol_version") != "1.0.0":
        raise Hold("HOLD_CROSS_NODE_PROTOCOL", "$.verification.cross_node_receipt")
    required_equal = {
        "run_id": run_id,
        "nonce": nonce,
        "logical_root_id": spec["logical_root_id"],
        "source_node": spec["node_id"],
        "input_revision": spec["revision"],
        "candidate_packet_sha256": candidate_sha,
    }
    for key, expected in required_equal.items():
        if receipt.get(key) != expected:
            raise Hold("HOLD_CROSS_NODE_BINDING", f"$.verification.cross_node_receipt.{key}")
    target_node = structural.require_str(receipt.get("target_node"), "$.verification.cross_node_receipt.target_node", max_bytes=128)
    if target_node == spec["node_id"]:
        raise Hold("HOLD_CROSS_NODE_IDENTITY", "$.verification.cross_node_receipt.target_node")
    for name in (
        "source_snapshot_sha256",
        "target_snapshot_sha256",
    ):
        structural.require_sha256(receipt.get(name), f"$.verification.cross_node_receipt.{name}")
    source_platform = structural.require_str(receipt.get("source_platform"), "$.verification.cross_node_receipt.source_platform", max_bytes=128)
    target_platform = structural.require_str(receipt.get("target_platform"), "$.verification.cross_node_receipt.target_platform", max_bytes=128)
    object_ref = receipt.get("object_ref")
    transfer_object, object_sha, normalized_object_ref = read_canonical_json(
        root,
        object_ref,
        "$.verification.cross_node_receipt.object_ref",
        source_zone=True,
        expected_sha_raw=receipt.get("object_sha256"),
        hash_hold_code="HOLD_CROSS_NODE_OBJECT_HASH",
    )
    if transfer_object != expected_cross_node_transfer_object(candidate, candidate_sha, transfer_result):
        raise Hold("HOLD_CROSS_NODE_OBJECT_BINDING", "$.verification.cross_node_receipt.object_ref")
    nonce_sha = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
    replay, _ = read_json(root, receipt.get("replay_index_ref"), "$.verification.cross_node_receipt.replay_index_ref")
    replay = structural.require_dict(replay, "$.verification.replay_index")
    used = structural.require_list(replay.get("used_nonce_sha256", []), "$.verification.replay_index.used_nonce_sha256", nonempty=False)
    if nonce_sha in used:
        raise Hold("HOLD_REPLAY", "$.verification.run_context.nonce")
    if receipt.get("trusted_root") == "PRESENT" or receipt.get("trusted_root_present") is True:
        raise Hold("HOLD_TRUSTED_ROOT_INJECTION", "$.verification.cross_node_receipt.trusted_root")
    authority_state = structural.require_str(receipt.get("authority_state"), "$.verification.cross_node_receipt.authority_state", max_bytes=64)
    if authority_state not in {"UNVERIFIED", "VERIFIED"}:
        raise Hold("HOLD_AUTHORITY_STATE", "$.verification.cross_node_receipt.authority_state")
    signature_state = structural.require_str(receipt.get("signature_state", "UNVERIFIED"), "$.verification.cross_node_receipt.signature_state", max_bytes=64)
    if signature_state not in {"UNVERIFIED", "VERIFIED"}:
        raise Hold("HOLD_SIGNATURE_STATE", "$.verification.cross_node_receipt.signature_state")
    claimed_verifier_result = structural.require_str(
        receipt.get("verifier_result", "UNVERIFIED"),
        "$.verification.cross_node_receipt.verifier_result",
        max_bytes=64,
    )
    crypto_claims = {
        f"claimed_{key}_present": key in receipt
        for key in SELF_CRYPTO_CLAIM_KEYS
    }
    claim_fields = {
        f"claimed_{name}": receipt.get(name, "UNSPECIFIED")
        for name in (
            "platform_compatibility",
            "pollution_guard",
            "drift_guard",
            "tamper_guard",
            "rollback_guard",
        )
    }
    # These fields are caller-supplied claims until a trusted cryptographic
    # signature verifier is implemented and bound to this receipt.
    authenticity_result = "UNVERIFIED"
    return {
        "integrity_result": STRUCTURE_RESULT,
        "authenticity_result": authenticity_result,
        "replay_result": "CROSS_NODE_REPLAY_UNVERIFIED",
        "run_id": run_id,
        "nonce_sha256": nonce_sha,
        "issued_at": issued.isoformat().replace("+00:00", "Z"),
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
        "logical_root_id": spec["logical_root_id"],
        "source_node": spec["node_id"],
        "target_node": target_node,
        "input_revision": spec["revision"],
        "candidate_packet_sha256": candidate_sha,
        "object_ref": normalized_object_ref,
        "object_sha256": object_sha,
        "source_platform": source_platform,
        "target_platform": target_platform,
        **claim_fields,
        "claimed_verifier_result": claimed_verifier_result,
        "claimed_authority_state": authority_state,
        "claimed_signature_state": signature_state,
        **crypto_claims,
        "activation": "NOT_AUTHORIZED",
    }


def verify(
    root: Path,
    spec: Any,
    bundle: Any,
    *,
    now: dt.datetime | None = None,
) -> Dict[str, Any]:
    root = _root_path(root)
    spec_map = structural.require_dict(spec, "$")
    bundle_map = structural.require_dict(bundle, "$.verification")
    candidate = producer.build_candidate(spec_map)
    relational = verify_relational_contract(root, spec_map, candidate)
    candidate_sha = structural.sha256_bytes(structural.canonical_bytes(candidate))
    if bundle_map.get("producer_code_sha256") != candidate["producer"]["code_sha256"]:
        raise Hold("HOLD_PRODUCER_CODE_BINDING", "$.verification.producer_code_sha256")
    if bundle_map.get("input_spec_sha256") != candidate["producer"]["input_spec_sha256"]:
        raise Hold("HOLD_INPUT_SPEC_BINDING", "$.verification.input_spec_sha256")
    if bundle_map.get("input_revision") != spec_map["revision"]:
        raise Hold("HOLD_INPUT_REVISION_BINDING", "$.verification.input_revision")
    journey = verify_journeys(root, spec_map, bundle_map)
    redteam = verify_redteam(root, candidate_sha, bundle_map)
    runtime = verify_runtime_receipts(root, spec_map, candidate, candidate_sha, bundle_map)
    core_functions = verify_core_function_receipts(root, spec_map, candidate, candidate_sha, bundle_map)
    transfer = verify_transfer_receipt(root, spec_map, candidate, candidate_sha, bundle_map)
    current = now or dt.datetime.now(dt.timezone.utc)
    cross_node = verify_cross_node(
        root,
        spec_map,
        candidate,
        candidate_sha,
        bundle_map,
        transfer,
        current.astimezone(dt.timezone.utc),
    )
    trade_secret = verify_trade_secret_receipt(
        root,
        spec_map,
        candidate,
        candidate_sha,
        bundle_map,
        transfer,
        cross_node,
    )
    final = dict(candidate)
    final["states"] = list(FINAL_STATES)
    final["verifier_result"] = STRUCTURE_RESULT
    final["detached_verification"] = {
        "producer_code_sha256": candidate["producer"]["code_sha256"],
        "input_spec_sha256": candidate["producer"]["input_spec_sha256"],
        "input_revision": spec_map["revision"],
        "candidate_packet_sha256": candidate_sha,
        "relational_contract": relational,
        "journey": journey,
        "redteam": redteam,
        "runtime": runtime,
        "core_functions": core_functions,
        "transfer": transfer,
        "trade_secret": trade_secret,
        "cross_node": cross_node,
    }
    final["governance"]["activation"] = "NOT_AUTHORIZED"
    return final


def secure_write(root: Path, output_ref: Any, packet: Mapping[str, Any]) -> Dict[str, Any]:
    root = _root_path(root)
    parts = _relative_parts(output_ref, "$.output_dir")
    if len(parts) < 2:
        raise Hold("HOLD_OUTPUT_NOT_NEW_RUN_DIRECTORY", "$.output_dir")
    parent_parts, target_name = parts[:-1], parts[-1]
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    parent_fd = os.open(root, os.O_RDONLY | directory | nofollow)
    try:
        for part in parent_parts:
            next_fd = os.open(part, os.O_RDONLY | directory | nofollow, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        try:
            os.stat(target_name, dir_fd=parent_fd, follow_symlinks=False)
            raise Hold("HOLD_OUTPUT_EXISTS", "$.output_dir")
        except FileNotFoundError:
            pass
        temp_name = f".ifgc-{uuid.uuid4().hex}"
        os.mkdir(temp_name, 0o700, dir_fd=parent_fd)
        temp_fd = os.open(temp_name, os.O_RDONLY | directory | nofollow, dir_fd=parent_fd)
        try:
            packet_bytes = structural.canonical_bytes(packet) + b"\n"
            packet_sha = hashlib.sha256(packet_bytes).hexdigest()
            seal = {
                "protocol": "IFGC-GTP",
                "protocol_version": "1.0.0",
                "states": list(packet["states"]),
                "verifier_result": STRUCTURE_RESULT,
                "authenticity_result": packet["detached_verification"]["cross_node"]["authenticity_result"],
                "packet_path": PACKET_NAME,
                "packet_sha256": packet_sha,
                "producer_code_sha256": packet["detached_verification"]["producer_code_sha256"],
                "input_revision": packet["revision"],
                "activation": "NOT_AUTHORIZED",
                "secret_included": False,
                "member_plaintext_included": False,
                "full_source_embedded": False,
                "summary": {
                    "candidate_packet_sha256": packet["detached_verification"]["candidate_packet_sha256"],
                    "mainline_relation": packet["mainline_relation"],
                    "continuation_distance": packet["continuation_distance"],
                    "supply_demand_fit": packet["supply_demand_fit"],
                    "relational_evidence": packet["detached_verification"]["relational_contract"],
                    "runtime_segments": len(packet["detached_verification"]["runtime"]["segments"]),
                    "core_functions": list(structural.CORE_FUNCTIONS),
                    "transfer_stages": list(TRANSFER_EVIDENCE_STAGES),
                    "trade_secret_public_contract_only": True,
                    "runtime_evidence": "UNVERIFIED",
                    "user_journey_evidence": "UNVERIFIED",
                },
            }
            files = {
                PACKET_NAME: packet_bytes,
                SHA_NAME: f"{packet_sha}  {PACKET_NAME}\n".encode("utf-8"),
                SEAL_NAME: structural.canonical_bytes(seal) + b"\n",
            }
            for name, data in files.items():
                file_fd = os.open(
                    name,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow,
                    0o600,
                    dir_fd=temp_fd,
                )
                try:
                    os.write(file_fd, data)
                    os.fsync(file_fd)
                finally:
                    os.close(file_fd)
            os.fsync(temp_fd)
            os.rename(temp_name, target_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            os.fsync(parent_fd)
            return {
                "states": list(packet["states"]),
                "verifier_result": STRUCTURE_RESULT,
                "packet_sha256": packet_sha,
                "artifacts_written": True,
                "artifact_names": [PACKET_NAME, SHA_NAME, SEAL_NAME],
                "activation": "NOT_AUTHORIZED",
            }
        except Exception:
            for name in (PACKET_NAME, SHA_NAME, SEAL_NAME):
                try:
                    os.unlink(name, dir_fd=temp_fd)
                except FileNotFoundError:
                    pass
            os.close(temp_fd)
            temp_fd = -1
            os.rmdir(temp_name, dir_fd=parent_fd)
            raise
        finally:
            if temp_fd >= 0:
                os.close(temp_fd)
    finally:
        os.close(parent_fd)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worktree-root", required=True, type=Path)
    parser.add_argument("--input-ref", required=True)
    parser.add_argument("--verification-bundle-ref", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.validate_only and not args.output_dir:
        parser.error("--output-dir is required unless --validate-only is used")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        root = _root_path(args.worktree_root)
        spec, _ = read_json(root, args.input_ref, "$.input_ref")
        bundle, _ = read_json(root, args.verification_bundle_ref, "$.verification_bundle_ref")
        packet = verify(root, spec, bundle)
        if args.validate_only:
            report = {
                "states": list(packet["states"]),
                "verifier_result": STRUCTURE_RESULT,
                "artifacts_written": False,
                "activation": "NOT_AUTHORIZED",
            }
        else:
            report = secure_write(root, args.output_dir, packet)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    except Hold as error:
        print(json.dumps(error.report(), ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
