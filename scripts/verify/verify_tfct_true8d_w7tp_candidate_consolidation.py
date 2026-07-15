#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused verifier for the TFCT/TRUE8D/W7TP candidate consolidation."""

from __future__ import annotations

import copy
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "TFCT_TRUE8D_W7TP_8DGTE_SYSTEM_CONSOLIDATION_CANDIDATE_V0_1"
DOC_ROOT = ROOT / "docs/total_field"
DOCUMENTS = {
    "theory": DOC_ROOT / "TFCT_THEORY_CANDIDATE.md",
    "mathematics": DOC_ROOT / "TFCT_MATHEMATICS_CANDIDATE.md",
    "engineering": DOC_ROOT / "TFCT_TRUE8D_ENGINEERING_CANDIDATE.md",
    "gte": DOC_ROOT / "8D_GOVERNANCE_TENSOR_EXPRESSION_CANDIDATE.md",
    "small_agent": DOC_ROOT / "W7TP_SMALL_GENERATIVE_TRANSPORT_AGENT_CANDIDATE.md",
    "xiaoj": DOC_ROOT / "XIAOJ_SOVEREIGN_AGENT_CANDIDATE.md",
    "adi": DOC_ROOT / "ADI_INDEX_STRATEGY_CANDIDATE.md",
    "living_lab": DOC_ROOT / "TFCT_LIVING_LAB_DEMO_CANDIDATE.md",
    "report": DOC_ROOT / "TFCT_TRUE8D_W7TP_CONSOLIDATION_REPORT.md",
}
SCHEMA = ROOT / "schemas/field/8d_governance_tensor_expression_candidate.schema.json"
ACTIVE_CANONICAL = ROOT / "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json"
PROTECTED_POINTERS = (
    ROOT / "runtime/total_field/active/ACTIVE_CODEX_TOTAL_FIELD_GLOBAL_AGENT_DOMAIN_POINTER.txt",
    ROOT / "runtime/total_field/active/ACTIVE_DOMAIN_BETA_DEPLOYMENT_POINTER.txt",
    ROOT / "runtime/total_field/active/ACTIVE_POS_OFFICIAL_CHAIN_POINTER.txt",
    ROOT / "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_POINTER.txt",
    ROOT / "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_POINTER.txt",
    ROOT / "runtime/total_field/active/ACTIVE_TRUE8D_ROUTER_ALLNODE_MERGE_POINTER.txt",
    ROOT / "runtime/total_field/active/ACTIVE_TRUE8D_ROUTER_BOUNDARY_POINTER.txt",
    ROOT / "runtime/total_field/active/ACTIVE_V4_TRUE8D_TIPO_LANDING_POINTER.txt",
)
EXPECTED_DIMENSIONS = {
    "D1": "Intent Field",
    "D2": "State Field",
    "D3": "Coordinate Field",
    "D4": "Evidence Field",
    "D5": "Execution Field",
    "D6": "Sovereign Privacy Field",
    "D7": "Generative Transmission & Resource Routing Field",
    "D8": "Red-Team Detour Alert & Quarantine Field",
}
THEORY_FORBIDDEN = (
    "runtime",
    "python",
    "json",
    "canonical",
    "packet",
    "hash",
    "adi",
    ".py",
    ".json",
    "tools/",
    "runtime/",
    "schemas/",
)
MATHEMATICS_FORBIDDEN = (
    ".py",
    ".json",
    "tools/",
    "runtime/",
    "schemas/",
    "scripts/",
    "tests/",
)
PERFORMANCE_PATTERN = re.compile(
    r"(?i)\b\d[\d,.]*(?:\s*[–-]\s*\d[\d,.]*)?\s*(?:x|倍|%|MB|GB|ms|毫秒|秒)\b"
)
EVIDENCE_LABELS = ("Measured", "Assumed", "Illustrative", "Unverified")
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(
        r"(?i)(?:api[_-]?key|token|password|client_secret)\s*[:=]\s*[A-Za-z0-9._-]{12,}"
    ),
)


def read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_schema() -> dict[str, Any]:
    return json.loads(read_utf8(SCHEMA))


def valid_candidate_vector() -> dict[str, Any]:
    return {
        "schema_version": "8d-gte-candidate/0.1",
        "lifecycle": "CANDIDATE",
        "event_ref": "event:fixed:001",
        "observation_domain_ref": "observation-domain:fixed:001",
        "dimensions": {f"D{index}_ref": f"field:D{index}:fixed:001" for index in range(1, 9)},
        "constraint_hypergraph_ref": "constraint-hypergraph:fixed:001",
        "convergence_operator_ref": "convergence-operator:fixed:001",
        "priority_policy_ref": "priority-policy:fixed:001",
        "fixed_point_status": "PENDING",
        "verification": {
            "final_decision": "PENDING",
            "commit_applied": False,
        },
        "tfs_result": None,
    }


