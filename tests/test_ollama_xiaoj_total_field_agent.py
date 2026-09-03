import hashlib
from copy import deepcopy
from pathlib import Path

import pytest

from tools.ollama_xiaoj_total_field_agent import (
    AgentConfig,
    OllamaXiaoJTotalFieldAgent,
    contains_secret_material,
)
from tools.total_field_dynamic_context import (
    REQUIRED_ALIGNMENT_ACKNOWLEDGEMENTS,
    build_dynamic_context,
    build_provider_neutral_intent_projection,
    build_total_field_correction_contract,
    build_total_field_progress_projection,
)


def _agent_with_context(packet):
    return OllamaXiaoJTotalFieldAgent(
        AgentConfig(total_field_root=Path(".")),
        receive_candidate=lambda candidate: candidate,
        dynamic_context_provider=lambda query, max_items: packet,
    )


def test_security_policy_words_are_not_secret_material():
    packet = {
        "state": "TOTAL_FIELD_DYNAMIC_CONTEXT_READY",
        "snippet": "No private key, token, password, or member plaintext is included.",
        "policy": {
            "credential_output": False,
            "member_plaintext_included": False,
        },
    }

    assert contains_secret_material(packet) is False
    loaded = _agent_with_context(packet)._load_dynamic_context(
        source="TOTAL_FIELD_PULL",
        prompt="safe",
    )
    assert loaded["state"] == "TOTAL_FIELD_DYNAMIC_CONTEXT_READY"


def test_actual_sensitive_value_still_fails_closed():
    packet = {
        "state": "TOTAL_FIELD_DYNAMIC_CONTEXT_READY",
        "private_key": "actual-secret-value",
    }

    assert contains_secret_material(packet) is True
    loaded = _agent_with_context(packet)._load_dynamic_context(
        source="TOTAL_FIELD_PULL",
        prompt="safe",
    )
    assert loaded["state"] == "HOLD_SECRET_OR_MEMBER_PLAINTEXT_INPUT"


def test_high_confidence_bearer_value_still_fails_closed():
    packet = {
        "state": "TOTAL_FIELD_DYNAMIC_CONTEXT_READY",
        "snippet": "Authorization: Bearer abcdefghijklmnopqrstuvwxyz",
    }

    assert contains_secret_material(packet) is True


def test_default_model_budget_matches_existing_gateway_budget():
    assert AgentConfig().timeout_seconds == 120.0


def _translation_observation(founder_intent, translator_ref):
    return {
        "schema_id": "W7TP_PROVIDER_NEUTRAL_INTENT_TRANSLATION_OBSERVATION_V1",
        "translator_ref": translator_ref,
        "founder_intent_sha256": hashlib.sha256(founder_intent.encode("utf-8")).hexdigest(),
        "acknowledged_invariants": sorted(REQUIRED_ALIGNMENT_ACKNOWLEDGEMENTS),
        "user_visible_language": "zh-TW",
        "english_terms_have_zh_tw_translation": True,
        "claims_canonical_authority": False,
        "requests_external_effect": False,
        "dimensions": {
            f"D{number}": {
                "state": "CANDIDATE",
                "claims_zh_TW": [f"第{number}維保持候選並等待總場裁決"],
                "refs": [f"dimension_ref:d{number}:test"],
            }
            for number in range(1, 9)
        },
        "unknowns": [],
    }


def test_provider_neutral_translators_produce_same_sparse_8dadi_projection():
    founder_intent = "以自然語言建構並在重新觀測後只修正剩餘差異。"
    first = build_provider_neutral_intent_projection(
        founder_intent,
        founder_intent_ref="intent_ref:founder:test",
        current_state_ref="state_ref:current:test",
        translation_observation=_translation_observation(
            founder_intent, "translator_ref:model_a"
        ),
        created_at="2026-09-03T05:00:00Z",
        root=Path("."),
    )
    second = build_provider_neutral_intent_projection(
        founder_intent,
        founder_intent_ref="intent_ref:founder:test",
        current_state_ref="state_ref:current:test",
        translation_observation=_translation_observation(
            founder_intent, "translator_ref:model_b"
        ),
        created_at="2026-09-03T05:00:00Z",
        root=Path("."),
    )

    assert first["state"] == "ALIGNMENT_ACCEPTED_READ_ONLY_CANDIDATE"
    assert first["candidate_projection_sha256"] == second["candidate_projection_sha256"]
    assert first["candidate_projection"] == second["candidate_projection"]
    assert first["packet_sha256"] != second["packet_sha256"]
    assert first["operation_authority"] is False


