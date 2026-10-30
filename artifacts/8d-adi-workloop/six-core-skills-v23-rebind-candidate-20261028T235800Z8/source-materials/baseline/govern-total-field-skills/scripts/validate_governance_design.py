#!/usr/bin/env python3
"""Red-team the Total Field skill-governance design and report convergence."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"MODULE_LOAD_FAILED:{name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(
    checks: list[dict[str, Any]],
    name: str,
    passed: bool,
    evidence: str,
) -> None:
    checks.append({
        "check": name,
        "pass": passed,
        "evidence": evidence,
    })


def main() -> int:
    checks: list[dict[str, Any]] = []
    schema_path = ROOT / "references" / "total_field_skill_manifest_v1.schema.json"
    catalog_path = ROOT / "references" / "core_skill_family_catalog_v1.json"
    manifest_path = ROOT / "total-field-skill-manifest.json"
    validator_path = ROOT / "scripts" / "validate_skill_manifest.py"
    inventory_path = ROOT / "scripts" / "inventory_skill_definitions.py"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validator = load_module("total_field_manifest_validator", validator_path)
    inventory = load_module("total_field_skill_inventory", inventory_path)
    definition_contract = (
        ROOT / "references" / "skill-definition-contract.md"
    ).read_text(encoding="utf-8")
    lifecycle_contract = (
        ROOT / "references" / "lifecycle-and-total-field.md"
    ).read_text(encoding="utf-8")
    technology_identity_contract = (
        ROOT / "references" / "technology-identity-manifest-contract.md"
    ).read_text(encoding="utf-8")

    check(
        checks,
        "schema_identity",
        schema.get("$id") == "w7tp://schemas/total-field-skill-manifest-v1",
        str(schema_path),
    )
    check(
        checks,
        "family_catalog_complete",
        len(catalog.get("families", [])) == 20
        and len({item["code"] for item in catalog["families"]}) == 20,
        str(catalog_path),
    )
    check(
        checks,
        "eight_fields_locked",
        catalog.get("eight_state_fields") == validator.EXPECTED_FIELDS,
        "D1 intent through D8 envelope authority",
    )
    check(
        checks,
        "technology_identity_schema_present",
        "technology_identity_contract" in schema.get("properties", {}),
        "references/total_field_skill_manifest_v1.schema.json",
    )
    check(
        checks,
        "technology_identity_reference_complete",
        all(
            term in technology_identity_contract
            for term in (
                "MECHANISM",
                "CAUSAL_PATH",
                "DEPENDENCIES",
                "ELIMINATED_OPERATIONS",
                "COST_TOPOLOGY",
                "CARRIER_RECONSTRUCTION_VERIFICATION",
            )
        ),
        "references/technology-identity-manifest-contract.md",
    )
    for lock in (
        "Intent Communication / State-Field Packet Communication",
        "packet-level irreversible local decision index",
        "system-level lineage/logical-time/state-transition/namespace/evidence spatial-temporal index network",
        "5D_INTEGER_METRIC",
        "floating-point data index",
        "deterministic replay evidence",
        "H64-TD",
        "current 10 claims",
        "V04’s 21-claim draft",
        "append-only",
        "Never silently overwrite",
        "effect equivalence is not technical equivalence",
        "ELIMINATED_OPERATIONS",
        "EFFECT_ONLY_EQUIVALENT",
        "EV5_REPRODUCIBLE_CAUSAL_EVIDENCE",
        "weighted identity scores",
    ):
        check(
            checks,
            f"v2_1_lock:{lock}",
            lock in definition_contract,
            "references/skill-definition-contract.md",
        )
    check(
        checks,
        "lifecycle_append_only",
        "append-only" in lifecycle_contract
        and "silently overwrite" in lifecycle_contract,
        "references/lifecycle-and-total-field.md",
    )

    valid = validator.validate_document(
        manifest,
        manifest_path=manifest_path,
        schema_path=schema_path,
    )
    check(
        checks,
        "governance_manifest_valid",
        valid["state"] == "PASS_SKILL_MANIFEST_VALID",
        ",".join(valid["errors"]) or "no errors",
    )

    inv = inventory.inventory(ROOT.parent)
    current = [item for item in inv["skills"] if item.get("name") == "govern-total-field-skills"]
    check(
        checks,
        "inventory_finds_governance_skill",
        len(current) == 1 and current[0]["definition_status"] == "MANIFEST_PRESENT",
        current[0]["path"] if current else "not found",
    )

    adversarial_cases = []

    authority_injection = copy.deepcopy(manifest)
    authority_injection["authority_boundary"]["allowed_outputs"].append("ALLOW")
    adversarial_cases.append(("authority_injection_blocked", authority_injection))

    seat_bypass = copy.deepcopy(manifest)
    seat_bypass["identity_and_seat"]["active_seat_required"] = False
    adversarial_cases.append(("seat_bypass_blocked", seat_bypass))

    cross_member = copy.deepcopy(manifest)
    cross_member["identity_and_seat"]["cross_member_plaintext_allowed"] = True
    adversarial_cases.append(("cross_member_plaintext_blocked", cross_member))

    d1_drift = copy.deepcopy(manifest)
    d1_drift["d1_d8_projection"]["D1"]["name"] = "STATE"
    adversarial_cases.append(("d1_identity_or_state_drift_blocked", d1_drift))

    red_team_waiver = copy.deepcopy(manifest)
    red_team_waiver["red_team_contract"]["stages"].remove("RED_TEAM_PRE_ACTIVATION")
    adversarial_cases.append(("red_team_waiver_blocked", red_team_waiver))

    fake_w7tp = copy.deepcopy(manifest)
    fake_w7tp["w7tp_contract"].update({
        "claimed": True,
        "canonical_ref": None,
        "protocol_bearing_packet": False,
        "reconstruction_conditions": False,
        "packet_carried_verification": False,
        "acceptance_mode": "NOT_APPLICABLE",
    })
    adversarial_cases.append(("fake_w7tp_claim_blocked", fake_w7tp))

    hidden_e5 = copy.deepcopy(manifest)
    hidden_e5["classification"]["maximum_effect_class"] = "E5"
    hidden_e5["authority_boundary"]["human_final_effect_classes"] = ["E4"]
    adversarial_cases.append(("e5_without_human_final_blocked", hidden_e5))

    protected_context = copy.deepcopy(manifest)
    protected_context["information_context"]["raw_protected_context_allowed"] = True
    adversarial_cases.append(("raw_protected_context_blocked", protected_context))

    legacy_canonical = copy.deepcopy(manifest)
    legacy_canonical["evidence_and_hashes"]["canonical_refs"].append(
        "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2"
    )
    adversarial_cases.append(("legacy_canonical_v2_blocked", legacy_canonical))

    float_replay_omission = copy.deepcopy(manifest)
    float_replay_omission["verification_contract"]["runtime_checks"] = [
        item
        for item in float_replay_omission["verification_contract"]["runtime_checks"]
        if "FLOAT" not in item
    ]
    adversarial_cases.append(
        ("floating_point_replay_omission_blocked", float_replay_omission)
    )

    technology_axes_omission = copy.deepcopy(manifest)
    technology_axes_omission["technology_identity_contract"]["axes"].remove(
        "COST_TOPOLOGY"
    )
    adversarial_cases.append(
        ("technology_identity_axis_omission_blocked", technology_axes_omission)
    )

    technology_weighted_score = copy.deepcopy(manifest)
    technology_weighted_score["technology_identity_contract"][
        "weighted_score_forbidden"
    ] = False
    adversarial_cases.append(
        ("technology_identity_weighted_score_blocked", technology_weighted_score)
    )

    technology_effect_equivalence = copy.deepcopy(manifest)
    technology_effect_equivalence["technology_identity_contract"][
        "effect_equivalence_not_technical_equivalence"
    ] = False
    adversarial_cases.append(
        ("effect_equivalence_shortcut_blocked", technology_effect_equivalence)
    )

    technology_effect_class_collision = copy.deepcopy(manifest)
    technology_effect_class_collision["technology_identity_contract"][
        "evidence_scale"
    ] = ["E0", "E1", "E2", "E3", "E4", "E5"]
    adversarial_cases.append(
        ("effect_class_evidence_collision_blocked", technology_effect_class_collision)
    )

    technology_patent_inference = copy.deepcopy(manifest)
    technology_patent_inference["technology_identity_contract"][
        "patentability_inference_forbidden"
    ] = False
    adversarial_cases.append(
        ("technology_identity_patent_inference_blocked", technology_patent_inference)
    )

    for name, candidate in adversarial_cases:
        outcome = validator.validate_document(
            candidate,
            manifest_path=None,
            schema_path=schema_path,
        )
        check(
            checks,
            name,
            outcome["state"] == "HOLD_SKILL_MANIFEST_INVALID",
            ",".join(outcome["errors"]) or "unexpected pass",
        )

    failed = [item for item in checks if not item["pass"]]
    result = {
        "state": (
            "PASS_TOTAL_FIELD_SKILL_GOVERNANCE_RED_TEAM_CONVERGED"
            if not failed
            else "HOLD_TOTAL_FIELD_SKILL_GOVERNANCE_FINDINGS_OPEN"
        ),
        "checks_passed": len(checks) - len(failed),
        "checks_total": len(checks),
        "open_findings": [item["check"] for item in failed],
        "checks": checks,
        "forbidden_actions_performed": [],
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
