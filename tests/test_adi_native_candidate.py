import ast
import re
from dataclasses import replace
from pathlib import Path

import pytest

from core.adi_native.distance import TransitionRuleHold, delta_f
from core.adi_native.index import direct_slot_f, phi_f, tau_f
from core.adi_native.models import (
    DirectSlotConfig,
    DimensionBoundaryFacts,
    NativeTransitionRule,
    StatePacket8D,
)
from core.adi_native.projection import metric_signature_f, state_cross_section
from core.adi_native.spiral import evidence_closure_stop, enumerate_shells, omega_f
from core.adi_native.verifier import (
    candidate_state_root_f,
    evidence_closed_f,
    total_field_candidate_decision,
    validate_8d,
    validate_ethics,
    validate_native_adi,
)


POSITIVE_FACT = DimensionBoundaryFacts(
    intent_satisfied=True,
    evidence_valid=True,
    life_safe=True,
    other_rights_safe=True,
)
POSITIVE_BOUNDARIES = (POSITIVE_FACT,) * 8


def packet(
    code="A",
    *,
    event_time=10,
    logical_time=1,
    parent_state_root="aa" * 32,
    boundaries=POSITIVE_BOUNDARIES,
    evidence=True,
):
    digests = {"ev": "digest-1"} if evidence else {}
    expected = {"ev": "digest-1"}
    value = StatePacket8D(
        dimensions=(1, 2, 3, 4, 5, 6, 7, 8),
        event_time=event_time,
        namespace="founder-native",
        state_profile="current-v1",
        native_state_ref=code,
        state_root="",
        parent_state_root=parent_state_root,
        evidence_root="bb" * 32,
        snapshot_id="snapshot-1",
        canonical_version="canonical-v1",
        rule_version="rule-v1",
        logical_time=logical_time,
        topology_coordinate_ref=f"topology:{logical_time}",
        event_hash_ref=f"event:{code}:{logical_time}",
        boundary_facts=boundaries,
        evidence_digests=digests,
        expected_evidence_digests=expected,
        satisfied_preconditions=frozenset({"ready"}),
        previous_logical_time=logical_time - 1,
    )
    value = replace(value, state_root=candidate_state_root_f(value))
    return replace(value, claimed_metric_signature=metric_signature_f(value).as_tuple())


def transition(
    rule_id,
    source,
    target,
    cost,
    direction,
    *,
    required=("ev",),
):
    return NativeTransitionRule(
        transition_rule_id=rule_id,
        from_state_code=source,
        to_state_code=target,
        preconditions=("ready",),
        required_evidence_refs=required,
        polarity=1,
        direction_code=direction,
        step_cost_uint=cost,
        rule_version="rule-v1",
    )


def slot_config(*packets, value_by_code=None):
    value_by_code = value_by_code or {}
    base = DirectSlotConfig(0, 100, 10, {})
    lookup = {}
    for index, item in enumerate(packets, start=1):
        key = (
            item.namespace,
            item.state_profile,
            tau_f(item.event_time, base),
            item.native_state_ref,
            item.canonical_version,
            item.rule_version,
        )
        lookup[key] = value_by_code.get(item.native_state_ref, 100 + index)
    return DirectSlotConfig(0, 100, 10, lookup)


def test_t01_same_input_produces_same_phi_f():
    origin, target = packet("A"), packet("B", event_time=20, logical_time=2)
    rules = (transition("r01", "A", "B", 3, "FORWARD"),)
    config = slot_config(target)
    assert phi_f(origin, target, rules, config) == phi_f(origin, target, rules, config)


def test_t02_delta_f_identity_is_zero():
    value = packet("A")
    assert delta_f(value, value, ()) == 0


def test_t03_different_parent_root_cannot_form_same_authoritative_state():
    origin = packet("A")
    first = packet("B", event_time=20, logical_time=2, parent_state_root="11" * 32)
    second = packet("B", event_time=20, logical_time=2, parent_state_root="22" * 32)
    rules = (transition("r01", "A", "B", 3, "FORWARD"),)
    config = slot_config(first, second)
    assert first.state_root != second.state_root
    assert phi_f(origin, first, rules, config).native_adi_ref != phi_f(
        origin, second, rules, config
    ).native_adi_ref
    assert total_field_candidate_decision(
        shell=0,
        candidate_state_root=first.state_root,
        total_field_state_root=second.state_root,
    ).state == "HOLD_LOCAL_CANDIDATE_ROOT_MISMATCH"


