"""Candidate adapters for the XiaoJ single-8B local stage."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from tools.total_field.xiaoj_fusion_rules import (
    CANDIDATE_ONLY_AUTHORITY,
    CLOUD_FILLABLE_PATHS,
    LOCAL_PRIMARY_MODEL,
    LOCAL_SOURCE,
)


def build_local_candidate(
    user_text: str,
    *,
    context_packets: Mapping[str, Any] | None = None,
    acceptance_criteria: Mapping[str, Any] | None = None,
    quality_score: float | None = None,
) -> dict[str, Any]:
    """Build the only physical local-model candidate."""
    score = _estimate_quality(user_text, acceptance_criteria) if quality_score is None else quality_score
    response = _natural_zh_tw_draft(user_text, context_packets)
    return {
        "source": LOCAL_SOURCE,
        "model": LOCAL_PRIMARY_MODEL["model"],
        "authority": CANDIDATE_ONLY_AUTHORITY,
        "candidate_type": "Candidate",
        "patch": {"response": {"natural_zh_tw": response}},
        "quality_score": float(score),
        "metadata": {
            "physical_model_count": 1,
            "base_model": LOCAL_PRIMARY_MODEL["base_model"],
            "context_length": LOCAL_PRIMARY_MODEL["contextLength"],
        },
        "assumptions": [],
    }


def build_frontbrain_candidate(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Compatibility entrypoint; frontbrain is a logical phase of the one 8B model."""
    return build_local_candidate(*args, **kwargs)


def build_backbrain_candidate(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Fail closed: the prior 1.7B physical backbrain is no longer a core dependency."""
    raise RuntimeError("HOLD_BACKBRAIN_DISABLED_SINGLE_8B")


def open_low_complexity_fillable_paths(local_candidate: Mapping[str, Any]) -> list[str]:
    """Return paths a governed cloud provider may fill when local quality is insufficient."""
    patch = local_candidate.get("patch", {})
    if isinstance(patch, Mapping) and patch.get("response"):
        return ["draft.style_polish", "draft.missing_local_detail"]
    return list(CLOUD_FILLABLE_PATHS)


def _natural_zh_tw_draft(user_text: str, context_packets: Mapping[str, Any] | None) -> str:
    context_note = "，並已依總場上下文約束整理" if context_packets else ""
    text = user_text.strip()
    if not text:
        return "已建立本地候選回答。"
    return f"已完成本地候選：{text}{context_note}。"


def _estimate_quality(user_text: str, acceptance_criteria: Mapping[str, Any] | None) -> float:
    threshold = float((acceptance_criteria or {}).get("quality_threshold", 0.8))
    if len(user_text.strip()) >= 12:
        return min(0.95, threshold + 0.05)
    return max(0.2, threshold - 0.35)
