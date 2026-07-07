"""Member intent precheck persona fallback.

Rule:
- member intent analysis is a pre-processing layer
- it is fully anthropomorphic for member-facing output
- unsupported / unexecutable intent never exposes internal gates
- direct fallback:
  這個我不懂，我只是個菜鳥，我幫你問店長或學長
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence


FALLBACK_MESSAGE = "這個我不懂，我只是個菜鳥，我幫你問店長或學長"

UNEXECUTABLE_ACTIONS = {
    "db_write",
    "database_write",
    "deploy",
    "restart",
    "reboot",
    "router_write",
    "payment_capture",
    "formal_activation",
    "production_activation",
    "create_container",
    "create_live_url",
    "create_live_route",
    "delete",
    "restore",
    "git_clean",
    "docker_prune",
    "secret_request",
    "member_plaintext_request",
    "illegal_action",
    "unsafe_action",
    "unknown_authority_action",
}

EXECUTABLE_HINTS = {
    "menu_recommendation",
    "member_registration_candidate",
    "cafe_business_onboarding_candidate",
    "order_draft",
    "question_answer",
    "support_request",
    "owner_admin_review_request",
    "total_field_candidate_request",
}


@dataclass(frozen=True)
class MemberIntentPrecheckResult:
    state: str
    decision: str
    member_facing_message: str
    internal_reason: str
    next_action: str
    persona: str = "rookie_shop_assistant"

    def as_dict(self) -> Dict[str, str]:
        return {
            "STATE": self.state,
            "decision": self.decision,
            "member_facing_message": self.member_facing_message,
            "internal_reason": self.internal_reason,
            "next_action": self.next_action,
            "persona": self.persona,
        }


def _normalize_actions(actions: Sequence[str] | None) -> set[str]:
    return {
        str(action).strip().lower().replace("-", "_")
        for action in (actions or [])
        if str(action).strip()
    }


def _text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(f"{k}={v}" for k, v in sorted(value.items()))
    return str(value or "")


def _detect_text_risk(text: str) -> str:
    lowered = text.lower()

    risky_fragments = {
        "deploy": "deploy_requested",
        "restart": "restart_requested",
        "reboot": "reboot_requested",
        "db write": "db_write_requested",
        "database": "database_write_or_read_boundary",
        "router": "router_write_boundary",
        "payment": "payment_capture_boundary",
        "刪": "delete_boundary",
        "刪除": "delete_boundary",
        "復原": "restore_boundary",
        "restore": "restore_boundary",
        "正式啟用": "formal_activation_boundary",
        "正式營運": "formal_activation_boundary",
        "金流": "payment_capture_boundary",
        "密鑰": "secret_boundary",
        "token": "secret_boundary",
        "password": "secret_boundary",
        "會員明文": "member_plaintext_boundary",
    }

    for fragment, reason in risky_fragments.items():
        if fragment in lowered:
            return reason

    return ""


def precheck_member_intent(
    *,
    intent_text: str,
    requested_actions: Sequence[str] | None = None,
    context: Mapping[str, Any] | None = None,
) -> Dict[str, str]:
    """Return a member-facing precheck decision.

    The member-facing fallback never says technical refusal.
    Internal reason stays available for Total Field / redteam.
    """
    actions = _normalize_actions(requested_actions)
    blocked_actions = sorted(actions & UNEXECUTABLE_ACTIONS)
    text_reason = _detect_text_risk(intent_text)
    context_data = dict(context or {})

    if context_data.get("force_unexecutable") is True:
      return MemberIntentPrecheckResult(
          state="HOLD_MEMBER_INTENT_PRECHECK_PERSONA_ESCALATION",
          decision="HOLD",
          member_facing_message=FALLBACK_MESSAGE,
          internal_reason="force_unexecutable",
          next_action="ASK_STORE_MANAGER_OR_SENIOR",
      ).as_dict()

    if blocked_actions:
        return MemberIntentPrecheckResult(
            state="HOLD_MEMBER_INTENT_PRECHECK_PERSONA_ESCALATION",
            decision="HOLD",
            member_facing_message=FALLBACK_MESSAGE,
            internal_reason="blocked_actions=" + ",".join(blocked_actions),
            next_action="ASK_STORE_MANAGER_OR_SENIOR",
        ).as_dict()

    if text_reason:
        return MemberIntentPrecheckResult(
            state="HOLD_MEMBER_INTENT_PRECHECK_PERSONA_ESCALATION",
            decision="HOLD",
            member_facing_message=FALLBACK_MESSAGE,
            internal_reason=text_reason,
            next_action="ASK_STORE_MANAGER_OR_SENIOR",
        ).as_dict()

    if actions and not actions <= EXECUTABLE_HINTS:
        unknown = sorted(actions - EXECUTABLE_HINTS)
        return MemberIntentPrecheckResult(
            state="HOLD_MEMBER_INTENT_PRECHECK_PERSONA_ESCALATION",
            decision="HOLD",
            member_facing_message=FALLBACK_MESSAGE,
            internal_reason="unknown_actions=" + ",".join(unknown),
            next_action="ASK_STORE_MANAGER_OR_SENIOR",
        ).as_dict()

    return MemberIntentPrecheckResult(
        state="PASS_MEMBER_INTENT_PRECHECK",
        decision="PASS_CANDIDATE",
        member_facing_message="我先幫你整理成可以讓店長確認的候選草稿。",
        internal_reason="member_intent_is_candidate_executable",
        next_action="TOTAL_FIELD_CANDIDATE_FLOW",
    ).as_dict()


def member_facing_reply_for_unexecutable_intent() -> str:
    return FALLBACK_MESSAGE
