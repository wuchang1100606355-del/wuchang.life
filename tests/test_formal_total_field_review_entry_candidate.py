from __future__ import annotations

import copy
import json
from pathlib import Path

from tools.total_field.formal_review_entry_candidate import (
    ACCEPT,
    EFFECT_SCOPE,
    HOLD,
    INPUT_SCHEMA,
    RECEIPT_SCHEMA,
    REJECT,
    evaluate_formal_review_entry_candidate,
)


ISSUED_AT = "2026-09-24T00:00:00Z"


def packet() -> dict:
    return {
        "schema_id": INPUT_SCHEMA,
        "FOUNDER_INTENT_REFERENCE": {
            "status": "BOUND",
            "reference": "founder_intent:test-bound-reference",
        },
        "SOURCE_LINEAGE": {
            "COMMON_PARENT": "d32ebc73ea7e413daa61c58cc831964743dba99d",
            "SOURCE_A": "680f646bd383077695b5a44e1d40657f7b6a358d",
            "SOURCE_B": "dbf06fca1fcee33d6a695c7be657146c543298ca",
            "SOURCE_C_SHA256": "0ba43b83fd9da27fa60751aeed22d2de1e8859a024775b78a99c6a5862b2577c",
            "LINEAGE_RECEIPT": "runtime/total_field/candidates/w7tp_v23_founder_semantic_successor_c/LINEAGE_RECEIPT.json",
            "authority": "D4_EVIDENCE_ONLY",
        },
        "CURRENT_8D_FIELD_REFERENCE": {
            "status": "UNKNOWN",
            "reference": None,
        },
        "CANDIDATE_STATE": {
            "SOURCE_C_SHA": "0ba43b83fd9da27fa60751aeed22d2de1e8859a024775b78a99c6a5862b2577c",
            "SEMANTIC_GUARD_RESULT": "PASS_14_OF_14",
            "CAPABILITY_PACK_HASH": "9417868c0d58dbd15f20f25a27d31ad2da4a7ec9110890beab2f6c4e2e5c413c",
            "CAPABILITY_PACK_SEMANTIC_RESULT": "PASS",
            "FOUNDER_DYNAMIC_CONTEXT_RESULT": "TOTAL_FIELD_DYNAMIC_CONTEXT_READY_CANDIDATE_ONLY",
            "CLOUD_CANDIDATE_ONLY": True,
            "D4_D8_SEPARATION": True,
            "ACTIVE": False,
            "CANONICAL": False,
            "D8": False,
        },
        "D4_EVIDENCE": {
            "source_c_sha_match": True,
            "semantic_guard": "PASS_14_OF_14",
            "lineage_receipt_sha256": "8f9205a77ca68767c54b4752474e2d6072e574d53da41600cc5059663d919bdc",
            "manifest_source_hash_match": True,
            "authority": "D4_EVIDENCE_ONLY",
            "d4_evidence_is_authority": False,
        },
        "RISK_RESULT": "PASS",
        "EFFECT_SCOPE": EFFECT_SCOPE,
    }


def evaluate(value: dict) -> dict:
    return evaluate_formal_review_entry_candidate(value, issued_at=ISSUED_AT)


def test_all_inputs_present_but_current_field_unknown_holds():
    result = evaluate(packet())
    assert result["review_result"] == HOLD
    assert "CURRENT_8D_FIELD_REFERENCE_NOT_BOUND" in result["reason_codes"]


def test_missing_founder_intent_ref_holds():
    value = packet()
    value.pop("FOUNDER_INTENT_REFERENCE")
    assert evaluate(value)["review_result"] == HOLD


def test_missing_source_lineage_holds():
    value = packet()
    value.pop("SOURCE_LINEAGE")
    assert evaluate(value)["review_result"] == HOLD


def test_missing_current_field_holds():
    value = packet()
    value.pop("CURRENT_8D_FIELD_REFERENCE")
    assert evaluate(value)["review_result"] == HOLD


def test_d4_all_pass_but_risk_unknown_holds():
    value = packet()
    value["CURRENT_8D_FIELD_REFERENCE"] = {"status": "BOUND", "reference": "field:test"}
    value["RISK_RESULT"] = "UNKNOWN"
    result = evaluate(value)
    assert result["review_result"] == HOLD
    assert result["reason_codes"] == ["RISK_RESULT_UNKNOWN"]


