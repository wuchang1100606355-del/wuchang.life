import json
import sys
from pathlib import Path

BASE = Path("runtime/total_field/landing")
ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field.w7tp_true8d_contract_sandbox import (  # noqa: E402
    GateResult,
    IntentRoot,
    MinimumDelta,
    NodeD8Envelope,
    StateFieldRef,
    construction_order,
    run_three_gate_subprocess,
)

def load(name):
    return json.loads((BASE / name).read_text(encoding="utf-8"))

def test_odoo_menu_probe_is_readonly():
    data = load("ODOO_MENU_READONLY_PROBE_REQUEST_V1.json")
    assert data["execution_mode"] == "REQUEST_ONLY"
    assert data["db_write"] is False
    assert data["deploy"] is False
    assert data["restart"] is False
    assert data["hard_limits"]["read_env"] is False
    assert data["hard_limits"]["read_credentials_xml"] is False
    assert data["hard_limits"]["read_internal_member_files"] is False
    assert data["hard_limits"]["dump_db"] is False
    assert data["hard_limits"]["write_odoo"] is False

def test_human_confirm_gate_blocks_auto_write():
    data = load("HUMAN_CONFIRM_GATE_V1.json")
    assert data["human_confirm_required"] is True
    assert data["candidate_only"] is True
    assert data["formal_write_allowed"] is False
    assert "WAIT_HUMAN_CONFIRM" in data["allowed_states"]
    assert "REJECTED_BY_HUMAN" in data["allowed_states"]


def _intent() -> IntentRoot:
    return IntentRoot(
        result="produce a candidate counter response",
        subject="cafe guest",
        scene="cafe public-test counter",
        known_state_refs=("state:menu:readonly",),
        constraints=("candidate-only", "no-write"),
        acceptance=("human can review the candidate",),
        target_product_effect=("guest understands the next safe action",),
    )


def _delta(*, unknown_slots=("reply_copy",)) -> MinimumDelta:
    return MinimumDelta(
        affected_coordinates=("coordinate:cafe-counter",),
        stable_refs=("state:menu:readonly", "rule:human-confirm"),
        changed_state={"candidate_response": "required"},
        unknown_slots=unknown_slots,
        reconstruction_conditions=("menu reference resolves",),
        verification_conditions=("candidate-only output",),
        target_product_effect=("guest understands the next safe action",),
    )


def _none_delta() -> MinimumDelta:
    return MinimumDelta(
        affected_coordinates=(),
        stable_refs=("state:menu:readonly",),
        changed_state={},
        unknown_slots=(),
        reconstruction_conditions=("menu reference resolves",),
        verification_conditions=("candidate-only output",),
        target_product_effect=("guest understands the next safe action",),
    )


def _candidate(packet):
    return {
        "candidate_delta_only": True,
        "unknown_slots": {
            slot: f"candidate:{slot}"
            for slot in packet["unknown_slots"]
        },
        "formal_authority": False,
    }


def _run(*, resolve_intent=_intent, current=None, canonical_gate=None,
         measure_minimum_delta=None, human_product_gate=None,
         verify_candidate=None, model53=_candidate):
    return run_three_gate_subprocess(
        user_input="raw user input must stay outside the model packet",
        node_id="node:cafe-counter",
        model53=model53,
        resolve_intent=lambda _text: resolve_intent(),
        load_scoped_state=lambda _intent_root, _node_id: (
            {"state_root_ref": "state:counter:verified"}
            if current is None else current
        ),
        canonical_gate=canonical_gate or (lambda _intent_root, _current: GateResult("PASS")),
        measure_minimum_delta=measure_minimum_delta or (lambda _intent_root, _current: _delta()),
        human_product_gate=human_product_gate or (lambda _intent_root, _minimum_delta: GateResult("PASS")),
        verify_candidate=verify_candidate or (
            lambda _intent_root, _current, _minimum_delta, _candidate_delta: GateResult("PASS")
        ),
    )


def test_t01_unresolved_d1_never_loads_or_generates():
    calls = {"load": 0, "model": 0}

    result = run_three_gate_subprocess(
        user_input="unresolved",
        node_id="node:cafe-counter",
        model53=lambda _packet: calls.__setitem__("model", calls["model"] + 1),
        resolve_intent=lambda _text: None,
        load_scoped_state=lambda _intent_root, _node_id: calls.__setitem__("load", calls["load"] + 1),
        canonical_gate=lambda _intent_root, _current: GateResult("PASS"),
        measure_minimum_delta=lambda _intent_root, _current: _delta(),
        human_product_gate=lambda _intent_root, _minimum_delta: GateResult("PASS"),
        verify_candidate=lambda _intent_root, _current, _minimum_delta, _candidate_delta: GateResult("PASS"),
    )

    assert result.state == "LOCAL_HOLD_INTENT_UNRESOLVED"
    assert result.model_calls == 0
    assert calls == {"load": 0, "model": 0}


def test_t02_gate_one_drift_holds_before_delta_or_model():
    calls = {"delta": 0, "model": 0}

    result = _run(
        current={"adi_native": "embedding"},
        measure_minimum_delta=lambda _intent_root, _current: calls.__setitem__("delta", calls["delta"] + 1),
        model53=lambda _packet: calls.__setitem__("model", calls["model"] + 1),
    )

    assert result.state == "HOLD_DETOUR_ALERT"
    assert result.model_calls == 0
    assert calls == {"delta": 0, "model": 0}


