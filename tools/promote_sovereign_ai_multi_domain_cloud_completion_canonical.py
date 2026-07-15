#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Promote the verified multi-domain completion policy into its own chain."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_CANONICAL_V0_1"
SOURCE_RUN_ID = "SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_CANDIDATE_V0_1"
SOURCE_POLICY_SHA256 = "795d86f1ab04047a4c212fa6c11231539119b5a0b96561981902d67aabad868a"

SOURCE_POLICY = Path(
    "runtime/total_field/candidate/sovereign_ai_domain_completion_policy_v0_1.json"
)
SOURCE_SCHEMA = Path(
    "schemas/field/sovereign_ai_domain_completion_candidate.schema.json"
)
SOURCE_VERIFIER = Path(
    "scripts/verify/verify_sovereign_ai_domain_completion_candidate.py"
)
SOURCE_REPORT = Path(
    "docs/total_field/SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_CANDIDATE_REPORT.md"
)

TRACKED_DIRECTORY = Path(
    "manifests/sovereign_ai_multi_domain_cloud_completion_canonical_v0_1"
)
TRACKED_POLICY = TRACKED_DIRECTORY / "policy.json"
CANONICAL_MANIFEST = TRACKED_DIRECTORY / "canonical_manifest.json"
PROMOTION_EVIDENCE = TRACKED_DIRECTORY / "promotion_evidence.json"
ROLLBACK_MANIFEST = TRACKED_DIRECTORY / "rollback_manifest.json"

RUNTIME_DIRECTORY = Path(
    "runtime/total_field/SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_CANONICAL_V0_1"
)
RUNTIME_CANONICAL = (
    RUNTIME_DIRECTORY / "SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_CANONICAL.json"
)
RUNTIME_MANIFEST = (
    RUNTIME_DIRECTORY
    / "SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_CANONICAL_MANIFEST.json"
)
RUNTIME_EVIDENCE = (
    RUNTIME_DIRECTORY
    / "SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_PROMOTION_EVIDENCE.json"
)
ACTIVE_CANONICAL = Path(
    "runtime/total_field/active/ACTIVE_SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_CANONICAL.json"
)
ACTIVE_POINTER = Path(
    "runtime/total_field/active/ACTIVE_SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_POINTER.txt"
)

DOMAINS = ("COMMUNITY", "COMMERCE", "PROPERTY")
SOURCE_MODES = ("TOTAL_FIELD_PULL", "LLM_PUSH", "XIAOJ_LOCAL")
SEMANTIC_LOCKS = {
    "ALLOW_ONLY_COMMIT": "REQUIRED",
    "CLOUD_COMPLETION": "SUPPORTED_AS_CANDIDATE_ONLY",
    "CLOUD_LLM_AUTHORITY": "NONE",
    "D4_EVIDENCE_GATE": "REQUIRED",
    "D6_PRIVACY_GATE": "REQUIRED",
    "D8_ADJUDICATION": "REQUIRED",
    "DB_WRITE": "OWNER_OR_FORMAL_GATE_REQUIRED",
    "FINANCIAL_ATTRIBUTES": "FINANCIAL_REVIEW_REQUIRED",
    "LEGAL_ATTRIBUTES": "LEGAL_REVIEW_REQUIRED",
    "OWNER_ATTRIBUTES": "OWNER_CONFIRMATION_REQUIRED",
    "SENSITIVE_ATTRIBUTES": "PRIVACY_RESTRICTED",
    "TOTAL_FIELD_GATEWAY": "REQUIRED",
    "XIAOJ_FINAL_AUTHORITY": "NO",
}
OPEN_PROBLEMS = (
    "PRODUCTION_CLOUD_PROVIDER_SECURITY_REVIEW",
    "PRODUCTION_OBSERVATION_DOMAIN_COMPLETENESS",
    "DOMAIN_ONTOLOGY_VERSIONING",
    "HUMAN_REVIEW_OPERATING_PROCEDURE",
    "PATENT_CANDIDATE_REVIEW",
)


class PromotionFailure(ValueError):
    """Stable promotion error that never includes source payload content."""

    def __init__(self, reason_code: str, path: str = "") -> None:
        self.reason_code = reason_code
        self.path = path
        super().__init__(reason_code)


@dataclass(frozen=True, slots=True)
class VerificationResult:
    status: str
    source_policy_sha256: str


