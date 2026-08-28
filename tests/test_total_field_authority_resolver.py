from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

CANDIDATE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = CANDIDATE_ROOT / "tools" / "total_field_authority_resolver.py"
SPEC = importlib.util.spec_from_file_location(
    "candidate_total_field_authority_resolver",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
resolver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resolver)


class FakePersistentLedger:
    persistent = True

    def __init__(self) -> None:
        self.used: set[str] = set()

    def mark_used_or_replay(
        self,
        nonce: str,
        packet_hash: str,
        now_epoch: float,
        ttl_seconds: int,
    ) -> bool:
        del packet_hash, now_epoch, ttl_seconds
        if nonce in self.used:
            return False
        self.used.add(nonce)
        return True


class FakeVolatileLedger(FakePersistentLedger):
    persistent = False


class FakeTrustedVerifier:
    trusted_runtime_verifier = True

    def __init__(self, *, allow: bool = True) -> None:
        self.allow = allow
        self.calls: list[tuple[str, str, str]] = []

    def verify(
        self,
        *,
        verifier_ref: str,
        payload_sha256: str,
        signature: str,
    ) -> bool:
        self.calls.append((verifier_ref, payload_sha256, signature))
        return self.allow and signature == f"sig:{payload_sha256}"


class ActiveAuthorityResolverCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.artifacts = self.root / resolver.ARTIFACT_ROOT_REL
        self.artifacts.mkdir(parents=True)
        self.pointer_path = self.root / resolver.ACTIVE_POINTER_REL
        self.pointer_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger = FakePersistentLedger()
        self.verifier = FakeTrustedVerifier()
        self.trusted = {"verifier_ref:total_field_runtime_v1"}
        self._build_valid_chain()

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def _utc(value: datetime) -> str:
        return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )

    @staticmethod
    def _bytes(value: Any) -> bytes:
        return (
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")

    def _write(self, path: Path, value: Any) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self._bytes(value)
        path.write_bytes(data)
        return hashlib.sha256(data).hexdigest()

    def _read(self, path: Path) -> dict[str, Any]:
        value = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(value, dict)
        return value

    def _sign_revocation(self, value: dict[str, Any]) -> dict[str, Any]:
        unsigned = dict(value)
        unsigned.pop("revocation_payload_sha256", None)
        unsigned.pop("signature", None)
        payload_hash = resolver.canonical_sha256(unsigned)
        value["revocation_payload_sha256"] = payload_hash
        value["signature"] = f"sig:{payload_hash}"
        return value

    def _resign_pointer(self, pointer: dict[str, Any]) -> None:
        unsigned = dict(pointer)
        unsigned.pop("authority_payload_sha256", None)
        payload_hash = resolver.canonical_sha256(unsigned)
        pointer["authority_payload_sha256"] = payload_hash
        self._write(self.pointer_path, pointer)
        signature = {
            "schema_id": "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_SIGNATURE_V1",
            "authority_id": pointer["authority_id"],
            "signed_payload_sha256": payload_hash,
            "verifier_ref": pointer["verifier_ref"],
            "signature": f"sig:{payload_hash}",
        }
        self._write(self.signature_path, signature)

    def _build_valid_chain(self) -> None:
        now = datetime.now(timezone.utc)
        self.authority_id = "authority_ref:founder_receive_candidate_v1"
        self.d8_path = self.artifacts / "d8_decision.json"
        self.owner_path = self.artifacts / "owner_seal.json"
        self.signature_path = self.artifacts / "authority_signature.json"
        self.revocation_path = self.artifacts / "revocation_list.json"

        d8 = {
            "schema_id": "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_D8_DECISION_V1",
            "authority_id": self.authority_id,
            "decision": "PASS",
            "reviewed_at": self._utc(now - timedelta(seconds=20)),
            "expires_at": self._utc(now + timedelta(seconds=240)),
        }
        owner = {
            "schema_id": "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_OWNER_SEAL_V1",
            "authority_id": self.authority_id,
            "authorization": "FOUNDER_APPROVED_RECEIVE_CANDIDATE",
            "single_use_id": "single_use_ref:founder_authority_v1",
            "issued_at": self._utc(now - timedelta(seconds=20)),
            "expires_at": self._utc(now + timedelta(seconds=240)),
        }
        revocation = self._sign_revocation(
            {
                "schema_id": "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_REVOCATION_LIST_V1",
                "updated_at": self._utc(now - timedelta(seconds=10)),
                "verifier_ref": "verifier_ref:total_field_runtime_v1",
                "revoked_authority_ids": [],
            }
        )
        d8_sha = self._write(self.d8_path, d8)
        owner_sha = self._write(self.owner_path, owner)
        self._write(self.revocation_path, revocation)

        pointer = {
            "schema_id": "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_V1",
            "authority_id": self.authority_id,
            "authority_version": "1.0.0",
            "state": "ACTIVE",
            "active": True,
            "founder_person_packet_ref": "person_packet_ref:founder_opaque_v1",
            "registered_device_ref": "device_ref:msi_registered_opaque_v1",
            "founder_capability_assignment_ref": (
                "capability_assignment_ref:receive_candidate_opaque_v1"
            ),
            "access_profile_ref": "access_profile_ref:founder_opaque_v1",
            "authority_scope": ["RECEIVE_CANDIDATE"],
            "issued_at": self._utc(now - timedelta(seconds=20)),
            "expires_at": self._utc(now + timedelta(seconds=240)),
            "nonce": "nonce_ref:sha256:" + "a" * 64,
            "d8_decision_ref": self.d8_path.relative_to(self.root).as_posix(),
            "d8_decision_sha256": d8_sha,
            "owner_seal_ref": self.owner_path.relative_to(self.root).as_posix(),
            "owner_seal_sha256": owner_sha,
            "signature_ref": self.signature_path.relative_to(self.root).as_posix(),
            "revocation_ref": self.revocation_path.relative_to(self.root).as_posix(),
            "verifier_ref": "verifier_ref:total_field_runtime_v1",
        }
        self._resign_pointer(pointer)

    def _configure_pointer_bootstrap_scope(self) -> None:
        owner = self._read(self.owner_path)
        owner["authorization"] = (
            "FOUNDER_APPROVED_CURRENT_ACTIVE_CANONICAL_POINTER_BOOTSTRAP"
        )
        pointer = self._read(self.pointer_path)
        pointer["authority_scope"] = [resolver.POINTER_BOOTSTRAP_SCOPE]
        pointer["authority_scope_constraints"] = dict(
            resolver.POINTER_BOOTSTRAP_SCOPE_CONSTRAINTS
        )
        pointer["founder_capability_assignment_ref"] = (
            "capability_assignment_ref:pointer_bootstrap_opaque_v1"
        )
        pointer["access_profile_ref"] = (
            "access_profile_ref:pointer_bootstrap_opaque_v1"
        )
        pointer["owner_seal_sha256"] = self._write(self.owner_path, owner)
        self._resign_pointer(pointer)

    def _configure_promotion_scope(self) -> None:
        owner = self._read(self.owner_path)
        owner["authorization"] = "FOUNDER_APPROVED_PROMOTE_ACCEPTED_CANDIDATE"
        pointer = self._read(self.pointer_path)
        pointer["authority_scope"] = [resolver.PROMOTION_SCOPE]
        pointer["authority_scope_constraints"] = dict(
            resolver.PROMOTION_SCOPE_CONSTRAINTS
        )
        pointer["founder_capability_assignment_ref"] = (
            "capability_assignment_ref:promotion_opaque_v1"
        )
        pointer["access_profile_ref"] = "access_profile_ref:promotion_opaque_v1"
        pointer["owner_seal_sha256"] = self._write(self.owner_path, owner)
        self._resign_pointer(pointer)

    def _resolve(
        self,
        lookup: Any = "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json",
        *,
        ledger: Any | None = None,
        verifier: Any | None = None,
        trusted: set[str] | None = None,
    ) -> dict[str, Any]:
        return resolver.resolve_active_total_field_authority(
            lookup,
            repo_root=self.root,
            nonce_ledger=self.ledger if ledger is None else ledger,
            signature_verifier=self.verifier if verifier is None else verifier,
            trusted_verifier_refs=self.trusted if trusted is None else trusted,
        )

    def test_01_complete_independent_chain_passes_without_execution_authority(self) -> None:
        result = self._resolve()
        self.assertEqual(result["state"], "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED")
        self.assertTrue(result["authority_verified"])
        self.assertFalse(result["candidate_authority"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["formal_decision_authority"])
        self.assertFalse(result["formal_seal_authority"])

    def test_02_wrong_lookup_reference_holds(self) -> None:
        result = self._resolve("runtime/total_field/other.json")
        self.assertEqual(result["state"], "HOLD_AUTHORITY_INCOMPLETE")

    def test_03_provider_or_caller_mapping_cannot_assert_authority(self) -> None:
        result = self._resolve(
            {
                "provider": "LINE",
                "founder_person_packet_ref": "person_packet_ref:claimed",
                "d8_decision_state": "PASS",
            }
        )
        self.assertEqual(result["state"], "BLOCK_PROVIDER_ACCOUNT_AUTHORITY")

    def test_04_missing_active_pointer_holds(self) -> None:
        self.pointer_path.unlink()
        result = self._resolve()
        self.assertEqual(result["state"], "HOLD_AUTHORITY_INCOMPLETE")

    def test_05_process_local_nonce_storage_is_rejected(self) -> None:
        result = self._resolve(ledger=FakeVolatileLedger())
        self.assertEqual(result["state"], "HOLD_NONCE_LEDGER_NOT_PERSISTENT")

    def test_06_untrusted_verifier_reference_blocks(self) -> None:
        result = self._resolve(trusted=set())
        self.assertEqual(result["state"], "BLOCK_AUTHORITY_SIGNATURE_INVALID")

    def test_07_pointer_payload_hash_mismatch_blocks(self) -> None:
        pointer = self._read(self.pointer_path)
        pointer["access_profile_ref"] = "access_profile_ref:tampered_opaque_v1"
        self._write(self.pointer_path, pointer)
        result = self._resolve()
        self.assertEqual(result["state"], "BLOCK_AUTHORITY_BINDING_INVALID")

    def test_08_expired_pointer_holds(self) -> None:
        now = datetime.now(timezone.utc)
        pointer = self._read(self.pointer_path)
        pointer["issued_at"] = self._utc(now - timedelta(seconds=300))
        pointer["expires_at"] = self._utc(now - timedelta(seconds=1))
        self._resign_pointer(pointer)
        result = self._resolve()
        self.assertEqual(result["state"], "HOLD_AUTHORITY_EXPIRED")

    def test_09_candidate_or_traversal_artifact_reference_blocks(self) -> None:
        pointer = self._read(self.pointer_path)
        pointer["d8_decision_ref"] = (
            "runtime/total_field/candidate_specs/fake/d8_decision.json"
        )
        self._resign_pointer(pointer)
        result = self._resolve()
        self.assertEqual(result["state"], "BLOCK_AUTHORITY_REFERENCE_INVALID")

    def test_10_d8_not_pass_holds(self) -> None:
        d8 = self._read(self.d8_path)
        d8["decision"] = "HOLD"
        pointer = self._read(self.pointer_path)
        pointer["d8_decision_sha256"] = self._write(self.d8_path, d8)
        self._resign_pointer(pointer)
        result = self._resolve()
        self.assertEqual(result["state"], "HOLD_D8_AUTHORITY_NOT_APPROVED")

    def test_11_owner_seal_invalid_blocks(self) -> None:
        owner = self._read(self.owner_path)
        owner["authorization"] = "CANDIDATE_SELF_APPROVED"
        pointer = self._read(self.pointer_path)
        pointer["owner_seal_sha256"] = self._write(self.owner_path, owner)
        self._resign_pointer(pointer)
        result = self._resolve()
        self.assertEqual(result["state"], "BLOCK_OWNER_SEAL_INVALID")

    def test_12_detached_signature_failure_blocks(self) -> None:
        signature = self._read(self.signature_path)
        signature["signature"] = "invalid"
        self._write(self.signature_path, signature)
        result = self._resolve()
        self.assertEqual(result["state"], "BLOCK_AUTHORITY_SIGNATURE_INVALID")

    def test_13_revoked_authority_blocks(self) -> None:
        revocation = self._read(self.revocation_path)
        revocation["revoked_authority_ids"] = [self.authority_id]
        revocation = self._sign_revocation(revocation)
        self._write(self.revocation_path, revocation)
        result = self._resolve()
        self.assertEqual(result["state"], "BLOCK_AUTHORITY_REVOKED")

    def test_14_nonce_replay_blocks_second_resolution(self) -> None:
        first = self._resolve()
        second = self._resolve()
        self.assertEqual(first["state"], "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED")
        self.assertEqual(second["state"], "BLOCK_AUTHORITY_REPLAY")

    def test_15_d8_file_hash_mismatch_blocks(self) -> None:
        d8 = self._read(self.d8_path)
        d8["decision"] = "PASS "
        self._write(self.d8_path, d8)
        result = self._resolve()
        self.assertEqual(result["state"], "BLOCK_AUTHORITY_BINDING_INVALID")


    def test_16_pointer_bootstrap_scope_exact_contract_passes(self) -> None:
        self._configure_pointer_bootstrap_scope()
        result = self._resolve()
        self.assertEqual(result["state"], "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED")
        self.assertEqual(result["scope"], [resolver.POINTER_BOOTSTRAP_SCOPE])
        self.assertEqual(
            result["authority_scope_constraints"],
            resolver.POINTER_BOOTSTRAP_SCOPE_CONSTRAINTS,
        )
        self.assertRegex(result["authority_sha256"], r"^[0-9a-f]{64}$")

    def test_17_pointer_bootstrap_scope_requires_exact_constraints(self) -> None:
        self._configure_pointer_bootstrap_scope()
        pointer = self._read(self.pointer_path)
        pointer["authority_scope_constraints"]["overwrite"] = True
        self._resign_pointer(pointer)
        result = self._resolve()
        self.assertEqual(result["state"], "BLOCK_AUTHORITY_SCOPE_ESCALATION")

    def test_18_mixed_authority_scopes_are_rejected(self) -> None:
        self._configure_pointer_bootstrap_scope()
        pointer = self._read(self.pointer_path)
        pointer["authority_scope"] = [
            resolver.POINTER_BOOTSTRAP_SCOPE,
            "RECEIVE_CANDIDATE",
        ]
        self._resign_pointer(pointer)
        result = self._resolve()
        self.assertEqual(result["state"], "HOLD_AUTHORITY_INCOMPLETE")

    def test_19_pointer_bootstrap_promotion_escalation_is_rejected(self) -> None:
        self._configure_pointer_bootstrap_scope()
        pointer = self._read(self.pointer_path)
        pointer["authority_scope_constraints"]["promotion"] = True
        self._resign_pointer(pointer)
        result = self._resolve()
        self.assertEqual(result["state"], "BLOCK_AUTHORITY_SCOPE_ESCALATION")

    def test_20_receive_candidate_scope_remains_supported(self) -> None:
        result = self._resolve()
        self.assertEqual(result["state"], "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED")
        self.assertEqual(result["scope"], ["RECEIVE_CANDIDATE"])



    def test_21_promotion_scope_exact_contract_passes(self) -> None:
        self._configure_promotion_scope()
        result = self._resolve()
        self.assertEqual(result["state"], "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED")
        self.assertEqual(result["scope"], [resolver.PROMOTION_SCOPE])
        self.assertEqual(
            result["authority_scope_constraints"],
            resolver.PROMOTION_SCOPE_CONSTRAINTS,
        )

    def test_22_promotion_scope_rejects_other_candidate(self) -> None:
        self._configure_promotion_scope()
        pointer = self._read(self.pointer_path)
        pointer["authority_scope_constraints"]["candidate_sha256"] = "0" * 64
        self._resign_pointer(pointer)
        result = self._resolve()
        self.assertEqual(result["state"], "BLOCK_AUTHORITY_SCOPE_ESCALATION")

    def test_23_promotion_scope_rejects_mechanism_drift(self) -> None:
        self._configure_promotion_scope()
        pointer = self._read(self.pointer_path)
        pointer["authority_scope_constraints"]["promotion_mechanism_sha256"] = (
            "1" * 64
        )
        self._resign_pointer(pointer)
        result = self._resolve()
        self.assertEqual(result["state"], "BLOCK_AUTHORITY_SCOPE_ESCALATION")

    def test_24_promotion_scope_rejects_forbidden_capability_escalation(self) -> None:
        forbidden = (
            "generic_canonical_write",
            "arbitrary_pointer_write",
            "deploy",
            "restart",
            "authority_management",
            "formal_submission",
            "other_candidate_promotion",
            "historical_mutation",
        )
        for field in forbidden:
            with self.subTest(field=field):
                self.tearDown()
                self.setUp()
                self._configure_promotion_scope()
                pointer = self._read(self.pointer_path)
                pointer["authority_scope_constraints"][field] = True
                self._resign_pointer(pointer)
                result = self._resolve()
                self.assertEqual(
                    result["state"], "BLOCK_AUTHORITY_SCOPE_ESCALATION"
                )

    def test_25_promotion_scope_rejects_mixed_scope(self) -> None:
        self._configure_promotion_scope()
        pointer = self._read(self.pointer_path)
        pointer["authority_scope"] = [
            resolver.PROMOTION_SCOPE,
            "RECEIVE_CANDIDATE",
        ]
        self._resign_pointer(pointer)
        result = self._resolve()
        self.assertEqual(result["state"], "HOLD_AUTHORITY_INCOMPLETE")



if __name__ == "__main__":
    unittest.main(verbosity=2)
