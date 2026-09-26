"""T-011B Dynamic Context + Member Sovereign Context -> MSI LLM adapter.

Candidate-only. Reuses existing Dynamic Context, T-011A member sovereignty,
resource arbitration, capability internalization, and Total Field authority.
It creates no runtime effect and no second 8D/D8/GST/Total Field.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from core.capability_internalization import select_internalized_capabilities
from tools.total_field_candidate_gateway import llm_push
from tools.total_field_dynamic_context_pull import (
    RESULT_SCHEMA,
    canonical_sha256 as dynamic_sha256,
    validate_model_visible_context,
)


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "configs/total_field/w7tp_msi_llm_model_selection_contract_v1.json"
CONTRACT_SCHEMA_PATH = ROOT / "schemas/field/w7tp_msi_llm_model_selection_contract_v1.schema.json"
RETURN_SCHEMA_PATH = ROOT / "schemas/field/w7tp_local_llm_candidate_return_v1.schema.json"
REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/+:-]{0,511}$")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)09\d{2}[- ]?\d{3}[- ]?\d{3}(?!\d)")
SECRET_RE = re.compile(r"(?:Bearer\s+[A-Za-z0-9._~+/-]{8,}|sk-[A-Za-z0-9_-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)", re.IGNORECASE)
ModelTransport = Callable[[str, str, list[dict[str, Any]], int], Mapping[str, Any]]


class MSILLMCandidateHold(RuntimeError):
    """Fail-closed T-011B candidate outcome."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise MSILLMCandidateHold(code)


def _ref(value: Any, code: str) -> str:
    _require(isinstance(value, str) and REF_RE.fullmatch(value) is not None, code)
    return str(value)


def _load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise MSILLMCandidateHold(code) from exc
    _require(isinstance(value, dict), code)
    return value


def _validate_with_schema(value: Mapping[str, Any], schema_path: Path, code: str) -> None:
    schema = _load_json(schema_path, code)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(dict(value)),
        key=lambda item: list(item.path),
    )
    if errors:
        raise MSILLMCandidateHold(code)


def load_model_selection_contract(
    contract_path: Path = CONTRACT_PATH,
    schema_path: Path = CONTRACT_SCHEMA_PATH,
) -> dict[str, Any]:
    contract = _load_json(contract_path, "HOLD_T011B_MODEL_SELECTION_CONTRACT_READ")
    _validate_with_schema(
        contract,
        schema_path,
        "HOLD_T011B_MODEL_SELECTION_CONTRACT_SCHEMA",
    )
    authority = contract["authority_boundary"]
    data = contract["data_boundary"]
    _require(
        authority["provider_authority"] is False
        and authority["model_authority"] is False
        and authority["codex_authority"] is False
        and authority["browser_authority"] is False
        and authority["canonical"] is False
        and authority["runtime_effect"] is False
        and authority["formal_effect_boundary"] == "TAIJI01_TOTAL_FIELD",
        "HOLD_T011B_AUTHORITY_BOUNDARY_DRIFT",
    )
    _require(
        data["member_plaintext_to_model"] is False
        and data["secret_to_model"] is False
        and data["credential_to_model"] is False
        and data["raw_browser_page_to_model"] is False
        and data["member_context_mode"] == "OPAQUE_REFERENCES_ONLY"
        and data["dynamic_context_persistence"] is False,
        "HOLD_T011B_DATA_BOUNDARY_DRIFT",
    )
    return copy.deepcopy(contract)


