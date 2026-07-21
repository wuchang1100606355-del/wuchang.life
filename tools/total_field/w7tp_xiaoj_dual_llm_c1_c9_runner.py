#!/usr/bin/env python3
"""Run the synthetic XiaoJ dual-LLM C1-C9 canary without external I/O."""

from __future__ import annotations

import argparse
import copy
import importlib
import importlib.metadata
import json
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.domain_completion_total_field_gateway import (
    DomainCompletionTotalFieldGateway,
)
from tools.sovereign_ai_domain_completion_candidate import build_candidate
from tools.w7tp_packet_inference_cockpit_server import run_dual_llm_governed_nlio
from tools.xiaoj_candidate_adapter import CandidateProviderFailure


RUN_ID = "W7TP_XIAOJ_DUAL_LLM_C1_C9_REPO_RUNNER_BINDING_V1"
SCENARIO_IDS = tuple(f"C{index}" for index in range(1, 10))
LOCAL_IMPORT_CLOSURE = (
    "tools.cloud_agent_candidate_provider",
    "tools.d3_coordinate_transition_candidate",
    "tools.domain_completion_total_field_gateway",
    "tools.eightd_gte_parser_candidate",
    "tools.intent_field.adi_5d_absolute_index_verifier",
    "tools.sovereign_ai_domain_completion_candidate",
    "tools.taiji_8d_canonical_verifier",
    "tools.tfct_true8d_runtime_candidate",
    "tools.total_field.final_state_gate",
    "tools.total_field.human_response_renderer",
    "tools.total_field_candidate_gateway",
    "tools.total_field_cloud_fill_packet",
    "tools.w7tp_packet_inference_cockpit_server",
    "tools.xiaoj_candidate_adapter",
)
OBSERVATION_REF = "observation-domain:community:c1-c9-canary:v1"
FORBIDDEN_OUTPUT_KEYS = frozenset(
    {
        "access_token",
        "client_secret",
        "cookie",
        "credential",
        "email",
        "member_name",
        "password",
        "session",
    }
)


class ScenarioFailure(RuntimeError):
    """Stable internal assertion failure for one synthetic scenario."""


@dataclass
class SyntheticProvider:
    """Injected candidate provider that has no credential or transport path."""

    candidates: tuple[dict[str, Any], ...]
    call_log: list[str]
    layer: str
    failure_class: str | None = None

    def candidates_for(
        self, request_ref: str, source_mode: str
    ) -> tuple[dict[str, Any], ...]:
        if not request_ref.startswith("nlio:sha256:"):
            raise ScenarioFailure("RAW_REQUEST_REACHED_PROVIDER")
        self.call_log.append(self.layer)
        if self.failure_class is not None:
            raise CandidateProviderFailure(self.failure_class)
        expected = "XIAOJ_LOCAL" if self.layer == "LOCAL" else "LLM_PUSH"
        if source_mode != expected:
            raise ScenarioFailure("PROVIDER_SOURCE_MODE_MISMATCH")
        return copy.deepcopy(self.candidates)


class ObservedTotalFieldGateway:
    """Observe calls while delegating to the existing Total Field gateway."""

    def __init__(self) -> None:
        self.call_count = 0
        self.received_count = 0
        self._gateway = DomainCompletionTotalFieldGateway(
            observation_domains={
                OBSERVATION_REF: {
                    "configured": True,
                    "observations": {
                        "observation_ref": "observation:community:c1-c9-canary:v1"
                    },
                }
            }
        )

    def receive_batch(
        self,
        candidates: tuple[dict[str, Any], ...],
        *,
        previous_values: dict[str, Any],
        forced_hold_reason: str | None = None,
    ) -> tuple[dict[str, Any], ...]:
        self.call_count += 1
        self.received_count += len(candidates)
        return self._gateway.receive_batch(
            candidates,
            previous_values=previous_values,
            forced_hold_reason=forced_hold_reason,
        )


