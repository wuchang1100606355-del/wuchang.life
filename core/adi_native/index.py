from __future__ import annotations

import hashlib
import json
from typing import Iterable

from .distance import resolve_canonical_path
from .models import DirectSlotConfig, NativeAdiIndex, NativeTransitionRule, StatePacket8D
from .projection import metric_signature_f, positive_negative_boundaries, project_8d_state

SOURCE_REF = "FOUNDER_NATIVE_ADI_RULE_DECLARATION_V1.md#complete-native-adi"
LEGACY_TRANSITION_PATH_DISTANCE_FIELD = "absolute_distance"


def tau_f(event_time: int, config: DirectSlotConfig) -> int:
    """Historical absolute-time slot projection retained as a distinct layer."""
    integer_inputs = (event_time, config.t_min, config.t_max, config.slot_count)
    if any(not isinstance(value, int) or isinstance(value, bool) for value in integer_inputs):
        raise ValueError("DIRECT_SLOT_INPUTS_MUST_BE_INTEGERS")
    if config.t_max <= config.t_min or config.slot_count <= 0:
        raise ValueError("INVALID_DIRECT_SLOT_RANGE")
    numerator = (event_time - config.t_min) * config.slot_count
    denominator = config.t_max - config.t_min
    result = numerator // denominator
    if result < 0:
        raise ValueError("DIRECT_SLOT_UINT_UNDERFLOW")
    return result


def time_axis_absolute_distance(state_slot: int, current_slot: int) -> int:
    """Return the non-negative slot distance from an explicit current slot."""
    for name, value in (("STATE_SLOT", state_slot), ("CURRENT_SLOT", current_slot)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{name}_MUST_BE_NON_NEGATIVE_INTEGER")
    return abs(state_slot - current_slot)


def direct_slot_f(packet: StatePacket8D, config: DirectSlotConfig) -> int:
    """Canonical lookup output; deliberately not the complete native ADI."""
    absolute_slot = tau_f(packet.event_time, config)
    key = (
        packet.namespace,
        packet.state_profile,
        absolute_slot,
        packet.native_state_ref,
        packet.canonical_version,
        packet.rule_version,
    )
    if key not in config.slot_lookup:
        raise KeyError("HOLD_DIRECT_SLOT_RULE_MISSING")
    result = config.slot_lookup[key]
    if not isinstance(result, int) or isinstance(result, bool) or result < 0:
        raise ValueError("DIRECT_SLOT_F_MUST_RETURN_UINT")
    return result


def _canonical_json(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def phi_f(
    origin: StatePacket8D,
    target: StatePacket8D,
    transition_rules: Iterable[NativeTransitionRule],
    slot_config: DirectSlotConfig,
) -> NativeAdiIndex:
    """Build the complete ordered Founder-native causal state index."""
    path = resolve_canonical_path(origin, target, transition_rules)
    transition_path_distance = path.total_cost
    direct_slot = direct_slot_f(target, slot_config)
    absolute_slot = tau_f(target.event_time, slot_config)
    metric = metric_signature_f(target).as_tuple()
    ordered_fields = (
        ("namespace", target.namespace),
        ("origin_state_root", origin.state_root),
        ("direct_slot", direct_slot),
        ("absolute_time_slot", absolute_slot),
        ("state_8d", project_8d_state(target)),
        ("boundary_state", positive_negative_boundaries(target)),
        ("metric_signature", metric),
        # Preserve the serialized field name while freezing its path-distance role.
        (LEGACY_TRANSITION_PATH_DISTANCE_FIELD, transition_path_distance),
        ("direction_path", path.direction_codes),
        ("parent_state_root", target.parent_state_root),
        ("evidence_root", target.evidence_root),
        ("canonical_version", target.canonical_version),
        ("rule_version", target.rule_version),
        ("logical_time", target.logical_time),
    )
    native_adi_ref = hashlib.sha256(_canonical_json(ordered_fields)).hexdigest()
    return NativeAdiIndex(
        ordered_fields,
        native_adi_ref,
        direct_slot,
        transition_path_distance,
        path.direction_codes,
    )