def _validate_dynamic_pull_result(value: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(value, Mapping), "HOLD_T011B_DYNAMIC_CONTEXT_RESULT_REQUIRED")
    result = copy.deepcopy(dict(value))
    _require(result.get("schema_version") == RESULT_SCHEMA, "HOLD_T011B_DYNAMIC_CONTEXT_SCHEMA")
    authority = result.get("authority")
    _require(isinstance(authority, Mapping), "HOLD_T011B_DYNAMIC_CONTEXT_AUTHORITY_REQUIRED")
    _require(
        authority.get("provider_authority") is False
        and authority.get("model_authority") is False
        and authority.get("candidate_only") is True
        and authority.get("formal_effect_authority") == "LOCAL_TOTAL_FIELD",
        "HOLD_T011B_DYNAMIC_CONTEXT_AUTHORITY_DRIFT",
    )
    persistence = result.get("persistence_policy")
    _require(isinstance(persistence, Mapping), "HOLD_T011B_DYNAMIC_CONTEXT_PERSISTENCE_REQUIRED")
    _require(
        persistence.get("dynamic_context_persistence_allowed") is False
        and persistence.get("full_state_persistence_allowed") is False
        and persistence.get("personal_plaintext_persistence_allowed") is False
        and persistence.get("credential_persistence_allowed") is False,
        "HOLD_T011B_DYNAMIC_CONTEXT_PERSISTENCE_DRIFT",
    )
    context = validate_model_visible_context(result.get("model_visible_context"))
    supplied_hash = result.get("pull_result_sha256")
    basis = copy.deepcopy(result)
    basis.pop("pull_result_sha256", None)
    _require(
        supplied_hash == dynamic_sha256(basis),
        "HOLD_T011B_DYNAMIC_CONTEXT_RESULT_HASH_MISMATCH",
    )
    result["model_visible_context"] = context
    return result


def _validate_member_context(value: Mapping[str, Any]) -> dict[str, Any]:
    context = validate_model_visible_context(value)
    projection = context["state_projection"]
    member = projection.get("member_sovereign_context")
    _require(isinstance(member, Mapping), "HOLD_T011B_MEMBER_CONTEXT_REQUIRED")
    data = member.get("data_boundary")
    authority = member.get("authority_route")
    _require(isinstance(data, Mapping), "HOLD_T011B_MEMBER_DATA_BOUNDARY_REQUIRED")
    _require(isinstance(authority, Mapping), "HOLD_T011B_MEMBER_AUTHORITY_ROUTE_REQUIRED")
    _require(
        data.get("model_visible_member_data") == "OPAQUE_REFERENCES_ONLY"
        and data.get("plaintext_policy") == "LOCAL_ONLY_NEVER_MODEL_VISIBLE"
        and data.get("reconstruction_policy") == "NO_AUTOMATIC_PLAINTEXT_RECONSTRUCTION"
        and data.get("dynamic_context_persistence") == "REFERENCES_ONLY",
        "HOLD_T011B_MEMBER_DATA_BOUNDARY_DRIFT",
    )
    _require(
        authority.get("candidate_authority") == "NONE"
        and authority.get("provider_authority") == "NONE"
        and authority.get("model_authority") == "NONE"
        and authority.get("formal_effect_route") == "EXISTING_TAIJI01_TOTAL_FIELD",
        "HOLD_T011B_MEMBER_AUTHORITY_DRIFT",
    )
    return context


def combine_model_visible_contexts(
    dynamic_context_pull_result: Mapping[str, Any],
    member_model_visible_context: Mapping[str, Any],
) -> dict[str, Any]:
    dynamic_result = _validate_dynamic_pull_result(dynamic_context_pull_result)
    dynamic_context = dynamic_result["model_visible_context"]
    member_context = _validate_member_context(member_model_visible_context)
    member_projection = member_context["state_projection"]["member_sovereign_context"]

    state_projection = {
        "dynamic_context_projection": copy.deepcopy(dynamic_context["state_projection"]),
        "member_sovereign_context": copy.deepcopy(member_projection),
    }
    refs = {}
    for field in (
        "evidence_refs",
        "capability_refs",
        "acceptance_conditions",
        "schema_refs",
        "interface_refs",
        "non_core_rule_capsule_refs",
    ):
        refs[field] = sorted(
            set(dynamic_context[field]).union(member_context[field])
        )
    seed = {
        "state_projection": state_projection,
        **refs,
    }
    combined = {
        "context_ref": "t011bctx:sha256:" + canonical_sha256(seed),
        "state_projection": state_projection,
        **refs,
    }
    return validate_model_visible_context(combined)


def _resource_item(resource_decision: Mapping[str, Any], provider_ref: str) -> Mapping[str, Any]:
    for item in resource_decision.get("RESOURCE_COORDINATES", []):
        if isinstance(item, Mapping) and item.get("RESOURCE_ID") == provider_ref:
            return item
    raise MSILLMCandidateHold("HOLD_T011B_MSI_RESOURCE_COORDINATE_MISSING")


