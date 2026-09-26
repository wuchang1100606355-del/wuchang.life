#!/usr/bin/env python3
"""Pointer-first Gemini Code Assist A2A candidate adapter.

Gemini is a replaceable candidate-only model organ. The first turn receives
only a Total Field bootstrap pointer. Local code performs the exact pull and
sends only the resulting bounded model-visible context on the second turn.
The candidate returns to the existing Total Field sole receiver.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, Mapping
from urllib.request import Request, urlopen

from core.resource_arbitration import probe_gemini_code_assist
from tools.total_field_candidate_gateway import llm_push
from tools.total_field_dynamic_context_pull import (
    TotalFieldDynamicContextPullBroker,
    canonical_sha256,
)


PROVIDER_REF = "provider:gemini-code-assist"
MODEL_REF = "model:gemini-code-assist:current"
MAX_A2A_EVENT_BYTES = 4 * 1024 * 1024
FORBIDDEN_CANDIDATE_KEYS = frozenset(
    {
        "authority_granted",
        "canonical",
        "commit_applied",
        "d8_authority",
        "execution_authorized",
        "formal_authority",
        "private_key",
        "password",
        "raw_token",
        "secret",
        "token",
        "total_field_decision",
    }
)


class GeminiA2AHold(RuntimeError):
    """Stable fail-closed Gemini A2A adapter error."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()
def _workspace_snapshot(root: Path) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        result[relative] = (len(data), hashlib.sha256(data).hexdigest())
    return result


def _extract_json(text: str) -> dict[str, Any]:
    value = str(text or "").strip()
    if not value:
        raise GeminiA2AHold("HOLD_GEMINI_A2A_EMPTY_TEXT")
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        fence = chr(96) * 3
        if value.startswith(fence) and value.endswith(fence):
            value = value[len(fence):-len(fence)].strip()
            if value.lower().startswith("json"):
                value = value[4:].strip()
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise GeminiA2AHold(
                "HOLD_GEMINI_A2A_JSON_RESPONSE_REQUIRED"
            ) from exc
    if not isinstance(parsed, dict):
        raise GeminiA2AHold("HOLD_GEMINI_A2A_JSON_OBJECT_REQUIRED")
    return parsed


def _walk_keys(value: Any):
    if isinstance(value, Mapping):
        for key, nested in value.items():
            yield str(key).strip().lower().replace("-", "_")
            yield from _walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_keys(nested)
def _validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    copied = json.loads(json.dumps(dict(candidate), ensure_ascii=False))
    if copied.get("state") != "CANDIDATE_ONLY":
        raise GeminiA2AHold("HOLD_GEMINI_A2A_CANDIDATE_ONLY_REQUIRED")
    body = copied.get("candidate")
    if not isinstance(body, dict):
        raise GeminiA2AHold("HOLD_GEMINI_A2A_CANDIDATE_BODY_REQUIRED")
    if FORBIDDEN_CANDIDATE_KEYS.intersection(_walk_keys(copied)):
        raise GeminiA2AHold("HOLD_GEMINI_A2A_AUTHORITY_CLAIM_BLOCKED")
    if len(_canonical_bytes(copied)) > 512 * 1024:
        raise GeminiA2AHold("HOLD_GEMINI_A2A_CANDIDATE_TOO_LARGE")
    return copied


def discover_a2a() -> dict[str, Any]:
    resource = probe_gemini_code_assist()
    if resource.get("CURRENT_STATE") != "AVAILABLE":
        raise GeminiA2AHold("HOLD_GEMINI_CODE_ASSIST_UNAVAILABLE")
    url = resource.get("A2A_URL")
    if not isinstance(url, str) or not url.startswith("http://127.0.0.1:"):
        raise GeminiA2AHold("HOLD_GEMINI_A2A_LOCAL_ENDPOINT_REQUIRED")
    return {
        "url": url,
        "agent_version": resource.get("AGENT_VERSION"),
        "resource_id": resource.get("RESOURCE_ID"),
    }


