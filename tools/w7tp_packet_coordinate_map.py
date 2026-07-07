#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W7TP Packet Coordinate Map.

- Does not write repo files.
- Does not stage files.
- Does not commit.
- Does not deploy.
- Observes packet D1-D8 coordinates only; does not approve or reject.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def coordinate_value(packet: Dict[str, Any]) -> Any:
    return packet.get("coordinate") or packet.get("D3_coordinate") or packet.get("spatial_binding")


def spatial_binding_summary(packet: Dict[str, Any]) -> Dict[str, Any]:
    spatial = packet.get("spatial_binding")
    if not isinstance(spatial, dict):
        return {
            "present": False,
            "static_group_positioning_only": None,
            "personal_positioning_allowed": None,
            "aggregate_demographic_context_present": False,
        }
    demographic = spatial.get("aggregate_demographic_context")
    return {
        "present": True,
        "binding_mode": spatial.get("binding_mode"),
        "positioning_subject": spatial.get("positioning_subject"),
        "geometry_scope": spatial.get("geometry_scope"),
        "coordinate_ref": spatial.get("coordinate_ref"),
        "geometry_ref": spatial.get("geometry_ref"),
        "jurisdiction_ref": spatial.get("jurisdiction_ref"),
        "static_group_positioning_only": spatial.get("static_group_positioning_only"),
        "personal_positioning_allowed": spatial.get("personal_positioning_allowed"),
        "contains_precise_person_location": spatial.get("contains_precise_person_location"),
        "reidentification_possible": spatial.get("reidentification_possible"),
        "aggregate_demographic_context_present": isinstance(demographic, dict),
        "aggregate_demographic_context": {
            "analysis_purpose": demographic.get("analysis_purpose"),
            "aggregation_level": demographic.get("aggregation_level"),
            "cohort_buckets": demographic.get("cohort_buckets"),
            "statistic_ref": demographic.get("statistic_ref"),
            "person_level_data_allowed": demographic.get("person_level_data_allowed"),
            "household_level_data_allowed": demographic.get("household_level_data_allowed"),
        } if isinstance(demographic, dict) else None,
    }


def evidence_present(packet: Dict[str, Any]) -> bool:
    if packet.get("evidence_ref"):
        return True
    d4 = packet.get("D4_evidence")
    return isinstance(d4, dict) and bool(d4)


def coordinate_map(packet: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "STATE": "PASS_COORDINATE_MAP",
        "D1_intent": packet.get("intent") or packet.get("D1_intent"),
        "D2_state": packet.get("state") or packet.get("D2_state"),
        "D3_coordinate": coordinate_value(packet),
        "D3_spatial_binding": spatial_binding_summary(packet),
        "D4_evidence_ref": evidence_present(packet),
        "D5_policy_flags": packet.get("policy_flags", []),
        "D5_execution": packet.get("D5_execution"),
        "D6_generation_claim": packet.get("generation_claim") or packet.get("D6_generation_claim") or packet.get("D6_gt"),
        "D7_redteam_flags": packet.get("redteam_flags", []),
        "D7_risk": packet.get("D7_risk"),
        "D8_envelope": packet.get("envelope") or packet.get("D8_envelope"),
        "writes_repo": False,
        "auto_stage": False,
        "auto_commit": False,
        "deploy": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    args = parser.parse_args()

    packet = json.loads(Path(args.file).read_text(encoding="utf-8"))
    if not isinstance(packet, dict):
        result = {
            "STATE": "HOLD_COORDINATE_MAP_INVALID_INPUT",
            "reason": "root JSON value must be an object",
            "writes_repo": False,
            "auto_stage": False,
            "auto_commit": False,
            "deploy": False,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    result = coordinate_map(packet)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
