"""Single XiaoJ local 8B pipeline with optional governed cloud candidates."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from tools.cloud_agent_candidate_provider import (
    GCPCloudCandidateProvider,
    OllamaCloudCandidateProvider,
)
from tools.total_field.human_response_renderer import render_human_response
from tools.total_field.xiaoj_fusion_rules import (
    CLOUD_SOURCE,
    DEFAULT_ACCEPTANCE_CRITERIA,
    LOCAL_SOURCE,
    RULE_CAPSULE_REF,
)
from tools.total_field_candidate_gateway import decide_candidates, receive_candidate
from tools.total_field_cloud_fill_packet import CloudFillPacketBroker
from tools.xiaoj_candidate_adapter import (
    build_local_candidate,
    open_low_complexity_fillable_paths,
)


class XiaojFusionPipeline:
    """Coordinate one physical local 8B model and Candidate-only cloud providers."""

    def __init__(
        self,
        *,
        cloud_broker: CloudFillPacketBroker | None = None,
        cloud_provider: Any | None = None,
        cloud_providers: Sequence[Any] | None = None,
        receiver: Callable[[Mapping[str, Any], str | None], dict[str, Any]] | None = None,
    ) -> None:
        self.cloud_broker = cloud_broker or CloudFillPacketBroker()
        if cloud_provider is not None:
            self.cloud_providers = [cloud_provider]
        elif cloud_providers is not None:
            self.cloud_providers = list(cloud_providers)
        else:
            self.cloud_providers = [
                OllamaCloudCandidateProvider(),
                GCPCloudCandidateProvider(),
            ]
        self.receiver = receiver or receive_candidate

    def run(
        self,
        user_text: str,
        *,
        identity_profile: Mapping[str, Any] | None = None,
        acceptance_criteria: Mapping[str, Any] | None = None,
        frontbrain_quality: float | None = None,
        backbrain_fields: Mapping[str, Any] | None = None,
        expected_cloud_quality_gain: float = 0.0,
        cloud_cost: float = 0.0,
        active_cloud_use_threshold: float = 0.0,
    ) -> dict[str, Any]:
        # backbrain_fields is retained only for API compatibility; no second model is invoked.
        _ = backbrain_fields
        criteria = {**DEFAULT_ACCEPTANCE_CRITERIA, **dict(acceptance_criteria or {})}
        quality_threshold = float(criteria.get("quality_threshold", 0.8))
        context_packets = pull_identity_8d_packets(identity_profile)

        receipts: list[dict[str, Any]] = []
        local_candidate = build_local_candidate(
            user_text,
            context_packets=context_packets,
            acceptance_criteria=criteria,
            quality_score=frontbrain_quality,
        )
        receipts.append(self.receiver(local_candidate, LOCAL_SOURCE))

        local_quality = _best_quality(receipts)
        cloud_request: dict[str, Any] | None = None
        cloud_called = False
        cloud_provider_used: str | None = None
        provider_states: dict[str, str] = {}
        request_hash = _sha256_obj(
            {
                "user_text": user_text,
                "criteria": criteria,
                "identity_ref": _identity_ref(identity_profile),
            }
        )
        rule_capsule_hash = _sha256_obj(RULE_CAPSULE_REF)

        if local_quality < quality_threshold:
            fillable_paths = open_low_complexity_fillable_paths(local_candidate)
            broker_result = self.cloud_broker.pull_request(
                request_hash=request_hash,
                rule_capsule_hash=rule_capsule_hash,
                locked_fields=_locked_fields(identity_profile),
                fillable_paths=fillable_paths,
                minimal_context=_minimal_deidentified_context(user_text, context_packets),
                acceptance_criteria=criteria,
                expected_quality_gain=expected_cloud_quality_gain,
                cost=cloud_cost,
                active_cloud_use_threshold=active_cloud_use_threshold,
            )
            cloud_request = broker_result
            cached_candidate = broker_result.get("cached_candidate")
            if cached_candidate is not None:
                receipts.append(self.receiver(cached_candidate, CLOUD_SOURCE))
            elif broker_result.get("should_call_cloud") and broker_result.get("packet"):
                for provider in self.cloud_providers:
                    name = str(getattr(provider, "provider_name", provider.__class__.__name__))
                    cloud_candidate = provider.provide_candidate(broker_result["packet"])
                    provider_states[name] = str(getattr(provider, "state", "UNKNOWN"))
                    if cloud_candidate is None:
                        continue
                    cloud_called = True
                    cloud_provider_used = name
                    receipt = self.receiver(cloud_candidate, CLOUD_SOURCE)
                    receipts.append(receipt)
                    if receipt.get("accepted"):
                        self.cloud_broker.remember_candidate(
                            cloud_candidate,
                            request_hash=request_hash,
                            rule_capsule_hash=rule_capsule_hash,
                        )
                    else:
                        self.cloud_broker.mark_invalid_packet(broker_result["packet"])
                    break

        decision = decide_candidates(
            receipts,
            acceptance_threshold=quality_threshold,
            acceptance_criteria=criteria,
        )
        return {
            "human_response": render_human_response(decision),
            "decision": decision,
            "candidate_receipts": receipts,
            "context_packets": context_packets,
            "cloud_request": cloud_request,
            "cloud_called": cloud_called,
            "cloud_provider_used": cloud_provider_used,
            "cloud_provider_states": provider_states,
            "request_hash": request_hash,
        }


def pull_identity_8d_packets(identity_profile: Mapping[str, Any] | None) -> dict[str, Any]:
    """Project the current work cell using the Founder-defined 8D ADI V2.3 dimensions."""
    identity_ref = _identity_ref(identity_profile)
    return {
        "D1_INTENT": {"source": "user_natural_language"},
        "D2_STATE": {"state": "candidate_construction"},
        "D3_COORDINATE": {"scope": "CURRENT_WORK_CELL"},
        "D4_EVIDENCE": {"evidence_scope": "local_only"},
        "D5_EXECUTION_POLICY": {"execution": "CANDIDATE_ONLY_NO_EFFECT"},
        "D6_GENERATIVE_STATE_TRANSMISSION": {
            "used": False,
            "cloud_inference_is_d6": False,
        },
        "D7_RISK_ISOLATION": {
            "cloud": "candidate_only_deidentified",
            "fail_closed": True,
        },
        "D8_ENVELOPE_AUTHORITY": {
            "identity_ref": identity_ref,
            "authority": "CANDIDATE_ONLY",
            "rule_capsule_ref": RULE_CAPSULE_REF,
        },
    }


def _best_quality(receipts: list[Mapping[str, Any]]) -> float:
    qualities = [
        float(receipt.get("candidate", {}).get("quality_score", 0.0))
        for receipt in receipts
        if receipt.get("accepted")
    ]
    return max(qualities, default=0.0)


def _identity_ref(identity_profile: Mapping[str, Any] | None) -> str:
    if not identity_profile:
        return "anonymous-local-user"
    return str(identity_profile.get("identity_ref") or identity_profile.get("user_id") or "anonymous-local-user")


def _locked_fields(identity_profile: Mapping[str, Any] | None) -> dict[str, Any]:
    return {
        "identity.identity_ref": _identity_ref(identity_profile),
        "authority.total_field": "sole_system_decision_gate",
        "decision.execution": "not_authorized_by_candidate",
    }


def _minimal_deidentified_context(user_text: str, context_packets: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "intent_hash": _sha256_obj(user_text),
        "intent_length": len(user_text),
        "language": "zh-TW",
        "packet_refs": sorted(context_packets),
    }


def _sha256_obj(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()
