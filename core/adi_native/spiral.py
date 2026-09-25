from __future__ import annotations

from collections import defaultdict
from typing import Callable, Iterable

from .distance import (
    BreakpointReachabilityDenied,
    DENY_BREAKPOINT_CROSSED,
    TransitionRuleHold,
    delta_f as transition_path_distance_f,
    resolve_canonical_path,
)
from .models import (
    DirectSlotConfig,
    NativeLookupReceipt,
    NativeSpiralShell,
    NativeTransitionRule,
    StatePacket8D,
)

SOURCE_REF = "FOUNDER_NATIVE_ADI_RULE_DECLARATION_V1.md#shells-and-native-spiral"


def _hex_bytes(value: str) -> bytes:
    normalized = value.lower()
    if normalized != value or len(normalized) % 2:
        raise ValueError("STATE_ROOT_MUST_BE_LOWERCASE_EVEN_HEX")
    try:
        return bytes.fromhex(normalized)
    except ValueError as exc:
        raise ValueError("STATE_ROOT_MUST_BE_LOWERCASE_HEX") from exc


def order_key_f(
    origin: StatePacket8D,
    candidate: StatePacket8D,
    transition_rules: Iterable[NativeTransitionRule],
):
    path = resolve_canonical_path(origin, candidate, transition_rules)
    return (
        tuple(value.encode("utf-8") for value in path.transition_rule_ids),
        tuple(value.encode("utf-8") for value in path.direction_codes),
        candidate.logical_time,
        _hex_bytes(candidate.state_root),
    )


def omega_f(
    origin: StatePacket8D,
    shell: Iterable[StatePacket8D],
    transition_rules: Iterable[NativeTransitionRule],
) -> tuple[StatePacket8D, ...]:
    rules = tuple(transition_rules)
    return tuple(sorted(shell, key=lambda item: order_key_f(origin, item, rules)))


def enumerate_shells(
    origin: StatePacket8D,
    candidates: Iterable[StatePacket8D],
    transition_rules: Iterable[NativeTransitionRule],
) -> tuple[NativeSpiralShell, ...]:
    """Group reachable candidates into TRANSITION_PATH_DISTANCE shells."""
    rules = tuple(transition_rules)
    grouped: dict[int, list[StatePacket8D]] = defaultdict(list)
    denied_count = 0
    for candidate in candidates:
        try:
            distance = transition_path_distance_f(origin, candidate, rules)
        except BreakpointReachabilityDenied:
            denied_count += 1
            continue
        grouped[distance].append(candidate)
    if not grouped and denied_count:
        raise BreakpointReachabilityDenied(DENY_BREAKPOINT_CROSSED)
    return tuple(
        NativeSpiralShell(
            radius,
            omega_f(origin, grouped[radius], rules),
            "AUTHORITATIVE_EXACT_SHELL" if radius == 0 else "RECONSTRUCTION_CANDIDATE_ONLY",
        )
        for radius in sorted(grouped)
    )


def evidence_closure_stop(
    origin: StatePacket8D,
    candidates: Iterable[StatePacket8D],
    transition_rules: Iterable[NativeTransitionRule],
    *,
    authoritative_parent_state_root: str,
    total_field_validate: Callable[[StatePacket8D], StatePacket8D | str],
    query_budget: int,
) -> NativeLookupReceipt:
    """Stop at the first fully checked shell with one evidence-closed fixed point."""
    from .verifier import evidence_closed_f

    rules = tuple(transition_rules)
    try:
        shells = enumerate_shells(origin, candidates, rules)
    except TransitionRuleHold as exc:
        return NativeLookupReceipt(exc.code, None, None, origin.state_root)

    examined = 0
    for shell in shells:
        fixed_points: list[StatePacket8D] = []
        for candidate in shell.candidates:
            examined += 1
            if examined > query_budget:
                return NativeLookupReceipt(
                    "HOLD_QUERY_BUDGET_EXCEEDED",
                    None,
                    None,
                    origin.state_root,
                    {"partial_pass": False, "examined": examined, "budget": query_budget},
                )
            closure = evidence_closed_f(
                origin,
                candidate,
                rules,
                authoritative_parent_state_root=authoritative_parent_state_root,
            )
            if closure.state != "PASS":
                continue
            validated = total_field_validate(candidate)
            validated_root = validated.state_root if isinstance(validated, StatePacket8D) else validated
            if validated_root == candidate.state_root:
                fixed_points.append(candidate)
        if len(fixed_points) > 1:
            return NativeLookupReceipt(
                "HOLD_CONSENSUS_DIVERGENCE",
                shell.radius,
                None,
                origin.state_root,
                {"fixed_point_count": len(fixed_points)},
            )
        if len(fixed_points) == 1:
            candidate = fixed_points[0]
            return NativeLookupReceipt(
                "UNIQUE_EVIDENCE_CLOSED_FIXED_POINT",
                shell.radius,
                candidate.state_root,
                origin.state_root,
                {"examined": examined, "stop_immediately": True},
            )
    return NativeLookupReceipt(
        "HOLD_TRANSITION_RULE_MISSING",
        None,
        None,
        origin.state_root,
        {"reason": "NO_EVIDENCE_CLOSED_FIXED_POINT"},
    )
