from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from tools.total_field.w7tp_intent_field_suite import (
    founder_identity_evidence_provider as provider,
)
from tools.total_field.w7tp_intent_field_suite import (
    founder_identity_evidence_snapshot_builder as builder,
)
from tools.total_field.w7tp_intent_field_suite import (
    member_sovereign_identity as p1,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = (
    REPO_ROOT
    / "tools/total_field/w7tp_intent_field_suite/"
    "founder_identity_evidence_snapshot_builder.py"
)
MANIFEST_PATH = (
    REPO_ROOT
    / "manifests/total_field/"
    "w7tp_founder_identity_evidence_snapshot_builder_v1/"
    "SHA256_MANIFEST.json"
)


class _SourceVerifier:
    trusted_odoo_snapshot_verifier = True

    def __init__(self, result: Any = True) -> None:
        self.result = result
        self.calls: list[dict[str, str]] = []

    def verify_snapshot(self, **kwargs: str) -> Any:
        self.calls.append(copy.deepcopy(kwargs))
        return self.result


def _production_shape_input() -> tuple[dict[str, Any], dict[str, str]]:
    p0 = p1._P0
    root = p0.synthetic_root("production-founder")
    root_registry = p0.synthetic_root_registry(root)
    proof_registry = p0.synthetic_proof_registry(root)
    derived = p0.synthetic_derived_packets(root)
    role_seat = derived["role_seat"]
    role_seat_registry = p0.synthetic_role_seat_registry(root, role_seat)
    dual_receipt = p0.synthetic_dual_receipt(
        root,
        derived["consent"]["action_binding"],
    )
    member_proof_registry = p0.synthetic_member_proof_registry(
        root, dual_receipt
    )
    refs = {
        "founder_person_packet_ref": p0.ref(
            "founder_person_packet_ref", "production-founder:person"
        ),
        "registered_device_ref": p0.ref(
            "registered_device_ref", "production-founder:device"
        ),
        "founder_capability_assignment_ref": p0.ref(
            "founder_capability_assignment_ref",
            "production-founder:capability",
        ),
        "access_profile_ref": p0.ref(
            "access_profile_ref", "production-founder:access-profile"
        ),
        "adi_binding_ref": p0.ref(
            "adi_binding_ref", "production-founder:8d-adi"
        ),
    }
    role_payload = role_seat["payload"]
    session_payload = derived["session"]["payload"]
    transmission = role_seat["generative_transmission"]
    source: dict[str, Any] = {
        "schema_version": builder.SOURCE_SNAPSHOT_SCHEMA_VERSION,
        "ledger_model": builder.SOURCE_LEDGER_MODEL,
        "registry_coordinate": provider.REGISTRY_COORDINATE,
        "process_authority": "odoo",
        "deidentified": True,
        "p1_evidence_payloads": {
            "root_chain_evidence": {"roots": [root]},
            "root_registry_evidence": root_registry,
            "proof_registry_evidence": proof_registry,
            "derived_packets_evidence": derived,
            "role_seat_registry_evidence": role_seat_registry,
            "nonce_replay_evidence": {
                "derived_seen": [],
                "receipt_seen": [],
            },
            "dual_receipt_evidence": dual_receipt,
            "member_proof_registry_evidence": member_proof_registry,
            "verification_context_evidence": {
                "observed_at": p0.FIXED_NOW,
            },
        },
        "founders": [
            {
                "founder_person_packet_ref": refs[
                    "founder_person_packet_ref"
                ],
                "identity_root_ref": root["identity_root_ref"],
                "role_seat_ref": role_payload["role_seat_ref"],
                "registered_device_ref": refs["registered_device_ref"],
                "founder_capability_assignment_ref": refs[
                    "founder_capability_assignment_ref"
                ],
                "access_profile_ref": refs["access_profile_ref"],
            }
        ],
        "role_seats": [
            {
                "identity_root_ref": root["identity_root_ref"],
                "role_seat_ref": role_payload["role_seat_ref"],
                "role_ref": role_payload["role_ref"],
                "seat_ref": role_payload["seat_ref"],
                "issuing_process_authority": "odoo",
            }
        ],
        "registered_devices": [
            {
                "identity_root_ref": root["identity_root_ref"],
                "registered_device_ref": refs["registered_device_ref"],
                "device_binding_ref": session_payload["device_binding_ref"],
            }
        ],
        "adi_binding": {
            "identity_root_ref": root["identity_root_ref"],
            "role_seat_ref": role_payload["role_seat_ref"],
            "protocol": "W7TP_8D_INTENT_FIELD_PACKET",
            "state_packet_ref": transmission["state_packet_ref"],
            "total_field_verify_ref": transmission[
                "total_field_verify_ref"
            ],
            "adi_binding_ref": refs["adi_binding_ref"],
        },
    }
    source_attestation = {
        "schema_version": builder.SOURCE_ATTESTATION_SCHEMA_VERSION,
        "registry_coordinate": provider.REGISTRY_COORDINATE,
        "ledger_model": builder.SOURCE_LEDGER_MODEL,
        "ledger_event_ref": p0.ref(
            "root_ledger_event_ref", "production-founder:odoo-ledger-event"
        ),
        "export_receipt_ref": p0.ref(
            "odoo_ledger_export_receipt_ref",
            "production-founder:odoo-export-receipt",
        ),
        "verifier_ref": p0.ref(
            "odoo_snapshot_verifier_ref",
            "production-founder:trusted-export-verifier",
        ),
        "attested_payload_sha256": builder.source_attested_payload_sha256(
            source
        ),
    }
    source_attestation["attestation_ref"] = (
        "odoo_snapshot_attestation_ref:sha256:"
        + builder.canonical_sha256(source_attestation)
    )
    source["source_attestation"] = source_attestation
    source["snapshot_sha256"] = builder.source_snapshot_sha256(source)
    return source, refs


def _reseal_source(source: dict[str, Any]) -> None:
    attestation = source["source_attestation"]
    attestation["attested_payload_sha256"] = (
        builder.source_attested_payload_sha256(source)
    )
    attestation_material = {
        key: copy.deepcopy(value)
        for key, value in attestation.items()
        if key != "attestation_ref"
    }
    attestation["attestation_ref"] = (
        "odoo_snapshot_attestation_ref:sha256:"
        + builder.canonical_sha256(attestation_material)
    )
    source["snapshot_sha256"] = builder.source_snapshot_sha256(source)


def _build(
    source: dict[str, Any],
    refs: dict[str, str],
    source_verifier: Any | None = None,
    trusted_verifier_refs: set[str] | None = None,
) -> dict[str, Any]:
    return builder.build_founder_identity_evidence_snapshot(
        sovereign_root_ledger_snapshot=source,
        source_attestation_verifier=(
            source_verifier if source_verifier is not None else _SourceVerifier()
        ),
        trusted_source_verifier_refs=(
            trusted_verifier_refs
            if trusted_verifier_refs is not None
            else {source["source_attestation"]["verifier_ref"]}
        ),
        **refs,
    )


def test_formal_shape_passes_existing_provider_and_p1_without_synthetic_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, refs = _production_shape_input()
    calls = {"count": 0}

    def forbidden_synthetic(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        calls["count"] += 1
        raise AssertionError("production path called a synthetic helper")

    for name in dir(p1._P0):
        if name.startswith("synthetic_"):
            monkeypatch.setattr(p1._P0, name, forbidden_synthetic)

    source_verifier = _SourceVerifier()
    snapshot = _build(source, refs, source_verifier)
    assert snapshot["state"] == (
        "BUILT_FOUNDER_IDENTITY_EVIDENCE_SNAPSHOT_CANDIDATE"
    )
    assert snapshot["db_write"] is False
    assert snapshot["active_authority_created"] is False
    assert snapshot["receiver_call_count"] == 0
    assert snapshot["synthetic_call_count"] == 0
    assert snapshot["p1_verifier_result"]["state"] == "PASS"
    assert calls["count"] == 0
    assert len(source_verifier.calls) == 1
    assert source_verifier.calls[0]["attested_payload_sha256"] == (
        source["source_attestation"]["attested_payload_sha256"]
    )

    p1_result = p1.verify_member_sovereign_identity_candidate(
        snapshot["p1_candidate"]
    )
    assert p1_result["state"] == "PASS"
    assert p1_result["reason_code"] == "PASS_P1_READ_ONLY_VERIFIER_CANDIDATE"

    reader_calls: list[str] = []

    def reader(coordinate: str) -> dict[str, Any]:
        reader_calls.append(coordinate)
        return copy.deepcopy(snapshot)

    provider_result = provider.ReadOnlyFounderIdentityEvidenceProviderCandidate(
        reader
    ).collect_and_verify()
    assert provider_result["state"] == "PASS"
    assert provider_result["reason_code"] == (
        "PASS_READ_ONLY_FOUNDER_IDENTITY_EVIDENCE_PROVIDER_CANDIDATE"
    )
    assert provider_result["root_registry_cardinality"] == 1
    assert provider_result["p1_verifier_result"]["state"] == "PASS"
    assert reader_calls == [provider.REGISTRY_COORDINATE]
    assert calls["count"] == 0


def test_same_input_is_deterministic_and_self_hashes() -> None:
    source, refs = _production_shape_input()
    first = _build(copy.deepcopy(source), copy.deepcopy(refs))
    second = _build(copy.deepcopy(source), copy.deepcopy(refs))
    assert first == second
    assert first["snapshot_sha256"] == second["snapshot_sha256"]
    material = copy.deepcopy(first)
    material.pop("snapshot_sha256")
    assert first["snapshot_sha256"] == builder.canonical_sha256(material)
    cardinality = first["current_root_registry_cardinality_evidence"][
        "payload"
    ]["cardinality"]
    assert type(cardinality) is int
    assert cardinality == 1


@pytest.mark.parametrize(
    "mutation",
    ["schema", "payload_sha256", "evidence_ref", "missing", "extra"],
)
def test_actual_provider_rejects_corrupt_p1_wrapper_contract(
    mutation: str,
) -> None:
    source, refs = _production_shape_input()
    snapshot = _build(source, refs)
    candidate = snapshot["p1_candidate"]
    wrapper = candidate["root_chain_evidence"]
    if mutation == "schema":
        wrapper["schema_version"] = "WRONG"
    elif mutation == "payload_sha256":
        wrapper["payload_sha256"] = "0" * 64
    elif mutation == "evidence_ref":
        wrapper["evidence_ref"] = p1._P0.ref(
            "root_chain_snapshot_ref", "wrong"
        )
    elif mutation == "missing":
        del candidate["root_chain_evidence"]
    else:
        candidate["extra_evidence"] = copy.deepcopy(wrapper)
    result = provider.ReadOnlyFounderIdentityEvidenceProviderCandidate(
        lambda coordinate: copy.deepcopy(snapshot)
        if coordinate == provider.REGISTRY_COORDINATE
        else None
    ).collect_and_verify()
    assert result["state"] == "HOLD"
    assert result["p1_verifier_result"]["state"] in {"HOLD", "NOT_RUN"}


@pytest.mark.parametrize(
    "mutation",
    ["schema", "payload_sha256", "evidence_ref"],
)
def test_actual_provider_rejects_corrupt_provider_wrapper_contract(
    mutation: str,
) -> None:
    source, refs = _production_shape_input()
    snapshot = _build(source, refs)
    wrapper = snapshot["current_root_registry_cardinality_evidence"]
    if mutation == "schema":
        wrapper["schema_version"] = "WRONG"
    elif mutation == "payload_sha256":
        wrapper["payload_sha256"] = "0" * 64
    else:
        wrapper["evidence_ref"] = p1._P0.ref(
            "current_root_registry_cardinality_evidence_ref", "wrong"
        )
    result = provider.ReadOnlyFounderIdentityEvidenceProviderCandidate(
        lambda coordinate: copy.deepcopy(snapshot)
        if coordinate == provider.REGISTRY_COORDINATE
        else None
    ).collect_and_verify()
    assert result["state"] == "HOLD"


@pytest.mark.parametrize(
    ("field", "empty_code", "second_code"),
    [
        ("founders", "HOLD_FOUNDER_CARDINALITY", "HOLD_SECOND_FOUNDER"),
        ("role_seats", "HOLD_ROLE_SEAT_CARDINALITY", "HOLD_SECOND_ROLE_SEAT"),
        (
            "registered_devices",
            "HOLD_REGISTERED_DEVICE_CARDINALITY",
            "HOLD_SECOND_REGISTERED_DEVICE",
        ),
    ],
)
@pytest.mark.parametrize("cardinality", [0, 2])
def test_founder_role_seat_and_device_cardinality_hold(
    field: str,
    empty_code: str,
    second_code: str,
    cardinality: int,
) -> None:
    source, refs = _production_shape_input()
    original = copy.deepcopy(source[field][0])
    source[field] = [] if cardinality == 0 else [original, copy.deepcopy(original)]
    _reseal_source(source)
    result = _build(source, refs)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == (
        empty_code if cardinality == 0 else second_code
    )


@pytest.mark.parametrize("cardinality", [0, 2])
def test_current_root_cardinality_holds(cardinality: int) -> None:
    source, refs = _production_shape_input()
    entries = source["p1_evidence_payloads"]["root_registry_evidence"][
        "entries"
    ]
    if cardinality == 0:
        entries[0]["current"] = False
    else:
        entries.append(copy.deepcopy(entries[0]))
    _reseal_source(source)
    result = _build(source, refs)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == (
        "HOLD_CURRENT_ROOT_CARDINALITY"
        if cardinality == 0
        else "HOLD_SECOND_CURRENT_ROOT"
    )


@pytest.mark.parametrize(
    ("mutation", "reason_code"),
    [
        ("identity_root", "HOLD_FOUNDER_BINDING"),
        ("role_seat", "HOLD_ROLE_SEAT_CROSS_BINDING"),
        ("registered_device", "HOLD_REGISTERED_DEVICE_CROSS_BINDING"),
        ("adi", "HOLD_8D_ADI_CROSS_BINDING"),
    ],
)
def test_cross_bindings_hold(mutation: str, reason_code: str) -> None:
    source, refs = _production_shape_input()
    other = p1._P0.ref("member_identity_root_ref", f"other:{mutation}")
    if mutation == "identity_root":
        source["founders"][0]["identity_root_ref"] = other
    elif mutation == "role_seat":
        source["role_seats"][0]["identity_root_ref"] = other
    elif mutation == "registered_device":
        source["registered_devices"][0]["identity_root_ref"] = other
    else:
        source["adi_binding"]["identity_root_ref"] = other
    _reseal_source(source)
    result = _build(source, refs)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == reason_code


def test_role_seat_requires_odoo_issuing_process_authority() -> None:
    source, refs = _production_shape_input()
    source["role_seats"][0]["issuing_process_authority"] = "external"
    _reseal_source(source)
    result = _build(source, refs)
    assert result["reason_code"] == "HOLD_ROLE_SEAT_CROSS_BINDING"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("email", "founder@example.invalid"),
        ("member_plaintext", "Founder Name"),
        ("private_key", "forbidden"),
        ("access_token", "forbidden"),
    ],
)
def test_member_plaintext_and_secret_keys_reject_immediately(
    key: str, value: str
) -> None:
    source, refs = _production_shape_input()
    source[key] = value
    _reseal_source(source)
    result = _build(source, refs)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_MEMBER_PLAINTEXT_BOUNDARY"
    assert result["db_write"] is False
    assert result["active_authority_created"] is False
    assert result["receiver_call_count"] == 0


