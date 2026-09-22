from __future__ import annotations

import copy
import inspect
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from tools.total_field.w7tp_total_field_genesis_stage_c_candidate import (
    ACTIVE_AUTHORITY_REL,
    BUILD_ONLY_EFFECT,
    FORMAL_ACTIVATION_EFFECT,
    FORMAL_AUTHORIZATION_SCHEMA_ID,
    REVOCATION_STATUS_SCHEMA_ID,
    SimulatedCrash,
    TARGET_HEAD,
    TARGET_NODE,
    canonical_sha256,
    prepare_stage_c_candidate,
    simulate_atomic_activation,
)


NOW = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64


class TrustedGovernanceVerifier:
    trusted_runtime_verifier = True

    def verify_formal_authorization(self, authorization: object) -> bool:
        return isinstance(authorization, dict)

    def verify_revocation_status(self, status: object) -> bool:
        return isinstance(status, dict)


GOVERNANCE_VERIFIER = TrustedGovernanceVerifier()


def self_hash(document: dict[str, object], field: str) -> str:
    unsigned = copy.deepcopy(document)
    unsigned.pop(field, None)
    return canonical_sha256(unsigned)


def make_stage_b(*, expires_at: str = "2026-09-20T12:04:00Z") -> dict[str, object]:
    value: dict[str, object] = {
        "schema_id": "W7TP_TOTAL_FIELD_GENESIS_AUTHORITY_BOOTSTRAP_CANDIDATE_V1",
        "stage": "B_SEALED_GENESIS_CANDIDATE",
        "state": "SEALED_GENESIS_AUTHORITY_CANDIDATE",
        "candidate_only": True,
        "authority_granted": False,
        "active_authority_created": False,
        "activation_called": False,
        "receiver_call_count": 0,
        "second_authority_created": False,
        "second_receiver_created": False,
        "database_written": False,
        "deployment_performed": False,
        "service_restarted": False,
        "private_key_read": False,
        "member_plaintext_included": False,
        "existing_d8_pass_required": False,
        "nonce_consumed": True,
        "total_field_decision": "NOT_RUN",
        "authority_record_path": ACTIVE_AUTHORITY_REL.as_posix(),
        "authority_id": f"authority_ref:sha256:{SHA_A}",
        "authority_version": 1,
        "authority_scope": ["E5_FORMAL_READ_ONLY_REVIEW", "RECEIVE_CANDIDATE"],
        "issued_at": "2026-09-20T11:59:00Z",
        "expires_at": expires_at,
        "nonce": f"nonce_ref:sha256:{SHA_A}",
        "verifier_ref": "verifier_ref:test.stage-c.v1",
        "registry_coordinate": (
            "odoo18://wuchang_member_registration/wuchang.member.registration/"
            "sovereign-authority-ledger-candidate-v1"
        ),
        "founder_person_packet_ref": f"person_ref:sha256:{SHA_A}",
        "founder_identity_root_ref": f"identity_ref:sha256:{SHA_B}",
        "founder_role_seat_ref": f"seat_ref:sha256:{SHA_C}",
        "registered_device_ref": f"device_ref:sha256:{SHA_D}",
        "founder_capability_assignment_ref": f"capability_ref:sha256:{SHA_A}",
        "access_profile_ref": f"access_ref:sha256:{SHA_B}",
        "evidence_bundle_sha256": SHA_C,
        "evidence_refs": {
            "founder_identity_binding_receipt_ref": f"receipt_ref:sha256:{SHA_A}",
            "8d_adi_binding_evidence_ref": f"adi_ref:sha256:{SHA_B}",
            "current_root_registry_cardinality_evidence_ref": (
                f"cardinality_ref:sha256:{SHA_C}"
            ),
        },
        "proposal_sha256": SHA_A,
        "proposal_ref": f"genesis_proposal_ref:sha256:{SHA_A}",
        "founder_signature_sha256": SHA_B,
        "owner_seal_sha256": SHA_C,
        "revocation_sha256": SHA_D,
        "activation_capability": {
            "capability_id": "W7TP_TOTAL_FIELD_GENESIS_ATOMIC_ACTIVATION_V1",
            "target": ACTIVE_AUTHORITY_REL.as_posix(),
            "single_use": True,
            "atomic_create_if_absent": True,
            "persistent_nonce_required": True,
            "permanent_self_stop_after_success": True,
            "call_forbidden_in_candidate_build": True,
            "implementation": "INJECTED_SINGLE_USE_ATOMIC_AUTHORITY_STORE",
        },
        "red_team_pre_definition": {
            "active_authority_preexistence": "PERMANENT_BLOCK",
            "activation_in_this_run": "FORBIDDEN",
            "database_write": "FORBIDDEN",
            "external_signature_verifier": "REQUIRED",
            "persistent_nonce": "REQUIRED",
            "private_key_access": "FORBIDDEN",
            "second_authority": "FORBIDDEN",
            "second_receiver": "FORBIDDEN",
            "second_registry_coordinate": "FORBIDDEN",
        },
    }
    value["sealed_candidate_sha256"] = self_hash(value, "sealed_candidate_sha256")
    return value


