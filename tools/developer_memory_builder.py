#!/usr/bin/env python3
"""Persist source-preserving model context into the existing local 8DADI index.

This closes the builder coordinate already named by runtime/developer_memory/README.md.
It never copies raw exports, changes Founder intent, grants D8 authority, or creates
a second memory database. Sanitized source envelopes are immutable and the derived
memory_index.jsonl remains append-only.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field_dynamic_context import (  # noqa: E402
    build_source_preserving_model_orchestration_packet,
)


MEMORY_ROOT_RELATIVE_PATH = Path("runtime/developer_memory")
INDEX_RELATIVE_PATH = Path("indexes/memory_index.jsonl")
SOURCE_DIRECTORY = Path("sources/model_context")
RECORD_DIRECTORY = Path("records/evidence/model_context")
FOUNDER_RECORD_DIRECTORY = Path("records/governance/human")
MAX_INPUT_BYTES = 1_000_000
FOUNDER_STATE_DIMENSIONS = tuple(f"D{index}" for index in range(1, 9))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _resolve_memory_root(root: str | Path) -> tuple[Path, Path]:
    workspace_root = Path(root).resolve()
    memory_root = (workspace_root / MEMORY_ROOT_RELATIVE_PATH).resolve()
    memory_root.relative_to(workspace_root)
    bootstrap = memory_root / "packets/developer_bootstrap.json"
    index = memory_root / INDEX_RELATIVE_PATH
    if not bootstrap.is_file() or not index.is_file():
        raise FileNotFoundError("EXISTING_DEVELOPER_MEMORY_CHAIN_NOT_FOUND")
    return workspace_root, memory_root


def initialize_minimum_base(
    *,
    root: str | Path,
    founder_seed_path: str | Path,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Create one fail-closed developer-memory base from a validated Founder seed."""
    workspace_root = Path(root).resolve()
    memory_root = (workspace_root / MEMORY_ROOT_RELATIVE_PATH).resolve()
    memory_root.relative_to(workspace_root)
    seed_path = Path(founder_seed_path).expanduser().resolve()
    if not seed_path.is_file():
        raise FileNotFoundError(seed_path)
    seed_bytes = seed_path.read_bytes()
    if len(seed_bytes) > MAX_INPUT_BYTES:
        raise ValueError("FOUNDER_SEED_TOO_LARGE")
    seed = json.loads(seed_bytes.decode("utf-8"))
    required = {
        "schema_id",
        "state",
        *FOUNDER_STATE_DIMENSIONS,
        "natural_language_execution_contract",
        "network_policy",
        "legacy_boundary",
        "authority_boundary",
    }
    if not isinstance(seed, Mapping) or not required.issubset(seed):
        raise ValueError("FOUNDER_SEED_8D_ENVELOPE_INCOMPLETE")
    authority = seed.get("authority_boundary")
    if not isinstance(authority, Mapping):
        raise ValueError("FOUNDER_SEED_AUTHORITY_BOUNDARY_INVALID")
    if (
        authority.get("ai_is_authority") is not False
        or authority.get("this_packet_grants_execution_authority") is not False
    ):
        raise ValueError("FOUNDER_SEED_MAY_NOT_GRANT_EXECUTION_AUTHORITY")

    expected_paths = (
        memory_root / "packets/developer_bootstrap.json",
        memory_root / "canonical/developer_overview.json",
        memory_root / "registry/source_manifest.json",
        memory_root / INDEX_RELATIVE_PATH,
    )
    if any(path.exists() for path in expected_paths):
        raise ValueError("DEVELOPER_MEMORY_BASE_ALREADY_EXISTS_OR_PARTIAL")

    timestamp = created_at or _utc_now()
    source_sha256 = sha256_bytes(seed_bytes)
    source_relative = (
        Path("runtime/total_field/intake")
        / f"W7TP_8DADI_FOUNDER_SEED_{source_sha256[:12].upper()}"
        / "FOUNDER_INTENT_8DADI_SEED.json"
    )
    source_path = workspace_root / source_relative
    record_relative = (
        FOUNDER_RECORD_DIRECTORY
        / f"founder-seed--{source_sha256[:12]}.json"
    )
    record_path = memory_root / record_relative
    record = {
        "schema_version": "1.0",
        "memory_id": source_sha256,
        "category": "governance/human",
        "status": "active",
        "trust": "founder_declared",
        "source": {
            "path": source_relative.as_posix(),
            "sha256": source_sha256,
            "size_bytes": len(seed_bytes),
            "captured_at": timestamp,
        },
        "media_type": "application/json",
        "payload": {
            "type": "W7TP_8DADI_FOUNDER_INTENT_REENTRY",
            "state": seed["state"],
            "authority": {
                "intent_source": "FOUNDER_SUPPLIED_VALIDATED_SEED",
                "effect_authority": "TOTAL_FIELD",
                "ai_is_authority": False,
                "execution_authority_granted_by_record": False,
            },
        },
    }
    index_row = {
        "memory_id": source_sha256,
        "category": "governance/human",
        "status": "active",
        "trust": "founder_declared",
        "record_path": record_relative.as_posix(),
        "source_path": source_relative.as_posix(),
        "source_sha256": source_sha256,
        "event": "FOUNDER_MINIMUM_BASE_INITIALIZED",
    }
    overview = {
        "schema_version": "1.0",
        "generated_at": timestamp,
        "workspace": workspace_root.name,
        "authority_order": [
            "CURRENT_FOUNDER_NATURAL_LANGUAGE",
            "LIVE_REPOSITORY_RUNTIME",
            "CANONICAL",
            "SEALED_EVIDENCE",
        ],
        "rules": {
            "unknown_is_not_invented": True,
            "candidate_is_not_authority": True,
            "minimum_context_only": True,
        },
    }
    registry = {
        "schema_version": "1.0",
        "generated_at": timestamp,
        "record_count": 1,
        "source_count": 1,
        "category_counts": {"governance/human": 1},
        "source_status_counts": {"active": 1},
        "sources": [
            {
                "path": source_relative.as_posix(),
                "sha256": source_sha256,
                "status": "active",
            }
        ],
    }
    bootstrap = {
        "schema_version": "1.0",
        "generated_at": timestamp,
        "workspace": workspace_root.name,
        "read_first": [
            "canonical/developer_overview.json",
            "registry/source_manifest.json",
            "indexes/memory_index.jsonl",
        ],
        "retrieval_policy": {
            "exclude_categories_by_default": ["quarantine/conversations"],
            "include_status": ["active"],
            "verify_source_before_code_change": True,
        },
    }

    writes = (
        (source_path, seed_bytes),
        (record_path, canonical_json_bytes(record)),
        (
            memory_root / INDEX_RELATIVE_PATH,
            (
                json.dumps(index_row, ensure_ascii=False, sort_keys=True) + "\n"
            ).encode("utf-8"),
        ),
        (
            memory_root / "canonical/developer_overview.json",
            canonical_json_bytes(overview),
        ),
        (
            memory_root / "registry/source_manifest.json",
            canonical_json_bytes(registry),
        ),
        (
            memory_root / "packets/developer_bootstrap.json",
            canonical_json_bytes(bootstrap),
        ),
    )
    files_changed = []
    for path, data in writes:
        if _immutable_create(path, data):
            files_changed.append(path.relative_to(workspace_root).as_posix())
    return {
        "state": "PASS_MINIMUM_DEVELOPER_MEMORY_BASE_INITIALIZED",
        "founder_seed_sha256": source_sha256,
        "files_changed": files_changed,
        "private_memory_copied": False,
        "canonical_changed": False,
        "d8_granted": False,
        "authority": "FOUNDER_INTENT_SOURCE_NO_EXTERNAL_EFFECT",
    }


