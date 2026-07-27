from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .models import CanonicalPath, NativeTransitionRule, StatePacket8D

SOURCE_REF = "FOUNDER_NATIVE_ADI_RULE_DECLARATION_V1.md#founder-transitions-direction-and-absolute-distance"


class TransitionRuleHold(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _rule_is_valid(
    rule: NativeTransitionRule,
    *,
    rule_version: str,
    preconditions: frozenset[str],
    evidence_refs: frozenset[str],
) -> bool:
    return (
        rule.rule_version == rule_version
        and set(rule.preconditions).issubset(preconditions)
        and set(rule.required_evidence_refs).issubset(evidence_refs)
    )


def resolve_canonical_path(
    left: StatePacket8D,
    right: StatePacket8D,
    transition_rules: Iterable[NativeTransitionRule],
) -> CanonicalPath:
    """Resolve the only valid Founder-canonical simple causal path."""
    if left.native_state_ref == right.native_state_ref:
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
    return CanonicalPath(paths[0])


def delta_f(
    left: StatePacket8D,
    right: StatePacket8D,
    transition_rules: Iterable[NativeTransitionRule] = (),
) -> int:
    # source_ref: delta_F is the integer cost sum of the unique canonical path.
    return resolve_canonical_path(left, right, transition_rules).total_cost