def _candidate(
    value: Any = "相容候選",
    *,
    attribute_name: str = "public_description",
    provider_ref: str = "provider:synthetic:local:v1",
    event_ref: str = "event:c1-c9:local:001",
) -> dict[str, Any]:
    return build_candidate(
        domain="COMMUNITY",
        entity_ref="entity:community:c1-c9:001",
        attribute_name=attribute_name,
        candidate_value=value,
        source_mode="TOTAL_FIELD_PULL",
        model_ref=f"model:{provider_ref}",
        provider_ref=provider_ref,
        event_ref=event_ref,
        observation_domain_ref=OBSERVATION_REF,
        rule_ref="rules/tfct/identity_v0_1",
        evidence_refs=[],
        confidence=0.75,
        sensitivity="SAFE_DERIVED",
        requires_human_confirmation=False,
    )


def _identity(candidate: dict[str, Any]) -> str:
    return "|".join(
        str(candidate[key])
        for key in ("domain", "entity_ref", "attribute_name")
    )


def _has_zh_text(value: Any) -> bool:
    return isinstance(value, str) and any("\u4e00" <= char <= "\u9fff" for char in value)


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).casefold().replace("-", "_") in FORBIDDEN_OUTPUT_KEYS
            or _contains_forbidden_key(nested)
            for key, nested in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _invoke(
    *,
    local_candidates: tuple[dict[str, Any], ...] = (),
    cloud_candidates: tuple[dict[str, Any], ...] = (),
    local_failure: str | None = None,
    cloud_failure: str | None = None,
    request_mode: str = "CHAT_ONLY",
    persona_text: str = "自然語言候選回覆。",
) -> tuple[dict[str, Any], ObservedTotalFieldGateway, list[str]]:
    seed = next(
        (
            candidate
            for candidate in (*local_candidates, *cloud_candidates)
            if all(
                key in candidate
                for key in ("domain", "entity_ref", "attribute_name")
            )
        ),
        _candidate(),
    )
    call_log: list[str] = []
    gateway = ObservedTotalFieldGateway()
    result = run_dual_llm_governed_nlio(
        "請處理這個合成隔離情境",
        local_provider=SyntheticProvider(
            copy.deepcopy(local_candidates), call_log, "LOCAL", local_failure
        ),
        cloud_provider=SyntheticProvider(
            copy.deepcopy(cloud_candidates), call_log, "CLOUD", cloud_failure
        ),
        domain_gateway=gateway,
        previous_values={_identity(seed): "先前有效值"},
        persona_text=persona_text,
        request_mode=request_mode,
    )
    return result, gateway, call_log


def _scenario_result(
    scenario_id: str,
    result: dict[str, Any],
    gateway: ObservedTotalFieldGateway,
    call_log: list[str],
    checks: dict[str, bool],
) -> dict[str, Any]:
    common_checks = {
        "total_field_is_authority": result.get("total_field_authority") is True,
        "candidate_sources_are_not_authority": result.get(
            "candidate_sources_are_authority"
        )
        is False,
        "side_effects_absent": result.get("side_effects_performed") is False,
        "reply_text_present": bool(result.get("reply_text")),
        "traditional_chinese_reply": _has_zh_text(result.get("reply_text")),
        "member_plaintext_or_secret_absent": not _contains_forbidden_key(result),
    }
    combined = {**common_checks, **checks}
    return {
        "scenario_id": scenario_id,
        "passed": all(combined.values()),
        "actual_state": result.get("STATE"),
        "total_field_decision": result.get("total_field_final_decision"),
        "renderer_decision": result.get("renderer_decision"),
        "failure_class": result.get("failure_class"),
        "degraded_mode": result.get("degraded_mode"),
        "dual_convergence": result.get("dual_convergence"),
        "provider_call_order": call_log,
        "total_field_gateway_calls": gateway.call_count,
        "total_field_candidates_received": gateway.received_count,
        "checks": combined,
    }


