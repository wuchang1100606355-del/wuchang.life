"""Fail-closed binding for the observed W7TP 8D ADI V2.3 candidate source.

This module deliberately does not promote the source to canonical or D8 authority.
It gives isolated consumers one deterministic preflight contract while the active
V2.1 authority remains unchanged.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_ID = "W7TP_8D_ADI_V2_3"
CANDIDATE_VERSION = "2.3"
CONTRACT_SCHEMA_VERSION = "W7TP-V2.3-CANDIDATE-SOURCE-CONTRACT/1.0"
CONTRACT_REF = (
    "manifests/total_field/w7tp_8d_adi_v2_3_candidate_source/CONTRACT.json"
)
CONTRACT_PATH = ROOT / CONTRACT_REF
PRIMARY_DOCUMENT_ID = "1Zk__7MMBvGxnnHNObeEjTev3SwKWB9rkCERw9tXnw84"
PRIMARY_REVISION_ID = (
    "ANLCKQngZKaKNPqTJtoWJgOGEZDmDiIu_XcrBq24Ibuho1v7G0ZS3J7DFZaqOsi76DB_"
    "EhL_0V1LG2DZZyllQidUFAHBEco1ZvRhBWID38A"
)
PRIMARY_NORMALIZED_TEXT_SHA256 = (
    "dfd9147a5d053764025f318cd49213cdb3ce9df6fa017ec0ad62ad08821f9597"
)
HISTORICAL_DOCUMENT_ID = "17uXPMEgfmQvjalou0_ik9LnKLB2NcgRuPCbqJa7g_FI"
HISTORICAL_REVISION_ID = (
    "ANLCKQkeOvl0OwwRO-MhommJ8y-HdY7DsJab2ySM5pOJoE8azr5wwBBrMxCsEa67Qdio"
    "OHUJo0WtXfYCO6r1CGy-Q72f0-BtN8hQ4gsZ_2k"
)
HISTORICAL_NORMALIZED_TEXT_SHA256 = (
    "426dc6a13ee63f61a6e9608dc812089fa7c4ec4dda21ccffe1cf030e7e8b23c7"
)
FORMAL_BASELINE_SHA256 = (
    "383aba5b7a9f5d0e948d9b43b83e7dd6b6ec9c27f025fb9069e83810f0ae870d"
)
REQUIRED_INVARIANTS = frozenset(
    {
        "D1_D8_INTERACTIVE_SINGLE_TASK_STATE_FIELD",
        "VALID_D8_NE_CANONICAL",
        "TEST_PASS_NE_CANONICAL",
        "CANDIDATE_CANNOT_SELF_PROMOTE",
        "F_DOMAIN_NON_AUTHORITATIVE",
        "EXACT_NE_GENERATIVE_RECONSTRUCTION",
        "RECONSTRUCTION_NE_REPAIR",
        "CAUSAL_ADMISSIBILITY_NE_COMMIT_AUTHORIZATION",
        "DEPENDENCY_HASH_AND_FRESHNESS_REQUIRED",
    }
)
FORBIDDEN_EFFECT_KEYS = frozenset(
    {
        "canonical_write",
        "pointer_change",
        "d8_issue",
        "deploy",
        "restart",
        "network_change",
        "credential_access",
        "ledger_consume",
        "git_commit",
        "git_push",
        "external_effect",
    }
)


class CandidateSourceError(ValueError):
    """One deterministic candidate-source preflight failure."""

    def __init__(self, reason_code: str, path: str = "$") -> None:
        super().__init__(f"{reason_code}:{path}")
        self.reason_code = reason_code
        self.path = path


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CandidateSourceError("HOLD_V23_CANDIDATE_DUPLICATE_KEY", key)
        result[key] = value
    return result


def _require_exact_keys(value: Any, expected: set[str], path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise CandidateSourceError("HOLD_V23_CANDIDATE_CONTRACT_SHAPE", path)
    return value


def _validate_source(
    source: Any,
    *,
    path: str,
    document_id: str,
    revision_id: str,
    title: str,
    modified_at: str,
    paragraphs: int,
    normalized_utf8_bytes: int,
    normalized_text_sha256: str,
    role: str,
) -> None:
    candidate = _require_exact_keys(
        source,
        {
            "kind",
            "role",
            "document_id",
            "document_url",
            "revision_id",
            "title",
            "modified_at",
            "paragraph_count",
            "normalization",
            "normalized_utf8_bytes",
            "normalized_paragraph_text_sha256",
        },
        path,
    )
    expected = {
        "kind": "GOOGLE_DOC_NATIVE_READ_ONLY_OBSERVATION",
        "role": role,
        "document_id": document_id,
        "document_url": f"https://docs.google.com/document/d/{document_id}",
        "revision_id": revision_id,
        "title": title,
        "modified_at": modified_at,
        "paragraph_count": paragraphs,
        "normalization": "UTF8_JOIN_PARAGRAPH_TEXT_WITH_LF/1.0",
        "normalized_utf8_bytes": normalized_utf8_bytes,
        "normalized_paragraph_text_sha256": normalized_text_sha256,
    }
    if dict(candidate) != expected:
        raise CandidateSourceError("HOLD_V23_CANDIDATE_SOURCE_DRIFT", path)


def validate_candidate_source_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Validate an observed candidate source without granting any authority."""

    candidate = _require_exact_keys(
        contract,
        {
            "schema_version",
            "contract_id",
            "version",
            "state",
            "source_observation",
            "authority_boundary",
            "formal_authority_baseline",
            "invariants",
            "consumer_preflight",
            "forbidden_effects",
            "contract_self_sha256",
        },
        "$",
    )
    if (
        candidate["schema_version"] != CONTRACT_SCHEMA_VERSION
        or candidate["contract_id"] != CANDIDATE_ID
        or candidate["version"] != CANDIDATE_VERSION
        or candidate["state"] != "CANDIDATE_FORMALIZATION_V0.1"
    ):
        raise CandidateSourceError("HOLD_V23_CANDIDATE_IDENTITY_DRIFT")

    sources = _require_exact_keys(
        candidate["source_observation"], {"primary", "historical"}, "$.source_observation"
    )
    _validate_source(
        sources["primary"],
        path="$.source_observation.primary",
        document_id=PRIMARY_DOCUMENT_ID,
        revision_id=PRIMARY_REVISION_ID,
        title="W7TP 8D ADI V2.3 Typed Formal Specification v0.1",
        modified_at="2026-08-28T06:24:17.373Z",
        paragraphs=126,
        normalized_utf8_bytes=17080,
        normalized_text_sha256=PRIMARY_NORMALIZED_TEXT_SHA256,
        role="CURRENT_CANDIDATE_TYPED_FORMAL_SPEC",
    )
    _validate_source(
        sources["historical"],
        path="$.source_observation.historical",
        document_id=HISTORICAL_DOCUMENT_ID,
        revision_id=HISTORICAL_REVISION_ID,
        title="W7TP 8D ADI Formal Specification V2.3",
        modified_at="2026-08-28T06:14:40.604Z",
        paragraphs=44,
        normalized_utf8_bytes=8625,
        normalized_text_sha256=HISTORICAL_NORMALIZED_TEXT_SHA256,
        role="EARLIER_CANONICAL_DRAFT_HISTORICAL_ONLY",
    )

    authority = _require_exact_keys(
        candidate["authority_boundary"],
        {
            "candidate_only",
            "canonical",
            "d8_authorized",
            "implemented",
            "runtime_protected",
            "self_promotion_allowed",
        },
        "$.authority_boundary",
    )
    if dict(authority) != {
        "candidate_only": True,
        "canonical": False,
        "d8_authorized": False,
        "implemented": "UNKNOWN",
        "runtime_protected": "NOT_PROVEN",
        "self_promotion_allowed": False,
    }:
        raise CandidateSourceError("HOLD_V23_CANDIDATE_AUTHORITY_DRIFT")

    baseline = _require_exact_keys(
        candidate["formal_authority_baseline"],
        {"canonical_id", "version", "document_ref", "document_sha256", "unchanged"},
        "$.formal_authority_baseline",
    )
    if dict(baseline) != {
        "canonical_id": "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1",
        "version": "2.1",
        "document_ref": (
            "docs/total_field/"
            "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1_"
            "FOUNDER_LOCKED_SUCCESSOR_20260728.md"
        ),
        "document_sha256": FORMAL_BASELINE_SHA256,
        "unchanged": True,
    }:
        raise CandidateSourceError("HOLD_V23_FORMAL_BASELINE_DRIFT")

    invariants = candidate["invariants"]
    if (
        not isinstance(invariants, list)
        or len(invariants) != len(set(invariants))
        or set(invariants) != REQUIRED_INVARIANTS
    ):
        raise CandidateSourceError("HOLD_V23_CANDIDATE_INVARIANTS_DRIFT")

    preflight = _require_exact_keys(
        candidate["consumer_preflight"],
        {
            "required",
            "mode",
            "allowed_output",
            "dependency_hashes_required",
            "freshness_required_for_formal_reuse",
        },
        "$.consumer_preflight",
    )
    if dict(preflight) != {
        "required": True,
        "mode": "CANDIDATE_PREFLIGHT_ONLY",
        "allowed_output": "CANDIDATE_EVIDENCE_ONLY",
        "dependency_hashes_required": True,
        "freshness_required_for_formal_reuse": True,
    }:
        raise CandidateSourceError("HOLD_V23_CANDIDATE_PREFLIGHT_DRIFT")

    effects = _require_exact_keys(
        candidate["forbidden_effects"], set(FORBIDDEN_EFFECT_KEYS), "$.forbidden_effects"
    )
    if any(value is not False for value in effects.values()):
        raise CandidateSourceError("HOLD_V23_CANDIDATE_FORBIDDEN_EFFECT")

    unsigned = dict(candidate)
    supplied_self_hash = unsigned.pop("contract_self_sha256")
    if supplied_self_hash != _canonical_sha256(unsigned):
        raise CandidateSourceError("HOLD_V23_CANDIDATE_SELF_HASH_MISMATCH")

    return {
        "state": "PASS_CANDIDATE_SOURCE_PREFLIGHT",
        "candidate_id": CANDIDATE_ID,
        "version": CANDIDATE_VERSION,
        "candidate_only": True,
        "canonical": False,
        "d8_authorized": False,
        "contract_self_sha256": supplied_self_hash,
        "source_revision_id": PRIMARY_REVISION_ID,
        "source_content_sha256": PRIMARY_NORMALIZED_TEXT_SHA256,
        "formal_authority_unchanged": True,
    }


