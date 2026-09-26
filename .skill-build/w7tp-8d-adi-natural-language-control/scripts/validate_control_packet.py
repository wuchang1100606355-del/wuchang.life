#!/usr/bin/env python3
import json
import sys
from pathlib import Path

CLAIM_REQUIRED = {
    "USER_EXPLICIT": ["source_ref"],
    "OBSERVED_FACT": ["evidence_refs", "observed_at"],
    "PROVEN_HISTORICAL": ["evidence_refs", "historical_coordinate"],
    "HYPOTHESIS": ["basis_refs", "prediction", "falsifier", "minimum_test"],
    "DESIGN": ["requirements_refs", "facts_used", "hypotheses_used",
               "adi_coordinate_set", "d1_d8_projection",
               "product_level_target", "competitor_benchmark", "product_gap_to_target",
               "acceptance_conditions", "failure_modes", "rollback_design"],
    "IMPLEMENTATION_CANDIDATE": ["design_ref", "source_coordinates"],
    "VERIFIED_IMPLEMENTATION": ["implementation_ref", "verification_refs"],
    "LANDED": ["target_coordinate", "landing_receipt", "reobservation_refs"],
    "ACTIVE": ["runtime_coordinate", "effect_evidence_refs"],
    "CANONICAL": ["authority_resolution_ref"],
}

LANDING_REQUIRED = [
    "intent_current",
    "target_fresh",
    "dependencies_closed",
    "tests_passed",
    "wiring_defined",
    "rollback_ready",
    "risk_clear",
    "authority_satisfied",
]

def nonempty(value):
    if value is None:
        return False
    if isinstance(value, (list, dict, str)):
        return len(value) > 0
    return bool(value)

def validate_claim(claim):
    errors = []
    kind = claim.get("type")
    if kind not in CLAIM_REQUIRED:
        return [f"UNKNOWN_CLAIM_TYPE:{kind}"]
    for field in CLAIM_REQUIRED[kind]:
        if not nonempty(claim.get(field)):
            errors.append(f"{kind}:MISSING:{field}")
    if kind == "OBSERVED_FACT" and claim.get("confidence") == "inferred":
        errors.append("OBSERVED_FACT:CANNOT_BE_INFERRED")
    if kind == "HYPOTHESIS" and claim.get("status") in {"ACTIVE", "CANONICAL"}:
        errors.append("HYPOTHESIS:CANNOT_SELF_PROMOTE")
    return errors

def validate_landing(landing):
    errors = []
    state = landing.get("state")
    if state == "READY_TO_LAND":
        errors.append("AUTO_LAND_FORBIDS_TERMINAL_READY_TO_LAND")
    if state in {"READY_TO_LAND", "LAND_NOW", "LANDED_REOBSERVE", "ACTIVE_VERIFIED"}:
        for field in LANDING_REQUIRED:
            if landing.get(field) is not True:
                errors.append(f"LANDING_GATE_NOT_CLOSED:{field}")
    if landing.get("auto_land_default") is False:
        errors.append("AUTO_LAND_DEFAULT_MUST_NOT_BE_DISABLED")
    return errors

def main():
    if len(sys.argv) != 2:
        print("usage: validate_control_packet.py <packet.json>")
        return 2
    packet = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    errors = []
    for claim in packet.get("claims", []):
        errors.extend(validate_claim(claim))
    errors.extend(validate_landing(packet.get("landing", {})))
    if errors:
        print(json.dumps({"state": "HOLD_INVALID_CONTROL_PACKET",
                          "errors": errors}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({"state": "PASS_CONTROL_PACKET_STRUCTURE",
                      "claim_count": len(packet.get("claims", [])),
                      "landing_state": packet.get("landing", {}).get("state")},
                     ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
