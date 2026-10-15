#!/usr/bin/env python3
"""8D ADI capability-internalization overlay and D3/D5/D7 selector.

This module does not replace resource arbitration or runtime capability owners.
It indexes existing capabilities and preserves the Total Field authority wall.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = (
    ROOT / "configs/total_field/w7tp_capability_internalization_registry_v1.json"
)
SCHEMA_PATH = (
    ROOT / "schemas/field/w7tp_capability_internalization_registry.schema.json"
)
REQUIRED_CLASSES = frozenset({
    "CLAW",
    "LLM",
    "STATIC_PULL",
    "DYNAMIC_CONTEXT",
    "NODE_COMPUTE",
    "ORIGIN_CELL",
    "GST",
    "NVR_READ",
})


class CapabilityInternalizationError(ValueError):
    """Stable fail-closed registry or selection rejection."""

    def __init__(self, reason_code: str, path: str = "$") -> None:
        self.reason_code = reason_code
        self.path = path
        super().__init__(f"{reason_code}:{path}")


def _load_json(path: Path, reason_code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise CapabilityInternalizationError(reason_code) from exc
    if not isinstance(value, dict):
        raise CapabilityInternalizationError(reason_code)
    return value


def _validate_source_refs(registry: dict[str, Any], root: Path = ROOT) -> None:
    for index, item in enumerate(registry["capabilities"]):
        for ref_index, source_ref in enumerate(item["source_refs"]):
            local_ref = str(source_ref).split("#", 1)[0]
            if not local_ref or ":" in local_ref:
                continue
            if not (root / local_ref).exists():
                raise CapabilityInternalizationError(
                    "CAPABILITY_SOURCE_REF_MISSING",
                    f"$.capabilities[{index}].source_refs[{ref_index}]",
                )


def load_internalization_registry(
    registry_path: Path = REGISTRY_PATH,
    schema_path: Path = SCHEMA_PATH,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Load and validate the overlay without granting any authority."""
    schema = _load_json(schema_path, "CAPABILITY_SCHEMA_READ_FAILED")
    registry = _load_json(registry_path, "CAPABILITY_REGISTRY_READ_FAILED")
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(registry), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        path = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in first.path
        )
        raise CapabilityInternalizationError(
            "CAPABILITY_REGISTRY_SCHEMA_INVALID",
            path,
        )

    capabilities = registry["capabilities"]
    ids = [item["capability_id"] for item in capabilities]
    classes = [item["capability_class"] for item in capabilities]
    if len(ids) != len(set(ids)):
        raise CapabilityInternalizationError("CAPABILITY_ID_DUPLICATE")
    if len(classes) != len(set(classes)):
        raise CapabilityInternalizationError("CAPABILITY_CLASS_DUPLICATE")
    if set(classes) != REQUIRED_CLASSES:
        raise CapabilityInternalizationError("CAPABILITY_CLASS_COVERAGE_INVALID")


    boundary = registry["authority_boundary"]
    if (
        registry.get("canonical") is not False
        or boundary.get("provider_authority") is not False
        or boundary.get("external_authority_inherited") is not False
        or boundary.get("total_field_verify_required") is not True
        or boundary.get("formal_effect_boundary") != "TAIJI01_TOTAL_FIELD"
    ):
        raise CapabilityInternalizationError("CAPABILITY_REGISTRY_AUTHORITY_WALL_INVALID")

    for index, item in enumerate(capabilities):
        d8 = item["d8_authority"]
        if (
            d8.get("provider_authority") is not False
            or d8.get("final_decision") is not False
            or d8.get("canonical") is not False
            or d8.get("requires_total_field_verify") is not True
        ):
            raise CapabilityInternalizationError(
                "CAPABILITY_PROVIDER_AUTHORITY_FORBIDDEN",
                f"$.capabilities[{index}].d8_authority",
            )
        if item["d7_risk"].get("fail_closed") is not True:
            raise CapabilityInternalizationError(
                "CAPABILITY_FAIL_CLOSED_REQUIRED",
                f"$.capabilities[{index}].d7_risk.fail_closed",
            )

    _validate_dependency_graph(registry)
    _validate_source_refs(registry, root)
    return copy.deepcopy(registry)


def _normalized(values: Iterable[str] | None) -> set[str]:
    if values is None:
        return set()
    return {str(value).strip().casefold() for value in values if str(value).strip()}


