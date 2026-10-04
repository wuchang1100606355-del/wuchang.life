"""Candidate Receiver Capability Contract V1 for W7TP Origin State reconstruction.

This module turns observed receiver prerequisites into a machine-verifiable,
fail-closed contract. It does not promote canonical authority, change active
pointers, deploy services, or redefine 8D ADI.
"""

from __future__ import annotations

import copy
import hashlib
import json
import platform
import sqlite3
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_SCHEMA = "w7tp-receiver-capability-contract/1.0-candidate"
CONTRACT_TYPE = "RECEIVER_CAPABILITY_CONTRACT"
CONTRACT_VERSION = "1.0-candidate"


class ReceiverCapabilityHold(RuntimeError):
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


def _contract_hash_basis(contract: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(contract))
    copied.pop("contract_sha256", None)
    return copied


def contract_sha256(contract: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        canonical_json_bytes(_contract_hash_basis(contract))
    ).hexdigest()


def build_contract_from_cross_node_evidence(
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    if evidence.get("state") != (
        "PASS_CROSS_NODE_EXACT_RECONSTRUCTION_"
        "WITH_EXPLICIT_RECEIVER_RUNTIME_BOOTSTRAP"
    ):
        raise ReceiverCapabilityHold(
            "HOLD_RECEIVER_EVIDENCE_STATE_NOT_ACCEPTED"
        )

    receiver = evidence.get("receiver")
    result = evidence.get("result")
    source = evidence.get("source")
    failed = evidence.get("failed_attempt_and_correction")
    if not all(isinstance(v, Mapping) for v in (receiver, result, source, failed)):
        raise ReceiverCapabilityHold("HOLD_RECEIVER_EVIDENCE_SHAPE_INVALID")

    runtime = receiver.get("successful_runtime")
    initial = failed.get("initial_receiver_runtime")
    if not isinstance(runtime, Mapping) or not isinstance(initial, Mapping):
        raise ReceiverCapabilityHold("HOLD_RECEIVER_RUNTIME_EVIDENCE_MISSING")

    contract: dict[str, Any] = {
        "schema_version": CONTRACT_SCHEMA,
        "contract_type": CONTRACT_TYPE,
        "contract_version": CONTRACT_VERSION,
        "contract_ref": (
            "receiver-capability:w7tp-origin-state:"
            + str(evidence.get("experiment_id"))
        ),
        "lifecycle": "CANDIDATE",
        "authority": {
            "canonical": False,
            "formal_authority": False,
            "global_canonical_promotion": False,
        },
        "receiver_requirement": {
            "compatibility_mode": "EXACT_RUNTIME_AND_PRIMITIVE_BINDING",
            "runtime": {
                "python_version": runtime.get("python"),
                "sqlite_version": runtime.get("sqlite"),
            },
            "primitive_binding": {
                "rule_ref": result.get("rule_ref"),
                "implementation_sha256": result.get("rule_impl_sha256"),
                "minimum_packet_implementation_sha256": result.get(
                    "minimum_packet_impl_sha256"
                ),
                "registry_sha256": result.get("registry_sha256"),
            },
        },
        "materialization_contract": {
            "equivalence_level": "BYTE_EXACT",
            "verification_method": (
                "FINAL_MANIFEST_SHA256_AND_TOTAL_BYTES_AND_FILE_COUNT"
            ),
            "expected_target_manifest_sha256": source.get(
                "target_manifest_sha256"
            ),
            "expected_target_bytes": source.get("target_bytes"),
            "expected_target_files": source.get("target_files"),
            "deterministic_runtime_fields": [
                "runtime.python_version",
                "runtime.sqlite_version",
                "primitive_binding.implementation_sha256",
                "primitive_binding.minimum_packet_implementation_sha256",
                "primitive_binding.registry_sha256",
            ],
            "fail_closed_on_mismatch": True,
        },
        "historical_counterexample": {
            "python_version": initial.get("python"),
            "sqlite_version": initial.get("sqlite"),
            "observed_state": initial.get("state"),
            "logical_rows_equal": (
                failed.get("diagnosis", {}).get(
                    "logical_rows_sha256_source"
                )
                == failed.get("diagnosis", {}).get(
                    "logical_rows_sha256_receiver"
                )
            ),
        },
        "evidence_refs": list(
            evidence.get(
                "evidence_refs",
                [
                    (
                        "evidence/total_field/"
                        "origin_state_minimum_us_20261003T0632Z/"
                        "FINAL_CROSS_NODE_EVIDENCE.json"
                    ),
                    (
                        "evidence/total_field/"
                        "origin_state_minimum_us_20261003T0632Z/"
                        "FINAL_REMOTE_RECEIPT.json"
                    ),
                    (
                        "evidence/total_field/"
                        "origin_state_minimum_us_20261003T0632Z/"
                        "LOCAL_SQLITE_LOGICAL.json"
                    ),
                ],
            )
        ),
        "contract_sha256": "",
    }
    contract["contract_sha256"] = contract_sha256(contract)
    validate_contract(contract)
    return contract


def validate_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(contract, Mapping):
        raise ReceiverCapabilityHold("HOLD_RECEIVER_CONTRACT_INVALID")
    if contract.get("schema_version") != CONTRACT_SCHEMA:
        raise ReceiverCapabilityHold("HOLD_RECEIVER_CONTRACT_SCHEMA_MISMATCH")
    if contract.get("contract_type") != CONTRACT_TYPE:
        raise ReceiverCapabilityHold("HOLD_RECEIVER_CONTRACT_TYPE_MISMATCH")
    if contract.get("lifecycle") != "CANDIDATE":
        raise ReceiverCapabilityHold("HOLD_RECEIVER_CONTRACT_LIFECYCLE_INVALID")
    authority = contract.get("authority")
    if (
        not isinstance(authority, Mapping)
        or authority.get("canonical") is not False
        or authority.get("formal_authority") is not False
        or authority.get("global_canonical_promotion") is not False
    ):
        raise ReceiverCapabilityHold("HOLD_RECEIVER_CONTRACT_AUTHORITY_ESCALATION")
    if contract.get("contract_sha256") != contract_sha256(contract):
        raise ReceiverCapabilityHold("HOLD_RECEIVER_CONTRACT_HASH_MISMATCH")

    requirement = contract.get("receiver_requirement")
    materialization = contract.get("materialization_contract")
    if not isinstance(requirement, Mapping) or not isinstance(materialization, Mapping):
        raise ReceiverCapabilityHold("HOLD_RECEIVER_CONTRACT_REQUIREMENTS_MISSING")
    if requirement.get("compatibility_mode") not in {
        "EXACT_RUNTIME_AND_PRIMITIVE_BINDING",
        "PROTOCOL_DESCRIPTOR_AND_EXECUTOR_BINDING",
    }:
        raise ReceiverCapabilityHold("HOLD_RECEIVER_COMPATIBILITY_MODE_INVALID")
    if materialization.get("equivalence_level") != "BYTE_EXACT":
        raise ReceiverCapabilityHold("HOLD_MATERIALIZATION_EQUIVALENCE_INVALID")
    if materialization.get("fail_closed_on_mismatch") is not True:
        raise ReceiverCapabilityHold("HOLD_MATERIALIZATION_FAIL_CLOSED_REQUIRED")
    return dict(contract)


def observe_local_receiver(
    *,
    node_ref: str,
    root: Path = ROOT,
) -> dict[str, Any]:
    primitive = (
        root
        / "products/eight_dimensional_generative_memory/"
        "w7tp_origin_cell_generative_v2.py"
    )
    minimum = (
        root
        / "products/eight_dimensional_generative_memory/"
        "w7tp_origin_state_minimum_packet_v1.py"
    )
    registry = (
        root / "configs/total_field/w7tp_local_origin_state_rule_registry_v1.json"
    )
    return {
        "node_ref": node_ref,
        "runtime": {
            "python_version": sys.version.split()[0],
            "sqlite_version": sqlite3.sqlite_version,
            "platform": platform.platform(),
        },
        "primitive_binding": {
            "implementation_sha256": sha256_file(primitive),
            "minimum_packet_implementation_sha256": sha256_file(minimum),
            "registry_sha256": sha256_file(registry),
        },
    }


def match_receiver_capability(
    contract: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> dict[str, Any]:
    validate_contract(contract)
    requirement = contract["receiver_requirement"]
    required_runtime = requirement["runtime"]
    required_primitive = requirement["primitive_binding"]
    observed_runtime = observed.get("runtime")
    observed_primitive = observed.get("primitive_binding")
    if not isinstance(observed_runtime, Mapping):
        raise ReceiverCapabilityHold("HOLD_RECEIVER_RUNTIME_OBSERVATION_MISSING")
    if not isinstance(observed_primitive, Mapping):
        raise ReceiverCapabilityHold("HOLD_RECEIVER_PRIMITIVE_OBSERVATION_MISSING")

    checks = (
        ("python_version", required_runtime, observed_runtime,
         "HOLD_RECEIVER_PYTHON_VERSION_MISMATCH"),
        ("sqlite_version", required_runtime, observed_runtime,
         "HOLD_RECEIVER_SQLITE_VERSION_MISMATCH"),
        ("implementation_sha256", required_primitive, observed_primitive,
         "HOLD_RECEIVER_PRIMITIVE_HASH_MISMATCH"),
        ("minimum_packet_implementation_sha256",
         required_primitive, observed_primitive,
         "HOLD_RECEIVER_MINIMUM_PACKET_HASH_MISMATCH"),
        ("registry_sha256", required_primitive, observed_primitive,
         "HOLD_RECEIVER_REGISTRY_HASH_MISMATCH"),
    )
    for key, expected, actual, code in checks:
        if expected.get(key) != actual.get(key):
            raise ReceiverCapabilityHold(code)

    return {
        "state": "PASS_RECEIVER_CAPABILITY_MATCH",
        "contract_ref": contract["contract_ref"],
        "contract_sha256": contract["contract_sha256"],
        "node_ref": observed.get("node_ref"),
        "equivalence_level": contract["materialization_contract"][
            "equivalence_level"
        ],
    }


def verify_materialization_receipt(
    contract: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    validate_contract(contract)
    expected = contract["materialization_contract"]
    checks = (
        ("target_manifest_sha256", "expected_target_manifest_sha256",
         "HOLD_MATERIALIZATION_MANIFEST_MISMATCH"),
        ("target_bytes", "expected_target_bytes",
         "HOLD_MATERIALIZATION_SIZE_MISMATCH"),
        ("target_files", "expected_target_files",
         "HOLD_MATERIALIZATION_FILE_COUNT_MISMATCH"),
    )
    for receipt_key, contract_key, code in checks:
        if receipt.get(receipt_key) != expected.get(contract_key):
            raise ReceiverCapabilityHold(code)
    return {
        "state": "PASS_MATERIALIZATION_CONTRACT_VERIFIED",
        "contract_ref": contract["contract_ref"],
        "contract_sha256": contract["contract_sha256"],
    }


def build_universal_executor_contract(
    *,
    executor_contract: str,
    implementation_sha256: str,
    protocol_descriptor_sha256: str,
    material_base_contracts: list[Mapping[str, Any]],
    max_reconstructed_bytes: int,
) -> dict[str, Any]:
    if not all(
        isinstance(value, str) and value
        for value in (
            executor_contract,
            implementation_sha256,
            protocol_descriptor_sha256,
        )
    ):
        raise ReceiverCapabilityHold(
            "HOLD_UNIVERSAL_EXECUTOR_CONTRACT_INPUT_INVALID"
        )
    if not isinstance(material_base_contracts, list) or not material_base_contracts:
        raise ReceiverCapabilityHold(
            "HOLD_UNIVERSAL_MATERIAL_BASE_CONTRACTS_INVALID"
        )
    contract: dict[str, Any] = {
        "schema_version": CONTRACT_SCHEMA,
        "contract_type": CONTRACT_TYPE,
        "contract_version": CONTRACT_VERSION,
        "contract_ref": (
            "receiver-capability:universal-origin-cell:"
            + protocol_descriptor_sha256[:16]
        ),
        "lifecycle": "CANDIDATE",
        "authority": {
            "canonical": False,
            "formal_authority": False,
            "global_canonical_promotion": False,
        },
        "receiver_requirement": {
            "compatibility_mode": (
                "PROTOCOL_DESCRIPTOR_AND_EXECUTOR_BINDING"
            ),
            "runtime": {},
            "primitive_binding": {
                "executor_contract": executor_contract,
                "implementation_sha256": implementation_sha256,
                "protocol_descriptor_sha256": protocol_descriptor_sha256,
                "material_base_contracts": [
                    dict(item) for item in material_base_contracts
                ],
                "max_reconstructed_bytes": max_reconstructed_bytes,
            },
        },
        "materialization_contract": {
            "equivalence_level": "BYTE_EXACT",
            "verification_method": "PER_FILE_SHA256_AND_SIZE",
            "fail_closed_on_mismatch": True,
        },
        "evidence_refs": [],
        "contract_sha256": "",
    }
    contract["contract_sha256"] = contract_sha256(contract)
    validate_contract(contract)
    return contract


def match_universal_executor_capability(
    contract: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> dict[str, Any]:
    validate_contract(contract)
    requirement = contract["receiver_requirement"]
    if requirement.get("compatibility_mode") != (
        "PROTOCOL_DESCRIPTOR_AND_EXECUTOR_BINDING"
    ):
        raise ReceiverCapabilityHold(
            "HOLD_UNIVERSAL_EXECUTOR_COMPATIBILITY_MODE_INVALID"
        )
    required = requirement["primitive_binding"]
    checks = (
        (
            "executor_contract",
            "HOLD_UNIVERSAL_EXECUTOR_CONTRACT_MISMATCH",
        ),
        (
            "implementation_sha256",
            "HOLD_UNIVERSAL_EXECUTOR_HASH_MISMATCH",
        ),
        (
            "protocol_descriptor_sha256",
            "HOLD_UNIVERSAL_PROTOCOL_DESCRIPTOR_MISMATCH",
        ),
        (
            "max_reconstructed_bytes",
            "HOLD_UNIVERSAL_RECONSTRUCTION_LIMIT_MISMATCH",
        ),
    )
    for key, code in checks:
        if observed.get(key) != required.get(key):
            raise ReceiverCapabilityHold(code)
    if observed.get("material_base_contracts") != required.get(
        "material_base_contracts"
    ):
        raise ReceiverCapabilityHold(
            "HOLD_UNIVERSAL_MATERIAL_BASE_CONTRACT_MISMATCH"
        )
    return {
        "state": "PASS_UNIVERSAL_EXECUTOR_CAPABILITY_MATCH",
        "contract_ref": contract["contract_ref"],
        "contract_sha256": contract["contract_sha256"],
        "equivalence_level": "BYTE_EXACT",
    }


def build_universal_receiver_bound_envelope(
    packet: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    validate_contract(contract)
    requirement = contract["receiver_requirement"]
    if requirement.get("compatibility_mode") != (
        "PROTOCOL_DESCRIPTOR_AND_EXECUTOR_BINDING"
    ):
        raise ReceiverCapabilityHold(
            "HOLD_UNIVERSAL_EXECUTOR_COMPATIBILITY_MODE_INVALID"
        )
    required = requirement["primitive_binding"]
    if packet.get("executor_contract") != required.get("executor_contract"):
        raise ReceiverCapabilityHold(
            "HOLD_UNIVERSAL_PACKET_EXECUTOR_CONTRACT_MISMATCH"
        )
    if packet.get("protocol_descriptor_sha256") != required.get(
        "protocol_descriptor_sha256"
    ):
        raise ReceiverCapabilityHold(
            "HOLD_UNIVERSAL_PACKET_PROTOCOL_DESCRIPTOR_MISMATCH"
        )
    packet_bases = packet.get("material_base_contracts")
    required_bases = required.get("material_base_contracts")
    if not isinstance(packet_bases, list) or not isinstance(
        required_bases, list
    ):
        raise ReceiverCapabilityHold(
            "HOLD_UNIVERSAL_PACKET_MATERIAL_BASES_INVALID"
        )
    required_by_id = {
        item.get("base_id"): dict(item)
        for item in required_bases
        if isinstance(item, Mapping)
    }
    for item in packet_bases:
        if (
            not isinstance(item, Mapping)
            or required_by_id.get(item.get("base_id")) != dict(item)
        ):
            raise ReceiverCapabilityHold(
                "HOLD_UNIVERSAL_PACKET_MATERIAL_BASE_MISMATCH"
            )
    field = packet.get("joint_state_field")
    d8 = field.get("D8") if isinstance(field, Mapping) else None
    if (
        not isinstance(d8, Mapping)
        or d8.get("model_authority") is not False
        or d8.get("canonical_runtime_effect") is not False
    ):
        raise ReceiverCapabilityHold(
            "HOLD_UNIVERSAL_PACKET_AUTHORITY_ESCALATION"
        )
    packet_hash = packet.get("packet_sha256")
    if not isinstance(packet_hash, str) or not packet_hash:
        raise ReceiverCapabilityHold(
            "HOLD_UNIVERSAL_PACKET_HASH_MISSING"
        )
    envelope: dict[str, Any] = {
        "schema_version": (
            "w7tp-origin-cell-universal-receiver-bound-envelope/"
            "1.0-candidate"
        ),
        "packet_sha256": packet_hash,
        "receiver_contract_ref": contract["contract_ref"],
        "receiver_contract_sha256": contract["contract_sha256"],
        "executor_contract": required["executor_contract"],
        "protocol_descriptor_sha256": required[
            "protocol_descriptor_sha256"
        ],
        "equivalence_level": "BYTE_EXACT",
        "authority": {
            "canonical": False,
            "formal_authority": False,
            "execution_authorized": False,
        },
        "envelope_sha256": "",
    }
    basis = copy.deepcopy(envelope)
    basis.pop("envelope_sha256")
    envelope["envelope_sha256"] = hashlib.sha256(
        canonical_json_bytes(basis)
    ).hexdigest()
    return envelope


def build_receiver_bound_envelope(
    packet: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    validate_contract(contract)
    if not isinstance(packet, Mapping):
        raise ReceiverCapabilityHold("HOLD_RECEIVER_BOUND_PACKET_INVALID")

    binding = packet.get("rule_binding")
    verification = packet.get("verification")
    required = contract["receiver_requirement"]["primitive_binding"]
    materialization = contract["materialization_contract"]
    if not isinstance(binding, Mapping) or not isinstance(verification, Mapping):
        raise ReceiverCapabilityHold(
            "HOLD_RECEIVER_BOUND_PACKET_CONTRACT_MISSING"
        )
    if binding.get("rule_ref") != required.get("rule_ref"):
        raise ReceiverCapabilityHold(
            "HOLD_RECEIVER_BOUND_RULE_REF_MISMATCH"
        )
    if binding.get("implementation_sha256") != required.get(
        "implementation_sha256"
    ):
        raise ReceiverCapabilityHold(
            "HOLD_RECEIVER_BOUND_PRIMITIVE_HASH_MISMATCH"
        )
    if verification.get("expected_target_manifest_sha256") != (
        materialization.get("expected_target_manifest_sha256")
    ):
        raise ReceiverCapabilityHold(
            "HOLD_RECEIVER_BOUND_MANIFEST_CONTRACT_MISMATCH"
        )
    if verification.get("expected_target_bytes") != materialization.get(
        "expected_target_bytes"
    ):
        raise ReceiverCapabilityHold(
            "HOLD_RECEIVER_BOUND_SIZE_CONTRACT_MISMATCH"
        )

    envelope: dict[str, Any] = {
        "schema_version": (
            "w7tp-origin-state-receiver-bound-envelope/1.0-candidate"
        ),
        "packet_ref": packet.get("packet_ref"),
        "packet_sha256": packet.get("packet_sha256"),
        "receiver_contract_ref": contract["contract_ref"],
        "receiver_contract_sha256": contract["contract_sha256"],
        "equivalence_level": materialization["equivalence_level"],
        "expected_target_manifest_sha256": verification[
            "expected_target_manifest_sha256"
        ],
        "expected_target_bytes": verification["expected_target_bytes"],
        "authority": {
            "canonical": False,
            "formal_authority": False,
            "execution_authorized": False,
        },
        "envelope_sha256": "",
    }
    basis = copy.deepcopy(envelope)
    basis.pop("envelope_sha256")
    envelope["envelope_sha256"] = hashlib.sha256(
        canonical_json_bytes(basis)
    ).hexdigest()
    return envelope


__all__ = [
    "CONTRACT_SCHEMA",
    "ReceiverCapabilityHold",
    "build_contract_from_cross_node_evidence",
    "build_receiver_bound_envelope",
    "build_universal_executor_contract",
    "build_universal_receiver_bound_envelope",
    "contract_sha256",
    "match_receiver_capability",
    "match_universal_executor_capability",
    "observe_local_receiver",
    "validate_contract",
    "verify_materialization_receipt",
]
