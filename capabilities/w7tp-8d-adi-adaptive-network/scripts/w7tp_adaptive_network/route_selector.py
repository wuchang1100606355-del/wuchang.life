from __future__ import annotations

from typing import Any

from .policy_engine import evaluate_policy


CHAIN_STEPS = ("source", "interface", "route", "target", "service", "application", "response")


def select_route(
    intent: dict[str, Any],
    paths: list[dict[str, Any]],
    verification: dict[str, bool] | None = None,
) -> dict[str, Any]:
    decision = evaluate_policy(intent, paths)
    verification = verification or {}
    chain = {step: bool(verification.get(step, False)) for step in CHAIN_STEPS}
    selected = decision.get("selected_path") is not None
    verified = selected and all(chain.values())
    return {
        **decision,
        "intent_id": intent.get("intent_id", "LOCALIZED_UNKNOWN"),
        "source_node": intent.get("source_node", "LOCALIZED_UNKNOWN"),
        "target_node": intent.get("target_node", "LOCALIZED_UNKNOWN"),
        "service_identity": intent.get("service_identity", "LOCALIZED_UNKNOWN"),
        "end_to_end_chain": chain,
        "end_to_end_verified": verified,
        "decision_state": (
            "VERIFIED_CANDIDATE"
            if verified
            else ("SELECTED_CANDIDATE_NOT_END_TO_END_VERIFIED" if selected else decision["decision"])
        ),
        "authority_scope": "CANDIDATE_D8_DECISION_ONLY",
    }