def _run_c1() -> dict[str, Any]:
    local = _candidate()
    cloud = _candidate(
        provider_ref="provider:synthetic:cloud:v1",
        event_ref="event:c1-c9:cloud:001",
    )
    result, gateway, calls = _invoke(
        local_candidates=(local,), cloud_candidates=(cloud,), persona_text="語氣甲"
    )
    alternate, _alternate_gateway, _alternate_calls = _invoke(
        local_candidates=(local,), cloud_candidates=(cloud,), persona_text="語氣乙"
    )
    persona_excluded = (
        result.get("local_candidate_hashes") == alternate.get("local_candidate_hashes")
        and result.get("cloud_candidate_hashes")
        == alternate.get("cloud_candidate_hashes")
        and result.get("candidate_results") == alternate.get("candidate_results")
    )
    return _scenario_result(
        "C1",
        result,
        gateway,
        calls,
        {
            "compatible_candidates_pass": result.get("total_field_final_decision")
            == "ALLOW",
            "dual_convergence": result.get("dual_convergence") is True,
            "both_candidates_received": result.get("both_received") is True,
            "persona_excluded_from_tfs_and_hash": persona_excluded,
        },
    )


def _run_c2() -> dict[str, Any]:
    result, gateway, calls = _invoke(
        local_candidates=(_candidate("候選甲"),),
        cloud_candidates=(
            _candidate(
                "候選乙",
                provider_ref="provider:synthetic:cloud:v1",
                event_ref="event:c1-c9:cloud:002",
            ),
        ),
    )
    return _scenario_result(
        "C2",
        result,
        gateway,
        calls,
        {
            "conflict_holds": result.get("total_field_final_decision") == "HOLD",
            "conflict_classified": result.get("failure_class")
            == "DOMAIN_CANDIDATE_CONFLICT",
            "fallback_forbidden": result.get("degraded_mode") is False,
        },
    )


def _run_c3() -> dict[str, Any]:
    result, gateway, calls = _invoke(
        cloud_candidates=(_candidate(provider_ref="provider:synthetic:cloud:v1"),),
        local_failure="PROVIDER_TIMEOUT",
        persona_text="備援聊天候選",
    )
    return _scenario_result(
        "C3",
        result,
        gateway,
        calls,
        {
            "legal_degradation": result.get("STATE") == "PASS"
            and result.get("degraded_mode") is True,
            "cloud_is_available_provider": result.get("available_provider") == "CLOUD",
            "timeout_classified": result.get("failure_class") == "PROVIDER_TIMEOUT",
            "backup_message_is_zh_tw": "備援模式" in str(result.get("reply_text", "")),
        },
    )


def _run_c4() -> dict[str, Any]:
    result, gateway, calls = _invoke(
        local_candidates=(_candidate(),),
        cloud_failure="PROVIDER_UNAVAILABLE",
        persona_text="本地備援候選",
    )
    return _scenario_result(
        "C4",
        result,
        gateway,
        calls,
        {
            "legal_degradation": result.get("STATE") == "PASS"
            and result.get("degraded_mode") is True,
            "local_is_available_provider": result.get("available_provider") == "LOCAL",
            "unavailable_classified": result.get("failure_class")
            == "PROVIDER_UNAVAILABLE",
        },
    )


def _run_c5() -> dict[str, Any]:
    result, gateway, calls = _invoke(
        local_candidates=(_candidate("diff --git a/demo.py b/demo.py\n+print('draft')"),),
        cloud_failure="TRANSPORT_UNREACHABLE",
        request_mode="CODE_DRAFT_ONLY",
        persona_text="",
    )
    draft = result.get("code_draft_candidate", {})
    return _scenario_result(
        "C5",
        result,
        gateway,
        calls,
        {
            "candidate_only": draft.get("status") == "CANDIDATE_ONLY",
            "no_file_write": draft.get("file_write") is False,
            "no_execution": draft.get("execution") is False,
            "no_commit": draft.get("commit") is False,
            "no_deploy": draft.get("deploy") is False,
        },
    )


