#!/usr/bin/env python3
"""Fail-closed GST 2.3 runtime-consumer binding candidate.

This adapter binds a received packet to the existing Origin Cell implementation.
It does not install a service, mutate a canonical pointer, or activate by default.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = Path(__file__).with_name("w7tp_gst_v23_runtime_consumer_contract.json")


class ConsumerHold(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConsumerHold("HOLD_JSON_READ_FAILED") from exc
    if not isinstance(value, dict):
        raise ConsumerHold("HOLD_JSON_OBJECT_REQUIRED")
    return value


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract = load_json(path)
    if contract.get("schema_version") != "w7tp-gst-v23-runtime-consumer-binding/1-candidate":
        raise ConsumerHold("HOLD_CONSUMER_CONTRACT_SCHEMA_MISMATCH")
    if contract.get("state") != "CANDIDATE_DISABLED":
        raise ConsumerHold("HOLD_CONSUMER_MUST_REMAIN_DISABLED")
    authority = contract.get("authority_resolution", {})
    if authority.get("founder_current_baseline") != "W7TP_8D_ADI_V2.3":
        raise ConsumerHold("HOLD_FOUNDER_V23_BASELINE_MISSING")
    if authority.get("legacy_v2_1_master_pointer_role") != "STALE_HISTORICAL_COORDINATE_NOT_CURRENT_VERSION_AUTHORITY":
        raise ConsumerHold("HOLD_AUTHORITY_SCOPE_RESOLUTION_INVALID")
    relation = contract.get("consumer_relation", {})
    required_false = (
        "differential_transfer_allowed",
        "file_copy_fallback_allowed",
        "automatic_fallback_allowed",
        "received_rule_code_formal_contract",
    )
    if any(relation.get(key) is not False for key in required_false):
        raise ConsumerHold("HOLD_FORBIDDEN_CONSUMER_SEMANTICS")
    governance = contract.get("governance", {})
    if governance != {
        "canonical": False,
        "runtime_activated": False,
        "service_installed": False,
        "deployed": False,
        "total_field_decision": "NOT_RUN",
    }:
        raise ConsumerHold("HOLD_CANDIDATE_GOVERNANCE_BOUNDARY_INVALID")
    return contract


def load_origin_cell(contract: dict[str, Any]) -> Any:
    binding = contract["existing_implementation_binding"]
    source = ROOT / binding["source_path"]
    if not source.is_file() or source.is_symlink():
        raise ConsumerHold("HOLD_ORIGIN_CELL_SOURCE_MISSING")
    if sha256_file(source) != binding["source_sha256"]:
        raise ConsumerHold("HOLD_ORIGIN_CELL_SOURCE_HASH_MISMATCH")
    spec = importlib.util.spec_from_file_location("w7tp_origin_cell_generative_v2_bound", source)
    if spec is None or spec.loader is None:
        raise ConsumerHold("HOLD_ORIGIN_CELL_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("validate_rule_packet", "execute_reconstruction_rules", "reconstruct_from_rule_packet"):
        if not callable(getattr(module, name, None)):
            raise ConsumerHold("HOLD_ORIGIN_CELL_ENTRYPOINT_MISSING")
    if module.PACKET_SCHEMA != binding["packet_schema"]:
        raise ConsumerHold("HOLD_PACKET_SCHEMA_BINDING_MISMATCH")
    return module


def inspect_binding(contract_path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract = load_contract(contract_path)
    load_origin_cell(contract)
    return {
        "state": "PASS_GST_V23_RUNTIME_CONSUMER_BINDING_CANDIDATE",
        "binding_id": contract["binding_id"],
        "founder_current_baseline": "W7TP_8D_ADI_V2.3",
        "origin_cell_source_sha256": contract["existing_implementation_binding"]["source_sha256"],
        "runtime_activated": False,
        "service_installed": False,
        "total_field_decision": "NOT_RUN",
    }


def run_isolated_candidate(packet_path: Path, workspace: Path) -> dict[str, Any]:
    contract = load_contract()
    origin_cell = load_origin_cell(contract)
    if workspace.exists():
        raise ConsumerHold("HOLD_WORKSPACE_ALREADY_EXISTS")
    packet = load_json(packet_path)
    origin_cell.validate_rule_packet(packet, Path(origin_cell.__file__).resolve())
    receiver = workspace / "empty_receiver"
    output = workspace / "reconstructed"
    receiver.mkdir(parents=True)
    receipt = origin_cell.reconstruct_from_rule_packet(packet, receiver, output)
    return {
        "state": "PASS_ISOLATED_GST_V23_CONSUMER_RECONSTRUCTION",
        "binding_id": contract["binding_id"],
        "packet_sha256": receipt["packet_sha256"],
        "target_manifest_sha256": receipt["target_manifest_sha256"],
        "target_bytes": receipt["target_bytes"],
        "target_files": receipt["target_files"],
        "differential_payload_bytes": receipt["differential_payload_bytes"],
        "transmitted_target_bytes": receipt["transmitted_target_bytes"],
        "runtime_activated": False,
        "candidate_isolated_execution": True,
        "formal_delivery": False,
        "total_field_decision": "NOT_RUN",
    }


def activate_once(packet_path: Path, workspace: Path, activation_receipt_path: Path) -> dict[str, Any]:
    del packet_path, workspace, activation_receipt_path
    load_contract()
    raise ConsumerHold("HOLD_FORMAL_ACTIVATION_ADAPTER_NOT_BOUND")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("inspect")
    isolated = commands.add_parser("isolated-run")
    isolated.add_argument("--packet", type=Path, required=True)
    isolated.add_argument("--workspace", type=Path, required=True)
    activate = commands.add_parser("activate")
    activate.add_argument("--packet", type=Path, required=True)
    activate.add_argument("--workspace", type=Path, required=True)
    activate.add_argument("--activation-receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect_binding()
        elif args.command == "isolated-run":
            result = run_isolated_candidate(args.packet, args.workspace)
        else:
            result = activate_once(args.packet, args.workspace, args.activation_receipt)
    except ConsumerHold as exc:
        print(json.dumps({"state": exc.code, "runtime_activated": False, "total_field_decision": "NOT_RUN"}))
        return 1
    print(canonical_json_bytes(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