def select_internalized_capabilities(
    *,
    d3_node: str | None = None,
    d5_modes: Iterable[str] | None = None,
    required_tags: Iterable[str] | None = None,
    forbidden_risks: Iterable[str] | None = None,
    registry_path: Path = REGISTRY_PATH,
    schema_path: Path = SCHEMA_PATH,
) -> dict[str, Any]:
    """Select existing capabilities through D3/D5/D7; D8 remains unchanged."""
    registry = load_internalization_registry(registry_path, schema_path)
    node = str(d3_node).strip().casefold() if d3_node else ""
    modes = {value.upper() for value in _normalized(d5_modes)}
    tags = _normalized(required_tags)
    blocked_risks = _normalized(forbidden_risks)
    selected: list[dict[str, Any]] = []

    for item in registry["capabilities"]:
        d3_nodes = _normalized(item["d3_coordinate"]["node_scope"])
        if node and node not in d3_nodes:
            continue
        mode = str(item["d5_execution"]["mode"]).upper()
        if modes and mode not in modes:
            continue
        item_tags = _normalized(item["selection_tags"])
        if tags and not tags.issubset(item_tags):
            continue
        risk_tags = _normalized(item["d7_risk"]["risk_tags"])
        if blocked_risks.intersection(risk_tags):
            continue
        selected.append(copy.deepcopy(item))

    return {
        "state": "PASS_CAPABILITY_INTERNALIZATION_SELECTION",
        "selection_basis": {
            "D3_node": d3_node,
            "D5_modes": sorted(modes),
            "D7_forbidden_risks": sorted(blocked_risks),
            "required_tags": sorted(tags),
        },
        "authority_boundary": copy.deepcopy(registry["authority_boundary"]),
        "selected_capability_ids": [
            item["capability_id"] for item in selected
        ],
        "selected_capabilities": selected,
    }


CAPABILITY_CONTEXT_SCHEMA = "W7TP_CAPABILITY_CONTEXT_PROJECTION/1.0"
CAPABILITY_REF_PREFIX = "capability:"
REGISTRY_REL = "configs/total_field/w7tp_capability_internalization_registry_v1.json"
SCHEMA_REL = "schemas/field/w7tp_capability_internalization_registry.schema.json"
POINTER_REL = "runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json"
_ID = re.compile(r"^CAP_INTERNAL_[A-Z0-9_]+_V1$")


def _projection_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _validate_dependency_graph(registry: Mapping[str, Any]) -> None:
    by_id = {row["capability_id"]: row for row in registry["capabilities"]}
    done: set[str] = set()
    active: set[str] = set()
    def visit(cid: str) -> None:
        if cid not in by_id:
            raise CapabilityInternalizationError("CAPABILITY_DEPENDENCY_MISSING", cid)
        if cid in active:
            raise CapabilityInternalizationError("CAPABILITY_DEPENDENCY_CYCLE", cid)
        if cid in done:
            return
        active.add(cid)
        for dep in by_id[cid].get("requires_capability_ids", []):
            visit(dep)
        active.remove(cid)
        done.add(cid)
    for cid in by_id:
        visit(cid)