def make_status(
    stage_b: dict[str, object], *, state: str = "NOT_REVOKED"
) -> dict[str, object]:
    return {
        "schema_id": REVOCATION_STATUS_SCHEMA_ID,
        "state": state,
        "verified": True,
        "authority_id": stage_b["authority_id"],
        "stage_b_document_sha256": canonical_sha256(stage_b),
        "checked_at": "2026-09-20T11:59:30Z",
        "expires_at": "2026-09-20T12:02:00Z",
        "verifier_ref": "verifier_ref:test.stage-c.v1",
        "evidence_sha256": SHA_D,
        "verification_receipt_ref": f"receipt_ref:sha256:{SHA_D}",
    }


def make_authorization(stage_b: dict[str, object]) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_id": FORMAL_AUTHORIZATION_SCHEMA_ID,
        "authorized_effect": FORMAL_ACTIVATION_EFFECT,
        "target_node": TARGET_NODE,
        "target_head": TARGET_HEAD,
        "authority_id": stage_b["authority_id"],
        "stage_b_document_sha256": canonical_sha256(stage_b),
        "authority_pointer": ACTIVE_AUTHORITY_REL.as_posix(),
        "single_use": True,
        "verifier_ref": "verifier_ref:test.stage-c.v1",
        "signer_identity_root_ref": f"identity_ref:sha256:{SHA_B}",
        "signer_role_seat_ref": f"seat_ref:sha256:{SHA_C}",
        "signature_sha256": SHA_D,
        "issued_at": "2026-09-20T11:59:30Z",
        "expires_at": "2026-09-20T12:01:00Z",
    }
    value["authorization_sha256"] = self_hash(value, "authorization_sha256")
    return value


def prepare(
    *,
    stage_b: dict[str, object] | None = None,
    status: dict[str, object] | None = None,
    authorization: dict[str, object] | None | object = ...,
    node: str = TARGET_NODE,
    head: str = TARGET_HEAD,
    active_pointer_exists: bool = False,
) -> dict[str, object]:
    b_value = stage_b or make_stage_b()
    status_value = status if status is not None else make_status(b_value)
    authorization_value = (
        make_authorization(b_value) if authorization is ... else authorization
    )
    return prepare_stage_c_candidate(
        stage_b=b_value,
        stage_b_document_sha256=canonical_sha256(b_value),
        revocation_status=status_value,
        founder_activation_authorization=authorization_value,  # type: ignore[arg-type]
        governance_verifier=GOVERNANCE_VERIFIER,
        current_build_effect=BUILD_ONLY_EFFECT,
        node_id=node,
        head=head,
        active_pointer_exists=active_pointer_exists,
        now=NOW,
    )


def test_absent_active_authority_allows_simulated_success(tmp_path: Path) -> None:
    plan = prepare()
    assert plan["state"] == "C_GENESIS_ACTIVATION_READY"

    receipt = simulate_atomic_activation(
        plan=plan,
        simulation_root=tmp_path,
        explicit_simulation=True,
    )

    assert receipt["state"] == "SIMULATED_ATOMIC_ACTIVATION"
    assert receipt["formal_activation_performed"] is False
    assert receipt["live_pointer_written"] is False
    assert (tmp_path / ACTIVE_AUTHORITY_REL).is_file()


def test_existing_active_authority_blocks() -> None:
    result = prepare(active_pointer_exists=True)
    assert result["state"] == "BLOCK"
    assert result["reason_code"] == "BLOCK_ACTIVE_TOTAL_FIELD_AUTHORITY_ALREADY_EXISTS"


def test_stage_b_hash_mismatch_rejects() -> None:
    stage_b = make_stage_b()
    result = prepare_stage_c_candidate(
        stage_b=stage_b,
        stage_b_document_sha256="0" * 64,
        revocation_status=make_status(stage_b),
        founder_activation_authorization=make_authorization(stage_b),
        governance_verifier=GOVERNANCE_VERIFIER,
        current_build_effect=BUILD_ONLY_EFFECT,
        node_id=TARGET_NODE,
        head=TARGET_HEAD,
        active_pointer_exists=False,
        now=NOW,
    )
    assert result["state"] == "REJECT"
    assert result["reason_code"] == "REJECT_GENESIS_STAGE_B_DOCUMENT_HASH_MISMATCH"


def test_stage_b_missing_holds() -> None:
    result = prepare_stage_c_candidate(
        stage_b=None,
        stage_b_document_sha256="",
        revocation_status=None,
        founder_activation_authorization=None,
        governance_verifier=GOVERNANCE_VERIFIER,
        current_build_effect=BUILD_ONLY_EFFECT,
        node_id=TARGET_NODE,
        head=TARGET_HEAD,
        active_pointer_exists=False,
        now=NOW,
    )
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_GENESIS_STAGE_B_MISSING"


def test_founder_formal_activation_authorization_absent_holds() -> None:
    result = prepare(authorization=None)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_FOUNDER_FORMAL_ACTIVATION_AUTHORIZATION_ABSENT"


