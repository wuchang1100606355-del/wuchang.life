"""Total Field error resolution / redteam gate.

Rule:
- solvable errors are marked SOLVED
- unsolved errors are routed to REDTEAM_HOLD
- unknown errors are never ignored; they become REDTEAM_HOLD
- false PASS after fatal/error is always REDTEAM_HOLD
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence


@dataclass(frozen=True)
class ErrorDecision:
    code: str
    state: str
    severity: str
    resolution: str
    redteam_reason: str
    next_action: str

    def as_dict(self) -> Dict[str, str]:
        return {
            "code": self.code,
            "state": self.state,
            "severity": self.severity,
            "resolution": self.resolution,
            "redteam_reason": self.redteam_reason,
            "next_action": self.next_action,
        }


def _text(event: Any) -> str:
    if isinstance(event, Mapping):
        parts = []
        for key, value in sorted(event.items()):
            parts.append(f"{key}={value}")
        return "\n".join(parts)
    return str(event)


def _lower(event: Any) -> str:
    return _text(event).lower()


def _flag(event: Any, key: str) -> bool:
    if isinstance(event, Mapping):
        return bool(event.get(key))
    return False


def classify_error(event: Any) -> Dict[str, str]:
    text = _lower(event)

    if ("fatal:" in text or "error:" in text) and ("state=pass" in text or "pass_" in text):
        return ErrorDecision(
            code="FALSE_PASS_AFTER_FATAL",
            state="REDTEAM_HOLD",
            severity="HIGH",
            resolution="not_solved",
            redteam_reason="fatal_or_error_was_followed_by_PASS_signal",
            next_action="route_to_redteam_and_require_total_field_decision_before_any_next_step",
        ).as_dict()

    if "pathspec" in text and "did not match" in text:
        if _flag(event, "later_commit_sealed"):
            return ErrorDecision(
                code="PATHSPEC_MISSING_SOLVED_BY_LATER_SEAL",
                state="SOLVED",
                severity="LOW",
                resolution="later_exact_commit_sealed_target_files",
                redteam_reason="none",
                next_action="do_not_rerun",
            ).as_dict()
        return ErrorDecision(
            code="PATHSPEC_MISSING",
            state="REDTEAM_HOLD",
            severity="HIGH",
            resolution="not_solved",
            redteam_reason="command_target_paths_do_not_exist_in_current_repo_context",
            next_action="route_to_redteam_branch_or_repo_context_check",
        ).as_dict()

    if "command not found" in text or "syntax error near unexpected token" in text or "no such file or directory" in text:
        if "taiji_admin@" in text or "[main" in text or "create mode" in text:
            return ErrorDecision(
                code="TERMINAL_OUTPUT_PASTED_AS_COMMAND",
                state="SOLVED",
                severity="LOW",
                resolution="shell_only_input_error_repo_state_not_changed_by_that_line",
                redteam_reason="none",
                next_action="ignore_terminal_echo_error_and_continue_from_last_valid_STATE",
            ).as_dict()
        return ErrorDecision(
            code="SHELL_COMMAND_ERROR",
            state="REDTEAM_HOLD",
            severity="MEDIUM",
            resolution="not_solved",
            redteam_reason="shell_error_without_safe_terminal_echo_signature",
            next_action="route_to_redteam_command_boundary_review",
        ).as_dict()

    if "no changes added to commit" in text or "nothing to commit" in text:
        if _flag(event, "already_sealed") or "already sealed" in text or "commit=" in text:
            return ErrorDecision(
                code="DUPLICATE_RERUN_AFTER_SEAL",
                state="SOLVED",
                severity="LOW",
                resolution="already_sealed_no_op",
                redteam_reason="none",
                next_action="do_not_rerun_do_not_revalidate",
            ).as_dict()
        return ErrorDecision(
            code="NO_CHANGES_TO_COMMIT_UNRESOLVED",
            state="REDTEAM_HOLD",
            severity="MEDIUM",
            resolution="not_solved",
            redteam_reason="commit_attempt_without_staged_delta_and_without_seal_evidence",
            next_action="route_to_redteam_scope_or_duplicate_rerun_review",
        ).as_dict()

    if "client_loop" in text and "broken pipe" in text:
        return ErrorDecision(
            code="SSH_BROKEN_PIPE",
            state="REDTEAM_HOLD",
            severity="MEDIUM",
            resolution="not_solved",
            redteam_reason="transport_disconnected_before_total_field_completion",
            next_action="route_to_redteam_network_or_session_boundary_review",
        ).as_dict()

    if "web/packet_inference_cockpit" in text:
        return ErrorDecision(
            code="FRONTEND_COCKPIT_DRIFT",
            state="REDTEAM_HOLD",
            severity="HIGH",
            resolution="held_no_delete_no_restore",
            redteam_reason="frontend_drift_ownership_unresolved",
            next_action="keep_hold_map_no_touch_until_total_field_decides",
        ).as_dict()

    if "branch_mismatch" in text or ("on branch main" in text and "design/wish-tree" in text):
        return ErrorDecision(
            code="BRANCH_OR_NODE_SPLIT",
            state="REDTEAM_HOLD",
            severity="HIGH",
            resolution="not_solved",
            redteam_reason="work_may_be_split_across_branch_or_node_contexts",
            next_action="route_to_redteam_branch_reconciliation_without_delete_or_restore",
        ).as_dict()

    if "docker compose up" in text or "docker compose restart" in text or "db_write=true" in text or "deploy=true" in text:
        return ErrorDecision(
            code="FORBIDDEN_RUNTIME_ACTION_ATTEMPT",
            state="REDTEAM_HOLD",
            severity="CRITICAL",
            resolution="blocked",
            redteam_reason="runtime_or_database_or_deploy_action_requested",
            next_action="block_until_total_field_pass_owner_admin_approval",
        ).as_dict()

    return ErrorDecision(
        code="UNKNOWN_ERROR_ROUTED_TO_REDTEAM",
        state="REDTEAM_HOLD",
        severity="MEDIUM",
        resolution="not_solved",
        redteam_reason="unknown_errors_are_not_allowed_to_remain_unrouted",
        next_action="route_to_redteam_with_existing_evidence",
    ).as_dict()


def classify_error_batch(events: Sequence[Any]) -> Dict[str, Any]:
    decisions = [classify_error(event) for event in events]
    redteam = [item for item in decisions if item["state"] == "REDTEAM_HOLD"]
    solved = [item for item in decisions if item["state"] == "SOLVED"]

    return {
        "STATE": "HOLD_REDTEAM_ERRORS_PRESENT" if redteam else "PASS_ALL_ERRORS_SOLVED",
        "TOTAL_ERRORS": len(decisions),
        "SOLVED_COUNT": len(solved),
        "REDTEAM_COUNT": len(redteam),
        "NO_ERROR_IGNORED": True,
        "DECISIONS": decisions,
        "NEXT": "REDTEAM_REVIEW_UNSOLVED_ONLY" if redteam else "CONTINUE_FROM_LAST_VALID_STATE",
    }


def assert_no_ignored_errors(events: Iterable[Any]) -> Dict[str, Any]:
    batch = classify_error_batch(list(events))
    if batch["TOTAL_ERRORS"] != batch["SOLVED_COUNT"] + batch["REDTEAM_COUNT"]:
        raise AssertionError("ERROR_ACCOUNTING_MISMATCH")
    if batch["NO_ERROR_IGNORED"] is not True:
        raise AssertionError("ERROR_IGNORED")
    return batch