def test_t04_missing_transition_rule_holds():
    with pytest.raises(TransitionRuleHold) as exc:
        delta_f(packet("A"), packet("B", logical_time=2), ())
    assert exc.value.code == "HOLD_TRANSITION_RULE_MISSING"


def test_t05_multiple_valid_canonical_paths_hold():
    origin, target = packet("A"), packet("D", logical_time=3)
    rules = (
        transition("r-direct", "A", "D", 5, "DIRECT"),
        transition("r-ab", "A", "B", 2, "FORWARD"),
        transition("r-bd", "B", "D", 3, "FORWARD"),
    )
    with pytest.raises(TransitionRuleHold) as exc:
        delta_f(origin, target, rules)
    assert exc.value.code == "HOLD_CANONICAL_PATH_DIVERGENCE"


def test_t06_shell_zero_is_only_authoritative_exact_state():
    root = packet().state_root
    result = total_field_candidate_decision(
        shell=0, candidate_state_root=root, total_field_state_root=root
    )
    assert result.state == "AUTHORITATIVE_EXACT_STATE"


def test_t07_positive_shell_is_never_authoritative():
    root = packet().state_root
    result = total_field_candidate_decision(
        shell=1, candidate_state_root=root, total_field_state_root=root
    )
    assert result.state == "RECONSTRUCTION_CANDIDATE_ONLY"
    assert result.evidence["authoritative"] is False


def test_t08_omega_order_is_reproducible():
    origin = packet("A")
    beta = packet("B", event_time=20, logical_time=3)
    gamma = packet("C", event_time=30, logical_time=2)
    rules = (
        transition("r-beta", "A", "B", 1, "EAST"),
        transition("r-alpha", "A", "C", 1, "WEST"),
    )
    expected = (gamma.state_root, beta.state_root)
    first = tuple(item.state_root for item in omega_f(origin, (beta, gamma), rules))
    second = tuple(item.state_root for item in omega_f(origin, (gamma, beta), rules))
    assert first == second == expected


def test_t09_first_unique_evidence_closed_fixed_point_stops_immediately():
    origin = packet("A")
    later = packet("B", event_time=20, logical_time=2)
    rules = (transition("r01", "A", "B", 1, "FORWARD"),)
    calls = []

    def validate(value):
        calls.append(value.state_root)
        return value

    receipt = evidence_closure_stop(
        origin,
        (later, origin),
        rules,
        authoritative_parent_state_root=origin.parent_state_root,
        total_field_validate=validate,
        query_budget=10,
    )
    assert receipt.state == "UNIQUE_EVIDENCE_CLOSED_FIXED_POINT"
    assert receipt.shell == 0
    assert receipt.evidence["stop_immediately"] is True
    assert calls == [origin.state_root]


def test_t10_query_budget_never_returns_partial_pass():
    result = total_field_candidate_decision(
        shell=0,
        candidate_state_root="aa",
        total_field_state_root="aa",
        examined=11,
        query_budget=10,
    )
    assert result.state == "HOLD_QUERY_BUDGET_EXCEEDED"
    assert result.evidence["partial_pass"] is False


def test_t11_life_or_rights_harm_is_absolute_redline():
    harmful = DimensionBoundaryFacts(life_harm=True)
    value = packet(boundaries=(harmful,) + POSITIVE_BOUNDARIES[1:])
    assert validate_8d(value).reason == "BLOCK_ABSOLUTE_REDLINE"
    assert validate_ethics([5] * 8, harms_others_rights=True).reason == "BLOCK_ABSOLUTE_REDLINE"


def test_t12_ethics_dimension_below_two_cannot_pass():
    assert validate_ethics([5, 5, 1, 5, 5, 5, 5, 5]).reason == "BLOCK_ETHICS_VECTOR_BELOW_2"


def test_t13_local_candidate_root_mismatch_holds():
    assert total_field_candidate_decision(
        shell=0, candidate_state_root="local", total_field_state_root="total"
    ).state == "HOLD_LOCAL_CANDIDATE_ROOT_MISMATCH"