def test_wrong_target_msi_blocks() -> None:
    result = prepare(node="MSI")
    assert result["state"] == "BLOCK"
    assert result["reason_code"] == "BLOCK_TARGET_NODE_NOT_TAIJI01"


def test_wrong_taiji01_head_holds() -> None:
    result = prepare(head="f" * 40)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_TAIJI01_HEAD_MISMATCH"


def test_untrusted_governance_verifier_holds() -> None:
    class UntrustedGovernanceVerifier(TrustedGovernanceVerifier):
        trusted_runtime_verifier = False

    stage_b = make_stage_b()
    result = prepare_stage_c_candidate(
        stage_b=stage_b,
        stage_b_document_sha256=canonical_sha256(stage_b),
        revocation_status=make_status(stage_b),
        founder_activation_authorization=make_authorization(stage_b),
        governance_verifier=UntrustedGovernanceVerifier(),
        current_build_effect=BUILD_ONLY_EFFECT,
        node_id=TARGET_NODE,
        head=TARGET_HEAD,
        active_pointer_exists=False,
        now=NOW,
    )
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_GENESIS_REVOCATION_STATUS_UNVERIFIED"


def test_expired_stage_b_holds() -> None:
    stage_b = make_stage_b(expires_at="2026-09-20T11:59:59Z")
    result = prepare(stage_b=stage_b)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_GENESIS_STAGE_B_EXPIRED"


def test_revoked_stage_b_blocks() -> None:
    stage_b = make_stage_b()
    result = prepare(stage_b=stage_b, status=make_status(stage_b, state="REVOKED"))
    assert result["state"] == "BLOCK"
    assert result["reason_code"] == "BLOCK_GENESIS_STAGE_B_REVOKED"


def test_replay_blocks(tmp_path: Path) -> None:
    plan = prepare()
    first = simulate_atomic_activation(
        plan=plan, simulation_root=tmp_path, explicit_simulation=True
    )
    second = simulate_atomic_activation(
        plan=plan, simulation_root=tmp_path, explicit_simulation=True
    )
    assert first["state"] == "SIMULATED_ATOMIC_ACTIVATION"
    assert second["state"] == "BLOCK"
    assert second["reason_code"] == "BLOCK_ACTIVE_TOTAL_FIELD_AUTHORITY_ALREADY_EXISTS"


def test_crash_before_commit_leaves_no_pointer(tmp_path: Path) -> None:
    try:
        simulate_atomic_activation(
            plan=prepare(),
            simulation_root=tmp_path,
            explicit_simulation=True,
            fault="before_commit",
        )
    except SimulatedCrash as exc:
        assert "before transaction commit" in str(exc)
    else:
        raise AssertionError("expected SimulatedCrash")
    assert not (tmp_path / ACTIVE_AUTHORITY_REL).exists()


def test_crash_mid_commit_leaves_no_half_active_pointer(tmp_path: Path) -> None:
    try:
        simulate_atomic_activation(
            plan=prepare(),
            simulation_root=tmp_path,
            explicit_simulation=True,
            fault="mid_commit",
        )
    except SimulatedCrash as exc:
        assert "after capsule commit" in str(exc)
    else:
        raise AssertionError("expected SimulatedCrash")
    assert not (tmp_path / ACTIVE_AUTHORITY_REL).exists()
    receipts = list(
        (tmp_path / "stage_c_transactions").glob(
            "*/ACTIVATION_RECEIPT_CANDIDATE.json"
        )
    )
    assert len(receipts) == 1


def test_receipt_failure_quarantines_and_leaves_no_pointer(tmp_path: Path) -> None:
    result = simulate_atomic_activation(
        plan=prepare(),
        simulation_root=tmp_path,
        explicit_simulation=True,
        fault="receipt_failure",
    )
    assert result["state"] == "QUARANTINE"
    assert result["reason_code"] == (
        "QUARANTINE_GENESIS_ACTIVATION_RECEIPT_OR_COMMIT_FAILURE"
    )
    assert not (tmp_path / ACTIVE_AUTHORITY_REL).exists()
    quarantines = list((tmp_path / "stage_c_transactions").glob("quarantine-*"))
    assert len(quarantines) == 1


def test_simulation_guard_blocks_live_repository_root() -> None:
    plan = prepare()
    repo_root = Path(__file__).resolve().parents[1]
    result = simulate_atomic_activation(
        plan=plan,
        simulation_root=repo_root,
        explicit_simulation=True,
    )
    assert result["state"] == "BLOCK"
    assert result["reason_code"] == "BLOCK_LIVE_REPOSITORY_SIMULATION"


if __name__ == "__main__":
    selected = [
        value
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    ]
    selected.sort(key=lambda value: value.__name__)
    for test in selected:
        if "tmp_path" in inspect.signature(test).parameters:
            with tempfile.TemporaryDirectory(prefix="stage-c-test-") as directory:
                test(Path(directory))
        else:
            test()
        print(f"PASS {test.__name__}")
    print(f"PASS_TOTAL={len(selected)}")