def select_msi_llm_model(
    *,
    resource_decision: Mapping[str, Any],
    combined_context: Mapping[str, Any],
    task_ref: str,
    intent_ref: str,
    contract_path: Path = CONTRACT_PATH,
) -> dict[str, Any]:
    contract = load_model_selection_contract(contract_path)
    task = _ref(task_ref, "HOLD_T011B_TASK_REF_INVALID")
    intent = _ref(intent_ref, "HOLD_T011B_INTENT_REF_INVALID")
    context = validate_model_visible_context(combined_context)
    provider = contract["provider_ref"]
    policy = contract["selection_policy"]
    qualified = set(resource_decision.get("QUALIFIED_SET") or [])
    preferred = set(resource_decision.get("PREFERRED_SET") or [])
    if policy["qualified_provider_required"]:
        _require(provider in qualified, "HOLD_T011B_MSI_PROVIDER_NOT_QUALIFIED")
    if policy["preferred_provider_required"]:
        _require(provider in preferred, "HOLD_T011B_MSI_PROVIDER_NOT_PREFERRED")


    resource = _resource_item(resource_decision, provider)
    _require(
        resource.get("CURRENT_STATE") == contract["required_resource_state"],
        "HOLD_T011B_MSI_RESOURCE_NOT_AVAILABLE",
    )
    capabilities = set(resource.get("CAPABILITY_SET") or [])
    _require(
        set(contract["required_capabilities"]).issubset(capabilities),
        "HOLD_T011B_MSI_CAPABILITY_SET_INCOMPLETE",
    )
    _require(
        resource.get("AUTHORITY_CLASS") == "CANDIDATE_ONLY_NOT_D8",
        "HOLD_T011B_MSI_RESOURCE_AUTHORITY_DRIFT",
    )

    internalized = select_internalized_capabilities(
        d3_node=policy["d3_node"],
        d5_modes=[policy["d5_mode"]],
        required_tags=["CODE"],
    )
    _require(
        contract["internalized_capability_id"]
        in internalized["selected_capability_ids"],
        "HOLD_T011B_INTERNALIZED_LLM_CAPABILITY_MISSING",
    )
    _require(
        internalized["authority_boundary"]["provider_authority"] is False
        and internalized["authority_boundary"]["total_field_verify_required"] is True,
        "HOLD_T011B_INTERNALIZED_AUTHORITY_DRIFT",
    )

    context_sha = canonical_sha256(context)
    selection = {
        "state": "PASS_T011B_MSI_LLM_MODEL_SELECTION_CANDIDATE",
        "task_ref": task,
        "intent_ref": intent,
        "provider_ref": provider,
        "model_ref": contract["model_ref"],
        "endpoint_env": contract["endpoint_env"],
        "endpoint_candidates": copy.deepcopy(
            sorted(contract["endpoint_candidates"], key=lambda item: item["priority"])
        ),
        "preferred_provider_observed": provider in preferred,
        "context_ref": context["context_ref"],
        "context_sha256": context_sha,
        "model_visible_context": copy.deepcopy(context),
        "model_visible_context_persistence_allowed": False,
        "candidate_only": True,
        "runtime_effect": False,
        "provider_authority": False,
        "model_authority": False,
        "requires_total_field_verify": True,
        "formal_effect_boundary": "TAIJI01_TOTAL_FIELD",
        "return_coordinate": contract["candidate_return"]["return_coordinate"],
        "max_candidate_chars": contract["candidate_return"]["max_candidate_chars"],
        "selection_sha256": "",
    }
    hash_basis = copy.deepcopy(selection)
    hash_basis.pop("selection_sha256", None)
    hash_basis.pop("model_visible_context", None)
    selection["selection_sha256"] = canonical_sha256(hash_basis)
    return selection


def _model_messages(selection: Mapping[str, Any]) -> list[dict[str, Any]]:
    model_context = validate_model_visible_context(
        selection["model_visible_context"]
    )
    system = (
        "You are a candidate-only local reasoning organ inside W7TP/8D ADI. "
        "Use only the supplied reference-only context. Never infer or reconstruct "
        "natural-person plaintext, secrets, credentials, authority, consent, or "
        "browser page contents. Do not execute tools or actions. Return only a "
        "small JSON candidate with keys candidate_summary, next_interface, risk_flags. "
        "All formal effects remain with the existing taiji01 Total Field."
    )
    user_payload = {
        "operation": "T011B_REFERENCE_ONLY_CANDIDATE_REASONING",
        "task_ref": selection["task_ref"],
        "intent_ref": selection["intent_ref"],
        "context_ref": selection["context_ref"],
        "model_visible_context": model_context,
    }
    return [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": json.dumps(
                user_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        },
    ]