@pytest.mark.parametrize(
    "key",
    ["Member_Plaintext", "PRIVATE_KEY", "raw_key", "Token"],
)
def test_nested_casefolded_plaintext_and_key_names_reject(key: str) -> None:
    source, refs = _production_shape_input()
    source["founders"][0][key] = "forbidden"
    _reseal_source(source)
    result = _build(source, refs)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_MEMBER_PLAINTEXT_BOUNDARY"


def test_source_snapshot_hash_mismatch_holds() -> None:
    source, refs = _production_shape_input()
    source["snapshot_sha256"] = "0" * 64
    result = _build(source, refs)
    assert result["reason_code"] == (
        "HOLD_SOURCE_LEDGER_SNAPSHOT_HASH_MISMATCH"
    )


def test_unattested_or_untrusted_source_never_builds() -> None:
    source, refs = _production_shape_input()
    verifier = _SourceVerifier()
    verifier.trusted_odoo_snapshot_verifier = False
    result = _build(source, refs, verifier)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == (
        "HOLD_SOURCE_ATTESTATION_VERIFIER_UNTRUSTED"
    )
    assert verifier.calls == []

    source, refs = _production_shape_input()
    verifier = _SourceVerifier()
    unknown_ref = p1._P0.ref(
        "odoo_snapshot_verifier_ref", "unknown-source-verifier"
    )
    result = _build(source, refs, verifier, {unknown_ref})
    assert result["state"] == "HOLD"
    assert result["reason_code"] == (
        "HOLD_SOURCE_ATTESTATION_VERIFIER_UNTRUSTED"
    )
    assert verifier.calls == []

    source, refs = _production_shape_input()
    source["source_attestation"]["attested_payload_sha256"] = "0" * 64
    attestation = source["source_attestation"]
    material = {
        key: value for key, value in attestation.items() if key != "attestation_ref"
    }
    attestation["attestation_ref"] = (
        "odoo_snapshot_attestation_ref:sha256:"
        + builder.canonical_sha256(material)
    )
    source["snapshot_sha256"] = builder.source_snapshot_sha256(source)
    result = _build(source, refs)
    assert result["reason_code"] == "HOLD_SOURCE_ATTESTATION_PAYLOAD_MISMATCH"


