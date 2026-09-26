#!/usr/bin/env python3
"""Open-source local-first human need router for XiaoJ.

The router is deterministic and local. It does not call cloud providers,
does not persist raw intent text, and does not grant execution authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "configs/product/w7tp_xiaoj_open_source_human_need_profile_v1.json"


def _load_profile() -> dict[str, Any]:
    value = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    if value.get("schema_version") != "w7tp.xiaoj-open-source-human-need-profile.v1":
        raise ValueError("HOLD_HUMAN_NEED_PROFILE_VERSION")
    return value


def _role_token(value: str) -> str:
    token = (value or "").strip()
    if ":" in token:
        token = token.split(":", 1)[1]
    return token


def normalize_roles(active_role_refs: Sequence[str]) -> list[str]:
    profile = _load_profile()
    aliases = profile["role_aliases"]
    roles: list[str] = []
    for raw in active_role_refs:
        key = aliases.get(_role_token(str(raw)))
        if key and key not in roles:
            roles.append(key)
    return roles


def _score(intent: str, keywords: Iterable[str]) -> tuple[int, list[str]]:
    hits: list[str] = []
    lower = intent.lower()
    for keyword in keywords:
        k = str(keyword)
        if k and k.lower() in lower:
            hits.append(k)
    return len(hits), hits


def route_human_need(
    *,
    active_role_refs: Sequence[str],
    intent: str,
) -> dict[str, Any]:
    """Route one local member intent by explicit active roles and human need."""

    profile = _load_profile()
    roles = normalize_roles(active_role_refs)
    intent_text = str(intent or "").strip()
    intent_sha256 = hashlib.sha256(intent_text.encode("utf-8")).hexdigest()

    base: dict[str, Any] = {
        "schema_version": "w7tp.xiaoj-human-need-route.v1",
        "candidate_only": True,
        "execution_allowed": False,
        "local_only": True,
        "cloud_required": False,
        "enterprise_sso_required": False,
        "paid_service_required": False,
        "kubernetes_required": False,
        "raw_intent_persisted": False,
        "intent_sha256": intent_sha256,
        "active_roles": roles,
    }

    if not roles:
        return {
            **base,
            "state": "HOLD_ROLE_CONTEXT_REQUIRED",
            "reason_code": "NO_EXPLICIT_ACTIVE_ROLE",
            "human_choice_required": True,
            "candidate_options": [],
        }

    if not intent_text:
        options = []
        for role in roles:
            spec = profile["roles"][role]
            default_need = spec["default_need"]
            need = spec["needs"][default_need]
            options.append(
                {
                    "role": role,
                    "role_label": spec["label"],
                    "need": default_need,
                    "need_label": need["label"],
                    "human_outcome": need["human_outcome"],
                }
            )
        return {
            **base,
            "state": "HOLD_HUMAN_NEED_REQUIRED",
            "reason_code": "NO_INTENT_TEXT",
            "human_choice_required": True,
            "candidate_options": options,
        }

    candidates: list[dict[str, Any]] = []
    for role in roles:
        role_spec = profile["roles"][role]
        for need_key, need_spec in role_spec["needs"].items():
            score, hits = _score(intent_text, need_spec.get("keywords", []))
            if score <= 0:
                continue
            candidates.append(
                {
                    "role": role,
                    "role_label": role_spec["label"],
                    "need": need_key,
                    "need_label": need_spec["label"],
                    "score": score,
                    "matched_keyword_count": len(hits),
                    "human_outcome": need_spec["human_outcome"],
                    "capability_refs": list(need_spec.get("capability_refs", [])),
                    "human_confirmation_required": bool(
                        need_spec.get("human_confirmation_required", False)
                    ),
                }
            )

    if not candidates:
        options = []
        for role in roles:
            role_spec = profile["roles"][role]
            default_need = role_spec["default_need"]
            need_spec = role_spec["needs"][default_need]
            options.append(
                {
                    "role": role,
                    "role_label": role_spec["label"],
                    "need": default_need,
                    "need_label": need_spec["label"],
                    "human_outcome": need_spec["human_outcome"],
                }
            )
        return {
            **base,
            "state": "HOLD_HUMAN_NEED_AMBIGUOUS",
            "reason_code": "NO_NEED_MATCH",
            "human_choice_required": True,
            "candidate_options": options,
        }

    candidates.sort(
        key=lambda item: (
            -int(item["score"]),
            str(item["role"]),
            str(item["need"]),
        )
    )
    best_score = int(candidates[0]["score"])
    best = [item for item in candidates if int(item["score"]) == best_score]

    if len(best) != 1:
        return {
            **base,
            "state": "HOLD_ROLE_OR_NEED_CHOICE_REQUIRED",
            "reason_code": "MULTIPLE_EQUAL_NEED_MATCHES",
            "human_choice_required": True,
            "candidate_options": best,
        }

    selected = dict(best[0])
    selected.pop("score", None)
    return {
        **base,
        "state": "PASS_HUMAN_NEED_ROUTE_CANDIDATE",
        "reason_code": "PASS_LOCAL_HUMAN_NEED_ROUTING",
        "human_choice_required": False,
        "selected": selected,
        "next_route": "T019_MEMBER_PRODUCT_ENTRY_CANDIDATE",
    }


__all__ = [
    "normalize_roles",
    "route_human_need",
]
