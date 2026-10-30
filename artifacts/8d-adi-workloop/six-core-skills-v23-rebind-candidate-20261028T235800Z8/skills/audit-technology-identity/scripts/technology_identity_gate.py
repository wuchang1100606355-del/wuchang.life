#!/usr/bin/env python3
"""Validate and converge a six-axis technology-identity assessment."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


AXES = (
    "MECHANISM",
    "CAUSAL_PATH",
    "DEPENDENCIES",
    "ELIMINATED_OPERATIONS",
    "COST_TOPOLOGY",
    "CARRIER_RECONSTRUCTION_VERIFICATION",
)
RELATIONS = {"SAME", "PARTIAL", "DIFFERENT", "UNKNOWN"}
EFFECT_RELATIONS = {"SAME", "DIFFERENT", "UNKNOWN"}
EVIDENCE_LEVELS = (
    "EV0_UNSUPPORTED",
    "EV1_ASSERTION",
    "EV2_SECONDARY_SOURCE",
    "EV3_PRIMARY_DOCUMENT",
    "EV4_IMPLEMENTATION_EVIDENCE",
    "EV5_REPRODUCIBLE_CAUSAL_EVIDENCE",
)
EVIDENCE_RANK = {name: index for index, name in enumerate(EVIDENCE_LEVELS)}


class ContractError(ValueError):
    """Raised when the assessment violates the gate contract."""


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{label} must be a non-empty string")
    return value.strip()


def require_string_list(value: Any, label: str) -> list[str]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        raise ContractError(f"{label} must be a list of non-empty strings")
    return [item.strip() for item in value]


def validate_assessment(document: Mapping[str, Any]) -> dict[str, Any]:
    if document.get("schema_version") != "technology-identity-gate/1.0":
        raise ContractError("schema_version must be technology-identity-gate/1.0")
    comparison_id = require_string(document.get("comparison_id"), "comparison_id")
    technology_a = require_string(document.get("technology_a"), "technology_a")
    technology_b = require_string(document.get("technology_b"), "technology_b")
    effect_relation = require_string(
        document.get("observable_effect_relation"),
        "observable_effect_relation",
    ).upper()
    if effect_relation not in EFFECT_RELATIONS:
        raise ContractError("observable_effect_relation must be SAME, DIFFERENT, or UNKNOWN")

    axes_raw = document.get("axes")
    if not isinstance(axes_raw, Mapping):
        raise ContractError("axes must be an object")
    if set(axes_raw) != set(AXES):
        raise ContractError("axes must contain exactly the six fixed technology-identity axes")

    normalized_axes: dict[str, dict[str, Any]] = {}
    for axis in AXES:
        raw = axes_raw[axis]
        if not isinstance(raw, Mapping):
            raise ContractError(f"axes.{axis} must be an object")
        relation = require_string(raw.get("relation"), f"axes.{axis}.relation").upper()
        if relation not in RELATIONS:
            raise ContractError(f"axes.{axis}.relation is invalid")
        evidence_level = require_string(
            raw.get("evidence_level"), f"axes.{axis}.evidence_level"
        ).upper()
        if evidence_level not in EVIDENCE_RANK:
            raise ContractError(f"axes.{axis}.evidence_level is invalid")
        evidence_refs = require_string_list(
            raw.get("evidence_refs", []), f"axes.{axis}.evidence_refs"
        )
        if EVIDENCE_RANK[evidence_level] > 0 and not evidence_refs:
            raise ContractError(f"axes.{axis} requires evidence_refs for {evidence_level}")
        finding = require_string(raw.get("finding"), f"axes.{axis}.finding")
        normalized_axes[axis] = {
            "relation": relation,
            "evidence_level": evidence_level,
            "evidence_refs": evidence_refs,
            "finding": finding,
        }

    return {
        "comparison_id": comparison_id,
        "technology_a": technology_a,
        "technology_b": technology_b,
        "observable_effect_relation": effect_relation,
        "axes": normalized_axes,
    }


def decide(document: Mapping[str, Any]) -> dict[str, Any]:
    normalized = validate_assessment(document)
    axes = normalized["axes"]
    effect_relation = normalized["observable_effect_relation"]

    all_same_strong = all(
        item["relation"] == "SAME"
        and EVIDENCE_RANK[item["evidence_level"]] >= 3
        for item in axes.values()
    )
    strong_differences = [
        axis
        for axis, item in axes.items()
        if item["relation"] == "DIFFERENT"
        and EVIDENCE_RANK[item["evidence_level"]] >= 3
    ]
    all_known_secondary = all(
        item["relation"] != "UNKNOWN"
        and EVIDENCE_RANK[item["evidence_level"]] >= 2
        for item in axes.values()
    )
    partial_axes = [
        axis for axis, item in axes.items() if item["relation"] == "PARTIAL"
    ]

    if all_same_strong:
        decision = "SAME_MECHANISM"
        decisive_axes = list(AXES)
    elif strong_differences and effect_relation == "SAME":
        decision = "EFFECT_ONLY_EQUIVALENT"
        decisive_axes = strong_differences
    elif strong_differences:
        decision = "DIFFERENT_TECHNOLOGY"
        decisive_axes = strong_differences
    elif partial_axes and all_known_secondary:
        decision = "PARTIAL_MECHANISM_OVERLAP"
        decisive_axes = partial_axes
    else:
        decision = "INSUFFICIENT_EVIDENCE"
        decisive_axes = [
            axis
            for axis, item in axes.items()
            if item["relation"] == "UNKNOWN"
            or EVIDENCE_RANK[item["evidence_level"]] < 3
        ]

    eliminated = axes["ELIMINATED_OPERATIONS"]
    if eliminated["relation"] == "UNKNOWN" or EVIDENCE_RANK[eliminated["evidence_level"]] < 3:
        structural_elimination = "UNKNOWN"
    elif "optim" in eliminated["finding"].lower() or "優化" in eliminated["finding"]:
        structural_elimination = "OPTIMIZATION_ONLY"
    else:
        structural_elimination = "EVIDENCE_BOUND"

    carrier = axes["CARRIER_RECONSTRUCTION_VERIFICATION"]
    carrier_boundary = (
        "PRESERVED"
        if carrier["relation"] != "UNKNOWN"
        and EVIDENCE_RANK[carrier["evidence_level"]] >= 2
        else "UNKNOWN"
    )

    return {
        "STATE": "PASS_TECHNOLOGY_IDENTITY_CANDIDATE",
        "DECISION": decision,
        "comparison_id": normalized["comparison_id"],
        "technology_a": normalized["technology_a"],
        "technology_b": normalized["technology_b"],
        "observable_effect_relation": effect_relation,
        "decisive_axes": decisive_axes,
        "axes": axes,
        "structural_elimination": structural_elimination,
        "carrier_reconstruction_boundary": carrier_boundary,
        "weighted_score_used": False,
        "patent_or_legal_conclusion": "NOT_DETERMINED",
        "authority": "CANDIDATE_ONLY",
    }


def fixture(
    *,
    effect: str = "SAME",
    relation: str = "SAME",
    level: str = "EV3_PRIMARY_DOCUMENT",
) -> dict[str, Any]:
    return {
        "schema_version": "technology-identity-gate/1.0",
        "comparison_id": "self-test",
        "technology_a": "A",
        "technology_b": "B",
        "observable_effect_relation": effect,
        "axes": {
            axis: {
                "relation": relation,
                "evidence_level": level,
                "evidence_refs": [f"fixture://{axis.lower()}"],
                "finding": "Primary evidence supports the declared bounded relation.",
            }
            for axis in AXES
        },
    }


def self_test() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def run(name: str, document: dict[str, Any], expected: str) -> None:
        actual = decide(document)["DECISION"]
        checks.append({"check": name, "expected": expected, "actual": actual, "pass": actual == expected})

    run("all_axes_same", fixture(), "SAME_MECHANISM")

    effect_only = fixture()
    effect_only["axes"]["MECHANISM"]["relation"] = "DIFFERENT"
    run("effect_only_equivalent", effect_only, "EFFECT_ONLY_EQUIVALENT")

    different = fixture(effect="DIFFERENT")
    different["axes"]["CAUSAL_PATH"]["relation"] = "DIFFERENT"
    run("different_technology", different, "DIFFERENT_TECHNOLOGY")

    partial = fixture(level="EV2_SECONDARY_SOURCE")
    partial["axes"]["DEPENDENCIES"]["relation"] = "PARTIAL"
    run("partial_overlap", partial, "PARTIAL_MECHANISM_OVERLAP")

    unknown = fixture()
    unknown["axes"]["COST_TOPOLOGY"].update({
        "relation": "UNKNOWN",
        "evidence_level": "EV0_UNSUPPORTED",
        "evidence_refs": [],
    })
    run("unknown_axis", unknown, "INSUFFICIENT_EVIDENCE")

    weak_same = fixture(level="EV1_ASSERTION")
    run("weak_same_claim", weak_same, "INSUFFICIENT_EVIDENCE")

    invalid = fixture()
    invalid["axes"].pop("MECHANISM")
    try:
        decide(invalid)
        invalid_pass = False
    except ContractError:
        invalid_pass = True
    checks.append({"check": "missing_axis_blocked", "expected": "ContractError", "actual": "ContractError" if invalid_pass else "PASS", "pass": invalid_pass})

    failed = [item for item in checks if not item["pass"]]
    return {
        "STATE": "SELF_TEST_COMPLETE" if not failed else "SELF_TEST_FAILED",
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks": checks,
        "weighted_score_used": False,
        "network_used": False,
    }


def load_document(path: str) -> Mapping[str, Any]:
    if path == "-":
        value = json.load(sys.stdin)
    else:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ContractError("assessment root must be an object")
    return value


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("assessment", nargs="?", help="JSON assessment path, or - for stdin")
    result.add_argument("--self-test", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.self_test:
        result = self_test()
        code = 0 if result["STATE"] == "SELF_TEST_COMPLETE" else 1
    elif not args.assessment:
        result = {"STATE": "PRECONDITION_MISSING", "error": "assessment is required"}
        code = 2
    else:
        try:
            result = decide(load_document(args.assessment))
            code = 0
        except (OSError, json.JSONDecodeError, ContractError) as exc:
            result = {"STATE": "PRECONDITION_MISSING", "error": str(exc)}
            code = 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
