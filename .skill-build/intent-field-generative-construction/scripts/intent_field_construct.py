#!/usr/bin/env python3
"""Build a minimal, source-labelled intent-field generative transfer packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


PROTOCOL = "IFGC-GTP"
PROTOCOL_VERSION = "1.0.0"
PACKET_NAME = "INTENT_FIELD_GENERATIVE_PACKET.json"
SHA_NAME = "INTENT_FIELD_GENERATIVE_PACKET.sha256"
SEAL_NAME = "SEAL.json"
MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_ITEMS = 512
MAX_STATEMENT_BYTES = 16 * 1024

USER_EXPLICIT = "USER_EXPLICIT"
AI_HYPOTHESIS = "AI_COMPLETION_HYPOTHESIS"
PROVENANCE_CLASSES = {
    USER_EXPLICIT,
    AI_HYPOTHESIS,
    "FIELD_EVIDENCE",
    "EXTERNAL_PRIMARY_SOURCE",
    "MODEL_PRIOR_CANDIDATE",
    "AUTHORITY_DECISION_REQUIRED",
}
PERSONAS = (
    "REAL_HUMAN_USER",
    "SILICON_VALLEY_DIGITAL_STARTUP_DIRECTOR_PRODUCT_OWNER",
)
JOURNEY_SCENARIOS = {
    "FIRST_TIME",
    "RETURNING",
    "LOW_PERMISSION",
    "PENDING_REVIEW",
    "APPROVED",
    "REVOKED_OR_EXPIRED",
    "ERROR_OR_TIMEOUT_RECOVERY",
}
SURFACE_MODES = {"DESKTOP", "MOBILE", "NOT_APPLICABLE_WITH_EVIDENCE"}

HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD = "HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD"

EIGHT_D_KEYS = (
    "identity_source",
    "authority_governance",
    "structure_contract",
    "supply_dependency",
    "function_execution",
    "causality_validation",
    "sequence_version",
    "risk_boundary",
)

TRANSFER_INVARIANT = {
    "protocol": "IFGC-GTP",
    "protocol_version": "1.0.0",
    "recipe_semantics": "STABLE",
    "canonical_serialization": "UTF8_SORTED_KEYS_COMPACT",
    "hash_method": "sha256",
    "full_source_embedded": False,
    "receiver_reconstruction_required": True,
    "equivalent_state_verification_required": True,
    "activation_boundary": "NOT_AUTHORIZED",
    "dynamic_depth_may_change_semantics": False,
}

CORE_FUNCTIONS = ("ANALYSIS", "TRANSFER", "CONSTRUCTION", "ADDRESSING")

CANDIDATE_RELATIONS = {
    "CONTINUE",
    "FUSE",
    "REPLACE",
    "PARALLEL_SHADOW",
    "ISOLATE",
    "HOLD",
}

CONTINUATION_AXES = (
    "semantic",
    "structure_contract",
    "dependency",
    "tests",
    "runtime_wiring",
    "data_migration",
    "governance_authority",
    "security",
    "cross_node",
    "recovery",
)

CONTINUATION_STATES = {"ALIGNED", "DELTA", "UNKNOWN"}

RELATION_HARD_GATES: Mapping[str, Tuple[str, ...]] = {
    "CONTINUE": ("input_output_contract", "dependencies", "version"),
    "FUSE": (
        "overlapping_supply",
        "priority",
        "dual_execution_risk",
        "authority_conflict",
    ),
    "REPLACE": (
        "all_consumers",
        "behavioral_equivalence",
        "data_migration",
        "exit_and_recovery",
    ),
    "PARALLEL_SHADOW": ("isolation", "no_effect", "no_mainline_impact"),
    "ISOLATE": ("unrelated_or_risk_boundary",),
    "HOLD": (),
}

RELATION_GATE_STATES = {"PASS", "FAIL", "UNKNOWN"}

SUPPLY_GAP_FIELDS = (
    "uncovered_demands",
    "extra_side_effects",
    "unknown_dynamic_consumers",
    "dependency_cycles",
    "authority_conflicts",
)

RECOVERY_STEPS = ("expand", "migrate", "deprecate")

TRADE_SECRET_BOUNDARY = {
    "private_lookup_tables_included": False,
    "weights_included": False,
    "phase_mapping_included": False,
    "why_it_runs_included": False,
    "internal_reasoning_included": False,
    "public_contract_only": True,
}

FORCE_8D_ESCALATION_TRIGGERS = {
    "MEMBER_IDENTITY",
    "AUTHORITY",
    "SECRET",
    "PRIVACY",
    "CROSS_NODE",
    "FORMAL_RUNTIME",
    "DATABASE",
    "DEPLOYMENT",
    "ROUTING",
    "EXTERNAL",
    "IRREVERSIBLE_EFFECT",
    "UNCERTAIN_FRONTIER",
}

RESOURCE_DOWNSCOPE_TRIGGERS = {
    "RESOURCE_SAVING",
    "RESOURCE_SAVING_DOWNSCOPE",
}

TECHNICAL_CHAIN_STAGES = (
    "RUNTIME_GAP_LOCALIZATION",
    "STATE_FIELD_ANALYSIS",
    "HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD",
    "ADI_COORDINATE_INDEX",
    "CAUSAL_RELATIONAL_SUPPLY_DEPENDENCY_GROUP_FUNCTION_ANALYSIS",
    "CODE_LOOP_CLOSURE",
    "SECOND_SCAN_DIFF",
    "GENERATIVE_TRANSFER_ANALYSIS",
    "PROGRAM_TRANSFER_RUBBING",
    "RECEIVER_RECONSTRUCTION",
    "EQUIVALENT_STATE_VERIFICATION",
    "REAL_HUMAN_USER_JOURNEY",
)

RUNTIME_REVERIFICATION_PATH = (
    "RUNTIME_GAP_LOCALIZATION",
    "HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD",
    "ADI_COORDINATE_INDEX",
    "GENERATIVE_TRANSFER_ANALYSIS",
    "RECEIVER_RECONSTRUCTION",
    "EQUIVALENT_STATE_VERIFICATION",
    "REAL_HUMAN_USER_JOURNEY",
)

FALLBACK_CLASSES = {"MODEL_PRIOR_CANDIDATE", "EXTERNAL_PRIMARY_SOURCE"}

CLOSURE_STAGES = (
    "definition",
    "implementation",
    "caller",
    "input_output",
    "error_handling",
    "tests",
    "wiring",
    "runtime_evidence",
    "rollback",
)

REDTEAM_CHECKS: Mapping[str, Tuple[str, ...]] = {
    "INTENT": ("assumptions", "value", "dark_patterns"),
    "SOURCE": ("poisoning", "version", "license", "source_authority"),
    "ARCHITECTURE": ("privilege", "privacy", "scaling", "single_point", "cost"),
    "CODE": (
        "injection",
        "path_escape",
        "resource_exhaustion",
        "replay",
        "forged_verification",
        "secrets",
    ),
    "HUMAN_JOURNEY": ("misleading", "accessibility", "error_recovery", "roles"),
    "CROSS_NODE_TRANSFER": ("pollution", "drift", "tampering", "rollback"),
    "PRE_ACTIVATION": ("false_pass", "authority", "effect_boundary", "rollback"),
}

BLOCKED_KEYS = {
    "password",
    "passwd",
    "secret",
    "private_key",
    "access_token",
    "refresh_token",
    "raw_token",
    "member_plaintext",
    "member_name",
    "member_email",
    "member_phone",
    "member_address",
    "national_id",
    "cookie",
    "authorization",
}

BLOCKED_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bBearer\s+\S+", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\b09\d{8}\b"),
    re.compile(r"\b[A-Z][12]\d{8}\b"),
)

PLACEHOLDER_WORDS = {
    "placeholder",
    "placeholder-only",
    "not-set",
    "unset",
    "example",
    "dummy",
    "redacted",
}


class ConstructionHold(Exception):
    """Fail closed without including an offending value in the error."""

    def __init__(self, code: str, path: str = "$", detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.path = path
        self.detail = detail

    def report(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "states": ["HOLD", "ACTIVATION_NOT_AUTHORIZED"],
            "first_divergence": self.code,
            "coordinate": self.path,
            "artifacts_written": False,
        }
        if self.detail:
            result["detail"] = self.detail
        return result


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def safe_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        normalized = value.strip().lower()
        return (
            normalized in PLACEHOLDER_WORDS
            or "placeholder" in normalized
            or (normalized.startswith("${") and normalized.endswith("}"))
            or normalized.startswith("env_ref:")
            or normalized.startswith("key_ref:")
            or (normalized.startswith("<") and normalized.endswith(">"))
        )
    if isinstance(value, dict) and len(value) == 1:
        return next(iter(value)).lower() in {"env_ref", "key_ref", "placeholder"}
    return False


def require_dict(value: Any, path: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ConstructionHold("HOLD_SCHEMA_TYPE", path, "expected_object")
    return value


def require_list(value: Any, path: str, *, nonempty: bool = True) -> List[Any]:
    if not isinstance(value, list):
        raise ConstructionHold("HOLD_SCHEMA_TYPE", path, "expected_array")
    if nonempty and not value:
        raise ConstructionHold("HOLD_REQUIRED_EMPTY", path)
    if len(value) > MAX_ITEMS:
        raise ConstructionHold("HOLD_ITEM_LIMIT", path)
    return value


def require_str(value: Any, path: str, *, max_bytes: int = 2048) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConstructionHold("HOLD_REQUIRED_STRING", path)
    if len(value.encode("utf-8")) > max_bytes:
        raise ConstructionHold("HOLD_STRING_LIMIT", path)
    return value


def require_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise ConstructionHold("HOLD_SCHEMA_TYPE", path, "expected_boolean")
    return value


def require_sha256(value: Any, path: str) -> str:
    result = require_str(value, path, max_bytes=64)
    if not re.fullmatch(r"[0-9a-f]{64}", result):
        raise ConstructionHold("HOLD_INVALID_SHA256", path)
    return result


def evidence_refs(value: Any, path: str, *, nonempty: bool = True) -> List[str]:
    refs = require_list(value, path, nonempty=nonempty)
    return [require_str(item, f"{path}[{index}]", max_bytes=512) for index, item in enumerate(refs)]


def require_unique_str_list(value: Any, path: str, *, nonempty: bool = True) -> List[str]:
    items = [
        require_str(item, f"{path}[{index}]", max_bytes=128)
        for index, item in enumerate(require_list(value, path, nonempty=nonempty))
    ]
    if len(items) != len(set(items)):
        raise ConstructionHold("HOLD_DUPLICATE_VALUE", path)
    return items


def scan_sensitive(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            normalized = key_text.lower().replace("-", "_")
            if normalized in BLOCKED_KEYS:
                if safe_placeholder(child):
                    continue
                raise ConstructionHold("HOLD_SENSITIVE_FIELD", f"{path}.{key_text}")
            scan_sensitive(child, f"{path}.{key_text}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_sensitive(child, f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern in BLOCKED_VALUE_PATTERNS:
            if pattern.search(value):
                raise ConstructionHold("HOLD_SENSITIVE_VALUE_PATTERN", path)


def validate_source(value: Any, path: str, expected_class: str) -> Dict[str, str]:
    source = require_dict(value, path)
    source_class = require_str(source.get("class"), f"{path}.class", max_bytes=64)
    if source_class != expected_class:
        raise ConstructionHold("HOLD_SOURCE_CLASS_MISMATCH", f"{path}.class")
    if source.get("authority_asserted") is True:
        raise ConstructionHold("HOLD_SOURCE_CANNOT_GRANT_AUTHORITY", path)
    return {
        "class": source_class,
        "ref": require_str(source.get("ref"), f"{path}.ref", max_bytes=512),
    }


def validate_statement_items(
    value: Any, path: str, expected_class: str
) -> Tuple[List[Dict[str, Any]], set[str]]:
    items = require_list(value, path)
    output: List[Dict[str, Any]] = []
    ids: set[str] = set()
    for index, raw in enumerate(items):
        item_path = f"{path}[{index}]"
        item = require_dict(raw, item_path)
        item_id = require_str(item.get("id"), f"{item_path}.id", max_bytes=128)
        if item_id in ids:
            raise ConstructionHold("HOLD_DUPLICATE_ID", f"{item_path}.id")
        ids.add(item_id)
        statement = require_str(
            item.get("statement"), f"{item_path}.statement", max_bytes=MAX_STATEMENT_BYTES
        )
        output.append(
            {
                "id": item_id,
                "statement_sha256": sha256_text(statement),
                "source": validate_source(item.get("source"), f"{item_path}.source", expected_class),
            }
        )
    return output, ids


def validate_allowed_effects(value: Any, user_ids: set[str]) -> List[Dict[str, Any]]:
    effects = require_list(value, "$.allowed_effects", nonempty=False)
    output: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(effects):
        path = f"$.allowed_effects[{index}]"
        effect = require_dict(raw, path)
        effect_id = require_str(effect.get("id"), f"{path}.id", max_bytes=128)
        if effect_id in seen:
            raise ConstructionHold("HOLD_DUPLICATE_ID", f"{path}.id")
        seen.add(effect_id)
        if effect.get("basis") != USER_EXPLICIT:
            raise ConstructionHold("HOLD_EFFECT_NOT_USER_EXPLICIT", f"{path}.basis")
        refs = [
            require_str(item, f"{path}.source_fragment_ids[{i}]", max_bytes=128)
            for i, item in enumerate(require_list(effect.get("source_fragment_ids"), f"{path}.source_fragment_ids"))
        ]
        if any(ref not in user_ids for ref in refs):
            raise ConstructionHold("HOLD_EFFECT_REFERENCES_NON_USER_SOURCE", f"{path}.source_fragment_ids")
        if "hypothesis_ids" in effect:
            raise ConstructionHold("HOLD_HYPOTHESIS_IN_ALLOWED_EFFECT", path)
        description = require_str(effect.get("description"), f"{path}.description", max_bytes=MAX_STATEMENT_BYTES)
        output.append(
            {
                "id": effect_id,
                "description_sha256": sha256_text(description),
                "basis": USER_EXPLICIT,
                "source_fragment_ids": refs,
            }
        )
    return output


def validate_perspectives(value: Any) -> Dict[str, List[Dict[str, Any]]]:
    perspectives = require_dict(value, "$.perspectives")
    result: Dict[str, List[Dict[str, Any]]] = {}
    for name in PERSONAS:
        items, _ = validate_statement_items(
            perspectives.get(name), f"$.perspectives.{name}", AI_HYPOTHESIS
        )
        result[name] = items
    return result


def _require_dimension_list(value: Any, path: str, *, nonempty: bool) -> List[str]:
    dimensions = require_unique_str_list(value, path, nonempty=nonempty)
    unknown = set(dimensions) - set(EIGHT_D_KEYS)
    if unknown:
        raise ConstructionHold("HOLD_8D_DIMENSION_SET", path)
    return dimensions


def validate_dynamic_depth(value: Any, path: str) -> Dict[str, Any]:
    depth = require_dict(value, path)
    selected = depth.get("selected_depth")
    if not isinstance(selected, int) or isinstance(selected, bool) or not 3 <= selected <= 8:
        raise ConstructionHold("HOLD_8D_DYNAMIC_DEPTH", f"{path}.selected_depth")
    included = _require_dimension_list(
        depth.get("included_dimensions"), f"{path}.included_dimensions", nonempty=True
    )
    omitted = _require_dimension_list(
        depth.get("omitted_dimensions"), f"{path}.omitted_dimensions", nonempty=False
    )
    if len(included) != selected:
        raise ConstructionHold("HOLD_8D_DYNAMIC_DEPTH_COUNT", f"{path}.selected_depth")
    included_set = set(included)
    omitted_set = set(omitted)
    if included_set & omitted_set or included_set | omitted_set != set(EIGHT_D_KEYS):
        raise ConstructionHold("HOLD_8D_DIMENSION_SET", path)
    triggers = require_unique_str_list(
        depth.get("escalation_triggers"), f"{path}.escalation_triggers", nonempty=False
    )
    trigger_set = set(triggers)
    if trigger_set & RESOURCE_DOWNSCOPE_TRIGGERS or depth.get("resource_saving_downscope") is True:
        raise ConstructionHold("HOLD_8D_RESOURCE_DOWNSCOPE", path)
    if depth.get("authority_effect") != "NONE":
        raise ConstructionHold("HOLD_8D_AUTHORITY_EFFECT", f"{path}.authority_effect")
    if depth.get("authority_granted") is not False:
        raise ConstructionHold("HOLD_8D_AUTHORITY_EFFECT", f"{path}.authority_granted")
    if depth.get("resource_saving_only") is not False:
        raise ConstructionHold("HOLD_8D_RESOURCE_DOWNSCOPE", f"{path}.resource_saving_only")
    if trigger_set & FORCE_8D_ESCALATION_TRIGGERS and selected != 8:
        raise ConstructionHold("HOLD_8D_FORCE_DEPTH", f"{path}.selected_depth")
    return {
        "selected_depth": selected,
        "selection_reason_refs": evidence_refs(
            depth.get("selection_reason_refs"), f"{path}.selection_reason_refs"
        ),
        "included_dimensions": included,
        "omitted_dimensions": omitted,
        "escalation_triggers": triggers,
        "authority_effect": "NONE",
        "authority_granted": False,
        "resource_saving_only": False,
        "dynamic_arrangement_is_authority": False,
    }


def validate_eight_d(value: Any) -> Dict[str, Any]:
    eight_d = require_dict(value, "$.eight_d")
    if eight_d.get("definition") != HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD:
        raise ConstructionHold("HOLD_8D_DEFINITION", "$.eight_d.definition")
    dimensions = require_dict(eight_d.get("dimensions"), "$.eight_d.dimensions")
    if set(dimensions) != set(EIGHT_D_KEYS):
        raise ConstructionHold("HOLD_8D_DIMENSION_SET", "$.eight_d.dimensions")
    result: Dict[str, Any] = {}
    for name in EIGHT_D_KEYS:
        path = f"$.eight_d.dimensions.{name}"
        item = require_dict(dimensions.get(name), path)
        if item.get("status") != "PASS":
            raise ConstructionHold("HOLD_8D_GATE", path)
        result[name] = {
            "status": "PASS",
            "evidence_refs": evidence_refs(item.get("evidence_refs"), f"{path}.evidence_refs"),
        }
    return {
        "definition": HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD,
        "not_ninth_dimension": True,
        "dynamic_depth": validate_dynamic_depth(eight_d.get("dynamic_depth"), "$.eight_d.dynamic_depth"),
        "dimensions": result,
    }


def validate_adi_map(value: Any) -> Dict[str, Any]:
    adi = require_dict(value, "$.adi_map")
    nodes_raw = require_list(adi.get("nodes"), "$.adi_map.nodes")
    nodes: List[Dict[str, Any]] = []
    node_ids: set[str] = set()
    for index, raw in enumerate(nodes_raw):
        path = f"$.adi_map.nodes[{index}]"
        item = require_dict(raw, path)
        node_id = require_str(item.get("id"), f"{path}.id", max_bytes=128)
        if node_id in node_ids:
            raise ConstructionHold("HOLD_DUPLICATE_ADI_NODE", f"{path}.id")
        node_ids.add(node_id)
        source_class = require_str(item.get("source_class"), f"{path}.source_class", max_bytes=64)
        if source_class not in PROVENANCE_CLASSES:
            raise ConstructionHold("HOLD_UNKNOWN_SOURCE_CLASS", f"{path}.source_class")
        nodes.append(
            {
                "id": node_id,
                "coordinate_ref": require_str(item.get("coordinate_ref"), f"{path}.coordinate_ref", max_bytes=512),
                "source_class": source_class,
            }
        )
    edges: List[Dict[str, str]] = []
    for index, raw in enumerate(require_list(adi.get("edges"), "$.adi_map.edges")):
        path = f"$.adi_map.edges[{index}]"
        edge = require_dict(raw, path)
        source = require_str(edge.get("from"), f"{path}.from", max_bytes=128)
        target = require_str(edge.get("to"), f"{path}.to", max_bytes=128)
        if source not in node_ids or target not in node_ids:
            raise ConstructionHold("HOLD_ADI_EDGE_DANGLING", path)
        edges.append(
            {
                "from": source,
                "to": target,
                "relation": require_str(edge.get("relation"), f"{path}.relation", max_bytes=64),
            }
        )
    frontiers = [
        require_str(item, f"$.adi_map.unknown_frontiers[{index}]", max_bytes=512)
        for index, item in enumerate(require_list(adi.get("unknown_frontiers", []), "$.adi_map.unknown_frontiers", nonempty=False))
    ]
    return {"nodes": nodes, "edges": edges, "unknown_frontiers": frontiers}


def validate_patterns(value: Any) -> Dict[str, Any]:
    patterns = require_dict(value, "$.pattern_recall")
    result: Dict[str, Any] = {"internal": [], "external": []}
    for group in ("internal", "external"):
        for index, raw in enumerate(require_list(patterns.get(group), f"$.pattern_recall.{group}", nonempty=False)):
            path = f"$.pattern_recall.{group}[{index}]"
            item = require_dict(raw, path)
            normalized: Dict[str, Any] = {
                "id": require_str(item.get("id"), f"{path}.id", max_bytes=128),
                "source_ref": require_str(item.get("source_ref"), f"{path}.source_ref", max_bytes=512),
                "version_ref": require_str(item.get("version_ref"), f"{path}.version_ref", max_bytes=256),
                "sha256": require_sha256(item.get("sha256"), f"{path}.sha256"),
            }
            if group == "external":
                if item.get("license_status") != "PASS":
                    raise ConstructionHold("HOLD_EXTERNAL_LICENSE", f"{path}.license_status")
                if item.get("source_authority_status") != "PASS":
                    raise ConstructionHold("HOLD_EXTERNAL_SOURCE_AUTHORITY", f"{path}.source_authority_status")
                normalized.update(
                    {"license_status": "PASS", "source_authority_status": "PASS"}
                )
            result[group].append(normalized)
    return result


def validate_architecture(value: Any) -> Dict[str, Any]:
    architecture = require_dict(value, "$.architecture")
    if architecture.get("status") != "PASS":
        raise ConstructionHold("HOLD_ARCHITECTURE_GATE", "$.architecture.status")
    components: List[Dict[str, str]] = []
    for index, raw in enumerate(require_list(architecture.get("components"), "$.architecture.components")):
        path = f"$.architecture.components[{index}]"
        item = require_dict(raw, path)
        components.append(
            {
                "id": require_str(item.get("id"), f"{path}.id", max_bytes=128),
                "kind": require_str(item.get("kind"), f"{path}.kind", max_bytes=128),
                "interface_ref": require_str(item.get("interface_ref"), f"{path}.interface_ref", max_bytes=512),
            }
        )
    constraints: List[Dict[str, Any]] = []
    for index, raw in enumerate(require_list(architecture.get("constraints"), "$.architecture.constraints")):
        path = f"$.architecture.constraints[{index}]"
        item = require_dict(raw, path)
        if item.get("status") != "PASS":
            raise ConstructionHold("HOLD_ARCHITECTURE_CONSTRAINT", path)
        constraints.append(
            {
                "id": require_str(item.get("id"), f"{path}.id", max_bytes=128),
                "status": "PASS",
                "evidence_refs": evidence_refs(item.get("evidence_refs"), f"{path}.evidence_refs"),
            }
        )
    return {
        "status": "PASS",
        "components": components,
        "constraints": constraints,
        "evidence_refs": evidence_refs(architecture.get("evidence_refs"), "$.architecture.evidence_refs"),
    }


def safe_relative_path(value: Any, path: str) -> str:
    raw = require_str(value, path, max_bytes=512)
    if "\\" in raw or ":" in raw:
        raise ConstructionHold("HOLD_UNSAFE_OUTPUT_PATH", path)
    parsed = PurePosixPath(raw)
    if parsed.is_absolute() or not parsed.parts or ".." in parsed.parts or "." in parsed.parts:
        raise ConstructionHold("HOLD_UNSAFE_OUTPUT_PATH", path)
    return str(parsed)


def reject_embedded_source(value: Any, path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in {"content", "source_text", "base64", "blob", "inline_source"}:
                raise ConstructionHold("HOLD_FULL_SOURCE_EMBEDDED", f"{path}.{key}")
            reject_embedded_source(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_embedded_source(child, f"{path}[{index}]")


def normalized_recipe(value: Any, path: str) -> Dict[str, str]:
    recipe = require_dict(value, path)
    reject_embedded_source(recipe, path)
    recipe_type = require_str(recipe.get("type"), f"{path}.type", max_bytes=64)
    if recipe_type not in {"template_ref", "ast_transform", "declarative_generator", "patch_recipe"}:
        raise ConstructionHold("HOLD_UNKNOWN_RECIPE", f"{path}.type")
    return {
        "type": recipe_type,
        "recipe_ref": require_str(recipe.get("recipe_ref"), f"{path}.recipe_ref", max_bytes=512),
        "parameters_sha256": require_sha256(recipe.get("parameters_sha256"), f"{path}.parameters_sha256"),
    }


def validate_code_reconstruction(value: Any) -> Dict[str, Any]:
    code = require_dict(value, "$.code_reconstruction")
    reject_embedded_source(code, "$.code_reconstruction")
    if code.get("status") != "PASS":
        raise ConstructionHold("HOLD_CODE_GATE", "$.code_reconstruction.status")
    if require_bool(code.get("full_source_embedded"), "$.code_reconstruction.full_source_embedded"):
        raise ConstructionHold("HOLD_FULL_SOURCE_EMBEDDED", "$.code_reconstruction.full_source_embedded")
    files: List[Dict[str, Any]] = []
    for index, raw in enumerate(require_list(code.get("files"), "$.code_reconstruction.files")):
        path = f"$.code_reconstruction.files[{index}]"
        item = require_dict(raw, path)
        action = require_str(item.get("action"), f"{path}.action", max_bytes=32)
        if action not in {"create", "modify"}:
            raise ConstructionHold("HOLD_UNKNOWN_FILE_ACTION", f"{path}.action")
        files.append(
            {
                "path": safe_relative_path(item.get("path"), f"{path}.path"),
                "action": action,
                "expected_sha256": require_sha256(item.get("expected_sha256"), f"{path}.expected_sha256"),
                "recipe": normalized_recipe(item.get("recipe"), f"{path}.recipe"),
            }
        )
    return {
        "status": "PASS",
        "full_source_embedded": False,
        "files": files,
        "entrypoint_refs": evidence_refs(code.get("entrypoint_refs"), "$.code_reconstruction.entrypoint_refs"),
    }


def validate_closure(value: Any) -> Dict[str, Any]:
    closure = require_dict(value, "$.closure")
    stages = require_dict(closure.get("stages"), "$.closure.stages")
    result: Dict[str, Any] = {}
    for name in CLOSURE_STAGES:
        path = f"$.closure.stages.{name}"
        item = require_dict(stages.get(name), path)
        if item.get("status") != "PASS":
            raise ConstructionHold("HOLD_CODE_LOOP", path)
        result[name] = {
            "status": "PASS",
            "evidence_refs": evidence_refs(item.get("evidence_refs"), f"{path}.evidence_refs"),
        }
    return {"stages": result}


def validate_runtime_completion_chain(value: Any) -> Dict[str, Any]:
    chain = require_dict(value, "$.runtime_completion_chain")
    if chain.get("runtime_gap_proven") is not True:
        raise ConstructionHold("HOLD_RUNTIME_GAP_NOT_PROVEN", "$.runtime_completion_chain.runtime_gap_proven")
    stages_raw = require_list(chain.get("stages"), "$.runtime_completion_chain.stages")
    if len(stages_raw) != len(TECHNICAL_CHAIN_STAGES):
        raise ConstructionHold("HOLD_RUNTIME_CHAIN_STAGE_SET", "$.runtime_completion_chain.stages")
    stages: List[Dict[str, Any]] = []
    seen: set[str] = set()
    gap_stage_proven = False
    for index, expected_name in enumerate(TECHNICAL_CHAIN_STAGES):
        path = f"$.runtime_completion_chain.stages[{index}]"
        item = require_dict(stages_raw[index], path)
        stage_name = require_str(item.get("stage"), f"{path}.stage", max_bytes=96)
        if stage_name in seen:
            raise ConstructionHold("HOLD_RUNTIME_CHAIN_STAGE_SET", f"{path}.stage")
        seen.add(stage_name)
        if stage_name != expected_name:
            if stage_name in TECHNICAL_CHAIN_STAGES:
                raise ConstructionHold("HOLD_RUNTIME_CHAIN_ORDER", f"{path}.stage")
            raise ConstructionHold("HOLD_RUNTIME_CHAIN_STAGE_SET", f"{path}.stage")
        if item.get("attempted") is not True or item.get("claimed_result") != "UNVERIFIED":
            raise ConstructionHold("HOLD_RUNTIME_CHAIN_GATE", path)
        stage = {
            "stage": stage_name,
            "attempted": True,
            "claimed_result": "UNVERIFIED",
            "evidence_refs": evidence_refs(item.get("evidence_refs"), f"{path}.evidence_refs"),
        }
        if stage_name == "RUNTIME_GAP_LOCALIZATION":
            if item.get("gap_state") != "GAP_PROVEN":
                raise ConstructionHold("HOLD_RUNTIME_GAP_NOT_PROVEN", f"{path}.gap_state")
            gap_stage_proven = True
            stage["gap_state"] = "GAP_PROVEN"
        stages.append(stage)
    if set(seen) != set(TECHNICAL_CHAIN_STAGES) or not gap_stage_proven:
        raise ConstructionHold("HOLD_RUNTIME_CHAIN_STAGE_SET", "$.runtime_completion_chain.stages")
    initial_gap_refs = evidence_refs(
        chain.get("initial_gap_refs", []),
        "$.runtime_completion_chain.initial_gap_refs",
        nonempty=False,
    )
    fallbacks: List[Dict[str, Any]] = []
    for index, raw in enumerate(
        require_list(chain.get("fallbacks", []), "$.runtime_completion_chain.fallbacks", nonempty=False)
    ):
        path = f"$.runtime_completion_chain.fallbacks[{index}]"
        if not initial_gap_refs:
            raise ConstructionHold("HOLD_FALLBACK_INITIAL_GAP_REFS", path)
        item = require_dict(raw, path)
        source_class = require_str(item.get("source_class"), f"{path}.source_class", max_bytes=96)
        if source_class not in FALLBACK_CLASSES:
            raise ConstructionHold("HOLD_FALLBACK_CLASS", f"{path}.source_class")
        if item.get("grants_authority") is not False:
            raise ConstructionHold("HOLD_FALLBACK_AUTHORITY_ESCALATION", path)
        enabled_after = require_str(item.get("enabled_after_stage"), f"{path}.enabled_after_stage", max_bytes=96)
        if enabled_after != TECHNICAL_CHAIN_STAGES[-1]:
            raise ConstructionHold("HOLD_FALLBACK_STAGE", f"{path}.enabled_after_stage")
        target_gap_refs = evidence_refs(item.get("target_gap_refs"), f"{path}.target_gap_refs")
        if not set(target_gap_refs).issubset(set(initial_gap_refs)):
            raise ConstructionHold("HOLD_FALLBACK_TARGET_GAP_REFS", f"{path}.target_gap_refs")
        fallbacks.append(
            {
                "source_class": source_class,
                "enabled_after_stage": enabled_after,
                "target_gap_refs": target_gap_refs,
                "grants_authority": False,
                "rerun_evidence_refs": evidence_refs(
                    item.get("rerun_evidence_refs"), f"{path}.rerun_evidence_refs"
                ),
                "field_evidence_refs": evidence_refs(
                    item.get("field_evidence_refs"), f"{path}.field_evidence_refs"
                ),
            }
        )
    return {
        "runtime_gap_proven": True,
        "initial_gap_refs": initial_gap_refs,
        "ordered_stages": stages,
        "reverification_path": list(RUNTIME_REVERIFICATION_PATH),
        "fallbacks": fallbacks,
    }


def hashed_field(item: Mapping[str, Any], name: str, path: str) -> str:
    return sha256_text(require_str(item.get(name), f"{path}.{name}", max_bytes=MAX_STATEMENT_BYTES))


def validate_journeys(value: Any) -> List[Dict[str, Any]]:
    journeys = require_list(value, "$.user_journeys")
    kinds: set[str] = set()
    scenarios: set[str] = set()
    surfaces: set[str] = set()
    not_applicable_with_evidence = False
    result: List[Dict[str, Any]] = []
    for index, raw in enumerate(journeys):
        path = f"$.user_journeys[{index}]"
        item = require_dict(raw, path)
        kind = require_str(item.get("kind"), f"{path}.kind", max_bytes=64)
        if kind not in {"HAPPY_PATH", "DENIAL_OR_RECOVERY"}:
            raise ConstructionHold("HOLD_UNKNOWN_JOURNEY_KIND", f"{path}.kind")
        kinds.add(kind)
        scenario = require_str(item.get("scenario"), f"{path}.scenario", max_bytes=64)
        if scenario not in JOURNEY_SCENARIOS:
            raise ConstructionHold("HOLD_UNKNOWN_JOURNEY_SCENARIO", f"{path}.scenario")
        scenarios.add(scenario)
        surface = require_str(item.get("surface"), f"{path}.surface", max_bytes=64)
        if surface not in SURFACE_MODES:
            raise ConstructionHold("HOLD_UNKNOWN_JOURNEY_SURFACE", f"{path}.surface")
        surfaces.add(surface)
        evidence = evidence_refs(item.get("evidence_refs"), f"{path}.evidence_refs")
        if surface == "NOT_APPLICABLE_WITH_EVIDENCE":
            not_applicable_with_evidence = bool(evidence)
        if item.get("status") != "PASS":
            raise ConstructionHold("HOLD_USER_JOURNEY", path)
        steps = require_list(item.get("steps"), f"{path}.steps")
        result.append(
            {
                "id": require_str(item.get("id"), f"{path}.id", max_bytes=128),
                "kind": kind,
                "scenario": scenario,
                "surface": surface,
                "role": require_str(item.get("role"), f"{path}.role", max_bytes=128),
                "goal_sha256": hashed_field(item, "goal", path),
                "entry_sha256": hashed_field(item, "entry", path),
                "step_sha256": [
                    sha256_text(require_str(step, f"{path}.steps[{i}]", max_bytes=MAX_STATEMENT_BYTES))
                    for i, step in enumerate(steps)
                ],
                "feedback_sha256": hashed_field(item, "feedback", path),
                "error_recovery_sha256": hashed_field(item, "error_recovery", path),
                "accessibility_sha256": hashed_field(item, "accessibility", path),
                "authorization_boundary_sha256": hashed_field(item, "authorization_boundary", path),
                "exit_sha256": hashed_field(item, "exit", path),
                "claimed_status": "PASS",
                "verification_state": "UNVERIFIED",
                "evidence_refs": evidence,
            }
        )
    if kinds != {"HAPPY_PATH", "DENIAL_OR_RECOVERY"}:
        raise ConstructionHold("HOLD_JOURNEY_SET_INCOMPLETE", "$.user_journeys")
    if scenarios != JOURNEY_SCENARIOS:
        raise ConstructionHold("HOLD_JOURNEY_SCENARIO_SET_INCOMPLETE", "$.user_journeys")
    if not {"DESKTOP", "MOBILE"}.issubset(surfaces) and not not_applicable_with_evidence:
        raise ConstructionHold("HOLD_JOURNEY_SURFACE_SET_INCOMPLETE", "$.user_journeys")
    return result


def validate_redteam(value: Any) -> Dict[str, Any]:
    redteam = require_dict(value, "$.redteam")
    max_rounds = redteam.get("max_rounds")
    if not isinstance(max_rounds, int) or isinstance(max_rounds, bool) or not 1 <= max_rounds <= 3:
        raise ConstructionHold("HOLD_REDTEAM_ROUND_LIMIT", "$.redteam.max_rounds")
    stages = require_dict(redteam.get("stages"), "$.redteam.stages")
    result: Dict[str, Any] = {}
    for stage_name, required_checks in REDTEAM_CHECKS.items():
        path = f"$.redteam.stages.{stage_name}"
        stage = require_dict(stages.get(stage_name), path)
        checks = {
            require_str(item, f"{path}.checks[{index}]", max_bytes=64)
            for index, item in enumerate(require_list(stage.get("checks"), f"{path}.checks"))
        }
        if not set(required_checks).issubset(checks):
            raise ConstructionHold("HOLD_REDTEAM_CHECKS_INCOMPLETE", f"{path}.checks")
        rounds = require_list(stage.get("rounds"), f"{path}.rounds")
        if len(rounds) > max_rounds:
            raise ConstructionHold("HOLD_REDTEAM_ROUND_LIMIT", f"{path}.rounds")
        normalized_rounds: List[Dict[str, Any]] = []
        for index, raw_round in enumerate(rounds):
            round_path = f"{path}.rounds[{index}]"
            round_item = require_dict(raw_round, round_path)
            if round_item.get("round") != index + 1:
                raise ConstructionHold("HOLD_REDTEAM_ROUND_SEQUENCE", f"{round_path}.round")
            if round_item.get("result") != "PASS":
                raise ConstructionHold("HOLD_REDTEAM_UNRESOLVED", round_path)
            issues_fixed = round_item.get("issues_fixed")
            if not isinstance(issues_fixed, int) or isinstance(issues_fixed, bool) or issues_fixed < 0:
                raise ConstructionHold("HOLD_REDTEAM_FIX_COUNT", f"{round_path}.issues_fixed")
            normalized_rounds.append(
                {
                    "round": index + 1,
                    "result": "PASS",
                    "issues_fixed": issues_fixed,
                    "evidence_refs": evidence_refs(round_item.get("evidence_refs"), f"{round_path}.evidence_refs"),
                }
            )
        result[stage_name] = {"checks": sorted(checks), "rounds": normalized_rounds}
    return {"max_rounds": max_rounds, "stages": result}


def validate_transfer(value: Any) -> Dict[str, Any]:
    transfer = require_dict(value, "$.transfer")
    reject_embedded_source(transfer, "$.transfer")
    if transfer.get("mode") != "GENERATIVE_PROGRAM_RUBBING":
        raise ConstructionHold("HOLD_TRANSFER_MODE", "$.transfer.mode")
    if require_bool(transfer.get("full_source_embedded"), "$.transfer.full_source_embedded"):
        raise ConstructionHold("HOLD_FULL_SOURCE_EMBEDDED", "$.transfer.full_source_embedded")
    if not require_bool(transfer.get("semantic_reconstruction"), "$.transfer.semantic_reconstruction"):
        raise ConstructionHold("HOLD_TRANSFER_NOT_GENERATIVE", "$.transfer.semantic_reconstruction")
    if require_bool(transfer.get("byte_identity_claim"), "$.transfer.byte_identity_claim"):
        raise ConstructionHold("HOLD_FALSE_BYTE_IDENTITY_CLAIM", "$.transfer.byte_identity_claim")
    invariant = require_dict(transfer.get("invariant"), "$.transfer.invariant")
    if invariant != TRANSFER_INVARIANT:
        raise ConstructionHold("HOLD_GENERATIVE_TRANSFER_SEMANTIC_DRIFT", "$.transfer.invariant")
    recipes = [
        normalized_recipe(item, f"$.transfer.recipes[{index}]")
        for index, item in enumerate(require_list(transfer.get("recipes"), "$.transfer.recipes"))
    ]
    tests: List[Dict[str, str]] = []
    for index, raw in enumerate(require_list(transfer.get("tests"), "$.transfer.tests")):
        path = f"$.transfer.tests[{index}]"
        item = require_dict(raw, path)
        if item.get("status") != "PASS":
            raise ConstructionHold("HOLD_TRANSFER_TEST", path)
        tests.append(
            {
                "id": require_str(item.get("id"), f"{path}.id", max_bytes=128),
                "status": "PASS",
                "evidence_ref": require_str(item.get("evidence_ref"), f"{path}.evidence_ref", max_bytes=512),
            }
        )
    cross_node = require_dict(transfer.get("cross_node"), "$.transfer.cross_node")
    for gate in ("pollution_guard", "drift_guard", "tamper_guard", "rollback_guard"):
        if cross_node.get(gate) != "PASS":
            raise ConstructionHold("HOLD_CROSS_NODE_GATE", f"$.transfer.cross_node.{gate}")
    return {
        "mode": "GENERATIVE_PROGRAM_RUBBING",
        "semantic_reconstruction": True,
        "byte_identity_claim": False,
        "full_source_embedded": False,
        "invariant": dict(TRANSFER_INVARIANT),
        "recipes": recipes,
        "tests": tests,
        "references": evidence_refs(transfer.get("references"), "$.transfer.references"),
        "cross_node": {
            "source_node": require_str(cross_node.get("source_node"), "$.transfer.cross_node.source_node", max_bytes=128),
            "target_node": require_str(cross_node.get("target_node"), "$.transfer.cross_node.target_node", max_bytes=128),
            "pollution_guard": "PASS",
            "drift_guard": "PASS",
            "tamper_guard": "PASS",
            "rollback_guard": "PASS",
            "rollback_ref": require_str(cross_node.get("rollback_ref"), "$.transfer.cross_node.rollback_ref", max_bytes=512),
        },
        "precision_preservation": "USE_GIT_OR_VERIFIED_CONTENT_ADDRESSING",
    }


def fallback_classes_used(adi_map: Mapping[str, Any], pattern_recall: Mapping[str, Any]) -> set[str]:
    used: set[str] = set()
    if pattern_recall["external"]:
        used.add("EXTERNAL_PRIMARY_SOURCE")
    for node in adi_map["nodes"]:
        source_class = node["source_class"]
        if source_class in FALLBACK_CLASSES:
            used.add(source_class)
    return used


def validate_fallback_usage(runtime_chain: Mapping[str, Any], used_classes: set[str]) -> None:
    declared = {item["source_class"] for item in runtime_chain["fallbacks"]}
    if used_classes - declared:
        raise ConstructionHold("HOLD_FALLBACK_UNDECLARED", "$.runtime_completion_chain.fallbacks")


def validate_dynamic_depth_escalation(
    dynamic_depth: Mapping[str, Any],
    adi_map: Mapping[str, Any],
    pattern_recall: Mapping[str, Any],
    transfer: Mapping[str, Any],
) -> None:
    required: set[str] = set()
    if adi_map["unknown_frontiers"]:
        required.add("UNCERTAIN_FRONTIER")
    if pattern_recall["external"] or any(
        node["source_class"] == "EXTERNAL_PRIMARY_SOURCE" for node in adi_map["nodes"]
    ):
        required.add("EXTERNAL")
    if any(node["source_class"] == "MODEL_PRIOR_CANDIDATE" for node in adi_map["nodes"]):
        required.add("UNCERTAIN_FRONTIER")
    if "cross_node" in transfer:
        required.add("CROSS_NODE")
    triggers = set(dynamic_depth["escalation_triggers"])
    if required - triggers:
        raise ConstructionHold("HOLD_8D_ESCALATION_TRIGGER_MISSING", "$.eight_d.dynamic_depth.escalation_triggers")
    if required and dynamic_depth["selected_depth"] != 8:
        raise ConstructionHold("HOLD_8D_FORCE_DEPTH", "$.eight_d.dynamic_depth.selected_depth")
    if transfer and dynamic_depth["selected_depth"] != 8:
        raise ConstructionHold("HOLD_8D_FORCE_DEPTH", "$.eight_d.dynamic_depth.selected_depth")


def validate_core_functions(value: Any) -> Dict[str, Any]:
    core = require_dict(value, "$.core_functions")
    if set(core) != set(CORE_FUNCTIONS):
        raise ConstructionHold("HOLD_CORE_FUNCTIONS", "$.core_functions")
    result: Dict[str, Any] = {}
    for name in CORE_FUNCTIONS:
        path = f"$.core_functions.{name}"
        item = require_dict(core.get(name), path)
        if item.get("enabled") is not True:
            raise ConstructionHold("HOLD_CORE_FUNCTIONS", f"{path}.enabled")
        result[name] = {
            "enabled": True,
            "evidence_refs": evidence_refs(item.get("evidence_refs"), f"{path}.evidence_refs"),
        }
    return result


def _validate_relational_evidence_binding(value: Any) -> Dict[str, Any]:
    path = "$.relational_evidence"
    binding = require_dict(value, path)
    required = {
        "evidence_class",
        "artifact_ref",
        "artifact_sha256",
        "stage_receipt_ref",
        "stage_receipt_sha256",
    }
    if set(binding) != required:
        raise ConstructionHold("HOLD_RELATIONAL_EVIDENCE_BINDING", path)
    if binding.get("evidence_class") != "FIELD_EVIDENCE":
        raise ConstructionHold("HOLD_RELATIONAL_EVIDENCE_CLASS", f"{path}.evidence_class")
    artifact_ref = safe_relative_path(binding.get("artifact_ref"), f"{path}.artifact_ref")
    stage_ref = safe_relative_path(
        binding.get("stage_receipt_ref"), f"{path}.stage_receipt_ref"
    )
    if not artifact_ref.endswith(".json") or not stage_ref.endswith(".json"):
        raise ConstructionHold("HOLD_RELATIONAL_EVIDENCE_JSON_REF", path)
    return {
        "evidence_class": "FIELD_EVIDENCE",
        "artifact_ref": artifact_ref,
        "artifact_sha256": require_sha256(
            binding.get("artifact_sha256"), f"{path}.artifact_sha256"
        ),
        "stage_receipt_ref": stage_ref,
        "stage_receipt_sha256": require_sha256(
            binding.get("stage_receipt_sha256"), f"{path}.stage_receipt_sha256"
        ),
    }


def _validate_relation_hard_gates(
    value: Any, relation: str, path: str
) -> Dict[str, Any]:
    gates = require_dict(value, path)
    all_gate_names = {
        gate for gate_names in RELATION_HARD_GATES.values() for gate in gate_names
    }
    if relation == "HOLD":
        if not set(gates).issubset(all_gate_names):
            raise ConstructionHold("HOLD_RELATION_GATE_SET", path)
    elif set(gates) != set(RELATION_HARD_GATES[relation]):
        raise ConstructionHold("HOLD_RELATION_GATE_SET", path)
    result: Dict[str, Any] = {}
    for gate_name, raw in gates.items():
        gate_path = f"{path}.{gate_name}"
        gate = require_dict(raw, gate_path)
        if set(gate) != {"state", "evidence_refs"}:
            raise ConstructionHold("HOLD_RELATION_GATE_SHAPE", gate_path)
        state = require_str(gate.get("state"), f"{gate_path}.state", max_bytes=16)
        if state not in RELATION_GATE_STATES:
            raise ConstructionHold("HOLD_RELATION_GATE_STATE", f"{gate_path}.state")
        result[gate_name] = {
            "state": state,
            "evidence_refs": evidence_refs(
                gate.get("evidence_refs"), f"{gate_path}.evidence_refs"
            ),
        }
    return result


def _validate_shortest_route(value: Any, path: str) -> List[Dict[str, Any]]:
    route = require_list(value, path, nonempty=False)
    result: List[Dict[str, Any]] = []
    for index, raw in enumerate(route):
        item_path = f"{path}[{index}]"
        item = require_dict(raw, item_path)
        if set(item) != {"step", "evidence_refs"}:
            raise ConstructionHold("HOLD_RELATION_ROUTE_SHAPE", item_path)
        result.append(
            {
                "step": require_str(item.get("step"), f"{item_path}.step", max_bytes=256),
                "evidence_refs": evidence_refs(
                    item.get("evidence_refs"), f"{item_path}.evidence_refs"
                ),
            }
        )
    return result


def _validate_mainline_relation(value: Any) -> Dict[str, Any]:
    path = "$.mainline_relation"
    relation = require_dict(value, path)
    required = {
        "candidate_relation",
        "hard_gates",
        "missing_gates",
        "first_breakpoint",
        "shortest_continuation_route",
    }
    if set(relation) != required:
        raise ConstructionHold("HOLD_MAINLINE_RELATION_SHAPE", path)
    candidate_relation = require_str(
        relation.get("candidate_relation"), f"{path}.candidate_relation", max_bytes=32
    )
    if candidate_relation not in CANDIDATE_RELATIONS:
        raise ConstructionHold("HOLD_CANDIDATE_RELATION", f"{path}.candidate_relation")
    missing_gates = require_unique_str_list(
        relation.get("missing_gates"), f"{path}.missing_gates", nonempty=False
    )
    breakpoint_raw = relation.get("first_breakpoint")
    first_breakpoint = (
        None
        if breakpoint_raw is None
        else require_str(breakpoint_raw, f"{path}.first_breakpoint", max_bytes=256)
    )
    route = _validate_shortest_route(
        relation.get("shortest_continuation_route"),
        f"{path}.shortest_continuation_route",
    )
    if missing_gates:
        if first_breakpoint != missing_gates[0] or not route:
            raise ConstructionHold("HOLD_RELATION_BREAKPOINT_ROUTE", path)
    elif first_breakpoint is not None or route:
        raise ConstructionHold("HOLD_RELATION_BREAKPOINT_ROUTE", path)
    return {
        "candidate_relation": candidate_relation,
        "hard_gates": _validate_relation_hard_gates(
            relation.get("hard_gates"), candidate_relation, f"{path}.hard_gates"
        ),
        "missing_gates": missing_gates,
        "first_breakpoint": first_breakpoint,
        "shortest_continuation_route": route,
    }


def _validate_continuation_distance(value: Any) -> Dict[str, Any]:
    path = "$.continuation_distance"
    distance = require_dict(value, path)
    if set(distance) != set(CONTINUATION_AXES):
        raise ConstructionHold("HOLD_CONTINUATION_AXIS_SET", path)
    result: Dict[str, Any] = {}
    for axis in CONTINUATION_AXES:
        axis_path = f"{path}.{axis}"
        item = require_dict(distance.get(axis), axis_path)
        if set(item) != {"state", "evidence_refs"}:
            raise ConstructionHold("HOLD_CONTINUATION_AXIS_SHAPE", axis_path)
        state = require_str(item.get("state"), f"{axis_path}.state", max_bytes=16)
        if state not in CONTINUATION_STATES:
            raise ConstructionHold("HOLD_CONTINUATION_AXIS_STATE", f"{axis_path}.state")
        result[axis] = {
            "state": state,
            "evidence_refs": evidence_refs(
                item.get("evidence_refs"), f"{axis_path}.evidence_refs"
            ),
        }
    return result


def _validate_evidenced_items(value: Any, path: str) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(require_list(value, path, nonempty=False)):
        item_path = f"{path}[{index}]"
        item = require_dict(raw, item_path)
        if set(item) != {"id", "evidence_refs"}:
            raise ConstructionHold("HOLD_SUPPLY_DEMAND_ITEM_SHAPE", item_path)
        item_id = require_str(item.get("id"), f"{item_path}.id", max_bytes=128)
        if item_id in seen:
            raise ConstructionHold("HOLD_DUPLICATE_VALUE", f"{item_path}.id")
        seen.add(item_id)
        result.append(
            {
                "id": item_id,
                "evidence_refs": evidence_refs(
                    item.get("evidence_refs"), f"{item_path}.evidence_refs"
                ),
            }
        )
    return result


def _validate_supply_demand_fit(value: Any) -> Dict[str, Any]:
    path = "$.supply_demand_fit"
    fit = require_dict(value, path)
    required = {"old_demand_set", "new_supply_mapping", "recovery_route", *SUPPLY_GAP_FIELDS}
    if set(fit) != required:
        raise ConstructionHold("HOLD_SUPPLY_DEMAND_SHAPE", path)
    old_demands = _validate_evidenced_items(fit.get("old_demand_set"), f"{path}.old_demand_set")
    if not old_demands:
        raise ConstructionHold("HOLD_REQUIRED_EMPTY", f"{path}.old_demand_set")
    demand_ids = {item["id"] for item in old_demands}
    mappings: List[Dict[str, Any]] = []
    mapped_ids: set[str] = set()
    for index, raw in enumerate(
        require_list(fit.get("new_supply_mapping"), f"{path}.new_supply_mapping", nonempty=False)
    ):
        item_path = f"{path}.new_supply_mapping[{index}]"
        item = require_dict(raw, item_path)
        if set(item) != {"demand_id", "supply_ids", "evidence_refs"}:
            raise ConstructionHold("HOLD_SUPPLY_MAPPING_SHAPE", item_path)
        demand_id = require_str(item.get("demand_id"), f"{item_path}.demand_id", max_bytes=128)
        if demand_id not in demand_ids or demand_id in mapped_ids:
            raise ConstructionHold("HOLD_SUPPLY_MAPPING_DEMAND", f"{item_path}.demand_id")
        mapped_ids.add(demand_id)
        mappings.append(
            {
                "demand_id": demand_id,
                "supply_ids": require_unique_str_list(
                    item.get("supply_ids"), f"{item_path}.supply_ids"
                ),
                "evidence_refs": evidence_refs(
                    item.get("evidence_refs"), f"{item_path}.evidence_refs"
                ),
            }
        )
    gaps = {
        name: _validate_evidenced_items(fit.get(name), f"{path}.{name}")
        for name in SUPPLY_GAP_FIELDS
    }
    uncovered_ids = {item["id"] for item in gaps["uncovered_demands"]}
    if not uncovered_ids.issubset(demand_ids) or mapped_ids | uncovered_ids != demand_ids:
        raise ConstructionHold("HOLD_SUPPLY_DEMAND_COVERAGE", path)
    if mapped_ids & uncovered_ids:
        raise ConstructionHold("HOLD_SUPPLY_DEMAND_COVERAGE", path)
    recovery: List[Dict[str, Any]] = []
    raw_recovery = require_list(fit.get("recovery_route"), f"{path}.recovery_route")
    if len(raw_recovery) != len(RECOVERY_STEPS):
        raise ConstructionHold("HOLD_RECOVERY_ROUTE", f"{path}.recovery_route")
    for index, step_name in enumerate(RECOVERY_STEPS):
        item_path = f"{path}.recovery_route[{index}]"
        item = require_dict(raw_recovery[index], item_path)
        if set(item) != {"step", "evidence_refs", "rollback"} or item.get("step") != step_name:
            raise ConstructionHold("HOLD_RECOVERY_ROUTE", item_path)
        rollback = require_dict(item.get("rollback"), f"{item_path}.rollback")
        if set(rollback) != {"action", "evidence_refs"}:
            raise ConstructionHold("HOLD_RECOVERY_ROUTE", f"{item_path}.rollback")
        recovery.append(
            {
                "step": step_name,
                "evidence_refs": evidence_refs(
                    item.get("evidence_refs"), f"{item_path}.evidence_refs"
                ),
                "rollback": {
                    "action": require_str(
                        rollback.get("action"), f"{item_path}.rollback.action", max_bytes=256
                    ),
                    "evidence_refs": evidence_refs(
                        rollback.get("evidence_refs"),
                        f"{item_path}.rollback.evidence_refs",
                    ),
                },
            }
        )
    return {
        "old_demand_set": old_demands,
        "new_supply_mapping": mappings,
        **gaps,
        "recovery_route": recovery,
    }


def validate_relational_contract(
    mainline_value: Any,
    distance_value: Any,
    supply_value: Any,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    mainline = _validate_mainline_relation(mainline_value)
    distance = _validate_continuation_distance(distance_value)
    supply = _validate_supply_demand_fit(supply_value)
    relation = mainline["candidate_relation"]
    missing = set(mainline["missing_gates"])
    required_missing = {
        f"continuation_distance.{axis}"
        for axis, item in distance.items()
        if item["state"] == "UNKNOWN"
    }
    required_missing.update(
        f"mainline_relation.hard_gates.{name}"
        for name, item in mainline["hard_gates"].items()
        if item["state"] != "PASS"
    )
    required_missing.update(
        f"supply_demand_fit.{name}"
        for name in SUPPLY_GAP_FIELDS
        if supply[name]
    )
    if not required_missing.issubset(missing):
        raise ConstructionHold("HOLD_RELATION_MISSING_GATE_BINDING", "$.mainline_relation.missing_gates")
    if required_missing and relation not in {"PARALLEL_SHADOW", "HOLD"}:
        raise ConstructionHold("HOLD_SUPPLY_DEMAND_RELATION_CONFLICT", "$.mainline_relation")
    if any(item["state"] == "UNKNOWN" for item in distance.values()) and relation != "HOLD":
        raise ConstructionHold("HOLD_RELATION_UNKNOWN_REQUIRES_HOLD", "$.mainline_relation")
    if relation != "HOLD" and any(
        item["state"] != "PASS" for item in mainline["hard_gates"].values()
    ):
        raise ConstructionHold("HOLD_RELATION_HARD_GATE_CONFLICT", "$.mainline_relation")
    if relation == "HOLD" and not mainline["missing_gates"]:
        raise ConstructionHold("HOLD_RELATION_REQUIRES_BREAKPOINT", "$.mainline_relation")
    return mainline, distance, supply


def validate_trade_secret_boundary(value: Any) -> Dict[str, bool]:
    boundary = require_dict(value, "$.trade_secret_boundary")
    if boundary != TRADE_SECRET_BOUNDARY:
        raise ConstructionHold("HOLD_TRADE_SECRET_BOUNDARY", "$.trade_secret_boundary")
    return dict(TRADE_SECRET_BOUNDARY)


def validate_governance(value: Any) -> Dict[str, Any]:
    governance = require_dict(value, "$.governance")
    if governance.get("lifecycle") != "CANDIDATE":
        raise ConstructionHold("HOLD_GOVERNANCE_LIFECYCLE", "$.governance.lifecycle")
    if governance.get("activation") != "NOT_AUTHORIZED":
        raise ConstructionHold("HOLD_ACTIVATION_AUTHORITY", "$.governance.activation")
    if require_bool(governance.get("packet_is_authorization"), "$.governance.packet_is_authorization"):
        raise ConstructionHold("HOLD_PACKET_CANNOT_AUTHORIZE", "$.governance.packet_is_authorization")
    if governance.get("ai_completion_grants_authority") is not False:
        raise ConstructionHold("HOLD_AI_CANNOT_GRANT_AUTHORITY", "$.governance.ai_completion_grants_authority")
    return {
        "lifecycle": "CANDIDATE",
        "activation": "NOT_AUTHORIZED",
        "packet_is_authorization": False,
        "ai_completion_grants_authority": False,
        "total_field_authority_ref": governance.get("total_field_authority_ref"),
        "authority_receipt_ref": governance.get("authority_receipt_ref"),
    }


def build_packet(spec: Any) -> Dict[str, Any]:
    root = require_dict(spec, "$")
    scan_sensitive(root)
    user_explicit, user_ids = validate_statement_items(
        root.get("user_explicit"), "$.user_explicit", USER_EXPLICIT
    )
    hypotheses, _ = validate_statement_items(
        root.get("ai_completion_hypotheses"), "$.ai_completion_hypotheses", AI_HYPOTHESIS
    )
    eight_d = validate_eight_d(root.get("eight_d"))
    adi_map = validate_adi_map(root.get("adi_map"))
    pattern_recall = validate_patterns(root.get("pattern_recall"))
    transfer = validate_transfer(root.get("transfer"))
    runtime_chain = validate_runtime_completion_chain(root.get("runtime_completion_chain"))
    validate_fallback_usage(runtime_chain, fallback_classes_used(adi_map, pattern_recall))
    validate_dynamic_depth_escalation(eight_d["dynamic_depth"], adi_map, pattern_recall, transfer)
    mainline_relation, continuation_distance, supply_demand_fit = validate_relational_contract(
        root.get("mainline_relation"),
        root.get("continuation_distance"),
        root.get("supply_demand_fit"),
    )
    packet = {
        "protocol": PROTOCOL,
        "protocol_version": PROTOCOL_VERSION,
        "states": [
            "CANDIDATE",
            "USER_JOURNEY_UNVERIFIED",
            "CROSS_NODE_UNVERIFIED",
            "ACTIVATION_NOT_AUTHORIZED",
        ],
        "intent_id": require_str(root.get("intent_id"), "$.intent_id", max_bytes=128),
        "logical_root_id": require_str(root.get("logical_root_id"), "$.logical_root_id", max_bytes=128),
        "node_id": require_str(root.get("node_id"), "$.node_id", max_bytes=128),
        "revision": require_str(root.get("revision"), "$.revision", max_bytes=256),
        "intent": {
            "user_explicit": user_explicit,
            "ai_completion_hypotheses": hypotheses,
            "allowed_effects": validate_allowed_effects(root.get("allowed_effects"), user_ids),
        },
        "perspectives": validate_perspectives(root.get("perspectives")),
        "eight_d": eight_d,
        "adi_map": adi_map,
        "pattern_recall": pattern_recall,
        "architecture": validate_architecture(root.get("architecture")),
        "code_reconstruction": validate_code_reconstruction(root.get("code_reconstruction")),
        "closure": validate_closure(root.get("closure")),
        "runtime_completion_chain": runtime_chain,
        "user_journeys": validate_journeys(root.get("user_journeys")),
        "redteam": validate_redteam(root.get("redteam")),
        "core_functions": validate_core_functions(root.get("core_functions")),
        "mainline_relation": mainline_relation,
        "continuation_distance": continuation_distance,
        "supply_demand_fit": supply_demand_fit,
        "relational_evidence": _validate_relational_evidence_binding(
            root.get("relational_evidence")
        ),
        "trade_secret_boundary": validate_trade_secret_boundary(root.get("trade_secret_boundary")),
        "transfer": transfer,
        "governance": validate_governance(root.get("governance")),
        "safety": {
            "secret_included": False,
            "member_plaintext_included": False,
            "full_source_embedded": False,
        },
    }
    return packet


def validate_output_dir(output_dir: Path) -> Path:
    if output_dir.is_symlink():
        raise ConstructionHold("HOLD_OUTPUT_SYMLINK", "$.output_dir")
    if output_dir.exists():
        raise ConstructionHold("HOLD_OUTPUT_EXISTS", "$.output_dir")
    parent = output_dir.parent.resolve()
    if not parent.exists() or not parent.is_dir() or parent.is_symlink():
        raise ConstructionHold("HOLD_OUTPUT_PARENT", "$.output_dir")
    return parent / output_dir.name


def write_artifacts(packet: Mapping[str, Any], output_dir: Path) -> Dict[str, Any]:
    raise ConstructionHold("HOLD_LEGACY_WRITER_DISABLED", "$.write_artifacts")


def load_spec(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise ConstructionHold("HOLD_INPUT_PATH", "$.input")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ConstructionHold("HOLD_INPUT_SIZE_LIMIT", "$.input")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ConstructionHold("HOLD_INPUT_JSON", "$.input") from None


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.validate_only and args.output_dir is None:
        parser.error("--output-dir is required unless --validate-only is used")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    parse_args(argv)
    error = ConstructionHold("HOLD_LEGACY_CLI_DISABLED", "$.intent_field_construct.py")
    print(json.dumps(error.report(), ensure_ascii=False, sort_keys=True))
    return 2


if __name__ == "__main__":
    sys.exit(main())
