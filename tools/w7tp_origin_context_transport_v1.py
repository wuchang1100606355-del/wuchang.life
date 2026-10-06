#!/usr/bin/env python3
"""Rule-base transport adapter for model-visible Total Field context.

This adapter only selects and envelopes an existing transport capability.
Origin Cell formation/reconstruction, receiver capability matching, and D8
boundaries remain owned by their existing modules.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "W7TP_TOTAL_FIELD_CONTEXT_RULE_BASE_TRANSPORT/1.0"
PAYLOAD_PATH = "dynamic_context.json"


class ContextTransportHold(RuntimeError):
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


def _load(path: Path, name: str) -> Any:
    if not path.is_file() or path.is_symlink():
        raise ContextTransportHold("HOLD_CONTEXT_TRANSPORT_COMPONENT_MISSING")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContextTransportHold("HOLD_CONTEXT_TRANSPORT_COMPONENT_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _components(root: Path) -> tuple[Any, Any, Any, dict[str, Any]]:
    base = root / "products/eight_dimensional_generative_memory"
    origin = _load(
        base / "w7tp_origin_cell_gst_universal_v23_candidate.py",
        "w7tp_context_transport_origin",
    )
    receiver = _load(
        base / "w7tp_receiver_capability_contract_v1.py",
        "w7tp_context_transport_receiver",
    )
    handshake = _load(
        base / "w7tp_endpoint_rule_handshake_v1.py",
        "w7tp_context_transport_handshake",
    )
    contract_path = (
        base / "w7tp_origin_cell_gst_universal_receiver_contract.json"
    )
    try:
        binding = json.loads(contract_path.read_text(encoding="utf-8"))
        contract = binding["receiver_capability_contract"]
        receiver.validate_contract(contract)
    except Exception as exc:
        code = getattr(exc, "code", None)
        raise ContextTransportHold(
            code if isinstance(code, str) else "HOLD_CONTEXT_RECEIVER_CONTRACT_INVALID"
        ) from exc
    return origin, receiver, handshake, contract


def _packet_wrapper(
    *,
    packet: Mapping[str, Any],
    envelope: Mapping[str, Any],
    target_sha256: str,
    target_bytes: int,
    receiver_handshake_sha256: str,
    receiver_node_ref: str,
    base_id: str,
) -> dict[str, Any]:
    return {
        "schema_id": SCHEMA,
        "mode": "SHARED_RULE_ORIGIN_CELL",
        "payload_path": PAYLOAD_PATH,
        "target_sha256": target_sha256,
        "target_bytes": target_bytes,
        "receiver_handshake_sha256": receiver_handshake_sha256,
        "receiver_node_ref": receiver_node_ref,
        "base_id": base_id,
        "packet": dict(packet),
        "receiver_bound_envelope": dict(envelope),
        "authority": {
            "canonical": False,
            "formal_authority": False,
            "execution_authorized": False,
            "authority_effect": "NONE",
        },
    }


def _full_wrapper(
    *,
    payload: Mapping[str, Any],
    target_sha256: str,
    target_bytes: int,
) -> dict[str, Any]:
    return {
        "schema_id": SCHEMA,
        "mode": "FULL_TRANSFER",
        "payload_path": PAYLOAD_PATH,
        "target_sha256": target_sha256,
        "target_bytes": target_bytes,
        "payload": dict(payload),
        "authority": {
            "canonical": False,
            "formal_authority": False,
            "execution_authorized": False,
            "authority_effect": "NONE",
        },
    }


def build_transport(
    payload: Mapping[str, Any],
    receiver_handshake: Mapping[str, Any],
    *,
    root: Path,
    source_state_root: Path | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ContextTransportHold("HOLD_CONTEXT_TRANSPORT_PAYLOAD_INVALID")
    root = root.resolve()
    origin, receiver, handshake, receiver_contract = _components(root)
    source_handshake = handshake.observe_endpoint_rule_capability(
        root=root,
        node_ref="taiji01-total-field",
        state_root=source_state_root,
    )
    try:
        shared_match = handshake.universal_executor_match(
            source_handshake,
            receiver_handshake,
        )
    except Exception as exc:
        code = getattr(exc, "code", None)
        raise ContextTransportHold(
            code if isinstance(code, str) else "HOLD_CONTEXT_SHARED_RULE_MATCH_FAILED"
        ) from exc

    raw = canonical_json_bytes(dict(payload))
    target_sha = hashlib.sha256(raw).hexdigest()
    full = _full_wrapper(
        payload=payload,
        target_sha256=target_sha,
        target_bytes=len(raw),
    )
    full_wire = len(canonical_json_bytes(full))

    best_origin: tuple[int, dict[str, Any], str] | None = None
    receiver_handshake_bytes = len(canonical_json_bytes(receiver_handshake))
    for base_id in ("ASCII26_SYMBOLS_V1", "OCTET256_V1"):
        packet = origin.build_packet(
            {PAYLOAD_PATH: raw},
            default_base_id=base_id,
        )
        try:
            envelope = receiver.build_universal_receiver_bound_envelope(
                packet,
                receiver_contract,
            )
        except Exception as exc:
            code = getattr(exc, "code", None)
            raise ContextTransportHold(
                code
                if isinstance(code, str)
                else "HOLD_CONTEXT_RECEIVER_ENVELOPE_FAILED"
            ) from exc
        wrapped = _packet_wrapper(
            packet=packet,
            envelope=envelope,
            target_sha256=target_sha,
            target_bytes=len(raw),
            receiver_handshake_sha256=str(
                receiver_handshake.get("handshake_sha256") or ""
            ),
            receiver_node_ref=str(
                receiver_handshake.get("node_ref") or ""
            ),
            base_id=base_id,
        )
        wire = len(canonical_json_bytes(wrapped)) + receiver_handshake_bytes
        if best_origin is None or wire < best_origin[0]:
            best_origin = (wire, wrapped, base_id)

    if best_origin is None:
        raise ContextTransportHold("HOLD_CONTEXT_ORIGIN_CELL_FORMATION_FAILED")
    decision = handshake.select_transport(
        full_transfer_wire_bytes=full_wire,
        shared_rule_origin_cell_wire_bytes=best_origin[0],
        shared_rule_match_state=shared_match,
    )
    return (
        best_origin[1]
        if decision["selected_mode"] == "SHARED_RULE_ORIGIN_CELL"
        else full
    )


def reconstruct_transport(
    transport: Mapping[str, Any],
    *,
    root: Path,
) -> dict[str, Any]:
    if not isinstance(transport, Mapping) or transport.get("schema_id") != SCHEMA:
        raise ContextTransportHold("HOLD_CONTEXT_TRANSPORT_SCHEMA_MISMATCH")
    root = root.resolve()
    origin, receiver, handshake, receiver_contract = _components(root)
    mode = transport.get("mode")

    if mode == "FULL_TRANSFER":
        payload = transport.get("payload")
        if not isinstance(payload, Mapping):
            raise ContextTransportHold("HOLD_CONTEXT_FULL_PAYLOAD_INVALID")
        raw = canonical_json_bytes(dict(payload))
    elif mode == "SHARED_RULE_ORIGIN_CELL":
        receiver_node_ref = transport.get("receiver_node_ref")
        if not isinstance(receiver_node_ref, str) or not receiver_node_ref:
            raise ContextTransportHold(
                "HOLD_CONTEXT_RECEIVER_NODE_REF_MISSING"
            )
        local_handshake = handshake.observe_endpoint_rule_capability(
            root=root,
            node_ref=receiver_node_ref,
            state_root=None,
        )
        if (
            transport.get("receiver_handshake_sha256")
            != local_handshake.get("handshake_sha256")
        ):
            raise ContextTransportHold(
                "HOLD_CONTEXT_RECEIVER_HANDSHAKE_DRIFT"
            )
        packet = transport.get("packet")
        supplied_envelope = transport.get("receiver_bound_envelope")
        if not isinstance(packet, Mapping) or not isinstance(
            supplied_envelope, Mapping
        ):
            raise ContextTransportHold("HOLD_CONTEXT_ORIGIN_PACKET_INVALID")
        try:
            expected_envelope = receiver.build_universal_receiver_bound_envelope(
                packet,
                receiver_contract,
            )
        except Exception as exc:
            code = getattr(exc, "code", None)
            raise ContextTransportHold(
                code
                if isinstance(code, str)
                else "HOLD_CONTEXT_RECEIVER_ENVELOPE_INVALID"
            ) from exc
        if (
            expected_envelope.get("envelope_sha256")
            != supplied_envelope.get("envelope_sha256")
        ):
            raise ContextTransportHold(
                "HOLD_CONTEXT_RECEIVER_ENVELOPE_MISMATCH"
            )
        try:
            raw = origin.reconstruct_single_file_bytes(packet)
        except Exception as exc:
            code = getattr(exc, "code", None)
            raise ContextTransportHold(
                code
                if isinstance(code, str)
                else "HOLD_CONTEXT_RECONSTRUCTION_FAILED"
            ) from exc
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise ContextTransportHold(
                "HOLD_CONTEXT_RECONSTRUCTED_JSON_INVALID"
            ) from exc
        if not isinstance(payload, dict):
            raise ContextTransportHold(
                "HOLD_CONTEXT_RECONSTRUCTED_OBJECT_REQUIRED"
            )
    else:
        raise ContextTransportHold("HOLD_CONTEXT_TRANSPORT_MODE_UNSUPPORTED")

    if len(raw) != transport.get("target_bytes"):
        raise ContextTransportHold("HOLD_CONTEXT_TARGET_SIZE_MISMATCH")
    if hashlib.sha256(raw).hexdigest() != transport.get("target_sha256"):
        raise ContextTransportHold("HOLD_CONTEXT_TARGET_HASH_MISMATCH")
    return dict(payload)


__all__ = [
    "ContextTransportHold",
    "SCHEMA",
    "build_transport",
    "canonical_json_bytes",
    "reconstruct_transport",
]