def test_t03_no_true_delta_stops_before_product_gate_or_model():
    calls = {"product": 0, "model": 0}

    result = _run(
        measure_minimum_delta=lambda _intent_root, _current: _none_delta(),
        human_product_gate=lambda _intent_root, _minimum_delta: calls.__setitem__("product", calls["product"] + 1),
        model53=lambda _packet: calls.__setitem__("model", calls["model"] + 1),
    )

    assert result.state == "BUILD_NOT_REQUIRED"
    assert result.minimum_delta is not None and result.minimum_delta.is_none
    assert result.model_calls == 0
    assert calls == {"product": 0, "model": 0}


def test_t04_product_effect_hold_never_calls_model():
    calls = {"model": 0}

    result = _run(
        human_product_gate=lambda _intent_root, _minimum_delta: GateResult(
            "HOLD", "operation load remains too high"
        ),
        model53=lambda _packet: calls.__setitem__("model", calls["model"] + 1),
    )

    assert result.state == "LOCAL_HOLD_PRODUCT_EFFECT"
    assert result.model_calls == 0
    assert calls["model"] == 0


def test_t05_model_packet_uses_only_refs_and_unknown_slots():
    captured = {}
    current = {
        "state_root_ref": "state:counter:verified",
        "known_value": "known-state-value",
        "private_known_value": "must never be copied to the model packet",
    }

    def capture_model(packet):
        captured.update(packet)
        return _candidate(packet)

    result = _run(current=current, model53=capture_model)

    assert result.state == "CANDIDATE_READY_FOR_TOTAL_FIELD"
    assert set(captured) == {
        "intent_root_ref", "current_state_root_ref", "stable_state_refs",
        "affected_coordinates", "unknown_slots", "target_product_effect",
        "reconstruction_conditions", "verification_conditions", "output_schema",
    }
    packet_text = json.dumps(captured, ensure_ascii=False)
    assert "known-state-value" not in packet_text
    assert "must never be copied" not in packet_text
    assert "raw user input" not in packet_text
    assert captured["unknown_slots"] == ["reply_copy"]


def test_t06_three_gates_and_unknown_slot_call_model_once():
    calls = {"model": 0}

    def counted_model(packet):
        calls["model"] += 1
        return _candidate(packet)

    result = _run(model53=counted_model)

    assert result.state == "CANDIDATE_READY_FOR_TOTAL_FIELD"
    assert result.model_calls == 1
    assert calls["model"] == 1


def test_t07_invalid_model_candidate_holds_without_verifier_pass():
    calls = {"verifier": 0}

    result = _run(
        model53=lambda _packet: {
            "candidate_delta_only": True,
            "unknown_slots": {},
            "formal_authority": False,
        },
        verify_candidate=lambda _intent_root, _current, _minimum_delta, _candidate_delta: calls.__setitem__(
            "verifier", calls["verifier"] + 1
        ),
    )

    assert result.state == "LOCAL_HOLD_MODEL_OUTPUT_INVALID"
    assert result.model_calls == 1
    assert calls["verifier"] == 0


def test_t08_valid_candidate_is_ready_but_not_formally_passed():
    result = _run()

    assert result.state == "CANDIDATE_READY_FOR_TOTAL_FIELD"
    assert result.candidate_delta is not None
    assert result.candidate_delta["candidate_delta_only"] is True
    assert result.candidate_delta["formal_authority"] is False
    assert "CANDIDATE_ONLY" in result.evidence


def test_t09_second_core_is_rejected_and_d8_stays_reference_only():
    calls = {"canonical": 0, "model": 0}
    envelope = NodeD8Envelope(
        node_id="node:cafe-counter",
        intent_root_ref="intent:d1:example",
        field_refs=(StateFieldRef("D1", "intent:d1:example", "REF"),),
        parent_state_root="state:counter:verified",
        evidence_root="evidence:preflight",
        rule_version="candidate-only-v1",
        logical_time=1,
    )
    result = _run(
        current={"second_total_field": True},
        canonical_gate=lambda _intent_root, _current: calls.__setitem__(
            "canonical", calls["canonical"] + 1
        ),
        model53=lambda _packet: calls.__setitem__("model", calls["model"] + 1),
    )

    assert envelope.field_refs[0].mode == "REF"
    assert result.state == "HOLD_DETOUR_ALERT"
    assert result.model_calls == 0
    assert calls == {"canonical": 0, "model": 0}


def test_t10_deterministic_delta_uses_no_model_and_order_is_fixed():
    calls = {"model": 0}
    result = _run(
        measure_minimum_delta=lambda _intent_root, _current: _delta(unknown_slots=()),
        model53=lambda _packet: calls.__setitem__("model", calls["model"] + 1),
    )

    assert result.state == "CANDIDATE_READY_FOR_TOTAL_FIELD"
    assert result.model_calls == 0
    assert calls["model"] == 0
    assert result.candidate_delta == {
        "candidate_delta_only": True,
        "unknown_slots": {},
        "formal_authority": False,
    }
    assert construction_order() == (
        "D1_INTENT_RESOLUTION",
        "LOAD_VERIFIED_SCOPED_STATE",
        "GATE_1_CANONICAL_LOCK",
        "GATE_2_INTENT_PRODUCT_GAP",
        "GATE_3_HUMAN_UI_PRODUCT_REVIEW",
        "GENERATE_UNKNOWN_DELTA_ONLY",
        "RECONSTRUCT_CANDIDATE_STATE",
        "VERIFY_CANDIDATE",
        "TOTAL_FIELD_REVIEW",
    )
