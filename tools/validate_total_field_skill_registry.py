#!/usr/bin/env python3
"""Validate the bounded Total Field skill registrations without mutation."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "manifests/ollama_xiaoj_total_field_v0_1"
REGISTRY_PATH = PACK / "capability_registry.json"
INDEX_PATH = PACK / "founder_all_skills_8d_index.json"

EXPECTED = {
    "8d-adi-founder-partner": "READY_LOCAL",
    "8d-adi-state-field-intelligence": "READY_LOCAL",
    "w7tp-capability-assimilator": "READY_LOCAL",
    "w7tp_generative_transmission": "READY_LOCAL",
    "w7tp_router_wireguard_control": "READY_LOCAL",
    "deep-research": "NEEDS_CONNECTOR",
}
MERGED_ALIAS = "w7tp-internal-generative-transmission"
ALLOWED_STATUSES = {
    "READY_LOCAL",
    "READY_MCP",
    "NEEDS_CONNECTOR",
    "NEEDS_LOCAL_ADAPTER",
    "PLATFORM_INTERNAL_UNEXPORTABLE",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"TOP_LEVEL_NOT_OBJECT:{path.relative_to(ROOT)}")
    return value


def validate() -> dict[str, Any]:
    errors: list[str] = []
    registry = _load(REGISTRY_PATH)
    index = _load(INDEX_PATH)

    packets = index.get("skill_packets")
    if not isinstance(packets, list):
        packets = []
        errors.append("INDEX_SKILL_PACKETS_MISSING")
    packet_ids = [packet.get("skill_id") for packet in packets if isinstance(packet, dict)]
    if len(packet_ids) != len(set(packet_ids)):
        errors.append("DUPLICATE_INDEX_SKILL_ID")
    packet_by_id = {
        packet["skill_id"]: packet
        for packet in packets
        if isinstance(packet, dict) and isinstance(packet.get("skill_id"), str)
    }

    contracts = registry.get("skills")
    if not isinstance(contracts, list):
        contracts = []
        errors.append("FORMAL_SKILL_CONTRACTS_MISSING")
    contract_ids = [contract.get("id") for contract in contracts if isinstance(contract, dict)]
    if len(contract_ids) != len(set(contract_ids)):
        errors.append("DUPLICATE_FORMAL_SKILL_ID")
    contract_by_id = {
        contract["id"]: contract
        for contract in contracts
        if isinstance(contract, dict) and isinstance(contract.get("id"), str)
    }

    for skill_id, status in EXPECTED.items():
        packet = packet_by_id.get(skill_id)
        contract = contract_by_id.get(skill_id)
        if packet is None:
            errors.append(f"MISSING_INDEX_SKILL:{skill_id}")
            continue
        if packet.get("status") != status:
            errors.append(f"STATUS_MISMATCH:{skill_id}")
        if contract is None:
            errors.append(f"MISSING_FORMAL_CONTRACT:{skill_id}")
            continue
        source = contract.get("source")
        if not isinstance(source, str):
            errors.append(f"SOURCE_PATH_MISSING:{skill_id}")
        else:
            source_path = ROOT / source
            if not source_path.is_file():
                errors.append(f"SOURCE_FILE_MISSING:{skill_id}")
            elif contract.get("source_sha256") != _sha256(source_path):
                errors.append(f"SOURCE_HASH_MISMATCH:{skill_id}")
        if not contract.get("tool_binding"):
            errors.append(f"TOOL_BINDING_MISSING:{skill_id}")
        if not contract.get("failure_contract"):
            errors.append(f"FAILURE_CONTRACT_MISSING:{skill_id}")
        if not contract.get("reobservation_contract"):
            errors.append(f"REOBSERVATION_CONTRACT_MISSING:{skill_id}")

    if MERGED_ALIAS in packet_by_id or MERGED_ALIAS in contract_by_id:
        errors.append("PARALLEL_GENERATIVE_TRANSMISSION_ROUTE_CREATED")
    transmission = packet_by_id.get("w7tp_generative_transmission", {})
    if transmission.get("D2_STATE", {}).get("merged_skill_ids") != [MERGED_ALIAS]:
        errors.append("GENERATIVE_TRANSMISSION_MERGE_BINDING_MISSING")
    if not transmission.get("D4_EVIDENCE", {}).get("supporting_sources"):
        errors.append("GENERATIVE_TRANSMISSION_SUPPORTING_EVIDENCE_MISSING")

    assimilator_refs = packet_by_id.get("w7tp-capability-assimilator", {}).get(
        "D5_EXECUTION", {}
    ).get("tool_refs", [])
    if not assimilator_refs or not all(str(ref).startswith("linux:") for ref in assimilator_refs):
        errors.append("ASSIMILATOR_LINUX_ENTRYPOINT_MISSING")
    research_refs = packet_by_id.get("deep-research", {}).get("D5_EXECUTION", {}).get(
        "tool_refs", []
    )
    if research_refs != ["controlled_connector:deep_research_work"]:
        errors.append("DEEP_RESEARCH_CONNECTOR_BOUNDARY_MISMATCH")

    router_packet = packet_by_id.get("w7tp_router_wireguard_control", {})
    router_refs = router_packet.get("D5_EXECUTION", {}).get("tool_refs", [])
    if (
        len(router_refs) != 1
        or not str(router_refs[0]).startswith("linux:python3 ")
        or "router_total_field_adapter.py" not in str(router_refs[0])
    ):
        errors.append("ROUTER_TOTAL_FIELD_ADAPTER_BINDING_MISSING")
    router_contract = contract_by_id.get("w7tp_router_wireguard_control", {})
    if router_contract.get("skill_execution_state") != "READY_LOCAL_PLAN_ONLY_D8_REQUIRED_FOR_EFFECT":
        errors.append("ROUTER_SKILL_EFFECT_BOUNDARY_MISMATCH")
    if router_contract.get("side_effects") is not False:
        errors.append("ROUTER_SKILL_SIDE_EFFECT_ESCALATION")
    if router_contract.get("d6_mapping") != "NOT_APPLICABLE_NETWORK_TRANSPORT_ONLY":
        errors.append("ROUTER_NETWORK_MISLABELED_AS_D6")
    if "AUTHORIZE_EXACT_ROUTER_NETWORK_CHANGE" not in str(router_contract.get("d8_requirement")):
        errors.append("ROUTER_D8_REQUIREMENT_MISSING")

    state_field_contract = contract_by_id.get("8d-adi-state-field-intelligence", {})
    if state_field_contract.get("skill_execution_state") != "READY_LOCAL_READ_ONLY_WRITE_EFFECTS_REQUIRE_SEPARATE_AUTHORIZATION":
        errors.append("STATE_FIELD_SKILL_EXECUTION_BOUNDARY_MISMATCH")
    if state_field_contract.get("side_effects") is not False:
        errors.append("STATE_FIELD_SKILL_SIDE_EFFECT_ESCALATION")
    state_field_refs = packet_by_id.get("8d-adi-state-field-intelligence", {}).get(
        "D5_EXECUTION", {}
    ).get("tool_refs", [])
    if (
        len(state_field_refs) != 2
        or not all(str(ref).startswith("linux:python3 ") for ref in state_field_refs)
        or not any("state_field_inventory.py" in str(ref) for ref in state_field_refs)
        or not any("adi_map_router.py" in str(ref) for ref in state_field_refs)
    ):
        errors.append("STATE_FIELD_READ_ONLY_TOOL_BINDING_MISSING")
    if any("adi_state_archive.py" in str(ref) for ref in state_field_refs):
        errors.append("STATE_FIELD_WRITE_TOOL_ACTIVATED")

    founder_partner_refs = packet_by_id.get("8d-adi-founder-partner", {}).get(
        "D5_EXECUTION", {}
    ).get("tool_refs", [])
    if founder_partner_refs != [
        "local:tools.total_field_dynamic_context.build_dynamic_context",
        "local:tools.total_field_dynamic_context.build_total_field_progress_projection",
        "local:tools.total_field_dynamic_context.build_total_field_correction_contract",
    ]:
        errors.append("FOUNDER_PARTNER_SINGLE_CHAIN_BINDING_MISMATCH")
    founder_partner_contract = contract_by_id.get("8d-adi-founder-partner", {})
    if (
        founder_partner_contract.get("skill_execution_state")
        != "READY_LOCAL_READ_ONLY_ADVISORY_CANDIDATE"
    ):
        errors.append("FOUNDER_PARTNER_CANDIDATE_BOUNDARY_MISMATCH")
    if founder_partner_contract.get("side_effects") is not False:
        errors.append("FOUNDER_PARTNER_SIDE_EFFECT_ESCALATION")
    if (
        founder_partner_contract.get("d6_mapping")
        != "NOT_APPLICABLE_ADVISORY_CONTEXT_AND_PROGRESS_PROJECTION_ONLY"
    ):
        errors.append("FOUNDER_PARTNER_ADVISORY_MISLABELED_AS_D6")
    if founder_partner_contract.get("external_representation_authority") is not False:
        errors.append("FOUNDER_PARTNER_EXTERNAL_REPRESENTATION_ESCALATION")
    if founder_partner_contract.get("progress_persistence_authority") is not False:
        errors.append("FOUNDER_PARTNER_PROGRESS_PERSISTENCE_ESCALATION")
    if founder_partner_contract.get("node_projection_activated") is not False:
        errors.append("FOUNDER_PARTNER_NODE_PROJECTION_ACTIVATED")
    if (
        founder_partner_contract.get("skill_coverage_claim")
        != "CURRENT_INDEX_ONLY_WITH_TRUTHFUL_READINESS_STATE"
    ):
        errors.append("FOUNDER_PARTNER_SKILL_COVERAGE_OVERCLAIM")
    if (
        founder_partner_contract.get("invention_coverage_claim")
        != "INDEXED_EVIDENCE_ONLY_NOT_ALL_INVENTIONS_PROVEN"
    ):
        errors.append("FOUNDER_PARTNER_INVENTION_COVERAGE_OVERCLAIM")
    founder_partner_d8 = str(founder_partner_contract.get("d8_requirement"))
    if not all(
        boundary in founder_partner_d8
        for boundary in (
            "PROGRESS_PERSISTENCE",
            "ADI_WRITE",
            "EXTERNAL_REPRESENTATION",
            "NODE_PROJECTION",
            "DEPLOYMENT",
            "ACTIVATION",
        )
    ):
        errors.append("FOUNDER_PARTNER_D8_BOUNDARY_INCOMPLETE")

    status_counts = Counter(
        packet.get("status") for packet in packets if isinstance(packet, dict)
    )
    if set(status_counts) - ALLOWED_STATUSES:
        errors.append("UNKNOWN_SKILL_STATUS")
    if dict(sorted(status_counts.items())) != index.get("classification_counts"):
        errors.append("INDEX_CLASSIFICATION_COUNTS_MISMATCH")
    registry_index = registry.get("founder_all_skills_index", {})
    if registry_index.get("classification_counts") != index.get("classification_counts"):
        errors.append("REGISTRY_CLASSIFICATION_COUNTS_MISMATCH")
    if registry_index.get("skills_discovered") != len(packets):
        errors.append("REGISTRY_SKILL_COUNT_MISMATCH")

    governance = registry.get("skill_registration_governance", {})
    if governance.get("current_baseline") != "8DADI_W7TP_2_3":
        errors.append("CURRENT_BASELINE_NOT_2_3")
    if governance.get("merged_aliases", {}).get(MERGED_ALIAS) != "w7tp_generative_transmission":
        errors.append("GOVERNANCE_MERGE_ALIAS_MISSING")
    if "w7tp_router_wireguard_control" not in governance.get("registered_skill_ids", []):
        errors.append("ROUTER_SKILL_GOVERNANCE_REGISTRATION_MISSING")
    if "8d-adi-state-field-intelligence" not in governance.get("registered_skill_ids", []):
        errors.append("STATE_FIELD_SKILL_GOVERNANCE_REGISTRATION_MISSING")
    if "8d-adi-founder-partner" not in governance.get("registered_skill_ids", []):
        errors.append("FOUNDER_PARTNER_GOVERNANCE_REGISTRATION_MISSING")
    rules = governance.get("registration_rules", {})
    if not all(
        rules.get(name) is True
        for name in (
            "ready_requires_tool_binding",
            "connector_capability_cannot_claim_local_execution",
            "platform_internal_cannot_claim_local_execution",
            "skill_is_not_canonical_authority",
            "side_effect_requires_separate_exact_authorization",
            "reobservation_required_for_completion",
            "no_bulk_promotion",
        )
    ):
        errors.append("REGISTRATION_RULES_INCOMPLETE")
    if status_counts.get("PLATFORM_INTERNAL_UNEXPORTABLE") != 5:
        errors.append("PLATFORM_INTERNAL_BOUNDARY_CHANGED")

    state = "PASS_TOTAL_FIELD_SKILL_REGISTRY_VALIDATED" if not errors else "FAIL_TOTAL_FIELD_SKILL_REGISTRY_VALIDATION"
    return {
        "state": state,
        "errors": errors,
        "skills_discovered": len(packets),
        "formal_skill_contracts": len(contracts),
        "classification_counts": dict(sorted(status_counts.items())),
        "registered": EXPECTED,
        "merged_alias": {MERGED_ALIAS: "w7tp_generative_transmission"},
        "linux_execution": {
            "8d-adi-founder-partner": "READY_LOCAL_READ_ONLY_ADVISORY_CANDIDATE",
            "8d-adi-state-field-intelligence": "READY_LOCAL_READ_ONLY_WRITE_EFFECTS_REQUIRE_SEPARATE_AUTHORIZATION",
            "w7tp-capability-assimilator": "READY_LOCAL",
            "w7tp_generative_transmission": "ADAPTER_COMMAND_READY_CURRENT_EFFECT_REQUIRES_2_3_BINDING_AND_AUTHORIZATION",
            "w7tp_router_wireguard_control": "READY_LOCAL_PLAN_ONLY_D8_REQUIRED_FOR_EFFECT",
            "deep-research": "HOLD_CONNECTOR_REQUIRED",
        },
        "mutation_performed": False,
        "authority_granted": False,
    }


def main() -> int:
    try:
        result = validate()
    except Exception as exc:
        result = {
            "state": "FAIL_TOTAL_FIELD_SKILL_REGISTRY_VALIDATION",
            "errors": [f"VALIDATOR_EXCEPTION:{type(exc).__name__}:{exc}"],
            "mutation_performed": False,
            "authority_granted": False,
        }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["state"] == "PASS_TOTAL_FIELD_SKILL_REGISTRY_VALIDATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
