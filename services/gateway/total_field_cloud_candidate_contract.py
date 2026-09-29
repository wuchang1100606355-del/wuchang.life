from __future__ import annotations

import ast
import hashlib
import json
import re
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

from tools.total_field_dynamic_context import (
    STATE_CELL_DIMENSIONS,
    build_8dadi_carrier_capability_registry,
    build_8dadi_state_cell_projection,
    canonical_sha256,
)

from tools.total_field_candidate_gateway import receive_candidate


COMPACT_STATUSES = frozenset({"OK", "HOLD", "BLOCK"})
COMPACT_ACTIONS = frozenset({"READ", "REPLACE", "INSERT", "DELETE"})
MAX_OPERATIONS = 8
MAX_EVIDENCE = 3
MAX_NEEDS = 3
MAX_STRING_LENGTH = 800

_FORBIDDEN_CONTEXT_KEYS = frozenset(
    {
        "authority_envelope_ref",
        "d8",
        "evidence_ref",
        "founder_intent_projection",
        "identity_root",
        "intent_translation_application_rules",
        "local_rule_bindings",
        "private_credential",
        "raw_rule_body",
        "required_local_rule_refs",
        "source_ref",
        "total_field_internal_policy",
        "work_target_lock_contract",
    }
)
_FORBIDDEN_TEXT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"\b(?:sk|gh[pousr])-[A-Za-z0-9_-]{12,}\b",
        r"\bAIza[0-9A-Za-z_-]{20,}\b",
        r"\bBearer\s+[A-Za-z0-9._-]{16,}\b",
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)",
        r"(?:[A-Za-z]:\\|/home/|/etc/|/var/|\\\\wsl|\\\\[^\\\s]+\\)",
        r"\b(?:taiji\d+|my-j-\d+|FOUNDER_NATURAL_PERSON_SOVEREIGN_IDENTITY_ROOT)\b",
        r"\b(?:identity_root|member_plaintext|private_key|client_secret|refresh_token)\b",
    )
)
_SYMBOLIC_OBJECT_REF = re.compile(r"(?:CELL|FILE|OBJECT)_[A-Z0-9]+")
_PROJECTABLE_OBJECT_TYPES = (ast.AsyncFunctionDef, ast.ClassDef, ast.FunctionDef)


