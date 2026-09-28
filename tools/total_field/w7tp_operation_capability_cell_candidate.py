#!/usr/bin/env python3
"""Reconstruct a read-only composite operation capability from 8D ADI cells.

Candidate-only adapter. It does not execute target operations, grant D8 authority,
change canonical state, or activate runtime bindings.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PACKET = ROOT / "evidence/total_field/operation_capability_cells/NVR_ROUTER_OPERATION_CAPABILITY_ASSIMILATION_CANDIDATE_V1.json"


class OperationCapabilityHold(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def load_packet(path: Path = DEFAULT_PACKET) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OperationCapabilityHold("HOLD_OPERATION_PACKET_UNREADABLE") from exc
    if not isinstance(value, dict):
        raise OperationCapabilityHold("HOLD_OPERATION_PACKET_NOT_OBJECT")
    return value


def validate_operation_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    if packet.get("state") != "PASS_READ_ONLY_ASSIMILATION" or packet.get("operation") != "ASSIMILATE":
        raise OperationCapabilityHold("HOLD_OPERATION_PACKET_ASSIMILATION_STATE_INVALID")
    for dim in ("d1", "d2", "d3", "d4", "d5", "d6", "d7", "d8"):
        if not isinstance(packet.get(dim), Mapping):
            raise OperationCapabilityHold("HOLD_OPERATION_PACKET_8D_INCOMPLETE")
    d5, d6, d7, d8 = packet["d5"], packet["d6"], packet["d7"], packet["d8"]
    if d5.get("direct_write_effect") is not False or d5.get("execution_policy") != "READ_ONLY_CANDIDATE_RECONSTRUCTION":
        raise OperationCapabilityHold("HOLD_OPERATION_PACKET_D5_WRITE_OR_POLICY_INVALID")
    if d6.get("mode") != "CAPABILITY_CELL_RELATION_RECONSTRUCTION_CANDIDATE" or d6.get("execution_is_not_implied") is not True:
        raise OperationCapabilityHold("HOLD_OPERATION_PACKET_D6_CONTRACT_INVALID")
    if d7.get("fail_closed") is not True or d7.get("write_effect_forbidden") is not True:
        raise OperationCapabilityHold("HOLD_OPERATION_PACKET_D7_FAIL_CLOSED_REQUIRED")
    if not (d8.get("authority") == "NONE" and d8.get("candidate_only") is True and d8.get("canonical") is False and d8.get("provider_authority") is False and d8.get("total_field_verify_required") is True):
        raise OperationCapabilityHold("HOLD_OPERATION_PACKET_D8_AUTHORITY_WALL_INVALID")

    model = packet.get("cell_model")
    if not isinstance(model, Mapping):
        raise OperationCapabilityHold("HOLD_OPERATION_CELL_MODEL_MISSING")
    cells = model.get("cells")
    relations = model.get("relations")
    conditions = model.get("reconstruction_conditions")
    if not isinstance(cells, list) or not cells or not isinstance(relations, list) or not isinstance(conditions, list) or not conditions:
        raise OperationCapabilityHold("HOLD_OPERATION_CELL_MODEL_INVALID")
    cell_ids: set[str] = set()
    capability_ids: set[str] = set()
    for cell in cells:
        if not isinstance(cell, Mapping):
            raise OperationCapabilityHold("HOLD_OPERATION_CELL_INVALID")
        cell_id = cell.get("cell_id")
        capability_id = cell.get("capability_id")
        coordinate_ref = cell.get("coordinate_ref")
        evidence_refs = cell.get("evidence_refs")
        if not all(isinstance(value, str) and value for value in (cell_id, capability_id, coordinate_ref)):
            raise OperationCapabilityHold("HOLD_OPERATION_CELL_ID_OR_COORDINATE_INVALID")
        if cell_id in cell_ids or capability_id in capability_ids:
            raise OperationCapabilityHold("HOLD_OPERATION_CELL_DUPLICATE")
        if cell.get("effect_mode") != "READ_ONLY" or not isinstance(evidence_refs, list) or not evidence_refs or not all(isinstance(ref, str) and ref for ref in evidence_refs):
            raise OperationCapabilityHold("HOLD_OPERATION_CELL_EFFECT_OR_EVIDENCE_INVALID")
        cell_ids.add(cell_id)
        capability_ids.add(capability_id)
    declared = packet.get("capabilities")
    if not isinstance(declared, list) or {item.get("capability_id") for item in declared if isinstance(item, Mapping)} != capability_ids:
        raise OperationCapabilityHold("HOLD_OPERATION_CELL_CAPABILITY_BINDING_MISMATCH")
    for relation in relations:
        if not isinstance(relation, Mapping) or relation.get("from") not in cell_ids or relation.get("to") not in cell_ids or not isinstance(relation.get("relation"), str):
            raise OperationCapabilityHold("HOLD_OPERATION_CELL_RELATION_INVALID")
    return {"state": "PASS_OPERATION_CAPABILITY_CELL_PACKET_VALIDATED", "cell_count": len(cells), "cell_ids": sorted(cell_ids)}


def reconstruct_composite_capability(packet: Mapping[str, Any]) -> dict[str, Any]:
    validation = validate_operation_packet(packet)
    model = packet["cell_model"]
    cells = sorted((copy.deepcopy(cell) for cell in model["cells"]), key=lambda item: item["cell_id"])
    relations = sorted((copy.deepcopy(rel) for rel in model["relations"]), key=lambda item: (item["from"], item["to"], item["relation"]))
    evidence_binding = [{"cell_id": cell["cell_id"], "coordinate_ref": cell["coordinate_ref"], "evidence_refs": cell["evidence_refs"]} for cell in cells]
    composite = {
        "state": "PASS_COMPOSITE_OPERATION_CAPABILITY_RECONSTRUCTED_CANDIDATE",
        "capability_ids": [cell["capability_id"] for cell in cells],
        "cells": cells,
        "relations": relations,
        "reconstruction_conditions": copy.deepcopy(model["reconstruction_conditions"]),
        "acceptance": model.get("acceptance"),
        "effect_mode": "READ_ONLY",
        "execution_performed": False,
        "effect_authorized": False,
        "canonical": False,
        "provider_authority": False,
        "total_field_verify_required": True,
        "cell_graph_sha256": sha256_value({"cells": cells, "relations": relations}),
        "evidence_binding_sha256": sha256_value(evidence_binding),
    }
    composite["composite_sha256"] = sha256_value(composite)
    return {"validation": validation, "composite": composite}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    args = parser.parse_args()
    try:
        result = reconstruct_composite_capability(load_packet(args.packet))
    except OperationCapabilityHold as exc:
        print(json.dumps({"state": "HOLD", "reason": exc.code}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
