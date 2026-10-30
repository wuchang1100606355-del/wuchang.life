#!/usr/bin/env python3
"""Validate W7TP Total Field skill manifests without changing system state."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "references" / "total_field_skill_manifest_v1.schema.json"
EXPECTED_FIELDS = {
    "D1": "INTENT",
    "D2": "STATE",
    "D3": "COORDINATE",
    "D4": "EVIDENCE",
    "D5": "EXECUTION_POLICY",
    "D6": "GENERATIVE_TRANSMISSION",
    "D7": "RED_TEAM_RISK_CONFINEMENT",
    "D8": "ENVELOPE_AUTHORITY",
}
FAMILIES = {f"F{number:02d}" for number in range(1, 21)}
EFFECTS = {f"E{number}" for number in range(6)}
TECHNOLOGY_IDENTITY_AXES = {
    "MECHANISM",
    "CAUSAL_PATH",
    "DEPENDENCIES",
    "ELIMINATED_OPERATIONS",
    "COST_TOPOLOGY",
    "CARRIER_RECONSTRUCTION_VERIFICATION",
}
TECHNOLOGY_IDENTITY_DECISIONS = {
    "SAME_MECHANISM",
    "PARTIAL_MECHANISM_OVERLAP",
    "EFFECT_ONLY_EQUIVALENT",
    "DIFFERENT_TECHNOLOGY",
    "INSUFFICIENT_EVIDENCE",
}
TECHNOLOGY_IDENTITY_EVIDENCE_SCALE = {
    "EV0_UNSUPPORTED",
    "EV1_ASSERTION",
    "EV2_SECONDARY_SOURCE",
    "EV3_PRIMARY_DOCUMENT",
    "EV4_IMPLEMENTATION_EVIDENCE",
    "EV5_REPRODUCIBLE_CAUSAL_EVIDENCE",
}
ALLOWED_OUTPUTS = {
    "CANDIDATE",
    "EVIDENCE",
    "HOLD",
    "AUTHORIZATION_REQUEST",
    "HUMAN_REPLY",
    "TOTAL_FIELD_DECISION_RECEIPT",
}
FORBIDDEN_AUTHORITY_MARKERS = {
    "ALLOW",
    "COMMITTED",
    "COMMIT_APPLIED",
    "TFS",
    "TFID",
    "TOTAL_FIELD_HASH",
    "CANONICAL_POINTER",
    "FINAL_SEAL",
    "DIRECT_DB_WRITE",
    "DIRECT_DEPLOY",
}
REQUIRED_HOLD_FIELDS = {
    "question",
    "answer",
    "risk_found",
    "possible_effect",
    "protected_state",
    "solution",
    "user_action_required",
}
REQUIRED_RED_TEAM_STAGES = {
    "RED_TEAM_PRE_DEFINITION",
    "RED_TEAM_PRE_ACTIVATION",
    "RED_TEAM_POST_OPERATION",
}
REQUIRED_TOP = {
    "schema_version",
    "manifest_state",
    "skill_id",
    "display_name_zh",
    "version",
    "language",
    "founder_authority_ref",
    "identity_and_seat",
    "product_output_contract",
    "classification",
    "information_context",
    "d1_d8_projection",
    "authority_boundary",
    "execution_contract",
    "w7tp_contract",
    "red_team_contract",
    "hold_contract",
    "authorization_contract",
    "verification_contract",
    "lifecycle",
    "evidence_and_hashes",
}
LEGACY_CANONICAL_REFS = {
    "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2",
    "docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2.md",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_manifest_hash(document: dict[str, Any]) -> str:
    value = copy.deepcopy(document)
    evidence = value.get("evidence_and_hashes")
    if isinstance(evidence, dict):
        evidence.pop("manifest_self_hash", None)
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def add(errors: list[str], condition: bool, code: str) -> None:
    if not condition:
        errors.append(code)


def optional_jsonschema_errors(
    document: dict[str, Any], schema_path: Path
) -> list[str]:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return []
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(document), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "$"
        errors.append(f"SCHEMA:{location}:{error.message}")
    return errors


def validate_document(
    document: dict[str, Any],
    *,
    manifest_path: Path | None = None,
    schema_path: Path = DEFAULT_SCHEMA,
    use_jsonschema: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    if use_jsonschema:
        errors.extend(optional_jsonschema_errors(document, schema_path))

    add(errors, REQUIRED_TOP <= set(document), "TOP_LEVEL_FIELDS_MISSING")
    add(
        errors,
        document.get("schema_version") == "w7tp-total-field-skill-manifest/1.0",
        "SCHEMA_VERSION_INVALID",
    )
    add(errors, document.get("language") == "zh-Hant", "LANGUAGE_NOT_ZH_HANT")
    add(
        errors,
        isinstance(document.get("skill_id"), str)
        and bool(re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,127}", document["skill_id"])),
        "SKILL_ID_INVALID",
    )
    add(
        errors,
        isinstance(document.get("version"), str)
        and bool(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", document["version"])),
        "VERSION_INVALID",
    )

    identity = document.get("identity_and_seat", {})
    for key in (
        "member_required",
        "xiaoj_identity_required",
        "fixed_role_capacity_required",
        "active_seat_required",
        "reservation_non_executable",
    ):
        add(errors, identity.get(key) is True, f"IDENTITY_SEAT_{key.upper()}_REQUIRED")
    add(
        errors,
        identity.get("cross_member_plaintext_allowed") is False,
        "CROSS_MEMBER_PLAINTEXT_MUST_BE_FALSE",
    )
    add(errors, bool(identity.get("allowed_roles")), "ALLOWED_ROLES_EMPTY")
    add(errors, bool(identity.get("access_profile_refs")), "ACCESS_PROFILE_REFS_EMPTY")

    product = document.get("product_output_contract", {})
    for key in (
        "intended_users",
        "user_need",
        "product_outcome",
        "deliverables",
        "interface_behavior",
        "quality_thresholds",
        "acceptance_criteria",
        "failure_behavior",
        "prohibited_outputs",
    ):
        add(errors, bool(product.get(key)), f"PRODUCT_OUTPUT_{key.upper()}_MISSING")

    technology_identity = document.get("technology_identity_contract")
    if technology_identity is not None:
        add(
            errors,
            technology_identity.get("applicable") is True,
            "TECHNOLOGY_IDENTITY_APPLICABLE_REQUIRED",
        )
        add(
            errors,
            technology_identity.get("gate_skill_ref")
            == "w7tp.technology-identity-audit@1.0.0",
            "TECHNOLOGY_IDENTITY_GATE_REF_INVALID",
        )
        add(
            errors,
            set(technology_identity.get("axes", [])) == TECHNOLOGY_IDENTITY_AXES,
            "TECHNOLOGY_IDENTITY_AXES_INCOMPLETE",
        )
        add(
            errors,
            set(technology_identity.get("decision_set", []))
            == TECHNOLOGY_IDENTITY_DECISIONS,
            "TECHNOLOGY_IDENTITY_DECISIONS_INCOMPLETE",
        )
        add(
            errors,
            set(technology_identity.get("evidence_scale", []))
            == TECHNOLOGY_IDENTITY_EVIDENCE_SCALE,
            "TECHNOLOGY_IDENTITY_EVIDENCE_SCALE_INVALID",
        )
        for key in (
            "effect_equivalence_not_technical_equivalence",
            "weighted_score_forbidden",
            "carrier_protocol_separation_required",
            "patentability_inference_forbidden",
        ):
            add(
                errors,
                technology_identity.get(key) is True,
                f"TECHNOLOGY_IDENTITY_{key.upper()}_REQUIRED",
            )

    classification = document.get("classification", {})
    add(
        errors,
        classification.get("primary_family") in FAMILIES,
        "PRIMARY_FAMILY_INVALID",
    )
    add(
        errors,
        set(classification.get("secondary_families", [])) <= FAMILIES,
        "SECONDARY_FAMILY_INVALID",
    )
    effect = classification.get("maximum_effect_class")
    add(errors, effect in EFFECTS, "EFFECT_CLASS_INVALID")

    context = document.get("information_context", {})
    add(errors, context.get("identity_derived_scope") is True, "CONTEXT_SCOPE_NOT_IDENTITY_DERIVED")
    add(errors, context.get("provenance_required") is True, "CONTEXT_PROVENANCE_NOT_REQUIRED")
    add(errors, context.get("retrieved_content_is_instruction") is False, "RETRIEVED_DATA_CAN_INSTRUCT")
    add(errors, context.get("raw_protected_context_allowed") is False, "RAW_PROTECTED_CONTEXT_ALLOWED")

    projections = document.get("d1_d8_projection", {})
    add(errors, set(projections) == set(EXPECTED_FIELDS), "D1_D8_KEYS_INVALID")
    for field, expected_name in EXPECTED_FIELDS.items():
        projection = projections.get(field, {})
        add(errors, projection.get("name") == expected_name, f"{field}_NAME_INVALID")
        add(errors, projection.get("required") is True, f"{field}_NOT_REQUIRED")
        add(errors, bool(projection.get("contract")), f"{field}_CONTRACT_EMPTY")

    authority = document.get("authority_boundary", {})
    outputs = set(authority.get("allowed_outputs", []))
    add(errors, bool(outputs), "ALLOWED_OUTPUTS_EMPTY")
    add(errors, outputs <= ALLOWED_OUTPUTS, "UNAUTHORIZED_OUTPUT_DECLARED")
    forbidden = {str(item).upper() for item in authority.get("forbidden_authority", [])}
    add(
        errors,
        FORBIDDEN_AUTHORITY_MARKERS <= forbidden,
        "FORBIDDEN_AUTHORITY_MARKERS_INCOMPLETE",
    )
    add(errors, authority.get("total_field_receiver_required") is True, "TOTAL_FIELD_RECEIVER_NOT_REQUIRED")
    add(errors, bool(authority.get("total_field_receiver_ref")), "TOTAL_FIELD_RECEIVER_REF_MISSING")
    human_final = set(authority.get("human_final_effect_classes", []))
    add(errors, "E5" in human_final, "E5_HUMAN_FINAL_MISSING")
    if effect in {"E4", "E5"}:
        add(errors, effect in human_final, f"{effect}_HUMAN_FINAL_MISSING")

    execution = document.get("execution_contract", {})
    add(errors, bool(execution.get("nodes")), "EXECUTION_NODES_EMPTY")
    add(errors, bool(execution.get("forbidden_effects")), "FORBIDDEN_EFFECTS_EMPTY")
    add(errors, bool(execution.get("rollback")), "ROLLBACK_EMPTY")
    if effect in {"E3", "E4", "E5"}:
        add(errors, execution.get("existing_state_preserved") is True, "EXISTING_STATE_NOT_PRESERVED")

    w7tp = document.get("w7tp_contract", {})
    add(errors, w7tp.get("carrier_is_not_w7tp") is True, "CARRIER_W7TP_CONFUSION")
    if w7tp.get("claimed") is True:
        for key in (
            "canonical_ref",
            "protocol_bearing_packet",
            "reconstruction_conditions",
            "packet_carried_verification",
        ):
            add(errors, bool(w7tp.get(key)), f"W7TP_{key.upper()}_MISSING")
        add(
            errors,
            w7tp.get("acceptance_mode") in {"EXACT_BYTES", "EQUIVALENT_STATE"},
            "W7TP_ACCEPTANCE_MODE_INVALID",
        )

    red_team = document.get("red_team_contract", {})
    add(errors, red_team.get("mandatory") is True, "RED_TEAM_NOT_MANDATORY")
    add(
        errors,
        set(red_team.get("stages", [])) == REQUIRED_RED_TEAM_STAGES,
        "RED_TEAM_STAGES_INCOMPLETE",
    )
    for key in (
        "high_critical_hold",
        "medium_requires_mitigation_or_policy",
        "closure_evidence_required",
        "authorization_cannot_waive_finding",
    ):
        add(errors, red_team.get(key) is True, f"RED_TEAM_{key.upper()}_REQUIRED")

    hold = document.get("hold_contract", {})
    add(errors, hold.get("language") == "zh-Hant", "HOLD_LANGUAGE_INVALID")
    add(
        errors,
        REQUIRED_HOLD_FIELDS <= set(hold.get("required_fields", [])),
        "HOLD_FIELDS_INCOMPLETE",
    )
    add(errors, hold.get("one_solution") is True, "HOLD_ONE_SOLUTION_REQUIRED")
    add(errors, hold.get("raw_code_only_forbidden") is True, "HOLD_RAW_CODE_ONLY_ALLOWED")

    authorization = document.get("authorization_contract", {})
    add(
        errors,
        set(authorization.get("required_for_effect_classes", [])) == {"E3", "E4", "E5"},
        "AUTHORIZATION_EFFECT_CLASSES_INCOMPLETE",
    )
    for key in (
        "single_use",
        "expiry_required",
        "input_hashes_required",
        "effect_and_risk_explanation_required",
        "rollback_required",
        "stop_conditions_required",
        "total_field_review_required",
    ):
        add(errors, authorization.get(key) is True, f"AUTHORIZATION_{key.upper()}_REQUIRED")

    verification = document.get("verification_contract", {})
    add(errors, bool(verification.get("product_acceptance_checks")), "PRODUCT_ACCEPTANCE_CHECKS_EMPTY")
    add(errors, bool(verification.get("evidence_required")), "VERIFICATION_EVIDENCE_EMPTY")
    add(errors, verification.get("existing_state_check") is True, "EXISTING_STATE_CHECK_MISSING")
    add(errors, verification.get("no_pass_without_evidence") is True, "PASS_WITHOUT_EVIDENCE_ALLOWED")

    serialized = json.dumps(document, ensure_ascii=False).upper()
    floating_index_declared = (
        "FLOATING_POINT_DATA_INDEX" in serialized
        or "浮點資料索引" in serialized
    )
    if floating_index_declared:
        static_checks = " ".join(
            str(item).upper() for item in verification.get("static_checks", [])
        )
        runtime_checks = " ".join(
            str(item).upper() for item in verification.get("runtime_checks", [])
        )
        evidence_required = " ".join(
            str(item).upper() for item in verification.get("evidence_required", [])
        )
        d7_contract = str(
            document.get("d1_d8_projection", {}).get("D7", {}).get("contract", "")
        ).upper()
        product_acceptance = " ".join(
            str(item).upper()
            for item in product.get("acceptance_criteria", [])
        )
        add(
            errors,
            "FLOAT" in static_checks,
            "FLOATING_POINT_DATA_INDEX_STATIC_CONTRACT_MISSING",
        )
        add(
            errors,
            "FLOAT" in runtime_checks,
            "FLOATING_POINT_DATA_INDEX_REPLAY_CHECK_MISSING",
        )
        add(
            errors,
            "FLOAT" in evidence_required,
            "FLOATING_POINT_DATA_INDEX_EVIDENCE_MISSING",
        )
        add(
            errors,
            "FLOAT" in d7_contract or "浮點" in d7_contract,
            "FLOATING_POINT_DATA_INDEX_RED_TEAM_CONTRACT_MISSING",
        )
        add(
            errors,
            "FLOAT" in product_acceptance or "浮點" in product_acceptance,
            "FLOATING_POINT_DATA_INDEX_PRODUCT_ACCEPTANCE_MISSING",
        )

    lifecycle = document.get("lifecycle", {})
    add(
        errors,
        lifecycle.get("state") == document.get("manifest_state"),
        "LIFECYCLE_STATE_MISMATCH",
    )
    add(errors, lifecycle.get("activation_requires_total_field_receipt") is True, "ACTIVATION_RECEIPT_NOT_REQUIRED")
    add(errors, bool(lifecycle.get("suspension_triggers")), "SUSPENSION_TRIGGERS_EMPTY")
    add(errors, lifecycle.get("retirement_preserves_evidence") is True, "RETIREMENT_EVIDENCE_NOT_PRESERVED")
    add(errors, lifecycle.get("session_revocation_on_seat_or_profile_change") is True, "SESSION_REVOCATION_NOT_REQUIRED")
    if lifecycle.get("state") in {"ALLOW_ISOLATED_CANARY_ONLY", "ACTIVE", "SUSPENDED", "DEPRECATED", "RETIRED", "BLOCKED"}:
        add(errors, bool(lifecycle.get("total_field_decision_ref")), "TOTAL_FIELD_DECISION_REF_MISSING")

    evidence = document.get("evidence_and_hashes", {})
    add(errors, evidence.get("hash_algorithm") == "SHA-256", "HASH_ALGORITHM_INVALID")
    add(
        errors,
        evidence.get("manifest_hash_excludes_field")
        == "evidence_and_hashes.manifest_self_hash",
        "SELF_HASH_EXCLUSION_INVALID",
    )
    add(errors, bool(evidence.get("canonical_refs")), "CANONICAL_REFS_EMPTY")
    add(errors, bool(evidence.get("schema_refs")), "SCHEMA_REFS_EMPTY")
    add(errors, bool(evidence.get("implementation_refs")), "IMPLEMENTATION_REFS_EMPTY")
    add(errors, bool(evidence.get("evidence_destination")), "EVIDENCE_DESTINATION_EMPTY")
    declared_canonical_refs = {
        str(item) for item in evidence.get("canonical_refs", [])
    }
    w7tp_canonical_ref = w7tp.get("canonical_ref")
    if isinstance(w7tp_canonical_ref, str):
        declared_canonical_refs.add(w7tp_canonical_ref)
    add(
        errors,
        declared_canonical_refs.isdisjoint(LEGACY_CANONICAL_REFS),
        "LEGACY_W7TP_CANONICAL_V2_REF",
    )

    self_hash = evidence.get("manifest_self_hash")
    expected_self_hash = canonical_manifest_hash(document)
    if self_hash != "PENDING_TOTAL_FIELD_SEAL":
        add(errors, self_hash == expected_self_hash, "MANIFEST_SELF_HASH_MISMATCH")
    if lifecycle.get("state") == "ACTIVE":
        add(errors, self_hash != "PENDING_TOTAL_FIELD_SEAL", "ACTIVE_MANIFEST_UNSEALED")

    if manifest_path is not None:
        manifest_dir = manifest_path.resolve().parent
        refs = evidence.get("implementation_refs", [])
        declared_hashes = evidence.get("implementation_sha256", {})
        for ref in refs:
            path = (manifest_dir / ref).resolve()
            try:
                path.relative_to(manifest_dir)
            except ValueError:
                errors.append(f"IMPLEMENTATION_REF_OUTSIDE_SKILL:{ref}")
                continue
            if not path.is_file():
                errors.append(f"IMPLEMENTATION_REF_MISSING:{ref}")
                continue
            declared = declared_hashes.get(ref)
            add(errors, declared == sha256_file(path), f"IMPLEMENTATION_HASH_MISMATCH:{ref}")

    errors = sorted(set(errors))
    return {
        "state": "PASS_SKILL_MANIFEST_VALID" if not errors else "HOLD_SKILL_MANIFEST_INVALID",
        "skill_id": document.get("skill_id"),
        "manifest_state": document.get("manifest_state"),
        "maximum_effect_class": effect,
        "calculated_manifest_self_hash": expected_self_hash,
        "errors": errors,
        "forbidden_actions_performed": [],
    }


def find_manifests(target: Path) -> list[Path]:
    target = target.resolve()
    if target.is_file():
        return [target]
    return sorted(target.rglob("total-field-skill-manifest.json"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--no-jsonschema", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifests = find_manifests(args.target)
    if not manifests:
        print(json.dumps({
            "state": "HOLD_NO_SKILL_MANIFEST_FOUND",
            "target": str(args.target),
            "errors": ["NO_MANIFEST"],
            "forbidden_actions_performed": [],
        }, ensure_ascii=False, indent=2))
        return 2

    results = []
    for path in manifests:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError("ROOT_NOT_OBJECT")
            result = validate_document(
                document,
                manifest_path=path,
                schema_path=args.schema,
                use_jsonschema=not args.no_jsonschema,
            )
        except Exception as exc:
            result = {
                "state": "HOLD_SKILL_MANIFEST_INVALID",
                "errors": [f"PARSE_OR_VALIDATION:{type(exc).__name__}"],
                "forbidden_actions_performed": [],
            }
        result["manifest"] = str(path)
        results.append(result)

    failed = [item for item in results if item["state"] != "PASS_SKILL_MANIFEST_VALID"]
    output = {
        "state": "PASS_ALL_SKILL_MANIFESTS_VALID" if not failed else "HOLD_SKILL_MANIFESTS_INVALID",
        "manifest_count": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "results": results,
        "forbidden_actions_performed": [],
    }
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
