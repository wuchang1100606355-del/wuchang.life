#!/usr/bin/env python3
"""Build an in-memory intent-field candidate; never emit a PASS verdict."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

import intent_field_construct as structural


Hold = structural.ConstructionHold

PROVENANCE_CLASSES = {
    "USER_EXPLICIT",
    "AI_COMPLETION_HYPOTHESIS",
    "FIELD_EVIDENCE",
    "EXTERNAL_PRIMARY_SOURCE",
    "MODEL_PRIOR_CANDIDATE",
    "AUTHORITY_DECISION_REQUIRED",
}

PERSONAS = {
    "REAL_HUMAN_USER",
    "SILICON_VALLEY_DIGITAL_STARTUP_DIRECTOR_PRODUCT_OWNER",
}

PRODUCT_MATRIX = {
    "user_problem",
    "value",
    "roles",
    "demand",
    "supply",
    "cost",
    "operations",
    "risk",
    "success_metric",
    "exit_rollback",
}

PLACEHOLDER_WORDS = {
    "placeholder",
    "placeholder-only",
    "not-set",
    "unset",
    "example",
    "dummy",
    "redacted",
}

SOURCE_CONTENT_KEYS = {
    "content",
    "source_text",
    "source_bytes",
    "base64",
    "blob",
    "inline_source",
    "full_source",
}

PRIVATE_CONTENT_KEYS = {
    "private_lookup",
    "private_lookup_table",
    "private_lookup_tables",
    "h64_private_lookup",
    "adi_private_lookup",
    "phase_mapping",
    "why_it_runs",
    "internal_reasoning",
    "chain_of_thought",
    "cot",
    "private_weights",
}

WEIGHT_COLLECTION_KEYS = {
    "weights",
    "weight_table",
    "weight_tables",
    "model_weights",
    "private_weights",
}

SENSITIVE_KEYS = {
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

RAW_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bBearer\s+\S+", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\b09\d{8}\b"),
    re.compile(r"\b[A-Z][12]\d{8}\b"),
)


def _safe_placeholder(value: Any) -> bool:
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


def _looks_like_source_blob(value: str) -> bool:
    encoded = value.encode("utf-8")
    if len(encoded) > 64 * 1024:
        return True
    lines = value.count("\n") + 1
    code_markers = sum(
        marker in value
        for marker in ("def ", "class ", "function ", "import ", "#!/", "<script", "BEGIN ")
    )
    if len(encoded) > 4096 and lines > 40 and code_markers:
        return True
    compact = re.sub(r"\s+", "", value)
    return len(compact) > 4096 and re.fullmatch(r"[A-Za-z0-9+/=_-]+", compact) is not None


def _looks_structured_or_technical(value: str) -> bool:
    if _safe_placeholder(value):
        return False
    if len(value.encode("utf-8")) > 512:
        return True
    markers = ("def ", "class ", "function ", "import ", "SELECT ", "INSERT ", "BEGIN ", "{", "}", "[", "]")
    return value.count("\n") > 2 or any(marker in value for marker in markers)


def _substantive_private_payload(value: Any) -> bool:
    if _safe_placeholder(value):
        return False
    if isinstance(value, (dict, list)):
        return bool(value)
    if isinstance(value, str):
        return bool(value.strip()) and (_looks_structured_or_technical(value) or len(value.strip()) > 64)
    return False


def _explicit_private_content_type(value: Any) -> bool:
    if not isinstance(value, str) or _safe_placeholder(value):
        return False
    normalized = value.strip().lower().replace("-", "_")
    if not normalized.startswith("private"):
        return False
    return any(
        token in normalized
        for token in ("lookup", "h64", "adi", "weight", "phase", "reasoning", "chain_of_thought")
    )


def _private_content_key(normalized: str) -> bool:
    if normalized in PRIVATE_CONTENT_KEYS:
        return True
    return (
        "private" in normalized
        and "lookup" in normalized
        and ("h64" in normalized or "adi" in normalized or "table" in normalized)
    )


def sanitize_for_structure(value: Any, path: str = "$", source_zone: bool = False) -> Any:
    """Reject substantive sensitive/source content and remove safe placeholder extras."""
    if isinstance(value, dict):
        result: Dict[str, Any] = {}
        for key, child in value.items():
            key_text = str(key)
            normalized = key_text.lower().replace("-", "_")
            child_path = f"{path}.{key_text}"
            if normalized in SENSITIVE_KEYS:
                if _safe_placeholder(child):
                    continue
                raise Hold("HOLD_SUBSTANTIVE_SENSITIVE_FIELD", child_path)
            if source_zone and normalized in SOURCE_CONTENT_KEYS:
                if _safe_placeholder(child):
                    continue
                raise Hold("HOLD_FULL_SOURCE_EMBEDDED", child_path)
            if normalized in {"content_type", "type"} and _explicit_private_content_type(child):
                raise Hold("HOLD_SUBSTANTIVE_PRIVATE_CONTENT_TYPE", child_path)
            if (
                _private_content_key(normalized)
                or (normalized in WEIGHT_COLLECTION_KEYS and isinstance(child, (dict, list)))
            ) and _substantive_private_payload(child):
                raise Hold("HOLD_SUBSTANTIVE_PRIVATE_CONTENT", child_path)
            next_source_zone = source_zone or normalized in {
                "code_reconstruction",
                "transfer",
                "recipe",
                "recipes",
            }
            result[key_text] = sanitize_for_structure(child, child_path, next_source_zone)
        return result
    if isinstance(value, list):
        return [
            sanitize_for_structure(child, f"{path}[{index}]", source_zone)
            for index, child in enumerate(value)
        ]
    if isinstance(value, str):
        if not _safe_placeholder(value):
            for pattern in RAW_PATTERNS:
                if pattern.search(value):
                    raise Hold("HOLD_SUBSTANTIVE_SENSITIVE_VALUE", path)
        if source_zone and _looks_like_source_blob(value):
            raise Hold("HOLD_FULL_SOURCE_BY_CONTENT_TYPE", path)
    return value


def _refs(value: Any, path: str) -> list[str]:
    return structural.evidence_refs(value, path)


def _validate_provenance(spec: Mapping[str, Any]) -> list[Dict[str, Any]]:
    raw = structural.require_list(spec.get("provenance_catalog"), "$.provenance_catalog")
    result: list[Dict[str, Any]] = []
    seen: set[str] = set()
    for index, item_raw in enumerate(raw):
        path = f"$.provenance_catalog[{index}]"
        item = structural.require_dict(item_raw, path)
        source_class = structural.require_str(item.get("class"), f"{path}.class", max_bytes=96)
        if source_class not in PROVENANCE_CLASSES or source_class in seen:
            raise Hold("HOLD_PROVENANCE_CLASS", f"{path}.class")
        seen.add(source_class)
        if item.get("grants_authority") is not False:
            raise Hold("HOLD_PROVENANCE_CANNOT_AUTHORIZE", path)
        result.append(
            {
                "class": source_class,
                "ref": structural.require_str(item.get("ref"), f"{path}.ref", max_bytes=512),
                "sha256": structural.require_sha256(item.get("sha256"), f"{path}.sha256"),
                "grants_authority": False,
            }
        )
    if seen != PROVENANCE_CLASSES:
        raise Hold("HOLD_PROVENANCE_SET_INCOMPLETE", "$.provenance_catalog")
    return sorted(result, key=lambda item: item["class"])


def _validate_personas(spec: Mapping[str, Any]) -> Dict[str, Any]:
    raw = structural.require_dict(spec.get("product_personas"), "$.product_personas")
    if set(raw) != PERSONAS:
        raise Hold("HOLD_PRODUCT_PERSONAS", "$.product_personas")
    result: Dict[str, Any] = {}
    for name in sorted(PERSONAS):
        path = f"$.product_personas.{name}"
        item = structural.require_dict(raw[name], path)
        if item.get("status") != "PASS":
            raise Hold("HOLD_PRODUCT_PERSONA_GATE", path)
        result[name] = {
            "claimed_status": "PASS",
            "structural_status": "STRUCTURAL_ONLY",
            "verification_state": "UNVERIFIED",
            "evidence_refs": _refs(item.get("evidence_refs"), f"{path}.evidence_refs"),
        }
    return result


def _validate_product_matrix(spec: Mapping[str, Any]) -> Dict[str, Any]:
    raw = structural.require_dict(spec.get("product_matrix"), "$.product_matrix")
    if not PRODUCT_MATRIX.issubset(raw):
        raise Hold("HOLD_PRODUCT_MATRIX_INCOMPLETE", "$.product_matrix")
    result: Dict[str, Any] = {}
    for name in sorted(PRODUCT_MATRIX):
        path = f"$.product_matrix.{name}"
        item = structural.require_dict(raw[name], path)
        if item.get("status") != "PASS":
            raise Hold("HOLD_PRODUCT_MATRIX_GATE", path)
        result[name] = {
            "claimed_status": "PASS",
            "structural_status": "STRUCTURAL_ONLY",
            "verification_state": "UNVERIFIED",
            "evidence_refs": _refs(item.get("evidence_refs"), f"{path}.evidence_refs"),
        }
    return result


def _validate_effect_chains(spec: Mapping[str, Any]) -> None:
    users = {
        item["id"]: {
            "statement_sha256": structural.sha256_text(item["statement"]),
            "source_ref": item["source"]["ref"],
        }
        for item in structural.require_list(spec.get("user_explicit"), "$.user_explicit")
    }
    for index, effect_raw in enumerate(structural.require_list(spec.get("allowed_effects"), "$.allowed_effects", nonempty=False)):
        path = f"$.allowed_effects[{index}]"
        effect = structural.require_dict(effect_raw, path)
        chain = structural.require_list(effect.get("immutable_source_chain"), f"{path}.immutable_source_chain")
        chain_ids: set[str] = set()
        for chain_index, link_raw in enumerate(chain):
            link_path = f"{path}.immutable_source_chain[{chain_index}]"
            link = structural.require_dict(link_raw, link_path)
            source_id = structural.require_str(link.get("id"), f"{link_path}.id", max_bytes=128)
            if source_id not in users:
                raise Hold("HOLD_EFFECT_CHAIN_SOURCE", link_path)
            expected = users[source_id]
            if structural.require_sha256(link.get("statement_sha256"), f"{link_path}.statement_sha256") != expected["statement_sha256"]:
                raise Hold("HOLD_EFFECT_CHAIN_HASH", link_path)
            if structural.require_str(link.get("source_ref"), f"{link_path}.source_ref", max_bytes=512) != expected["source_ref"]:
                raise Hold("HOLD_EFFECT_CHAIN_REF", link_path)
            chain_ids.add(source_id)
        if chain_ids != set(effect.get("source_fragment_ids", [])):
            raise Hold("HOLD_EFFECT_CHAIN_INCOMPLETE", path)


def _mark_structural_only(item: Dict[str, Any]) -> None:
    item["structural_status"] = "STRUCTURAL_ONLY"
    item["verification_state"] = "UNVERIFIED"


def _claim_status_structural_only(item: Dict[str, Any]) -> None:
    if "status" in item:
        item["claimed_status"] = item.pop("status")
    _mark_structural_only(item)


def _mark_candidate_self_reports(packet: Dict[str, Any]) -> None:
    packet["eight_d"]["dynamic_depth"]["structural_status"] = "STRUCTURAL_ONLY"
    packet["eight_d"]["dynamic_depth"]["verification_state"] = "UNVERIFIED"
    for item in packet["eight_d"]["dimensions"].values():
        item.pop("status", None)
        _mark_structural_only(item)

    _claim_status_structural_only(packet["architecture"])
    for item in packet["architecture"]["constraints"]:
        _claim_status_structural_only(item)

    _claim_status_structural_only(packet["code_reconstruction"])

    for item in packet["closure"]["stages"].values():
        _claim_status_structural_only(item)

    for item in packet["runtime_completion_chain"]["ordered_stages"]:
        item["verification_state"] = "UNVERIFIED"
        item["evidence_class"] = "STRUCTURAL_ONLY"

    for item in packet["core_functions"].values():
        _mark_structural_only(item)

    transfer = packet["transfer"]
    transfer["invariant"] = {
        "value": transfer["invariant"],
        "structural_status": "STRUCTURAL_ONLY",
        "verification_state": "UNVERIFIED",
    }
    for item in transfer["tests"]:
        item["claimed_status"] = item.pop("status")
        _mark_structural_only(item)

    packet["trade_secret_boundary"] = {
        "value": packet["trade_secret_boundary"],
        "structural_status": "STRUCTURAL_ONLY",
        "verification_state": "UNVERIFIED",
    }


def producer_code_sha256() -> str:
    files = [Path(structural.__file__).resolve(), Path(__file__).resolve()]
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_candidate(spec: Any) -> Dict[str, Any]:
    cleaned = sanitize_for_structure(copy.deepcopy(spec))
    root = structural.require_dict(cleaned, "$")
    _validate_effect_chains(root)
    packet = structural.build_packet(root)
    if set(root.get("redteam", {}).get("stages", {})) != set(structural.REDTEAM_CHECKS):
        raise Hold("HOLD_REDTEAM_STAGE_SET", "$.redteam.stages")
    packet["states"] = [
        "CANDIDATE",
        "RUNTIME_EVIDENCE_UNVERIFIED",
        "USER_JOURNEY_EVIDENCE_UNVERIFIED",
        "CROSS_NODE_REPLAY_UNVERIFIED",
        "AUTHENTICITY_UNVERIFIED",
        "ACTIVATION_NOT_AUTHORIZED",
    ]
    for journey in packet["user_journeys"]:
        journey["claimed_status"] = journey.get("claimed_status", journey.pop("status", "PASS"))
        journey["verification_state"] = "UNVERIFIED"
    for stage in packet["redteam"]["stages"].values():
        for round_item in stage["rounds"]:
            round_item["claimed_result"] = round_item.pop("result")
        stage["verification_state"] = "UNVERIFIED"
    cross_node = packet["transfer"]["cross_node"]
    for key in ("pollution_guard", "drift_guard", "tamper_guard", "rollback_guard"):
        cross_node[f"claimed_{key}"] = cross_node.pop(key)
    cross_node["verification_state"] = "UNVERIFIED"
    _mark_candidate_self_reports(packet)
    packet["product_personas"] = _validate_personas(root)
    packet["product_matrix"] = _validate_product_matrix(root)
    packet["provenance_catalog"] = _validate_provenance(root)
    effect_policy = structural.require_dict(root.get("effect_policy"), "$.effect_policy")
    if effect_policy != {
        "scope": "NEW_RUN_DIRECTORY_CANDIDATE_FILES_ONLY",
        "no_existing_file_overwrite": True,
        "no_external_side_effects": True,
    }:
        raise Hold("HOLD_EFFECT_POLICY", "$.effect_policy")
    packet["effect_policy"] = effect_policy
    packet["producer"] = {
        "verdict": "UNVERIFIED",
        "code_sha256": producer_code_sha256(),
        "input_spec_sha256": structural.sha256_bytes(structural.canonical_bytes(cleaned)),
        "input_revision": packet["revision"],
        "relational_contract_sha256": structural.sha256_bytes(
            structural.canonical_bytes(
                {
                    "mainline_relation": packet["mainline_relation"],
                    "continuation_distance": packet["continuation_distance"],
                    "supply_demand_fit": packet["supply_demand_fit"],
                    "relational_evidence": packet["relational_evidence"],
                }
            )
        ),
    }
    packet["governance"]["activation"] = "NOT_AUTHORIZED"
    packet["verifier_result"] = "NOT_RUN"
    return packet


def candidate_sha256(spec: Any) -> str:
    return structural.sha256_bytes(structural.canonical_bytes(build_candidate(spec)))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        spec = json.loads(args.input.read_text(encoding="utf-8"))
        candidate = build_candidate(spec)
        print(
            json.dumps(
                {
                    "states": candidate["states"],
                    "candidate_sha256": structural.sha256_bytes(structural.canonical_bytes(candidate)),
                    "producer_code_sha256": candidate["producer"]["code_sha256"],
                    "artifacts_written": False,
                    "verifier_result": "NOT_RUN",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except Hold as error:
        print(json.dumps(error.report(), ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
