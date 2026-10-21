#!/usr/bin/env python3
"""Build a governed Dynamic Context delivery for a remote endpoint.

This is a thin adapter over existing Total Field Dynamic Context, minimum
Origin State packets, and rule-base transport. It does not create D8
authority, mutate canonical pointers, or redefine W7TP/8D ADI V2.3.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path("/home/taiji_admin/Taiji_Hub")
sys.path.insert(0, str(ROOT))

from tools.total_field_dynamic_context_pull import (  # noqa: E402
    TotalFieldDynamicContextPullBroker,
)
from tools.w7tp_task_state_minimum_packet import (  # noqa: E402
    build_task_model_visible_context,
    issue_task_state_minimum_packet,
    select_task_state_support_refs,
)


class BridgeDynamicContextHold(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _load_context_transport(root: Path) -> Any:
    path = root / "tools/w7tp_origin_context_transport_v1.py"
    spec = importlib.util.spec_from_file_location(
        "w7tp_bridge_origin_context_transport",
        path,
    )
    if spec is None or spec.loader is None:
        raise BridgeDynamicContextHold(
            "HOLD_BRIDGE_CONTEXT_TRANSPORT_IMPORT_FAILED"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_work_ledger(root: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            (root / "state/WORK_LEDGER.json").read_text(encoding="utf-8")
        )
    except Exception as exc:
        raise BridgeDynamicContextHold(
            "HOLD_BRIDGE_WORK_LEDGER_UNAVAILABLE"
        ) from exc
    if not isinstance(value, dict):
        raise BridgeDynamicContextHold(
            "HOLD_BRIDGE_WORK_LEDGER_INVALID"
        )
    return value


def _bind_task(
    *,
    intent: str,
    root: Path,
) -> tuple[str, str]:
    work = _load_work_ledger(root)
    valid_tasks = {
        item.get("TASK_ID")
        for item in work.get("TASKS", [])
        if isinstance(item, dict) and isinstance(item.get("TASK_ID"), str)
    }
    explicit_refs = list(dict.fromkeys(re.findall(
        r"(?<![A-Z0-9])(?:T-[A-Z0-9-]+|XJ-[0-9]+)(?![A-Z0-9-])",
        intent.upper(),
    )))
    if len(explicit_refs) > 1:
        raise BridgeDynamicContextHold(
            "HOLD_DYNAMIC_CONTEXT_MULTIPLE_TASK_REFERENCES"
        )
    if explicit_refs:
        candidate = explicit_refs[0]
        if candidate in valid_tasks:
            return candidate, "EXPLICIT_INTENT_TASK"
        raise BridgeDynamicContextHold(
            "HOLD_DYNAMIC_CONTEXT_TASK_BINDING_UNKNOWN"
        )

    try:
        checkpoint = json.loads(
            (root / "state/CURRENT_CONVERSATION_CHECKPOINT.json").read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        checkpoint = {}
    current_goal = str(checkpoint.get("current_goal") or "")
    match = re.search(
        r"(?<![A-Z0-9])(?:T-[A-Z0-9-]+|XJ-[0-9]+)(?![A-Z0-9-])",
        current_goal.upper(),
    )
    if match and match.group(0) in valid_tasks:
        return match.group(0), "CURRENT_CONVERSATION_CHECKPOINT"

    raise BridgeDynamicContextHold(
        "HOLD_DYNAMIC_CONTEXT_TASK_BINDING_UNKNOWN"
    )


def build_dynamic_context_payload(
    *,
    intent: str,
    model: str,
    root: Path = ROOT,
) -> dict[str, Any]:
    if not isinstance(intent, str) or not intent.strip():
        raise BridgeDynamicContextHold(
            "HOLD_DYNAMIC_CONTEXT_INTENT_MISSING"
        )
    if not isinstance(model, str) or not model.strip():
        raise BridgeDynamicContextHold(
            "HOLD_DYNAMIC_CONTEXT_MODEL_MISSING"
        )

    # Route context by exact task references, not model/resource planning.
    task_id, binding_source = _bind_task(
        intent=intent,
        root=root,
    )
    selected = select_task_state_support_refs(
        task_id=task_id,
        max_actions=8,
        max_adi_refs=16,
    )
    issued = issue_task_state_minimum_packet(
        task_id=task_id,
        action_refs=selected["action_refs"],
        support_adi_record_ids=selected["adi_record_ids"],
    )
    packet = issued["packet"]
    broker = TotalFieldDynamicContextPullBroker()
    provider_ref = "provider:CODEX_LOCAL_OLLAMA"
    model_ref = "model:" + model
    expires_at = (
        datetime.now(timezone.utc) + timedelta(minutes=10)
    ).isoformat()
    bootstrap = broker.register(
        packet=packet,
        task_ref="task:" + task_id,
        provider_ref=provider_ref,
        model_ref=model_ref,
        expires_at=expires_at,
        return_coordinate="codex:local-model:response",
        context_builder=build_task_model_visible_context,
    )
    result = broker.pull(
        bootstrap["pull_coordinate"],
        task_ref="task:" + task_id,
        provider_ref=provider_ref,
        model_ref=model_ref,
    )
    visible = result["model_visible_context"]
    return {
        "state": "PASS_TOTAL_FIELD_DYNAMIC_CONTEXT",
        "task_id": task_id,
        "task_binding_source": binding_source,
        "provider_ref": provider_ref,
        "model_ref": model_ref,
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": bootstrap["expires_at"],
        "pull_result_sha256": result["pull_result_sha256"],
        "task_profile": {
            "routing_mode": "DETERMINISTIC_RULE_GATEWAY",
            "model_inference_for_transport": False,
        },
        "context_ref": visible["context_ref"],
        "state_projection": visible["state_projection"],
        "evidence_refs": visible["evidence_refs"],
        "capability_refs": visible["capability_refs"],
        "acceptance_conditions": visible["acceptance_conditions"],
        "schema_refs": visible["schema_refs"],
        "interface_refs": visible["interface_refs"],
        "non_core_rule_capsule_refs": visible[
            "non_core_rule_capsule_refs"
        ],
        "packet_ref": packet.get("packet_ref"),
        "packet_sha256": packet.get("packet_sha256"),
        "adi_coordinate_ref": packet.get("adi_coordinate_ref"),
        "authority": result.get("authority"),
        "persistence_policy": result.get("persistence_policy"),
        "transmission_semantics": result.get(
            "transmission_semantics"
        ),
    }


def build_bridge_delivery(
    *,
    intent: str,
    model: str,
    receiver_handshake: Mapping[str, Any],
    root: Path = ROOT,
) -> dict[str, Any]:
    if not isinstance(receiver_handshake, Mapping):
        raise BridgeDynamicContextHold(
            "HOLD_RECEIVER_HANDSHAKE_REQUIRED"
        )
    payload = build_dynamic_context_payload(
        intent=intent,
        model=model,
        root=root,
    )
    transport = _load_context_transport(root)
    return transport.build_transport(
        payload,
        receiver_handshake,
        root=root,
        source_state_root=root,
    )


def main() -> int:
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict):
            raise BridgeDynamicContextHold(
                "HOLD_BRIDGE_REQUEST_OBJECT_REQUIRED"
            )
        delivery = build_bridge_delivery(
            intent=request.get("intent"),
            model=request.get("model"),
            receiver_handshake=request.get("receiver_handshake"),
        )
    except BridgeDynamicContextHold as exc:
        print(
            json.dumps(
                {
                    "state": exc.code,
                    "authority_effect": "NONE",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    except Exception:
        print(
            json.dumps(
                {
                    "state": "HOLD_BRIDGE_CONTEXT_DELIVERY_FAILED",
                    "authority_effect": "NONE",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 3
    print(
        json.dumps(
            delivery,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
