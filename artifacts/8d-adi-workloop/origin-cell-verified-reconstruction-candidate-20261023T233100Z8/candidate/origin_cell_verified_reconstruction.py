#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W7TP / 8D ADI verified Origin-Cell reconstruction candidate.

Candidate-only companion layer around the existing V2.1 codec.

It does NOT:
- modify the anchored codec;
- issue D8 authority;
- deploy or activate a runtime;
- execute model-generated code;
- infer trust from file existence.

It DOES:
- bind deterministic reconstruction inputs into a stable reconstruction key;
- issue a hash-bound D4 reusable trust-seal candidate only after byte-exact verification;
- re-use that seal on identical reconstruction inputs through a cheap fast path;
- keep current D8 effect authority explicitly separate;
- accept model output only as an integration-reasoning candidate, never as executable truth.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

EXPECTED_CODEC_SHA256 = "345af4963feb2fd88c684a96c505aafae63ad46c2c16e5c4dd13722eb3c7a23b"
CODEC_REL = "runtime/total_field/conversation_intake/universal_origin_cell_codec_v2.py"
TRUST_SEAL_SCHEMA = "W7TP_ORIGIN_CELL_VERIFIED_RECONSTRUCTION_TRUST_SEAL_CANDIDATE_V1"
BINDING_SCHEMA = "W7TP_ORIGIN_CELL_DETERMINISTIC_RECONSTRUCTION_BINDING_V1"
MODEL_INTEGRATION_SCHEMA = "W7TP_8DADI_MODEL_INTEGRATION_REASONING_CANDIDATE_V1"
EMPTY_CACHE_SHA256 = hashlib.sha256(b"").hexdigest()
HEX64 = re.compile(r"^[0-9a-f]{64}$")

ALLOWED_RELATIONS = frozenset({
    "SAME_STATE",
    "SUPPLEMENTS",
    "VERSION_SUCCESSOR",
    "CONFLICTS",
    "DEPENDS_ON",
    "PARENT_OF",
    "CHILD_OF",
    "OBSERVES_SAME_EVENT",
})
FORBIDDEN_MODEL_KEYS = frozenset({
    "authority",
    "authorize",
    "execute",
    "execution",
    "shell",
    "command",
    "deploy",
    "restart",
    "write",
    "db_write",
    "signature",
    "effect_authorized",
})