def load_candidate_source_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except CandidateSourceError:
        raise
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise CandidateSourceError("HOLD_V23_CANDIDATE_CONTRACT_UNAVAILABLE", str(path)) from exc
    if not isinstance(value, dict):
        raise CandidateSourceError("HOLD_V23_CANDIDATE_CONTRACT_SHAPE")
    validate_candidate_source_contract(value)
    return value


def candidate_source_binding(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract = load_candidate_source_contract(path)
    validation = validate_candidate_source_contract(contract)
    return {
        "candidate_id": CANDIDATE_ID,
        "version": CANDIDATE_VERSION,
        "state": contract["state"],
        "candidate_only": True,
        "canonical": False,
        "d8_authorized": False,
        "contract_ref": CONTRACT_REF,
        "contract_file_sha256": _file_sha256(path),
        "contract_self_sha256": validation["contract_self_sha256"],
        "source_document_id": PRIMARY_DOCUMENT_ID,
        "source_revision_id": PRIMARY_REVISION_ID,
        "source_content_sha256": PRIMARY_NORMALIZED_TEXT_SHA256,
        "formal_authority_baseline": contract["formal_authority_baseline"],
        "allowed_output": "CANDIDATE_EVIDENCE_ONLY",
        "external_effect": False,
    }


ACTIVE_POINTER_REF = "runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json"
ACTIVE_POINTER_PATH = ROOT / ACTIVE_POINTER_REF
V23_CANONICAL_CONTRACT_REF = (
    "manifests/total_field/w7tp_8d_adi_v2_3_canonical/CONTRACT.json"
)
V23_CANONICAL_SCHEMA_REF = (
    "schemas/field/w7tp_8d_adi_v2_3_canonical_contract_v1.schema.json"
)


def _load_strict_json(path: Path, unavailable_code: str) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except CandidateSourceError:
        raise
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise CandidateSourceError(unavailable_code, str(path)) from exc
    if not isinstance(value, dict):
        raise CandidateSourceError(unavailable_code, str(path))
    return value


def active_canonical_binding(
    pointer_path: Path = ACTIVE_POINTER_PATH,
) -> dict[str, Any]:
    """Resolve the currently active W7TP authority through the tracked pointer."""

    pointer = _load_strict_json(
        pointer_path,
        "HOLD_ACTIVE_CANONICAL_POINTER_UNAVAILABLE",
    )
    if (
        pointer.get("schema") != "w7tp.total_field.active_w7tp_canonical_pointer.v1"
        or pointer.get("state") != "ACTIVE_CANONICAL"
        or pointer.get("namespace") != "w7tp_canonical"
    ):
        raise CandidateSourceError("HOLD_ACTIVE_CANONICAL_POINTER_INVALID")

    canonical_ref = pointer.get("canonical_path")
    canonical_sha = pointer.get("canonical_sha256")
    schema_ref = pointer.get("machine_schema_path")
    schema_sha = pointer.get("machine_schema_sha256")
    if not all(
        isinstance(value, str) and value
        for value in (canonical_ref, canonical_sha, schema_ref, schema_sha)
    ):
        raise CandidateSourceError("HOLD_ACTIVE_CANONICAL_POINTER_BINDING_MISSING")

    canonical_path = (ROOT / canonical_ref).resolve()
    schema_path = (ROOT / schema_ref).resolve()
    root_resolved = ROOT.resolve()
    try:
        canonical_path.relative_to(root_resolved)
        schema_path.relative_to(root_resolved)
    except ValueError as exc:
        raise CandidateSourceError("HOLD_ACTIVE_CANONICAL_PATH_ESCAPE") from exc

    if (
        not canonical_path.is_file()
        or _file_sha256(canonical_path) != canonical_sha
        or not schema_path.is_file()
        or _file_sha256(schema_path) != schema_sha
    ):
        raise CandidateSourceError("HOLD_ACTIVE_CANONICAL_HASH_OR_PATH_DRIFT")

    version = pointer.get("version")
    canonical_id = pointer.get("canonical_id")
    if not isinstance(version, str) or not isinstance(canonical_id, str):
        raise CandidateSourceError("HOLD_ACTIVE_CANONICAL_IDENTITY_INVALID")

    if version == "2.3":
        if (
            canonical_id != CANDIDATE_ID
            or canonical_ref != V23_CANONICAL_CONTRACT_REF
            or schema_ref != V23_CANONICAL_SCHEMA_REF
        ):
            raise CandidateSourceError("HOLD_ACTIVE_V23_CANONICAL_BINDING_INVALID")
        contract = _load_strict_json(
            canonical_path,
            "HOLD_ACTIVE_V23_CANONICAL_CONTRACT_UNAVAILABLE",
        )
        expected_dimensions = {
            "D1": "Intent",
            "D2": "State",
            "D3": "Coordinate",
            "D4": "Evidence",
            "D5": "Execution/Policy",
            "D6": "Generative State Transmission",
            "D7": "Risk/Isolation",
            "D8": "Envelope/Authority",
        }
        constraints = contract.get("coupled_constraints")
        if (
            contract.get("schema_version")
            != "W7TP-8D-ADI-CANONICAL-CONTRACT/2.3"
            or contract.get("canonical_id") != CANDIDATE_ID
            or contract.get("version") != "2.3"
            or contract.get("founder") != "江政隆"
            or contract.get("semantics") != "8_IN_1_SINGLE_DYNAMIC_STATE_FIELD"
            or contract.get("dimensions") != expected_dimensions
            or not isinstance(constraints, Mapping)
            or constraints.get("sequential_pipeline_definition_forbidden") is not True
            or constraints.get("fixed_eight_field_record_definition_forbidden") is not True
            or constraints.get("difference_analysis_is_transmission") is not False
            or constraints.get("model_is_authority") is not False
            or contract.get("activation_contract", {}).get("self_promotion_allowed")
            is not False
        ):
            raise CandidateSourceError("HOLD_ACTIVE_V23_CANONICAL_SEMANTICS_INVALID")
        unsigned = dict(contract)
        supplied = unsigned.pop("contract_self_sha256", None)
        if (
            contract.get("contract_self_hash_algorithm")
            != "SHA256_CANONICAL_JSON_EXCLUDING_CONTRACT_SELF_SHA256/1.0"
            or supplied != _canonical_sha256(unsigned)
        ):
            raise CandidateSourceError("HOLD_ACTIVE_V23_CANONICAL_SELF_HASH_INVALID")

    return {
        "state": "ACTIVE_CANONICAL",
        "pointer_ref": ACTIVE_POINTER_REF,
        "pointer_sha256": _file_sha256(pointer_path),
        "canonical_id": canonical_id,
        "version": version,
        "canonical_path": canonical_ref,
        "canonical_sha256": canonical_sha,
        "machine_schema_path": schema_ref,
        "machine_schema_sha256": schema_sha,
        "promotion_receipt_path": pointer.get("promotion_receipt_path"),
        "promotion_receipt_sha256": pointer.get("promotion_receipt_sha256"),
        "founder_authority": pointer.get("founder_authority"),
    }


def require_active_v23_binding() -> dict[str, Any]:
    binding = active_canonical_binding()
    if (
        binding["canonical_id"] != CANDIDATE_ID
        or binding["version"] != CANDIDATE_VERSION
    ):
        raise CandidateSourceError("HOLD_ACTIVE_V23_NOT_PROMOTED")
    return binding
