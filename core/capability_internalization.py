#!/usr/bin/env python3
"""8D ADI capability-internalization overlay and D3/D5/D7 selector.

This module does not replace resource arbitration or runtime capability owners.
It indexes existing capabilities and preserves the Total Field authority wall.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Iterable

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


def _validate_source_refs(registry: dict[str, Any]) -> None:
    for index, item in enumerate(registry["capabilities"]):
        for ref_index, source_ref in enumerate(item["source_refs"]):
            local_ref = str(source_ref).split("#", 1)[0]
            if not local_ref or ":" in local_ref:
                continue
            if not (ROOT / local_ref).exists():
                raise CapabilityInternalizationError(
                    "CAPABILITY_SOURCE_REF_MISSING",
                    f"$.capabilities[{index}].source_refs[{ref_index}]",
                )


def load_internalization_registry(
    registry_path: Path = REGISTRY_PATH,
    schema_path: Path = SCHEMA_PATH,
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

    _validate_source_refs(registry)
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