def test_risk_block_rejects():
    value = packet()
    value["RISK_RESULT"] = "BLOCK"
    assert evaluate(value)["review_result"] == REJECT


def test_effect_scope_mismatch_rejects():
    value = packet()
    value["EFFECT_SCOPE"] = "GLOBAL"
    assert evaluate(value)["review_result"] == REJECT


def test_pointer_only_holds():
    value = {"schema_id": INPUT_SCHEMA, "D4_EVIDENCE": {"pointer": "pointer:test"}}
    assert evaluate(value)["review_result"] == HOLD


def test_sha_only_holds():
    value = {"schema_id": INPUT_SCHEMA, "D4_EVIDENCE": {"sha256": "0" * 64}}
    assert evaluate(value)["review_result"] == HOLD


def test_passkey_only_holds():
    value = {"schema_id": INPUT_SCHEMA, "D4_EVIDENCE": {"passkey_valid": True}}
    assert evaluate(value)["review_result"] == HOLD


def test_signature_only_holds():
    value = {"schema_id": INPUT_SCHEMA, "D4_EVIDENCE": {"signature_valid": True}}
    assert evaluate(value)["review_result"] == HOLD


def test_cloud_candidate_direct_accept_holds():
    value = packet()
    value["CURRENT_8D_FIELD_REFERENCE"] = {"status": "BOUND", "reference": "field:test"}
    value["CANDIDATE_STATE"]["CLOUD_CANDIDATE_DIRECT_ACCEPT"] = True
    result = evaluate(value)
    assert result["review_result"] == HOLD
    assert "CLOUD_CANDIDATE_DIRECT_ACCEPT_FORBIDDEN" in result["reason_codes"]


def test_review_cannot_output_allow_effect():
    serialized = json.dumps(evaluate(packet()), sort_keys=True)
    assert "ALLOW_EFFECT" not in serialized
    assert "D8_ALLOW" not in serialized
    assert evaluate(packet())["total_field_effect_decision"] == "NOT_RUN"


def test_review_receipt_is_not_d8_receipt():
    receipt = evaluate(packet())["review_receipt_candidate"]
    assert receipt["schema_id"] == RECEIPT_SCHEMA
    assert receipt["receipt_type"] == "REVIEW_RECEIPT_CANDIDATE_NOT_D8_RECEIPT"
    assert receipt["d8_receipt"] is False
    assert receipt["authority_granted"] is False


def test_synthetic_fully_bound_packet_exercises_accept_candidate_branch_only():
    value = copy.deepcopy(packet())
    value["CURRENT_8D_FIELD_REFERENCE"] = {"status": "BOUND", "reference": "field:synthetic"}
    result = evaluate(value)
    assert result["review_result"] == ACCEPT
    assert result["authority_granted"] is False
    assert result["runtime_effect"] == "NONE"


def test_schema_declares_all_seven_inputs_and_candidate_only_outputs():
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "schemas/total_field/formal_total_field_review_entry_candidate_v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert set(schema["required"]) >= {
        "FOUNDER_INTENT_REFERENCE",
        "SOURCE_LINEAGE",
        "CURRENT_8D_FIELD_REFERENCE",
        "CANDIDATE_STATE",
        "D4_EVIDENCE",
        "RISK_RESULT",
        "EFFECT_SCOPE",
    }
    assert schema["x-review-output-contract"]["review_result"] == [ACCEPT, HOLD, REJECT]
    assert schema["x-review-output-contract"]["d8_decision"] == "NOT_RUN"


def test_wrong_source_lineage_holds():
    value = packet()
    value["CURRENT_8D_FIELD_REFERENCE"] = {"status": "BOUND", "reference": "field:test"}
    value["SOURCE_LINEAGE"]["SOURCE_A"] = "0" * 40
    assert evaluate(value)["review_result"] == HOLD


def test_failed_semantic_guard_cannot_accept():
    value = packet()
    value["CURRENT_8D_FIELD_REFERENCE"] = {"status": "BOUND", "reference": "field:test"}
    value["CANDIDATE_STATE"]["SEMANTIC_GUARD_RESULT"] = "FAIL"
    value["D4_EVIDENCE"]["semantic_guard"] = "FAIL"
    assert evaluate(value)["review_result"] == HOLD