class CloudCandidateContractError(ValueError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CloudCandidateContractError(f"HOLD_CLOUD_CONTEXT_{field.upper()}_MISSING")
    return value.strip()


def _local_state_cell(dynamic_context: Mapping[str, Any]) -> dict[str, Any]:
    founder = dynamic_context.get("founder_intent_projection")
    if not isinstance(founder, Mapping):
        raise CloudCandidateContractError("HOLD_CLOUD_CONTEXT_FOUNDER_PROJECTION_MISSING")
    dimensions = {name: deepcopy(founder.get(name)) for name in STATE_CELL_DIMENSIONS}
    if any(value is None for value in dimensions.values()):
        raise CloudCandidateContractError("HOLD_CLOUD_CONTEXT_8D_PROJECTION_INCOMPLETE")

    source_ref = _required_text(founder.get("source_ref"), "source_ref")
    source_sha256 = _required_text(founder.get("source_sha256"), "source_sha256")
    if re.fullmatch(r"[0-9a-f]{64}", source_sha256) is None:
        raise CloudCandidateContractError("HOLD_CLOUD_CONTEXT_SOURCE_SHA256_INVALID")

    route = dynamic_context.get("capability_route") or {}
    lookup = route.get("skill_lookup") if isinstance(route, Mapping) else {}
    capability = _required_text(
        lookup.get("selected_skill") if isinstance(lookup, Mapping) else None,
        "capability",
    )
    return {
        "cell_id": f"state-cell:{source_sha256[:24]}",
        "cell_class": "CURRENT_FOUNDER_INTENT_TASK",
        "node": source_ref,
        "capability": capability,
        "state": "CANDIDATE",
        "dimensions": dimensions,
        "evidence_ref": source_ref,
        "evidence_sha256": source_sha256,
        "freshness": _required_text(founder.get("state"), "freshness"),
        "relations": [],
        "source_class": "USER_DECLARED_CURRENT_INTENT",
        "target_eligible": True,
        "authority_envelope_ref": None,
    }


def build_local_state_cell_stack(dynamic_context: Mapping[str, Any]) -> dict[str, Any]:
    if dynamic_context.get("state") != "TOTAL_FIELD_DYNAMIC_CONTEXT_READY":
        raise CloudCandidateContractError("HOLD_CLOUD_CONTEXT_NOT_READY")
    if dynamic_context.get("retrieval_method") != "8DADI_MEMORY_INDEX_ONLY":
        raise CloudCandidateContractError("HOLD_CLOUD_CONTEXT_RETRIEVAL_INVALID")

    cell = _local_state_cell(dynamic_context)
    located = {
        "state": "TOTAL_FIELD_8DADI_LOCATED_EVIDENCE_READY",
        "target_field_sha256": cell["evidence_sha256"],
        "carrier_capability_registry_sha256": build_8dadi_carrier_capability_registry()[
            "packet_sha256"
        ],
        "observations_used": 1,
        "cell_candidates": [cell],
        "policy": {
            "evidence_only": True,
            "8dadi_located_coordinates_only": True,
            "carrier_registry_bound": True,
            "workspace_search": False,
            "old_version_target_import": False,
            "personal_data_included": False,
        },
    }
    located["packet_sha256"] = canonical_sha256(located)
    stack = build_8dadi_state_cell_projection(
        located,
        cell_budget=1,
        relation_traversal_budget=1,
        observation_budget=1,
    )
    if stack.get("state") != "8DADI_STATE_CELL_PROJECTION_CANDIDATE_READY":
        raise CloudCandidateContractError(str(stack.get("state") or "HOLD_STATE_CELL_STACK"))
    return stack


def _reject_sensitive(value: Any, path: str = "context") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in _FORBIDDEN_CONTEXT_KEYS or re.fullmatch(r"d[1-8]", normalized):
                raise CloudCandidateContractError(f"BLOCK_CONTEXT_LEAK:{path}.{key}")
            _reject_sensitive(child, f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_sensitive(child, f"{path}[{index}]")
        return
    if isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            raise CloudCandidateContractError(f"BLOCK_CONTEXT_STRING_TOO_LONG:{path}")
        if any(pattern.search(value) for pattern in _FORBIDDEN_TEXT_PATTERNS):
            raise CloudCandidateContractError(f"BLOCK_CONTEXT_LEAK:{path}")


def compact_output_contract() -> dict[str, Any]:
    return {
        "format": "COMPACT_JSON_ONLY",
        "authority": "CANDIDATE_ONLY",
        "fields": ["s", "o", "e", "n"],
        "statuses": sorted(COMPACT_STATUSES),
        "actions": sorted(COMPACT_ACTIONS),
        "operation_fields": ["f", "a", "p", "v"],
        "object_reference": "SYMBOLIC_ONLY_CELL_FILE_OR_OBJECT",
        "max_operations": MAX_OPERATIONS,
        "max_evidence": MAX_EVIDENCE,
        "max_needs": MAX_NEEDS,
        "max_string_length": MAX_STRING_LENGTH,
        "forbidden": [
            "MARKDOWN",
            "GREETING",
            "CLOSING",
            "EXPLANATION",
            "TASK_RESTATEMENT",
            "REASONING_TRACE",
            "FULL_FILE_OUTPUT",
            "UNCHANGED_CONTENT",
            "DUPLICATE_CONTENT",
        ],
    }


def _symbol_suffix(index: int) -> str:
    if index < 0 or index >= 26:
        raise CloudCandidateContractError("HOLD_CODE_PROJECTION_SYMBOL_LIMIT")
    return chr(ord("A") + index)


def project_allowlisted_code(
    repo_root: Path,
    fragment_allowlist: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Project explicitly allowlisted Python objects without exposing local coordinates."""
    root = repo_root.resolve()
    if not fragment_allowlist:
        raise CloudCandidateContractError("HOLD_CODE_PROJECTION_ALLOWLIST_MISSING")

    visible_objects: list[dict[str, str]] = []
    local_symbol_map: dict[str, dict[str, str]] = {}
    for file_index, entry in enumerate(fragment_allowlist):
        if not isinstance(entry, Mapping):
            raise CloudCandidateContractError("HOLD_CODE_PROJECTION_ALLOWLIST_INVALID")
        relative = entry.get("path")
        object_names = entry.get("objects")
        if (
            not isinstance(relative, str)
            or not relative
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
            or not isinstance(object_names, list)
            or not object_names
            or any(not isinstance(name, str) or not name for name in object_names)
        ):
            raise CloudCandidateContractError("HOLD_CODE_PROJECTION_ALLOWLIST_INVALID")
        source_path = (root / relative).resolve()
        try:
            source_path.relative_to(root)
        except ValueError as exc:
            raise CloudCandidateContractError("BLOCK_CODE_PROJECTION_OUTSIDE_ROOT") from exc
        if source_path.suffix != ".py" or not source_path.is_file():
            raise CloudCandidateContractError("HOLD_CODE_PROJECTION_SOURCE_INVALID")

        try:
            source = source_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=relative)
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            raise CloudCandidateContractError("HOLD_CODE_PROJECTION_SOURCE_UNREADABLE") from exc
        lines = source.splitlines(keepends=True)
        nodes = {
            node.name: node
            for node in tree.body
            if isinstance(node, _PROJECTABLE_OBJECT_TYPES)
        }
        file_ref = f"FILE_{_symbol_suffix(file_index)}"
        local_symbol_map[file_ref] = {
            "kind": "FILE",
            "path": str(source_path),
        }
        for object_name in object_names:
            node = nodes.get(object_name)
            if node is None or node.end_lineno is None:
                raise CloudCandidateContractError(
                    f"HOLD_CODE_PROJECTION_OBJECT_NOT_FOUND:{object_name}"
                )
            object_ref = f"OBJECT_{_symbol_suffix(len(visible_objects))}"
            object_kind = "class" if isinstance(node, ast.ClassDef) else "function"
            local_snippet = "".join(lines[node.lineno - 1 : node.end_lineno]).strip()
            projected_snippet = re.sub(
                rf"^(?P<prefix>(?:async\s+)?(?:def|class)\s+){re.escape(object_name)}\b",
                rf"\g<prefix>{object_ref}",
                local_snippet,
                count=1,
            )
            _reject_sensitive(projected_snippet, "projected_object")
            visible_objects.append(
                {
                    "ref": object_ref,
                    "file_ref": file_ref,
                    "kind": object_kind,
                    "content": projected_snippet,
                }
            )
            local_symbol_map[object_ref] = {
                "kind": "OBJECT",
                "file_ref": file_ref,
                "name": object_name,
                "object_type": object_kind,
                "source": local_snippet,
            }
    return {
        "model_visible_objects": visible_objects,
        "local_symbol_map": local_symbol_map,
    }


def build_cloud_candidate_request(
    dynamic_context: Mapping[str, Any],
    *,
    task: str,
    repo_root: Path | None = None,
    fragment_allowlist: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    stack = build_local_state_cell_stack(dynamic_context)
    task_text = _required_text(task, "task")
    _reject_sensitive(task_text, "local_task")
    model_visible = {
        "schema_id": "W7TP_CLOUD_CANDIDATE_REQUEST_V1",
        "task": "Produce only candidate operations for the abstract local request.",
        "state_cells": [
            {
                "ref": f"CELL_{index + 1}",
                "state": cell["state"],
                "relation_refs": [
                    f"CELL_{relation_index + 1}"
                    for relation_index, _ in enumerate(cell["relations"])
                ],
            }
            for index, cell in enumerate(stack["cells"])
        ],
        "local_rule_result": {
            "state": "ALLOW_CANDIDATE_REASONING_ONLY",
            "provider_authority": "NONE",
            "external_effect": False,
            "local_reconstruction_required": True,
            "raw_local_rules_visible": False,
        },
        "output_contract": compact_output_contract(),
    }
    projection = {"model_visible_objects": [], "local_symbol_map": {}}
    if fragment_allowlist is not None:
        if repo_root is None:
            raise CloudCandidateContractError("HOLD_CODE_PROJECTION_ROOT_MISSING")
        projection = project_allowlisted_code(repo_root, fragment_allowlist)
        model_visible["code_objects"] = projection["model_visible_objects"]
    _reject_sensitive(model_visible)
    local_symbol_map: dict[str, Any] = {
        f"CELL_{index + 1}": cell["cell_id"]
        for index, cell in enumerate(stack["cells"])
    }
    local_symbol_map.update(projection["local_symbol_map"])
    return {
        "state": "CLOUD_CANDIDATE_REQUEST_READY",
        "state_cell_stack": stack,
        "local_symbol_map": local_symbol_map,
        "local_task_sha256": hashlib.sha256(task_text.encode("utf-8")).hexdigest(),
        "model_visible_context": model_visible,
        "model_visible_context_sha256": _sha256(model_visible),
        "provider_route_in_model_context": False,
        "candidate_authority": False,
        "execution_authorized": False,
    }


def _request_field_names(value: Any, prefix: str = "$") -> list[str]:
    names: list[str] = []
    if isinstance(value, Mapping):
        for key in sorted(value):
            path = f"{prefix}.{key}"
            names.append(path)
            names.extend(_request_field_names(value[key], path))
    elif isinstance(value, list):
        for item in value:
            names.extend(_request_field_names(item, f"{prefix}[]"))
    elif isinstance(value, str) and value.startswith(("{", "[")):
        try:
            embedded = json.loads(value)
        except json.JSONDecodeError:
            embedded = None
        if embedded is not None:
            names.extend(_request_field_names(embedded, f"{prefix}.json"))
    return sorted(set(names))


def _reject_sensitive_provider_payload(value: Any, path: str = "provider_payload") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in _FORBIDDEN_CONTEXT_KEYS or re.fullmatch(r"d[1-8]", normalized):
                raise CloudCandidateContractError(f"BLOCK_CONTEXT_LEAK:{path}.{key}")
            _reject_sensitive_provider_payload(child, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sensitive_provider_payload(child, f"{path}[{index}]")
        return
    if isinstance(value, str):
        if value.startswith(("{", "[")):
            try:
                embedded = json.loads(value)
            except json.JSONDecodeError:
                embedded = None
            if embedded is not None:
                _reject_sensitive_provider_payload(embedded, f"{path}.json")
                return
        if any(pattern.search(value) for pattern in _FORBIDDEN_TEXT_PATTERNS):
            raise CloudCandidateContractError(f"BLOCK_CONTEXT_LEAK:{path}")
        if len(value) > MAX_STRING_LENGTH:
            raise CloudCandidateContractError(
                f"BLOCK_CONTEXT_STRING_TOO_LONG:{path}"
            )


def build_provider_request_audit(
    provider_payload: Mapping[str, Any],
    candidate_request: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify the final model-visible payload and build a content-free local receipt."""
    _reject_sensitive_provider_payload(provider_payload)
    payload_text = _canonical_json(dict(provider_payload))
    if "local_symbol_map" in payload_text:
        raise CloudCandidateContractError("BLOCK_CONTEXT_LEAK:LOCAL_SYMBOL_MAP")
    payload_bytes = payload_text.encode("utf-8")
    symbol_ids = sorted(
        symbol
        for symbol in candidate_request.get("local_symbol_map", {})
        if isinstance(symbol, str) and _SYMBOLIC_OBJECT_REF.fullmatch(symbol)
    )
    state_cell_ids = sorted(
        str(cell.get("cell_id"))
        for cell in candidate_request.get("state_cell_stack", {}).get("cells", [])
        if isinstance(cell, Mapping) and cell.get("cell_id")
    )
    return {
        "schema_id": "W7TP_SANITIZED_CLOUD_REQUEST_AUDIT_V1",
        "sanitized_request_hash": hashlib.sha256(payload_bytes).hexdigest(),
        "request_field_names": _request_field_names(provider_payload),
        "request_byte_count": len(payload_bytes),
        "state_cell_ids": state_cell_ids,
        "symbol_ids": symbol_ids,
        "leak_checks": {
            "raw_rule_body_sent_to_cloud": False,
            "founder_authority_sent_to_cloud": False,
            "identity_root_sent_to_cloud": False,
            "local_symbol_map_sent_to_cloud": False,
            "real_path_sent_to_cloud": False,
            "full_repository_sent_to_cloud": False,
        },
        "access_token_persisted": False,
        "candidate_authority": False,
        "execution_authorized": False,
    }


def write_provider_request_audit(audit_dir: Path, audit: Mapping[str, Any]) -> Path:
    audit_dir.mkdir(parents=True, exist_ok=True)
    digest = _required_text(audit.get("sanitized_request_hash"), "request_hash")
    path = audit_dir / f"{digest}.json"
    content = _canonical_json(dict(audit)) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise CloudCandidateContractError("HOLD_CLOUD_AUDIT_HASH_COLLISION")
        return path
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)
    return path


def _bounded_string(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise CloudCandidateContractError(f"HOLD_COMPACT_OUTPUT_STRING_REQUIRED:{path}")
    if len(value) > MAX_STRING_LENGTH:
        raise CloudCandidateContractError(f"HOLD_COMPACT_OUTPUT_STRING_TOO_LONG:{path}")
    return value


def validate_compact_candidate_response(raw: str) -> dict[str, Any]:
    if not isinstance(raw, str) or not raw.strip():
        raise CloudCandidateContractError("HOLD_COMPACT_OUTPUT_EMPTY")
    text = raw.strip()
    if text.startswith("```") or not text.startswith("{") or not text.endswith("}"):
        raise CloudCandidateContractError("HOLD_COMPACT_OUTPUT_JSON_ONLY")
    try:
        candidate = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CloudCandidateContractError("HOLD_COMPACT_OUTPUT_INVALID_JSON") from exc
    if not isinstance(candidate, dict) or set(candidate) != {"s", "o", "e", "n"}:
        raise CloudCandidateContractError("HOLD_COMPACT_OUTPUT_SCHEMA")
    if candidate["s"] not in COMPACT_STATUSES:
        raise CloudCandidateContractError("HOLD_COMPACT_OUTPUT_STATUS")
    if not isinstance(candidate["o"], list) or len(candidate["o"]) > MAX_OPERATIONS:
        raise CloudCandidateContractError("HOLD_COMPACT_OUTPUT_OPERATIONS")
    if not isinstance(candidate["e"], list) or len(candidate["e"]) > MAX_EVIDENCE:
        raise CloudCandidateContractError("HOLD_COMPACT_OUTPUT_EVIDENCE")
    if not isinstance(candidate["n"], list) or len(candidate["n"]) > MAX_NEEDS:
        raise CloudCandidateContractError("HOLD_COMPACT_OUTPUT_NEEDS")

    operations: list[dict[str, str]] = []
    operation_signatures: set[str] = set()
    for index, operation in enumerate(candidate["o"]):
        if not isinstance(operation, dict):
            raise CloudCandidateContractError("HOLD_COMPACT_OUTPUT_OPERATION_SCHEMA")
        if not {"f", "a"}.issubset(operation) or not set(operation).issubset(
            {"f", "a", "p", "v"}
        ):
            raise CloudCandidateContractError("HOLD_COMPACT_OUTPUT_OPERATION_SCHEMA")
        normalized = {
            key: _bounded_string(value, f"o[{index}].{key}")
            for key, value in operation.items()
        }
        if normalized["a"] not in COMPACT_ACTIONS:
            raise CloudCandidateContractError("HOLD_COMPACT_OUTPUT_ACTION")
        if _SYMBOLIC_OBJECT_REF.fullmatch(normalized["f"]) is None:
            raise CloudCandidateContractError("HOLD_COMPACT_OUTPUT_REAL_COORDINATE")
        signature = _canonical_json(normalized)
        if signature in operation_signatures:
            raise CloudCandidateContractError("HOLD_COMPACT_OUTPUT_DUPLICATE_OPERATION")
        operation_signatures.add(signature)
        operations.append(normalized)

    evidence = [_bounded_string(value, f"e[{index}]") for index, value in enumerate(candidate["e"])]
    needs = [_bounded_string(value, f"n[{index}]") for index, value in enumerate(candidate["n"])]
    if len(evidence) != len(set(evidence)) or len(needs) != len(set(needs)):
        raise CloudCandidateContractError("HOLD_COMPACT_OUTPUT_DUPLICATE_CONTENT")
    normalized_candidate = {"s": candidate["s"], "o": operations, "e": evidence, "n": needs}
    _reject_sensitive(normalized_candidate, "candidate")
    return normalized_candidate


def compact_candidate_json(candidate: Mapping[str, Any]) -> str:
    return _canonical_json(dict(candidate))


def local_unseal_candidate(
    candidate: Mapping[str, Any],
    candidate_request: Mapping[str, Any],
) -> dict[str, Any]:
    symbol_map = candidate_request.get("local_symbol_map")
    if not isinstance(symbol_map, Mapping):
        raise CloudCandidateContractError("HOLD_LOCAL_SYMBOL_MAP_MISSING")
    operations: list[dict[str, Any]] = []
    for index, operation in enumerate(candidate.get("o", [])):
        target_ref = operation.get("f")
        target = symbol_map.get(target_ref)
        if not isinstance(target, Mapping) or target.get("kind") not in {"FILE", "OBJECT"}:
            raise CloudCandidateContractError(
                f"HOLD_COMPACT_OUTPUT_UNKNOWN_SYMBOL:o[{index}].f"
            )
        normalized = dict(operation)
        normalized["target_ref"] = target_ref
        normalized["target"] = deepcopy(dict(target))
        position = operation.get("p")
        if isinstance(position, str) and _SYMBOLIC_OBJECT_REF.fullmatch(position):
            position_target = symbol_map.get(position)
            if not isinstance(position_target, Mapping):
                raise CloudCandidateContractError(
                    f"HOLD_COMPACT_OUTPUT_UNKNOWN_SYMBOL:o[{index}].p"
                )
            normalized["position_target"] = deepcopy(dict(position_target))
        operations.append(normalized)
    return {
        "state": "LOCAL_UNSEAL_CANDIDATE_READY",
        "status": candidate.get("s"),
        "operations": operations,
        "evidence": deepcopy(list(candidate.get("e", []))),
        "needs": deepcopy(list(candidate.get("n", []))),
        "candidate_authority": False,
        "execution_authorized": False,
    }


def _local_object_base(candidate_request: Mapping[str, Any]) -> dict[str, str]:
    symbol_map = candidate_request.get("local_symbol_map") or {}
    object_state = {
        str(symbol): str(binding["source"])
        for symbol, binding in symbol_map.items()
        if isinstance(binding, Mapping)
        and binding.get("kind") == "OBJECT"
        and isinstance(binding.get("source"), str)
    }
    file_state = {
        str(symbol): _canonical_json(
            sorted(
                object_symbol
                for object_symbol, object_binding in symbol_map.items()
                if isinstance(object_binding, Mapping)
                and object_binding.get("kind") == "OBJECT"
                and object_binding.get("file_ref") == symbol
            )
        )
        for symbol, binding in symbol_map.items()
        if isinstance(binding, Mapping) and binding.get("kind") == "FILE"
    }
    return {**file_state, **object_state}


def _apply_candidate_operations(
    base_state: Mapping[str, str],
    operations: list[Mapping[str, Any]],
) -> dict[str, str]:
    state = dict(base_state)
    for index, operation in enumerate(operations):
        target_ref = str(operation.get("target_ref") or operation.get("f") or "")
        action = operation.get("a")
        if target_ref not in state:
            raise CloudCandidateContractError(
                f"HOLD_LOCAL_RECONSTRUCTION_TARGET_INVALID:o[{index}]"
            )
        if action == "READ":
            continue
        if target_ref.startswith("FILE_"):
            raise CloudCandidateContractError(
                f"HOLD_FULL_FILE_OUTPUT_FORBIDDEN:o[{index}]"
            )
        if action == "DELETE":
            state[target_ref] = ""
            continue
        value = operation.get("v")
        if not isinstance(value, str):
            raise CloudCandidateContractError(
                f"HOLD_LOCAL_RECONSTRUCTION_VALUE_REQUIRED:o[{index}]"
            )
        if action == "REPLACE":
            state[target_ref] = value
        elif action == "INSERT":
            state[target_ref] = state[target_ref] + value
        else:
            raise CloudCandidateContractError(
                f"HOLD_LOCAL_RECONSTRUCTION_ACTION_INVALID:o[{index}]"
            )
    return state


def reconstruct_candidate_locally(
    unsealed_candidate: Mapping[str, Any],
    candidate_request: Mapping[str, Any],
) -> dict[str, Any]:
    base_state = _local_object_base(candidate_request)
    reconstructed = _apply_candidate_operations(
        base_state,
        list(unsealed_candidate.get("operations", [])),
    )
    return {
        "state": "LOCAL_RECONSTRUCTION_CANDIDATE_READY",
        "base_state_sha256": _sha256(base_state),
        "reconstructed_state": reconstructed,
        "reconstructed_state_sha256": _sha256(reconstructed),
        "worktree_modified": False,
        "candidate_authority": False,
        "execution_authorized": False,
    }


def run_local_candidate_pipeline(
    candidate: Mapping[str, Any],
    candidate_request: Mapping[str, Any],
) -> dict[str, Any]:
    intake = receive_candidate(
        {
            "source": "cloud",
            "authority": "CANDIDATE_ONLY",
            "candidate_type": "CompactCandidate",
            "patch": {
                "status": candidate.get("s"),
                "operations": deepcopy(list(candidate.get("o", []))),
                "provider_support": deepcopy(list(candidate.get("e", []))),
                "needs": deepcopy(list(candidate.get("n", []))),
            },
            "quality_score": 0.0,
        },
        source="cloud",
    )
    if intake.get("accepted") is not True:
        raise CloudCandidateContractError("HOLD_TOTAL_FIELD_CANDIDATE_INTAKE_REJECTED")
    if candidate.get("s") != "OK":
        raise CloudCandidateContractError(
            f"{candidate.get('s')}_CLOUD_CANDIDATE_STATUS"
        )
    unsealed = local_unseal_candidate(candidate, candidate_request)
    local_reconstruction = reconstruct_candidate_locally(unsealed, candidate_request)
    return {
        "state": "HOLD_GST_FOUNDER_COMPATIBLE_BINDING_MISSING",
        "candidate_intake": intake,
        "local_unseal": unsealed,
        "local_reconstruction": local_reconstruction,
        "gst_handoff": None,
        "gst_reconstruction": None,
        "8d_revalidation": None,
        "hold_reason": (
            "V2_3_RULE_CONTRACT_HAS_NO_OBSERVED_GENERIC_EXECUTOR_AND_"
            "V2_1_DELTA_CODEC_RECEIVER_IS_NOT_FOUNDER_GST"
        ),
        "candidate_authority": False,
        "execution_authorized": False,
        "total_field_decision": None,
    }
