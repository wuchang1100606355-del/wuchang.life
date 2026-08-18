"""Candidate-only skill bridge for the Ollama XiaoJ Total Field layer.

This module intentionally performs no external side effects. A skill can only
return evidence or a candidate fragment, and every unsafe or unavailable path
returns HOLD.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "manifests" / "ollama_xiaoj_total_field_v0_1" / "skill_manifest.schema.json"

FORBIDDEN_SKILL_OUTPUT_KEYS = {
    "ALLOW",
    "TFS",
    "TFID",
    "committed",
    "commit",
    "canonical_pointer",
    "pointer",
    "total_field_hash",
    "Total Field Hash",
}


class SkillBridgeError(ValueError):
    """Raised when a skill manifest is malformed."""


def load_skill_manifest(path: str | Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    manifest_path = Path(path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_skill_manifest(data)
    return data


def validate_skill_manifest(data: Mapping[str, Any]) -> None:
    if data.get("mode") != "candidate_only_skill_manifest":
        raise SkillBridgeError("skill manifest must be candidate_only_skill_manifest")
    if data.get("credential_material_allowed") is not False:
        raise SkillBridgeError("credential material must not be allowed")
    if data.get("db_write") is not False:
        raise SkillBridgeError("db_write must be false")
    if data.get("deploy") is not False:
        raise SkillBridgeError("deploy must be false")
    if data.get("router_write") is not False:
        raise SkillBridgeError("router_write must be false")

    skills = data.get("authorized_skills")
    if not isinstance(skills, list) or not skills:
        raise SkillBridgeError("authorized_skills must be a non-empty list")

    for skill in skills:
        if not isinstance(skill, dict):
            raise SkillBridgeError("authorized skill entries must be objects")
        if not skill.get("id"):
            raise SkillBridgeError("authorized skill missing id")
        if skill.get("enabled") is not True:
            raise SkillBridgeError(f"authorized skill disabled: {skill.get('id')}")
        if skill.get("output_kind") not in {"Evidence", "Candidate"}:
            raise SkillBridgeError(f"unsafe output_kind for {skill.get('id')}")
        forbidden = set(skill.get("forbidden_outputs") or [])
        if not FORBIDDEN_SKILL_OUTPUT_KEYS.issubset(forbidden):
            raise SkillBridgeError(f"skill missing forbidden output declarations: {skill.get('id')}")


def _safe_text(value: Any, limit: int = 2000) -> str:
    text = str(value)
    secret_markers = [
        "BEGIN PRIVATE KEY",
        "private_key",
        "access_token",
        "refresh_token",
        "id_token",
        "password",
        "passwd",
        "Authorization:",
        "Bearer ",
    ]
    lowered = text.lower()
    if any(marker.lower() in lowered for marker in secret_markers):
        return "[REDACTED_SECRET_OR_MEMBER_PLAINTEXT]"
    return text[:limit]


class OllamaTotalFieldSkillBridge:
    """Loads a local allowlist and invokes side-effect-free skill handlers."""

    def __init__(
        self,
        manifest_path: str | Path = DEFAULT_MANIFEST,
        *,
        credential_available: bool = False,
    ) -> None:
        self.manifest_path = Path(manifest_path)
        self.credential_available = credential_available
        self.manifest = load_skill_manifest(self.manifest_path)
        self._skills = {item["id"]: dict(item) for item in self.manifest["authorized_skills"]}

    @property
    def authorized_skill_ids(self) -> set[str]:
        return set(self._skills)

    def invoke(self, skill_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        skill = self._skills.get(skill_id)
        if not skill:
            return self._hold("HOLD_UNAUTHORIZED_SKILL", skill_id)
        if skill.get("credential_required") and not self.credential_available:
            return self._hold("HOLD_NO_CREDENTIAL", skill_id)

        handler = getattr(self, f"_skill_{skill_id}", None)
        if handler is None:
            return self._hold("HOLD_SKILL_HANDLER_MISSING", skill_id)

        result = handler(payload)
        return self._guard_skill_output(skill_id, skill, result)

    def _hold(self, state: str, skill_id: str) -> dict[str, Any]:
        return {
            "state": state,
            "skill_id": skill_id,
            "output_kind": "Evidence",
            "evidence": {"reason": state},
            "candidate": None,
        }

    def _guard_skill_output(
        self,
        skill_id: str,
        skill: Mapping[str, Any],
        result: Mapping[str, Any],
    ) -> dict[str, Any]:
        text = json.dumps(result, ensure_ascii=False, sort_keys=True)
        bad = [key for key in FORBIDDEN_SKILL_OUTPUT_KEYS if key in text]
        if bad:
            return {
                "state": "HOLD_SKILL_FORBIDDEN_OUTPUT",
                "skill_id": skill_id,
                "output_kind": "Evidence",
                "evidence": {"forbidden": sorted(bad)},
                "candidate": None,
            }
        output_kind = skill.get("output_kind")
        guarded = {
            "state": "SKILL_OUTPUT_CANDIDATE_ONLY",
            "skill_id": skill_id,
            "output_kind": output_kind,
            "evidence": result.get("evidence") if isinstance(result, dict) else None,
            "candidate": result.get("candidate") if output_kind == "Candidate" else None,
        }
        if output_kind == "Evidence":
            guarded["candidate"] = None
        return guarded

    def _skill_evidence_echo(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "evidence": {
                "source": "evidence_echo",
                "input_preview": _safe_text(payload.get("text") or payload.get("prompt") or ""),
            }
        }

    def _skill_candidate_outline(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        intent = _safe_text(payload.get("intent") or payload.get("prompt") or "candidate_outline")
        return {
            "candidate": {
                "kind": "skill_candidate_fragment",
                "intent": intent,
                "decision": "CANDIDATE_ONLY",
            },
            "evidence": {"source": "candidate_outline"},
        }

    def _skill_total_field_policy_check(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        text = _safe_text(payload)
        flags = []
        for marker in ["committed", "ALLOW", "TFS", "TFID", "Total Field Hash", "total_field_hash"]:
            if marker in text:
                flags.append(marker)
        return {
            "evidence": {
                "source": "total_field_policy_check",
                "unsafe_markers": flags,
                "safe_for_candidate": not flags,
            }
        }
