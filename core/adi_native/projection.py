from __future__ import annotations

from .models import (
    DirectSlotConfig,
    DimensionBoundaryFacts,
    MetricSignature,
    NativeTransitionRule,
    StateCrossSection,
    StatePacket8D,
)

SOURCE_REF = "FOUNDER_NATIVE_ADI_RULE_DECLARATION_V1.md"


def project_8d_state(packet: StatePacket8D) -> tuple[int, ...]:
    """X_F: exact integer codes already resolved by the Founder rule table."""
    if len(packet.dimensions) != 8:
        raise ValueError("BLOCK_INVALID_8D_DIMENSION_COUNT")
    if any(not isinstance(value, int) or isinstance(value, bool) for value in packet.dimensions):
        raise ValueError("BLOCK_NON_INTEGER_8D_STATE")
    return tuple(packet.dimensions)


def boundary_value(facts: DimensionBoundaryFacts) -> int:
    # source_ref: declaration, "Positive/negative boundaries"; negative wins.
    negative = any(
        (
            facts.intent_violated,
            facts.causal_order_violated,
            facts.life_harm,
            facts.other_rights_harm,
            facts.hard_risk,
        )
    )
    if negative:
        return -1
    positive = all(
        (
            facts.intent_satisfied,
            facts.evidence_valid,
            facts.life_safe,
            facts.other_rights_safe,
        )
    )
    return 1 if positive else 0


def positive_negative_boundaries(packet: StatePacket8D) -> tuple[int, ...]:
    if len(packet.boundary_facts) != 8:
        raise ValueError("BLOCK_INVALID_BOUNDARY_DIMENSION_COUNT")
    return tuple(boundary_value(facts) for facts in packet.boundary_facts)


def absolute_temporal_variation(current: StatePacket8D, previous: StatePacket8D) -> int:
    # source_ref: historical tau/dt rule; integer absolute event-time change.
    return abs(current.event_time - previous.event_time)


def metric_signature_f(packet: StatePacket8D) -> MetricSignature:
    # source_ref: declaration, METRIC_SIGNATURE_F ordered fields.
    return MetricSignature(
        packet.logical_time,
        packet.topology_coordinate_ref,
        packet.parent_state_root,
        packet.evidence_root,
        packet.event_hash_ref,
        packet.canonical_version,
        packet.rule_version,
    )


def state_cross_section(packet: StatePacket8D, slot_config: DirectSlotConfig) -> StateCrossSection:
    # Local import prevents projection/index import cycles.
    from .index import direct_slot_f, tau_f

    return StateCrossSection(
        tau_f(packet.event_time, slot_config),
        direct_slot_f(packet, slot_config),
        project_8d_state(packet),
        positive_negative_boundaries(packet),
        metric_signature_f(packet),
    )


def direction_state(selected_rule: NativeTransitionRule) -> str:
    return selected_rule.direction_code


def direction_path(rules: tuple[NativeTransitionRule, ...]) -> tuple[str, ...]:
    return tuple(direction_state(rule) for rule in rules)
