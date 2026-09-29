"""Render one natural Traditional Chinese human-facing response."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def render_human_response(decision: Mapping[str, Any]) -> str:
    """Return exactly one user-facing Traditional Chinese response string."""

    candidate = decision.get("candidate")
    if decision.get("accepted") and isinstance(candidate, Mapping):
        text = _extract_response_text(candidate.get("patch", {}))
        if text:
            return _one_line(text)
        return "已完成，候選結果已通過總場驗收。"

    reason = str(decision.get("reason") or "目前候選未達驗收標準")
    if reason == "quality_below_acceptance_threshold":
        return "尚未完成，候選品質未達驗收標準。"
    if reason == "no_executable_candidate":
        return "尚未完成，沒有可進入執行的已驗證候選。"
    return "尚未完成，總場已保留候選但未裁決通過。"


def _extract_response_text(patch: Any) -> str:
    if isinstance(patch, Mapping):
        response = patch.get("response")
        if isinstance(response, Mapping):
            text = response.get("natural_zh_tw")
            if isinstance(text, str):
                return text
        text = patch.get("natural_zh_tw")
        if isinstance(text, str):
            return text
        draft = patch.get("draft")
        if isinstance(draft, Mapping):
            text = draft.get("style_polish") or draft.get("continuation")
            if isinstance(text, str):
                return text
    return ""


def _one_line(text: str) -> str:
    return " ".join(part.strip() for part in text.splitlines() if part.strip())

