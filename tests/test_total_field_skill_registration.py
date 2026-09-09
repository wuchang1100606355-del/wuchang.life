from __future__ import annotations

import json
from pathlib import Path

from tools.validate_total_field_skill_registry import validate


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "manifests/ollama_xiaoj_total_field_v0_1"


def _load(name: str) -> dict:
    return json.loads((PACK / name).read_text(encoding="utf-8"))


def test_three_requested_skills_are_registered_with_truthful_execution_states():
    index = _load("founder_all_skills_8d_index.json")
    packets = {packet["skill_id"]: packet for packet in index["skill_packets"]}

    assert packets["w7tp-capability-assimilator"]["status"] == "READY_LOCAL"
    assert packets["deep-research"]["status"] == "NEEDS_CONNECTOR"
    assert packets["w7tp_generative_transmission"]["status"] == "READY_LOCAL"
    assert "w7tp-internal-generative-transmission" not in packets
    assert packets["w7tp_generative_transmission"]["D2_STATE"]["merged_skill_ids"] == [
        "w7tp-internal-generative-transmission"
    ]


def test_linux_entries_and_connector_boundary_are_explicit():
    index = _load("founder_all_skills_8d_index.json")
    packets = {packet["skill_id"]: packet for packet in index["skill_packets"]}
    assimilator_refs = packets["w7tp-capability-assimilator"]["D5_EXECUTION"]["tool_refs"]
    transmission_refs = packets["w7tp_generative_transmission"]["D5_EXECUTION"]["tool_refs"]

    assert all(ref.startswith("linux:") for ref in assimilator_refs)
    assert any("python3 -m w7tp_gt_mesh" in ref for ref in transmission_refs)
    assert packets["deep-research"]["D5_EXECUTION"]["tool_refs"] == [
        "controlled_connector:deep_research_work"
    ]
    assert packets["deep-research"]["D2_STATE"]["runtime_claim"] is False


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


def test_registry_validator_passes_and_no_bulk_promotion_occurs():
    result = validate()

    assert result["state"] == "PASS_TOTAL_FIELD_SKILL_REGISTRY_VALIDATED"
    assert result["skills_discovered"] == 103
    assert result["classification_counts"] == {
        "NEEDS_CONNECTOR": 39,
        "NEEDS_LOCAL_ADAPTER": 47,
        "PLATFORM_INTERNAL_UNEXPORTABLE": 5,
        "READY_LOCAL": 10,
        "READY_MCP": 2,
    }
