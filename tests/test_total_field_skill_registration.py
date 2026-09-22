from __future__ import annotations

import json
from pathlib import Path

from tools.total_field_dynamic_context import _load_capability_pack, _select_capability_route
from tools.validate_total_field_skill_registry import validate


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "manifests/ollama_xiaoj_total_field_v0_1"


def _load(name: str) -> dict:
    return json.loads((PACK / name).read_text(encoding="utf-8"))


def test_requested_skills_are_registered_with_truthful_execution_states():
    index = _load("founder_all_skills_8d_index.json")
    packets = {packet["skill_id"]: packet for packet in index["skill_packets"]}

    assert packets["8d-adi-founder-partner"]["status"] == "READY_LOCAL"
    assert packets["8d-adi-state-field-intelligence"]["status"] == "READY_LOCAL"
    assert packets["w7tp-capability-assimilator"]["status"] == "READY_LOCAL"
    assert packets["deep-research"]["status"] == "NEEDS_CONNECTOR"
    assert packets["w7tp_generative_transmission"]["status"] == "READY_LOCAL"
    assert packets["w7tp_router_wireguard_control"]["status"] == "READY_LOCAL"
    assert "w7tp-internal-generative-transmission" not in packets
    assert packets["w7tp_generative_transmission"]["D2_STATE"]["merged_skill_ids"] == [
        "w7tp-internal-generative-transmission"
    ]


def test_linux_entries_and_connector_boundary_are_explicit():
    index = _load("founder_all_skills_8d_index.json")
    packets = {packet["skill_id"]: packet for packet in index["skill_packets"]}
    assimilator_refs = packets["w7tp-capability-assimilator"]["D5_EXECUTION"]["tool_refs"]
    transmission_refs = packets["w7tp_generative_transmission"]["D5_EXECUTION"]["tool_refs"]
    router_refs = packets["w7tp_router_wireguard_control"]["D5_EXECUTION"]["tool_refs"]
    state_field_refs = packets["8d-adi-state-field-intelligence"]["D5_EXECUTION"]["tool_refs"]
    founder_partner_refs = packets["8d-adi-founder-partner"]["D5_EXECUTION"]["tool_refs"]

    assert founder_partner_refs == [
        "local:tools.total_field_dynamic_context.build_dynamic_context",
        "local:tools.total_field_dynamic_context.build_total_field_progress_projection",
        "local:tools.total_field_dynamic_context.build_total_field_correction_contract",
    ]
    assert all(ref.startswith("linux:") for ref in assimilator_refs)
    assert any("python3 -m w7tp_gt_mesh" in ref for ref in transmission_refs)
    assert router_refs == [
        "linux:python3 .skill-build/w7tp-router-wireguard-control/scripts/router_total_field_adapter.py --intent <REGISTERED_INTENT>"
    ]
    assert len(state_field_refs) == 2
    assert all(ref.startswith("linux:python3 ") for ref in state_field_refs)
    assert any("state_field_inventory.py" in ref for ref in state_field_refs)
    assert any("adi_map_router.py" in ref for ref in state_field_refs)
    assert not any("adi_state_archive.py" in ref for ref in state_field_refs)
    assert packets["deep-research"]["D5_EXECUTION"]["tool_refs"] == [
        "controlled_connector:deep_research_work"
    ]
    assert packets["deep-research"]["D2_STATE"]["runtime_claim"] is False


def test_founder_partner_route_is_unique_and_candidate_only():
    route = _select_capability_route(
        "小J總場代言，記住進度，我的發明，下一步建議",
        _load_capability_pack(ROOT),
        "founder",
    )

    assert route["skill_lookup"]["selected_skill"] == "8d-adi-founder-partner"
    assert route["skill_lookup"]["selected_status"] == "READY_LOCAL"
    assert route["skill_lookup"]["match_state"] == "UNIQUE_EXPLICIT_MATCH"
    assert route["total_field_gate"]["disposition"] == "CANDIDATE_ONLY"
    assert route["identity_projection"]["authority_verified"] is False
    assert route["total_field_gate"]["model_commit_allowed"] is False


def test_registration_governance_keeps_2_3_and_rejects_2_1_downgrade():
    registry = _load("capability_registry.json")
    governance = registry["skill_registration_governance"]
    contracts = {contract["id"]: contract for contract in registry["skills"]}

    assert governance["current_baseline"] == "8DADI_W7TP_2_3"
    govern_source = next(
        item
        for item in governance["attached_source_packages"]
        if item["name"] == "govern-total-field-skills (2).zip"
    )
    assert govern_source["rejected_binding"] == (
        "V2_1_CANONICAL_LOCK_CANNOT_DOWNGRADE_CURRENT_2_3_BASELINE"
    )
    assert contracts["w7tp_generative_transmission"]["compatibility_boundary"].endswith(
        "cannot redefine the current 2.3 contract."
    )
    router = contracts["w7tp_router_wireguard_control"]
    assert router["skill_execution_state"] == "READY_LOCAL_PLAN_ONLY_D8_REQUIRED_FOR_EFFECT"
    assert router["side_effects"] is False
    assert router["d6_mapping"] == "NOT_APPLICABLE_NETWORK_TRANSPORT_ONLY"
    assert "AUTHORIZE_EXACT_ROUTER_NETWORK_CHANGE" in router["d8_requirement"]
    state_field = contracts["8d-adi-state-field-intelligence"]
    assert state_field["skill_execution_state"] == (
        "READY_LOCAL_READ_ONLY_WRITE_EFFECTS_REQUIRE_SEPARATE_AUTHORIZATION"
    )
    assert state_field["side_effects"] is False
    assert "CANONICAL_MUTATION_REQUIRE_SEPARATE_EXACT_AUTHORIZATION" in state_field[
        "d8_requirement"
    ]
    founder_partner = contracts["8d-adi-founder-partner"]
    assert founder_partner["skill_execution_state"] == (
        "READY_LOCAL_READ_ONLY_ADVISORY_CANDIDATE"
    )
    assert founder_partner["side_effects"] is False
    assert founder_partner["d6_mapping"] == (
        "NOT_APPLICABLE_ADVISORY_CONTEXT_AND_PROGRESS_PROJECTION_ONLY"
    )
    assert founder_partner["external_representation_authority"] is False
    assert founder_partner["progress_persistence_authority"] is False
    assert founder_partner["node_projection_activated"] is False
    assert founder_partner["skill_coverage_claim"] == (
        "CURRENT_INDEX_ONLY_WITH_TRUTHFUL_READINESS_STATE"
    )
    assert founder_partner["invention_coverage_claim"] == (
        "INDEXED_EVIDENCE_ONLY_NOT_ALL_INVENTIONS_PROVEN"
    )
    assert "8d-adi-founder-partner" in governance["registered_skill_ids"]


def test_registry_validator_passes_and_no_bulk_promotion_occurs():
    result = validate()

    assert result["state"] == "PASS_TOTAL_FIELD_SKILL_REGISTRY_VALIDATED"
    assert result["skills_discovered"] == 105
    assert result["classification_counts"] == {
        "NEEDS_CONNECTOR": 39,
        "NEEDS_LOCAL_ADAPTER": 47,
        "PLATFORM_INTERNAL_UNEXPORTABLE": 5,
        "READY_LOCAL": 12,
        "READY_MCP": 2,
    }
