from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .models import (
    BreakpointReachabilityVerdict,
    CanonicalPath,
    NativeTransitionRule,
    StatePacket8D,
)

SOURCE_REF = "FOUNDER_NATIVE_ADI_RULE_DECLARATION_V1.md#founder-transitions-direction-and-absolute-distance"
ALLOW_REACHABLE = "ALLOW_REACHABLE"
DENY_BREAKPOINT_CROSSED = "DENY_BREAKPOINT_CROSSED"
HOLD_BREAKPOINT_EVIDENCE_INCOMPLETE = "HOLD_BREAKPOINT_EVIDENCE_INCOMPLETE"


class TransitionRuleHold(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class BreakpointReachabilityDenied(TransitionRuleHold):
    pass


def _breakpoint_ref_is_present(value: str | None) -> bool:
    return isinstance(value, str) and bool(value.strip())


def evaluate_breakpoint_reachability(
    origin_state: StatePacket8D,
    candidate_state: StatePacket8D,
    transition_rule: NativeTransitionRule,
) -> BreakpointReachabilityVerdict:
    """Evaluate the Founder V1 hard breakpoint segment boundary."""
    origin_segment_ref = origin_state.breakpoint_segment_ref
    candidate_segment_ref = candidate_state.breakpoint_segment_ref
    breakpoint_policy_ref = transition_rule.breakpoint_policy_ref
    if not _breakpoint_ref_is_present(origin_segment_ref):
        return BreakpointReachabilityVerdict(
            HOLD_BREAKPOINT_EVIDENCE_INCOMPLETE,
            origin_segment_ref,
            candidate_segment_ref,
            breakpoint_policy_ref,
            HOLD_BREAKPOINT_EVIDENCE_INCOMPLETE,
        )
    if not _breakpoint_ref_is_present(candidate_segment_ref):
        return BreakpointReachabilityVerdict(
            HOLD_BREAKPOINT_EVIDENCE_INCOMPLETE,
            origin_segment_ref,
            candidate_segment_ref,
            breakpoint_policy_ref,
            HOLD_BREAKPOINT_EVIDENCE_INCOMPLETE,
        )
    if not _breakpoint_ref_is_present(breakpoint_policy_ref):
        return BreakpointReachabilityVerdict(
            HOLD_BREAKPOINT_EVIDENCE_INCOMPLETE,
            origin_segment_ref,
            candidate_segment_ref,
            breakpoint_policy_ref,
            HOLD_BREAKPOINT_EVIDENCE_INCOMPLETE,
        )
    if origin_segment_ref != candidate_segment_ref:
        return BreakpointReachabilityVerdict(
            DENY_BREAKPOINT_CROSSED,
            origin_segment_ref,
            candidate_segment_ref,
            breakpoint_policy_ref,
            DENY_BREAKPOINT_CROSSED,
        )
    return BreakpointReachabilityVerdict(
        ALLOW_REACHABLE,
        origin_segment_ref,
        candidate_segment_ref,
        breakpoint_policy_ref,
        ALLOW_REACHABLE,
    )


def _enforce_breakpoint_reachability(
    origin_state: StatePacket8D,
    candidate_state: StatePacket8D,
    path: tuple[NativeTransitionRule, ...],
) -> None:
    for rule in path:
        verdict = evaluate_breakpoint_reachability(origin_state, candidate_state, rule)
        if verdict.verdict == DENY_BREAKPOINT_CROSSED:
            raise BreakpointReachabilityDenied(verdict.reason_code)
        if verdict.verdict != ALLOW_REACHABLE:
            raise TransitionRuleHold(verdict.reason_code)


def _rule_is_valid(
    rule: NativeTransitionRule,
    *,
    rule_version: str,
    preconditions: frozenset[str],
    evidence_refs: frozenset[str],
) -> bool:
    """Admit only positive, evidence-backed edges to the reachable graph."""
    return (
        rule.polarity == 1
        and isinstance(rule.step_cost_uint, int)
        and not isinstance(rule.step_cost_uint, bool)
        and rule.step_cost_uint > 0
        and rule.rule_version == rule_version
        and set(rule.preconditions).issubset(preconditions)
        and set(rule.required_evidence_refs).issubset(evidence_refs)
    )


def resolve_canonical_path(
    left: StatePacket8D,
    right: StatePacket8D,
    transition_rules: Iterable[NativeTransitionRule],
) -> CanonicalPath:
    """Resolve the only reachable Founder-canonical simple causal path."""
    if left.native_state_ref == right.native_state_ref:
        if not _breakpoint_ref_is_present(left.breakpoint_segment_ref):
            raise TransitionRuleHold(HOLD_BREAKPOINT_EVIDENCE_INCOMPLETE)
        if not _breakpoint_ref_is_present(right.breakpoint_segment_ref):
            raise TransitionRuleHold(HOLD_BREAKPOINT_EVIDENCE_INCOMPLETE)
        if left.breakpoint_segment_ref != right.breakpoint_segment_ref:
            raise BreakpointReachabilityDenied(DENY_BREAKPOINT_CROSSED)
        return CanonicalPath(())
    if left.rule_version != right.rule_version:
        raise TransitionRuleHold("HOLD_TRANSITION_RULE_MISSING")

    available_preconditions = left.satisfied_preconditions | right.satisfied_preconditions
    evidence_refs = frozenset(left.evidence_digests) | frozenset(right.evidence_digests)
    graph: dict[str, list[NativeTransitionRule]] = defaultdict(list)
    nodes = {left.native_state_ref, right.native_state_ref}
    for rule in transition_rules:
        if _rule_is_valid(
            rule,
            rule_version=right.rule_version,
            preconditions=available_preconditions,
            evidence_refs=evidence_refs,
        ):
            graph[rule.from_state_code].append(rule)
            nodes.update((rule.from_state_code, rule.to_state_code))
    for rules in graph.values():
        rules.sort(key=lambda item: item.transition_rule_id.encode("utf-8"))

    paths: list[tuple[NativeTransitionRule, ...]] = []

    def walk(state_code: str, visited: frozenset[str], path: tuple[NativeTransitionRule, ...]) -> None:
        if len(paths) > 1:
            return
        if state_code == right.native_state_ref:
            paths.append(path)
            return
        if len(path) >= len(nodes):
            return
        for rule in graph.get(state_code, ()):
            if rule.to_state_code in visited:
                continue
            walk(rule.to_state_code, visited | {rule.to_state_code}, path + (rule,))

    walk(left.native_state_ref, frozenset({left.native_state_ref}), ())
    if not paths:
        raise TransitionRuleHold("HOLD_TRANSITION_RULE_MISSING")
    if len(paths) != 1:
        raise TransitionRuleHold("HOLD_CANONICAL_PATH_DIVERGENCE")
    _enforce_breakpoint_reachability(left, right, paths[0])
    return CanonicalPath(paths[0])


def delta_f(
    left: StatePacket8D,
    right: StatePacket8D,
    transition_rules: Iterable[NativeTransitionRule] = (),
) -> int:
    """Return TRANSITION_PATH_DISTANCE, never a time-axis slot difference."""
    return resolve_canonical_path(left, right, transition_rules).total_cost
