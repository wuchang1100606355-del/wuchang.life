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
import zlib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = Path(__file__).with_name("w7tp_gst_v23_runtime_consumer_contract.json")


class ConsumerHold(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


_DIFF_KEYS = frozenset({
    "diff", "delta", "deltas", "upserts", "base_copy", "set_fixed",
    "byte_patch", "changed_bytes", "file_fragment", "literal_bytes",
    "source_target", "previous_state", "prior_state",
})
_DIFF_OPCODES = frozenset({"BASE_COPY", "SET_FIXED", "INSERT", "DELETE", "LITERAL"})


def require_discrete_generative_identity(value: Any) -> None:
    """Reject floating parameters and legacy diff masquerading before any execution."""
    if type(value) is float:
        raise ConsumerHold("HOLD_FLOAT_PARAMETER_FORBIDDEN")
    if isinstance(value, dict):
        for key, nested in value.items():
            name = str(key).strip().lower().replace("-", "_")
            if name in _DIFF_KEYS or name.endswith(("_delta", "_diff", "_upserts")):
                raise ConsumerHold("HOLD_DIFF_MASQUERADING_AS_D6_REJECTED")
            require_discrete_generative_identity(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            require_discrete_generative_identity(nested)
    elif isinstance(value, str) and value.strip().upper() in _DIFF_OPCODES:
        raise ConsumerHold("HOLD_DIFF_MASQUERADING_AS_D6_REJECTED")


def load_binary_origin_cell(contract: dict[str, Any]) -> Any:
    binding = contract.get("binary_origin_cell_binding")
    if not isinstance(binding, dict):
        raise ConsumerHold("HOLD_BINARY_ORIGIN_CELL_CONTRACT_REQUIRED")
    source_ref = binding.get("source_path")
    if not isinstance(source_ref, str) or not source_ref:
        raise ConsumerHold("HOLD_BINARY_ORIGIN_CELL_CONTRACT_REQUIRED")
    source = ROOT / source_ref
    if not source.is_file() or source.is_symlink():
        raise ConsumerHold("HOLD_BINARY_ORIGIN_CELL_SOURCE_MISSING")
    try:
        source.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ConsumerHold("HOLD_BINARY_ORIGIN_CELL_PATH_OUTSIDE_ROOT") from exc
    if sha256_file(source) != binding.get("source_sha256"):
        raise ConsumerHold("HOLD_BINARY_ORIGIN_CELL_SOURCE_HASH_MISMATCH")
    spec = importlib.util.spec_from_file_location("w7tp_origin_cell_codec_v2_bound", source)
    if spec is None or spec.loader is None:
        raise ConsumerHold("HOLD_BINARY_ORIGIN_CELL_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "UniversalOriginCellDecoder", None)):
        raise ConsumerHold("HOLD_BINARY_ORIGIN_CELL_DECODER_MISSING")
    return module


def _preflight_binary_output(
    packet: bytes, decoder: Any, *, max_packet: int,
    max_bundle: int, max_output: int,
) -> dict[int, int]:
    """Bound decompression and calculate output sizes without materializing output."""
    if not isinstance(packet, bytes) or not packet:
        raise ConsumerHold("HOLD_ORIGIN_CELL_BINARY_PACKET_REQUIRED")
    if len(packet) > max_packet:
        raise ConsumerHold("HOLD_D7_PACKET_RESOURCE_LIMIT")
    magic = packet[0]
    if magic == 0x8E:
        if len(packet) < 4:
            raise ConsumerHold("HOLD_PACKET_TRUNCATED")
        flag = packet[1]
        bundle_length = int.from_bytes(packet[2:4], "big")
        pos = 4
        if bundle_length < 1 or pos + bundle_length > len(packet):
            raise ConsumerHold("HOLD_SELF_CONTAINED_BUNDLE_TRUNCATED")
        bundle = packet[pos:pos + bundle_length]
        pos += bundle_length
        if flag == 1:
            inflater = zlib.decompressobj()
            try:
                expanded = inflater.decompress(bundle, max_bundle + 1)
                if len(expanded) > max_bundle or inflater.unconsumed_tail:
                    raise ConsumerHold("HOLD_D7_SUBSTRATE_RESOURCE_LIMIT")
                expanded += inflater.flush(max_bundle + 1 - len(expanded))
            except zlib.error as exc:
                raise ConsumerHold("HOLD_SUBSTRATE_DECOMPRESS_FAILED") from exc
            if len(expanded) > max_bundle:
                raise ConsumerHold("HOLD_D7_SUBSTRATE_RESOURCE_LIMIT")
            if not inflater.eof or inflater.unused_data or inflater.unconsumed_tail:
                raise ConsumerHold("HOLD_ZLIB_SUBSTREAM_TRAILING_BYTES")
            bundle = expanded
        elif flag != 0:
            raise ConsumerHold("HOLD_INVALID_COMPRESSION_FLAG")
        if len(bundle) > max_bundle:
            raise ConsumerHold("HOLD_D7_SUBSTRATE_RESOURCE_LIMIT")
        luts, templates = decoder._parse_bundle(bundle)
    elif magic == 0x8D:
        pos = 0
        luts, templates = decoder.luts, decoder.tpls
        if decoder.packets_decoded < 1:
            raise ConsumerHold("HOLD_WARM_SESSION_SUBSTRATE_REQUIRED")
    else:
        raise ConsumerHold("HOLD_INVALID_PACKET_MAGIC")

    def read(fmt: str) -> tuple[int, ...]:
        nonlocal pos
        value, pos = decoder._read(packet, pos, fmt)
        return value

    header, channels = read(">BB")
    if header != 0x8D or channels < 1:
        raise ConsumerHold("HOLD_INVALID_MUX_HEADER_OR_CHANNEL_COUNT")
    sizes: dict[int, int] = {}
    total, generated = 0, False
    for expected_id in range(1, channels + 1):
        target_id, op_count = read(">BB")
        if target_id != expected_id or op_count < 1:
            raise ConsumerHold("HOLD_INVALID_TARGET_ID_OR_OP_COUNT")
        size = 0
        for _ in range(op_count):
            (op,) = read(">B")
            increase = 0
            if op == 1:
                lid, tid, rows, columns, repeat = read(">BBBBB")
                if lid not in luts or tid not in templates or min(rows, columns, repeat) < 1:
                    raise ConsumerHold("HOLD_INVALID_TEMPLATE_SEQ_PARAMS")
                for _ in range(rows):
                    indices = read(f">{columns}B")
                    for part in templates[tid]:
                        index = (-part - 1)
                        if part >= 0:
                            index = part
                        else:
                            if index >= columns:
                                raise ConsumerHold("HOLD_TEMPLATE_VAR_OUT_OF_RANGE")
                            index = indices[index]
                        if index >= len(luts[lid]):
                            raise ConsumerHold("HOLD_LUT_COORDINATE_OUT_OF_RANGE")
                        increase += len(luts[lid][index])
                increase *= repeat
                generated = True
            elif op == 2:
                lid, coord, count = read(">BBH")
                if lid not in luts or coord >= len(luts[lid]) or count < 1:
                    raise ConsumerHold("HOLD_LUT_RUN_OUT_OF_RANGE")
                increase = len(luts[lid][coord]) * count
                generated = True
            elif op == 3:
                lid, segments, rows = read(">BBB")
                if lid not in luts or min(segments, rows) < 1:
                    raise ConsumerHold("HOLD_INVALID_PATTERN_2D_HEADER")
                row_size = 0
                for _ in range(segments):
                    coord, repeat = read(">BB")
                    if coord >= len(luts[lid]) or repeat < 1:
                        raise ConsumerHold("HOLD_PATTERN_2D_OUT_OF_RANGE")
                    row_size += len(luts[lid][coord]) * repeat
                increase = row_size * rows
                generated = True
            elif op == 4:
                period, repeat = read(">BH")
                if period < 1 or repeat < 1 or pos + period > len(packet):
                    raise ConsumerHold("HOLD_INVALID_RAW_REPEAT_PARAMS")
                pos += period
                increase = period * repeat
                generated = True
            elif op == 5:
                _, _, width, rows = read(">BBBB")
                if width < 1 or rows < 1:
                    raise ConsumerHold("HOLD_INVALID_ARITH_2D_PARAMS")
                increase = width * rows
                generated = True
            elif op == 6:
                (literal_bytes,) = read(">H")
                if literal_bytes < 1 or pos + literal_bytes > len(packet):
                    raise ConsumerHold("HOLD_INVALID_RAW_LITERAL")
                pos += literal_bytes
                increase = literal_bytes
            elif op == 7:
                (count,) = read(">B")
                if count < 1:
                    raise ConsumerHold("HOLD_EMPTY_SPARSE_PATCH")
                for _ in range(count):
                    offset, _ = read(">HB")
                    if offset >= size:
                        raise ConsumerHold("HOLD_SPARSE_PATCH_OUT_OF_BOUNDS")
            else:
                raise ConsumerHold("HOLD_DIFF_MASQUERADING_AS_D6_REJECTED")
            size += increase
            if size > max_output or total + size > max_output:
                raise ConsumerHold("HOLD_D7_RECONSTRUCTION_RESOURCE_LIMIT")
        sizes[target_id] = size
        total += size
    if pos != len(packet):
        raise ConsumerHold("HOLD_TRAILING_GARBAGE_BYTES")
    if not generated:
        raise ConsumerHold("HOLD_DIFF_MASQUERADING_AS_D6_REJECTED")
    return sizes


def reconstruct_binary_session(packets: list[bytes], *,
                               contract_path: Path = CONTRACT_PATH) -> dict[str, Any]:
    """Decode cold→warm in one authorized substrate session, without disk writes."""
    if not isinstance(packets, list) or not packets or len(packets) > 256:
        raise ConsumerHold("HOLD_D7_PACKET_RESOURCE_LIMIT")
    contract = load_contract(contract_path)
    module = load_binary_origin_cell(contract)
    limits = contract["binary_origin_cell_binding"]
    decoder = module.UniversalOriginCellDecoder()
    outputs: list[dict[str, Any]] = []
    for packet in packets:
        predicted = _preflight_binary_output(
            packet, decoder,
            max_packet=limits["max_packet_bytes"],
            max_bundle=limits["max_bundle_bytes"],
            max_output=limits["max_reconstructed_bytes"],
        )
        reconstructed = decoder.decode(packet)
        if {key: len(value) for key, value in reconstructed.items()} != predicted:
            raise ConsumerHold("HOLD_D7_OUTPUT_SIZE_MISMATCH")
        outputs.append({
            "magic": hex(packet[0]),
            "packet_bytes": len(packet),
            "reconstructed_bytes": sum(predicted.values()),
            "channels_sha256": {str(k): hashlib.sha256(v).hexdigest()
                                for k, v in reconstructed.items()},
        })
    return {
        "state": "PASS_ISOLATED_BINARY_ORIGIN_CELL_RECONSTRUCTION",
        "codec_sha256": limits["source_sha256"],
        "binary_session_outputs": outputs,
        "formal_delivery": False,
        "total_field_decision": "NOT_RUN",
    }


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
    if contract.get("schema_version") != "w7tp-gst-v23-runtime-consumer-binding/2-active":
        raise ConsumerHold("HOLD_CONSUMER_CONTRACT_SCHEMA_MISMATCH")
    if contract.get("state") != "ACTIVE_FOUNDER_AUTHORIZED_RUNTIME_BINDING":
        raise ConsumerHold("HOLD_CONSUMER_CONTRACT_NOT_ACTIVE")
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
        "runtime_activated": True,
        "service_installed": False,
        "deployed": True,
        "total_field_decision": "PASS",
    }:
        raise ConsumerHold("HOLD_ACTIVE_GOVERNANCE_BOUNDARY_INVALID")
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
    load_binary_origin_cell(contract)
    return {
        "state": "PASS_GST_V23_RUNTIME_CONSUMER_STATIC_BINDING",
        "binding_id": contract["binding_id"],
        "founder_current_baseline": "W7TP_8D_ADI_V2.3",
        "origin_cell_source_sha256": contract["existing_implementation_binding"]["source_sha256"],
        "binary_origin_cell_sha256": contract["binary_origin_cell_binding"]["source_sha256"],
        "discrete_identity_gate": "BOUND_BOTH_GENERATIVE_CAPABILITIES",
        "runtime_activated": False,
        "service_installed": False,
        "total_field_decision": "REQUIRES_SEPARATE_D8_RUNTIME_CHECK",
    }


def preflight_rule_resource_budget(packet: dict[str, Any], contract: dict[str, Any]) -> None:
    """Conservative upper budget, checked before any clean-room output is created."""
    max_bytes = contract["binary_origin_cell_binding"]["max_reconstructed_bytes"]
    total = 0
    for rule in packet.get("reconstruction_rules", []):
        primitive = rule.get("primitive")
        def nonnegative(name: str) -> int:
            value = rule.get(name)
            if type(value) is not int or value < 0:
                raise ConsumerHold("HOLD_D7_RULE_RESOURCE_PARAMETER_INVALID")
            return value

        if primitive == "CREATE_DIRECTORY":
            cost = 0
        elif primitive == "WRITE_PRNG_BYTES":
            cost = nonnegative("size")
            seed = rule.get("seed")
            if type(seed) is not int:
                raise ConsumerHold("HOLD_D7_RULE_RESOURCE_PARAMETER_INVALID")
        elif primitive == "WRITE_DETERMINISTIC_BYTES_AT_OFFSETS":
            size = nonnegative("size")
            writes = rule.get("writes")
            if not isinstance(writes, list) or len(writes) > 65536:
                raise ConsumerHold("HOLD_D7_RULE_RESOURCE_PARAMETER_INVALID")
            cost = max((w["offset"] + size for w in writes
                        if isinstance(w, dict) and type(w.get("offset")) is int
                        and w["offset"] >= 0), default=0)
            if len(writes) != sum(isinstance(w, dict) and
                                 type(w.get("offset")) is int and w["offset"] >= 0
                                 for w in writes):
                raise ConsumerHold("HOLD_D7_RULE_RESOURCE_PARAMETER_INVALID")
        elif primitive == "JSONL_WRITE":
            cost = nonnegative("row_count") * 2048
        elif primitive == "SQLITE_BUILD":
            cost = (nonnegative("base_rows") + nonnegative("insert_rows")) * 69632
            nonnegative("update_rows")
        elif primitive == "WRITE_DETERMINISTIC_FILE_SERIES":
            files = nonnegative("base_count") + nonnegative("new_count")
            cost = files * nonnegative("file_size")
            for key in ("replace_count", "delete_start", "delete_end",
                        "rename_start", "rename_end"):
                nonnegative(key)
        else:
            raise ConsumerHold("HOLD_DIFF_MASQUERADING_AS_D6_REJECTED")
        total += cost
        if total > max_bytes:
            raise ConsumerHold("HOLD_D7_RECONSTRUCTION_RESOURCE_LIMIT")


def run_isolated_candidate(packet_path: Path, workspace: Path) -> dict[str, Any]:
    contract = load_contract()
    origin_cell = load_origin_cell(contract)
    if workspace.exists():
        raise ConsumerHold("HOLD_WORKSPACE_ALREADY_EXISTS")
    packet = load_json(packet_path)
    require_discrete_generative_identity(packet)
    origin_cell.validate_rule_packet(packet, Path(origin_cell.__file__).resolve())
    preflight_rule_resource_budget(packet, contract)
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
    contract = load_contract()
    activation = load_json(activation_receipt_path)
    expected = {
        "schema_version": "w7tp-gst-v23-founder-runtime-activation/1",
        "state": "FOUNDER_DIRECT_RUNTIME_ACTIVATION_AUTHORIZED",
        "binding_id": contract["binding_id"],
        "founder_baseline": "W7TP_8D_ADI_V2.3",
        "contract_sha256": sha256_file(CONTRACT_PATH),
        "activation_scope": "GST_V23_RUNTIME_CONSUMER_BINDING_ONLY",
        "canonical_pointer_change": False,
        "service_restart": False,
        "rollback_operation": contract["rollback"]["operation"],
    }
    if any(activation.get(key) != value for key, value in expected.items()):
        raise ConsumerHold("HOLD_FOUNDER_ACTIVATION_RECORD_INVALID")
    if not activation.get("reviewed_commit") or not activation.get("founder_directive_ref"):
        raise ConsumerHold("HOLD_FOUNDER_ACTIVATION_RECORD_INVALID")
    result = run_isolated_candidate(packet_path, workspace)
    result.update(
        state="PASS_FOUNDER_AUTHORIZED_GST_V23_RUNTIME_RECONSTRUCTION",
        runtime_activated=True,
        candidate_isolated_execution=False,
        founder_authorized_delivery=True,
        formal_delivery=False,
        activation_authority="FOUNDER_DIRECT_GOVERNANCE_COMMAND",
        activation_receipt_sha256=sha256_file(activation_receipt_path),
        total_field_decision="NOT_RUN",
    )
    return result


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
    activate.add_argument("--result-receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect_binding()
        elif args.command == "isolated-run":
            result = run_isolated_candidate(args.packet, args.workspace)
        else:
            result = activate_once(args.packet, args.workspace, args.activation_receipt)
            if args.result_receipt.exists():
                raise ConsumerHold("HOLD_RESULT_RECEIPT_ALREADY_EXISTS")
            args.result_receipt.parent.mkdir(parents=True, exist_ok=True)
            args.result_receipt.write_bytes(canonical_json_bytes(result) + b"\n")
    except ConsumerHold as exc:
        print(json.dumps({"state": exc.code, "runtime_activated": False, "total_field_decision": "NOT_RUN"}))
        return 1
    print(canonical_json_bytes(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