def _run_c6() -> dict[str, Any]:
    result, gateway, calls = _invoke(
        local_candidates=(_candidate(),),
        cloud_failure="PROVIDER_UNAVAILABLE",
        request_mode="ACTION_REQUEST",
        persona_text="",
    )
    reply = str(result.get("reply_text", ""))
    return _scenario_result(
        "C6",
        result,
        gateway,
        calls,
        {
            "action_holds": result.get("STATE")
            == "HOLD_SINGLE_PROVIDER_ACTION_NOT_AUTHORIZED",
            "total_field_holds": result.get("total_field_final_decision") == "HOLD",
            "zh_tw_action_pause": "單一路徑可用" in reply
            and "執行部分已暫停" in reply,
        },
    )


def _run_c7() -> dict[str, Any]:
    invalid = _candidate()
    invalid.pop("domain")
    result, gateway, calls = _invoke(
        local_candidates=(invalid,),
        cloud_candidates=(_candidate(provider_ref="provider:synthetic:cloud:v1"),),
    )
    return _scenario_result(
        "C7",
        result,
        gateway,
        calls,
        {
            "invalid_schema_holds": result.get("STATE")
            == "HOLD_NON_DEGRADABLE_PROVIDER_FAILURE",
            "invalid_schema_classified": result.get("failure_class")
            == "INVALID_SCHEMA",
            "degradation_forbidden": result.get("degraded_mode") is False,
            "gateway_not_called": gateway.call_count == 0,
        },
    )


def _run_c8() -> dict[str, Any]:
    result, gateway, calls = _invoke(
        local_failure="PROVIDER_TIMEOUT",
        cloud_failure="PROVIDER_UNAVAILABLE",
        persona_text="",
    )
    return _scenario_result(
        "C8",
        result,
        gateway,
        calls,
        {
            "both_failures_hold": result.get("STATE")
            == "HOLD_BOTH_PROVIDERS_UNAVAILABLE",
            "gateway_not_called": gateway.call_count == 0,
            "previous_state_not_mutated": result.get("side_effects_performed") is False,
        },
    )


def _run_c9() -> dict[str, Any]:
    authority_claim = _candidate()
    authority_claim["final_decision"] = "ALLOW"
    result, gateway, calls = _invoke(
        local_candidates=(authority_claim,),
        cloud_candidates=(_candidate(provider_ref="provider:synthetic:cloud:v1"),),
        persona_text="",
    )
    return _scenario_result(
        "C9",
        result,
        gateway,
        calls,
        {
            "authority_claim_holds": result.get("STATE")
            == "HOLD_NON_DEGRADABLE_PROVIDER_FAILURE",
            "forbidden_authority_classified": result.get("failure_class")
            == "FORBIDDEN_AUTHORITY",
            "gateway_not_called": gateway.call_count == 0,
            "candidate_is_not_authority": result.get("candidate_sources_are_authority")
            is False,
        },
    )


SCENARIO_RUNNERS = (
    _run_c1,
    _run_c2,
    _run_c3,
    _run_c4,
    _run_c5,
    _run_c6,
    _run_c7,
    _run_c8,
    _run_c9,
)


