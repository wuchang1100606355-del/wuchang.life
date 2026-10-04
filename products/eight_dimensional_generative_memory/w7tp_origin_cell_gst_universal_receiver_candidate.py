#!/usr/bin/env python3
"""Fail-closed receiver-gated consumer for the tracked GST V2.3 universal Origin Cell candidate.

This is a governance adapter around the existing universal successor. It does
not redefine Origin Cell formation, activate a service, mutate canonical
pointers, or create D8 authority. Formal candidate materialization is allowed
only after exact receiver capability matching and receiver-bound envelope
formation.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = Path(__file__).with_name(
    "w7tp_origin_cell_gst_universal_receiver_contract.json"
)


class UniversalReceiverConsumerHold(RuntimeError):
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


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UniversalReceiverConsumerHold("HOLD_JSON_READ_FAILED") from exc
    if not isinstance(value, dict):
        raise UniversalReceiverConsumerHold("HOLD_JSON_OBJECT_REQUIRED")
    return value


def _load_bound_module(
    binding: Mapping[str, Any],
    *,
    module_name: str,
    missing_code: str,
    hash_code: str,
) -> tuple[Any, Path]:
    source_ref = binding.get("source_path")
    expected_hash = binding.get("source_sha256")
    if not isinstance(source_ref, str) or not source_ref:
        raise UniversalReceiverConsumerHold(missing_code)
    source = (ROOT / source_ref).resolve()
    try:
        source.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise UniversalReceiverConsumerHold(missing_code) from exc
    if not source.is_file() or source.is_symlink():
        raise UniversalReceiverConsumerHold(missing_code)
    if sha256_file(source) != expected_hash:
        raise UniversalReceiverConsumerHold(hash_code)
    spec = importlib.util.spec_from_file_location(module_name, source)
    if spec is None or spec.loader is None:
        raise UniversalReceiverConsumerHold(missing_code)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, source


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract = load_json(path)
    if contract.get("schema_version") != (
        "w7tp-origin-cell-gst-universal-receiver-binding/1-candidate"
    ):
        raise UniversalReceiverConsumerHold(
            "HOLD_UNIVERSAL_RECEIVER_CONTRACT_SCHEMA_MISMATCH"
        )
    if contract.get("state") != "CANDIDATE_DISABLED":
        raise UniversalReceiverConsumerHold(
            "HOLD_UNIVERSAL_RECEIVER_CONSUMER_MUST_REMAIN_DISABLED"
        )
    governance = contract.get("governance")
    expected_governance = {
        "canonical": False,
        "runtime_activated": False,
        "service_installed": False,
        "deployed": False,
        "total_field_decision": "NOT_RUN",
        "direct_raw_materialization_formal_allowed": False,
    }
    if governance != expected_governance:
        raise UniversalReceiverConsumerHold(
            "HOLD_UNIVERSAL_RECEIVER_GOVERNANCE_BOUNDARY_INVALID"
        )
    if contract.get("founder_baseline") != "W7TP_8D_ADI_V2.3":
        raise UniversalReceiverConsumerHold(
            "HOLD_UNIVERSAL_RECEIVER_FOUNDER_BASELINE_MISMATCH"
        )
    return contract


def load_bound_components(
    contract: Mapping[str, Any],
) -> tuple[Any, Path, Any, Path]:
    origin, origin_path = _load_bound_module(
        contract.get("universal_successor_binding", {}),
        module_name="w7tp_origin_cell_gst_universal_bound",
        missing_code="HOLD_UNIVERSAL_SUCCESSOR_SOURCE_MISSING",
        hash_code="HOLD_UNIVERSAL_SUCCESSOR_SOURCE_HASH_MISMATCH",
    )
    receiver, receiver_path = _load_bound_module(
        contract.get("receiver_capability_binding", {}),
        module_name="w7tp_receiver_capability_contract_bound",
        missing_code="HOLD_RECEIVER_CAPABILITY_SOURCE_MISSING",
        hash_code="HOLD_RECEIVER_CAPABILITY_SOURCE_HASH_MISMATCH",
    )
    required_origin = (
        "validate_packet",
        "reconstruct_to_directory",
        "protocol_descriptor",
        "material_base_contract",
    )
    required_receiver = (
        "validate_contract",
        "match_universal_executor_capability",
        "build_universal_receiver_bound_envelope",
    )
    if any(not callable(getattr(origin, name, None)) for name in required_origin):
        raise UniversalReceiverConsumerHold(
            "HOLD_UNIVERSAL_SUCCESSOR_ENTRYPOINT_MISSING"
        )
    if any(
        not callable(getattr(receiver, name, None))
        for name in required_receiver
    ):
        raise UniversalReceiverConsumerHold(
            "HOLD_RECEIVER_CAPABILITY_ENTRYPOINT_MISSING"
        )
    return origin, origin_path, receiver, receiver_path


def observe_bound_receiver(
    origin: Any,
    origin_path: Path,
) -> dict[str, Any]:
    descriptor_sha = origin.sha256_bytes(
        origin.canonical_json_bytes(origin.protocol_descriptor())
    )
    return {
        "executor_contract": origin.EXECUTOR_CONTRACT,
        "implementation_sha256": sha256_file(origin_path),
        "protocol_descriptor_sha256": descriptor_sha,
        "material_base_contracts": [
            origin.material_base_contract("ASCII26_SYMBOLS_V1"),
            origin.material_base_contract("OCTET256_V1"),
        ],
        "max_reconstructed_bytes": origin.MAX_RECONSTRUCTED_BYTES,
    }


def _receiver_gate(
    contract: Mapping[str, Any],
    origin: Any,
    origin_path: Path,
    receiver: Any,
    packet: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    receiver_contract = contract.get("receiver_capability_contract")
    if not isinstance(receiver_contract, Mapping):
        raise UniversalReceiverConsumerHold(
            "HOLD_RECEIVER_CAPABILITY_CONTRACT_MISSING"
        )
    try:
        receiver.validate_contract(receiver_contract)
        match = receiver.match_universal_executor_capability(
            receiver_contract,
            observe_bound_receiver(origin, origin_path),
        )
        envelope = receiver.build_universal_receiver_bound_envelope(
            packet,
            receiver_contract,
        )
    except Exception as exc:
        code = getattr(exc, "code", None)
        if isinstance(code, str):
            raise UniversalReceiverConsumerHold(code) from exc
        raise
    return match, envelope


def inspect_binding(
    contract_path: Path = CONTRACT_PATH,
) -> dict[str, Any]:
    contract = load_contract(contract_path)
    origin, origin_path, receiver, _ = load_bound_components(contract)
    receiver_contract = contract["receiver_capability_contract"]
    try:
        receiver.validate_contract(receiver_contract)
        match = receiver.match_universal_executor_capability(
            receiver_contract,
            observe_bound_receiver(origin, origin_path),
        )
    except Exception as exc:
        code = getattr(exc, "code", None)
        if isinstance(code, str):
            raise UniversalReceiverConsumerHold(code) from exc
        raise
    return {
        "state": "PASS_UNIVERSAL_RECEIVER_GATED_BINDING_CANDIDATE",
        "binding_id": contract["binding_id"],
        "origin_source_sha256": sha256_file(origin_path),
        "receiver_contract_sha256": receiver_contract["contract_sha256"],
        "receiver_match_state": match["state"],
        "runtime_activated": False,
        "canonical": False,
        "total_field_decision": "NOT_RUN",
    }


def run_isolated_candidate(
    packet_path: Path,
    workspace: Path,
    *,
    contract_path: Path = CONTRACT_PATH,
) -> dict[str, Any]:
    contract = load_contract(contract_path)
    if workspace.exists():
        raise UniversalReceiverConsumerHold(
            "HOLD_UNIVERSAL_RECEIVER_WORKSPACE_ALREADY_EXISTS"
        )
    origin, origin_path, receiver, _ = load_bound_components(contract)
    packet = load_json(packet_path)
    try:
        validation = origin.validate_packet(packet)
    except Exception as exc:
        code = getattr(exc, "code", None)
        if isinstance(code, str):
            raise UniversalReceiverConsumerHold(code) from exc
        raise

    match, envelope = _receiver_gate(
        contract,
        origin,
        origin_path,
        receiver,
        packet,
    )

    workspace.mkdir(parents=True)
    output = workspace / "reconstructed"
    try:
        receipt = origin.reconstruct_to_directory(packet, output)
    except Exception as exc:
        code = getattr(exc, "code", None)
        if isinstance(code, str):
            raise UniversalReceiverConsumerHold(code) from exc
        raise

    if receipt.get("state") != "PASS_EXACT_GENERATIVE_STATE_RECONSTRUCTION":
        raise UniversalReceiverConsumerHold(
            "HOLD_UNIVERSAL_RECEIVER_MATERIALIZATION_NOT_VERIFIED"
        )
    return {
        "state": (
            "PASS_UNIVERSAL_RECEIVER_GATED_EXACT_RECONSTRUCTION_CANDIDATE"
        ),
        "binding_id": contract["binding_id"],
        "packet_sha256": packet["packet_sha256"],
        "receiver_contract_sha256": (
            contract["receiver_capability_contract"]["contract_sha256"]
        ),
        "receiver_gate_state": match["state"],
        "receiver_bound_envelope_sha256": envelope["envelope_sha256"],
        "target_fact_bytes": validation["target_fact_bytes"],
        "raw_material_u_bytes": validation["raw_material_u_bytes"],
        "target_files": validation["file_count"],
        "reconstruction_state": receipt["state"],
        "difference_analysis_was_transmission": False,
        "canonical_runtime_effect": False,
        "formal_delivery": False,
        "total_field_decision": "NOT_RUN",
        "output_root": str(output),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inspect")
    run = sub.add_parser("isolated-run")
    run.add_argument("--packet", type=Path, required=True)
    run.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = (
            inspect_binding()
            if args.command == "inspect"
            else run_isolated_candidate(args.packet, args.workspace)
        )
    except UniversalReceiverConsumerHold as exc:
        print(
            json.dumps(
                {
                    "state": exc.code,
                    "runtime_activated": False,
                    "canonical": False,
                    "total_field_decision": "NOT_RUN",
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 1
    print(canonical_json_bytes(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