def _send_stream(
    *,
    a2a_url: str,
    text: str,
    workspace: Path,
    task_id: str | None = None,
    context_id: str | None = None,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "kind": "message",
        "role": "user",
        "messageId": str(uuid.uuid4()),
        "parts": [{"kind": "text", "text": text}],
    }
    if task_id is None:
        message["metadata"] = {
            "coderAgent": {
                "kind": "agent-settings",
                "workspacePath": str(workspace),
                "autoExecute": False,
            }
        }
    else:
        message["taskId"] = task_id
        if context_id:
            message["contextId"] = context_id

    body = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/stream",
        "params": {
            "message": message,
            "configuration": {
                "blocking": True,
                "acceptedOutputModes": ["text"],
            },
        },
    }
    request = Request(
        a2a_url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    observed_task_id = task_id
    observed_context_id = context_id
    text_chunks: list[str] = []
    final_state: str | None = None
    usage: dict[str, Any] | None = None
    provider_model: str | None = None

    with urlopen(request, timeout=timeout_seconds) as response:
        for raw in response:
            if len(raw) > MAX_A2A_EVENT_BYTES:
                raise GeminiA2AHold("HOLD_GEMINI_A2A_EVENT_TOO_LARGE")
            line = raw.decode("utf-8", errors="replace").rstrip()
            if not line.startswith("data: "):
                continue
            try:
                envelope = json.loads(line[6:])
            except json.JSONDecodeError as exc:
                raise GeminiA2AHold(
                    "HOLD_GEMINI_A2A_EVENT_JSON_INVALID"
                ) from exc
            if envelope.get("error") is not None:
                raise GeminiA2AHold("HOLD_GEMINI_A2A_JSONRPC_ERROR")
            event = envelope.get("result")
            if not isinstance(event, dict):
                continue

            if event.get("kind") == "task":
                observed_task_id = event.get("id") or observed_task_id
                observed_context_id = (
                    event.get("contextId") or observed_context_id
                )
                continue
            if event.get("kind") == "artifact-update":
                raise GeminiA2AHold("HOLD_GEMINI_A2A_ARTIFACT_BLOCKED")
            if event.get("kind") != "status-update":
                continue

            metadata = event.get("metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            coder = metadata.get("coderAgent")
            coder = coder if isinstance(coder, dict) else {}
            kind = str(coder.get("kind") or "")
            if kind.startswith("tool-call"):
                raise GeminiA2AHold("HOLD_GEMINI_A2A_TOOL_USE_BLOCKED")
            if isinstance(metadata.get("model"), str):
                provider_model = metadata["model"]
            if isinstance(metadata.get("usageMetadata"), dict):
                usage = dict(metadata["usageMetadata"])

            status = event.get("status")
            status = status if isinstance(status, dict) else {}
            if event.get("final") is True:
                final_state = str(status.get("state") or "")
            if kind != "text-content":
                continue
            status_message = status.get("message")
            if not isinstance(status_message, dict):
                continue
            for part in status_message.get("parts", []):
                if (
                    isinstance(part, dict)
                    and part.get("kind") == "text"
                    and isinstance(part.get("text"), str)
                ):
                    text_chunks.append(part["text"])
    if final_state not in {"input-required", "completed"}:
        raise GeminiA2AHold(
            "HOLD_GEMINI_A2A_FINAL_STATE:" + str(final_state)
        )
    if not observed_task_id or not observed_context_id:
        raise GeminiA2AHold("HOLD_GEMINI_A2A_TASK_BINDING_MISSING")
    response_text = "".join(text_chunks).strip()
    if not response_text:
        raise GeminiA2AHold("HOLD_GEMINI_A2A_EMPTY_TEXT")
    return {
        "task_id": observed_task_id,
        "context_id": observed_context_id,
        "text": response_text,
        "text_sha256": hashlib.sha256(
            response_text.encode("utf-8")
        ).hexdigest(),
        "final_state": final_state,
        "provider_model": provider_model,
        "usage_metadata": usage or {},
    }


def _require_pull_request(
    value: Mapping[str, Any],
    bootstrap: Mapping[str, Any],
) -> None:
    if value.get("state") != "CANDIDATE_ONLY":
        raise GeminiA2AHold("HOLD_GEMINI_A2A_PULL_STATE_INVALID")
    if value.get("action") != "PULL_CONTEXT":
        raise GeminiA2AHold("HOLD_GEMINI_A2A_PULL_ACTION_REQUIRED")
    if value.get("pull_coordinate") != bootstrap.get("pull_coordinate"):
        raise GeminiA2AHold("HOLD_GEMINI_A2A_PULL_COORDINATE_DRIFT")
    if value.get("bootstrap_sha256") != bootstrap.get("bootstrap_sha256"):
        raise GeminiA2AHold("HOLD_GEMINI_A2A_BOOTSTRAP_HASH_DRIFT")
def _adjudicate_candidate(
    *,
    candidate: Mapping[str, Any],
    context_ref: str,
    bootstrap: Mapping[str, Any],
    a2a_task_id: str,
    a2a_context_id: str,
) -> dict[str, Any]:
    candidate_hash = _sha(candidate)
    suffix = candidate_hash[:16]
    event_ref = f"event:gemini-a2a-candidate:{suffix}"
    domain_ref = f"observation-domain:gemini-a2a:{suffix}"
    shared = {
        "D1": {
            "intent_ref": f"intent-ref:context:{context_ref}",
        },
        "D3": {
            "node_ref": "node:taiji01",
            "a2a_task_ref": f"a2a-task:{a2a_task_id}",
            "a2a_context_ref": f"a2a-context:{a2a_context_id}",
        },
        "D4": {
            "evidence_ref": f"gemini-candidate:sha256:{candidate_hash}",
        },
        "D5": {
            "execution_ref": "execution:candidate-only:no-live-effect",
        },
        "D6": {
            "privacy_boundary_ref": (
                "privacy:pointer-first:ephemeral-context"
            ),
        },
        "D7": {
            "rule_ref": "rule:gemini-a2a:candidate-only",
            "routing_ref": "routing:total-field:llm-push",
            "reconstruction_condition": (
                "condition:pointer-first-context-pull-pass"
            ),
        },
        "D8": {
            "adjudication_policy_ref": "d8-policy:total-field:llm-candidate",
        },
    }
    previous = {
        **shared,
        "D2": {
            "state_ref": "state:model-organ:awaiting-candidate",
        },
    }
    proposed = {
        **shared,
        "D2": {
            "state_ref": f"state:model-organ:candidate:{suffix}",
        },
    }
    request = {
        "profile_schema_version": (
            "8d-gte-runtime-candidate-profile/0.1"
        ),
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
            "constraint_hypergraph_ref": (
                "constraints/tfct/runtime-hypergraph/v0_1"
            ),
            "convergence_operator_ref": (
                "convergence/tfct/finite-fixed-point/v0_1"
            ),
            "priority_policy_ref": "priority/tfct/candidate/v0_1",
            "fixed_point_status": "PENDING",
            "verification": {
                "final_decision": "PENDING",
                "commit_applied": False,
            },
            "tfs_result": None,
        },
        "event": {
            "event_id": f"event-id:gemini-a2a:{suffix}",
            "event_ref": event_ref,
            "event_code": "STATE_UPDATE",
            "logical_time": f"logical-time:gemini-a2a:{suffix}",
        },
        "rule_set_ref": "rules/tfct/identity_v0_1",
        "resolved_fields": proposed,
        "context": {
            "request_ref": f"request:gemini-a2a:{suffix}",
            "d3_context": {
                "projection_ref": (
                    f"projection:gemini-a2a:{suffix}"
                ),
            },
        },
        "adi_requested": False,
    }
    domains = {
        domain_ref: {
            "configured": True,
            "observations": {
                "candidate_sha256": candidate_hash,
                "context_ref": context_ref,
                "bootstrap_sha256": bootstrap["bootstrap_sha256"],
            },
        }
    }
    result = llm_push(
        request,
        previous_state=previous,
        observation_domains=domains,
    )
    return {
        "candidate_sha256": candidate_hash,
        "final_decision": result.get("final_decision"),
        "fixed_point_status": result.get("fixed_point_status"),
        "commit_applied": result.get("commit_applied"),
        "decision_reason_codes": result.get("decision_reason_codes"),
        "state_ref": result.get("state_ref"),
        "tfid": result.get("tfid"),
        "total_field_hash": result.get("total_field_hash"),
    }
def run_pointer_first_candidate(
    *,
    broker: TotalFieldDynamicContextPullBroker,
    bootstrap: Mapping[str, Any],
    task_ref: str,
    candidate_instruction: str,
    provider_ref: str = PROVIDER_REF,
    model_ref: str = MODEL_REF,
    a2a_url: str | None = None,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Run the two-turn pointer-first Gemini exchange in an isolated workspace."""

    discovered = discover_a2a() if a2a_url is None else {
        "url": a2a_url,
        "agent_version": None,
        "resource_id": "GEMINI_CODE_ASSIST",
    }
    url = str(discovered["url"])
    with tempfile.TemporaryDirectory(
        prefix="w7tp-gemini-a2a-",
        dir="/tmp",
    ) as workspace_name:
        workspace = Path(workspace_name)
        before = _workspace_snapshot(workspace)

        bootstrap_text = json.dumps(
            dict(bootstrap),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        first_prompt = (
            "You are a candidate-only model organ with no authority. "
            "Do not call tools, inspect files, create files, or modify files. "
            "The following is the complete W7TP bootstrap available to you. "
            "It contains only a governed pull coordinate and references. "
            "Do not infer or invent missing context. Reply with exactly one "
            "JSON object and no markdown: "
            "{\"state\":\"CANDIDATE_ONLY\","
            "\"action\":\"PULL_CONTEXT\","
            "\"pull_coordinate\":\"<exact pull_coordinate>\","
            "\"bootstrap_sha256\":\"<exact bootstrap_sha256>\"}. "
            "BOOTSTRAP="
            + bootstrap_text
        )
        first = _send_stream(
            a2a_url=url,
            text=first_prompt,
            workspace=workspace,
            timeout_seconds=timeout_seconds,
        )
        pull_request = _extract_json(first["text"])
        _require_pull_request(pull_request, bootstrap)

        pull_result = broker.pull(
            str(bootstrap["pull_coordinate"]),
            task_ref=task_ref,
            provider_ref=provider_ref,
            model_ref=model_ref,
        )
        model_context = pull_result["model_visible_context"]
        context_ref = str(model_context["context_ref"])
        second_prompt = (
            "CONTEXT_PULL_RESULT. This context is ephemeral and task-bound. "
            "Do not call tools, inspect files, create files, or modify files. "
            "Use only the supplied model-visible context. Do not claim "
            "authority, execution, canonical status, or Total Field decision. "
            "Return exactly one JSON object and no markdown with shape "
            "{\"state\":\"CANDIDATE_ONLY\","
            "\"context_ref\":\"<exact context_ref>\","
            "\"candidate\":{...}}. "
            "TASK=" + candidate_instruction
            + " CONTEXT="
            + json.dumps(
                model_context,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        second = _send_stream(
            a2a_url=url,
            text=second_prompt,
            workspace=workspace,
            task_id=str(first["task_id"]),
            context_id=str(first["context_id"]),
            timeout_seconds=timeout_seconds,
        )
        candidate = _validate_candidate(
            _extract_json(second["text"])
        )
        if candidate.get("context_ref") != context_ref:
            raise GeminiA2AHold(
                "HOLD_GEMINI_A2A_CONTEXT_REF_DRIFT"
            )

        after = _workspace_snapshot(workspace)
        if after != before:
            raise GeminiA2AHold(
                "HOLD_GEMINI_A2A_WORKSPACE_MUTATION_BLOCKED"
            )

        adjudication = _adjudicate_candidate(
            candidate=candidate,
            context_ref=context_ref,
            bootstrap=bootstrap,
            a2a_task_id=str(first["task_id"]),
            a2a_context_id=str(first["context_id"]),
        )
        if not (
            adjudication.get("final_decision") == "ALLOW"
            and adjudication.get("fixed_point_status") == "REACHED"
            and adjudication.get("commit_applied") is True
        ):
            raise GeminiA2AHold(
                "HOLD_GEMINI_A2A_TOTAL_FIELD:"
                + str(adjudication.get("final_decision"))
                + ":"
                + str(adjudication.get("fixed_point_status"))
            )
        return {
            "state": "PASS_GEMINI_A2A_POINTER_FIRST_CANDIDATE",
            "provider_ref": provider_ref,
            "model_ref": model_ref,
            "agent_version": discovered.get("agent_version"),
            "a2a_task_id": first["task_id"],
            "a2a_context_id": first["context_id"],
            "bootstrap_sha256": bootstrap["bootstrap_sha256"],
            "pull_result_sha256": pull_result["pull_result_sha256"],
            "context_ref": context_ref,
            "first_turn_text_sha256": first["text_sha256"],
            "second_turn_text_sha256": second["text_sha256"],
            "candidate": candidate,
            "candidate_sha256": adjudication["candidate_sha256"],
            "total_field": adjudication,
            "workspace_mutated": False,
            "raw_source_body_submitted_to_total_field": False,
            "provider_internal_context_controlled": False,
            "provider_reported_model": second["provider_model"],
            "provider_usage_metadata": second["usage_metadata"],
        }
__all__ = [
    "GeminiA2AHold",
    "MODEL_REF",
    "PROVIDER_REF",
    "discover_a2a",
    "run_pointer_first_candidate",
]
