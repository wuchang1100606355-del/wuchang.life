"""Single-turn, candidate-only stateless MSI model adapter for W7TP/8D ADI V2.3.

Thin integration only. The existing TotalFieldDynamicContextPullBroker owns
single-use minimum-state reconstruction, and the existing T-011B adapter owns
model selection, data boundaries, and model invocation. This file issues no
D8 authority, makes no canonical changes, and stores no conversation history.

Deployment is separately governed by the current taiji01 Total Field.
"""

from __future__ import annotations

import copy
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

from tools.total_field_dynamic_context_pull import (
    BOOTSTRAP_SCHEMA,
    TotalFieldDynamicContextPullBroker,
    canonical_sha256,
)
from tools.total_field.msi_llm_candidate_adapter import (
    load_model_selection_contract,
    run_msi_llm_candidate,
)

TURN_SCHEMA = "w7tp-stateless-msi-turn-candidate/1.0"
MAX_CONTEXT_TTL = timedelta(minutes=10)
REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/+:-]{0,511}$")


class StatelessTurnHold(RuntimeError):
    """Local fail-closed condition, not a D8 decision."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _must(condition: bool, code: str) -> None:
    if not condition:
        raise StatelessTurnHold(code)


def _ref(value: Any, code: str) -> str:
    _must(isinstance(value, str) and REF.fullmatch(value) is not None, code)
    return value


def _time(value: Any) -> datetime:
    _must(isinstance(value, str), "HOLD_STATELESS_EXPIRY_INVALID")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StatelessTurnHold("HOLD_STATELESS_EXPIRY_INVALID") from exc
    _must(parsed.tzinfo is not None, "HOLD_STATELESS_EXPIRY_INVALID")
    return parsed.astimezone(timezone.utc)


def _validate_bootstrap(value: Mapping[str, Any], current: datetime) -> dict[str, Any]:
    _must(isinstance(value, Mapping), "HOLD_STATELESS_BOOTSTRAP_REQUIRED")
    value = copy.deepcopy(dict(value))
    _must(value.get("schema_version") == BOOTSTRAP_SCHEMA, "HOLD_STATELESS_BOOTSTRAP_SCHEMA")
    _must(value.get("single_use") is True, "HOLD_STATELESS_SINGLE_USE_REQUIRED")
    for key in ("pull_coordinate", "packet_ref", "packet_sha256",
                "adi_coordinate_ref", "return_coordinate", "context_schema_ref",
                "persistence_policy_ref"):
        _ref(value.get(key), "HOLD_STATELESS_BOOTSTRAP_REF_INVALID")
    supplied_hash = _ref(value.get("bootstrap_sha256"), "HOLD_STATELESS_BOOTSTRAP_HASH_INVALID")
    _must(len(supplied_hash) == 64 and all(c in "0123456789abcdef" for c in supplied_hash),
          "HOLD_STATELESS_BOOTSTRAP_HASH_INVALID")
    basis = {k: v for k, v in value.items() if k != "bootstrap_sha256"}
    _must(canonical_sha256(basis) == supplied_hash,
          "HOLD_STATELESS_BOOTSTRAP_HASH_MISMATCH")
    expiry = _time(value.get("expires_at"))
    _must(current < expiry <= current + MAX_CONTEXT_TTL,
          "HOLD_STATELESS_CONTEXT_NOT_FRESH")
    return value


def run_stateless_msi_turn(
    *,
    broker: TotalFieldDynamicContextPullBroker,
    bootstrap: Mapping[str, Any],
    member_model_visible_context: Mapping[str, Any],
    resource_decision: Mapping[str, Any],
    task_ref: str,
    intent_ref: str,
    transport: Callable[..., Mapping[str, Any]] | None = None,
    timeout: int = 60,
    clock: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Rebuild current context for exactly ONE fresh model candidate turn.

    No previous messages or session identifier are accepted. Caller supplies
    a real broker with a pre-registered single-use coordinate. Packet issuance
    and authority resolution are OUTSIDE this adapter. `clock` is an internal
    test seam and must never be exposed as a user-supplied timestamp.
    """
    _must(isinstance(broker, TotalFieldDynamicContextPullBroker),
          "HOLD_STATELESS_BROKER_REQUIRED")
    task = _ref(task_ref, "HOLD_STATELESS_TASK_REF_INVALID")
    intent = _ref(intent_ref, "HOLD_STATELESS_INTENT_REF_INVALID")
    _must(task.startswith("task:"), "HOLD_STATELESS_TASK_REF_INVALID")
    current = (clock or (lambda: datetime.now(timezone.utc)))()
    _must(isinstance(current, datetime) and current.tzinfo is not None,
          "HOLD_STATELESS_CLOCK_INVALID")
    current = current.astimezone(timezone.utc)

    bound = _validate_bootstrap(bootstrap, current)
    contract = load_model_selection_contract()
    provider = "provider:" + _ref(contract.get("provider_ref"), "HOLD_STATELESS_PROVIDER_INVALID")
    model = "model:" + _ref(contract.get("model_ref"), "HOLD_STATELESS_MODEL_INVALID")
    coordinate = bound["pull_coordinate"]
    _must(not broker.is_consumed(coordinate), "HOLD_STATELESS_REPLAY_BLOCKED")

    # Broker consumes the coordinate before local reconstitution; it checks
    # task/provider/model bindings, expiry, reconstruction and workset erasure.
    pulled = broker.pull(
        coordinate,
        task_ref=task,
        provider_ref=provider,
        model_ref=model,
        now=current,
    )
    _must(isinstance(pulled, Mapping), "HOLD_STATELESS_PULL_RESULT_INVALID")
    _must(pulled.get("pull_coordinate") == coordinate and
          pulled.get("task_ref") == task and
          pulled.get("packet_ref") == bound["packet_ref"] and
          pulled.get("adi_coordinate_ref") == bound["adi_coordinate_ref"] and
          pulled.get("return_coordinate") == bound["return_coordinate"],
          "HOLD_STATELESS_PULL_BINDING_MISMATCH")
    evidence = pulled.get("reconstruction_evidence")
    _must(isinstance(evidence, Mapping) and
          evidence.get("packet_sha256") == bound["packet_sha256"] and
          evidence.get("workset_destroyed") is True and
          evidence.get("persistent_materialization") is False,
          "HOLD_STATELESS_RECONSTRUCTION_EVIDENCE_INVALID")

    # Existing T-011B gate validates signed-shape/hash, policy, member-opaque
    # boundaries, resource arbitration, and constructs ONLY current-turn messages.
    candidate = run_msi_llm_candidate(
        dynamic_context_pull_result=pulled,
        member_model_visible_context=member_model_visible_context,
        resource_decision=resource_decision,
        task_ref=task,
        intent_ref=intent,
        transport=transport,
        ollama_url=None,  # caller cannot redirect context to a chosen endpoint
        timeout=timeout,
    )
    _must(isinstance(candidate, Mapping) and
          candidate.get("candidate_only") is True and
          candidate.get("must_not_execute") is True and
          candidate.get("requires_total_field_verify") is True,
          "HOLD_STATELESS_CANDIDATE_BOUNDARY_INVALID")
    _must(candidate.get("state") in ("CANDIDATE_READY", "HOLD"),
          "HOLD_STATELESS_CANDIDATE_STATE_INVALID")
    return {
        "schema_version": TURN_SCHEMA,
        "state": candidate["state"],
        "task_ref": task,
        "intent_ref": intent,
        "provider_ref": provider,
        "model_ref": model,
        "bootstrap_sha256": bound["bootstrap_sha256"],
        "pull_result_sha256": pulled["pull_result_sha256"],
        "packet_ref": pulled["packet_ref"],
        "adi_coordinate_ref": pulled["adi_coordinate_ref"],
        "context_ref": pulled["model_visible_context"]["context_ref"],
        "stateless_model_boundary": {
            "previous_turn_messages_supplied": False,
            "server_session_reference_supplied": False,
            "state_owner": "EXISTING_TAIJI01_TOTAL_FIELD",
            "current_turn_context_reconstructed": True,
        },
        "authority": {
            "candidate_only": True,
            "execution_authorized": False,
            "activation_authorized": False,
            "canonical_authorized": False,
        },
        "candidate_return": copy.deepcopy(dict(candidate)),
    }


__all__ = ["StatelessTurnHold", "TURN_SCHEMA", "run_stateless_msi_turn"]
