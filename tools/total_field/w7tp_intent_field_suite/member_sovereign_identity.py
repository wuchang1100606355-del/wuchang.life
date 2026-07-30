"""Read-only P1 verifier candidate for the P0 member-sovereign identity contract."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
P0_VERIFIER_PATH = (
    REPO_ROOT
    / "scripts/verify/verify_member_sovereign_identity_root_contract.py"
)
P0_MANIFEST_PATH = (
    REPO_ROOT
    / "manifests/total_field/w7tp_member_sovereign_identity_root_v1/"
    "SHA256_MANIFEST.json"
)
P0_CONTENT_SHA256 = (
    "2b8fec135a9a714af0a8b4cc5c9a77fcbc06c643ea13c66b73271c6834e592ce"
)
P0_MANIFEST_SHA256 = (
    "4ee5af92bfb674ae3f1ad5e761e09122477bf545b66f5e0b408f6a969a8e625c"
)
EVIDENCE_SCHEMA_VERSION = "W7TP-MEMBER-IDENTITY-EVIDENCE-BINDING/1.0"
EVIDENCE_KIND_BY_FIELD = {
    "root_chain_evidence": "root_chain_snapshot",
    "root_registry_evidence": "root_registry_snapshot",
    "proof_registry_evidence": "proof_registry_snapshot",
    "derived_packets_evidence": "derived_packets",
    "role_seat_registry_evidence": "role_seat_registry_snapshot",
    "nonce_replay_evidence": "nonce_replay_snapshot",
    "dual_receipt_evidence": "dual_receipt",
    "member_proof_registry_evidence": "member_proof_registry_snapshot",
    "verification_context_evidence": "verification_context",
}
DERIVED_PACKET_KEYS = (
    "session",
    "scene",
    "consent",
    "revocation",
    "recovery",
    "role_seat",
)


class CandidateHold(RuntimeError):
    """Fail-closed P1 candidate result."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _load_p0_verifier() -> ModuleType:
    module_name = "_w7tp_member_sovereign_identity_p0_contract"
    loaded = sys.modules.get(module_name)
    if loaded is not None:
        return loaded
    spec = importlib.util.spec_from_file_location(module_name, P0_VERIFIER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("P0 verifier source is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_P0 = _load_p0_verifier()


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise CandidateHold(code)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _current_p0_content_sha256() -> str:
    lines = []
    for relative in _P0.MANIFEST_FILES:
        lines.append(f"{_file_sha256(REPO_ROOT / relative)}  {relative}\n")
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def verify_p0_hash_binding() -> dict[str, str]:
    """Verify the exact P0 source seal without changing P0 state."""

    current_content = _current_p0_content_sha256()
    current_manifest = _file_sha256(P0_MANIFEST_PATH)
    _require(
        current_content == P0_CONTENT_SHA256
        and current_manifest == P0_MANIFEST_SHA256,
        "HOLD_P0_HASH_BINDING_MISMATCH",
    )
    manifest_result = _P0.verify_manifest(P0_MANIFEST_PATH)
    _require(
        manifest_result["content_sha256"] == P0_CONTENT_SHA256,
        "HOLD_P0_HASH_BINDING_MISMATCH",
    )
    return {
        "p0_content_sha256": current_content,
        "p0_manifest_sha256": current_manifest,
    }


def _outcome(state: str, reason_code: str) -> dict[str, Any]:
    return {
        "state": state,
        "reason_code": reason_code,
        "candidate_only": True,
        "p0_content_sha256": P0_CONTENT_SHA256,
        "p0_manifest_sha256": P0_MANIFEST_SHA256,
    }


def _unwrap_evidence(
    candidate: Mapping[str, Any], field: str
) -> Any:
    wrapper = candidate.get(field)
    if not isinstance(wrapper, Mapping):
        raise CandidateHold("HOLD_NOT_EVIDENCED")
    if set(wrapper) != {
        "schema_version",
        "evidence_ref",
        "payload_sha256",
        "payload",
    }:
        raise CandidateHold("HOLD_NOT_EVIDENCED")
    payload = wrapper.get("payload")
    if payload is None:
        raise CandidateHold("HOLD_NOT_EVIDENCED")
    if wrapper.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise CandidateHold("HOLD_EVIDENCE_BINDING_INVALID")
    payload_sha256 = _P0.sha256_json(payload)
    kind = EVIDENCE_KIND_BY_FIELD[field]
    expected_ref = f"{kind}_ref:sha256:{payload_sha256}"
    _require(
        wrapper.get("payload_sha256") == payload_sha256
        and wrapper.get("evidence_ref") == expected_ref,
        "HOLD_EVIDENCE_HASH_MISMATCH",
    )
    return payload


def _registry_entries(payload: Any) -> list[Mapping[str, Any]]:
    if not isinstance(payload, Mapping):
        raise CandidateHold("HOLD_NOT_EVIDENCED")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise CandidateHold("HOLD_NOT_EVIDENCED")
    if not all(isinstance(entry, Mapping) for entry in entries):
        raise CandidateHold("HOLD_NOT_EVIDENCED")
    return entries


def _proofs(payload: Any) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise CandidateHold("HOLD_NOT_EVIDENCED")
    proofs = payload.get("proofs")
    if not isinstance(proofs, Mapping):
        raise CandidateHold("HOLD_NOT_EVIDENCED")
    return proofs


def _verify_root_chain(
    payload: Any,
    root_registry: Any,
    proof_registry: Any,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or not isinstance(
        payload.get("roots"), list
    ):
        raise CandidateHold("HOLD_NOT_EVIDENCED")
    roots = payload["roots"]
    if not roots or not all(isinstance(root, dict) for root in roots):
        raise CandidateHold("HOLD_NOT_EVIDENCED")
    registry_entries = _registry_entries(root_registry)
    proof_entries = _proofs(proof_registry)
    root_schema = _P0.load_schemas()["root"]
    stable_root_ref = roots[0].get("identity_root_ref")
    stable_subject_ref = roots[0].get("subject_binding_ref")
    previous_root: dict[str, Any] | None = None

    for index, root in enumerate(roots):
        try:
            _P0.validate_instance(root_schema, root)
        except _P0.ValidationError as exc:
            raise CandidateHold("HOLD_SCHEMA_INVALID") from exc
        _P0._walk_forbidden(root)
        _require(
            root["integrity"]["content_sha256"] == _P0.content_hash(root),
            "HOLD_ROOT_CONTENT_HASH_MISMATCH",
        )
        _require(
            root["identity_root_ref"] == stable_root_ref
            and root["subject_binding_ref"] == stable_subject_ref,
            "HOLD_ROOT_CHAIN_SUBJECT_MISMATCH",
        )
        _require(
            root["root_generation"] == index + 1,
            "HOLD_ROOT_GENERATION_GAP",
        )
        expected_state = (
            "ACTIVE_CANDIDATE"
            if index == len(roots) - 1
            else {"SUPERSEDED_CANDIDATE", "REVOKED_CANDIDATE"}
        )
        if isinstance(expected_state, set):
            _require(
                root["root_state"] in expected_state,
                "HOLD_ROOT_CHAIN_STATE_INVALID",
            )
        else:
            _require(
                root["root_state"] == expected_state,
                "HOLD_ROOT_CHAIN_STATE_INVALID",
            )
        if previous_root is None:
            _require(
                root["previous_root_packet_ref"] is None,
                "HOLD_ROOT_CHAIN_LINK_MISMATCH",
            )
        else:
            _require(
                root["previous_root_packet_ref"]
                == previous_root["root_packet_ref"],
                "HOLD_ROOT_CHAIN_LINK_MISMATCH",
            )
            _require(
                root["rotation_epoch"] > previous_root["rotation_epoch"],
                "HOLD_ROOT_ROTATION_EPOCH_REGRESSION",
            )
            _require(
                root["revocation_epoch"]
                >= previous_root["revocation_epoch"],
                "HOLD_ROOT_REVOCATION_EPOCH_REGRESSION",
            )

        matching_registry_entries = [
            entry
            for entry in registry_entries
            if entry.get("identity_root_ref") == root["identity_root_ref"]
            and entry.get("root_packet_ref") == root["root_packet_ref"]
            and entry.get("subject_binding_ref") == root["subject_binding_ref"]
            and entry.get("root_generation") == root["root_generation"]
        ]
        if len(matching_registry_entries) != 1:
            raise CandidateHold("HOLD_NOT_EVIDENCED")
        registry_entry = matching_registry_entries[0]
        _require(
            registry_entry.get("revocation_epoch")
            == root["revocation_epoch"]
            and registry_entry.get("current")
            is (index == len(roots) - 1),
            "HOLD_ROOT_REGISTRY_BINDING_MISMATCH",
        )

        proof = proof_entries.get(root["member_verification_proof_ref"])
        if not isinstance(proof, Mapping):
            raise CandidateHold("HOLD_NOT_EVIDENCED")
        for key in (
            "identity_root_ref",
            "root_packet_ref",
            "subject_binding_ref",
            "root_generation",
            "member_verification_key_commitment",
            "issuer_attestation_ref",
        ):
            _require(
                proof.get(key) == root[key],
                "HOLD_ROOT_PROOF_INVALID",
            )
        _require(
            proof.get("verification_state")
            == "VERIFIED_CANDIDATE_EVIDENCE",
            "HOLD_ROOT_PROOF_INVALID",
        )
        previous_root = root

    current_root = roots[-1]
    _P0.verify_root(
        current_root,
        root_registry_snapshot=dict(root_registry),
        proof_registry_snapshot=dict(proof_registry),
    )
    return current_root


def _replay_pairs(
    payload: Any, field: str, left: str, right: str
) -> set[tuple[str, str]]:
    if not isinstance(payload, Mapping):
        raise CandidateHold("HOLD_NOT_EVIDENCED")
    entries = payload.get(field)
    if not isinstance(entries, list):
        raise CandidateHold("HOLD_NOT_EVIDENCED")
    pairs: set[tuple[str, str]] = set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise CandidateHold("HOLD_NOT_EVIDENCED")
        left_value = entry.get(left)
        right_value = entry.get(right)
        if not isinstance(left_value, str) or not isinstance(
            right_value, str
        ):
            raise CandidateHold("HOLD_NOT_EVIDENCED")
        pairs.add((left_value, right_value))
    return pairs


def _verify_derived_packets(
    payload: Any,
    root: dict[str, Any],
    *,
    root_registry: Any,
    proof_registry: Any,
    role_seat_registry: Any,
    nonce_replay: Any,
    observed_at: str,
) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, Mapping) or set(payload) != set(
        DERIVED_PACKET_KEYS
    ):
        raise CandidateHold("HOLD_NOT_EVIDENCED")
    packets = {key: payload[key] for key in DERIVED_PACKET_KEYS}
    if not all(isinstance(packet, dict) for packet in packets.values()):
        raise CandidateHold("HOLD_NOT_EVIDENCED")
    seen_nonces = _replay_pairs(
        nonce_replay,
        "derived_seen",
        "replay_domain_ref",
        "nonce_ref",
    )
    for packet in packets.values():
        _P0.verify_derived_packet(
            packet,
            root,
            root_registry_snapshot=dict(root_registry),
            proof_registry_snapshot=dict(proof_registry),
            seen_nonces=seen_nonces,
            role_seat_registry_snapshot=dict(role_seat_registry),
            now=observed_at,
        )

    session = packets["session"]
    scene = packets["scene"]
    consent = packets["consent"]
    _require(
        scene["payload"]["session_ref"] == session["payload"]["session_ref"],
        "HOLD_SCENE_SESSION_MISMATCH",
    )
    _require(
        consent["payload"]["session_ref"] == session["payload"]["session_ref"]
        and consent["payload"]["scene_ref"] == scene["payload"]["scene_ref"],
        "HOLD_CONSENT_SESSION_SCENE_MISMATCH",
    )
    _require(
        set(scene["payload"]["scope_refs"])
        <= set(session["payload"]["scope_refs"]),
        "HOLD_SCENE_SCOPE_EXPANSION",
    )
    _require(
        set(consent["payload"]["scope_refs"])
        <= set(scene["payload"]["scope_refs"]),
        "HOLD_CONSENT_SCOPE_EXPANSION",
    )
    _require(
        consent["action_binding"]["action_hash"]
        == scene["action_binding"]["action_hash"],
        "HOLD_ACTION_HASH_RECEIPT_MISMATCH",
    )
    return packets


def _verify_join(
    dual_receipt: Any,
    packets: dict[str, dict[str, Any]],
    root: dict[str, Any],
    *,
    root_registry: Any,
    proof_registry: Any,
    member_proof_registry: Any,
    nonce_replay: Any,
    observed_at: str,
) -> str:
    if not isinstance(dual_receipt, dict):
        raise CandidateHold("HOLD_NOT_EVIDENCED")
    receipt_seen = _replay_pairs(
        nonce_replay,
        "receipt_seen",
        "authority",
        "nonce_ref",
    )
    dual_result = _P0.verify_dual_receipt(
        dual_receipt,
        root,
        root_registry_snapshot=dict(root_registry),
        proof_registry_snapshot=dict(proof_registry),
        member_proof_registry_snapshot=dict(member_proof_registry),
        seen_nonces=receipt_seen,
        now=observed_at,
    )
    consent_action = packets["consent"]["action_binding"]
    dual_action = dual_receipt["action_binding"]
    for field in (
        "action_hash",
        "purpose_ref",
        "scope_refs",
        "effect_class",
        "target_ref",
        "parameters_sha256",
        "resource_refs",
        "member_display_hash",
        "terms_version",
        "amount_currency_hash",
    ):
        _require(
            dual_action[field] == consent_action[field],
            "HOLD_DERIVED_DUAL_ACTION_MISMATCH",
        )
    return dual_result["state"]


def verify_member_sovereign_identity_candidate(
    candidate: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return only a read-only PASS, HOLD, or BLOCK candidate outcome."""

    try:
        verify_p0_hash_binding()
        if not isinstance(candidate, Mapping):
            raise CandidateHold("HOLD_NOT_EVIDENCED")
        evidence = {
            field: _unwrap_evidence(candidate, field)
            for field in EVIDENCE_KIND_BY_FIELD
        }
        context = evidence["verification_context_evidence"]
        if not isinstance(context, Mapping) or not isinstance(
            context.get("observed_at"), str
        ):
            raise CandidateHold("HOLD_NOT_EVIDENCED")
        observed_at = context["observed_at"]
        root = _verify_root_chain(
            evidence["root_chain_evidence"],
            evidence["root_registry_evidence"],
            evidence["proof_registry_evidence"],
        )
        packets = _verify_derived_packets(
            evidence["derived_packets_evidence"],
            root,
            root_registry=evidence["root_registry_evidence"],
            proof_registry=evidence["proof_registry_evidence"],
            role_seat_registry=evidence["role_seat_registry_evidence"],
            nonce_replay=evidence["nonce_replay_evidence"],
            observed_at=observed_at,
        )
        join_state = _verify_join(
            evidence["dual_receipt_evidence"],
            packets,
            root,
            root_registry=evidence["root_registry_evidence"],
            proof_registry=evidence["proof_registry_evidence"],
            member_proof_registry=evidence[
                "member_proof_registry_evidence"
            ],
            nonce_replay=evidence["nonce_replay_evidence"],
            observed_at=observed_at,
        )
        if join_state.startswith("BLOCK_"):
            return _outcome("BLOCK", join_state)
        if join_state == "PASS_DUAL_RECEIPT_READY_CANDIDATE":
            return _outcome("PASS", "PASS_P1_READ_ONLY_VERIFIER_CANDIDATE")
        return _outcome("HOLD", join_state)
    except CandidateHold as exc:
        return _outcome("HOLD", exc.code)
    except _P0.ContractHold as exc:
        return _outcome("HOLD", exc.code)
    except _P0.ValidationError:
        return _outcome("HOLD", "HOLD_SCHEMA_INVALID")
    except (KeyError, TypeError, ValueError):
        return _outcome("HOLD", "HOLD_CANDIDATE_INVALID")