class ReconstructionHold(ValueError):
    """Fail-closed state with a stable machine-readable code."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(code if not detail else f"{code}:{detail}")


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / CODEC_REL).is_file() and (candidate / "services/w7tp_state_hash.py").is_file():
            return candidate
    raise ReconstructionHold("HOLD_REPO_ROOT_NOT_FOUND")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.w7tp_state_hash import canonical_hash, canonical_json  # noqa: E402


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_hex64(value: str, code: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise ReconstructionHold(code)
    return value


def _codec_path() -> Path:
    return REPO_ROOT / CODEC_REL


def codec_anchor_observation() -> dict[str, Any]:
    path = _codec_path()
    actual = sha256_file(path)
    return {
        "ref": CODEC_REL,
        "expected_sha256": EXPECTED_CODEC_SHA256,
        "actual_sha256": actual,
        "match": actual == EXPECTED_CODEC_SHA256,
    }


def _load_codec_module():
    obs = codec_anchor_observation()
    if not obs["match"]:
        raise ReconstructionHold("HOLD_CODEC_ANCHOR_SHA256_MISMATCH")
    path = _codec_path()
    spec = importlib.util.spec_from_file_location("w7tp_origin_cell_codec_v21_anchor", path)
    if spec is None or spec.loader is None:
        raise ReconstructionHold("HOLD_CODEC_IMPORT_SPEC")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _normalized_channel_digests(values: Mapping[int | str, str]) -> dict[str, str]:
    if not values:
        raise ReconstructionHold("HOLD_EXPECTED_TARGET_DIGESTS_EMPTY")
    normalized: dict[str, str] = {}
    for key, digest in values.items():
        try:
            channel = int(key)
        except Exception as exc:
            raise ReconstructionHold("HOLD_TARGET_CHANNEL_ID_INVALID") from exc
        if channel < 1 or channel > 255:
            raise ReconstructionHold("HOLD_TARGET_CHANNEL_ID_INVALID")
        normalized[str(channel)] = _require_hex64(str(digest), "HOLD_TARGET_DIGEST_INVALID")
    return dict(sorted(normalized.items(), key=lambda item: int(item[0])))


def _output_digests(outputs: Mapping[int, bytes]) -> dict[str, str]:
    return {
        str(int(channel)): sha256_bytes(bytes(payload))
        for channel, payload in sorted(outputs.items())
    }


def _cache_digest(decoder: Any) -> str:
    digest = decoder.cache_sha256()
    return _require_hex64(digest, "HOLD_BASE_CACHE_DIGEST_INVALID")


def build_reconstruction_binding(
    *,
    packet: bytes,
    source_state_sha256: str,
    source_size_bytes: int,
    namespace: str,
    reconstruction_contract: str,
    route_ref: str,
    base_cache_sha256: str,
) -> dict[str, Any]:
    """Build the stable input identity.

    Dynamic node/time/evidence/D8 envelope data are intentionally excluded so
    A->B and repeated B reconstructions share the same structural identity.
    """
    if not isinstance(packet, (bytes, bytearray)) or not packet:
        raise ReconstructionHold("HOLD_PACKET_EMPTY")
    if not isinstance(source_size_bytes, int) or source_size_bytes < 0:
        raise ReconstructionHold("HOLD_SOURCE_SIZE_INVALID")
    for value, code in (
        (namespace, "HOLD_NAMESPACE_INVALID"),
        (reconstruction_contract, "HOLD_RECONSTRUCTION_CONTRACT_INVALID"),
        (route_ref, "HOLD_ROUTE_REF_INVALID"),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ReconstructionHold(code)

    source_state_sha256 = _require_hex64(
        source_state_sha256, "HOLD_SOURCE_STATE_DIGEST_INVALID"
    )
    base_cache_sha256 = _require_hex64(
        base_cache_sha256, "HOLD_BASE_CACHE_DIGEST_INVALID"
    )
    codec_obs = codec_anchor_observation()
    if not codec_obs["match"]:
        raise ReconstructionHold("HOLD_CODEC_ANCHOR_SHA256_MISMATCH")

    body = {
        "schema": BINDING_SCHEMA,
        "source_state_sha256": source_state_sha256,
        "source_size_bytes": source_size_bytes,
        "packet_sha256": sha256_bytes(bytes(packet)),
        "packet_bytes": len(packet),
        "codec_ref": CODEC_REL,
        "codec_sha256": codec_obs["actual_sha256"],
        "executor_contract": "UniversalOriginCellDecoder/V2.1-anchored",
        "base_cache_sha256": base_cache_sha256,
        "namespace": namespace,
        "reconstruction_contract": reconstruction_contract,
        "route_ref": route_ref,
        "allowed_opcode_set": [1, 2, 3, 4, 5, 6, 7],
        "dynamic_observation_envelope_in_identity": False,
        "current_d8_authority_in_identity": False,
    }
    body["reconstruction_key"] = canonical_hash(body)
    return body


def _seal_hash_body(seal: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(seal)
    body.pop("trust_seal_sha256", None)
    return body


def verify_trust_seal_record(seal: Mapping[str, Any]) -> None:
    if seal.get("schema") != TRUST_SEAL_SCHEMA:
        raise ReconstructionHold("HOLD_TRUST_SEAL_SCHEMA")
    supplied = _require_hex64(
        str(seal.get("trust_seal_sha256", "")), "HOLD_TRUST_SEAL_DIGEST_INVALID"
    )
    actual = canonical_hash(_seal_hash_body(seal))
    if supplied != actual:
        raise ReconstructionHold("HOLD_TRUST_SEAL_BINDING_MISMATCH")
    if seal.get("effect_authorization") is not False:
        raise ReconstructionHold("BLOCK_TRUST_SEAL_EFFECT_AUTHORITY_ESCALATION")
    if seal.get("current_d8_required_for_effect") is not True:
        raise ReconstructionHold("BLOCK_TRUST_SEAL_D8_SEPARATION_MISSING")


def full_verify_and_issue_candidate_seal(
    *,
    packet: bytes,
    expected_targets: Mapping[int, bytes],
    source_state_sha256: str,
    source_size_bytes: int,
    namespace: str,
    reconstruction_contract: str,
    route_ref: str,
    d4_evidence_refs: Iterable[str],
    observed_at: str,
    decoder: Any | None = None,
) -> dict[str, Any]:
    """Run full byte-exact verification, then issue a reusable D4 seal candidate."""
    codec = _load_codec_module()
    dec = decoder if decoder is not None else codec.UniversalOriginCellDecoder()
    base_cache_sha256 = _cache_digest(dec)

    expected = {
        int(channel): bytes(payload)
        for channel, payload in sorted(expected_targets.items())
    }
    if not expected:
        raise ReconstructionHold("HOLD_EXPECTED_TARGETS_EMPTY")
    expected_digests = _output_digests(expected)

    binding = build_reconstruction_binding(
        packet=packet,
        source_state_sha256=source_state_sha256,
        source_size_bytes=source_size_bytes,
        namespace=namespace,
        reconstruction_contract=reconstruction_contract,
        route_ref=route_ref,
        base_cache_sha256=base_cache_sha256,
    )

    reconstructed = dec.decode(bytes(packet))
    if set(reconstructed) != set(expected):
        raise ReconstructionHold("HOLD_RECONSTRUCTED_CHANNEL_SET_MISMATCH")
    for channel, expected_bytes in expected.items():
        if reconstructed[channel] != expected_bytes:
            raise ReconstructionHold(
                "HOLD_RECONSTRUCTED_BYTES_MISMATCH", str(channel)
            )

    actual_digests = _output_digests(reconstructed)
    if actual_digests != expected_digests:
        raise ReconstructionHold("HOLD_RECONSTRUCTED_DIGEST_MISMATCH")

    target_state_digest = canonical_hash(expected_digests)
    verified_identity = canonical_hash({
        "reconstruction_key": binding["reconstruction_key"],
        "target_state_digest": target_state_digest,
        "channel_digests": expected_digests,
    })
    refs = list(d4_evidence_refs)
    if not refs or not all(isinstance(ref, str) and ref for ref in refs):
        raise ReconstructionHold("HOLD_D4_EVIDENCE_REF_MISSING")
    if not isinstance(observed_at, str) or not observed_at:
        raise ReconstructionHold("HOLD_OBSERVATION_TIME_MISSING")

    seal = {
        "schema": TRUST_SEAL_SCHEMA,
        "state": "CANDIDATE_RECONSTRUCTION_TRUST_SEAL_VERIFIED",
        "seal_role": "D4_REUSABLE_EVIDENCE_CANDIDATE_NOT_D8_AUTHORITY",
        "reconstruction_key": binding["reconstruction_key"],
        "verified_reconstruction_identity": verified_identity,
        "binding": binding,
        "target_state_digest": target_state_digest,
        "channel_digests": expected_digests,
        "verification": {
            "method": "BYTE_EXACT_AND_SHA256",
            "result": "PASS",
            "observed_at": observed_at,
            "d4_evidence_refs": refs,
            "post_cache_sha256": _cache_digest(dec),
        },
        "wire_measurement": {
            "origin_cell_packet_bytes": len(packet),
            "source_state_bytes": source_size_bytes,
            "seal_bytes_are_control_evidence_not_origin_cell_payload": True,
        },
        "effect_authorization": False,
        "current_d8_required_for_effect": True,
        "reconstructed_equals_executed": False,
        "executed_equals_effect_verified": False,
    }
    seal["trust_seal_sha256"] = canonical_hash(seal)
    return seal


def build_trust_index(records: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build a deterministic lookup index without creating a new authority ledger."""
    index: dict[str, dict[str, Any]] = {}
    for record in records:
        verify_trust_seal_record(record)
        key = str(record["reconstruction_key"])
        if key in index and index[key]["trust_seal_sha256"] != record["trust_seal_sha256"]:
            raise ReconstructionHold("HOLD_TRUST_INDEX_CONFLICT")
        index[key] = dict(record)
    return index