@pytest.mark.parametrize("verifier_result", [False, "truthy", 1, object()])
def test_source_attestation_verifier_fails_closed(verifier_result: Any) -> None:
    source, refs = _production_shape_input()
    verifier = _SourceVerifier(verifier_result)
    result = _build(source, refs, verifier)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == (
        "HOLD_SOURCE_ATTESTATION_VERIFICATION_FAILED"
        if verifier_result is False
        else "HOLD_SOURCE_ATTESTATION_VERIFIER_RESULT_INVALID"
    )
    assert len(verifier.calls) == 1


def test_source_attestation_verifier_exception_holds() -> None:
    class RaisingSourceVerifier(_SourceVerifier):
        def verify_snapshot(self, **kwargs: str) -> bool:
            self.calls.append(copy.deepcopy(kwargs))
            raise RuntimeError("source verifier unavailable")

    source, refs = _production_shape_input()
    verifier = RaisingSourceVerifier()
    result = _build(source, refs, verifier)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == (
        "HOLD_SOURCE_ATTESTATION_VERIFIER_UNAVAILABLE"
    )
    assert len(verifier.calls) == 1


def test_existing_plaintext_value_boundary_rejects_hidden_email() -> None:
    source, refs = _production_shape_input()
    source["adi_binding"]["protocol"] = "founder@example.invalid"
    _reseal_source(source)
    result = _build(source, refs)
    assert result["reason_code"] == "HOLD_MEMBER_PLAINTEXT_BOUNDARY"