def _source_binding(root: Path, ref: str) -> dict[str, Any]:
    local = str(ref).split("#", 1)[0]
    path = Path(local)
    if path.is_absolute() or ".." in path.parts:
        raise CapabilityInternalizationError("CAPABILITY_SOURCE_PATH_ESCAPE", ref)
    if ":" in local:
        return {"ref": ref, "state": "EXTERNAL_REFERENCE_NOT_PROBED", "sha256": None}
    target = root / path
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise CapabilityInternalizationError("CAPABILITY_SOURCE_PATH_ESCAPE", ref) from exc
    if target.is_file():
        return {"ref": ref, "state": "FILE_HASH_OBSERVED",
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    return {"ref": ref, "state": "DIRECTORY_REFERENCE" if target.is_dir()
            else "LOCALIZED_UNKNOWN_SOURCE_NOT_PRESENT", "sha256": None}


def _source_index_projection(root: Path, ref: str) -> dict[str, Any]:
    """Retain identifiers from known existing indexes, without importing authority."""
    binding = _source_binding(root, ref)
    result = {**binding, "content_scope": "REFERENCE_ONLY", "entries": [],
              "effect_authorization": "NOT_GRANTED_BY_CONTEXT"}
    if binding["state"] != "FILE_HASH_OBSERVED":
        return result
    path = root / ref.split("#", 1)[0]
    entries = []
    if ref == "docs/adi_native/NATIVE_ADI_SOURCE_RULE_MATRIX.md":
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("| `"):
                cells = line.split("|")
                identifier = cells[1].strip().strip("`")
                if re.fullmatch(r"[A-Z0-9_]+", identifier):
                    entries.append({"id": identifier, "source_status": cells[2].strip(),
                                    "role": "RULE_SOURCE_NAVIGATION_NOT_CURRENT_AUTHORITY"})
    elif ref in {"capabilities/W7TP_NATIVE_SKILLS_INDEX.json",
                  "runtime/total_field/secondary_cloud/capability_registry.json",
                  "packets/product_av_ordering_ai/merchant_invention_capability_map.json"}:
        data = _load_json(path, "CAPABILITY_CONTEXT_SOURCE_INDEX_INVALID")
        for item in data.get("skills", []):
            if isinstance(item, str) and re.fullmatch(r"[a-zA-Z0-9_.:-]+", item):
                entries.append({"id": item, "role": "REGISTERED_SKILL_NOT_RUNTIME_PROOF"})
        for item in data.get("capabilities", []):
            if not isinstance(item, Mapping):
                raise CapabilityInternalizationError("CAPABILITY_CONTEXT_SOURCE_INDEX_INVALID", ref)
            identifier = item.get("capability_ref") or item.get("id")
            if not isinstance(identifier, str) or not re.fullmatch(r"[a-zA-Z0-9_.:-]+", identifier):
                raise CapabilityInternalizationError("CAPABILITY_CONTEXT_SOURCE_INDEX_INVALID", ref)
            entries.append({"id": identifier, "role": "SOURCE_RECORDED_CAPABILITY_NOT_ACTIVE_CLAIM"})
    else:
        return result
    if _source_binding(root, ref)["sha256"] != binding["sha256"]:
        raise CapabilityInternalizationError("CAPABILITY_CONTEXT_SOURCE_INDEX_DRIFT", ref)
    if len(entries) > 512:
        raise CapabilityInternalizationError("CAPABILITY_CONTEXT_SOURCE_INDEX_BUDGET", ref)
    result.update(content_scope="ALL_DECLARED_IDENTIFIERS_IN_BOUND_SOURCE", entries=entries,
                  entry_count=len(entries), runtime_readiness="NOT_REOBSERVED")
    return result


def build_capability_context_projection(task: Mapping[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    """Project the existing inventory; never infer runtime readiness or grant effects.

    All catalogue entries remain visible, while exact task requirements and their
    declared dependencies are distinguished. External index references stay
    explicitly unexpanded instead of being counted as complete system coverage.
    """
    task_id = task.get("TASK_ID")
    if not isinstance(task_id, str) or not task_id:
        raise CapabilityInternalizationError("CAPABILITY_CONTEXT_TASK_REQUIRED")
    registry = load_internalization_registry(root / REGISTRY_REL, root / SCHEMA_REL, root=root)
    pointer = _load_json(root / POINTER_REL, "CAPABILITY_CONTEXT_POINTER_MISSING")
    contract_ref = pointer.get("canonical_path")
    if not isinstance(contract_ref, str):
        raise CapabilityInternalizationError("CAPABILITY_CONTEXT_CONTRACT_REF_MISSING")
    contract_binding = _source_binding(root, contract_ref)
    if contract_binding["sha256"] != pointer.get("canonical_sha256"):
        raise CapabilityInternalizationError("CAPABILITY_CONTEXT_CONTRACT_HASH_MISMATCH")
    contract = _load_json(root / contract_ref, "CAPABILITY_CONTEXT_CONTRACT_MISSING")
    if (pointer.get("state") != "ACTIVE_CANONICAL" or
        pointer.get("canonical_id") != contract.get("canonical_id") or
        pointer.get("version") != contract.get("version") or
        contract.get("semantics") != "8_IN_1_SINGLE_DYNAMIC_STATE_FIELD"):
        raise CapabilityInternalizationError("CAPABILITY_CONTEXT_CURRENT_CONTRACT_MISMATCH")
    requested = task.get("REQUIRED_CAPABILITY_IDS", [])
    if (not isinstance(requested, list) or
        any(not isinstance(cid, str) or not _ID.fullmatch(cid) for cid in requested) or
        len(requested) != len(set(requested))):
        raise CapabilityInternalizationError("CAPABILITY_CONTEXT_REQUIREMENTS_INVALID")
    rows = registry["capabilities"]
    by_id = {row["capability_id"]: row for row in rows}
    required = set(requested) | {"CAP_INTERNAL_DYNAMIC_CONTEXT_V1"}
    # Match exact declared source coordinates, not model guesses or keyword similarity.
    deps = task.get("DEPENDENCIES", [])
    coordinate = task.get("D3_COORDINATE", {})
    affected = coordinate.get("affected_closure", []) if isinstance(coordinate, Mapping) else []
    task_source_refs = {x for x in [*deps, *affected] if isinstance(x, str)}
    for row in rows:
        if task_source_refs.intersection(row["source_refs"]):
            required.add(row["capability_id"])
    pending = list(required)
    while pending:
        cid = pending.pop()
        if cid in by_id:
            for dep in by_id[cid].get("requires_capability_ids", []):
                if dep not in required:
                    required.add(dep)
                    pending.append(dep)
    missing = sorted(required - by_id.keys())
    catalogue = []
    for row in sorted(rows, key=lambda x: x["capability_id"]):
        cid = row["capability_id"]
        catalogue.append({
            "capability_id": cid, "capability_ref": CAPABILITY_REF_PREFIX + cid,
            "capability_class": row["capability_class"],
            "registered_status": row["status"], "runtime_readiness": "NOT_REOBSERVED",
            "node_scope": list(row["d3_coordinate"]["node_scope"]),
            "owner_ref": row["d3_coordinate"]["owner_ref"],
            "coordinate_ref": row["d3_coordinate"]["coordinate_ref"],
            "source_bindings": [_source_binding(root, ref) for ref in row["source_refs"]],
            "resource_refs": list(row["resource_refs"]),
            "requires_capability_ids": list(row.get("requires_capability_ids", [])),
            "selection_reason": "REQUIRED_BY_TASK_OR_CONTEXT_DEPENDENCY" if cid in required
                else "CATALOGUE_AWARENESS_ONLY_NOT_SELECTED_FOR_EFFECT",
            "effect_policy": row["d5_execution"]["mode"],
            "risk_tags": list(row["d7_risk"]["risk_tags"]),
            "effect_authorization": "NOT_GRANTED_BY_CONTEXT",
        })
    indices = [_source_index_projection(root, ref) for ref in registry["source_registry_refs"]]
    value = {
        "schema_id": CAPABILITY_CONTEXT_SCHEMA, "task_ref": "task:" + task_id,
        "state": "HOLD_REQUIRED_CAPABILITY_UNRESOLVED" if missing else "BOUND_REGISTERED_CAPABILITY_CONTEXT",
        "system_frame": {"canonical_id": contract["canonical_id"],
                         "version": contract["version"], "semantics": contract["semantics"],
                         "dimensions": copy.deepcopy(contract["dimensions"]),
                         "adi_definition_ref": "AGENTS.md#2.2",
                         "founder_definition_authority": "FOUNDER_ONLY",
                         "effect_authority_ref": "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json",
                         "provider_authority": False},
        "source_bindings": [_source_binding(root, REGISTRY_REL), _source_binding(root, SCHEMA_REL),
                            _source_binding(root, POINTER_REL), contract_binding,
                            _source_binding(root, "AGENTS.md"),
                            _source_binding(root, "core/capability_internalization.py"),
                            _source_binding(root, "tools/w7tp_task_state_local_rule.py"),
                            _source_binding(root, "tools/w7tp_task_state_minimum_packet.py"),
                            _source_binding(root, "tools/total_field_dynamic_context_pull.py"),
                            _source_binding(root, "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json")],
        "catalogue": catalogue,
        "required_capability_ids": sorted(required), "missing_required_capability_ids": missing,
        "catalogue_count": len(catalogue),
        "source_index_refs": indices,
        "coverage": {"scope": "EXACT_BOUND_INTERNALIZATION_REGISTRY",
                     "registry_entries_complete": True,
                     "all_technologies_complete": False,
                     "external_index_contents": "DECLARED_IDENTIFIERS_ONLY_NO_RULE_BODY_OR_AUTHORITY",
                     "unexpanded_index_refs": [v["ref"] for v in indices if v["content_scope"] == "REFERENCE_ONLY"],
                     "task_evidence_scope": "SELECTED_RECORDS_NOT_ENTIRE_HISTORY",
                     "runtime_effect_scope": "NOT_TESTED_BY_INDEX",
                     "dependency_scope": "EXPLICIT_DECLARED_CAPABILITY_DEPENDENCIES_ONLY"},
        "effect_authorization": "NOT_GRANTED_BY_CONTEXT",
    }
    value["projection_sha256"] = _projection_hash(value)
    return value


def validate_capability_context_projection(value: Mapping[str, Any], *, task_ref: str,
                                           capability_refs: Iterable[str] | None = None) -> dict[str, Any]:
    """Reject omitted inventory, wrong task, forged coverage or changed projection."""
    if not isinstance(value, Mapping) or value.get("schema_id") != CAPABILITY_CONTEXT_SCHEMA:
        raise CapabilityInternalizationError("CAPABILITY_CONTEXT_SCHEMA_INVALID")
    out = copy.deepcopy(dict(value)); claimed = out.pop("projection_sha256", None)
    if not isinstance(claimed, str) or claimed != _projection_hash(out):
        raise CapabilityInternalizationError("CAPABILITY_CONTEXT_HASH_MISMATCH")
    if out.get("task_ref") != task_ref:
        raise CapabilityInternalizationError("CAPABILITY_CONTEXT_TASK_MISMATCH")
    catalogue = out.get("catalogue", [])
    if not isinstance(catalogue, list) or out.get("catalogue_count") != len(catalogue):
        raise CapabilityInternalizationError("CAPABILITY_CONTEXT_CATALOGUE_INCOMPLETE")
    if any(not isinstance(row, Mapping) or
           not isinstance(row.get("capability_id"), str) or
           not _ID.fullmatch(row["capability_id"]) or
           not isinstance(row.get("capability_class"), str)
           for row in catalogue):
        raise CapabilityInternalizationError("CAPABILITY_CONTEXT_CATALOGUE_INVALID")
    ids = [row.get("capability_id") for row in catalogue]
    classes = [row.get("capability_class") for row in catalogue]
    if len(ids) != len(set(ids)) or set(classes) != REQUIRED_CLASSES or len(classes) != len(REQUIRED_CLASSES):
        raise CapabilityInternalizationError("CAPABILITY_CONTEXT_CATALOGUE_INCOMPLETE")
    refs = {CAPABILITY_REF_PREFIX + cid for cid in ids}
    if capability_refs is not None and not refs.issubset(set(capability_refs)):
        raise CapabilityInternalizationError("CAPABILITY_CONTEXT_REFERENCE_OMITTED")
    required = out.get("required_capability_ids", [])
    if (not isinstance(required, list) or
        any(not isinstance(cid, str) or not _ID.fullmatch(cid) for cid in required) or
        len(required) != len(set(required))):
        raise CapabilityInternalizationError("CAPABILITY_CONTEXT_REQUIREMENTS_INVALID")
    frame = out.get("system_frame", {})
    if (not isinstance(frame, Mapping) or frame.get("provider_authority") is not False or
        frame.get("founder_definition_authority") != "FOUNDER_ONLY" or
        frame.get("semantics") != "8_IN_1_SINGLE_DYNAMIC_STATE_FIELD"):
        raise CapabilityInternalizationError("CAPABILITY_CONTEXT_AUTHORITY_ESCALATION")
    expected_missing = sorted(set(required) - set(ids))
    if expected_missing != out.get("missing_required_capability_ids"):
        raise CapabilityInternalizationError("CAPABILITY_CONTEXT_REQUIREMENT_COVERAGE_MISMATCH")
    for row in catalogue:
        if row.get("capability_ref") != CAPABILITY_REF_PREFIX + row["capability_id"]:
            raise CapabilityInternalizationError("CAPABILITY_CONTEXT_REFERENCE_MISMATCH")
        if row["capability_id"] in required and not set(row.get("requires_capability_ids", [])).issubset(required):
            raise CapabilityInternalizationError("CAPABILITY_CONTEXT_DEPENDENCY_OMITTED")
        if row.get("effect_authorization") != "NOT_GRANTED_BY_CONTEXT" or row.get("runtime_readiness") != "NOT_REOBSERVED":
            raise CapabilityInternalizationError("CAPABILITY_CONTEXT_AUTHORITY_ESCALATION")
    expected_state = "HOLD_REQUIRED_CAPABILITY_UNRESOLVED" if expected_missing else "BOUND_REGISTERED_CAPABILITY_CONTEXT"
    coverage = out.get("coverage", {})
    if (out.get("state") != expected_state or coverage.get("registry_entries_complete") is not True or
        coverage.get("all_technologies_complete") is not False or
        out.get("effect_authorization") != "NOT_GRANTED_BY_CONTEXT"):
        raise CapabilityInternalizationError("CAPABILITY_CONTEXT_COVERAGE_OVERCLAIM")
    out["projection_sha256"] = claimed
    return out