def fast_reconstruct_with_trust_seal(
    *,
    packet: bytes,
    source_state_sha256: str,
    source_size_bytes: int,
    namespace: str,
    reconstruction_contract: str,
    route_ref: str,
    trust_index: Mapping[str, Mapping[str, Any]],
    decoder: Any | None = None,
) -> dict[str, Any]:
    """Cheap deterministic path: binding lookup -> decode -> digest compare."""
    codec = _load_codec_module()
    dec = decoder if decoder is not None else codec.UniversalOriginCellDecoder()
    binding = build_reconstruction_binding(
        packet=packet,
        source_state_sha256=source_state_sha256,
        source_size_bytes=source_size_bytes,
        namespace=namespace,
        reconstruction_contract=reconstruction_contract,
        route_ref=route_ref,
        base_cache_sha256=_cache_digest(dec),
    )
    key = binding["reconstruction_key"]
    seal = trust_index.get(key)
    if seal is None:
        return {
            "state": "HOLD_FULL_VERIFICATION_REQUIRED",
            "reconstruction_key": key,
            "effect_authorization": False,
            "current_d8_required_for_effect": True,
        }
    verify_trust_seal_record(seal)
    if seal.get("binding") != binding:
        raise ReconstructionHold("HOLD_TRUST_SEAL_INPUT_BINDING_DRIFT")

    reconstructed = dec.decode(bytes(packet))
    actual_digests = _output_digests(reconstructed)
    expected_digests = _normalized_channel_digests(seal["channel_digests"])
    if actual_digests != expected_digests:
        raise ReconstructionHold("HOLD_FASTPATH_TARGET_DIGEST_MISMATCH")
    target_state_digest = canonical_hash(actual_digests)
    if target_state_digest != seal.get("target_state_digest"):
        raise ReconstructionHold("HOLD_FASTPATH_TARGET_STATE_DIGEST_MISMATCH")

    return {
        "state": "PASS_TRUST_SEAL_FAST_RECONSTRUCTION",
        "reconstruction_key": key,
        "verified_reconstruction_identity": seal["verified_reconstruction_identity"],
        "trust_seal_sha256": seal["trust_seal_sha256"],
        "target_state_digest": target_state_digest,
        "channel_digests": actual_digests,
        "origin_cell_packet_bytes": len(packet),
        "effect_authorization": False,
        "current_d8_required_for_effect": True,
        "reconstructed_equals_executed": False,
    }


