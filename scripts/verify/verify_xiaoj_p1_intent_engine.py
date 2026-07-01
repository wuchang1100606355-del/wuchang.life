#!/usr/bin/env python3
"""Verify the pure XiaoJ P1 local intent engine.

This imports only the pure service module and exercises multi-intent, order,
payment, and receipt payloads. It does not import Odoo, write DB rows, create
orders, capture payments, save raw audio, call external APIs, or read secrets.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/p1_intent_engine.py"


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    raise SystemExit(1)


def load_engine():
    spec = importlib.util.spec_from_file_location("p1_intent_engine", ENGINE)
    if spec is None or spec.loader is None:
        fail("engine_import_spec_missing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def assert_false_flags(payload: dict) -> None:
    flags = payload.get("safety_flags", {})
    for flag in [
        "SECRET_READ",
        "MEMBER_PLAINTEXT_READ",
        "RAW_AUDIO_SAVED",
        "ODOO_DB_WRITE",
        "POS_ORDER_CREATED",
        "PAYMENT_CAPTURE",
        "EXTERNAL_API_CALL",
    ]:
        if flags.get(flag) is not False:
            fail(f"safety_flag_not_false:{flag}")


def assert_authority_chain(payload: dict, expected_decision: str | None = None) -> None:
    if not isinstance(payload.get("total_field_subfield_query"), dict):
        fail(f"total_field_subfield_query_missing:{payload.get('intent')}")
    total_field_query = payload["total_field_subfield_query"]
    if total_field_query.get("query_required") is not True or total_field_query.get("queried") is not True:
        fail(f"total_field_subfield_query_not_required_and_queried:{payload.get('intent')}")
    if total_field_query.get("state") != "TOTAL_FIELD_SUBFIELD_QUERY_OK":
        fail(f"total_field_subfield_query_not_ok:{payload.get('intent')}:{total_field_query.get('state')}")
    if not total_field_query.get("query_hash"):
        fail(f"total_field_subfield_query_hash_missing:{payload.get('intent')}")
    if int(total_field_query.get("subfield_count") or 0) <= 0:
        fail(f"total_field_subfield_query_empty:{payload.get('intent')}")
    for boundary_flag in ["secret_read", "member_plaintext_read", "db_write", "deploy", "service_restart"]:
        if total_field_query.get(boundary_flag) is not False:
            fail(f"total_field_query_boundary_flag_not_false:{payload.get('intent')}:{boundary_flag}")

    for key in ["authority_packet", "local_reconstruction", "local_verifier", "execution_gate", "evidence_seal"]:
        if not isinstance(payload.get(key), dict):
            fail(f"authority_chain_missing:{key}:{payload.get('intent')}")
    packet = payload["authority_packet"]
    reconstruction = payload["local_reconstruction"]
    verifier = payload["local_verifier"]
    gate = payload["execution_gate"]
    seal = payload["evidence_seal"]
    if packet.get("candidate_only") is not True:
        fail(f"authority_packet_not_candidate_only:{payload.get('intent')}")
    if packet.get("cloud_authority") is not False:
        fail(f"authority_packet_cloud_authority_not_false:{payload.get('intent')}")
    if packet.get("local_authority") != "discrete_state_core":
        fail(f"authority_packet_local_authority_wrong:{payload.get('intent')}")
    if packet.get("reality_layer") != "IMAGINED_CANDIDATE":
        fail(f"authority_packet_reality_layer_wrong:{payload.get('intent')}")
    reality_boundary = packet.get("reality_boundary", {})
    if reality_boundary.get("llm_hallucination_allowed") != "conditional":
        fail(f"authority_packet_reality_boundary_missing:{payload.get('intent')}")
    if reality_boundary.get("cloud_can_label_real_verified") is not False:
        fail(f"authority_packet_cloud_can_label_real:{payload.get('intent')}")
    if reality_boundary.get("cloud_can_set_executable_authorized") is not False:
        fail(f"authority_packet_cloud_can_set_executable:{payload.get('intent')}")
    if reality_boundary.get("total_field_distinguishes_real_or_imagined") is not True:
        fail(f"authority_packet_reality_distinction_missing:{payload.get('intent')}")
    if packet.get("total_field_subfield_query_required") is not True:
        fail(f"packet_total_field_query_not_required:{payload.get('intent')}")
    if packet.get("total_field_subfield_query_hash") != total_field_query.get("query_hash"):
        fail(f"packet_total_field_query_hash_mismatch:{payload.get('intent')}")
    if packet.get("generative_transmission", {}).get("full_body_transmitted") is not False:
        fail(f"generative_transmission_full_body_not_false:{payload.get('intent')}")
    if packet.get("generative_transmission", {}).get("total_field_subfield_query_hash") != total_field_query.get("query_hash"):
        fail(f"gt_total_field_query_hash_mismatch:{payload.get('intent')}")
    if reconstruction.get("packet_hash") != packet.get("packet_hash"):
        fail(f"reconstruction_packet_hash_mismatch:{payload.get('intent')}")
    reconstructed_query = reconstruction.get("total_field_subfield_query", {})
    if reconstructed_query.get("query_hash") != total_field_query.get("query_hash"):
        fail(f"reconstruction_total_field_query_hash_mismatch:{payload.get('intent')}")
    if reconstruction.get("cloud_authority") is not False:
        fail(f"reconstruction_cloud_authority_not_false:{payload.get('intent')}")
    reconstruction_reality = reconstruction.get("reality_boundary", {})
    if reconstruction_reality.get("llm_hallucination_allowed_only_as_candidate") is not True:
        fail(f"reconstruction_reality_boundary_missing:{payload.get('intent')}")
    if verifier.get("cloud_candidate_not_authority") is not True:
        fail(f"verifier_cloud_candidate_clause_missing:{payload.get('intent')}")
    if verifier.get("no_floating_point_authority") is not True:
        fail(f"verifier_no_float_clause_missing:{payload.get('intent')}")
    verifier_reality = verifier.get("reality_layer_verification", {})
    if verifier_reality.get("cloud_output_layer") != "IMAGINED_CANDIDATE":
        fail(f"verifier_reality_layer_wrong:{payload.get('intent')}")
    if verifier_reality.get("cloud_can_upgrade_to_real_or_executable") is not False:
        fail(f"verifier_cloud_upgrade_reality_not_false:{payload.get('intent')}")
    if gate.get("state") != verifier.get("decision"):
        fail(f"gate_verifier_decision_mismatch:{payload.get('intent')}")
    if gate.get("formal_pos_write") is not False or gate.get("payment_capture") is not False:
        fail(f"gate_has_side_effect_flag:{payload.get('intent')}")
    if seal.get("packet_hash") != packet.get("packet_hash"):
        fail(f"seal_packet_hash_mismatch:{payload.get('intent')}")
    if seal.get("formal_pos_write") is not False or seal.get("payment_capture") is not False:
        fail(f"seal_has_side_effect_flag:{payload.get('intent')}")
    if expected_decision and verifier.get("decision") != expected_decision:
        fail(f"decision_mismatch:{payload.get('intent')}:{verifier.get('decision')}:{expected_decision}")


def assert_release_status(payload: dict, expected_ready: bool) -> None:
    gates = payload.get("formal_release_gates")
    if not isinstance(gates, dict):
        fail("formal_release_gates_missing")
    for gate_id in ["member_registration", "pos_order", "payment", "lineworks_send"]:
        gate = gates.get(gate_id)
        if not isinstance(gate, dict):
            fail(f"formal_release_gate_missing:{gate_id}")
        if gate.get("release_ready") is not expected_ready:
            fail(f"formal_release_ready_mismatch:{gate_id}:{gate.get('release_ready')}:{expected_ready}")
        if expected_ready:
            expected_decision = "RELEASE_READY_FOR_HUMAN_ACTIVATION"
            if gate.get("decision") != expected_decision:
                fail(f"formal_release_decision_mismatch:{gate_id}:{gate.get('decision')}:{expected_decision}")
        elif gate.get("decision") not in {"HOLD_RELEASE_REQUIREMENTS_INCOMPLETE", "HOLD_RELEASE_REFS_UNVERIFIED"}:
            fail(f"formal_release_hold_decision_wrong:{gate_id}:{gate.get('decision')}")
        if "provided_refs" in gate:
            fail(f"formal_release_raw_refs_exposed:{gate_id}")
        if not isinstance(gate.get("provided_ref_hashes"), dict):
            fail(f"formal_release_ref_hashes_missing:{gate_id}")
        if expected_ready and sorted(gate.get("verified_ref_keys") or []) != sorted(gate.get("required_refs") or []):
            fail(f"formal_release_verified_keys_wrong:{gate_id}")
        side_effects = gate.get("p1_side_effects", {})
        for flag in ["member_plaintext_read", "formal_db_write", "formal_pos_write", "payment_capture", "external_api_call"]:
            if side_effects.get(flag) is not False:
                fail(f"formal_release_side_effect_not_false:{gate_id}:{flag}")
        query = gate.get("total_field_subfield_query", {})
        if query.get("state") != "TOTAL_FIELD_SUBFIELD_QUERY_OK":
            fail(f"formal_release_total_field_query_not_ok:{gate_id}")
    if payload.get("all_release_gates_ready") is not expected_ready:
        fail(f"all_release_gates_ready_mismatch:{payload.get('all_release_gates_ready')}:{expected_ready}")
    if payload.get("formal_pos_write") is not False or payload.get("payment_capture") is not False:
        fail("formal_release_payload_has_side_effect_flag")
    assert_false_flags(payload)
    assert_authority_chain(payload)


def verified_release_ref(gate_id: str, ref: str) -> dict:
    return {
        "ref": f"TEST_VERIFIED_REF_{gate_id}_{ref}",
        "packet_hash": "a" * 64,
        "verifier": "total_field_release_registry",
        "verified": True,
    }


def main() -> int:
    engine = load_engine()

    expected = {
        "LINE註冊": "member_register",
        "現金付款": "payment_candidate",
        "我要下單拿鐵": "order_candidate",
        "退這筆": "return_candidate",
        "改價": "manager_price_change",
        "請轉越文": "translate_assist",
        "櫃台提醒後台": "live_notice",
        "廠商費用預支": "cash_advance_ref",
        "客人回訪": "loyalty_return",
        "店員語音POS": "staff_voice_pos_operation",
        "招牌咖啡有什麼": "menu_lookup",
        "主權會員優惠": "sovereign_member_personalization",
        "幫我發社群貼文": "merchant_social_candidate",
        "社區訪客通知": "property_community_candidate",
        "人形服務生點餐": "humanoid_service_candidate",
        "LINE WORKS 通知會員": "lineworks_notify_candidate",
    }
    for text, intent in expected.items():
        got = engine.detect_intent(text)
        if got != intent:
            fail(f"intent_mismatch:{text}:{got}:{intent}")

    for intent in engine.SUPPORTED_INTENTS:
        payload = engine.candidate_action("test", intent)
        if payload["intent"] != intent:
            fail(f"candidate_intent_mismatch:{intent}")
        if payload["runtime_ready"] is not False:
            fail(f"candidate_runtime_ready_not_false:{intent}")
        assert_false_flags(payload)
        assert_authority_chain(payload)

    order = engine.order_payload([
        {"product_ref": "49180031", "name": "招牌咖啡", "quantity": 2, "price": 120},
        {"product_ref": "49180038", "name": "檸檬汁", "quantity": 1, "price": 90},
    ])
    if order["amount"] != 330:
        fail(f"order_amount_wrong:{order['amount']}")
    if order["pos_order_created"] is not False or order["odoo_db_write"] is not False:
        fail("order_has_side_effect_flag")
    assert_false_flags(order)
    assert_authority_chain(order, "HOLD")

    payment = engine.payment_payload(330, "cash")
    if payment["amount"] != 330 or payment["mode"] != "cash":
        fail("payment_payload_wrong")
    if payment["payment_capture"] is not False:
        fail("payment_capture_not_false")
    assert_false_flags(payment)
    assert_authority_chain(payment, "HOLD")

    dead_payment = engine.payment_payload(-1, "cash")
    assert_authority_chain(dead_payment, "DEAD_LETTER")

    receipt = engine.receipt_payload("ORDER-CANDIDATE-1")
    if receipt["receipt_created"] is not False:
        fail("receipt_created_not_false")
    if receipt["waiting_for_odoo_pos_order_id"] is not True:
        fail("receipt_not_waiting_for_order_id")
    assert_false_flags(receipt)
    assert_authority_chain(receipt, "HOLD")

    capability = engine.merchant_capability_payload()
    if len(capability["capability_map"]["capabilities"]) < 10:
        fail("merchant_capability_map_too_small")
    if capability["formal_pos_write"] is not False or capability["payment_capture"] is not False:
        fail("merchant_capability_has_side_effect")
    assert_false_flags(capability)
    assert_authority_chain(capability, "EXECUTE")

    release_hold = engine.formal_release_status_payload({})
    assert_release_status(release_hold, False)

    fake_release_refs = {}
    for gate_id, gate in engine.FORMAL_RELEASE_GATES.items():
        fake_release_refs[gate_id] = {ref: f"TEST_REF_{gate_id}_{ref}" for ref in gate["required_refs"]}
    release_fake = engine.formal_release_status_payload(fake_release_refs)
    assert_release_status(release_fake, False)
    for gate_id, gate in release_fake["formal_release_gates"].items():
        if gate.get("decision") != "HOLD_RELEASE_REFS_UNVERIFIED":
            fail(f"fake_release_ref_not_blocked:{gate_id}:{gate.get('decision')}")
        if sorted(gate.get("unverified_ref_keys") or []) != sorted(gate.get("required_refs") or []):
            fail(f"fake_release_unverified_keys_wrong:{gate_id}")

    release_refs = {}
    for gate_id, gate in engine.FORMAL_RELEASE_GATES.items():
        release_refs[gate_id] = {ref: verified_release_ref(gate_id, ref) for ref in gate["required_refs"]}
    release_ready = engine.formal_release_status_payload(release_refs)
    assert_release_status(release_ready, True)
    if release_ready.get("formal_lineworks_send_release") != "RELEASE_READY_FOR_HUMAN_ACTIVATION":
        fail("formal_lineworks_send_release_not_ready")

    original_subfields_root = engine.INTENT_SUBFIELDS_ROOT
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        inbox = tmp_root / "danger_subfield" / "inbox"
        inbox.mkdir(parents=True)
        (inbox / "danger.total_field_packet.json").write_text(
            json.dumps(
                {
                    "state": "DANGER_PACKET_FOR_VERIFIER_TEST",
                    "run_id": "TEST_DANGER_FLAGS",
                    "mission": "verify danger flags block authority",
                    "db_write": True,
                    "service_restart": False,
                    "deploy": False,
                    "secret_read": False,
                    "member_plaintext_read": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        engine.INTENT_SUBFIELDS_ROOT = tmp_root
        dangerous_payload = engine.candidate_action("test", "merchant_capability_map")
        dangerous_query = dangerous_payload["total_field_subfield_query"]
        if dangerous_query.get("state") != "HOLD_TOTAL_FIELD_SUBFIELD_DANGER_FLAGS":
            fail(f"danger_subfield_query_not_hold:{dangerous_query.get('state')}")
        if dangerous_query.get("danger_flags_present") is not True:
            fail("danger_subfield_flag_missing")
        if dangerous_payload["local_verifier"]["decision"] != "HOLD":
            fail(f"danger_subfield_verifier_not_hold:{dangerous_payload['local_verifier']['decision']}")
        if "total_field_subfield_danger_flags" not in dangerous_payload["local_verifier"]["failure_reasons"]:
            fail("danger_subfield_failure_reason_missing")
        dangerous_release = engine.formal_release_status_payload(release_refs)
        for gate_id, gate in dangerous_release["formal_release_gates"].items():
            if gate.get("decision") != "HOLD_RELEASE_TOTAL_FIELD_DANGER_FLAGS":
                fail(f"danger_release_not_blocked:{gate_id}:{gate.get('decision')}")
        engine.INTENT_SUBFIELDS_ROOT = original_subfields_root

    lineworks = engine.lineworks_notify_payload(
        "提醒志工明天 10:00 到聊國咖啡館集合",
        "lineworks_user_ref_demo",
        "member_service",
        "staff_ref_demo",
    )
    if lineworks["intent"] != "lineworks_notify_candidate":
        fail("lineworks_intent_wrong")
    if lineworks.get("formal_lineworks_send") is not False or lineworks.get("external_api_call") is not False:
        fail("lineworks_has_external_side_effect")
    candidate = lineworks.get("lineworks_notify_candidate", {})
    if candidate.get("target_ref_mode") != "hash_only" or not candidate.get("target_ref_hash"):
        fail("lineworks_target_hash_missing")
    if "lineworks_user_ref_demo" in json.dumps(lineworks, ensure_ascii=False):
        fail("lineworks_raw_target_ref_exposed")
    if "lineworks_send_release_required" not in lineworks["local_verifier"]["failure_reasons"]:
        fail("lineworks_release_failure_reason_missing")
    assert_false_flags(lineworks)
    assert_authority_chain(lineworks, "HOLD")

    voice = engine.staff_voice_pos_payload("店員語音POS 我要下單招牌咖啡", "staff_ref_demo", "zh-Hant")
    if voice["intent"] != "staff_voice_pos_operation":
        fail("voice_pos_intent_wrong")
    if voice["raw_audio_saved"] is not False:
        fail("voice_raw_audio_saved_not_false")
    if voice["pos_order_created"] is not False or voice["payment_capture"] is not False:
        fail("voice_has_transaction_side_effect")
    if voice["candidate_action"]["confirm_state"] != "draft":
        fail("voice_candidate_not_draft")
    assert_false_flags(voice)
    assert_authority_chain(voice, "HOLD")

    grammar = engine.parse_staff_voice_order("大冰少糖拿鐵")
    if grammar["valid"] is not True:
        fail(f"grammar_valid_example_failed:{grammar}")
    slots = grammar["slots"]
    expected_slots = {
        "size": "large",
        "temperature": "ice",
        "sweetness": "less_sugar",
        "item": "拿鐵",
    }
    if slots["size"]["value"] != expected_slots["size"]:
        fail("grammar_size_wrong")
    if slots["temperature"]["value"] != expected_slots["temperature"]:
        fail("grammar_temperature_wrong")
    if slots["sweetness"]["value"] != expected_slots["sweetness"]:
        fail("grammar_sweetness_wrong")
    if slots["item"]["text"] != expected_slots["item"]:
        fail("grammar_item_wrong")

    grammar_payload = engine.staff_voice_pos_payload("大冰少糖拿鐵", "staff_ref_demo", "zh-Hant")
    if grammar_payload["voice_pos_grammar"]["valid"] is not True:
        fail("grammar_payload_not_valid")
    if grammar_payload["candidate_action"]["grammar_valid"] is not True:
        fail("grammar_candidate_not_valid")
    assert_false_flags(grammar_payload)
    assert_authority_chain(grammar_payload, "HOLD")

    invalid = engine.parse_staff_voice_order("拿鐵大冰少糖")
    if invalid["valid"] is not False:
        fail("grammar_invalid_order_passed")
    if "out_of_order_requires_repeat_confirmation" not in invalid["errors"]:
        fail("grammar_invalid_missing_repeat_confirmation_error")
    if invalid["repeat_confirmation_required"] is not True:
        fail("grammar_invalid_repeat_confirmation_not_required")
    if invalid["repeat_confirmation"]["canonical_transcript"] != "大冰少糖拿鐵":
        fail("grammar_invalid_repeat_confirmation_wrong")
    inferred = invalid["inferred_slots"]
    if inferred["size"]["value"] != "large":
        fail("grammar_invalid_inferred_size_wrong")
    if inferred["temperature"]["value"] != "ice":
        fail("grammar_invalid_inferred_temperature_wrong")
    if inferred["sweetness"]["value"] != "less_sugar":
        fail("grammar_invalid_inferred_sweetness_wrong")
    if inferred["item"]["text"] != "拿鐵":
        fail("grammar_invalid_inferred_item_wrong")

    invalid_payload = engine.staff_voice_pos_payload("拿鐵大冰少糖", "staff_ref_demo", "zh-Hant")
    invalid_candidate = invalid_payload["candidate_action"]
    if invalid_candidate["grammar_valid"] is not False:
        fail("invalid_payload_grammar_valid_not_false")
    if invalid_candidate["repeat_confirmation_required"] is not True:
        fail("invalid_payload_repeat_confirmation_not_required")
    if invalid_payload["pos_order_created"] is not False or invalid_payload["payment_capture"] is not False:
        fail("invalid_payload_has_transaction_side_effect")
    assert_false_flags(invalid_payload)
    assert_authority_chain(invalid_payload, "HOLD")

    print("STATE=PASS_XIAOJ_P1_INTENT_ENGINE_AUTHORITY_CHAIN_READY")
    print("ACTION=VERIFY_XIAOJ_P1_INTENT_ENGINE")
    print(f"ENGINE={ENGINE.relative_to(ROOT)}")
    print("SUPPORTED_INTENTS=" + str(len(engine.SUPPORTED_INTENTS)))
    print("ORDER_AMOUNT_TEST=330")
    print("STAFF_VOICE_POS_OPERATION=TRUE")
    print("VOICE_POS_GRAMMAR=size_temperature_sweetness_item")
    print("VOICE_POS_EXAMPLE=大冰少糖拿鐵")
    print("VOICE_POS_REVERSE_EXAMPLE=拿鐵大冰少糖")
    print("VOICE_POS_REVERSE_REPEAT_CONFIRMATION=TRUE")
    print("RUNTIME_READY=FALSE")
    print("ODOO_DB_WRITE=FALSE")
    print("POS_ORDER_CREATED=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("RAW_AUDIO_SAVED=FALSE")
    print("EXTERNAL_API_CALL=FALSE")
    print("AUTHORITY_PACKET=TRUE")
    print("LOCAL_RECONSTRUCTION=TRUE")
    print("LOCAL_VERIFIER=TRUE")
    print("EXECUTION_GATE=TRUE")
    print("EVIDENCE_SEAL=TRUE")
    print("TOTAL_FIELD_SUBFIELD_QUERY=TRUE")
    print("LLM_REALITY_LAYER_GOVERNANCE=TRUE")
    print("LLM_HALLUCINATION=CONDITIONALLY_ALLOWED_AS_IMAGINED_CANDIDATE")
    print("FORMAL_RELEASE_GATES=TRUE")
    print("FORMAL_MEMBER_REGISTRATION_RELEASE_GATE=TRUE")
    print("FORMAL_POS_ORDER_RELEASE_GATE=TRUE")
    print("FORMAL_PAYMENT_RELEASE_GATE=TRUE")
    print("FORMAL_LINEWORKS_SEND_RELEASE_GATE=TRUE")
    print("LINEWORKS_NOTIFY_CANDIDATE=TRUE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