@pytest.mark.parametrize(
    "proxy",
    [
        "Morton",
        "Z-order",
        "bit interleaving",
        "Manhattan",
        "Chebyshev",
        "Gray code",
        "Hilbert",
        "vector similarity",
        "generic nearest-neighbor",
        "speculative decoding",
        "KV cache",
        "PagedAttention",
        "token-level constrained decoding",
        "模型投票",
        "模型平均",
    ],
)
def test_t14_forbidden_native_profile_is_definition_drift(proxy):
    decision = validate_native_adi(proxy, {"PHI_F": "CURRENT_FOUNDER_CANONICAL"})
    assert decision.reason == "BLOCK_NATIVE_ADI_DEFINITION_DRIFT"


def test_t15_state8d_to_adi_io_relationship_is_complete():
    origin, target = packet("A"), packet("B", event_time=20, logical_time=2)
    rules = (transition("r01", "A", "B", 3, "FORWARD"),)
    result = phi_f(origin, target, rules, slot_config(target))
    names = tuple(name for name, _ in result.ordered_fields)
    assert names == (
        "namespace",
        "origin_state_root",
        "direct_slot",
        "absolute_time_slot",
        "state_8d",
        "boundary_state",
        "metric_signature",
        "absolute_distance",
        "direction_path",
        "parent_state_root",
        "evidence_root",
        "canonical_version",
        "rule_version",
        "logical_time",
    )


def test_t16_evidence_closure_requires_exact_evidence():
    origin = packet("A")
    target = packet("B", event_time=20, logical_time=2, evidence=False)
    rules = (transition("r01", "A", "B", 1, "FORWARD"),)
    result = evidence_closed_f(
        origin,
        target,
        rules,
        authoritative_parent_state_root=target.parent_state_root,
    )
    assert result.reason == "HOLD_REQUIRED_EVIDENCE_MISSING"


def test_t17_direct_slot_is_not_complete_phi_f():
    origin, target = packet("A"), packet("B", event_time=20, logical_time=2)
    rules = (transition("r01", "A", "B", 3, "FORWARD"),)
    config = slot_config(target)
    slot = direct_slot_f(target, config)
    adi = phi_f(origin, target, rules, config)
    assert isinstance(slot, int)
    assert adi.direct_slot == slot
    assert adi.ordered_fields != slot


def test_t18_metric_signature_binds_required_causal_fields():
    value = packet()
    signature = metric_signature_f(value)
    assert signature.as_tuple() == (
        value.logical_time,
        value.topology_coordinate_ref,
        value.parent_state_root,
        value.evidence_root,
        value.event_hash_ref,
        value.canonical_version,
        value.rule_version,
    )
    cross_section = state_cross_section(value, slot_config(value))
    assert cross_section.metric_signature == signature


def test_t19_delta_f_is_not_direct_slot_arithmetic():
    origin, target = packet("A"), packet("B", event_time=20, logical_time=2)
    rules = (transition("r01", "A", "B", 7, "FORWARD"),)
    config = slot_config(origin, target, value_by_code={"A": 55, "B": 55})
    assert abs(direct_slot_f(origin, config) - direct_slot_f(target, config)) == 0
    assert delta_f(origin, target, rules) == 7


def test_t20_external_research_dependencies_are_isolated():
    core_dir = Path(__file__).parents[1] / "core" / "adi_native"
    modules = [
        core_dir / name
        for name in ("models.py", "projection.py", "index.py", "distance.py", "spiral.py", "verifier.py")
    ]
    prohibited = {
        "judy",
        "art",
        "mmap",
        "sendfile",
        "minkowski",
        "alcubierre",
        "carter-wegman",
        "mireo",
        "ray",
        "localai",
    }
    imported = set()
    combined = ""
    for module in modules:
        source = module.read_text(encoding="utf-8")
        combined += "\n" + source.casefold()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.casefold() for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.casefold())
    assert not any(any(token in module for token in prohibited) for module in imported)
    for token in prohibited:
        assert re.search(rf"(?<![a-z0-9_-]){re.escape(token)}(?![a-z0-9_-])", combined) is None


def test_shell_enumeration_uses_integer_transition_costs():
    origin = packet("A")
    target = packet("B", event_time=20, logical_time=2)
    shells = enumerate_shells(
        origin,
        (target, origin),
        (transition("r01", "A", "B", 4, "FORWARD"),),
    )
    assert tuple(shell.radius for shell in shells) == (0, 4)