def _walk_forbidden_model_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in FORBIDDEN_MODEL_KEYS:
                raise ReconstructionHold(
                    "BLOCK_MODEL_CANDIDATE_EFFECT_OR_AUTHORITY_FIELD", f"{path}.{key}"
                )
            _walk_forbidden_model_keys(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _walk_forbidden_model_keys(item, f"{path}[{index}]")


def normalize_model_integration_candidate(proposal: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize LLM reasoning about information integration.

    The model may identify relations and propose a rule reference. It cannot
    authorize, execute, write, deploy, or become a trust seal.
    """
    _walk_forbidden_model_keys(proposal)
    input_refs = proposal.get("input_refs")
    relations = proposal.get("relation_candidates")
    if not isinstance(input_refs, list) or not input_refs:
        raise ReconstructionHold("HOLD_MODEL_INPUT_REFS_MISSING")
    if not isinstance(relations, list) or not relations:
        raise ReconstructionHold("HOLD_MODEL_RELATION_CANDIDATES_MISSING")

    normalized_relations = []
    for item in relations:
        if not isinstance(item, Mapping):
            raise ReconstructionHold("HOLD_MODEL_RELATION_INVALID")
        subject = item.get("subject_ref")
        predicate = item.get("predicate")
        obj = item.get("object_ref")
        if not all(isinstance(x, str) and x for x in (subject, predicate, obj)):
            raise ReconstructionHold("HOLD_MODEL_RELATION_INVALID")
        if predicate not in ALLOWED_RELATIONS:
            raise ReconstructionHold("HOLD_MODEL_RELATION_NOT_ALLOWED")
        normalized_relations.append({
            "subject_ref": subject,
            "predicate": predicate,
            "object_ref": obj,
        })

    result = {
        "schema": MODEL_INTEGRATION_SCHEMA,
        "state": "CANDIDATE_ONLY",
        "input_refs": list(input_refs),
        "relation_candidates": normalized_relations,
        "rule_candidate_ref": proposal.get("rule_candidate_ref"),
        "deterministic_next_required": [
            "COMPILE_TO_EXISTING_RESTRICTED_ORIGIN_CELL_RULE_SET",
            "VERIFY_RECONSTRUCTION_AGAINST_EXPECTED_TARGET",
            "ISSUE_D4_TRUST_SEAL_ONLY_AFTER_PASS",
            "RESOLVE_CURRENT_D8_SEPARATELY_FOR_ANY_EFFECT",
        ],
        "model_output_is_authority": False,
        "model_output_is_effect": False,
    }
    result["candidate_sha256"] = canonical_hash(result)
    return result


def status_snapshot() -> dict[str, Any]:
    return {
        "state": "CANDIDATE_NOT_CANONICAL",
        "repo_root": str(REPO_ROOT),
        "codec_anchor": codec_anchor_observation(),
        "trust_seal_is_d4_reusable_evidence_only": True,
        "trust_seal_is_d8_authority": False,
        "model_role": "INTEGRATION_RELATION_REASONING_CANDIDATE_ONLY",
        "known_reconstruction": "DETERMINISTIC_FAST_PATH",
        "unknown_reconstruction": "HOLD_FULL_VERIFICATION_OR_MODEL_CANDIDATE",
    }


if __name__ == "__main__":
    print(json.dumps(status_snapshot(), ensure_ascii=False, indent=2, sort_keys=True))