def test_builder_refuses_p1_invalid_evidence_before_emitting_snapshot() -> None:
    source, refs = _production_shape_input()
    current_root = source["p1_evidence_payloads"]["root_chain_evidence"][
        "roots"
    ][-1]
    current_root["root_state"] = "REVOKED_CANDIDATE"
    _reseal_source(source)
    result = _build(source, refs)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_P1_VERIFIER_REJECTED"
    assert result["db_write"] is False
    assert result["active_authority_created"] is False
    assert result["receiver_call_count"] == 0


def test_production_source_has_no_synthetic_or_side_effect_call_path() -> None:
    tree = ast.parse(BUILDER_PATH.read_text(encoding="utf-8"))
    called_names: set[str] = set()
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(
                alias.name.split(".", 1)[0] for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called_names.add(node.func.attr)
    assert not any(name.startswith("synthetic_") for name in called_names)
    assert imported_roots.isdisjoint(
        {"odoo", "requests", "socket", "sqlite3", "subprocess"}
    )
    assert called_names.isdisjoint(
        {
            "receive_candidate",
            "open",
            "write",
            "write_bytes",
            "write_text",
            "create",
            "deploy",
            "activate",
        }
    )


def test_manifest_excludes_itself_and_binds_exact_two_payload_files() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    expected = {
        "tools/total_field/w7tp_intent_field_suite/"
        "founder_identity_evidence_snapshot_builder.py",
        "tests/test_founder_identity_evidence_snapshot_builder.py",
    }
    assert manifest["schema_version"] == "W7TP_SHA256_MANIFEST_V1"
    assert manifest["candidate_id"] == (
        "W7TP_FOUNDER_IDENTITY_EVIDENCE_SNAPSHOT_BUILDER_V1"
    )
    assert manifest["manifest_excludes_itself"] is True
    assert manifest["db_write"] is False
    assert manifest["active_authority_created"] is False
    assert manifest["receiver_call_count"] == 0
    paths = [entry["path"] for entry in manifest["files"]]
    assert len(paths) == len(set(paths)) == 2
    assert set(paths) == expected
    assert manifest["manifest_path"] not in expected
    for entry in manifest["files"]:
        raw = (REPO_ROOT / entry["path"]).read_bytes()
        assert entry["bytes"] == len(raw)
        assert entry["sha256"] == hashlib.sha256(raw).hexdigest()