def _load_exports(paths: Sequence[str | Path]) -> tuple[list[Mapping[str, Any]], list[str]]:
    if not paths:
        raise ValueError("SOURCE_EXPORT_PATH_REQUIRED")
    exports: list[Mapping[str, Any]] = []
    input_sha256s: list[str] = []
    total_bytes = 0
    for raw_path in paths:
        path = Path(raw_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        data = path.read_bytes()
        total_bytes += len(data)
        if total_bytes > MAX_INPUT_BYTES:
            raise ValueError("SOURCE_EXPORTS_TOO_LARGE")
        value = json.loads(data.decode("utf-8"))
        if not isinstance(value, Mapping):
            raise ValueError("SOURCE_EXPORT_MUST_BE_JSON_OBJECT")
        exports.append(value)
        input_sha256s.append(sha256_bytes(data))
    return exports, sorted(input_sha256s)


def _immutable_create(path: Path, data: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if sha256_bytes(path.read_bytes()) != sha256_bytes(data):
            raise ValueError(f"IMMUTABLE_CONTEXT_COLLISION:{path}")
        return False
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return True


def _append_index_row(index_path: Path, row: Mapping[str, Any]) -> bool:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("a+", encoding="utf-8") as handle:
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except ImportError:  # pragma: no cover - WSL/Linux is the production coordinate
            fcntl = None
        handle.seek(0)
        existing_rows = [
            json.loads(line)
            for line in handle.read().splitlines()
            if line.strip()
        ]
        matches = [item for item in existing_rows if item.get("memory_id") == row["memory_id"]]
        if matches:
            if any(item != row for item in matches):
                raise ValueError("MEMORY_INDEX_BINDING_CONFLICT")
            return False
        handle.seek(0, os.SEEK_END)
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return True


def _latest_index_rows(index_path: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(
        index_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict) or not value.get("memory_id"):
            raise ValueError(f"MEMORY_INDEX_ROW_INVALID:{line_number}")
        latest[str(value["memory_id"])] = value
    return latest


def _append_index_rows(index_path: Path, rows: Sequence[Mapping[str, Any]]) -> bool:
    """Append an exact group of index events under one lock and one fsync."""
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("a+", encoding="utf-8") as handle:
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except ImportError:  # pragma: no cover - WSL/Linux is the production coordinate
            fcntl = None
        handle.seek(0)
        existing = [
            json.loads(line)
            for line in handle.read().splitlines()
            if line.strip()
        ]
        pending = [dict(row) for row in rows if dict(row) not in existing]
        if not pending:
            return False
        handle.seek(0, os.SEEK_END)
        for row in pending:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return True


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_current_founder_intent(
    workspace_root: Path, memory_root: Path
) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
    latest = _latest_index_rows(memory_root / INDEX_RELATIVE_PATH)
    candidates: list[tuple[dict[str, Any], dict[str, Any], Path, Path]] = []
    for row in latest.values():
        if not (
            row.get("category") == "governance/human"
            and row.get("status") == "active"
            and row.get("trust") == "founder_declared"
        ):
            continue
        record_path = (memory_root / str(row.get("record_path", ""))).resolve()
        record_path.relative_to(memory_root)
        if not record_path.is_file():
            raise FileNotFoundError("CURRENT_FOUNDER_INTENT_RECORD_NOT_FOUND")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        payload = record.get("payload") if isinstance(record, Mapping) else None
        if not isinstance(payload, Mapping) or payload.get("type") != (
            "W7TP_8DADI_FOUNDER_INTENT_REENTRY"
        ):
            continue
        source_path = (workspace_root / str(row.get("source_path", ""))).resolve()
        source_path.relative_to(workspace_root)
        source_bytes = source_path.read_bytes()
        if sha256_bytes(source_bytes) != row.get("source_sha256"):
            raise ValueError("CURRENT_FOUNDER_INTENT_SOURCE_DRIFT")
        if record.get("memory_id") != row.get("memory_id"):
            raise ValueError("CURRENT_FOUNDER_INTENT_RECORD_BINDING_MISMATCH")
        source = json.loads(source_bytes.decode("utf-8"))
        if not isinstance(source, Mapping):
            raise ValueError("CURRENT_FOUNDER_INTENT_SOURCE_INVALID")
        candidates.append((dict(row), dict(source), source_path, record_path))
    if not candidates:
        raise ValueError("CURRENT_FOUNDER_INTENT_NOT_INDEXED")
    if len(candidates) != 1:
        raise ValueError("CURRENT_FOUNDER_INTENT_AMBIGUOUS")
    return candidates[0]


def persist_founder_target_lock(
    *,
    root: str | Path,
    primary_goal_zh_tw: str,
    product_name_zh_tw: str,
    competition_name_zh_tw: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Create an append-only successor for the latest Founder target.

    The prior declaration remains immutable D4 evidence.  Its index state is
    advanced to superseded and exactly one new Founder declaration becomes
    active.  This operation does not grant D8 or deployment authority.
    """
    workspace_root, memory_root = _resolve_memory_root(root)
    goal = " ".join(str(primary_goal_zh_tw).split())
    product = " ".join(str(product_name_zh_tw).split())
    competition = " ".join(str(competition_name_zh_tw).split())
    if not goal or not product or not competition:
        raise ValueError("FOUNDER_TARGET_LOCK_FIELDS_REQUIRED")
    goal_sha256 = sha256_bytes(goal.encode("utf-8"))
    old_row, old_source, _, _ = _load_current_founder_intent(
        workspace_root, memory_root
    )
    old_target_lock = old_source.get("target_lock")
    if (
        isinstance(old_target_lock, Mapping)
        and old_target_lock.get("goal_sha256") == goal_sha256
        and old_target_lock.get("locked") is True
    ):
        return {
            "state": "PASS_FOUNDER_TARGET_ALREADY_LOCKED",
            "active_founder_intent_ref": old_row["source_path"],
            "active_founder_intent_sha256": old_row["source_sha256"],
            "goal_sha256": goal_sha256,
            "files_changed": [],
            "canonical_changed": False,
            "d8_granted": False,
            "authority": "FOUNDER_INTENT_TARGET_SOURCE_NO_EXTERNAL_EFFECT",
        }

    timestamp = created_at or _utc_now()
    reentry_id = f"W7TP_8DADI_FOUNDER_TARGET_{goal_sha256[:12].upper()}"
    successor = deepcopy(old_source)
    successor.update(
        {
            "schema_id": "W7TP_8DADI_FOUNDER_INTENT_REENTRY_V1",
            "reentry_id": reentry_id,
            "created_at": timestamp,
            "source_class": "FOUNDER_LATEST_NATURAL_LANGUAGE_TARGET_LOCK",
            "state": "ACTIVE_FOUNDER_TARGET_LOCK_REQUIRES_LIVE_REOBSERVATION",
            "supersedes": {
                "memory_id": old_row["memory_id"],
                "source_ref": old_row["source_path"],
                "source_sha256": old_row["source_sha256"],
            },
        }
    )
    successor["D1"] = {
        "intent": goal,
        "primary_goal_zh_TW": goal,
        "product_goal": (
            f"完成可實際操作的{product}，向評審與社會展示 8D／ADI 的能力。"
        ),
        "competition_goal": f"參加{competition}並取得成績與輿論目光。",
        "persistence_goal": (
            "跨上下文壓縮、模型替換與工作重啟時，從本機 8DADI 索引重放同一目標。"
        ),
    }
    successor["D2"] = {
        "target_state": "COMPETITION_AUDIOVISUAL_XIAOJ_8DADI_DEMO_REOBSERVED_CLOSED",
        "current_state": "TARGET_LOCK_ACTIVE_REQUIRES_PRODUCT_REOBSERVATION",
        "completion_rule": (
            "作品實際可操作、影音店員服務與 8DADI 展示均重新觀測符合目標後才可結案。"
        ),
    }
    prior_nodes = []
    for node in (old_source.get("D3") or {}).get("system_nodes") or []:
        if not isinstance(node, Mapping):
            continue
        item = deepcopy(dict(node))
        item["status"] = "PRIOR_SOURCE_REFERENCE_REQUIRES_LIVE_REOBSERVATION"
        prior_nodes.append(item)
    successor["D3"] = {
        "system_nodes": prior_nodes,
        "relation_rule": (
            "所有節點與模型僅是總場可調度器官；實際路徑由 8DADI 精確定位，區網優先，VPN 僅在區網不可用時使用。"
        ),
        "node_state_source": old_row["source_path"],
        "node_state_current": "UNKNOWN_UNTIL_LIVE_REOBSERVATION",
    }
    successor["D4"] = {
        "evidence_only": [
            "live runtime observation",
            "canonical",
            "hash receipt manifest sealed evidence",
            "versioned historical evidence",
            "founder declaration",
        ],
        "prior_source_ref": old_row["source_path"],
        "prior_source_sha256": old_row["source_sha256"],
        "current_live_observations": [],
        "freshness_rule": (
            "執行前只重新觀測受影響座標；舊節點狀態不得冒充目前事實。"
        ),
    }
    successor["D6"] = {
        "definition": (
            "TARGET_BASE_STATE + MINIMUM_REQUIRED_DELTA + REFERENCES + COORDINATES + "
            "RECONSTRUCTION_RULES + VERIFICATION_RULES -> DESTINATION_DETERMINISTIC_RECONSTRUCTION"
        ),
        "transmission_object": "VERIFIABLE_TARGET_STATE_AND_CAUSAL_RECONSTRUCTION_CONDITIONS",
        "carrier_is_d6": False,
        "prompt_or_cloud_inference_is_d6": False,
        "receiver_rule": "RECONSTRUCT_WITH_VERIFIED_LOCAL_BASE_AND_REOBSERVE_RESULT",
        "cloud_rule": "MINIMUM_CANDIDATE_SUPPLY_RETURN_TO_TOTAL_FIELD_BEFORE_EFFECT",
        "local_first": True,
    }
    successor["D7"] = deepcopy(old_source.get("D7") or {})
    guards = list(successor["D7"].get("pollution_guards") or [])
    for guard in (
        "WORK_TARGET_MAY_NOT_DRIFT_AFTER_CONTEXT_COMPACTION",
        "OPTIMIZATION_MAY_NOT_TRANSFER_PURPOSE",
        "PROVEN_BOUND_CAPABILITY_IS_REUSED_UNTIL_BINDING_DRIFTS",
    ):
        if guard not in guards:
            guards.append(guard)
    successor["D7"]["pollution_guards"] = guards
    successor["D8"] = deepcopy(old_source.get("D8") or {})
    successor["D8"]["packet_self_authority"] = False
    successor["D8"]["this_target_lock_grants_external_effect"] = False
    successor["target_lock"] = {
        "schema_id": "W7TP_8DADI_WORK_TARGET_LOCK_V1",
        "locked": True,
        "goal_sha256": goal_sha256,
        "goal_source": "FOUNDER_LATEST_NATURAL_LANGUAGE",
        "purpose_transfer_forbidden": True,
        "side_question_behavior": "ANSWER_THEN_RETURN_TO_LOCKED_TARGET",
        "compaction_behavior": "REPLAY_FROM_LOCAL_8DADI_INDEX",
        "unlock_only_when": [
            "TARGET_REOBSERVED_CLOSED",
            "FOUNDER_EXPLICITLY_CORRECTS_REPLACES_OR_CANCELS_TARGET",
        ],
    }
    successor["optimization_policy"] = {
        "optimization_allowed": True,
        "must_improve_or_preserve_primary_goal": True,
        "allowed_dimensions": [
            "HUMAN_EXPERIENCE",
            "QUALITY",
            "RELIABILITY",
            "LATENCY",
            "COST",
            "RESOURCE_PRESSURE",
        ],
        "purpose_transfer_forbidden": True,
        "unrelated_work": "DEFER_OUTSIDE_CURRENT_TARGET",
    }
    successor["high_cost_work_policy"] = {
        "applies_to": [
            "IMAGE_SKINNING",
            "HEAVY_AUDIOVISUAL_GENERATION",
            "ARCHITECTURE_OPTION_EXPLORATION",
        ],
        "current_scope": "LOCATE_COMPARE_AND_RECOMMEND_ONLY",
        "implementation": False,
        "model_download": False,
        "paid_compute_execution": False,
        "activation_or_deployment": False,
        "future_execution_requires": "FOUNDER_EXPLICIT_TASK_AND_CURRENT_COST_BOUND",
    }
    successor["external_capability_assimilation"] = {
        "scope": "ANY_TARGET_RELEVANT_EXTERNAL_PROGRAM_SERVICE_MODEL_OR_PROTOCOL_NOT_ONLY_3D",
        "current_mode": "READ_ONLY_CAPABILITY_EXTRACTION_AND_OPTION_COMPARISON",
        "classification": ["REUSE", "ADAPT", "REIMPLEMENT", "REJECT"],
        "installation_or_integration": False,
        "external_authority_import": False,
        "target_aware_minimum_delta_only": True,
        "result": "CANDIDATE_CAPABILITY_CONTRACT_RETURN_TO_TOTAL_FIELD",
    }
    successor["acceptance_contract"] = {
        "product": product,
        "competition": competition,
        "required_observable_outcomes": [
            "CAFE_SERVICE_CLERK_BROWSER_FLOW_USABLE",
            "AUDIOVISUAL_XIAOJ_OBSERVABLY_INTERACTIVE",
            "8DADI_MULTI_NODE_CAPABILITY_DEMONSTRATION_REOBSERVED",
            "LAN_FIRST_OPERATION_AND_OUTAGE_BOUNDARY_REOBSERVED",
        ],
        "test_or_file_existence_alone_is_completion": False,
        "completion_authority": "REOBSERVED_TARGET_STATE_FIELD_UNDER_TOTAL_FIELD",
    }

    source_bytes = canonical_json_bytes(successor)
    source_sha256 = sha256_bytes(source_bytes)
    source_relative = Path("runtime/total_field/intake") / reentry_id / (
        "FOUNDER_INTENT_8DADI_TARGET_LOCK.json"
    )
    source_path = workspace_root / source_relative
    record = {
        "schema_version": "1.0",
        "memory_id": source_sha256,
        "category": "governance/human",
        "status": "active",
        "trust": "founder_declared",
        "source": {
            "path": source_relative.as_posix(),
            "sha256": source_sha256,
            "size_bytes": len(source_bytes),
            "captured_at": timestamp,
        },
        "media_type": "application/json",
        "payload": {
            "type": "W7TP_8DADI_FOUNDER_INTENT_REENTRY",
            "reentry_id": reentry_id,
            "state": successor["state"],
            "intent": goal,
            "product_goal": successor["D1"]["product_goal"],
            "competition_goal": successor["D1"]["competition_goal"],
            "network_invariant": "LAN_PRECEDES_VPN",
            "target_lock": successor["target_lock"],
            "authority": {
                "intent_source": "FOUNDER_LATEST_NATURAL_LANGUAGE",
                "effect_authority": "TOTAL_FIELD",
                "ai_is_authority": False,
                "execution_authority_granted_by_record": False,
            },
            "continuity": (
                "Future models read this verified active source from the existing local 8DADI index."
            ),
        },
    }
    record_bytes = canonical_json_bytes(record)
    record_relative = FOUNDER_RECORD_DIRECTORY / (
        f"{reentry_id.lower()}--{source_sha256[:12]}.json"
    )
    record_path = memory_root / record_relative
    superseded_event = {
        **old_row,
        "status": "superseded",
        "event": "SUPERSEDED_BY_NEWER_FOUNDER_NATURAL_LANGUAGE_TARGET",
        "superseded_by_memory_id": source_sha256,
    }
    active_event = {
        "memory_id": source_sha256,
        "category": "governance/human",
        "status": "active",
        "trust": "founder_declared",
        "record_path": record_relative.as_posix(),
        "source_path": source_relative.as_posix(),
        "source_sha256": source_sha256,
        "event": "FOUNDER_TARGET_LOCK_ACTIVATED",
        "supersedes_memory_id": old_row["memory_id"],
    }

    files_changed: list[str] = []
    if _immutable_create(source_path, source_bytes):
        files_changed.append(source_relative.as_posix())
    if _immutable_create(record_path, record_bytes):
        files_changed.append(
            (MEMORY_ROOT_RELATIVE_PATH / record_relative).as_posix()
        )
    if _append_index_rows(
        memory_root / INDEX_RELATIVE_PATH,
        [superseded_event, active_event],
    ):
        files_changed.append(
            (MEMORY_ROOT_RELATIVE_PATH / INDEX_RELATIVE_PATH).as_posix()
        )
    return {
        "state": "PASS_FOUNDER_TARGET_LOCK_INDEXED",
        "active_founder_intent_ref": source_relative.as_posix(),
        "active_founder_intent_sha256": source_sha256,
        "superseded_founder_intent_ref": old_row["source_path"],
        "goal_sha256": goal_sha256,
        "files_changed": files_changed,
        "canonical_changed": False,
        "d8_granted": False,
        "authority": "FOUNDER_INTENT_TARGET_SOURCE_NO_EXTERNAL_EFFECT",
    }


def persist_model_source_context(
    *,
    root: str | Path,
    export_paths: Sequence[str | Path],
    task_scope: str,
    current_founder_intent_ref: str,
) -> dict[str, Any]:
    """Persist one deterministic sanitized evidence envelope and its 8DADI index row."""
    workspace_root, memory_root = _resolve_memory_root(root)
    exports, input_sha256s = _load_exports(export_paths)
    packet = build_source_preserving_model_orchestration_packet(
        mode="ASSIMILATE_SOURCE_EXPORTS",
        task_scope=task_scope,
        current_founder_intent_ref=current_founder_intent_ref,
        source_exports=exports,
        generated_at="DETERMINISTIC_SOURCE_SET",
    )
    if str(packet.get("state", "")).startswith("HOLD"):
        return {
            "state": packet["state"],
            "files_changed": [],
            "source_payload_retained": False,
            "authority": "NONE",
            "packet_sha256": packet["packet_sha256"],
        }

    source_envelope = {
        "schema_id": "W7TP_8DADI_LOCAL_MODEL_CONTEXT_SOURCE_ENVELOPE_V1",
        "state": "SOURCE_PRESERVED_D4_EVIDENCE",
        "persistence_class": "LOCAL_DISK_APPEND_ONLY_NOT_GIT",
        "raw_exports_copied": False,
        "input_file_sha256s": input_sha256s,
        "model_source_packet": packet,
        "authority": "D4_EVIDENCE_ONLY_NO_D8",
    }
    source_bytes = canonical_json_bytes(source_envelope)
    source_sha256 = sha256_bytes(source_bytes)
    source_relative = SOURCE_DIRECTORY / f"{source_sha256}.json"
    source_path = memory_root / source_relative

    record = {
        "schema_version": "1.0",
        "memory_id": source_sha256,
        "category": "evidence/model_context",
        "status": "active",
        "trust": "source_preserved_external_d4",
        "source": {
            "path": (MEMORY_ROOT_RELATIVE_PATH / source_relative).as_posix(),
            "sha256": source_sha256,
            "size_bytes": len(source_bytes),
        },
        "payload": {
            "type": "W7TP_8DADI_MODEL_SOURCE_CONTEXT",
            "model_source_packet": packet,
            "persistence_class": "LOCAL_DISK_APPEND_ONLY_NOT_GIT",
            "current_founder_intent_changed": False,
            "canonical_changed": False,
            "d8_granted": False,
        },
    }
    record_bytes = canonical_json_bytes(record)
    record_relative = RECORD_DIRECTORY / f"{source_sha256}.json"
    record_path = memory_root / record_relative
    index_row = {
        "memory_id": source_sha256,
        "category": "evidence/model_context",
        "status": "active",
        "trust": "source_preserved_external_d4",
        "record_path": record_relative.as_posix(),
        "source_path": (MEMORY_ROOT_RELATIVE_PATH / source_relative).as_posix(),
        "source_sha256": source_sha256,
    }

    files_changed: list[str] = []
    if _immutable_create(source_path, source_bytes):
        files_changed.append(source_path.relative_to(workspace_root).as_posix())
    if _immutable_create(record_path, record_bytes):
        files_changed.append(record_path.relative_to(workspace_root).as_posix())
    if _append_index_row(memory_root / INDEX_RELATIVE_PATH, index_row):
        files_changed.append(
            (MEMORY_ROOT_RELATIVE_PATH / INDEX_RELATIVE_PATH).as_posix()
        )

    return {
        "state": (
            "PASS_MODEL_SOURCE_CONTEXT_INDEXED"
            if files_changed
            else "PASS_MODEL_SOURCE_CONTEXT_ALREADY_INDEXED"
        ),
        "source_envelope_ref": source_path.relative_to(workspace_root).as_posix(),
        "source_envelope_sha256": source_sha256,
        "record_ref": record_path.relative_to(workspace_root).as_posix(),
        "packet_sha256": packet["packet_sha256"],
        "conflict_count": len(packet["D7_RISK_QUARANTINE"]["conflicts"]),
        "claim_group_count": len(packet["D4_EVIDENCE"]["exact_claim_groups"]),
        "capability_group_count": len(packet["D4_EVIDENCE"]["documented_capability_groups"]),
        "files_changed": files_changed,
        "raw_exports_copied": False,
        "current_founder_intent_changed": False,
        "canonical_changed": False,
        "d8_granted": False,
        "authority": "D4_EVIDENCE_ONLY_NO_D8",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--source-export", action="append")
    parser.add_argument("--task-scope")
    parser.add_argument("--current-founder-intent-ref")
    parser.add_argument("--founder-target-lock", action="store_true")
    parser.add_argument("--primary-goal-zh-tw")
    parser.add_argument("--product-name-zh-tw")
    parser.add_argument("--competition-name-zh-tw")
    parser.add_argument("--created-at")
    parser.add_argument("--initialize-minimum-base", action="store_true")
    parser.add_argument("--founder-seed")
    args = parser.parse_args()
    if args.initialize_minimum_base:
        if not args.founder_seed:
            parser.error("--initialize-minimum-base requires --founder-seed")
        result = initialize_minimum_base(
            root=args.root,
            founder_seed_path=args.founder_seed,
            created_at=args.created_at,
        )
    elif args.founder_target_lock:
        result = persist_founder_target_lock(
            root=args.root,
            primary_goal_zh_tw=args.primary_goal_zh_tw or "",
            product_name_zh_tw=args.product_name_zh_tw or "",
            competition_name_zh_tw=args.competition_name_zh_tw or "",
            created_at=args.created_at,
        )
    else:
        if not args.source_export or not args.task_scope or not args.current_founder_intent_ref:
            parser.error(
                "model-source mode requires --source-export, --task-scope, and "
                "--current-founder-intent-ref"
            )
        result = persist_model_source_context(
            root=args.root,
            export_paths=args.source_export,
            task_scope=args.task_scope,
            current_founder_intent_ref=args.current_founder_intent_ref,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if str(result.get("state", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
