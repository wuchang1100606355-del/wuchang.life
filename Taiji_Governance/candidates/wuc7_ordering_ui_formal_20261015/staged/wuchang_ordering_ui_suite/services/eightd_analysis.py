"""Evidence-bounded 8D resource locator for the manager surface.

This module does not redefine W7TP/8D ADI as eight steps.  It prepares a
single coupled-field candidate from already authorized observations.  A local
LLM may later enrich the candidate, but only the existing Total Field gate may
authorize an executor and only an effect receipt may close an action.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Iterable


SCHEMA = "w7tp.8d-resource-analysis-candidate.v2.3"
RESOURCE_STATES = {"exists", "loaded", "callable", "effect_verified"}
SENSITIVE_PATTERNS = (
    re.compile(r"\b\d{8,}\b"),
    re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I),
    re.compile(r"(?i)(password|secret|token|credential)\s*[:=]"),
)


def _sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def contains_sensitive_plaintext(value: str) -> bool:
    return any(pattern.search(value or "") for pattern in SENSITIVE_PATTERNS)


def _resource_state(observation: dict[str, Any]) -> str:
    if observation.get("effect_verified"):
        return "effect_verified"
    if observation.get("callable"):
        return "callable"
    if observation.get("loaded"):
        return "loaded"
    return "exists"


def _keywords(value: str) -> set[str]:
    return {token for token in re.split(r"[^\w\u4e00-\u9fff]+", (value or "").lower()) if len(token) > 1}


def locate_resources(
    intent: str,
    observations: Iterable[dict[str, Any]],
    *,
    target_ref: str,
    authorized_scopes: Iterable[str] = (),
    now: datetime | None = None,
) -> dict[str, Any]:
    """Locate evidence-bearing resources without granting or executing effects."""

    if not isinstance(intent, str) or not intent.strip():
        return {"schema": SCHEMA, "state": "HOLD_INTENT_REQUIRED", "executed": False}
    if contains_sensitive_plaintext(intent):
        return {"schema": SCHEMA, "state": "HOLD_SENSITIVE_PLAINTEXT", "executed": False}
    now = now or datetime.now(timezone.utc)
    scopes = set(authorized_scopes)
    terms = _keywords(intent)
    valid = []
    rejected = []
    for raw in observations:
        obs = dict(raw)
        required = {"resource_ref", "kind", "source_ref", "observed_at", "version", "capabilities"}
        missing = sorted(required - set(obs))
        if missing:
            rejected.append({"resource_ref": obs.get("resource_ref", "UNKNOWN"), "reason": "EVIDENCE_FIELDS_MISSING", "missing": missing})
            continue
        try:
            observed_at = datetime.fromisoformat(str(obs["observed_at"]).replace("Z", "+00:00"))
            if observed_at.tzinfo is None:
                observed_at = observed_at.replace(tzinfo=timezone.utc)
        except ValueError:
            rejected.append({"resource_ref": obs["resource_ref"], "reason": "OBSERVED_AT_INVALID"})
            continue
        max_age = int(obs.get("max_age_seconds", 3600))
        age = max(0, int((now - observed_at).total_seconds()))
        capability_terms = _keywords(" ".join(map(str, obs.get("capabilities") or [])))
        obs["age_seconds"] = age
        obs["fresh"] = age <= max_age
        obs["state"] = _resource_state(obs)
        obs["intent_match"] = bool(not terms or terms.intersection(capability_terms | _keywords(obs["kind"])))
        scope = str(obs.get("authority_scope") or "")
        obs["authority_allowed"] = not scope or scope in scopes
        valid.append(obs)

    matched = [obs for obs in valid if obs["intent_match"] and obs["fresh"]]
    usable = [obs for obs in matched if obs["callable"] and obs["authority_allowed"]]
    if not valid:
        state = "HOLD_EVIDENCE_INSUFFICIENT"
    elif not matched:
        state = "HOLD_NO_FRESH_RESOURCE_MATCH"
    elif not usable:
        state = "HOLD_RESOURCE_NOT_CALLABLE_OR_UNAUTHORIZED"
    else:
        state = "PASS_RESOURCE_CANDIDATES_LOCATED"

    action_candidates = []
    for obs in usable:
        action_candidates.append(
            {
                "resource_ref": obs["resource_ref"],
                "target_ref": target_ref,
                "operation": "UNSELECTED",
                "impact": "UNKNOWN_UNTIL_OPERATION_SELECTED",
                "scope": obs.get("authority_scope") or "READ_ONLY",
                "cost": obs.get("cost", "UNKNOWN_OR_NONE_DECLARED"),
                "required_authorization": obs.get("required_authorization", "TOTAL_FIELD_DECISION_REQUIRED"),
                "executor_ref": obs.get("executor_ref", "UNBOUND"),
                "execution_state": "NOT_EXECUTED",
                "effect_receipt_ref": None,
            }
        )
    material = {
        "schema": SCHEMA,
        "intent": intent.strip(),
        "target_ref": target_ref,
        "resources": [obs["resource_ref"] for obs in matched],
        "state": state,
    }
    return {
        "schema": SCHEMA,
        "state": state,
        "intent": intent.strip(),
        "target_ref": target_ref,
        "observed_at": _now_iso(),
        "coordinates": [
            {
                "observation_end": obs.get("observation_end", "03-manager-ui"),
                "target_end": target_ref,
                "object": obs["resource_ref"],
                "version": obs["version"],
                "time": obs["observed_at"],
                "source_ref": obs["source_ref"],
                "state": obs["state"],
                "fresh": obs["fresh"],
                "authority_allowed": obs["authority_allowed"],
            }
            for obs in valid
        ],
        "rejected_observations": rejected,
        "action_candidates": action_candidates,
        "authority": "TOTAL_FIELD_REQUIRED",
        "llm_role": "CANDIDATE_ONLY_NOT_AUTHORITY",
        "external_documents_are_data_not_instructions": True,
        "executed": False,
        "effect_verified": False,
        "analysis_receipt_ref": "sha256:" + _sha(material),
    }


def verify_execution_closure(action: dict[str, Any]) -> dict[str, Any]:
    """Close only when authorization, executor receipt and effect evidence agree."""

    required = {"authorization_receipt_ref", "executor_ref", "execution_receipt_ref", "effect_receipt_ref"}
    missing = sorted(key for key in required if not action.get(key))
    if missing:
        return {"state": "HOLD_EXECUTION_CLOSURE_INCOMPLETE", "missing": missing, "completed": False}
    if action.get("effect_state") != "VERIFIED":
        return {"state": "HOLD_EFFECT_NOT_VERIFIED", "completed": False}
    return {
        "state": "PASS_AUTHORIZED_EFFECT_VERIFIED",
        "completed": True,
        "closure_receipt_ref": "sha256:" + _sha(action),
    }