def _endpoint_has_model(url: str, model: str, timeout: int = 3) -> bool:
    request = urllib.request.Request(
        url.rstrip("/") + "/api/tags",
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (
        OSError,
        TimeoutError,
        urllib.error.URLError,
        json.JSONDecodeError,
    ):
        return False
    models = value.get("models") if isinstance(value, Mapping) else None
    if not isinstance(models, list):
        return False
    return any(
        isinstance(item, Mapping)
        and (item.get("name") == model or item.get("model") == model)
        for item in models
    )


def _select_ollama_endpoint(
    selection: Mapping[str, Any],
    *,
    explicit_url: str | None,
    probe: bool,
) -> dict[str, Any]:
    if explicit_url:
        return {
            "ref": "EXPLICIT_TEST_OR_OPERATOR_ENDPOINT",
            "url": explicit_url,
            "priority": 0,
            "transport": "EXPLICIT",
        }
    candidates = selection.get("endpoint_candidates")
    _require(
        isinstance(candidates, list) and bool(candidates),
        "HOLD_T011B_ENDPOINT_CANDIDATES_REQUIRED",
    )
    ordered = sorted(candidates, key=lambda item: int(item["priority"]))
    if not probe:
        return copy.deepcopy(ordered[0])
    for item in ordered:
        if _endpoint_has_model(
            str(item["url"]),
            str(selection["model_ref"]),
        ):
            return copy.deepcopy(item)
    raise MSILLMCandidateHold("HOLD_T011B_NO_REACHABLE_MSI_OLLAMA_ENDPOINT")


def _default_transport(
    url: str,
    model: str,
    messages: list[dict[str, Any]],
    timeout: int,
) -> Mapping[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "keep_alive": "30s",
        "options": {"temperature": 0},
    }
    request = urllib.request.Request(
        url.rstrip("/") + "/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (
        OSError,
        TimeoutError,
        urllib.error.URLError,
        json.JSONDecodeError,
    ) as exc:
        raise MSILLMCandidateHold("HOLD_T011B_MSI_MODEL_CALL_FAILED") from exc
    _require(isinstance(value, Mapping), "HOLD_T011B_MSI_MODEL_RESPONSE_INVALID")
    return value


def _scan_output(text: str) -> list[str]:
    hits: list[str] = []
    if EMAIL_RE.search(text):
        hits.append("EMAIL_LITERAL")
    if PHONE_RE.search(text):
        hits.append("PHONE_LITERAL")
    if SECRET_RE.search(text):
        hits.append("SECRET_LITERAL")
    return hits


def _candidate_return(
    *,
    selection: Mapping[str, Any],
    dynamic_context_ref: str,
    member_context_ref: str,
    model_response: Mapping[str, Any],
    selected_endpoint: Mapping[str, Any],
    candidate_text: str,
    state: str,
    risk_flags: list[str],
    hold_reason: str | None,
) -> dict[str, Any]:
    candidate_sha = hashlib.sha256(candidate_text.encode("utf-8")).hexdigest()
    response_sha = canonical_sha256(model_response)
    result = {
        "schema_version": "w7tp.local-llm-candidate-return.v1",
        "state": state,
        "task_ref": selection["task_ref"],
        "intent_ref": selection["intent_ref"],
        "provider_ref": selection["provider_ref"],
        "model_ref": selection["model_ref"],
        "context_ref": selection["context_ref"],
        "context_sha256": selection["context_sha256"],
        "candidate_ref": "candidate:sha256:" + candidate_sha,
        "candidate_sha256": candidate_sha,
        "candidate_text": candidate_text,
        "candidate_only": True,
        "must_not_execute": True,
        "requires_total_field_verify": True,
        "member_plaintext_transferred": False,
        "secret_transferred": False,
        "raw_browser_page_transferred": False,
        "authority": {
            "provider_authority": False,
            "model_authority": False,
            "codex_authority": False,
            "browser_authority": False,
            "formal_effect_boundary": "TAIJI01_TOTAL_FIELD",
        },
        "d4_evidence": {
            "model_selection_sha256": selection["selection_sha256"],
            "dynamic_context_ref": dynamic_context_ref,
            "member_context_ref": member_context_ref,
            "model_response_sha256": response_sha,
            "endpoint_ref": str(selected_endpoint["ref"]),
            "endpoint_transport": str(selected_endpoint["transport"]),
        },
        "d7_risk": {
            "risk_flags": sorted(set(risk_flags)),
            "output_scan_pass": not risk_flags,
            "hold_reason": hold_reason,
        },
        "return_coordinate": selection["return_coordinate"],
    }
    _validate_with_schema(
        result,
        RETURN_SCHEMA_PATH,
        "HOLD_T011B_CANDIDATE_RETURN_SCHEMA",
    )
    return result


def run_msi_llm_candidate(
    *,
    dynamic_context_pull_result: Mapping[str, Any],
    member_model_visible_context: Mapping[str, Any],
    resource_decision: Mapping[str, Any],
    task_ref: str,
    intent_ref: str,
    transport: ModelTransport | None = None,
    ollama_url: str | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    dynamic_result = _validate_dynamic_pull_result(dynamic_context_pull_result)
    member_context = _validate_member_context(member_model_visible_context)
    combined = combine_model_visible_contexts(
        dynamic_result,
        member_context,
    )
    selection = select_msi_llm_model(
        resource_decision=resource_decision,
        combined_context=combined,
        task_ref=task_ref,
        intent_ref=intent_ref,
    )
    selected_endpoint = _select_ollama_endpoint(
        selection,
        explicit_url=ollama_url,
        probe=transport is None,
    )
    caller = transport or _default_transport
    response = caller(
        str(selected_endpoint["url"]),
        str(selection["model_ref"]),
        _model_messages(selection),
        timeout,
    )
    message = response.get("message")
    _require(isinstance(message, Mapping), "HOLD_T011B_MSI_MODEL_MESSAGE_REQUIRED")
    _require(
        not message.get("tool_calls"),
        "HOLD_T011B_MODEL_TOOL_CALL_FORBIDDEN",
    )
    candidate = str(message.get("content") or "").strip()
    _require(candidate != "", "HOLD_T011B_EMPTY_MODEL_CANDIDATE")
    _require(
        len(candidate) <= int(selection["max_candidate_chars"]),
        "HOLD_T011B_MODEL_CANDIDATE_TOO_LARGE",
    )
    risk_flags = _scan_output(candidate)
    if risk_flags:
        return _candidate_return(
            selection=selection,
            dynamic_context_ref=dynamic_result["model_visible_context"]["context_ref"],
            member_context_ref=member_context["context_ref"],
            model_response=response,
            selected_endpoint=selected_endpoint,
            candidate_text="",
            state="HOLD",
            risk_flags=risk_flags,
            hold_reason="HOLD_T011B_MODEL_OUTPUT_BOUNDARY_SCAN",
        )
    return _candidate_return(
        selection=selection,
        dynamic_context_ref=dynamic_result["model_visible_context"]["context_ref"],
        member_context_ref=member_context["context_ref"],
        model_response=response,
        selected_endpoint=selected_endpoint,
        candidate_text=candidate,
        state="CANDIDATE_READY",
        risk_flags=[],
        hold_reason=None,
    )


def adjudicate_msi_candidate_return(
    candidate_return: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a local-LLM candidate to the existing Total Field sole receiver."""
    _require(
        isinstance(candidate_return, Mapping),
        "HOLD_T011B_CANDIDATE_RETURN_REQUIRED",
    )
    packet = copy.deepcopy(dict(candidate_return))
    _validate_with_schema(
        packet,
        RETURN_SCHEMA_PATH,
        "HOLD_T011B_CANDIDATE_RETURN_SCHEMA",
    )
    _require(
        packet.get("state") == "CANDIDATE_READY",
        "HOLD_T011B_CANDIDATE_NOT_READY",
    )
    _require(
        packet.get("candidate_only") is True
        and packet.get("must_not_execute") is True
        and packet.get("requires_total_field_verify") is True,
        "HOLD_T011B_CANDIDATE_BOUNDARY_DRIFT",
    )
    candidate_sha = str(packet["candidate_sha256"])
    suffix = candidate_sha[:16]
    event_ref = f"event:msi-llm-candidate:{suffix}"
    domain_ref = f"observation-domain:msi-llm:{suffix}"
    shared = {
        "D1": {
            "intent_ref": str(packet["intent_ref"]),
        },
        "D3": {
            "node_ref": "node:MSI",
            "provider_ref": "provider:MSI_OLLAMA_LOCAL",
            "model_ref": "model:taiji-qwen2.5-coder-7b:ctx16k",
            "endpoint_ref": str(packet["d4_evidence"]["endpoint_ref"]),
        },
        "D4": {
            "evidence_ref": f"msi-llm-candidate:sha256:{candidate_sha}",
        },
        "D5": {
            "execution_ref": "execution:candidate-only:no-live-effect",
        },
        "D6": {
            "privacy_boundary_ref": "privacy:member-opaque-reference-only",
        },
        "D7": {
            "rule_ref": "rule:t011b:local-llm-candidate-only",
            "routing_ref": "routing:total-field:llm-push",
            "reconstruction_condition": "condition:t011b-context-and-model-selection-bound",
        },
        "D8": {
            "adjudication_policy_ref": "d8-policy:total-field:llm-candidate",
        },
    }
    previous = {
        **shared,
        "D2": {
            "state_ref": "state:msi-llm:awaiting-candidate",
        },
    }
    proposed = {
        **shared,
        "D2": {
            "state_ref": f"state:msi-llm:candidate:{suffix}",
        },
    }
    request = {
        "profile_schema_version": "8d-gte-runtime-candidate-profile/0.1",
        "profile_type": "RUNTIME_REQUEST",
        "gte": {
            "schema_version": "8d-gte-candidate/0.1",
            "lifecycle": "CANDIDATE",
            "event_ref": event_ref,
            "observation_domain_ref": domain_ref,
            "dimensions": {
                f"D{i}_ref": f"field/tfct/D{i}/v0_1"
                for i in range(1, 9)
            },
            "constraint_hypergraph_ref": "constraints/tfct/runtime-hypergraph/v0_1",
            "convergence_operator_ref": "convergence/tfct/finite-fixed-point/v0_1",
            "priority_policy_ref": "priority/tfct/candidate/v0_1",
            "fixed_point_status": "PENDING",
            "verification": {
                "final_decision": "PENDING",
                "commit_applied": False,
            },
            "tfs_result": None,
        },
        "event": {
            "event_id": f"event-id:msi-llm:{suffix}",
            "event_ref": event_ref,
            "event_code": "STATE_UPDATE",
            "logical_time": f"logical-time:msi-llm:{suffix}",
        },
        "rule_set_ref": "rules/tfct/identity_v0_1",
        "resolved_fields": proposed,
        "context": {
            "request_ref": f"request:msi-llm:{suffix}",
            "d3_context": {
                "projection_ref": f"projection:msi-llm:{suffix}",
            },
        },
        "adi_requested": False,
    }
    observations = {
        domain_ref: {
            "configured": True,
            "observations": {
                "candidate_sha256": candidate_sha,
                "context_sha256": str(packet["context_sha256"]),
                "model_selection_sha256": str(
                    packet["d4_evidence"]["model_selection_sha256"]
                ),
                "model_response_sha256": str(
                    packet["d4_evidence"]["model_response_sha256"]
                ),
                "endpoint_ref": str(packet["d4_evidence"]["endpoint_ref"]),
                "endpoint_transport": str(
                    packet["d4_evidence"]["endpoint_transport"]
                ),
            },
        }
    }
    result = llm_push(
        request,
        previous_state=previous,
        observation_domains=observations,
    )
    return {
        "state": "PASS_T011B_TOTAL_FIELD_CANDIDATE_RETURN",
        "candidate_sha256": candidate_sha,
        "candidate_text_submitted_to_total_field": False,
        "candidate_execution_allowed": False,
        "final_decision": result.get("final_decision"),
        "fixed_point_status": result.get("fixed_point_status"),
        "commit_applied": result.get("commit_applied"),
        "decision_reason_codes": result.get("decision_reason_codes"),
        "state_ref": result.get("state_ref"),
        "tfid": result.get("tfid"),
        "total_field_hash": result.get("total_field_hash"),
        "formal_effect_boundary": "TAIJI01_TOTAL_FIELD",
    }


__all__ = [
    "MSILLMCandidateHold",
    "adjudicate_msi_candidate_return",
    "combine_model_visible_contexts",
    "load_model_selection_contract",
    "run_msi_llm_candidate",
    "select_msi_llm_model",
]