def test_alignment_rejects_missing_acknowledgement():
    founder_intent = "區網優先，虛擬私人網路只在區網不可用時使用。"
    observation = _translation_observation(
        founder_intent, "translator_ref:incomplete"
    )
    observation["acknowledged_invariants"].remove("LAN_PRECEDES_VPN")

    with pytest.raises(ValueError, match="ALIGNMENT_ACKNOWLEDGEMENTS_INCOMPLETE"):
        build_provider_neutral_intent_projection(
            founder_intent,
            founder_intent_ref="intent_ref:founder:test",
            current_state_ref="state_ref:current:test",
            translation_observation=observation,
            created_at="2026-09-03T05:00:00Z",
            root=Path("."),
        )


def test_unknown_translation_stays_hold_and_is_not_invented():
    founder_intent = "只使用已觀測的能力。"
    observation = _translation_observation(founder_intent, "translator_ref:unknown")
    observation["dimensions"]["D3"] = {
        "state": "UNKNOWN",
        "claims_zh_TW": ["商米節點的區網原生位址未知"],
        "refs": ["node_ref:taiji04:lan"],
    }
    observation["unknowns"] = ["商米節點的區網原生位址未知"]

    result = build_provider_neutral_intent_projection(
        founder_intent,
        founder_intent_ref="intent_ref:founder:test",
        current_state_ref="state_ref:current:test",
        translation_observation=observation,
        created_at="2026-09-03T05:00:00Z",
        root=Path("."),
    )

    assert result["state"] == "HOLD_TRANSLATION_UNRESOLVED"
    assert result["candidate_projection"]["unknowns"] == ["商米節點的區網原生位址未知"]
    assert result["candidate_projection"]["policy"]["unknown_will_not_be_invented"] is True


def _progress_observation(state, ref, digest):
    return {"state": state, "ref": ref, "sha256": digest}


def test_progress_projection_is_append_only_and_closes_only_on_reobservation():
    target_hash = "a" * 64
    first = build_total_field_progress_projection(
        founder_intent_ref="intent_ref:founder:test",
        founder_intent_sha256="b" * 64,
        target_state=_progress_observation("RECONSTRUCTED", "state_ref:target:test", target_hash),
        current_state=_progress_observation("OBSERVED", "state_ref:current:test", "c" * 64),
        reobserved_state=_progress_observation("OBSERVED", "state_ref:reobserved:test", "d" * 64),
        remaining_difference_refs=["delta_ref:one:test"],
        receipt_refs=["receipt_ref:observation:test"],
        node_observations=[
            {
                "node_id": "MSI",
                "state": "OBSERVED",
                "observed_at": "2026-09-03T05:00:00Z",
                "evidence_ref": "evidence_ref:msi:test",
                "evidence_sha256": "e" * 64,
            }
        ],
        created_at="2026-09-03T05:00:00Z",
    )
    second = build_total_field_progress_projection(
        founder_intent_ref="intent_ref:founder:test",
        founder_intent_sha256="b" * 64,
        target_state=_progress_observation("RECONSTRUCTED", "state_ref:target:test", target_hash),
        current_state=_progress_observation("OBSERVED", "state_ref:current:test", "c" * 64),
        reobserved_state=_progress_observation("OBSERVED", "state_ref:reobserved:test", target_hash),
        remaining_difference_refs=[],
        receipt_refs=["receipt_ref:reobserved:test"],
        node_observations=[
            {
                "node_id": "MSI",
                "state": "OBSERVED",
                "observed_at": "2026-09-03T05:05:00Z",
                "evidence_ref": "evidence_ref:msi:reobserved",
                "evidence_sha256": "f" * 64,
            }
        ],
        created_at="2026-09-03T05:05:00Z",
        previous_progress=deepcopy(first),
    )

    assert first["state"] == "OPEN_RESIDUAL_DIFFERENCE"
    assert second["state"] == "REOBSERVED_TARGET_FIELD_CLOSED"
    assert second["logical_time"] == first["logical_time"] + 1
    assert second["parent_progress_sha256"] == first["packet_sha256"]
    assert second["model_access"] == "READ_ONLY"
    assert second["formal_decision_authority"] is False


def test_progress_projection_rejects_stale_node_observation():
    with pytest.raises(ValueError, match="PROGRESS_NODE_OBSERVATION_STALE"):
        build_total_field_progress_projection(
            founder_intent_ref="intent_ref:founder:test",
            founder_intent_sha256="b" * 64,
            target_state=_progress_observation("RECONSTRUCTED", "state_ref:target:test", "a" * 64),
            current_state=_progress_observation("OBSERVED", "state_ref:current:test", "c" * 64),
            reobserved_state=_progress_observation("UNKNOWN", "state_ref:reobserved:test", "d" * 64),
            remaining_difference_refs=["delta_ref:unknown:test"],
            receipt_refs=["receipt_ref:observation:test"],
            node_observations=[
                {
                    "node_id": "MSI",
                    "state": "OBSERVED",
                    "observed_at": "2026-09-03T04:00:00Z",
                    "evidence_ref": "evidence_ref:msi:stale",
                    "evidence_sha256": "e" * 64,
                }
            ],
            created_at="2026-09-03T05:00:00Z",
            ttl_seconds=900,
        )


