#!/usr/bin/env python3
"""Endpoint rule-capability handshake and wire-cost transport selection.

This adapter reuses the existing local rule registry and minimum Origin State
packet contract. It does not define a second Origin Cell core, grant D8
authority, mutate canonical pointers, or equate file presence with readiness.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import socket
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "W7TP_ENDPOINT_RULE_CAPABILITY_HANDSHAKE/1.0"
SELECTOR_SCHEMA = "W7TP_RULE_BASE_TRANSPORT_SELECTOR/1.0"


class EndpointRuleHandshakeHold(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_module(path: Path, name: str) -> Any:
    if not path.is_file() or path.is_symlink():
        raise EndpointRuleHandshakeHold("HOLD_ENDPOINT_RULE_MODULE_MISSING")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise EndpointRuleHandshakeHold("HOLD_ENDPOINT_RULE_MODULE_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rule_base_paths(root: Path) -> dict[str, Path]:
    base = root / "products/eight_dimensional_generative_memory"
    return {
        "registry": root / "configs/total_field/w7tp_local_origin_state_rule_registry_v1.json",
        "minimum_packet": base / "w7tp_origin_state_minimum_packet_v1.py",
        "receiver_contract": base / "w7tp_receiver_capability_contract_v1.py",
        "universal_origin": base / "w7tp_origin_cell_gst_universal_v23_candidate.py",
        "universal_receiver": base / "w7tp_origin_cell_gst_universal_receiver_candidate.py",
        "universal_contract": base / "w7tp_origin_cell_gst_universal_receiver_contract.json",
    }


def _task_state_dependencies(state_root: Path | None) -> dict[str, Any]:
    if state_root is None:
        return {
            "state": "NOT_READY_STATE_ROOT_UNBOUND",
            "ready": False,
            "state_root": None,
            "required": [
                "state/WORK_LEDGER.json",
                "state/ACTION_LEDGER.json",
                "state/CURRENT_CONVERSATION_CHECKPOINT.json",
                "native-adi:http://127.0.0.1:9110",
            ],
        }
    required = [
        state_root / "state/WORK_LEDGER.json",
        state_root / "state/ACTION_LEDGER.json",
        state_root / "state/CURRENT_CONVERSATION_CHECKPOINT.json",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    native_adi_observed = False
    try:
        with socket.create_connection(("127.0.0.1", 9110), timeout=0.5):
            native_adi_observed = True
    except OSError:
        pass
    ready = not missing and native_adi_observed
    return {
        "state": (
            "READY_LOCAL_TASK_STATE_DEPENDENCIES"
            if ready
            else "NOT_READY_LOCAL_TASK_STATE_DEPENDENCIES"
        ),
        "ready": ready,
        "state_root": str(state_root),
        "missing": missing,
        "native_adi_required": True,
        "native_adi_observed": native_adi_observed,
    }


def _observe_universal_binding(paths: Mapping[str, Path]) -> dict[str, Any]:
    receiver_gate = _load_module(
        paths["universal_receiver"],
        "w7tp_endpoint_universal_receiver_gate",
    )
    try:
        result = receiver_gate.inspect_binding(paths["universal_contract"])
        contract = json.loads(
            paths["universal_contract"].read_text(encoding="utf-8")
        )
    except Exception as exc:
        code = getattr(exc, "code", None)
        raise EndpointRuleHandshakeHold(
            code if isinstance(code, str) else "HOLD_UNIVERSAL_ENDPOINT_BINDING_INVALID"
        ) from exc
    primitive = (
        contract["receiver_capability_contract"]
        ["receiver_requirement"]
        ["primitive_binding"]
    )
    return {
        "state": result.get("state"),
        "ready": (
            result.get("receiver_match_state")
            == "PASS_UNIVERSAL_EXECUTOR_CAPABILITY_MATCH"
        ),
        "executor_contract": primitive.get("executor_contract"),
        "implementation_sha256": primitive.get("implementation_sha256"),
        "protocol_descriptor_sha256": primitive.get(
            "protocol_descriptor_sha256"
        ),
        "material_base_contracts": primitive.get("material_base_contracts"),
        "max_reconstructed_bytes": primitive.get("max_reconstructed_bytes"),
        "receiver_contract_sha256": result.get("receiver_contract_sha256"),
        "runtime_activated": result.get("runtime_activated"),
        "canonical": result.get("canonical"),
    }


def observe_endpoint_rule_capability(
    *,
    root: Path,
    node_ref: str | None = None,
    state_root: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    paths = _rule_base_paths(root)
    minimum = _load_module(paths["minimum_packet"], "w7tp_endpoint_minimum_packet")
    receiver = _load_module(paths["receiver_contract"], "w7tp_endpoint_receiver_contract")
    try:
        registry = minimum.load_rule_registry(
            root=root,
            registry_path=paths["registry"],
        )
    except Exception as exc:
        code = getattr(exc, "code", None)
        raise EndpointRuleHandshakeHold(
            code if isinstance(code, str) else "HOLD_ENDPOINT_RULE_REGISTRY_INVALID"
        ) from exc

    rules: list[dict[str, Any]] = []
    all_present = True
    for rule_ref, entry in sorted(registry.items()):
        implementation = Path(entry["implementation_path"])
        observed_hash = sha256_file(implementation)
        expected_hash = entry.get("implementation_sha256")
        present = observed_hash == expected_hash
        all_present = all_present and present
        dependency = (
            _task_state_dependencies(state_root)
            if rule_ref == "local-rule:w7tp-task-state-ledger-reconstruction/v1"
            else {"state": "READY_RULE_LOCAL_ONLY", "ready": present}
        )
        rules.append(
            {
                "rule_ref": rule_ref,
                "implementation_ref": entry.get("implementation_ref"),
                "implementation_sha256": observed_hash,
                "expected_sha256": expected_hash,
                "present": present,
                "runtime_dependency": dependency,
                "ready": bool(present and dependency.get("ready") is True),
            }
        )

    observed = receiver.observe_local_receiver(
        node_ref=node_ref or socket.gethostname(),
        root=root,
    )
    universal = _observe_universal_binding(paths)
    ready_rules = sorted(item["rule_ref"] for item in rules if item["ready"])
    present_rules = sorted(item["rule_ref"] for item in rules if item["present"])
    handshake: dict[str, Any] = {
        "schema_id": SCHEMA,
        "node_ref": observed["node_ref"],
        "observed_root": str(root),
        "rule_base": {
            "registry_schema": "W7TP_LOCAL_ORIGIN_STATE_RULE_REGISTRY_V1",
            "registry_sha256": observed["primitive_binding"]["registry_sha256"],
            "minimum_packet_implementation_sha256": observed["primitive_binding"][
                "minimum_packet_implementation_sha256"
            ],
            "origin_cell_implementation_sha256": observed["primitive_binding"][
                "implementation_sha256"
            ],
            "packet_schema": getattr(minimum, "PACKET_SCHEMA", None),
            "protocol_version": getattr(minimum, "PROTOCOL_VERSION", None),
            "present_rule_refs": present_rules,
            "ready_rule_refs": ready_rules,
            "rules": rules,
            "universal_executor": universal,
        },
        "runtime": observed["runtime"],
        "state": (
            "PASS_ENDPOINT_RULE_BASE_PRESENT"
            if all_present and universal.get("ready") is True
            else "HOLD_ENDPOINT_RULE_BASE_DRIFT"
        ),
        "authority": {
            "canonical": False,
            "formal_authority": False,
            "execution_authorized": False,
            "authority_effect": "NONE",
        },
        "semantics": {
            "file_presence_is_not_readiness": True,
            "rule_body_local_only": True,
            "wire_cost_metric": "CANONICAL_SERIALIZED_WIRE_BYTES",
        },
    }
    basis = dict(handshake)
    handshake["handshake_sha256"] = hashlib.sha256(
        canonical_json_bytes(basis)
    ).hexdigest()
    if not all_present:
        raise EndpointRuleHandshakeHold("HOLD_ENDPOINT_RULE_BASE_DRIFT")
    return handshake


def shared_rule_match(
    source: Mapping[str, Any],
    receiver: Mapping[str, Any],
    *,
    rule_ref: str,
) -> dict[str, Any]:
    if source.get("schema_id") != SCHEMA or receiver.get("schema_id") != SCHEMA:
        raise EndpointRuleHandshakeHold("HOLD_ENDPOINT_HANDSHAKE_SCHEMA_MISMATCH")
    sbase = source.get("rule_base")
    rbase = receiver.get("rule_base")
    if not isinstance(sbase, Mapping) or not isinstance(rbase, Mapping):
        raise EndpointRuleHandshakeHold("HOLD_ENDPOINT_RULE_BASE_MISSING")
    if sbase.get("packet_schema") != rbase.get("packet_schema"):
        raise EndpointRuleHandshakeHold("HOLD_ENDPOINT_PACKET_SCHEMA_MISMATCH")
    if sbase.get("protocol_version") != rbase.get("protocol_version"):
        raise EndpointRuleHandshakeHold("HOLD_ENDPOINT_PROTOCOL_VERSION_MISMATCH")
    srules = {
        item.get("rule_ref"): item
        for item in sbase.get("rules", [])
        if isinstance(item, Mapping)
    }
    rrules = {
        item.get("rule_ref"): item
        for item in rbase.get("rules", [])
        if isinstance(item, Mapping)
    }
    left = srules.get(rule_ref)
    right = rrules.get(rule_ref)
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        raise EndpointRuleHandshakeHold("HOLD_SHARED_RULE_NOT_PRESENT")
    if left.get("implementation_sha256") != right.get("implementation_sha256"):
        raise EndpointRuleHandshakeHold("HOLD_SHARED_RULE_HASH_MISMATCH")
    return {
        "state": "PASS_SHARED_RULE_EXACT_MATCH",
        "rule_ref": rule_ref,
        "implementation_sha256": left.get("implementation_sha256"),
        "source_ready": left.get("ready") is True,
        "receiver_ready": right.get("ready") is True,
    }


def universal_executor_match(
    source: Mapping[str, Any],
    receiver: Mapping[str, Any],
) -> dict[str, Any]:
    if source.get("schema_id") != SCHEMA or receiver.get("schema_id") != SCHEMA:
        raise EndpointRuleHandshakeHold("HOLD_ENDPOINT_HANDSHAKE_SCHEMA_MISMATCH")
    sbase = source.get("rule_base")
    rbase = receiver.get("rule_base")
    if not isinstance(sbase, Mapping) or not isinstance(rbase, Mapping):
        raise EndpointRuleHandshakeHold("HOLD_ENDPOINT_RULE_BASE_MISSING")
    left = sbase.get("universal_executor")
    right = rbase.get("universal_executor")
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        raise EndpointRuleHandshakeHold("HOLD_UNIVERSAL_ENDPOINT_BINDING_MISSING")
    for key, code in (
        ("executor_contract", "HOLD_UNIVERSAL_EXECUTOR_CONTRACT_MISMATCH"),
        ("implementation_sha256", "HOLD_UNIVERSAL_EXECUTOR_HASH_MISMATCH"),
        (
            "protocol_descriptor_sha256",
            "HOLD_UNIVERSAL_PROTOCOL_DESCRIPTOR_MISMATCH",
        ),
        (
            "receiver_contract_sha256",
            "HOLD_UNIVERSAL_RECEIVER_CONTRACT_MISMATCH",
        ),
    ):
        if left.get(key) != right.get(key):
            raise EndpointRuleHandshakeHold(code)
    if left.get("material_base_contracts") != right.get("material_base_contracts"):
        raise EndpointRuleHandshakeHold(
            "HOLD_UNIVERSAL_MATERIAL_BASE_CONTRACT_MISMATCH"
        )
    return {
        "state": "PASS_SHARED_UNIVERSAL_EXECUTOR_MATCH",
        "rule_ref": left.get("executor_contract"),
        "implementation_sha256": left.get("implementation_sha256"),
        "source_ready": left.get("ready") is True,
        "receiver_ready": right.get("ready") is True,
    }


def select_transport(
    *,
    full_transfer_wire_bytes: int,
    shared_rule_origin_cell_wire_bytes: int | None,
    shared_rule_match_state: Mapping[str, Any] | None,
    generative_origin_cell_wire_bytes: int | None = None,
) -> dict[str, Any]:
    if not isinstance(full_transfer_wire_bytes, int) or full_transfer_wire_bytes < 0:
        raise EndpointRuleHandshakeHold("HOLD_FULL_TRANSFER_WIRE_BYTES_INVALID")
    candidates: list[tuple[str, int, str]] = [
        ("FULL_TRANSFER", full_transfer_wire_bytes, "BASELINE_FULL_WIRE_BYTES")
    ]
    if (
        isinstance(shared_rule_origin_cell_wire_bytes, int)
        and shared_rule_origin_cell_wire_bytes >= 0
        and isinstance(shared_rule_match_state, Mapping)
        and shared_rule_match_state.get("state") in {
            "PASS_SHARED_RULE_EXACT_MATCH",
            "PASS_SHARED_UNIVERSAL_EXECUTOR_MATCH",
        }
        and shared_rule_match_state.get("receiver_ready") is True
    ):
        candidates.append(
            (
                "SHARED_RULE_ORIGIN_CELL",
                shared_rule_origin_cell_wire_bytes,
                "EXACT_SHARED_RULE_AND_RECEIVER_READY",
            )
        )
    if (
        isinstance(generative_origin_cell_wire_bytes, int)
        and generative_origin_cell_wire_bytes >= 0
    ):
        candidates.append(
            (
                "GENERATIVE_RULE_ORIGIN_CELL",
                generative_origin_cell_wire_bytes,
                "GENERATIVE_PACKET_WIRE_BYTES_MEASURED",
            )
        )
    selected = min(candidates, key=lambda item: (item[1], item[0]))
    return {
        "schema_id": SELECTOR_SCHEMA,
        "state": "PASS_TRANSPORT_SELECTED",
        "selected_mode": selected[0],
        "selected_wire_bytes": selected[1],
        "reason": selected[2],
        "full_transfer_wire_bytes": full_transfer_wire_bytes,
        "candidates": [
            {"mode": mode, "wire_bytes": size, "eligibility": reason}
            for mode, size, reason in candidates
        ],
        "metric_rule": (
            "COMPARE_COMPLETE_SERIALIZED_WIRE_BYTES_INCLUDING_RULE_INDEX_U_ENVELOPE_"
            "HASH_AUTHORITY_AND_REQUIRED_PRECONDITIONS"
        ),
        "authority_effect": "NONE",
    }


__all__ = [
    "EndpointRuleHandshakeHold",
    "SCHEMA",
    "SELECTOR_SCHEMA",
    "observe_endpoint_rule_capability",
    "select_transport",
    "shared_rule_match",
    "universal_executor_match",
]
