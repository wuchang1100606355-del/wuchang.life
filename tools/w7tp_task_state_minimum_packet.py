#!/usr/bin/env python3
"""Issue real task-specific W7TP Origin-State Minimum Packets."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from products.eight_dimensional_generative_memory.w7tp_origin_state_minimum_packet_v1 import (
    PACKET_SCHEMA,
    PACKET_TYPE,
    PROTOCOL_VERSION,
    REGISTRY_PATH,
    ROOT,
    load_rule_registry,
    packet_sha256,
    validate_minimum_packet,
)
from tools.w7tp_task_state_local_rule import (
    build_task_state_recipe,
    build_task_state_snapshot,
    execute_task_state_rules,
    task_state_manifest,
)


RULE_REF = "local-rule:w7tp-task-state-ledger-reconstruction/v1"
NATIVE_ADI_URL = "http://127.0.0.1:9110"
REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/+:-]{0,511}$")


class TaskStatePacketError(RuntimeError):
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


def _require_ref(value: Any, code: str) -> str:
    if not isinstance(value, str) or REF_RE.fullmatch(value) is None:
        raise TaskStatePacketError(code)
    return value
def _require_refs(value: Any, code: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or len(value) != len(set(value))
    ):
        raise TaskStatePacketError(code)
    return [_require_ref(item, code) for item in value]


def _post_json(path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        NATIVE_ADI_URL.rstrip("/") + path,
        data=canonical_json_bytes(dict(payload)),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            value = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise TaskStatePacketError("HOLD_TASK_PACKET_NATIVE_ADI_UNAVAILABLE") from exc
    if not isinstance(value, dict):
        raise TaskStatePacketError("HOLD_TASK_PACKET_NATIVE_ADI_RESPONSE_INVALID")
    return value


def _snapshot_time_slot(snapshot: Mapping[str, Any]) -> int:
    task = snapshot.get("task")
    checkpoint = snapshot.get("checkpoint")
    value = None
    if isinstance(task, Mapping):
        value = task.get("LAST_UPDATE")
    if not isinstance(value, str) and isinstance(checkpoint, Mapping):
        value = checkpoint.get("updated_at")
    if not isinstance(value, str):
        raise TaskStatePacketError("HOLD_TASK_PACKET_TIME_COORDINATE_MISSING")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TaskStatePacketError("HOLD_TASK_PACKET_TIME_COORDINATE_INVALID") from exc
    if parsed.tzinfo is None:
        raise TaskStatePacketError("HOLD_TASK_PACKET_TIME_COORDINATE_INVALID")
    return int(parsed.astimezone(timezone.utc).timestamp())


def _task_state_record_payload(
    snapshot: Mapping[str, Any],
    *,
    task_id: str,
    action_refs: list[str],
    support_adi_record_ids: list[str],
) -> dict[str, Any]:
    task = snapshot["task"]
    checkpoint = snapshot["checkpoint"]
    git = snapshot["git"]
    source_hashes = snapshot["source_hashes"]
    return {
        "knowledge_type": "OBSERVED_TASK_STATE_COORDINATE",
        "state": "TASK_STATE_SNAPSHOT_INDEXED",
        "title": f"Task state snapshot {task_id}",
        "D1_INTENT": {
            "task_ref": f"task:{task_id}",
            "parent_intent_ref": task.get("PARENT_INTENT"),
            "title": task.get("TITLE"),
        },
        "D2_STATE": {
            "current": task.get("STATE"),
            "priority": task.get("PRIORITY"),
            "snapshot_sha256": snapshot["snapshot_sha256"],
        },
        "D3_COORDINATE": {
            "task_coordinate": task.get("D3_COORDINATE"),
            "git_head": git.get("head"),
            "git_branch": git.get("branch"),
            "worktree_clean": git.get("worktree_clean"),
            "support_native_adi_packet_sha256": source_hashes.get(
                "native_adi_packet_sha256"
            ),
        },
        "D4_EVIDENCE": {
            "task_state_sha256": source_hashes.get("task_state_sha256"),
            "selected_actions_sha256": source_hashes.get(
                "selected_actions_sha256"
            ),
            "checkpoint_sha256": source_hashes.get("checkpoint_sha256"),
            "selected_action_refs": list(action_refs),
        },
        "D5_EXECUTION": {
            "next_action": checkpoint.get("next_action"),
            "task_dirty_zero_required": True,
            "reconstruction_scope": "LOCAL_TASK_STATE_ONLY",
        },
        "D6_GST": {
            "packet_contract": "ORIGIN_STATE_MINIMUM_PACKET",
            "rule_ref": RULE_REF,
            "rule_body_location": "LOCAL_ONLY",
            "reconstruction": "LOCAL_VOLATILE_ON_PULL",
            "compression": False,
            "differential": False,
        },
        "D7_RISK": {
            "blockers": task.get("BLOCKERS", []),
            "source_hash_drift": "FAIL_CLOSED",
            "missing_action_ref": "FAIL_CLOSED",
            "missing_adi_record": "FAIL_CLOSED",
        },
        "D8_AUTHORITY": {
            "candidate_only": True,
            "canonical": False,
            "provider_authority": False,
            "model_authority": False,
            "formal_effect_authority": "LOCAL_TOTAL_FIELD",
        },
        "relations": [
            {"ref": ref, "type": "TASK_STATE_SUPPORT"}
            for ref in support_adi_record_ids
        ],
    }


def insert_task_state_adi_record(
    *,
    task_id: str,
    action_refs: list[str],
    support_adi_record_ids: list[str],
) -> dict[str, Any]:
    task = _require_ref(task_id, "HOLD_TASK_PACKET_TASK_ID_INVALID")
    actions = _require_refs(
        action_refs,
        "HOLD_TASK_PACKET_ACTION_REFS_INVALID",
    )
    support_ids = _require_refs(
        support_adi_record_ids,
        "HOLD_TASK_PACKET_ADI_RECORD_IDS_INVALID",
    )
    snapshot = build_task_state_snapshot(
        task_id=task,
        action_refs=actions,
        adi_record_ids=support_ids,
    )
    record_id = (
        f"task-state:{task}:{snapshot['snapshot_sha256'][:16]}"
    )
    payload = _task_state_record_payload(
        snapshot,
        task_id=task,
        action_refs=actions,
        support_adi_record_ids=support_ids,
    )
    result = _post_json(
        "/v1/adi/insert",
        {
            "id": record_id,
            "time_slot": _snapshot_time_slot(snapshot),
            "payload": payload,
        },
    )
    if result.get("state") != "PASS" or not isinstance(result.get("record"), dict):
        raise TaskStatePacketError("HOLD_TASK_PACKET_ADI_INSERT_FAILED")
    return {
        "record_id": record_id,
        "record": result["record"],
        "support_snapshot_sha256": snapshot["snapshot_sha256"],
    }
def _materialized_manifest(
    *,
    task_id: str,
    action_refs: list[str],
    adi_record_ids: list[str],
) -> tuple[dict[str, Any], int, str]:
    recipe = build_task_state_recipe(
        task_id=task_id,
        action_refs=action_refs,
        adi_record_ids=adi_record_ids,
    )
    tmp_root = Path("/dev/shm")
    if not tmp_root.is_dir():
        raise TaskStatePacketError("HOLD_TASK_PACKET_VOLATILE_ROOT_UNAVAILABLE")
    workset = Path(
        tempfile.mkdtemp(prefix="w7tp-task-packet-issue-", dir=tmp_root)
    )
    output = workset / "reconstructed"
    output.mkdir()
    try:
        execute_task_state_rules(
            output,
            copy.deepcopy(list(recipe["rules"])),
            copy.deepcopy(list(recipe["execution_order"])),
        )
        _, total_bytes, manifest_sha = task_state_manifest(output)
        return recipe, total_bytes, manifest_sha
    finally:
        shutil.rmtree(workset, ignore_errors=True)


def build_task_state_minimum_packet(
    *,
    task_id: str,
    action_refs: list[str],
    adi_record_ids: list[str],
    root: Path = ROOT,
    registry_path: Path = REGISTRY_PATH,
) -> dict[str, Any]:
    task = _require_ref(task_id, "HOLD_TASK_PACKET_TASK_ID_INVALID")
    actions = _require_refs(
        action_refs,
        "HOLD_TASK_PACKET_ACTION_REFS_INVALID",
    )
    adi_ids = _require_refs(
        adi_record_ids,
        "HOLD_TASK_PACKET_ADI_RECORD_IDS_INVALID",
    )
    registry = load_rule_registry(
        root=root,
        registry_path=registry_path,
    )
    entry = registry.get(RULE_REF)
    if entry is None:
        raise TaskStatePacketError("HOLD_TASK_PACKET_LOCAL_RULE_MISSING")

    snapshot = build_task_state_snapshot(
        task_id=task,
        action_refs=actions,
        adi_record_ids=adi_ids,
    )
    _, target_bytes, target_manifest = _materialized_manifest(
        task_id=task,
        action_refs=actions,
        adi_record_ids=adi_ids,
    )
    source_hashes = snapshot["source_hashes"]
    task_state = snapshot["task"]
    adi_packet = snapshot["native_adi_packet"]
    snapshot_sha = snapshot["snapshot_sha256"]
    packet: dict[str, Any] = {
        "schema_version": PACKET_SCHEMA,
        "packet_type": PACKET_TYPE,
        "protocol_version": PROTOCOL_VERSION,
        "packet_ref": (
            f"packet:task-state:{task}:{snapshot_sha[:16]}"
        ),
        "adi_coordinate_ref": (
            "native-adi-packet:sha256:"
            + str(adi_packet["packet_sha256"])
        ),
        "state_ref": f"task:{task}",
        "state_version_ref": (
            f"task-state-snapshot:sha256:{snapshot_sha}"
        ),
        "joint_state_field": {
            "D1": {
                "intent_ref": task_state.get("PARENT_INTENT"),
                "task_ref": f"task:{task}",
            },
            "D2": {
                "task_state": task_state.get("STATE"),
                "priority": task_state.get("PRIORITY"),
                "snapshot_sha256": snapshot_sha,
            },
            "D3": {
                "task_coordinate": task_state.get("D3_COORDINATE"),
                "native_adi_packet_sha256": adi_packet["packet_sha256"],
                "git_head": snapshot["git"].get("head"),
            },
            "D4": dict(source_hashes),
            "D5": {
                "execution_policy": (
                    "LOCAL_VOLATILE_TASK_STATE_RECONSTRUCTION_ONLY"
                ),
                "persistent_materialization_default": False,
                "canonical_write": False,
                "service_restart": False,
            },
            "D6": {
                "mode": "LOCAL_RULE_REF_MINIMUM_STATE",
                "rule_body_transmitted": False,
                "target_bytes_transmitted": 0,
                "differential_payload_bytes": 0,
                "compression_payload_bytes": 0,
                "persistent_materialization_default": False,
            },
            "D7": {
                "fail_closed_on_task_hash_mismatch": True,
                "fail_closed_on_action_hash_mismatch": True,
                "fail_closed_on_checkpoint_hash_mismatch": True,
                "fail_closed_on_adi_packet_mismatch": True,
                "fail_closed_on_rule_hash_mismatch": True,
                "fail_closed_on_final_manifest_mismatch": True,
            },
            "D8": {
                "authority": "CANDIDATE_ONLY",
                "canonical": False,
                "formal_effect_authority": "LOCAL_TOTAL_FIELD",
            },
            "coupling_rule": (
                "TASK_LEDGER_ACTION_CHECKPOINT_ADI_BIND_ONE_STATE_SNAPSHOT"
            ),
        },
        "rule_binding": {
            "rule_ref": RULE_REF,
            "implementation_ref": entry["implementation_ref"],
            "implementation_sha256": entry["implementation_sha256"],
            "minimum_information_keys": entry["minimum_information_keys"],
        },
        "minimum_new_information": {
            "task_id": task,
            "action_refs": actions,
            "adi_record_ids": adi_ids,
        },
        "necessary_condition_refs": [
            "condition:task-state-records-exist",
            "condition:selected-actions-bind-task",
            "condition:native-adi-id-set-match",
            "condition:local-rule-registry-match",
            "condition:volatile-reconstruction",
            "condition:final-manifest-match",
        ],
        "verification": {
            "expected_target_manifest_sha256": target_manifest,
            "expected_target_bytes": target_bytes,
        },
        "packet_sha256": "",
    }
    packet["packet_sha256"] = packet_sha256(packet)
    validate_minimum_packet(
        packet,
        root=root,
        registry_path=registry_path,
    )
    return packet


def issue_task_state_minimum_packet(
    *,
    task_id: str,
    action_refs: list[str],
    support_adi_record_ids: list[str],
) -> dict[str, Any]:
    inserted = insert_task_state_adi_record(
        task_id=task_id,
        action_refs=action_refs,
        support_adi_record_ids=support_adi_record_ids,
    )
    adi_record_ids = [
        *support_adi_record_ids,
        inserted["record_id"],
    ]
    packet = build_task_state_minimum_packet(
        task_id=task_id,
        action_refs=action_refs,
        adi_record_ids=adi_record_ids,
    )
    return {
        "state": "PASS_REAL_TASK_STATE_MINIMUM_PACKET_ISSUED",
        "task_state_record_id": inserted["record_id"],
        "task_state_record": inserted["record"],
        "support_snapshot_sha256": inserted[
            "support_snapshot_sha256"
        ],
        "packet": packet,
    }


def build_task_model_visible_context(
    workset_path: Path,
    packet: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    def load(name: str) -> dict[str, Any]:
        path = workset_path / name
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise TaskStatePacketError(
                "HOLD_TASK_CONTEXT_WORKSET_INVALID"
            ) from exc
        if not isinstance(value, dict):
            raise TaskStatePacketError(
                "HOLD_TASK_CONTEXT_WORKSET_INVALID"
            )
        return value

    task_state = load("task_state.json")
    action_state = load("action_state.json")
    checkpoint = load("checkpoint.json")
    adi_packet = load("native_adi_packet.json")
    task = task_state["task"]
    actions = action_state.get("actions", [])
    action_projection = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        confirmed = item.get("LAST_CONFIRMED_EFFECT")
        confirmed_state = (
            confirmed.get("state")
            if isinstance(confirmed, dict)
            else None
        )
        action_projection.append(
            {
                "action_ref": item.get("ACTION_ID"),
                "state": item.get("STATE"),
                "target_coordinate": item.get("TARGET_COORDINATE"),
                "confirmed_effect_state": confirmed_state,
                "resume_from": item.get("RESUME_FROM"),
                "error": item.get("ERROR"),
            }
        )

    lookup = adi_packet.get("reference_lookup")
    entries = lookup.get("entries", []) if isinstance(lookup, dict) else []
    adi_refs = [
        item.get("id")
        for item in entries
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    verification = adi_packet.get("verification")
    verification = verification if isinstance(verification, dict) else {}
    source = adi_packet.get("source")
    source = source if isinstance(source, dict) else {}

    task_ref = str(task.get("TASK_ID"))
    context_ref = (
        f"context:task-state:{task_ref}:"
        + str(packet["packet_sha256"])[:16]
    )
    evidence_refs = list(
        dict.fromkeys(
            [
                *[str(ref) for ref in adi_refs],
                *[
                    str(item.get("ACTION_ID"))
                    for item in actions
                    if isinstance(item, dict)
                    and isinstance(item.get("ACTION_ID"), str)
                ],
            ]
        )
    )
    return {
        "context_ref": context_ref,
        "state_projection": {
            "task": {
                "task_ref": f"task:{task_ref}",
                "title": task.get("TITLE"),
                "description": task.get("DESCRIPTION"),
                "state": task.get("STATE"),
                "priority": task.get("PRIORITY"),
                "coordinate": task.get("D3_COORDINATE"),
                "dependencies": task.get("DEPENDENCIES", []),
                "blockers": task.get("BLOCKERS", []),
                "completion_criteria": task.get(
                    "COMPLETION_CRITERIA"
                ),
                "next_action": task.get("NEXT_ACTION"),
            },
            "checkpoint": {
                "current_goal": checkpoint.get("current_goal"),
                "current_state": checkpoint.get("current_state"),
                "last_decision": checkpoint.get("last_decision"),
                "next_action": checkpoint.get("next_action"),
                "d8": checkpoint.get("d8"),
                "hold_reason": checkpoint.get("hold_reason"),
            },
            "actions": action_projection,
            "native_adi": {
                "packet_sha256": adi_packet.get("packet_sha256"),
                "source_state_sha256": source.get("state_sha256"),
                "verification_root": verification.get(
                    "verification_root"
                ),
                "record_refs": adi_refs,
                "adi_packet_decision": adi_packet.get(
                    "total_field_decision"
                ),
            },
            "git": task_state.get("git"),
            "reconstruction_receipt": {
                "target_manifest_sha256": receipt.get(
                    "target_manifest_sha256"
                ),
                "target_files": receipt.get("target_files"),
                "workset_backend": receipt.get("workset_backend"),
            },
        },
        "evidence_refs": evidence_refs,
        "capability_refs": [
            "capability:total-field-pointer-first-context-pull:20260926:v1",
            "capability:gemini-code-assist-a2a-pointer-first:20260926:v1",
        ],
        "acceptance_conditions": [
            "condition:task-state-hashes-match",
            "condition:native-adi-packet-match",
            "condition:candidate-only",
            "condition:return-to-total-field",
        ],
        "schema_refs": [
            "schema:w7tp:origin-state-minimum-packet:2.3-successor",
            "schema:w7tp:task-state-local-snapshot:v1",
        ],
        "interface_refs": [
            "interface:total-field:pointer-first-context-pull",
            "interface:total-field:llm-push",
        ],
        "non_core_rule_capsule_refs": [],
    }


__all__ = [
    "RULE_REF",
    "TaskStatePacketError",
    "build_task_model_visible_context",
    "build_task_state_minimum_packet",
    "insert_task_state_adi_record",
    "issue_task_state_minimum_packet",
]