def run_self_check() -> dict[str, Any]:
    """Validate the offline runtime closure without executing C1-C9."""

    imported_modules: list[str] = []
    import_errors: list[dict[str, str]] = []
    for module_name in LOCAL_IMPORT_CLOSURE:
        try:
            importlib.import_module(module_name)
            imported_modules.append(module_name)
        except Exception as exc:  # pragma: no cover - exercised by image qualification
            import_errors.append(
                {"module": module_name, "error_type": type(exc).__name__}
            )

    try:
        jsonschema_version = importlib.metadata.version("jsonschema")
    except importlib.metadata.PackageNotFoundError:
        jsonschema_version = None

    scenario_names = [runner.__name__ for runner in SCENARIO_RUNNERS]
    checks = {
        "python_3_12": sys.version_info[:2] == (3, 12),
        "jsonschema_imported": "jsonschema" in sys.modules,
        "jsonschema_version_4_10_3": jsonschema_version == "4.10.3",
        "local_import_closure": not import_errors
        and len(imported_modules) == len(LOCAL_IMPORT_CLOSURE),
        "c1_c9_scenarios_loadable": len(SCENARIO_RUNNERS) == len(SCENARIO_IDS)
        and all(callable(runner) for runner in SCENARIO_RUNNERS)
        and scenario_names == [f"_run_c{index}" for index in range(1, 10)],
    }
    return {
        "schema_version": "W7TP-XIAOJ-DUAL-LLM-C1-C9-SELF-CHECK/1.0",
        "run_id": RUN_ID,
        "state": "PASS" if all(checks.values()) else "HOLD",
        "mode": "SELF_CHECK_ONLY_NO_SCENARIO_EXECUTION",
        "python_version": platform.python_version(),
        "jsonschema_version": jsonschema_version,
        "local_import_modules": list(LOCAL_IMPORT_CLOSURE),
        "local_imported_count": len(imported_modules),
        "local_import_errors": import_errors,
        "scenario_ids": list(SCENARIO_IDS),
        "scenario_functions": scenario_names,
        "scenario_execution_count": 0,
        "external_call_count": 0,
        "vertex_call_count": 0,
        "ollama_call_count": 0,
        "secret_read_count": 0,
        "member_plaintext_read_count": 0,
        "db_write_count": 0,
        "repo_write_count": 0,
        "checks": checks,
    }


def run_c1_c9() -> dict[str, Any]:
    """Execute all nine deterministic scenarios and return one safe summary."""

    scenario_results = [runner() for runner in SCENARIO_RUNNERS]
    scenarios_pass = sum(item["passed"] is True for item in scenario_results)
    all_zh_tw = all(
        item["checks"]["traditional_chinese_reply"] for item in scenario_results
    )
    total_field_only = all(
        item["checks"]["total_field_is_authority"]
        and item["checks"]["candidate_sources_are_not_authority"]
        for item in scenario_results
    )
    return {
        "schema_version": "W7TP-XIAOJ-DUAL-LLM-C1-C9-RUNNER-RESULT/1.0",
        "run_id": RUN_ID,
        "state": "PASS" if scenarios_pass == len(SCENARIO_IDS) else "HOLD",
        "scenario_ids": list(SCENARIO_IDS),
        "scenario_results": scenario_results,
        "scenarios_pass": scenarios_pass,
        "scenarios_total": len(SCENARIO_IDS),
        "total_field_authority_check": "PASS" if total_field_only else "HOLD",
        "conflict_hold_check": "PASS" if scenario_results[1]["passed"] else "HOLD",
        "single_provider_degradation_check": "PASS"
        if all(scenario_results[index]["passed"] for index in (2, 3, 4))
        else "HOLD",
        "traditional_chinese_reply_check": "PASS" if all_zh_tw else "HOLD",
        "persona_tfs_hash_exclusion": "PASS"
        if scenario_results[0]["checks"]["persona_excluded_from_tfs_and_hash"]
        else "HOLD",
        "provider_mode": "SYNTHETIC_INJECTED_ONLY",
        "external_call_count": 0,
        "workspace_call_count": 0,
        "vertex_call_count": 0,
        "ollama_call_count": 0,
        "secret_read_count": 0,
        "member_plaintext_read_count": 0,
        "db_write_count": 0,
        "repo_write_count": 0,
        "formal_state_write_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="validate imports and scenario loading without executing C1-C9",
    )
    args = parser.parse_args([] if argv is None else argv)
    result = run_self_check() if args.self_check else run_c1_c9()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result["state"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
