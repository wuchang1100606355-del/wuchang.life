import json

import pytest

from tools.cloud_agent_candidate_provider import (
    GCPCloudCandidateProvider,
    OllamaCloudCandidateProvider,
)
from tools.total_field.xiaoj_fusion_rules import (
    CLOUD_REQUEST_ALLOWED_KEYS,
    LOCAL_PRIMARY_MODEL,
)
from tools.total_field_candidate_gateway import decide_candidates, receive_candidate
from tools.xiaoj_candidate_adapter import build_backbrain_candidate
from tools.xiaoj_fusion_pipeline import XiaojFusionPipeline, pull_identity_8d_packets


def test_single_physical_local_model_is_qwen3_abliterated_8b():
    assert LOCAL_PRIMARY_MODEL["physical_model_count"] == 1
    assert LOCAL_PRIMARY_MODEL["model"] == "xiaoj:latest"
    assert LOCAL_PRIMARY_MODEL["base_model"] == "huihui_ai/qwen3-abliterated:8b"
    assert LOCAL_PRIMARY_MODEL["contextLength"] == 8192


def test_legacy_physical_backbrain_is_disabled():
    with pytest.raises(RuntimeError, match="HOLD_BACKBRAIN_DISABLED_SINGLE_8B"):
        build_backbrain_candidate(["draft.style_polish"], {"draft.style_polish": "x"})


def test_founder_defined_v23_dimension_mapping_is_preserved():
    packet = pull_identity_8d_packets({"identity_ref": "opaque-owner-ref"})
    assert list(packet) == [
        "D1_INTENT",
        "D2_STATE",
        "D3_COORDINATE",
        "D4_EVIDENCE",
        "D5_EXECUTION_POLICY",
        "D6_GENERATIVE_STATE_TRANSMISSION",
        "D7_RISK_ISOLATION",
        "D8_ENVELOPE_AUTHORITY",
    ]
    assert packet["D6_GENERATIVE_STATE_TRANSMISSION"]["cloud_inference_is_d6"] is False
    assert packet["D8_ENVELOPE_AUTHORITY"]["authority"] == "CANDIDATE_ONLY"


def test_local_quality_sufficient_does_not_call_cloud():
    calls = []

    def client(packet):
        calls.append(packet)
        return {"patch": {"response": {"natural_zh_tw": "雲端不應被呼叫。"}}, "quality_score": 0.99}

    pipeline = XiaojFusionPipeline(cloud_provider=GCPCloudCandidateProvider(client))
    result = pipeline.run(
        "請直接整理這個本地可完成的需求",
        frontbrain_quality=0.92,
        acceptance_criteria={"quality_threshold": 0.8},
        expected_cloud_quality_gain=1.0,
        cloud_cost=0.0,
    )
    assert calls == []
    assert result["cloud_called"] is False
    assert result["decision"]["accepted"] is True


def test_quality_gap_builds_minimal_deidentified_cloud_fill_packet():
    packets = []

    def client(packet):
        packets.append(packet)
        return {
            "patch": {"response": {"natural_zh_tw": "雲端填空候選已回總場。"}},
            "quality_score": 0.95,
        }

    pipeline = XiaojFusionPipeline(cloud_provider=GCPCloudCandidateProvider(client))
    result = pipeline.run(
        "短",
        identity_profile={"identity_ref": "OWNER-001", "token": "DO_NOT_EXPOSE"},
        frontbrain_quality=0.2,
        acceptance_criteria={"quality_threshold": 0.9},
        expected_cloud_quality_gain=0.8,
        cloud_cost=0.1,
    )
    assert result["cloud_called"] is True
    packet = packets[0]
    assert set(packet) <= CLOUD_REQUEST_ALLOWED_KEYS
    serialized = json.dumps(packet, ensure_ascii=False, sort_keys=True)
    assert "短" not in serialized
    assert "DO_NOT_EXPOSE" not in serialized
    assert "OWNER-001" not in serialized
    assert "value_hash" in serialized


def test_ollama_cloud_is_candidate_only_with_injected_client():
    provider = OllamaCloudCandidateProvider(
        lambda _packet: {
            "patch": {"response": {"natural_zh_tw": "Ollama Cloud 候選。"}},
            "quality_score": 0.96,
        },
        model="example-cloud-model",
    )
    candidate = provider.provide_candidate({"return_schema": "Candidate"})
    assert candidate is not None
    assert candidate["authority"] == "CANDIDATE_ONLY"
    assert candidate["source"] == "cloud"
    assert candidate["metadata"]["provider"] == "OLLAMA_CLOUD"
    assert candidate["metadata"]["cloud_inference_is_d6"] is False
    assert candidate["metadata"]["external_effect"] is False


def test_cloud_result_enters_receiver_after_single_local_8b():
    received_sources = []

    def client(_packet):
        return {
            "patch": {"response": {"natural_zh_tw": "雲端候選經總場接收後才參與裁決。"}},
            "quality_score": 0.96,
        }

    def receiver(candidate, source=None):
        received_sources.append(source or candidate.get("source"))
        return receive_candidate(candidate, source)

    pipeline = XiaojFusionPipeline(
        cloud_provider=OllamaCloudCandidateProvider(client, model="example-cloud-model"),
        receiver=receiver,
    )
    result = pipeline.run(
        "短",
        frontbrain_quality=0.2,
        acceptance_criteria={"quality_threshold": 0.9},
        expected_cloud_quality_gain=0.8,
        cloud_cost=0.1,
    )
    assert received_sources == ["local_8b", "cloud"]
    assert result["cloud_provider_used"] == "OLLAMA_CLOUD"
    assert result["decision"]["candidate_source"] == "cloud"


def test_unverified_assumption_cannot_enter_execution():
    receipt = receive_candidate(
        {
            "source": "local_8b",
            "authority": "CANDIDATE_ONLY",
            "patch": {"response": {"natural_zh_tw": "含未驗證權限假設的候選。"}},
            "quality_score": 0.99,
            "assumptions": [
                {
                    "assumption_id": "A1",
                    "affects": ["authority.permission"],
                    "verified": False,
                }
            ],
        },
        "local_8b",
    )
    assert receipt["accepted"] is True
    assert receipt["execution_allowed"] is False
    decision = decide_candidates([receipt], acceptance_threshold=0.8)
    assert decision["accepted"] is False
    assert decision["reason"] == "no_executable_candidate"


def test_valid_cached_cloud_candidate_is_reused_without_second_cloud_call():
    calls = []

    def client(packet):
        calls.append(packet)
        return {
            "patch": {"response": {"natural_zh_tw": "有效快取候選。"}},
            "quality_score": 0.95,
        }

    provider = GCPCloudCandidateProvider(client)
    pipeline = XiaojFusionPipeline(cloud_provider=provider)
    kwargs = {
        "frontbrain_quality": 0.2,
        "acceptance_criteria": {"quality_threshold": 0.9},
        "expected_cloud_quality_gain": 0.8,
        "cloud_cost": 0.1,
    }
    first = pipeline.run("短", **kwargs)
    second = pipeline.run("短", **kwargs)
    assert first["cloud_called"] is True
    assert second["cloud_called"] is False
    assert len(calls) == 1
    assert second["cloud_request"]["reason"] == "valid_cached_candidate_reused"