def valid_committed_vector() -> dict[str, Any]:
    value = valid_candidate_vector()
    value["lifecycle"] = "COMMITTED"
    value["fixed_point_status"] = "REACHED"
    value["verification"] = {
        "final_decision": "ALLOW",
        "commit_applied": True,
    }
    value["tfs_result"] = {
        "state_ref": "tfs-state:fixed:001",
        "tfid": "tfid:fixed:001",
        "total_field_hash": "total-field-hash:fixed:001",
    }
    return value


def schema_errors(instance: dict[str, Any], schema: dict[str, Any] | None = None) -> list[str]:
    validator = Draft202012Validator(schema or load_schema())
    return [error.message for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.path))]


def _require(text: str, markers: tuple[str, ...], code: str, errors: list[str]) -> None:
    for marker in markers:
        if marker not in text:
            errors.append(f"{code}:{marker}")


def _protected_files_clean() -> bool:
    paths = [ACTIVE_CANONICAL, *PROTECTED_POINTERS]
    relative = [str(path.relative_to(ROOT)) for path in paths]
    result = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *relative],
        cwd=ROOT,
        check=False,
    )
    return result.returncode == 0


def content_errors() -> list[str]:
    errors: list[str] = []
    texts: dict[str, str] = {}
    for name, path in DOCUMENTS.items():
        try:
            texts[name] = read_utf8(path)
        except FileNotFoundError:
            errors.append(f"DOCUMENT_MISSING:{name}")
        except UnicodeError:
            errors.append(f"DOCUMENT_NOT_UTF8:{name}")
    if errors:
        return errors

    theory_lower = texts["theory"].lower()
    for term in THEORY_FORBIDDEN:
        if term.lower() in theory_lower:
            errors.append(f"THEORY_LAYER_FORBIDDEN_TERM:{term}")
    _require(
        texts["theory"],
        (
            "Total Field Convergence Theory",
            "E1",
            "E2",
            "E3",
            "E4",
            "F1",
            "F2",
            "F3",
            "F4",
            "F5",
            "Consistency Principle",
            "Governance Principle",
            "Separation Principle",
            "Open Problems",
        ),
        "THEORY_REQUIRED_MARKER_MISSING",
        errors,
    )

    mathematics_lower = texts["mathematics"].lower()
    for term in MATHEMATICS_FORBIDDEN:
        if term.lower() in mathematics_lower:
            errors.append(f"MATHEMATICS_LAYER_FORBIDDEN_TERM:{term}")
    _require(
        texts["mathematics"],
        (
            "Constraint Hypergraph",
            "Priority Policy",
            "Required Theorem RT1",
            "Required Theorem RT2",
            "Required Theorem RT3",
            "Required Theorem RT4",
            "UNPROVEN",
            "Open Problems",
        ),
        "MATHEMATICS_REQUIRED_MARKER_MISSING",
        errors,
    )

    _require(
        texts["engineering"],
        (
            "TFCT_THEORY_CANDIDATE.md",
            "TFCT_MATHEMATICS_CANDIDATE.md",
            "`Implemented`",
            "`Candidate`",
            "`Legacy`",
            "`Conflict`",
            "`Open Problem`",
            "D6_gt",
            "D7_risk",
            "D8_envelope",
            "D1_identity",
            "D8_commit",
        ),
        "ENGINEERING_MAPPING_MISSING",
        errors,
    )

    try:
        active = json.loads(read_utf8(ACTIVE_CANONICAL))
        actual_dimensions = {
            item.get("id"): item.get("field_en")
            for item in active.get("dimensions", [])
            if isinstance(item, dict)
        }
        if actual_dimensions != EXPECTED_DIMENSIONS:
            errors.append("ACTIVE_CANONICAL_DIMENSION_MISMATCH")
    except (FileNotFoundError, UnicodeError, json.JSONDecodeError):
        errors.append("ACTIVE_CANONICAL_UNREADABLE")

    adopted_text = "\n".join((texts["engineering"], texts["gte"], texts["report"]))
    _require(
        adopted_text,
        (
            "Sovereign Privacy Field",
            "Generative Transmission & Resource Routing Field",
            "Red-Team Detour Alert & Quarantine Field",
        ),
        "ACTIVE_DIMENSION_SEMANTIC_MARKER_MISSING",
        errors,
    )

    all_text = "\n".join(texts.values())
    for prohibited_claim in (
        "generative transmission is file moving",
        "generative transmission equals file transfer",
        "生成式傳輸是檔案搬運",
        "生成式傳輸等於檔案搬運",
        "生成式傳輸是雲端同步",
    ):
        if prohibited_claim.lower() in all_text.lower():
            errors.append(f"GENERATIVE_TRANSMISSION_DEFINITION_DRIFT:{prohibited_claim}")
    _require(
        texts["report"],
        (
            "state-field packets",
            "references",
            "reconstruction conditions",
            "equivalent-state generation",
            "Total Field verification",
        ),
        "GENERATIVE_TRANSMISSION_REQUIRED_MEANING_MISSING",
        errors,
    )

    if not any(marker in texts["adi"] for marker in ("ADI is not D3", "ADI 不是 D3", "ADI ≠ D3")):
        errors.append("ADI_NOT_D3_MARKER_MISSING")
    _require(
        texts["xiaoj"] + texts["small_agent"],
        ("Candidate", "Total Field", "ALLOW"),
        "CANDIDATE_AUTHORITY_BOUNDARY_MISSING",
        errors,
    )
    _require(
        adopted_text,
        ("Only `ALLOW` may commit", "preserve the prior committed state"),
        "ALLOW_ONLY_COMMIT_MARKER_MISSING",
        errors,
    )

    for line_no, line in enumerate(texts["living_lab"].splitlines(), start=1):
        if PERFORMANCE_PATTERN.search(line) and not any(label in line for label in EVIDENCE_LABELS):
            errors.append(f"PERFORMANCE_EVIDENCE_LABEL_MISSING:{line_no}")

    _require(
        texts["report"],
        (
            "Fixed-point existence and uniqueness conditions",
            "global finite convergence",
            "Cross-node equivalence",
            "PATENT_CANDIDATE_REVIEW_REQUIRED=YES",
        ),
        "OPEN_PROBLEM_OR_PATENT_MARKER_MISSING",
        errors,
    )
    for prohibited_claim in ("NOVEL", "PATENTED", "WORLD_FIRST"):
        if prohibited_claim in all_text:
            errors.append(f"PATENT_OVERCLAIM:{prohibited_claim}")
    for pattern in SECRET_PATTERNS:
        if pattern.search(all_text):
            errors.append("RAW_SECRET_PATTERN")
            break

    try:
        schema = load_schema()
        Draft202012Validator.check_schema(schema)
        serialized_schema = json.dumps(schema, ensure_ascii=False, sort_keys=True)
        for forbidden_schema_term in (
            "D6_gt",
            "D7_risk",
            "D8_envelope",
            "D1_identity",
            "D8_commit",
        ):
            if forbidden_schema_term in serialized_schema:
                errors.append(f"SCHEMA_LEGACY_TERM:{forbidden_schema_term}")
        if schema_errors(valid_candidate_vector(), schema):
            errors.append("SCHEMA_VALID_CANDIDATE_REJECTED")
        if schema_errors(valid_committed_vector(), schema):
            errors.append("SCHEMA_VALID_COMMITTED_REJECTED")
    except (FileNotFoundError, UnicodeError, json.JSONDecodeError):
        errors.append("SCHEMA_UNREADABLE")
    except Exception as exc:  # jsonschema emits version-specific exception classes
        errors.append(f"SCHEMA_INVALID:{type(exc).__name__}")

    if not _protected_files_clean():
        errors.append("PROTECTED_ACTIVE_OR_POINTER_CHANGED")
    return errors


def main() -> int:
    errors = content_errors()
    if errors:
        print("STATE=HOLD_VERIFY_TFCT_TRUE8D_W7TP_CANDIDATE_CONSOLIDATION")
        print(f"RUN_ID={RUN_ID}")
        print(f"REASON={errors[0]}")
        return 1
    print("UTF8_DOCUMENTS=PASS")
    print("LAYER_SEPARATION=PASS")
    print("ACTIVE_DIMENSION_SEMANTICS=PASS")
    print("LEGACY_CONFLICT_RECORD=PASS")
    print("ALLOW_ONLY_COMMIT=PASS")
    print("PERFORMANCE_EVIDENCE_LABELS=PASS")
    print("SCHEMA_DRAFT_2020_12=PASS")
    print("PROTECTED_FILES_UNCHANGED=PASS")
    print(f"RUN_ID={RUN_ID}")
    print("STATE=PASS_VERIFY_TFCT_TRUE8D_W7TP_CANDIDATE_CONSOLIDATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