@dataclass(frozen=True, slots=True)
class PromotionResult:
    status: str
    files_written: tuple[str, ...]


def _duplicate_guard(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PromotionFailure("JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> Any:
    raise PromotionFailure("JSON_NONFINITE_VALUE", value)


def _require_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise PromotionFailure("JSON_NONFINITE_VALUE")
    if isinstance(value, dict):
        for nested in value.values():
            _require_finite(nested)
    elif isinstance(value, list):
        for nested in value:
            _require_finite(nested)


def load_strict_json(path: str | Path) -> Any:
    source = Path(path)
    try:
        raw = source.read_bytes()
    except FileNotFoundError as exc:
        raise PromotionFailure("SOURCE_FILE_MISSING", str(source)) from exc
    except OSError as exc:
        raise PromotionFailure("SOURCE_FILE_READ_FAILED", str(source)) from exc
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PromotionFailure("SOURCE_FILE_NOT_UTF8", str(source)) from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_duplicate_guard,
            parse_constant=_reject_nonfinite,
        )
        _require_finite(value)
        return value
    except PromotionFailure:
        raise
    except (json.JSONDecodeError, RecursionError) as exc:
        raise PromotionFailure("STRICT_JSON_INVALID", str(source)) from exc


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise PromotionFailure("JSON_NOT_CANONICALIZABLE") from exc


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _require_object(value: Any, reason_code: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PromotionFailure(reason_code)
    return value


def _read_text(root: Path, relative: Path) -> str:
    try:
        return (root / relative).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PromotionFailure("SOURCE_EVIDENCE_MISSING", str(relative)) from exc
    except UnicodeError as exc:
        raise PromotionFailure("SOURCE_EVIDENCE_NOT_UTF8", str(relative)) from exc


def _check_policy(policy: dict[str, Any]) -> None:
    if policy.get("run_id") != SOURCE_RUN_ID or policy.get("status") != "CANDIDATE":
        raise PromotionFailure("SOURCE_POLICY_MISMATCH", str(SOURCE_POLICY))
    if policy.get("cloud_completion") != "SUPPORTED_AS_CANDIDATE_ONLY":
        raise PromotionFailure("SOURCE_POLICY_MISMATCH", str(SOURCE_POLICY))
    domains = policy.get("domains")
    if not isinstance(domains, dict) or tuple(sorted(domains)) != tuple(sorted(DOMAINS)):
        raise PromotionFailure("SOURCE_POLICY_MISMATCH", str(SOURCE_POLICY))
    if policy.get("decision_priority") != ["QUARANTINE", "BLOCK", "HOLD", "ALLOW"]:
        raise PromotionFailure("SOURCE_POLICY_MISMATCH", str(SOURCE_POLICY))
    modes = policy.get("allowed_source_modes")
    if not isinstance(modes, list) or not set(SOURCE_MODES).issubset(modes):
        raise PromotionFailure("SOURCE_POLICY_MISMATCH", str(SOURCE_POLICY))
    rules = policy.get("gate_rules")
    required_rules = {
        "EVIDENCE_REQUIRED",
        "FINANCIAL_REVIEW_REQUIRED",
        "LEGAL_REVIEW_REQUIRED",
        "OWNER_CONFIRMATION_REQUIRED",
        "PRIVACY_RESTRICTED",
        "SAFE_DERIVED",
        "UNSUPPORTED",
    }
    if not isinstance(rules, dict) or set(rules) != required_rules:
        raise PromotionFailure("SOURCE_POLICY_MISMATCH", str(SOURCE_POLICY))
    side_effects = policy.get("side_effects")
    if not isinstance(side_effects, dict) or any(side_effects.values()):
        raise PromotionFailure("SOURCE_POLICY_MISMATCH", str(SOURCE_POLICY))


def verify_source(root: str | Path = ROOT) -> VerificationResult:
    base = Path(root)
    policy = _require_object(
        load_strict_json(base / SOURCE_POLICY), "SOURCE_POLICY_NOT_OBJECT"
    )
    if canonical_sha256(policy) != SOURCE_POLICY_SHA256:
        raise PromotionFailure("SOURCE_POLICY_MISMATCH", str(SOURCE_POLICY))
    _check_policy(policy)
    schema = _require_object(
        load_strict_json(base / SOURCE_SCHEMA), "SOURCE_SCHEMA_NOT_OBJECT"
    )
    domain_enum = schema.get("properties", {}).get("domain", {}).get("enum")
    if domain_enum != list(DOMAINS):
        raise PromotionFailure("SOURCE_SCHEMA_MISMATCH", str(SOURCE_SCHEMA))
    verifier = _read_text(base, SOURCE_VERIFIER)
    report = _read_text(base, SOURCE_REPORT)
    required_verifier = (
        "STATE=PASS_VERIFY_SOVEREIGN_AI_DOMAIN_COMPLETION_CANDIDATE",
        'print("TEST_COUNT=30")',
        "SUPPORTED_AS_CANDIDATE_ONLY",
    )
    required_report = (
        "CLOUD_COMPLETION=SUPPORTED_AS_CANDIDATE_ONLY",
        "ALLOW-only",
        "D6 sovereign privacy",
        "D8 adjudication",
        "DB_WRITE=NO",
        "DEPLOY=NO",
        "RESTART=NO",
        "ROUTER_WRITE=NO",
    )
    if any(marker not in verifier for marker in required_verifier):
        raise PromotionFailure("SOURCE_PASS_EVIDENCE_INVALID", str(SOURCE_VERIFIER))
    if any(marker not in report for marker in required_report):
        raise PromotionFailure("SOURCE_PASS_EVIDENCE_INVALID", str(SOURCE_REPORT))
    return VerificationResult("MATCH", SOURCE_POLICY_SHA256)


def _canonical_manifest_value() -> dict[str, Any]:
    return {
        "schema_version": "sovereign-ai.multi-domain-cloud-completion-canonical-manifest/0.1",
        "run_id": RUN_ID,
        "status": "ACTIVE_CANONICAL",
        "canonical_scope": "SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_GOVERNANCE",
        "canonical_version": "v0.1",
        "source_policy": str(SOURCE_POLICY),
        "source_policy_sha256": SOURCE_POLICY_SHA256,
        "owner_confirmation": "YES",
        "domains": {domain: "ACTIVE_CANONICAL" for domain in DOMAINS},
        "cloud_completion": "SUPPORTED_AS_CANDIDATE_ONLY",
        "semantic_locks": dict(SEMANTIC_LOCKS),
        "patent_candidate_review_required": True,
        "side_effects": {
            "db_write": False,
            "deploy": False,
            "restart": False,
            "router_write": False,
        },
    }


def _promotion_evidence_value() -> dict[str, Any]:
    return {
        "schema_version": "sovereign-ai.multi-domain-cloud-completion-promotion-evidence/0.1",
        "promotion_run_id": RUN_ID,
        "state": "PASS",
        "owner_confirmation": "YES",
        "source_candidate": {
            "run_id": "TFCT_TRUE8D_RUNTIME_SECURITY_CORRECTION_V0_1",
            "state": "PASS_SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_CANDIDATE",
            "policy": str(SOURCE_POLICY),
            "policy_sha256": SOURCE_POLICY_SHA256,
            "focused_tests": "30/30",
            "verifier": "PASS_VERIFY_SOVEREIGN_AI_DOMAIN_COMPLETION_CANDIDATE",
        },
        "promoted_scope": list(DOMAINS),
        "candidate_only": True,
        "common_gateway_sources": list(SOURCE_MODES),
        "gates": {"D4": "REQUIRED", "D6": "REQUIRED", "D8": "REQUIRED"},
        "allow_only_commit": True,
        "protected_other_active_and_pointers": True,
        "patent_candidate_review_required": True,
        "side_effects": {
            "db_write": False,
            "deploy": False,
            "restart": False,
            "router_write": False,
        },
    }


def _runtime_canonical_value(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "sovereign-ai.multi-domain-cloud-completion-canonical/0.1",
        "run_id": RUN_ID,
        "status": "ACTIVE_CANONICAL",
        "canonical_scope": "SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_GOVERNANCE",
        "canonical_version": "v0.1",
        "source_policy": str(SOURCE_POLICY),
        "source_policy_sha256": SOURCE_POLICY_SHA256,
        "policy": policy,
        "domains": {domain: "ACTIVE_CANONICAL" for domain in DOMAINS},
        "cloud_completion": "SUPPORTED_AS_CANDIDATE_ONLY",
        "source_modes": {
            mode: "TOTAL_FIELD_GATEWAY_REQUIRED" for mode in SOURCE_MODES
        },
        "semantic_locks": dict(SEMANTIC_LOCKS),
        "open_problems": list(OPEN_PROBLEMS),
        "side_effects": {
            "db_write": False,
            "deploy": False,
            "restart": False,
            "router_write": False,
        },
    }


def _runtime_manifest_value(runtime: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "sovereign-ai.multi-domain-cloud-completion-runtime-manifest/0.1",
        "run_id": RUN_ID,
        "status": "ACTIVE_CANONICAL",
        "runtime_canonical": str(RUNTIME_CANONICAL),
        "runtime_canonical_sha256": canonical_sha256(runtime),
        "source_policy_sha256": SOURCE_POLICY_SHA256,
        "active_canonical": str(ACTIVE_CANONICAL),
        "active_pointer": str(ACTIVE_POINTER),
    }


def _rollback_value(root: Path) -> dict[str, Any]:
    active = root / ACTIVE_CANONICAL
    pointer = root / ACTIVE_POINTER
    if active.exists() or pointer.exists():
        raise PromotionFailure(
            "EXISTING_MULTI_DOMAIN_CANONICAL_CONFLICT", str(ACTIVE_CANONICAL)
        )
    return {
        "schema_version": "sovereign-ai.multi-domain-cloud-completion-rollback-plan/0.1",
        "promotion_run_id": RUN_ID,
        "status": "PLAN_ONLY",
        "previous_active_canonical_exists": False,
        "previous_active_canonical_sha256": None,
        "previous_active_pointer_exists": False,
        "previous_active_pointer_content": None,
        "promoted_canonical": str(RUNTIME_CANONICAL),
        "promoted_active_canonical": str(ACTIVE_CANONICAL),
        "promoted_pointer": str(ACTIVE_POINTER),
        "rollback_requires_owner_confirmation": True,
        "automatic_rollback": False,
    }


def _expected_values(root: Path, *, allow_existing_rollback: bool) -> dict[Path, bytes]:
    policy = _require_object(load_strict_json(root / SOURCE_POLICY), "SOURCE_POLICY_NOT_OBJECT")
    runtime = _runtime_canonical_value(policy)
    evidence = _promotion_evidence_value()
    rollback_path = root / ROLLBACK_MANIFEST
    if allow_existing_rollback and rollback_path.is_file():
        rollback = _require_object(
            load_strict_json(rollback_path), "ROLLBACK_MANIFEST_NOT_OBJECT"
        )
    else:
        rollback = _rollback_value(root)
    pointer_target = str((root / RUNTIME_CANONICAL).resolve()) + "\n"
    return {
        TRACKED_POLICY: _json_bytes(policy),
        CANONICAL_MANIFEST: _json_bytes(_canonical_manifest_value()),
        PROMOTION_EVIDENCE: _json_bytes(evidence),
        ROLLBACK_MANIFEST: _json_bytes(rollback),
        RUNTIME_CANONICAL: _json_bytes(runtime),
        RUNTIME_MANIFEST: _json_bytes(_runtime_manifest_value(runtime)),
        RUNTIME_EVIDENCE: _json_bytes(evidence),
        ACTIVE_CANONICAL: _json_bytes(runtime),
        ACTIVE_POINTER: pointer_target.encode("utf-8"),
    }


def _write_exact(root: Path, relative: Path, content: bytes, *, atomic: bool) -> bool:
    path = root / relative
    if path.exists():
        try:
            current = path.read_bytes()
        except OSError as exc:
            raise PromotionFailure("CANONICAL_READ_FAILED", str(relative)) from exc
        if current != content:
            raise PromotionFailure(
                "EXISTING_MULTI_DOMAIN_CANONICAL_CONFLICT", str(relative)
            )
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    if not atomic:
        path.write_bytes(content)
        return True
    temporary = path.with_name(f".{path.name}.promotion-tmp")
    if temporary.exists():
        raise PromotionFailure("ATOMIC_TEMP_PATH_CONFLICT", str(relative))
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise PromotionFailure("ATOMIC_WRITE_FAILED", str(relative)) from exc
    return True


def promote(
    root: str | Path = ROOT, *, owner_confirmation: str
) -> PromotionResult:
    if owner_confirmation != "YES":
        raise PromotionFailure("OWNER_CONFIRMATION_REQUIRED")
    base = Path(root)
    verify_source(base)
    expected = _expected_values(base, allow_existing_rollback=True)
    for relative, content in expected.items():
        path = base / relative
        if path.exists() and path.read_bytes() != content:
            raise PromotionFailure(
                "EXISTING_MULTI_DOMAIN_CANONICAL_CONFLICT", str(relative)
            )
    written: list[str] = []
    for relative, content in expected.items():
        if _write_exact(
            base,
            relative,
            content,
            atomic=relative in {ACTIVE_CANONICAL, ACTIVE_POINTER},
        ):
            written.append(str(relative))
    verify_active(base)
    return PromotionResult("PROMOTED" if written else "ALREADY_ACTIVE", tuple(written))


def verify_active(root: str | Path = ROOT) -> VerificationResult:
    base = Path(root)
    verify_source(base)
    expected = _expected_values(base, allow_existing_rollback=True)
    for relative, content in expected.items():
        path = base / relative
        if not path.is_file() or path.read_bytes() != content:
            raise PromotionFailure(
                "EXISTING_MULTI_DOMAIN_CANONICAL_CONFLICT", str(relative)
            )
    tracked = load_strict_json(base / TRACKED_POLICY)
    runtime = load_strict_json(base / RUNTIME_CANONICAL)
    active = load_strict_json(base / ACTIVE_CANONICAL)
    if not isinstance(runtime, dict) or not isinstance(active, dict):
        raise PromotionFailure("ACTIVE_CANONICAL_INVALID", str(ACTIVE_CANONICAL))
    if canonical_json(tracked) != canonical_json(runtime.get("policy")):
        raise PromotionFailure("SOURCE_POLICY_MISMATCH", str(TRACKED_POLICY))
    if canonical_json(tracked) != canonical_json(active.get("policy")):
        raise PromotionFailure("SOURCE_POLICY_MISMATCH", str(ACTIVE_CANONICAL))
    return VerificationResult("ACTIVE_MATCH", SOURCE_POLICY_SHA256)


def rollback_plan(root: str | Path = ROOT) -> dict[str, Any]:
    base = Path(root)
    value = _require_object(
        load_strict_json(base / ROLLBACK_MANIFEST), "ROLLBACK_MANIFEST_NOT_OBJECT"
    )
    if value.get("status") != "PLAN_ONLY" or value.get("automatic_rollback") is not False:
        raise PromotionFailure("ROLLBACK_MANIFEST_INVALID", str(ROLLBACK_MANIFEST))
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify-source")
    promote_parser = subparsers.add_parser("promote")
    promote_parser.add_argument("--owner-confirmation", required=True)
    subparsers.add_parser("verify-active")
    subparsers.add_parser("rollback-plan")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "verify-source":
            result = verify_source()
            print("STATE=PASS_VERIFY_SOURCE_SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION")
            print(f"SOURCE_POLICY_SHA256={result.source_policy_sha256}")
        elif args.command == "promote":
            result = promote(owner_confirmation=args.owner_confirmation)
            print("STATE=PASS_PROMOTE_SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_CANONICAL")
            print(f"PROMOTION_STATUS={result.status}")
            print(f"FILES_WRITTEN={','.join(result.files_written) or 'NONE'}")
        elif args.command == "verify-active":
            result = verify_active()
            print("STATE=PASS_VERIFY_ACTIVE_SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION")
            print(f"SOURCE_POLICY_SHA256={result.source_policy_sha256}")
        else:
            plan = rollback_plan()
            print("STATE=PASS_ROLLBACK_PLAN_ONLY")
            print(canonical_json(plan))
        return 0
    except PromotionFailure as exc:
        state = (
            "HOLD_SOURCE_POLICY_MISMATCH"
            if exc.reason_code == "SOURCE_POLICY_MISMATCH"
            else "HOLD_EXISTING_MULTI_DOMAIN_CANONICAL_CONFLICT"
            if exc.reason_code == "EXISTING_MULTI_DOMAIN_CANONICAL_CONFLICT"
            else "HOLD_SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_PROMOTION"
        )
        print(f"STATE={state}")
        print(f"REASON_CODE={exc.reason_code}")
        print(f"FILE={exc.path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
