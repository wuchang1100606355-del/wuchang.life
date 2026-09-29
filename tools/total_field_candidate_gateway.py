"""Candidate gateway for Total Field normalization and validation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tools.total_field.xiaoj_fusion_rules import (
    BACKBRAIN_SOURCE,
    CANDIDATE_ONLY_AUTHORITY,
    CLOUD_SOURCE,
    FORBIDDEN_AUTHORITY_CLAIM_KEYS,
    PROTECTED_PATH_PREFIXES,
)


def receive_candidate(candidate: Mapping[str, Any], source: str | None = None) -> dict[str, Any]:
    """Normalize and validate a candidate before it can influence a decision."""

    normalized = _normalize_candidate(candidate, source)
    errors: list[str] = []
    warnings: list[str] = []

    authority = normalized.get("authority")
    if authority != CANDIDATE_ONLY_AUTHORITY:
        errors.append("candidate_authority_must_be_candidate_only")

    authority_claims = _forbidden_authority_claim_paths(candidate)
    if authority_claims:
        errors.append("forbidden_authority_claim:" + ",".join(authority_claims))

    protected_paths = _protected_patch_paths(normalized.get("patch", {}))
    if normalized["source"] in {BACKBRAIN_SOURCE, CLOUD_SOURCE} and protected_paths:
        errors.append("protected_path_rewrite_forbidden:" + ",".join(protected_paths))

    assumptions = _as_list(candidate.get("assumptions") or candidate.get("assumption_register"))
    blocking_assumptions = [
        str(item.get("assumption_id") or item.get("AssumptionId") or index)
        for index, item in enumerate(assumptions)
        if isinstance(item, Mapping) and _assumption_blocks_execution(item)
    ]
    execution_allowed = not blocking_assumptions
    if blocking_assumptions:
        warnings.append("unverified_assumption_blocks_execution:" + ",".join(blocking_assumptions))

    accepted = not errors
    return {
        "accepted": accepted,
        "source": normalized["source"],
        "candidate": normalized,
        "errors": errors,
        "warnings": warnings,
        "execution_allowed": execution_allowed,
    }


def decide_candidates(
    receipts: list[Mapping[str, Any]],
    *,
    acceptance_threshold: float,
    acceptance_criteria: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Choose the best accepted candidate without granting execution authority."""

    accepted = [receipt for receipt in receipts if receipt.get("accepted")]
    executable = [receipt for receipt in accepted if receipt.get("execution_allowed", True)]

    if not executable:
        return {
            "status": "hold",
            "reason": "no_executable_candidate",
            "accepted": False,
            "quality_score": 0.0,
            "candidate": None,
            "candidate_source": None,
            "acceptance_criteria": dict(acceptance_criteria or {}),
        }

    best = max(executable, key=lambda receipt: float(receipt.get("candidate", {}).get("quality_score", 0.0)))
    candidate = dict(best["candidate"])
    quality_score = float(candidate.get("quality_score", 0.0))
    if quality_score < acceptance_threshold:
        return {
            "status": "hold",
            "reason": "quality_below_acceptance_threshold",
            "accepted": False,
            "quality_score": quality_score,
            "candidate": candidate,
            "candidate_source": candidate.get("source"),
            "acceptance_criteria": dict(acceptance_criteria or {}),
        }

    return {
        "status": "selected",
        "reason": "candidate_meets_acceptance_threshold",
        "accepted": True,
        "quality_score": quality_score,
        "candidate": candidate,
        "candidate_source": candidate.get("source"),
        "acceptance_criteria": dict(acceptance_criteria or {}),
    }


def _normalize_candidate(candidate: Mapping[str, Any], source: str | None) -> dict[str, Any]:
    patch = candidate.get("patch")
    if patch is None:
        patch = candidate.get("fields", {})
    if not isinstance(patch, Mapping):
        patch = {"value": patch}

    return {
        "source": str(source or candidate.get("source") or "unknown"),
        "authority": str(candidate.get("authority") or CANDIDATE_ONLY_AUTHORITY),
        "candidate_type": str(candidate.get("candidate_type") or "Candidate"),
        "patch": dict(patch),
        "quality_score": float(candidate.get("quality_score", 0.0)),
        "model": candidate.get("model"),
        "metadata": dict(candidate.get("metadata", {})) if isinstance(candidate.get("metadata"), Mapping) else {},
        "assumptions": _as_list(candidate.get("assumptions") or candidate.get("assumption_register")),
    }


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _protected_patch_paths(patch: Any, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(patch, Mapping):
        for key, value in patch.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if _is_protected_path(path):
                paths.append(path)
            paths.extend(_protected_patch_paths(value, path))
    return sorted(set(paths))


def _is_protected_path(path: str) -> bool:
    normalized = path.lower().replace("-", "_")
    return any(
        normalized == protected or normalized.startswith(protected + ".")
        for protected in PROTECTED_PATH_PREFIXES
    )


def _forbidden_authority_claim_paths(value: Any, prefix: str = "") -> list[str]:
    claims: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = str(key).lower().replace("-", "_")
            path = f"{prefix}.{key}" if prefix else str(key)
            if normalized_key in FORBIDDEN_AUTHORITY_CLAIM_KEYS:
                claims.append(path)
            claims.extend(_forbidden_authority_claim_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            claims.extend(_forbidden_authority_claim_paths(child, f"{prefix}[{index}]"))
    return sorted(set(claims))


def _assumption_blocks_execution(assumption: Mapping[str, Any]) -> bool:
    verified = bool(assumption.get("verified") or assumption.get("Verified"))
    affects = assumption.get("affects") or assumption.get("AffectedD1D8Fields") or []
    irreversible = bool(assumption.get("irreversible") or assumption.get("Irreversible"))
    safety = bool(assumption.get("safety_relevant") or assumption.get("SafetyRelevant"))
    if isinstance(affects, str):
        affects = [affects]
    affects_protected = any(_is_protected_path(str(path)) for path in affects)
    return not verified and (affects_protected or irreversible or safety)