def test_correction_contract_is_idempotent_and_residual_only():
    progress = build_total_field_progress_projection(
        founder_intent_ref="intent_ref:founder:test",
        founder_intent_sha256="b" * 64,
        target_state=_progress_observation("RECONSTRUCTED", "state_ref:target:test", "a" * 64),
        current_state=_progress_observation("OBSERVED", "state_ref:current:test", "c" * 64),
        reobserved_state=_progress_observation("OBSERVED", "state_ref:reobserved:test", "d" * 64),
        remaining_difference_refs=["delta_ref:network:test"],
        receipt_refs=["receipt_ref:observation:test"],
        node_observations=[
            {
                "node_id": "MSI",
                "state": "OBSERVED",
                "observed_at": "2026-09-03T05:00:00Z",
                "evidence_ref": "evidence_ref:msi:test",
                "evidence_sha256": "e" * 64,
            }
        ],
        created_at="2026-09-03T05:00:00Z",
    )
    arguments = {
        "affected_coordinate_refs": [
            "delta_ref:network:test",
            "delta_ref:unaffected:test",
        ],
        "attempt": 1,
        "max_attempts": 3,
        "rollback_ref": "snapshot_ref:before:test",
        "verification_procedure": ["REOBSERVE_8D_STATE_FIELD"],
    }

    first = build_total_field_correction_contract(progress, **arguments)
    second = build_total_field_correction_contract(deepcopy(progress), **arguments)

    assert first == second
    assert first["state"] == "CORRECTION_CANDIDATE_READY"
    assert first["materialization_scope"] == ["delta_ref:network:test"]
    assert "delta_ref:unaffected:test" not in first["materialization_scope"]
    assert first["post_state_receipt_required"] is True
    assert first["operation_authority"] is False


def test_correction_contract_holds_after_attempt_limit():
    progress = build_total_field_progress_projection(
        founder_intent_ref="intent_ref:founder:test",
        founder_intent_sha256="b" * 64,
        target_state=_progress_observation("RECONSTRUCTED", "state_ref:target:test", "a" * 64),
        current_state=_progress_observation("OBSERVED", "state_ref:current:test", "c" * 64),
        reobserved_state=_progress_observation("OBSERVED", "state_ref:reobserved:test", "d" * 64),
        remaining_difference_refs=["delta_ref:network:test"],
        receipt_refs=["receipt_ref:observation:test"],
        node_observations=[
            {
                "node_id": "MSI",
                "state": "OBSERVED",
                "observed_at": "2026-09-03T05:00:00Z",
                "evidence_ref": "evidence_ref:msi:test",
                "evidence_sha256": "e" * 64,
            }
        ],
        created_at="2026-09-03T05:00:00Z",
    )

    result = build_total_field_correction_contract(
        progress,
        affected_coordinate_refs=["delta_ref:network:test"],
        attempt=4,
        max_attempts=3,
        rollback_ref="snapshot_ref:before:test",
        verification_procedure=["REOBSERVE_8D_STATE_FIELD"],
    )

    assert result["state"] == "HOLD_CORRECTION_ATTEMPTS_EXHAUSTED"
    assert result["materialization_scope"] == []
    assert result["divergence_policy"] == "QUARANTINE_AND_ROLLBACK"


def test_founder_dynamic_context_exposes_translation_and_progress_contracts():
    packet = build_dynamic_context(
        "自然語言總場進度",
        root=Path("."),
        identity_class="founder",
        max_items=8,
    )

    assert packet["state"] == "TOTAL_FIELD_DYNAMIC_CONTEXT_READY"
    assert packet["retrieval_method"] == "8DADI_MEMORY_INDEX_ONLY"
    assert packet["founder_intent_projection"]["D8"]["packet_self_authority"] is False
    assert packet["intent_translation_application_rules"]["provider_neutral"] is True
    assert packet["intent_translation_runtime_binding"]["profile_active"] is False
    assert packet["intent_translation_runtime_binding"]["formal_ingress_switched"] is False
    assert (
        packet["intent_translation_runtime_binding"]["profile_state"]
        == "HOLD_D8_AUTHORITY_NOT_APPROVED"
    )
    assert packet["progress_projection_contract"]["model_access"] == "READ_ONLY"
    assert packet["policy"]["workspace_search"] is False
